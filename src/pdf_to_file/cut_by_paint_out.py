import numpy as np
import cv2
from matplotlib import cm

veryfy_pix = 20
con_size_th = 500


def get_canny(img, gf_size=5, min_t=50, max_t=150):
    if len(img.shape) == 3:
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    else:
        gray = img
    gauss = cv2.GaussianBlur(gray, (gf_size, gf_size), 0)
    canny = cv2.Canny(gauss, min_t, max_t)
    return canny


def parse_contours(contours):
    '''contours: [x, y, w, h, size]'''
    left_cons, right_cons = [], []
    tobira = np.array([])
    # sizeで降順ソート
    sorted_cons = sorted(contours, key=lambda x: -x[4])
    # 最外殻（ページ画像そのもの）を取り出しておく
    orig = sorted_cons.pop(0)
    orig_w, orig_h = orig[2], orig[3]
    sorted_cons = [c for c in sorted_cons if not (c[2] > orig_w * 0.9 and c[3] > orig_h * 0.9)]

    if len(sorted_cons) < 2:
        print('contours　less than 2!')
        return left_cons, right_cons, tobira

    # 扉絵らしきものがあれば取り出しておく
    first_w, first_h = sorted_cons[0][2], sorted_cons[0][3]
    second_w, second_h = sorted_cons[1][2], sorted_cons[1][3]
    ue_or_shita_tobira = first_w > second_w * 1.3 and first_h > second_h * 1.3
    right_tobira = second_w * 0.9 < first_w < second_w * 1.1 and first_h > second_h * 3
    if ue_or_shita_tobira or right_tobira:
        tobira = sorted_cons.pop(0)
    # 小さすぎる領域を削除
    cons_koma = [c for c in sorted_cons if c[2] > 200 and c[3] > 50]
    # sort by y
    cons_koma = sorted(cons_koma, key=lambda x: x[1])

    # 領域のleft_positionがページ画像幅の半分より左か右かで分ける
    for con in cons_koma:
        con_left_position = con[0]
        if con_left_position < orig_w / 2 * 0.45:
            left_cons.append(con)
        else:
            right_cons.append(con)
    return left_cons, right_cons, tobira


def make_paint_out_img(img, canny, verify=False):
    _, _, contours, _ = cv2.connectedComponentsWithStats(canny)
    contours = sorted([c for c in contours if c[4] > con_size_th], key=lambda x: -x[4])
    if not contours:
        return

    # 最外殻（ページ画像そのもの）を取り出しておく
    orig = contours.pop(0)
    orig_width, orig_height = orig[2], orig[3]
    # 最外殻以外で大きすぎるものを除外
    contours = [c for c in contours if not (c[2] > orig_width * 0.9 and c[3] > orig_height * 0.9)]

    if not contours:
        return

    for idx, con in enumerate(contours):
        x, y, w, h, size = con
        if verify:
            if idx < 8:
                color = cm.Set1(idx % 8)
            elif idx < 16:
                color = cm.Set2(idx % 8)
            else:
                color = cm.Set3(idx % 8)
            color = [int(c * 255) for c in color[:3]]
        else:
            color = (192, 192, 192)  # GAのカラー画像、棺担ぎのクロが抜けるようになった

        img_p = cv2.rectangle(img, (x, y), (x + w, y + h), color, -1)

        if verify:
            img_p[veryfy_pix * idx: veryfy_pix * idx + veryfy_pix, :veryfy_pix] = color
    return img_p
