import os
from os.path import basename
from os.path import join
import subprocess
import sys

import cv2

import config
import utils
from pdf_to_jpg import PDF_TO_JPG_DIR

NEW_JPG_DIR = 'adir'
CLEAN_PDF_DIR = 'clean_pdf'
CLEAN_PDF_SUFFIX = '_clean'


def devide_jpgs(jpg_dir, norm_img_size=True):
    '''カラーならc.jpg、グレーでよければグレスケ化してg.jpgで保存'''
    out_dir = utils.make_outdir(jpg_dir, NEW_JPG_DIR)
    for jpg_path in utils.get_path_list(jpg_dir, 'jpg'):
        img = cv2.imread(jpg_path)
        if img is None:
            continue

        # norm_img_sizeが指定されていればリサイズ
        if norm_img_size:
            img = utils.img_resize(img, max_height=config.MAX_HEIGHT)

        if utils.is_color_img(img):
            cv2.imwrite(join(out_dir, basename(jpg_path).replace('.jpg', 'c.jpg')), img)
        else:
            img = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            cv2.imwrite(join(out_dir, basename(jpg_path).replace('.jpg', 'g.jpg')), img)


def run_process(argv):
    print('exec_code: {}'.format(' '.join(argv)))
    # コマンドを実行
    if subprocess.call(argv) != 0:
        print('failed: {}'.format(' '.join(argv)))


def clean_jpg_gray(jpg_dir_path):
    # mogrify -level 25%,83% -deskew 40% -density 150 *g.jpg
    argv = ['mogrify',
            '-level', config.LEVEL_GRAY,  # グレスケ用のレベル補正
            '-deskew', '45%',  # 傾きを補正
            # '-density', '100',  # 解像度
            '-density', str(config.DENSITY_LOW),  # 解像度
            join(jpg_dir_path, '*g.jpg')]  # g.jpgだけを対象
    run_process(argv)


def clean_jpg_color(jpg_dir_path):
    # mogrify -level 5%,95% -deskew 40% -density 150 *c.jpg
    argv = ['mogrify',
            '-level', config.LEVEL_COLOR,  # カラー用のレベル補正
            '-deskew', '35%',  # 傾きを補正
            # '-density', '100',  # 解像度
            '-density', str(config.DENSITY_LOW),  # 解像度
            join(jpg_dir_path, '*c.jpg')]  # g.jpgだけを対象
    run_process(argv)


def jpg_to_pdf(jpg_dir_path, pdf_path):
    # convert -quality 20 *.jpg 元pdf_clean.pdf
    argv = ['convert',
            '-quality', str(config.PDF_QUALITY),  # pdfの圧縮率
            join(jpg_dir_path, '*.jpg'),  # すべてのjpgを対象
            pdf_path.replace('.pdf', '{}.pdf'.format(CLEAN_PDF_SUFFIX))  # 出力するpdf
            ]
    run_process(argv)


if __name__ == '__main__':
    pdf_dir = utils.check_argv_path(sys.argv)
    pdf_path_list = utils.get_path_list(pdf_dir, '.pdf')
    clean_pdf_dir = utils.make_outdir(pdf_dir, CLEAN_PDF_DIR)
    print('pdf files:', len(pdf_path_list))
    for pdf_path in pdf_path_list:
        jpg_dir_path = join(os.path.dirname(pdf_path), PDF_TO_JPG_DIR, basename(pdf_path))

        if not os.path.isdir(jpg_dir_path):
            continue

        # jpgファイルをグレスケとカラーで分別
        # devide_jpgs(jpg_dir_path, norm_img_size=False)

        new_jpg_dir_path = join(jpg_dir_path, NEW_JPG_DIR)

        # 美白化と傾き補正
        # clean_jpg_gray(new_jpg_dir_path)
        # clean_jpg_color(new_jpg_dir_path)

        # jpgファイルをpdf化
        clean_pdf_path = join(os.path.dirname(pdf_path), CLEAN_PDF_DIR, basename(pdf_path))
        jpg_to_pdf(new_jpg_dir_path, clean_pdf_path)
