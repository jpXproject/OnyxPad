"""OnyxPad demo — contoh file untuk showcase syntax highlighting.

Fitur yang ditampilkan: docstring, decorator, dataclass, type hints,
string f, komentar, dan struktur fungsi/kelas.
"""

import json
import time
from dataclasses import dataclass, field
from pathlib import Path

DEFAULT_TTL = 300  # detik


@dataclass
class Cache:
    """Cache sederhana dengan masa berlaku (TTL)."""

    ttl: int = DEFAULT_TTL
    store: dict = field(default_factory=dict)

    def get(self, key: str):
        item = self.store.get(key)
        if item and item["expire"] > time.time():
            return item["value"]
        return None

    def set(self, key: str, value, ttl: int | None = None) -> dict:
        expire = time.time() + (ttl or self.ttl)
        self.store[key] = {"value": value, "expire": expire}
        return self.store[key]


def load_config(path: Path) -> dict:
    """Muat konfigurasi dari file JSON."""
    with path.open("r", encoding="utf-8") as fh:
        data = json.load(fh)
    cache = Cache()
    for key, item in data.items():
        cache.set(key, item)          # simpan ke cache
        data[key] = cache.get(key)    # ambil dari cache
    return data


class Router:
    """Router HTTP sederhana dengan handler berbasis dict."""

    def route(self, method: str, url: str) -> None:
        # Contoh: GET /api/items -> items.index()
        handlers = {"GET": self._get, "POST": self._post}
        handler = handlers.get(method.upper(), self._not_found)
        handler(url)

    def _get(self, url: str) -> None:
        print(f"GET {url}")

    def _post(self, url: str) -> None:
        print(f"POST {url}")

    def _not_found(self, url: str) -> None:
        print(f"404 {url}")
