from flask import Flask, render_template, request
from api.search import SITES, search_products
import uuid
# 商品名から型番を探すために使用
import re
from db import (
    init_db,
    save_results,
    count_results,
    get_results,
    get_results_page,
    clear_results,
    get_results_by_site,
    count_results_by_site,
)


# アプリ開始
app = Flask(__name__)
# データベースを準備
init_db()
# 表示件数
LIMITS = (5, 10, 20, 30)
# 各APIから取得する件数
FETCH_LIMIT = 100
# 価格順の指定
SORTS = {
    "recommend_desc": "おすすめ順",
    "price_desc": "価格の高い順",
    "price_asc": "価格の安い順", 
    "rating_desc": "評価の高い順",
    "review_desc": "レビューの多い順",
    }
# 検索精度の指定
SEARCH_MODES = {
    "strict": "高",
    "standard": "標準",
    "normal": "低",
}
# 表示方法の指定
DISPLAY_MODES = {
    "compare": "サイト別比較",
    "list": "価格順一覧",
    # JANコード・型番などが一致する商品をまとめて比較
    "same_product": "同一商品比較",
}

# 商品名から型番らしい文字列を取り出す関数
def extract_model_codes(product_name):
    # 大文字に統一して比較しやすくする
    name = product_name.upper()

    # 英字と数字の両方を含む文字列を探す
    candidates = re.findall(
        r"[A-Z0-9]+(?:-[A-Z0-9]+)*",
        name
    )

    model_codes = []

    for code in candidates:
        # 英字と数字の両方が入っているものだけ残す
        has_letter = any(char.isalpha() for char in code)
        has_number = any(char.isdigit() for char in code)

        if has_letter and has_number and len(code) >= 4:
            model_codes.append(code)

    return model_codes

# 同一商品比較から除外するアクセサリー商品を判定
def is_accessory_product(product_name):
    name = product_name.lower()

    # 本体ではない可能性が高いキーワード
    accessory_keywords = [
        "ケース",
        "カバー",
        "保護",
        "イヤーパッド",
        "イヤークッション",
        "ヘッドバンド",
        "クッション",
        "ケーブル",
        "フィルム",
        "スタンド",
        "ホルダー",
    ]

    return any(
        keyword in name
        for keyword in accessory_keywords
    )

# http://127.0.0.1:5000/←の/にアクセスが来たら
# 下のindexが実行される
@app.get("/")
def index():
    # request.args にブラウザから送られてきた検索条件が入る
    searched = bool(request.args)
    # 検索窓の商品名を取得、.strip()前後の余計な空白を消す
    keyword = request.args.get("keyword", "").strip()
    # 除外キーワードを取得
    exclude_keywords_text = request.args.get("exclude_keywords", "").strip()
    # どの検索結果なのかを識別するIDを取得
    search_id = request.args.get("search_id", "").strip()
    # 取得するサイトのチェックボックス
    selected = request.args.getlist("sites") if searched else list(SITES)
    # 表示件数・ページ番号・昇順降順の初期値
    limit = request.args.get("limit", "10")
    page_text = request.args.get("page", "1")
    page = int(page_text) if page_text.isdigit() and int(page_text) >= 1 else 1
    sort = request.args.get("sort", "price_asc")
    # 検索精度
    search_mode = request.args.get("search_mode", "standard")
    # 表示方法
    display_mode = request.args.get("display_mode", "list")
    # 価格上限下限の設定
    min_price_text = request.args.get("min_price", "").strip()
    max_price_text = request.args.get("max_price", "").strip()
    min_price = int(min_price_text) if min_price_text.isdigit() else None
    max_price = int(max_price_text) if max_price_text.isdigit() else None
    # 検索時、未入力(エラー)か検索結果が入る空のリスト
    products, errors = [], []
    # サイト別比較用の商品データ
    products_by_site = {}
    # 同一商品比較用の商品グループ
    same_product_groups = []
    # サイトごとの商品件数
    site_counts = {}
    total_products = 0
    total_pages = 0

    # 検索をされたときに動くメイン部分(入力チェック)
    if searched:
        # 検索窓の確認
        if not keyword or len(keyword) > 128:
            errors.append("商品名を1〜128文字で入力してください。")
        # 除外キーワードの長さを確認
        if len(exclude_keywords_text) > 128:
            errors.append("除外キーワードは128文字以内で入力してください。")
        # サイトの指定の確認
        if not selected or any(site not in SITES for site in selected):
            errors.append("検索対象サイトを選択してください。")
        # 表示件数の確認
        if limit not in {str(value) for value in LIMITS}:
            errors.append("表示件数を選択肢から選んでください。")
        # 並び順の確認
        if sort not in SORTS:
            errors.append("並び順を選択肢から選んでください。")
        # 表示方法の確認
        if display_mode not in DISPLAY_MODES:
            errors.append("表示方法を選択肢から選んでください。")
        # 検索精度の確認
        if search_mode not in SEARCH_MODES:
            errors.append("検索精度を選択肢から選んでください。")
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
            # search_idがない場合は新しい検索
            if not search_id:
                # 新しい検索の前に古い検索結果を削除
                clear_results()
                products, errors = search_products(
                    keyword,
                    selected,
                    FETCH_LIMIT,
                    sort,
                    min_price=min_price,
                    max_price=max_price,
                    exclude_keywords_text=exclude_keywords_text,
                    search_mode=search_mode,
                )
                # APIから商品を取得できたら検索IDを作ってDBに保存
                if products:
                    search_id = uuid.uuid4().hex
                    save_results(search_id, products)
            # 1ページに表示する件数
            page_size = int(limit)
            # DBに保存されている検索結果の総件数
            total_products = count_results(search_id)
            # 価格順一覧
            if display_mode == "list":
                # 全商品の件数から総ページ数を計算
                total_pages = (total_products + page_size - 1) // page_size
                # ページ番号が最大ページを超えていたら最後のページにする
                if total_pages > 0 and page > total_pages:
                    page = total_pages
                # 現在のページ分だけDBから取得
                products = get_results_page(
                    search_id,
                    page,
                    page_size,
                    sort,
                )
            # サイト別比較
            elif display_mode == "compare":
                # サイトごとのページ数を入れる
                site_pages = []
                # 選択されたサイトごとの商品件数を確認
                for site_id in selected:
                    site_name = SITES[site_id]["name"]
                    site_count = count_results_by_site(
                        search_id,
                        site_name,
                    )
                    # site_countsの辞書に"サイト名”：件数で入れる
                    site_counts[site_name] = site_count
                    # このサイトの総ページ数
                    pages = (site_count + page_size - 1) // page_size
                    site_pages.append(pages)
                # 一番ページ数が多いサイトに合わせる
                total_pages = max(site_pages, default=0)
                # ページ番号が最大ページを超えていたら最後のページにする
                if total_pages > 0 and page > total_pages:
                    page = total_pages
                # サイトごとに現在ページの商品を取得
                for site_id in selected:
                    site_name = SITES[site_id]["name"]
                    products_by_site[site_name] = get_results_by_site(
                        search_id,
                        site_name,
                        page,
                        page_size,
                        sort,
                    )
            # 同一商品比較
            elif display_mode == "same_product":
                # 今回の検索結果をすべてDBから取得
                all_products = get_results(search_id)

                # 型番ごとに商品をまとめるための辞書
                model_groups = {}

                # 全商品を1件ずつ確認
                for product in all_products:
                    # 商品名から型番候補を取得
                    model_codes = set(extract_model_codes(product["name"]))

                    # 見つかった型番ごとに商品をまとめる
                    for model_code in model_codes:

                        # 初めて出てきた型番なら空のリストを作る
                        if model_code not in model_groups:
                            model_groups[model_code] = []

                        model_groups[model_code].append(product)
                    # 2サイト以上に存在する型番だけ同一商品候補にする
                for model_code, group in model_groups.items():

                    # この型番の商品が存在するサイトを取得
                    group_sites = {
                        product["site"]
                        for product in group
                    }

                    # 楽天＋Yahoo!など、2サイト以上にあれば比較対象にする
                    if len(group_sites) >= 2:
                        same_product_groups.append({
                            "model_code": model_code,
                            "products": group,
                        })
                print("同一商品候補グループ数:", len(same_product_groups))

                # 型番候補の確認用（最初の10商品だけ）
                for product in all_products[:10]:
                    model_codes = extract_model_codes(product["name"])

                    if model_codes:
                        print(
                            "サイト:", product["site"],
                            "型番候補:", model_codes,
                            "商品名:", product["name"]
                        )

                # 取得件数の確認用
                print("同一商品比較用の商品数:", len(all_products))
                    # JANコードごとに商品をまとめる
                jan_groups = {}

                for product in all_products:
                    jan_code = product["jan_code"]

                    # JANコードがない商品は今回はまとめない
                    if not jan_code:
                        continue

                    # 初めて出てきたJANコードなら空リストを作る
                    if jan_code not in jan_groups:
                        jan_groups[jan_code] = []

                    # 同じJANコードの商品を追加
                    jan_groups[jan_code].append(product)

                # 2件以上あるJANコードだけ確認
                for jan_code, group in jan_groups.items():
                    if len(group) >= 2:
                        # このグループに含まれるサイト名を確認
                        sites = {product["site"] for product in group}

                        print(
                            "同一JAN:",
                            jan_code,
                            "商品数:",
                            len(group),
                            "サイト:",
                            sites
                        )

    # APIから帰ってきた情報をHTMLへ渡す
    return render_template(
        "index.html",
        sites=SITES,
        limits=LIMITS,
        sorts=SORTS,
        search_modes=SEARCH_MODES,
        display_modes=DISPLAY_MODES,
        keyword=keyword,
        exclude_keywords_text=exclude_keywords_text,
        selected=selected,
        limit=limit,
        sort=sort,
        search_mode=search_mode,
        display_mode=display_mode,
        min_price_text=min_price_text,
        max_price_text=max_price_text,
        products=products,
        products_by_site=products_by_site,
        same_product_groups=same_product_groups,
        site_counts=site_counts,
        errors=errors,
        searched=searched,
        page=page,
        total_pages=total_pages,
        total_products=total_products,
        search_id=search_id,
    )

# python app.pyが実行されたときにapp.run()が動いて
# Flaskサーバーが起動。127.0.0.1:5000でブラウザから
# アクセスできるようになる
if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000)

# 実行後　http://127.0.0.1:5000 をブラウザに入力







