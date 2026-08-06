"""Bar find & replace — Ctrl+F cari, Ctrl+H ganti, Enter=berikutnya."""

import re

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QKeySequence, QShortcut, QTextCursor, QTextDocument
from PySide6.QtWidgets import (QCheckBox, QHBoxLayout, QLabel, QLineEdit,
                               QMessageBox, QPushButton, QVBoxLayout, QWidget)


class SearchBar(QWidget):
    def __init__(self, theme, parent=None):
        super().__init__(parent)
        self._theme = theme
        self._get_editor = None

        self.find_edit = QLineEdit()
        self.find_edit.setPlaceholderText(
            "Cari…  (Enter berikutnya · Shift+Enter sebelumnya)")
        self.replace_edit = QLineEdit()
        self.replace_edit.setPlaceholderText("Ganti dengan…")

        self.case_box = QCheckBox("Aa")
        self.case_box.setToolTip("Cocokkan huruf besar/kecil")
        self.word_box = QCheckBox("Kata")
        self.word_box.setToolTip("Kata utuh saja")
        self.regex_box = QCheckBox(".*")
        self.regex_box.setToolTip("Gunakan ekspresi reguler")

        self.count_label = QLabel("")
        self.count_label.setStyleSheet("color: #888; padding: 0 6px;")

        self.prev_btn = QPushButton("‹ Sebelumnya")
        self.next_btn = QPushButton("Berikutnya ›")
        self.replace_btn = QPushButton("Ganti")
        self.replace_all_btn = QPushButton("Ganti Semua")
        self.close_btn = QPushButton("✕")
        self.close_btn.setFixedWidth(28)

        row1 = QHBoxLayout()
        row1.setSpacing(6)
        row1.addWidget(self.find_edit, 1)
        row1.addWidget(self.case_box)
        row1.addWidget(self.word_box)
        row1.addWidget(self.regex_box)
        row1.addWidget(self.count_label)
        row1.addWidget(self.prev_btn)
        row1.addWidget(self.next_btn)
        row1.addWidget(self.close_btn)

        row2 = QHBoxLayout()
        row2.setSpacing(6)
        row2.addWidget(QLabel("Ganti:"))
        row2.addWidget(self.replace_edit, 1)
        row2.addWidget(self.replace_btn)
        row2.addWidget(self.replace_all_btn)
        row2.addStretch(1)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 4, 8, 4)
        layout.addLayout(row1, 3)
        layout.addLayout(row2, 2)

        self.prev_btn.clicked.connect(lambda: self._do_find(False))
        self.next_btn.clicked.connect(lambda: self._do_find(True))
        self.replace_btn.clicked.connect(self._replace)
        self.replace_all_btn.clicked.connect(self._replace_all)
        self.close_btn.clicked.connect(self.hide_bar)
        self.find_edit.returnPressed.connect(lambda: self._do_find(True))
        self.replace_edit.returnPressed.connect(self._replace)

        self._install_shortcuts()

        self.hide()
        self.replace_edit.hide()
        self.replace_btn.hide()
        self.replace_all_btn.hide()

    # ----------------------------------------------------------- wiring
    def set_editor_getter(self, fn):
        self._get_editor = fn

    def active_editor(self):
        if not self._get_editor:
            return None
        return self._get_editor()

    def _install_shortcuts(self):
        for widget in (self.find_edit, self.replace_edit):
            QShortcut(QKeySequence("Escape"), widget, self.hide_bar)
            QShortcut(QKeySequence("Shift+Return"), widget,
                      lambda: self._do_find(False))
            QShortcut(QKeySequence("F3"), widget, lambda: self._do_find(True))
            QShortcut(QKeySequence("Shift+F3"), widget,
                      lambda: self._do_find(False))
        QShortcut(QKeySequence("Ctrl+F"), self, self.show_find)
        QShortcut(QKeySequence("Ctrl+H"), self, self.show_replace)
        QShortcut(QKeySequence("F3"), self, lambda: self._do_find(True))
        QShortcut(QKeySequence("Shift+F3"), self, lambda: self._do_find(False))

    # ------------------------------------------------------------- mode
    def show_find(self):
        self.replace_edit.hide()
        self.replace_btn.hide()
        self.replace_all_btn.hide()
        self.show()
        self.find_edit.setFocus()
        self.find_edit.selectAll()

    def show_replace(self):
        self.replace_edit.show()
        self.replace_btn.show()
        self.replace_all_btn.show()
        self.show()
        self.find_edit.setFocus()
        self.find_edit.selectAll()

    def hide_bar(self):
        self.hide()
        editor = self.active_editor()
        if editor is not None:
            editor.set_search_matches("", QTextDocument.FindFlags())
            editor.setFocus()

    def apply_theme(self, theme):
        self._theme = theme

    # ------------------------------------------------------------- find
    def _flags(self):
        flags = QTextDocument.FindFlags()
        if self.case_box.isChecked():
            flags |= QTextDocument.FindFlag.FindCaseSensitively
        if self.word_box.isChecked():
            flags |= QTextDocument.FindFlag.FindWholeWords
        return flags

    def _pattern(self):
        """Konversi input ke pola (regex bila kotak .* aktif)."""
        text = self.find_edit.text()
        if not text:
            return ""
        return text if self.regex_box.isChecked() else re.escape(text)

    def _do_find(self, next_):
        editor = self.active_editor()
        if editor is None or not self.find_edit.text():
            return
        pattern = self._pattern()
        flags = self._flags()
        use_regex = self.regex_box.isChecked()
        if next_:
            found = editor.find_next(pattern, flags, use_regex)
            if not found:
                editor.moveCursor(QTextCursor.MoveOperation.Start)
                editor.find_next(pattern, flags, use_regex)
        else:
            found = editor.find_prev(pattern, flags, use_regex)
            if not found:
                editor.moveCursor(QTextCursor.MoveOperation.End)
                editor.find_prev(pattern, flags, use_regex)
        self._highlight()
        self._update_count()

    def _highlight(self):
        editor = self.active_editor()
        if editor is None:
            return
        editor.set_search_matches(self._pattern(), self._flags(),
                                  use_regex=self.regex_box.isChecked())

    def _update_count(self):
        editor = self.active_editor()
        if editor is None or not self.find_edit.text():
            self.count_label.setText("")
            return
        if self.regex_box.isChecked():
            try:
                re.compile(self.find_edit.text())
            except re.error:
                self.count_label.setText("pola regex salah")
                return
        n = editor.count_matches(self._pattern(), self._flags(),
                                 self.regex_box.isChecked())
        self.count_label.setText(f"{n} cocok")

    # ----------------------------------------------------------- replace
    def _replace(self):
        editor = self.active_editor()
        if editor is None:
            return
        pattern = self._pattern()
        if not pattern:
            return
        use_regex = self.regex_box.isChecked()
        if editor.replace_current(pattern, self.replace_edit.text(),
                                  self._flags(), use_regex):
            self._do_find(True)
            self._update_count()

    def _replace_all(self):
        editor = self.active_editor()
        if editor is None:
            return
        pattern = self._pattern()
        if not pattern:
            return
        n = editor.replace_all(pattern, self.replace_edit.text(),
                               self._flags(), self.regex_box.isChecked())
        self._update_count()
        if n:
            editor.set_search_matches("", QTextDocument.FindFlags())
            QMessageBox.information(self, "Ganti Semua",
                                    f"{n} kemunculan diganti.")
