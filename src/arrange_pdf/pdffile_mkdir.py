import sys
import shutil
from collections import defaultdict

import utils


if __name__ == "__main__":
    pdf_dir = utils.check_argv_path(sys.argv)
    pdf_path_list = utils.get_path_list(pdf_dir, "pdf")

    # 作者名：pdfパスの辞書を作る
    author_dict = defaultdict(list)
    for pdf_path in pdf_path_list:
        if len(pdf_path.split("[")) != 3:
            continue
        author = "[{}]".format(pdf_path.split("[")[2].split("]")[0]).replace(" ", "")
        author_dict[author].append(pdf_path)
    # 作者名毎にmkdirしてpdfファイルを移動
    for author, writing_path_list in author_dict.items():
        author_dir = utils.make_outdir(pdf_dir, author)
        for writing_path in writing_path_list:
            shutil.move(writing_path, author_dir)
