"""Sistem split panes bertingkat (gaya tmux / VS Code).

Struktur: pohon QSplitter — setiap node adalah QSplitter (horizontal/vertikal)
atau Pane (QTabWidget berisi beberapa editor). Split dilakukan dengan menyisipkan
pane ke splitter terdekat, atau membungkus pane dalam splitter baru bila orientasi
berbeda (memungkinkan split di dalam split).
"""

from PySide6.QtCore import Qt, QMimeData, QPoint, Signal, QTimer
from PySide6.QtGui import QDrag
from PySide6.QtWidgets import (QMessageBox, QSplitter, QTabBar, QTabWidget,
                               QVBoxLayout, QWidget)


# ID unik untuk drag-drop antar pane
_DRAG_MIME = "application/x-onyxpad-editor"

# Referensi global sementara saat drag berlangsung
_drag_source_pane   = None
_drag_source_editor = None


class Pane(QTabWidget):
    """Satu wilayah layar berisi beberapa tab editor."""

    focused = Signal()
    empty   = Signal()

    def __init__(self, theme, save_editor=None, parent=None):
        super().__init__(parent)
        self._theme = theme
        self._save_editor = save_editor or (lambda ed: True)
        self._editors = []
        self.setDocumentMode(True)
        self.setMovable(True)
        self.setTabsClosable(True)
        self.setUsesScrollButtons(True)
        self.tabCloseRequested.connect(self.close_tab_at)
        self.currentChanged.connect(lambda _idx: self.focused.emit())

        # Aktifkan drag-drop pada tab bar
        self.tabBar().setAcceptDrops(True)
        self.tabBar().installEventFilter(self)
        self.setAcceptDrops(True)

    # --------------------------------------------------------- drag & drop
    def mousePressEvent(self, event):
        # Deteksi klik di tab bar untuk memulai drag
        if event.button() == Qt.MouseButton.LeftButton:
            tab_idx = self.tabBar().tabAt(event.position().toPoint())
            if tab_idx >= 0:
                self._drag_start_tab = tab_idx
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if (event.buttons() & Qt.MouseButton.LeftButton and
                hasattr(self, '_drag_start_tab') and
                self._drag_start_tab >= 0):
            editor = self.widget(self._drag_start_tab)
            if editor is not None:
                self._start_tab_drag(editor)
        super().mouseMoveEvent(event)

    def _start_tab_drag(self, editor):
        global _drag_source_pane, _drag_source_editor
        _drag_source_pane   = self
        _drag_source_editor = editor

        mime = QMimeData()
        mime.setData(_DRAG_MIME, b"1")

        drag = QDrag(self)
        drag.setMimeData(mime)
        drag.exec(Qt.DropAction.MoveAction)
        self._drag_start_tab = -1

    def dragEnterEvent(self, event):
        if event.mimeData().hasFormat(_DRAG_MIME):
            event.acceptProposedAction()

    def dragMoveEvent(self, event):
        if event.mimeData().hasFormat(_DRAG_MIME):
            event.acceptProposedAction()

    def dropEvent(self, event):
        global _drag_source_pane, _drag_source_editor
        if not event.mimeData().hasFormat(_DRAG_MIME):
            return
        src_pane   = _drag_source_pane
        src_editor = _drag_source_editor
        _drag_source_pane   = None
        _drag_source_editor = None

        if src_editor is None or src_pane is self:
            event.ignore()
            return

        # Pindahkan editor dari pane asal ke pane ini
        src_pane.detach_editor(src_editor)
        self.add_editor(src_editor)
        event.acceptProposedAction()

    # --------------------------------------------------------- detach
    def detach_editor(self, editor):
        """Lepas editor dari pane ini tanpa menutupnya."""
        idx = self.indexOf(editor)
        if idx == -1:
            return
        self.removeTab(idx)
        if editor in self._editors:
            self._editors.remove(editor)
        editor.setParent(None)
        if self.count() == 0:
            self.empty.emit()

    # ------------------------------------------------------------ editors
    def add_editor(self, editor):
        editor.focused.connect(self._on_child_focus)
        self._editors.append(editor)
        index = self.addTab(editor, editor.display_name())
        self.setCurrentIndex(index)
        editor.document().modificationChanged.connect(
            lambda _m, ed=editor: self._update_tab_title(ed))
        editor.textChanged.connect(
            lambda ed=editor: self._update_tab_title(ed))
        self._update_tab_title(editor)
        editor.setFocus()
        self.focused.emit()
        return editor

    def _update_tab_title(self, editor):
        idx = self.indexOf(editor)
        if idx == -1:
            return
        name = editor.display_name()
        modified = editor.document().isModified()
        if modified:
            name = "● " + name
        self.setTabText(idx, name)
        self._update_tab_tooltip(editor, idx)

    def _refresh_tab_title(self, editor):
        """Dipanggil dari luar (misal setelah rename/delete dari filetree)."""
        self._update_tab_title(editor)

    def _update_tab_tooltip(self, editor, idx):
        """Tooltip tab: path lengkap + statistik file."""
        import os
        path = editor.file_path() or "(belum disimpan)"
        words, chars = editor.stats()
        lines = editor.document().blockCount()
        enc   = editor.set_encoding_name()
        modified_str = " [belum disimpan]" if editor.document().isModified() else ""
        tip = (
            f"{path}{modified_str}\n"
            f"────────────────────\n"
            f"Baris   : {lines:,}\n"
            f"Kata    : {words:,}\n"
            f"Karakter: {chars:,}\n"
            f"Encoding: {enc}"
        )
        self.setTabToolTip(idx, tip)

    def _on_child_focus(self):
        self.focused.emit()

    def current_editor(self):
        return self.currentWidget()

    def editors(self):
        return list(self._editors)

    def any_modified(self):
        return any(ed.document().isModified() for ed in self._editors)

    # ------------------------------------------------------------- close
    def close_tab_at(self, index):
        """Tutup tab; kembalikan False bila dibatalkan pengguna."""
        editor = self.widget(index)
        if editor is None:
            return False
        if editor.document().isModified():
            box = QMessageBox()
            box.setWindowTitle("Perubahan Belum Disimpan")
            box.setIcon(QMessageBox.Icon.Warning)
            box.setText(f"Simpan perubahan pada '{editor.display_name()}'?")
            save = box.addButton("Simpan", QMessageBox.ButtonRole.AcceptRole)
            discard = box.addButton("Jangan Simpan",
                                    QMessageBox.ButtonRole.DestructiveRole)
            cancel = box.addButton("Batal", QMessageBox.ButtonRole.RejectRole)
            box.setDefaultButton(save)
            box.exec()
            clicked = box.clickedButton()
            if clicked is cancel:
                return False
            if clicked is save and not self._save_editor(editor):
                return False
        self._remove_editor_at(index)
        return True

    def _remove_editor_at(self, index):
        editor = self.widget(index)
        if editor in self._editors:
            self._editors.remove(editor)
        self.removeTab(index)
        editor.deleteLater()
        if self.count() == 0:
            self.empty.emit()

    def apply_theme(self, theme):
        self._theme = theme
        for ed in self._editors:
            ed.apply_theme(theme)


class SplitManager(QWidget):
    """Pohon splitter + pane; pemilik semua editor."""

    def __init__(self, theme, make_editor, save_editor, parent=None):
        super().__init__(parent)
        self._theme = theme
        self._make_editor = make_editor      # callable() -> CodeEditor
        self._save_editor = save_editor      # callable(editor) -> bool
        self._panes = []
        self._active = None

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        self.root = QSplitter(Qt.Orientation.Horizontal)
        self.root.setChildrenCollapsible(False)
        self.root.setHandleWidth(5)
        layout.addWidget(self.root)

    # ---------------------------------------------------------- factories
    def _make_pane(self):
        pane = Pane(self._theme, save_editor=self._save_editor)
        pane.focused.connect(lambda p=pane: self._set_active(p))
        pane.empty.connect(lambda p=pane: self.close_pane(p))
        pane.apply_theme(self._theme)
        return pane

    def _register(self, pane):
        if pane not in self._panes:
            self._panes.append(pane)
        self._set_active(pane)

    def _set_active(self, pane):
        self._active = pane

    # ------------------------------------------------------------- basics
    def active_pane(self):
        if self._active in self._panes:
            return self._active
        return self._panes[-1] if self._panes else None

    def active_editor(self):
        pane = self.active_pane()
        return pane.current_editor() if pane else None

    def all_editors(self):
        return [ed for p in self._panes for ed in p.editors()]

    def ensure_first_pane(self):
        if not self._panes:
            self.new_pane()

    def new_pane(self, editor=None):
        """Pane baru di samping kanan pane aktif (atau pane pertama)."""
        pane = self._make_pane()
        if editor is None:
            editor = self._make_editor()
        pane.add_editor(editor)
        anchor = self.active_pane()
        if anchor is not None:
            self.split_insert(pane, anchor, Qt.Orientation.Horizontal)
        else:
            self.root.addWidget(pane)
        self._register(pane)
        return pane

    def _parent_splitter(self, widget):
        w = widget
        while w is not None:
            p = w.parentWidget()
            if isinstance(p, QSplitter):
                return p
            w = p
        return self.root

    # -------------------------------------------------------------- split
    def split_right(self):
        return self.split(Qt.Orientation.Horizontal)

    def split_below(self):
        return self.split(Qt.Orientation.Vertical)

    def split(self, orientation):
        """Split pane aktif: Horizontal = ke kanan, Vertical = ke bawah."""
        pane = self.active_pane()
        if pane is None:
            return self.new_pane()
        new_pane = self._make_pane()
        editor = self._make_editor()
        new_pane.add_editor(editor)
        self.split_insert(new_pane, pane, orientation)
        self._register(new_pane)
        return new_pane

    def split_insert(self, new_pane, anchor, orientation):
        """Letakkan new_pane di samping anchor sesuai orientasi."""
        parent = self._parent_splitter(anchor)
        if parent.orientation() == orientation:
            idx = parent.indexOf(anchor)
            parent.insertWidget(idx + 1, new_pane)
        else:
            sizes = parent.sizes()
            idx = parent.indexOf(anchor)
            size = sizes[idx] if idx < len(sizes) else 400
            wrapper = QSplitter(orientation)
            wrapper.setChildrenCollapsible(False)
            wrapper.setHandleWidth(5)
            # catatan: pakai insertWidget, bukan replaceWidget — replaceWidget
            # tidak mengalihkan kepemilikan ke C++ sehingga widget bisa terhapus
            # saat referensi Python-nya hilang (bug PySide6/shiboken).
            parent.insertWidget(idx, wrapper)
            wrapper.addWidget(anchor)
            wrapper.addWidget(new_pane)
            parent.setSizes(sizes)
            half = max(60, size // 2)
            wrapper.setSizes([half, size - half])

    # -------------------------------------------------------------- close
    def close_pane(self, pane=None):
        pane = pane or self.active_pane()
        if pane is None or pane not in self._panes:
            return
        while pane.count() > 0:
            before = pane.count()
            ok = pane.close_tab_at(pane.currentIndex())
            if not ok or pane.count() == before:
                return
        self._remove_pane_widget(pane)

    def _remove_pane_widget(self, pane):
        if pane not in self._panes:
            return
        self._panes.remove(pane)
        if self._active is pane:
            self._active = self._panes[-1] if self._panes else None
        parent = self._parent_splitter(pane)
        pane.hide()
        pane.deleteLater()
        QTimer.singleShot(0, lambda: self._cleanup(parent))

    def _cleanup(self, splitter):
        if splitter is None:
            return
        if splitter.count() == 0:
            # jangan hapus splitter akar — biarkan kosong agar bisa diisi lagi
            if isinstance(splitter.parentWidget(), QSplitter):
                splitter.deleteLater()
            return
        if splitter.count() == 1 and isinstance(splitter.widget(0), QSplitter):
            only = splitter.widget(0)
            grandparent = splitter.parentWidget()
            if isinstance(grandparent, QSplitter):
                idx = grandparent.indexOf(splitter)
                sizes = grandparent.sizes()
                # angkat satu-satunya anak ke grandparent, lalu buang wrapper
                splitter.setParent(None)
                grandparent.insertWidget(idx, only)
                grandparent.setSizes(sizes)
                splitter.deleteLater()

    # --------------------------------------------------------- navigation
    def next_pane(self):
        if not self._panes:
            return None
        try:
            idx = self._panes.index(self.active_pane())
        except ValueError:
            idx = -1
        pane = self._panes[(idx + 1) % len(self._panes)]
        self._set_active(pane)
        self._focus_pane(pane)
        return pane

    def prev_pane(self):
        if not self._panes:
            return None
        try:
            idx = self._panes.index(self.active_pane())
        except ValueError:
            idx = 0
        pane = self._panes[(idx - 1) % len(self._panes)]
        self._set_active(pane)
        self._focus_pane(pane)
        return pane

    def pane_in_direction(self, dx, dy):
        anchor = self.active_pane()
        if anchor is None:
            return None
        ac = anchor.mapTo(self, QPoint(anchor.width() // 2,
                                       anchor.height() // 2))
        best, best_dist = None, None
        for pane in self._panes:
            if pane is anchor:
                continue
            c = pane.mapTo(self, QPoint(pane.width() // 2, pane.height() // 2))
            dvx, dvy = c.x() - ac.x(), c.y() - ac.y()
            if dx > 0 and dvx <= 0:
                continue
            if dx < 0 and dvx >= 0:
                continue
            if dy > 0 and dvy <= 0:
                continue
            if dy < 0 and dvy >= 0:
                continue
            dist = dvx * dvx + dvy * dvy
            if best_dist is None or dist < best_dist:
                best, best_dist = pane, dist
        if best is not None:
            self._set_active(best)
            self._focus_pane(best)
        return best

    def _focus_pane(self, pane):
        pane.setFocus()
        ed = pane.current_editor()
        if ed:
            ed.setFocus()

    # ------------------------------------------------------------- theme
    def apply_theme(self, theme):
        self._theme = theme
        for pane in self._panes:
            pane.apply_theme(theme)

    # ------------------------------------------------------- serialize
    def serialize(self):
        return self._serialize_widget(self.root)

    def _serialize_widget(self, w):
        if isinstance(w, QSplitter):
            return {
                "t": "s",
                "o": "h" if w.orientation() == Qt.Orientation.Horizontal else "v",
                "sz": w.sizes(),
                "c": [self._serialize_widget(w.widget(i))
                      for i in range(w.count())],
            }
        if isinstance(w, Pane):
            return {
                "t": "p",
                "tabs": [ed.file_path() or None for ed in w._editors],
                "act": w.currentIndex(),
            }
        return None

    def restore(self, node):
        """Bangun ulang layout dari hasil serialize()."""
        try:
            new_root = self._build(node)
        except Exception:
            return False
        old = self.root
        self.root = new_root
        self.layout().replaceWidget(old, new_root)
        old.deleteLater()
        if isinstance(node, dict) and node.get("t") == "s":
            sizes = node.get("sz") or []
            QTimer.singleShot(0, lambda: self.root.setSizes(sizes))
        if self._panes:
            self._set_active(self._panes[0])
            self._focus_pane(self._panes[0])
        return True

    def _build(self, node):
        if node is None:
            pane = self._make_pane()
            pane.add_editor(self._make_editor())
            self._register(pane)
            return pane
        if node.get("t") == "s":
            splitter = QSplitter(
                Qt.Orientation.Horizontal if node.get("o") == "h"
                else Qt.Orientation.Vertical)
            splitter.setChildrenCollapsible(False)
            splitter.setHandleWidth(5)
            for child in node.get("c", []):
                splitter.addWidget(self._build(child))
            return splitter
        pane = self._make_pane()
        tabs = node.get("tabs", []) or []
        active = int(node.get("act", 0))
        if not tabs:
            pane.add_editor(self._make_editor())
        for i, path in enumerate(tabs):
            editor = self._make_editor()
            if path:
                ok, _err = editor.load(path)
                if not ok:
                    editor.setPlainText(f"// Tidak dapat membuka: {path}")
            pane.add_editor(editor)
        if tabs:
            pane.setCurrentIndex(max(0, min(active, len(tabs) - 1)))
        self._register(pane)
        return pane
