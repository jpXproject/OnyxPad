"""Syntax highlighting multi-bahasa untuk NotepadBlack.

Strategi: aturan regex per bahasa (string & komentar baris diproses TERAKHIR lewat
sweeper agar `#`/`//` di dalam string tidak ikut ter-warnai), plus state machine
untuk string tiga-kutip (Python) dan komentar blok (C-like/CSS).
"""

import os
import re

from PySide6.QtGui import QColor, QFont, QSyntaxHighlighter, QTextCharFormat

LANG_EXT = {
    ".py": "python", ".pyw": "python", ".js": "javascript", ".mjs": "javascript",
    ".jsx": "javascript", ".ts": "typescript", ".tsx": "typescript",
    ".html": "html", ".htm": "html", ".css": "css", ".scss": "css", ".less": "css",
    ".c": "c", ".h": "c", ".cpp": "cpp", ".cc": "cpp", ".hpp": "cpp",
    ".java": "java", ".json": "json", ".md": "markdown", ".markdown": "markdown",
    ".sh": "shell", ".bash": "shell", ".yaml": "yaml", ".yml": "yaml",
    ".txt": "plain", ".log": "plain",
}

LANG_NAMES = {
    "python": "Python", "javascript": "JavaScript", "typescript": "TypeScript",
    "html": "HTML", "css": "CSS", "c": "C", "cpp": "C++", "java": "Java",
    "json": "JSON", "markdown": "Markdown", "shell": "Shell", "yaml": "YAML",
    "plain": "Teks Biasa",
}

_PY_KEYWORDS = (r"\b(?:def|class|if|elif|else|for|while|return|import|from|as|"
                r"try|except|finally|with|lambda|pass|break|continue|global|"
                r"nonlocal|yield|raise|assert|del|in|not|and|or|is|None|True|"
                r"False|async|await|match|case)\b")
_PY_BUILTINS = (r"\b(?:print|len|range|int|str|float|list|dict|set|tuple|open|"
                r"type|isinstance|enumerate|zip|map|filter|sum|min|max|abs|"
                r"round|sorted|reversed|super|object|Exception|ValueError|"
                r"TypeError|KeyError|FileNotFoundError|input|repr|bool|bytes|"
                r"iter|next|self|cls)\b")

_JS_KEYWORDS = (r"\b(?:const|let|var|function|return|if|else|for|while|do|"
                r"switch|case|break|continue|default|new|class|extends|super|"
                r"this|typeof|instanceof|in|of|try|catch|finally|throw|async|"
                r"await|yield|import|export|from|delete|void|null|undefined|"
                r"true|false|interface|type|enum|implements|public|private|"
                r"readonly|static|abstract|namespace|declare)\b")

_CPP_KEYWORDS = (r"\b(?:int|char|float|double|void|bool|long|short|unsigned|"
                 r"signed|struct|class|enum|union|typedef|auto|const|static|"
                 r"extern|namespace|template|typename|public|private|protected|"
                 r"virtual|override|final|new|delete|this|nullptr|NULL|true|"
                 r"false|return|if|else|for|while|do|switch|case|break|continue|"
                 r"default|try|catch|throw|using|include|define|pragma|goto|"
                 r"sizeof|volatile|register|inline|friend|operator)\b")

_STRING_RE = r'"(?:[^"\\\n]|\\.)*"|\'(?:[^\'\\\n]|\\.)*\''
_PY_STRING_RE = (r'(?:[rbfuRBFU]{0,2})"(?:[^"\\\n]|\\.)*"|'
                 r'(?:[rbfuRBFU]{0,2})\'(?:[^\'\\\n]|\\.)*\'')
_NUMBER_RE = (r"\b0[xX][0-9a-fA-F_]+\b|\b0[bB][01_]+\b|\b0[oO][0-7_]+\b|"
              r"\b\d[\d_]*(?:\.[\d_]+)?(?:[eE][+-]?\d+)?\b")
_FUNC_CALL_RE = r"\b[A-Za-z_][A-Za-z0-9_]*(?=\s*\()"
_FUNC_DEF_RE = r"\b(def|function|fun)\s+([A-Za-z_][A-Za-z0-9_]*)\b"
_CLASS_DEF_RE = r"\b(class|klass)\s+([A-Za-z_][A-Za-z0-9_]*)\b"


def detect_language(filename):
    """Deteksi bahasa dari ekstensi file."""
    ext = os.path.splitext(filename or "")[1].lower()
    return LANG_EXT.get(ext, "plain")


# (regex, token_key, group) — group None berarti format seluruh match
def _rules_for(lang):
    r = []
    if lang == "python":
        r += [
            (re.compile(r"@[A-Za-z_][A-Za-z0-9_.]*"), "decorator", None),
            (re.compile(_PY_KEYWORDS), "keyword", None),
            (re.compile(_PY_BUILTINS), "builtin", None),
            (re.compile(_NUMBER_RE), "number", None),
            (re.compile(r"\bdef\s+([A-Za-z_][A-Za-z0-9_]*)\b"), "function", 1),
            (re.compile(r"\bclass\s+([A-Za-z_][A-Za-z0-9_]*)\b"), "klass", 1),
            (re.compile(_FUNC_CALL_RE), "function", None),
            (re.compile(_PY_STRING_RE), "string", None),
        ]
    elif lang in ("javascript", "typescript"):
        r += [
            (re.compile(_JS_KEYWORDS), "keyword", None),
            (re.compile(_NUMBER_RE), "number", None),
            (re.compile(r"\b(function|class)\s+([A-Za-z_][A-Za-z0-9_]*)\b"),
             "function", 2),
            (re.compile(_FUNC_CALL_RE), "function", None),
            (re.compile(r"`(?:[^`\\]|\\.)*`"), "string", None),
            (re.compile(_STRING_RE), "string", None),
        ]
    elif lang in ("c", "cpp", "java"):
        r += [
            (re.compile(_CPP_KEYWORDS), "keyword", None),
            (re.compile(_NUMBER_RE), "number", None),
            (re.compile(r"'(?:[^'\\\n]|\\.)*'"), "string", None),
            (re.compile(_STRING_RE), "string", None),
            (re.compile(_FUNC_CALL_RE), "function", None),
        ]
    elif lang == "html":
        r += [
            (re.compile(r"<[A-Za-z!/][^>]*>"), "tag", None),
            (re.compile(r"\b[A-Za-z_:][A-Za-z0-9_.:-]*(?==)"), "attribute", None),
            (re.compile(r"&[a-zA-Z#0-9]+;"), "constant", None),
            (re.compile(_STRING_RE), "string", None),
        ]
    elif lang in ("css", "scss", "less"):
        r += [
            (re.compile(r"[^{}\n]+(?=\{)"), "selector", None),
            (re.compile(r"\b[a-zA-Z-]+(?=\s*:)"), "property", None),
            (re.compile(r"@[\w-]+"), "keyword", None),
            (re.compile(r"\b\d+(?:\.\d+)?(?:px|em|rem|%|vh|vw|s|ms|deg|fr)?\b"),
             "number", None),
            (re.compile(_STRING_RE), "string", None),
        ]
    elif lang == "json":
        r += [
            (re.compile(r'"([^"]+)"(?=\s*:)'), "json_key", 1),
            (re.compile(r"\b(?:true|false|null)\b"), "constant", None),
            (re.compile(r"-?\b\d+(?:\.\d+)?(?:[eE][+-]?\d+)?\b"), "number", None),
            (re.compile(_STRING_RE), "string", None),
        ]
    elif lang == "markdown":
        r += [
            (re.compile(r"^#{1,6}\s.*$"), "heading", None),
            (re.compile(r"```.*$"), "code", None),
            (re.compile(r"`[^`\n]+`"), "code", None),
            (re.compile(r"\*\*[^*\n]+\*\*|__[^_\n]+__"), "bold", None),
            (re.compile(r"(?<!\*)\*[^*\n]+\*(?!\*)|(?<!_)_[^_\n]+_(?!_)"),
             "italic", None),
            (re.compile(r"\[[^\]\n]*\]\([^)\n]*\)"), "link", None),
            (re.compile(r"^\s*[-*+]\s+.*$"), "property", None),
            (re.compile(r"^\s*\d+\.\s+.*$"), "number", None),
        ]
    elif lang == "shell":
        r += [
            (re.compile(r"\b(?:if|then|else|elif|fi|for|while|do|done|case|"
                        r"esac|function|export|local|echo|cd|source|return|"
                        r"exit|shift|read|test)\b"), "keyword", None),
            (re.compile(r"\$[A-Za-z_][A-Za-z0-9_]*|\$\{[^}]*\}|\$\([^)]*\)"),
             "constant", None),
            (re.compile(_NUMBER_RE), "number", None),
            (re.compile(_STRING_RE), "string", None),
        ]
    elif lang == "yaml":
        r += [
            (re.compile(r"^\s*[A-Za-z0-9_\-]+(?=\s*:)"), "property", None),
            (re.compile(r"\b(?:true|false|null|yes|no|on|off)\b"), "constant", None),
            (re.compile(r"-?\b\d+(?:\.\d+)?\b"), "number", None),
            (re.compile(_STRING_RE), "string", None),
        ]
    return r

_COMMENT_MARKER = {
    "python": "#", "shell": "#", "javascript": "//", "typescript": "//",
    "c": "//", "cpp": "//", "java": "//",
}
_BLOCK_COMMENT_LANGS = ("c", "cpp", "java", "javascript", "typescript",
                        "css", "scss", "less")
_TRIPLE_QUOTE_LANGS = ("python",)


class Highlighter(QSyntaxHighlighter):
    def __init__(self, document, lang="plain", theme=None):
        super().__init__(document)
        self._lang = "plain"
        self._theme = theme
        self._cache = {}
        self.set_language(lang)

    # ---------- format helpers ----------
    def _fmt(self, key, bold=False, italic=False):
        theme = self._theme
        if theme is None:
            return QTextCharFormat()
        tokens = theme["tokens"]
        f = QTextCharFormat()
        f.setForeground(QColor(tokens.get(key, theme["fg"])))
        if bold:
            f.setFontWeight(QFont.Weight.Bold)
        if italic:
            f.setFontItalic(True)
        return f

    def _fmt_cached(self, key, bold=False, italic=False):
        cache_key = (key, bold, italic)
        if cache_key not in self._cache:
            self._cache[cache_key] = self._fmt(key, bold, italic)
        return self._cache[cache_key]

    # ---------- public ----------
    def set_theme(self, theme):
        self._theme = theme
        self._cache.clear()
        self._rebuild()
        self.rehighlight()

    def set_language(self, lang):
        known = ("python", "javascript", "typescript", "html", "css", "c",
                 "cpp", "java", "json", "markdown", "shell", "yaml", "plain")
        self._lang = lang if lang in known else "plain"
        self._rebuild()
        self.rehighlight()

    def language_name(self):
        return LANG_NAMES.get(self._lang, "Teks Biasa")

    def _rebuild(self):
        self._rules = [(rx, self._fmt_cached(key, bold=(key == "heading")),
                        grp) for rx, key, grp in _rules_for(self._lang)]
        self._fmt_comment = self._fmt_cached("comment", italic=True)
        self._fmt_string = self._fmt_cached("string")
        self._fmt_keyword = self._fmt_cached("keyword")

    # ---------- block highlighting ----------
    def highlightBlock(self, text):
        for rx, fmt, grp in self._rules:
            for m in rx.finditer(text):
                s = m.start(grp) if grp is not None else m.start()
                e = m.end(grp) if grp is not None else m.end()
                if s >= 0 and e > s:
                    self.setFormat(s, e - s, fmt)

        marker = _COMMENT_MARKER.get(self._lang)
        if marker:
            self._comment_sweep(text, marker)
        if self._lang in _BLOCK_COMMENT_LANGS:
            self._block_comment(text)
        if self._lang in _TRIPLE_QUOTE_LANGS:
            self._triple_quote(text, '"', 1)
            self._triple_quote(text, "'", 2)

    def _comment_sweep(self, text, marker):
        """Warnai komentar baris TAPI lewati bagian yang ada di dalam string."""
        in_str = None
        i = 0
        n = len(text)
        while i < n:
            ch = text[i]
            if in_str:
                if ch == "\\":
                    i += 2
                    continue
                if ch == in_str:
                    in_str = None
                i += 1
                continue
            if ch in "\"'":
                in_str = ch
                i += 1
                continue
            if text.startswith(marker, i):
                self.setFormat(i, n - i, self._fmt_comment)
                return
            i += 1

    def _block_comment(self, text):
        start = 0
        if self.previousBlockState() == 1:
            j = text.find("*/")
            if j == -1:
                self.setFormat(0, len(text), self._fmt_comment)
                self.setCurrentBlockState(1)
                return
            self.setFormat(0, j + 2, self._fmt_comment)
            start = j + 2
        i = text.find("/*", start)
        while i != -1:
            j = text.find("*/", i + 2)
            if j == -1:
                self.setFormat(i, len(text) - i, self._fmt_comment)
                self.setCurrentBlockState(1)
                return
            self.setFormat(i, j + 2 - i, self._fmt_comment)
            i = text.find("/*", j + 2)
        self.setCurrentBlockState(0)

    def _triple_quote(self, text, quote, state):
        q3 = quote * 3
        i = 0
        if self.previousBlockState() == state:
            j = text.find(q3)
            if j == -1:
                self.setFormat(0, len(text), self._fmt_string)
                self.setCurrentBlockState(state)
                return
            self.setFormat(0, j + 3, self._fmt_string)
            i = j + 3
        pat = re.compile(re.escape(q3) + r".*?" + re.escape(q3))
        m = pat.search(text, i)
        while m:
            self.setFormat(m.start(), m.end() - m.start(), self._fmt_string)
            m = pat.search(text, m.end())
        idx = text.find(q3, i)
        if idx != -1:
            self.setFormat(idx, len(text) - idx, self._fmt_string)
            self.setCurrentBlockState(state)
        else:
            self.setCurrentBlockState(0)
