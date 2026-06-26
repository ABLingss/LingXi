"""
elements.py — TDX formula parser and element assembler.

Parses a TDX formula string into a list of FormulaElement objects.
Each element is classified as one of:
  - cross:       CROSS(A, B) — golden/death cross detection
  - compare:     X OP Y or X OP value — comparison against threshold
  - statistical: HHV/LLV/REF/SUM with pure-variable args — engine computes
  - opaque:      Nested conditions, complex expressions — LLM's job

Design rule:
  COUNT/EVERY/IF with a nested condition as the first argument → opaque.
  The engine does NOT recursively parse conditions; the LLM evaluates them
  against the provided series.
"""

import re
from typing import Any, Dict, List, Optional, Tuple

from data.formula_engine.constants import (
    CN_TO_EN,
    ALIAS_TO_CANONICAL,
    FUNCTION_NAMES,
    COMPARE_OPS,
    COMPARE_OP_CN,
    LOGIC_OPS,
    normalize_formula,
    resolve_variable,
    make_cross_label,
    make_compare_label,
    make_statistical_label,
    make_cross_status,
    make_compare_status,
)
from data.formula_engine.events import (
    detect_cross_events,
    detect_threshold_breaches,
    detect_trend,
)


# ============================================================
# Paren-aware split by logical operators
# ============================================================

def _split_by_logic(text: str) -> List[Tuple[str, Optional[str]]]:
    """Split formula by & / | / AND / OR at parenthesis depth 0.

    Returns:
        List of (sub_expression, logic_op) tuples.
        logic_op is None for the last element.
    """
    fragments: List[Tuple[str, Optional[str]]] = []
    depth = 0
    start = 0
    current_logic: Optional[str] = None

    i = 0
    while i < len(text):
        ch = text[i]
        if ch == '(':
            depth += 1
            i += 1
        elif ch == ')':
            depth -= 1
            i += 1
        elif depth == 0:
            # Check for & or |
            if ch in ('&', '|'):
                frag = text[start:i].strip()
                if frag:
                    fragments.append((frag, ch))
                start = i + 1
                i += 1
            else:
                i += 1
        else:
            i += 1

    # Last fragment (strip trailing &/| from split)
    last = text[start:].strip()
    if last:
        fragments.append((last, None))

    return fragments


# ============================================================
# Pattern matchers
# ============================================================

def _find_matching_paren(text: str, start: int) -> int:
    """Find the closing paren that matches text[start] (must be '(')."""
    depth = 0
    for i in range(start, len(text)):
        if text[i] == '(':
            depth += 1
        elif text[i] == ')':
            depth -= 1
            if depth == 0:
                return i
    return -1


def _split_args(text: str, start: int, end: int) -> List[str]:
    """Split comma-separated arguments inside parentheses, at depth 0 within the parens.

    text[start] is '(' and text[end] is the matching ')'.
    Returns list of argument strings (stripped).
    """
    inner = text[start + 1:end]
    args: List[str] = []
    depth = 0
    current_start = 0
    for i, ch in enumerate(inner):
        if ch == '(':
            depth += 1
        elif ch == ')':
            depth -= 1
        elif ch == ',' and depth == 0:
            args.append(inner[current_start:i].strip())
            current_start = i + 1
    args.append(inner[current_start:].strip())
    return args


def _has_comparison_op(expr: str) -> bool:
    """Check if expression contains a comparison operator (at depth 0)."""
    depth = 0
    for i, ch in enumerate(expr):
        if ch == '(':
            depth += 1
        elif ch == ')':
            depth -= 1
        elif depth == 0:
            # Look for >=, <=, !=, ==, =, >, <
            sub = expr[i:]
            for op in (">=", "<=", "!=", "==", "=", ">", "<"):
                if sub.startswith(op):
                    return True
    return False


def _contains_nested_function(expr: str) -> bool:
    """Check if expr contains a function call inside parentheses that's not
    just a pure variable reference. Used to detect COUNT(C>MA(C,20),10)
    vs COUNT(C,10)."""
    # Find all top-level parenthesized groups
    depth = 0
    for i, ch in enumerate(expr):
        if ch == '(':
            if depth == 0:
                closer = _find_matching_paren(expr, i)
                if closer < 0:
                    continue
                inner = expr[i + 1:closer]
                # If inner contains comparison operators → nested condition
                if _has_comparison_op(inner):
                    return True
                # If inner contains another function call
                inner_upper = inner.upper()
                for fn in FUNCTION_NAMES:
                    if re.search(r'\b' + fn + r'\s*\(', inner_upper):
                        return True
            depth += 1
        elif ch == ')':
            depth -= 1
    return False


# ---- MATCH CROSS ----

CROSS_RE = re.compile(r'CROSS\s*\(', re.IGNORECASE)


def _match_cross(expr: str) -> Optional[Dict[str, Any]]:
    """Try to match CROSS(X, Y) pattern.

    Returns dict with {a, b, variables} or None.
    """
    m = CROSS_RE.search(expr)
    if not m:
        return None

    paren_start = m.end() - 1  # position of '('
    paren_end = _find_matching_paren(expr, paren_start)
    if paren_end < 0:
        return None

    # Verify this CROSS covers the full expression (or is the main element)
    args = _split_args(expr, paren_start, paren_end)
    if len(args) != 2:
        return None

    # Check for nested CROSS → opaque
    if CROSS_RE.search(args[0]) or CROSS_RE.search(args[1]):
        return None

    a_expr = args[0]
    b_expr = args[1]
    variables = resolve_variable(expr)

    return {
        "element_type": "cross",
        "a": a_expr,
        "b": b_expr,
        "variables": variables,
        "raw": expr,
        "label_cn": make_cross_label(a_expr, b_expr),
    }


# ---- MATCH COMPARE ----

COMPARE_RE = re.compile(
    r'([A-Za-z0-9_.()]+)\s*(>=|<=|!=|==|=|<|>)\s*([A-Za-z0-9_.()]+)'
)


def _match_compare(expr: str) -> Optional[Dict[str, Any]]:
    """Try to match X OP Y or X OP numeric_value pattern.

    Returns dict with {left, op, op_cn, right, threshold, variables} or None.
    """
    m = COMPARE_RE.search(expr)
    if not m:
        return None

    left = m.group(1).strip()
    op_raw = m.group(2).strip()
    right = m.group(3).strip()

    op_key = COMPARE_OPS.get(op_raw, op_raw)

    # Try to parse right as a number (threshold)
    threshold: Optional[float] = None
    try:
        threshold = float(right)
    except ValueError:
        pass

    variables = resolve_variable(expr)

    if not variables:
        return None  # Nothing we can compute

    return {
        "element_type": "compare",
        "left": left,
        "op": op_key,
        "op_cn": COMPARE_OP_CN.get(op_key, op_raw),
        "right": right,
        "threshold": threshold,
        "variables": variables,
        "raw": expr,
        "label_cn": make_compare_label(left, COMPARE_OP_CN.get(op_key, op_key), right),
    }


# ---- MATCH STATISTICAL ----

STAT_FN_RE = re.compile(
    r'(HHV|LLV|COUNT|EVERY|REF|SUM|ABS|MAX|MIN)\s*\(',
    re.IGNORECASE
)


def _match_statistical(expr: str) -> Optional[Dict[str, Any]]:
    """Try to match a statistical function: HHV/LLV/REF/SUM/COUNT/EVERY/ABS/MAX/MIN.

    V1 boundary: if the first argument contains a comparison operator or
    nested function call → return opaque instead.

    Returns dict or None.
    """
    m = STAT_FN_RE.search(expr)
    if not m:
        return None

    fn_name = m.group(1).upper()
    paren_start = m.end() - 1
    paren_end = _find_matching_paren(expr, paren_start)
    if paren_end < 0:
        return None

    args = _split_args(expr, paren_start, paren_end)
    if not args:
        return None

    # Check for nested conditions in first argument → opaque
    if fn_name in ("COUNT", "EVERY", "IF", "IIF"):
        if _has_comparison_op(args[0]) or _contains_nested_function(args[0]):
            # Return as opaque — engine can't evaluate nested conditions
            variables = resolve_variable(expr)
            return {
                "element_type": "opaque",
                "raw": expr,
                "variables": variables,
                "label_cn": f"复杂表达式: {expr}",
                "reason": "nested_condition",
            }

    # IF/IIF with comparison → opaque
    if fn_name in ("IF", "IIF"):
        if any(_has_comparison_op(a) for a in args):
            variables = resolve_variable(expr)
            return {
                "element_type": "opaque",
                "raw": expr,
                "variables": variables,
                "label_cn": f"复杂表达式: {expr}",
                "reason": "conditional_branch",
            }

    variables = resolve_variable(expr)

    # Extract parameter (second argument for most statistical functions)
    param: Optional[int] = None
    if fn_name in ("HHV", "LLV", "COUNT", "EVERY", "SUM") and len(args) >= 2:
        try:
            param = int(args[1])
        except ValueError:
            param = None
    elif fn_name == "REF" and len(args) >= 2:
        try:
            param = int(args[1])
        except ValueError:
            param = None

    label_cn = make_statistical_label(fn_name, args[0], param or 0)

    return {
        "element_type": "statistical",
        "function_name": fn_name,
        "args": args,
        "param": param,
        "variables": variables,
        "raw": expr,
        "label_cn": label_cn,
    }


# ============================================================
# Formula element assembly
# ============================================================

def _compute_current_state(
    element: Dict[str, Any],
    series: Dict[str, List[Optional[float]]],
    dates: List[str],
) -> Dict[str, Any]:
    """Fill in the 'current' field of a formula element with factual data.

    Does NOT make buy/sell judgements — only describes what the data shows.
    """
    etype = element["element_type"]
    variables = element.get("variables", [])

    if etype == "cross":
        return _current_cross(element, series, dates)
    elif etype == "compare":
        return _current_compare(element, series, dates)
    elif etype == "statistical":
        return _current_statistical(element, series, dates)
    else:
        # opaque
        return {
            "description_cn": "引擎无法自动评估此表达式，请LLM基于提供的序列数据自行分析。",
            "details": {},
        }


def _current_cross(
    element: Dict[str, Any],
    series: Dict[str, List[Optional[float]]],
    dates: List[str],
) -> Dict[str, Any]:
    """Compute current state for a cross element."""
    variables = element["variables"]
    if len(variables) < 2:
        return {"description_cn": "无法确定交叉双方", "details": {}}

    # Find two main series keys (first two variables)
    key_a, key_b = variables[0], variables[1]
    series_a = series.get(key_a, [])
    series_b = series.get(key_b, [])

    # Latest values
    import itertools
    latest_a = None
    latest_b = None
    for i in range(len(series_a) - 1, -1, -1):
        if latest_a is None and series_a[i] is not None:
            latest_a = series_a[i]
        if latest_b is None and series_b[i] is not None:
            latest_b = series_b[i]
        if latest_a is not None and latest_b is not None:
            break

    if latest_a is None or latest_b is None:
        return {"description_cn": "数据不足，无法判断交叉状态", "details": {}}

    relation = "above" if latest_a > latest_b else "below" if latest_a < latest_b else "equal"

    # Count consecutive days in current relation
    consecutive = 0
    for i in range(len(series_a) - 1, -1, -1):
        if series_a[i] is not None and series_b[i] is not None:
            cur_rel = "above" if series_a[i] > series_b[i] else "below" if series_a[i] < series_b[i] else "equal"
            if cur_rel == relation:
                consecutive += 1
            else:
                break
        else:
            break

    key_a_cn = element.get("a", key_a)
    key_b_cn = element.get("b", key_b)

    desc = make_cross_status(key_a_cn, latest_a, key_b_cn, latest_b, relation, consecutive)

    return {
        "description_cn": desc,
        "details": {
            f"{key_a}_latest": latest_a,
            f"{key_b}_latest": latest_b,
            "relation": relation,
            "consecutive_days": consecutive,
        },
    }


def _current_compare(
    element: Dict[str, Any],
    series: Dict[str, List[Optional[float]]],
    dates: List[str],
) -> Dict[str, Any]:
    """Compute current state for a compare element."""
    variables = element.get("variables", [])
    threshold = element.get("threshold")
    operator = element.get("op", "gt")

    if not variables or threshold is None:
        return {"description_cn": "无法评估比较条件（缺少指标或阈值）", "details": {}}

    # Use the first variable
    key = variables[0]
    ser = series.get(key, [])

    # Find latest value
    latest_val = None
    for v in reversed(ser):
        if v is not None:
            latest_val = v
            break

    if latest_val is None:
        return {"description_cn": f"{key}数据不足", "details": {}}

    # Determine relation to threshold
    if operator in ("gt", "gte"):
        relation = "above" if latest_val >= threshold else "below"
    elif operator in ("lt", "lte"):
        relation = "below" if latest_val <= threshold else "above"
    else:
        relation = "unknown"

    gap = abs(latest_val - threshold)

    # Trend
    trend_info = detect_trend(ser, window=5)
    recent_5d = trend_info.get("recent_values", [])

    desc = make_compare_status(key, latest_val, threshold, operator,
                               trend_info["direction"], recent_5d)

    return {
        "description_cn": desc,
        "details": {
            f"{key}_latest": latest_val,
            "threshold": threshold,
            "relation": relation,
            "gap": round(gap, 4),
            "recent_trend": trend_info["direction"],
            "recent_5d": recent_5d[-5:] if recent_5d else [],
        },
    }


def _current_statistical(
    element: Dict[str, Any],
    series: Dict[str, List[Optional[float]]],
    dates: List[str],
) -> Dict[str, Any]:
    """Compute current state for a statistical element."""
    fn_name = element.get("function_name", "").upper()
    param = element.get("param")
    variables = element.get("variables", [])

    if not variables or param is None:
        return {"description_cn": f"{fn_name}参数不足", "details": {}}

    key = variables[0]
    ser = series.get(key, [])

    if fn_name == "HHV":
        # Max of last `param` valid values
        vals = [v for v in ser[-param:] if v is not None]
        result = max(vals) if vals else None
    elif fn_name == "LLV":
        vals = [v for v in ser[-param:] if v is not None]
        result = min(vals) if vals else None
    elif fn_name == "REF":
        # Value `param` bars ago
        idx = len(ser) - 1 - param
        result = ser[idx] if 0 <= idx < len(ser) else None
    elif fn_name == "SUM":
        vals = [v for v in ser[-param:] if v is not None]
        result = sum(vals) if vals else None
    elif fn_name == "COUNT":
        # COUNT of non-zero / True values (for pure variable: count of defined values)
        vals = [v for v in ser[-param:] if v is not None]
        result = len(vals)
    elif fn_name == "EVERY":
        # EVERY: all non-None values in window → True (1) or False (0)
        vals = [v for v in ser[-param:] if v is not None]
        result = 1.0 if len(vals) == param else 0.0
    elif fn_name == "ABS":
        latest = None
        for v in reversed(ser):
            if v is not None:
                latest = v
                break
        result = abs(latest) if latest is not None else None
    elif fn_name in ("MAX", "MIN"):
        vs = variables[:2]
        if len(vs) < 2:
            result = None
        else:
            s2 = series.get(vs[1], [])
            v1 = None
            v2 = None
            for v in reversed(ser):
                if v is not None:
                    v1 = v
                    break
            for v in reversed(s2):
                if v is not None:
                    v2 = v
                    break
            if v1 is not None and v2 is not None:
                result = max(v1, v2) if fn_name == "MAX" else min(v1, v2)
            else:
                result = None
    else:
        result = None

    if result is not None:
        desc = make_statistical_status(fn_name, result, element.get("label_cn", fn_name))
    else:
        desc = f"{fn_name}: 数据不足，无法计算"

    return {
        "description_cn": desc,
        "details": {
            "function": fn_name,
            "param": param,
            "result": round(result, 4) if isinstance(result, float) else result,
        },
    }


def _compute_events(
    element: Dict[str, Any],
    series: Dict[str, List[Optional[float]]],
    dates: List[str],
) -> List[Dict[str, Any]]:
    """Detect historical events relevant to this element."""
    etype = element["element_type"]
    variables = element.get("variables", [])

    if etype == "cross" and len(variables) >= 2:
        s_a = series.get(variables[0], [])
        s_b = series.get(variables[1], [])
        return detect_cross_events(s_a, s_b, dates)

    elif etype == "compare" and variables and element.get("threshold") is not None:
        ser = series.get(variables[0], [])
        return detect_threshold_breaches(ser, element["threshold"], dates, element.get("op", "gt"))

    else:
        return []


def _extract_sequence(
    element: Dict[str, Any],
    series: Dict[str, List[Optional[float]]],
    dates: List[str],
    days: int = 60,
) -> Dict[str, List[Any]]:
    """Extract relevant series slice for this element (last `days` items)."""
    variables = element.get("variables", [])
    n = len(dates)
    start = max(0, n - days)

    seq: Dict[str, List[Any]] = {
        "dates": dates[start:],
    }
    for key in variables:
        if key in series:
            seq[key] = series[key][start:]

    return seq


# ============================================================
# Main entry: parse a formula into elements
# ============================================================

def parse_formula(
    formula: str,
    series: Dict[str, List[Optional[float]]],
    dates: List[str],
    *,
    sequence_days: int = 60,
) -> List[Dict[str, Any]]:
    """Parse a TDX formula string into a list of structured FormulaElement dicts.

    Args:
        formula: Raw TDX formula text (may contain Chinese).
        series: Indicator series dict from compute_all_series().
        dates: Date strings aligned with the series.
        sequence_days: Number of recent days to include in element.sequence.

    Returns:
        List of FormulaElement-compatible dicts, in formula order.
        Each dict has keys:
          order, raw, label_cn, element_type, variables, logic_op,
          current, events, sequence
    """
    if not formula or not formula.strip():
        return []

    # Normalize
    normalized = normalize_formula(formula)

    # Split by logic operators
    fragments = _split_by_logic(normalized)

    elements: List[Dict[str, Any]] = []
    warnings: List[str] = []

    for idx, (frag, logic_op) in enumerate(fragments):
        if not frag:
            continue

        # Try pattern matchers in priority order:
        # 1. cross    (CROSS specific)
        # 2. statistical (HHV/LLV/COUNT/... — must precede compare because
        #    COUNT(C>MA(C,20),10) contains ">" but is a function, not a compare)
        # 3. compare  (generic X OP Y)
        matched = (
            _match_cross(frag)
            or _match_statistical(frag)
            or _match_compare(frag)
        )

        if not matched:
            # Fallback → opaque
            variables = resolve_variable(frag)
            matched = {
                "element_type": "opaque",
                "raw": frag,
                "variables": variables,
                "label_cn": f"复杂表达式: {frag}",
            }

        # Attach order and logic
        matched["order"] = idx
        matched["logic_op"] = logic_op

        # Compute current state
        try:
            matched["current"] = _compute_current_state(matched, series, dates)
        except Exception:
            matched["current"] = {"description_cn": "状态计算失败", "details": {}}

        # Detect events
        try:
            matched["events"] = _compute_events(matched, series, dates)
        except Exception:
            matched["events"] = []

        # Extract sequence
        try:
            matched["sequence"] = _extract_sequence(matched, series, dates, days=sequence_days)
        except Exception:
            matched["sequence"] = {}

        # Add warnings for opaque elements
        if matched["element_type"] == "opaque" and matched.get("reason") == "nested_condition":
            warnings.append(
                f"要素{idx}: '{frag[:60]}' 包含嵌套条件，引擎不解析，需LLM自行分析"
            )

        elements.append(matched)

    # Attach warnings to first element or last if needed (for caller to use)
    if warnings and elements:
        elements[0]["_parse_warnings"] = warnings

    return elements
