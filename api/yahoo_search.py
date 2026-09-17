import time
import os
import requests
from dotenv import load_dotenv

# API情報(キー)の取得(env)
load_dotenv()
client_id = os.getenv("YAHOO_CLIENT_ID")
# APIの接続先
url = "https://shopping.yahooapis.jp/ShoppingWebService/V3/itemSearch"

# 検索用の関数
def search_yahoo(keyword, limit=5, sort="price_asc", min_price=None, max_price=None):
    """Yahoo!の商品を既存の共通形式に変換して返す。"""
    if not client_id:
        raise ValueError("Yahoo!のAPIキーが未設定です。")
    # 1回のAPI通信で取得する件数
    results_limit = min(limit, 50)
    # 取得開始位置
    start = 1
    # APIに送る検索条件
    params = {
        "appid": client_id,
        "query": keyword,
        "results": results_limit,
        "start": start,
    }
    if sort is not None:
        params["sort"] = {
            "price_asc": "+price",
            "price_desc": "-price"
        }[sort]

    # 価格の上限下限を指定
    if min_price is not None:
        params["price_from"] = min_price
    if max_price is not None:
        params["price_to"] = max_price

    # 結果を入れる空リスト
    yahoo_results = []
    # 欲しい件数に届くまで繰り返す
    while len(yahoo_results) < limit:
        # 今回の取得開始位置を指定
        params["start"] = start
        # APIと通信
        response = requests.get(url, params=params, timeout=15)
        # HTTPのエラー確認
        response.raise_for_status()
        # JSONをPython用のデータに
        data = response.json()
        # 商品が1件もなければ繰り返し終了
        if not data["hits"]:
            break
        # 共通の表示形式に変換
        for item in data["hits"]:
            review = item.get("review") or {}
            seller = item.get("seller") or {}
            # 送料情報を取得
            shipping = item.get("shipping") or {}
            # ポイント情報を取得
            point = item.get("point") or {}
            yahoo_results.append({
                "name": item["name"],
                "price": int(item["price"]),
                "url": item["url"],
                "image": (item.get("image") or {}).get("medium", ""),
                "shop": seller.get("name", ""),
                "rating": review.get("rate") or 0,
                "review_count": review.get("count") or 0,
                # 同一商品判定に使うJANコード
                "jan_code": item.get("janCode") or "",
                # Yahoo!の送料情報をアプリ用に変換
                "postage": (
                    0 if shipping.get("code") == 2
                    else 1 if shipping.get("code") in (1, 3)
                    else None
                ),
                # Yahoo!のポイント倍率
                "point_rate": point.get("lyLimitedBonusTimes") or 1,
            })

                # 欲しい件数に到達したら商品追加を終了
            if len(yahoo_results) >= limit:
                break

        # 次の取得開始位置へ
        start += results_limit
        # API検索時のクールタイム
        if len(yahoo_results) < limit:
            time.sleep(1)

    # 商品一覧を search.py に返す
    return yahoo_results