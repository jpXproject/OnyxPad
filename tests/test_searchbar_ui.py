"""Test UI SearchBar dengan pytest-qt — visibilitas, tombol, keyboard, replace."""

import pytest
from PySide6.QtCore import Qt
from PySide6.QtGui import QTextDocument
from PySide6.QtWidgets import QMainWindow, QMessageBox

from src.search import SearchBar
from src.themes import THEMES, THEME_ORDER


def empty_flags():
    """Panggilan via fungsi agar terhindar dari rewrite assert pytest."""
    return QTextDocument.FindFlags()


@pytest.fixture()
def bar(qtbot, theme, make_editor):
    """SearchBar di dalam window yang ditampilkan + editor yang terhubung."""
    b = SearchBar(theme)
    ed = make_editor()
    b.set_editor_getter(lambda: ed)
    win = QMainWindow()
    win.setCentralWidget(b)
    # qtbot.addWidget hanya menyimpan weakref — simpan referensi kuat agar
    # window (yang dimiliki Python) tidak di-GC dan menghapus SearchBar.
    b._test_window = win
    qtbot.addWidget(win)
    win.show()
    qtbot.waitExposed(win)
    qtbot.waitUntil(lambda: win.isActiveWindow())
    return b, ed


# -------------------------------------------------------------- visibility
def test_hidden_by_default(bar):
    b, _ed = bar
    assert b.isHidden()
    assert b.replace_edit.isHidden()
    assert b.replace_btn.isHidden()
    assert b.replace_all_btn.isHidden()


def test_show_find_mode(bar):
    b, _ed = bar
    b.show_find()
    assert not b.isHidden()
    assert b.replace_edit.isHidden()
    assert b.replace_btn.isHidden()
    assert b.replace_all_btn.isHidden()
    assert b.find_edit.hasFocus()


def test_show_replace_mode(bar):
    b, _ed = bar
    b.show_replace()
    assert not b.isHidden()
    assert not b.replace_edit.isHidden()
    assert not b.replace_btn.isHidden()
    assert not b.replace_all_btn.isHidden()


def test_show_find_selects_existing_text(bar):
    b, _ed = bar
    b.find_edit.setText("halo")
    b.show_find()
    assert b.find_edit.selectedText() == "halo"


def test_close_btn_hides_and_clears_matches(bar, qtbot):
    b, ed = bar
    ed.setPlainText("satu dua")
    b.find_edit.setText("satu")
    b.show_find()
    b._do_find(True)
    assert ed._search_query  # ada highlight
    qtbot.mouseClick(b.close_btn, Qt.MouseButton.LeftButton)
    assert b.isHidden()
    assert ed._search_query == ""


# ------------------------------------------------------------------ find
def test_next_btn_selects_match(bar, qtbot):
    b, ed = bar
    ed.setPlainText("hello world")
    b.find_edit.setText("hello")
    b.show_find()
    qtbot.mouseClick(b.next_btn, Qt.MouseButton.LeftButton)
    assert ed.textCursor().selectedText() == "hello"


def test_prev_btn_selects_backward(bar, qtbot):
    b, ed = bar
    ed.setPlainText("hello hello")
    b.find_edit.setText("hello")
    b.show_find()
    qtbot.mouseClick(b.next_btn, Qt.MouseButton.LeftButton)
    qtbot.mouseClick(b.next_btn, Qt.MouseButton.LeftButton)
    # mundur: kembali ke kemunculan pertama
    qtbot.mouseClick(b.prev_btn, Qt.MouseButton.LeftButton)
    assert ed.textCursor().selectionStart() == 0


def test_enter_key_finds_next(bar, qtbot):
    b, ed = bar
    ed.setPlainText("one two one")
    b.find_edit.setText("one")
    b.show_find()
    b.find_edit.setFocus()
    qtbot.keyClick(b.find_edit, Qt.Key.Key_Return)
    assert ed.textCursor().selectedText() == "one"
    assert ed.textCursor().selectionStart() == 0
    qtbot.keyClick(b.find_edit, Qt.Key.Key_Return)
    assert ed.textCursor().selectionStart() == 8


def test_find_wraps_around(bar, qtbot):
    b, ed = bar
    ed.setPlainText("one two one")
    b.find_edit.setText("one")
    b.show_find()
    # klik Berikutnya 3x — melewati kemunculan terakhir → kembali ke awal
    for _ in range(3):
        qtbot.mouseClick(b.next_btn, Qt.MouseButton.LeftButton)
    assert ed.textCursor().selectionStart() == 0


def test_find_with_no_text_does_nothing(bar):
    b, ed = bar
    ed.setPlainText("abc")
    b.show_find()
    b._do_find(True)  # find_edit kosong → tidak crash
    assert not ed.textCursor().hasSelection()


def test_find_without_editor_safe(qtbot, theme):
    b = SearchBar(theme)
    qtbot.addWidget(b)
    b.find_edit.setText("abc")
    b._do_find(True)  # tidak ada editor → tidak crash
    b._replace_all()  # tidak ada editor → tidak crash


# ------------------------------------------------------------------ count
def test_count_label_after_find(bar, qtbot):
    b, ed = bar
    ed.setPlainText("kucing anjing kucing")
    b.find_edit.setText("kucing")
    b.show_find()
    qtbot.mouseClick(b.next_btn, Qt.MouseButton.LeftButton)
    assert b.count_label.text() == "2 cocok"


def test_count_label_empty_without_text(bar):
    b, ed = bar
    ed.setPlainText("abc")
    b.show_find()
    b._update_count()
    assert b.count_label.text() == ""


def test_count_label_invalid_regex(bar):
    b, _ed = bar
    b.find_edit.setText("(")
    b.regex_box.setChecked(True)
    b._update_count()
    assert b.count_label.text() == "pola regex salah"


# ------------------------------------------------------------------ flags
def test_flags_empty_by_default(bar):
    b, _ed = bar
    assert b._flags() == empty_flags()


def test_flags_case_sensitive(bar):
    b, _ed = bar
    b.case_box.setChecked(True)
    assert b._flags() & QTextDocument.FindFlag.FindCaseSensitively


def test_flags_whole_word(bar):
    b, _ed = bar
    b.word_box.setChecked(True)
    assert b._flags() & QTextDocument.FindFlag.FindWholeWords


def test_pattern_escaped_literal(bar):
    b, _ed = bar
    b.find_edit.setText("a.b")
    assert b._pattern() == "a\\.b"
    assert b._pattern() != "a.b"


def test_pattern_raw_when_regex(bar):
    b, _ed = bar
    b.find_edit.setText(r"\d+")
    b.regex_box.setChecked(True)
    assert b._pattern() == r"\d+"


def test_regex_find_via_ui(bar, qtbot):
    b, ed = bar
    ed.setPlainText("a1 b22 c333")
    b.find_edit.setText(r"\d+")
    b.regex_box.setChecked(True)
    b.show_find()
    qtbot.mouseClick(b.next_btn, Qt.MouseButton.LeftButton)
    assert ed.textCursor().selectedText() == "1"
    b._update_count()
    assert b.count_label.text() == "3 cocok"


# ---------------------------------------------------------------- replace
def test_replace_button(bar, qtbot):
    b, ed = bar
    ed.setPlainText("a bb a")
    b.find_edit.setText("bb")
    b.replace_edit.setText("X")
    b.show_replace()
    b._do_find(True)
    qtbot.mouseClick(b.replace_btn, Qt.MouseButton.LeftButton)
    assert ed.toPlainText() == "a X a"


def test_replace_all_button(bar, qtbot, monkeypatch):
    b, ed = bar
    messages = []
    monkeypatch.setattr(QMessageBox, "information",
                        lambda *a, **k: messages.append(a))
    ed.setPlainText("a1 b2 a3")
    b.find_edit.setText(r"\d")
    b.replace_edit.setText("#")
    b.regex_box.setChecked(True)
    b.show_replace()
    qtbot.mouseClick(b.replace_all_btn, Qt.MouseButton.LeftButton)
    assert ed.toPlainText() == "a# b# a#"
    assert len(messages) == 1
    assert "3 kemunculan diganti." in messages[0][-1]


def test_replace_all_no_match_no_dialog(bar, qtbot, monkeypatch):
    b, ed = bar
    called = []
    monkeypatch.setattr(QMessageBox, "information",
                        lambda *a, **k: called.append(a))
    ed.setPlainText("abc")
    b.find_edit.setText("xyz")
    b.replace_edit.setText("#")
    b.show_replace()
    qtbot.mouseClick(b.replace_all_btn, Qt.MouseButton.LeftButton)
    assert ed.toPlainText() == "abc"
    assert called == []


# --------------------------------------------------------------- keyboard
def test_escape_hides_bar(bar, qtbot):
    b, _ed = bar
    b.find_edit.setText("a")
    b.show_find()
    b.find_edit.setFocus()
    qtbot.keyClick(b.find_edit, Qt.Key.Key_Escape)
    assert b.isHidden()


def test_shift_enter_finds_previous(bar, qtbot):
    b, ed = bar
    ed.setPlainText("x y x")
    b.find_edit.setText("x")
    b.show_find()
    b.find_edit.setFocus()
    # dari posisi awal (0) mundur → wrap ke kemunculan terakhir (pos 4)
    qtbot.keyClick(b.find_edit, Qt.Key.Key_Return,
                   Qt.KeyboardModifier.ShiftModifier)
    assert ed.textCursor().selectionStart() == 4


def test_apply_theme_no_crash(bar):
    b, _ed = bar
    b.apply_theme(THEMES["Monokai"])
    assert b._theme["name"] == "Monokai"
