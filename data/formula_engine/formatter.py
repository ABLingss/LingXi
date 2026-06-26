"""
formatter.py — Dual output formatting for the formula engine.

Provides two output paths:
  1. to_json(pkg)    → structured JSON for LLM API consumption
  2. to_prompt(pkg)  → markdown prompt for user copy-paste

Handles 4 scenarios:
  - single          — 1 stock, no formula
  - single_formula  — 1 stock + formula
  - multi           — 2-6 stocks, no formula
  - multi_formula   — 2-6 stocks + formula

Token budget control for multi-stock scenarios:
  - K-lines: last 30 days (vs 60 for single)
  - Indicators: only 8 core series (vs all 22)
"""

import json
from typing import Any, Dict, List, Optional

# Multi-stock: only these 8 core series are included (per-stock K-lines still included)
_MULTI_CORE_SERIES = [
    "c", "ma5", "ma20", "ma60",
    "macd_dif", "macd_bar",
    "rsi6",
    "boll_mid",
]


# ============================================================
# JSON output
# ============================================================

def to_json(pkg, compact: bool = False) -> str:
    """Serialize AnalysisPackage to structured JSON.

    Args:
        pkg: AnalysisPackage instance.
        compact: If True, reduce sequence lengths and omit verbose fields.

    Returns:
        JSON string (with Chinese support).
    """
    data = _package_to_dict(pkg, compact=compact)
    return json.dumps(data, ensure_ascii=False, indent=2 if not compact else None, default=str)


def _package_to_dict(pkg, compact: bool = False) -> Dict[str, Any]:
    """Convert AnalysisPackage to a plain dict for JSON serialization."""
    out: Dict[str, Any] = {
        "scenario": pkg.scenario,
        "stocks": [s.__dict__ if hasattr(s, '__dict__') else s for s in pkg.stocks],
        "warnings": pkg.warnings,
    }

    # K-lines
    out["klines"] = {}
    for code, klines in pkg.klines.items():
        out["klines"][code] = klines

    # Series — slim down for multi-stock
    out["series"] = {}
    for code, ser in pkg.series.items():
        if pkg.scenario.startswith("multi"):
            out["series"][code] = {k: ser.get(k, []) for k in _MULTI_CORE_SERIES if k in ser}
        else:
            out["series"][code] = ser

    # Formula
    if pkg.formula:
        out["formula"] = {
            "raw": pkg.formula.raw if hasattr(pkg.formula, 'raw') else pkg.formula.get("raw", ""),
            "elements": [],
        }
        elements = pkg.formula.elements if hasattr(pkg.formula, 'elements') else pkg.formula.get("elements", [])
        for el in elements:
            el_dict = el.__dict__ if hasattr(el, '__dict__') else el
            out["formula"]["elements"].append(el_dict)
    else:
        out["formula"] = None

    # Comparison table (multi-stock only)
    if pkg.comparison:
        comp = pkg.comparison
        out["comparison"] = comp.__dict__ if hasattr(comp, '__dict__') else comp
    else:
        out["comparison"] = None

    return out


# ============================================================
# Markdown prompt output
# ============================================================

def to_prompt(pkg, days: int = 60) -> str:
    """Build a markdown-prompt string from an AnalysisPackage.

    Args:
        pkg: AnalysisPackage instance.
        days: Number of recent days to include in the prompt series.

    Returns:
        Markdown string.
    """
    scenario = pkg.scenario

    if scenario == "single":
        return _build_single(pkg, days)
    elif scenario == "single_formula":
        return _build_single_formula(pkg, days)
    elif scenario == "multi":
        return _build_multi(pkg, days)
    elif scenario == "multi_formula":
        return _build_multi_formula(pkg, days)
    else:
        return f"# Unknown scenario: {scenario}"


# ---- Single stock, no formula ----

def _build_single(pkg, days: int) -> str:
    stocks = pkg.stocks
    s = stocks[0] if stocks else {}
    name = getattr(s, 'name', '未知')
    code = getattr(s, 'code', '未知')
    period = getattr(s, 'period', '日线')

    parts = [
        f"# 深度技术分析: {name}({code})",
        "",
        _build_basic_info(s),
        "",
        "## 完整K线数据 (最近{days}天)".format(days=len(_get_klines_slice(pkg, code, days))),
        "```json",
        _json_block(_get_klines_slice(pkg, code, days)),
        "```",
        "",
        "## 全部技术指标序列 (最近{days}天，均已按日期对齐K线)".format(days=days),
        "```json",
        _json_block(_get_series_slice(pkg, code, days, core_only=False)),
        "```",
        "",
        _build_analysis_framework(),
    ]

    return "\n".join(parts)


# ---- Single stock + formula ----

def _build_single_formula(pkg, days: int) -> str:
    stocks = pkg.stocks
    s = stocks[0] if stocks else {}
    name = getattr(s, 'name', '未知')
    code = getattr(s, 'code', '未知')

    parts = [
        f"# 选股公式技术分析: {name}({code})",
        "",
        _build_basic_info(s),
        "",
        "## 选股公式",
        f"`{_get_formula_raw(pkg)}`",
        "",
    ]

    # Formula elements section
    parts.append(_build_formula_section(pkg))

    # Warnings
    if pkg.warnings:
        parts.append("")
        parts.append("## ⚠️ 注意事项")
        for w in pkg.warnings:
            parts.append(f"- {w}")

    # K-lines
    k_slice = _get_klines_slice(pkg, code, days)
    parts.extend([
        "",
        f"## 完整K线数据 (最近{len(k_slice)}天)",
        "```json",
        _json_block(k_slice),
        "```",
    ])

    # Full indicator series
    ser_slice = _get_series_slice(pkg, code, days, core_only=False)
    parts.extend([
        "",
        f"## 全部技术指标序列 (最近{days}天)",
        "```json",
        _json_block(ser_slice),
        "```",
    ])

    # Analysis framework
    parts.extend([
        "",
        _build_formula_analysis_requirements(),
    ])

    return "\n".join(parts)


# ---- Multi stock, no formula ----

def _build_multi(pkg, days: int = 30) -> str:
    stock_names = ", ".join(getattr(s, 'name', '?') for s in pkg.stocks)
    parts = [
        f"# 多股对比分析: {stock_names}",
        "",
    ]

    # Basic info for each stock
    for s in pkg.stocks:
        code = getattr(s, 'code', '?')
        parts.append(_build_basic_info(s))
        parts.append("")

    # Comparison table
    if pkg.comparison:
        parts.append("## 多股指标对比")
        parts.append(_build_comparison_markdown(pkg.comparison))
        parts.append("")

    # K-lines + core series for each stock
    for s in pkg.stocks:
        code = getattr(s, 'code', '?')
        name = getattr(s, 'name', '?')
        parts.append(f"### {name}({code}) K线数据 (最近30天)")
        parts.append("```json")
        parts.append(_json_block(_get_klines_slice(pkg, code, 30)))
        parts.append("```")
        parts.append("")

    # Core series for each stock
    for s in pkg.stocks:
        code = getattr(s, 'code', '?')
        name = getattr(s, 'name', '?')
        parts.append(f"### {name}({code}) 核心指标序列 (最近30天)")
        parts.append("```json")
        parts.append(_json_block(_get_series_slice(pkg, code, 30, core_only=True)))
        parts.append("```")
        parts.append("")

    parts.append(_build_multi_analysis_requirements())
    return "\n".join(parts)


# ---- Multi stock + formula ----

def _build_multi_formula(pkg, days: int = 30) -> str:
    stock_names = ", ".join(getattr(s, 'name', '?') for s in pkg.stocks)
    parts = [
        f"# 多股选股公式对比: {stock_names}",
        "",
        "## 选股公式",
        f"`{_get_formula_raw(pkg)}`",
        "",
    ]

    # Formula elements
    parts.append(_build_formula_section(pkg))
    parts.append("")

    # Formula comparison table
    if pkg.comparison and hasattr(pkg.comparison, 'formula_comparison'):
        fc = pkg.comparison.formula_comparison
        parts.append("## 公式要素逐股对比")
        parts.append(_build_formula_comparison_markdown(fc))
        parts.append("")

    # Per-stock info + K-lines
    for s in pkg.stocks:
        code = getattr(s, 'code', '?')
        name = getattr(s, 'name', '?')
        parts.append(f"### {name}({code})")
        parts.append(_build_basic_info(s))
        parts.append("")
        parts.append("K线数据 (最近30天):")
        parts.append("```json")
        parts.append(_json_block(_get_klines_slice(pkg, code, 30)))
        parts.append("```")
        parts.append("")

        parts.append("核心指标序列 (最近30天):")
        parts.append("```json")
        parts.append(_json_block(_get_series_slice(pkg, code, 30, core_only=True)))
        parts.append("```")
        parts.append("")

    parts.append(_build_formula_analysis_requirements())
    return "\n".join(parts)


# ============================================================
# Section builders
# ============================================================

def _build_basic_info(s) -> str:
    """Build basic info markdown table."""
    lines = [
        "| 项目 | 内容 |",
        "|------|------|",
        f"| 代码 | {getattr(s, 'code', '?')} |",
        f"| 名称 | {getattr(s, 'name', '?')} |",
        f"| 市场 | {getattr(s, 'market', '?')} |",
        f"| 周期 | {getattr(s, 'period', '日线')} |",
        f"| 数据量 | {getattr(s, 'bar_count', 0)} 条",
        f" ({getattr(s, 'start_date', '?')} ~ {getattr(s, 'end_date', '?')}) |",
    ]
    return "\n".join(lines)


def _build_formula_section(pkg) -> str:
    """Build formula elements analysis section (reused in single_formula + multi_formula)."""
    if not pkg.formula:
        return "## 公式要素\n(无公式)"

    elements = pkg.formula.elements if hasattr(pkg.formula, 'elements') else pkg.formula.get("elements", [])
    if not elements:
        return "## 公式要素\n(未能解析公式要素)"

    lines = ["## 🧩 公式要素拆解", ""]

    for el in elements:
        el_dict = el.__dict__ if hasattr(el, '__dict__') else el
        label = el_dict.get("label_cn", "未知")
        etype = el_dict.get("element_type", "?")
        logic_op = el_dict.get("logic_op")
        raw = el_dict.get("raw", "")
        current = el_dict.get("current", {})
        events = el_dict.get("events", [])
        sequence = el_dict.get("sequence", {})

        type_emoji = {"cross": "🔀", "compare": "📊", "statistical": "📈", "opaque": "❓"}.get(etype, "❓")
        type_cn = {"cross": "金叉/死叉", "compare": "条件判断", "statistical": "统计函数", "opaque": "复杂表达式"}.get(etype, etype)

        lines.append(f"### 要素{el_dict.get('order', 0)+1}: {type_emoji} {label}")
        lines.append(f"- **公式片段**: `{raw}`")
        lines.append(f"- **类型**: {type_cn}")
        lines.append(f"- **当前状态**: {current.get('description_cn', '未知')}")

        # Events
        if events:
            lines.append(f"- **历史事件**:")
            for ev in events[:5]:  # Top 5 most recent
                lines.append(
                    f"  - {ev.get('date', '?')}: {ev.get('direction_cn', '?')} "
                    f"(间隔{ev.get('gap', '?')}, 距今{ev.get('days_since', '?')}天)"
                )

        # Sequence
        if sequence and sequence.get("dates"):
            lines.append(f"- **相关序列**(最近{len(sequence.get('dates', []))}天):")
            lines.append("```json")
            lines.append(_json_block(sequence))
            lines.append("```")

        # Logic connector
        if logic_op and el != elements[-1]:
            logic_cn = "AND (同时满足)" if logic_op == "&" else "OR (满足其一)"
            lines.append(f"  ═══ {logic_cn} ═══")

        lines.append("")

    # Warnings from opaque elements
    for el in elements:
        el_dict = el.__dict__ if hasattr(el, '__dict__') else el
        if el_dict.get("element_type") == "opaque":
            lines.append(f"> ⚠️ `{el_dict.get('raw', '')[:80]}` 引擎无法自动解析，需LLM对照序列自行分析。")
            lines.append("")

    return "\n".join(lines)


def _build_comparison_markdown(comparison) -> str:
    """Build comparison table markdown."""
    comp = comparison.__dict__ if hasattr(comparison, '__dict__') else comparison
    headers = comp.get("headers", [])
    rows = comp.get("rows", [])

    if not headers or not rows:
        return "(对比数据不足)"

    lines = []
    # Header
    lines.append("| " + " | ".join(str(h) for h in headers) + " |")
    lines.append("|" + "|".join("------" for _ in headers) + "|")

    # Rows
    for row in rows:
        label = row.get("label", "")
        unit = row.get("unit", "")
        vals = []
        for v in row.get("values", []):
            val_str = str(v.get("val", "-"))
            hl = v.get("highlight")
            if hl == "best":
                val_str = f"**{val_str}** 🏆"
            elif hl == "worst":
                val_str = f"*{val_str}* ⚠️"
            vals.append(val_str)
        label_text = f"{label}({unit})" if unit else label
        lines.append("| " + label_text + " | " + " | ".join(vals) + " |")

    return "\n".join(lines)


def _build_formula_comparison_markdown(fc) -> str:
    """Build formula comparison table."""
    fc_data = fc.__dict__ if hasattr(fc, '__dict__') else fc
    if isinstance(fc_data, list):
        items = fc_data
    else:
        return "(对比数据不足)"

    if not items:
        return "(无公式对比数据)"

    lines = []
    for item in items:
        label = item.get("element_label", "?")
        lines.append(f"**{label}**")
        for stock_info in item.get("stocks", []):
            code = stock_info.get("code", "?")
            state = stock_info.get("state", "?")
            hl = stock_info.get("highlight", "")
            icon = {"golden": "✅", "met": "✔️", "close": "🟡", None: "❌"}.get(hl, "")
            lines.append(f"  - {code}: {state} {icon}")
        lines.append("")

    return "\n".join(lines)


def _build_analysis_framework() -> str:
    """Standard analysis framework (no formula)."""
    return """## 分析要求

你是一位资深A股量化分析师。请基于以上完整数据，进行深度技术分析：

1. **趋势判断**: 多/空/震荡，支撑位和压力位（给出具体价位）
2. **量价关系**: 放量/缩量特征，主力资金动向判断
3. **形态识别**: 识别关键K线形态和技术形态
4. **指标信号**: MACD金叉/死叉，RSI超买超卖，BOLL收窄/扩张，KDJ状态
5. **风险评估**: 波动率水平、回撤风险、仓位建议

> ⚠️ 以上分析仅供参考，不构成投资建议。股市有风险，投资需谨慎。"""


def _build_formula_analysis_requirements() -> str:
    """Analysis requirements for formula-based scenarios."""
    return """## 分析要求

你是一位资深A股量化分析师。请基于以上完整数据，逐要素进行分析：

1. **逐要素分析**: 对上述每个公式要素，分析其当前状态、历史演变、趋势方向
2. **要素配合度**: 各要素之间是否相互印证或矛盾
3. **接近满足**: 哪些条件接近满足但尚未满足，差距有多大
4. **整体评估**:
   - 趋势: 多/空/震荡
   - 支撑压力: 给出具体价位
   - 量价关系: 放量/缩量特征
   - 形态: 识别关键形态
   - 风险: 波动率、回撤风险
5. **注意事项**: 请说明分析中不确定的部分和需要更多数据确认的点

> ⚠️ 以上分析仅供参考，不构成投资建议。股市有风险，投资需谨慎。"""


def _build_multi_analysis_requirements() -> str:
    """Analysis requirements for multi-stock comparison."""
    return """## 分析要求

请基于以上多只股票的K线和指标数据进行横向对比分析：

1. **横向对比**: 各股趋势、动能、量价、位置的对比排名
2. **最强/最弱**: 找出表现最强和最弱的标的，说明理由
3. **共振**: 多股是否出现共同的技术信号（如同时金叉/同时超卖）
4. **选择建议**: 综合评估后给出选股优先级排序

> ⚠️ 以上分析仅供参考，不构成投资建议。股市有风险，投资需谨慎。"""


# ============================================================
# Helpers
# ============================================================

def _get_formula_raw(pkg) -> str:
    """Extract raw formula string from package."""
    if not pkg.formula:
        return ""
    if hasattr(pkg.formula, 'raw'):
        return pkg.formula.raw
    return pkg.formula.get("raw", "")


def _get_klines_slice(pkg, code: str, days: int) -> List[Dict]:
    """Get last N klines for a stock code."""
    klines = pkg.klines.get(code, [])
    return klines[-days:] if len(klines) > days else klines


def _get_series_slice(pkg, code: str, days: int, core_only: bool = False):
    """Get last N values from each series for a stock code."""
    ser = pkg.series.get(code, {})
    result: Dict[str, List] = {}
    keys = _MULTI_CORE_SERIES if core_only else list(ser.keys())
    for k in keys:
        if k in ser:
            arr = ser[k]
            result[k] = arr[-days:] if len(arr) > days else arr
    return result


def _json_block(obj) -> str:
    """Serialize to compact-ish JSON for inline code blocks."""
    return json.dumps(obj, ensure_ascii=False, indent=2, default=str)
