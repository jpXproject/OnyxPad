"""Hasilkan screenshot statis OnyxPad untuk README.

Pemakaian:
    python tools/take_screenshots.py
    (opsional) QT_QPA_PLATFORM=offscreen python tools/take_screenshots.py

Hasil di: docs/screenshots/*.png
"""

import os
import re
import sys
import tempfile
import time

# Redirect folder settings ke temp agar skrip tidak menimpa sesi asli
os.environ.setdefault("USERPROFILE", tempfile.mkdtemp(prefix="onyxpad_shot_"))

# Qt offscreen TIDAK menemukan font sistem tanpa petunjuk direktori —
# tanpa ini semua teks dirender sebagai kotak (tofu). Wajib di-set
# SEBELUM QApplication dibuat.
if os.name == "nt":
    os.environ.setdefault("QT_QPA_FONTDIR", "C:/Windows/Fonts")
else:
    os.environ.setdefault("QT_QPA_FONTDIR",
                          "/usr/share/fonts:/usr/local/share/fonts")

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PySide6.QtWidgets import QApplication

from src.app import OnyxPad
from src.themes import THEME_ORDER

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "docs", "screenshots")
DEMO = os.path.join(ROOT, "docs", "demo", "demo.py")
README = os.path.join(ROOT, "README.md")

SIZE = (1280, 800)


def pump(app, n=8, dt=0.025):
    for _ in range(n):
        app.processEvents()
        time.sleep(dt)


def new_window(app, theme):
    win = OnyxPad()
    win.apply_theme(theme)
    win.open_folder(ROOT)
    win.resize(*SIZE)
    win.show()
    pump(app)
    return win


def save(win, name):
    os.makedirs(OUT, exist_ok=True)
    path = os.path.join(OUT, name)
    ok = win.grab().save(path, "PNG")
    print(f"{'OK ' if ok else 'GAGAL'} {path}")
    return path


def hero_dark(app):
    """Dracula + editor demo.py + search bar aktif."""
    win = new_window(app, "Dracula (Default)")
    win.open_file(DEMO)
    win.search_bar.show_find()
    win.search_bar.find_edit.setText("def")
    pump(app)
    save(win, "hero-dark.png")
    win.close()


def split_panes(app):
    """One Dark + split kanan: demo.py dan README dibuka bersamaan."""
    win = new_window(app, "One Dark")
    win.open_file(DEMO)
    win.manager.split_right()
    win.open_file(README)
    pump(app)
    save(win, "split-panes.png")
    win.close()


def theme_gallery(app):
    """Satu screenshot per tema gelap (Light tidak disertakan di galeri)."""
    for name in THEME_ORDER:
        if name == "Light":
            continue
        win = new_window(app, name)
        win.open_file(DEMO)
        pump(app)
        slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
        save(win, f"theme-{slug}.png")
        win.close()


def main():
    app = QApplication(sys.argv)
    hero_dark(app)
    split_panes(app)
    theme_gallery(app)
    print("Selesai. Screenshot ada di docs/screenshots/")


if __name__ == "__main__":
    main()
