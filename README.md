# ec-search-app

楽天市場とYahoo!ショッピングの商品を検索し、同じ形式で価格比較する最小構成のFlaskアプリです。

## 起動（Windows / PowerShell）

Python 3.10以上を使用します。

```powershell
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

`.env.example` を参考にプロジェクト直下の `.env` に以下を設定してください。既存の `.env` がある場合はそのまま使用できます。

```dotenv
RAKUTEN_APPLICATION_ID=楽天のアプリID
RAKUTEN_ACCESS_KEY=楽天のアクセスキー
YAHOO_CLIENT_ID=Yahoo!のクライアントID
```

```powershell
.\.venv\Scripts\python.exe app.py
```

ブラウザで http://127.0.0.1:5000 を開きます。終了は Ctrl+C です。ローカル開発用サーバーです。

## 機能

- 楽天・Yahoo!をチェックボックスで選択（両方も可）
- 商品名検索、合計表示件数5・10・20・30件、価格の安い順／高い順
- 画像・商品名・価格・サイト名・商品ページURLの共通一覧
- 各APIに件数・価格順を指定し、取得結果を統合して再ソート後、指定件数に制限
- 一方のAPIが失敗しても、もう一方の結果とエラーを表示
- 画像なし・検索結果なし・未入力への対応

全サイト合計の上位件数なので、価格によっては片方のサイトだけが表示されます。送料やポイントは比較に含めません。同一商品の自動照合・ページ送りは未実装です。

## 構成とサイトの追加方法

```text
app.py                 フォームの検証と画面表示
api/rakuten_api.py      既存の楽天API取得処理
api/yahoo_search.py     既存のYahoo! API取得処理
api/search.py           サイト登録・結果統合・価格ソート
templates/index.html   検索フォームと結果一覧
static/style.css       最小限のスタイル
tests/test_search.py    外部APIを呼ばない自動テスト
```

1. `api/` に `search_xxx(keyword, limit=5, sort="price_asc")` を実装します。`sort` は `price_asc` / `price_desc` です。取得先APIでも指定順で検索し、上位 `limit` 件を返してください。
2. 商品を `{"name": str, "price": int, "url": str, "image": str}` のリストに変換します。価格は円単位の整数、画像がない場合は空文字列です。
3. `api/search.py` の `SITES` に表示名と関数を登録します。検索画面の選択肢にも自動で追加されます。

既存の `search_rakuten(keyword)` / `search_yahoo(keyword)` 呼び出しも利用できます（既定5件・価格の安い順）。APIキーはサーバー側の `.env` で管理し、例外の生データを画面に出さない構成です。

## テスト

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

## API仕様

- [楽天市場商品検索API](https://webservice.rakuten.co.jp/documentation/ichiba-item-search)
- [Yahoo!ショッピング商品検索API v3](https://developer.yahoo.co.jp/webapi/shopping/v3/itemsearch.html)