"""Test untuk deteksi bahasa dan syntax highlighting."""

from PySide6.QtGui import QTextDocument

from src.syntax import Highlighter, LANG_EXT, LANG_NAMES, detect_language
from src.themes import THEMES, THEME_ORDER


class Recorder(Highlighter):
    """Merekam semua panggilan setFormat: (block_number, start, length, color)."""

    def __init__(self, document, lang="plain", theme=None):
        super().__init__(document, lang, theme)
        self.spans = []

    def setFormat(self, start, length, format_):
        color = format_.foreground().color().name().lower()
        self.spans.append((self.currentBlock().blockNumber(), start, length,
                           color))
        super().setFormat(start, length, format_)


def make_recorder(lang, theme=None):
    theme = theme or THEMES[THEME_ORDER[0]]
    doc = QTextDocument()
    recorder = Recorder(doc, lang, theme)
    return recorder, doc


def recolor(recorder, text):
    recorder.spans.clear()
    recorder.document().setPlainText(text)
    recorder.rehighlight()
    return list(recorder.spans)


def colors_of(spans, block=0):
    return {c for b, _s, _l, c in spans if b == block}


def spans_of(spans, block=0):
    return [(s, l) for b, s, l, _c in spans if b == block]


def token_color(theme, key):
    return theme["tokens"][key].lower()


# ------------------------------------------------------------ detect lang
def test_detect_language():
    cases = {
        "a.py": "python", "a.pyw": "python",
        "a.js": "javascript", "a.ts": "typescript",
        "a.html": "html", "a.css": "css",
        "a.c": "c", "a.cpp": "cpp", "a.java": "java",
        "a.json": "json", "a.md": "markdown",
        "a.sh": "shell", "a.yaml": "yaml",
        "a.xyz": "plain", "": "plain",
    }
    for filename, expected in cases.items():
        assert detect_language(filename) == expected, filename


def test_lang_ext_all_known():
    for ext, lang in LANG_EXT.items():
        assert lang in LANG_NAMES, ext


# ------------------------------------------------------------- highlight
def test_python_keyword_and_function():
    theme = THEMES[THEME_ORDER[0]]
    rec, doc = make_recorder("python", theme)
    spans = recolor(rec, "def foo():\n    return 1")
    colors = colors_of(spans, 0)
    kw = token_color(theme, "keyword")
    fn = token_color(theme, "function")
    assert kw in colors
    assert fn in colors
    assert kw in colors_of(spans, 1)  # "return"


def test_python_string_highlighted():
    theme = THEMES[THEME_ORDER[0]]
    rec, doc = make_recorder("python", theme)
    spans = recolor(rec, 's = "halo dunia"')
    assert token_color(theme, "string") in colors_of(spans, 0)


def test_comment_sweep_skips_strings():
    theme = THEMES[THEME_ORDER[0]]
    rec, doc = make_recorder("python", theme)
    spans = recolor(rec, 's = "a # b"  # komentar asli')
    st = token_color(theme, "string")
    cm = token_color(theme, "comment")
    # '#' di dalam string berada dalam span string, bukan komentar
    string_span = next((s, l) for s, l, c in
                       ((s, l, c) for _b, s, l, c in spans if _b == 0)
                       if c == st and s <= 5 < s + l)
    assert string_span is not None
    # masih ada komentar sungguhan yang terwarnai
    assert cm in colors_of(spans, 0)


def test_block_comment_multiline_c():
    theme = THEMES[THEME_ORDER[0]]
    rec, doc = make_recorder("c", theme)
    spans = recolor(rec, "/* mulai\nakhir */\nint x;")
    cm = token_color(theme, "comment")
    assert cm in colors_of(spans, 0)
    assert cm in colors_of(spans, 1)
    assert cm not in colors_of(spans, 2)


def test_triple_quote_python():
    theme = THEMES[THEME_ORDER[0]]
    rec, doc = make_recorder("python", theme)
    spans = recolor(rec, '"""baris1\nbaris2"""\nx = 1')
    st = token_color(theme, "string")
    assert st in colors_of(spans, 0)
    assert st in colors_of(spans, 1)
    assert st not in colors_of(spans, 2)


def test_json_key_highlighted():
    theme = THEMES[THEME_ORDER[0]]
    rec, doc = make_recorder("json", theme)
    spans = recolor(rec, '{"nama": "budi"}')
    assert token_color(theme, "json_key") in colors_of(spans, 0)


def test_theme_switch_recolors():
    t1 = THEMES["Dracula (Default)"]
    t2 = THEMES["Monokai"]
    rec, doc = make_recorder("python", t1)
    spans = recolor(rec, "def f():\n    pass")
    rec.set_theme(t2)
    rec.rehighlight()
    spans = list(rec.spans)
    assert token_color(t2, "keyword") in colors_of(spans, 0)


def test_set_language_rebuilds():
    theme = THEMES[THEME_ORDER[0]]
    rec, doc = make_recorder("python", theme)
    doc.setPlainText("def f(): return 1")
    rec.set_language("javascript")
    assert rec.language_name() == "JavaScript"


def test_plain_language_no_tokens():
    theme = THEMES[THEME_ORDER[0]]
    rec, doc = make_recorder("plain", theme)
    spans = recolor(rec, "def return 123")
    assert spans == []
