# 1ページの画像から各コマを切り出す処理
import os
import sys

import cv2

from cut import AverageDiffCut
import utils


if __name__ == "__main__":
    image_dir = utils.check_argv_path(sys.argv)
    outdir_name = "koma"
    output_path = utils.make_outdir(image_dir, outdir_name)
    img_path_list = utils.get_path_list(image_dir, "jpg")

    adc = AverageDiffCut()

    # 切り出し座標＝カットポイント(cp)を探すためのループ
    print("切り出し座標を検出しています")
    odd_cp_list = []  # 奇数idxページのカットポイントを格納
    even_cp_list = []  # 偶数idxページのカットポイントを格納
    not_cut_img_path_dict = {}
    for idx, img_path in enumerate(img_path_list):
        img = cv2.imread(img_path)
        img_gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

        # 切り出し座標の探索
        cp_dict = adc.search_cut_point(img_gray)

        print(idx, cp_dict, len(cp_dict["x"]), len(cp_dict["y"]))
        # 切り出し座標が規定の数だけ帰ってきたらリストに追加
        if len(cp_dict["x"]) == adc.cp_num_x and len(cp_dict["y"]) == adc.cp_num_y:
            if idx % 2 == 1:
                odd_cp_list.append(cp_dict)
            else:
                even_cp_list.append(cp_dict)
            # 切り出す
            cut_img_path = os.path.join(output_path, os.path.basename(img_path)[:-4])
            adc.cutout(
                img, cp_dict, img_path=cut_img_path, padding=True, extra_cut=True
            )
        else:
            # 見つからなかったものはリストに入れておいて、後で切り出し座標でカット
            not_cut_img_path_dict[idx] = img_path

    # 平均カットポイントを算出
    odd_page_cp = adc.find_average_point(odd_cp_list)
    even_page_cp = adc.find_average_point(even_cp_list)

    # 平均切り出し座標から画像を切り出すループ
    print("平均切り出し座標から画像を切り出しています")
    for idx, img_path in not_cut_img_path_dict.items():
        img = cv2.imread(img_path)
        if img is None:
            continue
        cut_img_path = os.path.join(output_path, os.path.basename(img_path)[:-4])
        if idx % 2 == 1:
            adc.cutout(
                img, odd_page_cp, img_path=cut_img_path, padding=True, extra_cut=True
            )
        else:
            adc.cutout(
                img, even_page_cp, img_path=cut_img_path, padding=True, extra_cut=True
            )
