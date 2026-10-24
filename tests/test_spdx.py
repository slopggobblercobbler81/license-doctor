# SPDX-FileCopyrightText: Copyright (c) 2026 slopggobblercobbler81
# SPDX-License-Identifier: MIT

"""Tests for SPDX 3.20+ identifier validation and expression parser."""

import pytest
from license_doctor.spdx_validator import (
    validate_license_id,
    validate_exception_id,
    validate_spdx_expression,
    suggest_spdx_id,
)


class TestSPDXValidation:
    def test_canonical_licenses(self):
        valid_licenses = [
            "MIT",
            "Apache-2.0",
            "BSD-2-Clause",
            "BSD-3-Clause",
            "GPL-2.0-only",
            "GPL-2.0-or-later",
            "GPL-3.0-only",
            "GPL-3.0-or-later",
            "AGPL-3.0-only",
            "AGPL-3.0-or-later",
            "MPL-2.0",
            "ISC",
            "0BSD",
            "Unlicense",
            "CC0-1.0",
        ]
        for lic in valid_licenses:
            is_valid, canon, warn, err = validate_license_id(lic)
            assert is_valid, f"Expected {lic} to be valid"
            assert canon == lic
            assert err is None

    def test_case_insensitivity(self):
        is_valid, canon, warn, err = validate_license_id("mit")
        assert is_valid
        assert canon == "MIT"
        assert warn is not None
        assert err is None

        is_valid, canon, warn, err = validate_license_id("apache-2.0")
        assert is_valid
        assert canon == "Apache-2.0"

    def test_deprecated_license_mapping(self):
        is_valid, canon, warn, err = validate_license_id("GPL-3.0")
        assert is_valid
        assert canon == "GPL-3.0-only"
        assert "deprecated" in warn.lower()

        is_valid, canon, warn, err = validate_license_id("GPL-3.0+")
        assert is_valid
        assert canon == "GPL-3.0-or-later"

    def test_custom_licenseref(self):
        is_valid, canon, warn, err = validate_license_id("LicenseRef-Custom-Proprietary")
        assert is_valid
        assert canon == "LicenseRef-Custom-Proprietary"

        is_valid, canon, warn, err = validate_license_id("DocumentRef-Doc1:LicenseRef-Special")
        assert is_valid

    def test_invalid_license_suggestion(self):
        is_valid, canon, warn, err = validate_license_id("Apche-2.0")
        assert not is_valid
        assert "Apache-2.0" in err

    def test_empty_license(self):
        is_valid, _, _, err = validate_license_id("")
        assert not is_valid
        assert "Empty" in err

    def test_license_exceptions(self):
        is_valid, canon, warn, err = validate_exception_id("Classpath-exception-2.0")
        assert is_valid
        assert canon == "Classpath-exception-2.0"
        assert err is None

        is_valid, canon, warn, err = validate_exception_id("LLVM-exception")
        assert is_valid
        assert canon == "LLVM-exception"

        # Invalid exception
        is_valid, canon, warn, err = validate_exception_id("Nonexistent-exception-xyz")
        assert not is_valid
        assert err is not None


class TestSPDXExpressions:
    def test_simple_expression(self):
        res = validate_spdx_expression("MIT")
        assert res.is_valid
        assert res.normalized_expression == "MIT"
        assert "MIT" in res.detected_licenses

    def test_or_expression(self):
        res = validate_spdx_expression("MIT OR Apache-2.0")
        assert res.is_valid
        assert res.normalized_expression == "MIT OR Apache-2.0"
        assert {"MIT", "Apache-2.0"}.issubset(res.detected_licenses)

    def test_and_expression(self):
        res = validate_spdx_expression("BSD-3-Clause AND MIT")
        assert res.is_valid
        assert res.normalized_expression == "BSD-3-Clause AND MIT"

    def test_with_exception(self):
        res = validate_spdx_expression("GPL-2.0-or-later WITH Classpath-exception-2.0")
        assert res.is_valid
        assert res.normalized_expression == "GPL-2.0-or-later WITH Classpath-exception-2.0"
        assert "Classpath-exception-2.0" in res.detected_exceptions

    def test_parenthesized_expression(self):
        res = validate_spdx_expression("(MIT OR Apache-2.0) AND BSD-3-Clause")
        assert res.is_valid
        assert res.normalized_expression == "(MIT OR Apache-2.0) AND BSD-3-Clause"

    def test_case_normalization_in_expression(self):
        res = validate_spdx_expression("mit or apache-2.0")
        assert res.is_valid
        assert res.normalized_expression == "MIT OR Apache-2.0"
        assert len(res.warnings) > 0

    def test_syntax_errors(self):
        # Empty
        res = validate_spdx_expression("")
        assert not res.is_valid

        # Trailing operator
        res = validate_spdx_expression("MIT OR")
        assert not res.is_valid
        assert any("Expected expression after 'OR'" in e for e in res.errors)

        # Leading operator
        res = validate_spdx_expression("AND MIT")
        assert not res.is_valid

        # Missing closing paren
        res = validate_spdx_expression("(MIT OR Apache-2.0")
        assert not res.is_valid
        assert any("closing parenthesis" in e for e in res.errors)

        # Missing exception after WITH
        res = validate_spdx_expression("GPL-3.0-only WITH")
        assert not res.is_valid

        # Unknown license in expression
        res = validate_spdx_expression("MIT OR UnknownFakeLicense123")
        assert not res.is_valid
        assert any("Unknown SPDX license identifier" in e for e in res.errors)

    def test_to_dict(self):
        res = validate_spdx_expression("MIT")
        data = res.to_dict()
        assert data["is_valid"] is True
        assert data["expression"] == "MIT"
        assert "MIT" in data["detected_licenses"]
