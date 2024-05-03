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
from typing import Optional, Union

import cv2
import numpy as np
from PIL.Image import Image as PILImageType


def pil2cv(image_pil: PILImageType) -> np.ndarray:
    """
    refs. https://qiita.com/derodero24/items/f22c22b22451609908ee
    PIL型 -> OpenCV型"""
    new_image = np.array(image_pil, dtype=np.uint8)
    if new_image.ndim == 2:  # モノクロ
        pass
    elif new_image.shape[2] == 3:  # カラー
        new_image = cv2.cvtColor(new_image, cv2.COLOR_RGB2BGR)
    elif new_image.shape[2] == 4:  # 透過
        new_image = cv2.cvtColor(new_image, cv2.COLOR_RGBA2BGRA)
    return new_image


def cv2pil(image_cv: np.ndarray) -> PILImageType:
    """OpenCV型 -> PIL型"""
    new_image = image_cv.copy()
    if new_image.ndim == 2:  # モノクロ
        pass
    elif new_image.shape[2] == 3:  # カラー
        new_image = cv2.cvtColor(new_image, cv2.COLOR_BGR2RGB)
    elif new_image.shape[2] == 4:  # 透過
        new_image = cv2.cvtColor(new_image, cv2.COLOR_BGRA2RGBA)
    new_image = Image.fromarray(new_image)
    return new_image


def check_work_dir():
    work_dir_path = make_outdir("./", "work_dir")
    return work_dir_path


def check_argv_path(argv: Union[argparse.Namespace, list[str]]) -> str:
    """
    指定のディレクトリパスを存在チェック

    Args:
        argv (argparse.Namespace or list[str]): コマンドライン引数または引数リスト

    Returns:
        str: ディレクトリパス

    Raises:
        IOError: ディレクトリパスが指定されていない場合
        IOError: ディレクトリが存在しない場合
    """
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
    """
    書き出し用ディレクトリを作成

    Args:
        image_dir (str): 画像ディレクトリパス
        dir_name (str): ディレクトリ名

    Returns:
        str: 書き出し用ディレクトリパス
    """
    output_path = join(image_dir, dir_name)
    # print('書き出しディレクトリ:', output_path)
    if not os.path.exists(output_path):
        os.mkdir(output_path)
    return output_path


def make_outdir_from_file(file_path: str) -> str:
    """
    書き出し用ディレクトリを作成

    Args:
        file_path (str): ファイルパス

    Returns:
        str: 書き出し用ディレクトリパス
    """
    output_path = make_outdir(os.path.dirname(file_path), basename(file_path)[:-4])
    return output_path


def img_resize(
    img: np.ndarray, rate: float = 0.5, max_height: Optional[int] = None
) -> np.ndarray:
    """
    画像のリサイズ

    Args:
        img (np.ndarray): 入力画像
        rate (float, optional): リサイズ倍率. Defaults to 0.5.
        max_height (int, optional): リサイズ後の最大高さ. Defaults to None.

    Returns:
        np.ndarray: リサイズ後の画像
    """
    h, w = img.shape[:2]
    if max_height:
        resized_img = cv2.resize(img, (int(w * max_height / h), max_height))
    else:
        resized_img = cv2.resize(img, (int(w * rate), int(h * rate)))
    return resized_img


def img_to_gray(img: np.ndarray) -> np.ndarray:
    """
    カラー画像をグレースケールに変換

    Args:
        img (np.ndarray): 入力画像

    Returns:
        np.ndarray: グレースケール画像
    """
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    return gray


def img_to_canny(
    img: np.ndarray, gf_size: int = 5, min_t: int = 50, max_t: int = 150
) -> np.ndarray:
    """
    画像をCannyエッジ検出処理を適用した画像に変換

    Args:
        img (np.ndarray): 入力画像
        gf_size (int, optional): ガウシアンフィルタのカーネルサイズ. Defaults to 5.
        min_t (int, optional): Cannyエッジ検出の下限閾値. Defaults to 50.
        max_t (int, optional): Cannyエッジ検出の上限閾値. Defaults to 150.

    Returns:
        np.ndarray: Cannyエッジ検出処理を適用した画像
    """
    if len(img.shape) == 3:
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    else:
        gray = img
    gauss = cv2.GaussianBlur(gray, (gf_size, gf_size), 0)
    canny = cv2.Canny(gauss, min_t, max_t)
    return canny


def make_outdir_of_imgfile(
    img_path: str, outdir_name: str = "out", add_name: str = "_out"
) -> str:
    """
    画像ファイルの書き出し用ディレクトリを作成

    Args:
        img_path (str): 画像ファイルパス
        outdir_name (str, optional): 書き出し用ディレクトリ名. Defaults to "out".
        add_name (str, optional): 追加するファイル名. Defaults to "_out".

    Returns:
        str: 書き出し用ファイルパス
    """
    img_dirname = os.path.dirname(img_path)
    outdir = join(img_dirname, outdir_name)
    if not os.path.exists(outdir):
        os.mkdir(outdir)
    new_img_name = basename(img_path).split(".")[0] + add_name + ".png"
    return join(outdir, new_img_name)


def pickle_dump(value, filename: str = "out.pickle") -> None:
    """
    pickleファイルにオブジェクトを保存

    Args:
        value: 保存するオブジェクト
        filename (str, optional): 保存するファイル名. Defaults to "out.pickle".
    """
    with open(filename, "wb") as f:
        try:
            pickle.dump(value, f)
        except pickle.PickleError:
            pickle.dump([value], f)


def pickle_load(filename: str = "out.pickle"):
    """
    pickleファイルからオブジェクトを読み込み

    Args:
        filename (str, optional): 読み込むファイル名. Defaults to "out.pickle".

    Returns:
        Any: 読み込んだオブジェクト
    """
    with open(filename, "rb") as f:
        return pickle.load(f)


def get_path_list(image_dir: str, target_name: str) -> list[str]:
    """
    ディレクトリ中の指定のファイルパスを取得

    Args:
        image_dir (str): ディレクトリパス
        target_name (str): 検索するファイル名

    Returns:
        list[str]: ファイルパスのリスト
    """
    glob_res = glob.glob(join(glob.escape(image_dir), "*{}*".format(target_name)))
    if glob_res:
        return glob_res
    else:
        path_list = []
        for path in os.listdir(image_dir):
            if target_name.replace("*", "") in path:
                path_list.append(join(image_dir, path))
        return path_list


def get_image_path_list(image_dir: str) -> list[str]:
    """
    ディレクトリ中の画像ファイルパスを取得

    Args:
        image_dir (str): ディレクトリパス

    Returns:
        list[str]: 画像ファイルパスのリスト
    """
    image_path_list = get_path_list(image_dir, "*jpg")
    image_path_list.extend(get_path_list(image_dir, "*JPG"))
    image_path_list.extend(get_path_list(image_dir, "*png"))
    image_path_list.extend(get_path_list(image_dir, "*PNG"))

    return image_path_list


def generate_senga(img_src: np.ndarray, n: int = 4) -> np.ndarray:
    """
    線画を生成する

    Args:
        img_src (np.ndarray): 入力画像
        n (int, optional): 近傍法の指定. Defaults to 4.

    Returns:
        np.ndarray: 線画
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
