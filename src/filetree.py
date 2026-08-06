"""Sidebar penjelajah folder (file explorer) — buka file dengan klik dua kali."""

from PySide6.QtCore import QDir, Qt, Signal
from PySide6.QtWidgets import (QFileSystemModel, QMenu, QTreeView, QVBoxLayout,
                               QWidget)


class FileTree(QWidget):
    file_activated = Signal(str)          # path dibuka di pane aktif
    open_in_new_pane = Signal(str)        # path dibuka di pane baru

    def __init__(self, theme, parent=None):
        super().__init__(parent)
        self._theme = theme
        self._root_path = None

        self.model = QFileSystemModel(self)
        self.model.setFilter(
            QDir.Filter.AllEntries | QDir.Filter.NoDotAndDotDot |
            QDir.Filter.AllDirs)

        self.tree = QTreeView(self)
        self.tree.setModel(self.model)
        self.tree.setHeaderHidden(True)
        self.tree.setAnimated(True)
        self.tree.setUniformRowHeights(True)
        self.tree.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.tree.doubleClicked.connect(self._on_double_click)
        self.tree.customContextMenuRequested.connect(self._on_context_menu)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.tree)

    def set_root(self, path):
        self._root_path = path
        self.model.setRootPath(path)
        self.tree.setRootIndex(self.model.index(path))
        self.tree.expandToDepth(0)

    def root_path(self):
        return self._root_path

    def _path_at(self, index):
        if index is None or not index.isValid():
            return None
        return self.model.filePath(index)

    def _on_double_click(self, index):
        if not self.model.isDir(index):
            path = self.model.filePath(index)
            if path:
                self.file_activated.emit(path)

    def _on_context_menu(self, pos):
        index = self.tree.indexAt(pos)
        path = self._path_at(index)
        if not path:
            return
        menu = QMenu(self)
        if not self.model.isDir(index):
            a_open = menu.addAction("Buka")
            a_pane = menu.addAction("Buka di Pane Baru")
            menu.addSeparator()
        a_expand = menu.addAction("Buka Folder Ini di Explorer")
        chosen = menu.exec(self.tree.viewport().mapToGlobal(pos))
        if chosen is a_open:
            self.file_activated.emit(path)
        elif chosen is a_pane:
            self.open_in_new_pane.emit(path)
        elif chosen is a_expand:
            _reveal(path)

    def apply_theme(self, theme):
        self._theme = theme


def _reveal(path):
    """Buka folder/select file di Windows Explorer."""
    import subprocess
    import os
    try:
        if os.path.isdir(path):
            subprocess.Popen(["explorer", os.path.normpath(path)])
        else:
            subprocess.Popen(["explorer", "/select,", os.path.normpath(path)])
    except OSError:
        pass
