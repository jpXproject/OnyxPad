"""Test untuk pencarian & penggantian — literal, case, kata utuh, regex."""

from PySide6.QtGui import QTextCursor, QTextDocument


def F():
    """Flags kosong — dipanggil langsung agar quirk PySide6 tidak aktif."""
    return QTextDocument.FindFlags()


CASE = QTextDocument.FindFlag.FindCaseSensitively
WORD = QTextDocument.FindFlag.FindWholeWords


def make_bar(theme, editor):
    from src.search import SearchBar
    bar = SearchBar(theme)
    bar.set_editor_getter(lambda: editor)
    return bar


# ------------------------------------------------------------------ find
def test_find_next_literal(make_editor):
    ed = make_editor()
    ed.setPlainText("hello world\nhello again")
    assert ed.find_next("hello", F()) is True
    assert ed.textCursor().selectedText() == "hello"


def test_find_prev(make_editor):
    ed = make_editor()
    ed.setPlainText("hello hello")
    assert ed.find_next("hello", F()) is True
    assert ed.find_next("hello", F()) is True
    assert ed.find_prev("hello", F()) is True


def test_case_sensitivity(make_editor):
    ed = make_editor()
    ed.setPlainText("Hello")
    # default case-insensitive
    assert ed.find_next("hello", F()) is True
    ed.moveCursor(QTextCursor.MoveOperation.Start)
    # case-sensitive → tidak cocok dengan "Hello"
    assert ed.find_next("hello", CASE) is False


def test_whole_word(make_editor):
    ed = make_editor()
    ed.setPlainText("the then")
    ed.moveCursor(QTextCursor.MoveOperation.Start)
    assert ed.find_next("the", WORD) is True
    # "the" di dalam "then" bukan kata utuh
    assert ed.find_next("the", WORD) is False


def test_regex_find(make_editor):
    ed = make_editor()
    ed.setPlainText("foo 123 bar 456")
    assert ed.find_next(r"\d+", F(), use_regex=True) is True
    assert ed.textCursor().selectedText() == "123"


def test_invalid_regex_is_safe(make_editor):
    ed = make_editor()
    ed.setPlainText("abc")
    assert ed.find_next("(", F(), use_regex=True) is False
    assert ed.count_matches("(", F(), True) == 0
    assert ed.replace_all("(", "X", F(), True) == 0


def test_count_matches(make_editor):
    ed = make_editor()
    ed.setPlainText("cat dog cat")
    assert ed.count_matches("cat", F()) == 2


def test_count_matches_empty(make_editor):
    ed = make_editor()
    ed.setPlainText("abc")
    assert ed.count_matches("", F()) == 0


def test_collect_matches(make_editor):
    ed = make_editor()
    ed.setPlainText("x y x")
    ed.set_search_matches("x", F())
    assert ed._collect_matches() == [(0, 1), (4, 5)]


def test_collect_matches_regex(make_editor):
    ed = make_editor()
    ed.setPlainText("a1 a22")
    ed.set_search_matches(r"\d+", F(), use_regex=True)
    assert ed._collect_matches() == [(1, 2), (4, 6)]


# --------------------------------------------------------------- replace
def test_replace_current(make_editor):
    ed = make_editor()
    ed.setPlainText("a bb a")
    assert ed.find_next("bb", F()) is True
    assert ed.replace_current("bb", "X", F()) is True
    assert ed.toPlainText() == "a X a"


def test_replace_current_without_selection(make_editor):
    ed = make_editor()
    ed.setPlainText("abc")
    assert ed.replace_current("abc", "X", F()) is False


def test_replace_current_regex(make_editor):
    ed = make_editor()
    ed.setPlainText("foo 42 bar")
    assert ed.find_next(r"\d+", F(), use_regex=True) is True
    assert ed.replace_current(r"\d+", "0", F(), use_regex=True) is True
    assert ed.toPlainText() == "foo 0 bar"


def test_replace_all_literal(make_editor):
    ed = make_editor()
    ed.setPlainText("aa ab aa")
    n = ed.replace_all("aa", "z", F())
    assert n == 2
    assert ed.toPlainText() == "z ab z"


def test_replace_all_regex(make_editor):
    ed = make_editor()
    ed.setPlainText("a1 b2 a3")
    n = ed.replace_all(r"\d", "#", F(), use_regex=True)
    assert n == 3
    assert ed.toPlainText() == "a# b# a#"


# ------------------------------------------------------------- search bar
def test_search_bar_find(qapp, theme, make_editor):
    ed = make_editor()
    ed.setPlainText("one two one")
    bar = make_bar(theme, ed)
    bar.find_edit.setText("one")
    bar._do_find(True)
    assert ed.textCursor().selectedText() == "one"
    bar._do_find(True)
    assert ed.textCursor().selectedText() == "one"  # wrap ke awal
    bar._update_count()
    assert bar.count_label.text() == "2 cocok"
    bar.deleteLater()


def test_search_bar_regex_count(qapp, theme, make_editor):
    ed = make_editor()
    ed.setPlainText("a1 a22 a333")
    bar = make_bar(theme, ed)
    bar.find_edit.setText(r"\d+")
    bar.regex_box.setChecked(True)
    bar._update_count()
    assert bar.count_label.text() == "3 cocok"
    bar.deleteLater()


def test_search_bar_invalid_regex_message(qapp, theme, make_editor):
    ed = make_editor()
    ed.setPlainText("abc")
    bar = make_bar(theme, ed)
    bar.find_edit.setText("(")
    bar.regex_box.setChecked(True)
    bar._update_count()
    assert "salah" in bar.count_label.text()
    bar.deleteLater()


def test_search_bar_replace_all(qapp, theme, make_editor):
    ed = make_editor()
    ed.setPlainText("x1 x2")
    bar = make_bar(theme, ed)
    bar.find_edit.setText(r"\d")
    bar.replace_edit.setText("0")
    bar.regex_box.setChecked(True)
    # hindari dialog modal: panggil editor langsung
    n = ed.replace_all(r"\d", "0", F(), use_regex=True)
    assert n == 2
    assert ed.toPlainText() == "x0 x0"
    bar.deleteLater()
