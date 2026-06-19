r"""
clipboard_monitor.py — Clipboard polling and stock code parsing for Stock JSON Clipper.

Polls the system clipboard every 0.5 seconds, matches A-share stock codes
against the defined pattern, and fires a callback when a valid code is found.
Includes deduplication: same code won't re-trigger within 2 seconds.

Pattern: ^([#]?)([WM]:)?(\\d{6})$
  - #  → save-to-file mode
  - W: → weekly K-line
  - M: → monthly K-line
  - (default) → daily K-line
"""

import re
import threading
import time
from dataclasses import dataclass
from typing import Callable, Optional

import pyperclip

# --- Pattern ---
# Matches: 000001, #000001, W:000001, M:000001, #W:000001, #M:000001
STOCK_PATTERN = re.compile(r"^([#]?)([WM]:)?(\d{6})$")

# Minimum interval between re-triggering the same code (seconds)
DEDUP_INTERVAL = 2.0


@dataclass
class StockRequest:
    """Parsed stock code request from clipboard.

    Attributes:
        code: 6-digit stock code, e.g. '000001'.
        period: 'daily', 'weekly', or 'monthly'.
        save_mode: If True, save to local JSON file instead of clipboard output.
        raw: Original clipboard text.
    """

    code: str
    period: str
    save_mode: bool
    raw: str


def parse_clipboard(text: str) -> Optional[StockRequest]:
    """Parse clipboard text and extract stock request if valid.

    Args:
        text: Raw clipboard text (stripped of whitespace).

    Returns:
        StockRequest if valid stock code pattern matched, else None.
    """
    text = text.strip()
    if not text:
        return None

    m = STOCK_PATTERN.match(text)
    if not m:
        return None

    save_flag = m.group(1)  # '#' or ''
    period_flag = m.group(2)  # 'W:', 'M:', or None
    code = m.group(3)

    # Determine period
    if period_flag:
        if period_flag.startswith("W"):
            period = "weekly"
        elif period_flag.startswith("M"):
            period = "monthly"
        else:
            period = "daily"
    else:
        period = "daily"

    return StockRequest(
        code=code,
        period=period,
        save_mode=bool(save_flag),
        raw=text,
    )


class ClipboardMonitor:
    """Background clipboard monitor that polls for stock codes.

    Runs in a background thread. When a valid stock code is detected,
    calls the provided callback with a StockRequest.

    Usage:
        monitor = ClipboardMonitor(on_detected=my_handler)
        monitor.start()
        ...
        monitor.stop()
    """

    def __init__(
        self,
        on_detected: Callable[[StockRequest], None],
        poll_interval: float = 0.5,
    ) -> None:
        """Initialize clipboard monitor.

        Args:
            on_detected: Callback invoked when a stock code is detected.
            poll_interval: Polling interval in seconds (default 0.5).
        """
        self._on_detected = on_detected
        self._poll_interval = poll_interval
        self._thread: Optional[threading.Thread] = None
        self._running = threading.Event()
        self._last_text: str = ""
        self._last_trigger_time: float = 0.0
        self._last_code: str = ""

    def start(self) -> None:
        """Start the clipboard polling thread."""
        if self._thread is not None and self._thread.is_alive():
            return
        self._running.set()
        self._thread = threading.Thread(target=self._poll_loop, daemon=True, name="clipboard-monitor")
        self._thread.start()

    def stop(self) -> None:
        """Stop the clipboard polling thread and wait for it to exit."""
        self._running.clear()
        if self._thread is not None:
            self._thread.join(timeout=2.0)
            self._thread = None

    @property
    def is_running(self) -> bool:
        return self._running.is_set()

    def _poll_loop(self) -> None:
        """Main polling loop. Runs in background thread."""
        while self._running.is_set():
            try:
                text = pyperclip.paste()
                if text and text != self._last_text:
                    self._last_text = text
                    self._handle_text(text)
            except Exception:
                # pyperclip may fail on headless systems; silently ignore
                pass

            time.sleep(self._poll_interval)

    def _handle_text(self, text: str) -> None:
        """Process detected clipboard text.

        Args:
            text: Raw clipboard text.
        """
        request = parse_clipboard(text)
        if request is None:
            return  # Not a stock code — silently ignore

        # Dedup: same code within DEDUP_INTERVAL seconds
        now = time.monotonic()
        if request.code == self._last_code and (now - self._last_trigger_time) < DEDUP_INTERVAL:
            return

        self._last_code = request.code
        self._last_trigger_time = now

        try:
            self._on_detected(request)
        except Exception:
            # Callback errors should not crash the monitor thread
            pass
