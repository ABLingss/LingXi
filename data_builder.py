"""
data_builder.py — JSON assembly for Stock JSON Clipper.

Combines K-line data, stock info, technical indicators, and statistical
summary into the final output JSON structure defined in spec §4.3.
"""

import json
import math
import statistics
from typing import Any, Dict, List, Optional

from indicators import calc_all_indicators


def build_summary(kline_data: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Build statistical summary from K-line data.

    Args:
        kline_data: List of OHLCV dicts from api_client.fetch_kline().

    Returns:
        Dict with keys:
          period_change, max_close, min_close, avg_volume, volatility.
    """
    if not kline_data:
        return {
            "period_change": 0.0,
            "max_close": 0.0,
            "min_close": 0.0,
            "avg_volume": 0,
            "volatility": 0.0,
        }

    closes = [bar["close"] for bar in kline_data]
    volumes = [bar["volume"] for bar in kline_data]

    first_close = closes[0]
    last_close = closes[-1]
    period_change = (
        ((last_close - first_close) / first_close * 100.0)
        if first_close != 0
        else 0.0
    )

    # Volatility: standard deviation of daily returns (close-to-close), annualized approx
    if len(closes) >= 2:
        returns = [
            (closes[i] - closes[i - 1]) / closes[i - 1] * 100.0
            for i in range(1, len(closes))
        ]
        volatility = statistics.stdev(returns) if len(returns) >= 2 else 0.0
        # Rough annualization: daily vol * sqrt(250)
        volatility = volatility * math.sqrt(250)
    else:
        volatility = 0.0

    return {
        "period_change": round(period_change, 2),
        "max_close": round(max(closes), 4),
        "min_close": round(min(closes), 4),
        "avg_volume": int(sum(volumes) / len(volumes)) if volumes else 0,
        "volatility": round(volatility, 2),
    }


def build_json(
    kline_data: List[Dict[str, Any]],
    stock_info: Dict[str, Any],
    code: str,
    period: str = "daily",
    count: int = 250,
) -> Dict[str, Any]:
    """Assemble the complete output JSON structure.

    Args:
        kline_data: List of OHLCV dicts from api_client.fetch_kline().
        stock_info: Stock info dict from api_client.fetch_stock_info().
        code: 6-digit stock code.
        period: 'daily', 'weekly', or 'monthly'.
        count: Number of bars requested.

    Returns:
        Full output dict matching the spec §4.3 JSON structure.
    """
    market_info = _determine_market_label(code)

    # Dates
    start_date = kline_data[0]["date"] if kline_data else ""
    end_date = kline_data[-1]["date"] if kline_data else ""

    # Technical indicators (on closing prices)
    closes = [bar["close"] for bar in kline_data]
    indicators = calc_all_indicators(closes)

    # Statistical summary
    summary = build_summary(kline_data)

    # Slim data: only keep date, open, high, low, close, volume
    slim_data = []
    for bar in kline_data:
        slim_data.append({
            "date": bar["date"],
            "open": bar["open"],
            "high": bar["high"],
            "low": bar["low"],
            "close": bar["close"],
            "volume": bar["volume"],
        })

    return {
        "meta": {
            "code": code,
            "name": stock_info.get("name", "未知"),
            "market": market_info,
            "industry": stock_info.get("industry", "未知"),
            "pe_ttm": stock_info.get("pe_ttm", -1.0),
            "total_mv": stock_info.get("total_mv", -1.0),
            "period": period,
            "data_count": len(kline_data),
            "start_date": start_date,
            "end_date": end_date,
        },
        "indicators": indicators,
        "summary": summary,
        "data": slim_data,
    }


def to_json_string(data: Dict[str, Any], indent: int = 2) -> str:
    """Serialize output dict to JSON string with ensure_ascii=False (Chinese support).

    Args:
        data: Output dict from build_json().
        indent: JSON indentation (default 2).

    Returns:
        Formatted JSON string.
    """
    return json.dumps(data, ensure_ascii=False, indent=indent, default=str)


def build_error_json(code: str, error_message: str) -> str:
    """Build an error JSON string for clipboard output when API fails.

    Args:
        code: Stock code that failed.
        error_message: Human-readable error description.

    Returns:
        JSON string with error details.
    """
    error_obj = {
        "error": True,
        "code": code,
        "message": error_message,
        "timestamp": "",
    }
    # Add timestamp via string formatting (avoiding Date.now() equivalent)
    import time
    error_obj["timestamp"] = time.strftime("%Y-%m-%d %H:%M:%S")
    return json.dumps(error_obj, ensure_ascii=False, indent=2)


def _determine_market_label(code: str) -> str:
    """Determine market label from stock code."""
    if code.startswith(("60", "68")):
        return "沪市"
    return "深市"
