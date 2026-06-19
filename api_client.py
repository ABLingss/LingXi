"""
api_client.py — Multi-source A-share data API wrapper for Stock JSON Clipper V2.0.

Data sources (tried in order until one succeeds):
  1. Tencent (腾讯财经) — K-line + stock name, supports day/week/month
  2. Sina (新浪财经) — K-line, fast & reliable
  3. East Money (东方财富) — K-line + full stock info (PE, industry, market cap)

All functions return standardized dicts/lists or raise StockError on all-source failure.

Provider-specific URLs:
  Tencent K-line: web.ifzq.gtimg.cn/appstock/app/fqkline/get
  Tencent info:   qt.gtimg.cn/q={sz/sh}{code}
  Sina K-line:    money.finance.sina.com.cn/quotes_service/api/json_v2.php
  East Money:     push2his.eastmoney.com + push2.eastmoney.com (may be unavailable)
"""

import json
import re
from typing import Any, Dict, List, Optional

import requests


# ============================================================
# Constants
# ============================================================

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
}

DEFAULT_TIMEOUT = 5

# Period mapping: internal → Tencent / Sina / EastMoney
PERIOD_MAP = {
    "daily":   {"tencent": "day",   "sina_scale": 240,  "em_klt": 101},
    "weekly":  {"tencent": "week",  "sina_scale": 1200, "em_klt": 102},
    "monthly": {"tencent": "month", "sina_scale": 7200, "em_klt": 103},
}


# ============================================================
# Error type
# ============================================================

class StockError(Exception):
    """Raised when stock data cannot be fetched from any source."""

    def __init__(self, code: str, message: str) -> None:
        self.code = code
        self.message = message
        super().__init__(f"[{code}] {message}")


# ============================================================
# Market helpers
# ============================================================

def _is_sh(code: str) -> bool:
    """Check if a 6-digit A-share code belongs to Shanghai (沪市)."""
    return code.startswith(("60", "68"))


def _market_prefix(code: str) -> str:
    """Return 'sh' or 'sz' for the given 6-digit stock code."""
    return "sh" if _is_sh(code) else "sz"


def _em_secid(code: str) -> str:
    """Build East Money secid: '1.000001' (SH) or '0.000001' (SZ)."""
    pre = "1" if _is_sh(code) else "0"
    return f"{pre}.{code}"


# ============================================================
# Provider: Tencent (腾讯财经)
# ============================================================

def _tct_kline(code: str, period: str, count: int, timeout: int) -> List[Dict[str, Any]]:
    """Fetch K-line from Tencent Finance.

    URL: web.ifzq.gtimg.cn/appstock/app/fqkline/get
    Response format:
      data.{prefix}{code}.qfq{period} → [[date, open, close, high, low, volume], ...]
    """
    prefix = _market_prefix(code)
    tct_period = PERIOD_MAP[period]["tencent"]
    param = f"{prefix}{code},{tct_period},,,{count},qfq"

    resp = requests.get(
        "http://web.ifzq.gtimg.cn/appstock/app/fqkline/get",
        params={"param": param},
        headers=HEADERS,
        timeout=timeout,
    )
    resp.raise_for_status()
    data = resp.json()

    # Tencent API may return list instead of dict when count exceeds available data
    if isinstance(data, list):
        raise StockError(code, "腾讯API返回数据格式异常(超量请求)")

    if data.get("code") != 0:
        raise StockError(code, "腾讯API返回错误: " + str(data.get("msg", "")))

    symbol = f"{prefix}{code}"
    kline_key = f"qfq{tct_period}"
    stock_data = data.get("data", {})
    if not isinstance(stock_data, dict):
        raise StockError(code, "腾讯API返回数据格式异常")
    raw_bars = stock_data.get(symbol, {}).get(kline_key, [])

    if not raw_bars:
        raise StockError(code, "腾讯API无K线数据")

    result: List[Dict[str, Any]] = []
    for bar in raw_bars:
        # [date, open, close, high, low, volume]
        if len(bar) < 6:
            continue
        result.append({
            "date": str(bar[0]).strip(),
            "open": _safe_float(bar[1]),
            "close": _safe_float(bar[2]),
            "high": _safe_float(bar[3]),
            "low": _safe_float(bar[4]),
            "volume": int(_safe_float(bar[5])),
            "amount": 0.0,
            "amplitude": 0.0,
            "change_pct": 0.0,
            "change": 0.0,
            "turnover": 0.0,
        })

    return result


def _tct_stock_info(code: str, timeout: int) -> Dict[str, Any]:
    """Fetch basic stock info (name, PE, market cap) from Tencent qt API.

    URL: qt.gtimg.cn/q={sz/sh}{code}
    Response: tilde-separated GBK-encoded key-value string.
      Field 1:  stock name
      Field 39: PE (TTM)
      Field 72: total market cap (总市值)
      Field 73: float market cap (流通市值)
    """
    prefix = _market_prefix(code)
    resp = requests.get(
        "http://qt.gtimg.cn/",
        params={"q": f"{prefix}{code}"},
        headers=HEADERS,
        timeout=timeout,
    )
    resp.raise_for_status()

    # Tencent qt API returns GBK-encoded data; requests auto-detects via charset
    raw = resp.text

    # Parse tilde-separated format: v_sz000001="field0~field1~..."
    match = re.search(r'="([^"]*)"', raw)
    if not match:
        raise StockError(code, "腾讯股票信息格式异常")

    fields = match.group(1).split("~")
    if len(fields) < 10:
        raise StockError(code, "腾讯股票信息字段不足")

    name = fields[1].strip() if len(fields) > 1 else "未知"
    # Field 39 = PE(TTM), e.g. 4.74 for 平安银行
    pe_ttm = _safe_float(fields[39] if len(fields) > 39 else None, -1.0)
    # Field 72 = total market cap (总市值), 73 = float market cap (流通市值)
    total_mv = _safe_float(fields[72] if len(fields) > 72 else None, -1.0)
    float_mv = _safe_float(fields[73] if len(fields) > 73 else None, -1.0)
    # Use stock type field (GP-A) as industry placeholder; East Money gives real industry
    industry = _safe_str(fields[61] if len(fields) > 61 else None, "")

    return {
        "name": name,
        "pe_ttm": pe_ttm,
        "total_mv": total_mv,
        "float_mv": float_mv,
        "industry": industry,
        "list_date": "",
    }


# ============================================================
# Provider: Sina (新浪财经)
# ============================================================

def _sina_kline(code: str, period: str, count: int, timeout: int) -> List[Dict[str, Any]]:
    """Fetch K-line from Sina Finance.

    URL: money.finance.sina.com.cn/quotes_service/api/json_v2.php/CN_MarketData.getKLineData
    Params: symbol={sz/sh}{code}, scale={240/1200/7200}, datalen={count}
    Response: [{day, open, high, low, close, volume}, ...]
    """
    prefix = _market_prefix(code)
    scale = PERIOD_MAP[period]["sina_scale"]

    resp = requests.get(
        "http://money.finance.sina.com.cn/quotes_service/api/json_v2.php/"
        "CN_MarketData.getKLineData",
        params={
            "symbol": f"{prefix}{code}",
            "scale": scale,
            "ma": "no",
            "datalen": count,
        },
        headers=HEADERS,
        timeout=timeout,
    )
    resp.raise_for_status()

    # Sina sometimes returns HTML error pages with 200 status
    content_type = resp.headers.get("Content-Type", "")
    if "html" in content_type.lower() or resp.text.strip().startswith("<"):
        raise StockError(code, "新浪API返回非JSON数据")

    raw_data = resp.json()
    if not isinstance(raw_data, list):
        raise StockError(code, "新浪API返回格式异常")

    if not raw_data:
        raise StockError(code, "新浪API无K线数据")

    result: List[Dict[str, Any]] = []
    for bar in raw_data:
        result.append({
            "date": str(bar.get("day", "")).strip(),
            "open": _safe_float(bar.get("open")),
            "close": _safe_float(bar.get("close")),
            "high": _safe_float(bar.get("high")),
            "low": _safe_float(bar.get("low")),
            "volume": _safe_int(bar.get("volume")),
            "amount": 0.0,
            "amplitude": 0.0,
            "change_pct": 0.0,
            "change": 0.0,
            "turnover": 0.0,
        })

    return result


def _sina_stock_info(code: str, timeout: int) -> Dict[str, Any]:
    """Sina doesn't have a dedicated stock info API we can use.
    Always raises StockError to trigger fallback.
    """
    raise StockError(code, "新浪不支持股票信息查询")


# ============================================================
# Provider: East Money (东方财富)
# ============================================================

def _em_kline(code: str, period: str, count: int, timeout: int) -> List[Dict[str, Any]]:
    """Fetch K-line from East Money. May return 502 when service is down."""
    secid = _em_secid(code)
    klt = PERIOD_MAP[period]["em_klt"]

    params: Dict[str, Any] = {
        "secid": secid,
        "klt": klt,
        "fqt": 1,
        "lmt": count,
        "fields1": "f1,f2,f3,f4,f5,f6",
        "fields2": "f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61",
        "end": "20500101",
        "ut": "fa5fd1943c7b386f172d6893dbfc10f1",
    }

    resp = requests.get(
        "http://push2his.eastmoney.com/api/qt/stock/kline/get",
        params=params,
        headers=HEADERS,
        timeout=timeout,
    )
    resp.raise_for_status()

    raw = resp.json()

    if raw.get("rc") != 0 and raw.get("data") is None:
        raise StockError(code, "股票代码无效或已退市")

    data_block = raw.get("data")
    if data_block is None:
        raise StockError(code, "未获取到K线数据")

    klines_raw = data_block.get("klines", [])
    if not klines_raw:
        raise StockError(code, "该股票无K线数据")

    result: List[Dict[str, Any]] = []
    for line in klines_raw:
        parts = line.split(",")
        if len(parts) < 7:
            continue
        result.append({
            "date": parts[0].strip(),
            "open": _safe_float(parts[1]),
            "close": _safe_float(parts[2]),
            "high": _safe_float(parts[3]),
            "low": _safe_float(parts[4]),
            "volume": _safe_int(parts[5]),
            "amount": _safe_float(parts[6]),
            "amplitude": _safe_float(parts[7]) if len(parts) > 7 else 0.0,
            "change_pct": _safe_float(parts[8]) if len(parts) > 8 else 0.0,
            "change": _safe_float(parts[9]) if len(parts) > 9 else 0.0,
            "turnover": _safe_float(parts[10]) if len(parts) > 10 else 0.0,
        })

    return result


def _em_stock_info(code: str, timeout: int) -> Dict[str, Any]:
    """Fetch full stock info from East Money. May return 502 when service is down."""
    secid = _em_secid(code)

    params: Dict[str, Any] = {
        "secid": secid,
        "fields": "f57,f58,f116,f162,f167,f168",
        "ut": "fa5fd1943c7b386f172d6893dbfc10f1",
    }

    resp = requests.get(
        "http://push2.eastmoney.com/api/qt/stock/get",
        params=params,
        headers=HEADERS,
        timeout=timeout,
    )
    resp.raise_for_status()

    raw = resp.json()

    data_block = raw.get("data")
    if data_block is None:
        raise StockError(code, "未获取到股票基本信息")

    return {
        "name": _safe_str(data_block.get("f57"), "未知"),
        "pe_ttm": _safe_float(data_block.get("f162"), -1.0),
        "total_mv": _safe_float(data_block.get("f116"), -1.0),
        "float_mv": _safe_float(data_block.get("f167"), -1.0),
        "industry": _safe_str(data_block.get("f58"), "未知"),
        "list_date": _safe_date(data_block.get("f168"), ""),
    }


# ============================================================
# Public API with failover
# ============================================================

# Source order: prefer sources that give richest data first
KLINE_SOURCES = [
    ("Tencent", _tct_kline),      # K-line + name in qt
    ("Sina", _sina_kline),        # Reliable, fast
    ("EastMoney", _em_kline),     # Richest data (amount, turnover, etc.)
]

STOCK_INFO_SOURCES = [
    ("Tencent", _tct_stock_info),      # Always available, gives name + PE
    ("EastMoney", _em_stock_info),     # Full info when available
    # Sina: no stock info
]


def fetch_kline(
    code: str,
    period: str = "daily",
    count: int = 250,
    timeout: int = DEFAULT_TIMEOUT,
) -> List[Dict[str, Any]]:
    """Fetch historical K-line data from the first available source.

    Tries sources in order: Tencent → Sina → EastMoney.
    Returns standardized OHLCV list on first success.

    Args:
        code: 6-digit stock code.
        period: 'daily', 'weekly', or 'monthly'.
        count: Number of bars to fetch.
        timeout: Request timeout in seconds.

    Returns:
        List of OHLCV dicts ordered oldest-first.

    Raises:
        StockError: If ALL sources fail.
    """
    errors: List[str] = []

    for src_name, src_func in KLINE_SOURCES:
        try:
            result = src_func(code, period, count, timeout)
            if result:
                return result
            errors.append(f"{src_name}: empty data")
        except StockError as e:
            errors.append(f"{src_name}: {e.message}")
        except requests.Timeout:
            errors.append(f"{src_name}: timeout")
        except requests.ConnectionError:
            errors.append(f"{src_name}: connection error")
        except requests.RequestException as e:
            errors.append(f"{src_name}: {e}")
        except (json.JSONDecodeError, KeyError, ValueError, TypeError) as e:
            errors.append(f"{src_name}: parse error ({e})")

    raise StockError(code, " | ".join(errors))


def fetch_stock_info(
    code: str,
    timeout: int = DEFAULT_TIMEOUT,
) -> Dict[str, Any]:
    """Fetch stock basic info from the first available source.

    Tries sources in order: Tencent → EastMoney.
    Returns standardized info dict on first success.

    Args:
        code: 6-digit stock code.
        timeout: Request timeout in seconds.

    Returns:
        Dict with keys: name, industry, pe_ttm, total_mv, float_mv, list_date.

    Raises:
        StockError: If ALL sources fail.
    """
    errors: List[str] = []

    for src_name, src_func in STOCK_INFO_SOURCES:
        try:
            result = src_func(code, timeout)
            if result and result.get("name") and result["name"] != "未知":
                return result
            if result:
                errors.append(f"{src_name}: name is empty")
                continue
        except StockError as e:
            errors.append(f"{src_name}: {e.message}")
        except requests.Timeout:
            errors.append(f"{src_name}: timeout")
        except requests.ConnectionError:
            errors.append(f"{src_name}: connection error")
        except requests.RequestException as e:
            errors.append(f"{src_name}: {e}")
        except (json.JSONDecodeError, KeyError, ValueError, TypeError) as e:
            errors.append(f"{src_name}: parse error ({e})")

    raise StockError(code, " | ".join(errors))


# ============================================================
# Helpers
# ============================================================

def _safe_float(value: Any, default: float = 0.0) -> float:
    """Safely convert a value to float."""
    if value is None:
        return default
    try:
        val = float(value)
        return val if val == val else default
    except (ValueError, TypeError):
        return default


def _safe_int(value: Any, default: int = 0) -> int:
    """Safely convert a value to int."""
    if value is None:
        return default
    try:
        return int(float(value))
    except (ValueError, TypeError):
        return default


def _safe_str(value: Any, default: str = "") -> str:
    """Safely convert a value to string."""
    if value is None:
        return default
    s = str(value).strip()
    return s if s else default


def _safe_date(value: Any, default: str = "") -> str:
    """Convert East Money date value (int) to ISO date string."""
    if value is None or value == "-" or value == "":
        return default
    try:
        s = str(int(float(value)))
        if len(s) == 8:
            return f"{s[:4]}-{s[4:6]}-{s[6:8]}"
    except (ValueError, TypeError):
        pass
    return default
