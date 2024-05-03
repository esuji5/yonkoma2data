# require: zbar
# TODO: 引数で処理済みのファイルも処理対象にしたりFIND_PAGEを調整したりできるといいなあ
import os
import re
import sys
import unicodedata
from time import sleep
from typing import Optional
from urllib.error import HTTPError

import fitz
from PIL import Image
from pyzbar.pyzbar import decode
from requests_html import HTMLResponse, HTMLSession

import utils

KINOKUNIYA_ZASSHI_SEARCH_URL = "https://www.kinokuniya.co.jp/f/dsg-04-"
KINOKUNIYA_SEARCH_URL = (
    "https://www.kinokuniya.co.jp/disp/CSfDispListPage_001.jsp?qsd=true&ptk=01&gtin="
)

RE_KANJI = re.compile("(<|〈).+?(>|〉)")
RE_ISBN = re.compile("(978[0-9]{10}|491[0-9]{10})")
NO_RESULT_MESSAGE = "該当する結果がありません"
FIND_PAGE = 3  # 最初と最後からどれだけのページを探索するか


def fetch_isbn_from_pdf(pdf_path: str, from_the_back: bool = True) -> str:
    """PDFファイルからISBNを抽出する。

    Args:
        pdf_path (str): PDFファイルのパス。
        from_the_back (bool): ページの後ろから探索するかどうか。

    Returns:
        Optional[str]: 抽出されたISBNコード。見つからない場合はNone。
    """
    with utils.timer("fetch_isbn_from_pdf: " + pdf_path):
        doc = fitz.open(pdf_path)  # ドキュメントを開く
        for page_idx, page in enumerate(
            reversed(doc)
        ):  # ドキュメントのページを反復処理する
            if FIND_PAGE < page_idx <= (len(doc) - FIND_PAGE):
                continue
            xref = page.get_images()[0][0]  # 画像のXREF番号を取得する
            pix = fitz.Pixmap(doc, xref)
            if pix.n < 5:  # 画像がRGBAでない場合は変換する
                pix = fitz.Pixmap(fitz.csRGB, pix)
            image = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
            decoded_list = decode(image)
            jan_code_list = [
                dd.data.decode()
                for dd in decoded_list
                if dd.data.decode().startswith(("978", "491"))
            ]

            if jan_code_list:
                return jan_code_list[0]
    return ""


def item_search(isbn: str) -> Optional[HTMLResponse]:
    """紀伊國屋書店のウェブサイトでISBNに基づいて商品を検索する。

    Args:
        isbn (str): 検索する商品のISBN。

    Returns:
        Optional[HTMLResponse]: 検索結果のHTMLレスポンス。該当する商品がない場合はNone。
    """
    """:return: requests_html.HTMLResponse"""
    if isbn.startswith("491"):
        res = session.get(KINOKUNIYA_ZASSHI_SEARCH_URL + isbn)
    else:
        res = session.get(KINOKUNIYA_SEARCH_URL + isbn)
    if NO_RESULT_MESSAGE in res.text:
        return None
    else:
        return res


def get_book_data(isbn: str, res: HTMLResponse) -> tuple[str, str, str, str]:
    """HTMLレスポンスから書籍または雑誌のデータを抽出する。

    Args:
        isbn (str): 検索した書籍または雑誌のISBN。
        res (HTMLResponse): 紀伊國屋書店の検索結果ページのHTMLレスポンス。

    Returns:
        Tuple[str, str, str, str]: 書籍または雑誌のタイトル、著者（雑誌の場合は空文字）、出版社、発行日を含むタプル。
    """
    if isbn.startswith("491"):  # 雑誌
        author = ""
        page_title = res.html.find("title")[0].text
        publisher = (
            res.html.find("#main_contents > form.formArea.ml00.mr00")[0]
            .find("li")[2]
            .text
        )
    else:
        page_title = res.html.find(
            "#main_contents > form > div.list_area_wrap > div > div.listrightbloc > h3 > a"
        )[0].text
        author = res.html.find(
            "#main_contents > form > div.list_area_wrap > div > div.listrightbloc > div.details > p"
        )[0].text
        publisher_info = res.html.find(
            "#main_contents > form > div.list_area_wrap > div > div.listrightbloc > div.details2.select_section1 > ul > li:nth-child(1)"
        )[0].text
    title = page_title.split(" - ")[0]
    title, page_title, author, publisher_info = [
        unicodedata.normalize("NFKC", t)
        for t in [title, page_title, author, publisher_info]
    ]
    search_kanji = RE_KANJI.search(page_title)
    if search_kanji:
        kanji = search_kanji.group(0).replace("〈", "").replace("〉", "")
        title = f"{title} {kanji}巻"
    publisher_split = publisher_info.split("(")

    publisher = "(".join(publisher_split[:-1])
    publish_date = "(" + publisher_split[-1]
    return title, author, publisher, publish_date


def get_new_name(isbn: str, res: HTMLResponse) -> str:
    """
    ISBNとHTMLレスポンスから新しいファイル名を生成する。

    Args:
        isbn (str): 書籍または雑誌のISBN。
        res (HTMLResponse): 紀伊國屋書店の検索結果ページのHTMLレスポンス。

    Returns:
        str: 新しいファイル名。
    """
    title, author, publisher, publish_date = get_book_data(isbn, res)
    name_dict = {
        "title": title,
        "author": author,
        "publisher": publisher,
        "publish_date": publish_date,
    }
    # ここでタイトルのフォーマットを設定する
    if isbn.startswith("491"):
        # 雑誌は著者情報が返ってこない
        newname = "[{publisher}]{title}{publish_date}.pdf".format(**name_dict)
    else:
        newname = "[{publisher}][{author}]{title}{publish_date}.pdf".format(**name_dict)
    return newname.replace("/", "／")  # ファイルシステム上の禁則文字をreplaceする


def fetch_kinokuniya_item(isbn: str) -> Optional[HTMLResponse]:
    """
    ISBNを使用して紀伊國屋書店のアイテムを検索し、HTMLレスポンスを取得する。

    Args:
        isbn (str): 検索するアイテムのISBNコード。

    Returns:
        Optional[HTMLResponse]: 検索結果のHTMLレスポンス。該当するアイテムがない場合はNoneを返す。
    """
    req_count = 0
    # 3回までリクエストを投げてみる
    while req_count < 3:
        try:
            items = item_search(isbn)
            if items:
                return items
            else:
                return None
        except HTTPError as e:
            # エラーが出たら( ˘ω˘)ｽﾔｧ
            print(e)
            req_count += 1
            if req_count < 3:
                # sleep_timeが徐々に伸びるように設定
                sleep_time = 2**req_count
                print("retry after {} second".format(sleep_time))
                sleep(sleep_time)
            else:
                # 呼び出し元でエラー内容等を表示
                raise
    return None


if __name__ == "__main__":
    pdf_dir = utils.check_argv_path(sys.argv)
    pdf_path_list = utils.get_path_list(pdf_dir, "pdf")
    print("pdf files:", len(pdf_path_list))

    session = HTMLSession()
    # 処理済みのファイルを雑に判別して除外
    pdf_path_list = [
        p for p in pdf_path_list if not os.path.basename(p).startswith("[")
    ]
    for pdf_path in pdf_path_list:
        print(pdf_path)
        isbn = fetch_isbn_from_pdf(pdf_path)
        if not isbn:
            print("Not found isbn")
            continue
        try:
            kinokuniya_item = fetch_kinokuniya_item(isbn)
        except HTTPError as e:
            print("情報の取得に失敗しました:", pdf_path, isbn)
            continue
        except Exception as e:
            print(e, pdf_path, isbn)
            continue
        if kinokuniya_item:
            new_name = get_new_name(isbn, kinokuniya_item)
        else:
            new_name = str(isbn) + ".pdf"
            # pdfファイルをリネーム
        print(pdf_path, "->", os.path.join(pdf_dir, new_name))
        os.rename(pdf_path, os.path.join(pdf_dir, new_name))
        # API制限にかからないようにsleepを設定
        sleep(2)
