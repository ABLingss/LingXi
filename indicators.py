"""
indicators.py — Pure Python technical indicator calculations for Stock JSON Clipper.

**No numpy/pandas** — uses only built-in math and statistics modules.
All functions operate on lists of float values (typically closing prices).

Indicators:
  - MA(N): Simple moving average over last N bars.
  - EMA(N): Exponential moving average (recursive).
  - MACD(12,26,9): DIF, DEA, BAR (histogram).
  - RSI(6/12): Relative Strength Index.
  - BOLL(20,2): Bollinger Bands (mid, upper, lower).
"""

import math
import statistics
from typing import Dict, List, Optional


def calc_ma(closes: List[float], period: int) -> Optional[float]:
    """Simple Moving Average of the last `period` closes.

    Args:
        closes: List of closing prices, oldest first.
        period: Lookback period (e.g. 5, 10, 20, 60).

    Returns:
        MA value, or None if insufficient data.
    """
    if len(closes) < period or period <= 0:
        return None
    return sum(closes[-period:]) / period


def calc_ema(data: List[float], span: int) -> List[float]:
    """Exponential Moving Average (recursive) over the entire series.

    Formula: ema = price * alpha + prev_ema * (1 - alpha)
             where alpha = 2 / (span + 1)

    The first EMA value is seeded with the simple average of the first `span` values.

    Args:
        data: List of float values, oldest first.
        span: EMA span (e.g. 12, 26).

    Returns:
        List of EMA values, same length as input. First (span-1) entries are 0.0.
    """
    if len(data) < span:
        return [0.0] * len(data)

    alpha = 2.0 / (span + 1.0)
    ema = [0.0] * len(data)

    # Seed: simple average of first `span` values
    ema[span - 1] = sum(data[:span]) / span

    # Recurse
    for i in range(span, len(data)):
        ema[i] = data[i] * alpha + ema[i - 1] * (1.0 - alpha)

    return ema


def calc_macd(
    closes: List[float],
    fast: int = 12,
    slow: int = 26,
    signal: int = 9,
) -> Dict[str, float]:
    """MACD indicator — returns the LATEST values only.

    Algorithm:
      DIF = EMA(fast) - EMA(slow)
      DEA = EMA(signal) of DIF
      BAR = 2 * (DIF - DEA)

    Args:
        closes: List of closing prices, oldest first.
        fast: Fast EMA period (default 12).
        slow: Slow EMA period (default 26).
        signal: Signal line period (default 9).

    Returns:
        Dict with keys 'dif', 'dea', 'bar'. Values default to 0.0 if insufficient data.
    """
    min_len = slow + signal
    if len(closes) < min_len:
        return {"dif": 0.0, "dea": 0.0, "bar": 0.0}

    ema_fast = calc_ema(closes, fast)
    ema_slow = calc_ema(closes, slow)

    # DIF = EMA(12) - EMA(26)
    dif_series = [ema_fast[i] - ema_slow[i] for i in range(len(closes))]

    # DEA = EMA(9) of DIF
    dea_series = calc_ema(dif_series, signal)

    dif = round(dif_series[-1], 4)
    dea = round(dea_series[-1], 4)
    bar = round(2.0 * (dif - dea), 4)

    return {"dif": dif, "dea": dea, "bar": bar}


def calc_rsi(closes: List[float], period: int = 14) -> Optional[float]:
    """Relative Strength Index (RSI) — returns the LATEST value only.

    Algorithm:
      RS = average_gain / average_loss
      RSI = 100 - 100 / (1 + RS)

    Uses Wilder's smoothing method for the initial average.

    Args:
        closes: List of closing prices, oldest first.
        period: RSI period (default 14; typical: 6 or 12).

    Returns:
        RSI value (0-100), or None if insufficient data.
    """
    if len(closes) < period + 1:
        return None

    gains = []
    losses = []
    for i in range(1, len(closes)):
        diff = closes[i] - closes[i - 1]
        if diff > 0:
            gains.append(diff)
            losses.append(0.0)
        else:
            gains.append(0.0)
            losses.append(abs(diff))

    # Initial average (simple mean of first `period` changes)
    avg_gain = sum(gains[:period]) / period
    avg_loss = sum(losses[:period]) / period

    # Wilder's smoothing for the rest
    for i in range(period, len(gains)):
        avg_gain = (avg_gain * (period - 1) + gains[i]) / period
        avg_loss = (avg_loss * (period - 1) + losses[i]) / period

    if avg_loss == 0.0:
        return 100.0 if avg_gain > 0 else 50.0

    rs = avg_gain / avg_loss
    rsi = 100.0 - (100.0 / (1.0 + rs))
    return round(rsi, 2)


def calc_boll(closes: List[float], period: int = 20, multiplier: float = 2.0) -> Dict[str, Optional[float]]:
    """Bollinger Bands — returns the LATEST values only.

    Algorithm:
      mid = MA(period)
      upper = mid + multiplier * stdev
      lower = mid - multiplier * stdev

    Args:
        closes: List of closing prices, oldest first.
        period: MA period (default 20).
        multiplier: Standard deviation multiplier (default 2.0).

    Returns:
        Dict with keys 'upper', 'mid', 'lower'. Values are None if insufficient data.
    """
    if len(closes) < period:
        return {"upper": None, "mid": None, "lower": None}

    window = closes[-period:]
    mid = sum(window) / period
    stdev = statistics.stdev(window) if len(window) >= 2 else 0.0

    return {
        "upper": round(mid + multiplier * stdev, 4),
        "mid": round(mid, 4),
        "lower": round(mid - multiplier * stdev, 4),
    }


def calc_all_indicators(closes: List[float]) -> Dict:
    """Calculate all standard indicators and return as a nested dict.

    Args:
        closes: List of closing prices, oldest first.

    Returns:
        Dict matching the 'indicators' section of the output JSON spec:
        {
          "ma5": float or None,
          "ma10": float or None,
          "ma20": float or None,
          "ma60": float or None,
          "macd": {"dif": float, "dea": float, "bar": float},
          "rsi_6": float or None,
          "rsi_12": float or None,
          "boll": {"upper": float or None, "mid": float or None, "lower": float or None}
        }
    """
    return {
        "ma5": calc_ma(closes, 5),
        "ma10": calc_ma(closes, 10),
        "ma20": calc_ma(closes, 20),
        "ma60": calc_ma(closes, 60),
        "macd": calc_macd(closes),
        "rsi_6": calc_rsi(closes, 6),
        "rsi_12": calc_rsi(closes, 12),
        "boll": calc_boll(closes, 20),
    }
