"""Asciinema v2 Recorder dan Player untuk OnyxPad.

Modul ini menyediakan:
1. AsciinemaRecorder: Merekam output terminal/editor ke dalam format asciinema v2 (.cast).
2. AsciinemaPlayerDialog: UI dialog untuk memutar ulang file rekaman .cast di dalam OnyxPad.
"""

import json
import queue
import time
from pathlib import Path

from PySide6.QtCore import Qt, QTimer, QThread, QMutex, QMutexLocker
from PySide6.QtGui import QFont, QIcon, QKeySequence, QTextCursor
from PySide6.QtWidgets import (QDialog, QFileDialog, QHBoxLayout, QLabel,
                                QMessageBox, QPushButton, QRadioButton, QSlider,
                                QSpinBox, QStyle, QPlainTextEdit, QVBoxLayout, QWidget)


class RecordingScopeDialog(QDialog):
    """Dialog modern untuk memilih skop perekaman Asciinema (Notepad, Terminal, atau Full Workspace)."""

    def __init__(self, theme=None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Pilih Area Perekaman Asciinema (.cast)")
        self.setFixedWidth(440)
        self.theme = theme or {}
        self.selected_scope = "notepad"

        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        lbl = QLabel("<b>Pilih area aktivitas yang ingin Anda rekam:</b>", self)
        layout.addWidget(lbl)

        self.rb_notepad = QRadioButton("📝  <b>Notepad / Editor Teks Aktif</b><br>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;<small style='color:#a6adc8;'>Merekam pengetikan & koding pada dokumen editor aktif</small>", self)
        self.rb_terminal = QRadioButton("💻  <b>Terminal Interaktif</b><br>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;<small style='color:#a6adc8;'>Merekam sesi perintah & output di terminal</small>", self)
        self.rb_workspace = QRadioButton("⚡  <b>Seluruh Area Kerja (Full Workspace)</b><br>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;<small style='color:#a6adc8;'>Merekam pengetikan Notepad + perintah Terminal sekaligus!</small>", self)

        self.rb_notepad.setChecked(True)

        layout.addWidget(self.rb_notepad)
        layout.addWidget(self.rb_terminal)
        layout.addWidget(self.rb_workspace)

        btn_box = QHBoxLayout()
        btn_ok = QPushButton("⏺ Mulai Merekam", self)
        btn_ok.setStyleSheet("background-color: #f38ba8; color: #11111b; font-weight: bold; padding: 6px 16px;")
        btn_ok.clicked.connect(self.accept)

        btn_cancel = QPushButton("Batal", self)
        btn_cancel.clicked.connect(self.reject)

        btn_box.addStretch()
        btn_box.addWidget(btn_cancel)
        btn_box.addWidget(btn_ok)
        layout.addLayout(btn_box)

    def accept(self):
        if self.rb_notepad.isChecked():
            self.selected_scope = "notepad"
        elif self.rb_terminal.isChecked():
            self.selected_scope = "terminal"
        else:
            self.selected_scope = "workspace"
        super().accept()


class AsciinemaRecorder:
    """Perekam sesi berformat asciinema v2 JSON Lines spec."""

    def __init__(self, title="OnyxPad Recording", width=80, height=24):
        self.title = title
        self.width = width
        self.height = height
        self.is_recording = False
        self.start_time = None
        self.header = {}
        self._frames = []
        self._mutex = QMutex()

    @property
    def frames(self):
        with QMutexLocker(self._mutex):
            return list(self._frames)

    @frames.setter
    def frames(self, value):
        with QMutexLocker(self._mutex):
            self._frames = list(value)

    def _append_frame_from_thread(self, elapsed: float, event_type: str, text: str):
        with QMutexLocker(self._mutex):
            self._frames.append([elapsed, event_type, text])

    def start(self, width=None, height=None, title=None):
        if width:
            self.width = width
        if height:
            self.height = height
        if title:
            self.title = title

        self.start_time = time.time()
        self.header = {
            "version": 2,
            "width": self.width,
            "height": self.height,
            "timestamp": int(self.start_time),
            "title": self.title,
            "env": {
                "SHELL": "powershell" if time.tzname else "bash",
                "TERM": "xterm-256color"
            }
        }
        with QMutexLocker(self._mutex):
            # Rekam frame awal (0.0s) agar file .cast selalu memuat snapshot awal
            self._frames = [[0.0, "o", ""]]
        self.is_recording = True

    def record_output(self, text: str):
        """Merekam event output ('o') secara presisi dengan timestamp relatif (detik)."""
        if not self.is_recording or self.start_time is None or not text:
            return
        elapsed = round(time.time() - self.start_time, 6)
        with QMutexLocker(self._mutex):
            self._frames.append([elapsed, "o", text])

    def record_input(self, text: str):
        """Merekam event input ('i') secara presisi dengan timestamp relatif (detik)."""
        if not self.is_recording or self.start_time is None or not text:
            return
        elapsed = round(time.time() - self.start_time, 6)
        with QMutexLocker(self._mutex):
            self._frames.append([elapsed, "i", text])

    def stop(self):
        """Menghentikan perekaman dan mengembalikan data asciinema."""
        self.is_recording = False
        with QMutexLocker(self._mutex):
            frames_copy = list(self._frames)
        return {
            "header": self.header,
            "frames": frames_copy
        }

    def save_to_file(self, filepath: str) -> bool:
        """Menyimpan hasil perekaman ke file format .cast asciinema v2."""
        try:
            path = Path(filepath)
            with open(path, "w", encoding="utf-8") as f:
                f.write(json.dumps(self.header) + "\n")
                for frame in self.frames:
                    f.write(json.dumps(frame) + "\n")
            return True
        except Exception:
            return False

    @staticmethod
    def load_from_file(filepath: str):
        """Membaca file format .cast asciinema v2."""
        header = {}
        frames = []
        path = Path(filepath)
        if not path.exists():
            return None, None
        try:
            with open(path, "r", encoding="utf-8-sig", errors="replace") as f:
                lines = [l.strip() for l in f.readlines() if l.strip()]
                if not lines:
                    return None, None
                header = json.loads(lines[0])
                for line in lines[1:]:
                    try:
                        frame = json.loads(line)
                        if isinstance(frame, list) and len(frame) >= 3:
                            frames.append(frame)
                    except Exception:
                        continue
            return header, frames
        except Exception:
            return None, None


class AsciinemaPlayerDialog(QDialog):
    """Dialog player interaktif untuk memutar ulang file .cast asciinema."""

    def __init__(self, filepath=None, header=None, frames=None, theme=None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("OnyxPad — Asciinema Player (.cast)")
        self.resize(750, 480)

        self.theme = theme or {}
        self.header = header or {}
        self.frames = frames or []

        if filepath and not self.frames:
            h, f = AsciinemaRecorder.load_from_file(filepath)
            if h is not None and f is not None:
                self.header = h
                self.frames = f

        self._current_frame_idx = 0
        self._is_playing = False
        self._speed = 1.0

        self._timer = QTimer(self)
        self._timer.timeout.connect(self._on_timer_tick)

        self._build_ui()
        self._apply_theme()
        if self.frames:
            self._init_player()
            # Auto-start playback on launch for instant enjoyment
            QTimer.singleShot(200, self.start_playback)
        else:
            self.display.setPlainText("[Rekaman ini tidak memuat aktivitas terminal / 0 frame]")

    def _build_ui(self):
        layout = QVBoxLayout(self)

        # Title Info
        title_text = self.header.get("title", "Asciinema Recording")
        w = self.header.get("width", 80)
        h = self.header.get("height", 24)
        self.lbl_title = QLabel(f"🎬 <b>{title_text}</b> ({w}x{h})")
        layout.addWidget(self.lbl_title)

        # Screen Display
        self.display = QPlainTextEdit(self)
        self.display.setReadOnly(True)
        mono_font = QFont("Consolas", 11)
        mono_font.setStyleHint(QFont.StyleHint.Monospace)
        self.display.setFont(mono_font)
        layout.addWidget(self.display, 1)

        # Controls
        ctrl_layout = QHBoxLayout()

        self.btn_play = QPushButton("▶ Putar", self)
        self.btn_play.clicked.connect(self.toggle_play)
        ctrl_layout.addWidget(self.btn_play)

        self.btn_stop = QPushButton("⏹ Stop", self)
        self.btn_stop.clicked.connect(self.stop_playback)
        ctrl_layout.addWidget(self.btn_stop)

        self.lbl_speed = QLabel("Kecepatan:")
        ctrl_layout.addWidget(self.lbl_speed)

        self.btn_speed = QPushButton("1.0x", self)
        self.btn_speed.setMenu(self._build_speed_menu())
        ctrl_layout.addWidget(self.btn_speed)

        self.slider = QSlider(Qt.Orientation.Horizontal, self)
        self.slider.setRange(0, max(1, len(self.frames) - 1))
        self.slider.sliderMoved.connect(self._on_slider_moved)
        ctrl_layout.addWidget(self.slider, 1)

        self.lbl_time = QLabel("00:00 / 00:00")
        ctrl_layout.addWidget(self.lbl_time)

        self.btn_open = QPushButton("📂 Buka .cast", self)
        self.btn_open.clicked.connect(self._open_cast_file)
        ctrl_layout.addWidget(self.btn_open)

        layout.addLayout(ctrl_layout)

    def _build_speed_menu(self):
        from PySide6.QtWidgets import QMenu
        menu = QMenu(self)
        for s in [0.5, 1.0, 1.5, 2.0, 4.0]:
            act = menu.addAction(f"{s}x")
            act.triggered.connect(lambda _c, val=s: self.set_speed(val))
        return menu

    def set_speed(self, speed: float):
        self._speed = speed
        self.btn_speed.setText(f"{speed}x")

    def _apply_theme(self):
        bg = self.theme.get("editor_bg", "#1e1e2e")
        fg = self.theme.get("editor_fg", "#cdd6f4")
        self.setStyleSheet(f"""
            QDialog {{ background-color: {self.theme.get('bg', '#181825')}; color: {fg}; }}
            QPlainTextEdit {{ background-color: {bg}; color: {fg}; border: 1px solid #45475a; font-family: 'Consolas', monospace; }}
            QLabel {{ color: {fg}; }}
            QPushButton {{ background-color: #313244; color: {fg}; border: 1px solid #45475a; padding: 5px 10px; border-radius: 4px; }}
            QPushButton:hover {{ background-color: #45475a; }}
        """)

    def _init_player(self):
        self._current_frame_idx = 0
        self.slider.setRange(0, len(self.frames) - 1)
        self.display.clear()
        self._update_time_label()

    def toggle_play(self):
        if not self.frames:
            return
        if self._is_playing:
            self.pause_playback()
        else:
            self.start_playback()

    def start_playback(self):
        if self._current_frame_idx >= len(self.frames) - 1:
            self._current_frame_idx = 0
            self.display.clear()

        self._is_playing = True
        self.btn_play.setText("⏸ Pause")
        self._schedule_next_frame()

    def pause_playback(self):
        self._is_playing = False
        self.btn_play.setText("▶ Putar")
        self._timer.stop()

    def stop_playback(self):
        self.pause_playback()
        self._current_frame_idx = 0
        self.slider.setValue(0)
        self.display.clear()
        self._update_time_label()

    def _schedule_next_frame(self):
        if not self._is_playing or self._current_frame_idx >= len(self.frames):
            self.pause_playback()
            return

        current_time = self.frames[self._current_frame_idx][0]
        if self._current_frame_idx + 1 < len(self.frames):
            next_time = self.frames[self._current_frame_idx + 1][0]
            delay = max(10, int(((next_time - current_time) / self._speed) * 1000))
        else:
            delay = 100

        self._timer.start(delay)

    def _on_timer_tick(self):
        self._timer.stop()
        if self._current_frame_idx < len(self.frames):
            self._render_frame(self._current_frame_idx)
            self._current_frame_idx += 1
            self.slider.setValue(self._current_frame_idx)
            self._update_time_label()
            self._schedule_next_frame()
        else:
            self.pause_playback()

    def _render_frame(self, idx):
        if 0 <= idx < len(self.frames):
            frame = self.frames[idx]
            event_type = frame[1]
            content = frame[2]
            if event_type in ("o", "i"):
                # Clean ANSI escape sequences for simple display rendering
                clean_text = self._strip_ansi(content)
                self.display.moveCursor(QTextCursor.MoveOperation.End)
                self.display.insertPlainText(clean_text)
                self.display.ensureCursorVisible()

    def _strip_ansi(self, text: str) -> str:
        import re
        ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
        return ansi_escape.sub('', text)

    def _on_slider_moved(self, position):
        self.pause_playback()
        self.display.clear()
        self._current_frame_idx = 0
        for i in range(min(position + 1, len(self.frames))):
            self._render_frame(i)
        self._current_frame_idx = position
        self._update_time_label()

    def _update_time_label(self):
        curr_t = self.frames[self._current_frame_idx][0] if self.frames and self._current_frame_idx < len(self.frames) else 0
        total_t = self.frames[-1][0] if self.frames else 0
        self.lbl_time.setText(f"{self._fmt_sec(curr_t)} / {self._fmt_sec(total_t)}")

    def _fmt_sec(self, seconds: float) -> str:
        m = int(seconds) // 60
        s = int(seconds) % 60
        return f"{m:02d}:{s:02d}"

    def _open_cast_file(self):
        filepath, _ = QFileDialog.getOpenFileName(
            self, "Buka File Rekaman Asciinema (.cast)", "", "Asciinema Cast (*.cast *.json);;Semua File (*.*)")
        if filepath:
            h, f = AsciinemaRecorder.load_from_file(filepath)
            if h is not None and f is not None:
                self.header = h
                self.frames = f
                title_text = self.header.get("title", "Asciinema Recording")
                w = self.header.get("width", 80)
                h_val = self.header.get("height", 24)
                self.lbl_title.setText(f"🎬 <b>{title_text}</b> ({w}x{h_val})")
                if self.frames:
                    self._init_player()
                    self.start_playback()
                else:
                    self.display.setPlainText("[Rekaman ini tidak memuat aktivitas terminal / 0 frame]")
            else:
                QMessageBox.warning(self, "Format Salah", "Gagal membaca format file asciinema .cast")
