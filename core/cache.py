"""
cache_manager.py — Thread-safe in-memory TTL cache for Stock JSON Clipper.

Key format: "{code}_{period}" (e.g. "000001_daily")
Default TTL: 300 seconds (5 minutes).
"""

import threading
import time
from typing import Any, Dict, Optional


class CacheEntry:
    """A single cache entry with value and expiration timestamp."""

    __slots__ = ("value", "expires_at")

    def __init__(self, value: Any, ttl: float) -> None:
        self.value = value
        self.expires_at = time.monotonic() + ttl

    @property
    def expired(self) -> bool:
        return time.monotonic() > self.expires_at


class CacheManager:
    """Thread-safe in-memory cache with per-entry TTL."""

    def __init__(self, ttl: float = 300.0) -> None:
        """Initialize cache manager.

        Args:
            ttl: Default time-to-live in seconds (default 300 = 5 min).
        """
        self._ttl = ttl
        self._store: Dict[str, CacheEntry] = {}
        self._lock = threading.Lock()

    def get(self, key: str) -> Optional[Any]:
        """Retrieve a cached value by key. Returns None if missing or expired.

        Args:
            key: Cache key (e.g. "000001_daily").

        Returns:
            Cached value or None.
        """
        with self._lock:
            entry = self._store.get(key)
            if entry is None:
                return None
            if entry.expired:
                del self._store[key]
                return None
            return entry.value

    def set(self, key: str, value: Any, ttl: Optional[float] = None) -> None:
        """Store a value in the cache.

        Args:
            key: Cache key.
            value: Value to cache.
            ttl: Time-to-live in seconds (uses default if None).
        """
        with self._lock:
            self._store[key] = CacheEntry(value, ttl if ttl is not None else self._ttl)

    def clear(self) -> None:
        """Remove all entries from the cache."""
        with self._lock:
            self._store.clear()

    def remove(self, key: str) -> None:
        """Remove a specific key from the cache."""
        with self._lock:
            self._store.pop(key, None)

    @property
    def size(self) -> int:
        """Return current number of entries (including expired, before cleanup)."""
        with self._lock:
            return len(self._store)

    def cleanup(self) -> int:
        """Remove all expired entries. Returns count of removed entries."""
        removed = 0
        with self._lock:
            expired_keys = [
                k for k, v in self._store.items() if v.expired
            ]
            for k in expired_keys:
                del self._store[k]
                removed += 1
        return removed

    def make_key(self, code: str, period: str, count: int = 0) -> str:
        """Build a standard cache key from stock code, period, and count.

        Cache key includes count to avoid returning wrong-sized cached data
        when the user requests a different number of bars.

        Args:
            code: 6-digit stock code.
            period: 'daily', 'weekly', or 'monthly'.
            count: Number of K-line bars requested (0 = count not used in key).

        Returns:
            Cache key string like "000001_daily_250".
        """
        if count > 0:
            return f"{code}_{period}_{count}"
        return f"{code}_{period}"
