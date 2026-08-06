"""Test integrasi aplikasi — window, tema, sesi, recent files, scan folder."""

import json

import pytest

import src.app as app_module
from src.app import OnyxPad


@pytest.fixture()
def app_window(qapp, monkeypatch, tmp_path):
    monkeypatch.setattr(app_module, "SETTINGS_DIR", tmp_path)
    monkeypatch.setattr(app_module, "SETTINGS_FILE", tmp_path / "settings.json")
    win = OnyxPad()
    yield win
    for ed in win.manager.all_editors():
        ed.document().setModified(False)
    win.close()


def patch_settings(monkeypatch, tmp_path):
    monkeypatch.setattr(app_module, "SETTINGS_DIR", tmp_path)
    monkeypatch.setattr(app_module, "SETTINGS_FILE", tmp_path / "settings.json")


# ----------------------------------------------------------------- window
def test_window_created(app_window):
    assert app_window.manager.active_editor() is not None
    assert len(app_window.manager._panes) == 1
    assert app_window._theme_name == "Dracula (Default)"


def test_new_tab_adds_editor(app_window):
    before = len(app_window.manager.all_editors())
    app_window.file_new_tab()
    assert len(app_window.manager.all_editors()) == before + 1


# ----------------------------------------------------------------- theme
def test_apply_theme(app_window):
    app_window.apply_theme("One Dark")
    assert app_window._theme_name == "One Dark"
    assert app_window.theme["name"] == "One Dark"
    for pane in app_window.manager._panes:
        for ed in pane.editors():
            assert ed._theme["name"] == "One Dark"
    for act in app_window._theme_actions:
        assert act.isChecked() == (act.text() == "One Dark")
    app_window.apply_theme("Dracula (Default)")


def test_apply_theme_invalid_name(app_window):
    app_window.apply_theme("Tidak Ada")
    assert app_window._theme_name == "Dracula (Default)"


# ---------------------------------------------------------------- status
def test_status_refresh(app_window):
    ed = app_window.manager.active_editor()
    ed.setPlainText("a b c")
    app_window._refresh_status()
    assert "3 kata" in app_window.sb_stats.text()
    assert app_window.sb_line.text().startswith("Ln 1")
    assert "Python" not in app_window.sb_lang.text()  # plain
    assert "%" in app_window.sb_lang.text()


def test_comment_action(app_window):
    ed = app_window.manager.active_editor()
    ed.set_language("python")
    ed.setPlainText("x = 1")
    app_window.toggle_comment()
    assert ed.toPlainText() == "#x = 1"
    app_window.toggle_comment()
    assert ed.toPlainText() == "x = 1"


# ---------------------------------------------------------------- session
def test_save_settings(app_window, tmp_path):
    app_window.file_new_tab()
    app_window._save_settings()
    data = json.loads((tmp_path / "settings.json").read_text(encoding="utf-8"))
    assert data["theme"] == "Dracula (Default)"
    assert "layout" in data
    assert data["font_size"] == app_window._font_size


def test_session_restore(qapp, monkeypatch, tmp_path):
    f = tmp_path / "halo.txt"
    f.write_text("konten sesi", encoding="utf-8")
    settings = {
        "theme": "Monokai",
        "layout": {"t": "p", "tabs": [str(f)], "act": 0},
    }
    (tmp_path / "settings.json").write_text(json.dumps(settings),
                                            encoding="utf-8")
    patch_settings(monkeypatch, tmp_path)
    win = OnyxPad()
    try:
        eds = win.manager.all_editors()
        assert len(eds) == 1
        assert eds[0].toPlainText() == "konten sesi"
        assert win._theme_name == "Monokai"
    finally:
        for ed in win.manager.all_editors():
            ed.document().setModified(False)
        win.close()


def test_session_restore_invalid_layout(qapp, monkeypatch, tmp_path):
    settings = {"layout": {"t": "junk"}}
    (tmp_path / "settings.json").write_text(json.dumps(settings),
                                            encoding="utf-8")
    patch_settings(monkeypatch, tmp_path)
    win = OnyxPad()
    try:
        # restore gagal → fallback ke pane kosong
        assert len(win.manager.all_editors()) == 1
    finally:
        for ed in win.manager.all_editors():
            ed.document().setModified(False)
        win.close()


# ------------------------------------------------------------------ open
def test_open_file_reuses_tab(qapp, monkeypatch, tmp_path):
    f = tmp_path / "test.txt"
    f.write_text("isi", encoding="utf-8")
    patch_settings(monkeypatch, tmp_path)
    win = OnyxPad()
    try:
        ed1 = win.open_file(str(f))
        assert ed1 is not None
        assert ed1.toPlainText() == "isi"
        count = len(win.manager.all_editors())
        ed2 = win.open_file(str(f))
        assert ed2 is ed1
        assert len(win.manager.all_editors()) == count
    finally:
        for ed in win.manager.all_editors():
            ed.document().setModified(False)
        win.close()


def test_open_file_new_pane(qapp, monkeypatch, tmp_path):
    f = tmp_path / "test.txt"
    f.write_text("isi", encoding="utf-8")
    patch_settings(monkeypatch, tmp_path)
    win = OnyxPad()
    try:
        win.open_file(str(f), new_pane=True)
        assert len(win.manager._panes) == 2
    finally:
        for ed in win.manager.all_editors():
            ed.document().setModified(False)
        win.close()


def test_open_missing_file_returns_none(qapp, monkeypatch, tmp_path):
    patch_settings(monkeypatch, tmp_path)
    win = OnyxPad()
    try:
        # path tidak ada → kembalikan None tanpa dialog
        assert win.open_file(str(tmp_path / "nope.txt")) is None
    finally:
        win.close()


# ---------------------------------------------------------------- recent
def test_recent_capped(app_window, tmp_path):
    for i in range(15):
        p = tmp_path / f"f{i}.txt"
        p.write_text("x", encoding="utf-8")
        app_window._add_recent(str(p))
    assert len(app_window._recent) <= app_module.MAX_RECENT
    assert app_window._recent[0] == str(tmp_path / "f14.txt")


def test_recent_dedupe_and_reorder(app_window, tmp_path):
    p = tmp_path / "f.txt"
    p.write_text("x", encoding="utf-8")
    q = tmp_path / "g.txt"
    q.write_text("x", encoding="utf-8")
    app_window._add_recent(str(p))
    app_window._add_recent(str(q))
    app_window._add_recent(str(p))
    assert app_window._recent.count(str(p)) == 1
    assert app_window._recent[0] == str(p)


# ------------------------------------------------------------- scan folder
def test_scan_folder_filters(tmp_path):
    (tmp_path / "a.py").write_text("", encoding="utf-8")
    (tmp_path / "b.txt").write_text("", encoding="utf-8")
    (tmp_path / "c.bin").write_text("", encoding="utf-8")
    (tmp_path / "node_modules").mkdir()
    (tmp_path / "node_modules" / "x.js").write_text("", encoding="utf-8")
    (tmp_path / ".hidden").mkdir()
    (tmp_path / ".hidden" / "y.py").write_text("", encoding="utf-8")
    (tmp_path / "__pycache__").mkdir()
    (tmp_path / "__pycache__" / "z.pyc").write_text("", encoding="utf-8")

    files = app_module.OnyxPad._scan_folder(str(tmp_path))
    names = [p.replace("\\", "/") for p in files]
    assert "a.py" in names
    assert "b.txt" in names
    assert not any(n.endswith("c.bin") for n in names)
    assert not any("node_modules" in n for n in names)
    assert not any(".hidden" in n for n in names)
    assert not any("__pycache__" in n for n in names)


# ------------------------------------------------------------------ wrap
def test_toggle_wrap(app_window):
    from PySide6.QtWidgets import QPlainTextEdit
    ed = app_window.manager.active_editor()
    before = app_window._wrap
    app_window.toggle_wrap()
    assert app_window._wrap is not before
    mode = ed.lineWrapMode()
    assert mode == (QPlainTextEdit.LineWrapMode.WidgetWidth
                    if app_window._wrap
                    else QPlainTextEdit.LineWrapMode.NoWrap)
    app_window.toggle_wrap()


def test_zoom_actions(app_window):
    ed = app_window.manager.active_editor()
    app_window._zoom(1)
    assert ed.zoom_level() >= 0
    app_window._zoom_reset()
    assert ed.font().pointSize() == app_window._font_size


# --------------------------------------------------------------- help
def test_help_menu_has_repo_author_and_update(app_window):
    """Menu Bantuan memuat tautan repo/author dan item cek pembaruan."""
    texts = []
    for act in app_window.menuBar().actions():
        menu = act.menu()
        if menu is not None:
            for a in menu.actions():
                texts.append(a.text())
    assert "Repositori GitHub" in texts
    assert "Author: jpXCode" in texts
    assert "Cek Pembaruan…" in texts


def test_show_about_mentions_repo_and_author(app_window, monkeypatch):
    """Dialog Tentang memuat versi, URL repo, dan nama author."""
    captured = {}

    def fake_about(parent, title, text):
        captured["title"] = title
        captured["text"] = text

    monkeypatch.setattr(app_module.QMessageBox, "about",
                        staticmethod(fake_about))
    app_window.show_about()
    assert "Tentang" in captured["title"]
    assert "github.com" in captured["text"]
    assert "jpXCode" in captured["text"]


def test_help_menu_opens_repo_url(app_window, monkeypatch):
    """Item 'Repositori GitHub' membuka URL repo (tanpa browser asli)."""
    opened = []
    monkeypatch.setattr(app_module, "QDesktopServices",
                        type("Fake", (object,), {
                            "openUrl": staticmethod(
                                lambda url: opened.append(url.toString()))}))
    for act in app_window.menuBar().actions():
        menu = act.menu()
        if menu is not None and act.text() == "Bantuan":
            for a in menu.actions():
                if a.text() == "Repositori GitHub":
                    a.trigger()
    assert opened and "github.com" in opened[0]
