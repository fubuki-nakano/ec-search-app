import os
import requests
from dotenv import load_dotenv

load_dotenv()
# Appキー・アクセスキー呼び出し
application_id = os.getenv("RAKUTEN_APPLICATION_ID")
access_key = os.getenv("RAKUTEN_ACCESS_KEY")

url = "https://openapi.rakuten.co.jp/ichibams/api/IchibaItem/Search/20260701"

# 検索用のキーワードを入力(確認用)
# keyword = input("検索したい商品を入力してください：")

def search_rakuten(keyword):

    # APIに渡す情報
    params = {
        "applicationId": application_id,
        "accessKey": access_key,
        "keyword": keyword,
        "format": "json"
    }

# 楽天の商品検索APIに、
# paramsの条件を付けてGETリクエストを送って、
# 返ってきた結果をresponseに入れる
    response = requests.get(url, params=params)
# 返答確認
    # print(response.status_code)
# 帰ってきたJsonをdataにセット
    data = response.json()

# ↓APIから帰ってきたデータの０番目(1番目)のデータを表示させる
# item = data["Items"][0]["Item"]
# print(item["itemName"])
# print(item["itemPrice"])
# print(item["itemUrl"])

# return用の箱
    results = []

# for文で5件目まで表示
    for i,itemList in enumerate(data["Items"]):
        if i >= 5:
            break

        item = itemList["Item"]

        # 商品取得時用のディクショナリ
        product = {
        "name": item["itemName"],
        "price": item["itemPrice"],
        "url": item["itemUrl"]
        }

        results.append(product)

    return results

# 商品情報受け渡しテスト用
# test = search_rakuten("iPhone")
# print(test)