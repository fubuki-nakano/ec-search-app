import os
import requests
from dotenv import load_dotenv

# APIキーの取得
load_dotenv()
serp_api = os.getenv("SERPAPI_KEY")

# APIの接続先
url = "https://serpapi.com/search"

# 検索用関数
def search_serp(keyword, limit=5, sort="price_asc", min_price=None, max_price=None):
    """serpの検索結果を共通形式に変換して返す"""
    if not serp_api:
        raise ValueError("SerpAPIキーが未設定です")

    # APIに送る検索条件
    params = {
        "engine": "google_shopping_light",
        "q": keyword,
        "gl": "jp",
        "hl": "ja",
        "api_key": serp_api,
        "sort_by": {"price_asc": 1, "price_desc": 2}[sort],
    }
    # 価格の上限下限を決める
    if min_price is not None:
        params["min_price"] = min_price
    if max_price is not None:
        params["max_price"] = max_price
    # APIと通信
    response = requests.get(url, params=params, timeout=15)
    # HTTPのエラー確認
    response.raise_for_status()
    # JSONをPython用のデータに
    data = response.json()
# Google Shoppingの商品一覧を取得
    shopping_results = data.get("shopping_results", [])

    # 結果を入れる空リスト
    serp_results = []
    # 共通の表示形式に変換
    for item in shopping_results:
        serp_results.append({
            "name": item.get("title", ""),
            "price": int(item["extracted_price"]),
            "url": item.get("product_link", item.get("link", "")),
            "image": item.get("thumbnail", ""),
        })
    # 指定された件数だけ search.py に返す
    return serp_results[:limit]
