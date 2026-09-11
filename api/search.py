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
        "max_limit": 100,
        },
    "yahoo": {
        "name": "Yahoo!ショッピング",
        "search": search_yahoo,
        "max_limit": 100,
        },
    "serp": {
        "name": "Google Shopping",
        "search": search_serp,
        "max_limit": 40,
        },
}

# app.pyから渡された情報の受け取り
def search_products(
    keyword,
    selected_sites,
    fetch_limit,
    sort,
    min_price=None,
    max_price=None,
    exclude_keywords_text="",
    search_mode="standard",
):
    # 商品結果とエラーを入れる空リスト
    products, errors = [], []
    # 除外キーワードを空白ごとに分ける
    # .split()は、空白を基準に文字列を分割する
    exclude_keywords = exclude_keywords_text.lower().split()
    # 検索キーワードを空白ごとに分ける
    search_keywords = keyword.lower().split()
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
            # 取得した商品を1件ずつ確認
            for product in results:
                product_name = product["name"].lower()
                # 検索精度：標準
                # 検索キーワードのどれか1つが含まれていれば残す
                if search_mode == "standard":
                    if not any(word in product_name for word in search_keywords):
                        continue
                # 検索精度：高
                # 検索キーワードがすべて商品名に含まれているものだけ残す
                elif search_mode == "strict":
                    if not all(word in product_name for word in search_keywords):
                        continue
                # 検索精度：低の場合は一致チェックをしない
                # 除外キーワードが商品名に1つでも含まれていたら除外
                if any(word in product_name for word in exclude_keywords):
                    continue
                # 条件を通った商品だけ追加
                products.append({**product, "site": site["name"]})
            # APIへの通信失敗等でもアプリが停止しない処理
        except (requests.RequestException, ValueError, KeyError, TypeError) as e:
            print(f"{site['name']} エラー:", repr(e))

            errors.append(
                f"{site['name']}では条件に合う商品を取得できませんでした。"
                "検索条件を変えて再検索するか、通信状況を確認して時間をおいてお試しください。"
            )
    # APIから帰ってきた情報をまとめて価格順に並べる
    products.sort(key=lambda product: product["price"], reverse=sort == "price_desc")
    # 価格順に並べた検索結果をすべてapp.pyへ返す
    return products, errors