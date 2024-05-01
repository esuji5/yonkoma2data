# require: zbar, ImageMagick
# TODO: 引数で処理済みのファイルも処理対象にしたりFIND_PAGEを調整したりできるといいなあ
import glob
import os
import re
import subprocess
import sys
import unicodedata
from time import sleep
from urllib.error import HTTPError

import utils
from requests_html import HTMLSession

KINOKUNIYA_SEARCH_URL = (
    "https://www.kinokuniya.co.jp/disp/CSfDispListPage_001.jsp?qsd=true&ptk=01&gtin="
)
KINOKUNIYA_ZASSHI_SEARCH_URL = "https://www.kinokuniya.co.jp/f/dsg-04-"

RE_PAGE = re.compile("Pages:\s*[0-9]{1,}")
RE_KANJI = re.compile("(<|〈).+?(>|〉)")
RE_ISBN = re.compile("(978[0-9]{10}|491[0-9]{10})")
NO_RESULT_MESSAGE = "該当する結果がありません"
FIND_PAGE = 3  # 後ろからどれだけのページを探索するか


def pdf_to_isbn(pdf_path, from_the_back=True):
    # print('pdf_path:', pdf_path)
    def remove_tmp_img(images_path):
        # 一時ファイルを削除
        tmp_img_list = glob.glob(images_path)
        for tmp_img in tmp_img_list:
            os.remove(tmp_img)

    # ページ数を取得
    args_pdfinfo = ["pdfinfo", pdf_path]
    pdfinfo_result = subprocess.check_output(args_pdfinfo)
    page = RE_PAGE.search(str(pdfinfo_result)).group(0).split(" ")[-1]

    # 一時ファイル名を設定
    tmp_file = "tmp-img"
    img_path = os.path.join(os.path.dirname(pdf_path), tmp_file)
    images_path = f"{img_path}*"

    # 存在する一時ファイルがあれば削除しておく
    remove_tmp_img(images_path)

    # target_page = 0
    # if from_the_back:
    #     target_page =
    # 対象のページを一時ファイルとしてjpgに切り出す
    args_pdfimages_from_tail_page = [
        "pdfimages",
        "-j",
        "-f",
        str(int(page) - FIND_PAGE + 1),
        pdf_path,
        img_path + "_t",
    ]
    subprocess.check_call(args_pdfimages_from_tail_page)
    args_pdfimages_from_head_page = [
        "pdfimages",
        "-j",
        "-f",
        "1",
        "-l",
        str(FIND_PAGE),
        pdf_path,
        img_path + "_h",
    ]
    subprocess.check_call(args_pdfimages_from_head_page)
    # jpgからバーコードを読み取り、ISBNがあれば返す
    tmp_img_list = glob.glob(images_path)
    isbn = None
    for tmp_img in tmp_img_list:
        if not tmp_img.endswith("jpg"):
            continue
        args3 = ["zbarimg", "-q", tmp_img]
        p3 = subprocess.Popen(
            args3,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            shell=False,
        )
        out = str(p3.stdout.readlines())
        if RE_ISBN.search(out):
            isbn = RE_ISBN.search(out).group(0)
            print("found isbn:", isbn)
            break

    # 一時ファイルを削除
    remove_tmp_img(images_path)
    return isbn


# 紀伊國屋書店の検索をスクレイピング
def item_search(isbn):
    """:return: requests_html.HTMLResponse"""
    if isbn.startswith("491"):
        res = session.get(KINOKUNIYA_ZASSHI_SEARCH_URL + isbn)
    else:
        res = session.get(KINOKUNIYA_SEARCH_URL + isbn)
    if NO_RESULT_MESSAGE in res.text:
        return
    else:
        return res


def get_book_data(res):
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
        publisher = res.html.find(
            "#main_contents > form > div.list_area_wrap > div > div.listrightbloc > div.details2.select_section1 > ul > li:nth-child(1)"
        )[0].text
    title = page_title.split(" - ")[0]
    title, page_title, author, publisher = [
        unicodedata.normalize("NFKC", t) for t in [title, page_title, author, publisher]
    ]
    search_kanji = RE_KANJI.search(page_title)
    if search_kanji:
        kanji = search_kanji.group(0).replace("〈", "").replace("〉", "")
        title = f"{title} {kanji}巻"
    # import ipdb;ipdb.set_trace()
    publisher, publish_date = publisher.split("(")
    return title, author, publisher, "(" + publish_date


# 取得したxml(item)から必要な情報を抜き出して新しいファイル名を返す
def get_new_name(r):
    title, author, publisher, publish_date = get_book_data(r)
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


def fetch_kinokuniya_item(isbn):
    req_count = 0
    # 5回までamazonのAPIにリクエストを投げてみる
    while req_count < 5:
        try:
            items = item_search(isbn)
            if items:
                return items
            else:
                return
        except HTTPError as e:
            # エラーが出たら( ˘ω˘)ｽﾔｧ
            print(e)
            req_count += 1
            if req_count < 5:
                # sleep_timeが徐々に伸びるように設定
                sleep_time = 2**req_count
                print("retry after {} second".format(sleep_time))
                sleep(sleep_time)
            else:
                # 呼び出し元でエラー内容等を表示
                raise
    return


if __name__ == "__main__":
    pdf_dir = utils.check_argv_path(sys.argv)
    pdf_path_list = utils.get_path_list(pdf_dir, "pdf")
    print("pdf files:", len(pdf_path_list))

    session = HTMLSession()
    # 処理済みのファイルを雑に判別して除外
    # pdf_path_list = [
    #     p for p in pdf_path_list if not os.path.basename(p).startswith("[")
    # ]
    pdf_path_list = [
        p
        for p in pdf_path_list
        if os.path.basename(p) == "[芳文社]まんがタイムきらら 2016年 02 月号 [雑誌]_4910083450165.pdf"
    ]
    for pdf_path in pdf_path_list:
        print(pdf_path)
        isbn = pdf_to_isbn(pdf_path)
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
            new_name = get_new_name(kinokuniya_item)
        else:
            new_name = str(isbn) + ".pdf"
            # pdfファイルをリネーム
        print(pdf_path, "->", os.path.join(pdf_dir, new_name))
        os.rename(pdf_path, os.path.join(pdf_dir, new_name))
        # API制限にかからないようにsleepを設定
        sleep(2)
