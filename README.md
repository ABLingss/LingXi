# Stock JSON Clipper V2.0

A股数据与AI分析之间的桥梁。复制股票代码即可生成结构化JSON，粘贴到ChatGPT/DeepSeek/Claude进行分析。

## 这是什么

在通达信、同花顺等股票软件中复制代码，自动拉取K线数据和技术指标，生成AI可直接理解的JSON格式。纯本地运行，无需安装Python或任何运行环境。

## 下载

从 [Releases](https://github.com/ABLingss/Stock-JSON-Clipper/releases) 下载最新版本：

- **Windows 10/11**: 下载 `StockJSONClipper.exe`（单文件，双击运行）
- **macOS**: 下载 `StockJSONClipper.app`

> Windows 用户若杀毒软件报警，请添加白名单。本程序无恶意行为，代码完全开源。

## 使用方法

### 1. 启动程序

双击 `StockJSONClipper.exe`，程序会在系统托盘（屏幕右下角）显示图标。

### 2. 获取数据

**方式一（剪贴板自动识别）：**
在股票软件中选中6位代码按 `Ctrl+C`，程序自动识别并生成JSON到剪贴板，直接 `Ctrl+V` 粘贴到AI对话框。

**方式二（面板手动输入）：**
右键托盘图标 → 显示面板，在搜索框输入代码点击查询。

### 3. 支持的输入格式

| 输入 | 含义 |
|------|------|
| `000001` | 深市平安银行，日线数据 |
| `W:000001` | 周线数据 |
| `M:000001` | 月线数据 |
| `#000001` | 保存为本地JSON文件（不入剪贴板） |

### 4. 输出内容

生成的JSON包含：股票基本信息、MA/MACD/RSI/BOLL技术指标、区间统计摘要、原始K线数据。

### 5. 公式辅助

在面板中粘贴通达信选股公式（如 `CROSS(MA(C,5), MA(C,20)) AND RSI(6)>50`），点击生成AI分析提示词，粘贴到AI对话框获取逐条条件判断。

## 从源码运行

```bash
git clone https://github.com/ABLingss/Stock-JSON-Clipper.git
cd Stock-JSON-Clipper
pip install pyperclip pystray pywebview requests Pillow
python main.py
```

CLI模式：`python main.py --code 000001`

## 构建

```bash
pip install pyinstaller pyperclip pystray pywebview requests Pillow
bash build.sh
```

输出在 `dist/` 目录。

## 数据来源

腾讯财经、新浪财经、东方财富的公开API。纯个人学习研究用途。

## 配置

首次运行自动生成 `config.ini`，可在面板设置中修改：数据条数、保存目录、缓存时间、轮询间隔等。

## License

MIT
