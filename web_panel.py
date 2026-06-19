"""
web_panel.py — Lightweight info panel using PyWebView for Stock JSON Clipper V1.0.

Displays:
  - Title bar with version
  - Status indicator (monitoring / fetching)
  - History table (last 5 entries)
  - Settings: output format, default count
  - Formula input → Prompt generator

The panel runs as a PyWebView window (400×500, resizable, not always-on-top).
Closing the panel hides it — it does not exit the application.

JS ↔ Python bridge via webview.expose() API.
"""

import json
import threading
from typing import TYPE_CHECKING, Any, Dict, List

import webview

if TYPE_CHECKING:
    from stock_clipper import StockClipper


# --- HTML template ---
PANEL_HTML = r"""
<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<style>
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body {
    font-family: "Microsoft YaHei", "PingFang SC", "Helvetica Neue", sans-serif;
    font-size: 13px;
    background: #1e1e2e;
    color: #cdd6f4;
    padding: 16px;
    overflow-x: hidden;
  }
  h1 { font-size: 16px; text-align: center; margin-bottom: 4px; color: #89b4fa; }
  .subtitle { text-align: center; font-size: 11px; color: #6c7086; margin-bottom: 12px; }

  /* Status */
  .status-bar {
    display: flex; align-items: center; gap: 8px;
    padding: 8px 12px; border-radius: 8px; margin-bottom: 12px;
    background: #313244; font-size: 12px;
  }
  .status-dot { width: 10px; height: 10px; border-radius: 50%; flex-shrink: 0; }
  .status-dot.monitoring { background: #a6e3a1; box-shadow: 0 0 6px #a6e3a1; }
  .status-dot.fetching { background: #f9e2af; box-shadow: 0 0 6px #f9e2af; animation: pulse 0.8s infinite; }
  @keyframes pulse { 0%,100% { opacity: 1; } 50% { opacity: 0.3; } }

  /* Sections */
  .section {
    background: #313244; border-radius: 10px; padding: 12px; margin-bottom: 10px;
  }
  .section-title {
    font-size: 13px; font-weight: bold; color: #cba6f7; margin-bottom: 8px;
    display: flex; align-items: center; gap: 6px;
  }

  /* History table */
  table { width: 100%; border-collapse: collapse; font-size: 11px; }
  th { text-align: left; padding: 4px 6px; border-bottom: 1px solid #45475a; color: #a6adc8; font-weight: normal; }
  td { padding: 4px 6px; border-bottom: 1px solid #313244; }
  .status-success { color: #a6e3a1; }
  .status-error { color: #f38ba8; }
  .status-cached { color: #89b4fa; }
  .status-pending { color: #f9e2af; }
  .empty-row { text-align: center; color: #6c7086; padding: 16px; }

  /* Settings */
  label { color: #a6adc8; font-size: 12px; margin-right: 6px; }
  select, input[type="number"] {
    background: #1e1e2e; color: #cdd6f4; border: 1px solid #45475a;
    border-radius: 4px; padding: 4px 8px; font-size: 12px; margin-right: 12px;
  }
  input[type="number"] { width: 70px; }
  .btn-row { display: flex; gap: 8px; margin-top: 8px; }

  /* Buttons */
  button {
    background: #45475a; color: #cdd6f4; border: none;
    border-radius: 6px; padding: 6px 14px; font-size: 12px; cursor: pointer;
    transition: background 0.15s;
  }
  button:hover { background: #585b70; }
  button.primary { background: #89b4fa; color: #1e1e2e; font-weight: bold; }
  button.primary:hover { background: #74c7ec; }
  button:disabled { opacity: 0.4; cursor: not-allowed; }

  textarea {
    width: 100%; height: 80px; background: #1e1e2e; color: #cdd6f4;
    border: 1px solid #45475a; border-radius: 6px; padding: 8px;
    font-size: 12px; font-family: "Cascadia Code", "Consolas", monospace;
    resize: vertical;
  }

  /* Footer */
  .footer {
    text-align: center; color: #6c7086; font-size: 10px; margin-top: 8px;
  }
</style>
</head>
<body>

<h1>📈 Stock JSON Clipper V1.0</h1>
<div class="subtitle">剪贴板驱动 · 一键JSON · AI就绪</div>

<!-- Status -->
<div class="status-bar">
  <div class="status-dot monitoring" id="statusDot"></div>
  <span id="statusText">🟢 监控中...</span>
</div>

<!-- History -->
<div class="section">
  <div class="section-title">📋 最近记录</div>
  <table>
    <thead><tr><th>时间</th><th>代码</th><th>名称</th><th>状态</th></tr></thead>
    <tbody id="historyBody">
      <tr class="empty-row"><td colspan="4">暂无记录 — 在通达信复制股票代码即可</td></tr>
    </tbody>
  </table>
</div>

<!-- Settings -->
<div class="section">
  <div class="section-title">⚙️ 设置</div>
  <div style="display:flex; align-items:center; flex-wrap:wrap; gap:10px;">
    <div>
      <label>输出格式:</label>
      <select id="outputFormat" onchange="onConfigChange('output_format', this.value)">
        <option value="json" selected>JSON</option>
        <option value="markdown" disabled>Markdown (开发中)</option>
        <option value="csv" disabled>CSV (开发中)</option>
      </select>
    </div>
    <div>
      <label>数据条数:</label>
      <input type="number" id="defaultCount" min="5" max="9999" value="250"
             onchange="onConfigChange('default_count', parseInt(this.value))">
    </div>
  </div>
  <div class="btn-row">
    <button onclick="onClearCache()">🔄 清空缓存</button>
  </div>
</div>

<!-- Formula -->
<div class="section">
  <div class="section-title">🤖 公式辅助</div>
  <textarea id="formulaInput" placeholder="在此粘贴通达信选股公式..."></textarea>
  <div class="btn-row" style="margin-top:8px;">
    <button class="primary" onclick="onGeneratePrompt()">✨ 生成Prompt</button>
    <button onclick="onClearFormula()">清空</button>
  </div>
</div>

<div class="footer">Stock JSON Clipper V1.0 · Open Source</div>

<script>
// --- JS ↔ Python bridge ---
// These functions are injected by pywebview.expose on the Python side.

function refreshHistory() {
  pywebview.api.get_history().then(function(data) {
    var tbody = document.getElementById('historyBody');
    if (!data || data.length === 0) {
      tbody.innerHTML = '<tr class="empty-row"><td colspan="4">暂无记录 — 在通达信复制股票代码即可</td></tr>';
      return;
    }
    var rows = '';
    data.forEach(function(r) {
      var cls = 'status-' + (r.status || 'pending');
      var label = r.status === 'success' ? '✅' :
                  r.status === 'error' ? '❌' :
                  r.status === 'cached' ? '📦' : '⏳';
      var name = r.name || '-';
      rows += '<tr><td>' + r.time + '</td><td>' + r.code + '</td><td>' + name + '</td>'
            + '<td class="' + cls + '">' + label + ' ' + (r.message || r.status) + '</td></tr>';
    });
    tbody.innerHTML = rows;
  });
}

function refreshStatus() {
  pywebview.api.get_status().then(function(status) {
    var dot = document.getElementById('statusDot');
    var text = document.getElementById('statusText');
    if (status === 'fetching') {
      dot.className = 'status-dot fetching';
      text.innerText = '⏳ 拉取数据中...';
    } else {
      dot.className = 'status-dot monitoring';
      text.innerText = '🟢 监控中...';
    }
  });
}

function loadConfig() {
  pywebview.api.get_config().then(function(cfg) {
    if (cfg) {
      document.getElementById('outputFormat').value = cfg.output_format || 'json';
      document.getElementById('defaultCount').value = cfg.default_count || 250;
    }
  });
}

function onConfigChange(key, value) {
  pywebview.api.set_config(key, value);
}

function onClearCache() {
  pywebview.api.clear_cache();
  alert('缓存已清空 ✅');
}

function onGeneratePrompt() {
  var formula = document.getElementById('formulaInput').value.trim();
  if (!formula) {
    alert('请先粘贴通达信选股公式！');
    return;
  }
  pywebview.api.generate_prompt(formula).then(function(result) {
    if (result && result.success) {
      alert('✅ Prompt 已生成并复制到剪贴板！\n直接粘贴到 AI 对话框即可。');
    } else {
      alert('❌ 生成失败: ' + (result ? result.error : '未知错误'));
    }
  });
}

function onClearFormula() {
  document.getElementById('formulaInput').value = '';
}

// Periodic refresh (every 3 seconds)
setInterval(function() {
  refreshHistory();
  refreshStatus();
}, 3000);

// Initial load
document.addEventListener('DOMContentLoaded', function() {
  loadConfig();
  refreshHistory();
  refreshStatus();
});
</script>
</body>
</html>
"""


# --- Python-side API exposed to JS ---
class PanelAPI:
    """API class exposed to the PyWebView JavaScript context."""

    def __init__(self, clipper: "StockClipper") -> None:
        self._clipper = clipper

    def get_history(self) -> List[Dict[str, Any]]:
        return self._clipper.get_history()

    def get_config(self) -> Dict[str, Any]:
        cfg = self._clipper.get_config()
        return {
            "output_format": cfg.get("output_format", "json"),
            "default_count": cfg.get("default_count", 250),
        }

    def set_config(self, key: str, value: Any) -> None:
        self._clipper.set_config(key, value)

    def clear_cache(self) -> None:
        self._clipper.clear_cache()

    def get_status(self) -> str:
        return self._clipper.get_status()

    def generate_prompt(self, formula_text: str) -> Dict[str, Any]:
        """Generate AI prompt from TDX formula text.

        Args:
            formula_text: User-pasted TDX formula.

        Returns:
            Dict with 'success' bool and 'error' string (if failed).
        """
        try:
            from formula_prompt import generate_prompt
            import pyperclip

            last = self._clipper.get_last_result()
            if last is None:
                return {"success": False, "error": "暂无股票数据，请先在通达信复制股票代码触发一次数据提取"}

            # Get the cached data to extract indicators
            cache = self._clipper._cache
            indicators = {}
            summary = {}

            # Try to get from last result's cached JSON
            cache_key = cache.make_key(last.code, last.period)
            cached_json = cache.get(cache_key)
            if cached_json:
                import json
                data = json.loads(cached_json)
                indicators = data.get("indicators", {})
                summary = data.get("summary", {})

            prompt = generate_prompt(
                formula=formula_text,
                stock_code=last.code,
                stock_name=last.name or "未知",
                indicators=indicators,
                summary=summary,
            )

            pyperclip.copy(prompt)
            return {"success": True}
        except Exception as e:
            return {"success": False, "error": str(e)}


# --- Panel manager ---
_panel_window: "webview.Window | None" = None
_panel_lock = threading.Lock()


def show_panel(clipper: "StockClipper") -> None:
    """Show or focus the info panel.

    Creates a new PyWebView window if one doesn't exist, otherwise
    brings the existing window to front.

    Args:
        clipper: StockClipper instance for API access.
    """
    global _panel_window

    with _panel_lock:
        # If window exists, try to bring it to front
        if _panel_window is not None:
            try:
                _panel_window.show()
                _panel_window.restore()
                return
            except Exception:
                _panel_window = None

        # Create new window
        api = PanelAPI(clipper)
        _panel_window = webview.create_window(
            title="Stock JSON Clipper V1.0",
            html=PANEL_HTML,
            width=420,
            height=560,
            resizable=True,
            on_top=False,
            js_api=api,
        )

        # Start webview in a daemon thread so it doesn't block tray
        def _on_closed():
            global _panel_window
            _panel_window = None

        _panel_window.events.closed += _on_closed
        webview.start(gui=None, debug=False)
