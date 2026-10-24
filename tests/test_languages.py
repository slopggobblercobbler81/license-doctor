# SPDX-FileCopyrightText: Copyright (c) 2026 slopggobblercobbler81
# SPDX-License-Identifier: MIT

"""Tests for language detection and comment formatting."""

from pathlib import Path
import pytest
from license_doctor.languages import get_language_spec, LANGUAGES


class TestLanguages:
    def test_extension_detection(self):
        cases = [
            ("main.py", "Python", "#"),
            ("script.sh", "Shell", "#"),
            ("index.js", "JavaScript", "//"),
            ("app.ts", "TypeScript", "//"),
            ("server.go", "Go", "//"),
            ("lib.rs", "Rust", "//"),
            ("main.c", "C", "//"),
            ("main.cpp", "C++", "//"),
            ("App.java", "Java", "//"),
            ("index.html", "HTML", None),
            ("style.css", "CSS", None),
            ("query.sql", "SQL", "--"),
            ("config.yaml", "YAML", "#"),
            ("settings.toml", "TOML", "#"),
        ]
        for fname, lang_name, expected_line_comment in cases:
            spec = get_language_spec(Path(fname))
            assert spec is not None, f"Failed to detect spec for {fname}"
            assert spec.name == lang_name
            if expected_line_comment:
                assert spec.line_comment == expected_line_comment

    def test_filename_detection(self):
        cases = [
            ("Dockerfile", "Dockerfile"),
            ("Makefile", "Makefile"),
            ("Gemfile", "Ruby"),
        ]
        for fname, expected_name in cases:
            spec = get_language_spec(Path(fname))
            assert spec is not None
            assert spec.name == expected_name

    def test_unknown_extension(self):
        spec = get_language_spec(Path("archive.unknownext123"))
        assert spec is None

    def test_format_header_line_style(self):
        spec = get_language_spec(Path("foo.py"))
        formatted = spec.format_header(["Line 1", "Line 2"])
        assert formatted == "# Line 1\n# Line 2\n"

    def test_format_header_block_style(self):
        spec = get_language_spec(Path("style.css"))
        formatted = spec.format_header(["Line 1", "Line 2"])
        assert "/*" in formatted
        assert " * Line 1" in formatted
        assert " */" in formatted

    def test_format_header_xml_style(self):
        spec = get_language_spec(Path("index.html"))
        formatted = spec.format_header(["Line 1", "Line 2"])
        assert "<!--" in formatted
        assert "  Line 1" in formatted
        assert "-->" in formatted
