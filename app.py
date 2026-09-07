from api.rakuten_api import search_rakuten
from api.yahoo_search import search_yahoo

# 検索用キーワード
keyword = input("検索したい商品を入力してください：")

# 同じキーワードで楽天とYahoo!を検索
rakuten_results = search_rakuten(keyword)
yahoo_results = search_yahoo(keyword)

print("===== 楽天市場 =====")

for product in rakuten_results:
    print(product["name"])
    print(product["price"])
    print(product["url"])
    print(product["image"])

print("===== Yahoo!ショッピング =====")

for product in yahoo_results:
    print(product["name"])
    print(product["price"])
    print(product["url"])
    print(product["image"])


