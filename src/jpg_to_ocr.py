import os
import sys
import io
from pathlib import Path

from PIL import ImageDraw
from google.cloud import vision
from google.cloud.vision import types

import utils


def get_image(file_path):
    # Loads the image into memory
    with io.open(file_path, "rb") as image_file:
        content = image_file.read()

    image = types.Image(content=content)
    return image


def get_response_text_annotations(image):
    # Performs label detection on the image file
    response = client.annotate_image(
        {
            "image": image,
            "features": [{"type": vision.enums.Feature.Type.TEXT_DETECTION}],
        }
    )
    return response.text_annotations


# テキスト部分を赤線で囲う
def highlight_texts(img, responce):
    draw = ImageDraw.Draw(img)
    for text in responce[1:]:
        color = "#ff0000"
        box = [
            (v.get("x", 0.0), v.get("y", 0.0)) for v in text["boundingPoly"]["vertices"]
        ]
        draw.line(box + [box[0]], width=2, fill=color)
    return img


if __name__ == "__main__":
    image_dir = Path(utils.check_argv_path(sys.argv))

    key_file_path = "/Users/esuji/Dropbox/program/cvtest/yonkoma2data/src/MyFirstProject-b8427fd28b8d.json"
    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = key_file_path

    # Instantiates a client
    client = vision.ImageAnnotatorClient()

    pickle_dir = utils.make_outdir(image_dir / "..", "pickles")
    image_path_list = sorted(utils.get_path_list(image_dir, ".jpg"))

    ta_list = []
    for idx_koma, image_path in enumerate(image_path_list[100:110]):
        print(idx_koma, image_path)

        try:
            image = get_image(image_path)
            ta = get_response_text_annotations(image)
            ta_list.append({"image_path": image_path, "text_annotation": list(ta)})
            print(ta[0].description)
        except Exception as e:
            print(e)
        finally:
            # OCR結果を適宜保存するpickle
            utils.pickle_dump(
                {"last_idx": idx_koma, "values": ta_list},
                f"{pickle_dir}/{image_dir.name}.pickle",
            )

    # 最後までエラーが出ずに動いたら保存されるpickle
    utils.pickle_dump(
        {"last_idx": idx_koma, "values": ta_list},
        f"{pickle_dir}/{image_dir.name}_master.pickle",
    )
