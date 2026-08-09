"""
===============================================================================
Universal Prompt Studio
Engineering Toolkit

Filesystem Utilities Tests

Tests cover:
- Directory creation (ensure_directory)
- Filesystem queries (exists, is_file, is_directory)
- Text read/write (UTF-8, Unicode, parent auto-creation, return contract)
- Binary read/write
- YAML read/write (round-trip, empty, invalid root, Unicode)
- JSON read/write (round-trip, invalid root)
- Exception behavior (documented contract)

===============================================================================
"""

from __future__ import annotations

from pathlib import Path

import pytest

from Engineering.core.exceptions import FileReadError
from Engineering.core.filesystem import (
    ensure_directory,
    exists,
    is_directory,
    is_file,
    read_bytes,
    read_json,
    read_text,
    read_yaml,
    write_bytes,
    write_json,
    write_text,
    write_yaml,
)

# -----------------------------------------------------------------------------
# Directory Utilities
# -----------------------------------------------------------------------------


class TestEnsureDirectory:
    def test_creates_directory(self, tmp_path: Path) -> None:
        target = tmp_path / "new_dir"
        result = ensure_directory(target)
        assert target.is_dir()
        assert result == target

    def test_creates_nested_directories(self, tmp_path: Path) -> None:
        target = tmp_path / "a" / "b" / "c"
        ensure_directory(target)
        assert target.is_dir()

    def test_existing_directory(self, tmp_path: Path) -> None:
        result = ensure_directory(tmp_path)
        assert tmp_path.is_dir()
        assert result == tmp_path


# -----------------------------------------------------------------------------
# Filesystem Queries
# -----------------------------------------------------------------------------


class TestExists:
    def test_existing_file(self, tmp_path: Path) -> None:
        f = tmp_path / "file.txt"
        f.write_text("x", encoding="utf-8")
        assert exists(f) is True

    def test_existing_directory(self, tmp_path: Path) -> None:
        assert exists(tmp_path) is True

    def test_missing_path(self, tmp_path: Path) -> None:
        assert exists(tmp_path / "nope") is False


class TestIsFile:
    def test_regular_file(self, tmp_path: Path) -> None:
        f = tmp_path / "file.txt"
        f.write_text("x", encoding="utf-8")
        assert is_file(f) is True

    def test_directory_is_not_file(self, tmp_path: Path) -> None:
        assert is_file(tmp_path) is False

    def test_missing_path(self, tmp_path: Path) -> None:
        assert is_file(tmp_path / "nope") is False


class TestIsDirectory:
    def test_directory(self, tmp_path: Path) -> None:
        assert is_directory(tmp_path) is True

    def test_file_is_not_directory(self, tmp_path: Path) -> None:
        f = tmp_path / "file.txt"
        f.write_text("x", encoding="utf-8")
        assert is_directory(f) is False

    def test_missing_path(self, tmp_path: Path) -> None:
        assert is_directory(tmp_path / "nope") is False


# -----------------------------------------------------------------------------
# Text Files
# -----------------------------------------------------------------------------


class TestReadWriteText:
    def test_round_trip_ascii(self, tmp_path: Path) -> None:
        f = tmp_path / "file.txt"
        write_text(f, "hello world")
        assert read_text(f) == "hello world"

    def test_round_trip_unicode(self, tmp_path: Path) -> None:
        f = tmp_path / "unicode.txt"
        content = "日本語テスト 🎉 café résumé"
        write_text(f, content)
        assert read_text(f) == content

    def test_utf8_encoding(self, tmp_path: Path) -> None:
        f = tmp_path / "encoded.txt"
        write_text(f, "data")
        raw = f.read_bytes()
        assert raw == b"data"

    def test_parent_directory_auto_created(self, tmp_path: Path) -> None:
        f = tmp_path / "deep" / "nested" / "file.txt"
        write_text(f, "content")
        assert f.is_file()
        assert read_text(f) == "content"

    def test_overwrites_existing(self, tmp_path: Path) -> None:
        f = tmp_path / "file.txt"
        write_text(f, "old")
        write_text(f, "new")
        assert read_text(f) == "new"

    def test_empty_content(self, tmp_path: Path) -> None:
        f = tmp_path / "empty.txt"
        write_text(f, "")
        assert read_text(f) == ""

    def test_multiline(self, tmp_path: Path) -> None:
        f = tmp_path / "multi.txt"
        content = "line1\nline2\nline3\n"
        write_text(f, content)
        assert read_text(f) == content

    def test_write_text_returns_none(self, tmp_path: Path) -> None:
        f = tmp_path / "none.txt"
        result = write_text(f, "data")
        assert result is None

    def test_read_text_missing_file(self, tmp_path: Path) -> None:
        f = tmp_path / "missing.txt"
        with pytest.raises(FileReadError):
            read_text(f)


# -----------------------------------------------------------------------------
# Binary Files
# -----------------------------------------------------------------------------


class TestReadWriteBinary:
    def test_round_trip(self, tmp_path: Path) -> None:
        f = tmp_path / "file.bin"
        data = b"\x00\x01\x02\xff"
        write_bytes(f, data)
        assert read_bytes(f) == data

    def test_parent_directory_auto_created(self, tmp_path: Path) -> None:
        f = tmp_path / "deep" / "nested" / "file.bin"
        write_bytes(f, b"data")
        assert f.is_file()
        assert read_bytes(f) == b"data"

    def test_empty_binary(self, tmp_path: Path) -> None:
        f = tmp_path / "empty.bin"
        write_bytes(f, b"")
        assert read_bytes(f) == b""

    def test_large_binary(self, tmp_path: Path) -> None:
        f = tmp_path / "large.bin"
        data = bytes(range(256)) * 100
        write_bytes(f, data)
        assert read_bytes(f) == data
        assert len(data) == 25600


# -----------------------------------------------------------------------------
# YAML
# -----------------------------------------------------------------------------


class TestReadWriteYaml:
    def test_round_trip(self, tmp_path: Path) -> None:
        f = tmp_path / "data.yaml"
        original = {"key": "value", "number": 42, "nested": {"a": True}}
        write_yaml(f, original)
        result = read_yaml(f)
        assert result == original

    def test_unicode_values(self, tmp_path: Path) -> None:
        f = tmp_path / "unicode.yaml"
        original = {"name": "日本語", "city": "café"}
        write_yaml(f, original)
        result = read_yaml(f)
        assert result == original

    def test_empty_yaml(self, tmp_path: Path) -> None:
        f = tmp_path / "empty.yaml"
        f.write_text("", encoding="utf-8")
        result = read_yaml(f)
        assert result == {}

    def test_yaml_with_only_comments(self, tmp_path: Path) -> None:
        f = tmp_path / "comments.yaml"
        f.write_text("# just a comment\n", encoding="utf-8")
        result = read_yaml(f)
        assert result == {}

    def test_invalid_root_scalar(self, tmp_path: Path) -> None:
        f = tmp_path / "scalar.yaml"
        f.write_text("just a string\n", encoding="utf-8")
        with pytest.raises(TypeError, match="mapping"):
            read_yaml(f)

    def test_invalid_root_list(self, tmp_path: Path) -> None:
        f = tmp_path / "list.yaml"
        f.write_text("- item1\n- item2\n", encoding="utf-8")
        with pytest.raises(TypeError, match="mapping"):
            read_yaml(f)

    def test_preserves_order(self, tmp_path: Path) -> None:
        f = tmp_path / "order.yaml"
        original = {"z": 1, "a": 2, "m": 3}
        write_yaml(f, original)
        result = read_yaml(f)
        assert list(result.keys()) == ["z", "a", "m"]

    def test_read_yaml_missing_file(self, tmp_path: Path) -> None:
        f = tmp_path / "missing.yaml"
        with pytest.raises(FileReadError):
            read_yaml(f)


# -----------------------------------------------------------------------------
# JSON
# -----------------------------------------------------------------------------


class TestReadWriteJson:
    def test_round_trip(self, tmp_path: Path) -> None:
        f = tmp_path / "data.json"
        original = {"key": "value", "number": 42, "nested": {"a": True}}
        write_json(f, original)
        result = read_json(f)
        assert result == original

    def test_unicode_values(self, tmp_path: Path) -> None:
        f = tmp_path / "unicode.json"
        original = {"name": "日本語", "city": "café"}
        write_json(f, original)
        result = read_json(f)
        assert result == original

    def test_invalid_root_array(self, tmp_path: Path) -> None:
        f = tmp_path / "array.json"
        f.write_text('[1, 2, 3]', encoding="utf-8")
        with pytest.raises(TypeError, match="object"):
            read_json(f)

    def test_invalid_root_string(self, tmp_path: Path) -> None:
        f = tmp_path / "string.json"
        f.write_text('"hello"', encoding="utf-8")
        with pytest.raises(TypeError, match="object"):
            read_json(f)

    def test_empty_object(self, tmp_path: Path) -> None:
        f = tmp_path / "empty.json"
        write_json(f, {})
        assert read_json(f) == {}

    def test_json_indentation(self, tmp_path: Path) -> None:
        f = tmp_path / "indented.json"
        write_json(f, {"a": 1})
        content = f.read_text(encoding="utf-8")
        assert "\n" in content
        assert "    " in content

    def test_read_json_missing_file(self, tmp_path: Path) -> None:
        f = tmp_path / "missing.json"
        with pytest.raises(FileReadError):
            read_json(f)


# -----------------------------------------------------------------------------
# Exception Contract
# -----------------------------------------------------------------------------


class TestExceptionContract:
    def test_read_text_raises_file_read_error(self, tmp_path: Path) -> None:
        with pytest.raises(FileReadError):
            read_text(tmp_path / "nonexistent.txt")

    def test_read_yaml_raises_file_read_error(self, tmp_path: Path) -> None:
        with pytest.raises(FileReadError):
            read_yaml(tmp_path / "nonexistent.yaml")

    def test_read_json_raises_file_read_error(self, tmp_path: Path) -> None:
        with pytest.raises(FileReadError):
            read_json(tmp_path / "nonexistent.json")

    def test_read_yaml_invalid_root_raises_type_error(self, tmp_path: Path) -> None:
        f = tmp_path / "bad.yaml"
        f.write_text("- item\n", encoding="utf-8")
        with pytest.raises(TypeError):
            read_yaml(f)

    def test_read_json_invalid_root_raises_type_error(self, tmp_path: Path) -> None:
        f = tmp_path / "bad.json"
        f.write_text("123", encoding="utf-8")
        with pytest.raises(TypeError):
            read_json(f)

    def test_write_text_does_not_raise(self, tmp_path: Path) -> None:
        f = tmp_path / "ok.txt"
        result = write_text(f, "data")
        assert result is None
