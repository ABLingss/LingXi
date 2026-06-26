"""
events.py — Signal event detection for the formula engine.

Detects historically significant events from indicator time series:
  - Golden cross / death cross (two series crossing)
  - Threshold breaches (series crossing a fixed threshold)
  - Trend direction (rising / falling / flat over recent window)

All functions receive series (List[Optional[float]]) and dates (List[str]),
and return lists of event dicts.  Events are factual — no buy/sell judgement.
"""

from typing import Any, Dict, List, Optional


def _last_valid(series: List[Optional[float]]) -> Optional[float]:
    """Return the last non-None value in the series."""
    for v in reversed(series):
        if v is not None:
            return v
    return None


def _last_valid_idx(series: List[Optional[float]]) -> int:
    """Return the index of the last non-None value."""
    for i in range(len(series) - 1, -1, -1):
        if series[i] is not None:
            return i
    return -1


# ============================================================
# Cross detection
# ============================================================

def detect_cross_events(
    series_a: List[Optional[float]],
    series_b: List[Optional[float]],
    dates: List[str],
    lookback: int = 250,
) -> List[Dict[str, Any]]:
    """Detect all golden cross and death cross events.

    Golden cross (金叉):   a[i-1] <= b[i-1]  AND  a[i] > b[i]
    Death cross (死叉):   a[i-1] >= b[i-1]  AND  a[i] < b[i]

    Args:
        series_a: "Fast" series (e.g. MA5).
        series_b: "Slow" series (e.g. MA20).
        dates: Date strings aligned with the series.
        lookback: Maximum number of events to return (most recent first).

    Returns:
        List of event dicts, most recent first:
        {date, type, direction_cn, value_a, value_b, gap, days_since}
    """
    n = min(len(series_a), len(series_b), len(dates))
    if n < 2:
        return []

    total_days = n - 1  # index of last bar
    events: List[Dict[str, Any]] = []

    for i in range(1, n):
        a_prev, a_curr = series_a[i - 1], series_a[i]
        b_prev, b_curr = series_b[i - 1], series_b[i]

        if a_prev is None or a_curr is None or b_prev is None or b_curr is None:
            continue

        event_type = None
        direction_cn = ""

        if a_prev <= b_prev and a_curr > b_curr:
            event_type = "golden_cross"
            direction_cn = "上穿"
        elif a_prev >= b_prev and a_curr < b_curr:
            event_type = "death_cross"
            direction_cn = "下穿"

        if event_type:
            events.append({
                "date": dates[i],
                "type": event_type,
                "direction_cn": direction_cn,
                "value_a": round(a_curr, 4),
                "value_b": round(b_curr, 4),
                "gap": round(a_curr - b_curr, 4),
                "days_since": total_days - i,
            })

    # Return most recent first, limited to lookback
    events.reverse()
    return events[:lookback]


# ============================================================
# Threshold breach detection
# ============================================================

def detect_threshold_breaches(
    series: List[Optional[float]],
    threshold: float,
    dates: List[str],
    operator: str,
    lookback: int = 250,
) -> List[Dict[str, Any]]:
    """Detect all threshold breach events.

    operator=">"  (indicator should be above threshold):
        breach_up   → value crosses above threshold
        breach_down → value crosses below threshold

    operator="<"  (indicator should be below threshold):
        breach_down → value crosses below threshold (moves away from desired)
        breach_up   → value crosses above threshold (moves away from desired)

    For ">" operator (want indicator > threshold):
      - breach_up   (向上突破): prev <= thresh AND curr > thresh  → positive
      - breach_down (向下跌破): prev >= thresh AND curr < thresh  → negative

    For "<" operator (want indicator < threshold):
      - breach_down (向下跌破): prev >= thresh AND curr < thresh  → positive
      - breach_up   (向上突破): prev <= thresh AND curr > thresh  → negative

    Args:
        series: Indicator values.
        threshold: Fixed threshold value.
        dates: Aligned date strings.
        operator: ">" or "<" (the comparison direction in the formula).
        lookback: Max events to return.

    Returns:
        List of event dicts, most recent first.
    """
    n = min(len(series), len(dates))
    if n < 2:
        return []

    total_days = n - 1
    events: List[Dict[str, Any]] = []

    for i in range(1, n):
        prev_val, curr_val = series[i - 1], series[i]
        if prev_val is None or curr_val is None:
            continue

        event_type = None
        direction_cn = ""

        if prev_val <= threshold and curr_val > threshold:
            event_type = "breach_up"
            direction_cn = "向上突破"
        elif prev_val >= threshold and curr_val < threshold:
            event_type = "breach_down"
            direction_cn = "向下跌破"

        if event_type:
            events.append({
                "date": dates[i],
                "type": event_type,
                "direction_cn": direction_cn,
                "value": round(curr_val, 4),
                "threshold": threshold,
                "gap": round(abs(curr_val - threshold), 4),
                "days_since": total_days - i,
            })

    events.reverse()
    return events[:lookback]


# ============================================================
# Trend detection
# ============================================================

def detect_trend(
    series: List[Optional[float]],
    window: int = 5,
) -> Dict[str, Any]:
    """Detect the trend direction over the most recent N valid values.

    Uses simple linear regression slope over the last `window` valid points.

    Args:
        series: Indicator values.
        window: Number of recent valid points to examine.

    Returns:
        {direction: "rising"|"falling"|"flat", slope: float, recent_values: [...]}
    """
    # Collect last `window` valid (index, value) pairs
    valid_pairs: List[tuple] = []
    for i in range(len(series) - 1, -1, -1):
        if series[i] is not None:
            valid_pairs.append((i, series[i]))
        if len(valid_pairs) >= window:
            break

    valid_pairs.reverse()  # chronological order

    recent_values = [v for _, v in valid_pairs]

    if len(valid_pairs) < 2:
        return {
            "direction": "flat",
            "slope": 0.0,
            "recent_values": recent_values,
        }

    # Simple linear regression: slope = (N*Σxy - Σx*Σy) / (N*Σx² - (Σx)²)
    # x = 0, 1, 2, ... N-1
    n_pts = len(valid_pairs)
    sum_x = (n_pts - 1) * n_pts / 2.0
    sum_y = sum(v for _, v in valid_pairs)
    sum_xy = sum(i * v for i, (_, v) in enumerate(valid_pairs))
    sum_x2 = sum(i * i for i in range(n_pts))

    denom = n_pts * sum_x2 - sum_x * sum_x
    if denom == 0:
        slope = 0.0
    else:
        slope = (n_pts * sum_xy - sum_x * sum_y) / denom

    # Determine direction
    # Use a small threshold relative to the average value
    avg_val = sum_y / n_pts if n_pts > 0 else 0.0
    threshold_pct = 0.001  # 0.1% of average per step
    if avg_val != 0 and abs(slope / avg_val) < threshold_pct:
        direction = "flat"
    elif slope > 0:
        direction = "rising"
    elif slope < 0:
        direction = "falling"
    else:
        direction = "flat"

    return {
        "direction": direction,
        "slope": round(slope, 6),
        "recent_values": [round(v, 4) for v in recent_values],
    }
