import os
from os.path import basename
from os.path import dirname
from os.path import join
import sys

from pdfminer.converter import PDFPageAggregator
from pdfminer.pdfparser import PDFParser
from pdfminer.pdfdocument import PDFDocument
from pdfminer.pdfinterp import PDFResourceManager
from pdfminer.pdfinterp import PDFPageInterpreter
from pdfminer.pdfpage import PDFPage
from pdfminer.pdfparser import PDFException
from pdfminer.layout import LAParams, LTFigure, LTImage
from PIL import Image

import utils

MAX_WIDTH_JPG1 = 130
PDF_TO_JPG_DIR = 'pdf_to_jpg'
TMP_FILENAME_PAGE1 = 'tmp_pdf_page1.jpg'


def find_images_in_thing(outer_layout, out_dir, page_num, max_width=None):
    for thing in outer_layout:
        if isinstance(thing, LTImage):
            save_image(thing, out_dir, page_num, max_width)


def save_image(lt_image, out_dir='./', filename='hoge', max_width=None):
    """Try to save the image data from this LTImage object, and return the file name"""
    result = None
    if lt_image.stream:
        filedata = lt_image.stream.get_rawdata()
        with open(join(out_dir, filename), 'wb') as fp:
            result = fp.write(filedata)
        if max_width:
            print('max_width:', max_width)
            img = Image.open(join(out_dir, filename))
            w, h = img.size[:2]
            img_resize = img.resize((max_width, h * max_width // w), Image.ANTIALIAS)
            img_resize.save(join(out_dir, filename), 'JPEG')
            # img_resize.save(join(out_dir, filename + '.jpg'), 'JPEG')
        return result


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
    with open(pdf_path, 'rb') as fp:
        # 画像を格納するディレクトリを作成
        out_dir = utils.make_outdir(pdf_to_jpg_dir, basename(pdf_path))
        # 既に実行結果のようなものがある場合はスキップ
        if len(os.listdir(out_dir)) > 3:
            return
        print(out_dir)
        print('checking pdf...')
        parser, document = prev_pdf_parser(fp)
        # Check if the document allows text extraction. If not, abort.
        if not document.is_extractable:
            raise PDFException
        print('create pages...')
        pages = PDFPage.create_pages(document)

        # Process each page contained in the document.
        for idx, page in enumerate(pages):
            page_num = str(idx).zfill(4)
            layout = prev_pdf_layout(page)
            for thing in layout:
                if isinstance(thing, LTImage):
                    save_image(thing, out_dir, 'image-' + page_num + '.jpg')
                if isinstance(thing, LTFigure):
                    find_images_in_thing(thing, out_dir, 'image-' + page_num + '.jpg')


def pdf_to_page1(pdf_path):
    with open(pdf_path, 'rb') as fp:
        parser, document = prev_pdf_parser(fp)

        # Check if the document allows text extraction. If not, abort.
        if not document.is_extractable:
            raise PDFException
        page1 = PDFPage.create_pages(document).__next__()  # next関数が実装されてない？

        layout = prev_pdf_layout(page1)
        for thing in layout:
            if isinstance(thing, LTImage):
                save_image(
                    thing, dirname(pdf_path), TMP_FILENAME_PAGE1, max_width=MAX_WIDTH_JPG1)
            if isinstance(thing, LTFigure):
                find_images_in_thing(
                    thing, dirname(pdf_path), TMP_FILENAME_PAGE1, max_width=MAX_WIDTH_JPG1)
    return join(dirname(pdf_path), TMP_FILENAME_PAGE1)


if __name__ == '__main__':
    pdf_dir = utils.check_argv_path(sys.argv)
    pdf_path_list = utils.get_path_list(pdf_dir, 'pdf')
    pdf_to_jpg_dir = utils.make_outdir(pdf_dir, PDF_TO_JPG_DIR)
    print('pdf files:', len(pdf_path_list))
    # 処理済みのファイルを雑に判別して除外
    for pdf_path in pdf_path_list:
        pdf_to_jpg(pdf_path)
