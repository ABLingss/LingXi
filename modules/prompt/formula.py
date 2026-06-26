"""
formula_prompt.py — TDX formula → AI prompt converter for Stock JSON Clipper V3.0.

Generates professional A-share technical analysis prompts with:
  - Multi-timeframe resonance analysis (日/周/月)
  - Trend, support/resistance, volume-price, momentum frameworks
  - Formula condition verification (逐条判断)
  - Backtesting & parameter optimization suggestions
  - Risk/reward assessment

The user pastes the generated prompt into ChatGPT/DeepSeek/Claude for analysis.
"""

import re
import json
from typing import Any, Dict, List, Optional, Tuple


# ============================================================
# Pattern recognizers
# ============================================================
MA_PATTERN = re.compile(r"MA\s*\(\s*C\s*,\s*(\d+)\s*\)", re.IGNORECASE)
MACD_PATTERN = re.compile(r"MACD\s*\.\s*(DIF|DEA|MACD)\b", re.IGNORECASE)
RSI_PATTERN = re.compile(r"RSI\s*\(\s*(\d+)\s*\)", re.IGNORECASE)
BOLL_PATTERN = re.compile(r"BOLL\s*\.\s*(UPPER|LOWER|MID)\b", re.IGNORECASE)
CROSS_PATTERN = re.compile(r"CROSS\s*\(", re.IGNORECASE)
COMPARE_PATTERN = re.compile(
    r"([A-Za-z_.0-9()]+)\s*(>=?|<=?|==?|!=)\s*([A-Za-z_.0-9()]+)"
)
KEYWORD_PATTERN = re.compile(
    r"\b(SMA|EMA|VOL|CLOSE|OPEN|HIGH|LOW|AMOUNT|REF|HHV|LLV|BARSLAST|"
    r"EVERY|EXIST|COUNT|IF|THEN|BUY|SELL|FILTER|ABS|MAX|MIN|SUM|"
    r"STD|AVEDEV|SLOPE|FORCAST|DEA|DIF)\b",
    re.IGNORECASE,
)

# Period labels for display
PERIOD_LABELS = {"daily": "日线", "weekly": "周线", "monthly": "月线"}


# ============================================================
# Formula parser
# ============================================================
def _find_cross_args(text: str, start: int) -> tuple:
    """Extract the two arguments of a CROSS() call using paren counting."""
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
    """Extract indicator references from TDX formula text."""
    found: List[Dict[str, str]] = []

    # CROSS
    for m in CROSS_PATTERN.finditer(formula):
        a, b, end = _find_cross_args(formula, m.end() - 1)
        if a and b:
            found.append({"type": "金叉/死叉", "detail": f"{a} 与 {b} 交叉"})

    # MA
    for m in MA_PATTERN.finditer(formula):
        found.append({"type": "均线", "detail": f"MA(C,{m.group(1)})"})

    # MACD
    for m in MACD_PATTERN.finditer(formula):
        found.append({"type": "MACD", "detail": f"MACD.{m.group(1).upper()}"})

    # RSI
    for m in RSI_PATTERN.finditer(formula):
        found.append({"type": "RSI", "detail": f"RSI({m.group(1)})"})

    # BOLL
    for m in BOLL_PATTERN.finditer(formula):
        found.append({"type": "布林带", "detail": f"BOLL.{m.group(1).upper()}"})

    # Comparisons
    for m in COMPARE_PATTERN.finditer(formula):
        left, op, right = m.group(1).strip(), m.group(2).strip(), m.group(3).strip()
        if "CROSS" in left.upper() or "CROSS" in right.upper():
            continue
        op_cn = {
            ">": "大于", "<": "小于", ">=": "大于等于",
            "<=": "小于等于", "=": "等于", "==": "等于", "!=": "不等于",
        }.get(op, op)
        found.append({"type": "条件判断", "detail": f"{left} {op_cn} {right}"})

    # Keywords
    seen = {f["detail"] for f in found}
    for m in KEYWORD_PATTERN.finditer(formula):
        kw = m.group(1).upper()
        if kw not in seen:
            found.append({"type": "函数", "detail": kw})
            seen.add(kw)

    return found


# ============================================================
# Indicator formatters
# ============================================================
def _fmt_indicators(indicators: Dict[str, Any], summary: Dict[str, Any]) -> List[str]:
    """Format current indicator values as markdown table rows."""
    lines = []
    # MA
    mas = [("MA5", indicators.get("ma5")), ("MA10", indicators.get("ma10")),
           ("MA20", indicators.get("ma20")), ("MA60", indicators.get("ma60"))]
    ma_parts = []
    for label, val in mas:
        if val is not None:
            ma_parts.append(f"{label}={val:.2f}")
    if ma_parts:
        lines.append(f"  **均线**: {'  |  '.join(ma_parts)}")

    # MA alignment
    ma_vals = [(n, indicators.get(f"ma{n}")) for n in [5,10,20,60] if indicators.get(f"ma{n}") is not None]
    if len(ma_vals) >= 3:
        aligned = all(ma_vals[i][1] >= ma_vals[i+1][1] for i in range(len(ma_vals)-1))
        reversed_aligned = all(ma_vals[i][1] <= ma_vals[i+1][1] for i in range(len(ma_vals)-1))
        if aligned:
            lines.append(f"  **均线排列**: 多头排列 📈 (MA5≥MA10≥MA20≥MA60)")
        elif reversed_aligned:
            lines.append(f"  **均线排列**: 空头排列 📉 (MA5≤MA10≤MA20≤MA60)")
        else:
            lines.append(f"  **均线排列**: 交叉缠绕 ⚠️ (趋势不明确)")

    # MACD
    macd = indicators.get("macd", {})
    if macd:
        dif = macd.get("dif", 0)
        dea = macd.get("dea", 0)
        bar = macd.get("bar", 0)
        lines.append(f"  **MACD**: DIF={dif:.4f}  DEA={dea:.4f}  BAR={bar:.4f}")
        if dif > dea:
            lines.append(f"  **MACD状态**: DIF在DEA上方，多头主导 ↑")
        elif dif < dea:
            lines.append(f"  **MACD状态**: DIF在DEA下方，空头主导 ↓")
        if bar > 0:
            lines.append(f"  **MACD动能**: 红柱(BAR>0)，多头动能" + ("增强" if bar > 0 else "") + " ↑")
        else:
            lines.append(f"  **MACD动能**: 绿柱(BAR<0)，空头动能 ↓")

    # RSI
    rsi6 = indicators.get("rsi_6")
    rsi12 = indicators.get("rsi_12")
    if rsi6 is not None and rsi12 is not None:
        lines.append(f"  **RSI**: RSI(6)={rsi6:.2f}  RSI(12)={rsi12:.2f}")
        if rsi6 > 80:
            lines.append(f"  **RSI状态**: RSI(6)>80，超买区域 ⚠️ 注意回调风险")
        elif rsi6 < 20:
            lines.append(f"  **RSI状态**: RSI(6)<20，超卖区域 💡 关注反弹机会")
        elif rsi6 > 50:
            lines.append(f"  **RSI状态**: 偏强区域 (50-80)，多头占优")
        else:
            lines.append(f"  **RSI状态**: 偏弱区域 (20-50)，空头占优")

    # BOLL
    boll = indicators.get("boll", {})
    if boll.get("mid") is not None:
        lines.append(f"  **布林带**: 上轨={boll['upper']:.2f}  中轨={boll['mid']:.2f}  下轨={boll['lower']:.2f}")
        bandwidth = (boll['upper'] - boll['lower']) / boll['mid'] * 100 if boll['mid'] else 0
        lines.append(f"  **布林带宽度**: {bandwidth:.1f}% " +
                     ("(收窄→可能变盘)" if bandwidth < 5 else "(正常)" if bandwidth < 15 else "(扩张→高波动)"))

    # Summary
    lines.append(f"  **区间涨跌**: {summary.get('period_change', 0):.2f}%")
    lines.append(f"  **年化波动率**: {summary.get('volatility', 0):.2f}%")
    lines.append(f"  **平均成交量**: {summary.get('avg_volume', 0):,}")
    lines.append(f"  **区间最高/最低**: {summary.get('max_close', 0):.2f} / {summary.get('min_close', 0):.2f}")

    return lines


# ============================================================
# Core prompt generators
# ============================================================
def generate_prompt(
    formula: str,
    stock_code: str,
    stock_name: str,
    indicators: Dict[str, Any],
    summary: Dict[str, Any],
    extra_data: Optional[Dict[str, Any]] = None,
) -> str:
    """Generate a comprehensive AI analysis prompt from TDX formula + stock data.

    Args:
        formula: Raw TDX formula text.
        stock_code: 6-digit stock code.
        stock_name: Stock name in Chinese.
        indicators: Dict from calc_all_indicators().
        summary: Dict from build_summary().
        extra_data: Optional dict with keys like 'weekly_indicators', 'monthly_indicators'
                    for multi-timeframe analysis.

    Returns:
        Natural language Chinese prompt ready for AI analysis.
    """
    extracted = extract_indicators(formula)

    parts = [
        f"# A股技术分析任务",
        "",
        f"请对 **{stock_code} {stock_name}** 进行技术分析，结合以下选股公式逐条判断是否满足条件。",
        "",
        "## 当前技术指标",
        "",
    ]
    parts.extend(_fmt_indicators(indicators, summary))

    # Multi-timeframe
    if extra_data:
        parts.extend(["", "## 🔄 多周期数据"])
        for key, label in [("weekly_indicators", "周线"), ("monthly_indicators", "月线")]:
            if key in extra_data and extra_data[key]:
                wi = extra_data[key]
                parts.append(f"")
                parts.append(f"### {label}")
                parts.append(f"  MA5={wi['ma5']:.2f}  MA20={wi['ma20']:.2f}  " if wi.get('ma5') else "  数据不足")
                if wi.get("macd"):
                    m = wi["macd"]
                    parts.append(f"  MACD: DIF={m['dif']:.4f} DEA={m['dea']:.4f} BAR={m['bar']:.4f}")

    parts.extend([
        "",
        "---",
        "",
        "## 🧩 选股公式解析",
        f"```",
        formula.strip(),
        f"```",
        "",
        "公式包含以下要素：",
    ])
    for item in extracted:
        parts.append(f"  - **{item['type']}**: `{item['detail']}`")
    if not extracted:
        parts.append("  (未能自动解析，请人工理解公式意图)")

    parts.extend([
        "",
        "## 分析框架",
        "",
        "1. **趋势**: 均线排列 + MACD方向 → 上升/下降/震荡",
        "2. **支撑压力**: BOLL带 + 均线 + 区间极值 → 关键价位",
        "3. **量价**: 成交量趋势 + 价格配合度 → 放量/缩量判断",
        "4. **动量**: RSI超买超卖 + 波动率 → 风险程度",
        "5. **形态**: 金叉/死叉/顶底背离/突破信号",
        "",
        "## 选股条件逐条判断",
        "",
        "请对公式中的每个条件给出明确结论：",
        "",
        "| 条件 | 是否满足 | 依据 | 置信度 |",
        "|------|----------|------|--------|",
    ])

    for item in extracted:
        parts.append(f"| {item['detail'][:40]} | 是/否 | (给出具体数值) | 高/中/低 |")

    parts.extend([
        "",
        "## 综合结论",
        "",
        "| 评分项 | 得分 | 说明 |",
        "|--------|------|------|",
        "| 趋势 | _/3 | |",
        "| 动量 | _/3 | |",
        "| 量价 | _/2 | |",
        "| 位置 | _/2 | |",
        "| **总分** | **_/10** | |",
        "",
        "### 操作建议",
        "- 方向: 买入/持有/减仓/观望",
        "- 仓位: 轻(1-3成)/中(4-6成)/重(7-10成)",
        "- 入场: _ 元",
        "- 止损: _ 元",
        "- 目标: _ 元",
        "",
        "> 以上分析仅供参考，不构成投资建议。股市有风险，投资需谨慎。",
    ])

    return "\n".join(parts)


# ============================================================
# Module wrapper
# ============================================================
from core.registry import BaseModule


class PromptModule(BaseModule):
    """AI prompt generation module — wraps formula prompt generators.

    Exposes generate_prompt and quick_analysis_prompt as JS-callable
    API methods via the module registry.
    """

    name = "AI分析"
    description = "通达信公式 → AI分析提示词生成器"
    version = "2.1"

    def get_api_methods(self) -> dict:
        return {
            "generate_prompt": self._api_generate_prompt,
            "quick_analysis_prompt": self._api_quick_analysis_prompt,
        }

    def get_panel_tab(self) -> dict:
        """Return the AI analysis tab definition."""
        return {
            "id": "tab-formula",
            "title": "🤖 AI分析",
            "html": r"""
<div class='main-area'>
  <div class='card'>
    <div class='card-title' style='font-size:13px;margin-bottom:10px;'>🤖 通达信公式 → AI分析提示词</div>
    <div style='font-size:12px;color:var(--text2);margin-bottom:8px;'>
      将通达信选股公式粘贴到下方，系统会自动解析公式要素，结合当前股票的技术指标，
      生成一份专业的AI分析提示词。将提示词粘贴到 ChatGPT / DeepSeek / Claude 对话框即可获得分析。
    </div>
    <textarea id='formulaInput' placeholder='在此粘贴通达信选股公式&#10;例如: CROSS(MA(收盘价,5), MA(收盘价,20)) AND RSI(6) 大于 50&#10;&#10;支持: MA均线 / MACD / RSI / BOLL布林带 / CROSS金叉死叉 / 比较运算'></textarea>
    <div class='card-actions' style='margin-top:10px;'>
      <button class='btn-primary' onclick='onGeneratePrompt()'>✨ 生成选股分析提示词</button>
      <button onclick='onQuickAnalyze()'>📊 快速技术分析（无需公式）</button>
      <button onclick="document.getElementById('formulaInput').value=''">清空公式</button>
    </div>
    <div style='font-size:10px;color:var(--text3);margin-top:6px;'>
      提示词将自动复制到剪贴板，直接粘贴到AI对话框使用。生成前请先查询股票数据。
    </div>
  </div>
</div>""",
        }

    # ---- Internal API handlers ----

    def _api_generate_prompt(self, formula_text: str) -> dict:
        """JS-exposed: generate a formula-based analysis prompt."""
        import traceback
        try:
            import pyperclip
            detail = self._clipper.get_result_detail()
            if not detail or not detail.get("meta") or not detail["meta"].get("code"):
                return {"success": False, "error": "暂无股票数据，请先在搜索框输入代码查询"}
            prompt = generate_prompt(
                formula=formula_text,
                stock_code=detail["meta"]["code"],
                stock_name=detail["meta"].get("name", "未知"),
                indicators=detail.get("indicators", {}),
                summary=detail.get("summary", {}),
            )
            pyperclip.copy(prompt)
            return {"success": True}
        except Exception as e:
            return {"success": False, "error": str(e), "detail": traceback.format_exc()}

    def _api_quick_analysis_prompt(self) -> dict:
        """JS-exposed: generate a quick analysis prompt without formula."""
        import traceback
        try:
            import pyperclip
            detail = self._clipper.get_result_detail()
            if not detail or not detail.get("meta") or not detail["meta"].get("code"):
                return {"success": False, "error": "暂无股票数据，请先在搜索框输入代码查询"}
            prompt = generate_quick_prompt(
                code=detail["meta"]["code"],
                name=detail["meta"].get("name", "未知"),
                indicators=detail.get("indicators", {}),
                summary=detail.get("summary", {}),
            )
            pyperclip.copy(prompt)
            return {"success": True}
        except Exception as e:
            return {"success": False, "error": str(e), "detail": traceback.format_exc()}


def generate_quick_prompt(
    code: str,
    name: str,
    indicators: Dict[str, Any],
    summary: Dict[str, Any],
    extra_data: Optional[Dict[str, Any]] = None,
) -> str:
    """Generate a generic comprehensive analysis prompt (no formula)."""
    return generate_prompt(
        formula="(无特定公式 — 全维度技术分析)",
        stock_code=code,
        stock_name=name,
        indicators=indicators,
        summary=summary,
        extra_data=extra_data,
    )
