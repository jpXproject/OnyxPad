"""Sidebar penjelajah folder (file explorer) — buka file dengan klik dua kali."""

import os
import shutil
import subprocess

from PySide6.QtCore import QDir, Qt, Signal
from PySide6.QtWidgets import (QFileSystemModel, QInputDialog, QMenu,
                               QMessageBox, QTreeView, QVBoxLayout, QWidget)


class FileTree(QWidget):
    file_activated   = Signal(str)   # path dibuka di pane aktif
    open_in_new_pane = Signal(str)   # path dibuka di pane baru
    file_renamed     = Signal(str, str)  # (path_lama, path_baru)
    file_deleted     = Signal(str)   # path yang dihapus

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
        for col in range(1, 4):
            self.tree.setColumnHidden(col, True)
        self.tree.setIndentation(14)
        self.tree.setAnimated(True)
        self.tree.setUniformRowHeights(True)
        self.tree.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.tree.doubleClicked.connect(self._on_item_activated)
        self.tree.activated.connect(self._on_item_activated)
        self.tree.customContextMenuRequested.connect(self._on_context_menu)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.tree)

    # ---------------------------------------------------------------- public
    def set_root(self, path):
        self._root_path = path
        self.model.setRootPath(path)
        self.tree.setRootIndex(self.model.index(path))
        self.tree.expandToDepth(0)

    def root_path(self):
        return self._root_path

    # ---------------------------------------------------------------- private
    def _path_at(self, index):
        if index is None or not index.isValid():
            return None
        return self.model.filePath(index)

    def _on_item_activated(self, index):
        if not index or not index.isValid():
            return
        if not self.model.isDir(index):
            path = self.model.filePath(index)
            if path and os.path.isfile(path):
                self.file_activated.emit(path)

    def _on_context_menu(self, pos):
        index = self.tree.indexAt(pos)
        path  = self._path_at(index)

        # Tentukan apakah klik di item atau di area kosong
        is_dir  = path and self.model.isDir(index)
        is_file = path and not is_dir

        menu = QMenu(self)

        # --- Aksi untuk FILE ---
        a_open = a_pane = None
        if is_file:
            a_open = menu.addAction("📄  Buka")
            a_pane = menu.addAction("➕  Buka di Pane Baru")
            menu.addSeparator()

        # --- Aksi untuk FILE dan FOLDER ---
        a_rename = a_delete = None
        if path:
            a_rename = menu.addAction("✏️  Rename")
            a_delete = menu.addAction("🗑️  Hapus")
            menu.addSeparator()

        # --- Aksi NEW (selalu tersedia) ---
        # Tentukan folder target: jika klik folder pakai itu, else pakai parent
        if is_dir:
            target_dir = path
        elif is_file:
            target_dir = os.path.dirname(path)
        else:
            target_dir = self._root_path  # klik area kosong

        a_new_file   = menu.addAction("📝  File Baru")
        a_new_folder = menu.addAction("📁  Folder Baru")

        # --- Buka di Explorer ---
        if path:
            menu.addSeparator()
            a_reveal = menu.addAction("🔍  Tampilkan di Explorer")
        else:
            a_reveal = None

        chosen = menu.exec(self.tree.viewport().mapToGlobal(pos))
        if chosen is None:
            return

        if chosen is a_open and is_file:
            self.file_activated.emit(path)
        elif chosen is a_pane and is_file:
            self.open_in_new_pane.emit(path)
        elif chosen is a_rename and path:
            self._do_rename(path)
        elif chosen is a_delete and path:
            self._do_delete(path, is_dir)
        elif chosen is a_new_file and target_dir:
            self._do_new_file(target_dir)
        elif chosen is a_new_folder and target_dir:
            self._do_new_folder(target_dir)
        elif chosen is a_reveal and path:
            _reveal(path)

    # ---------------------------------------------------------------- actions
    def _do_rename(self, path):
        old_name = os.path.basename(path)
        new_name, ok = QInputDialog.getText(
            self, "Rename", "Nama baru:", text=old_name)
        if not ok or not new_name.strip() or new_name == old_name:
            return
        new_name = new_name.strip()
        new_path = os.path.join(os.path.dirname(path), new_name)
        if os.path.exists(new_path):
            QMessageBox.warning(self, "Rename Gagal",
                                f"Nama '{new_name}' sudah ada.")
            return
        try:
            os.rename(path, new_path)
            self.file_renamed.emit(path, new_path)
        except OSError as e:
            QMessageBox.warning(self, "Rename Gagal", str(e))

    def _do_delete(self, path, is_dir):
        name = os.path.basename(path)
        tipe = "folder beserta isinya" if is_dir else "file"
        reply = QMessageBox.question(
            self, "Konfirmasi Hapus",
            f"Hapus {tipe}:\n\n  {name}\n\nTindakan ini tidak bisa dibatalkan.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No)
        if reply != QMessageBox.StandardButton.Yes:
            return
        try:
            if is_dir:
                shutil.rmtree(path)
            else:
                os.remove(path)
            self.file_deleted.emit(path)
        except OSError as e:
            QMessageBox.warning(self, "Hapus Gagal", str(e))

    def _do_new_file(self, target_dir):
        name, ok = QInputDialog.getText(
            self, "File Baru", "Nama file baru:", text="untitled.txt")
        if not ok or not name.strip():
            return
        new_path = os.path.join(target_dir, name.strip())
        if os.path.exists(new_path):
            QMessageBox.warning(self, "File Baru Gagal",
                                f"'{name}' sudah ada.")
            return
        try:
            open(new_path, "w", encoding="utf-8").close()
            # Langsung buka file baru di editor
            self.file_activated.emit(new_path)
            # Pilih & scroll ke item baru di tree
            idx = self.model.index(new_path)
            self.tree.setCurrentIndex(idx)
            self.tree.scrollTo(idx)
        except OSError as e:
            QMessageBox.warning(self, "File Baru Gagal", str(e))

    def _do_new_folder(self, target_dir):
        name, ok = QInputDialog.getText(
            self, "Folder Baru", "Nama folder baru:", text="folder_baru")
        if not ok or not name.strip():
            return
        new_path = os.path.join(target_dir, name.strip())
        if os.path.exists(new_path):
            QMessageBox.warning(self, "Folder Baru Gagal",
                                f"'{name}' sudah ada.")
            return
        try:
            os.makedirs(new_path)
            idx = self.model.index(new_path)
            self.tree.setCurrentIndex(idx)
            self.tree.expand(self.model.index(target_dir))
            self.tree.scrollTo(idx)
        except OSError as e:
            QMessageBox.warning(self, "Folder Baru Gagal", str(e))

    def apply_theme(self, theme):
        self._theme = theme


# ------------------------------------------------------------------ helper
def _reveal(path):
    """Buka folder / select file di Windows Explorer."""
    try:
        if os.path.isdir(path):
            subprocess.Popen(["explorer", os.path.normpath(path)])
        else:
            subprocess.Popen(["explorer", "/select,", os.path.normpath(path)])
    except OSError:
        pass
