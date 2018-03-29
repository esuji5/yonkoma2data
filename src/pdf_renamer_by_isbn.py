# require: zbar, ImageMagick
# TODO: 引数で処理済みのファイルも処理対象にしたりFIND_PAGEを調整したりできるといいなあ
import glob
import os
import re
import sys
import subprocess
from time import sleep
from urllib.error import HTTPError

import bottlenose
from bs4 import BeautifulSoup

import utils
import key_amazon as ka

re_page = re.compile('Pages:\s*[0-9]{1,}')
re_isbn = re.compile('(978[0-9]{10}|491[0-9]{10})')

amazon = bottlenose.Amazon(ka.AMAZON_ACCESS_KEY_ID, ka.AMAZON_SECRET_KEY,
                           ka.AMAZON_ASSOC_TAG, Region='JP')
FIND_PAGE = 3  # 後ろからどれだけのページを探索するか


def pdf_to_isbn(pdf_path):
    def remove_tmp_img(imges_path):
        # 一時ファイルを削除
        tmp_img_list = glob.glob(imges_path)
        for tmp_img in tmp_img_list:
            os.remove(tmp_img)

    # ページ数を取得
    argv1 = ['pdfinfo', pdf_path]
    p1_out = subprocess.check_output(argv1)
    page = re_page.search(str(p1_out)).group(0).split(' ')[-1]

    # 一時ファイル名を設定
    tmp_file = 'tmp-img'
    img_path = os.path.join(os.path.dirname(pdf_path), tmp_file)
    imges_path = '{}*'.format(img_path)

    # 存在する一時ファイルがあれば削除しておく
    remove_tmp_img(imges_path)

    # 対象のページを一時ファイルとしてjpgに切り出す
    # argv2_h = ['pdfimages', '-j', '-l', str(FIND_PAGE), pdf_path, img_path + '_h']
    argv2_t = ['pdfimages', '-j', '-f', str(int(page) - FIND_PAGE + 1), pdf_path, img_path + '_t']
    subprocess.check_call(argv2_t)
    # subprocess.check_call(argv2_h)
    # print(' '.join(argv2_h), ' '.join(argv2_t))
    # jpgからバーコードを読み取り、ISBNがあれば返す
    tmp_img_list = glob.glob(imges_path)

    isbn = None
    for tmp_img in tmp_img_list:
        if not tmp_img.endswith('jpg'):
            continue
        argv3 = ['zbarimg', '-q', tmp_img]
        p3 = subprocess.Popen(argv3, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                              stderr=subprocess.PIPE, shell=False)
        out = str(p3.stdout.readlines())
        if re_isbn.search(out):
            isbn = re_isbn.search(out).group(0)
            break

    # 一時ファイルを削除
    remove_tmp_img(imges_path)
    return isbn


# AmazonのAPIを叩いてxmlを返す
def item_search(isbn, search_index='Books', item_page=1):
    response = amazon.ItemSearch(
        SearchIndex=search_index,
        Keywords=isbn,
        ItemPage=item_page,
        ResponseGroup='Large')
    soup = BeautifulSoup(response, 'xml')
    return soup.findAll('Item')


# 取得したxml(item)から必要な情報を抜き出して新しいファイル名を返す
def get_newname(items):
    item = items[0]
    name_dict = {
        'title': item.find('Title').text,
        'author': item.find('Author').text.replace(' ', '') if item.find('Author') else '',
        'publisher': item.find('Publisher').text,
    }
    # ここでタイトルのフォーマットを設定する
    if '491' in isbn:
        # 雑誌は著者情報が返ってこない
        newname = '[{publisher}]{title}.pdf'.format(**name_dict)
    else:
        newname = '[{publisher}][{author}]{title}.pdf'.format(**name_dict)
    return newname.replace('/', '／')  # ファイルシステム上の禁則文字をreplaceする


# AmazonAPIからxmlを取りにいく。503が返ることが多いのでリトライ機構を持たせている
def fetch_amazon_item(isbn):
    req_count = 0
    # 5回までamazonのAPIにリクエストを投げてみる
    while(req_count < 5):
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
                sleep_time = 2 ** req_count
                print('retry after {} second'.format(sleep_time))
                sleep(sleep_time)
            else:
                # 呼び出し元でエラー内容等を表示
                raise
    return


if __name__ == '__main__':
    pdf_dir = utils.check_argv_path(sys.argv)
    pdf_path_list = utils.get_path_list(pdf_dir, 'pdf')
    print('pdf files:', len(pdf_path_list))
    # 処理済みのファイルを雑に判別して除外
    pdf_path_list = [p for p in pdf_path_list if not os.path.basename(p).startswith('[')]
    pdf_path_list = [p for p in pdf_path_list if os.path.basename(p).startswith('201')]
    for pdf_path in pdf_path_list:
        print(pdf_path)
        isbn = pdf_to_isbn(pdf_path)
        if isbn:
            try:
                amazon_items = fetch_amazon_item(isbn)
            except HTTPError as e:
                print('情報の取得に失敗しました:', pdf_path, isbn)
                continue
            if amazon_items:
                newname = get_newname(amazon_items)
            else:
                newname = str(isbn) + '.pdf'
                # pdfファイルをリネーム
            print(pdf_path, '->', os.path.join(pdf_dir, newname))
            os.rename(pdf_path,
                      os.path.join(pdf_dir, newname))
            # API制限にかからないようにsleepを設定
            sleep(2)
