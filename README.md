# 灵析 (LingXi) — 你的A股AI分析师

> 🧠 把股票代码变成 AI 分析提示词。粘贴到 ChatGPT / DeepSeek / Claude，秒出专业研报。

<p align="center">
  <strong>输入代码 → 技术指标 → SVG图表 → AI提示词 → 一键复制</strong>
</p>

---

## 🤔 你是不是也有这个问题？

**场景一：**

你在通达信写了个选股公式——`CROSS(MA(C,5), MA(C,20)) AND RSI(6) > 50`——然后想：「这公式现在到底成不成立？AI 能不能帮我分析一下？」

于是你手动打开行情软件 → 截图K线 → 翻遍均线/MACD/RSI数值 → 一个个敲进 ChatGPT → 还得解释公式啥意思……

**十分钟过去了，你还没开始真正的分析。**

**场景二：**

你想写个量化策略，需要干净的 A 股 JSON 数据（OHLCV + 均线 + MACD + RSI + 布林带）。现有选择：写爬虫（维护地狱）、买数据（年费几千）、用 tushare（要 token）……

**你就是想要个数据，为什么要这么麻烦？**

---

## ✅ 灵析怎么解决

<p align="center">
  <b>你只需要输入一个股票代码。<br>剩下的——查数据、算指标、画图表、写提示词——全部自动完成。</b>
</p>

```
你做的事                          灵析做的事
─────────                      ────────────────
输入 000001           →         三源灾备获取K线数据
                                （腾讯→新浪→东财自动切换）

（啥也不用干）         →         计算 MA5/10/20/60
                                MACD(DIF/DEA/BAR)
                                RSI(6)/RSI(12)
                                布林带(上/中/下)

（啥也不用干）         →         生成 SVG 技术图表
                                K线+成交量+MACD+RSI 统一画布
                                鼠标悬停看即时数据

粘贴通达信公式         →         自动解析公式要素
                                逐条判断条件是否满足
                                生成结构化AI分析提示词

点一下复制            →         粘贴到任何AI对话框
                                获得专业级技术分析
```

---

## 📸 一眼看清

![灵析主界面](assets/image.png)

---

## 🔥 杀手功能：通达信公式 → AI分析

这是**市面上唯一**把通达信公式自动转成 AI 提示词的工具。

### 你输入：

```
CROSS(MA(C,5), MA(C,20)) AND MACD.DIF > MACD.DEA
AND RSI(6) > 50 AND C > BOLL.MID
```

### 灵析输出（自动复制到剪贴板）：

```markdown
# A股技术分析任务

请对 **000001 平安银行** 进行技术分析，结合以下选股公式逐条判断是否满足条件。

## 当前技术指标

  **均线**: MA5=11.65 | MA10=11.58 | MA20=11.42 | MA60=10.89
  **均线排列**: 多头排列 📈
  **MACD**: DIF=0.0812  DEA=0.0523  BAR=0.0578
  **MACD状态**: DIF在DEA上方，多头主导 ↑
  **RSI**: RSI(6)=62.50  RSI(12)=58.30
  **布林带**: 上轨=12.15  中轨=11.42  下轨=10.69

## 选股条件逐条判断

| 条件 | 是否满足 | 依据 | 置信度 |
|------|----------|------|--------|
| CROSS(MA(C,5), MA(C,20)) | 是/否 | (给出具体数值) | 高/中/低 |
| MACD.DIF > MACD.DEA | 是 | DIF=0.0812 > DEA=0.0523 | 高 |
| RSI(6) > 50 | 是 | RSI(6)=62.50 > 50 | 高 |
| C > BOLL.MID | 是/否 | (给出具体数值) | 高/中/低 |

## 综合结论

| 评分项 | 得分 | 说明 |
|--------|------|------|
| 趋势 | _/3 | |
| 动量 | _/3 | |
| 量价 | _/2 | |
| 位置 | _/2 | |
| **总分** | **_/10** | |

### 操作建议
- 方向: 买入/持有/减仓/观望
- 仓位: 轻/中/重
- 入场 / 止损 / 目标
```

**粘贴到 DeepSeek / ChatGPT / Claude → 30秒获得专业研报级分析。**

---

## 🎯 为什么用灵析

| 你现在的做法 | 用灵析之后 |
|-------------|-----------|
| 打开同花顺→找K线→截图→敲数据→问AI | 输入代码→点AI分析→粘贴→完事 |
| 手动计算均线/MACD/RSI | 自动算，精确到小数点后4位 |
| 公式看不懂，条件判断靠猜 | 逐条自动判断，附带依据和数值 |
| 软件几百MB，弹窗烦人 | 20MB绿色exe，安静待在托盘 |
| 数据锁在软件里拿不出来 | JSON格式，随便接任何工具 |

---

## 📦 下载

从 [Releases](https://github.com/ABLingss/LingXi/releases) 下载最新版本：

| 平台 | 文件 | 说明 |
|------|------|------|
| 🪟 **Windows 10/11** | `LingXi.exe` | 绿色免安装，双击即用 |
| 🐧 **Linux** | 从源码运行 | `python main.py` |

> 需要 Windows WebView2 运行时（Win11 自带，Win10 会自动提示安装）。

---

## 🚀 快速开始

### GUI 模式（推荐）

```
双击 LingXi.exe
    ↓
托盘出现图标 📈
    ↓
右键 → 显示面板
    ↓
输入股票代码 → 回车
```

### CLI 模式（量化/脚本党）

```bash
# 直接输出完整JSON到终端
python main.py --code 000001

# 保存到文件
python main.py --code 000001 --output data.json

# 自定义周期和数量
python main.py --code SH600519 --period weekly --count 100
```

输出 JSON 结构：
```json
{
  "meta": {
    "code": "SZ000001",
    "name": "平安银行",
    "market": "深市",
    "period": "daily",
    "data_count": 250
  },
  "indicators": {
    "ma5": 11.65,
    "ma10": 11.58,
    "ma20": 11.42,
    "ma60": 10.89,
    "macd": {"dif": 0.0812, "dea": 0.0523, "bar": 0.0578},
    "rsi_6": 62.5,
    "rsi_12": 58.3,
    "boll": {"upper": 12.15, "mid": 11.42, "lower": 10.69}
  },
  "summary": {
    "period_change": 8.52,
    "volatility": 28.3,
    "max_close": 12.05,
    "min_close": 10.21
  },
  "data": [
    {"date": "2025-01-02", "open": 10.50, "high": 10.80, "low": 10.45, "close": 10.72, "volume": 45678900},
    ...
  ]
}
```

---

## 🧩 全部功能

### 📊 技术图表
- K线图 + 成交量柱 + MACD + RSI 四合一画布
- MACD/RSI 可选开关，想看哪个看哪个
- 鼠标任意位置悬停即时显示 OHLCV 数据
- 点击图表弹出大图，方便截图分享

### 🔄 多股对比
- 点 **+** 添加多只股票
- 并排对比 MA/MACD/RSI/涨跌幅
- 每只独立图表，一目了然
- 自动生成多股排序提示词

### 🤖 AI 分析引擎
- **AI分析**: 粘贴通达信公式 → 解析 + 判断 + 生成提示词
- **深度分析**: 无公式也能做，完整6维度框架（趋势/动量/量价/支撑压力/形态/风险）
- **对比模式**: 多股自动生成排序 + 横向对比提示词
- 提示词全部自动复制到剪贴板，粘贴即用

### 📈 通达信公式引擎 (V1)
- 解析通达信公式语法（MA/CROSS/MACD/RSI/BOLL/REF/HHV/LLV/...）
- 计算指标时间序列
- 结构化 JSON 输出

### ⏰ 价格预警引擎
- 后台轮询，阈值触发通知
- 托盘弹窗提醒，不打扰工作流

### 📋 数据操作
- **复制 JSON**: 一键复制完整结构化数据
- **保存文件**: 导出 .json 到本地
- **历史记录**: 查过的股票都有记录

---

## 🛠 从源码运行

```bash
git clone https://github.com/ABLingss/LingXi.git
cd LingXi
pip install pyperclip pystray pywebview requests Pillow
python main.py
```

### CLI 模式需要 Node.js ≥18

```bash
python main.py --code 000001
```

---

## 🏗 项目架构

```
main.py                  入口（CLI + Tray 双模式）
core/
  clipper.py             核心调度器
  config.py              INI 配置（自动写入 exe 同级目录）
  cache.py               TTL 内存缓存
  registry.py            插件注册系统
  alert_engine.py        后台价格预警引擎
  logging_setup.py       日志轮转
data/
  indicators.py          纯 Python 技术指标（无 numpy）
  builder.py             JSON 组装 + 统计摘要
  formula_engine/        通达信公式解析引擎
ui/
  tray.py                pystray 系统托盘
  panel.py               WebView 面板（70KB，全内置）
modules/prompt/
  formula.py             公式 → AI 提示词生成器
```

**技术栈**: Python 3.9+ · pywebview · pystray · 纯 Python 指标计算（零依赖） · stock-api 浏览器包（内嵌） · PyInstaller 单文件打包

---

## 📄 协议

GPL-3.0 — 集成了 [stock-api](https://github.com/zhangxiangliang/stock-api) (MIT) 和 [RollerCoaster](https://github.com/YQBaobao/RollerCoaster) (GPL-3.0)。

---

<p align="center">
  <sub>股市有风险，投资需谨慎。灵析提供的分析仅供参考，不构成投资建议。</sub>
</p>
