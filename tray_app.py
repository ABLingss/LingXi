"""
tray_app.py — System tray icon and menu for Stock JSON Clipper V1.0.

Uses pystray + PIL to create a tray icon with right-click menu:
  - Show Panel
  - Clear Cache
  - (current clipboard preview)
  - ---
  - Exit

The tray icon is generated programmatically (green/red candlestick).
"""

import io
import threading
from typing import TYPE_CHECKING, Optional

from PIL import Image, ImageDraw
import pystray

if TYPE_CHECKING:
    from stock_clipper import StockClipper


# --- Icon generation ---
def _create_tray_icon(size: int = 64) -> Image.Image:
    """Generate a simple stock K-line style tray icon using PIL.

    Draws a green candlestick on a transparent background at 64x64.

    Args:
        size: Icon size in pixels (square).

    Returns:
        PIL Image in RGBA mode.
    """
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # Background rounded rect (dark)
    margin = 4
    draw.rounded_rectangle(
        [margin, margin, size - margin, size - margin],
        radius=10,
        fill=(30, 30, 35, 255),
    )

    # Up-trend candle (green bullish)
    body_top = 18
    body_bottom = 34
    shadow_top = 12
    shadow_bottom = 48
    body_left = 18
    body_right = 46
    center_x = (body_left + body_right) // 2

    # Wick (upper shadow)
    draw.line(
        [(center_x, shadow_top), (center_x, body_top)],
        fill=(0, 200, 100, 255),
        width=3,
    )
    # Wick (lower shadow)
    draw.line(
        [(center_x, body_bottom), (center_x, shadow_bottom)],
        fill=(0, 200, 100, 255),
        width=3,
    )
    # Body (green filled rectangle)
    draw.rectangle(
        [body_left, body_top, body_right, body_bottom],
        fill=(0, 220, 120, 255),
        outline=(0, 180, 90, 255),
    )

    return img


# --- Tray setup ---
def _create_menu(clipper: "StockClipper", icon: pystray.Icon) -> pystray.Menu:
    """Build the right-click menu for the tray icon.

    Args:
        clipper: StockClipper instance.
        icon: pystray Icon instance.

    Returns:
        pystray.Menu object.
    """
    def on_show_panel():
        """Show the PyWebView info panel."""
        try:
            from web_panel import show_panel
            show_panel(clipper)
        except Exception as e:
            icon.notify(f"无法打开面板: {e}", title="Stock JSON Clipper")

    def on_clear_cache():
        clipper.clear_cache()
        icon.notify("缓存已清空", title="Stock JSON Clipper")

    def on_exit():
        icon.stop()
        clipper.stop()

    return pystray.Menu(
        pystray.MenuItem("📊 显示面板", on_show_panel, default=True),
        pystray.MenuItem("🔄 清空缓存", on_clear_cache),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem("❌ 退出", on_exit),
    )


def run_tray(clipper: "StockClipper") -> None:
    """Initialize and run the system tray icon (blocking).

    This should be called from the main thread as pystray.run()
    runs its own event loop.

    Args:
        clipper: StockClipper instance with start() already called.
    """
    icon_image = _create_tray_icon()

    # Create icon without menu first
    icon = pystray.Icon(
        name="StockJSONClipper",
        icon=icon_image,
        title="Stock JSON Clipper V1.0",
    )

    # Build menu with reference to icon (for notifications)
    icon.menu = _create_menu(clipper, icon)

    # Register notification callback
    def notify_cb(title: str, message: str) -> None:
        try:
            icon.notify(message, title=title)
        except Exception:
            pass

    clipper.set_notification_callback(notify_cb)

    # Run the tray (blocking)
    icon.run()
