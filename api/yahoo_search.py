import os
import requests
from dotenv import load_dotenv

load_dotenv()

# クライアントキー呼び出し
client_id = os.getenv("YAHOO_CLIENT_ID")
# リクエストURL
url = "https://shopping.yahooapis.jp/ShoppingWebService/V3/itemSearch"


def search_yahoo(keyword):

    params = {
        "appid": client_id,
        "query": keyword,
        "results": 5
    }

# paramsの条件を付けてGETリクエストを送って、
# 返ってきた結果をresponseに入れる
    response = requests.get(url, params=params)

# 帰ってきたJsonをdataにセット
    data = response.json()

# ↓APIから帰ってきたデータの０番目(1番目)のデータを表示させる(テスト用)
# item = data["hits"][0]
# print(item["name"])
# print(item["price"])
# print(item["url"])

# app.py転送用のリスト
    yahoo_results = []

# 帰ってきたデータをfor文で表示(回数はparamで指定済み)
    for item in data["hits"]:
        yahoo_results.append({
            "name": item["name"],
            "price": item["price"],
            "url": item["url"],
            "image": item["image"]["medium"]
            })

    return yahoo_results

