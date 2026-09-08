import unittest
from unittest.mock import Mock, patch

import requests

from app import app
from api.search import SITES, search_products
from api.rakuten_api import search_rakuten
from api.yahoo_search import search_yahoo


def product(price, name="テスト商品"):
    return {"name": name, "price": price, "url": "https://example.com/item", "image": ""}


class SearchTests(unittest.TestCase):
    def setUp(self):
        self.rakuten = Mock(return_value=[product(100), product(300)])
        self.yahoo = Mock(return_value=[product(200), product(400)])
        self.registry = patch.dict(SITES, {
            "rakuten": {"name": "楽天市場", "search": self.rakuten},
            "yahoo": {"name": "Yahoo!ショッピング", "search": self.yahoo},
        }, clear=True)
        self.registry.start()
        self.addCleanup(self.registry.stop)
        app.config["TESTING"] = True
        self.client = app.test_client()

    def test_merge_sort_and_total_limit(self):
        for sort, expected in [("price_asc", [100, 200]), ("price_desc", [400, 300])]:
            with self.subTest(sort=sort):
                results, errors = search_products("商品", list(SITES), 2, sort)
                self.assertEqual([p["price"] for p in results], expected)
                self.assertFalse(errors)
                self.rakuten.assert_called_with("商品", limit=2, sort=sort)

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
        page = self.client.get("/?keyword=test&sites=rakuten").get_data(as_text=True)
        self.assertIn("¥1,234", page)
        self.assertIn("&lt;script&gt;", page)
        self.assertNotIn("<script>", page)
        self.assertNotIn("javascript:", page)
        self.assertIn("画像なし", page)


class AdapterTests(unittest.TestCase):
    @patch("api.rakuten_api.access_key", "test-key")
    @patch("api.rakuten_api.application_id", "test-id")
    @patch("api.rakuten_api.requests.get")
    def test_rakuten_params_and_image_fallback(self, get):
        get.return_value.json.return_value = {"Items": [{"Item": {
            "itemName": "商品", "itemPrice": "1200", "itemUrl": "https://example.com",
            "mediumImageUrls": [],
        }}]}
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
        }]}
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


if __name__ == "__main__":
    unittest.main()
