"""Test identitas & perbandingan versi (cek pembaruan)."""

from src.version import (APP_AUTHOR, APP_REPO_URL, is_newer_version,
                         parse_version)


def test_identity():
    assert APP_AUTHOR == "jpXCode"
    assert "github.com" in APP_REPO_URL
    assert APP_REPO_URL.endswith("OnyxPad")


def test_parse_version_basic():
    assert parse_version("1.0.0") == (1, 0, 0)
    assert parse_version("v1.2.3") == (1, 2, 3)
    assert parse_version("1.4") == (1, 4, 0)
    assert parse_version("2") == (2, 0, 0)
    assert parse_version("v1.2.3-beta") == (1, 2, 3)


def test_parse_version_invalid():
    assert parse_version("") is None
    assert parse_version("abc") is None
    assert parse_version(None) is None


def test_is_newer_version():
    assert is_newer_version("1.0.0", "v1.0.1") is True
    assert is_newer_version("1.0.0", "v1.1.0") is True
    assert is_newer_version("1.0.0", "v2.0.0") is True
    assert is_newer_version("1.0.0", "v1.0.0") is False
    assert is_newer_version("1.0.0", "v0.9.9") is False
    assert is_newer_version("1.2.0", "v1.1.9") is False


def test_is_newer_version_invalid_tag():
    assert is_newer_version("1.0.0", "garbage") is False
    assert is_newer_version("", "v1.0.0") is False
