# coding: utf-8
# require: ImageMagick
# jpgからpngへ
# convert -geometry 1240x1240 -density 300 -deskew 40% *.jpg -set filename:f '%t' 'image-%03d.png'
# jpgからpdfへ
# convert `ls -v` hoge.pdf
# TODO: argparseとwandを使って頑張りたい
from __future__ import print_function
from __future__ import unicode_literals
import os
import sys
import subprocess

import utils

DENSITY = 300  # dpi
MAX_HEIGHT = 1240  # px


def pdf_to_png(root_path):
    for dirpath, _, filenames in os.walk(root_path):
        for filename in filenames:
            if not filename.endswith('.pdf'):
                continue

            # 画像を格納するディレクトリを作成
            output_path = utils.make_outdir(root_path, filename[:-4])

            # 既に実行結果のようなものがある場合はスキップ
            if len(os.listdir(output_path)) > 3:
                continue

            pdf_path = os.path.join(dirpath, filename)
            png_path = os.path.join(output_path, 'image-%03d.png')

            print('convert: {} -> {}'.format(pdf_path, png_path))

            argv = ['convert',
                    # '-define', 'jpeg:size={0}x{0}'.format(MAX_HEIGHT),  # 大きい画像を変換するときに速くなるかも
                    '-deskew', '40%',  # 傾きを補正
                    '-density', str(DENSITY),  # 解像度を指定。未指定は72dpiになってしまう
                    '-geometry', '{0}x{0}'.format(MAX_HEIGHT),  # 最大の画像大きさを指定。縦横比は守られる
                    pdf_path, png_path]

            # コマンドを実行
            if subprocess.call(argv) != 0:
                print('failed: {}'.format(pdf_path))

if __name__ == '__main__':
    root_path = utils.check_argv_path(sys.argv)
    pdf_to_png(root_path)
