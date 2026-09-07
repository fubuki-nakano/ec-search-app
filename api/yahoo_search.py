import os
import requests
from dotenv import load_dotenv

load_dotenv()

# クライアントキー呼び出し
client_id = os.getenv("YAHOO_CLIENT_ID")
# リクエストURL
url = "https://shopping.yahooapis.jp/ShoppingWebService/V3/itemSearch"


keyword = input("検索したい商品を入力してください：")

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

# 帰ってきたデータをfor文で表示(回数はparamで指定済み)
for item in data["hits"]:
    print(item["name"])
    print(item["price"])
    print(item["url"])


