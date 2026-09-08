import os
import requests
from dotenv import load_dotenv

# # API情報(キー)の取得(env)
load_dotenv()
client_id = os.getenv("YAHOO_CLIENT_ID")
# # APIの接続先
url = "https://shopping.yahooapis.jp/ShoppingWebService/V3/itemSearch"

# 検索用の関数
def search_yahoo(keyword, limit=5, sort="price_asc", min_price=None, max_price=None):
    """Yahoo!の商品を既存の共通形式に変換して返す。"""
    if not client_id:
        raise ValueError("Yahoo!のAPIキーが未設定です。")
    # APIに送る検索条件
    params = {
        "appid": client_id,
        "query": keyword,
        "results": limit,
        "sort": {"price_asc": "+price", "price_desc": "-price"}[sort],
    }
    # 価格の上限下限を指定
    if min_price is not None:
        params["price_from"] = min_price
    if max_price is not None:
        params["price_to"] = max_price
    # APIと通信
    response = requests.get(url, params=params, timeout=15)
    # HTTPのエラー確認
    response.raise_for_status()
    # JSONをPython用のデータに
    data = response.json()
    # 結果を入れる空リスト
    yahoo_results = []
    # 共通の表示形式に変換
    for item in data["hits"]:
        yahoo_results.append({
            "name": item["name"],
            "price": int(item["price"]),
            "url": item["url"],
            "image": (item.get("image") or {}).get("medium", ""),
        })
    return yahoo_results