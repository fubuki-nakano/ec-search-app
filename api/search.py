"""サイト登録と横断検索。各APIは同じ引数・商品形式を使う。"""
import requests
from api.rakuten_api import search_rakuten
from api.yahoo_search import search_yahoo
from api.google_shopping import search_serp

# 表示時のサイト別表示対応表
SITES = {
    "rakuten": {
        "name": "楽天市場",
        "search": search_rakuten, 
        "max_limit": 30,
        },
    "yahoo": {
        "name": "Yahoo!ショッピング",
        "search": search_yahoo,
        "max_limit": 50,
        },
    "serp": {
        "name": "Google Shopping",
        "search": search_serp,
        "max_limit": 30,
        },
}

# app.pyから渡された情報の受け取り
def search_products(keyword, selected_sites, fetch_limit, sort, min_price=None, max_price=None):
    # 商品結果とエラーを入れる空リスト
    products, errors = [], []
    # これは選択されたサイトを順番に処理
    # dict.fromkeys() は重複を消す
    for site_id in dict.fromkeys(selected_sites):
        # 選択されたサイトに合わせてSITESから表示形式を呼び出す
        site = SITES[site_id]
        try:
            # サイトごとの上限を決める
            site_limit = min(fetch_limit, site["max_limit"])
            # API検索
            results = site["search"](keyword, 
            limit=site_limit, sort=sort,min_price=min_price,
            max_price=max_price,)
            # APIの検索結果にサイト名を追加して表示
            products.extend({**product, "site": site["name"]} for product in results)
            # APIへの通信失敗等でもアプリが停止しない処理
        except (requests.RequestException, ValueError, KeyError, TypeError):
            # 例外にはAPIキー付きURLが含まれる場合があるため表示しない。
            errors.append(
                f"{site['name']}の商品を取得できませんでした。"
                "APIキーの設定や通信状況を確認し、時間をおいて再検索してください。"
            )
    # APIから帰ってきた情報をまとめて価格順に並べる
    products.sort(key=lambda product: product["price"], reverse=sort == "price_desc")
    # 価格順に並べた検索結果をすべてapp.pyへ返す
    return products, errors