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

from core.logging_setup import get_logger

if TYPE_CHECKING:
    from core.clipper import StockClipper

log = get_logger("panel")


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
    --bg: #0b0e11;
    --bg2: #11161c;
    --surface: #181c24;
    --surface2: #1f2430;
    --border: #2a3040;
    --border2: #363d50;
    --text: #bcc3cd;
    --text1: #e6e9ef;
    --text2: #7e8594;
    --text3: #515766;
    --green: #2ebd59;
    --green-bg: rgba(46,189,89,0.12);
    --red: #f0534b;
    --red-bg: rgba(240,83,75,0.12);
    --orange: #f0a040;
    --orange-bg: rgba(240,160,64,0.12);
    --blue: #5098f0;
    --blue-bg: rgba(80,152,240,0.12);
    --purple: #9d7aef;
    --purple-bg: rgba(157,122,239,0.1);
    --radius: 10px;
    --radius-sm: 6px;
    --shadow: 0 1px 3px rgba(0,0,0,0.3);
    --font: -apple-system, BlinkMacSystemFont, "Microsoft YaHei", "PingFang SC",
             "Segoe UI", "Helvetica Neue", sans-serif;
    --font-mono: "Cascadia Code", "Fira Code", "JetBrains Mono", "Consolas", monospace;
  }

  * { box-sizing: border-box; margin: 0; padding: 0; }
  html, body { height: 100%; }

  body {
    font-family: var(--font);
    font-size: 13px;
    background: var(--bg);
    color: var(--text);
    line-height: 1.55;
    overflow-x: hidden;
    -webkit-user-select: none;
    user-select: none;
  }

  ::-webkit-scrollbar { width: 4px; }
  ::-webkit-scrollbar-track { background: transparent; }
  ::-webkit-scrollbar-thumb { background: var(--border2); border-radius: 4px; }
  ::-webkit-scrollbar-thumb:hover { background: var(--text3); }

  /* ---- Header ---- */
  .header {
    background: linear-gradient(165deg, #12192a 0%, #151e2e 40%, #111726 100%);
    padding: 16px 20px 14px;
    border-bottom: 1px solid var(--border);
    text-align: center;
    position: relative;
    overflow: hidden;
  }
  .header::before {
    content: '';
    position: absolute;
    top: -30px; right: -20px;
    width: 100px; height: 100px;
    background: radial-gradient(circle, rgba(80,152,240,0.06) 0%, transparent 70%);
    pointer-events: none;
  }
  .header .logo {
    font-size: 16px; font-weight: 800; color: #fff; letter-spacing: 0.5px;
  }
  .header .logo .ver {
    font-size: 10px; color: var(--blue); margin-left: 7px; font-weight: 500;
    background: var(--blue-bg); padding: 1px 6px; border-radius: 3px;
  }
  .header .desc { font-size: 11px; color: var(--text3); margin-top: 3px; letter-spacing: 0.2px; }

  /* ---- Search ---- */
  .search-section {
    padding: 14px 16px 12px;
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
  .search-input-wrap::before {
    content: '\1F50D';
    position: absolute;
    left: 11px; top: 50%;
    -webkit-transform: translateY(-50%); transform: translateY(-50%);
    font-size: 13px; opacity: 0.4; pointer-events: none; z-index: 1;
  }
  .search-input-wrap input {
    width: 100%;
    background: var(--surface);
    color: #fff;
    border: 1px solid var(--border);
    border-radius: var(--radius-sm);
    padding: 9px 12px 9px 32px;
    font-size: 14px;
    font-family: var(--font);
    outline: none;
    -webkit-transition: all 0.2s; transition: all 0.2s;
    box-shadow: inset 0 1px 2px rgba(0,0,0,0.2);
  }
  .search-input-wrap input:focus {
    border-color: var(--blue);
    box-shadow: 0 0 0 3px rgba(80,152,240,0.12), inset 0 1px 2px rgba(0,0,0,0.2);
  }
  .search-input-wrap input::-webkit-input-placeholder { color: var(--text3); }
  .search-input-wrap input::placeholder { color: var(--text3); }

  select {
    background: var(--surface);
    color: var(--text1);
    border: 1px solid var(--border);
    border-radius: var(--radius-sm);
    padding: 9px 8px;
    font-size: 13px;
    font-family: var(--font);
    outline: none;
    cursor: pointer;
    min-width: 72px;
    -webkit-transition: border-color 0.2s; transition: border-color 0.2s;
    -webkit-appearance: none; appearance: none;
    background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='12' height='12' viewBox='0 0 12 12'%3E%3Cpath fill='%237e8594' d='M6 8L1 3h10z'/%3E%3C/svg%3E");
    background-repeat: no-repeat;
    background-position: right 6px center;
    padding-right: 22px;
  }
  select:focus { border-color: var(--blue); }

  .btn-search {
    background: linear-gradient(135deg, #4d8aee 0%, #3b6fd4 100%);
    color: #fff;
    border: none;
    border-radius: var(--radius-sm);
    padding: 9px 20px;
    font-size: 13px;
    font-weight: 600;
    font-family: var(--font);
    cursor: pointer;
    -webkit-transition: all 0.2s; transition: all 0.2s;
    white-space: nowrap;
    box-shadow: 0 2px 6px rgba(59,111,212,0.25);
    letter-spacing: 0.3px;
  }
  .btn-search:hover { -webkit-transform: translateY(-1px); transform: translateY(-1px); box-shadow: 0 4px 12px rgba(59,111,212,0.35); }
  .btn-search:active { -webkit-transform: translateY(0); transform: translateY(0); }
  .btn-search:disabled { opacity: 0.45; cursor: not-allowed; -webkit-transform: none; transform: none; box-shadow: none; }

  .search-options {
    display: -webkit-flex; display: flex;
    gap: 16px; margin-top: 8px;
    font-size: 11px; color: var(--text2);
    -webkit-align-items: center; align-items: center;
  }
  .search-options label {
    display: -webkit-flex; display: flex;
    -webkit-align-items: center; align-items: center;
    gap: 5px; cursor: pointer;
    -webkit-transition: color 0.15s; transition: color 0.15s;
  }
  .search-options label:hover { color: var(--text); }
  .search-options input[type="checkbox"] { accent-color: var(--blue); cursor: pointer; width: 14px; height: 14px; }

  /* ---- Status ---- */
  .status-line {
    display: -webkit-flex; display: flex;
    -webkit-align-items: center; align-items: center;
    gap: 9px; padding: 7px 18px;
    font-size: 11px; color: var(--text2);
    background: var(--bg);
    border-bottom: 1px solid var(--border);
  }
  .status-dot {
    width: 8px; height: 8px;
    border-radius: 50%;
    -webkit-flex-shrink: 0; flex-shrink: 0;
  }
  .status-dot.on { background: var(--green); box-shadow: 0 0 6px rgba(46,189,89,0.5); }
  .status-dot.off { background: var(--text3); }
  .status-dot.fetching { background: var(--orange); box-shadow: 0 0 6px rgba(240,160,64,0.5); -webkit-animation: pulse 0.7s infinite; animation: pulse 0.7s infinite; }
  @-webkit-keyframes pulse { 0%,100% { opacity: 1; } 50% { opacity: 0.15; } }
  @keyframes pulse { 0%,100% { opacity: 1; } 50% { opacity: 0.15; } }

  /* ---- Tabs ---- */
  .tabs {
    display: -webkit-flex; display: flex;
    gap: 0;
    padding: 0 14px;
    background: var(--bg2);
    border-bottom: 1px solid var(--border);
  }
  .tab-btn {
    background: none; border: none;
    border-bottom: 2px solid transparent;
    color: var(--text2);
    padding: 11px 16px;
    font-size: 13px; font-weight: 500;
    font-family: var(--font);
    cursor: pointer;
    -webkit-transition: all 0.2s; transition: all 0.2s;
    position: relative;
  }
  .tab-btn:hover { color: var(--text1); }
  .tab-btn.active { color: #fff; border-bottom-color: var(--blue); font-weight: 600; }

  .tab-content { display: none; -webkit-animation: fadeIn 0.2s; animation: fadeIn 0.2s; }
  .tab-content.active { display: block; }
  @-webkit-keyframes fadeIn { from { opacity: 0; -webkit-transform: translateY(4px); transform: translateY(4px); } to { opacity: 1; -webkit-transform: translateY(0); transform: translateY(0); } }
  @keyframes fadeIn { from { opacity: 0; transform: translateY(4px); } to { opacity: 1; transform: translateY(0); } }

  .main-area { padding: 14px 14px 8px; }

  /* ---- Card ---- */
  .card {
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: var(--radius);
    padding: 15px 17px;
    margin-bottom: 10px;
    contain: layout style;
    box-shadow: var(--shadow);
    -webkit-transition: border-color 0.2s; transition: border-color 0.2s;
  }
  .card:hover { border-color: var(--border2); }
  .card-header {
    display: -webkit-flex; display: flex;
    -webkit-justify-content: space-between; justify-content: space-between;
    -webkit-align-items: center; align-items: center;
    margin-bottom: 12px;
  }
  .card-title { font-size: 15px; font-weight: 700; color: #fff; }
  .card-title .code { color: var(--text2); font-weight: 400; margin-left: 8px; font-size: 13px; }

  .meta-tags {
    display: -webkit-flex; display: flex;
    gap: 6px; -webkit-flex-wrap: wrap; flex-wrap: wrap;
    margin-bottom: 12px;
  }
  .meta-tag {
    background: var(--surface2);
    color: var(--text2);
    padding: 3px 10px; border-radius: 5px;
    font-size: 11px; white-space: nowrap;
    border: 1px solid var(--border);
  }
  .meta-tag .val { color: var(--text1); font-weight: 500; }

  /* Indicator table */
  .ind-table { width: 100%; border-collapse: collapse; font-size: 12px; }
  .ind-table td { padding: 7px 10px; border-bottom: 1px solid rgba(255,255,255,0.04); vertical-align: top; }
  .ind-table tr:last-child td { border-bottom: none; }
  .ind-table .lbl { color: var(--text2); white-space: nowrap; width: 34%; font-size: 11px; }
  .ind-table .val { color: var(--text1); font-weight: 600; font-family: var(--font-mono); font-size: 13px; }
  .ind-table .val.up { color: var(--green); }
  .ind-table .val.down { color: var(--red); }
  .ind-table .note { color: var(--text3); font-size: 10px; font-weight: 400; padding-left: 6px; }

  .card-actions { display: -webkit-flex; display: flex; gap: 8px; margin-top: 12px; -webkit-flex-wrap: wrap; flex-wrap: wrap; }
  .card-actions button {
    background: var(--surface2); color: var(--text1);
    border: 1px solid var(--border); border-radius: var(--radius-sm);
    padding: 8px 15px; font-size: 12px; font-family: var(--font);
    cursor: pointer; font-weight: 500;
    -webkit-transition: all 0.2s; transition: all 0.2s;
    letter-spacing: 0.2px;
  }
  .card-actions button:hover { background: #2a3142; border-color: var(--border2); }
  .card-actions button:active { -webkit-transform: scale(0.97); transform: scale(0.97); }
  .card-actions button.btn-primary {
    background: var(--blue-bg); color: var(--blue);
    border-color: rgba(80,152,240,0.3); font-weight: 600;
  }
  .card-actions button.btn-primary:hover { background: rgba(80,152,240,0.2); border-color: rgba(80,152,240,0.5); }

  /* Empty state */
  .empty-state { text-align: center; padding: 48px 24px; color: var(--text3); }
  .empty-state .icon { font-size: 44px; margin-bottom: 12px; opacity: 0.6; }
  .empty-state .hint { font-size: 12px; color: var(--text2); margin-top: 6px; line-height: 1.7; }

  /* History */
  .history-table { width: 100%; border-collapse: collapse; font-size: 12px; }
  .history-table th {
    text-align: left; padding: 6px 10px;
    border-bottom: 2px solid var(--border);
    color: var(--text2); font-weight: 600; font-size: 10px;
    text-transform: uppercase; letter-spacing: 0.5px;
  }
  .history-table td { padding: 6px 10px; border-bottom: 1px solid rgba(255,255,255,0.03); }
  .history-table tr:hover td { background: rgba(255,255,255,0.015); }
  .history-table .status-ok { color: var(--green); font-weight: 500; }
  .history-table .status-err { color: var(--red); font-weight: 500; }
  .history-table .status-cache { color: var(--blue); font-weight: 500; }
  .history-table .status-pend { color: var(--orange); font-weight: 500; }
  .history-table .empty { text-align: center; color: var(--text3); padding: 20px; }

  /* Settings */
  .setting-item { margin-bottom: 14px; }
  .setting-item label {
    display: block; font-size: 10px; color: var(--text2);
    margin-bottom: 4px; text-transform: uppercase;
    letter-spacing: 0.6px; font-weight: 600;
  }
  .setting-item .setting-hint { font-size: 10px; color: var(--text3); margin-top: 3px; }
  .setting-item input[type="text"],
  .setting-item input[type="number"] {
    background: var(--bg); color: var(--text1);
    border: 1px solid var(--border); border-radius: var(--radius-sm);
    padding: 8px 11px; font-size: 13px; font-family: var(--font);
    outline: none; width: 100%;
    -webkit-transition: all 0.2s; transition: all 0.2s;
  }
  .setting-item input:focus { border-color: var(--blue); box-shadow: 0 0 0 3px rgba(80,152,240,0.1); }
  .setting-item input[type="number"] { width: 130px; }

  .btn-row { display: -webkit-flex; display: flex; gap: 8px; margin-top: 10px; }
  .btn-row button {
    background: var(--surface2); color: var(--text1);
    border: 1px solid var(--border); border-radius: var(--radius-sm);
    padding: 8px 15px; font-size: 12px; font-family: var(--font);
    cursor: pointer; -webkit-transition: all 0.2s; transition: all 0.2s;
  }
  .btn-row button:hover { background: #2a3142; }
  .btn-row button.btn-danger { color: var(--red); }
  .btn-row button.btn-danger:hover { background: var(--red-bg); border-color: rgba(240,83,75,0.4); }

  /* Toggle switch */
  .toggle-wrap {
    display: -webkit-flex; display: flex;
    -webkit-align-items: center; align-items: center;
    gap: 10px; cursor: pointer;
  }
  .toggle-sw {
    width: 38px; height: 22px;
    background: var(--border2); border-radius: 11px;
    position: relative; cursor: pointer;
    -webkit-transition: all 0.25s; transition: all 0.25s;
  }
  .toggle-sw.on { background: var(--green); box-shadow: 0 0 8px rgba(46,189,89,0.3); }
  .toggle-sw::after {
    content: ''; position: absolute;
    top: 2px; left: 2px;
    width: 18px; height: 18px;
    background: #fff; border-radius: 50%;
    -webkit-transition: -webkit-transform 0.25s; transition: transform 0.25s;
    box-shadow: 0 1px 3px rgba(0,0,0,0.3);
  }
  .toggle-sw.on::after { -webkit-transform: translateX(16px); transform: translateX(16px); }

  /* Textarea */
  textarea {
    width: 100%; min-height: 90px;
    background: var(--bg); color: var(--text1);
    border: 1px solid var(--border); border-radius: var(--radius-sm);
    padding: 11px; font-size: 12px; font-family: var(--font-mono);
    resize: vertical; outline: none;
    -webkit-transition: all 0.2s; transition: all 0.2s;
    box-shadow: inset 0 1px 2px rgba(0,0,0,0.2);
  }
  textarea:focus { border-color: var(--blue); box-shadow: 0 0 0 3px rgba(80,152,240,0.1), inset 0 1px 2px rgba(0,0,0,0.2); }

  /* Toast */
  .toast {
    position: fixed; bottom: 24px; left: 50%;
    -webkit-transform: translateX(-50%) translateY(20px); transform: translateX(-50%) translateY(20px);
    background: #2a3140; color: #fff;
    padding: 10px 24px; border-radius: 22px;
    font-size: 12px; font-weight: 500;
    opacity: 0; pointer-events: none; z-index: 999;
    box-shadow: 0 4px 20px rgba(0,0,0,0.4);
    -webkit-transition: all 0.3s; transition: all 0.3s;
    border: 1px solid var(--border);
  }
  .toast.show { opacity: 1; -webkit-transform: translateX(-50%) translateY(0); transform: translateX(-50%) translateY(0); }
  .toast.error { background: #3d1a1a; color: #fca5a5; border-color: rgba(240,83,75,0.3); }

  /* Error Banner */
  .error-banner {
    display: none; margin: 8px 14px;
    padding: 11px 15px;
    background: var(--red-bg);
    border: 1px solid rgba(240,83,75,0.25);
    border-radius: var(--radius-sm);
    font-size: 12px; color: #fca5a5;
    word-break: break-all;
    -webkit-user-select: text; user-select: text;
  }
  .error-banner.show { display: block; -webkit-animation: fadeIn 0.2s; animation: fadeIn 0.2s; }
  .error-banner .err-title { font-weight: 700; color: #f0534b; margin-bottom: 5px; font-size: 13px; }
  .error-banner .err-detail {
    color: var(--text2); font-size: 11px; font-family: var(--font-mono);
    white-space: pre-wrap; max-height: 130px; overflow-y: auto;
    margin-top: 5px; line-height: 1.5;
  }
  .error-banner .err-close {
    float: right; color: var(--text2); font-size: 16px;
    line-height: 1; cursor: pointer; padding: 0 5px;
    -webkit-transition: color 0.15s; transition: color 0.15s;
  }
  .error-banner .err-close:hover { color: #fff; }

  .footer {
    text-align: center; color: var(--text3);
    font-size: 10px; padding: 10px 8px; opacity: 0.4;
    letter-spacing: 0.2px;
  }
  /* Market Watch (baked inline) */
  .mw-row { display: flex; align-items: center; gap: 8px; padding: 8px 10px; border-radius: var(--radius-sm); margin-bottom: 4px; background: var(--surface); border: 1px solid var(--border); }
  .mw-row.mw-up { border-left: 3px solid #ff6b6b; }
  .mw-row.mw-down { border-left: 3px solid #4ddf7c; }
  .mw-row.mw-flat { border-left: 3px solid var(--text3); }
  .mw-info { flex: 1; min-width: 0; }
  .mw-code { font-weight: 700; color: var(--text1); font-size: 12px; font-family: var(--font-mono); }
  .mw-name { color: var(--text2); font-size: 10px; margin-left: 6px; }
  .mw-price { font-weight: 700; font-size: 14px; font-family: var(--font-mono); text-align: right; min-width: 60px; }
  .mw-up .mw-price { color: #ff6b6b; }
  .mw-down .mw-price { color: #4ddf7c; }
  .mw-change { font-size: 12px; font-family: var(--font-mono); text-align: right; min-width: 70px; font-weight: 600; }
  .mw-up .mw-change { color: #ff6b6b; }
  .mw-down .mw-change { color: #4ddf7c; }
  .mw-remove { background: none; border: none; color: var(--text3); cursor: pointer; font-size: 16px; padding: 0 2px; }
  .mw-remove:hover { color: var(--red); }
  .mw-empty { text-align: center; padding: 20px 10px; color: var(--text3); font-size: 12px; }
  .mw-add-row { display: flex; gap: 6px; margin-top: 8px; }
  .mw-add-row input { flex: 1; background: var(--surface); color: var(--text1); border: 1px solid var(--border); border-radius: var(--radius-sm); padding: 6px 8px; font-size: 12px; font-family: var(--font-mono); outline: none; }
  .mw-add-row input:focus { border-color: var(--blue); }
  .mw-add-row button { background: var(--blue); color: #fff; border: none; border-radius: var(--radius-sm); padding: 6px 12px; font-size: 11px; font-weight: 600; cursor: pointer; white-space: nowrap; }
  .mw-hint { font-size: 9px; color: var(--text3); margin-top: 4px; }
</style>
</head>
<body>

<div class="header">
  <div class="logo">📈 Stock JSON Clipper<span class="ver">V2.1</span></div>
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
  <button class="tab-btn" data-tab="watch">👁 盯盘</button>
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

<!-- ====== Tab: 盯盘 ====== -->
<div class="tab-content" id="tab-watch">
  <div class="main-area">
    <div class="card" style="margin-bottom:8px;">
      <div style="font-size:12px;font-weight:700;color:var(--text1);margin-bottom:6px;">📡 实时行情</div>
      <div style="font-size:10px;color:var(--text3);margin-bottom:8px;">
        数据源: 新浪财经 · 每3秒刷新 · 仅交易时段有效
      </div>
      <div id="mwQuotes">
        <div class="mw-empty">加载中...</div>
      </div>
      <div class="mw-add-row">
        <input type="text" id="mwAddInput" placeholder="输入6位代码, 如 000001" maxlength="6"
               onkeydown="if(event.key==='Enter')mwAddCode()">
        <button onclick="mwAddCode()">+ 添加</button>
      </div>
      <div class="mw-hint">支持最多6只股票 · 点击 × 移除</div>
    </div>
  </div>
</div>

<div class="toast" id="toast"></div>
<div class="footer">Stock JSON Clipper V2.1 · GPL-3.0 · 数据来源: 腾讯财经/新浪财经/东方财富</div>

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
    if (typeof pywebview === 'undefined' || !pywebview.api) { _timer = setTimeout(poll, 200); return; }
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
  // Delay first poll until pywebview is likely ready
  _timer = setTimeout(poll, 800);
})();

// Safe API caller — waits for pywebview to be ready
function _api(method) {
  return function() {
    var args = arguments;
    if (typeof pywebview === 'undefined' || !pywebview.api) {
      return Promise.reject(new Error('pywebview not ready'));
    }
    return pywebview.api[method].apply(pywebview.api, args);
  };
}

(function init() {
  function _ready(cb, retries) {
    retries = retries || 0;
    if (typeof pywebview !== 'undefined' && pywebview.api) { cb(); return; }
    if (retries > 50) return; // give up after 5s
    setTimeout(function() { _ready(cb, retries + 1); }, 100);
  }
  _ready(function() {
    loadConfig();
    refreshHistory();
    refreshStatus();
    pywebview.api.get_last_result_detail().then(function(detail) {
      if (detail && detail.meta && detail.meta.code) { window._currentResult = detail; renderResultCard(detail); }
    });
  });
  setTimeout(function() { document.getElementById('searchInput').focus(); }, 400);
})();

// ============================================================
// Market Watch — baked inline (was module JS)
// ============================================================
var _mwTimer = null;
function mwRefresh() {
  pywebview.api.mw_get_quotes().then(function(data) {
    var c = document.getElementById('mwQuotes');
    if (!c) return;
    if (!data || !Object.keys(data).length) {
      c.innerHTML = '<div class="mw-empty">暂无自选股<br><span style="font-size:10px;color:var(--text3)">下方添加代码开始盯盘</span></div>';
      return;
    }
    var codes = Object.keys(data).sort();
    var h = '';
    for (var i = 0; i < codes.length; i++) {
      var q = data[codes[i]], up = q.percent > 0, dn = q.percent < 0;
      var cls = up ? 'mw-up' : (dn ? 'mw-down' : 'mw-flat');
      h += '<div class="mw-row ' + cls + '">';
      h += '<div class="mw-info"><span class="mw-code">' + codes[i] + '</span><span class="mw-name">' + (q.name || '--') + '</span></div>';
      h += '<div class="mw-price">' + (q.current ? q.current.toFixed(2) : '--') + '</div>';
      h += '<div class="mw-change">' + (up ? '▲' : (dn ? '▼' : '—')) + ' ' + (q.percent ? q.percent.toFixed(2) : '0.00') + '%</div>';
      h += '<button class="mw-remove" onclick="event.stopPropagation();pywebview.api.mw_remove_code(\'' + codes[i] + '\').then(function(){mwRefresh();})">&times;</button>';
      h += '</div>';
    }
    c.innerHTML = h;
  });
}
function mwAddCode() {
  var v = document.getElementById('mwAddInput').value.trim().replace(/[#WM:]/g, '');
  if (!/^\d{6}$/.test(v)) return;
  pywebview.api.mw_add_code(v).then(function(r) {
    if (r && r.success) { document.getElementById('mwAddInput').value = ''; mwRefresh(); }
  });
}
// Poll watch when tab is visible
setInterval(function() {
  var tab = document.getElementById('tab-watch');
  if (tab && tab.classList.contains('active')) mwRefresh();
}, 2500);
setTimeout(mwRefresh, 800);
</script>
</body>
</html>
"""


# ============================================================
# Python-side API exposed to JS
# ============================================================
class PanelAPI:
    """API class exposed to the PyWebView JavaScript context.

    Core methods (get_history, search_stock, etc.) are defined directly.
    Feature module methods are dynamically attached from the module registry
    — no hardcoded module imports needed.
    """

    def __init__(self, clipper: "StockClipper") -> None:
        self._clipper = clipper
        # Dynamically attach module API methods from registry
        for name, func in clipper.registry.get_all_api_methods().items():
            setattr(self, name, func)

    def ping(self) -> str:
        """Diagnostic: verify JS↔Python bridge works."""
        return "pong"

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
                        StockRequest(code=actual_code, period=actual_period, save_mode=True, raw=code))
                except Exception:
                    pass

            if result.status == "error":
                return {"success": False, "error": result.message}
            return {"success": True}
        except Exception as e:
            import traceback
            tb = traceback.format_exc()
            log.error("search_stock failed for %s: %s", code, e)
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
            title="Stock JSON Clipper V2.1",
            html=PANEL_HTML,
            width=560,
            height=760,
            resizable=True,
            on_top=False,
            js_api=api,
        )

        def _on_closed():
            global _panel_window
            _panel_window = None

        _panel_window.events.closed += _on_closed

        # Pick GUI backend: Windows → edgechromium, Linux → gtk
        import sys as _sys
        gui = None
        if _sys.platform == "win32":
            gui = "edgechromium"
        elif _sys.platform == "linux":
            gui = "gtk"

        try:
            webview.start(gui=gui, debug=False)
        except Exception:
            # Fallback: let pywebview auto-detect
            webview.start(gui=None, debug=False)
