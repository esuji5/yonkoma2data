import unicodedata
import re
from itertools import combinations
from operator import itemgetter

import cv2
import numpy as np
from PIL import ImageDraw
from sklearn.cluster import KMeans

import utils
from extract_serif.joyo_kanji import JOYO_KANJI


SKIP_SIZE_EVAL_LIST = {'!', '?', '一', '...', '…', 'が', 'か', 'く', 'へ', 'と'}
SKIP_LONG_WIDTH_LIST = {'一', 'が', 'か'}
SKIP_NG_WORD_LIST = {'1', '2', '3', '8', 'UFO'}
RE_BALLOON_NG_MATCH = re.compile('(^[0-9]{2,}$|^[a-zA-Z()\-\\\/%:;\"\'\.,_"]{1,}$|^フ$|^℃$|^ù$)',
                                 re.UNICODE)


class Koma:
    def __init__(self, img_path=''):
        if img_path:
            self.img_path = img_path
            self.img = cv2.imread(img_path)
            if self.img is not None:
                self.img_height, self.img_width = self.img.shape[:2]


class Balloons(Koma):
    NG_HEIGHT_RATIO = 0.03
    NG_LONG_WIDTH_RATIO = 1.3
    ta_rect_list = []

    def _text_replace(self, text):
        table = str.maketrans({
            'ー': '-',
            'か': '力',
            'か': 'カ',
        })
        result = text.translate(table)
        return result

    def _define_rect(self, positions):
        ''' positions = [left_top, right_top, right_bottom, left_bottom] lt={x:val, y:val}'''
        lt, rt, rb, lb = positions
        # rect = x, y, w, h の形式で返す。なぜかx,yの値が無いことがあるのでその場合は0を入れておく
        rect = [lt.get('x', 0), lt.get('y', 0),
                rt.get('x', 0) - lt.get('x', 0), lb.get('y', 0) - lt.get('y', 0)]
        return rect

    def get_ta_value(self, text_annotation):
        pos = self._define_rect(text_annotation['boundingPoly']['vertices'])
        text = text_annotation['description'].replace('\n', '')
        text = self._text_replace(text)
        return {'rect': pos, 'text': text}

    def detect_balloon(self):
        for ta in self.ta_list:
            h, w = self.img.shape[:2]
            mask = np.zeros((h+2, w+2), np.uint8)
            flooded_try = self.img.copy()
            rect_set = set()
            for ta in self.ta_list:
                # if ta['text'].startswith(("亍", "宁", "佇", "■", "𠆤", "枣", "令ひ")):
                    # continue
                target = (ta['rect'][0], ta['rect'][1])

                # 塗りつぶしを行い、塗りつぶし範囲のrectを取得
                _, _, _, rect = cv2.floodFill(
                    flooded_try, mask, target, (0, 0, 220), (1, 1, 1), (250, 250, 250))
                x, y, rw, rh = rect
                area = rw * rh

                # 塗りつぶした範囲が適正なら吹き出しと判断
                is_nice_x_range = w * 0.1 < rw < w * 0.7
                is_nice_y_range = h * 0.1 < rh < h * 0.999
                is_nice_area = 0.03 < area / (w * h) < 0.45
                mean_val = (self.img[y:y + rh, x:x + rw] > 200).mean()
                is_white = mean_val > 0.68
                if area and is_nice_x_range and is_nice_y_range and is_nice_area and is_white:
                    rect_set.add(rect)
                    # print(target, rect, area, bp['text'], area / (w*h), mean_val)
            # xの降順、yの昇順でソート。右上の吹き出しから順番になるように
            s = sorted(rect_set, key=itemgetter(1), reverse=False)
            rect_list = sorted(s, key=itemgetter(0), reverse=True)
            self.ta_rect_list = rect_list

    def _detect_laped(self, a, b):
        ax, ay, aw, ah = a['rect']
        bx, by, bw, bh = b['rect']

        sx = np.array([ax, bx]).max()
        sy = np.array([ay, by]).max()
        ex = np.array([ax + aw, bx + bw]).min()
        ey = np.array([ay + ah, by + bh]).min()

        w = ex - sx
        h = ey - sy
        if w > 0 and h > 0:
            return True

    def define_balloon(self, text_annotations):
        # 不正っぽいtext_annotationの結果を取り除く
        ta_list = [self.get_ta_value(ta) for ta in text_annotations[1:] if self.is_good_ta(ta)]

        # taが重複している領域をいい感じにする
        for combi in list(combinations(ta_list, 2)):
            is_duprect = self._detect_laped(*combi)
            if is_duprect:
                try:
                    # 文字数が少ないtaを除去。それが一緒なら後のtaを除去
                    if len(combi[1]['text']) > len(combi[0]['text']):
                        ta_list.remove(combi[0])
                    else:
                        ta_list.remove(combi[1])
                    print(combi)
                except KeyError:
                    print('already removed:', combi[1])
        self.ta_list = ta_list

        # 吹き出しの領域を検出
        self.detect_balloon()
        # 吹き出し毎にtaを分ける
        self.ta_rect_dict = {}
        for rect in self.ta_rect_list:
            x, y, w, h = rect
            for ta in self.ta_list:
                ta_x, ta_y, _, _ = ta['rect']
                if x < ta_x < x + w and y < ta_y < y + h:
                    try:
                        self.ta_rect_dict[rect] += [ta]
                    except KeyError:
                        self.ta_rect_dict[rect] = [ta]

        # 吹き出し内で縦に分かれていたら、いい感じにする
        for rect, ta_list in self.ta_rect_dict.items():
            # 吹き出しの高さ/画像の高さによって縦に分割されてそうか判断
            balloon_height_rate = rect[3] / self.img.shape[0]
            if balloon_height_rate > 0.8:
                # 2クラスに分類
                print(rect[3], self.img.shape[0], rect[3] / self.img.shape[0])
                y_positions = [[i['rect'][1]] for i in ta_list]
                clf = KMeans(n_clusters=2).fit(y_positions)
                classes = clf.predict(y_positions)  # 0か1に分類される

                # 分類結果でta_listを分割
                ta_list_1 = [ta for ta, cls in zip(ta_list, classes) if cls == 0]
                ta_list_2 = [ta for ta, cls in zip(ta_list, classes) if cls == 1]
                x1, y1, w1, h1 = ta_list_1[0]['rect']
                x2, y2, w2, h2 = ta_list_2[0]['rect']
                x1l, y1l, w1l, h1l = ta_list_1[-1]['rect']
                x2l, y2l, w2l, h2l = ta_list_2[-1]['rect']
                print('わかれて〜：', y1l + h1l - y2, y2l + h2l - y1)
                # 新しいtaのリストを作成してself.ta_rect_dict[rect]に設定する
                if y1 < y2:
                    new_ta_list = ta_list_1 + [{'text': '\n'}] + ta_list_2
                else:
                    new_ta_list = ta_list_2 + [{'text': '\n'}] + ta_list_1
                self.ta_rect_dict[rect] = new_ta_list

        # 吹き出しidとtaのjoinを作成
        self.text_list = []
        for ta_list in self.ta_rect_dict.values():
            text = "".join([i['text'] for i in ta_list])
            print(text)
            self.text_list.append(text)

    def is_good_ta(self, text_annotation):
        ta_value = self.get_ta_value(text_annotation)
        rect, text = ta_value['rect'], ta_value['text']

        # NGリストの文字は多分不正
        if text not in SKIP_NG_WORD_LIST:
            # is_japanese = len(text) == 1 and is_japanese_char(text)
            # is_japanese_kanji = len(text) == 1 and "CJK UNIFIED" in unicodedata.name(text) and text in
            if RE_BALLOON_NG_MATCH.search(text):
                print('NG Word: {}'.format(text))
                return False
            elif len(text) == 1:
                if not is_japanese_char(text):
                    print('NG char: {}'.format(text))
                    return False
                elif "CJK UNIFIED" in unicodedata.name(text) and text not in JOYO_KANJI:
                    print('NG KANJI: {}'.format(text))
                    return False

        area_width, area_height = rect[2:]

        # 小さすぎる領域は多分不正。でもSKIP_SIZE_EVAL_LISTに入っている文字は間違いやすいからここをSKIP
        if text not in SKIP_SIZE_EVAL_LIST:
            if area_height < self.img_height * self.NG_HEIGHT_RATIO:
                print('NG small area height: {}'.format(text))
                print('{} < {} * {} = {}'.format(area_height, self.img_height, self.NG_HEIGHT_RATIO,
                                                 self.img_height * self.NG_HEIGHT_RATIO))
                return False
            if area_width < self.img_width * (self.NG_HEIGHT_RATIO - 0.01):
                print('NG small area width: {}'.format(text))
                print('{} < {} * {} = {}'.format(area_width, self.img_width, self.NG_HEIGHT_RATIO,
                                                 self.img_width * self.NG_HEIGHT_RATIO))
                return False

        # 横長の領域は多分不正
        if text not in SKIP_LONG_WIDTH_LIST:
            if area_width > area_height * self.NG_LONG_WIDTH_RATIO:
                print('NG long width: {}'.format(text))
                print('{} > {} * {}'.format(area_width, area_height, self.NG_LONG_WIDTH_RATIO))
                return False

        return True


def is_japanese_char(char):
    # ref. http://minus9d.hatenablog.com/entry/2015/07/16/231608
    name = unicodedata.name(char)
    japanese_char = ("CJK UNIFIED", "HIRAGANA", "KATAKANA")
    if name.startswith(japanese_char) or "MARK" in name or 'HORIZONTAL ELLIPSIS' in name:
        return True
    return False

# テキスト部分を赤線で囲う
def highlight_texts(img, responce):
    draw = ImageDraw.Draw(img)
    for text in responce[1:]:
        color = '#ff0000'
        box = [(v.get('x', 0.0), v.get('y', 0.0)) for v in text['boundingPoly']['vertices']]
        draw.line(box + [box[0]], width=2, fill=color)
    return img


if __name__ == '__main__':
    ta_list = utils.pickle_load('pickles/yuyu4.pickle')

    vsplit = ('017-5.png', '022-1.png', '028-8.png', '038-5.png', '041-2.png','053-6.png','028-1.png','034-3.png','039-6.png','053-6.png',
              '058-5.png', '065-6.png', '066-7.png', '075-3.png', '079-1.png', '092-1.png', '095-3.png')
    bal_list = []
    for idx, ta in enumerate(ta_list[:]):
        # if not ta[0].endswith(vsplit):
        #     continue
        print(ta[0].replace('cut_images_wide/knife_cut/knife_cut-', 'koma/'))
        bal = Balloons(ta[0].replace('cut_images_wide/knife_cut/knife_cut-', 'koma/'))
        if bal.img is not None:
            # bal.NG_HEIGHT_RATIO = 0.03
            bal.define_balloon(ta[1])
            bal_list.append(bal)
