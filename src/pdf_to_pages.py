import os
import sys
from os.path import basename, join

import fitz
from PIL import Image, ImageOps

import utils

PDF_TO_PAGES_DIR = "pdf_to_pages"


def save_image(lt_image, out_dir, filename, max_width=None):
    """Try to save the image data from this LTImage object, and return the file name"""
    if not lt_image.stream:
        return

    filedata = lt_image.stream.get_data()
    out_file_name = join(out_dir, filename)

    bits_per_component = lt_image.stream.attrs["BitsPerComponent"]
    if bits_per_component == 8:
        # カラーとグレー画像はそのまま保存
        with open(out_file_name, "wb") as fp:
            fp.write(filedata)
    elif bits_per_component == 1:
        # モノクロ画像はfiledataから作成
        w, h = lt_image.stream.attrs["Width"], lt_image.stream.attrs["Height"]
        img = Image.frombytes("1", (w, h), filedata)
        # グレー化、リサイズ、invertを行って保存
        img = img.convert("L").resize((w // 2, h // 2), Image.ANTIALIAS)
        img = ImageOps.invert(img)
        img.save(out_file_name)

    if max_width:
        print("max_width:", max_width)
        img = Image.open(out_file_name)
        w, h = img.size[:2]
        img_resize = img.resize((max_width, h * max_width // w), Image.ANTIALIAS)
        img_resize.save(out_file_name)


def pdf_to_pages(pdf_path):
    # 画像を格納するディレクトリを作成
    out_dir = utils.make_outdir(pdf_to_pages_dir, basename(pdf_path))

    with utils.timer("extract: " + pdf_path):
        doc = fitz.open(pdf_path)  # ドキュメントを開く
        for page_idx, page in enumerate(doc):  # ドキュメントのページを反復処理する
            xref = page.get_images()[0][0]  # 画像のXREF番号を取得する
            pix = fitz.Pixmap(doc, xref)
            if pix.n < 5:  # 画像がRGBAでない場合は変換する
                pix = fitz.Pixmap(fitz.csRGB, pix)
            image_data = pix.tobytes()
            with open(
                os.path.join(out_dir, f"image-{str(page_idx).zfill(3)}.png"), "wb"
            ) as f:
                f.write(image_data)
            # save_image(thing, out_dir, "image-" + page_num + ".jpg")


if __name__ == "__main__":
    # work_dirを作成し、そこに加工したファイルを格納する
    work_dir = utils.check_work_dir()
    pdf_dir = utils.check_argv_path(sys.argv)
    pdf_path_list = utils.get_path_list(pdf_dir, "pdf")
    pdf_path_list = [path for path in pdf_path_list if not os.path.isdir(path)]
    pdf_to_pages_dir = utils.make_outdir(work_dir, PDF_TO_PAGES_DIR)

    print("pdf files:", len(pdf_path_list))
    for pdf_path in pdf_path_list:
        pdf_to_pages(pdf_path)
