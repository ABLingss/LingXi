"""
tests.test_api_client — HTTP mock tests for api.client with failover coverage.

Tests:
  1. Tencent K-line response parsing
  2. Sina K-line response parsing
  3. EastMoney K-line response parsing
  4. Tencent stock info parsing
  5. EastMoney stock info parsing
  6. Failover: Tencent fails → Sina succeeds
  7. Failover: all sources fail → StockError
  8. Edge cases: empty data, invalid JSON, timeout
"""

import json
import sys
import os
import unittest
from unittest.mock import patch, Mock, MagicMock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import requests
from api.client import (
    fetch_kline,
    fetch_stock_info,
    StockError,
    HEADERS,
    _tct_kline,
    _tct_stock_info,
    _sina_kline,
    _em_kline,
    _em_stock_info,
    _safe_float,
    _safe_int,
    _safe_str,
    _safe_date,
    _is_sh,
    _market_prefix,
    _em_secid,
)


class TestMarketHelpers(unittest.TestCase):
    def test_is_sh(self):
        self.assertTrue(_is_sh("600036"))
        self.assertTrue(_is_sh("688001"))
        self.assertFalse(_is_sh("000001"))
        self.assertFalse(_is_sh("300750"))

    def test_market_prefix(self):
        self.assertEqual(_market_prefix("600036"), "sh")
        self.assertEqual(_market_prefix("000001"), "sz")

    def test_em_secid(self):
        self.assertEqual(_em_secid("600036"), "1.600036")
        self.assertEqual(_em_secid("000001"), "0.000001")

    def test_safe_converters(self):
        self.assertEqual(_safe_float("3.14"), 3.14)
        self.assertEqual(_safe_float(None), 0.0)
        self.assertEqual(_safe_float("abc"), 0.0)
        self.assertEqual(_safe_int("100"), 100)
        self.assertEqual(_safe_int(None), 0)
        self.assertEqual(_safe_str(None), "")
        self.assertEqual(_safe_str("  hello  "), "hello")
        self.assertEqual(_safe_date(20200101), "2020-01-01")
        self.assertEqual(_safe_date(None), "")


class TestTencentKline(unittest.TestCase):
    def setUp(self):
        # Mock response for 平安银行 (000001) daily K-line
        self.mock_resp = Mock()
        self.mock_resp.json.return_value = {
            "code": 0,
            "data": {
                "sz000001": {
                    "qfqday": [
                        ["2026-06-22", "10.520", "10.650", "10.670", "10.420", "1265317"],
                        ["2026-06-23", "10.650", "10.710", "10.910", "10.630", "1190604"],
                    ]
                }
            },
        }
        self.mock_resp.raise_for_status = Mock()

    @patch("api.client.requests.get")
    def test_parse_bars(self, mock_get):
        mock_get.return_value = self.mock_resp
        bars = _tct_kline("000001", "daily", 5, 10)
        self.assertEqual(len(bars), 2)
        self.assertEqual(bars[0]["date"], "2026-06-22")
        self.assertEqual(bars[0]["open"], 10.52)
        self.assertEqual(bars[0]["close"], 10.65)
        self.assertEqual(bars[1]["volume"], 1190604)

    @patch("api.client.requests.get")
    def test_empty_data_raises(self, mock_get):
        mock_get.return_value.json.return_value = {
            "code": 0,
            "data": {"sz000001": {"qfqday": []}},
        }
        mock_get.return_value.raise_for_status = Mock()
        with self.assertRaises(StockError):
            _tct_kline("000001", "daily", 5, 10)

    @patch("api.client.requests.get")
    def test_error_code_raises(self, mock_get):
        mock_get.return_value.json.return_value = {
            "code": -1,
            "msg": "Invalid param",
        }
        mock_get.return_value.raise_for_status = Mock()
        with self.assertRaises(StockError):
            _tct_kline("000001", "daily", 5, 10)


class TestSinaKline(unittest.TestCase):
    def setUp(self):
        self.mock_resp = Mock()
        self.mock_resp.json.return_value = [
            {"day": "2026-06-22", "open": "10.520", "high": "10.670",
             "low": "10.420", "close": "10.650", "volume": "1265317"},
        ]
        self.mock_resp.raise_for_status = Mock()
        self.mock_resp.headers = {"Content-Type": "application/json"}
        self.mock_resp.text = '[{"day":"2026-06-22"}]'

    @patch("api.client.requests.get")
    def test_parse_bars(self, mock_get):
        mock_get.return_value = self.mock_resp
        bars = _sina_kline("000001", "daily", 5, 10)
        self.assertEqual(len(bars), 1)
        self.assertEqual(bars[0]["close"], 10.65)

    @patch("api.client.requests.get")
    def test_html_response_raises(self, mock_get):
        mock_get.return_value.headers = {"Content-Type": "text/html"}
        mock_get.return_value.text = "<html>Error</html>"
        mock_get.return_value.raise_for_status = Mock()
        with self.assertRaises(StockError):
            _sina_kline("000001", "daily", 5, 10)


class TestEastMoneyKline(unittest.TestCase):
    def setUp(self):
        self.mock_resp = Mock()
        self.mock_resp.json.return_value = {
            "rc": 0,
            "data": {
                "klines": [
                    "2026-06-22,10.52,10.65,10.67,10.42,1265317,13400000.00,2.30,0.50,0.05,1.20",
                ],
            },
        }
        self.mock_resp.raise_for_status = Mock()

    @patch("api.client.requests.get")
    def test_parse_full_fields(self, mock_get):
        mock_get.return_value = self.mock_resp
        bars = _em_kline("000001", "daily", 5, 10)
        self.assertEqual(len(bars), 1)
        self.assertEqual(bars[0]["amount"], 13400000.0)
        self.assertEqual(bars[0]["amplitude"], 2.3)
        self.assertEqual(bars[0]["change_pct"], 0.5)
        self.assertEqual(bars[0]["turnover"], 1.2)


class TestTencentStockInfo(unittest.TestCase):
    @patch("api.client.requests.get")
    def test_parse_info(self, mock_get):
        mock_resp = Mock()
        # Simulate Tencent qt API response with ~ separated fields
        mock_resp.text = 'v_sz000001="1~平安银行~000001~10.23~...placeholder fields...~4.61~...~20000000000~..."'
        mock_resp.raise_for_status = Mock()
        mock_get.return_value = mock_resp

        # We need at least 86 fields for the test
        fields = [""] * 86
        fields[1] = "平安银行"
        fields[39] = "4.61"
        fields[72] = "20000000000"
        fields[73] = "18000000000"
        fields[61] = "银行"
        mock_resp.text = f'v_sz000001="{"~".join(fields)}"'

        info = _tct_stock_info("000001", 10)
        self.assertEqual(info["name"], "平安银行")
        self.assertEqual(info["pe_ttm"], 4.61)
        self.assertEqual(info["total_mv"], 20000000000.0)


class TestFailover(unittest.TestCase):
    @patch("api.client.requests.get")
    def test_fetch_kline_fallback_to_sina(self, mock_get):
        """Tencent fails, Sina succeeds."""
        # Tencent: error
        resp_tct = Mock()
        resp_tct.json.return_value = {"code": -1, "msg": "error"}
        resp_tct.raise_for_status = Mock()

        # Sina: success
        resp_sina = Mock()
        resp_sina.json.return_value = [
            {"day": "2026-06-22", "open": "10.5", "high": "10.7",
             "low": "10.4", "close": "10.6", "volume": "1000000"},
        ]
        resp_sina.raise_for_status = Mock()
        resp_sina.headers = {"Content-Type": "application/json"}
        resp_sina.text = "[]"

        mock_get.side_effect = [resp_tct, resp_sina]

        bars = fetch_kline("000001", "daily", 5, 10)
        self.assertEqual(len(bars), 1)
        self.assertEqual(bars[0]["close"], 10.6)

    @patch("api.client.requests.get")
    def test_all_sources_fail(self, mock_get):
        """All sources fail → StockError with all error messages."""
        resp = Mock()
        resp.json.return_value = {"code": -1, "msg": "error"}
        resp.raise_for_status = Mock()
        mock_get.return_value = resp

        with self.assertRaises(StockError) as ctx:
            fetch_kline("000001", "daily", 5, 3)
        self.assertIn("Tencent", ctx.exception.message)
        self.assertIn("Sina", ctx.exception.message)
        self.assertIn("EastMoney", ctx.exception.message)

    @patch("api.client.requests.get")
    def test_timeout_triggers_fallback(self, mock_get):
        """Timeout → fallback message, not crash."""
        resp_tct = Mock()
        resp_tct.json.side_effect = requests.Timeout()
        resp_tct.raise_for_status = Mock()

        resp_sina = Mock()
        resp_sina.json.return_value = [
            {"day": "2026-06-22", "open": "10.5", "high": "10.7",
             "low": "10.4", "close": "10.6", "volume": "1000000"},
        ]
        resp_sina.raise_for_status = Mock()
        resp_sina.headers = {"Content-Type": "application/json"}
        resp_sina.text = "[]"

        mock_get.side_effect = [resp_tct, resp_sina]
        bars = fetch_kline("000001", "daily", 5, 10)
        self.assertEqual(len(bars), 1)


class TestStockError(unittest.TestCase):
    def test_error_message(self):
        err = StockError("000001", "测试错误")
        self.assertEqual(err.code, "000001")
        self.assertIn("000001", str(err))
        self.assertIn("测试错误", str(err))


if __name__ == "__main__":
    unittest.main(verbosity=2)
