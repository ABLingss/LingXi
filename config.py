"""
config.py — Configuration management for Stock JSON Clipper V1.0
Reads/writes config.ini using configparser.
Creates default config.ini if missing.
"""

import os
import configparser
from typing import Any, Dict

# --- Default configuration ---
DEFAULTS: Dict[str, Any] = {
    "output_format": "json",       # json | markdown | csv (markdown/csv reserved)
    "default_count": 250,          # default K-line bars to fetch (5 ~ full)
    "poll_interval": 0.5,          # clipboard polling interval in seconds
    "cache_ttl": 300,              # cache time-to-live in seconds (5 min)
    "request_timeout": 5,          # API request timeout in seconds
}

CONFIG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.ini")


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
