import os
import re
import sys
import unicodedata
import utils

re_kakkotsuki = re.compile('\s?\([0-9a-z]{1,2}\)')


def rename_file(filename):
    newname = filename
    # 全角英数を半角英数に
    newname = unicodedata.normalize('NFKC', newname)
    newname = newname.replace('/', '／')
    newname = newname.replace('2006', '2016').replace('2007', '2017')
    newname = newname.replace('　', ' ')
    # (1)→1巻
    if re_kakkotsuki.search(newname):
        kakkotsuki = re_kakkotsuki.search(newname).group(0).replace(' ', '')
        kanji = kakkotsuki[1:-1]  # 巻次
        newname = newname.replace(kakkotsuki, ' {}巻'.format(kanji.zfill(2)))
    return newname


if __name__ == '__main__':
    pdf_dir = utils.check_argv_path(sys.argv)
    pdf_path_list = utils.get_path_list(pdf_dir, 'pdf')
    print('pdf files:', len(pdf_path_list))

    for pdf_path in pdf_path_list:
        filename = os.path.basename(pdf_path)
        newname = rename_file(filename)
        if filename != newname:
            # print(pdf_path, '->', os.path.join(pdf_dir, newname))
            print(filename, '->', newname)
            if os.path.exists(os.path.join(pdf_dir, newname)):
                print('already exists:', newname)
                continue
            os.rename(pdf_path, os.path.join(pdf_dir, newname))
