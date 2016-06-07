# - * - coding: utf-8 - * -
from __future__ import print_function
from __future__ import unicode_literals
from __future__ import division
import os
import math
import cv2
import numpy as np


# 平均画素値誤差法
class AverageDiffCut(object):
    cp_num_x = 4  # 横方向のカットポイント数
    cp_num_y = 8  # 縦方向のカットポイント数
    diff_threshold = 60  # 枠線があるかどうかのdiff値の境界
    line_width = 4  # 枠線の範疇と判定する太さ（px）
    padding_x = 50  # 平均の切り出し座標から余白を横方向に取る（px）
    padding_y = 27  # 平均の切り出し座標から余白を縦方向に取る（px）

    # 横方向に使う言葉: x, width, column
    # 縦方向に使う言葉: y, height, row
    def search_cut_point(self, img):
        '''入力された画像のカットポイントを検出して返す '''

        def get_big_diff(avg_list):
            # TODO: numpy使って書けそう
            '''しきい値以上のdiffがあるポイントを返す'''
            big_diff_list = []
            for idx in range(1, len(avg_list)):
                if math.fabs(avg_list[idx - 1]) >= self.diff_threshold:
                    big_diff_list.append([idx, avg_list[idx - 1]])
            return big_diff_list

        def find_cut_point(big_diff_list):
            '''しきい値を超えたリストからカットポイントを検出してリストで返す'''
            cp_list = []
            recent_point = 0
            for cp in big_diff_list:
                # 座標位置の差分が設定した線の太さより大きいときにカットポイントを設定
                if cp[0] - recent_point >= self.line_width:
                    # カットポイントの要素数が偶数。白から黒、最初の点
                    if len(cp_list) % 2 == 0 and cp[1] <= 0:
                        cp_list.append(cp[0])
                        recent_point = cp[0]
                    # カットポイントの要素数が奇数。黒から白、最後の点
                    elif len(cp_list) % 2 == 1 and cp[1] >= 0:
                        cp_list.append(cp[0])
                        recent_point = cp[0]
            return cp_list

        # 縦方向と横方向の画素値平均をリストにする
        row_avg_list = np.average(img, axis=0)
        col_avg_list = np.average(img, axis=1)

        # avgのdiffを取り、境界値より大きな座標とそのdiff値をbig_diffに保持
        row_avg_diff = np.diff(row_avg_list, n=1)
        col_avg_diff = np.diff(col_avg_list, n=1)
        row_big_diff = get_big_diff(row_avg_diff)
        col_big_diff = get_big_diff(col_avg_diff)

        # カットポイントを定義
        cp_x = find_cut_point(row_big_diff)
        cp_y = find_cut_point(col_big_diff)

        return {'x': cp_x, 'y': cp_y}

    def cutout(self, img, cut_point, img_path='trim', padding=False, extra_cut=False):
        '''渡した画像とカットポイントでimage_pathに切り出す'''
        px = self.padding_x if padding else 0
        py = self.padding_y if padding else 0
        cp_x = cut_point['x']
        cp_y = cut_point['y']
        for i in range(0, len(cp_y)):
            if i % 2 == 0:
                img_cut_1_4 = img[cp_y[i] - py:cp_y[i + 1] + py, cp_x[2] - px:cp_x[3] + px]
                img_cut_5_8 = img[cp_y[i] - py:cp_y[i + 1] + py, cp_x[0] - px:cp_x[1] + px]
                if extra_cut:
                    # ページ画像から1コマ画像へ一気に切り抜く場合などに使う
                    img_cut_1_4 = hybrid_cut(img=img_cut_1_4, img_path='dum-{}'.format(i // 2 + 1))
                    img_cut_5_8 = hybrid_cut(img=img_cut_5_8, img_path='dum-{}'.format(i // 2 + 5))
                cv2.imwrite('{}-{}.png'.format(img_path, str(i // 2 + 1)), img_cut_1_4)
                cv2.imwrite('{}-{}.png'.format(img_path, str(i // 2 + 5)), img_cut_5_8)

    def find_average_point(self, cp_list):
        '''カットポイントの平均を算出'''
        # TODO: numpy使って書く
        average_list_x = [0 for i in range(self.cp_num_x)]
        average_list_y = [0 for i in range(self.cp_num_y)]
        for cut_point in cp_list:
            for index, cp_value in enumerate(cut_point['x']):
                average_list_x[index] += cp_value
            for index, cp_value in enumerate(cut_point['y']):
                average_list_y[index] += cp_value
        average_cp_x = [i // len(cp_list) for i in average_list_x]
        average_cp_y = [i // len(cp_list) for i in average_list_y]
        return {'x': average_cp_x, 'y': average_cp_y}


# 迫り来る壁法
class LoomingWall(object):
    white_threthould = 210

    def get_init_postions(self, img):
        # looming_wall法の初期値を返す
        height, wigth = img.shape
        left, top = 0, 0
        right = wigth - 1
        bottom = height - 1
        return (left, right, top, bottom)

    def search_looming_wallpoint(self, img):
        # 縦・横方向それぞれの閾値より白い画素値を数える TODO:本当は0 or 1 でよい
        row_white_list = np.sum(img < self.white_threthould, axis=0)
        col_white_list = np.sum(img < self.white_threthould, axis=1)
        left, right, top, bottom = self.get_init_postions(img)

        # それぞれの方向から白いとこしかない列/行から黒い部分がある列/行に変わる位置を保持して返す
        # TODO: もうちょっとエレガントに書けない？
        # 左から走査
        for i in range(len(row_white_list[:AverageDiffCut.padding_x + 10])):
            if row_white_list[i] == 0 and row_white_list[i + 1] > 0:
                left = i
                break
        # 右から走査
        for i in range(len(row_white_list[:AverageDiffCut.padding_x + 10])):
            if row_white_list[-(i + 1)] == 0 and row_white_list[-(i + 2)] > 0:
                right = len(row_white_list) - i - 1
                break
        # 上から走査
        for i in range(len(col_white_list[:AverageDiffCut.padding_y + 10])):
            if col_white_list[i] == 0 and col_white_list[i + 1] > 0:
                top = i
                break
        # 下から走査
        for i in range(len(col_white_list[:AverageDiffCut.padding_y + 10])):
            if col_white_list[-(i + 1)] == 0 and col_white_list[-(i + 2)] > 0:
                bottom = len(col_white_list) - i - 1
                break
        return (left, right, top, bottom)


# (WIP)一番大きい輪郭を抽出して透視変換
class Homograph(object):
    last_approx = None

    def transform_by4(self, img, points):
        points = sorted(points, key=lambda x: x[1])
        if len(points) == 4:
            top = sorted(points[:2], key=lambda x: x[0])
            bottom = sorted(points[2:], key=lambda x: x[0], reverse=True)
            points = np.array(top + bottom, dtype='float32')
        else:
            y_min, y_max = points[0][1], points[-1][1]
            points = sorted(points, key=lambda x: x[0])
            x_min, x_max = points[0][0], points[-1][0]
            points = np.array([np.array([x_min, y_min]),
                               np.array([x_max, y_min]),
                               np.array([x_max, y_max]),
                               np.array([x_min, y_max])],
                              np.float32)

        width = max(np.sqrt(((points[0][0] - points[2][0]) ** 2) * 2),
                    np.sqrt(((points[1][0] - points[3][0]) ** 2) * 2))
        height = max(np.sqrt(((points[0][1] - points[2][1]) ** 2) * 2),
                     np.sqrt(((points[1][1] - points[3][1]) ** 2) * 2))

        dst = np.array([np.array([0, 0]),
                        np.array([width - 1, 0]),
                        np.array([width - 1, height - 1]),
                        np.array([0, height - 1]),
                        ], np.float32)

        # 変換前の座標と変換後の座標を渡すことで透視変換を行う
        trans = cv2.getPerspectiveTransform(points, dst)
        return cv2.warpPerspective(img, trans, (int(width), int(height)))

    def homography(self, img, outdir_name=''):
        orig = img
        # 2値画像に変換
        gray = cv2.cvtColor(orig, cv2.COLOR_BGR2GRAY)
        gauss = cv2.GaussianBlur(gray, (5, 5), 0)
        canny = cv2.Canny(gauss, 50, 150)

        # 2値画像中の輪郭を抽出
        contours = cv2.findContours(canny, cv2.RETR_LIST, cv2.CHAIN_APPROX_NONE)[1]
        # 面積が大きい順にソート
        contours.sort(key=cv2.contourArea, reverse=True)

        if len(contours) > 0:
            arclen = cv2.arcLength(contours[0], True)
            # 輪郭を構成する点を抽出
            approx = cv2.approxPolyDP(contours[0], 0.01 * arclen, True)
            # warp = approx.copy()
            if len(approx) >= 4:
                self.last_approx = approx.copy()
            elif self.last_approx is not None:
                approx = self.last_approx
        else:
            approx = self.last_approx
        rect = self.get_rect_by_points(approx)
        # warped = self.transform_by4(orig, warp[:, 0, :])
        return orig[rect[0]:rect[1], rect[2]:rect[3]]

    def get_rect_by_points(self, points):
        # prepare simple array
        points = list(map(lambda x: x[0], points))

        points = sorted(points, key=lambda x: x[1])
        top_points = sorted(points[:2], key=lambda x: x[0])
        bottom_points = sorted(points[2:4], key=lambda x: x[0])
        points = top_points + bottom_points

        left = min(points[0][0], points[2][0])
        right = max(points[1][0], points[3][0])
        top = min(points[0][1], points[1][1])
        bottom = max(points[2][1], points[3][1])
        return (top, bottom, left, right)


def hybrid_cut(img=None, img_path=''):
    # === 現状、looming_wall -> average_diff_cut -> looming_wall の3段処理
    # --- 前処理
    if img is None:
        img = cv2.imread(img_path)
    img_gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    adc = AverageDiffCut()
    looming_wall = LoomingWall()

    # ページ番号があると上手くいかないのでそこにかかる程度に下を切っておく
    if img_path:
        koma_num_str = os.path.basename(img_path).split('-')[-1][0]
        if koma_num_str.isdigit() and int(koma_num_str) % 4 == 0:
            img_gray = img_gray[:img_gray.shape[0] - (adc.padding_y - 4), :]

    # --- looming_wall
    left, right, top, bottom = looming_wall.search_looming_wallpoint(img_gray)
    img_out = img[top: bottom, left: right]

    # --- average_diff_cut: cut後のサイズが大きいものはAverageDiff法で余分なところを除去
    pad_left, pad_right = 0, 0
    _, width, _ = img_out.shape
    if width > 360:
        adc.diff_threshold = 90

        cp = adc.search_cut_point(img_gray[top: bottom, left: right])
        x = np.array(cp['x'])
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

    img_out = img[top: bottom, left + pad_left: right - pad_right]

    # --- looming_wall: カラーのものを切り取ってもう一度同じ処理をするとうまくいく場合もある
    img_out_gray = cv2.cvtColor(img_out, cv2.COLOR_BGR2GRAY)
    left, right, top, bottom = looming_wall.search_looming_wallpoint(img_out_gray)
    img_out = img_out[top: bottom, left: right]

    return img_out
