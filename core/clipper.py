"""
core.clipper — Core orchestrator for Stock JSON Clipper V3.0.

Data fetching is handled by stock-api (browser bundle) in the panel.
Python side manages: config, cache, module registry, file I/O, tray.
"""

import json
import os
import time
from typing import Any, Callable, Dict, List, Optional

from core.cache import CacheManager
from core.config import load_config, update_config
from core.registry import ModuleRegistry


class StockClipper:
    """Minimal orchestrator — data comes from JS/stock-api."""

    def __init__(self, config_path: Optional[str] = None) -> None:
        self._config_path = config_path
        self._config = load_config(config_path) if config_path else load_config()
        self.registry = ModuleRegistry()
        self._cache = CacheManager(ttl=self._config.get("cache_ttl", 300.0))

    def start(self) -> None:
        self.registry.start_all()

    def stop(self) -> None:
        self.registry.stop_all()

    def run_tray(self, auto_show_panel: bool = True) -> None:
        from ui.tray import run_tray
        run_tray(self, auto_show_panel=auto_show_panel)

    # Config
    def get_config(self) -> Dict[str, Any]:
        return dict(self._config)

    def set_config(self, key: str, value: Any) -> None:
        self._config[key] = value
        if self._config_path:
            update_config(key, value, self._config_path)
        else:
            update_config(key, value)

    # Cache
    def clear_cache(self) -> None:
        self._cache.clear()

    def cache_get(self, key: str) -> Optional[str]:
        return self._cache.get(key)

    def cache_set(self, key: str, value: str) -> None:
        self._cache.set(key, value)
