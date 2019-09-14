import os
import pathlib
from collections import defaultdict
import re
import unicodedata

import cv2
import numpy as np

import utils
from extract_serif.joyo_kanji import JOYO_KANJI


SKIP_SIZE_EVAL_LIST = {'!', '?', '一', '...', '…', 'が', 'か', 'く', 'へ', 'と', '1', '2', '3'}
SKIP_LONG_WIDTH_LIST = {'一', 'が', 'か'}
SKIP_NG_WORD_LIST = {'1', '2', '3', '8', 'UFO'}
RE_BALLOON_NG_MATCH = re.compile('(^[0-9]{2,}$|^[a-zA-Z()\-\\\/%:;\"\'\.,_"!ー]{1,}[0-9a-zA-Z]?|^フ$|^℃$|^ù$|廿|仃|另|יו)',
                                 re.UNICODE)
NG_HEIGHT_RATIO = 0.03
NG_LONG_WIDTH_RATIO = 1.3
NG_LONG_WIDTH_RATIO = 2.5


class TA:
    def __init__(self, text, rect):
        self.text = text
        self.rect = rect


class Koma:
    def __init__(self, img_path='', ta_in_koma=[]):
        if img_path:
            self.img_path = img_path
            self.img = cv2.imread(img_path)
            if self.img is not None:
                self.height, self.width = self.img.shape[:2]
        if ta_in_koma:
            self._arrange_ta_in_koma(ta_in_koma[1:])
        else:
            self.ta_in_koma = []
        self.ta_in_balloon = []
        self.serif_list = []

    def _arrange_ta_in_koma(self, ta_in_koma):
        new_ta_in_koma = []
        for ta in ta_in_koma:
            text = ta.description
            if self.filter_ta_text(text):
                # text = clean_text(text)
                new_ta_in_koma.append(TA(text, self._define_rect(ta.bounding_poly.vertices)))
        self.ta_in_koma = new_ta_in_koma

    def filter_ta_text(self, text):
        ng_tuple = ("亍", "宁", "佇", "■", "𠆤", "枣", "令ひ", "0")
        # print(text)
        if len(text) <= 2 and text.startswith(ng_tuple):
            return False
        return True

    def _is_japanese_char(self, char):
        # ref. http://minus9d.hatenablog.com/entry/2015/07/16/231608
        name = unicodedata.name(char)
        japanese_char = ("CJK UNIFIED", "HIRAGANA", "KATAKANA")
        if name.startswith(japanese_char) or "MARK" in name or 'HORIZONTAL ELLIPSIS' in name:
            return True
        return False

    def _define_rect(self, positions):
        '''
        yokogaki_positions: [left_top, right_top, right_bottom, left_bottom]
        tategaki_positions: [right_top, right_bottom, left_bottom, left_top]
        rect: [w, h, rw, rh]
        '''
        if positions[2].x - positions[0].x > 0:
#             print('yokogaki!')
            lt, rt, rb, lb = positions  # yokogaki
        elif positions[2].x - positions[0].x <= 0:
            rt, rb, lb, lt = positions  # tategaki

        area_width = rt.x - lt.x
        area_height = lb.y - lt.y

        rect = [lt.x, lt.y, area_width, area_height]
        return rect

    def is_good_ta(self, ta):
        # NGリストの文字は多分不正
        if ta.text not in SKIP_NG_WORD_LIST:
            if RE_BALLOON_NG_MATCH.search(ta.text):
                print('NG Word: {}'.format(ta.text))
                return False
            elif len(ta.text) == 1:
                if not self._is_japanese_char(ta.text):
                    print('NG char: {}'.format(ta.text))
                    return False
                elif "CJK UNIFIED" in unicodedata.name(ta.text) and ta.text not in JOYO_KANJI:
                    print('NG KANJI: {}'.format(ta.text))
                    return False

        area_width, area_height = ta.rect[2:]

        # 小さすぎる領域は多分不正。でもSKIP_SIZE_EVAL_LISTに入っている文字は間違いやすいからここをSKIP
        if ta.text not in SKIP_SIZE_EVAL_LIST:
            if area_height < self.height * NG_HEIGHT_RATIO:
                print('NG small area height: {}'.format(ta.text))
                print('{} < {} * {} = {}'.format(area_height, self.height, NG_HEIGHT_RATIO,
                                                 self.height * NG_HEIGHT_RATIO))
                return False
            if area_width < self.width * (NG_HEIGHT_RATIO - 0.01):
                print('NG small area width: {}'.format(ta.text))
                print('{} < {} * {} = {}'.format(area_width, self.width, NG_HEIGHT_RATIO,
                                                 self.width * NG_HEIGHT_RATIO))
                return False

        # 横長の領域は多分不正
        if ta.text not in SKIP_LONG_WIDTH_LIST:
            if area_width > area_height * NG_LONG_WIDTH_RATIO:
                print('NG long width: {}'.format(ta.text))
                print('{} > {} * {}'.format(area_width, area_height, NG_LONG_WIDTH_RATIO))
                    # return False

        return True

    def get_available_tas(self):
        tas = self.ta_in_koma[1:]
        tas = [ta for ta in tas if self.is_good_ta(ta)]
        self.ta_in_koma = tas

    def find_ta_in_balloon(self):
        # 吹き出し内にあるtaを探す
        mask = np.zeros((self.height + 2, self.width + 2), np.uint8)
        flooded_try = self.img.copy()
        flood_rect_set = set()
        for ta in self.ta_in_koma:
            target = tuple(ta.rect[:2])

            # 既に定義された吹き出し内のtaはスキップ
            continue_flg = False
            for rect in flood_rect_set:
                x, y, rw, rh = rect
                if x < target[0] < x + rw and y < target[1] < y + rh:
                    continue_flg = True
                    break
            if continue_flg:
                continue

            # 塗りつぶしを行い、塗りつぶし範囲のrectを取得
            pre_flooded = flooded_try.copy()
            _, img_fl, _, flood_rect = cv2.floodFill(
                flooded_try, mask, target, newVal=(30, 100, 220), loDiff=(5, 5, 5), upDiff=(250, 250, 250))
            x, y, rw, rh = flood_rect
            area = rw * rh
            img_fl[target[1] - 5:target[1] + 5, target[0] - 5:target[0] + 5] = (255, 0, 100)

            # 塗りつぶした範囲が適正なら吹き出しと判断
            is_nice_x_range = self.width * 0.1 < rw < self.width * 0.7
            is_nice_y_range = self.height * 0.1 < rh < self.height * 0.999
            is_nice_area = 0.03 < area / (self.width * self.height) < 0.45
            rect_mean_val = (self.img[y:y + rh, x:x + rw] > 200).mean()
            is_white = rect_mean_val > 0.68
            if area and is_nice_x_range and is_nice_y_range and is_nice_area and is_white:
                flood_rect_set.add(flood_rect)
            else:
                flooded_try = pre_flooded

            # display(Image.fromarray(canny[y-off:y+rh+off, x-off:x+rw+off]))
            # display(Image.fromarray(img_fl))
            print(ta.text, target, flood_rect, area, is_nice_x_range, is_nice_y_range, is_nice_area, is_white)
            print(self.width * 0.1, rw, self.width * 0.7, '|', self.height * 0.1, rh, self.height * 0.999,
                  '|', 0.03, area / (self.width * self.height), 0.45, rect_mean_val)
            # print(target, rect, area, bp['text'], area / (w*h), rect_mean_val)
        # xの降順、yの昇順でソート。右上の吹き出しから順番になるように
        s = sorted(flood_rect_set, key=lambda x: x[1], reverse=False)
        rect_list = sorted(s, key=lambda x: x[0] + x[2], reverse=True)
        print('rects:', len(rect_list), rect_list)
        self.balloon_rect_list = rect_list

    def devide_ta_by_balloon_area(self):
        # 吹き出し毎にtaを分ける
        ta_rect_dict = defaultdict(list)
        for rect in self.balloon_rect_list:
            print(rect)
            x, y, rw, rh = rect
            for ta in self.ta_in_koma:
                ta_x, ta_y = ta.rect[:2]
                if x < ta_x < x + rw and y < ta_y < y + rh:
                    ta_rect_dict[rect] += [ta]
        self.ta_rect_dict = ta_rect_dict

    def make_serif_list(self):
        self.get_available_tas()
        self.find_ta_in_balloon()
        self.devide_ta_by_balloon_area()
        cnt = 1
        serif_list = []
        for rect, split_tas in self.ta_rect_dict.items():
            x, y, rw, rh = rect
            area = rw * rh
            r_area_sum = 0
            for ta in split_tas:
                x, y, ta_rw, ta_rh = ta.rect
                r_area = ta_rw * ta_rh
                r_area_sum += r_area
            if np.abs(r_area_sum / area) < 0.02:
                print('dame?', ''.join([ta.text for ta in split_tas]), area, r_area_sum, r_area_sum / area)
            else:
                serif = ''.join([ta.text for ta in split_tas])
                print(cnt, serif, area, r_area_sum, r_area_sum / area)
                serif_list.append([rect, serif])
                cnt += 1
        print('------------------------------------------------------')
        self.serif_list = serif_list
        return serif_list