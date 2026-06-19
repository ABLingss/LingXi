"""
formula_prompt.py — TDX formula → AI prompt converter for Stock JSON Clipper.

Extracts key indicators and conditions from TDX (通达信) formula text
using regex, then generates a natural-language Chinese prompt that includes
the current stock's actual indicator values. The user pastes this prompt
into an AI (ChatGPT/DeepSeek) for analysis.

Supported TDX patterns:
  - CROSS(A, B)      → Golden/death cross
  - MA(C, N)         → Moving average
  - MACD.DIF/DEA     → MACD components
  - RSI(N)           → RSI threshold
  - BOLL.UPPER/LOWER → Bollinger Bands
  - Comparison ops   → >, <, >=, <=, =
  - Logical ops      → AND, OR, &&
  - Numeric constants
"""

import re
import json
from typing import Any, Dict, List, Tuple


# --- Pattern recognizers ---
# CROSS uses a specialized extractor (see _extract_cross) to handle
# nested parentheses in arguments like CROSS(MA(C,5), MA(C,20))
MA_PATTERN = re.compile(r"MA\s*\(\s*C\s*,\s*(\d+)\s*\)", re.IGNORECASE)
MACD_PATTERN = re.compile(r"MACD\s*\.\s*(DIF|DEA|MACD)\b", re.IGNORECASE)
RSI_PATTERN = re.compile(r"RSI\s*\(\s*(\d+)\s*\)", re.IGNORECASE)
BOLL_PATTERN = re.compile(r"BOLL\s*\.\s*(UPPER|LOWER|MID)\b", re.IGNORECASE)
COMPARE_PATTERN = re.compile(
    r"([A-Za-z_.0-9()]+)\s*(>=?|<=?|==?|!=)\s*([A-Za-z_.0-9()]+)"
)
NUMERIC_PATTERN = re.compile(r"[-+]?\d*\.?\d+")
KEYWORD_PATTERN = re.compile(
    r"\b(SMA|EMA|VOL|CLOSE|OPEN|HIGH|LOW|AMOUNT|REF|HHV|LLV|BARSLAST|"
    r"EVERY|EXIST|COUNT|IF|THEN|BUY|SELL|FILTER)\b",
    re.IGNORECASE,
)

# English → Chinese indicator name mapping
INDICATOR_NAMES_CN = {
    "MA": "均线",
    "MACD": "MACD",
    "MACD.DIF": "MACD快线(DIF)",
    "MACD.DEA": "MACD慢线(DEA)",
    "MACD.MACD": "MACD柱(BAR)",
    "RSI": "RSI相对强弱",
    "BOLL": "布林带",
    "BOLL.UPPER": "布林上轨",
    "BOLL.MID": "布林中轨",
    "BOLL.LOWER": "布林下轨",
    "VOL": "成交量",
    "CLOSE": "收盘价",
    "OPEN": "开盘价",
    "HIGH": "最高价",
    "LOW": "最低价",
}


def _find_cross_args(text: str, start: int) -> tuple:
    """Extract the two arguments of a CROSS() call using paren counting.

    Handles nested function calls like CROSS(MA(C,5), MA(C,20)).

    Args:
        text: The formula text.
        start: Position of the opening paren of CROSS(.

    Returns:
        (arg1, arg2, end_pos) or (None, None, -1) on failure.
    """
    # start points to '(' — find matching ')'
    depth = 0
    end = -1
    for i in range(start, len(text)):
        if text[i] == '(':
            depth += 1
        elif text[i] == ')':
            depth -= 1
            if depth == 0:
                end = i
                break

    if end < 0:
        return (None, None, -1)

    inner = text[start + 1:end]

    # Split inner on the top-level comma (not inside nested parens)
    split_pos = -1
    depth = 0
    for i, ch in enumerate(inner):
        if ch == '(':
            depth += 1
        elif ch == ')':
            depth -= 1
        elif ch == ',' and depth == 0:
            split_pos = i
            break

    if split_pos < 0:
        return (None, None, -1)

    return (inner[:split_pos].strip(), inner[split_pos + 1:].strip(), end)


def extract_indicators(formula: str) -> List[Dict[str, str]]:
    """Extract indicator references from TDX formula text.

    Args:
        formula: Raw TDX formula text.

    Returns:
        List of dicts with 'type' and 'detail' keys.
    """
    found: List[Dict[str, str]] = []

    # CROSS patterns — use paren-counting extractor for nested args
    cross_re = re.compile(r"CROSS\s*\(", re.IGNORECASE)
    for m in cross_re.finditer(formula):
        a, b, end = _find_cross_args(formula, m.end() - 1)
        if a and b:
            found.append({"type": "CROSS", "detail": f"{a} 穿越 {b}"})

    # MA patterns
    for m in MA_PATTERN.finditer(formula):
        n = m.group(1)
        found.append({"type": "MA", "detail": f"MA({n})"})

    # MACD patterns
    for m in MACD_PATTERN.finditer(formula):
        comp = m.group(1).upper()
        found.append({"type": "MACD", "detail": f"MACD.{comp}"})

    # RSI patterns
    for m in RSI_PATTERN.finditer(formula):
        n = m.group(1)
        found.append({"type": "RSI", "detail": f"RSI({n})"})

    # BOLL patterns
    for m in BOLL_PATTERN.finditer(formula):
        band = m.group(1).upper()
        found.append({"type": "BOLL", "detail": f"BOLL.{band}"})

    # Comparison patterns
    for m in COMPARE_PATTERN.finditer(formula):
        left = m.group(1).strip()
        op = m.group(2).strip()
        right = m.group(3).strip()
        # Skip if it's a CROSS or already captured pattern internals
        if "CROSS" in left.upper() or "CROSS" in right.upper():
            continue
        found.append({"type": "CONDITION", "detail": f"{left} {op} {right}"})

    # Keywords
    for m in KEYWORD_PATTERN.finditer(formula):
        kw = m.group(1).upper()
        found.append({"type": "KEYWORD", "detail": kw})

    return found


def generate_prompt(
    formula: str,
    stock_code: str,
    stock_name: str,
    indicators: Dict[str, Any],
    summary: Dict[str, Any],
) -> str:
    """Generate an AI-ready natural language prompt from TDX formula + stock data.

    Args:
        formula: Raw TDX formula text (as pasted by user).
        stock_code: 6-digit stock code.
        stock_name: Stock name in Chinese.
        indicators: Dict from indicators.calc_all_indicators().
        summary: Dict from data_builder.build_summary().

    Returns:
        Natural language prompt string (Chinese) ready for AI analysis.
    """
    extracted = extract_indicators(formula)

    # Build indicator summary for injection
    indicator_lines = []
    if indicators.get("ma5") is not None:
        indicator_lines.append(f"  MA5: {indicators['ma5']:.2f}  |  MA10: {indicators['ma10']:.2f}  |  MA20: {indicators['ma20']:.2f}  |  MA60: {indicators['ma60']:.2f}")
    macd = indicators.get("macd", {})
    if macd:
        indicator_lines.append(f"  MACD: DIF={macd.get('dif', 0):.4f}  DEA={macd.get('dea', 0):.4f}  BAR={macd.get('bar', 0):.4f}")
    if indicators.get("rsi_6") is not None:
        indicator_lines.append(f"  RSI(6): {indicators['rsi_6']:.2f}  |  RSI(12): {indicators['rsi_12']:.2f}")
    boll = indicators.get("boll", {})
    if boll.get("mid") is not None:
        indicator_lines.append(f"  BOLL: 上轨={boll['upper']:.2f}  中轨={boll['mid']:.2f}  下轨={boll['lower']:.2f}")

    # Build extracted formula summary
    formula_elements = []
    for item in extracted:
        formula_elements.append(f"  - {item['type']}: {item['detail']}")

    # assemble prompt
    prompt_parts = [
        f"你是一位专业的A股技术分析师。请基于以下信息，判断股票 {stock_code}（{stock_name}）",
        f"是否满足我选股公式的条件。",
        "",
        "---",
        "## 当前技术指标数值",
        "",
    ]
    prompt_parts.extend(indicator_lines if indicator_lines else ["  (无指标数据)"])

    prompt_parts.extend([
        "",
        "## 统计摘要",
        f"  区间涨跌幅: {summary.get('period_change', 0):.2f}%",
        f"  区间最高收盘价: {summary.get('max_close', 0):.2f}",
        f"  区间最低收盘价: {summary.get('min_close', 0):.2f}",
        f"  平均成交量: {summary.get('avg_volume', 0):,}",
        f"  年化波动率: {summary.get('volatility', 0):.2f}%",
        "",
        "## 我的选股公式",
        "```",
        formula.strip(),
        "```",
        "",
        "## 公式解析（自动提取）",
    ])
    if formula_elements:
        prompt_parts.extend(formula_elements)
    else:
        prompt_parts.append("  (未能自动解析公式要素，请人工判断)")

    prompt_parts.extend([
        "",
        "---",
        "请逐条判断公式中的每个条件是否满足（是/否），并给出综合结论和操作建议。",
        "如果条件涉及金叉/死叉，请根据指标数值趋势推断。",
    ])

    return "\n".join(prompt_parts)


def generate_quick_prompt(
    code: str,
    name: str,
    indicators: Dict[str, Any],
    summary: Dict[str, Any],
) -> str:
    """Generate a generic AI analysis prompt (no formula), for quick stock analysis.

    Args:
        code: 6-digit stock code.
        name: Stock name.
        indicators: Dict from calc_all_indicators().
        summary: Dict from build_summary().

    Returns:
        Natural language prompt string.
    """
    return generate_prompt(
        formula="(无特定公式 — 通用技术分析)",
        stock_code=code,
        stock_name=name,
        indicators=indicators,
        summary=summary,
    )
