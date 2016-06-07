# coding: utf-8
# utility系のメソッドを格納
from __future__ import print_function
from __future__ import unicode_literals
from __future__ import division
import os
import glob
import pickle


# TODO: argparseを使う方に寄せていきたい
def check_argv_path(argv):
    '''指定のディレクトリパスを存在チェック'''
    if len(argv) <= 1:
        raise IOError('処理対象のディレクトリパスを入力してください ex. $ python avg_cut.py path/to/image_dir')
    image_dir = argv[1]
    if not os.path.exists(image_dir):
        raise IOError(image_dir + 'は存在しません')

    return argv[1]


def make_outdir(image_dir, dir_name):
    '''書き出し用ディレクトリを作成'''
    output_path = os.path.join(image_dir, dir_name)
    print('書き出しディレクトリ:', output_path)
    if not os.path.exists(output_path):
        os.mkdir(output_path)
    return output_path


def make_outdir_of_imgfile(img_path, outdir_name='out', add_name='_out'):
    img_dirname = os.path.dirname(img_path)
    outdir = os.path.join(img_dirname, outdir_name)
    if not os.path.exists(outdir):
        os.mkdir(outdir)
    new_img_name = os.path.basename(img_path).split('.')[0] + add_name + '.png'
    return os.path.join(outdir, new_img_name)


def pickle_dump(value, filename='out.pickel'):
    '''pickleファイルを保存'''
    with open(filename, 'wb') as f:
        pickle.dump(value, f)


def pickle_load(filename='out.pickel'):
    '''pickleファイルを読み込み'''
    with open(filename, 'rb') as f:
        return pickle.load(f)


def get_path_list(image_dir, target_name):
    '''ディレクトリ中のtarge_nameを持つファイルパスを取得'''
    return glob.glob(os.path.join(image_dir, '*{}*'.format(target_name)))


def get_image_path_list(image_dir):
    '''ディレクトリ中の画像ファイルパスを取得'''
    image_path_list = get_path_list(image_dir, '*jpg')
    image_path_list.extend(get_path_list(image_dir, '*JPG'))
    image_path_list.extend(get_path_list(image_dir, '*png'))
    image_path_list.extend(get_path_list(image_dir, '*PNG'))

    return image_path_list


# (WIP)
def resize_images(image_dir, height=1240):
    '''pillowを用いた画像リサイズ'''
    import math
    from PIL import Image
    for image_path in get_path_list(image_dir, 'png'):
        im = Image.open(image_path)
        org_width, org_height = im.size
        expand_rate = height / float(org_height)
        width = int(math.ceil(org_width * expand_rate))
        im = im.resize((width, height), Image.ANTIALIAS)
        im.save(image_path, 'PNG')


def rename_by_index(image_dir):
    '''get_path_listで取得した順にインデックス番号でリネームする'''
    img_path_list = get_path_list(image_dir, 'png')

    for idx, img_path in enumerate(img_path_list, 1):
        new_name = '{}{}'.format(str(idx).zfill(3), img_path[-4:])
        os.rename(img_path, os.path.join(image_dir, new_name))


# (WIP)
def rename_by_pagenum(image_dir):
    '''画像中のページ番号を文字認識させてリネームする'''
    import math
    from PIL import Image
    import pytesseract

    # ページ番号部分の拡大率
    EXPAND_RATE = 5

    image_path_list = get_path_list(image_dir, 'png')

    def fetch_pagenum(im, idx):
        width, height = im.size
        # だいたいこの辺にページ番号があるよっていうのをとりあえず手入力してる
        H_UP = int(math.ceil(100 / float(1240) * height))
        H_DOWN = int(math.ceil(20 / float(1240) * height))
        W_UP = int(math.ceil(120 / float(829) * width))
        W_DOWN = int(math.ceil(60 / float(829) * width))

        im_crop = im.crop((W_DOWN, height - H_UP, W_UP, height - H_DOWN))
        wc, hc = im_crop.size
        # 縦1240px程度の画像だとページ番号の部分が小さすぎて文字認識できないようなので拡大させる
        im_resize = im_crop.resize((wc * EXPAND_RATE, hc * EXPAND_RATE), Image.ANTIALIAS)
        # page_num = pytesseract.image_to_string(im_resize, config="-psm 6")
        # page_num = pytesseract.image_to_string(im_resize, config="nobatch digits")
        # if not page_num or not page_num.isdigit():
        im_crop = im.crop((width - W_UP, height - H_UP, width - W_DOWN, height - H_DOWN))
        wc, hc = im_crop.size
        im_resize = im_crop.resize((wc * EXPAND_RATE, hc * EXPAND_RATE), Image.ANTIALIAS)
        im_resize.save('image/prop_img/{}.png'.format(str(idx).zfill(3)), 'PNG')
        # im_resize.save('/prom_img/{}.png'.format(str(idx).zfill(3), 'PNG', quality=100, optimize=True)
        # import pdb; pdb.set_trace()
        page_num = pytesseract.image_to_string(im_resize, config="-psm 8")
        # page_num = pytesseract.image_to_string(im_resize, config="digits.txt")
        print('page_num:', page_num)

        return page_num

    # 最初に画像認識が上手くいったページを起点に残りのページ番号を振ればいいんじゃない？
    first_page_idx = 0
    first_page_num = 0
    for idx, img_path in enumerate(image_path_list):
        im = Image.open(img_path)
        page_num = fetch_pagenum(im, idx)
        if page_num and page_num.isdigit():
            first_page_idx = idx
            first_page_num = int(page_num)
            # break

    if first_page_idx:
        idx_diff = first_page_num - first_page_idx
        for idx, img_path in enumerate(image_path_list):
            new_filename = '{}.png'.format(str(idx + idx_diff).zfill(3))
            os.rename(os.path.join(image_dir, os.path.basename(img_path)),
                      os.path.join(image_dir, new_filename))
