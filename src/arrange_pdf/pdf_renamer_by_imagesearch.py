import os
import sys
import shutil
from io import BytesIO
from time import sleep

import cv2
import numpy as np
import requests
from lxml.html import fromstring
from selenium import webdriver
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.chrome.options import Options

from pdf_to_jpg import pdf_to_page1
from pdf_to_jpg import TMP_FILENAME_PAGE1
import utils


def cl_a(x, y):
    actions = ActionChains(driver)
    actions.move_by_offset(x, y)
    actions.click_and_hold(on_element=None)
    actions.release(on_element=None)
    actions.perform()


def cl_e(elem, x, y):
    ActionChains(driver).move_to_element_with_offset(elem, x, y).click().perform()


def fetch_item_info(page1_path):
    target_url = "https://www.google.co.jp/imghp?hl=ja"
    driver.get(target_url)
    while True:
        try:
            driver.find_element_by_id("qbi").click()
            break
        except:
            print("waiting...")
            sleep(0.1)

    # 画像をアップロード
    driver.find_element_by_id("qbfile").send_keys(page1_path)

    # 類似の画像で頑張るパターン
    elem_imgbox = None
    try:
        elem_imgbox = driver.find_element_by_id("imagebox_bigimages")
    except:
        print("no elem_imgbox")
    if elem_imgbox:
        driver.execute_script(
            "window.scrollTo(0, {});".format(elem_imgbox.location["y"])
        )
        ss_bio = BytesIO(driver.get_screenshot_as_png())
        screen_shot_color = cv2.imdecode(
            np.asarray(bytearray(ss_bio.read()), dtype=np.uint8), 1
        )
        screen_shot_gray = utils.img_to_gray(screen_shot_color)

        row_avg_list = np.average(screen_shot_gray, axis=0)
        diff_list = np.diff(row_avg_list, n=1)
        for idx, diff in enumerate(diff_list):
            if diff != 0:
                trim_x = idx + 1
                break
        w, h = screen_shot_color.shape[:2]
        screen_shot_color = screen_shot_color[0:h, trim_x:w]
        screen_shot_gray = screen_shot_gray[0:h, trim_x:w]

        img_template = cv2.imread(os.path.join(pdf_dir, TMP_FILENAME_PAGE1), 0)
        match_result = cv2.matchTemplate(
            screen_shot_gray, img_template, cv2.TM_CCOEFF_NORMED
        )
        min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(match_result)
        print(min_val, max_val, min_loc, max_loc)
        if max_val < 0.25:
            print("no similar image?")
            return
        top_left = max_loc
        w, h = img_template.shape[::-1]
        bottom_right = (top_left[0] + w, top_left[1] + h)

        # 検出領域を四角で囲んで保存(確認用)
        rect_result = cv2.rectangle(
            screen_shot_color, top_left, bottom_right, (0, 0, 255), 4
        )
        cv2.imwrite(os.path.join(pdf_dir, "rect_result.png"), rect_result)
        # imgboxからの縦オフセット値を取得
        y_scroll = driver.execute_script("return window.pageYOffset;")
        y_elem_loc = elem_imgbox.location["y"]
        x_elem_loc = elem_imgbox.location["x"]
        x_offset, y_offset = (top_left[0], top_left[1])
        if y_elem_loc != y_scroll:
            y_offset = 70
        print("x_offset y_offset:", x_offset, y_offset)
        print("y_elem_loc y_scroll:", y_elem_loc, y_scroll)
        print(
            "elem_imgbox.size[width], x_elem_loc:",
            elem_imgbox.size["width"],
            x_elem_loc,
        )
        print("click:", x_offset - elem_imgbox.size["width"] // 2 + 0, y_offset + 10)
        # import pdb; pdb.set_trace()
        actions = ActionChains(driver)
        if (x_offset - elem_imgbox.size["width"] // 2 + 0) < 0:
            actions.move_to_element_with_offset(
                elem_imgbox, 10, y_offset + 10
            ).click().perform()
        else:
            actions.move_to_element_with_offset(
                elem_imgbox,
                x_offset - elem_imgbox.size["width"] // 2 + 0,
                y_offset + 10,
            ).click().perform()

    target = None
    while target is None:
        sleep(2)
        # 選択した画像の表示ボタンからリンクtargetを設定
        a_list = [
            a
            for a in driver.find_elements_by_css_selector("a.irc_vpl")
            if a.text == "表示"
        ]
        if a_list:
            target = a_list[0].get_attribute("href")
            print("target:", target)
            break

        # 画像が選択されていなければ、最初の画像をクリック
        try:
            print('do: driver.find_elements_by_css_selector("img.rg_ic")[0].click()')
            driver.find_elements_by_css_selector("img.rg_ic")[0].click()
        except:
            print("微妙な結果なのでamazonに頼る")
            # 最良結果を使うパティーン
            best_result = driver.find_elements_by_xpath(
                "//div[contains(text(), 'この画像の最良の推測結果')]"
            )
            if best_result:
                driver.get(
                    best_result[0].find_element_by_tag_name("a").get_attribute("href")
                )
            amazon_a_list = driver.find_elements_by_xpath(
                "//a[contains(@href, 'amazon')]"
            )
            # 商品へのリンクであるものに絞る
            amazon_a_list = [
                a for a in amazon_a_list if "dp" in a.get_attribute("href")
            ]
            if len(amazon_a_list):
                amazon_a_list[0].click()
                sleep(0.1)
                title = driver.find_element_by_id("productTitle").text
                try:
                    author = driver.find_element_by_css_selector("span.author").text[
                        :-4
                    ]
                except:
                    author = ""
                return author, title
            else:
                # ない場合はwhileを抜けてrecommendの情報を使う
                break
    # import pdb; pdb.set_trace()
    sleep(1)
    if target:
        div_list = driver.find_elements_by_css_selector("div.irc_asc")
        div_list = [d.text for d in div_list if d.text != ""]
        if div_list:
            caption = div_list[0]
            return caption
        else:
            # キャプションがない場合はタイトルを使う
            r = requests.get(target)
            tree = fromstring(r.content)
            title = tree.findtext(".//title")
            return title
    else:
        try:
            recommend = driver.find_element_by_css_selector("a._gUb").text
            return recommend
        except:
            return None


if __name__ == "__main__":
    pdf_dir = utils.check_argv_path(sys.argv)
    pdf_path_list = utils.get_path_list(pdf_dir, "pdf")
    pdf_path_list = [p for p in pdf_path_list if p.endswith(".pdf")]
    pdf_path_list = [p for p in pdf_path_list if "[test]" not in p]
    pdf_path_list = [p for p in pdf_path_list if os.path.basename(p).startswith("201")]
    options = Options()
    # ヘッドレスモードを有効にする（次の行をコメントアウトすると画面が表示される）。
    # options.add_argument('--headless')
    # ChromeのWebDriverオブジェクトを作成する。
    if pdf_path_list:
        driver = webdriver.Chrome(chrome_options=options)
        driver.set_window_position(0, 0)
        driver.set_window_size(700, 850)
    else:
        print("no pdf files")
        sys.exit()

    for pdf_path in pdf_path_list[:]:
        print(pdf_path)
        # 1枚目のjpgファイルを作成
        page1_path = pdf_to_page1(pdf_path)
        if not os.path.exists(page1_path):
            raise

        filename = fetch_item_info(page1_path)
        filename = "[test]{}.pdf".format(filename).replace("/", "／")
        if filename:
            print("res:", filename)
            if os.path.exists(os.path.join(pdf_dir, filename)):
                print("already exists")
                continue
            else:
                # pass
                os.rename(pdf_path, os.path.join(pdf_dir, filename))
                print(
                    "rename:{} -> {}".format(pdf_path, os.path.join(pdf_dir, filename))
                )
        else:
            print("no result")
        shutil.os.remove(page1_path)
    driver.close()
