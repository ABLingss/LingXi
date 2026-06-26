#!/usr/bin/env python3.9
"""
main.py — Stock JSON Clipper V2.0 entry point.

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
from core.config import load_config, save_config
from core.clipper import StockClipper

log = get_logger("main")


def run_cli(args) -> None:
    """CLI mode: fetch a single stock code and output JSON to stdout or file."""
    from api.client import fetch_kline, fetch_stock_info, StockError
    from data.builder import build_json, to_json_string
    from core.clipboard import parse_clipboard

    # Parse code with optional prefixes
    raw_code = args.code.strip()
    request = parse_clipboard(raw_code)

    if request is None:
        print(f"Error: Invalid stock code '{raw_code}'. Must be 6 digits.")
        print("Supported formats: 000001, #000001, W:000001, M:000001")
        sys.exit(1)

    code = request.code
    period = request.period

    # Override period if explicitly provided
    if args.period != "daily":
        period = args.period

    cfg = load_config()
    count = args.count if args.count is not None else cfg["default_count"]
    timeout = cfg.get("request_timeout", 5)

    print(f"📈 Stock JSON Clipper V2.0 (CLI)")
    print(f"   Code: {code}  |  Period: {period}  |  Count: {count}")
    print(f"{'─' * 50}")

    # Fetch
    try:
        print("⏳ Fetching K-line data...")
        kline_data = fetch_kline(code, period=period, count=count, timeout=timeout)
        print(f"   ✅ Got {len(kline_data)} bars ({kline_data[0]['date']} ~ {kline_data[-1]['date']})")

        print("⏳ Fetching stock info...")
        stock_info = fetch_stock_info(code, timeout=timeout)
        print(f"   ✅ {stock_info['name']} | {stock_info['industry']} | PE(TTM): {stock_info['pe_ttm']}")

    except StockError as e:
        print(f"❌ Error: {e.message}")
        sys.exit(1)

    # Build JSON
    print("⏳ Computing indicators & building JSON...")
    result = build_json(kline_data, stock_info, code, period=period, count=count)
    json_str = to_json_string(result)

    # Output
    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(json_str)
        print(f"✅ Saved to {args.output}")
    elif request.save_mode:
        # #save mode: write to file, print path
        import time
        date_str = time.strftime("%Y%m%d")
        safe_name = stock_info["name"].replace("/", "_").replace("\\", "_").replace(" ", "")
        filename = f"{code}_{safe_name}_{date_str}.json"
        filepath = os.path.join(os.getcwd(), filename)
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(json_str)
        print(f"✅ Saved to {filepath}")
    else:
        print(f"{'─' * 50}")
        print(json_str)

    # Summary
    print(f"\n{'─' * 50}")
    print(f"📊 Summary:")
    print(f"   Name: {result['meta']['name']}")
    print(f"   Market: {result['meta']['market']}")
    print(f"   Period Change: {result['summary']['period_change']}%")
    print(f"   MA5: {result['indicators']['ma5']}  MA20: {result['indicators']['ma20']}")
    macd = result['indicators']['macd']
    print(f"   MACD: DIF={macd['dif']}  DEA={macd['dea']}  BAR={macd['bar']}")
    print(f"   RSI(6): {result['indicators']['rsi_6']}  RSI(12): {result['indicators']['rsi_12']}")


def run_tray(args) -> None:
    """Tray mode: launch the full system tray application."""
    from ui.tray import run_tray

    print("📈 Stock JSON Clipper V2.0")
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
    log.info("Stock JSON Clipper V2.1 starting")

    parser = argparse.ArgumentParser(
        description="Stock JSON Clipper V2.1 — A-share stock data to AI-ready JSON",
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
        choices=["daily", "weekly", "monthly"],
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
