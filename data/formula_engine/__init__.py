"""
formula_engine — Zero-dependency TDX formula engine for Stock JSON Clipper.

Unified entry point:
    prepare(klines_map, stock_info_map, formula, ...) → AnalysisPackage

Usage:
    from data.formula_engine import prepare

    pkg = prepare(
        klines_map={"SH600519": [{date, open, high, low, close, volume}, ...]},
        stock_info_map={"SH600519": {"name": "贵州茅台", "market": "沪市"}},
        formula="CROSS(MA(C,5), MA(C,20)) & RSI(6) > 50",
    )

    # For LLM API:
    json_str = pkg.to_json()

    # For copy-paste:
    prompt = pkg.to_prompt()
"""

import json
from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional

from data.formula_engine.series import compute_all_series
from data.formula_engine.elements import parse_formula
from data.formula_engine.comparator import (
    build_comparison_table,
    build_formula_comparison,
)
from data.formula_engine.formatter import to_json, to_prompt


# ============================================================
# Dataclasses
# ============================================================

@dataclass
class StockMeta:
    """Metadata for a single stock in the analysis package."""
    code: str
    name: str
    market: str
    period: str = "daily"
    bar_count: int = 0
    start_date: str = ""
    end_date: str = ""


@dataclass
class FormulaElement:
    """A single parsed element from a TDX formula."""
    order: int
    raw: str
    label_cn: str
    element_type: str          # "cross" | "compare" | "statistical" | "opaque"
    variables: List[str] = field(default_factory=list)
    logic_op: Optional[str] = None  # "&" | "|" | None
    current: Dict[str, Any] = field(default_factory=dict)
    events: List[Dict[str, Any]] = field(default_factory=list)
    sequence: Dict[str, List[Any]] = field(default_factory=dict)


@dataclass
class FormulaResult:
    """Parsed formula with elements."""
    raw: str
    elements: List[FormulaElement] = field(default_factory=list)


@dataclass
class AnalysisPackage:
    """Complete analysis package — unified output of the formula engine.

    Scenarios:
      - "single"           1 stock, no formula
      - "single_formula"   1 stock + formula
      - "multi"            2-6 stocks, no formula
      - "multi_formula"    2-6 stocks + formula
    """
    scenario: str
    stocks: List[StockMeta] = field(default_factory=list)
    klines: Dict[str, List[Dict[str, Any]]] = field(default_factory=dict)
    series: Dict[str, Dict[str, List[Optional[float]]]] = field(default_factory=dict)
    formula: Optional[FormulaResult] = None
    comparison: Optional[Dict[str, Any]] = None
    warnings: List[str] = field(default_factory=list)

    def to_json(self, compact: bool = False) -> str:
        """Serialize to structured JSON for LLM API consumption.

        Args:
            compact: If True, use compact encoding (no indent).

        Returns:
            JSON string.
        """
        return to_json(self, compact=compact)

    def to_prompt(self, days: int = 60) -> str:
        """Build a markdown prompt for user copy-paste.

        Args:
            days: Number of recent days of data to include.

        Returns:
            Markdown string.
        """
        return to_prompt(self, days=days)


# ============================================================
# Public entry point
# ============================================================

def prepare(
    klines_map: Dict[str, List[Dict[str, Any]]],
    stock_info_map: Dict[str, Dict[str, Any]],
    formula: Optional[str] = None,
    *,
    series_days: int = 60,
    include_full_klines: bool = True,
) -> AnalysisPackage:
    """Prepare a complete analysis package from stock K-lines and optional formula.

    Automatically detects scenario (single / multi × with / without formula),
    computes all indicator series, parses the formula (if provided), detects
    events, and builds comparison tables for multi-stock scenarios.

    Args:
        klines_map:
            Dict of stock_code → [{date, open, high, low, close, volume}, ...].
            Codes should have SH/SZ prefix (e.g. "SH600519", "SZ000001").
        stock_info_map:
            Dict of stock_code → {name, market, industry, pe_ttm, total_mv, ...}.
            At minimum, "name" is required.
        formula:
            Optional TDX formula string (may contain Chinese). If None or empty,
            scenario is treated as "no formula".
        series_days:
            Number of recent days to include in element sequences. Default 60.
            Reduced to 30 automatically for multi-stock scenarios.
        include_full_klines:
            Whether to include full K-line data in the package. Default True.

    Returns:
        AnalysisPackage with all computed data, ready for to_json() or to_prompt().

    Raises:
        ValueError: If klines_map is empty or contains > 6 stocks.
    """
    if not klines_map:
        raise ValueError("klines_map must not be empty")

    if len(klines_map) > 6:
        raise ValueError(f"Maximum 6 stocks supported, got {len(klines_map)}")

    is_multi = len(klines_map) > 1
    has_formula = bool(formula and formula.strip())

    # Determine scenario
    if is_multi and has_formula:
        scenario = "multi_formula"
    elif is_multi:
        scenario = "multi"
    elif has_formula:
        scenario = "single_formula"
    else:
        scenario = "single"

    # For multi-stock, reduce series_days to 30
    effective_series_days = 30 if is_multi else series_days

    warnings: List[str] = []

    # ── Build StockMeta list ──
    stocks: List[StockMeta] = []
    for code in klines_map:
        klines = klines_map[code]
        info = stock_info_map.get(code, {})
        start_date = klines[0].get("date", "") if klines else ""
        end_date = klines[-1].get("date", "") if klines else ""

        # Check for potential suspension (last trade > 7 days ago)
        if end_date:
            import datetime as _dt
            try:
                last_dt = _dt.datetime.strptime(end_date, "%Y-%m-%d")
                days_since = (_dt.datetime.now() - last_dt).days
                if days_since > 7:
                    warnings.append(f"{code} 最后交易日为{end_date}(距今{days_since}天)，可能停牌")
            except (ValueError, TypeError):
                pass

        stocks.append(StockMeta(
            code=code,
            name=info.get("name", code),
            market=info.get("market", "未知"),
            period=info.get("period", "daily"),
            bar_count=len(klines),
            start_date=start_date,
            end_date=end_date,
        ))

    # ── Compute series for each stock ──
    series_map: Dict[str, Dict[str, List[Optional[float]]]] = {}
    for code, klines in klines_map.items():
        try:
            series_map[code] = compute_all_series(klines)
        except Exception as e:
            warnings.append(f"{code} 指标计算失败: {e}")
            series_map[code] = {}

    # ── Check for insufficient data ──
    for code, klines in klines_map.items():
        if len(klines) < 20:
            warnings.append(f"{code} 数据量仅{len(klines)}条，均线计算受限")

    # ── Check for unequal bar counts ──
    if is_multi:
        counts = [len(klines) for klines in klines_map.values()]
        if len(set(counts)) > 1:
            codes_str = ", ".join(f"{c}({n})" for c, n in zip(klines_map.keys(), counts))
            warnings.append(f"各股数据条数不同({codes_str})，对比表基于各股独立计算")

    # ── Parse formula ──
    formula_result: Optional[FormulaResult] = None
    if has_formula:
        assert formula is not None
        # Parse against the first stock's series (formula elements are the same across stocks)
        first_code = list(klines_map.keys())[0]
        first_series = series_map.get(first_code, {})
        first_dates = [bar.get("date", "") for bar in klines_map.get(first_code, [])]

        try:
            element_dicts = parse_formula(
                formula, first_series, first_dates,
                sequence_days=effective_series_days,
            )
        except Exception as e:
            warnings.append(f"公式解析失败: {e}")
            element_dicts = []

        # Collect parse warnings
        if element_dicts and "_parse_warnings" in element_dicts[0]:
            warnings.extend(element_dicts[0].pop("_parse_warnings"))

        if not element_dicts:
            warnings.append("无法自动解析公式，请人工分析")

        elements = [
            FormulaElement(
                order=el.get("order", i),
                raw=el.get("raw", ""),
                label_cn=el.get("label_cn", ""),
                element_type=el.get("element_type", "opaque"),
                variables=el.get("variables", []),
                logic_op=el.get("logic_op"),
                current=el.get("current", {}),
                events=el.get("events", []),
                sequence=el.get("sequence", {}),
            )
            for i, el in enumerate(element_dicts)
        ]

        formula_result = FormulaResult(raw=formula, elements=elements)

    # ── Build comparison table (multi-stock only) ──
    comparison: Optional[Dict[str, Any]] = None
    if is_multi:
        comp_table = build_comparison_table(series_map, stock_info_map, klines_map)

        # Attach formula comparison if applicable
        formula_comp: Optional[List[Dict[str, Any]]] = None
        if formula_result and formula_result.elements:
            element_dicts_for_comp = [asdict(el) for el in formula_result.elements]
            formula_comp = build_formula_comparison(
                element_dicts_for_comp, series_map, stock_info_map
            )

        comparison = {
            "headers": comp_table.get("headers", []),
            "rows": comp_table.get("rows", []),
            "formula_comparison": formula_comp,
        }

    # ── Assemble ──
    pkg = AnalysisPackage(
        scenario=scenario,
        stocks=stocks,
        klines=klines_map,
        series=series_map,
        formula=formula_result,
        comparison=comparison,
        warnings=warnings,
    )

    return pkg
