# yonkoma2data

## description
漫画のデジタルデータについて、以下の様な処理を行えます
- PDFファイルのバーコード（JANコード）を読み取り自動リネーム
- PDFファイルをページ毎のPNGファイルに切り出す

また、4コマ漫画に対しては、以下の様な処理も行えます
- ページ毎のPNGファイルを1コマ毎のPNGファイルに切り出す
- コマ中のセリフを抽出する

Python3系とOpenCVを基本として用途に応じて、ImageMagick、zbar等のインストール、Amazon Product Advertising API、Google Cloud Platformのアカウントが必要になります。

## TODO
- サンプルに使える画像ファイルを用意
- テストコード色々用意
- セリフ抜き出しは上下吹き出し対応ができたらコミット予定

## prepare
- install Python3 (3.5推奨) http://www.python.jp/
- install OpenCV (3.0以上推奨) http://opencv.jp/

```
$ git clone https://github.com/esuji5/yonkoma2data
$ cd yonkoma2data
$ pip install -r requirement.txt
```

## PDFファイルのバーコード（JANコード）を読み取り自動リネーム
### require
- install zbar(http://zbar.sourceforge.net/)
- install ImageMagick(http://www.imagemagick.org/script/index.php)
- prepare Amazon Product Advertising API(https://affiliate.amazon.co.jp/gp/advertising/api/detail/main.html)
- src/key_amazon.pyに↑のID、Keyを入力
- リネームしたいpdfファイル群を入れたディレクトリ

### run
`$ python src/pdf_renamer.py path/to/pdffiles_dir`

## PDFファイルをページ毎のPNGファイルに切り出す
### require
- install ImageMagick
- 切り出したpdfファイル群を入れたディレクトリ
- ↑を日本語パスが含まれない場所に移動・リネーム(OpenCVが日本語含みのパスを読み込めないため)

### run
`$ python src/pdf_to_pageimage.py path/to/pdffiles_dir`


## ページ毎のPNGファイルを1コマ毎のPNGファイルに切り出す
### require
- ページ毎の画像を入れたディレクトリ

### run
`$ python src/page_to_koma.py path/to/image_dir`

## コマ中のセリフを抽出する
### require
- prepare Google Cloud Platformのアカウント

WIP
