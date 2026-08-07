"""OnyxPad — editor split-panes pro berbasis PySide6."""

import json
import os
from pathlib import Path

from PySide6.QtCore import Qt, QTimer, QUrl
from PySide6.QtGui import QDesktopServices, QFontDatabase, QIcon, QKeySequence
from PySide6.QtNetwork import (QNetworkAccessManager, QNetworkReply,
                               QNetworkRequest)
from PySide6.QtWidgets import (QApplication, QComboBox, QDialog, QDialogButtonBox,
                               QDockWidget, QFileDialog, QFormLayout,
                               QHBoxLayout, QInputDialog, QLabel, QLineEdit,
                               QListWidget, QMainWindow, QMessageBox,
                               QPlainTextEdit, QSpinBox, QSplitter,
                               QVBoxLayout, QWidget)

from .editor import CodeEditor, detect_language
from .filetree import FileTree
from .panes import SplitManager
from .search import SearchBar
from .syntax import LANG_NAMES
from .themes import THEMES, THEME_ORDER, build_qss
from .version import (APP_AUTHOR, APP_AUTHOR_URL, APP_ID, APP_NAME,
                      APP_RELEASES_API, APP_REPO_URL, APP_TAGLINE,
                      APP_VERSION, is_newer_version)

APP_DIR = Path(__file__).resolve().parent.parent
ICON_PATH = APP_DIR / "favicon.ico"
SETTINGS_DIR = Path.home() / f".{APP_ID}"
SETTINGS_FILE = SETTINGS_DIR / "settings.json"

MAX_RECENT = 10
CODE_EXTS = {".py", ".js", ".ts", ".jsx", ".tsx", ".html", ".css", ".c", ".cpp",
             ".h", ".hpp", ".java", ".json", ".md", ".txt", ".sh", ".yaml",
             ".yml", ".ini", ".cfg", ".log", ".toml", ".xml", ".sql"}


def pick_mono_font():
    families = set(QFontDatabase.families())
    for name in ("JetBrains Mono", "Cascadia Code", "Fira Code", "Consolas",
                 "DejaVu Sans Mono", "Courier New"):
        if name in families:
            return name
    return "Consolas"


class OnyxPad(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(f"{APP_NAME} — Pro")
        if ICON_PATH.exists():
            self.setWindowIcon(QIcon(str(ICON_PATH)))

        self.settings = self._load_settings()
        self._theme_name = self.settings.get("theme", THEME_ORDER[0])
        self.theme = THEMES[self._theme_name]
        self._recent = list(self.settings.get("recent", []))
        self._font_family = self.settings.get("font", pick_mono_font())
        self._font_size = int(self.settings.get("font_size", 12))
        self._tab_width = int(self.settings.get("tab_width", 4))
        self._wrap = bool(self.settings.get("wrap", False))
        self._untitled_counter = 0
        self._theme_actions = []

        self._build_ui()
        self._build_menus()

        # restore sesi / pane awal
        layout_node = self.settings.get("layout")
        if layout_node:
            self.manager.restore(layout_node)
        self.manager.ensure_first_pane()

        self._refresh_status()
        self.statusBar().showMessage(
            f"{APP_NAME} v{APP_VERSION} — {APP_TAGLINE}", 4000)
        self._update_manual = True
        self._net = QNetworkAccessManager(self)
        self._net.finished.connect(self._on_release_check)
        QTimer.singleShot(2500, lambda: self.check_for_updates(manual=False))
        self.setAcceptDrops(True)

    # ================================================================ UI
    def _build_ui(self):
        central = QWidget(self)
        self.manager = SplitManager(
            self.theme, make_editor=self._make_editor,
            save_editor=self.save_editor)
        self.search_bar = SearchBar(self.theme)
        self.search_bar.set_editor_getter(
            lambda: self.manager.active_editor())

        vbox = QVBoxLayout(central)
        vbox.setContentsMargins(0, 0, 0, 0)
        vbox.setSpacing(0)
        vbox.addWidget(self.manager, 1)
        vbox.addWidget(self.search_bar)
        self.setCentralWidget(central)

        # sidebar file
        self.filetree = FileTree(self.theme)
        self.filetree.file_activated.connect(self.open_file)
        self.filetree.open_in_new_pane.connect(self.open_in_new_pane)
        self.filetree.file_renamed.connect(self._on_file_renamed)
        self.filetree.file_deleted.connect(self._on_file_deleted)
        self.dock = QDockWidget("File Explorer", self)
        self.dock.setObjectName("fileDock")
        self.dock.setWidget(self.filetree)
        self.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, self.dock)
        root_folder = self.settings.get("root_folder")
        if root_folder and os.path.isdir(root_folder):
            self.filetree.set_root(root_folder)

        # status bar
        self.sb_line = QLabel("Ln 1, Col 1")
        self.sb_sel = QLabel("")
        self.sb_stats = QLabel("")
        self.sb_meta = QLabel(f"v{APP_VERSION}")
        self.sb_lang = QLabel("")
        bar = self.statusBar()
        bar.addWidget(self.sb_line)
        bar.addWidget(self.sb_sel)
        bar.addWidget(self.sb_stats)
        bar.addPermanentWidget(self.sb_meta)
        bar.addPermanentWidget(self.sb_lang)

        self.apply_theme(self._theme_name)

    # ============================================================ menus
    def _build_menus(self):
        mb = self.menuBar()

        # ---------------- File
        m_file = mb.addMenu("File")
        self._add(m_file, "Tab Baru", self.file_new_tab, "Ctrl+T")
        self._add(m_file, "Buka File…", self.open_file_dialog, "Ctrl+O")
        self._add(m_file, "Buka Folder…", self.open_folder_dialog,
                  "Ctrl+Shift+O")
        self._add(m_file, "Buka Cepat…", self.quick_open, "Ctrl+P")
        self.recent_menu = m_file.addMenu("Terbaru")
        self._rebuild_recent()
        m_file.addSeparator()
        self._add(m_file, "Simpan", self.save_active, "Ctrl+S")
        self._add(m_file, "Simpan Sebagai…", self.save_active_as,
                  "Ctrl+Shift+S")
        self._add(m_file, "Simpan Semua", self.save_all, "Ctrl+Alt+S")
        m_file.addSeparator()
        self._add(m_file, "Tutup Tab", self.close_active_tab, "Ctrl+W")
        self._add(m_file, "Tutup Pane", self.close_pane_action, "Ctrl+Shift+W")
        m_file.addSeparator()
        m_file.addAction("Keluar", self.close, QKeySequence("Ctrl+Q"))

        # ---------------- Edit
        m_edit = mb.addMenu("Edit")
        self._add_std(m_edit, "Undo", QKeySequence.StandardKey.Undo,
                      self._with_editor("undo"))
        self._add_std(m_edit, "Redo", QKeySequence.StandardKey.Redo,
                      self._with_editor("redo"))
        m_edit.addSeparator()
        self._add_std(m_edit, "Potong", QKeySequence.StandardKey.Cut,
                      self._with_editor("cut"))
        self._add_std(m_edit, "Salin", QKeySequence.StandardKey.Copy,
                      self._with_editor("copy"))
        self._add_std(m_edit, "Tempel", QKeySequence.StandardKey.Paste,
                      self._with_editor("paste"))
        self._add_std(m_edit, "Pilih Semua", QKeySequence.StandardKey.SelectAll,
                      self._with_editor("selectAll"))
        m_edit.addSeparator()
        self._add(m_edit, "Cari…", self.search_bar.show_find, "Ctrl+F")
        self._add(m_edit, "Cari Berikutnya", lambda: self.search_bar._do_find(True), "F3")
        self._add(m_edit, "Cari Sebelumnya",
                  lambda: self.search_bar._do_find(False), "Shift+F3")
        self._add(m_edit, "Ganti…", self.search_bar.show_replace, "Ctrl+H")
        m_edit.addSeparator()
        self._add(m_edit, "Komentari / Batal Komentari", self.toggle_comment,
                  "Ctrl+/")
        self._add(m_edit, "Pergi ke Baris…", self.go_to_line, "Ctrl+G")

        # ---------------- Split
        m_split = mb.addMenu("Split")
        self._add(m_split, "Split Kanan", self.manager.split_right, "Ctrl+\\")
        self._add(m_split, "Split Bawah", self.manager.split_below, "Ctrl+'")
        m_split.addSeparator()
        self._add(m_split, "Pane Berikutnya", self.manager.next_pane, "Ctrl+Tab")
        self._add(m_split, "Pane Sebelumnya", self.manager.prev_pane,
                  "Ctrl+Shift+Tab")
        self._add(m_split, "Fokus Pane Kiri",
                  lambda: self.manager.pane_in_direction(-1, 0), "Alt+Left")
        self._add(m_split, "Fokus Pane Kanan",
                  lambda: self.manager.pane_in_direction(1, 0), "Alt+Right")
        self._add(m_split, "Fokus Pane Atas",
                  lambda: self.manager.pane_in_direction(0, -1), "Alt+Up")
        self._add(m_split, "Fokus Pane Bawah",
                  lambda: self.manager.pane_in_direction(0, 1), "Alt+Down")
        m_split.addSeparator()
        self._add(m_split, "Tutup Pane", self.close_pane_action, "Ctrl+Shift+W")

        # ---------------- Tampilan
        m_view = mb.addMenu("Tampilan")
        self.theme_menu = m_view.addMenu("Tema")
        self._theme_actions = []
        for name in THEME_ORDER:
            act = self.theme_menu.addAction(name)
            act.setCheckable(True)
            act.setChecked(name == self._theme_name)
            act.triggered.connect(lambda _c, n=name: self.apply_theme(n))
            self._theme_actions.append(act)
        m_view.addSeparator()
        m_view.addAction(self.dock.toggleViewAction())
        self._add(m_view, "Bungkus Kata (editor aktif)", self.toggle_wrap,
                  "Alt+Z")
        m_view.addSeparator()
        self._add(m_view, "Perbesar", lambda: self._zoom(1), "Ctrl+=")
        self._add(m_view, "Perkecil", lambda: self._zoom(-1), "Ctrl+-")
        self._add(m_view, "Reset Zoom", lambda: self._zoom_reset(), "Ctrl+0")
        m_view.addSeparator()
        self._add(m_view, "Preferensi…", self.show_preferences, "Ctrl+,")

        # ---------------- Bantuan
        m_help = mb.addMenu("Bantuan")
        self._add(m_help, "Pintasan Keyboard", self.show_shortcuts, "F1")
        self._add(m_help, f"Tentang {APP_NAME}", self.show_about)
        m_help.addSeparator()
        # lambda agar arg 'checked' dari sinyal tidak menimpa manual=True
        self._add(m_help, "Cek Pembaruan…",
                  lambda _checked=False: self.check_for_updates(manual=True))
        m_help.addSeparator()
        self._add(m_help, "Repositori GitHub",
                  lambda: self._open_url(APP_REPO_URL))
        self._add(m_help, f"Author: {APP_AUTHOR}",
                  lambda: self._open_url(APP_AUTHOR_URL))

    def _add(self, menu, label, slot, shortcut=None):
        act = menu.addAction(label, slot)
        if shortcut:
            act.setShortcut(QKeySequence(shortcut))
        return act

    def _add_std(self, menu, label, standard_key, slot):
        act = menu.addAction(label, slot)
        act.setShortcut(QKeySequence(standard_key))
        return act

    def _with_editor(self, method):
        def run():
            ed = self.manager.active_editor()
            if ed is not None:
                getattr(ed, method)()
        return run

    # ============================================================ editor
    def _make_editor(self):
        ed = CodeEditor(self.theme, language="plain",
                        font_family=self._font_family,
                        font_size=self._font_size,
                        tab_width=self._tab_width,
                        wrap=self._wrap)
        ed.focused.connect(self._refresh_status)
        ed.cursorPositionChanged.connect(self._refresh_status)
        ed.textChanged.connect(self._refresh_status)
        ed.document().modificationChanged.connect(
            lambda _m: self._refresh_status())
        return ed

    def _new_untitled_name(self):
        self._untitled_counter += 1
        return f"Tanpa Judul {self._untitled_counter}"

    def file_new_tab(self):
        ed = self._make_editor()
        self.manager.active_pane().add_editor(ed)
        ed.setFocus()

    # ============================================================ open
    def open_file_dialog(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Buka File", "", self._file_filters())
        if path:
            self.open_file(path)

    def _file_filters(self):
        return ("Semua File Pendukung (*.py *.js *.ts *.jsx *.html *.css *.c "
                "*.cpp *.h *.java *.json *.md *.txt *.sh *.yaml *.yml *.xml "
                "*.sql *.toml *.ini *.cfg *.log);;Semua File (*.*)")

    def open_file(self, path, new_pane=False):
        if not path or not os.path.isfile(path):
            return None
        # jika file sudah terbuka, fokuskan tab-nya
        for pane in self.manager._panes:
            for ed in pane.editors():
                if ed.file_path() and os.path.normpath(ed.file_path()) == os.path.normpath(path):
                    pane.setCurrentWidget(ed)
                    ed.setFocus()
                    return ed
        ed = self._make_editor()
        ok, err = ed.load(path)
        if not ok:
            QMessageBox.warning(self, "Gagal Membuka",
                                f"Tidak dapat membaca:\n{path}\n\n{err}")
            ed.deleteLater()
            return None
        if new_pane:
            self.manager.new_pane(ed)
        else:
            self.manager.active_pane().add_editor(ed)
        self._add_recent(path)
        self._refresh_status()
        return ed

    def open_in_new_pane(self, path):
        self.open_file(path, new_pane=True)

    def open_folder_dialog(self):
        path = QFileDialog.getExistingDirectory(self, "Buka Folder", "")
        if path:
            self.open_folder(path)

    def open_folder(self, path):
        self.filetree.set_root(path)
        self.settings["root_folder"] = path
        self.statusBar().showMessage(f"Folder: {path}", 4000)

    def _on_file_renamed(self, old_path, new_path):
        """Update tab editor yang file-nya di-rename dari sidebar."""
        import os
        for pane in self.manager._panes:
            for ed in pane.editors():
                if ed.file_path() and os.path.normpath(ed.file_path()) == os.path.normpath(old_path):
                    ed._file_path = new_path
                    ed.set_language(__import__('src.editor', fromlist=['detect_language']).detect_language(new_path))
                    pane._refresh_tab_title(ed)
        self.statusBar().showMessage(
            f"Renamed: {os.path.basename(old_path)} → {os.path.basename(new_path)}", 3000)

    def _on_file_deleted(self, path):
        """Tandai tab editor yang file-nya dihapus dari sidebar."""
        import os
        for pane in self.manager._panes:
            for ed in pane.editors():
                if ed.file_path() and os.path.normpath(ed.file_path()) == os.path.normpath(path):
                    ed._file_path = None
                    ed.document().setModified(True)
                    pane._refresh_tab_title(ed)
        self.statusBar().showMessage(
            f"Dihapus: {os.path.basename(path)} (tab masih terbuka, belum disimpan)", 4000)

    def quick_open(self):
        """Buka Cepat — filter nama file di folder yang sedang dibuka."""
        root = self.filetree.root_path()
        if not root:
            QMessageBox.information(
                self, "Buka Cepat",
                "Buka folder dulu (File → Buka Folder…) agar Buka Cepat bekerja.")
            return
        files = self._scan_folder(root)
        dlg = QDialog(self)
        dlg.setWindowTitle("Buka Cepat (Ctrl+P)")
        dlg.resize(460, 420)
        layout = QVBoxLayout(dlg)
        edit = QLineEdit()
        edit.setPlaceholderText("Ketik nama file…")
        lst = QListWidget()
        layout.addWidget(edit)
        layout.addWidget(lst)

        def refill(text):
            t = text.strip().lower()
            lst.clear()
            for f in files:
                if t in f.lower():
                    lst.addItem(f)
            if lst.count():
                lst.setCurrentRow(0)

        edit.textChanged.connect(refill)
        refill("")

        def open_selected():
            item = lst.currentItem()
            if item:
                self.open_file(str(Path(root) / item.text()))
            dlg.accept()

        lst.itemDoubleClicked.connect(lambda _i: open_selected())
        edit.returnPressed.connect(open_selected)
        edit.setFocus()
        dlg.exec()

    @staticmethod
    def _scan_folder(root, limit=800):
        out = []
        for dirpath, dirnames, filenames in os.walk(root):
            dirnames[:] = [d for d in dirnames
                           if not d.startswith((".", "__")) and d != "node_modules"]
            for name in filenames:
                ext = os.path.splitext(name)[1].lower()
                if ext in CODE_EXTS:
                    rel = os.path.relpath(os.path.join(dirpath, name), root)
                    out.append(rel.replace("\\", "/"))
                    if len(out) >= limit:
                        return out
        return out

    # ============================================================ save
    def save_active(self):
        ed = self.manager.active_editor()
        if ed is None:
            return
        self.save_editor(ed)

    def save_active_as(self):
        ed = self.manager.active_editor()
        if ed is None:
            return
        self.save_editor_as(ed)

    def save_editor(self, editor) -> bool:
        if editor.file_path():
            ok, err = editor.save()
            if not ok:
                QMessageBox.warning(self, "Gagal Menyimpan",
                                    f"{editor.file_path()}\n\n{err}")
            return ok
        return self.save_editor_as(editor)

    def save_editor_as(self, editor) -> bool:
        path, _ = QFileDialog.getSaveFileName(
            self, "Simpan Sebagai", editor.display_name(), self._file_filters())
        if not path:
            return False
        ok, err = editor.save(path)
        if not ok:
            QMessageBox.warning(self, "Gagal Menyimpan",
                                f"{path}\n\n{err}")
            return False
        self._add_recent(path)
        return True

    def save_all(self):
        count = 0
        for ed in self.manager.all_editors():
            if self.save_editor(ed):
                count += 1
        if count:
            self.statusBar().showMessage(f"{count} file disimpan.", 3000)

    # ============================================================ close
    def close_active_tab(self):
        pane = self.manager.active_pane()
        if pane is not None and pane.count():
            pane.close_tab_at(pane.currentIndex())

    def close_pane_action(self):
        self.manager.close_pane()

    # ============================================================ tools
    def toggle_comment(self):
        ed = self.manager.active_editor()
        if ed is not None:
            ed.toggle_comment()

    def go_to_line(self):
        ed = self.manager.active_editor()
        if ed is None:
            return
        line, _ok = QInputDialog.getInt(self, "Pergi ke Baris",
                                        "Nomor baris:", 1, 1, 10 ** 6)
        if _ok:
            ed.go_to_line(line)

    def toggle_wrap(self):
        self._wrap = not self._wrap
        mode = (QPlainTextEdit.LineWrapMode.WidgetWidth
                if self._wrap else QPlainTextEdit.LineWrapMode.NoWrap)
        for ed in self.manager.all_editors():
            ed.setLineWrapMode(mode)
        self.statusBar().showMessage(
            f"Bungkus kata: {'aktif' if self._wrap else 'nonaktif'}", 2500)

    def _zoom(self, delta):
        ed = self.manager.active_editor()
        if ed is None:
            return
        if delta > 0:
            ed.zoomIn(1)
        else:
            ed.zoomOut(1)
        ed._update_line_area_width()
        self._refresh_status()

    def _zoom_reset(self):
        ed = self.manager.active_editor()
        if ed is None:
            return
        ed.set_font_size(self._font_size)
        ed._update_line_area_width()
        self._refresh_status()

    # ============================================================ preferences
    def show_preferences(self):
        """Dialog Preferensi — ubah font, ukuran, dan lebar tab."""
        dlg = QDialog(self)
        dlg.setWindowTitle("Preferensi")
        dlg.setMinimumWidth(360)

        form = QFormLayout()
        form.setSpacing(12)
        form.setContentsMargins(16, 16, 16, 8)

        # Font family
        font_combo = QComboBox()
        mono_fonts = [
            "JetBrains Mono", "Cascadia Code", "Fira Code", "Consolas",
            "DejaVu Sans Mono", "Courier New", "Lucida Console",
            "Source Code Pro", "Hack", "Inconsolata",
        ]
        available = set(QFontDatabase.families())
        for f in mono_fonts:
            if f in available:
                font_combo.addItem(f)
        # pastikan font saat ini ada di list
        if self._font_family not in [font_combo.itemText(i)
                                      for i in range(font_combo.count())]:
            font_combo.insertItem(0, self._font_family)
        font_combo.setCurrentText(self._font_family)
        form.addRow("Font:", font_combo)

        # Font size
        size_spin = QSpinBox()
        size_spin.setRange(6, 72)
        size_spin.setValue(self._font_size)
        size_spin.setSuffix(" pt")
        form.addRow("Ukuran font:", size_spin)

        # Tab width
        tab_spin = QSpinBox()
        tab_spin.setRange(1, 16)
        tab_spin.setValue(self._tab_width)
        tab_spin.setSuffix(" spasi")
        form.addRow("Lebar tab:", tab_spin)

        # Tombol OK / Batal
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok |
            QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(dlg.accept)
        buttons.rejected.connect(dlg.reject)

        vbox = QVBoxLayout(dlg)
        vbox.addLayout(form)
        vbox.addWidget(buttons)

        if dlg.exec() != QDialog.DialogCode.Accepted:
            return

        new_family = font_combo.currentText()
        new_size   = size_spin.value()
        new_tab    = tab_spin.value()

        changed_font   = new_family != self._font_family
        changed_size   = new_size   != self._font_size
        changed_tab    = new_tab    != self._tab_width

        self._font_family = new_family
        self._font_size   = new_size
        self._tab_width   = new_tab

        # Terapkan ke semua editor yang sudah terbuka
        for ed in self.manager.all_editors():
            if changed_font:
                ed.set_font_family(new_family)
            if changed_size:
                ed.set_font_size(new_size)
            if changed_tab:
                ed._tab_width = new_tab
                from PySide6.QtGui import QFontMetricsF
                ed.setTabStopDistance(
                    QFontMetricsF(ed.font()).horizontalAdvance(" ") * new_tab)
            ed._update_line_area_width()

        self.statusBar().showMessage(
            f"Preferensi disimpan — font: {new_family} {new_size}pt, "
            f"tab: {new_tab} spasi", 4000)

    # ============================================================ theme
    def apply_theme(self, name):
        if name not in THEMES:
            return
        self._theme_name = name
        self.theme = THEMES[name]
        QApplication.instance().setStyleSheet(build_qss(self.theme["ui"]))
        self.manager.apply_theme(self.theme)
        self.filetree.apply_theme(self.theme)
        self.search_bar.apply_theme(self.theme)
        for act in self._theme_actions:
            act.setChecked(act.text() == name)
        self._refresh_status()

    # ============================================================ status
    def _refresh_status(self, *_):
        ed = self.manager.active_editor()
        if ed is None:
            return
        line, col, sel = ed.cursor_info()
        words, chars = ed.stats()
        count = ed.cursor_count()
        suffix = f" · {count} kursor" if count > 1 else ""
        self.sb_line.setText(f"Ln {line}, Col {col}{suffix}")
        self.sb_sel.setText(f"  {sel} dipilih" if sel else "")
        self.sb_stats.setText(f"  {words} kata · {chars} karakter")
        lang = LANG_NAMES.get(getattr(ed, "_language", "plain"), "")
        self.sb_lang.setText(f"{lang} · {ed.set_encoding_name()} · "
                             f"{int(ed.zoom_level()) or 100}%")
        name = ed.display_name()
        star = " ●" if ed.document().isModified() else ""
        self.setWindowTitle(f"{APP_NAME} — {name}{star}")

    # ============================================================ recent
    def _add_recent(self, path):
        norm = os.path.normpath(path)
        if norm in self._recent:
            self._recent.remove(norm)
        self._recent.insert(0, norm)
        del self._recent[MAX_RECENT:]
        self._rebuild_recent()

    def _rebuild_recent(self):
        self.recent_menu.clear()
        if not self._recent:
            act = self.recent_menu.addAction("(kosong)")
            act.setEnabled(False)
            return
        for path in self._recent:
            self.recent_menu.addAction(
                path, lambda _c=False, p=path: self.open_file(p))

    # ============================================================ drag&drop
    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event):
        for url in event.mimeData().urls():
            path = url.toLocalFile()
            if path and os.path.isfile(path):
                self.open_file(path)
        event.acceptProposedAction()

    # ============================================================ dialogs
    def show_shortcuts(self):
        QMessageBox.information(self, "Pintasan Keyboard", SHORTCUTS_TEXT)

    def show_about(self):
        QMessageBox.about(
            self, f"Tentang {APP_NAME}",
            f"<h3>{APP_NAME} — {APP_TAGLINE}</h3>"
            f"<p><b>Versi {APP_VERSION}</b> · editor teks dengan split panes "
            "bertingkat gaya tmux/VS Code, dibangun dengan PySide6 (Qt6).</p>"
            "<p>Fitur: split kanan/bawah, tab per pane, syntax highlighting "
            "multi-bahasa, find &amp; replace, 7 tema, multi-kursor, sesi "
            "otomatis, dan penjelajah folder.</p>"
            f"<p>Open source: <a href=\"{APP_REPO_URL}\">{APP_REPO_URL}</a><br>"
            f"Author: <a href=\"{APP_AUTHOR_URL}\">{APP_AUTHOR}</a> — "
            "buka tautan lewat menu Bantuan.</p>")

    # ============================================================ updates
    def _open_url(self, url):
        QDesktopServices.openUrl(QUrl(url))

    def check_for_updates(self, manual=True):
        """Cek rilis terbaru di GitHub (async — tidak memblokir UI)."""
        req = QNetworkRequest(QUrl(APP_RELEASES_API))
        req.setRawHeader(b"User-Agent", b"OnyxPad")
        req.setRawHeader(b"Accept", b"application/vnd.github+json")
        reply = self._net.get(req)
        # simpan bendera per-request agar jawaban yang terlambat tidak
        # menimpa perilaku cek manual (hindari race antar permintaan)
        reply.setProperty("manual", manual)

    def _on_release_check(self, reply):
        manual = bool(reply.property("manual"))
        if reply.error() == QNetworkReply.NetworkError.NoError:
            try:
                data = json.loads(bytes(reply.readAll()).decode("utf-8"))
                tag = data.get("tag_name", "")
                if is_newer_version(APP_VERSION, tag):
                    latest = tag.lstrip("vV")
                    self.statusBar().showMessage(
                        f"Pembaruan tersedia: v{latest} — menu Bantuan → "
                        "Repositori GitHub", 8000)
                    if self._update_manual:
                        box = QMessageBox(self)
                        box.setWindowTitle("Pembaruan Tersedia")
                        box.setIcon(QMessageBox.Icon.Information)
                        box.setText(f"<b>{APP_NAME} v{latest}</b> sudah rilis!")
                        box.setInformativeText(
                            f"Anda menjalankan v{APP_VERSION}.\n"
                            "Kunjungi halaman rilis untuk mengunduh versi baru.")
                        open_btn = box.addButton(
                            "Buka Halaman Rilis",
                            QMessageBox.ButtonRole.AcceptRole)
                        box.addButton("Nanti",
                                      QMessageBox.ButtonRole.RejectRole)
                        box.exec()
                        if box.clickedButton() is open_btn:
                            self._open_url(data.get("html_url")
                                           or APP_REPO_URL)
                elif manual:
                    self.statusBar().showMessage(
                        f"{APP_NAME} sudah versi terbaru (v{APP_VERSION}).",
                        4000)
            except Exception:
                pass
        elif manual:
            self.statusBar().showMessage(
                "Gagal memeriksa pembaruan (tidak ada koneksi?).", 4000)
        reply.deleteLater()

    # ============================================================ session
    def _load_settings(self):
        try:
            if SETTINGS_FILE.exists():
                return json.loads(SETTINGS_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
        return {}

    def _save_settings(self):
        try:
            SETTINGS_DIR.mkdir(parents=True, exist_ok=True)
            data = {
                "theme": self._theme_name,
                "font": self._font_family,
                "font_size": self._font_size,
                "tab_width": self._tab_width,
                "wrap": self._wrap,
                "recent": self._recent,
                "root_folder": self.settings.get("root_folder"),
                "layout": self.manager.serialize(),
            }
            SETTINGS_FILE.write_text(json.dumps(data, indent=2),
                                     encoding="utf-8")
        except Exception:
            pass

    def closeEvent(self, event):
        modified = [ed for ed in self.manager.all_editors()
                    if ed.document().isModified()]
        if modified:
            box = QMessageBox(self)
            box.setWindowTitle("Perubahan Belum Disimpan")
            box.setIcon(QMessageBox.Icon.Warning)
            box.setText(f"{len(modified)} file belum disimpan.")
            save = box.addButton("Simpan Semua", QMessageBox.ButtonRole.AcceptRole)
            discard = box.addButton("Buang Semua", QMessageBox.ButtonRole.DestructiveRole)
            cancel = box.addButton("Batal", QMessageBox.ButtonRole.RejectRole)
            box.exec()
            clicked = box.clickedButton()
            if clicked is cancel:
                event.ignore()
                return
            if clicked is save:
                for ed in modified:
                    if not self.save_editor(ed):
                        event.ignore()
                        return
        self._save_settings()
        event.accept()

SHORTCUTS_TEXT = """\
<b>File</b>
  Ctrl+T       Tab baru
  Ctrl+O       Buka file
  Ctrl+Shift+O Buka folder
  Ctrl+P       Buka cepat
  Ctrl+S       Simpan · Ctrl+Shift+S Simpan sebagai
  Ctrl+Alt+S   Simpan semua · Ctrl+W Tutup tab

<b>Split (tmux style)</b>
  Ctrl+\\       Split kanan
  Ctrl+'       Split bawah
  Ctrl+Tab     Pane berikutnya · Ctrl+Shift+Tab sebelumnya
  Alt+←↑→↓     Fokus pane ke arah itu
  Ctrl+Shift+W Tutup pane

<b>Edit</b>
  Ctrl+F cari · Ctrl+H ganti · F3 berikutnya · Shift+F3 sebelumnya
  Ctrl+/ komentari · Ctrl+G pergi ke baris
  Ctrl+= / Ctrl+- / Ctrl+0 zoom in / out / reset

<b>Multi-kursor</b>
  Ctrl+D     tambah kursor di kemunculan kata berikutnya
  Ctrl+U     buang kursor terakhir · Esc selesai
  Ketik/Backspace/Enter berlaku di semua kursor sekaligus

<b>Lainnya</b>
  Ctrl+wheel  zoom · Alt+Z bungkus kata · Esc tutup bar cari
"""
