# Stock JSON Clipper V2.1

A股数据与AI分析之间的桥梁。复制股票代码即可生成结构化JSON，粘贴到ChatGPT/DeepSeek/Claude进行分析。

## 下载

从 [Releases](https://github.com/ABLingss/Stock-JSON-Clipper/releases) 下载最新版本：

- **Windows 10/11**: `StockJSONClipper.exe`（绿色免安装）或 `StockJSONClipper-Setup-V2.1.exe`（安装器）
- **Linux**: 从源码运行（见下方）

> 不再支持 macOS。

## 使用方法

### 启动

双击 `StockJSONClipper.exe`，系统托盘出现图标。右键 → **显示面板** 打开操作界面。

### 获取数据

**剪贴板自动识别：** 在股票软件中复制6位代码（`Ctrl+C`），自动生成JSON到剪贴板，直接粘贴给AI。

**面板手动输入：** 在搜索框输入代码点击查询。

### 输入格式

| 输入 | 含义 |
|------|------|
| `000001` | 日线数据 |
| `W:000001` | 周线数据 |
| `M:000001` | 月线数据 |
| `#000001` | 保存为本地JSON |

### 功能

- **数据查询**: K线 + MA/MACD/RSI/BOLL 技术指标
- **AI分析**: 粘贴通达信选股公式 → 生成分析提示词
- **实时盯盘**: 新浪实时行情，红涨绿跌，最多6股同屏

## 从源码运行

```bash
git clone https://github.com/ABLingss/Stock-JSON-Clipper.git
cd Stock-JSON-Clipper
pip install pyperclip pystray pywebview requests Pillow
python main.py                 # 托盘模式
python main.py --code 000001   # CLI 模式
```

## 构建

```bash
pip install pyinstaller pyperclip pystray pywebview requests Pillow

# Windows
python -m PyInstaller StockJSONClipper.spec

# 安装器 (需 Inno Setup 6)
iscc installer.iss
```

## 项目结构

```
core/      配置、缓存、剪贴板、日志、模块注册
api/       腾讯/新浪/东财 K线 + 新浪实时行情
data/      技术指标计算、JSON 构建
ui/        系统托盘、WebView 面板
modules/   AI分析、实时盯盘
```

## 数据来源

腾讯财经、新浪财经、东方财富的公开API。

## License

GPL-3.0 — 本项目集成了 [RollerCoaster](https://github.com/YQBaobao/RollerCoaster) 的实时行情组件。
