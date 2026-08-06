"""CodeEditor pro berbasis QPlainTextEdit — nomor baris, highlight baris aktif,
pencocokan kurung, auto-pair/indent, find & replace, zoom, dan tema."""

import os

from PySide6.QtCore import Qt, QRect, QRegularExpression, QSize, Signal
from PySide6.QtGui import (QColor, QFontMetricsF, QPainter, QTextCharFormat,
                           QTextCursor, QTextDocument, QTextFormat, QWheelEvent)
from PySide6.QtWidgets import (QApplication, QPlainTextEdit, QTextEdit,
                               QWidget)

from .syntax import Highlighter, LANG_NAMES, detect_language

PAIRS = {"(": ")", "[": "]", "{": "}", '"': '"', "'": "'", "`": "`"}
_CLOSERS = set(PAIRS.values())

_COMMENT_TOGGLE = {
    "python": "#", "shell": "#", "javascript": "//", "typescript": "//",
    "c": "//", "cpp": "//", "java": "//", "css": "/*", "html": "<!--",
}


class LineNumberArea(QWidget):
    def __init__(self, editor):
        super().__init__(editor)
        self._editor = editor

    def sizeHint(self):
        return QSize(self._editor.line_number_area_width(), 0)

    def paintEvent(self, event):
        self._editor.line_number_area_paint(event)


class CodeEditor(QPlainTextEdit):
    focused = Signal()

    def __init__(self, theme, language="plain", font_family=None, font_size=11,
                 tab_width=4, wrap=False, parent=None):
        super().__init__(parent)
        self._theme = theme
        self._file_path = None
        self._language = language if language in LANG_NAMES else "plain"
        self._encoding = "utf-8"
        self._tab_width = max(1, int(tab_width))
        self._search_query = ""
        self._search_flags = QTextDocument.FindFlags()
        self._search_use_regex = False
        self._search_color = QColor(theme["selection"])
        self._zoom = 0
        self._extra_cursors = []  # rentang [start, end] kursor sekunder (Ctrl+D)

        f = self.font()
        if font_family:
            f.setFamily(font_family)
        f.setPointSize(max(6, int(font_size)))
        self.setFont(f)
        self.setTabStopDistance(
            QFontMetricsF(self.font()).horizontalAdvance(" ") * self._tab_width)
        self.setLineWrapMode(
            QPlainTextEdit.LineWrapMode.WidgetWidth if wrap
            else QPlainTextEdit.LineWrapMode.NoWrap)
        self.setCenterOnScroll(True)
        self.document().setDocumentMargin(8)

        self._line_area = LineNumberArea(self)
        self.blockCountChanged.connect(self._update_line_area_width)
        self.updateRequest.connect(self._update_line_area)
        self.cursorPositionChanged.connect(self._on_cursor_moved)
        self.textChanged.connect(self._refresh_current_line)

        self._highlighter = Highlighter(self.document(), self._language, theme)
        self._apply_editor_colors()
        self._update_line_area_width()
        self._refresh_extra()
        # setDocumentMargin()/setStyleSheet() menandai dokumen sebagai modified
        # — editor baru harus tampil bersih (tanpa titik "belum disimpan").
        self.document().setModified(False)

    # ------------------------------------------------------------------ fonts
    def set_font_family(self, family):
        f = self.font()
        f.setFamily(family)
        self.setFont(f)

    def set_font_size(self, size):
        f = self.font()
        f.setPointSize(max(6, int(size)))
        self.setFont(f)

    def setFont(self, font):
        super().setFont(font)
        self.setTabStopDistance(
            QFontMetricsF(self.font()).horizontalAdvance(" ") * self._tab_width)
        self._update_line_area_width()

    def zoom_level(self):
        return self._zoom

    def wheelEvent(self, event: QWheelEvent):
        if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            delta = event.angleDelta().y()
            if delta > 0:
                self.zoomIn(1)
                self._zoom += 1
            elif delta < 0:
                self.zoomOut(1)
                self._zoom -= 1
            self._update_line_area_width()
            event.accept()
            return
        super().wheelEvent(event)

    # ---------------------------------------------------------- line numbers
    def line_number_area_width(self):
        digits = max(2, len(str(max(1, self.blockCount()))))
        metrics = QFontMetricsF(self.font())
        return int(metrics.horizontalAdvance("9") * digits + 16)

    def _update_line_area_width(self, *_):
        self.setViewportMargins(self.line_number_area_width(), 0, 0, 0)

    def _update_line_area(self, rect, dy):
        if dy:
            self._line_area.scroll(0, dy)
        else:
            self._line_area.update(0, rect.y(), self._line_area.width(),
                                   rect.height())
        if rect.contains(self.viewport().rect()):
            self._update_line_area_width()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        cr = self.contentsRect()
        self._line_area.setGeometry(
            QRect(cr.left(), cr.top(), self.line_number_area_width(),
                  cr.height()))

    def line_number_area_paint(self, event):
        painter = QPainter(self._line_area)
        painter.fillRect(event.rect(), QColor(self._theme["gutter_bg"]))
        block = self.firstVisibleBlock()
        block_number = block.blockNumber()
        top = self.blockBoundingGeometry(block).translated(
            self.contentOffset()).top()
        bottom = top + self.blockBoundingRect(block).height()
        current = self.textCursor().blockNumber()
        while block.isValid() and top <= event.rect().bottom():
            if block.isVisible() and bottom >= event.rect().top():
                if block_number == current:
                    painter.fillRect(
                        0, int(top), self._line_area.width(),
                        int(self.blockBoundingRect(block).height()),
                        QColor(self._theme["current_line"]))
                    painter.setPen(QColor(self._theme["current_line_num"]))
                else:
                    painter.setPen(QColor(self._theme["gutter_fg"]))
                painter.drawText(
                    0, int(top), self._line_area.width() - 4,
                    int(self.blockBoundingRect(block).height()),
                    Qt.AlignmentFlag.AlignRight, str(block_number + 1))
            block = block.next()
            top = bottom
            bottom = top + self.blockBoundingRect(block).height()
            block_number += 1

    # -------------------------------------------------------------- editing
    def keyPressEvent(self, event):
        key = event.key()
        mods = event.modifiers()
        ctrl = Qt.KeyboardModifier.ControlModifier
        if key == Qt.Key.Key_D and mods & ctrl:
            self._add_next_occurrence()
            return
        if key == Qt.Key.Key_U and mods & ctrl:
            self._remove_last_cursor()
            return
        if self._extra_cursors:
            # mode multi-kursor: ketik/backspace/Enter diproses di semua
            # kursor; kunci lain (panah, pintasan) menutup mode ini.
            if self._handle_multi_key(event):
                return
            self._clear_extra_cursors()
        if key == Qt.Key.Key_Tab:
            self._handle_tab(mods & Qt.KeyboardModifier.ShiftModifier)
            return
        if key == Qt.Key.Key_Backspace:
            if self._handle_dedent():
                return
        if key in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            self._handle_newline(event)
            return
        text = event.text()
        if text and not mods & ctrl:
            # cek penutup DULU: karakter seperti '"' ada di PAIRS sekaligus
            # _CLOSERS — mengetiknya di depan penutup harus melompati
            # (overtype), bukan membuat pasangan baru yang menduplikat.
            if text in _CLOSERS:
                if self._skip_closer(text):
                    return
            if text in PAIRS:
                self._insert_pair(text, PAIRS[text])
                return
        super().keyPressEvent(event)

    def _handle_tab(self, shift):
        cursor = self.textCursor()
        if shift:
            # dedent: hapus hingga 4 spasi di awal baris
            block_text = cursor.block().text()
            pos = cursor.positionInBlock()
            leading = len(block_text) - len(block_text.lstrip(" "))
            to_remove = min(4, leading, pos)
            for _ in range(to_remove):
                cursor.deletePreviousChar()
            return
        if cursor.hasSelection():
            self._indent_selection(1)
            return
        if self._jump_out_pair():
            return
        self.insertPlainText(" " * self._tab_width)

    def _indent_selection(self, direction):
        cursor = self.textCursor()
        doc = self.document()
        start = cursor.selectionStart()
        end = cursor.selectionEnd()
        first = doc.findBlock(start)
        last = doc.findBlock(end)
        # jangan ikutkan blok kosong terakhir (paragraf penutup QPlainTextEdit)
        if last.text() == "" and last == doc.lastBlock() and first != last:
            last = last.previous()
        first_num = first.blockNumber()
        last_num = max(first_num, last.blockNumber())
        cursor.beginEditBlock()
        for n in range(first_num, last_num + 1):
            block = doc.findBlockByNumber(n)
            c = QTextCursor(block)
            c.movePosition(QTextCursor.MoveOperation.StartOfBlock)
            if direction > 0:
                c.insertText(" " * self._tab_width)
            else:
                block_text = c.block().text()
                if block_text.startswith(" " * self._tab_width):
                    c.movePosition(QTextCursor.MoveOperation.Right,
                                   QTextCursor.MoveMode.KeepAnchor,
                                   self._tab_width)
                    c.removeSelectedText()
        cursor.endEditBlock()
        self._restore_block_selection(first_num, last_num)

    def _restore_block_selection(self, first_num, last_num):
        """Seleksi ulang dari awal blok pertama sampai akhir blok terakhir."""
        doc = self.document()
        first = doc.findBlockByNumber(first_num)
        last = doc.findBlockByNumber(last_num)
        if not first.isValid() or not last.isValid():
            return
        c = QTextCursor(first)
        c.movePosition(QTextCursor.MoveOperation.StartOfBlock)
        end = QTextCursor(last)
        end.movePosition(QTextCursor.MoveOperation.EndOfBlock)
        c.setPosition(end.position(), QTextCursor.MoveMode.KeepAnchor)
        self.setTextCursor(c)

    def _handle_dedent(self):
        cursor = self.textCursor()
        if cursor.hasSelection():
            return False
        block_text = cursor.block().text()
        pos = cursor.positionInBlock()
        leading = len(block_text) - len(block_text.lstrip(" "))
        if 0 < pos <= leading and pos % self._tab_width == 0:
            for _ in range(self._tab_width):
                cursor.deletePreviousChar()
            return True
        return False

    def _handle_newline(self, event):
        cursor = self.textCursor()
        block = cursor.block()
        line = block.text()
        indent = line[: len(line) - len(line.lstrip(" "))]
        stripped = line.strip()
        extra = ""
        if self._language == "python" and stripped.endswith(":"):
            extra = " " * self._tab_width
        elif stripped.endswith(("{", "(", "[")):
            extra = " " * self._tab_width
        self.insertPlainText("\n" + indent + extra)

    def _insert_pair(self, opener, closer):
        cursor = self.textCursor()
        if cursor.hasSelection():
            selected = cursor.selectedText()
            cursor.insertText(opener + selected + closer)
            # kembalikan posisi kursor ke tengah
            c = self.textCursor()
            c.setPosition(cursor.selectionStart() + len(opener) + len(selected))
            self.setTextCursor(c)
            return
        cursor.insertText(opener + closer)
        c = self.textCursor()
        c.movePosition(QTextCursor.MoveOperation.Left)
        self.setTextCursor(c)

    def _skip_closer(self, closer):
        cursor = self.textCursor()
        # seleksi aktif = bungkus pasangan (via _insert_pair), bukan skip
        if cursor.hasSelection():
            return False
        c = self.document().characterAt(cursor.position())
        if c == closer:
            cursor.movePosition(QTextCursor.MoveOperation.Right)
            self.setTextCursor(cursor)
            return True
        return False

    def _jump_out_pair(self):
        """Tab stop: Tab di depan penutup pasangan (kurung/kutip) melompat
        melewatinya alih-alih menyisipkan spasi. Hanya jika karakter di
        kanan kursor memang penutup: kurung asimetris wajib punya pembuka
        yang cocok; kutip simetris harus berjumlah ganjil sebelum kursor
        (genap berarti karakter itu justru pembuka — jangan dilompati)."""
        cursor = self.textCursor()
        if cursor.hasSelection():
            return False
        pos = cursor.position()
        closer = self.document().characterAt(pos)
        if closer not in _CLOSERS:
            return False
        text = self.document().toPlainText()
        if PAIRS.get(closer) == closer:
            if text[:pos].count(closer) % 2 == 0:
                return False
        elif _find_backward(text, pos, closer) < 0:
            return False
        cursor.movePosition(QTextCursor.MoveOperation.Right)
        self.setTextCursor(cursor)
        return True

    # -------------------------------------------------------- multi-kursor
    def cursor_count(self):
        """Jumlah kursor aktif (utama + ekstra)."""
        return 1 + len(self._extra_cursors)

    def _multi_ranges(self):
        """Rentang semua kursor [(start, end, is_main)] terurut menaik."""
        c = self.textCursor()
        items = [(c.selectionStart(), c.selectionEnd(), True)]
        items.extend((s, e, False) for s, e in self._extra_cursors)
        return sorted(items)

    def _clear_extra_cursors(self):
        if not self._extra_cursors:
            return
        self._extra_cursors = []
        self._refresh_extra()

    def _remove_last_cursor(self):
        """Ctrl+U: buang kursor ekstra terakhir, kursor utama pindah ke sana."""
        if not self._extra_cursors:
            return
        start, end = self._extra_cursors.pop()
        c = self.textCursor()
        c.setPosition(start)
        c.setPosition(end, QTextCursor.MoveMode.KeepAnchor)
        self.setTextCursor(c)
        self._refresh_extra()

    def _add_next_occurrence(self):
        """Ctrl+D: pilih kata di kursor; tekan lagi untuk menambahkan
        kemunculan berikutnya (wrap ke awal dokumen bila habis)."""
        c = self.textCursor()
        if not c.hasSelection():
            # mulai urutan baru: buang kursor ekstra kosong yang basi
            self._extra_cursors = [r for r in self._extra_cursors
                                   if r[0] != r[1]]
            word = self._word_under_cursor()
            if word is None:
                return
            start, end = word
            c.setPosition(start)
            c.setPosition(end, QTextCursor.MoveMode.KeepAnchor)
            self.setTextCursor(c)
            return
        term = c.selectedText().replace("\u2029", "\n")
        if not term:
            return
        text = self.document().toPlainText()
        ranges = self._multi_ranges()
        last = max(end for _s, end, _m in ranges)
        pos = text.find(term, last)
        if pos < 0:
            pos = text.find(term)  # wrap: cari dari awal dokumen
        if pos < 0:
            return
        new_end = pos + len(term)
        if any(s == pos and e == new_end for s, e, _m in ranges):
            return
        self._extra_cursors = [[s, e] for s, e, _m in ranges if s != e]
        nc = self.textCursor()
        nc.setPosition(pos)
        nc.setPosition(new_end, QTextCursor.MoveMode.KeepAnchor)
        self.setTextCursor(nc)
        self._refresh_extra()

    def _word_under_cursor(self):
        """Kembalikan (start, end) kata di bawah kursor, atau None."""
        pos = self.textCursor().position()
        text = self.document().toPlainText()
        n = len(text)
        if n == 0 or pos > n:
            return None

        def is_word(ch):
            return ch.isalnum() or ch == "_"

        p = pos
        if p >= n or not is_word(text[p]):
            p -= 1
        if p < 0 or not is_word(text[p]):
            return None
        start = p
        while start > 0 and is_word(text[start - 1]):
            start -= 1
        end = p
        while end < n and is_word(text[end]):
            end += 1
        return start, end

    def _handle_multi_key(self, event):
        """Tangani tombol saat multi-kursor aktif; False = keluar mode."""
        key = event.key()
        mods = event.modifiers()
        ctrl = Qt.KeyboardModifier.ControlModifier
        if key == Qt.Key.Key_Escape:
            self._clear_extra_cursors()
            return True
        if key == Qt.Key.Key_Backspace:
            self._multi_delete_text(back=True)
            return True
        if key == Qt.Key.Key_Delete:
            self._multi_delete_text(back=False)
            return True
        if key in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            self._multi_insert_text("\n")
            return True
        if key == Qt.Key.Key_Tab and not (mods & Qt.KeyboardModifier.ShiftModifier):
            self._multi_insert_text(" " * self._tab_width)
            return True
        if key == Qt.Key.Key_V and mods & ctrl:
            text = QApplication.clipboard().text()
            if text:
                self._multi_insert_text(text)
            return True
        text = event.text()
        if not text or mods & ctrl:
            return False
        if text in PAIRS:
            self._multi_insert_pair(text, PAIRS[text])
            return True
        if text in _CLOSERS:
            self._multi_insert_closer(text)
            return True
        self._multi_insert_text(text)
        return True

    def _multi_insert_text(self, text):
        """Sisipkan text di semua kursor (seleksi diganti), dari bawah ke atas."""
        results = []
        for start, end, is_main in reversed(self._multi_ranges()):
            c = QTextCursor(self.document())
            c.setPosition(start)
            c.setPosition(end, QTextCursor.MoveMode.KeepAnchor)
            c.insertText(text)
            d = len(text) - (end - start)
            results.append((c.position(), is_main, d))
        self._finish_multi_edit(results)

    def _multi_insert_pair(self, opener, closer):
        """Bungkus seleksi di semua kursor dengan pasangan pembuka/penutup."""
        results = []
        for start, end, is_main in reversed(self._multi_ranges()):
            c = QTextCursor(self.document())
            c.setPosition(start)
            c.setPosition(end, QTextCursor.MoveMode.KeepAnchor)
            if start != end:
                selected = c.selectedText()
                c.insertText(opener + selected + closer)
            else:
                c.insertText(opener + closer)
            results.append((c.position(), is_main, 2))
        self._finish_multi_edit(results)

    def _multi_insert_closer(self, closer):
        """Sisipkan penutup di semua kursor; lompati penutup yang sudah ada."""
        results = []
        for start, end, is_main in reversed(self._multi_ranges()):
            c = QTextCursor(self.document())
            c.setPosition(start)
            c.setPosition(end, QTextCursor.MoveMode.KeepAnchor)
            if start == end and self.document().characterAt(end) == closer:
                c.setPosition(end + 1)
                results.append((c.position(), is_main, 0))
            else:
                c.insertText(closer)
                results.append((c.position(), is_main, 1))
        self._finish_multi_edit(results)

    def _multi_delete_text(self, back):
        """Backspace/Delete di semua kursor (hapus seleksi atau satu karakter)."""
        results = []
        for start, end, is_main in reversed(self._multi_ranges()):
            c = QTextCursor(self.document())
            c.setPosition(start)
            c.setPosition(end, QTextCursor.MoveMode.KeepAnchor)
            if start != end:
                c.removeSelectedText()
                d = -(end - start)
            else:
                before = self.document().characterCount()
                if back:
                    c.deletePreviousChar()
                else:
                    c.deleteChar()
                d = self.document().characterCount() - before
            results.append((c.position(), is_main, d))
        self._finish_multi_edit(results)

    def _finish_multi_edit(self, results):
        """Perbarui kursor setelah edit multi. results = [(posisi, is_main,
        delta_karakter)]; posisi yang lebih besar digeser oleh edit yang
        posisinya lebih kecil, jadi koreksi dilakukan lewat akumulasi delta."""
        items = sorted(results)
        acc = 0
        corrected = []
        for q, is_main, d in items:
            corrected.append((q + acc, is_main))
            acc += d
        corrected.sort()
        main_pos = next(p for p, is_main in corrected if is_main)
        self._extra_cursors = [[p, p] for p, is_main in corrected
                               if not is_main]
        c = self.textCursor()
        c.setPosition(main_pos)
        self.setTextCursor(c)
        self._refresh_extra()

    def toggle_comment(self):
        prefix = _COMMENT_TOGGLE.get(self._language, "//")
        cursor = self.textCursor()
        doc = self.document()
        start = cursor.selectionStart()
        end = cursor.selectionEnd()
        has_sel = cursor.hasSelection()
        first = doc.findBlock(start)
        last = doc.findBlock(end)
        # jangan ikutkan blok kosong terakhir (paragraf penutup QPlainTextEdit)
        if last.text() == "" and last == doc.lastBlock() and first != last:
            last = last.previous()
        first_num = first.blockNumber()
        last_num = max(first_num, last.blockNumber())

        lines = [doc.findBlockByNumber(n) for n in range(first_num,
                                                         last_num + 1)]
        all_commented = all(
            b.text().strip().startswith(prefix) for b in lines)
        cursor.beginEditBlock()
        for n in range(first_num, last_num + 1):
            block = doc.findBlockByNumber(n)
            c = QTextCursor(block)
            c.movePosition(QTextCursor.MoveOperation.StartOfBlock)
            if all_commented:
                text = c.block().text()
                # lewati spasi di awal baris, baru hapus prefix komentar
                while c.positionInBlock() < len(text) and \
                        text[c.positionInBlock()].isspace():
                    c.movePosition(QTextCursor.MoveOperation.Right)
                c.movePosition(QTextCursor.MoveOperation.Right,
                               QTextCursor.MoveMode.KeepAnchor, len(prefix))
                c.removeSelectedText()
            else:
                c.insertText(prefix)
        cursor.endEditBlock()

        # pulihkan seleksi (kira-kira) mencakup baris yang disentuh
        if has_sel:
            self._restore_block_selection(first_num, last_num)

    def go_to_line(self, line_number):
        if line_number < 1:
            return
        block = self.document().findBlockByNumber(line_number - 1)
        if not block.isValid():
            return
        cursor = QTextCursor(block)
        cursor.movePosition(QTextCursor.MoveOperation.StartOfBlock)
        self.setTextCursor(cursor)
        self.centerCursor()
        self.setFocus()

    # ------------------------------------------------------------ appearance
    def apply_theme(self, theme):
        self._theme = theme
        self._search_color = QColor(theme["selection"])
        self._apply_editor_colors()
        if self._highlighter is not None:
            self._highlighter.set_theme(theme)
        self._refresh_extra()
        self._line_area.update()

    def _apply_editor_colors(self):
        # setStyleSheet() menandai dokumen sebagai modified — pertahankan
        # status aslinya agar tab baru tidak terlihat "belum disimpan".
        doc = self.document()
        was_modified = doc.isModified()
        t = self._theme
        self.setStyleSheet(
            f"QPlainTextEdit {{ background: {t['bg']}; color: {t['fg']}; "
            f"selection-background-color: {t['selection']}; "
            f"selection-color: {t['fg']}; }}")
        doc.setModified(was_modified)

    def set_language(self, lang):
        self._language = lang if lang in LANG_NAMES else "plain"
        if self._highlighter is not None:
            self._highlighter.set_language(self._language)

    # ------------------------------------------------------------ file io
    def file_path(self):
        return self._file_path

    def display_name(self):
        if self._file_path:
            return os.path.basename(self._file_path)
        return "Tanpa Judul"

    def load(self, path):
        try:
            with open(path, "rb") as f:
                raw = f.read()
        except OSError as exc:
            return False, str(exc)
        text, encoding = _decode(raw)
        self.setPlainText(text)
        self._extra_cursors = []
        self._file_path = path
        self._encoding = encoding
        self.set_language(detect_language(path))
        self.document().setModified(False)
        self._on_cursor_moved()
        return True, None

    def save(self, path=None):
        target = path or self._file_path
        if not target:
            return False, "Tidak ada path file."
        try:
            content = self.toPlainText()
            data = content.encode(self._encoding, errors="replace")
            with open(target, "wb") as f:
                f.write(data)
        except OSError as exc:
            return False, str(exc)
        self._file_path = target
        self.set_language(detect_language(target))
        self.document().setModified(False)
        return True, None

    def set_encoding_name(self):
        return self._encoding

    # ---------------------------------------------------------------- find
    def _compile_find(self, query, flags, use_regex):
        """Kompliasi pola pencarian (regex atau literal) jadi QRegularExpression."""
        opts = QRegularExpression.PatternOption.UseUnicodePropertiesOption
        if not (flags & QTextDocument.FindFlag.FindCaseSensitively):
            opts |= QRegularExpression.PatternOption.CaseInsensitiveOption
        pattern = query if use_regex else QRegularExpression.escape(query)
        if flags & QTextDocument.FindFlag.FindWholeWords:
            pattern = r"\b(?:%s)\b" % pattern
        rx = QRegularExpression(pattern, opts)
        return rx if rx.isValid() else None

    def count_matches(self, query, flags, use_regex=False):
        if not query:
            return 0
        rx = self._compile_find(query, flags, use_regex)
        if rx is None:
            return 0
        doc = self.document()
        count = 0
        pos = 0
        while True:
            c = doc.find(rx, pos, flags)
            if c.isNull():
                break
            count += 1
            pos = c.selectionEnd() if c.selectionEnd() > pos else pos + 1
        return count

    def set_search_matches(self, query, flags, color=None, use_regex=False):
        self._search_query = query
        self._search_flags = flags
        self._search_use_regex = use_regex
        if color is not None:
            self._search_color = color
        self._refresh_extra()

    def find_next(self, query, flags, use_regex=False):
        rx = self._compile_find(query, flags, use_regex)
        if rx is None:
            return False
        return self.find(rx, flags)

    def find_prev(self, query, flags, use_regex=False):
        rx = self._compile_find(query, flags, use_regex)
        if rx is None:
            return False
        return self.find(rx, flags | QTextDocument.FindFlag.FindBackward)

    def replace_current(self, query, replacement, flags=None, use_regex=False):
        cursor = self.textCursor()
        if not cursor.hasSelection():
            return False
        sel = cursor.selectedText()
        if use_regex:
            rx = self._compile_find(query, flags or QTextDocument.FindFlags(),
                                    True)
            if rx is None:
                return False
            m = rx.match(sel)
            if not m.hasMatch() or m.capturedStart() != 0 \
                    or m.capturedEnd() != len(sel):
                return False
        elif sel != query:
            return False
        cursor.insertText(replacement)
        return True

    def replace_all(self, query, replacement, flags, use_regex=False):
        if not query:
            return 0
        rx = self._compile_find(query, flags, use_regex)
        if rx is None:
            return 0
        doc = self.document()
        count = 0
        pos = 0
        while True:
            c = doc.find(rx, pos, flags)
            if c.isNull():
                break
            c.beginEditBlock()
            c.insertText(replacement)
            c.endEditBlock()
            count += 1
            pos = c.position() if c.position() > pos else pos + 1
        self._extra_cursors = []
        self._refresh_extra()
        return count

    # ------------------------------------------------------------- display
    def _collect_matches(self):
        ranges = []
        if not self._search_query:
            return ranges
        rx = self._compile_find(self._search_query, self._search_flags,
                                self._search_use_regex)
        if rx is None:
            return ranges
        doc = self.document()
        pos = 0
        while True:
            c = doc.find(rx, pos, self._search_flags)
            if c.isNull():
                break
            ranges.append((c.selectionStart(), c.selectionEnd()))
            pos = c.selectionEnd() if c.selectionEnd() > pos else pos + 1
        return ranges

    def _refresh_extra(self):
        extras = []
        t = self._theme
        # baris aktif
        line_sel = QTextEdit.ExtraSelection()
        line_sel.format.setBackground(QColor(t["current_line"]))
        line_sel.format.setProperty(QTextFormat.FullWidthSelection, True)
        line_sel.cursor = self.textCursor()
        line_sel.cursor.clearSelection()
        extras.append(line_sel)
        # pasangan kurung
        for a, b in self._bracket_pairs():
            for pos in (a, b):
                sel = QTextEdit.ExtraSelection()
                sel.format.setBackground(QColor(t["ui"].get("accent", "#888888")))
                sel.format.setForeground(QColor(t["fg"]))
                sel.format.setFontWeight(700)
                c = QTextCursor(self.document())
                c.setPosition(pos)
                c.movePosition(QTextCursor.MoveOperation.Right,
                               QTextCursor.MoveMode.KeepAnchor)
                sel.cursor = c
                extras.append(sel)
        # hasil pencarian
        for s, e in self._collect_matches():
            sel = QTextEdit.ExtraSelection()
            sel.format.setBackground(self._search_color)
            sel.format.setForeground(QColor(t["fg"]))
            c = QTextCursor(self.document())
            c.setPosition(s)
            c.setPosition(e, QTextCursor.MoveMode.KeepAnchor)
            sel.cursor = c
            extras.append(sel)
        # kursor multi (Ctrl+D) — seleksi sekunder lebih redup dari utama
        if self._extra_cursors:
            extra_color = QColor(t["selection"])
            extra_color.setAlpha(120)
            for s, e in self._extra_cursors:
                sel = QTextEdit.ExtraSelection()
                sel.format.setBackground(extra_color)
                c = QTextCursor(self.document())
                c.setPosition(s)
                c.setPosition(e, QTextCursor.MoveMode.KeepAnchor)
                sel.cursor = c
                extras.append(sel)
        self.setExtraSelections(extras)

    def _bracket_pairs(self):
        """Kembalikan posisi pasangan kurung di sekitar kursor (jika ada)."""
        cursor = self.textCursor()
        doc = self.document()
        pos = cursor.position()
        text = doc.toPlainText()
        n = len(text)
        char = None
        start = -1
        for candidate in (pos - 1, pos):
            if 0 <= candidate < n:
                ch = text[candidate]
                if ch in PAIRS or ch in _CLOSERS:
                    char = ch
                    start = candidate
                    break
        if char is None:
            return []
        if PAIRS.get(char) == char:
            # pasangan simetris (kutip): coba sebagai pembuka, lalu penutup
            match = _find_forward(text, start, char, char)
            if match >= 0:
                return [(start, match)]
            match = _find_backward(text, start, char)
            if match >= 0:
                return [(match, start)]
            return []
        if char in PAIRS:
            match = _find_forward(text, start, char, PAIRS[char])
            if match >= 0:
                return [(start, match)]
        elif char in _CLOSERS:
            match = _find_backward(text, start, char)
            if match >= 0:
                return [(match, start)]
        return []

    def _refresh_current_line(self):
        self._line_area.update()

    def _on_cursor_moved(self, *_):
        self._refresh_extra()
        self._line_area.update()

    # -------------------------------------------------------------- status
    def cursor_info(self):
        cursor = self.textCursor()
        line = cursor.blockNumber() + 1
        col = cursor.positionInBlock() + 1
        sel_len = len(cursor.selectedText()) if cursor.hasSelection() else 0
        return line, col, sel_len

    def stats(self):
        text = self.toPlainText()
        words = len(text.split()) if text.strip() else 0
        return words, len(text)

    def mousePressEvent(self, event):
        # klik menempatkan ulang kursor — akhiri mode multi-kursor
        if self._extra_cursors:
            self._clear_extra_cursors()
        super().mousePressEvent(event)

    def focusInEvent(self, event):
        self.focused.emit()
        super().focusInEvent(event)


# ------------------------------------------------------------- helpers
def _find_forward(text, start, opener, closer):
    n = len(text)
    if opener == closer:
        # pasangan simetris (kutip): kemunculan pertama = pembuka, kemunculan
        # berikutnya menurunkan kedalaman sampai 0 = penutupnya.
        depth = 0
        i = start
        while i < n:
            if text[i] == opener:
                if depth == 0:
                    depth = 1
                else:
                    depth -= 1
                    if depth == 0:
                        return i
            i += 1
        return -1
    depth = 0
    i = start
    while i < n:
        ch = text[i]
        if ch == opener:
            depth += 1
        elif ch == closer:
            depth -= 1
            if depth == 0:
                return i
        i += 1
    return -1


def _find_backward(text, start, closer):
    opener = {v: k for k, v in PAIRS.items()}.get(closer)
    if opener is None:
        return -1
    if opener == closer:
        # pasangan simetris: kemunculan di start = penutup, kemunculan
        # sebelumnya menurunkan kedalaman sampai 0 = pembukanya.
        depth = 0
        i = start
        while i >= 0:
            if text[i] == closer:
                if depth == 0:
                    depth = 1
                else:
                    depth -= 1
                    if depth == 0:
                        return i
            i -= 1
        return -1
    depth = 0
    i = start
    while i >= 0:
        ch = text[i]
        if ch == closer:
            depth += 1
        elif ch == opener:
            depth -= 1
            if depth == 0:
                return i
        i -= 1
    return -1


def _decode(raw):
    """Deteksi encoding file (BOM, UTF-8, lalu fallback cp1252)."""
    if raw.startswith(b"\xef\xbb\xbf"):
        return raw.decode("utf-8-sig"), "utf-8-sig"
    try:
        return raw.decode("utf-8"), "utf-8"
    except UnicodeDecodeError:
        return raw.decode("cp1252", errors="replace"), "cp1252"
