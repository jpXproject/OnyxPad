"""Rekam footage promo TikTok 9:16 (portrait) OnyxPad — tiap beat jadi clip terpisah.

Menggabung pendekatan tools/record_demo.py dengan output yang cocok untuk
video promo vertikal: window app portrait 1080x1520, satu clip mp4 per beat
fitur (agar komposisi HyperFrames bisa memotong/memainkan tiap beat dengan
durasi presisi), plus gabungan penuh dan frames cadangan.

Hasil di: <root>/videos/onyxpad-promo/capture/assets/{frames,clips,*.mp4}
"""

import os
import subprocess
import sys
import tempfile
import time

# Redirect folder settings ke temp agar tidak mengganggu sesi asli
os.environ.setdefault("USERPROFILE", tempfile.mkdtemp(prefix="onyxpad_tiktok_"))
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

# Qt offscreen TIDAK menemukan font sistem tanpa petunjuk direktori —
# tanpa ini semua teks dirender sebagai kotak (tofu). Wajib SEBELUM QApplication.
if os.name == "nt":
    os.environ.setdefault("QT_QPA_FONTDIR", "C:/Windows/Fonts")
else:
    os.environ.setdefault("QT_QPA_FONTDIR",
                          "/usr/share/fonts:/usr/local/share/fonts")

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PySide6.QtCore import Qt
from PySide6.QtGui import QTextCursor
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication

from src.app import OnyxPad

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROJ = os.path.join(os.path.dirname(ROOT), "videos", "onyxpad-promo")
ASSETS = os.path.join(PROJ, "capture", "assets")
FRAMES = os.path.join(ASSETS, "frames")
CLIPS = os.path.join(ASSETS, "clips")
DEMO = os.path.join(ROOT, "docs", "demo", "demo.py")
README = os.path.join(ROOT, "README.md")

SIZE = (1080, 1520)   # portrait 9:16-ish, mengisi kanvas 1080x1920
FPS = 24

frames = []
beats = []            # [(name, start_idx, end_idx)]


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


def begin(name):
    beats.append([name, len(frames), None])


def end():
    beats[-1][2] = len(frames)


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
def beat_boot():
    begin("01-boot")
    cursor_end(ed)
    snap()
    hold(20)
    end()


def beat_typing():
    begin("02-typing")
    type_text(ed, "\ndef handler(request):\n")
    snap()
    hold(6)
    type_text(ed, "item = cache.get(request)\n")
    snap()
    hold(10)
    end()


def beat_multicursor():
    begin("03-multicursor")
    cursor_to_word(ed, "print")
    snap()
    hold(6)
    # Ctrl+D tiga kali: kata di bawah kursor + 2 kemunculan berikutnya
    for _ in range(3):
        key(ed, Qt.Key.Key_D, Qt.KeyboardModifier.ControlModifier)
        snap()
        hold(4)
    type_text(ed, "log")
    snap()
    hold(10)
    key(ed, Qt.Key.Key_Escape)  # selesai mode multi-kursor
    end()


def beat_find():
    begin("04-find")
    win.search_bar.show_find()
    pump(app)
    win.search_bar.find_edit.setFocus()
    QTest.keyClicks(win.search_bar.find_edit, "def", delay=40)
    pump(app)
    snap()
    hold(18)
    key(ed, Qt.Key.Key_Escape)
    end()


def beat_split():
    begin("05-split")
    win.manager.split_below()   # split horizontal: editor atas, pane bawah
    win.open_file(README)
    pump(app)
    snap()
    hold(20)
    end()


def beat_theme():
    begin("06-theme")
    win.apply_theme("One Dark")
    pump(app)
    snap()
    hold(6)
    win.apply_theme("Matrix Green")
    pump(app)
    snap()
    hold(6)
    win.apply_theme("Dracula (Default)")  # kembali ke tema standar (ciri khas)
    pump(app)
    snap()
    hold(12)
    end()


def write_frames():
    os.makedirs(FRAMES, exist_ok=True)
    for f in os.listdir(FRAMES):
        os.remove(os.path.join(FRAMES, f))
    # JPG agar hemat disk; frames ini cadangan (clip mp4 sumber utama)
    for i, pm in enumerate(frames, 1):
        pm.save(os.path.join(FRAMES, f"f{i:04d}.jpg"), "JPEG", quality=92)
    print(f"{len(frames)} frame -> {FRAMES}")


def _render_range(name, start, end, out):
    """Render slice frames[start:end] menjadi mp4 clip."""
    if end <= start:
        return
    pat = os.path.join(FRAMES, "f%04d.jpg")
    subprocess.run(
        ["ffmpeg", "-y", "-framerate", str(FPS), "-start_number", str(start + 1),
         "-i", pat, "-frames:v", str(end - start),
         "-vf", "scale=1080:-2:flags=lanczos,format=yuv420p",
         "-c:v", "libx264", "-crf", "21", "-preset", "medium",
         "-movflags", "+faststart", out], check=True)


def render():
    os.makedirs(CLIPS, exist_ok=True)
    for name, start, end in beats:
        out = os.path.join(CLIPS, f"{name}.mp4")
        _render_range(name, start, end, out)
        print(f"clip {name}: {end - start} frame -> {out}")
    # gabungan penuh
    all_out = os.path.join(ASSETS, "app-tiktok.mp4")
    pat = os.path.join(FRAMES, "f%04d.jpg")
    subprocess.run(
        ["ffmpeg", "-y", "-framerate", str(FPS), "-i", pat,
         "-vf", "scale=1080:-2:flags=lanczos,format=yuv420p",
         "-c:v", "libx264", "-crf", "21", "-preset", "medium",
         "-movflags", "+faststart", all_out], check=True)
    print(f"gabungan -> {all_out}")


app = QApplication(sys.argv)
win = OnyxPad()
win.apply_theme("Dracula (Default)")
win.open_folder(ROOT)
win.open_file(DEMO)
win.resize(*SIZE)
win.show()
pump(app)
ed = win.manager.active_editor()

beat_boot()
beat_typing()
beat_multicursor()
beat_find()
beat_split()
beat_theme()

write_frames()
render()
print("Selesai. Footage TikTok ada di capture/assets/")
