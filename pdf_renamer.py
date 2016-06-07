# coding: utf-8
# TODO: 引数で処理済みのファイルも処理対象にしたりFIND_PAGEを調整したりできるといいなあ
from __future__ import print_function
from __future__ import unicode_literals
import glob
import os
import re
import sys
import subprocess
from time import sleep
from urllib.error import HTTPError

from bottlenose import api
from bs4 import BeautifulSoup

import utils
import key_amazon_esuji as ka

re_page = re.compile('Pages:\s*[0-9]{1,}')
re_isbn = re.compile('(978[0-9]{10}|491[0-9]{10})')

amazon_api = api.Amazon(ka.AMAZON_ACCESS_KEY_ID, ka.AMAZON_SECRET_KEY,
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

    # 対象のページをjpgに切り出す
    argv2_h = ['pdfimages', '-j', '-l', str(FIND_PAGE), pdf_path, img_path + '_h']
    argv2_t = ['pdfimages', '-j', '-f', str(int(page) - FIND_PAGE + 1), pdf_path, img_path + '_t']
    subprocess.check_call(argv2_t)
    subprocess.check_call(argv2_h)

    # jpgからバーコードを読み取り、ISBNがあれば返す
    tmp_img_list = glob.glob(imges_path)
    isbn = None
    for tmp_img in tmp_img_list:
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
    response = amazon_api.ItemSearch(
        SearchIndex=search_index,
        Keywords=isbn,
        ItemPage=item_page,
        ResponseGroup='Large')
    soup = BeautifulSoup(response, 'lxml')
    return soup.findAll('item')


# 取得したxml(item)から必要な情報を抜き出して新しいファイル名を返す
def get_newname(item):
    item = item[0]
    name_dict = {
        'title': item.find('title').text,
        'author': item.find('author').text.replace(' ', '') if item.find('author') else '',
        'publisher': item.find('publisher').text,
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
            item = item_search(isbn)
            if item:
                return item
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
    # 処理済みのファイルを雑に判別して除外
    pdf_path_list = [p for p in pdf_path_list if not os.path.basename(p).startswith('[')]
    for pdf_path in pdf_path_list:
        isbn = pdf_to_isbn(pdf_path)
        if isbn:
            try:
                amazon_item = fetch_amazon_item(isbn)
            except HTTPError as e:
                print('情報の取得に失敗しました:', pdf_path, isbn)
                continue

            newname = get_newname(amazon_item)
            # pdfファイルをリネーム
            print(pdf_path, '->', os.path.join(pdf_dir, newname))
            os.rename(pdf_path,
                      os.path.join(pdf_dir, newname))
            # API制限にかからないようにsleepを設定
            sleep(2)
