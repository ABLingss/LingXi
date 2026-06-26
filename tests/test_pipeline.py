#!/usr/bin/env python3.9
"""
test_pipeline.py — Unit tests for Stock JSON Clipper core pipeline (M2).

Tests:
  1. Indicator calculations (with known-answer test data)
  2. Data builder JSON structure validation
  3. Cache manager TTL and thread safety
  4. Clipboard monitor pattern matching
  5. Stock code parsing edge cases
  6. API error handling (with mock responses)
  7. Market detection

Usage:
  python3.9 test_pipeline.py
"""

import json
import sys
import os
import time
import threading

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.clipboard import parse_clipboard, StockRequest
from core.cache import CacheManager
from api.client import StockError, _em_secid as make_secid
from data.indicators import (
    calc_ma, calc_ema, calc_macd, calc_rsi, calc_boll, calc_all_indicators,
)
from data.builder import build_json, build_summary, to_json_string, _determine_market_label

# Compatibility wrapper: tests expect determine_market to return dict
def determine_market(code: str) -> dict:
    return {"market": _determine_market_label(code)}


PASS = 0
FAIL = 0


def check(condition, test_name):
    """Simple test assertion."""
    global PASS, FAIL
    if condition:
        PASS += 1
        print(f"  ✅ {test_name}")
    else:
        FAIL += 1
        print(f"  ❌ {test_name}")


# ============================================================
# 1. Clipboard Monitor — pattern matching
# ============================================================
def test_clipboard_patterns():
    print("\n📋 Clipboard Monitor — Pattern Matching")

    # Valid patterns
    req = parse_clipboard("000001")
    check(req is not None and req.code == "000001" and req.period == "daily" and not req.save_mode,
          "000001 → daily, no save")

    req = parse_clipboard("600036")
    check(req is not None and req.code == "600036" and req.period == "daily",
          "600036 → daily")

    req = parse_clipboard("#000001")
    check(req is not None and req.code == "000001" and req.save_mode,
          "#000001 → save mode")

    req = parse_clipboard("W:000001")
    check(req is not None and req.code == "000001" and req.period == "weekly",
          "W:000001 → weekly")

    req = parse_clipboard("M:000001")
    check(req is not None and req.code == "000001" and req.period == "monthly",
          "M:000001 → monthly")

    req = parse_clipboard("#W:600036")
    check(req is not None and req.code == "600036" and req.period == "weekly" and req.save_mode,
          "#W:600036 → weekly + save")

    req = parse_clipboard("#M:300750")
    check(req is not None and req.code == "300750" and req.period == "monthly" and req.save_mode,
          "#M:300750 → monthly + save")

    # Invalid patterns
    check(parse_clipboard("") is None, "empty string → None")
    check(parse_clipboard("hello") is None, "random text → None")
    check(parse_clipboard("00000") is None, "5 digits → None")
    check(parse_clipboard("0000001") is None, "7 digits → None")
    check(parse_clipboard("000001,000002") is None, "comma separated → None")
    check(parse_clipboard("ABC:000001") is None, "bad prefix → None")


# ============================================================
# 2. Market Detection
# ============================================================
def test_market_detection():
    print("\n🏛️  Market Detection")

    check(determine_market("600036")["market"] == "沪市", "600036 → 沪市")
    check(determine_market("688001")["market"] == "沪市", "688001 → 沪市")
    check(determine_market("000001")["market"] == "深市", "000001 → 深市")
    check(determine_market("300750")["market"] == "深市", "300750 → 深市")
    check(determine_market("002415")["market"] == "深市", "002415 → 深市")

    check(make_secid("600036") == "1.600036", "secid 600036")
    check(make_secid("000001") == "0.000001", "secid 000001")


# ============================================================
# 3. Technical Indicators — known answer tests
# ============================================================
def test_indicators():
    print("\n📊 Technical Indicators")

    # Simple test data: 100 linearly increasing prices from 10.0 to 10.99
    prices = [10.0 + i * 0.01 for i in range(100)]

    # MA
    ma5 = calc_ma(prices, 5)
    check(ma5 is not None and abs(ma5 - 10.97) < 0.02, f"MA5 ≈ 10.97 (got {ma5})")

    ma60 = calc_ma(prices, 60)
    check(ma60 is not None and abs(ma60 - 10.695) < 0.02, f"MA60 ≈ 10.695 (got {ma60})")

    # Insufficient data
    ma200 = calc_ma(prices, 200)
    check(ma200 is None, "MA200 on 100 bars → None")

    # EMA
    ema12 = calc_ema(prices, 12)
    check(len(ema12) == 100, f"EMA length = 100 (got {len(ema12)})")
    check(ema12[-1] > 10.9, f"EMA12(last) > 10.9 (got {ema12[-1]:.4f})")

    # MACD
    macd = calc_macd(prices)
    check("dif" in macd and "dea" in macd and "bar" in macd,
          "MACD returns {dif, dea, bar}")
    # For linearly increasing prices, DIF should be positive but small
    check(abs(macd["dif"]) < 0.2, f"MACD DIF small for linear trend (got {macd['dif']})")

    # RSI — linear uptrend should give high RSI
    rsi6 = calc_rsi(prices, 6)
    check(rsi6 is not None and rsi6 > 50, f"RSI(6) > 50 in uptrend (got {rsi6})")

    rsi12 = calc_rsi(prices, 12)
    check(rsi12 is not None and rsi12 > 50, f"RSI(12) > 50 in uptrend (got {rsi12})")

    # RSI insufficient data
    rsi_bad = calc_rsi([10.0, 10.1, 10.2], 14)
    check(rsi_bad is None, "RSI(14) on 3 bars → None")

    # BOLL
    boll = calc_boll(prices, 20)
    check(boll["mid"] is not None and boll["upper"] is not None and boll["lower"] is not None,
          "BOLL returns {upper, mid, lower}")
    check(boll["upper"] > boll["mid"] > boll["lower"],
          f"BOLL upper({boll['upper']}) > mid({boll['mid']}) > lower({boll['lower']})")

    # BOLL insufficient data
    boll_bad = calc_boll([1.0, 2.0, 3.0], 20)
    check(boll_bad["mid"] is None, "BOLL(20) on 3 bars → None")

    # calc_all_indicators
    all_ind = calc_all_indicators(prices)
    check("ma5" in all_ind and "macd" in all_ind and "rsi_6" in all_ind and "boll" in all_ind,
          "calc_all_indicators returns all keys")

    # Edge: constant prices (zero volatility)
    flat = [10.0] * 50
    rsi_flat = calc_rsi(flat, 14)
    check(rsi_flat is not None and rsi_flat == 50.0, f"RSI on flat prices → 50 (got {rsi_flat})")

    boll_flat = calc_boll(flat, 20)
    check(boll_flat["upper"] == boll_flat["mid"] == boll_flat["lower"],
          f"BOLL on flat prices → all equal (got {boll_flat})")

    # Edge: single element
    check(calc_ma([10.0], 5) is None, "MA5 on 1 element → None")


# ============================================================
# 4. Data Builder — JSON structure validation
# ============================================================
def test_data_builder():
    print("\n🏗️  Data Builder — JSON Structure")

    # Mock K-line data
    kline_data = []
    for i in range(250):
        kline_data.append({
            "date": f"2025-{(i // 20) + 1:02d}-{(i % 28) + 1:02d}",
            "open": 10.0 + i * 0.01,
            "high": 10.5 + i * 0.01,
            "low": 9.8 + i * 0.01,
            "close": 10.2 + i * 0.01,
            "volume": 1000000 + i * 10000,
            "amount": 10200000.0 + i * 100000,
            "amplitude": 2.0,
            "change_pct": 0.1,
            "change": 0.01,
            "turnover": 1.5,
        })

    stock_info = {
        "name": "平安银行",
        "industry": "银行",
        "pe_ttm": 5.23,
        "total_mv": 2800.5,
        "float_mv": 2500.0,
        "list_date": "1991-04-03",
    }

    result = build_json(kline_data, stock_info, "000001", period="daily", count=250)

    # Check meta
    check(result["meta"]["code"] == "000001", "meta.code")
    check(result["meta"]["name"] == "平安银行", "meta.name")
    check(result["meta"]["market"] == "深市", "meta.market")
    check(result["meta"]["industry"] == "银行", "meta.industry")
    check(result["meta"]["pe_ttm"] == 5.23, "meta.pe_ttm")
    check(result["meta"]["total_mv"] == 2800.5, "meta.total_mv")
    check(result["meta"]["period"] == "daily", "meta.period")
    check(result["meta"]["data_count"] == 250, "meta.data_count")
    check(len(result["meta"]["start_date"]) == 10, "meta.start_date format")
    check(len(result["meta"]["end_date"]) == 10, "meta.end_date format")

    # Check indicators
    check("ma5" in result["indicators"], "indicators.ma5 exists")
    check("ma10" in result["indicators"], "indicators.ma10 exists")
    check("ma20" in result["indicators"], "indicators.ma20 exists")
    check("ma60" in result["indicators"], "indicators.ma60 exists")
    check("dif" in result["indicators"]["macd"], "indicators.macd.dif")
    check("rsi_6" in result["indicators"], "indicators.rsi_6")
    check("rsi_12" in result["indicators"], "indicators.rsi_12")
    check("upper" in result["indicators"]["boll"], "indicators.boll.upper")

    # Check summary
    check("period_change" in result["summary"], "summary.period_change")
    check("max_close" in result["summary"], "summary.max_close")
    check("min_close" in result["summary"], "summary.min_close")
    check("avg_volume" in result["summary"], "summary.avg_volume")
    check("volatility" in result["summary"], "summary.volatility")

    # Check data array
    check(len(result["data"]) == 250, "data array length = 250")
    check("date" in result["data"][0] and "close" in result["data"][0],
          "data[0] has date and close")
    # Verify no extra API fields in slim output
    check("amplitude" not in result["data"][0], "data[0] has no extra fields")

    # JSON serialization
    json_str = to_json_string(result)
    check(isinstance(json_str, str) and len(json_str) > 100,
          "to_json_string returns valid string")
    check("平安银行" in json_str, "JSON contains Chinese characters")
    parsed = json.loads(json_str)
    check(parsed["meta"]["code"] == "000001", "round-trip JSON parse OK")

    # Empty data edge case
    empty_result = build_json([], stock_info, "000001")
    check(empty_result["meta"]["data_count"] == 0, "empty data → data_count=0")
    check(empty_result["meta"]["start_date"] == "", "empty data → start_date=''")

    # build_summary standalone
    summary = build_summary(kline_data)
    check(summary["max_close"] > summary["min_close"], "summary max > min")


# ============================================================
# 5. Cache Manager — TTL & thread safety
# ============================================================
def test_cache_manager():
    print("\n💾 Cache Manager")

    cm = CacheManager(ttl=1.0)  # 1 second TTL for testing

    # Basic set/get
    cm.set("000001_daily", {"data": "test"})
    val = cm.get("000001_daily")
    check(val == {"data": "test"}, "cache set/get")

    # Miss on unknown key
    check(cm.get("nonexistent") is None, "cache miss → None")

    # TTL expiry
    time.sleep(1.2)
    expired = cm.get("000001_daily")
    check(expired is None, "cache entry expired after TTL")

    # Clear
    cm.set("a", 1)
    cm.set("b", 2)
    cm.clear()
    check(cm.get("a") is None and cm.get("b") is None, "clear() removes all")

    # make_key
    key = cm.make_key("600036", "weekly")
    check(key == "600036_weekly", f"make_key = '600036_weekly' (got '{key}')")

    # Thread safety: concurrent writes
    errors = []
    def writer():
        try:
            for i in range(100):
                cm.set(f"key_{i}", i)
        except Exception as e:
            errors.append(str(e))

    threads = [threading.Thread(target=writer) for _ in range(4)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    check(len(errors) == 0, f"concurrent writes no errors (got {len(errors)} errors)")
    check(cm.size > 0, f"entries after concurrent writes: {cm.size}")

    # Cleanup
    removed = cm.cleanup()
    print(f"   ℹ️  cleanup removed {removed} expired entries")


# ============================================================
# 6. StockError
# ============================================================
def test_stock_error():
    print("\n⚠️  StockError")

    err = StockError("000001", "测试错误")
    check(err.code == "000001", "StockError.code")
    check("000001" in str(err) and "测试错误" in str(err), "StockError string representation")


# ============================================================
# Main
# ============================================================
if __name__ == "__main__":
    print("=" * 60)
    print("🧪 Stock JSON Clipper — Pipeline Test Suite")
    print("=" * 60)

    test_clipboard_patterns()
    test_market_detection()
    test_indicators()
    test_data_builder()
    test_cache_manager()
    test_stock_error()

    print("\n" + "=" * 60)
    total = PASS + FAIL
    print(f"Results: {PASS}/{total} passed")
    if FAIL > 0:
        print(f"❌ {FAIL} test(s) FAILED!")
        sys.exit(1)
    else:
        print("✅ All tests passed!")
        sys.exit(0)
