"""Test untuk tema — kelengkapan data & kebenaran stylesheet."""

from src.themes import THEMES, THEME_ORDER, TOKEN_KEYS, build_qss

REQUIRED_UI = [
    "window", "panel", "panel_alt", "text", "muted", "accent", "border",
    "tab_active", "tab_inactive", "hover", "danger", "input", "menu",
    "menu_sel",
]
EDITOR_KEYS = [
    "name", "bg", "fg", "gutter_bg", "gutter_fg", "current_line",
    "current_line_num", "selection", "ui", "tokens",
]
COLOR_KEYS = ["bg", "fg", "gutter_bg", "gutter_fg", "current_line",
              "current_line_num", "selection"]


def test_theme_count():
    assert len(THEMES) == len(THEME_ORDER) == 7


def test_default_theme_first():
    assert THEME_ORDER[0] == "Dracula (Default)"


def test_every_theme_complete():
    for name in THEME_ORDER:
        t = THEMES[name]
        for k in EDITOR_KEYS:
            assert k in t, f"{name} kehilangan kunci {k}"
        for k in REQUIRED_UI:
            assert k in t["ui"], f"{name} ui kehilangan {k}"
        for k in TOKEN_KEYS:
            assert k in t["tokens"], f"{name} tokens kehilangan {k}"


def test_colors_are_valid_hex():
    for name in THEME_ORDER:
        t = THEMES[name]
        for k in COLOR_KEYS:
            v = t[k]
            assert v.startswith("#") and len(v) == 7, f"{name}.{k}={v!r}"


def test_build_qss_no_leftover_tokens():
    for name in THEME_ORDER:
        qss = build_qss(THEMES[name]["ui"])
        for token in REQUIRED_UI:
            assert f"@{token}" not in qss, f"{name} sisa token @{token}"
        # bug lama: penggantian berurutan mengubah @menu_sel jadi '#xxx_sel'
        assert "_sel" not in qss
        assert "_alt" not in qss
        assert "_active" not in qss
        assert "_inactive" not in qss


def test_build_qss_contains_accent():
    for name in THEME_ORDER:
        qss = build_qss(THEMES[name]["ui"])
        assert THEMES[name]["ui"]["accent"].lower() in qss.lower()


def test_build_qss_differs_between_themes():
    qss_dark = build_qss(THEMES["Dracula (Default)"]["ui"])
    qss_light = build_qss(THEMES["Light"]["ui"])
    assert qss_dark != qss_light


def test_tokens_defaults_filled():
    # tema yang tidak menimpa token harus tetap memakai warna default Dracula
    t = THEMES["Dracula (Default)"]
    assert t["tokens"]["keyword"] == "#ff79c6"
    assert t["tokens"]["comment"] == "#6272a4"
