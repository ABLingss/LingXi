#!/usr/bin/env python3
"""
main.py — Stock JSON Clipper V2.2 entry point.

Two modes:
  1. CLI mode:    python3.9 main.py --code 000001          (fetch & print JSON)
  2. Tray mode:   python3.9 main.py                        (full tray + panel)
  3. Debug mode:  python3.9 main.py --debug                (tray + console output)

Usage:
  python3.9 main.py                        # Launch tray app
  python3.9 main.py --code 000001          # CLI: fetch single stock
  python3.9 main.py --code #000001         # CLI: save to file
  python3.9 main.py --debug                # Tray app with console logging
"""

import argparse
import os
import signal
import sys

# Fix UnicodeEncodeError on Windows console (GBK can't encode emoji)
# Note: sys.stdout is None in --noconsole (Windows GUI) mode
if sys.stdout is not None and sys.stdout.encoding:
    try:
        if sys.stdout.encoding.upper() in ('GBK', 'CP936', 'CP950'):
            sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

# Ensure the project root is on sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.logging_setup import init_logging, get_logger
from core.config import load_config
from core.clipper import StockClipper

log = get_logger("main")


def run_cli(args) -> None:
    """CLI mode: fetch stock data via stock-api npx."""
    import subprocess, json as _json

    code = args.code.strip()
    period = args.period
    count = args.count if args.count is not None else 250

    # Convert to stock-api code format
    if not code.startswith(("SH", "SZ", "HK", "US")):
        if code.startswith(("60", "68")):
            code = f"SH{code}"
        else:
            code = f"SZ{code}"

    period_map = {"daily": "day", "weekly": "week", "monthly": "month",
                  "1min": "day", "5min": "day", "15min": "day", "30min": "day", "60min": "day"}
    sp = period_map.get(period, "day")

    print(f"Stock JSON Clipper V3.2 (CLI)")
    print(f"   Code: {code}  |  Period: {period}  |  Count: {count}")
    print(f"{'=' * 50}")

    try:
        print("Fetching via stock-api...")
        result = subprocess.run(
            ["npx", "-y", "stock-api", "get-klines", code, "--period", sp, "--count", str(count)],
            capture_output=True, text=True, timeout=30, shell=True)
        if result.returncode != 0:
            print(f"Error: stock-api failed. Is Node.js >=18 installed?")
            print(result.stderr[:500])
            sys.exit(1)
        kline_data = _json.loads(result.stdout)
        if not isinstance(kline_data, list):
            kline_data = kline_data.get("data", kline_data.get("klines", []))

        # Also get stock info
        result2 = subprocess.run(
            ["npx", "-y", "stock-api", "get-stock", code],
            capture_output=True, text=True, timeout=15, shell=True)
        stock_info = _json.loads(result2.stdout) if result2.returncode == 0 else {"name": code}

        print(f"   Got {len(kline_data)} bars")

    except FileNotFoundError:
        print("Error: Node.js not found. Install Node.js >=18 or use the GUI panel.")
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

    # Compute indicators
    from data.indicators import calc_all_indicators
    from data.builder import build_summary, to_json_string
    closes = [k.get("close", 0) for k in kline_data]
    indicators = calc_all_indicators(closes)
    summary_data = build_summary(kline_data)

    meta = {
        "code": code, "name": stock_info.get("name", code),
        "market": "沪市" if code.startswith("SH") else "深市",
        "period": period, "data_count": len(kline_data),
        "start_date": kline_data[0].get("date", "") if kline_data else "",
        "end_date": kline_data[-1].get("date", "") if kline_data else "",
    }
    result_json = {"meta": meta, "indicators": indicators, "summary": summary_data, "data": kline_data}
    json_str = to_json_string(result_json)

    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(json_str)
        print(f"Saved to {args.output}")
    else:
        print(json_str)


def run_tray(args) -> None:
    """Tray mode: launch the full system tray application."""
    from ui.tray import run_tray

    print("📈 Stock JSON Clipper V3.2")
    print("   Starting system tray mode...")
    print("   Copy a 6-digit stock code (e.g. 000001) in any application.")
    print("   Right-click the tray icon for options.")
    print("   Press Ctrl+C to exit.")

    config_path = args.config if hasattr(args, 'config') and args.config else None
    clipper = StockClipper(config_path=config_path)

    # Register built-in feature modules
    from modules.prompt.formula import PromptModule
    clipper.registry.register(PromptModule(), clipper)

    # Graceful shutdown on Ctrl+C
    def _shutdown(signum, frame):
        print("\n🛑 Shutting down...")
        clipper.stop()
        sys.exit(0)

    signal.signal(signal.SIGINT, _shutdown)
    signal.signal(signal.SIGTERM, _shutdown)

    # Start background threads
    clipper.start()

    # Run tray (blocking)
    auto_show = not args.no_panel
    try:
        clipper.run_tray(auto_show_panel=auto_show)
    except KeyboardInterrupt:
        pass
    finally:
        clipper.stop()


def main() -> None:
    # Initialize logging early
    init_logging()
    log.info("Stock JSON Clipper V3.2 starting")

    parser = argparse.ArgumentParser(
        description="Stock JSON Clipper V3.2 — A-share stock data to AI-ready JSON",
    )
    parser.add_argument(
        "--code", "-c",
        type=str,
        default=None,
        help="6-digit stock code for CLI mode (e.g. 000001, #000001, W:000001). "
             "If omitted, launches tray mode.",
    )
    parser.add_argument(
        "--period", "-p",
        type=str,
        default="daily",
        choices=["1min", "5min", "15min", "30min", "60min", "daily", "weekly", "monthly"],
        help="K-line period for CLI mode (default: daily).",
    )
    parser.add_argument(
        "--count", "-n",
        type=int,
        default=None,
        help="Number of K-line bars for CLI mode (default: from config, 250).",
    )
    parser.add_argument(
        "--output", "-o",
        type=str,
        default=None,
        help="Save JSON to file instead of stdout (CLI mode).",
    )
    parser.add_argument(
        "--config",
        type=str,
        default=None,
        help="Path to config.ini file.",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug/console logging.",
    )
    parser.add_argument(
        "--no-panel",
        action="store_true",
        help="Do not auto-show the info panel on startup.",
    )

    args = parser.parse_args()

    if args.code:
        # CLI mode
        run_cli(args)
    else:
        # Tray mode
        run_tray(args)


if __name__ == "__main__":
    main()
