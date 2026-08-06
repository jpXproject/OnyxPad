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


def test_quote_overtype_skips_closer(make_editor):
    """Mengetik kutip di depan penutup kutip = overtype (lompat), bukan duplikat."""
    ed = make_editor()
    press(ed, '"', Qt.Key.Key_QuoteDbl)  # "" auto-close, kursor di tengah
    press(ed, '"', Qt.Key.Key_QuoteDbl)  # overtype: lompat ke kanan
    assert ed.toPlainText() == '""'
    assert ed.textCursor().position() == 2


def test_open_paren_before_closer_nests(make_editor):
    """'(' bukan penutup — mengetiknya tetap membuat pasangan baru (bukan skip)."""
    ed = make_editor()
    ed.setPlainText("()")
    set_cursor(ed, 0)
    press(ed, "(", Qt.Key.Key_ParenLeft)
    assert ed.toPlainText() == "()()"
    assert ed.textCursor().position() == 1


def test_bracket_matching_quotes(make_editor):
    """Pasangan kutip simetris juga ikut dipasangkan (dulu selalu gagal)."""
    ed = make_editor()
    ed.setPlainText('"abc"')
    set_cursor(ed, 4)  # kursor tepat pada penutup
    assert ed._bracket_pairs() == [(0, 4)]
    set_cursor(ed, 0)  # kursor tepat pada pembuka
    assert ed._bracket_pairs() == [(0, 4)]


# ------------------------------------------------------- tab stop
def test_tab_stop_jumps_out_parenthesis(make_editor):
    ed = make_editor(tab_width=4)
    press(ed, "(", Qt.Key.Key_ParenLeft)  # () kursor di 1
    press(ed, "x", Qt.Key.Key_X)          # (x) kursor di 2
    press(ed, "\t", Qt.Key.Key_Tab)
    assert ed.toPlainText() == "(x)"
    assert ed.textCursor().position() == 3  # melewati ')'


def test_tab_stop_jumps_out_quote(make_editor):
    ed = make_editor(tab_width=4)
    press(ed, '"', Qt.Key.Key_QuoteDbl)  # "" kursor di 1
    press(ed, "a", Qt.Key.Key_A)          # "a" kursor di 2
    press(ed, "\t", Qt.Key.Key_Tab)
    assert ed.toPlainText() == '"a"'
    assert ed.textCursor().position() == 3


def test_tab_stop_empty_pair_jumps_out(make_editor):
    """Tab langsung setelah auto-close (kursor di tengah pair kosong) ikut keluar."""
    ed = make_editor(tab_width=4)
    press(ed, "[", Qt.Key.Key_BracketLeft)
    press(ed, "\t", Qt.Key.Key_Tab)
    assert ed.toPlainText() == "[]"
    assert ed.textCursor().position() == 2


def test_tab_stop_not_on_stray_closer(make_editor):
    """Tab di depan ')' tanpa pasangan terbuka: tetap menyisipkan spasi."""
    ed = make_editor(tab_width=4)
    ed.setPlainText(")")
    set_cursor(ed, 0)
    press(ed, "\t", Qt.Key.Key_Tab)
    assert ed.toPlainText() == "    )"
    assert ed.textCursor().position() == 4


def test_tab_stop_with_selection_indents(make_editor):
    """Dengan seleksi, Tab tetap mengindentasi baris — bukan melompat keluar."""
    ed = make_editor(tab_width=4)
    ed.setPlainText("(ab)")
    ed.selectAll()
    press(ed, "\t", Qt.Key.Key_Tab)
    assert ed.toPlainText() == "    (ab)"


def test_quote_wraps_selection_near_closer(make_editor):
    """Seleksi aktif selalu dibungkus pasangan — skip hanya berlaku tanpa seleksi."""
    ed = make_editor()
    ed.setPlainText('"foo"')
    set_cursor(ed, 1)
    c = ed.textCursor()
    c.setPosition(4, QTextCursor.MoveMode.KeepAnchor)  # pilih "foo"
    ed.setTextCursor(c)
    press(ed, '"', Qt.Key.Key_QuoteDbl)
    assert ed.toPlainText() == '""foo""'


def test_tab_stop_not_before_opening_quote(make_editor):
    """Tab di depan KUTIP PEMBUKA (jumlah kutip sebelumnya genap) tidak melompat."""
    ed = make_editor(tab_width=4)
    ed.setPlainText('"a" "b"')
    set_cursor(ed, 4)  # tepat sebelum pembuka string kedua
    press(ed, "\t", Qt.Key.Key_Tab)
    assert ed.toPlainText() == '"a"     "b"'
    assert ed.textCursor().position() == 8


# ------------------------------------------------------- multi-kursor
CTRL = Qt.KeyboardModifier.ControlModifier


def ctrl_d(ed):
    press(ed, "", Qt.Key.Key_D, CTRL)


def test_ctrl_d_selects_word_under_cursor(make_editor):
    ed = make_editor()
    ed.setPlainText("foo bar baz")
    set_cursor(ed, 0)
    ctrl_d(ed)
    c = ed.textCursor()
    assert c.hasSelection()
    assert (c.selectionStart(), c.selectionEnd()) == (0, 3)


def test_ctrl_d_word_under_cursor_at_line_end(make_editor):
    ed = make_editor()
    ed.setPlainText("foo bar")
    set_cursor(ed, 3)  # tepat di akhir 'foo'
    ctrl_d(ed)
    c = ed.textCursor()
    assert (c.selectionStart(), c.selectionEnd()) == (0, 3)


def test_ctrl_d_adds_next_occurrence(make_editor):
    ed = make_editor()
    ed.setPlainText("foo bar foo baz foo")
    set_cursor(ed, 0)
    ctrl_d(ed)
    ctrl_d(ed)
    c = ed.textCursor()
    assert (c.selectionStart(), c.selectionEnd()) == (8, 11)
    assert ed._extra_cursors == [[0, 3]]


def test_ctrl_d_no_duplicate_when_wrapping(make_editor):
    ed = make_editor()
    ed.setPlainText("foo bar")
    set_cursor(ed, 0)
    for _ in range(3):
        ctrl_d(ed)
    c = ed.textCursor()
    assert (c.selectionStart(), c.selectionEnd()) == (0, 3)
    assert ed._extra_cursors == []


def test_ctrl_d_from_manual_selection(make_editor):
    ed = make_editor()
    ed.setPlainText("ab ab")
    set_cursor(ed, 0)
    c = ed.textCursor()
    c.setPosition(2, QTextCursor.MoveMode.KeepAnchor)
    ed.setTextCursor(c)
    ctrl_d(ed)
    c = ed.textCursor()
    assert (c.selectionStart(), c.selectionEnd()) == (3, 5)


def test_multi_cursor_typing_replaces_all(make_editor):
    ed = make_editor()
    ed.setPlainText("foo foo")
    set_cursor(ed, 0)
    ctrl_d(ed)
    ctrl_d(ed)
    press(ed, "x", Qt.Key.Key_X)
    assert ed.toPlainText() == "x x"
    assert not ed.textCursor().hasSelection()
    assert ed.cursor_count() == 2


def test_multi_cursor_backspace(make_editor):
    ed = make_editor()
    ed.setPlainText("foo foo")
    set_cursor(ed, 0)
    ctrl_d(ed)
    ctrl_d(ed)
    press(ed, "\b", Qt.Key.Key_Backspace)
    assert ed.toPlainText() == " "


def test_multi_cursor_pair_wraps_each_selection(make_editor):
    ed = make_editor()
    ed.setPlainText("foo foo")
    set_cursor(ed, 0)
    ctrl_d(ed)
    ctrl_d(ed)
    press(ed, "(", Qt.Key.Key_ParenLeft)
    assert ed.toPlainText() == "(foo) (foo)"
    assert not ed.textCursor().hasSelection()


def test_multi_cursor_escape_keeps_main_selection(make_editor):
    ed = make_editor()
    ed.setPlainText("foo foo")
    set_cursor(ed, 0)
    ctrl_d(ed)
    ctrl_d(ed)
    press(ed, "", Qt.Key.Key_Escape)
    assert ed._extra_cursors == []
    assert ed.textCursor().hasSelection()


def test_multi_cursor_arrow_exits_mode(make_editor):
    ed = make_editor()
    ed.setPlainText("foo foo")
    set_cursor(ed, 0)
    ctrl_d(ed)
    ctrl_d(ed)
    press(ed, "", Qt.Key.Key_Right)
    assert ed._extra_cursors == []


def test_ctrl_u_removes_last_cursor(make_editor):
    ed = make_editor()
    ed.setPlainText("foo foo foo")
    set_cursor(ed, 0)
    ctrl_d(ed)
    ctrl_d(ed)
    ctrl_d(ed)
    press(ed, "", Qt.Key.Key_U, CTRL)
    assert ed._extra_cursors == [[0, 3]]
    c = ed.textCursor()
    assert (c.selectionStart(), c.selectionEnd()) == (4, 7)


def test_multi_cursor_delete(make_editor):
    ed = make_editor()
    ed.setPlainText("foo foo")
    set_cursor(ed, 0)
    ctrl_d(ed)
    ctrl_d(ed)
    press(ed, "", Qt.Key.Key_Delete)
    assert ed.toPlainText() == " "


def test_multi_cursor_enter(make_editor):
    ed = make_editor()
    ed.setPlainText("foo foo")
    set_cursor(ed, 0)
    ctrl_d(ed)
    ctrl_d(ed)
    press(ed, "\r", Qt.Key.Key_Return)
    # spasi di tengah "foo foo" tetap tersisa
    assert ed.toPlainText() == "\n \n"


def test_ctrl_d_after_typing_drops_stale_cursors(make_editor):
    """Kursor ekstra kosong yang basi tidak boleh menyisipkan karakter ekstra."""
    ed = make_editor()
    ed.setPlainText("foo foo")
    set_cursor(ed, 0)
    ctrl_d(ed)
    ctrl_d(ed)
    press(ed, "x", Qt.Key.Key_X)       # kursor jadi kosong: "x x"
    ctrl_d(ed)                          # mulai urutan baru (seleksi kata)
    ctrl_d(ed)                          # tambah kemunculan berikutnya
    press(ed, "z", Qt.Key.Key_Z)
    assert ed.toPlainText() == "z z"
    assert ed.cursor_count() == 2


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
