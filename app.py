from api.rakuten_api import search_rakuten

# 検索用キーワード
keyword = input("検索したい商品を入力してください：")

results = search_rakuten(keyword)

for product in results:
    print(product["name"])
    print(product["price"])
    print(product["url"])

