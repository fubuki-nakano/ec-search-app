import gc
from html.parser import HTMLParser
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch

import requests

import db

# app の読み込み時の初期化も、利用中のDBには書き込ませない。
with patch.object(db, "init_db"):
    from app import app, extract_model_codes, select_best_model_code

from api.search import SITES, search_products
from api.rakuten_api import search_rakuten
from api.yahoo_search import search_yahoo
from api.google_shopping import search_serp


def product(price, name="テスト商品"):
    return {
        "name": name, "price": price, "url": "https://example.com/item", "image": "",
        "shop": "テスト店舗", "rating": 4.0, "review_count": 20,
        "postage": 0, "point_rate": 1, "jan_code": "",
    }


class PageElements(HTMLParser):
    """スクリプトやdata属性とは分けて、実際のリンク・画像を確認する。"""

    def __init__(self, html):
        super().__init__()
        self.elements = []
        self.feed(html)

    def handle_starttag(self, tag, attrs):
        self.elements.append((tag, dict(attrs)))


class DatabaseTestCase(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_patch = patch.object(db, "DB_PATH", Path(self.temp_dir.name) / "test.db")
        self.db_patch.start()
        db.init_db()
        self.addCleanup(self.cleanup_database)

    def cleanup_database(self):
        self.db_patch.stop()
        # sqlite3 の接続を回収してから、Windows上で一時DBを削除する。
        gc.collect()
        self.temp_dir.cleanup()


class SearchTests(DatabaseTestCase):
    def setUp(self):
        super().setUp()
        self.rakuten = Mock(return_value=[product(100), product(300)])
        self.yahoo = Mock(return_value=[product(200), product(400)])
        self.registry = patch.dict(SITES, {
            "rakuten": {"name": "楽天市場", "search": self.rakuten, "max_limit": 100},
            "yahoo": {"name": "Yahoo!ショッピング", "search": self.yahoo, "max_limit": 100},
        }, clear=True)
        self.registry.start()
        self.addCleanup(self.registry.stop)
        app.config["TESTING"] = True
        self.client = app.test_client()

    def test_merge_sort_and_per_site_fetch_limit(self):
        for sort, expected in [("price_asc", [100, 200, 300, 400]), ("price_desc", [400, 300, 200, 100])]:
            with self.subTest(sort=sort):
                results, errors = search_products("商品", list(SITES), 2, sort)
                self.assertEqual([p["price"] for p in results], expected)
                self.assertFalse(errors)
                self.rakuten.assert_called_with(
                    "商品", limit=2, sort=sort, min_price=None, max_price=None,
                )

    def test_only_selected_site_and_no_duplicate_request(self):
        results, _ = search_products("商品", ["yahoo", "yahoo"], 5, "price_asc")
        self.rakuten.assert_not_called()
        self.yahoo.assert_called_once()
        self.assertTrue(all(p["site"] == "Yahoo!ショッピング" for p in results))

    def test_partial_failure_hides_exception(self):
        self.rakuten.side_effect = requests.Timeout("secret-api-key")
        response = self.client.get("/", query_string={
            "keyword": "商品", "sites": ["rakuten", "yahoo"],
        })
        page = response.get_data(as_text=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn("取得できませんでした", page)
        self.assertIn("テスト商品", page)
        self.assertNotIn("secret-api-key", page)

    def test_initial_page_does_not_search(self):
        self.assertEqual(self.client.get("/").status_code, 200)
        self.rakuten.assert_not_called()
        self.yahoo.assert_not_called()

    def test_invalid_input_does_not_call_api(self):
        for invalid in [
            {"keyword": "  "}, {"keyword": "あ" * 129}, {"sites": []},
            {"sites": "unknown"}, {"limit": "999"}, {"limit": "abc"},
            {"sort": "unknown"},
        ]:
            with self.subTest(invalid=invalid):
                query = {"keyword": "商品", "sites": "rakuten", **invalid}
                response = self.client.get("/", query_string=query)
                self.assertIn('role="alert"', response.get_data(as_text=True))
        self.rakuten.assert_not_called()
        self.yahoo.assert_not_called()

    def test_empty_results(self):
        self.rakuten.return_value = []
        response = self.client.get("/?keyword=test&sites=rakuten")
        self.assertIn("該当する商品がありません", response.get_data(as_text=True))

    def test_escape_results_and_reject_unsafe_links(self):
        self.rakuten.return_value = [{
            **product(1234, '<script>alert(1)</script>'),
            "url": "javascript:alert(1)", "image": "javascript:alert(2)",
        }]
        page = self.client.get("/?keyword=test&sites=rakuten&search_mode=normal&display_mode=list").get_data(as_text=True)
        self.assertIn("¥1,234", page)
        self.assertIn("&lt;script&gt;", page)
        self.assertNotIn("<script>alert(1)</script>", page)
        for tag, attrs in PageElements(page).elements:
            if tag in ("a", "img"):
                self.assertFalse(attrs.get("href", attrs.get("src", "")).startswith("javascript:"))
        self.assertIn("画像なし", page)

    def test_search_precision_and_exclusions(self):
        self.rakuten.return_value = [
            product(100, "商品 赤 AB-123"), product(200, "商品 青 AB-123"),
            product(300, "別製品 赤"), product(400, "別製品"),
        ]
        for mode, expected in [("strict", [100]), ("standard", [100, 300]), ("normal", [100, 300, 400])]:
            with self.subTest(mode=mode):
                results, errors = search_products(
                    "商品 赤", ["rakuten"], 100, "price_asc",
                    exclude_keywords_text="青", search_mode=mode,
                )
                self.assertFalse(errors)
                self.assertEqual([p["price"] for p in results], expected)

    def test_shipping_and_point_filters_saved_to_db(self):
        self.rakuten.return_value = [
            {**product(100), "postage": 0, "point_rate": 2},
            {**product(200), "postage": 1, "point_rate": 5},
            {**product(300), "postage": 0, "point_rate": 1},
        ]
        with patch("app.uuid.uuid4") as uid:
            uid.return_value.hex = "filtered"
            response = self.client.get("/?keyword=商品&sites=rakuten&postage_only=1&point_up_only=1")
        self.assertEqual(response.status_code, 200)
        self.assertEqual([r["price"] for r in db.get_results("filtered")], [100])

    def test_cached_results_modes_paging_and_site_filter_do_not_call_api(self):
        products = [
            {**product(i * 100, "商品 AB-123"), "site": site, "url": f"https://example.com/{site}/{i}"}
            for site in ["楽天市場", "Yahoo!ショッピング"] for i in range(1, 8)
        ]
        db.save_results("cached", products)
        for mode in ["list", "compare", "same_product"]:
            for sort in ["price_asc", "price_desc", "rating_desc", "review_desc", "recommend_desc"]:
                with self.subTest(mode=mode, sort=sort):
                    response = self.client.get("/", query_string={
                        "keyword": "商品", "sites": ["rakuten", "yahoo"], "search_id": "cached",
                        "display_mode": mode, "sort": sort, "limit": "5", "page": "999",
                        "result_site": "rakuten",
                    })
                    self.assertEqual(response.status_code, 200)
                    self.assertIn("商品 AB-123", response.get_data(as_text=True))
        self.rakuten.assert_not_called()
        self.yahoo.assert_not_called()

    def test_same_product_keeps_single_site_models_and_jan_precedence(self):
        db.save_results("groups", [
            {**product(200, "商品 AB-123"), "site": "楽天市場", "url": "https://example.com/a", "jan_code": "123"},
            {**product(100, "商品 AB-123"), "site": "Yahoo!ショッピング", "url": "https://example.com/b", "jan_code": "123"},
            {**product(300, "商品 Solo-777 ケース"), "site": "楽天市場", "url": "https://example.com/c"},
        ])
        page = self.client.get("/?keyword=商品&sites=rakuten&sites=yahoo&search_id=groups&display_mode=same_product").get_data(as_text=True)
        self.assertIn("JANコード：123", page)
        self.assertNotIn("型番：AB-123", page)
        self.assertIn("型番：SOLO-777", page)
        self.assertLess(page.index('href="https://example.com/b"'), page.index('href="https://example.com/a"'))

    def test_model_extraction_ignores_capacity_and_waterproof_codes(self):
        name = "商品 WH-1000XM5 IPX5 256GB BLUETOOTH5"
        self.assertEqual(extract_model_codes(name), ["WH-1000XM5"])
        self.assertEqual(select_best_model_code(name), "WH-1000XM5")


class DatabaseOrderingTests(DatabaseTestCase):
    def test_all_sort_orders_and_ties_in_both_queries(self):
        fixtures = [(300, 0, 100), (100, 5, 1), (200, 4, 100), (200, 4, 100)]
        db.save_results("sort", [
            {**product(price), "name": str(i), "rating": rating, "review_count": count, "site": "楽天市場"}
            for i, (price, rating, count) in enumerate(fixtures)
        ])
        expected = {
            "price_asc": [1, 2, 3, 0], "price_desc": [0, 2, 3, 1],
            "rating_desc": [1, 2, 3, 0], "review_desc": [2, 3, 0, 1],
            "recommend_desc": [1, 2, 3, 0], "unknown": [1, 2, 3, 0],
        }
        for sort, order in expected.items():
            with self.subTest(sort=sort):
                all_rows = db.get_results_page("sort", 1, 10, sort)
                site_rows = db.get_results_by_site("sort", "楽天市場", 1, 10, sort)
                self.assertEqual([int(row["name"]) for row in all_rows], order)
                self.assertEqual(site_rows, all_rows)
                self.assertEqual(db.get_results_page("sort", 2, 2, sort), all_rows[2:4])


class AdapterTests(unittest.TestCase):
    def setUp(self):
        sleep = patch("time.sleep")
        sleep.start()
        self.addCleanup(sleep.stop)

    @patch("api.rakuten_api.access_key", "test-key")
    @patch("api.rakuten_api.application_id", "test-id")
    @patch("api.rakuten_api.requests.get")
    def test_rakuten_params_and_image_fallback(self, get):
        get.return_value.json.return_value = {"Items": [{"Item": {
            "itemName": "商品", "itemPrice": "1200", "itemUrl": "https://example.com",
            "mediumImageUrls": [],
        }}] * 20}
        result = search_rakuten("商品", 20, "price_desc")
        self.assertEqual(result[0]["price"], 1200)
        self.assertEqual(result[0]["image"], "")
        self.assertEqual(get.call_args.kwargs["params"]["hits"], 20)
        self.assertEqual(get.call_args.kwargs["params"]["sort"], "-itemPrice")
        self.assertEqual(get.call_args.kwargs["timeout"], 15)
        get.return_value.raise_for_status.assert_called_once()

    @patch("api.yahoo_search.client_id", "test-id")
    @patch("api.yahoo_search.requests.get")
    def test_yahoo_params_and_image_fallback(self, get):
        get.return_value.json.return_value = {"hits": [{
            "name": "商品", "price": "800", "url": "https://example.com", "image": None,
        }] * 10}
        result = search_yahoo("商品", 10, "price_asc")
        self.assertEqual(result[0]["price"], 800)
        self.assertEqual(result[0]["image"], "")
        self.assertEqual(get.call_args.kwargs["params"]["results"], 10)
        self.assertEqual(get.call_args.kwargs["params"]["sort"], "+price")
        get.return_value.raise_for_status.assert_called_once()

    @patch("api.yahoo_search.client_id", "test-id")
    @patch("api.yahoo_search.requests.get")
    def test_http_error_is_not_treated_as_empty_results(self, get):
        get.return_value.raise_for_status.side_effect = requests.HTTPError()
        with self.assertRaises(requests.HTTPError):
            search_yahoo("商品")
        get.return_value.json.assert_not_called()

    @patch("api.google_shopping.serp_api", "test-key")
    @patch("api.google_shopping.requests.get")
    def test_google_params_price_filter_and_mapping(self, get):
        get.return_value.json.return_value = {"shopping_results": [
            {"title": "価格なし"},
            {"title": "安すぎる", "extracted_price": 50},
            {"title": "対象", "extracted_price": 100.9, "product_link": "https://example.com/item", "delivery": "送料無料"},
            {"title": "高すぎる", "extracted_price": 300},
        ]}
        with patch("builtins.print"):
            results = search_serp("商品", 5, "price_desc", min_price=100, max_price=200)
        self.assertEqual([p["name"] for p in results], ["対象"])
        self.assertEqual(results[0]["price"], 100)
        self.assertEqual(results[0]["postage"], 0)
        self.assertIsNone(results[0]["point_rate"])
        self.assertEqual(get.call_args.kwargs["params"], {
            "engine": "google_shopping_light", "q": "商品", "gl": "jp", "hl": "ja",
            "api_key": "test-key", "sort_by": 2,
        })
        self.assertEqual(get.call_args.kwargs["timeout"], 15)
        get.return_value.raise_for_status.assert_called_once()


if __name__ == "__main__":
    unittest.main()
