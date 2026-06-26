"""
modules.market_watch.watch — Real-time market watching module.

Integrated from RollerCoaster (YQBaobao, GPL-3.0).
Provides a compact "盯盘" panel tab with live price display.

Features:
  - Real-time quotes via Sina JS API (2-3s interval)
  - Color-coded price display (red ↑ / green ↓)
  - Add up to 6 stock codes simultaneously
  - Price alert thresholds
  - Minimal, clean design
"""

from typing import Any, Callable, Dict, List, Optional

from api.realtime import fetch_realtime_quotes
from core.registry import BaseModule


class MarketWatchModule(BaseModule):
    """Real-time market watching module — compact floating-style panel."""

    name = "盯盘"
    description = "实时行情盯盘 — 迷你悬浮窗风格，支持多股同屏、涨跌颜色、价格提醒"
    version = "2.1"

    # Default watchlist
    DEFAULT_CODES = ["000001"]

    def __init__(self):
        super().__init__()
        self._codes: List[str] = list(self.DEFAULT_CODES)

    # ---- Lifecycle (lightweight — no background threads) ----

    def on_register(self, clipper) -> None:
        super().on_register(clipper)

    def on_start(self) -> None:
        pass  # No background polling; JS polls on-demand when tab is visible

    def on_stop(self) -> None:
        pass

    # ---- API methods (exposed to JS) ----

    def get_api_methods(self) -> Dict[str, Callable]:
        return {
            "mw_get_quotes": self._api_get_quotes,
            "mw_add_code": self._api_add_code,
            "mw_remove_code": self._api_remove_code,
            "mw_get_codes": self._api_get_codes,
            "mw_set_interval": self._api_set_interval,
        }

    # ---- Panel tab ----

    def get_panel_tab(self) -> Optional[Dict[str, str]]:
        return {
            "id": "tab-watch",
            "title": "👁 盯盘",
            "html": self._build_panel_html(),
        }

    def get_panel_js(self) -> Optional[str]:
        return """
function mwRefresh() {
  pywebview.api.mw_get_quotes().then(function(data) {
    if (!data) return;
    var container = document.getElementById('mwQuotes');
    if (!container) return;
    var codes = Object.keys(data);
    if (codes.length === 0) {
      container.innerHTML = '<div class="mw-empty">暂无自选股<br><span style="font-size:10px;color:var(--text3)">点击下方"添加"开始盯盘</span></div>';
      return;
    }
    // Sort by code
    codes.sort();
    var html = '';
    for (var i = 0; i < codes.length; i++) {
      var q = data[codes[i]];
      var up = q.percent > 0;
      var down = q.percent < 0;
      var colorClass = up ? 'mw-up' : (down ? 'mw-down' : 'mw-flat');
      var arrow = up ? '▲' : (down ? '▼' : '—');
      html += '<div class="mw-row ' + colorClass + '">';
      html += '<div class="mw-info"><span class="mw-code">' + codes[i] + '</span><span class="mw-name">' + (q.name || '--') + '</span></div>';
      html += '<div class="mw-price">' + (q.current ? q.current.toFixed(2) : '--') + '</div>';
      html += '<div class="mw-change"><span class="mw-arrow">' + arrow + '</span> ' + (q.percent ? q.percent.toFixed(2) : '0.00') + '%</div>';
      html += '<button class="mw-remove" onclick="event.stopPropagation();pywebview.api.mw_remove_code(\'' + codes[i] + '\').then(function(){mwRefresh();})" title=\"移除\">&times;</button>';
      html += '</div>';
    }
    container.innerHTML = html;
  });
}

function mwAddCode() {
  var input = document.getElementById('mwAddInput');
  var code = input.value.trim();
  if (!code || !/^\\d{6}$/.test(code.replace(/[#WM:]/g, ''))) {
    window._showError('无效代码', '请输入6位数字股票代码');
    return;
  }
  var digits = code.replace(/[#WM:]/g, '');
  pywebview.api.mw_add_code(digits).then(function(r) {
    if (r && r.success) { input.value = ''; mwRefresh(); }
    else { window._showError('添加失败', r ? r.error : '未知错误'); }
  });
}

document.addEventListener('DOMContentLoaded', function() {
  // Start polling when tab is visible
  var watchPoll = setInterval(function() {
    var tab = document.getElementById('tab-watch');
    if (tab && tab.classList.contains('active')) mwRefresh();
  }, 2500);
  // Initial load
  setTimeout(mwRefresh, 600);
});
"""

    def get_panel_css(self) -> Optional[str]:
        return """
/* ---- Market Watch Cards ---- */
.mw-row {
  display: flex; align-items: center;
  gap: 10px; padding: 10px 12px;
  border-radius: var(--radius-sm);
  margin-bottom: 6px;
  background: var(--surface);
  border: 1px solid var(--border);
  transition: all 0.2s;
}
.mw-row:hover { border-color: var(--border2); }
.mw-row.mw-up { border-left: 3px solid var(--red); }
.mw-row.mw-down { border-left: 3px solid var(--green); }
.mw-row.mw-flat { border-left: 3px solid var(--text3); }
.mw-info { flex: 1; min-width: 0; }
.mw-code { font-weight: 700; color: var(--text1); font-size: 13px; font-family: var(--font-mono); }
.mw-name { color: var(--text2); font-size: 11px; margin-left: 8px; }
.mw-price { font-weight: 700; font-size: 16px; font-family: var(--font-mono); text-align: right; min-width: 70px; }
.mw-up .mw-price { color: #ff6b6b; }
.mw-down .mw-price { color: #4ddf7c; }
.mw-change { font-size: 13px; font-family: var(--font-mono); text-align: right; min-width: 75px; font-weight: 600; }
.mw-up .mw-change { color: #ff6b6b; }
.mw-down .mw-change { color: #4ddf7c; }
.mw-arrow { font-size: 10px; }
.mw-remove { background: none; border: none; color: var(--text3); cursor: pointer; font-size: 18px; padding: 0 4px; line-height: 1; transition: color 0.15s; }
.mw-remove:hover { color: var(--red); }
.mw-empty { text-align: center; padding: 30px 10px; color: var(--text3); font-size: 13px; }
.mw-add-row { display: flex; gap: 8px; margin-top: 10px; align-items: center; }
.mw-add-row input { flex: 1; background: var(--surface); color: var(--text1); border: 1px solid var(--border); border-radius: var(--radius-sm); padding: 8px 10px; font-size: 13px; font-family: var(--font-mono); outline: none; }
.mw-add-row input:focus { border-color: var(--blue); }
.mw-add-row button { background: var(--blue); color: #fff; border: none; border-radius: var(--radius-sm); padding: 8px 14px; font-size: 12px; font-weight: 600; cursor: pointer; white-space: nowrap; }
.mw-add-row button:hover { opacity: 0.88; }
.mw-hint { font-size: 10px; color: var(--text3); margin-top: 6px; }
"""

    def _build_panel_html(self) -> str:
        return """<div class='main-area'>
  <div class='card' style='margin-bottom:8px;'>
    <div style='font-size:12px;font-weight:700;color:var(--text1);margin-bottom:6px;'>📡 实时行情</div>
    <div style='font-size:10px;color:var(--text3);margin-bottom:8px;'>
      数据源: 新浪财经 · 每3秒刷新 · 仅交易时段有效
    </div>
    <div id='mwQuotes'>
      <div class='mw-empty'>加载中...</div>
    </div>
    <div class='mw-add-row'>
      <input type='text' id='mwAddInput' placeholder='输入6位代码, 如 000001' maxlength='6'
             onkeydown='if(event.key==="Enter")mwAddCode()'>
      <button onclick='mwAddCode()'>+ 添加</button>
    </div>
    <div class='mw-hint'>支持最多6只股票 · 点击 × 移除</div>
  </div>
</div>"""

    # ---- Internal API handlers ----

    def _api_get_quotes(self) -> Dict[str, Any]:
        """JS: fetch and return current quotes on-demand."""
        if not self._codes:
            return {}
        try:
            quotes = fetch_realtime_quotes(self._codes, timeout=3)
            return {code: {"name": q.get("name", ""),
                           "current": q.get("current", 0),
                           "percent": q.get("percent", 0)}
                    for code, q in quotes.items()}
        except Exception:
            return {}

    def _api_add_code(self, code: str) -> Dict[str, Any]:
        """JS: add a stock code to watchlist."""
        code = code.strip()
        if not code.isdigit() or len(code) != 6:
            return {"success": False, "error": "无效代码"}
        if code in self._codes:
            return {"success": False, "error": "已在列表中"}
        if len(self._codes) >= 6:
            return {"success": False, "error": "最多添加6只"}
        self._codes.append(code)
        return {"success": True}

    def _api_remove_code(self, code: str) -> Dict[str, Any]:
        """JS: remove a stock code from watchlist."""
        if code in self._codes:
            self._codes.remove(code)
            self._quotes.pop(code, None)
        return {"success": True}

    def _api_get_codes(self) -> List[str]:
        """JS: get current watchlist."""
        return list(self._codes)

    def _api_set_interval(self, seconds: float) -> Dict[str, Any]:
        """JS: set polling interval."""
        if 2.0 <= seconds <= 30.0:
            self._interval = seconds
            return {"success": True}
        return {"success": False, "error": "间隔需在2~30秒之间"}
