"""
stock_clipper.py — Core orchestrator for Stock JSON Clipper V2.0.

Ties together clipboard monitoring, API fetching, indicator calculation,
JSON assembly, cache management, file saving, and UI notifications.

Threading:
  - Main thread: runs the tray (pystray) event loop
  - Clipboard thread: polls clipboard every 0.5s
  - Fetch worker thread: processes one fetch request at a time from a queue

Communication between threads via queue.Queue.
"""

import json
import os
import queue
import threading
import time
from collections import deque
from typing import Any, Callable, Dict, List, Optional, Tuple

from api_client import fetch_kline, fetch_stock_info, StockError
from cache_manager import CacheManager
from clipboard_monitor import ClipboardMonitor, StockRequest
from config import load_config, save_config, update_config
from data_builder import build_json, to_json_string
from indicators import calc_all_indicators


# --- Fetch result for panel logging ---
class FetchResult:
    """Result of a single stock fetch operation for display in the info panel."""

    __slots__ = ("timestamp", "code", "name", "status", "period", "count", "message")

    def __init__(
        self,
        code: str,
        name: str = "",
        status: str = "pending",
        period: str = "daily",
        count: int = 0,
        message: str = "",
    ) -> None:
        self.timestamp = time.strftime("%H:%M:%S")
        self.code = code
        self.name = name
        self.status = status  # 'success', 'error', 'cached', 'pending'
        self.period = period
        self.count = count
        self.message = message

    def to_dict(self) -> Dict[str, Any]:
        return {
            "time": self.timestamp,
            "code": self.code,
            "name": self.name,
            "status": self.status,
            "period": self.period,
            "count": self.count,
            "message": self.message,
        }


class StockClipper:
    """Core orchestrator for the Stock JSON Clipper application.

    Usage:
        clipper = StockClipper()
        clipper.start()      # starts clipboard monitor + fetch worker
        clipper.run_tray()   # blocks on pystray main loop
        clipper.stop()       # graceful shutdown
    """

    MAX_HISTORY = 5

    def __init__(self, config_path: Optional[str] = None) -> None:
        """Initialize the clipper.

        Args:
            config_path: Optional path to config.ini.
        """
        self._config_path = config_path
        self._config = load_config(config_path) if config_path else load_config()

        # Cache
        self._cache = CacheManager(ttl=self._config.get("cache_ttl", 300.0))

        # Queues
        self._fetch_queue: queue.Queue = queue.Queue(maxsize=100)
        self._result_queue: queue.Queue = queue.Queue(maxsize=100)

        # History
        self._history: deque = deque(maxlen=self.MAX_HISTORY)
        self._history_lock = threading.Lock()

        # Threads
        self._clipboard_monitor: Optional[ClipboardMonitor] = None
        self._fetch_worker_thread: Optional[threading.Thread] = None

        # Callbacks for UI
        self._on_notification: Optional[Callable[[str, str], None]] = None
        self._on_status_change: Optional[Callable[[str], None]] = None

        # State
        self._running = threading.Event()
        self._fetching = threading.Event()
        self._last_result: Optional[FetchResult] = None

    # --- Public API ---

    def start(self) -> None:
        """Start the background threads (clipboard monitor + fetch worker)."""
        if self._running.is_set():
            return

        self._running.set()

        # Start clipboard monitor
        self._clipboard_monitor = ClipboardMonitor(
            on_detected=self._on_stock_detected,
            poll_interval=self._config.get("poll_interval", 0.5),
        )
        self._clipboard_monitor.start()

        # Start fetch worker
        self._fetch_worker_thread = threading.Thread(
            target=self._fetch_worker_loop,
            daemon=True,
            name="fetch-worker",
        )
        self._fetch_worker_thread.start()

    def stop(self) -> None:
        """Gracefully stop all background threads."""
        self._running.clear()

        if self._clipboard_monitor:
            self._clipboard_monitor.stop()

        # Send sentinel to unblock worker
        try:
            self._fetch_queue.put_nowait(None)
        except queue.Full:
            pass

        if self._fetch_worker_thread:
            self._fetch_worker_thread.join(timeout=3.0)

    def run_tray(self) -> None:
        """Run the system tray (blocking). Imported here to avoid circular deps."""
        from tray_app import run_tray
        run_tray(self)

    # --- Callback registration ---

    def set_notification_callback(self, cb: Callable[[str, str], None]) -> None:
        """Set callback for tray notifications: cb(title, message)."""
        self._on_notification = cb

    def set_status_callback(self, cb: Callable[[str], None]) -> None:
        """Set callback for status changes: cb(status_text)."""
        self._on_status_change = cb

    # --- Core logic ---

    def _on_stock_detected(self, request: StockRequest) -> None:
        """Called by clipboard monitor when a stock code is detected.

        Args:
            request: Parsed StockRequest from clipboard.
        """
        # Push to fetch queue (non-blocking)
        try:
            self._fetch_queue.put_nowait(request)
        except queue.Full:
            pass  # Silently drop if queue is full

    def _fetch_worker_loop(self) -> None:
        """Main worker loop running in a background thread."""
        while self._running.is_set():
            try:
                request = self._fetch_queue.get(timeout=0.5)
            except queue.Empty:
                continue

            # Sentinel value to stop
            if request is None:
                break

            self._fetching.set()
            self._signal_status("fetching")

            try:
                self._process_request(request)
            except Exception as e:
                import traceback
                traceback.print_exc()
                result = FetchResult(
                    code=request.code,
                    status="error",
                    period=request.period,
                    message=f"内部错误: {e}",
                )
                self._add_history(result)
                self._notify("❌ 处理失败", f"{request.code}: {e}")

            self._fetching.clear()
            self._signal_status("monitoring")

    def _process_request(self, request: StockRequest) -> None:
        """Process a single stock fetch request.

        Args:
            request: StockRequest to process.
        """
        # 1. Check cache
        cache_key = self._cache.make_key(request.code, request.period)
        cached = self._cache.get(cache_key)
        if cached is not None:
            # Cached hit — write cached JSON to clipboard, #save mode writes fresh
            if not request.save_mode:
                self._write_clipboard(cached)
                result = FetchResult(
                    code=request.code,
                    name=json.loads(cached)["meta"]["name"],
                    status="cached",
                    period=request.period,
                    message="从缓存返回",
                )
                self._add_history(result)
                self._notify(
                    "✅ 缓存命中",
                    f"{request.code} 已从缓存复制到剪贴板",
                )
                return
            else:
                # #save mode: clear cache and re-fetch full data
                self._cache.remove(cache_key)

        # 2. Fetch data
        count = self._config.get("default_count", 250)
        try:
            kline_data = fetch_kline(
                request.code,
                period=request.period,
                count=count,
                timeout=self._config.get("request_timeout", 5),
            )
            stock_info = fetch_stock_info(
                request.code,
                timeout=self._config.get("request_timeout", 5),
            )
        except StockError as e:
            self._write_clipboard(f"Error: {e.message}")
            result = FetchResult(
                code=request.code,
                status="error",
                period=request.period,
                message=e.message,
            )
            self._add_history(result)
            self._notify("❌ 拉取失败", f"{request.code}: {e.message}")
            return

        # 3. Build JSON
        result_json = build_json(kline_data, stock_info, request.code, period=request.period, count=count)
        json_str = to_json_string(result_json)

        # 4. Save or clipboard
        if request.save_mode:
            # Save to file
            filepath = self._save_to_file(request.code, stock_info["name"], json_str)
            self._write_clipboard(filepath)
            result = FetchResult(
                code=request.code,
                name=stock_info["name"],
                status="success",
                period=request.period,
                count=len(kline_data),
                message=f"已保存: {os.path.basename(filepath)}",
            )
            self._notify("💾 已保存", f"{request.code} {stock_info['name']} → {os.path.basename(filepath)}")
        else:
            # Write to clipboard
            self._write_clipboard(json_str)
            # Cache the result
            self._cache.set(cache_key, json_str)
            result = FetchResult(
                code=request.code,
                name=stock_info["name"],
                status="success",
                period=request.period,
                count=len(kline_data),
                message=f"{len(kline_data)}条数据",
            )
            self._notify(
                "✅ 已完成",
                f"{request.code} {stock_info['name']} ({len(kline_data)}条) → 剪贴板",
            )

        self._add_history(result)
        self._last_result = result

    def _write_clipboard(self, text: str) -> None:
        """Write text to system clipboard (thread-safe wrapper)."""
        import pyperclip
        for attempt in range(3):
            try:
                pyperclip.copy(text)
                return
            except Exception:
                if attempt < 2:
                    time.sleep(0.1)
                else:
                    raise

    def _save_to_file(self, code: str, name: str, json_str: str) -> str:
        """Save JSON to a local file in the current directory.

        File naming: {code}_{name}_{date}.json

        Args:
            code: 6-digit stock code.
            name: Stock name.
            json_str: JSON string to save.

        Returns:
            Absolute path of the saved file.
        """
        date_str = time.strftime("%Y%m%d")
        # Sanitize filename
        safe_name = name.replace("/", "_").replace("\\", "_").replace(" ", "")
        filename = f"{code}_{safe_name}_{date_str}.json"
        filepath = os.path.join(os.getcwd(), filename)

        with open(filepath, "w", encoding="utf-8") as f:
            f.write(json_str)

        return os.path.abspath(filepath)

    def _add_history(self, result: FetchResult) -> None:
        """Add a fetch result to the history deque (thread-safe)."""
        with self._history_lock:
            self._history.appendleft(result)

    def _notify(self, title: str, message: str) -> None:
        """Send notification to tray (if callback registered)."""
        if self._on_notification:
            try:
                self._on_notification(title, message)
            except Exception:
                pass

    def _signal_status(self, status: str) -> None:
        """Signal status change to panel (if callback registered)."""
        if self._on_status_change:
            try:
                self._on_status_change(status)
            except Exception:
                pass

    # --- Getters for UI panel ---

    def get_history(self) -> List[Dict[str, Any]]:
        """Get recent fetch history (max 5 items).

        Returns:
            List of result dicts, newest first.
        """
        with self._history_lock:
            return [r.to_dict() for r in self._history]

    def get_config(self) -> Dict[str, Any]:
        """Get current configuration."""
        return dict(self._config)

    def set_config(self, key: str, value: Any) -> None:
        """Update a config value (persists to file)."""
        self._config[key] = value
        update_config(key, value, self._config_path)

    def clear_cache(self) -> None:
        """Clear the in-memory cache."""
        self._cache.clear()

    def get_status(self) -> str:
        """Get current status ('monitoring' or 'fetching')."""
        return "fetching" if self._fetching.is_set() else "monitoring"

    def get_last_result(self) -> Optional[FetchResult]:
        """Get the most recent fetch result."""
        return self._last_result

    def get_result_detail(self) -> Optional[Dict[str, Any]]:
        """Get detailed info from the last fetch result for panel display.

        Returns the raw cached JSON data (meta, indicators, summary) of the
        most recent fetch, suitable for rendering the result card in the UI.

        Returns:
            Dict with 'meta', 'indicators', 'summary' keys, or None if no data.
        """
        last = self._last_result
        if last is None:
            return None

        cache_key = self._cache.make_key(last.code, last.period)
        cached_json = self._cache.get(cache_key)
        if cached_json:
            try:
                data = json.loads(cached_json)
                return {
                    "meta": data.get("meta", {}),
                    "indicators": data.get("indicators", {}),
                    "summary": data.get("summary", {}),
                }
            except json.JSONDecodeError:
                pass

        return {
            "meta": {
                "code": last.code,
                "name": last.name,
                "period": last.period,
            },
            "indicators": {},
            "summary": {},
        }

    def fetch_manual(self, code: str, period: str = "daily") -> FetchResult:
        """Manually trigger a fetch (used by panel search box).

        Args:
            code: 6-digit stock code.
            period: 'daily', 'weekly', or 'monthly'.

        Returns:
            FetchResult for the operation.
        """
        request = StockRequest(code=code, period=period, save_mode=False, raw=code)
        try:
            self._fetch_queue.put_nowait(request)
        except queue.Full:
            return FetchResult(code=code, status="error", message="队列已满，请稍后重试")
        return FetchResult(code=code, status="pending", period=period, message="已加入队列")
