# 吹き出し画像のOCR結果をいい感じにする
import csv
import re
import sys
from pathlib import Path

from PIL import Image, ImageDraw
import cv2

import utils


RE_BALLOON_NG_MATCH = re.compile(
    '(^[0-9]{2,}$|[a-zA-Z()\-\\\/%:;"\'\.,_"]{1,2}|^フ$|^℃$|^ù$|廿|仃|另|יו)', re.UNICODE
)


class TA:
    def __init__(self, text, rect, is_yokogaki):
        self.text = text
        self.rect = rect
        self.is_yokogaki = is_yokogaki


class Balloon:
    def __init__(self, img_path="", ta_list=[]):
        if img_path:
            self.img_path = img_path
            self.img = cv2.imread(img_path)
            if self.img is not None:
                self.height, self.width = self.img.shape[:2]
        if ta_list:
            self.orig_ta_in_koma = ta_list
            self._arrange_ta_in_koma(ta_list[1:])
        else:
            self.orig_ta_in_koma = []
            self.ta_list = []

    def _arrange_ta_in_koma(self, ta_list):
        new_ta_in_koma = []
        for ta in ta_list:
            text = ta.description
            if text:
                rect, is_yokogaki = self._define_rect(ta.bounding_poly.vertices)
                new_ta_in_koma.append(TA(text, rect, is_yokogaki))
        self.ta_list = new_ta_in_koma

    def _define_rect(self, positions):
        """
        yokogaki_positions: [left_top, right_top, right_bottom, left_bottom]
        tategaki_positions: [right_top, right_bottom, left_bottom, left_top]
        rect: [w, h, rw, rh]
        """
        if positions[2].x - positions[0].x > 0:
            #             print('yokogaki!')
            is_yokogaki = True
            lt, rt, rb, lb = positions  # yokogaki
        elif positions[2].x - positions[0].x <= 0:
            is_yokogaki = False
            rt, rb, lb, lt = positions  # tategaki

        area_width = rt.x - lt.x
        area_height = lb.y - lt.y

        rect = [lt.x, lt.y, area_width, area_height]
        return rect, is_yokogaki

    def _sort_ta_by_topright(self, ta_list):
        #         return sorted(ta_list, key=lambda x: )
        return ta_list

    def is_good_ta(self, ta):
        text = ta.text

        # NGリストの文字は多分不正
        if RE_BALLOON_NG_MATCH.search(text):
            print("NG Word: {}".format(text))
            return False
        elif len(text) == 1:
            pass
        #             if "CJK UNIFIED" in unicodedata.name(text) and text not in JOYO_KANJI:
        #                 print('NG KANJI: {}'.format(text))
        #                 return False
        return True

    def get_available_tas(self):
        ta_list = self._sort_ta_by_topright(self.ta_list)
        ta_list = [ta for ta in ta_list if self.is_good_ta(ta)]
        self.ta_list = ta_list

    def _build_serif(self):
        max_char_width = 18

        def split_rect(chars, rect):
            n = len(chars)
            x, y, w, h = rect
            char_w = int(round(w / n))
            char_rects = [[x + i * char_w, y, char_w, h] for i in range(n)]
            # char_rects[-1] = [x + w - max_char_width, y, w, h]
            return char_rects

        def align_rects_v(ta_list):
            new_ta_list = []
            max_v_align_num = 0
            while ta_list:
                rect_list = [ta[1] for ta in ta_list]
                most_right = max([r[0] + r[2] for r in rect_list])
                align_ta_list = [
                    ta
                    for ta in ta_list
                    if most_right - max_char_width < ta[1][0] + ta[1][2] <= most_right
                ]
                [ta_list.remove(ta) for ta in align_ta_list]
                align_ta_list = sorted(align_ta_list, key=lambda x: x[1][1])
                new_ta_list += align_ta_list
                if len(align_ta_list) > max_v_align_num:
                    max_v_align_num = len(align_ta_list)
            print("max_v_align_num:", max_v_align_num)
            return new_ta_list, max_v_align_num

        orig_ta_list = self.ta_list
        text_list = [ta.text for ta in self.ta_list]
        is_yokogaki_list = [ta.is_yokogaki for ta in self.ta_list]
        # 横書き→縦書きの処理をしてセリフ結合
        # 横書きのままセリフ結合

        # 横書きtaが半数以上だったら横書きの処理
        if sum(is_yokogaki_list) >= len(self.ta_list) / 2:
            rect_list = [ta.rect for ta in self.ta_list]
            new_ta_list = zip(text_list, rect_list, is_yokogaki_list)
            char_rect_list = []
            # 1文字毎にtextとrectを分割
            for t, r, _ in new_ta_list:
                if len(t) > 1:
                    chars = list(t)
                    chars_rects = split_rect(chars, r)
                    char_rect_list += zip(chars, chars_rects)
                else:
                    char_rect_list += [(t, r)]

            new_ta_list = sorted(char_rect_list, key=lambda x: -(x[1][0] + x[1][2]))
            new_ta_list, max_v_align_num = align_rects_v(new_ta_list)
            print("include yokogaki")
            if max_v_align_num <= 3:
                print("koreha yoko no mama", max_v_align_num)
                text_list = [ta.text for ta in orig_ta_list]
            else:
                text_list = [ta[0] for ta in new_ta_list]
            return "".join(text_list)
        else:
            # そうでなければ縦書きのセリフ結合
            return "".join(text_list)

    def make_serif(self):
        self.get_available_tas()
        serif = self._build_serif()
        return serif

    # テキスト部分を赤線で囲う
    def highlight_texts(self):
        img_p = Image.fromarray(self.img)
        draw = ImageDraw.Draw(img_p)
        if self.orig_ta_in_koma:
            for text in self.orig_ta_in_koma[1:]:
                color = "#ff6644"
                box = [(v.x, v.y) for v in text.bounding_poly.vertices]
                draw.line(box + [box[0]], width=2, fill=color)
        return img_p


pickle_path = Path(utils.check_argv_path(sys.argv))
img_dir = pickle_path / ".." / pickle_path.name

path_serif_list = []
ta_list = utils.pickle_load(pickle_path)["values"]

for idx, val in enumerate(ta_list[:]):
    img_path = val["image_path"]
    tas_orig = val["text_annotation"]
    bal = Balloon(img_path, tas_orig)
    draw = bal.highlight_texts()
    serif = bal.make_serif()
    path_serif_list.append([img_path, serif])

csv_dir = utils.make_outdir((pickle_path / ".." / "..").resolve(), "csv")

with open(Path(csv_dir) / f"{pickle_path.name}.csv", "w") as csv_file:
    fieldnames = ["img_path", "serif"]
    writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
    writer.writeheader()
    [writer.writerow({fieldnames[0]: p, fieldnames[1]: s}) for p, s in path_serif_list]
