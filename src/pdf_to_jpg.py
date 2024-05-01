import os
import sys
from os.path import basename, dirname, join

import utils
from pdfminer.converter import PDFPageAggregator
from pdfminer.layout import LAParams, LTImage
from pdfminer.pdfdocument import PDFDocument
from pdfminer.pdfinterp import PDFPageInterpreter, PDFResourceManager
from pdfminer.pdfpage import PDFPage
from pdfminer.pdfparser import PDFException, PDFParser
from PIL import Image, ImageOps


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


def prev_pdf_parser(fp):
    parser = PDFParser(fp)
    document = PDFDocument(parser)
    parser.set_document(document)  # set document to parser
    return parser, document


def prev_pdf_layout(page):
    rsrcmgr = PDFResourceManager()
    laparams = LAParams()
    device = PDFPageAggregator(rsrcmgr, laparams=laparams)
    interpreter = PDFPageInterpreter(rsrcmgr, device)
    interpreter.process_page(page)
    # receive the LTPage object for this page
    layout = device.get_result()
    return layout


def pdf_to_jpg(pdf_path):
    with open(pdf_path, "rb") as fp:
        # 画像を格納するディレクトリを作成
        out_dir = utils.make_outdir(pdf_to_jpg_dir, basename(pdf_path))
        # 既に実行結果のようなものがある場合はスキップ
        if len(os.listdir(out_dir)) > 10:
            print("dir exists: skip")
            return

        with utils.timer("extract: " + pdf_path):
            parser, document = prev_pdf_parser(fp)
            # Check if the document allows text extraction. If not, abort.
            if not document.is_extractable:
                raise PDFException
            pages = PDFPage.create_pages(document)

            # Process each page contained in the document.
            for idx, page in enumerate(pages):
                page_num = str(idx).zfill(4)
                layouts = prev_pdf_layout(page)
                for layout in layouts:
                    for thing in layout:
                        if isinstance(thing, LTImage):
                            # save_image(thing, out_dir, 'image-' + page_num + '.png')
                            save_image(thing, out_dir, "image-" + page_num + ".jpg")


def pdf_to_page1(pdf_path):
    with open(pdf_path, "rb") as fp:
        parser, document = prev_pdf_parser(fp)

        # Check if the document allows text extraction. If not, abort.
        if not document.is_extractable:
            raise PDFException
        # 最初のページを取得
        page1 = PDFPage.create_pages(document).__next__()

        layouts = prev_pdf_layout(page1)
        for layout in layouts:
            for thing in layout:
                save_image(
                    thing,
                    dirname(pdf_path),
                    TMP_FILENAME_PAGE1,
                    max_width=MAX_WIDTH_JPG1,
                )

    return join(dirname(pdf_path), TMP_FILENAME_PAGE1)


if __name__ == "__main__":
    pdf_dir = utils.check_argv_path(sys.argv)
    pdf_path_list = utils.get_path_list(pdf_dir, "pdf")
    pdf_path_list = [path for path in pdf_path_list if not os.path.isdir(path)]
    pdf_to_jpg_dir = utils.make_outdir(pdf_dir, PDF_TO_JPG_DIR)

    print("pdf files:", len(pdf_path_list))
    for pdf_path in pdf_path_list:
        pdf_to_jpg(pdf_path)
