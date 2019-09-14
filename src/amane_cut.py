'''あまねく4コマを切り取るすごいやつだよ'''
import argparse
import os
from os.path import basename
from os.path import join
import shutil

import cv2
import numpy as np

import pdf_to_file.cut_by_paint_out as cut_po
import utils


def cut_koma(con, img, padding=False):
    px = padding_x if padding else 0
    py = padding_y if padding else 0

    x, y, w, h, size = con
    # paddingで画像幅を超えないように調整
    cut_y = y - py if y - py >= 0 else 0
    cut_y_h = y + h + py if y + h + py < img.shape[0] else img.shape[0] - 1
    cut_x = x - px if x - px >= 0 else 0
    cut_x_w = x + w + py if x + w + py < img.shape[1] else img.shape[1] - 1
    koma = img[cut_y: cut_y_h, cut_x: cut_x_w]

    return koma


def imwrite(cut_path, koma_id, img, sufix=''):
    cv2.imwrite('{}-{}{}.jpg'.format(cut_path, koma_id, sufix), img)


def find_average_point(cp_list):
    '''カットポイントの平均を算出
    args cp_list: [(left_cons, right_cons)]
    cons: (x, y, w, h, size)
    '''
    def calc_mean(cons):
        if cons.any():
            orig_sh = cons.shape
            rs_cons = cons.reshape((orig_sh[0], orig_sh[1] * orig_sh[2]))
            return rs_cons.mean(axis=0).reshape((orig_sh[1], orig_sh[2])).astype(int)
        else:
            return np.array([])

    all_left_cons = np.array([cp[0] for cp in cp_list])
    mean_left_cons = calc_mean(all_left_cons)
    if args.pagetype == 'wide':
        mean_right_cons = np.array([])
    else:
        all_right_cons = np.array([cp[1] for cp in cp_list])
        mean_right_cons = calc_mean(all_right_cons)
    return mean_left_cons, mean_right_cons


def make_labeled_contours(img, kind):
    if img is None:
        return
    canny1 = cut_po.get_canny(img)
    img_p1 = cut_po.make_paint_out_img(img, canny1)

    canny2 = None
    if img_p1 is None:
        if kind == '2nd':
            canny2 = canny1
        else:
            return
    if canny2 is None:
        canny2 = cut_po.get_canny(img_p1)
    # 画像をラベリングして輪郭群を取得
    _, _, contours, _ = cv2.connectedComponentsWithStats(canny2)
    return contours


def exec_paint_out_cut(img_path_list, kind):
    '''nyaa式改修版'''
    if kind == '1st':
        if args.end:
            target_path_list = enumerate(img_path_list[args.start: -1 * args.end])
        else:
            target_path_list = enumerate(img_path_list[args.start:])
    else:
        target_path_list = enumerate(img_path_list)
    for idx, img_path in target_path_list:
        # print(img_path)
        img = cv2.imread(img_path)
        img_o = img.copy()
        contours = make_labeled_contours(img, kind)
        if contours is None:
            continue
        if len(contours) < 2 and kind == '1st':
            print('contours　less than 2:', img_path)
            continue

        if kind == '1st':
            is_good_cons, is_nice_size = False, False
            left_cons, right_cons, tobira = cut_po.parse_contours(contours)
            len_right, len_left = len(right_cons), len(left_cons)
            # print(len(left_cons), len(right_cons), tobira.any())
            if args.pagetype == 'wide':
                is_good_cons = len_left == good_cons_num_y and not len_right
            elif args.tobirae and tobira.any():
                is_good_cons = len_left + len_right == good_cons_num_y
            else:
                is_good_cons = len_left == len_right and len_right == good_cons_num_y

            # コマサイズの分散が大きいものは変な切り抜きになっているので除外
            if is_good_cons:
                if args.with_subtitle or args.shave_subtitle:
                    left_size_std = np.array(left_cons[1:]).std(axis=0)[4]
                    right_size_std = np.array(right_cons[1:]).std(axis=0)[4]
                elif args.tobirae and tobira.any():
                    # left_size_stdに4コマ分をまとめて計算
                    left_size_std = np.array(left_cons + right_cons).std(axis=0)[4]
                    right_size_std = 0
                else:
                    left_size_std = np.array(left_cons).std(axis=0)[4] if left_cons else 0
                    right_size_std = np.array(right_cons).std(axis=0)[4] if right_cons else 0
                is_nice_size = left_size_std < 100 and right_size_std < 100

            cut_path = join(output_shaved_path, basename(img_path)[:-4])

            if is_good_cons and is_nice_size:
                # 切り抜き
                if tobira.any():
                    print('tobira', img_path)
                    imwrite(cut_path, 0, cut_koma(tobira, img_o, False))
                if args.pagetype == 'left_start':
                    right_cons, left_cons = left_cons, right_cons
                if args.shave_subtitle:
                    right_cons, left_cons = right_cons[1:], left_cons[1:]

                [imwrite(cut_path, i + 1, cut_koma(con, img_o, False))
                    for i, con in enumerate(right_cons)]
                [imwrite(cut_path, i + 1 + len_right, cut_koma(con, img_o, False))
                    for i, con in enumerate(left_cons)]

                # 扉絵切り抜きがなければ切り抜き位置を保存
                if not tobira.any():
                    if idx % 2 == 1:
                        odd_cp_list.append((left_cons, right_cons))
                    else:
                        even_cp_list.append((left_cons, right_cons))
            else:
                # 見つからなかったものはリストに入れておいて、後で平均切り出し座標でカット
                not_cut_img_path_dict[idx] = img_path

        elif kind == '2nd':
            cut_path = join(output_shaved_path, basename(img_path)[:-4])
            shaved_img = exec_po_2nd(img_o, contours)
            cv2.imwrite('{}-{}.jpg'.format(cut_path, 'shaved'), shaved_img)


def exec_po_2nd(img_o, contours):
    sorted_contours = sorted(contours, key=lambda x: -x[4])
    # 最外殻の次が切り抜きたい部分
    if len(sorted_contours) > 1:
        sorted_contours.pop(0)
    x, y, w, h, size = sorted_contours[0]
    # 小さくなりすぎたら元の画像のまま
    orig_h, orig_w = img_o.shape[:2]
    if w < (orig_w - padding_x * 2) * 0.9 or h < (orig_h - padding_y * 2) * 0.9:
        shaved_img = img_o
    else:
        shaved_img = img_o[y: y + h, x: x + w]
    return shaved_img


def detect_only_koma(left_cons, right_cons, even_page_cp, odd_page_cp, img_o):
    # 平均コマ面積を求める
    all_mean = (np.array(even_page_cp) + np.array(odd_page_cp)) / 2
    all_mean = all_mean.mean(axis=1).mean(axis=0)
    mean_area = all_mean[2] * all_mean[3]
    # shaveした後とする前で面積を比較
    right_imgs = [cut_koma(con, img_o, True) for i, con in enumerate(right_cons)]
    left_imgs = [cut_koma(con, img_o, True) for i, con in enumerate(left_cons)]
    right_s_imgs = [exec_po_2nd(im, make_labeled_contours(im, '2nd')) for im in right_imgs]
    left_s_imgs = [exec_po_2nd(im, make_labeled_contours(im, '2nd')) for im in left_imgs]
    right_s_area = np.array([im.shape[0] * im.shape[1] for im in right_s_imgs])
    left_s_area = np.array([im.shape[0] * im.shape[1] for im in left_s_imgs])

    # 平均コマ面積の95~110%に収まっているか:
    # True -> shaveされたコマ画像, False -> コマ画像以外の可能性が高い
    lh, ht = 0.95, 1.1
    r_nice_size = (mean_area * lh <= right_s_area) * (right_s_area <= mean_area * ht)
    l_nice_size = (mean_area * lh <= left_s_area) * (left_s_area <= mean_area * ht)
    print(r_nice_size, l_nice_size)
    # コマがない1枚絵のページ。全てがFalseの場合はコマ画像がない可能性が高い
    if not r_nice_size.any() and not l_nice_size.any():
        return [], []
    # その他、上半分がFalseなら上に扉絵のあるページ等、判定したいが精度が低い
    # 試行錯誤の跡をonly_koma.pyに残す

    return left_cons, right_cons


# メインの処理
parser = argparse.ArgumentParser()
parser.add_argument('filepath')
parser.add_argument('-p', '--pagetype',
                    default='normal', choices=['normal', 'wide', 'left_start'],
                    help=('set page type: [normal(default), wide, left_start]'))
parser.add_argument('-ws', '--with_subtitle', action="store_true",
                    help=('have subtitle and cut them'))
parser.add_argument('-ss', '--shave_subtitle', action="store_true",
                    help=('have subtitle and do not have to cut them'))
parser.add_argument('-ok', '--only_koma', action="store_true",
                    help=('cut only komas'))
parser.add_argument('-s', '--start', type=int, default="0",
                    help=('start page num'))
parser.add_argument('-e', '--end', type=int, default="0",
                    help=('end page num from last. slice like this [: -1 * end]'))
parser.add_argument('-t', '--tobirae', action="store_true",
                    help=('cut tobirae'))
parser.add_argument('-x', '--pad_x', default=50, type=int,
                    help=('set padding size(px) for x'))
parser.add_argument('-y', '--pad_y', default=27, type=int,
                    help=('set padding size(px) for y'))
parser.add_argument('--ext', default='jpg', help=('target ext'))
args = parser.parse_args()
print(args)

image_dir = utils.check_argv_path(args)
padding_x = args.pad_x
padding_y = args.pad_y
good_cons_num_y = 4
if args.with_subtitle or args.shave_subtitle:
    good_cons_num_y += 1

# 出力ディレクトリ・パスを準備
outdir_name = '2_paint_out'
output_path = utils.make_outdir(image_dir, outdir_name)

output_koma_path = utils.make_outdir(output_path, '0_koma')
if len(os.listdir(output_koma_path)) >= 3:
    shutil.rmtree(output_path)
    output_path = utils.make_outdir(image_dir, outdir_name)
    output_koma_path = utils.make_outdir(output_path, '0_koma')
output_shaved_path = utils.make_outdir(output_koma_path, '0_padding_shave')


# paint_out処理: 1st
img_path_list = utils.get_path_list(image_dir, args.ext)
print('pages:', len(img_path_list) - (args.start + args.end))
with utils.timer('paint_out処理: 1st 切り抜き位置が求められた画像を切り抜き'):
    odd_cp_list = []  # 奇数idxページのカットポイントを格納
    even_cp_list = []  # 偶数idxページのカットポイントを格納
    not_cut_img_path_dict = {}
    exec_paint_out_cut(img_path_list, kind='1st')

    # 平均切り出し座標を算出
    even_page_cp = find_average_point(even_cp_list)
    odd_page_cp = find_average_point(odd_cp_list)

print('lens', len(img_path_list) - len(not_cut_img_path_dict))

# 平均切り出し座標から画像を切り出すループ
if not_cut_img_path_dict:
    with utils.timer('平均切り出し座標から画像を切り出しています'):
        for idx, img_path in not_cut_img_path_dict.items():
            img = cv2.imread(img_path)
            if img is None:
                continue
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            # 白すぎな画像を除外
            if gray.mean() >= 250:
                continue
            img_o = img.copy()
            cut_path = join(output_koma_path, basename(img_path)[:-4])
            left_cons, right_cons = odd_page_cp if idx % 2 == 1 else even_page_cp
            if args.only_koma:
                print(img_path)
                left_cons, right_cons = detect_only_koma(
                    left_cons, right_cons, even_page_cp, odd_page_cp, gray)
            [imwrite(cut_path, i + 1, cut_koma(con, img_o, True), '-pad')
                for i, con in enumerate(right_cons)]
            [imwrite(cut_path, i + 1 + len(right_cons), cut_koma(con, img_o, True), '-pad')
                for i, con in enumerate(left_cons)]
else:
    print('平均切り出し座標はありません')

# paint_out処理: 2nd padding削ぎ落とし
img_path_list = utils.get_path_list(output_koma_path, '-pad.jpg')
print('komas:', len(img_path_list))
with utils.timer('paint_out処理: 2nd padding削ぎ落とし'):
    exec_paint_out_cut(img_path_list, kind='2nd')
