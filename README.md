# yonkoma2data

**2024.05.04現在、Pythonや関係ライブラリ、処理内容を大幅にアップデートしています。**

## description
漫画のデジタルデータについて、以下の様な処理を行えます
- PDFファイルのバーコード（JANコード）を読み取り自動リネーム
- PDFファイルをページ毎のPNGファイルに切り出す

また、4コマ漫画に対しては、以下の様な処理も行えます
- ページ毎のPNGファイルを1コマ毎のPNGファイルに切り出す
- コマ中のセリフを抽出する

Python3系とOpenCVを基本として用途に応じて、ImageMagick、zbar等のインストール、Google Cloud Platformのアカウントが必要になります。

## TODO
- サンプルに使える画像ファイルを用意
- テストコード色々用意
- セリフ抜き出しは上下吹き出し対応ができたらコミット予定

## prepare
- install Python3 (3.12) http://www.python.jp/

```
$ git clone https://github.com/esuji5/yonkoma2data
$ cd yonkoma2data
$ pip install -r requirements.txt
```

## PDFファイルのバーコード（JANコード）を読み取り自動リネーム
**TODO: AWSのライブラリ最新版にしたい**
### require
- install zbar(http://zbar.sourceforge.net/)
- install ImageMagick(http://www.imagemagick.org/script/index.php)
- リネームしたいpdfファイル群を入れたディレクトリ

### run
※ファイルを直接リネームするので、念の為ディレクトリ毎コピーを取るのを推奨します
`$ python pdf_renamer_by_isbn.py path/to/pdffiles_dir`

## PDFファイルをページ毎のPNGファイルに切り出す
### require
- install ImageMagick
- 切り出したpdfファイル群を入れたディレクトリ
- ↑を日本語パスが含まれない場所に移動・リネーム(OpenCVが日本語含みのパスを読み込めないため)

### run
`$ python pdf_to_pages.py path/to/pdffiles_dir`

**↑2024.05.04現在、アップデート完了ここまで ↑**

## 傾き補正、美白化を行う
`$ cd path/to/pages`

`$ mogrify -level 25%,83% -deskew 40% -density 200 *.png`
- 以下の値は適宜調整する
    - 傾き補正度 `-deskew`: 35~45%程度
    - 美白度 `-level`: {下限}, {上限}
    - 解像度 `-density`: 100~350程度  

## ページ毎のJPGファイルを1コマ毎のJPGファイルに切り出す。多くの作品に対応版
### require
- ページ毎の画像を入れたディレクトリ
- Python3.12

### run
`$ python amane_cut.py path/to/pages`

### args
| args name | default | more |
| --------- | -------| ------- |
|filepath| | file path|
|-p, --pagetype|normal| choices=[normal, wide, left_start],set page type: [normal(, wide, left_start)]|
|-ws, --with_subtitle| |have subtitle and cut them|
|-ss, --shave_subtitle| |have subtitle and do not have to cut them|
|-ok, --only_koma| |cut only komas|
|-s, --start | 0| start page num
|-e, --end | 0| end page num from last. slice like this [: -1 * end]
|-t, --tobirae| |cut tobirae|
|-x, --pad_x| 50 |set padding size(px) for x|
|-y, --pad_y| 27 |set padding size(px) for y|
|--ext |jpg| target ext|

#### args run exmaple
- 扉絵付き、最初と最後の5ページ分はスキップ
  - `python3 amane_cut.py ~/image/hoge -t -s 5 -e 5`
- 枠線付きサブタイトルがある作品。サブタイトルがいらない場合
  - `python3 amane_cut.py ~/image/hoge -ss`
- 枠線付きサブタイトルがある作品。サブタイトルも保存する場合
  - `python3 amane_cut.py ~/image/hoge -ws`
- 1ページに1本だけ4コマがあるワイドな4コマ作品の場合
  - `python3 amane_cut.py ~/image/hoge -p wide`
- 余白幅をyが50px、xが80pxにする場合
  - `python3 amane_cut.py ~/image/hoge -s 10 -y 50 -x 80`

## コマ中のセリフを抽出する
### require
- prepare Google Cloud Platformのアカウント
- Cloud Vision APIを有効化し、API keyをjsonで保存する

### 画像をOCRをにかける
`$ python3 jpg_to_ocr.py path/to/image_dir_path/`
OCR結果は `path/to/pickle/image_dir_path(_master).pickle` に保存されます。
- `image_dir_path.pickle`: OCR結果を適宜保存するpickle
- `image_dir_path_master.pickle`: 最後までエラーが出ずに動いたら保存されるpickle

### OCR結果を綺麗にしてcsv出力
`$ python3 pickle_to_serif_data.py ~/image/rename_test/pdf_to_jpg/ato.pdf/2_paint_out/0_koma/pickles/0_padding_shave_master.pickle`
