from flask import Flask, render_template, request
from api.search import SITES, search_products

# アプリ開始
app = Flask(__name__)
# 表示件数
LIMITS = (5, 10, 20, 30)
# 価格順の指定
SORTS = {"price_asc": "価格の安い順", "price_desc": "価格の高い順"}

# http://127.0.0.1:5000/←の/にアクセスが来たら
# 下のindexが実行される
@app.get("/")
def index():
    # request.args にブラウザから送られてきた検索条件が入る
    searched = bool(request.args)
    # 検索窓の商品名を取得、.strip()前後の余計な空白を消す
    keyword = request.args.get("keyword", "").strip()
    # 取得するサイトのチェックボックス
    selected = request.args.getlist("sites") if searched else list(SITES)
    # 表示件数・昇順降順の初期値
    limit = request.args.get("limit", "10")
    sort = request.args.get("sort", "price_asc")
    # 価格上限下限の設定
    min_price_text = request.args.get("min_price", "").strip()
    max_price_text = request.args.get("max_price", "").strip()
    min_price = int(min_price_text) if min_price_text.isdigit() else None
    max_price = int(max_price_text) if max_price_text.isdigit() else None
    # 検索時、未入力(エラー)か検索結果が入るからのリスト
    products, errors = [], []

    # 検索をされたときに動くメイン部分
    if searched:
        # 検索窓の確認
        if not keyword or len(keyword) > 128:
            errors.append("商品名を1〜128文字で入力してください。")
        # サイトの指定の確認
        if not selected or any(site not in SITES for site in selected):
            errors.append("検索対象サイトを選択してください。")
        # 表示件数の確認
        if limit not in {str(value) for value in LIMITS}:
            errors.append("表示件数を選択肢から選んでください。")
        # 並び順の確認
        if sort not in SORTS:
            errors.append("並び順を選択肢から選んでください。")
        # 最低価格の確認
        if min_price_text and not min_price_text.isdigit():
            errors.append("最低価格は0以上の数字で入力してください。")
        # 最高価格の確認
        if max_price_text and not max_price_text.isdigit():
            errors.append("最高価格は0以上の数字で入力してください。")
        # 最低価格と最高価格が逆になっていないか確認
        if min_price is not None and max_price is not None and min_price > max_price:
            errors.append("最低価格は最高価格以下にしてください。")
        # ↑までにエラーが出ていなければ↓が実行される
        # ここまでの指定されたものをAPIに渡す
        if not errors:
            products, errors = search_products(
                keyword,
                selected,
                int(limit),
                sort,
                min_price=min_price,
                max_price=max_price,
            )
    # APIから帰ってきた情報をHTMLへ渡す
    return render_template(
        "index.html", sites=SITES,
        limits=LIMITS,
        sorts=SORTS,
        keyword=keyword,
        selected=selected,
        limit=limit,
        sort=sort,
        min_price_text=min_price_text,
        max_price_text=max_price_text,
        products=products,
        errors=errors,
        searched=searched,
    )

# python app.pyが実行されたときにapp.run()が動いて
# Flaskサーバーが起動。127.0.0.1:5000でブラウザから
# アクセスできるようになる
if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000)

# 実行後　http://127.0.0.1:5000 をブラウザに入力
