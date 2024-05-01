# utility系のメソッドを格納
import argparse
import glob
import os
import pickle
import shutil
import subprocess
import time
from contextlib import contextmanager
from os.path import basename, join

import cv2
import numpy as np


def check_argv_path(argv: list) -> str:
    """指定のディレクトリパスを存在チェック"""
    if isinstance(argv, argparse.Namespace):
        target_dir = argv.filepath
    else:
        if len(argv) <= 1:
            raise IOError(
                "処理対象のディレクトリパスを入力してください ex. $ python avg_cut.py path/to/target_dir"
            )
        target_dir = argv[1]
    if not os.path.exists(target_dir):
        raise IOError(target_dir + "は存在しません")

    return target_dir


def make_outdir(image_dir: str, dir_name: str) -> str:
    """書き出し用ディレクトリを作成"""
    output_path = join(image_dir, dir_name)
    # print('書き出しディレクトリ:', output_path)
    if not os.path.exists(output_path):
        os.mkdir(output_path)
    return output_path


def make_outdir_from_file(file_path):
    """書き出し用ディレクトリを作成"""
    output_path = make_outdir(os.path.dirname(file_path), basename(file_path)[:-4])
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


def img_to_canny(img, gf_size=5, min_t=50, max_t=150):
    if len(img.shape) == 3:
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    else:
        gray = img
    gauss = cv2.GaussianBlur(gray, (gf_size, gf_size), 0)
    canny = cv2.Canny(gauss, min_t, max_t)
    return canny


def make_outdir_of_imgfile(img_path, outdir_name="out", add_name="_out"):
    img_dirname = os.path.dirname(img_path)
    outdir = join(img_dirname, outdir_name)
    if not os.path.exists(outdir):
        os.mkdir(outdir)
    new_img_name = basename(img_path).split(".")[0] + add_name + ".png"
    return join(outdir, new_img_name)


def pickle_dump(value, filename="out.pickle"):
    """pickleファイルを保存"""
    with open(filename, "wb") as f:
        try:
            pickle.dump(value, f)
        except pickle.PickleError:
            pickle.dump([value], f)


def pickle_load(filename="out.pickle"):
    """pickleファイルを読み込み"""
    with open(filename, "rb") as f:
        return pickle.load(f)


def get_path_list(image_dir, target_name):
    """ディレクトリ中のtarge_nameを持つファイルパスを取得"""
    # print(glob.escape(image_dir))
    glob_res = glob.glob(join(glob.escape(image_dir), "*{}*".format(target_name)))
    if glob_res:
        return glob_res
    else:
        path_list = []
        for path in os.listdir(image_dir):
            if target_name.replace("*", "") in path:
                path_list.append(join(image_dir, path))
        return path_list


def get_image_path_list(image_dir):
    """ディレクトリ中の画像ファイルパスを取得"""
    image_path_list = get_path_list(image_dir, "*jpg")
    image_path_list.extend(get_path_list(image_dir, "*JPG"))
    image_path_list.extend(get_path_list(image_dir, "*png"))
    image_path_list.extend(get_path_list(image_dir, "*PNG"))

    return image_path_list


def generate_senga(img_src, n=4):
    """線画を得る。近傍法の指定は[4, 8, 24]から。値が大きいほどはっきりした線を得られる
    refs. https://www.blog.umentu.work/python-opencv3%E3%81%A7%E7%94%BB%E7%B4%A0%E3%81%AE%E8%86%A8%E5%BC%B5%E5%87%A6%E7%90%86dilation%E3%81%A8%E5%8F%8E%E7%B8%AE%E5%87%A6%E7%90%86erosion-%E3%81%A1%E3%82%87%E3%81%A3%E3%81%A8%E8%A7%A3/
    refs. http://www.cellstat.net/absdiff/
    """
    # 4近傍の定義
    neiborhood4 = np.array([[0, 1, 0], [1, 1, 1], [0, 1, 0]], np.uint8)
    # 8近傍の定義
    neiborhood8 = np.array([[1, 1, 1], [1, 1, 1], [1, 1, 1]], np.uint8)

    # ２４近傍の定義
    neiborhood24 = np.array(
        [
            [1, 1, 1, 1, 1],
            [1, 1, 1, 1, 1],
            [1, 1, 1, 1, 1],
            [1, 1, 1, 1, 1],
            [1, 1, 1, 1, 1],
        ],
        np.uint8,
    )

    if n == 8:
        neiborhood = neiborhood8
    elif n == 24:
        neiborhood = neiborhood24
    else:
        neiborhood = neiborhood4

    # 膨張処理
    img_dilation = cv2.dilate(img_src, neiborhood, iterations=1)

    # 元画像と膨張処理した画像の差を取る
    img_s = cv2.absdiff(img_src, img_dilation)
    # 白黒を反転
    img_p = cv2.bitwise_not(img_s)

    # カラー画像はグレー化
    if img_p.shape == 3:
        img_p = cv2.cvtColor(img_p, cv2.COLOR_BGR2GRAY)
    return img_p


def run_process(argv):
    print("exec_code: {}".format(" ".join(argv)))
    # コマンドを実行
    if subprocess.call(argv) != 0:
        # print()
        raise OSError("failed: {}".format(" ".join(argv)))


def clean_image(image_dir_path, target, is_gray=True):
    # mogrify -level 25%,83% -deskew 40% -density 150 *.jpg
    # level = config.LEVEL_GRAY if is_gray else config.LEVEL_COLOR
    argv = [
        "mogrify",
        # '-level', '10%,85%',  # レベル補正
        "-deskew",
        "40%",  # 傾きを補正
        # '-density', '100',  # 解像度
        "-density",
        str(150),  # 解像度
        join(image_dir_path, target),
    ]  # g.jpgだけを対象
    run_process(argv)


def clean_dir(dir_path, dir_name):
    output_path = make_outdir(dir_path, dir_name)
    if len(os.listdir(output_path)) >= 3:
        shutil.rmtree(output_path)
        output_path = make_outdir(dir_path, dir_name)


@contextmanager
def timer(name):
    print("[{}] progres...".format(name))
    t0 = time.time()
    yield
    print("[{}] done in {:.3f} s".format(name, time.time() - t0))
