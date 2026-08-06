"""Test untuk CodeEditor — pasangan kurung, auto-indent, komentar, I/O, find."""

from PySide6.QtCore import Qt, QEvent, QPoint, QPointF
from PySide6.QtGui import QKeyEvent, QTextCursor, QWheelEvent
from PySide6.QtWidgets import QPlainTextEdit


def press(editor, text, key=Qt.Key.Key_unknown,
          modifiers=Qt.KeyboardModifier.NoModifier):
    editor.keyPressEvent(
        QKeyEvent(QEvent.Type.KeyPress, key, modifiers, text))


def set_cursor(editor, pos):
    c = editor.textCursor()
    c.setPosition(pos)
    editor.setTextCursor(c)


def move_end(editor):
    editor.moveCursor(QTextCursor.MoveOperation.End)


# ---------------------------------------------------------------- state
def test_initial_state(make_editor):
    ed = make_editor(language="python", tab_width=4)
    assert ed.toPlainText() == ""
    assert ed._language == "python"
    assert ed._tab_width == 4
    assert ed.display_name() == "Tanpa Judul"
    assert ed.file_path() is None
    assert ed.set_encoding_name() == "utf-8"
    assert ed._highlighter is not None


def test_unknown_language_falls_back(make_editor):
    ed = make_editor(language="nope")
    assert ed._language == "plain"


def test_wrap_mode_widget_width(make_editor):
    ed = make_editor(wrap=True)
    assert ed.lineWrapMode() == QPlainTextEdit.LineWrapMode.WidgetWidth
    ed2 = make_editor(wrap=False)
    assert ed2.lineWrapMode() == QPlainTextEdit.LineWrapMode.NoWrap


def test_fresh_editor_not_modified(make_editor):
    ed = make_editor()
    assert not ed.document().isModified()


# ------------------------------------------------------------ auto-pair
def test_auto_pair_parenthesis(make_editor):
    ed = make_editor()
    press(ed, "(", Qt.Key.Key_ParenLeft)
    assert ed.toPlainText() == "()"
    assert ed.textCursor().position() == 1


def test_auto_pair_quote(make_editor):
    ed = make_editor()
    press(ed, '"', Qt.Key.Key_QuoteDbl)
    assert ed.toPlainText() == '""'
    assert ed.textCursor().position() == 1


def test_pair_wraps_selection(make_editor):
    ed = make_editor()
    ed.setPlainText("abc")
    ed.selectAll()
    press(ed, "(", Qt.Key.Key_ParenLeft)
    assert ed.toPlainText() == "(abc)"


def test_skip_closer(make_editor):
    ed = make_editor()
    ed.setPlainText("()")
    set_cursor(ed, 1)
    press(ed, ")", Qt.Key.Key_ParenRight)
    assert ed.toPlainText() == "()"
    assert ed.textCursor().position() == 2


# ---------------------------------------------------------------- indent
def test_tab_indents_four_spaces(make_editor):
    ed = make_editor(tab_width=4)
    press(ed, "\t", Qt.Key.Key_Tab)
    assert ed.toPlainText() == "    "


def test_shift_tab_dedents(make_editor):
    ed = make_editor(tab_width=4)
    ed.setPlainText("        x = 1")
    set_cursor(ed, 8)
    press(ed, "\t", Qt.Key.Key_Tab,
          Qt.KeyboardModifier.ShiftModifier)
    assert ed.toPlainText() == "    x = 1"


def test_indent_selection(make_editor):
    ed = make_editor(tab_width=4)
    ed.setPlainText("a\nb")
    ed.selectAll()
    ed._indent_selection(1)
    assert ed.toPlainText() == "    a\n    b"


def test_auto_indent_after_brace(make_editor):
    ed = make_editor(tab_width=4)
    ed.setPlainText("def f() {")
    move_end(ed)
    press(ed, "\r", Qt.Key.Key_Return)
    assert ed.toPlainText() == "def f() {\n    "


def test_auto_indent_python_colon(make_editor):
    ed = make_editor(language="python", tab_width=4)
    ed.setPlainText("if x:")
    move_end(ed)
    press(ed, "\r", Qt.Key.Key_Return)
    assert ed.toPlainText() == "if x:\n    "


def test_backspace_dedents(make_editor):
    ed = make_editor(tab_width=4)
    ed.setPlainText("        x")
    set_cursor(ed, 4)
    press(ed, "\b", Qt.Key.Key_Backspace)
    assert ed.toPlainText() == "    x"


# -------------------------------------------------------------- comment
def test_toggle_comment_python(make_editor):
    ed = make_editor(language="python")
    ed.setPlainText("x = 1\ny = 2")
    ed.selectAll()
    ed.toggle_comment()
    assert ed.toPlainText() == "#x = 1\n#y = 2"
    ed.toggle_comment()
    assert ed.toPlainText() == "x = 1\ny = 2"


def test_toggle_comment_javascript(make_editor):
    ed = make_editor(language="javascript")
    ed.setPlainText("var a = 1;")
    ed.selectAll()
    ed.toggle_comment()
    assert ed.toPlainText() == "//var a = 1;"


def test_toggle_comment_indented(make_editor):
    """Un-comment baris berindentasi harus menghapus prefix, bukan spasi."""
    ed = make_editor(language="python")
    ed.setPlainText("    # x = 1")
    ed.selectAll()
    ed.toggle_comment()
    # indentasi 4 spasi tetap utuh; yang dihapus hanya prefix '#'
    assert ed.toPlainText() == "     x = 1"
    # komentari lagi: prefix disisipkan di kolom 0 (di depan indentasi)
    ed.toggle_comment()
    assert ed.toPlainText() == "#     x = 1"


def test_indent_selection_preserves_selection(make_editor):
    ed = make_editor(tab_width=4)
    ed.setPlainText("a\nb\nc")
    ed.selectAll()
    ed._indent_selection(1)
    assert ed.toPlainText() == "    a\n    b\n    c"
    assert ed.textCursor().hasSelection()
    # selectedText() memakai U+2029 sebagai pemisah paragraf
    assert ed.textCursor().selectedText() == "    a\u2029    b\u2029    c"


# --------------------------------------------------------- bracket match
def test_bracket_matching(make_editor):
    ed = make_editor()
    ed.setPlainText("foo(bar)")
    set_cursor(ed, 4)
    assert ed._bracket_pairs() == [(3, 7)]
    set_cursor(ed, 8)
    assert ed._bracket_pairs() == [(3, 7)]


def test_bracket_matching_no_pair(make_editor):
    ed = make_editor()
    ed.setPlainText("foo(bar")
    set_cursor(ed, 4)
    assert ed._bracket_pairs() == []


# ---------------------------------------------------------------- status
def test_cursor_info(make_editor):
    ed = make_editor()
    ed.setPlainText("abc\ndef")
    move_end(ed)
    line, col, sel = ed.cursor_info()
    assert (line, col) == (2, 4)
    assert sel == 0


def test_stats(make_editor):
    ed = make_editor()
    ed.setPlainText("hello world\nfoo")
    words, chars = ed.stats()
    assert words == 3
    assert chars == 15  # "hello world" (11) + "\n" + "foo" (3)


def test_go_to_line(make_editor):
    ed = make_editor()
    ed.setPlainText("a\nb\nc")
    ed.go_to_line(3)
    assert ed.textCursor().blockNumber() == 2


def test_go_to_line_invalid(make_editor):
    ed = make_editor()
    ed.setPlainText("a\nb")
    ed.go_to_line(99)  # tidak boleh crash
    ed.go_to_line(0)
    assert ed.toPlainText() == "a\nb"


# ---------------------------------------------------------------- file io
def test_load_and_save(tmp_path, make_editor):
    p = tmp_path / "test.py"
    p.write_text("print('halo')\n", encoding="utf-8")
    ed = make_editor()
    ok, err = ed.load(str(p))
    assert ok and err is None
    assert ed.toPlainText() == "print('halo')\n"
    assert ed._language == "python"
    assert not ed.document().isModified()

    ed.setPlainText("x = 1")
    ok, err = ed.save()
    assert ok and err is None
    assert p.read_text(encoding="utf-8") == "x = 1"
    assert not ed.document().isModified()


def test_save_as(tmp_path, make_editor):
    p = tmp_path / "out.txt"
    ed = make_editor()
    ed.setPlainText("isi")
    ok, err = ed.save(str(p))
    assert ok and err is None
    assert p.read_text(encoding="utf-8") == "isi"
    assert ed.file_path() == str(p)
    assert ed.display_name() == "out.txt"


def test_load_missing_file(make_editor):
    ed = make_editor()
    ok, err = ed.load("tidak/ada/file.txt")
    assert not ok
    assert err


def test_save_without_path_fails(make_editor):
    ed = make_editor()
    ok, err = ed.save()
    assert not ok
    assert err


def test_encoding_bom(tmp_path, make_editor):
    p = tmp_path / "bom.txt"
    p.write_bytes(b"\xef\xbb\xbfhalo")
    ed = make_editor()
    ok, _err = ed.load(str(p))
    assert ok
    assert ed.set_encoding_name() == "utf-8-sig"
    assert ed.toPlainText() == "halo"


def test_display_name_with_path(tmp_path, make_editor):
    p = tmp_path / "script.js"
    p.write_text("var x = 1;", encoding="utf-8")
    ed = make_editor()
    ed.load(str(p))
    assert ed.display_name() == "script.js"
    assert ed._language == "javascript"


# ----------------------------------------------------------------- zoom
def test_ctrl_wheel_zoom(make_editor):
    ed = make_editor()
    before = ed._zoom
    ev = QWheelEvent(
        QPointF(10, 10), QPointF(10, 10), QPoint(0, 0), QPoint(0, 120),
        Qt.MouseButton.NoButton, Qt.KeyboardModifier.ControlModifier,
        Qt.ScrollPhase.NoScrollPhase, False)
    ed.wheelEvent(ev)
    assert ed._zoom == before + 1


def test_plain_wheel_no_zoom(make_editor):
    ed = make_editor()
    ev = QWheelEvent(
        QPointF(10, 10), QPointF(10, 10), QPoint(0, 0), QPoint(0, 120),
        Qt.MouseButton.NoButton, Qt.KeyboardModifier.NoModifier,
        Qt.ScrollPhase.NoScrollPhase, False)
    ed.wheelEvent(ev)
    assert ed._zoom == 0
