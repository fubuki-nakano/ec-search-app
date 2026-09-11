from flask import Flask, render_template, request
from api.search import SITES, search_products
import uuid
from db import (
    init_db,
    save_results,
    count_results,
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
    "price_asc": 
    "価格の安い順", 
    "price_desc": 
    "価格の高い順"
    }
# 検索精度の指定
SEARCH_MODES = {
    "strict": "高",
    "standard": "標準",
    "normal": "低",
}
# 表示方法の指定
DISPLAY_MODES = {
    "list": "価格順一覧",
    "compare": "サイト別比較",
}

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







