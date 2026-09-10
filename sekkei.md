# EC価格比較サイト 設計書

## 1. システム構成・ファイル管理

### 1-1. システム構成

<pre>
ブラウザ
  ↓
Webアプリ
  ↓
検索条件の受付・検索処理
  ↓
外部EC系API
  ↓
商品情報を共通形式に変換
  ↓
データベースへ一時保存
  ↓
検索結果を画面表示
</pre>

### 1-2. ディレクトリ構造

<pre>
ec-search-app/
├─ app.py
├─ db.py
├─ search_cache.db
├─ .env
├─ api/
│  ├─ search.py
│  └─ 各API.py
├─ templates/
│  └─ index.html
└─ static/
   └─ style.css
</pre>


### 1-3. 主要ファイル・モジュール

| ファイル・モジュール | 役割 |
|---|---|
| app.py | Webアプリ本体。検索条件の受付、入力確認、検索処理、画面表示の制御 |
| db.py | データベースへの接続、検索結果の保存・取得・削除 |
| api/search.py | 複数の外部APIをまとめて呼び出し、検索結果を統合 |
| api/各API.py | 各外部APIとの通信、取得データを共通形式に変換 |
| templates/index.html | 検索画面・検索結果の表示 |
| static/style.css | 画面デザインの設定 |
| .env | APIキーなどの環境変数を管理 |


## 2. データベース設計

### 2-1. 使用データベース

SQLite

### 2-2. テーブル定義

テーブル名：search_results

| 項目 | 型 | 内容 |
|---|---|---|
| id | INTEGER | 商品データのID |
| search_id | TEXT | 検索ごとに発行する識別ID |
| site | TEXT | 商品を取得したサイト名 |
| name | TEXT | 商品名 |
| price | INTEGER | 商品価格 |
| url | TEXT | 商品ページURL |
| image | TEXT | 商品画像URL |

### 2-3. ER図

<pre>
search_results

PK  id
    search_id
    site
    name
    price
    url
    image
</pre>


## 3. 処理フロー・アルゴリズム

### 3-1. 商品検索処理

<pre>
ユーザーが検索条件を入力
  ↓
app.pyで入力内容を確認
  ↓
新規検索の場合、古い検索結果を削除
  ↓
search.pyへ検索条件を渡す
  ↓
選択された各APIを呼び出す
  ↓
各APIの商品情報を共通形式に変換
  ↓
価格順に並び替え
  ↓
search_idを発行
  ↓
SQLiteへ検索結果を保存
  ↓
指定されたページの商品だけDBから取得
  ↓
index.htmlへ渡して表示
</pre>


### 3-2. ページ切り替え処理

<pre>
ページ番号を選択
  ↓
search_idとページ番号をapp.pyへ送信
  ↓
APIは再検索しない
  ↓
SQLiteから該当ページの商品だけ取得
  ↓
画面へ表示
</pre>


## 4. 外部連携・API仕様

| サービス | 用途 | 主な入力 | 主な取得データ |
|---|---|---|---|
| 楽天市場API | 楽天市場の商品検索 | キーワード、価格、並び順、取得件数 | 商品名、価格、URL、画像 |
| Yahoo!ショッピングAPI | Yahoo!の商品検索 | キーワード、価格、並び順、取得件数 | 商品名、価格、URL、画像 |
| SerpAPI | Google Shopping検索 | キーワード、価格、並び順 | 商品名、価格、URL、画像 |

### 共通化する商品データ

各APIから取得したデータは、アプリ内で以下の共通形式に変換して扱う。

* name：商品名
* price：価格
* url：商品ページURL
* image：商品画像URL
* site：取得元サイト名

### 使用ライブラリ

* requests：外部APIとのHTTP通信
* python-dotenv：.envからAPIキーを取得
* sqlite3：SQLite操作
* pathlib：DBファイルのパス管理
* uuid：検索ごとのsearch_id生成


