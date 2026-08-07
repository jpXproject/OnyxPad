"""Test unit untuk modul recorder dan terminal OnyxPad."""

import os
import tempfile
import pytest
from src.recorder import AsciinemaRecorder, AsciinemaPlayerDialog
from src.terminal import TerminalPanel, TerminalDock, ANSIParser
from PySide6.QtGui import QColor
from PySide6.QtWidgets import QPlainTextEdit


def test_asciinema_recorder_start_and_stop():
    recorder = AsciinemaRecorder(title="Test Rec", width=100, height=30)
    recorder.start()
    assert recorder.is_recording is True
    assert recorder.header["title"] == "Test Rec"
    assert recorder.header["width"] == 100
    assert recorder.header["height"] == 30

    recorder.record_input("ls\n")
    recorder.record_output("file1.py\nfile2.py\n")

    res = recorder.stop()
    assert recorder.is_recording is False
    assert len(res["frames"]) == 2
    assert res["frames"][0][1] == "i"
    assert res["frames"][0][2] == "ls\n"
    assert res["frames"][1][1] == "o"
    assert res["frames"][1][2] == "file1.py\nfile2.py\n"


def test_asciinema_recorder_save_and_load(tmp_path):
    recorder = AsciinemaRecorder(title="Test Save", width=80, height=24)
    recorder.start()
    recorder.record_output("Hello World\n")
    recorder.stop()

    file_path = tmp_path / "session.cast"
    ok = recorder.save_to_file(str(file_path))
    assert ok is True
    assert file_path.exists()

    header, frames = AsciinemaRecorder.load_from_file(str(file_path))
    assert header["title"] == "Test Save"
    assert len(frames) == 1
    assert frames[0][2] == "Hello World\n"


def test_ansi_parser(qapp):
    edit = QPlainTextEdit()
    parser = ANSIParser(default_fg=QColor("#ffffff"))

    # Test raw text & ANSI red color code
    text = "Normal \x1b[31mRed Text\x1b[0m Normal Again"
    parser.append_ansi_text(edit, text)
    assert edit.toPlainText() == "Normal Red Text Normal Again"


def test_terminal_panel_creation(qapp, tmp_path):
    panel = TerminalPanel(cwd=str(tmp_path))
    assert panel.cwd == str(tmp_path)
    assert panel.process is not None

    # Test history navigation
    panel._on_command_submitted("echo hello")
    assert "echo hello" in panel.history

    panel._on_history_up()
    assert panel.history_idx == 0

    panel._on_history_down()
    assert panel.history_idx == 1

    panel.kill_process()


def test_terminal_dock_creation(qapp, tmp_path):
    dock = TerminalDock(cwd=str(tmp_path))
    assert dock.terminal_panel is not None
    dock.set_cwd(str(tmp_path))
    dock.terminal_panel.kill_process()


def test_player_dialog_creation(qapp, tmp_path):
    filepath = tmp_path / "player_test.cast"
    recorder = AsciinemaRecorder(title="Player Test")
    recorder.start()
    recorder.record_output("Testing Player\n")
    recorder.stop()
    recorder.save_to_file(str(filepath))

    dlg = AsciinemaPlayerDialog(filepath=str(filepath))
    assert dlg.header["title"] == "Player Test"
    assert len(dlg.frames) == 1
    dlg._render_frame(0)
    assert "Testing Player" in dlg.display.toPlainText()
