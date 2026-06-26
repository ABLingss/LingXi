"""
api.realtime — Real-time stock quote API (Sina JS interface).

Extracted and adapted from RollerCoaster (YQBaobao, GPL-3.0).
Provides live price + change% for stocks and futures.

Data sources:
  - Sina JS: hq.sinajs.cn (stocks) / w.sinajs.cn (futures, backup)

Stock symbol format: sh600036, sz000001
Futures symbol format: nf_AU0, nf_AU2508
"""

import random
import time
from decimal import Decimal
from typing import Any, Dict, List

import requests

HEADERS_SINA = {
    "Accept": "*/*",
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/135.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    "Connection": "keep-alive",
    "Referer": "https://finance.sina.com.cn/",
}


def _market_prefix(code: str) -> str:
    """Convert 6-digit code to Sina prefix: 000001 → sz000001, 600036 → sh600036."""
    if code.startswith(("60", "68")):
        return f"sh{code}"
    return f"sz{code}"


def fetch_realtime_quotes(codes: List[str], timeout: int = 5) -> Dict[str, Dict[str, Any]]:
    """Fetch real-time quotes for multiple stocks via Sina JS API.

    Args:
        codes: List of 6-digit stock codes (e.g. ['000001', '600036']).
        timeout: Request timeout in seconds.

    Returns:
        Dict mapping code → {current, percent, name, open, high, low, volume, ...}
        Percent is relative to yesterday's settlement price.

    Raises:
        RuntimeError: If the API request fails.
    """
    if not codes:
        return {}

    symbols = [_market_prefix(c) for c in codes]
    symbol_str = ",".join(symbols)
    rn = int(1234567890 * random.random() + 1) + int(9876543210 * random.random() + 1)

    url = f"https://hq.sinajs.cn/rn={rn}&list={symbol_str}"
    headers = dict(HEADERS_SINA)
    headers["host"] = "hq.sinajs.cn"

    resp = requests.get(url, headers=headers, timeout=timeout)
    if resp.status_code != 200:
        raise RuntimeError(f"Sina API returned {resp.status_code}: {resp.text[:200]}")

    raw_lines = resp.text.strip().split("\n")
    result: Dict[str, Dict[str, Any]] = {}

    for i, line in enumerate(raw_lines):
        if not line.strip():
            continue
        # Parse: var hq_str_sz000001="name,open,yest_close,current,high,low,..."
        try:
            # Extract values between quotes after '='
            eq_pos = line.index('="')
            values_str = line[eq_pos + 2:]
            if values_str.endswith('";'):
                values_str = values_str[:-2]
            elif values_str.endswith('"'):
                values_str = values_str[:-1]

            fields = values_str.split(",")
            if len(fields) < 32:
                continue

            name = fields[0]
            open_price = _safe_float(fields[1])
            yest_close = _safe_float(fields[2])
            current = _safe_float(fields[3])
            high = _safe_float(fields[4])
            low = _safe_float(fields[5])
            volume = int(_safe_float(fields[8]))
            amount = _safe_float(fields[9])

            # Calculate percent change
            if yest_close > 0:
                percent = float(
                    Decimal(str((current - yest_close) / yest_close * 100)).quantize(
                        Decimal("0.01")
                    )
                )
            else:
                percent = 0.0

            code = codes[i] if i < len(codes) else symbols[i]
            result[code] = {
                "name": name,
                "current": current,
                "percent": percent,
                "open": open_price,
                "high": high,
                "low": low,
                "yest_close": yest_close,
                "volume": volume,
                "amount": amount,
            }
        except (ValueError, IndexError):
            continue

    return result


def _safe_float(value: Any, default: float = 0.0) -> float:
    """Safely convert a value to float."""
    if value is None or value == "":
        return default
    try:
        return float(value)
    except (ValueError, TypeError):
        return default
