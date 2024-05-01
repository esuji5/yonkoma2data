import io

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


if __name__ == "__main__":
    # Instantiates a client
    client = vision.ImageAnnotatorClient()

    pickle_dir = utils.make_outdir("./", "pickles")
    pickle_list = utils.get_path_list(pickle_dir, ".pickle")
    image_dir_base = "/Users/esuji/work/yuyu_data/yuyu{}/koma"

    for idx_kanji in [str(i).zfill(2) for i in range(1, 10)]:
        master_str = f"{idx_kanji}_master.pickle"
        if master_str in [s[-len(master_str) :] for s in pickle_list]:
            continue
        # elif f'{idx_kanji}.pickle' in pickle_list:
        #     utils.pickle_load()
        start_idx = 0

        print(idx_kanji + "巻")
        image_path_list = sorted(
            utils.get_path_list(image_dir_base.format(idx_kanji), ".jpg")
        )

        ta_list = []
        for idx_koma, image_path in enumerate(image_path_list, start=start_idx):
            print(idx_koma, image_path)
            try:
                image = get_image(image_path)
                ta = get_response_text_annotations(image)
                ta_list.append({"image_path": image_path, "text_annotation": list(ta)})
                print(ta[0].description)
            except Exception as e:
                print(e)
            finally:
                utils.pickle_dump(
                    {"last_idx": idx_koma, "values": ta_list},
                    f"./pickles/yuyu{idx_kanji}.pickle",
                )
        utils.pickle_dump(
            {"last_idx": idx_koma, "values": ta_list},
            f"./pickles/yuyu{idx_kanji}_master.pickle",
        )

    ds = [ta["text_annotation"][0].description for ta in ta_list]
