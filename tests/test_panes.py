"""Test untuk sistem split panes — split, navigasi, close, serialize."""

import pytest
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QSplitter

from src.editor import CodeEditor
from src.panes import SplitManager
from src.themes import THEMES, THEME_ORDER


@pytest.fixture()
def manager(qapp):
    theme = THEMES[THEME_ORDER[0]]

    def make_editor():
        return CodeEditor(theme, language="plain")

    m = SplitManager(theme, make_editor=make_editor,
                     save_editor=lambda ed: True)
    yield m
    m.deleteLater()


# ---------------------------------------------------------------- basics
def test_ensure_first_pane(manager):
    manager.ensure_first_pane()
    assert len(manager._panes) == 1
    assert manager.active_editor() is not None
    assert manager.active_pane() is manager._panes[0]


def test_new_pane_adds_editor(manager):
    manager.ensure_first_pane()
    assert len(manager.all_editors()) == 1
    manager.new_pane()
    assert len(manager.all_editors()) == 2


# ----------------------------------------------------------------- split
def test_split_right_horizontal(manager):
    manager.ensure_first_pane()
    manager.split_right()
    assert len(manager._panes) == 2
    assert manager.root.orientation() == Qt.Orientation.Horizontal


def test_split_below_vertical(manager):
    manager.ensure_first_pane()
    manager.split_below()
    assert len(manager._panes) == 2
    # root tetap horizontal; anaknya berupa pembungkus vertikal (split bertingkat)
    assert manager.root.count() == 1
    wrapper = manager.root.widget(0)
    assert isinstance(wrapper, QSplitter)
    assert wrapper.orientation() == Qt.Orientation.Vertical


def test_nested_split_wraps(manager):
    manager.ensure_first_pane()
    manager.split_right()
    manager.next_pane()
    manager.split_below()
    assert len(manager._panes) == 3
    # root punya satu anak berupa splitter pembungkus
    root_children = [manager.root.widget(i) for i in range(manager.root.count())]
    assert any(isinstance(w, QSplitter) for w in root_children)


# ------------------------------------------------------------ navigation
def test_next_prev_cycle(manager):
    manager.ensure_first_pane()
    manager.split_right()
    first = manager.active_pane()
    manager.next_pane()
    second = manager.active_pane()
    assert second is not first
    manager.next_pane()
    assert manager.active_pane() is first
    manager.prev_pane()
    assert manager.active_pane() is second


def test_pane_in_direction(qapp, manager):
    manager.resize(800, 600)
    manager.show()
    manager.ensure_first_pane()
    left = manager.active_pane()
    manager.split_right()
    right = manager.active_pane()
    assert right is not left
    qapp.processEvents()

    manager._set_active(left)
    assert manager.pane_in_direction(1, 0) is right
    manager._set_active(left)
    assert manager.pane_in_direction(-1, 0) is None
    manager.hide()


# ----------------------------------------------------------------- close
def test_close_active_pane(qapp, manager):
    manager.ensure_first_pane()
    manager.split_right()
    manager.next_pane()
    manager.close_pane()
    qapp.processEvents()  # jalankan pembersihan yang dijadwalkan QTimer
    assert len(manager._panes) == 1


def test_close_all_panes(qapp, manager):
    manager.ensure_first_pane()
    manager.close_pane()
    qapp.processEvents()
    assert manager._panes == []
    # app menciptakan ulang pane jika kosong
    manager.ensure_first_pane()
    qapp.processEvents()
    assert len(manager._panes) == 1


# -------------------------------------------------------------- serialize
def test_serialize_roundtrip(qapp, manager, tmp_path):
    p1 = tmp_path / "a.py"
    p1.write_text("print(1)", encoding="utf-8")
    p2 = tmp_path / "b.py"
    p2.write_text("print(2)", encoding="utf-8")

    manager.ensure_first_pane()
    manager.active_editor().load(str(p1))
    manager.split_right()
    manager.active_editor().load(str(p2))

    node = manager.serialize()
    assert node["t"] == "s"
    assert node["o"] == "h"

    # pulihkan ke manager baru
    theme = THEMES[THEME_ORDER[0]]

    def make_editor():
        return CodeEditor(theme, language="plain")

    m2 = SplitManager(theme, make_editor=make_editor,
                      save_editor=lambda ed: True)
    assert m2.restore(node) is True
    qapp.processEvents()

    paths = sorted(ed.file_path() for p in m2._panes
                   for ed in p.editors())
    assert paths == [str(p1), str(p2)]

    contents = {ed.file_path(): ed.toPlainText()
                for p in m2._panes for ed in p.editors()}
    assert contents[str(p1)] == "print(1)"
    assert contents[str(p2)] == "print(2)"
    m2.deleteLater()


def test_serialize_single_pane(manager):
    manager.ensure_first_pane()
    node = manager.serialize()
    # akar selalu splitter; satu pane menjadi anaknya
    assert node["t"] == "s"
    assert len(node["c"]) == 1
    assert node["c"][0]["t"] == "p"
    assert node["c"][0]["tabs"] == [None]
