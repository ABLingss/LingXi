"""
constants.py — TDX formula keyword mappings and Chinese labels.

Phase A (needed by elements.py):
  - CN_TO_EN: Chinese → English canonical token replacement
  - ALIAS_TO_CANONICAL: English aliases → canonical form
  - FUNCTION_NAMES: set of recognized TDX function names
  - COMPARE_OPS / COMPARE_OP_CN: comparison operator mappings

Phase B (needed by formatter + comparator):
  - VARIABLE_MAP: expression fragment → indicator series key (regex-based)
  - LABEL_TEMPLATES: per-element-type Chinese label generators
  - STATUS_DESCRIPTIONS: human-readable status description templates
"""

import re
from typing import Any, Dict, List, Match, Optional, Tuple


# ============================================================
# Phase A — Normalization
# ============================================================

# Chinese → English canonical token
CN_TO_EN: Dict[str, str] = {
    "收盘价": "C",
    "开盘价": "O",
    "最高价": "H",
    "最低价": "L",
    "成交量": "VOL",
    "成交额": "AMOUNT",
    "涨幅": "CHANGE",
    "换手率": "TURNOVER",
    "量比": "VOLRATIO",
}

# English aliases → canonical form
ALIAS_TO_CANONICAL: Dict[str, str] = {
    "CLOSE": "C",
    "OPEN": "O",
    "HIGH": "H",
    "LOW": "L",
    "VOLUME": "VOL",
    "VOL": "VOL",
    "V": "VOL",
    "AMOUNT": "AMOUNT",
}

# Recognized TDX function names (uppercase)
FUNCTION_NAMES: set = {
    "MA", "EMA", "SMA", "WMA",
    "CROSS",
    "RSI", "MACD", "BOLL", "KDJ",
    "HHV", "LLV",
    "COUNT", "EVERY",
    "REF",
    "SUM",
    "IF", "IIF",
    "ABS", "MAX", "MIN", "STD",
    "BARSLAST", "BARSCOUNT",
    "FILTER", "EXIST",
    "AVEDEV", "SLOPE", "FORCAST",
}

# Comparison operators
COMPARE_OPS: Dict[str, str] = {
    ">=": "gte",
    "<=": "lte",
    ">": "gt",
    "<": "lt",
    "=": "eq",
    "==": "eq",
    "!=": "neq",
}

COMPARE_OP_CN: Dict[str, str] = {
    "gte": "大于等于",
    "lte": "小于等于",
    "gt": "大于",
    "lt": "小于",
    "eq": "等于",
    "neq": "不等于",
}

# Logical operators for splitting
LOGIC_OPS = {"&", "|", "AND", "OR"}


# ============================================================
# Phase B — Variable resolution (regex patterns)
# ============================================================

# Each pattern: (regex, lambda match → variable key)
# Order matters — more specific patterns first.
_VARIABLE_PATTERNS: List[Tuple[re.Pattern, Any]] = [
    # MA(C, N) → maN
    (re.compile(r"MA\s*\(\s*C\s*,\s*(\d+)\s*\)", re.IGNORECASE),
     lambda m: f"ma{int(m.group(1))}"),
    # MA(CLOSE, N) → maN
    (re.compile(r"MA\s*\(\s*CLOSE\s*,\s*(\d+)\s*\)", re.IGNORECASE),
     lambda m: f"ma{int(m.group(1))}"),
    # RSI(N) → rsiN
    (re.compile(r"RSI\s*\(\s*(\d+)\s*\)", re.IGNORECASE),
     lambda m: f"rsi{int(m.group(1))}"),
    # EMA(C, N) → emaN (we map common ones)
    (re.compile(r"EMA\s*\(\s*C\s*,\s*(\d+)\s*\)", re.IGNORECASE),
     lambda m: f"ema_{int(m.group(1))}"),
    # MACD.DIF / MACD.DEA / MACD.MACD
    (re.compile(r"MACD\s*\.\s*DIF\b", re.IGNORECASE),
     lambda m: "macd_dif"),
    (re.compile(r"MACD\s*\.\s*DEA\b", re.IGNORECASE),
     lambda m: "macd_dea"),
    (re.compile(r"MACD\s*\.\s*MACD\b", re.IGNORECASE),
     lambda m: "macd_bar"),
    # BOLL.UPPER / BOLL.MID / BOLL.LOWER
    (re.compile(r"BOLL\s*\.\s*UPPER\b", re.IGNORECASE),
     lambda m: "boll_upper"),
    (re.compile(r"BOLL\s*\.\s*MID\b", re.IGNORECASE),
     lambda m: "boll_mid"),
    (re.compile(r"BOLL\s*\.\s*LOWER\b", re.IGNORECASE),
     lambda m: "boll_lower"),
    # KDJ.K / KDJ.D / KDJ.J
    (re.compile(r"KDJ\s*\.\s*K\b", re.IGNORECASE),
     lambda m: "kdj_k"),
    (re.compile(r"KDJ\s*\.\s*D\b", re.IGNORECASE),
     lambda m: "kdj_d"),
    (re.compile(r"KDJ\s*\.\s*J\b", re.IGNORECASE),
     lambda m: "kdj_j"),
    # C / CLOSE → c
    (re.compile(r"\bC\b"), lambda m: "c"),
    (re.compile(r"\bCLOSE\b", re.IGNORECASE), lambda m: "c"),
    # O / OPEN → o
    (re.compile(r"\bO\b"), lambda m: "o"),
    (re.compile(r"\bOPEN\b", re.IGNORECASE), lambda m: "o"),
    # H / HIGH → h
    (re.compile(r"\bH\b"), lambda m: "h"),
    (re.compile(r"\bHIGH\b", re.IGNORECASE), lambda m: "h"),
    # L / LOW → l
    (re.compile(r"\bL\b"), lambda m: "l"),
    (re.compile(r"\bLOW\b", re.IGNORECASE), lambda m: "l"),
    # V / VOL / VOLUME → v
    (re.compile(r"\bV\b"), lambda m: "v"),
    (re.compile(r"\bVOL\b", re.IGNORECASE), lambda m: "v"),
    (re.compile(r"\bVOLUME\b", re.IGNORECASE), lambda m: "v"),
]


def resolve_variable(expr: str) -> List[str]:
    """Resolve an expression fragment to its indicator series keys.

    Scans the expression against all known patterns and returns
    a deduplicated list of unique variable keys found.

    Example:
        "MA(C,5)" → ["ma5"]
        "CROSS(MA(C,5), MA(C,20))" → ["ma5", "ma20"]
        "RSI(6) > 50" → ["rsi6"]
        "C" → ["c"]

    Args:
        expr: A normalized (uppercase, English) sub-expression.

    Returns:
        Deduplicated list of series variable keys.
    """
    found: List[str] = []
    seen: set = set()
    for pattern, resolver in _VARIABLE_PATTERNS:
        for m in pattern.finditer(expr):
            key = resolver(m)
            if key not in seen:
                found.append(key)
                seen.add(key)
    return found


# ============================================================
# Phase B — Chinese label templates
# ============================================================

def make_cross_label(a_expr: str, b_expr: str) -> str:
    """Generate Chinese label for CROSS(A, B)."""
    return f"{a_expr}与{b_expr}交叉"


def make_compare_label(left: str, op_cn: str, right: str) -> str:
    """Generate Chinese label for comparison 'left OP right'."""
    return f"{left}是否{op_cn}{right}"


def make_statistical_label(func_name: str, arg_expr: str, param: int) -> str:
    """Generate Chinese label for statistical functions."""
    labels = {
        "HHV": f"最近{param}日{arg_expr}的最高值",
        "LLV": f"最近{param}日{arg_expr}的最低值",
        "REF": f"{param}日前的{arg_expr}值",
        "SUM": f"最近{param}日{arg_expr}的累加值",
        "COUNT": f"最近{param}日{arg_expr}的计数",
        "EVERY": f"最近{param}日{arg_expr}是否全部满足",
    }
    return labels.get(func_name.upper(), f"{func_name}({arg_expr}, {param})")


# ============================================================
# Phase B — Status description templates
# ============================================================

def make_cross_status(
    a_name: str, a_val: float,
    b_name: str, b_val: float,
    relation: str,  # "above" | "below"
    consecutive_days: int,
) -> str:
    """Generate current status for a cross-type element."""
    rel_cn = "上方" if relation == "above" else "下方"
    return (
        f"{a_name}({a_val:.2f}) 在 {b_name}({b_val:.2f}) {rel_cn}，"
        f"已维持 {consecutive_days} 个交易日"
    )


def make_compare_status(
    indicator_name: str,
    latest_val: float,
    threshold: float,
    operator: str,
    recent_trend: str,
    recent_5d: List[float],
) -> str:
    """Generate current status for a compare-type element."""
    op_cn = COMPARE_OP_CN.get(operator, operator)
    gap = abs(latest_val - threshold)

    if operator in ("gt", "gte"):
        relation = "满足(上方)" if latest_val >= threshold else "低于"
    elif operator in ("lt", "lte"):
        relation = "满足(下方)" if latest_val <= threshold else "高于"
    else:
        relation = "未知"

    trend_cn = {"rising": "上升中", "falling": "下降中", "flat": "持平"}.get(recent_trend, recent_trend)
    recent_str = " → ".join(f"{v:.2f}" for v in recent_5d[-5:]) if recent_5d else "无数据"

    return (
        f"{indicator_name}={latest_val:.2f}，{relation}阈值{threshold}，"
        f"差距{gap:.2f}。近5日趋势：{trend_cn}({recent_str})"
    )


def make_statistical_status(
    func_name: str,
    result_value: float,
    description: str,
) -> str:
    """Generate current status for a statistical-type element."""
    return f"{description} = {result_value:.4f}"


# ============================================================
# Normalization helpers
# ============================================================

def normalize_formula(text: str) -> str:
    """Normalize a TDX formula string for parsing.

    Steps:
      1. Replace Chinese tokens with English canonical forms.
      2. Uppercase everything.
      3. Collapse whitespace around operators.
      4. Remove extra spaces.

    Args:
        text: Raw formula text (may contain Chinese).

    Returns:
        Cleaned, uppercase, English-only formula string.
    """
    result = text.strip()

    # Replace Chinese → English
    for cn, en in CN_TO_EN.items():
        result = result.replace(cn, en)

    # Uppercase
    result = result.upper()

    # Normalize logical operators
    result = re.sub(r'\bAND\b', '&', result)
    result = re.sub(r'\bOR\b', '|', result)

    # Collapse whitespace
    result = re.sub(r'\s+', ' ', result).strip()

    # Remove spaces around comparison operators and parentheses
    result = re.sub(r'\s*([><=!]=?)\s*', r'\1', result)
    result = re.sub(r'\s*([(),&|])\s*', r'\1', result)

    # Add spaces back around & and | for readability (optional)
    # result = re.sub(r'\s*&\s*', ' & ', result)
    # result = re.sub(r'\s*\|\s*', ' | ', result)

    return result
