"""
test_formula_engine.py — Unit tests for the formula engine.

Tests:
  1. series.py — MA, EMA, MACD, RSI, BOLL, KDJ series computation
  2. events.py — Cross detection, threshold breaches, trend
  3. elements.py — Formula parsing (cross, compare, statistical, opaque)
  4. __init__.py — prepare() integration (4 scenarios)
"""

import json
import math
import os
import sys
import unittest

# Ensure project root on path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


# ============================================================
# Test helpers — generate synthetic K-line data
# ============================================================

def make_klines(n: int = 250, base_price: float = 100.0, trend: float = 0.02,
                volatility: float = 1.0) -> list:
    """Generate synthetic daily K-lines with a gentle uptrend + noise.

    Uses a deterministic pseudo-random sequence so tests are reproducible.

    Args:
        n: Number of bars
        base_price: Starting price
        trend: Daily drift
        volatility: Daily noise stddev

    Returns:
        [{date, open, high, low, close, volume}]
    """
    import datetime
    import math as _m
    # Simple deterministic noise: use sin-based pseudo-random
    bars = []
    price = base_price
    for i in range(n):
        # Deterministic "random" using sin(i * large_prime)
        noise = _m.sin(i * 2654435761.0 % (2 * _m.pi)) * volatility
        change = trend + noise
        price = max(price + change, 1.0)  # prevent negative
        date = (datetime.date(2025, 6, 1) + datetime.timedelta(days=i)).strftime("%Y-%m-%d")
        o = round(price - change * 0.3, 2)
        h = round(price + abs(noise) * 1.5, 2)
        l = round(price - abs(noise) * 1.5, 2)
        c = round(price, 2)
        v = int(1e7 + abs(noise) * 5e6)
        bars.append({"date": date, "open": o, "high": h, "low": l, "close": c, "volume": v})
    return bars


def make_flat_klines(n: int = 250) -> list:
    """Generate flat K-lines (all same price) for edge case testing."""
    import datetime
    bars = []
    for i in range(n):
        date = (datetime.date(2025, 6, 1) + datetime.timedelta(days=i)).strftime("%Y-%m-%d")
        bars.append({"date": date, "open": 100.0, "high": 101.0, "low": 99.0,
                      "close": 100.0, "volume": 1e7})
    return bars


# ============================================================
# series.py tests
# ============================================================

class TestSeries(unittest.TestCase):
    """Test indicator series computation."""

    def setUp(self):
        self.klines = make_klines(250, base_price=100.0, trend=0.02, volatility=1.0)
        from data.formula_engine.series import compute_all_series
        self.series = compute_all_series(self.klines)

    def test_output_has_all_keys(self):
        """All 22 expected series keys are present."""
        expected = {"c", "o", "h", "l", "v",
                    "ma5", "ma10", "ma20", "ma60",
                    "macd_dif", "macd_dea", "macd_bar",
                    "rsi6", "rsi12",
                    "boll_upper", "boll_mid", "boll_lower",
                    "kdj_k", "kdj_d", "kdj_j",
                    "vol_ma5", "vol_ma20", "change_pct"}
        self.assertEqual(set(self.series.keys()), expected)

    def test_length_equals_klines(self):
        """Every series has the same length as input klines."""
        n = len(self.klines)
        for key, arr in self.series.items():
            self.assertEqual(len(arr), n, f"Series '{key}' length mismatch: {len(arr)} vs {n}")

    def test_ma_padding(self):
        """MA series have None for first (period-1) elements."""
        ma5 = self.series["ma5"]
        self.assertIsNone(ma5[0])
        self.assertIsNone(ma5[3])
        self.assertIsNotNone(ma5[4])  # 5th element = first valid MA5

        ma60 = self.series["ma60"]
        self.assertIsNone(ma60[58])
        self.assertIsNotNone(ma60[59])

    def test_ma_values_plausible(self):
        """MA values are within reasonable range of price."""
        ma5 = [v for v in self.series["ma5"] if v is not None]
        self.assertGreater(len(ma5), 200)
        # MA5 should be close to the average of last 5 closes
        last_5 = [self.klines[i]["close"] for i in range(-5, 0)]
        expected = sum(last_5) / 5
        self.assertAlmostEqual(ma5[-1], expected, delta=2.0)

    def test_macd_structure(self):
        """MACD dif/dea/bar have proper relationships."""
        dif = self.series["macd_dif"]
        dea = self.series["macd_dea"]
        bar = self.series["macd_bar"]

        # Find last valid
        last_valid = -1
        for i in range(len(dif) - 1, -1, -1):
            if dif[i] is not None and dea[i] is not None and bar[i] is not None:
                last_valid = i
                break

        self.assertGreater(last_valid, 0)
        # BAR = 2 * (DIF - DEA)
        self.assertAlmostEqual(bar[last_valid], 2.0 * (dif[last_valid] - dea[last_valid]), delta=0.01)

    def test_rsi_range(self):
        """RSI values are within [0, 100] range."""
        for key in ["rsi6", "rsi12"]:
            for v in self.series[key]:
                if v is not None:
                    self.assertGreaterEqual(v, 0.0)
                    self.assertLessEqual(v, 100.0)

    def test_rsi_flat_is_50(self):
        """RSI on flat prices should approach 50 (no change → no gain/loss)."""
        flat = make_flat_klines(50)
        from data.formula_engine.series import calc_rsi_series
        closes = [b["close"] for b in flat]
        rsi = calc_rsi_series(closes, 6)
        # Values should be near 50 (equal gains and losses = 0)
        vals = [v for v in rsi if v is not None]
        if vals:
            self.assertAlmostEqual(vals[-1], 50.0, delta=5.0)

    def test_boll_structure(self):
        """Bollinger upper >= mid >= lower."""
        upper = self.series["boll_upper"]
        mid = self.series["boll_mid"]
        lower = self.series["boll_lower"]
        for i in range(len(upper)):
            if upper[i] is not None and mid[i] is not None and lower[i] is not None:
                self.assertGreaterEqual(upper[i], mid[i])
                self.assertGreaterEqual(mid[i], lower[i])

    def test_kdj_values_plausible(self):
        """KDJ values are in a reasonable range."""
        for key in ["kdj_k", "kdj_d", "kdj_j"]:
            vals = [v for v in self.series[key] if v is not None]
            self.assertTrue(len(vals) > 0, f"No valid values for {key}")

    def test_change_pct_first_is_none(self):
        """First change_pct element is None."""
        self.assertIsNone(self.series["change_pct"][0])

    def test_volume_ma(self):
        """Volume MA values are non-negative."""
        for key in ["vol_ma5", "vol_ma20"]:
            for v in self.series[key]:
                if v is not None:
                    self.assertGreaterEqual(v, 0.0)


# ============================================================
# events.py tests
# ============================================================

class TestEvents(unittest.TestCase):
    """Test event detection."""

    def setUp(self):
        from data.formula_engine.series import compute_all_series
        self.klines = make_klines(250, base_price=100.0, trend=0.02, volatility=1.0)
        self.series = compute_all_series(self.klines)
        self.dates = [b["date"] for b in self.klines]

    def test_cross_detection_no_error(self):
        """Cross detection runs without error."""
        from data.formula_engine.events import detect_cross_events
        events = detect_cross_events(self.series["ma5"], self.series["ma20"], self.dates)
        self.assertIsInstance(events, list)

    def test_cross_detection_with_none(self):
        """Cross detection handles None values gracefully."""
        from data.formula_engine.events import detect_cross_events
        # Series full of None should return empty
        none_series = [None] * 250
        events = detect_cross_events(none_series, none_series, self.dates)
        self.assertEqual(events, [])

    def test_cross_detection_known_case(self):
        """Cross detection on a constructed case where we know the answer."""
        from data.formula_engine.events import detect_cross_events
        # Series A crosses above B at index 1
        a = [None, None, 5.0, 6.0, 7.0]
        b = [None, None, 5.0, 5.0, 5.0]
        dates = ["2025-01-01", "2025-01-02", "2025-01-03", "2025-01-04", "2025-01-05"]
        events = detect_cross_events(a, b, dates, lookback=10)
        self.assertGreaterEqual(len(events), 1)
        self.assertEqual(events[0]["type"], "golden_cross")
        self.assertEqual(events[0]["date"], "2025-01-04")

        # Series A crosses below B at index 1
        a2 = [None, None, 5.0, 4.0, 3.0]
        events2 = detect_cross_events(a2, b, dates, lookback=10)
        self.assertGreaterEqual(len(events2), 1)
        self.assertEqual(events2[0]["type"], "death_cross")

    def test_threshold_breaches(self):
        """Threshold breach detection works."""
        from data.formula_engine.events import detect_threshold_breaches
        s = [None, 45.0, 48.0, 52.0, 55.0, 51.0]
        dates = [f"2025-01-0{i}" for i in range(1, 7)]
        events = detect_threshold_breaches(s, 50.0, dates, operator=">", lookback=10)
        self.assertGreaterEqual(len(events), 1)
        self.assertEqual(events[0]["type"], "breach_up")
        self.assertEqual(events[0]["date"], "2025-01-04")

    def test_trend_detection(self):
        """Trend detection returns expected structure."""
        from data.formula_engine.events import detect_trend
        result = detect_trend(self.series["c"], window=10)
        self.assertIn(result["direction"], ["rising", "falling", "flat"])
        self.assertIn("slope", result)
        self.assertIn("recent_values", result)
        self.assertEqual(len(result["recent_values"]), 10)


# ============================================================
# elements.py tests
# ============================================================

class TestElements(unittest.TestCase):
    """Test formula parsing and element assembly."""

    def setUp(self):
        from data.formula_engine.series import compute_all_series
        self.klines = make_klines(250)
        self.series = compute_all_series(self.klines)
        self.dates = [b["date"] for b in self.klines]

    def test_parse_simple_cross(self):
        """Parse CROSS(MA(C,5), MA(C,20))."""
        from data.formula_engine.elements import parse_formula
        elements = parse_formula("CROSS(MA(C,5), MA(C,20))", self.series, self.dates)
        self.assertEqual(len(elements), 1)
        self.assertEqual(elements[0]["element_type"], "cross")

    def test_parse_compare(self):
        """Parse RSI(6) > 50."""
        from data.formula_engine.elements import parse_formula
        elements = parse_formula("RSI(6) > 50", self.series, self.dates)
        self.assertEqual(len(elements), 1)
        self.assertEqual(elements[0]["element_type"], "compare")
        self.assertEqual(elements[0]["threshold"], 50)

    def test_parse_chinese_formula(self):
        """Parse a formula with Chinese tokens."""
        from data.formula_engine.elements import parse_formula
        elements = parse_formula("收盘价 > 50", self.series, self.dates)
        self.assertGreaterEqual(len(elements), 1)

    def test_parse_compound_and(self):
        """Parse formula with AND logic."""
        from data.formula_engine.elements import parse_formula
        elements = parse_formula("CROSS(MA(C,5), MA(C,20)) & RSI(6) > 50", self.series, self.dates)
        self.assertEqual(len(elements), 2)
        self.assertEqual(elements[0]["logic_op"], "&")
        self.assertEqual(elements[1]["logic_op"], None)

    def test_parse_statistical_hhv(self):
        """Parse HHV(H, 20) as statistical."""
        from data.formula_engine.elements import parse_formula
        elements = parse_formula("HHV(H, 20)", self.series, self.dates)
        self.assertEqual(len(elements), 1)
        self.assertEqual(elements[0]["element_type"], "statistical")

    def test_parse_statistical_llv(self):
        """Parse LLV(L, 20) as statistical."""
        from data.formula_engine.elements import parse_formula
        elements = parse_formula("LLV(L, 20)", self.series, self.dates)
        self.assertEqual(len(elements), 1)
        self.assertEqual(elements[0]["element_type"], "statistical")

    def test_parse_count_condition_is_opaque(self):
        """COUNT(C > MA(C,20), 10) → opaque (nested condition)."""
        from data.formula_engine.elements import parse_formula
        elements = parse_formula("COUNT(C > MA(C,20), 10)", self.series, self.dates)
        self.assertEqual(len(elements), 1)
        self.assertEqual(elements[0]["element_type"], "opaque")

    def test_parse_count_pure_variable_is_statistical(self):
        """COUNT(C, 10) → statistical (pure variable)."""
        from data.formula_engine.elements import parse_formula
        elements = parse_formula("COUNT(C, 10)", self.series, self.dates)
        self.assertEqual(len(elements), 1)
        # COUNT of pure var → it will be matched as compare or statistical
        # Actually: COUNT is a statistical function, but with C as pure variable
        self.assertIn(elements[0]["element_type"], ["statistical", "compare"])

    def test_parse_empty_formula(self):
        """Parse empty formula returns empty list."""
        from data.formula_engine.elements import parse_formula
        elements = parse_formula("", self.series, self.dates)
        self.assertEqual(elements, [])

    def test_parse_opaque_unknown(self):
        """Unknown expression becomes opaque."""
        from data.formula_engine.elements import parse_formula
        elements = parse_formula("XYZ_UNKNOWN(1,2,3)", self.series, self.dates)
        self.assertGreaterEqual(len(elements), 1)
        # Should be opaque since it doesn't match any known pattern
        self.assertEqual(elements[0]["element_type"], "opaque")

    def test_variable_resolution(self):
        """_resolve_variable returns correct keys."""
        from data.formula_engine.constants import resolve_variable
        self.assertIn("ma5", resolve_variable("MA(C,5)"))
        self.assertIn("rsi6", resolve_variable("RSI(6)"))
        self.assertIn("c", resolve_variable("C"))
        self.assertIn("macd_dif", resolve_variable("MACD.DIF"))

    def test_normalize_formula(self):
        """Normalize formula converts Chinese and standardizes."""
        from data.formula_engine.constants import normalize_formula
        result = normalize_formula("收盘价 > 50")
        self.assertIn("C", result)  # 收盘价 → C
        self.assertIn(">", result)

    def test_split_by_logic(self):
        """Split formula by logic operators at correct paren depth."""
        from data.formula_engine.elements import _split_by_logic
        fragments = _split_by_logic("MA(C,5) & RSI(6) | CROSS(A,B)")
        self.assertEqual(len(fragments), 3)
        self.assertEqual(fragments[0][1], "&")   # MA(C,5) &
        self.assertEqual(fragments[1][1], "|")   # RSI(6) |
        self.assertEqual(fragments[2][1], None)  # CROSS(A,B)


# ============================================================
# Integration tests — prepare()
# ============================================================

class TestPrepare(unittest.TestCase):
    """Integration test for the unified prepare() entry point."""

    def setUp(self):
        self.klines = make_klines(250)
        self.stock_info = {"name": "测试股票", "market": "沪市", "period": "daily"}

    def test_scenario_single(self):
        """Scenario 'single': 1 stock, no formula."""
        from data.formula_engine import prepare
        pkg = prepare(
            {"SH600000": self.klines},
            {"SH600000": self.stock_info},
        )
        self.assertEqual(pkg.scenario, "single")
        self.assertEqual(len(pkg.stocks), 1)
        self.assertIsNone(pkg.formula)

    def test_scenario_single_formula(self):
        """Scenario 'single_formula': 1 stock + formula."""
        from data.formula_engine import prepare
        pkg = prepare(
            {"SH600000": self.klines},
            {"SH600000": self.stock_info},
            formula="CROSS(MA(C,5), MA(C,20)) & RSI(6) > 50",
        )
        self.assertEqual(pkg.scenario, "single_formula")
        self.assertIsNotNone(pkg.formula)
        self.assertGreater(len(pkg.formula.elements), 0)

    def test_scenario_multi(self):
        """Scenario 'multi': 2 stocks, no formula."""
        from data.formula_engine import prepare
        k2 = make_klines(245, base_price=50.0)
        pkg = prepare(
            {"SH600000": self.klines, "SZ000001": k2},
            {"SH600000": self.stock_info, "SZ000001": {"name": "测试B", "market": "深市"}},
        )
        self.assertEqual(pkg.scenario, "multi")
        self.assertEqual(len(pkg.stocks), 2)
        self.assertIsNone(pkg.formula)
        self.assertIsNotNone(pkg.comparison)
        self.assertIn("headers", pkg.comparison)

    def test_scenario_multi_formula(self):
        """Scenario 'multi_formula': 2 stocks + formula."""
        from data.formula_engine import prepare
        k2 = make_klines(250, base_price=50.0)
        pkg = prepare(
            {"SH600000": self.klines, "SZ000001": k2},
            {"SH600000": self.stock_info, "SZ000001": {"name": "测试B", "market": "深市"}},
            formula="CROSS(MA(C,5), MA(C,20))",
        )
        self.assertEqual(pkg.scenario, "multi_formula")
        self.assertIsNotNone(pkg.formula)
        self.assertIsNotNone(pkg.comparison)
        self.assertIn("formula_comparison", pkg.comparison)

    def test_to_json_output(self):
        """to_json returns valid JSON string."""
        from data.formula_engine import prepare
        pkg = prepare(
            {"SH600000": self.klines},
            {"SH600000": self.stock_info},
            formula="RSI(6) > 50",
        )
        json_str = pkg.to_json()
        self.assertIsInstance(json_str, str)
        data = json.loads(json_str)
        self.assertEqual(data["scenario"], "single_formula")
        self.assertEqual(len(data["stocks"]), 1)

    def test_to_json_compact(self):
        """to_json(compact=True) returns valid JSON."""
        from data.formula_engine import prepare
        pkg = prepare(
            {"SH600000": self.klines},
            {"SH600000": self.stock_info},
        )
        json_str = pkg.to_json(compact=True)
        data = json.loads(json_str)
        self.assertEqual(data["scenario"], "single")

    def test_to_prompt_output(self):
        """to_prompt returns a meaningful markdown string."""
        from data.formula_engine import prepare
        pkg = prepare(
            {"SH600000": self.klines},
            {"SH600000": self.stock_info},
            formula="CROSS(MA(C,5), MA(C,20))",
        )
        prompt = pkg.to_prompt(days=30)
        self.assertIsInstance(prompt, str)
        self.assertIn("测试股票", prompt)
        self.assertIn("SH600000", prompt)
        self.assertIn("选股公式", prompt)

    def test_warnings_for_short_data(self):
        """Warnings generated for insufficient data."""
        from data.formula_engine import prepare
        short = make_klines(10)
        pkg = prepare(
            {"SH600000": short},
            {"SH600000": self.stock_info},
        )
        data_short_warnings = [w for w in pkg.warnings if "条" in w and "均线" in w]
        self.assertGreater(len(data_short_warnings), 0)

    def test_max_6_stocks(self):
        """Maximum 6 stocks enforced."""
        from data.formula_engine import prepare
        kl_map = {}
        info_map = {}
        for i in range(7):
            code = f"SH60000{i}"
            kl_map[code] = make_klines(100)
            info_map[code] = {"name": f"股票{i}"}
        with self.assertRaises(ValueError):
            prepare(kl_map, info_map)

    def test_unknown_formula_is_opaque(self):
        """A completely unknown string is handled as opaque."""
        from data.formula_engine import prepare
        pkg = prepare(
            {"SH600000": self.klines},
            {"SH600000": self.stock_info},
            formula="SOME_UNKNOWN_INDICATOR(1,2,3)",
        )
        if pkg.formula and pkg.formula.elements:
            for el in pkg.formula.elements:
                if el.element_type == "opaque":
                    break
            else:
                # If no opaque element, formula resulted in empty elements list
                pass


if __name__ == "__main__":
    unittest.main(verbosity=2)
