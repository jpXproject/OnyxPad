"""Preview Komponen Media (Gambar & Video) untuk OnyxPad."""

import os
from pathlib import Path

from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import QFont, QIcon, QPixmap
from PySide6.QtWidgets import (QHBoxLayout, QLabel, QPushButton, QScrollArea,
                                QSlider, QVBoxLayout, QWidget)

try:
    from PySide6.QtMultimedia import QAudioOutput, QMediaPlayer
    from PySide6.QtMultimediaWidgets import QVideoWidget
    MULTIMEDIA_AVAILABLE = True
except ImportError:
    MULTIMEDIA_AVAILABLE = False


IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".gif", ".ico", ".bmp", ".svg", ".webp"}
VIDEO_EXTS = {".mp4", ".webm", ".avi", ".mkv", ".mov"}


class ImagePreviewWidget(QWidget):
    """Widget preview gambar interaktif."""

    def __init__(self, file_path: str, theme=None, parent=None):
        super().__init__(parent)
        self._file_path = file_path
        self.theme = theme or {}
        self._build_ui()

    def display_name(self):
        return os.path.basename(self._file_path)

    def file_path(self):
        return self._file_path

    def is_media_preview(self):
        return True

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)

        # Header Info
        info_layout = QHBoxLayout()
        size_mb = os.path.getsize(self._file_path) / (1024 * 1024) if os.path.exists(self._file_path) else 0
        pix = QPixmap(self._file_path)
        w, h = pix.width(), pix.height()

        lbl_info = QLabel(
            f"🖼 <b>{os.path.basename(self._file_path)}</b> ({w}x{h} px · {size_mb:.2f} MB)"
        )
        info_layout.addWidget(lbl_info)
        info_layout.addStretch()
        layout.addLayout(info_layout)

        # Scroll Area with Centered Image
        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setAlignment(Qt.AlignmentFlag.AlignCenter)

        container = QWidget()
        c_layout = QVBoxLayout(container)
        c_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        lbl_img = QLabel()
        lbl_img.setPixmap(pix)
        lbl_img.setAlignment(Qt.AlignmentFlag.AlignCenter)
        c_layout.addWidget(lbl_img)

        scroll.setWidget(container)
        layout.addWidget(scroll, 1)

        self.apply_theme(self.theme)

    def apply_theme(self, theme):
        self.theme = theme or {}
        bg = self.theme.get("editor_bg", "#1e1e2e")
        fg = self.theme.get("editor_fg", "#cdd6f4")
        self.setStyleSheet(f"""
            QWidget {{ background-color: {self.theme.get('bg', '#181825')}; color: {fg}; }}
            QScrollArea {{ background-color: {bg}; border: 1px solid #45475a; }}
            QLabel {{ color: {fg}; }}
        """)


class VideoPreviewWidget(QWidget):
    """Widget preview video interaktif dengan kontrol putar/pause & slider."""

    def __init__(self, file_path: str, theme=None, parent=None):
        super().__init__(parent)
        self._file_path = file_path
        self.theme = theme or {}
        self._build_ui()

    def display_name(self):
        return os.path.basename(self._file_path)

    def file_path(self):
        return self._file_path

    def is_media_preview(self):
        return True

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)

        size_mb = os.path.getsize(self._file_path) / (1024 * 1024) if os.path.exists(self._file_path) else 0
        lbl_info = QLabel(
            f"🎬 <b>{os.path.basename(self._file_path)}</b> ({size_mb:.2f} MB)"
        )
        layout.addWidget(lbl_info)

        if MULTIMEDIA_AVAILABLE:
            self.video_widget = QVideoWidget(self)
            layout.addWidget(self.video_widget, 1)

            self.player = QMediaPlayer(self)
            self.audio_output = QAudioOutput(self)
            self.player.setAudioOutput(self.audio_output)
            self.player.setVideoOutput(self.video_widget)
            self.player.setSource(QUrl.fromLocalFile(self._file_path))

            # Controls
            ctrl_layout = QHBoxLayout()

            self.btn_play = QPushButton("▶ Putar", self)
            self.btn_play.clicked.connect(self._toggle_play)
            ctrl_layout.addWidget(self.btn_play)

            self.slider = QSlider(Qt.Orientation.Horizontal, self)
            self.slider.sliderMoved.connect(self._set_position)
            ctrl_layout.addWidget(self.slider, 1)

            self.lbl_time = QLabel("00:00 / 00:00", self)
            ctrl_layout.addWidget(self.lbl_time)

            layout.addLayout(ctrl_layout)

            self.player.positionChanged.connect(self._on_position_changed)
            self.player.durationChanged.connect(self._on_duration_changed)
        else:
            lbl_err = QLabel("QtMultimedia tidak tersedia untuk pemutaran video.")
            layout.addWidget(lbl_err, 1)

        self.apply_theme(self.theme)

    def _toggle_play(self):
        if not MULTIMEDIA_AVAILABLE:
            return
        if self.player.playbackState() == QMediaPlayer.PlaybackState.PlayingState:
            self.player.pause()
            self.btn_play.setText("▶ Putar")
        else:
            self.player.play()
            self.btn_play.setText("⏸ Pause")

    def _set_position(self, position):
        if MULTIMEDIA_AVAILABLE:
            self.player.setPosition(position)

    def _on_position_changed(self, position):
        if not MULTIMEDIA_AVAILABLE:
            return
        self.slider.setValue(position)
        dur = self.player.duration()
        self.lbl_time.setText(f"{self._fmt(position)} / {self._fmt(dur)}")

    def _on_duration_changed(self, duration):
        if MULTIMEDIA_AVAILABLE:
            self.slider.setRange(0, duration)

    @staticmethod
    def _fmt(ms):
        sec = ms // 1000
        m = sec // 60
        s = sec % 60
        return f"{m:02d}:{s:02d}"

    def apply_theme(self, theme):
        self.theme = theme or {}
        bg = self.theme.get("editor_bg", "#1e1e2e")
        fg = self.theme.get("editor_fg", "#cdd6f4")
        self.setStyleSheet(f"""
            QWidget {{ background-color: {self.theme.get('bg', '#181825')}; color: {fg}; }}
            QPushButton {{ background-color: #313244; color: {fg}; border: 1px solid #45475a; padding: 4px 10px; border-radius: 4px; }}
            QPushButton:hover {{ background-color: #45475a; }}
            QLabel {{ color: {fg}; }}
        """)

    def closeEvent(self, event):
        if MULTIMEDIA_AVAILABLE and hasattr(self, 'player'):
            self.player.stop()
        super().closeEvent(event)
