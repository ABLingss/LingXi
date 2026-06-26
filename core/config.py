"""
core.config — Configuration management for Stock JSON Clipper V2.1.
Reads/writes config.ini using configparser.
Creates default config.ini next to the executable (or project root in dev).
"""

import os
import sys
import configparser
from typing import Any, Dict

# --- Default configuration ---
DEFAULTS: Dict[str, Any] = {
    "output_format": "json",
    "default_count": 250,
    "poll_interval": 0.5,
    "cache_ttl": 300,
    "request_timeout": 5,
    "save_directory": "",
}


def _get_config_dir() -> str:
    """Get the directory where config.ini should live.

    PyInstaller (frozen): next to the .exe
    Dev mode: project root (parent of core/ directory)
    """
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    else:
        # core/config.py → core/ → project root
        return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


CONFIG_PATH = os.path.join(_get_config_dir(), "config.ini")


def load_config(config_path: str = CONFIG_PATH) -> Dict[str, Any]:
    """Load configuration from INI file, creating it with defaults if missing.

    Args:
        config_path: Path to config.ini file.

    Returns:
        Dict with merged config values (defaults overridden by file values).
    """
    cfg = dict(DEFAULTS)
    parser = configparser.ConfigParser()

    if os.path.exists(config_path):
        parser.read(config_path, encoding="utf-8")
        if parser.has_section("settings"):
            for key in cfg:
                if parser.has_option("settings", key):
                    raw = parser.get("settings", key)
                    # Type-cast based on default type
                    if isinstance(cfg[key], int):
                        cfg[key] = int(raw)
                    elif isinstance(cfg[key], float):
                        cfg[key] = float(raw)
                    else:
                        cfg[key] = raw
    else:
        # Create default config.ini
        save_config(cfg, config_path)

    return cfg


def save_config(cfg: Dict[str, Any], config_path: str = CONFIG_PATH) -> None:
    """Save configuration to INI file.

    Args:
        cfg: Config dict to save.
        config_path: Path to config.ini file.
    """
    # Ensure directory exists (esp. for frozen bundles)
    cfg_dir = os.path.dirname(config_path)
    if cfg_dir:
        os.makedirs(cfg_dir, exist_ok=True)

    parser = configparser.ConfigParser()
    parser.add_section("settings")
    for key, value in cfg.items():
        parser.set("settings", key, str(value))

    with open(config_path, "w", encoding="utf-8") as f:
        parser.write(f)


def update_config(key: str, value: Any, config_path: str = CONFIG_PATH) -> None:
    """Update a single configuration key and persist to file.

    Args:
        key: Config key name.
        value: New value.
        config_path: Path to config.ini file.
    """
    cfg = load_config(config_path)
    cfg[key] = value
    save_config(cfg, config_path)
