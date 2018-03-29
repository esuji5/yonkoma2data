# utility系のメソッドを格納
import glob
import os
import pickle

import cv2
import numpy as np


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
    # print('書き出しディレクトリ:', output_path)
    if not os.path.exists(output_path):
        os.mkdir(output_path)
    return output_path


def make_outdir_from_file(file_path):
    '''書き出し用ディレクトリを作成'''
    output_path = make_outdir(os.path.dirname(file_path), os.path.basename(file_path)[:-4])
    return output_path


def img_resize(img, rate=0.5, max_height=None):
    h, w = img.shape[:2]
    if max_height:
        resized_img = cv2.resize(img, (int(w * max_height / h), max_height))
    else:
        resized_img = cv2.resize(img, (int(w * rate), int(h * rate)))
    return resized_img


def img_to_gray(img):
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    return gray


def make_outdir_of_imgfile(img_path, outdir_name='out', add_name='_out'):
    img_dirname = os.path.dirname(img_path)
    outdir = os.path.join(img_dirname, outdir_name)
    if not os.path.exists(outdir):
        os.mkdir(outdir)
    new_img_name = os.path.basename(img_path).split('.')[0] + add_name + '.png'
    return os.path.join(outdir, new_img_name)


def pickle_dump(value, filename='out.pickle'):
    '''pickleファイルを保存'''
    with open(filename, 'wb') as f:
        pickle.dump(value, f)


def pickle_load(filename='out.pickle'):
    '''pickleファイルを読み込み'''
    with open(filename, 'rb') as f:
        return pickle.load(f)


def get_path_list(image_dir, target_name):
    '''ディレクトリ中のtarge_nameを持つファイルパスを取得'''
    return glob.glob(os.path.join(glob.escape(image_dir), '*{}*'.format(target_name)))


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


def generate_senga(img_src, n=4):
    '''線画を得る。近傍法の指定は[4, 8, 24]から。値が大きいほどはっきりした線を得られる
    refs. https://www.blog.umentu.work/python-opencv3%E3%81%A7%E7%94%BB%E7%B4%A0%E3%81%AE%E8%86%A8%E5%BC%B5%E5%87%A6%E7%90%86dilation%E3%81%A8%E5%8F%8E%E7%B8%AE%E5%87%A6%E7%90%86erosion-%E3%81%A1%E3%82%87%E3%81%A3%E3%81%A8%E8%A7%A3/
    refs. http://www.cellstat.net/absdiff/
    '''
    # 4近傍の定義
    neiborhood4 = np.array([[0, 1, 0],
                            [1, 1, 1],
                            [0, 1, 0]],
                           np.uint8)
    # 8近傍の定義
    neiborhood8 = np.array([[1, 1, 1],
                            [1, 1, 1],
                            [1, 1, 1]],
                           np.uint8)

    # ２４近傍の定義
    neiborhood24 = np.array([[1, 1, 1, 1, 1],
                             [1, 1, 1, 1, 1],
                             [1, 1, 1, 1, 1],
                             [1, 1, 1, 1, 1],
                             [1, 1, 1, 1, 1]],
                            np.uint8)

    if n == 8:
        neiborhood = neiborhood8
    elif n == 24:
        neiborhood = neiborhood24
    else:
        neiborhood = neiborhood4

    # 膨張処理
    img_dilation = cv2.dilate(img_src,
                              neiborhood,
                              iterations=1)

    # 元画像と膨張処理した画像の差を取る
    img_s = cv2.absdiff(img_src, img_dilation)
    # 白黒を反転
    img_p = cv2.bitwise_not(img_s)

    # カラー画像はグレー化
    if img_p.shape == 3:
        img_p = cv2.cvtColor(img_p, cv2.COLOR_BGR2GRAY)
    return img_p


def is_color_img(img):
    h, w = img.shape[:2]
    # 画像の画素値(b,g,r)に分散がないか調べる
    color_std = cv2.resize(img, (32, 32)).std(axis=2).std()

    # ページ焼けで赤みがかかったものをgrayに判定
    b_hist = cv2.calcHist([img], [0], None, [256], [0, 256])
    # g_hist = cv2.calcHist([img], [1], None, [256], [0, 256])
    r_hist = cv2.calcHist([img], [2], None, [256], [0, 256])

    # gray: (b,g,r)はほとんど同じ値になるので分散は小さい
    if color_std < 0.03:
        return False
    # color: 分散が大きければカラー画像
    elif color_std > 12:
        return True
    # akami: 赤ヒストグラムの分布が青より大きく右にずれていれば赤みがかかった画像
    elif r_hist.argmax() - b_hist.argmax() > 10:
        return False
    # akami:
    elif r_hist.argmax() - b_hist.argmax() == 0:
        return False
    # それ以外のカラー画像
    else:
        return True
