"""
api_client.py — East Money (东方财富) public API wrapper for Stock JSON Clipper.

Data sources (sole — see spec §4.2):
  - K-line: http://push2his.eastmoney.com/api/qt/stock/kline/get
  - Stock info: http://push2.eastmoney.com/api/qt/stock/get

All functions return parsed dicts/lists or raise StockError on failure.
"""

import json
import time
from typing import Any, Dict, List, Optional, Tuple

import requests


# --- Constants ---
KLINE_URL = "http://push2his.eastmoney.com/api/qt/stock/kline/get"
STOCK_INFO_URL = "http://push2.eastmoney.com/api/qt/stock/get"

# Period → klt parameter mapping
PERIOD_MAP = {
    "daily": 101,
    "weekly": 102,
    "monthly": 103,
}

# Default request timeout (seconds)
DEFAULT_TIMEOUT = 5

# User-agent to avoid being blocked
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Referer": "http://quote.eastmoney.com/",
}


class StockError(Exception):
    """Raised when stock data cannot be fetched (invalid code, timeout, etc.)."""

    def __init__(self, code: str, message: str) -> None:
        self.code = code
        self.message = message
        super().__init__(f"[{code}] {message}")


# --- Market detection ---
def determine_market(code: str) -> Dict[str, str]:
    """Determine market (沪市/深市) and secid prefix for a 6-digit A-share code.

    Rules:
      - 60xxxx, 688xxx → 沪市 (Shanghai), secid prefix "1"
      - 00xxxx, 30xxxx, 002xxx, 003xxx → 深市 (Shenzhen), secid prefix "0"

    Args:
        code: 6-digit stock code string.

    Returns:
        Dict with keys: 'market' ('沪市'|'深市'), 'secid_pre' ('1'|'0').
    """
    if code.startswith(("60", "68")):
        return {"market": "沪市", "secid_pre": "1"}
    else:
        # 00xxxx, 30xxxx (including 002, 003 SME/GEM varieties)
        return {"market": "深市", "secid_pre": "0"}


def make_secid(code: str, use_kline_prefix: bool = True) -> str:
    """Build East Money secid parameter from 6-digit stock code.

    Args:
        code: 6-digit stock code.
        use_kline_prefix: If True, use K-line API prefix (1. for SH, 0. for SZ).
                          Stock info API also uses same prefix system.

    Returns:
        secid string like "1.000001" or "0.000001".
    """
    pre = determine_market(code)["secid_pre"]
    return f"{pre}.{code}"


# --- K-line API ---
def fetch_kline(
    code: str,
    period: str = "daily",
    count: int = 250,
    timeout: int = DEFAULT_TIMEOUT,
) -> List[Dict[str, Any]]:
    """Fetch historical K-line data from East Money.

    Args:
        code: 6-digit stock code (e.g. '000001').
        period: 'daily', 'weekly', or 'monthly'.
        count: Number of bars to fetch (default 250; set large for full history).
        timeout: Request timeout in seconds.

    Returns:
        List of OHLCV dicts, each with keys:
          date, open, high, low, close, volume, amount, amplitude, change_pct, change, turnover.
        Ordered oldest-first.

    Raises:
        StockError: On network error, invalid response, or empty data.
    """
    klt = PERIOD_MAP.get(period, 101)
    secid = make_secid(code, use_kline_prefix=True)

    params: Dict[str, Any] = {
        "secid": secid,
        "klt": klt,
        "fqt": 1,  # 前复权 (forward-adjusted)
        "lmt": count,
        "fields1": "f1,f2,f3,f4,f5,f6",
        "fields2": "f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61",
        "end": "20500101",  # always fetch up to latest
        "ut": "fa5fd1943c7b386f172d6893dbfc10f1",  # utility token (public)
    }

    try:
        resp = requests.get(KLINE_URL, params=params, headers=HEADERS, timeout=timeout)
        resp.raise_for_status()
    except requests.Timeout:
        raise StockError(code, "数据拉取超时，请检查网络")
    except requests.ConnectionError:
        raise StockError(code, "网络连接失败，请检查网络")
    except requests.RequestException as e:
        raise StockError(code, f"API请求失败: {e}")

    try:
        raw = resp.json()
    except json.JSONDecodeError:
        raise StockError(code, "API返回数据格式异常")

    # Check for API-level errors
    if raw.get("rc") != 0 and raw.get("data") is None:
        raise StockError(code, "股票代码无效或已退市")

    data_block = raw.get("data")
    if data_block is None:
        raise StockError(code, "未获取到K线数据")

    klines_raw = data_block.get("klines", [])
    if not klines_raw:
        raise StockError(code, "该股票无K线数据")

    # Parse K-line strings
    # Format: "日期,开盘,收盘,最高,最低,成交量,成交额,振幅,涨跌幅,涨跌额,换手率"
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


# --- Stock info API ---
def fetch_stock_info(
    code: str,
    timeout: int = DEFAULT_TIMEOUT,
) -> Dict[str, Any]:
    """Fetch stock basic info (name, industry, PE, market cap, etc.) from East Money.

    Args:
        code: 6-digit stock code.
        timeout: Request timeout in seconds.

    Returns:
        Dict with keys: name, industry, pe_ttm, total_mv, float_mv, list_date.

    Raises:
        StockError: On network error or invalid response.
    """
    secid = make_secid(code, use_kline_prefix=True)

    params: Dict[str, Any] = {
        "secid": secid,
        "fields": "f57,f58,f116,f162,f167,f168",
        "ut": "fa5fd1943c7b386f172d6893dbfc10f1",
    }

    try:
        resp = requests.get(
            STOCK_INFO_URL, params=params, headers=HEADERS, timeout=timeout
        )
        resp.raise_for_status()
    except requests.Timeout:
        raise StockError(code, "获取股票信息超时，请检查网络")
    except requests.ConnectionError:
        raise StockError(code, "网络连接失败，请检查网络")
    except requests.RequestException as e:
        raise StockError(code, f"API请求失败: {e}")

    try:
        raw = resp.json()
    except json.JSONDecodeError:
        raise StockError(code, "股票信息API返回数据格式异常")

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


# --- Helpers ---
def _safe_float(value: Any, default: float = 0.0) -> float:
    """Safely convert a value to float, returning default on failure."""
    if value is None:
        return default
    try:
        val = float(value)
        return val if val == val else default  # NaN check
    except (ValueError, TypeError):
        return default


def _safe_int(value: Any, default: int = 0) -> int:
    """Safely convert a value to int, returning default on failure."""
    if value is None:
        return default
    try:
        return int(float(value))
    except (ValueError, TypeError):
        return default


def _safe_str(value: Any, default: str = "") -> str:
    """Safely convert a value to string, returning default on failure."""
    if value is None:
        return default
    return str(value).strip() or default


def _safe_date(value: Any, default: str = "") -> str:
    """Convert East Money date value (int like 20260619) to ISO string."""
    if value is None or value == "-" or value == "":
        return default
    s = str(int(float(value)))
    if len(s) == 8:
        return f"{s[:4]}-{s[4:6]}-{s[6:8]}"
    return s
