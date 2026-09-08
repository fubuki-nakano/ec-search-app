"""サイト登録と横断検索。各APIは同じ引数・商品形式を使う。"""
import requests
from api.rakuten_api import search_rakuten
from api.yahoo_search import search_yahoo

# 表示時のサイト別表示対応表
SITES = {
    "rakuten": {"name": "楽天市場", "search": search_rakuten},
    "yahoo": {"name": "Yahoo!ショッピング", "search": search_yahoo},
}

# app.pyから渡された情報の受け取り
def search_products(keyword, selected_sites, limit, sort):
    # 商品結果とエラーを入れる空リスト
    products, errors = [], []
    # これは選択されたサイトを順番に処理
    # dict.fromkeys() は重複を消す
    for site_id in dict.fromkeys(selected_sites):
        # 選択されたサイトに合わせてSITESから表示形式を呼び出す
        site = SITES[site_id]
        try:
            # API検索
            results = site["search"](keyword, limit=limit, sort=sort)
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
    # 合計の表示件数の制限(指定件数だけ表示)
    return products[:limit], errors