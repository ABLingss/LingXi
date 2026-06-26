"""
web_panel.py — Info panel for Stock JSON Clipper V2.0.

Tahoe-inspired professional UI with full Chinese localization:
  - Every indicator label includes Chinese explanation
  - Clean card-based layout with visual hierarchy
  - Windows 7+ compatible (fallback-safe CSS)
  - Manual stock code search + clipboard status

JS ↔ Python bridge via webview.expose() API.
"""

import json
import threading
import os
import time
from typing import TYPE_CHECKING, Any, Dict, List, Optional

import webview

if TYPE_CHECKING:
    from core.clipper import StockClipper


# ============================================================
# HTML Template
# ============================================================
PANEL_HTML = r"""
<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta http-equiv="X-UA-Compatible" content="IE=edge">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<style>
  :root {
    --bg: #14161a;
    --bg2: #1a1d24;
    --surface: #1f2229;
    --surface2: #262a33;
    --border: #2e3340;
    --border2: #3a3f4d;
    --text: #c9cdd4;
    --text1: #e2e4e9;
    --text2: #8b8f9a;
    --text3: #5f636e;
    --green: #22c55e;
    --green-bg: rgba(34,197,94,0.1);
    --red: #ef4444;
    --red-bg: rgba(239,68,68,0.1);
    --orange: #f59e0b;
    --orange-bg: rgba(245,158,11,0.1);
    --blue: #60a5fa;
    --blue-bg: rgba(96,165,250,0.1);
    --purple: #a78bfa;
    --purple-bg: rgba(167,139,250,0.08);
    --radius: 8px;
    --radius-sm: 5px;
    --font: -apple-system, BlinkMacSystemFont, "Microsoft YaHei", "PingFang SC",
             "Segoe UI", "Helvetica Neue", sans-serif;
    --font-mono: "Cascadia Code", "Fira Code", "Consolas", "Courier New", monospace;
  }

  * { box-sizing: border-box; margin: 0; padding: 0; }
  html, body { height: 100%; }

  body {
    font-family: var(--font);
    font-size: 13px;
    background: var(--bg);
    color: var(--text);
    line-height: 1.5;
    overflow-x: hidden;
    -webkit-user-select: none;
    user-select: none;
  }

  /* ---- Scrollbar ---- */
  ::-webkit-scrollbar { width: 5px; }
  ::-webkit-scrollbar-track { background: transparent; }
  ::-webkit-scrollbar-thumb { background: var(--border2); border-radius: 3px; }

  /* ---- Header ---- */
  .header {
    background: linear-gradient(160deg, #191d28 0%, #1f2330 60%, #1a1e2a 100%);
    padding: 14px 18px 12px;
    border-bottom: 1px solid var(--border);
    text-align: center;
  }
  .header .logo { font-size: 15px; font-weight: 700; color: #fff; letter-spacing: 0.3px; }
  .header .logo .ver { font-size: 10px; color: var(--blue); margin-left: 6px; font-weight: 400; }
  .header .desc { font-size: 11px; color: var(--text2); margin-top: 2px; }

  /* ---- Search ---- */
  .search-section {
    padding: 12px 16px;
    background: var(--bg2);
    border-bottom: 1px solid var(--border);
  }
  .search-row {
    display: -webkit-flex; display: flex;
    gap: 8px;
    -webkit-align-items: center; align-items: center;
  }
  .search-input-wrap {
    -webkit-flex: 1; flex: 1;
    position: relative;
  }
  .search-input-wrap input {
    width: 100%;
    background: var(--surface);
    color: #fff;
    border: 1px solid var(--border);
    border-radius: var(--radius-sm);
    padding: 9px 12px;
    font-size: 14px;
    font-family: var(--font);
    outline: none;
    -webkit-transition: border-color 0.2s; transition: border-color 0.2s;
  }
  .search-input-wrap input:focus { border-color: var(--blue); }
  .search-input-wrap input::-webkit-input-placeholder { color: var(--text3); }
  .search-input-wrap input::-ms-input-placeholder { color: var(--text3); }
  .search-input-wrap input::placeholder { color: var(--text3); }

  select {
    background: var(--surface);
    color: var(--text1);
    border: 1px solid var(--border);
    border-radius: var(--radius-sm);
    padding: 9px 10px;
    font-size: 13px;
    font-family: var(--font);
    outline: none;
    cursor: pointer;
    min-width: 72px;
  }
  select:focus { border-color: var(--blue); }

  .btn-search {
    background: var(--blue);
    color: #fff;
    border: none;
    border-radius: var(--radius-sm);
    padding: 9px 18px;
    font-size: 13px;
    font-weight: 600;
    font-family: var(--font);
    cursor: pointer;
    -webkit-transition: opacity 0.15s; transition: opacity 0.15s;
    white-space: nowrap;
  }
  .btn-search:hover { opacity: 0.88; }
  .btn-search:disabled { opacity: 0.4; cursor: not-allowed; }

  .search-options {
    display: -webkit-flex; display: flex;
    gap: 14px;
    margin-top: 8px;
    font-size: 12px;
    color: var(--text2);
    -webkit-align-items: center; align-items: center;
  }
  .search-options label {
    display: -webkit-flex; display: flex;
    -webkit-align-items: center; align-items: center;
    gap: 4px;
    cursor: pointer;
  }
  .search-options input[type="checkbox"] { accent-color: var(--blue); cursor: pointer; }

  /* ---- Status ---- */
  .status-line {
    display: -webkit-flex; display: flex;
    -webkit-align-items: center; align-items: center;
    gap: 8px;
    padding: 6px 18px;
    font-size: 11px;
    color: var(--text2);
    background: var(--bg);
    border-bottom: 1px solid var(--border);
  }
  .status-dot {
    width: 7px; height: 7px;
    border-radius: 50%;
    -webkit-flex-shrink: 0; flex-shrink: 0;
  }
  .status-dot.on { background: var(--green); }
  .status-dot.off { background: var(--text3); }
  .status-dot.fetching { background: var(--orange); -webkit-animation: pulse 0.8s infinite; animation: pulse 0.8s infinite; }
  @-webkit-keyframes pulse { 0%,100% { opacity: 1; } 50% { opacity: 0.2; } }
  @keyframes pulse { 0%,100% { opacity: 1; } 50% { opacity: 0.2; } }

  /* ---- Tabs ---- */
  .tabs {
    display: -webkit-flex; display: flex;
    gap: 2px;
    padding: 0 14px;
    background: var(--bg2);
    border-bottom: 1px solid var(--border);
  }
  .tab-btn {
    background: none;
    border: none;
    border-bottom: 2px solid transparent;
    color: var(--text2);
    padding: 10px 14px;
    font-size: 13px;
    font-family: var(--font);
    cursor: pointer;
    -webkit-transition: color 0.2s, border-color 0.2s;
    transition: color 0.2s, border-color 0.2s;
  }
  .tab-btn:hover { color: var(--text); }
  .tab-btn.active { color: var(--blue); border-bottom-color: var(--blue); }

  .tab-content { display: none; }
  .tab-content.active { display: block; }

  /* ---- Main scroll area ---- */
  .main-area { padding: 12px 14px; }

  /* ---- Card ---- */
  .card {
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: var(--radius);
    padding: 14px 16px;
    margin-bottom: 10px;
    contain: layout style;
  }
  .card-header {
    display: -webkit-flex; display: flex;
    -webkit-justify-content: space-between; justify-content: space-between;
    -webkit-align-items: center; align-items: center;
    margin-bottom: 10px;
  }
  .card-title {
    font-size: 14px;
    font-weight: 700;
    color: #fff;
  }
  .card-title .code { color: var(--text2); font-weight: 400; margin-left: 6px; }

  .meta-tags {
    display: -webkit-flex; display: flex;
    gap: 6px;
    -webkit-flex-wrap: wrap; flex-wrap: wrap;
    margin-bottom: 10px;
  }
  .meta-tag {
    background: var(--surface2);
    color: var(--text2);
    padding: 2px 8px;
    border-radius: 4px;
    font-size: 11px;
    white-space: nowrap;
  }
  .meta-tag .val { color: var(--text1); }

  /* Indicator table */
  .ind-table {
    width: 100%;
    border-collapse: collapse;
    font-size: 12px;
  }
  .ind-table td {
    padding: 6px 8px;
    border-bottom: 1px solid var(--border);
    vertical-align: top;
  }
  .ind-table .lbl { color: var(--text2); white-space: nowrap; width: 30%; }
  .ind-table .val { color: var(--text1); font-weight: 600; font-family: var(--font-mono); font-size: 13px; }
  .ind-table .val.up { color: var(--green); }
  .ind-table .val.down { color: var(--red); }
  .ind-table .note { color: var(--text3); font-size: 11px; font-weight: 400; padding-left: 6px; }

  .card-actions {
    display: -webkit-flex; display: flex;
    gap: 8px;
    margin-top: 10px;
  }
  .card-actions button {
    background: var(--surface2);
    color: var(--text1);
    border: 1px solid var(--border);
    border-radius: var(--radius-sm);
    padding: 7px 14px;
    font-size: 12px;
    font-family: var(--font);
    cursor: pointer;
    -webkit-transition: all 0.15s; transition: all 0.15s;
  }
  .card-actions button:hover { background: #323748; }
  .card-actions button.btn-primary {
    background: var(--blue-bg);
    color: var(--blue);
    border-color: rgba(96,165,250,0.25);
  }
  .card-actions button.btn-primary:hover { background: rgba(96,165,250,0.2); }

  /* Empty state */
  .empty-state {
    text-align: center;
    padding: 40px 20px;
    color: var(--text3);
  }
  .empty-state .icon { font-size: 40px; margin-bottom: 10px; }
  .empty-state .hint { font-size: 12px; color: var(--text2); margin-top: 4px; line-height: 1.6; }

  /* History */
  .history-table {
    width: 100%;
    border-collapse: collapse;
    font-size: 12px;
  }
  .history-table th {
    text-align: left;
    padding: 5px 8px;
    border-bottom: 1px solid var(--border);
    color: var(--text2);
    font-weight: 500;
    font-size: 11px;
  }
  .history-table td {
    padding: 5px 8px;
    border-bottom: 1px solid var(--border);
  }
  .history-table .status-ok { color: var(--green); }
  .history-table .status-err { color: var(--red); }
  .history-table .status-cache { color: var(--blue); }
  .history-table .status-pend { color: var(--orange); }
  .history-table .empty { text-align: center; color: var(--text3); padding: 16px; }

  /* Settings */
  .setting-item {
    margin-bottom: 12px;
  }
  .setting-item label {
    display: block;
    font-size: 11px;
    color: var(--text2);
    margin-bottom: 3px;
    text-transform: uppercase;
    letter-spacing: 0.5px;
  }
  .setting-item .setting-hint {
    font-size: 10px;
    color: var(--text3);
    margin-top: 2px;
  }
  .setting-item input[type="text"],
  .setting-item input[type="number"] {
    background: var(--bg);
    color: var(--text1);
    border: 1px solid var(--border);
    border-radius: var(--radius-sm);
    padding: 7px 10px;
    font-size: 13px;
    font-family: var(--font);
    outline: none;
    width: 100%;
  }
  .setting-item input:focus { border-color: var(--blue); }
  .setting-item input[type="number"] { width: 120px; }

  .btn-row { display: -webkit-flex; display: flex; gap: 8px; margin-top: 10px; }
  .btn-row button {
    background: var(--surface2);
    color: var(--text1);
    border: 1px solid var(--border);
    border-radius: var(--radius-sm);
    padding: 7px 14px;
    font-size: 12px;
    font-family: var(--font);
    cursor: pointer;
    -webkit-transition: all 0.15s; transition: all 0.15s;
  }
  .btn-row button:hover { background: #323748; }
  .btn-row button.btn-danger { color: var(--red); }
  .btn-row button.btn-danger:hover { background: var(--red-bg); border-color: var(--red); }

  /* Toggle switch */
  .toggle-wrap {
    display: -webkit-flex; display: flex;
    -webkit-align-items: center; align-items: center;
    gap: 8px;
    cursor: pointer;
  }
  .toggle-sw {
    width: 36px; height: 20px;
    background: var(--border2);
    border-radius: 10px;
    position: relative;
    cursor: pointer;
    -webkit-transition: background 0.2s; transition: background 0.2s;
  }
  .toggle-sw.on { background: var(--green); }
  .toggle-sw::after {
    content: '';
    position: absolute;
    top: 2px; left: 2px;
    width: 16px; height: 16px;
    background: #fff;
    border-radius: 50%;
    -webkit-transition: -webkit-transform 0.2s; transition: transform 0.2s;
  }
  .toggle-sw.on::after { -webkit-transform: translateX(16px); transform: translateX(16px); }

  /* Textarea */
  textarea {
    width: 100%;
    min-height: 90px;
    background: var(--bg);
    color: var(--text1);
    border: 1px solid var(--border);
    border-radius: var(--radius-sm);
    padding: 10px;
    font-size: 12px;
    font-family: var(--font-mono);
    resize: vertical;
    outline: none;
  }
  textarea:focus { border-color: var(--blue); }

  /* Toast */
  .toast {
    position: fixed;
    bottom: 20px;
    left: 50%;
    -webkit-transform: translateX(-50%); transform: translateX(-50%);
    background: #333a47;
    color: #fff;
    padding: 10px 24px;
    border-radius: 20px;
    font-size: 12px;
    opacity: 0;
    -webkit-transition: opacity 0.3s; transition: opacity 0.3s;
    pointer-events: none;
    z-index: 999;
  }
  .toast.show { opacity: 1; }
  .toast.error { background: #4a1a1a; color: #fca5a5; }

  /* Error Banner */
  .error-banner {
    display: none;
    margin: 6px 14px;
    padding: 10px 14px;
    background: var(--red-bg);
    border: 1px solid rgba(239,68,68,0.3);
    border-radius: var(--radius-sm);
    font-size: 12px;
    color: #fca5a5;
    word-break: break-all;
    -webkit-user-select: text;
    user-select: text;
  }
  .error-banner.show { display: block; }
  .error-banner .err-title {
    font-weight: 700;
    color: #ef4444;
    margin-bottom: 4px;
  }
  .error-banner .err-detail {
    color: var(--text2);
    font-size: 11px;
    font-family: var(--font-mono);
    white-space: pre-wrap;
    max-height: 120px;
    overflow-y: auto;
    margin-top: 4px;
  }
  .error-banner .err-close {
    float: right;
    color: var(--text2);
    font-size: 14px;
    line-height: 1;
    cursor: pointer;
    padding: 0 4px;
  }

  .footer {
    text-align: center;
    color: var(--text3);
    font-size: 10px;
    padding: 8px;
    opacity: 0.5;
  }
</style>
</head>
<body>

<div class="header">
  <div class="logo">📈 Stock JSON Clipper<span class="ver">V2.0</span></div>
  <div class="desc">A股数据桥梁 · 纯本地运行 · 一键生成AI分析JSON</div>
</div>

<!-- Search -->
<div class="search-section">
  <div class="search-row">
    <div class="search-input-wrap">
      <input type="text" id="searchInput"
             placeholder="输入6位股票代码，如 000001（深市平安银行）"
             maxlength="8" autofocus autocomplete="off">
    </div>
    <select id="searchPeriod">
      <option value="daily">日线</option>
      <option value="weekly">周线</option>
      <option value="monthly">月线</option>
    </select>
    <button class="btn-search" id="searchBtn" onclick="onSearch()">查询</button>
  </div>
  <div class="search-options">
    <label><input type="checkbox" id="searchSave"><span>保存为本地文件（不写入剪贴板）</span></label>
    <span style="color:var(--text3);">| 剪贴板快捷: <code>W:</code>周线 <code>M:</code>月线 <code>#</code>保存</span>
  </div>
</div>

<!-- Status -->
<div class="status-line">
  <div class="status-dot on" id="statusDot"></div>
  <span id="statusText">剪贴板监控运行中 — 在股票软件复制代码即可自动识别</span>
</div>

<!-- Error Banner -->
<div class="error-banner" id="errorBanner" onclick="(function(e){if(e.target.classList.contains('err-close'))document.getElementById('errorBanner').classList.remove('show')})(event)">
  <span class="err-close">&times;</span>
  <div class="err-title" id="errTitle">⚠ 错误</div>
  <div class="err-detail" id="errDetail"></div>
</div>

<!-- Tabs -->
<div class="tabs">
  <button class="tab-btn active" data-tab="data">📊 数据查询</button>
  <button class="tab-btn" data-tab="settings">⚙️ 设置</button>
  <button class="tab-btn" data-tab="formula">🤖 AI分析</button>
</div>

<!-- ====== Tab: 数据查询 ====== -->
<div class="tab-content active" id="tab-data">
  <div class="main-area">

    <!-- Result Card -->
    <div id="resultCard" class="card" style="display:none;">
      <div class="card-header">
        <div class="card-title" id="rcTitle">--<span class="code"></span></div>
        <span style="font-size:11px;color:var(--text3);" id="rcPeriod"></span>
      </div>
      <div class="meta-tags" id="rcMeta"></div>

      <!-- Indicators -->
      <table class="ind-table" id="rcIndicators"></table>

      <div class="card-actions">
        <button class="btn-primary" onclick="onCopyJSON()">📋 复制完整JSON</button>
        <button onclick="onCopyPrompt()">🤖 生成AI分析提示词</button>
        <button onclick="onSaveFile()">💾 保存为JSON文件</button>
      </div>
    </div>

    <div id="emptyResult">
      <div class="empty-state">
        <div class="icon">📡</div>
        <div>暂无查询数据</div>
        <div class="hint">在上方输入股票代码点击「查询」<br>或在通达信/同花顺中 Ctrl+C 复制代码自动识别<br><br><span style="color:var(--text3);">支持: 000001（日线）/ W:000001（周线）/ M:000001（月线）/ #000001（保存文件）</span></div>
      </div>
    </div>

    <!-- History -->
    <div class="card" style="margin-top:6px;">
      <div style="font-size:13px;font-weight:600;color:var(--text1);margin-bottom:8px;">📜 最近查询记录</div>
      <table class="history-table">
        <thead><tr><th>时间</th><th>代码</th><th>名称</th><th>状态</th></tr></thead>
        <tbody id="historyBody">
          <tr class="empty"><td colspan="4">暂无记录 — 查询或复制股票代码后自动显示</td></tr>
        </tbody>
      </table>
    </div>
  </div>
</div>

<!-- ====== Tab: 设置 ====== -->
<div class="tab-content" id="tab-settings">
  <div class="main-area">
    <div class="card">
      <div class="card-title" style="font-size:13px;margin-bottom:10px;">🔌 剪贴板监控</div>
      <div class="toggle-wrap" onclick="onToggleMonitor()">
        <div class="toggle-sw on" id="clipboardToggle"></div>
        <span style="font-size:13px;">启用剪贴板自动识别</span>
      </div>
      <div class="setting-hint" style="color:var(--text3);font-size:11px;margin-top:4px;">
        关闭后仅可通过上方搜索框手动输入代码查询
      </div>
    </div>

    <div class="card">
      <div class="card-title" style="font-size:13px;margin-bottom:10px;">📊 数据设置</div>
      <div class="setting-item">
        <label>默认拉取K线条数（5 ~ 9999）</label>
        <input type="number" id="defaultCount" min="5" max="9999" value="250"
               onchange="onConfigChange('default_count', parseInt(this.value))">
        <div class="setting-hint">数值越大包含的历史数据越多，但JSON越长</div>
      </div>
      <div class="setting-item">
        <label>JSON文件保存目录（留空 = 程序所在目录）</label>
        <input type="text" id="saveDirectory" placeholder="例如: D:\股票数据" style="width:100%;"
               onchange="onConfigChange('save_directory', this.value)">
        <div class="setting-hint">修改后点击「💾 保存为JSON文件」时将保存到新目录</div>
      </div>
    </div>

    <div class="card">
      <div class="card-title" style="font-size:13px;margin-bottom:10px;">⚡ 高级设置</div>
      <div class="setting-item">
        <label>剪贴板轮询间隔（秒，0.2 ~ 5）</label>
        <input type="number" id="pollInterval" min="0.2" max="5" step="0.1" value="0.5"
               onchange="onConfigChange('poll_interval', parseFloat(this.value))">
        <div class="setting-hint">每0.5秒检查一次剪贴板。调大可以减少CPU占用</div>
      </div>
      <div class="setting-item">
        <label>数据缓存时间（秒，10 ~ 3600）</label>
        <input type="number" id="cacheTTL" min="10" max="3600" value="300"
               onchange="onConfigChange('cache_ttl', parseInt(this.value))">
        <div class="setting-hint">同一代码在缓存时间内重复查询将直接返回缓存结果，不消耗API请求</div>
      </div>
    </div>

    <div class="btn-row" style="padding:0 0 10px 0;">
      <button class="btn-danger" onclick="onClearCache()">🗑 清空数据缓存</button>
    </div>
  </div>
</div>

<!-- ====== Tab: AI分析 ====== -->
<div class="tab-content" id="tab-formula">
  <div class="main-area">
    <div class="card">
      <div class="card-title" style="font-size:13px;margin-bottom:10px;">🤖 通达信公式 → AI分析提示词</div>
      <div style="font-size:12px;color:var(--text2);margin-bottom:8px;">
        将通达信选股公式粘贴到下方，系统会自动解析公式要素，结合当前股票的技术指标，
        生成一份专业的AI分析提示词。将提示词粘贴到 ChatGPT / DeepSeek / Claude 对话框即可获得分析。
      </div>
      <textarea id="formulaInput" placeholder="在此粘贴通达信选股公式&#10;例如: CROSS(MA(收盘价,5), MA(收盘价,20)) AND RSI(6) 大于 50&#10;&#10;支持: MA均线 / MACD / RSI / BOLL布林带 / CROSS金叉死叉 / 比较运算"></textarea>
      <div class="card-actions" style="margin-top:10px;">
        <button class="btn-primary" onclick="onGeneratePrompt()">✨ 生成选股分析提示词</button>
        <button onclick="onQuickAnalyze()">📊 快速技术分析（无需公式）</button>
        <button onclick="document.getElementById('formulaInput').value=''">清空公式</button>
      </div>
      <div style="font-size:10px;color:var(--text3);margin-top:6px;">
        提示词将自动复制到剪贴板，直接粘贴到AI对话框使用。生成前请先查询股票数据。
      </div>
    </div>
  </div>
</div>

<div class="toast" id="toast"></div>
<div class="footer">Stock JSON Clipper V2.0 · 开源软件 · 数据来源: 腾讯财经/新浪财经/东方财富</div>

<script>
// ============================================================
// Global Error Handler — show all JS errors in UI
// ============================================================
window._showError = function(title, detail) {
  var banner = document.getElementById('errorBanner');
  document.getElementById('errTitle').textContent = '⚠ ' + (title || '错误');
  document.getElementById('errDetail').textContent = detail || '';
  banner.classList.add('show');
  // Also toast
  var toast = document.getElementById('toast');
  toast.textContent = title || detail || '未知错误';
  toast.classList.add('show', 'error');
  clearTimeout(toast._timeout);
  toast._timeout = setTimeout(function() { toast.classList.remove('show', 'error'); }, 6000);
};

window.onerror = function(msg, url, line, col, err) {
  var detail = msg;
  if (url) detail += '\n文件: ' + url;
  if (line) detail += '\n行: ' + line + (col ? ':' + col : '');
  if (err && err.stack) detail += '\n\n' + err.stack;
  window._showError('JavaScript 运行时错误', detail);
  return false;
};

window.addEventListener('unhandledrejection', function(e) {
  var detail = (e.reason ? (e.reason.message || String(e.reason)) : 'Promise rejected');
  if (e.reason && e.reason.stack) detail += '\n\n' + e.reason.stack;
  window._showError('未捕获的异步错误', detail);
});

// ============================================================
// Tab switching
// ============================================================
(function() {
  var btns = document.querySelectorAll('.tab-btn');
  for (var i = 0; i < btns.length; i++) {
    btns[i].addEventListener('click', function() {
      var tab = this.dataset.tab;
      var allBtns = document.querySelectorAll('.tab-btn');
      for (var j = 0; j < allBtns.length; j++) allBtns[j].classList.remove('active');
      var allTabs = document.querySelectorAll('.tab-content');
      for (var k = 0; k < allTabs.length; k++) allTabs[k].classList.remove('active');
      this.classList.add('active');
      document.getElementById('tab-' + tab).classList.add('active');
    });
  }
})();

// ============================================================
// Search
// ============================================================
function onSearch() {
  var input = document.getElementById('searchInput');
  var code = input.value.trim();
  if (!code) { showToast('请输入股票代码（6位数字）'); return; }

  var digits = code.replace(/[#WM:]/g, '');
  if (!/^\d{6}$/.test(digits)) {
    showToast('请输入有效的6位数字股票代码，例如 000001');
    return;
  }

  var period = document.getElementById('searchPeriod').value;
  var saveMode = document.getElementById('searchSave').checked;
  var btn = document.getElementById('searchBtn');
  btn.disabled = true;
  btn.textContent = '查询中…';

  document.getElementById('statusDot').className = 'status-dot fetching';
  document.getElementById('statusText').textContent = '正在拉取 ' + code + ' 的数据…';
  window._pollFast = true;

  pywebview.api.search_stock(code, period, saveMode).then(function(res) {
    if (res && res.success) {
      showToast('已加入查询队列: ' + code + '（数据源: 腾讯财经→新浪财经→东方财富 自动切换）');
      fastPollResult(0);
    } else {
      var errMsg = (res && res.error ? res.error : '未知错误');
      var errDetail = (res && res.detail ? res.detail : '');
      showToast('查询失败: ' + errMsg);
      window._showError('查询失败 ' + code, errMsg + (errDetail ? '\n\n' + errDetail : ''));
      btn.disabled = false;
      btn.textContent = '查询';
      window._pollFast = false;
    }
  }).catch(function(e) {
    showToast('内部错误，请重试');
    window._showError('通信错误', '与后端API通信失败。请确认程序完整运行。\n' + (e && e.message ? e.message : String(e)));
    btn.disabled = false;
    btn.textContent = '查询';
    window._pollFast = false;
  });
}

function fastPollResult(count) {
  if (count > 30) {
    window._pollFast = false;
    document.getElementById('searchBtn').disabled = false;
    document.getElementById('searchBtn').textContent = '查询';
    return;
  }
  pywebview.api.get_last_result_detail().then(function(detail) {
    if (detail && detail.meta && detail.meta.code) {
      window._currentResult = detail;
      renderResultCard(detail);
      document.getElementById('searchBtn').disabled = false;
      document.getElementById('searchBtn').textContent = '查询';
      window._pollFast = false;
    } else {
      setTimeout(function() { fastPollResult(count + 1); }, 200);
    }
  }).catch(function() {
    setTimeout(function() { fastPollResult(count + 1); }, 200);
  });
}

document.getElementById('searchInput').addEventListener('keydown', function(e) {
  if (e.key === 'Enter') onSearch();
});

// ============================================================
// Result Card
// ============================================================
function renderResultCard(detail) {
  if (!detail) return;
  var meta = detail.meta || {};
  var ind = detail.indicators || {};
  var sum = detail.summary || {};
  var macd = ind.macd || {};
  var boll = ind.boll || {};

  document.getElementById('emptyResult').style.display = 'none';
  document.getElementById('resultCard').style.display = 'block';

  // Title
  var name = meta.name || '--';
  var code = meta.code || '--';
  document.getElementById('rcTitle').innerHTML = name + '<span class="code">' + code + '</span>';

  // Period label
  var pLabels = {daily: '日线数据', weekly: '周线数据', monthly: '月线数据'};
  document.getElementById('rcPeriod').textContent = pLabels[meta.period] || meta.period || '';

  // Meta tags
  var tags = '';
  if (meta.market) tags += '<span class="meta-tag">市场: <span class="val">' + meta.market + '</span></span>';
  if (meta.industry && meta.industry !== 'GP-A') tags += '<span class="meta-tag">行业: <span class="val">' + meta.industry + '</span></span>';
  if (meta.pe_ttm !== undefined && meta.pe_ttm > 0)
    tags += '<span class="meta-tag">市盈率(PE): <span class="val">' + meta.pe_ttm.toFixed(2) + '</span></span>';
  if (meta.total_mv !== undefined && meta.total_mv > 0) {
    var mv = meta.total_mv;
    var mvStr = mv >= 1e8 ? (mv/1e8).toFixed(0) + '亿' : (mv/1e4).toFixed(0) + '万';
    tags += '<span class="meta-tag">总市值: <span class="val">' + mvStr + '</span></span>';
  }
  if (meta.start_date) tags += '<span class="meta-tag">数据区间: <span class="val">' + meta.start_date + ' ~ ' + meta.end_date + '</span></span>';
  document.getElementById('rcMeta').innerHTML = tags;

  // Indicator table
  var rows = '';
  function row(label, val, unit, note) {
    unit = unit || '';
    note = note || '';
    var v = '--';
    var cls = '';
    if (val !== null && val !== undefined && !isNaN(val)) {
      v = Number(val).toFixed(2);
    }
    rows += '<tr><td class="lbl">' + label + '</td><td class="val ' + cls + '">' + v + unit + '<span class="note">' + note + '</span></td></tr>';
  }

  // Price
  row('最新收盘价', sum.max_close ? (ind.ma5 || '') : '', '', '最近交易日收盘价');

  // MA
  row('5日均线 (MA5)', ind.ma5, '', '短期趋势参考');
  row('10日均线 (MA10)', ind.ma10, '', '短期趋势参考');
  row('20日均线 (MA20)', ind.ma20, '', '中期趋势参考');
  row('60日均线 (MA60)', ind.ma60, '', '长期趋势参考（季线）');

  // MACD
  row('MACD快线 (DIF)', macd.dif, '', '指数平滑异同平均线 — 快线（12日EMA）');
  row('MACD慢线 (DEA)', macd.dea, '', '指数平滑异同平均线 — 慢线（9日DIF均线）');
  row('MACD柱状线 (BAR)', macd.bar, '', '红柱=多头动能，绿柱=空头动能');

  // RSI
  row('相对强弱指标 RSI(6)', ind.rsi_6, '', '6日RSI — >80超买区，<20超卖区');
  row('相对强弱指标 RSI(12)', ind.rsi_12, '', '12日RSI — 中长期超买超卖判断');

  // BOLL
  row('布林带上轨 (BOLL Upper)', boll.upper, '', '压力位参考 — 价格触及上轨可能回调');
  row('布林带中轨 (BOLL Mid)', boll.mid, '', '20日均线 — 多空平衡位');
  row('布林带下轨 (BOLL Lower)', boll.lower, '', '支撑位参考 — 价格触及下轨可能反弹');

  // Summary
  row('区间涨跌幅', sum.period_change, '%', '选中时间范围内的价格变动百分比');
  row('年化波动率', sum.volatility, '%', '年化标准差 — 衡量风险程度');
  row('区间最高收盘价', sum.max_close, '', '选中范围内最高收盘价');
  row('区间最低收盘价', sum.min_close, '', '选中范围内最低收盘价');
  row('平均成交量', (sum.avg_volume || 0), '手', '选中范围内日均成交量');

  document.getElementById('rcIndicators').innerHTML = rows;
}

// ============================================================
// Card actions
// ============================================================
function onCopyJSON() {
  pywebview.api.copy_last_json().then(function(r) {
    if (r && r.success) {
      showToast('完整JSON已复制到剪贴板，可直接粘贴到AI对话框');
    } else {
      showToast((r && r.error) || '暂无数据可复制');
      if (r && r.detail) window._showError('复制失败', r.error + '\n\n' + r.detail);
    }
  });
}

function onCopyPrompt() {
  pywebview.api.quick_analysis_prompt().then(function(r) {
    if (r && r.success) {
      showToast('AI分析提示词已复制到剪贴板，请粘贴到 ChatGPT/DeepSeek/Claude');
    } else {
      showToast((r && r.error) || '操作失败');
      if (r && r.detail) window._showError('生成提示词失败', r.error + '\n\n' + r.detail);
    }
  });
}

function onSaveFile() {
  pywebview.api.save_last_to_file().then(function(r) {
    if (r && r.success) {
      showToast('已保存文件: ' + r.filename);
    } else {
      showToast((r && r.error) || '保存失败');
      if (r && r.detail) window._showError('保存失败', r.error + '\n\n' + r.detail);
    }
  });
}

// ============================================================
// AI Prompt
// ============================================================
function onGeneratePrompt() {
  var formula = document.getElementById('formulaInput').value.trim();
  if (!formula) { showToast('请先粘贴通达信选股公式到文本框中'); return; }
  pywebview.api.generate_prompt(formula).then(function(r) {
    if (r && r.success) {
      showToast('选股分析提示词已生成并复制到剪贴板！请粘贴到AI对话框');
    } else {
      showToast((r && r.error) || '生成失败');
      if (r && r.detail) window._showError('生成提示词失败', r.error + '\n\n' + r.detail);
    }
  });
}

function onQuickAnalyze() {
  pywebview.api.quick_analysis_prompt().then(function(r) {
    if (r && r.success) {
      showToast('技术分析提示词已复制到剪贴板！请粘贴到AI对话框');
    } else {
      showToast((r && r.error) || '暂无股票数据，请先查询股票代码');
      if (r && r.detail) window._showError('快速分析失败', r.error + '\n\n' + r.detail);
    }
  });
}

// ============================================================
// Settings
// ============================================================
function onToggleMonitor() {
  pywebview.api.toggle_clipboard_monitor().then(function(isOn) {
    var el = document.getElementById('clipboardToggle');
    if (isOn) { el.classList.add('on'); }
    else { el.classList.remove('on'); }
    showToast(isOn ? '剪贴板监控已开启 — 复制股票代码即可自动识别' : '剪贴板监控已暂停 — 您仍可手动输入代码查询');
  });
}

function onClearCache() { pywebview.api.clear_cache(); showToast('数据缓存已清空，下次查询将重新拉取最新数据'); }

function onConfigChange(key, value) {
  pywebview.api.set_config(key, value);
  showToast('设置已保存: ' + key);
}

// ============================================================
// Polling
// ============================================================
function refreshHistory() {
  pywebview.api.get_history().then(function(data) {
    var tbody = document.getElementById('historyBody');
    if (!data || data.length === 0) {
      tbody.innerHTML = '<tr class="empty"><td colspan="4">暂无记录 — 查询或复制股票代码后自动显示</td></tr>';
      return;
    }
    var rows = '';
    for (var i = 0; i < data.length; i++) {
      var r = data[i];
      var icons = {success: 'ok', error: 'err', cached: 'cache', pending: 'pend'};
      var labels = {success: '成功', error: '失败', cached: '缓存', pending: '排队中'};
      var cls = 'status-' + (icons[r.status] || 'pend');
      var label = (labels[r.status] || r.status) + ' ' + (r.message || '');
      rows += '<tr><td>' + r.time + '</td><td>' + r.code + '</td><td>' + (r.name || '-') + '</td><td class="' + cls + '">' + label + '</td></tr>';
    }
    tbody.innerHTML = rows;
  });
}

function refreshStatus() {
  pywebview.api.get_status().then(function(status) {
    var dot = document.getElementById('statusDot');
    var text = document.getElementById('statusText');
    if (status === 'fetching') {
      dot.className = 'status-dot fetching';
      text.textContent = '正在拉取数据… 请稍候';
    } else {
      pywebview.api.is_monitoring().then(function(on) {
        if (on) {
          dot.className = 'status-dot on';
          text.textContent = '剪贴板监控运行中 — 在股票软件复制代码即可自动识别';
        } else {
          dot.className = 'status-dot off';
          text.textContent = '剪贴板监控已暂停 — 可使用上方搜索框手动查询';
        }
      });
    }
  });
  if (!window._pollFast) {
    pywebview.api.get_last_result_detail().then(function(detail) {
      if (detail && detail.meta && detail.meta.code) {
        window._currentResult = detail;
        renderResultCard(detail);
      }
    });
  }
}

function loadConfig() {
  pywebview.api.get_config().then(function(cfg) {
    if (!cfg) return;
    if (cfg.output_format) document.getElementById('outputFormat').value = cfg.output_format;
    if (cfg.default_count) document.getElementById('defaultCount').value = cfg.default_count;
    if (cfg.poll_interval !== undefined) document.getElementById('pollInterval').value = cfg.poll_interval;
    if (cfg.cache_ttl !== undefined) document.getElementById('cacheTTL').value = cfg.cache_ttl;
    if (cfg.save_directory !== undefined) document.getElementById('saveDirectory').value = cfg.save_directory || '';
  });
  pywebview.api.is_monitoring().then(function(on) {
    var el = document.getElementById('clipboardToggle');
    if (on) { el.classList.add('on'); }
    else { el.classList.remove('on'); }
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
  el._timeout = setTimeout(function() { el.classList.remove('show'); }, 3000);
}

// ============================================================
// Init
// ============================================================
// ============================================================
// Adaptive polling — adjusts interval based on state
// ============================================================
(function() {
  var FAST = 400, NORMAL = 3000, SLOW = 10000;
  var _interval = NORMAL;
  var _timer = null;
  var _lastHistory = '';

  function poll() {
    // Batch: refresh both in one rAF
    var doRefresh = function() {
      refreshStatus();
      // Skip history if data unchanged
      pywebview.api.get_history().then(function(data) {
        var key = JSON.stringify(data);
        if (key !== _lastHistory) {
          _lastHistory = key;
          var tbody = document.getElementById('historyBody');
          if (!data || data.length === 0) {
            tbody.innerHTML = '<tr class="empty"><td colspan="4">暂无记录</td></tr>';
            return;
          }
          var rows = '';
          for (var i = 0; i < data.length; i++) {
            var r = data[i];
            var icons = {success: 'ok', error: 'err', cached: 'cache', pending: 'pend'};
            var labels = {success: '成功', error: '失败', cached: '缓存', pending: '排队中'};
            var cls = 'status-' + (icons[r.status] || 'pend');
            rows += '<tr><td>' + r.time + '</td><td>' + r.code + '</td><td>' + (r.name || '-') + '</td><td class="' + cls + '">' + (labels[r.status] || r.status) + ' ' + (r.message || '') + '</td></tr>';
          }
          tbody.innerHTML = rows;
        }
      });
      if (!window._pollFast) {
        pywebview.api.get_last_result_detail().then(function(detail) {
          if (detail && detail.meta && detail.meta.code) {
            window._currentResult = detail;
            renderResultCard(detail);
          }
        });
      }
    };

    window.requestAnimationFrame(doRefresh);

    // Adaptive: fast when polling result, slow when hidden
    var next = window._pollFast ? FAST :
               (document.hidden ? SLOW : NORMAL);
    if (next !== _interval) { _interval = next; }
    _timer = setTimeout(poll, _interval);
  }

  // Visibility change → adjust interval immediately
  document.addEventListener('visibilitychange', function() {
    if (!document.hidden) {
      _interval = window._pollFast ? FAST : NORMAL;
      clearTimeout(_timer);
      _timer = setTimeout(poll, 100);
    }
  });

  // Start
  _timer = setTimeout(poll, 500);
})();

(function init() {
  // Defer non-critical init
  setTimeout(function() { loadConfig(); }, 50);
  refreshHistory();
  refreshStatus();
  pywebview.api.get_last_result_detail().then(function(detail) {
    if (detail && detail.meta && detail.meta.code) { window._currentResult = detail; renderResultCard(detail); }
  });
  setTimeout(function() { document.getElementById('searchInput').focus(); }, 200);
})();
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
            "save_directory": cfg.get("save_directory", ""),
        }

    def set_config(self, key: str, value: Any) -> None:
        self._clipper.set_config(key, value)

    def clear_cache(self) -> None:
        self._clipper.clear_cache()

    def toggle_clipboard_monitor(self) -> bool:
        return self._clipper.toggle_clipboard_monitor()

    def is_monitoring(self) -> bool:
        return self._clipper.is_monitoring()

    def get_status(self) -> str:
        return self._clipper.get_status()

    def get_last_result_detail(self) -> Optional[Dict[str, Any]]:
        return self._clipper.get_result_detail()

    def search_stock(self, code: str, period: str = "daily", save_mode: bool = False) -> Dict[str, Any]:
        import os, time as _time
        try:
            from core.clipboard import parse_clipboard
            code = code.strip()
            request = parse_clipboard(code)
            if request:
                actual_code, actual_period, actual_save = request.code, request.period, request.save_mode
            else:
                if not code.isdigit() or len(code) != 6:
                    return {"success": False, "error": "无效的股票代码，请输入6位数字"}
                actual_code, actual_period, actual_save = code, period, save_mode
            if period != "daily" and actual_period == "daily":
                actual_period = period
            if save_mode:
                actual_save = True

            result = self._clipper.fetch_manual(actual_code, actual_period)

            if actual_save:
                from core.clipboard import StockRequest
                try:
                    self._clipper._fetch_queue.put_nowait(
                        StockRequest(code=actual_code, period=actual_period, save_mode=True, raw=code)
                    )
                except Exception:
                    pass

            if result.status == "error":
                return {"success": False, "error": result.message}
            return {"success": True}
        except Exception as e:
            import traceback
            tb = traceback.format_exc()
            try:
                with open(os.path.join(os.getcwd(), "error.log"), "a", encoding="utf-8") as f:
                    f.write(f"[{_time.strftime('%Y-%m-%d %H:%M:%S')}] PanelAPI.search_stock\n")
                    f.write(tb)
            except Exception:
                pass
            return {
                "success": False,
                "error": f"{type(e).__name__}: {e}",
                "detail": tb,
            }

    def copy_last_json(self) -> Dict[str, Any]:
        import pyperclip, traceback
        try:
            last = self._clipper.get_last_result()
            if last is None:
                return {"success": False, "error": "暂无数据"}
            cache_key = last.cache_key or self._clipper._cache.make_key(
                last.code, last.period, self._clipper._config.get("default_count", 250))
            cached_json = self._clipper._cache.get(cache_key)
            if cached_json:
                pyperclip.copy(cached_json)
                return {"success": True}
            return {"success": False, "error": "缓存已过期，请重新查询"}
        except Exception as e:
            return {"success": False, "error": str(e), "detail": traceback.format_exc()}

    def save_last_to_file(self) -> Dict[str, Any]:
        import traceback
        try:
            last = self._clipper.get_last_result()
            if last is None:
                return {"success": False, "error": "暂无数据"}
            cache_key = last.cache_key or self._clipper._cache.make_key(
                last.code, last.period, self._clipper._config.get("default_count", 250))
            cached_json = self._clipper._cache.get(cache_key)
            if not cached_json:
                return {"success": False, "error": "缓存已过期，请重新查询"}
            data = json.loads(cached_json)
            name = data["meta"].get("name", "未知")
            safe_name = name.replace("/", "_").replace("\\", "_").replace(" ", "")
            date_str = time.strftime("%Y%m%d")
            filename = f"{last.code}_{safe_name}_{date_str}.json"
            save_dir = self._clipper._config.get("save_directory", "")
            if save_dir and os.path.isdir(save_dir):
                filepath = os.path.join(save_dir, filename)
            else:
                filepath = os.path.join(os.getcwd(), filename)
            os.makedirs(os.path.dirname(filepath) or ".", exist_ok=True)
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(cached_json)
            return {"success": True, "filename": filename}
        except Exception as e:
            return {"success": False, "error": str(e), "detail": traceback.format_exc()}

    def quick_analysis_prompt(self) -> Dict[str, Any]:
        import pyperclip, traceback
        detail = self._clipper.get_result_detail()
        if not detail or not detail.get("meta") or not detail["meta"].get("code"):
            return {"success": False, "error": "暂无股票数据，请先在搜索框输入代码查询"}
        try:
            from modules.prompt.formula import generate_quick_prompt
            prompt = generate_quick_prompt(
                code=detail["meta"]["code"],
                name=detail["meta"].get("name", "未知"),
                indicators=detail.get("indicators", {}),
                summary=detail.get("summary", {}),
            )
            pyperclip.copy(prompt)
            return {"success": True}
        except Exception as e:
            tb = traceback.format_exc()
            return {"success": False, "error": str(e), "detail": tb}

    def generate_prompt(self, formula_text: str) -> Dict[str, Any]:
        import traceback
        try:
            from modules.prompt.formula import generate_prompt
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
            tb = traceback.format_exc()
            return {"success": False, "error": str(e), "detail": tb}


# ============================================================
# Panel manager
# ============================================================
_panel_window: "Optional[webview.Window]" = None
_panel_lock = threading.Lock()


def show_panel(clipper: "StockClipper") -> None:
    """Show or focus the info panel."""
    global _panel_window
    with _panel_lock:
        if _panel_window is not None:
            try:
                _panel_window.show()
                _panel_window.restore()
                return
            except Exception:
                _panel_window = None

        api = PanelAPI(clipper)
        _panel_window = webview.create_window(
            title="Stock JSON Clipper V2.0",
            html=PANEL_HTML,
            width=540,
            height=720,
            resizable=True,
            on_top=False,
            js_api=api,
        )

        def _on_closed():
            global _panel_window
            _panel_window = None

        _panel_window.events.closed += _on_closed
        webview.start(gui=None, debug=False)
