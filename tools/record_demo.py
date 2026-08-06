"""Rekam video demo fitur OnyxPad (gaya asciinema) untuk README.

Alur: jalankan app offscreen, simulasikan ketikan/multi-kursor/search/split/
ganti tema via QTest, ambil frame tiap aksi, lalu gabung dengan ffmpeg
menjadi demo.mp4 dan demo.gif.

Pemakaian:
    python tools/record_demo.py

Hasil di: docs/demo/demo.mp4, docs/demo/demo.gif
"""

import os
import subprocess
import sys
import tempfile
import time

# Redirect folder settings ke temp agar tidak mengganggu sesi asli
os.environ.setdefault("USERPROFILE", tempfile.mkdtemp(prefix="onyxpad_demo_"))
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PySide6.QtCore import Qt
from PySide6.QtGui import QTextCursor
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication

from src.app import OnyxPad

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FRAMES = os.path.join(ROOT, "docs", "demo", "frames")
DEMO = os.path.join(ROOT, "docs", "demo", "demo.py")
README = os.path.join(ROOT, "README.md")
MP4 = os.path.join(ROOT, "docs", "demo", "demo.mp4")
GIF = os.path.join(ROOT, "docs", "demo", "demo.gif")
SIZE = (1080, 640)
FPS = 12

frames = []


def pump(app, n=6, dt=0.02):
    for _ in range(n):
        app.processEvents()
        time.sleep(dt)


def snap():
    frames.append(win.grab())


def hold(n=2):
    frames.extend([frames[-1]] * n)


def key(ed, k, mods=Qt.KeyboardModifier.NoModifier):
    QTest.keyClick(ed, k, mods)
    pump(app)


def type_text(ed, text):
    """Ketik teks karakter demi karakter (pakai auto-pair editor)."""
    for ch in text:
        if ch == "\n":
            key(ed, Qt.Key.Key_Return)
        else:
            QTest.keyClicks(ed, ch, delay=8)
            pump(app)
        snap()
        hold(1)


def cursor_end(ed):
    c = ed.textCursor()
    c.movePosition(QTextCursor.MoveOperation.End)
    ed.setTextCursor(c)
    ed.ensureCursorVisible()
    pump(app)


def cursor_to_word(ed, word):
    c = ed.document().find(word)
    if not c.isNull():
        c.setPosition(c.selectionStart())
        ed.setTextCursor(c)
        ed.ensureCursorVisible()
        pump(app)


# ------------------------------------------------------------------ alur
def boot():
    cursor_end(ed)
    snap()
    hold(16)


def step_typing():
    type_text(ed, "\ndef handler(request):\n")
    snap()
    hold(8)
    type_text(ed, "    item = cache.get(request)\n")
    snap()
    hold(10)


def step_multicursor():
    cursor_to_word(ed, "print")
    snap()
    hold(4)
    # Ctrl+D tiga kali: kata di bawah kursor + 2 kemunculan berikutnya
    for _ in range(3):
        key(ed, Qt.Key.Key_D, Qt.KeyboardModifier.ControlModifier)
        snap()
        hold(3)
    type_text(ed, "log")
    snap()
    hold(10)
    key(ed, Qt.Key.Key_Escape)  # selesai mode multi-kursor


def step_search():
    win.search_bar.show_find()
    pump(app)
    win.search_bar.find_edit.setFocus()
    QTest.keyClicks(win.search_bar.find_edit, "def", delay=40)
    pump(app)
    snap()
    hold(14)
    key(ed, Qt.Key.Key_Escape)


def step_split():
    win.manager.split_right()
    win.open_file(README)
    pump(app)
    snap()
    hold(16)


def step_theme():
    win.apply_theme("One Dark")
    pump(app)
    snap()
    hold(12)


def write_frames():
    os.makedirs(FRAMES, exist_ok=True)
    for f in os.listdir(FRAMES):
        os.remove(os.path.join(FRAMES, f))
    for i, pm in enumerate(frames, 1):
        pm.save(os.path.join(FRAMES, f"f{i:04d}.png"), "PNG")
    print(f"{len(frames)} frame -> {FRAMES}")


def render():
    pat = os.path.join(FRAMES, "f%04d.png")
    subprocess.run(
        ["ffmpeg", "-y", "-framerate", str(FPS), "-i", pat,
         "-vf", "scale=1080:-2:flags=lanczos,format=yuv420p",
         "-c:v", "libx264", "-crf", "23", "-preset", "medium",
         "-movflags", "+faststart", MP4], check=True)
    subprocess.run(
        ["ffmpeg", "-y", "-framerate", str(FPS), "-i", pat,
         "-vf", "scale=720:-2:flags=lanczos,split[s0][s1];"
                "[s0]palettegen=stats_mode=diff[p];[s1][p]paletteuse=dither=bayer:bayer_scale=5",
         GIF], check=True)
    print(f"MP4: {MP4}\nGIF: {GIF}")


app = QApplication(sys.argv)
win = OnyxPad()
win.apply_theme("Dracula (Default)")
win.open_folder(ROOT)
win.open_file(DEMO)
win.resize(*SIZE)
win.show()
pump(app)
ed = win.manager.active_editor()

boot()
step_typing()
step_multicursor()
step_search()
step_split()
step_theme()

write_frames()
render()
print("Selesai. Video demo di docs/demo/")
