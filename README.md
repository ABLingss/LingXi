# 📈 Stock JSON Clipper V2.0

<div align="center">

**零安装 · 纯本地 · 剪贴板驱动 · AI就绪**

[![Version](https://img.shields.io/badge/version-2.0-blue)](https://github.com/ABLingss/Stock-JSON-Clipper/releases)
[![Platform](https://img.shields.io/badge/platform-Windows%20%7C%20macOS%20%7C%20Linux-lightgrey)](https://github.com/ABLingss/Stock-JSON-Clipper/releases)
[![License](https://img.shields.io/badge/license-MIT-green)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.9%2B-orange)](https://python.org)

</div>

---

## 简介

**Stock JSON Clipper** 是一座连接传统股票软件与 AI 大模型的数据桥梁。

在通达信/同花顺中 `Ctrl+C` 复制股票代码 → 自动生成结构化 JSON（含技术指标）→ `Ctrl+V` 粘贴到 ChatGPT/DeepSeek 对话框。让 AI 拥有实时、准确的 A 股数据。

**V2.0 新增**: 🎯 面板直接输入代码查询 · 📊 实时指标卡片 · 🎨 全新原生感 UI


## ✨ 功能亮点

| 功能 | 说明 |
|------|------|
| 🔍 **双输入模式** | 剪贴板自动识别 或 面板手动输入股票代码 |
| 📊 **8项技术指标** | MA(5/10/20/60)、MACD(DIF/DEA/柱)、RSI(6/12)、BOLL(上/中/下) |
| 📅 **多周期支持** | 日线 / 周线 / 月线（`W:` `M:` 前缀或面板下拉） |
| 💾 **本地保存** | `#` 前缀保存全量历史数据为 JSON 文件 |
| 🧠 **公式辅助** | 粘贴通达信选股公式 → 自动解析 → 生成 AI 分析 Prompt |
| ⚡ **5分钟缓存** | 避免重复请求，东方财富 API 1次/秒安全线 |
| 🔒 **纯本地运行** | 无数据上传，无遥测，代码完全开源 |
| 🎨 **原生桌面体验** | 系统托盘 + WebView 面板（Windows: Edge, macOS: WebKit） |


## 🚀 快速开始

### Windows

从 [Releases](https://github.com/ABLingss/Stock-JSON-Clipper/releases) 下载 `StockJSONClipper.exe`（~22MB 单文件），双击运行。

> 部分杀毒软件可能误报，请将 exe 添加至白名单。本程序无恶意行为，代码完全开源。

### macOS

```bash
# 下载 StockJSONClipper 或 StockJSONClipper.app
# 双击运行或:
chmod +x StockJSONClipper
./StockJSONClipper
```

### 从源码运行

```bash
git clone https://github.com/ABLingss/Stock-JSON-Clipper.git
cd Stock-JSON-Clipper

pip install pyperclip pystray pywebview requests Pillow
python3 main.py                    # 启动托盘模式
python3 main.py --code 000001      # CLI 模式: 查询单只股票
```


## 📖 使用方法

### 方式一：剪贴板模式（后台自动）

| 复制内容 | 含义 |
|----------|------|
| `000001` | 深市平安银行 — 日线数据（默认250条） |
| `W:000001` | 周线数据 |
| `M:000001` | 月线数据 |
| `#000001` | 保存全量历史数据为本地 JSON 文件 |
| `#W:000001` | 保存周线全量数据到本地文件 |

1. 确保 Stock JSON Clipper 在系统托盘运行（右下角图标）
2. 在股票软件中复制代码（`Ctrl+C`）
3. 程序自动识别 → 拉取数据 → 生成 JSON → 写入剪贴板
4. 到 AI 对话框粘贴（`Ctrl+V`）即可

### 方式二：面板输入（V2.0 新增）

1. 右键托盘图标 → 📊 显示面板
2. 在顶部搜索框输入 6 位代码，选择周期
3. 点击「查询」→ 查看实时指标卡片
4. 点击「复制 JSON」或「生成 AI Prompt」

### 公式辅助

1. 在面板切换到「🤖 公式辅助」标签
2. 粘贴通达信选股公式（如 `CROSS(MA(C,5), MA(C,20)) AND RSI(6)>50`）
3. 点击「生成 Prompt」→ 自动复制到剪贴板
4. 粘贴到 AI 对话框 → AI 会结合当前数据逐条判断条件


## 📦 输出格式

程序生成的 JSON 包含以下结构：

```
{
  "meta": {
    "code": "000001",           // 股票代码
    "name": "平安银行",         // 股票名称
    "market": "深市",           // 市场
    "industry": "银行",         // 行业
    "pe_ttm": 5.23,            // PE(TTM)
    "total_mv": 213456789012,   // 总市值
    "period": "daily",          // 周期
    "start_date": "2025-06-01", // 起始日期
    "end_date": "2026-06-19"    // 结束日期
  },
  "indicators": {
    "ma5": 12.34,               // 5日均线
    "ma10": 12.10,              // 10日均线
    "ma20": 11.88,              // 20日均线
    "ma60": 11.52,              // 60日均线
    "macd": {
      "dif": 0.1250,            // MACD快线
      "dea": 0.0820,            // MACD慢线
      "bar": 0.0860             // MACD柱
    },
    "rsi_6": 55.20,             // RSI(6)
    "rsi_12": 52.30,            // RSI(12)
    "boll": {
      "upper": 13.45,           // 布林上轨
      "mid": 11.88,             // 布林中轨
      "lower": 10.31            // 布林下轨
    }
  },
  "summary": {
    "period_change": 5.23,      // 区间涨跌幅(%)
    "max_close": 13.45,         // 最高收盘价
    "min_close": 10.20,         // 最低收盘价
    "avg_volume": 85000000,     // 平均成交量
    "volatility": 28.50         // 年化波动率(%)
  },
  "data": [...]                 // 原始K线数据（日期、OHLCV）
}
```


## 🏗 技术架构

```
┌─────────────────────────────────────────────────┐
│                   System Tray                     │
│  ┌──────────┐     ┌───────────────────────────┐  │
│  │ pystray  │     │      PyWebView Panel       │  │
│  │ Tray Icon│     │  ┌─────────┬─────────────┐ │  │
│  │ + Menu   │     │  │  Result  │   History   │ │  │
│  │          │     │  │  Card    │   Table     │ │  │
│  └──────────┘     │  ├─────────┴─────────────┤ │  │
│                    │  │ Settings │  Formula   │ │  │
│                    │  └──────────────────────┘ │  │
│                    └───────────────────────────┘  │
├─────────────────────────────────────────────────┤
│              StockClipper (Core)                  │
│  ┌──────────┐  ┌──────────┐  ┌───────────────┐  │
│  │Clipboard │  │  Fetch   │  │  Cache         │  │
│  │ Monitor  │  │  Worker  │  │  Manager       │  │
│  │(0.5s poll)│ │(queue)  │  │  (5min TTL)   │  │
│  └──────────┘  └──────────┘  └───────────────┘  │
├─────────────────────────────────────────────────┤
│              Data Layer                           │
│  ┌──────────┐  ┌──────────┐  ┌───────────────┐  │
│  │EastMoney │  │Technical │  │  JSON Builder  │  │
│  │  API     │  │Indicators│  │  + Formatter   │  │
│  │ Client   │  │ (pure Py)│  │                │  │
│  └──────────┘  └──────────┘  └───────────────┘  │
└─────────────────────────────────────────────────┘
```

**依赖链**: 无 numpy/pandas — 纯 Python 数学计算，PyInstaller 打包后 ~22MB。


## 🔧 构建

```bash
# 安装构建依赖
pip install pyinstaller pyperclip pystray pywebview requests Pillow

# 构建当前平台可执行文件
bash build.sh

# 清理构建产物
bash build.sh clean

# 输出
# Windows → dist/StockJSONClipper.exe
# macOS   → dist/StockJSONClipper  /  StockJSONClipper.app
# Linux   → dist/StockJSONClipper
```


## ⚙️ 配置

首次运行自动生成 `config.ini`，也可在面板「设置」标签中修改：

| 配置项 | 默认值 | 说明 |
|--------|--------|------|
| `output_format` | json | 输出格式（json） |
| `default_count` | 250 | 默认拉取K线条数 |
| `poll_interval` | 0.5 | 剪贴板轮询间隔（秒） |
| `cache_ttl` | 300 | 缓存时间（秒） |
| `request_timeout` | 5 | API 请求超时（秒） |


## 📋 数据源

- **K线数据**: 东方财富公开 API (`push2his.eastmoney.com`)
- **股票信息**: 东方财富公开 API (`push2.eastmoney.com`)
- **频率限制**: 内置 1次/秒 安全线，5分钟缓存
- 纯个人学习研究用途，请勿用于商业高频场景


## ❓ 常见问题

<details>
<summary><b>Q: 复制代码后无反应？</b></summary>
确认复制的文本仅为6位数字（如 <code>000001</code>），不含其他文字。或使用面板搜索框直接输入。
</details>

<details>
<summary><b>Q: 杀毒软件报毒？</b></summary>
本工具由 PyInstaller 打包为单文件程序，部分杀软会误报。请将 <code>StockJSONClipper.exe</code> 添加到白名单。
</summary>

<details>
<summary><b>Q: 提示"数据拉取超时"？</b></summary>
检查网络连接。本工具需要联网访问东方财富公开API。
</details>

<details>
<summary><b>Q: 如何彻底退出？</b></summary>
右键托盘图标 → ❌ 退出。关闭面板不会退出程序。
</details>

<details>
<summary><b>Q: 支持哪些股票？</b></summary>
A股（沪深两市）：60xxxx、688xxx、00xxxx、30xxxx。不支持港股/美股。
</details>


## 🤝 贡献

欢迎提交 Issue 和 Pull Request。

```bash
# 运行测试
python3 test_pipeline.py

# 开发模式（带控制台输出）
python3 main.py --debug
```


## 📄 License

MIT © 2026 Stock JSON Clipper Contributors

---

<div align="center">
  <sub>Built with ❤️ for A-share investors and AI enthusiasts</sub>
</div>
