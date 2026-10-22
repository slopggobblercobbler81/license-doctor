"""Unit tests for license template generation."""

import pytest
from license_doctor.generator import generate_license, list_available_templates


def test_list_templates():
    templates = list_available_templates()
    assert "MIT" in templates
    assert "Apache-2.0" in templates
    assert "BSD-3-Clause" in templates
    assert "ISC" in templates
    assert "Unlicense" in templates


def test_generate_mit():
    text = generate_license("MIT", holder="Acme Corporation", year=2026)
    assert "MIT License" in text
    assert "Copyright (c) 2026 Acme Corporation" in text
    assert "Permission is hereby granted" in text


def test_generate_apache2():
    text = generate_license("Apache-2.0", holder="Open Source Org", year=2026)
    assert "Apache License" in text
    assert "Version 2.0, January 2004" in text
    assert "Copyright 2026 Open Source Org" in text


def test_generate_bsd_clauses():
    bsd2 = generate_license("BSD-2-Clause", holder="John Doe", year=2026)
    assert "BSD 2-Clause License" in bsd2
    assert "Copyright (c) 2026, John Doe" in bsd2

    bsd3 = generate_license("BSD-3-Clause", holder="John Doe", year=2026)
    assert "BSD 3-Clause License" in bsd3
    assert "Neither the name of the copyright holder" in bsd3


def test_generate_unknown_template():
    with pytest.raises(ValueError) as exc:
        generate_license("Nonexistent-Lic-999")
    assert "Unknown license template" in str(exc.value)
