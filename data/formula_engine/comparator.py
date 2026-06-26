"""
comparator.py — Multi-stock comparison table builder.

Builds two types of comparison data:
  1. Indicator comparison rows (latest price, change %, MA deviation,
     MACD status, RSI, volatility) with best/worst highlighting.
  2. Formula element per-stock comparison (when formula is provided).

Note: Turnover rate (换手率) is NOT included because stock-api does not
return shares outstanding, making it impossible to compute accurately.
"""

import math
from typing import Any, Dict, List, Optional


def _last_valid(series: List[Optional[float]]) -> Optional[float]:
    """Return the last non-None value."""
    for v in reversed(series):
        if v is not None:
            return v
    return None


def _get_stock_info(stock_info_map, code: str):
    """Safely get stock info dict."""
    return stock_info_map.get(code, {})


def build_comparison_table(
    series_map: Dict[str, Dict[str, List[Optional[float]]]],
    stock_info_map: Dict[str, Dict[str, Any]],
    klines_map: Optional[Dict[str, List[Dict[str, Any]]]] = None,
) -> Dict[str, Any]:
    """Build a multi-stock indicator comparison table.

    Args:
        series_map: code → {"c": [...], "ma5": [...], ...} from compute_all_series().
        stock_info_map: code → {name, market, ...}.
        klines_map: code → [{date, open, high, low, close, volume}, ...] (optional).

    Returns:
        Multi-stock comparison dict:
          {headers: [...], rows: [{label, unit, values: [{code, val, highlight}]}]}
    """
    codes = list(series_map.keys())
    if not codes:
        return {"headers": [], "rows": []}

    headers = ["指标"] + [
        stock_info_map.get(c, {}).get("name", c) for c in codes
    ]
    rows: List[Dict[str, Any]] = []

    # ── Row definitions: (label, unit, extractor_fn) ──
    def _latest(ser_key):
        def fn(code):
            s = series_map.get(code, {}).get(ser_key, [])
            return _last_valid(s)
        return fn

    def _pct_change(ser_key):
        """Compute period change from series."""
        def fn(code):
            s = series_map.get(code, {}).get(ser_key, [])
            first = None
            last = None
            for v in s:
                if v is not None:
                    if first is None:
                        first = v
                    last = v
            if first and last and first != 0:
                return round((last - first) / first * 100, 2)
            return None
        return fn

    def _ma_deviation(ma_key):
        """MA deviation from close: (ma - close) / close * 100."""
        def fn(code):
            ser = series_map.get(code, {})
            c = _last_valid(ser.get("c", []))
            ma = _last_valid(ser.get(ma_key, []))
            if c and ma and c != 0:
                return round((ma - c) / c * 100, 2)
            return None
        return fn

    def _macd_status(code):
        """MACD status: DIF vs DEA + BAR sign."""
        ser = series_map.get(code, {})
        dif = _last_valid(ser.get("macd_dif", []))
        dea = _last_valid(ser.get("macd_dea", []))
        bar = _last_valid(ser.get("macd_bar", []))
        if dif is None or dea is None or bar is None:
            return None
        parts = []
        parts.append("多头" if dif > dea else "空头")
        parts.append("红柱" if bar > 0 else "绿柱")
        return " | ".join(parts)

    def _rsi_status(code):
        """RSI(6) category."""
        r = _last_valid(series_map.get(code, {}).get("rsi6", []))
        if r is None:
            return None
        if r > 80:
            return f"{r:.1f} 超买"
        elif r < 20:
            return f"{r:.1f} 超卖"
        elif r > 50:
            return f"{r:.1f} 偏强"
        else:
            return f"{r:.1f} 偏弱"

    def _volatility(code):
        """Annualized volatility from change_pct series."""
        s = series_map.get(code, {}).get("change_pct", [])
        vals = [v for v in s if v is not None]
        if len(vals) < 2:
            return None
        import statistics
        stdev = statistics.stdev(vals)
        return round(stdev * math.sqrt(250), 2)  # Annualized

    row_defs = [
        ("最新价", "元", _latest("c")),
        ("区间涨跌幅", "%", _pct_change("c")),
        ("MA5偏离度", "%", _ma_deviation("ma5")),
        ("MA20偏离度", "%", _ma_deviation("ma20")),
        ("MACD状态", None, _macd_status),
        ("RSI(6)", None, _rsi_status),
        ("年化波动率", "%", _volatility),
    ]

    for label, unit, fn in row_defs:
        values: List[Dict[str, Any]] = []
        for code in codes:
            try:
                val = fn(code)
            except Exception:
                val = None
            values.append({"code": code, "val": val, "highlight": None})

        # Determine best/worst for numeric values
        numeric_vals = [(i, v["val"]) for i, v in enumerate(values) if isinstance(v["val"], (int, float))]
        if len(numeric_vals) >= 2:
            # For "MACD状态" and other categorical — skip best/worst
            if unit is not None:
                # For change%, volatility — higher is not always "best" — we mark extremes
                sorted_vals = sorted(numeric_vals, key=lambda x: x[1])
                best_idx = sorted_vals[-1][0]
                worst_idx = sorted_vals[0][0]
                values[best_idx]["highlight"] = "best"
                values[worst_idx]["highlight"] = "worst"

        rows.append({
            "label": label,
            "unit": unit,
            "values": values,
        })

    return {
        "headers": headers,
        "rows": rows,
    }


def build_formula_comparison(
    elements: List[Dict[str, Any]],
    series_map: Dict[str, Dict[str, List[Optional[float]]]],
    stock_info_map: Dict[str, Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """Build per-element, per-stock comparison for a formula.

    Args:
        elements: Parsed formula elements list.
        series_map: code → series dict.
        stock_info_map: code → stock info.

    Returns:
        List of {element_label, stocks: [{code, state, highlight}]}
    """
    codes = list(series_map.keys())
    result: List[Dict[str, Any]] = []

    for el in elements:
        el_dict = el.__dict__ if hasattr(el, '__dict__') else el
        etype = el_dict.get("element_type", "?")
        label = el_dict.get("label_cn", "?")

        stocks_info: List[Dict[str, Any]] = []

        for code in codes:
            state = ""
            highlight = None

            if etype == "cross":
                # Check if currently in golden cross state
                variables = el_dict.get("variables", [])
                if len(variables) >= 2:
                    s_a = _last_valid(series_map.get(code, {}).get(variables[0], []))
                    s_b = _last_valid(series_map.get(code, {}).get(variables[1], []))
                    if s_a is not None and s_b is not None:
                        if s_a > s_b:
                            state = f"金叉状态({variables[0]}>{variables[1]})"
                            highlight = "golden"
                        else:
                            state = f"未金叉({variables[0]}<{variables[1]})"
                    else:
                        state = "数据不足"
                else:
                    state = "无法判断"

            elif etype == "compare":
                variables = el_dict.get("variables", [])
                threshold = el_dict.get("threshold")
                operator = el_dict.get("op", "gt")
                if variables and threshold is not None:
                    s = _last_valid(series_map.get(code, {}).get(variables[0], []))
                    if s is not None:
                        if operator in ("gt", "gte"):
                            if s >= threshold:
                                state = f"满足({s:.2f})"
                                highlight = "met"
                            else:
                                gap = threshold - s
                                if gap < threshold * 0.1:  # Within 10%
                                    state = f"接近({s:.2f},差{gap:.2f})"
                                    highlight = "close"
                                else:
                                    state = f"不满足({s:.2f},差{gap:.2f})"
                        elif operator in ("lt", "lte"):
                            if s <= threshold:
                                state = f"满足({s:.2f})"
                                highlight = "met"
                            else:
                                gap = s - threshold
                                if gap < threshold * 0.1:
                                    state = f"接近({s:.2f},差{gap:.2f})"
                                    highlight = "close"
                                else:
                                    state = f"不满足({s:.2f},差{gap:.2f})"
                        else:
                            state = f"{s:.2f} (阈值{threshold})"
                    else:
                        state = "数据不足"
                else:
                    state = "无法评估"

            elif etype == "statistical":
                fn_name = el_dict.get("function_name", "")
                param = el_dict.get("param")
                variables = el_dict.get("variables", [])
                if variables and param:
                    s = series_map.get(code, {}).get(variables[0], [])
                    vals = [v for v in s[-param:] if v is not None]
                    if fn_name == "HHV":
                        state = f"{max(vals):.2f}" if vals else "数据不足"
                    elif fn_name == "LLV":
                        state = f"{min(vals):.2f}" if vals else "数据不足"
                    elif fn_name == "REF" and param < len(s):
                        v = s[-1 - param]
                        state = f"{v:.2f}" if v is not None else "数据不足"
                    elif fn_name == "SUM":
                        state = f"{sum(vals):.2f}" if vals else "数据不足"
                    else:
                        state = f"{fn_name}={len(vals)}" if vals else "数据不足"
                else:
                    state = "参数不足"

            elif etype == "opaque":
                state = "需LLM自行分析"

            stocks_info.append({
                "code": code,
                "state": state,
                "highlight": highlight,
            })

        result.append({
            "element_label": label,
            "stocks": stocks_info,
        })

    return result
