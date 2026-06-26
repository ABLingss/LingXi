"""
series.py — Full-length indicator time-series computation for Stock JSON Clipper.

Zero dependencies (math + statistics stdlib only). Every output array has the
same length as the input klines; positions where there is insufficient data are
filled with None.

Indicators:
  - MA(N): Simple moving average over last N bars (full series).
  - EMA(N): Exponential moving average (recursive, full series).
  - MACD(12,26,9): DIF, DEA, BAR — full series.
  - RSI(6/12): Relative Strength Index with Wilder's smoothing — full series.
  - BOLL(20,2): Bollinger Bands (mid, upper, lower) — full series.
  - KDJ(9,3,3): Stochastic oscillator (uses 同花顺 SMA, NOT EMA).
  - vol_ma: Volume moving averages.
  - change_pct: Daily close-to-close return.
"""

import math
import statistics
from typing import Any, Dict, List, Optional


# ============================================================
# Internal helpers
# ============================================================

def _safe_div(a: float, b: float, default: float = 0.0) -> float:
    """Divide with zero-protection."""
    return a / b if b != 0.0 else default


# ============================================================
# SMA (同花顺 recursive SMA)
# ============================================================

def calc_sma_series(data: List[Optional[float]], n: int) -> List[Optional[float]]:
    """同花顺 SMA — recursive, NOT EMA.

    Formula: SMA[i] = ((n - 1) * SMA[i-1] + raw[i]) / n

    This is the SMA used in KDJ calculation (same as funcat SMASeries).
    The first SMA value is seeded with the raw value at the first valid position.

    Args:
        data: Input series (may contain None).
        n: Smoothing parameter.

    Returns:
        SMA series, same length as input. None where data is None or before seed.
    """
    result: List[Optional[float]] = [None] * len(data)

    if n <= 0:
        return result

    # Find first valid value to seed
    seed_idx = -1
    for i, v in enumerate(data):
        if v is not None:
            seed_idx = i
            result[i] = v  # Seed with first valid raw value
            break

    if seed_idx < 0:
        return result

    for i in range(seed_idx + 1, len(data)):
        if data[i] is not None and result[i - 1] is not None:
            result[i] = ((n - 1) * result[i - 1] + data[i]) / n
        # else: stays None

    return result


# ============================================================
# MA
# ============================================================

def calc_ma_series(data: List[Optional[float]], period: int) -> List[Optional[float]]:
    """Simple Moving Average — full series, None for first (period-1) positions.

    Args:
        data: Input series (may contain None).
        period: Lookback window.

    Returns:
        Same-length list. Window-sum approach.
    """
    n = len(data)
    result: List[Optional[float]] = [None] * n

    if period <= 0 or n < period:
        return result

    # Running window sum (ignoring None — treat None as breaking the sum)
    window_sum = 0.0
    window_count = 0
    for i in range(n):
        v = data[i]
        if v is not None:
            window_sum += v
            window_count += 1

        # Remove value that fell out of window
        drop_idx = i - period
        if drop_idx >= 0:
            drop_v = data[drop_idx]
            if drop_v is not None:
                window_sum -= drop_v
                window_count -= 1

        if window_count == period:
            result[i] = round(window_sum / period, 4)

    return result


# ============================================================
# EMA
# ============================================================

def calc_ema_series(data: List[Optional[float]], span: int) -> List[Optional[float]]:
    """Exponential Moving Average — full series.

    Seed: SMA of first `span` valid values.
    Formula: EMA[i] = val[i] * alpha + EMA[i-1] * (1 - alpha)
             alpha = 2 / (span + 1)

    Args:
        data: Input series (may contain None).
        span: EMA span (e.g. 12, 26).

    Returns:
        Same-length list. None for positions before seed.
    """
    n = len(data)
    result: List[Optional[float]] = [None] * n

    if span <= 0 or n < span:
        return result

    # Find first `span` valid values for seed
    valid_indices = [i for i, v in enumerate(data) if v is not None]
    if len(valid_indices) < span:
        return result

    seed_idx = valid_indices[span - 1]
    seed_sum = sum(data[valid_indices[i]] for i in range(span))  # type: ignore[arg-type]
    result[seed_idx] = round(seed_sum / span, 4)

    alpha = 2.0 / (span + 1.0)
    for i in range(seed_idx + 1, n):
        if data[i] is not None and result[i - 1] is not None:
            result[i] = round(data[i] * alpha + result[i - 1] * (1.0 - alpha), 4)
        # else: stays None

    return result


# ============================================================
# MACD
# ============================================================

def calc_macd_series(closes: List[Optional[float]], fast: int = 12,
                     slow: int = 26, signal: int = 9) -> Dict[str, List[Optional[float]]]:
    """MACD — full-series DIF, DEA, BAR.

    DIF = EMA(12) - EMA(26)
    DEA = EMA(9) of DIF
    BAR = 2 * (DIF - DEA)

    Returns:
        {"dif": [...], "dea": [...], "bar": [...]}
    """
    n = len(closes)
    empty: List[Optional[float]] = [None] * n

    ema_fast = calc_ema_series(closes, fast)
    ema_slow = calc_ema_series(closes, slow)

    # DIF = fast - slow
    dif: List[Optional[float]] = [None] * n
    for i in range(n):
        if ema_fast[i] is not None and ema_slow[i] is not None:
            dif[i] = round(ema_fast[i] - ema_slow[i], 4)

    # DEA = EMA(9) of DIF
    dea = calc_ema_series(dif, signal)

    # BAR = 2 * (DIF - DEA)
    bar: List[Optional[float]] = [None] * n
    for i in range(n):
        if dif[i] is not None and dea[i] is not None:
            bar[i] = round(2.0 * (dif[i] - dea[i]), 4)

    return {"dif": dif, "dea": dea, "bar": bar}


# ============================================================
# RSI (Wilder's smoothing)
# ============================================================

def calc_rsi_series(closes: List[Optional[float]], period: int = 14) -> List[Optional[float]]:
    """RSI — full series with Wilder's smoothing.

    First average: simple mean of first `period` changes.
    Subsequent: avg = (avg * (period-1) + new_val) / period

    Args:
        closes: Close price series (may contain None).
        period: RSI period (typically 6 or 12).

    Returns:
        Same-length list. None where insufficient data.
    """
    n = len(closes)
    result: List[Optional[float]] = [None] * n

    if period <= 0:
        return result

    # Collect gains and losses from valid adjacent pairs
    changes: List[Optional[float]] = [None] * n
    for i in range(1, n):
        if closes[i] is not None and closes[i - 1] is not None:
            changes[i] = closes[i] - closes[i - 1]  # type: ignore[operator]

    # Find first `period` valid changes
    valid_c = [i for i, v in enumerate(changes) if v is not None]
    if len(valid_c) < period:
        return result

    # Seed: simple mean of first `period` changes
    seed_indices = valid_c[:period]
    gain_sum = sum(max(changes[i], 0.0) for i in seed_indices)  # type: ignore[arg-type]
    loss_sum = sum(abs(min(changes[i], 0.0)) for i in seed_indices)  # type: ignore[arg-type]
    avg_gain = gain_sum / period
    avg_loss = loss_sum / period

    seed_i = seed_indices[-1]
    if avg_loss == 0.0:
        result[seed_i] = 100.0 if avg_gain > 0 else 50.0
    else:
        rs = avg_gain / avg_loss
        result[seed_i] = round(100.0 - (100.0 / (1.0 + rs)), 2)

    # Wilder's smoothing
    for i in range(seed_i + 1, n):
        if changes[i] is not None:
            diff = changes[i]
            gain = max(diff, 0.0)
            loss = abs(min(diff, 0.0))
            avg_gain = (avg_gain * (period - 1) + gain) / period
            avg_loss = (avg_loss * (period - 1) + loss) / period
            if avg_loss == 0.0:
                result[i] = 100.0 if avg_gain > 0 else 50.0
            else:
                rs = avg_gain / avg_loss
                result[i] = round(100.0 - (100.0 / (1.0 + rs)), 2)
        # else: stays None

    return result


# ============================================================
# BOLL
# ============================================================

def calc_boll_series(closes: List[Optional[float]], period: int = 20,
                     multiplier: float = 2.0) -> Dict[str, List[Optional[float]]]:
    """Bollinger Bands — full series, per-window stdev.

    mid  = MA(period)
    upper = mid + multiplier * stdev(window)
    lower = mid - multiplier * stdev(window)

    Returns:
        {"upper": [...], "mid": [...], "lower": [...]}
    """
    n = len(closes)
    empty_series: List[Optional[float]] = [None] * n
    upper: List[Optional[float]] = [None] * n
    mid: List[Optional[float]] = [None] * n
    lower: List[Optional[float]] = [None] * n

    if period <= 0 or n < period:
        return {"upper": upper, "mid": mid, "lower": lower}

    for i in range(period - 1, n):
        # Gather last `period` valid close values
        window = [closes[j] for j in range(i - period + 1, i + 1) if closes[j] is not None]
        if len(window) < period:
            continue
        m = sum(window) / period
        stdev = statistics.stdev(window) if len(window) >= 2 else 0.0
        mid[i] = round(m, 4)
        upper[i] = round(m + multiplier * stdev, 4)
        lower[i] = round(m - multiplier * stdev, 4)

    return {"upper": upper, "mid": mid, "lower": lower}


# ============================================================
# KDJ (with 同花顺 SMA)
# ============================================================

def calc_kdj_series(klines: List[Dict[str, Any]], n: int = 9,
                    m1: int = 3, m2: int = 3) -> Dict[str, List[Optional[float]]]:
    """KDJ stochastic oscillator — full series.

    Algorithm (matches funcat/indicators.py KDJ):
      RSV = (C - LLV(L, n)) / (HHV(H, n) - LLV(L, n)) * 100
      K   = SMA(RSV, 2*m1 - 1)    ← 同花顺 recursive SMA, NOT EMA
      D   = SMA(K,   2*m2 - 1)
      J   = 3*K - 2*D

    Args:
        klines: [{date, open, high, low, close, volume}, ...]
        n: RSV period (default 9).
        m1: K smoothing (default 3 → SMA period = 5).
        m2: D smoothing (default 3 → SMA period = 5).

    Returns:
        {"k": [...], "d": [...], "j": [...]}
    """
    length = len(klines)
    empty: List[Optional[float]] = [None] * length

    # Extract H, L, C
    highs: List[Optional[float]] = [bar.get("high") for bar in klines]
    lows: List[Optional[float]] = [bar.get("low") for bar in klines]
    closes: List[Optional[float]] = [bar.get("close") for bar in klines]

    # Compute RSV
    rsv: List[Optional[float]] = [None] * length
    for i in range(n - 1, length):
        window_h = [highs[j] for j in range(i - n + 1, i + 1) if highs[j] is not None]
        window_l = [lows[j] for j in range(i - n + 1, i + 1) if lows[j] is not None]
        if len(window_h) < n or len(window_l) < n or closes[i] is None:
            continue
        hhv_n = max(window_h)
        llv_n = min(window_l)
        denom = hhv_n - llv_n
        if denom == 0:
            rsv[i] = 50.0  # Flat range → middle
        else:
            rsv[i] = (closes[i] - llv_n) / denom * 100.0  # type: ignore[operator]

    # K = SMA(RSV, 2*m1 - 1)
    k_series = calc_sma_series(rsv, 2 * m1 - 1)

    # D = SMA(K, 2*m2 - 1)
    d_series = calc_sma_series(k_series, 2 * m2 - 1)

    # J = 3*K - 2*D
    j_series: List[Optional[float]] = [None] * length
    for i in range(length):
        if k_series[i] is not None and d_series[i] is not None:
            j_series[i] = round(3.0 * k_series[i] - 2.0 * d_series[i], 2)

    # Round K, D to 2 decimal places
    k_series = [round(v, 2) if v is not None else None for v in k_series]
    d_series = [round(v, 2) if v is not None else None for v in d_series]

    return {"k": k_series, "d": d_series, "j": j_series}


# ============================================================
# Daily change percent
# ============================================================

def calc_change_pct(closes: List[Optional[float]]) -> List[Optional[float]]:
    """Daily close-to-close percent change.

    change_pct[i] = (close[i] - close[i-1]) / close[i-1] * 100

    Returns:
        Same-length list. First element is None.
    """
    n = len(closes)
    result: List[Optional[float]] = [None] * n
    for i in range(1, n):
        if closes[i] is not None and closes[i - 1] is not None and closes[i - 1] != 0:
            result[i] = round((closes[i] - closes[i - 1]) / closes[i - 1] * 100.0, 2)  # type: ignore[operator]
    return result


# ============================================================
# Unified entry point
# ============================================================

def compute_all_series(klines: List[Dict[str, Any]]) -> Dict[str, List[Optional[float]]]:
    """Compute all indicator time series for a single stock.

    Every output array has the same length as `klines`.
    Positions with insufficient data are filled with None.

    Args:
        klines: [{date, open, high, low, close, volume}, ...], oldest first.

    Returns:
        Dict with 22 series keys:
          Raw:   c, o, h, l, v
          MA:     ma5, ma10, ma20, ma60
          MACD:   macd_dif, macd_dea, macd_bar
          RSI:    rsi6, rsi12
          BOLL:   boll_upper, boll_mid, boll_lower
          KDJ:    kdj_k, kdj_d, kdj_j
          Volume: vol_ma5, vol_ma20
          Other:  change_pct
    """
    n = len(klines)

    # ── Step 1: Extract raw series ──
    c: List[Optional[float]] = [bar.get("close") for bar in klines]
    o: List[Optional[float]] = [bar.get("open") for bar in klines]
    h: List[Optional[float]] = [bar.get("high") for bar in klines]
    l: List[Optional[float]] = [bar.get("low") for bar in klines]
    v: List[Optional[float]] = [float(bar.get("volume", 0) or 0) for bar in klines]

    # ── Step 2: MA series ──
    ma5 = calc_ma_series(c, 5)
    ma10 = calc_ma_series(c, 10)
    ma20 = calc_ma_series(c, 20)
    ma60 = calc_ma_series(c, 60)

    # ── Step 3-4: MACD series ──
    macd = calc_macd_series(c, fast=12, slow=26, signal=9)

    # ── Step 5: RSI series ──
    rsi6 = calc_rsi_series(c, 6)
    rsi12 = calc_rsi_series(c, 12)

    # ── Step 6: BOLL series ──
    boll = calc_boll_series(c, period=20, multiplier=2.0)

    # ── Step 7: KDJ series ──
    kdj = calc_kdj_series(klines, n=9, m1=3, m2=3)

    # ── Step 8: Volume MA ──
    vol_ma5 = calc_ma_series(v, 5)
    vol_ma20 = calc_ma_series(v, 20)

    # ── Step 9: Change % ──
    change_pct = calc_change_pct(c)

    return {
        # Raw
        "c": c, "o": o, "h": h, "l": l, "v": v,
        # MA
        "ma5": ma5, "ma10": ma10, "ma20": ma20, "ma60": ma60,
        # MACD
        "macd_dif": macd["dif"], "macd_dea": macd["dea"], "macd_bar": macd["bar"],
        # RSI
        "rsi6": rsi6, "rsi12": rsi12,
        # BOLL
        "boll_upper": boll["upper"], "boll_mid": boll["mid"], "boll_lower": boll["lower"],
        # KDJ
        "kdj_k": kdj["k"], "kdj_d": kdj["d"], "kdj_j": kdj["j"],
        # Volume MA
        "vol_ma5": vol_ma5, "vol_ma20": vol_ma20,
        # Change %
        "change_pct": change_pct,
    }
