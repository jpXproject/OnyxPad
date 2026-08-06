"""Identitas aplikasi OnyxPad."""

import re

APP_NAME = "OnyxPad"
APP_TAGLINE = "Editor Split Panes Pro"
APP_VERSION = "1.0.0"
# Turunan nama untuk folder settings pengguna (~/.onyxpad)
APP_ID = APP_NAME.lower()

# --- identitas penulis & repo (menu Bantuan + cek pembaruan) ---
APP_AUTHOR = "jpXCode"                        # nama penulis (display name)
APP_AUTHOR_URL = "https://github.com/jpXproject"
APP_REPO_URL = "https://github.com/jpXproject/OnyxPad"
APP_RELEASES_API = ("https://api.github.com/repos/"
                    "jpXproject/OnyxPad/releases/latest")


def parse_version(text):
    """Ambil (major, minor, patch) dari string versi; None bila tak cocok.

    Contoh: "v1.2.3-beta" -> (1, 2, 3)  ·  "1.4" -> (1, 4, 0)
    """
    m = re.search(r"(\d+)(?:\.(\d+))?(?:\.(\d+))?", text or "")
    if not m:
        return None
    return tuple(int(g or 0) for g in m.groups())


def is_newer_version(current, latest_tag):
    """True bila tag rilis terbaru lebih baru dari versi yang terpasang."""
    c, l = parse_version(current), parse_version(latest_tag)
    if c is None or l is None:
        return False
    return l > c
