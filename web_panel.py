"""
web_panel.py — Info panel using PyWebView for Stock JSON Clipper V2.0.

Redesigned with:
  - Manual stock code search bar (no longer clipboard-only)
  - Tabbed layout: Records / Settings / Formula
  - Result card with live indicator values
  - Modern dark theme with native-feel polish

JS ↔ Python bridge via webview.expose() API.
"""

import json
import threading
from typing import TYPE_CHECKING, Any, Dict, List, Optional

import webview

if TYPE_CHECKING:
    from stock_clipper import StockClipper


# ============================================================
# HTML Template
# ============================================================
PANEL_HTML = r"""
<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<style>
  :root {
    --bg: #1a1a24;
    --surface: #232336;
    --surface2: #2c2c42;
    --border: #35354f;
    --text: #c8c8e0;
    --text2: #8e8ea8;
    --accent: #7c9ff5;
    --accent2: #5b7bd5;
    --green: #4cda8c;
    --red: #f54b6a;
    --yellow: #f0c24b;
    --purple: #b89df0;
    --radius: 10px;
    --radius-sm: 6px;
    --shadow: 0 2px 12px rgba(0,0,0,0.3);
  }

  * { box-sizing: border-box; margin: 0; padding: 0; }

  body {
    font-family: -apple-system, BlinkMacSystemFont, "Microsoft YaHei", "PingFang SC",
                 "Segoe UI", "Helvetica Neue", sans-serif;
    font-size: 13px;
    background: var(--bg);
    color: var(--text);
    padding: 0;
    overflow-x: hidden;
    user-select: none;
    -webkit-user-select: none;
  }

  /* ---- Header ---- */
  .header {
    background: linear-gradient(135deg, #1e1e38 0%, #232348 100%);
    padding: 16px 20px 12px;
    text-align: center;
    border-bottom: 1px solid var(--border);
  }
  .header h1 {
    font-size: 17px;
    font-weight: 700;
    color: #fff;
    letter-spacing: 0.5px;
  }
  .header .tagline {
    font-size: 11px;
    color: var(--text2);
    margin-top: 3px;
  }

  /* ---- Search Bar ---- */
  .search-bar {
    display: flex;
    gap: 8px;
    padding: 12px 16px;
    background: var(--surface);
    border-bottom: 1px solid var(--border);
    align-items: center;
    flex-wrap: wrap;
  }
  .search-bar input[type="text"] {
    flex: 1;
    min-width: 100px;
    background: var(--bg);
    color: #fff;
    border: 1px solid var(--border);
    border-radius: var(--radius-sm);
    padding: 8px 12px;
    font-size: 14px;
    font-family: inherit;
    outline: none;
    transition: border-color 0.2s;
  }
  .search-bar input[type="text"]:focus {
    border-color: var(--accent);
    box-shadow: 0 0 0 3px rgba(124,159,245,0.15);
  }
  .search-bar select {
    background: var(--bg);
    color: var(--text);
    border: 1px solid var(--border);
    border-radius: var(--radius-sm);
    padding: 8px 10px;
    font-size: 13px;
    font-family: inherit;
    outline: none;
    cursor: pointer;
  }
  .search-bar button {
    background: var(--accent);
    color: #fff;
    border: none;
    border-radius: var(--radius-sm);
    padding: 8px 18px;
    font-size: 13px;
    font-weight: 600;
    cursor: pointer;
    transition: background 0.15s, transform 0.1s;
    font-family: inherit;
  }
  .search-bar button:hover { background: var(--accent2); }
  .search-bar button:active { transform: scale(0.97); }
  .search-bar button:disabled { opacity: 0.4; cursor: not-allowed; transform: none; }

  .save-toggle {
    display: flex;
    align-items: center;
    gap: 5px;
    font-size: 12px;
    color: var(--text2);
    cursor: pointer;
  }
  .save-toggle input { cursor: pointer; accent-color: var(--accent); }

  /* ---- Status bar ---- */
  .status-bar {
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 8px 20px;
    font-size: 12px;
    color: var(--text2);
    background: var(--bg);
  }
  .status-dot {
    width: 8px; height: 8px;
    border-radius: 50%;
    flex-shrink: 0;
    transition: background 0.3s;
  }
  .status-dot.monitoring { background: var(--green); box-shadow: 0 0 6px rgba(76,218,140,0.4); }
  .status-dot.fetching { background: var(--yellow); box-shadow: 0 0 6px rgba(240,194,75,0.5); animation: pulse 0.8s infinite; }
  @keyframes pulse { 0%,100% { opacity: 1; } 50% { opacity: 0.25; } }

  /* ---- Tabs ---- */
  .tabs {
    display: flex;
    gap: 0;
    padding: 0 16px;
    background: var(--surface);
    border-bottom: 1px solid var(--border);
  }
  .tab-btn {
    background: none;
    border: none;
    color: var(--text2);
    padding: 10px 16px;
    font-size: 13px;
    cursor: pointer;
    border-bottom: 2px solid transparent;
    transition: color 0.2s, border-color 0.2s;
    font-family: inherit;
  }
  .tab-btn:hover { color: var(--text); }
  .tab-btn.active {
    color: var(--accent);
    border-bottom-color: var(--accent);
  }

  /* ---- Tab content ---- */
  .tab-content { display: none; padding: 16px; }
  .tab-content.active { display: block; }

  /* ---- Result Card ---- */
  .result-card {
    background: var(--surface);
    border-radius: var(--radius);
    padding: 14px 16px;
    margin-bottom: 12px;
    border: 1px solid var(--border);
    box-shadow: var(--shadow);
  }
  .result-card .stock-title {
    font-size: 16px;
    font-weight: 700;
    color: #fff;
    margin-bottom: 4px;
  }
  .result-card .stock-meta {
    font-size: 11px;
    color: var(--text2);
    margin-bottom: 10px;
    display: flex;
    gap: 12px;
    flex-wrap: wrap;
  }
  .result-card .stock-meta span {
    background: var(--surface2);
    padding: 2px 8px;
    border-radius: 4px;
  }

  .indicator-grid {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 8px;
    margin-bottom: 10px;
  }
  .indicator-item {
    background: var(--surface2);
    border-radius: var(--radius-sm);
    padding: 8px 10px;
  }
  .indicator-item .label { font-size: 10px; color: var(--text2); text-transform: uppercase; }
  .indicator-item .value { font-size: 15px; font-weight: 700; color: #fff; font-variant-numeric: tabular-nums; }
  .indicator-item .value.up { color: var(--green); }
  .indicator-item .value.down { color: var(--red); }

  .card-actions {
    display: flex;
    gap: 8px;
  }
  .card-actions button {
    background: var(--surface2);
    color: var(--text);
    border: 1px solid var(--border);
    border-radius: var(--radius-sm);
    padding: 7px 14px;
    font-size: 12px;
    cursor: pointer;
    transition: all 0.15s;
    font-family: inherit;
  }
  .card-actions button:hover {
    background: var(--accent);
    color: #fff;
    border-color: var(--accent);
  }
  .card-actions button.primary {
    background: var(--accent);
    color: #fff;
    border-color: var(--accent);
  }
  .card-actions button.primary:hover { background: var(--accent2); }

  .empty-result {
    text-align: center;
    padding: 32px 16px;
    color: var(--text2);
    background: var(--surface);
    border-radius: var(--radius);
  }
  .empty-result .icon { font-size: 36px; margin-bottom: 8px; }
  .empty-result p { font-size: 12px; line-height: 1.6; }

  /* ---- History Table ---- */
  table {
    width: 100%;
    border-collapse: collapse;
    font-size: 12px;
  }
  th {
    text-align: left;
    padding: 6px 8px;
    border-bottom: 1px solid var(--border);
    color: var(--text2);
    font-weight: 500;
    font-size: 11px;
  }
  td { padding: 6px 8px; border-bottom: 1px solid var(--surface2); }
  .status-success { color: var(--green); }
  .status-error { color: var(--red); }
  .status-cached { color: var(--accent); }
  .status-pending { color: var(--yellow); }
  .empty-row { text-align: center; color: var(--text2); padding: 20px !important; }

  /* ---- Settings ---- */
  .setting-group {
    background: var(--surface);
    border-radius: var(--radius);
    padding: 14px 16px;
    margin-bottom: 10px;
    border: 1px solid var(--border);
  }
  .setting-group label {
    display: block;
    font-size: 11px;
    color: var(--text2);
    margin-bottom: 4px;
    text-transform: uppercase;
  }
  .setting-row {
    display: flex;
    align-items: center;
    gap: 10px;
    margin-bottom: 10px;
    flex-wrap: wrap;
  }
  .setting-row input[type="number"] {
    background: var(--bg);
    color: #fff;
    border: 1px solid var(--border);
    border-radius: var(--radius-sm);
    padding: 6px 10px;
    font-size: 13px;
    width: 90px;
    font-family: inherit;
    outline: none;
  }
  .setting-row input[type="number"]:focus { border-color: var(--accent); }
  .setting-row select {
    background: var(--bg);
    color: var(--text);
    border: 1px solid var(--border);
    border-radius: var(--radius-sm);
    padding: 6px 10px;
    font-size: 13px;
    font-family: inherit;
    outline: none;
  }

  .btn-row { display: flex; gap: 8px; margin-top: 6px; }
  .btn-row button {
    background: var(--surface2);
    color: var(--text);
    border: 1px solid var(--border);
    border-radius: var(--radius-sm);
    padding: 7px 14px;
    font-size: 12px;
    cursor: pointer;
    transition: all 0.15s;
    font-family: inherit;
  }
  .btn-row button:hover { background: #3c3c58; }
  .btn-row button.danger { color: var(--red); }
  .btn-row button.danger:hover { background: var(--red); color: #fff; border-color: var(--red); }

  /* ---- Formula ---- */
  textarea {
    width: 100%;
    min-height: 100px;
    background: var(--bg);
    color: var(--text);
    border: 1px solid var(--border);
    border-radius: var(--radius-sm);
    padding: 10px;
    font-size: 12px;
    font-family: "Cascadia Code", "Consolas", "Fira Code", monospace;
    resize: vertical;
    outline: none;
  }
  textarea:focus { border-color: var(--accent); }

  /* ---- Toast ---- */
  .toast {
    position: fixed;
    bottom: 20px;
    left: 50%;
    transform: translateX(-50%);
    background: #333;
    color: #fff;
    padding: 10px 24px;
    border-radius: 20px;
    font-size: 12px;
    opacity: 0;
    transition: opacity 0.3s;
    pointer-events: none;
    z-index: 999;
    box-shadow: 0 4px 20px rgba(0,0,0,0.5);
  }
  .toast.show { opacity: 1; }

  /* ---- Footer ---- */
  .footer {
    text-align: center;
    color: var(--text2);
    font-size: 10px;
    padding: 10px;
    opacity: 0.6;
  }
</style>
</head>
<body>

<!-- Header -->
<div class="header">
  <h1>📈 Stock JSON Clipper V2.0</h1>
  <div class="tagline">零安装 · 纯本地 · 剪贴板驱动 · AI就绪</div>
</div>

<!-- Search Bar -->
<div class="search-bar">
  <input type="text" id="searchInput" placeholder="输入6位股票代码，如 000001…" maxlength="8"
         autofocus autocomplete="off">
  <select id="searchPeriod">
    <option value="daily">日线</option>
    <option value="weekly">周线</option>
    <option value="monthly">月线</option>
  </select>
  <button id="searchBtn" onclick="onSearch()">🔍 查询</button>
  <label class="save-toggle">
    <input type="checkbox" id="searchSave">
    <span>保存到文件</span>
  </label>
</div>

<!-- Status -->
<div class="status-bar">
  <div class="status-dot monitoring" id="statusDot"></div>
  <span id="statusText">🟢 剪贴板监控中…</span>
</div>

<!-- Tabs -->
<div class="tabs">
  <button class="tab-btn active" data-tab="records">📋 查询结果</button>
  <button class="tab-btn" data-tab="settings">⚙️ 设置</button>
  <button class="tab-btn" data-tab="formula">🤖 公式辅助</button>
</div>

<!-- ========== Tab: Records ========== -->
<div class="tab-content active" id="tab-records">

  <!-- Result Card -->
  <div id="resultCard" class="result-card" style="display:none;">
    <div class="stock-title" id="rcTitle">--</div>
    <div class="stock-meta" id="rcMeta"></div>
    <div class="indicator-grid" id="rcIndicators"></div>
    <div class="card-actions">
      <button class="primary" onclick="onCopyJSON()">📋 复制 JSON</button>
      <button onclick="onCopyPrompt()">🤖 生成 AI Prompt</button>
      <button onclick="onSaveFile()">💾 保存到文件</button>
    </div>
  </div>

  <!-- Empty state -->
  <div id="emptyResult" class="empty-result">
    <div class="icon">📡</div>
    <p>等待数据…</p>
    <p style="font-size:11px;">上方输入股票代码查询<br>或在股票软件中复制代码自动识别</p>
  </div>

  <!-- History -->
  <div style="margin-top:14px;">
    <div style="font-size:12px;font-weight:600;color:var(--text2);margin-bottom:6px;">📜 最近记录</div>
    <table>
      <thead><tr><th>时间</th><th>代码</th><th>名称</th><th>状态</th></tr></thead>
      <tbody id="historyBody">
        <tr class="empty-row"><td colspan="4">暂无记录</td></tr>
      </tbody>
    </table>
  </div>
</div>

<!-- ========== Tab: Settings ========== -->
<div class="tab-content" id="tab-settings">
  <div class="setting-group">
    <label>输出格式</label>
    <div class="setting-row">
      <select id="outputFormat" onchange="onConfigChange('output_format', this.value)">
        <option value="json" selected>JSON</option>
      </select>
      <span style="font-size:11px;color:var(--text2);">更多格式开发中</span>
    </div>
  </div>

  <div class="setting-group">
    <label>数据设置</label>
    <div class="setting-row">
      <span style="font-size:12px;">默认条数</span>
      <input type="number" id="defaultCount" min="5" max="9999" value="250"
             onchange="onConfigChange('default_count', parseInt(this.value))">
    </div>
    <div class="setting-row">
      <span style="font-size:12px;">剪贴板轮询间隔</span>
      <input type="number" id="pollInterval" min="0.2" max="5" step="0.1" value="0.5"
             onchange="onConfigChange('poll_interval', parseFloat(this.value))">
      <span style="font-size:11px;color:var(--text2);">秒</span>
    </div>
    <div class="setting-row">
      <span style="font-size:12px;">缓存时间</span>
      <input type="number" id="cacheTTL" min="10" max="3600" value="300"
             onchange="onConfigChange('cache_ttl', parseInt(this.value))">
      <span style="font-size:11px;color:var(--text2);">秒</span>
    </div>
  </div>

  <div class="btn-row">
    <button class="danger" onclick="onClearCache()">🗑 清空缓存</button>
  </div>
</div>

<!-- ========== Tab: Formula ========== -->
<div class="tab-content" id="tab-formula">
  <div class="setting-group">
    <label>通达信选股公式</label>
    <textarea id="formulaInput" placeholder="在此粘贴通达信选股公式…&#10;例如: CROSS(MA(C,5), MA(C,20)) AND RSI(6)>50"></textarea>
    <div class="btn-row">
      <button class="primary" onclick="onGeneratePrompt()">✨ 生成 Prompt 并复制</button>
      <button onclick="document.getElementById('formulaInput').value=''">清空</button>
    </div>
  </div>
  <div class="setting-group">
    <label>快速操作</label>
    <div class="btn-row">
      <button onclick="onQuickAnalyze()">📊 快速技术分析</button>
    </div>
  </div>
</div>

<!-- Toast -->
<div class="toast" id="toast"></div>

<div class="footer">Stock JSON Clipper V2.0 · Open Source · MIT</div>

<script>
// ============================================================
// Globals
// ============================================================
var _currentResult = null;  // last fetched detail
var _pollFast = false;

// ============================================================
// Tab switching
// ============================================================
document.querySelectorAll('.tab-btn').forEach(function(btn) {
  btn.addEventListener('click', function() {
    document.querySelectorAll('.tab-btn').forEach(function(b) { b.classList.remove('active'); });
    document.querySelectorAll('.tab-content').forEach(function(c) { c.classList.remove('active'); });
    btn.classList.add('active');
    document.getElementById('tab-' + btn.dataset.tab).classList.add('active');
  });
});

// ============================================================
// Search
// ============================================================
function onSearch() {
  var input = document.getElementById('searchInput');
  var code = input.value.trim();
  if (!code) { showToast('请输入股票代码'); return; }

  // Support prefix notation: #000001, W:000001, M:000001
  // Strip non-digit for validation, but pass raw to backend
  var digits = code.replace(/[#WM:]/g, '');
  if (!/^\d{6}$/.test(digits)) {
    showToast('请输入有效的6位数字股票代码');
    return;
  }

  var period = document.getElementById('searchPeriod').value;
  var saveMode = document.getElementById('searchSave').checked;

  var btn = document.getElementById('searchBtn');
  btn.disabled = true;
  btn.textContent = '⏳ 查询中…';

  // Show loading
  document.getElementById('statusDot').className = 'status-dot fetching';
  document.getElementById('statusText').textContent = '⏳ 正在拉取数据…';
  _pollFast = true;

  // Queue the search via Python backend
  pywebview.api.search_stock(code, period, saveMode).then(function(res) {
    if (res && res.success) {
      showToast('✅ 已加入查询队列: ' + code);
      // Start fast polling for result
      fastPollResult(0);
    } else {
      showToast('❌ ' + (res && res.error ? res.error : '查询失败'));
      btn.disabled = false;
      btn.textContent = '🔍 查询';
      _pollFast = false;
    }
  }).catch(function(e) {
    showToast('❌ 内部错误');
    btn.disabled = false;
    btn.textContent = '🔍 查询';
    _pollFast = false;
  });
}

function fastPollResult(count) {
  if (count > 30) {  // timeout after ~3s
    _pollFast = false;
    document.getElementById('searchBtn').disabled = false;
    document.getElementById('searchBtn').textContent = '🔍 查询';
    return;
  }
  pywebview.api.get_last_result_detail().then(function(detail) {
    if (detail && detail.meta && detail.meta.code) {
      _currentResult = detail;
      renderResultCard(detail);
      document.getElementById('searchBtn').disabled = false;
      document.getElementById('searchBtn').textContent = '🔍 查询';
      _pollFast = false;
    } else {
      setTimeout(function() { fastPollResult(count + 1); }, 200);
    }
  }).catch(function() {
    setTimeout(function() { fastPollResult(count + 1); }, 200);
  });
}

// Allow Enter key in search input
document.getElementById('searchInput').addEventListener('keydown', function(e) {
  if (e.key === 'Enter') onSearch();
});

// ============================================================
// Result Card
// ============================================================
function renderResultCard(detail) {
  if (!detail) return;
  var meta = detail.meta || {};
  var indicators = detail.indicators || {};
  var summary = detail.summary || {};
  var macd = indicators.macd || {};
  var boll = indicators.boll || {};

  // Hide empty state, show card
  document.getElementById('emptyResult').style.display = 'none';
  document.getElementById('resultCard').style.display = 'block';

  // Title
  var name = meta.name || '--';
  var code = meta.code || '--';
  document.getElementById('rcTitle').textContent = name + ' (' + code + ')';

  // Meta tags
  var metaHtml = '';
  if (meta.market) metaHtml += '<span>🏛 ' + meta.market + '</span>';
  if (meta.industry) metaHtml += '<span>📂 ' + meta.industry + '</span>';
  if (meta.pe_ttm !== undefined && meta.pe_ttm >= 0) metaHtml += '<span>PE(TTM): ' + meta.pe_ttm.toFixed(2) + '</span>';
  if (meta.total_mv !== undefined && meta.total_mv > 0) {
    var mv = meta.total_mv;
    var mvStr = mv >= 1e8 ? (mv/1e8).toFixed(0) + '亿' : (mv/1e4).toFixed(0) + '万';
    metaHtml += '<span>市值: ' + mvStr + '</span>';
  }
  if (meta.period) {
    var pLabels = {daily:'日线', weekly:'周线', monthly:'月线'};
    metaHtml += '<span>📅 ' + (pLabels[meta.period] || meta.period) + '</span>';
  }
  if (meta.start_date) metaHtml += '<span>' + meta.start_date + ' ~ ' + meta.end_date + '</span>';
  document.getElementById('rcMeta').innerHTML = metaHtml;

  // Indicator grid
  var indHtml = '';
  function addItem(label, value, unit) {
    var cls = 'value';
    if (value === null || value === undefined) {
      value = '--';
    } else if (typeof value === 'number') {
      value = value.toFixed(2);
    }
    indHtml += '<div class="indicator-item"><div class="label">' + label + '</div><div class="' + cls + '">' + value + (unit||'') + '</div></div>';
  }
  addItem('MA5', indicators.ma5);
  addItem('MA10', indicators.ma10);
  addItem('MA20', indicators.ma20);
  addItem('MA60', indicators.ma60);
  addItem('MACD · DIF', macd.dif);
  addItem('MACD · DEA', macd.dea);
  addItem('MACD · BAR', macd.bar);
  addItem('RSI(6)', indicators.rsi_6);
  addItem('RSI(12)', indicators.rsi_12);
  addItem('BOLL上轨', boll.upper);
  addItem('BOLL中轨', boll.mid);
  addItem('BOLL下轨', boll.lower);
  addItem('区间涨跌', summary.period_change, '%');
  addItem('年化波动', summary.volatility, '%');
  addItem('最高收盘', summary.max_close);
  addItem('最低收盘', summary.min_close);
  document.getElementById('rcIndicators').innerHTML = indHtml;
}

// ============================================================
// Card actions
// ============================================================
function onCopyJSON() {
  pywebview.api.copy_last_json().then(function(r) {
    if (r && r.success) showToast('✅ JSON 已复制到剪贴板');
    else showToast('❌ 暂无数据可复制');
  });
}

function onCopyPrompt() {
  pywebview.api.quick_analysis_prompt().then(function(r) {
    if (r && r.success) showToast('✅ Prompt 已复制到剪贴板，直接粘贴到 AI 对话框');
    else showToast('❌ ' + (r && r.error ? r.error : '操作失败'));
  });
}

function onSaveFile() {
  pywebview.api.save_last_to_file().then(function(r) {
    if (r && r.success) showToast('💾 已保存: ' + r.filename);
    else showToast('❌ 保存失败');
  });
}

// ============================================================
// Other JS↔Py calls
// ============================================================
function onGeneratePrompt() {
  var formula = document.getElementById('formulaInput').value.trim();
  if (!formula) { showToast('请先粘贴通达信选股公式'); return; }
  pywebview.api.generate_prompt(formula).then(function(r) {
    if (r && r.success) showToast('✅ Prompt 已生成并复制到剪贴板');
    else showToast('❌ ' + (r && r.error ? r.error : '生成失败'));
  });
}

function onQuickAnalyze() {
  pywebview.api.quick_analysis_prompt().then(function(r) {
    if (r && r.success) showToast('✅ 分析 Prompt 已复制到剪贴板');
    else showToast('❌ ' + (r && r.error ? r.error : '暂无数据'));
  });
}

function onClearCache() {
  pywebview.api.clear_cache();
  showToast('🔄 缓存已清空');
}

function onConfigChange(key, value) {
  pywebview.api.set_config(key, value);
  showToast('⚙️ 已保存: ' + key);
}

// ============================================================
// Polling
// ============================================================
function refreshHistory() {
  pywebview.api.get_history().then(function(data) {
    var tbody = document.getElementById('historyBody');
    if (!data || data.length === 0) {
      tbody.innerHTML = '<tr class="empty-row"><td colspan="4">暂无记录</td></tr>';
      return;
    }
    var rows = '';
    data.forEach(function(r) {
      var cls = 'status-' + (r.status || 'pending');
      var icons = {success:'✅', error:'❌', cached:'📦', pending:'⏳'};
      var label = (icons[r.status] || '⏳') + ' ' + (r.message || r.status);
      var name = r.name || '-';
      rows += '<tr><td>' + r.time + '</td><td>' + r.code + '</td><td>' + name + '</td>'
            + '<td class="' + cls + '">' + label + '</td></tr>';
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
      text.textContent = '⏳ 拉取数据中…';
    } else {
      dot.className = 'status-dot monitoring';
      text.textContent = '🟢 剪贴板监控中…';
    }
  });
  // Also refresh result detail in case clipboard trigger updated it
  if (!_pollFast) {
    pywebview.api.get_last_result_detail().then(function(detail) {
      if (detail && detail.meta && detail.meta.code) {
        _currentResult = detail;
        renderResultCard(detail);
      }
    });
  }
}

function loadConfig() {
  pywebview.api.get_config().then(function(cfg) {
    if (cfg) {
      if (cfg.output_format) document.getElementById('outputFormat').value = cfg.output_format;
      if (cfg.default_count) document.getElementById('defaultCount').value = cfg.default_count;
      if (cfg.poll_interval !== undefined) document.getElementById('pollInterval').value = cfg.poll_interval;
      if (cfg.cache_ttl !== undefined) document.getElementById('cacheTTL').value = cfg.cache_ttl;
    }
  });
}

// ============================================================
// Toast
// ============================================================
function showToast(msg) {
  var el = document.getElementById('toast');
  el.textContent = msg;
  el.classList.add('show');
  clearTimeout(el._timeout);
  el._timeout = setTimeout(function() { el.classList.remove('show'); }, 2000);
}

// ============================================================
// Init
// ============================================================
setInterval(function() {
  refreshHistory();
  refreshStatus();
}, 3000);

document.addEventListener('DOMContentLoaded', function() {
  loadConfig();
  refreshHistory();
  refreshStatus();
  // Try to load existing result
  pywebview.api.get_last_result_detail().then(function(detail) {
    if (detail && detail.meta && detail.meta.code) {
      _currentResult = detail;
      renderResultCard(detail);
    }
  });
  // Focus search
  setTimeout(function() { document.getElementById('searchInput').focus(); }, 300);
});
</script>
</body>
</html>
"""


# ============================================================
# Python-side API exposed to JS
# ============================================================
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
            "poll_interval": cfg.get("poll_interval", 0.5),
            "cache_ttl": cfg.get("cache_ttl", 300),
        }

    def set_config(self, key: str, value: Any) -> None:
        self._clipper.set_config(key, value)

    def clear_cache(self) -> None:
        self._clipper.clear_cache()

    def get_status(self) -> str:
        return self._clipper.get_status()

    def get_last_result_detail(self) -> Optional[Dict[str, Any]]:
        """Return detailed indicators/meta/summary of last fetch for the UI card."""
        return self._clipper.get_result_detail()

    def search_stock(self, code: str, period: str = "daily", save_mode: bool = False) -> Dict[str, Any]:
        """Manually trigger a stock search from the panel search bar.

        Args:
            code: Raw input (may include #, W:, M: prefixes).
            period: 'daily', 'weekly', or 'monthly'.
            save_mode: If True, save to file instead of clipboard.

        Returns:
            Dict with 'success' bool and 'error' string if failed.
        """
        from clipboard_monitor import parse_clipboard

        # Strip whitespace
        code = code.strip()
        # Try to parse with prefix notation
        request = parse_clipboard(code)
        if request:
            actual_code = request.code
            actual_period = request.period
            actual_save = request.save_mode
        else:
            # Plain 6-digit code
            if not code.isdigit() or len(code) != 6:
                return {"success": False, "error": "无效的股票代码，请输入6位数字"}
            actual_code = code
            actual_period = period
            actual_save = save_mode

        # Override period from dropdown if user explicitly selected non-daily
        if period != "daily" and actual_period == "daily":
            actual_period = period
        if save_mode:
            actual_save = True

        result = self._clipper.fetch_manual(actual_code, actual_period)

        # If save mode, modify the request before queuing
        if actual_save:
            from clipboard_monitor import StockRequest
            try:
                self._clipper._fetch_queue.put_nowait(
                    StockRequest(code=actual_code, period=actual_period, save_mode=True, raw=code)
                )
            except Exception:
                pass

        if result.status == "error":
            return {"success": False, "error": result.message}
        return {"success": True}

    def copy_last_json(self) -> Dict[str, Any]:
        """Copy the last result's full JSON to clipboard."""
        import pyperclip
        last = self._clipper.get_last_result()
        if last is None:
            return {"success": False, "error": "暂无数据"}

        cache_key = self._clipper._cache.make_key(last.code, last.period)
        cached_json = self._clipper._cache.get(cache_key)
        if cached_json:
            pyperclip.copy(cached_json)
            return {"success": True}
        return {"success": False, "error": "缓存已过期，请重新查询"}

    def save_last_to_file(self) -> Dict[str, Any]:
        """Save the last result's JSON to a file."""
        import pyperclip
        import os
        import time

        last = self._clipper.get_last_result()
        if last is None:
            return {"success": False, "error": "暂无数据"}

        cache_key = self._clipper._cache.make_key(last.code, last.period)
        cached_json = self._clipper._cache.get(cache_key)
        if not cached_json:
            return {"success": False, "error": "缓存已过期，请重新查询"}

        data = json.loads(cached_json)
        name = data["meta"].get("name", "未知")
        safe_name = name.replace("/", "_").replace("\\", "_").replace(" ", "")
        date_str = time.strftime("%Y%m%d")
        filename = f"{last.code}_{safe_name}_{date_str}.json"
        filepath = os.path.join(os.getcwd(), filename)

        with open(filepath, "w", encoding="utf-8") as f:
            f.write(cached_json)

        return {"success": True, "filename": filename}

    def quick_analysis_prompt(self) -> Dict[str, Any]:
        """Generate a generic quick analysis prompt from last result."""
        import pyperclip

        detail = self._clipper.get_result_detail()
        if not detail or not detail.get("meta") or not detail["meta"].get("code"):
            return {"success": False, "error": "暂无股票数据，请先查询或复制股票代码"}

        try:
            from formula_prompt import generate_quick_prompt
            prompt = generate_quick_prompt(
                code=detail["meta"]["code"],
                name=detail["meta"].get("name", "未知"),
                indicators=detail.get("indicators", {}),
                summary=detail.get("summary", {}),
            )
            pyperclip.copy(prompt)
            return {"success": True}
        except Exception as e:
            return {"success": False, "error": str(e)}

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

            detail = self._clipper.get_result_detail()
            if not detail or not detail.get("meta") or not detail["meta"].get("code"):
                return {"success": False, "error": "暂无股票数据，请先查询或复制股票代码"}

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
            return {"success": False, "error": str(e)}


# ============================================================
# Panel manager
# ============================================================
_panel_window: "Optional[webview.Window]" = None
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
            title="Stock JSON Clipper V2.0",
            html=PANEL_HTML,
            width=480,
            height=680,
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
