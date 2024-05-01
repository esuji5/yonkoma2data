# coding: utf-8
from __future__ import print_function
from __future__ import unicode_literals
from __future__ import division
import os
import sys
import cv2
import numpy as np

import utils
from cut import AverageDiffCut
from cut import LoomingWall


# === 中間処理のビジュアライズ ===
# ---ｙ軸の黒さ平均値を左端、x軸は下端に表示 ---
# for x_index, avg_value in enumerate(row_avg_list):
#     cv2.line(img, (x_index + 1, 1), (x_index + 1, 50), (avg_value, avg_value, avg_value), 1)
# for y_index, avg_value in enumerate(col_avg_list):
#     cv2.line(img, (1, y_index + 1), (50, y_index + 1), (avg_value, avg_value, avg_value), 1)
# --- カットポイントに線を引く ---
# for cx in cp_x:
#     cv2.line(img, (cx, 1), (cx, height), (255, 0, 0), 1)
# for cy in cp_y:
# cv2.line(img, (1, cy), (width, cy), (0, 255, 0), 1)
# --- 画像の表示 ---
# half = cv2.resize(img, (850 * width / height, 850))
# cv2.imshow('result', half)
# cv2.waitKey(0)
# cv2.destroyAllWindows()


def hybrid_cut(img_path):
    # === 現状、looming_wall -> average_diff_cut -> looming_wall の3段処理
    # --- 前処理
    img = cv2.imread(img_path)
    img_gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    adc = AverageDiffCut()
    looming_wall = LoomingWall()

    # ページ番号があると上手くいかないのでそこにかかる程度に下を切っておく
    koma_num_str = os.path.basename(img_path).split("-")[-1][0]
    if koma_num_str.isdigit() and int(koma_num_str) % 4 == 0:
        img_gray = img_gray[: img_gray.shape[0] - (adc.padding_y - 4), :]

    # --- looming_wall
    left, right, top, bottom = looming_wall.search_looming_wallpoint(img_gray)
    img_out = img[top:bottom, left:right]

    # --- average_diff_cut: cut後のサイズが大きいものはAverageDiff法で余分なところを除去
    pad_left, pad_right = 0, 0
    _, width, _ = img_out.shape
    if width > 360:
        adc.diff_threshold = 90

        cp = adc.search_cut_point(img_gray[top:bottom, left:right])
        x = np.array(cp["x"])
        x = np.append(x, [0, right])
        # 左側カットポイント
        pad_left = x[x <= adc.padding_x + 10].max()
        # 右側カットポイント
        if right > 400:
            right_arr = x[x >= right - (adc.padding_x + 5) * 2]
            if len(right_arr) >= 3:
                pad_right = right_arr[1] - right_arr[0]
    # 縦方向はいらなさそう？ 一応残しておく
    # y = np.array(cp['y'])
    # pad_y = y[1] if len(y) > 1 and y[1] <= adc.padding_y else 0

    img_out = img[top:bottom, left + pad_left : right - pad_right]

    # --- looming_wall: カラーのものを切り取ってもう一度同じ処理をするとうまく場合もある
    img_out_gray = cv2.cvtColor(img_out, cv2.COLOR_BGR2GRAY)
    left, right, top, bottom = looming_wall.search_looming_wallpoint(img_out_gray)
    img_out = img_out[top:bottom, left:right]

    oh, ow, _ = img_out.shape
    # if 253 < oh < 253 + adc.padding_y:
    #     print('tall image: {}x{} {}'.format(oh, ow, img_path))
    #     print(pad_y, pad_left, pad_right, y, x)
    # if 328 < ow < 328 + adc.padding_x:
    #     print('wide image: {}x{} {}'.format(oh, ow, img_path))
    #     print(pad_y, pad_left, pad_right, y, x)
    if oh < 245:
        print("short image: {}x{} {}".format(oh, ow, img_path))
        print(pad_left, pad_right)
    if ow < 320:
        print("nallow image: {}x{} {}".format(oh, ow, img_path))
        print(pad_left, pad_right)

    return img_out

    def looming_wall_for(self, img_gray):
        # 繰り返してやるのがちょうどいい場合もある
        img_cut = img_gray.copy()
        left_init, right_init, top_init, bottom_init = self.get_init_postions(img_cut)
        left, right, top, bottom = self.get_init_postions(img_cut)
        pos = [left, right, top, bottom]
        diff_sum_list = [0, 0, 0, 0]

        for i in range(5):
            pos_old = self.get_init_postions(img_cut)
            pos_current = [left, right, top, bottom]
            pos_new = self.search_looming_wallpoint(img_cut)

            diff_list = []
            for idx, pos in enumerate(pos_new):
                # old値から動いてなければdiffを0にする。そのまま計算するとdiff_sumが0に収束するため
                if pos == list(pos_old)[idx]:
                    diff_list.append(0)
                else:
                    diff_list.append(pos - pos_current[idx])

            # 動きがなければ繰り返し処理終了
            if diff_list == [0, 0, 0, 0]:
                break

            # 動きがあればcutした結果を代入して再度処理を行う
            left, right, top, bottom = pos_new
            for idx, diff in enumerate(diff_list):
                diff_sum_list[idx] += diff
            img_cut = img_cut[top:bottom, left:right]

        left, right = left_init + diff_sum_list[0], right_init + diff_sum_list[1]
        top, bottom = top_init + diff_sum_list[2], bottom_init + diff_sum_list[3]

        return (left, right, top, bottom)
