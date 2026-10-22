"""Unit tests for SPDX expression parsing, validation, and normalization."""

import pytest
from license_doctor.spdx import (
    validate_spdx_expression,
    tokenize_spdx,
    SPDX_DATABASE,
    LicenseCategory,
)


def test_tokenize_spdx():
    tokens = tokenize_spdx("MIT OR (Apache-2.0 AND BSD-3-Clause)")
    assert tokens == ["MIT", "OR", "(", "Apache-2.0", "AND", "BSD-3-Clause", ")"]

    with_tokens = tokenize_spdx("GPL-3.0-or-later WITH Classpath-exception-2.0")
    assert with_tokens == ["GPL-3.0-or-later", "WITH", "Classpath-exception-2.0"]


def test_validate_single_license():
    report = validate_spdx_expression("MIT")
    assert report.is_valid is True
    assert report.identifiers == ["MIT"]
    assert len(report.errors) == 0

    report2 = validate_spdx_expression("Apache-2.0")
    assert report2.is_valid is True
    assert report2.identifiers == ["Apache-2.0"]


def test_validate_compound_expression():
    report = validate_spdx_expression("MIT OR Apache-2.0")
    assert report.is_valid is True
    assert set(report.identifiers) == {"MIT", "Apache-2.0"}

    report_paren = validate_spdx_expression("(MIT AND BSD-3-Clause) OR ISC")
    assert report_paren.is_valid is True
    assert set(report_paren.identifiers) == {"MIT", "BSD-3-Clause", "ISC"}


def test_validate_exceptions():
    report = validate_spdx_expression("GPL-3.0-or-later WITH Classpath-exception-2.0")
    assert report.is_valid is True
    assert report.identifiers == ["GPL-3.0-or-later"]
    assert report.exceptions == ["Classpath-exception-2.0"]

    # Unknown exception
    bad_report = validate_spdx_expression("GPL-3.0-or-later WITH Unknown-Exception")
    assert bad_report.is_valid is False
    assert any("Unknown or unapproved license exception" in e.message for e in bad_report.errors)


def test_validate_deprecated_identifier():
    report = validate_spdx_expression("GPL-3.0")
    assert report.is_valid is True  # Valid with warning
    assert len(report.warnings) == 1
    assert report.warnings[0].suggestion == "GPL-3.0-only"
    assert report.canonical_expression == "GPL-3.0-only"


def test_validate_casing_normalization():
    report = validate_spdx_expression("mit")
    assert report.is_valid is True
    assert len(report.warnings) == 1
    assert report.warnings[0].suggestion == "MIT"
    assert report.canonical_expression == "MIT"


def test_validate_syntax_errors():
    # Empty
    assert validate_spdx_expression("").is_valid is False

    # Unclosed paren
    assert validate_spdx_expression("(MIT AND Apache-2.0").is_valid is False

    # Trailing operator
    assert validate_spdx_expression("MIT OR").is_valid is False

    # Unexpected operator at start
    assert validate_spdx_expression("AND MIT").is_valid is False

    # Unknown identifier
    bad_id = validate_spdx_expression("MyCustomLicense-1.0")
    assert bad_id.is_valid is False
    assert any("Unknown or non-standard" in e.message for e in bad_id.errors)
