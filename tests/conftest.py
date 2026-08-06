"""Fixtures bersama untuk semua test — Qt berjalan mode offscreen."""

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest


@pytest.fixture(scope="session")
def qapp():
    from PySide6.QtWidgets import QApplication
    app = QApplication.instance() or QApplication([])
    yield app


@pytest.fixture()
def theme():
    from src.themes import THEMES, THEME_ORDER
    return THEMES[THEME_ORDER[0]]


@pytest.fixture()
def make_editor(qapp, theme):
    from src.editor import CodeEditor
    created = []

    def factory(language="plain", **kwargs):
        ed = CodeEditor(theme, language=language, **kwargs)
        created.append(ed)
        return ed

    yield factory
    for ed in created:
        ed.deleteLater()
