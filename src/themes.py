"""Palet tema OnyxPad — setiap tema punya warna editor, warna UI (QSS), dan warna token syntax."""

# Kunci token yang dipakai syntax.py
TOKEN_KEYS = [
    "keyword", "builtin", "string", "comment", "number", "function", "klass",
    "decorator", "operator", "preprocessor", "tag", "attribute", "heading",
    "bold", "italic", "link", "code", "json_key", "property", "selector",
    "datatype", "constant",
]

_DEFAULT_TOKENS = {
    "keyword": "#ff79c6", "builtin": "#8be9fd", "string": "#f1fa8c",
    "comment": "#6272a4", "number": "#bd93f9", "function": "#50fa7b",
    "klass": "#8be9fd", "decorator": "#ffb86c", "operator": "#ff79c6",
    "preprocessor": "#ffb86c", "tag": "#ff79c6", "attribute": "#50fa7b",
    "heading": "#ff79c6", "bold": "#f8f8f2", "italic": "#f8f8f2",
    "link": "#8be9fd", "code": "#f1fa8c", "json_key": "#8be9fd",
    "property": "#50fa7b", "selector": "#ff79c6", "datatype": "#bd93f9",
    "constant": "#bd93f9",
}

_DEFAULT_UI = {
    "window": "#21222c", "panel": "#282a36", "panel_alt": "#1e1f29",
    "text": "#f8f8f2", "muted": "#8a8f98", "accent": "#bd93f9",
    "border": "#3a3d4d", "tab_active": "#44475a", "tab_inactive": "#1e1f29",
    "hover": "#383a4a", "danger": "#ff5555", "input": "#191a21",
    "menu": "#21222c", "menu_sel": "#44475a",
}


def _theme(name, bg, fg, gutter_bg, gutter_fg, current_line, current_line_num,
           selection, ui, tokens):
    ui = {**_DEFAULT_UI, **ui}
    tokens = {**_DEFAULT_TOKENS, **tokens}
    return {
        "name": name, "bg": bg, "fg": fg,
        "gutter_bg": gutter_bg, "gutter_fg": gutter_fg,
        "current_line": current_line, "current_line_num": current_line_num,
        "selection": selection, "ui": ui, "tokens": tokens,
    }


THEMES = {
    "Dracula (Default)": _theme(
        "Dracula (Default)",
        "#282a36", "#f8f8f2", "#242632", "#6a6c7a", "#313442", "#f8f8f2",
        "#44475a",
        {"accent": "#bd93f9", "border": "#3a3d4d", "tab_active": "#44475a"},
        {},
    ),
    "One Dark": _theme(
        "One Dark",
        "#282c34", "#abb2bf", "#21252b", "#4b5263", "#2c313a", "#d19a66",
        "#3e4451",
        {"window": "#1e2229", "panel": "#282c34", "panel_alt": "#21252b",
         "accent": "#61afef", "muted": "#7f848e", "border": "#3a3f4b",
         "tab_active": "#3e4451", "tab_inactive": "#21252b",
         "hover": "#2c313a", "input": "#171a1f", "menu": "#1e2229",
         "menu_sel": "#3e4451"},
        {"keyword": "#c678dd", "builtin": "#56b6c2", "string": "#98c379",
         "comment": "#5c6370", "number": "#d19a66", "function": "#61afef",
         "klass": "#e5c07b", "decorator": "#d19a66", "operator": "#56b6c2",
         "preprocessor": "#d19a66", "tag": "#e06c75", "attribute": "#d19a66",
         "heading": "#e06c75", "bold": "#e06c75", "italic": "#c678dd",
         "link": "#61afef", "code": "#98c379", "json_key": "#e06c75",
         "property": "#61afef", "selector": "#e06c75",
         "datatype": "#e5c07b", "constant": "#d19a66"},
    ),
    "Monokai": _theme(
        "Monokai",
        "#272822", "#f8f8f2", "#1e1f1c", "#75715e", "#2d2e28", "#f8f8f2",
        "#49483e",
        {"window": "#1e1f1c", "panel": "#272822", "panel_alt": "#211f1c",
         "accent": "#a6e22e", "muted": "#75715e", "border": "#3a3a33",
         "tab_active": "#49483e", "tab_inactive": "#1e1f1c",
         "hover": "#33342c", "input": "#171813", "menu": "#1e1f1c",
         "menu_sel": "#49483e"},
        {"keyword": "#f92672", "builtin": "#a6e22e", "string": "#e6db74",
         "comment": "#75715e", "number": "#ae81ff", "function": "#a6e22e",
         "klass": "#66d9ef", "decorator": "#a6e22e", "operator": "#f92672",
         "preprocessor": "#a6e22e", "tag": "#f92672", "attribute": "#a6e22e",
         "heading": "#f92672", "bold": "#f92672", "italic": "#66d9ef",
         "link": "#66d9ef", "code": "#e6db74", "json_key": "#66d9ef",
         "property": "#a6e22e", "selector": "#f92672", "datatype": "#66d9ef",
         "constant": "#ae81ff"},
    ),
    "Matrix Green": _theme(
        "Matrix Green",
        "#000000", "#00ff00", "#020d02", "#00aa00", "#051505", "#00ff00",
        "#003a00",
        {"window": "#000000", "panel": "#020d02", "panel_alt": "#010701",
         "accent": "#00ff00", "muted": "#008800", "border": "#003a00",
         "tab_active": "#052505", "tab_inactive": "#010701",
         "hover": "#052505", "input": "#000000", "menu": "#000000",
         "menu_sel": "#052505"},
        {"keyword": "#00ff00", "builtin": "#00dd00", "string": "#00cc00",
         "comment": "#005500", "number": "#00ff88", "function": "#00ff00",
         "klass": "#00ffcc", "decorator": "#00ff88", "operator": "#00ff00",
         "preprocessor": "#00ff88", "tag": "#00ff00", "attribute": "#00dd00",
         "heading": "#00ff00", "bold": "#00ff00", "italic": "#00dd00",
         "link": "#00ffff", "code": "#00cc00", "json_key": "#00dd00",
         "property": "#00ff00", "selector": "#00ff00", "datatype": "#00ffcc",
         "constant": "#00ff88"},
    ),
    "Nord": _theme(
        "Nord",
        "#2e3440", "#d8dee9", "#2b303b", "#616e88", "#3b4252", "#eceff4",
        "#434c5e",
        {"window": "#242933", "panel": "#2e3440", "panel_alt": "#2b303b",
         "accent": "#88c0d0", "muted": "#7b88a1", "border": "#3b4252",
         "tab_active": "#434c5e", "tab_inactive": "#242933",
         "hover": "#3b4252", "input": "#1f242e", "menu": "#242933",
         "menu_sel": "#434c5e"},
        {"keyword": "#81a1c1", "builtin": "#88c0d0", "string": "#a3be8c",
         "comment": "#616e88", "number": "#b48ead", "function": "#88c0d0",
         "klass": "#ebcb8b", "decorator": "#d08770", "operator": "#81a1c1",
         "preprocessor": "#d08770", "tag": "#81a1c1", "attribute": "#ebcb8b",
         "heading": "#88c0d0", "bold": "#d8dee9", "italic": "#d8dee9",
         "link": "#5e81ac", "code": "#a3be8c", "json_key": "#8fbcbb",
         "property": "#88c0d0", "selector": "#81a1c1", "datatype": "#ebcb8b",
         "constant": "#b48ead"},
    ),
    "Solarized Dark": _theme(
        "Solarized Dark",
        "#002b36", "#839496", "#00222c", "#586e75", "#073642", "#93a1a1",
        "#073642",
        {"window": "#001b22", "panel": "#002b36", "panel_alt": "#00222c",
         "accent": "#268bd2", "muted": "#586e75", "border": "#073642",
         "tab_active": "#073642", "tab_inactive": "#001b22",
         "hover": "#073642", "input": "#00141a", "menu": "#001b22",
         "menu_sel": "#073642"},
        {"keyword": "#859900", "builtin": "#2aa198", "string": "#2aa198",
         "comment": "#586e75", "number": "#d33682", "function": "#268bd2",
         "klass": "#b58900", "decorator": "#cb4b16", "operator": "#859900",
         "preprocessor": "#cb4b16", "tag": "#268bd2", "attribute": "#b58900",
         "heading": "#268bd2", "bold": "#93a1a1", "italic": "#93a1a1",
         "link": "#268bd2", "code": "#2aa198", "json_key": "#859900",
         "property": "#268bd2", "selector": "#859900", "datatype": "#b58900",
         "constant": "#d33682"},
    ),
    "Light": _theme(
        "Light",
        "#ffffff", "#1f2430", "#f0f0f0", "#8a8f98", "#f2f4f8", "#1f2430",
        "#cfe3ff",
        {"window": "#f0f2f5", "panel": "#ffffff", "panel_alt": "#f0f0f0",
         "accent": "#2563eb", "muted": "#6b7280", "border": "#d7dbe0",
         "tab_active": "#ffffff", "tab_inactive": "#e5e7eb",
         "hover": "#eef1f5", "input": "#ffffff", "menu": "#ffffff",
         "menu_sel": "#e5e7eb"},
        {"keyword": "#9d1bb0", "builtin": "#0070c0", "string": "#0a7b0a",
         "comment": "#8a8f98", "number": "#c9771e", "function": "#0057a6",
         "klass": "#c9771e", "decorator": "#b15a00", "operator": "#9d1bb0",
         "preprocessor": "#b15a00", "tag": "#c22e2e", "attribute": "#0a7b0a",
         "heading": "#9d1bb0", "bold": "#1f2430", "italic": "#1f2430",
         "link": "#0057a6", "code": "#0a7b0a", "json_key": "#c22e2e",
         "property": "#0057a6", "selector": "#c22e2e", "datatype": "#c9771e",
         "constant": "#c9771e"},
    ),
}

THEME_ORDER = [
    "Dracula (Default)", "One Dark", "Monokai", "Matrix Green",
    "Nord", "Solarized Dark", "Light",
]


def build_qss(ui):
    """Bangun stylesheet global dari token UI tema."""
    tpl = """
QMainWindow, QDialog { background: @window; }
QMenuBar { background: @window; color: @text; border-bottom: 1px solid @border; }
QMenuBar::item { background: transparent; padding: 4px 10px; border-radius: 3px; }
QMenuBar::item:selected { background: @hover; }
QMenuBar::item:pressed { background: @menu_sel; }
QMenu { background: @menu; color: @text; border: 1px solid @border; }
QMenu::item { padding: 5px 24px 5px 14px; }
QMenu::item:selected { background: @menu_sel; color: @text; }
QMenu::separator { height: 1px; background: @border; margin: 4px 10px; }
QStatusBar { background: @window; border-top: 1px solid @border; }
QStatusBar QLabel { color: @muted; padding: 0 6px; font-size: 11px; }
QStatusBar QLabel#sbHighlight { color: @accent; font-weight: bold; }
QTabWidget::pane { border: none; background: @panel; }
QTabBar { background: @panel_alt; }
QTabBar::tab { background: @tab_inactive; color: @muted; padding: 5px 12px;
  border: none; border-right: 1px solid @border; min-width: 80px; }
QTabBar::tab:selected { background: @tab_active; color: @text;
  border-bottom: 2px solid @accent; }
QTabBar::tab:hover:!selected { background: @hover; color: @text; }
QTabBar::close-button { image: none; }
QSplitter::handle { background: @border; }
QSplitter::handle:hover { background: @accent; }
QDockWidget { color: @text; titlebar-close-icon: none; }
QDockWidget::title { background: @panel_alt; padding: 5px 8px;
  border-bottom: 1px solid @border; font-weight: bold; }
QTreeView { background: @panel; color: @text; border: none; outline: none; }
QTreeView::item { padding: 2px; }
QTreeView::item:selected { background: @accent; color: @window; }
QTreeView::item:hover { background: @hover; }
QLineEdit, QPlainTextEdit, QTextEdit { background: @input; color: @text;
  border: 1px solid @border; border-radius: 4px; selection-background-color: @menu_sel; }
QLineEdit { padding: 3px 6px; }
QLineEdit:focus, QPlainTextEdit:focus, QTextEdit:focus { border: 1px solid @accent; }
QPushButton { background: @panel_alt; color: @text; border: 1px solid @border;
  border-radius: 4px; padding: 4px 12px; }
QPushButton:hover { background: @hover; border-color: @accent; }
QPushButton:pressed { background: @menu_sel; }
QPushButton:focus { border: 1px solid @accent; }
QMessageBox QPushButton { min-width: 90px; padding: 6px 16px; }
QCheckBox { color: @text; }
QToolTip { background: @panel_alt; color: @text; border: 1px solid @border;
  padding: 4px 8px; }
QScrollBar:vertical { background: transparent; width: 10px; margin: 0; }
QScrollBar::handle:vertical { background: @border; border-radius: 4px; min-height: 24px; }
QScrollBar::handle:vertical:hover { background: @muted; }
QScrollBar::add-line, QScrollBar::sub-line { height: 0; }
QScrollBar:horizontal { background: transparent; height: 10px; margin: 0; }
QScrollBar::handle:horizontal { background: @border; border-radius: 4px; min-width: 24px; }
QScrollBar::add-line, QScrollBar::sub-line { width: 0; }
QListWidget { background: @panel; color: @text; border: 1px solid @border; }
QListWidget::item:selected { background: @accent; color: @window; }
"""
    q = tpl
    # ganti token terpanjang dulu agar @menu_sel tidak tertelan @menu, dst.
    for k, v in sorted(ui.items(), key=lambda kv: len(kv[0]), reverse=True):
        q = q.replace("@" + k, v)
    return q
