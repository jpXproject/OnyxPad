"""Panel Terminal Terintegrasi untuk OnyxPad.

Mendukung:
- Shell interaktif (PowerShell / CMD / Bash) via QProcess.
- Parsing kode warna ANSI escape sequence.
- Perekaman sesi asciinema v2 (.cast).
- Navigasi riwayat perintah (Panah Atas/Bawah).
- Penyesuaian tema OnyxPad.
"""

import os
import re
import sys
import time
from pathlib import Path

from PySide6.QtCore import QProcess, Qt, Signal, QTimer
from PySide6.QtGui import (QColor, QFont, QIcon, QKeySequence, QTextCharFormat,
                           QTextCursor)
from PySide6.QtWidgets import (QComboBox, QDockWidget, QFileDialog, QHBoxLayout,
                                QLabel, QMessageBox, QPushButton, QPlainTextEdit,
                                QVBoxLayout, QWidget)

from .recorder import AsciinemaRecorder, AsciinemaPlayerDialog


class ANSIParser:
    """Parser sederhana untuk mengonversi ANSI escape code ke format teks PySide6."""

    ANSI_COLOR_MAP = {
        30: QColor("#1e1e2e"),  # Black
        31: QColor("#f38ba8"),  # Red
        32: QColor("#a6e3a1"),  # Green
        33: QColor("#f9e2af"),  # Yellow
        34: QColor("#89b4fa"),  # Blue
        35: QColor("#cba6f7"),  # Magenta
        36: QColor("#94e2d5"),  # Cyan
        37: QColor("#bac2de"),  # White
        90: QColor("#585b70"),  # Bright Black / Gray
        91: QColor("#f38ba8"),  # Bright Red
        92: QColor("#a6e3a1"),  # Bright Green
        93: QColor("#f9e2af"),  # Bright Yellow
        94: QColor("#89b4fa"),  # Bright Blue
        95: QColor("#cba6f7"),  # Bright Magenta
        96: QColor("#94e2d5"),  # Bright Cyan
        97: QColor("#a6adc8"),  # Bright White
    }

    def __init__(self, default_fg=QColor("#cdd6f4")):
        self.default_fg = default_fg
        self.ansi_regex = re.compile(r'\x1b\[([0-9;]*)m')

    def append_ansi_text(self, text_edit: QPlainTextEdit, text: str):
        cursor = text_edit.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)

        parts = self.ansi_regex.split(text)
        fmt = QTextCharFormat()
        fmt.setForeground(self.default_fg)

        i = 0
        while i < len(parts):
            chunk = parts[i]
            if i % 2 == 0:
                if chunk:
                    cursor.insertText(chunk, fmt)
            else:
                # Code escape
                codes = [int(c) for c in chunk.split(';') if c.isdigit()]
                for code in codes:
                    if code == 0:
                        fmt.setForeground(self.default_fg)
                        fmt.setFontWeight(QFont.Weight.Normal)
                    elif code == 1:
                        fmt.setFontWeight(QFont.Weight.Bold)
                    elif code in self.ANSI_COLOR_MAP:
                        fmt.setForeground(self.ANSI_COLOR_MAP[code])
            i += 1

        text_edit.setTextCursor(cursor)
        text_edit.ensureCursorVisible()


class TerminalEdit(QPlainTextEdit):
    """Widget QPlainTextEdit yang disesuaikan untuk input terminal."""

    command_submitted = Signal(str)
    interrupt_signal = Signal()
    history_up = Signal()
    history_down = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.input_start_pos = 0

    def keyPressEvent(self, event):
        cursor = self.textCursor()

        # Izinkan pengetikan jika kursor berada setelah input_start_pos
        if event.key() == Qt.Key.Key_Return or event.key() == Qt.Key.Key_Enter:
            cursor.movePosition(QTextCursor.MoveOperation.End)
            self.setTextCursor(cursor)
            cmd_text = self.toPlainText()[self.input_start_pos:]
            self.appendPlainText("")  # Pindah baris baru
            self.command_submitted.emit(cmd_text)
            return

        if event.key() == Qt.Key.Key_Backspace:
            if cursor.position() <= self.input_start_pos:
                return  # Mencegah menghapus prompt

        if event.modifiers() == Qt.KeyboardModifier.ControlModifier and event.key() == Qt.Key.Key_C:
            if self.textCursor().hasSelection():
                super().keyPressEvent(event)
            else:
                self.interrupt_signal.emit()
            return

        if event.key() == Qt.Key.Key_Up:
            self.history_up.emit()
            return

        if event.key() == Qt.Key.Key_Down:
            self.history_down.emit()
            return

        # Pastikan pengetikan terjadi di akhir teks
        if cursor.position() < self.input_start_pos:
            cursor.movePosition(QTextCursor.MoveOperation.End)
            self.setTextCursor(cursor)

        super().keyPressEvent(event)

    def set_input_prompt_pos(self):
        cursor = self.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        self.input_start_pos = cursor.position()


class TerminalPanel(QWidget):
    """Panel Terminal Interaktif terintegrasi."""

    def __init__(self, theme=None, cwd=None, parent=None):
        super().__init__(parent)
        self.theme = theme or {}
        self.cwd = cwd or os.getcwd()
        self.process = None

        self.history = []
        self.history_idx = -1
        self.current_cmd_draft = ""

        self.recorder = AsciinemaRecorder()
        self.parser = ANSIParser()

        self._build_ui()
        self.apply_theme(self.theme)
        self.start_terminal()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(4)

        # Toolbar
        tb = QHBoxLayout()

        self.lbl_shell = QLabel("Shell:", self)
        tb.addWidget(self.lbl_shell)

        self.cb_shell = QComboBox(self)
        if sys.platform == "win32":
            self.cb_shell.addItems(["PowerShell", "Command Prompt (CMD)"])
        else:
            self.cb_shell.addItems(["Bash", "Sh"])
        self.cb_shell.currentIndexChanged.connect(self.restart_terminal)
        tb.addWidget(self.cb_shell)

        tb.addSpacing(10)

        self.btn_clear = QPushButton("🧹 Bersihkan", self)
        self.btn_clear.clicked.connect(self.clear_terminal)
        tb.addWidget(self.btn_clear)

        self.btn_restart = QPushButton("🔄 Restart Shell", self)
        self.btn_restart.clicked.connect(self.restart_terminal)
        tb.addWidget(self.btn_restart)

        tb.addStretch()

        # Rec Controls (Asciinema)
        self._rec_timer = QTimer(self)
        self._rec_timer.timeout.connect(self._update_rec_timer_label)

        self.lbl_rec_status = QLabel("🔴 REC 00:00", self)
        self.lbl_rec_status.setStyleSheet("color: #ff5555; font-weight: bold; font-family: monospace;")
        self.lbl_rec_status.setVisible(False)
        tb.addWidget(self.lbl_rec_status)

        self.btn_record = QPushButton("⏺ Rekam Asciinema", self)
        self.btn_record.clicked.connect(self.toggle_recording)
        tb.addWidget(self.btn_record)

        self.btn_play_rec = QPushButton("▶ Putar .cast", self)
        self.btn_play_rec.clicked.connect(self.open_player_dialog)
        tb.addWidget(self.btn_play_rec)

        layout.addLayout(tb)

        # Terminal Edit Area
        self.editor = TerminalEdit(self)
        mono_font = QFont("Consolas", 10)
        mono_font.setStyleHint(QFont.StyleHint.Monospace)
        self.editor.setFont(mono_font)

        self.editor.command_submitted.connect(self._on_command_submitted)
        self.editor.interrupt_signal.connect(self._on_interrupt)
        self.editor.history_up.connect(self._on_history_up)
        self.editor.history_down.connect(self._on_history_down)

        layout.addWidget(self.editor, 1)

    def apply_theme(self, theme):
        self.theme = theme or {}
        bg = self.theme.get("editor_bg", "#1e1e2e")
        fg = self.theme.get("editor_fg", "#cdd6f4")
        accent = self.theme.get("accent", "#89b4fa")

        self.parser.default_fg = QColor(fg)
        self.setStyleSheet(f"""
            QWidget {{ background-color: {self.theme.get('bg', '#181825')}; color: {fg}; }}
            QPlainTextEdit {{ background-color: {bg}; color: {fg}; border: 1px solid #45475a; selection-background-color: {accent}; }}
            QPushButton {{ background-color: #313244; color: {fg}; border: 1px solid #45475a; padding: 3px 8px; border-radius: 3px; font-size: 11px; }}
            QPushButton:hover {{ background-color: #45475a; }}
            QComboBox {{ background-color: #313244; color: {fg}; border: 1px solid #45475a; padding: 2px 5px; font-size: 11px; }}
        """)

    def set_cwd(self, directory: str):
        if directory and os.path.isdir(directory):
            self.cwd = directory
            if self.process and self.process.state() == QProcess.ProcessState.Running:
                self.restart_terminal()

    def start_terminal(self):
        if self.process:
            self.process.kill()
            self.process.waitForFinished(1000)

        self.process = QProcess(self)
        self.process.setWorkingDirectory(self.cwd)

        # Setting Environment
        env = QProcess.systemEnvironment()
        env.append("TERM=xterm-256color")
        self.process.setEnvironment(env)

        self.process.readyReadStandardOutput.connect(self._read_stdout)
        self.process.readyReadStandardError.connect(self._read_stderr)
        self.process.finished.connect(self._on_process_finished)

        shell_type = self.cb_shell.currentText()
        if sys.platform == "win32":
            if "CMD" in shell_type:
                self.process.start("cmd.exe", ["/q", "/k", f"cd /d \"{self.cwd}\""])
            else:
                self.process.start("powershell.exe", ["-NoLogo", "-NoExit", "-Command", f"Set-Location '{self.cwd}'"])
        else:
            shell_name = "bash" if "Bash" in shell_type else "sh"
            self.process.start(shell_name, ["-i"])

        self.editor.set_input_prompt_pos()

    def _on_process_finished(self, exit_code, exit_status):
        msg = f"\n\n[Sesi Terminal Berhenti (code {exit_code}) — Klik 'Reset' atau ganti Shell untuk sesi baru]\n"
        self.parser.append_ansi_text(self.editor, msg)
        self.editor.set_input_prompt_pos()

    def restart_terminal(self):
        self.clear_terminal()
        self.start_terminal()

    def clear_terminal(self):
        self.editor.clear()
        self.editor.set_input_prompt_pos()

    def kill_process(self):
        if self.process and self.process.state() != QProcess.ProcessState.NotRunning:
            self.process.kill()
            self.process.waitForFinished(500)

    def closeEvent(self, event):
        self.kill_process()
        super().closeEvent(event)

    def _read_stdout(self):
        data = self.process.readAllStandardOutput().data().decode("utf-8", errors="replace")
        if data:
            self.parser.append_ansi_text(self.editor, data)
            self.editor.set_input_prompt_pos()
            if self.recorder.is_recording:
                self.recorder.record_output(data)

    def _read_stderr(self):
        data = self.process.readAllStandardError().data().decode("utf-8", errors="replace")
        if data:
            self.parser.append_ansi_text(self.editor, data)
            self.editor.set_input_prompt_pos()
            if self.recorder.is_recording:
                self.recorder.record_output(data)

    def _on_command_submitted(self, cmd_text: str):
        if cmd_text.strip():
            self.history.append(cmd_text)
            self.history_idx = len(self.history)

        if self.recorder.is_recording:
            self.recorder.record_input(cmd_text + "\n")

        if self.process and self.process.state() == QProcess.ProcessState.Running:
            self.process.write((cmd_text + "\n").encode("utf-8"))

    def _on_interrupt(self):
        if self.process and self.process.state() == QProcess.ProcessState.Running:
            if sys.platform == "win32":
                self.process.write(b"\x03")
            else:
                self.process.write(b"\x03")

    def _on_history_up(self):
        if not self.history:
            return
        if self.history_idx == len(self.history):
            cursor = self.editor.textCursor()
            cursor.setPosition(self.editor.input_start_pos)
            cursor.movePosition(QTextCursor.MoveOperation.End, QTextCursor.MoveMode.KeepAnchor)
            self.current_cmd_draft = cursor.selectedText()

        if self.history_idx > 0:
            self.history_idx -= 1
            self._replace_current_input(self.history[self.history_idx])

    def _on_history_down(self):
        if not self.history or self.history_idx >= len(self.history):
            return
        self.history_idx += 1
        if self.history_idx < len(self.history):
            self._replace_current_input(self.history[self.history_idx])
        else:
            self._replace_current_input(self.current_cmd_draft)

    def _replace_current_input(self, text: str):
        cursor = self.editor.textCursor()
        cursor.setPosition(self.editor.input_start_pos)
        cursor.movePosition(QTextCursor.MoveOperation.End, QTextCursor.MoveMode.KeepAnchor)
        cursor.insertText(text)

    # Asciinema Recording Integrasi
    def _update_rec_timer_label(self):
        if not hasattr(self, "_rec_start_time") or self._rec_start_time is None:
            return
        elapsed = int(time.time() - self._rec_start_time)
        m = elapsed // 60
        s = elapsed % 60
        self.lbl_rec_status.setText(f"🔴 REC {m:02d}:{s:02d}")

    def toggle_recording(self):
        win = self.window()
        if self.recorder.is_recording:
            # Stop & Save silently without annoying popups
            self.recorder.stop()
            self._rec_timer.stop()
            self.lbl_rec_status.setVisible(False)
            self.btn_record.setText("⏺ Rekam Asciinema")
            self.btn_record.setStyleSheet("")

            default_dir = os.path.expanduser("~/.onyxpad/recordings")
            os.makedirs(default_dir, exist_ok=True)
            default_name = os.path.join(default_dir, f"session_{int(time.time())}.cast")

            filepath, _ = QFileDialog.getSaveFileName(
                self, "Simpan Rekaman Asciinema", default_name, "Asciinema Cast (*.cast);;JSON Lines (*.json)")
            if filepath:
                if self.recorder.save_to_file(filepath):
                    if hasattr(win, "statusBar") and win.statusBar():
                        win.statusBar().showMessage(f"File tersimpan: {os.path.basename(filepath)}", 4000)
                    # Buka dialog player secara otomatis
                    dlg = AsciinemaPlayerDialog(filepath=filepath, theme=self.theme, parent=self)
                    dlg.exec()
        else:
            # Start Recording SILENTLY (No intrusive popup message box!)
            title = f"OnyxPad Terminal Session ({self.cb_shell.currentText()})"
            self.recorder.start(width=80, height=24, title=title)
            self._rec_start_time = time.time()
            self._rec_timer.start(1000)
            self._update_rec_timer_label()
            self.lbl_rec_status.setVisible(True)
            self.btn_record.setText("⏹ Hentikan Rekam")
            self.btn_record.setStyleSheet("background-color: #f38ba8; color: #11111b; font-weight: bold;")
            if hasattr(win, "statusBar") and win.statusBar():
                win.statusBar().showMessage("🔴 Perekaman Terminal Dimulai (Tekan ⏹ Hentikan Rekam untuk Menyimpan)", 4000)

    def open_player_dialog(self):
        dlg = AsciinemaPlayerDialog(theme=self.theme, parent=self)
        dlg.exec()


class TerminalDock(QDockWidget):
    """DockWidget pembungkus untuk panel terminal."""

    def __init__(self, theme=None, cwd=None, parent=None):
        super().__init__("Terminal Terintegrasi", parent)
        self.setObjectName("terminalDock")
        self.terminal_panel = TerminalPanel(theme=theme, cwd=cwd, parent=self)
        self.setWidget(self.terminal_panel)

    def apply_theme(self, theme):
        self.terminal_panel.apply_theme(theme)

    def set_cwd(self, directory: str):
        self.terminal_panel.set_cwd(directory)
