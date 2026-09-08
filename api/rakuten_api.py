import os
import requests
from dotenv import load_dotenv

# API情報(キー)の取得(env)
load_dotenv()
application_id = os.getenv("RAKUTEN_APPLICATION_ID")
access_key = os.getenv("RAKUTEN_ACCESS_KEY")
# APIの接続先
url = "https://openapi.rakuten.co.jp/ichibams/api/IchibaItem/Search/20260701"

# 検索用の関数
def search_rakuten(keyword, limit=5, sort="price_asc", min_price=None, max_price=None):
    """楽天の商品を既存の共通形式に変換して返す。"""
    if not application_id or not access_key:
        # APIキーが取得できていないときの処理
        raise ValueError("楽天のAPIキーが未設定です。")
        # APIに送る条件表
    params = {
        "applicationId": application_id,
        "accessKey": access_key,
        "keyword": keyword,
        "format": "json",
        "hits": limit,
        # ここで価格順に直すためにAPIから帰ってきた情報を変換
        "sort": {"price_asc": "+itemPrice", "price_desc": "-itemPrice"}[sort],
    }
    # 価格の上限下限を指定
    if min_price is not None:
        params["minPrice"] = min_price
    if max_price is not None:
        params["maxPrice"] = max_price
    # 楽天APIへ問い合わせ
    response = requests.get(url, params=params, timeout=15)
    # エラーが返ってきたら例外にする
    response.raise_for_status()
    # 楽天から返ってきたJSONをPythonで扱える形に変換
    data = response.json()
    # 結果を入れる空リスト
    rakuten_results = []

    # 楽天から返ってきた商品を1件ずつ処理
    for item_list in data["Items"]:
        # 実際の商品情報部分を取り出し
        item = item_list["Item"]
        # 商品画像の一覧を取得
        images = item.get("mediumImageUrls") or []
        # 楽天の項目名を、このアプリの形式に変換
        rakuten_results.append({
            "name": item["itemName"],
            "price": int(item["itemPrice"]),
            "url": item["itemUrl"],
            "image": images[0].get("imageUrl", "") if images else "",
        })
    # 商品一覧を search.py に返す
    return rakuten_results