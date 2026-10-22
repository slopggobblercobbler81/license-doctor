"""Unit tests for license compatibility checking."""

import pytest
from license_doctor.compatibility import check_license_compatibility


def test_compat_permissive_combination():
    report = check_license_compatibility(["MIT", "Apache-2.0"])
    assert report.is_compatible is True
    assert report.effective_license == "Apache-2.0"
    assert len(report.conflicts) == 0

    report2 = check_license_compatibility(["MIT", "BSD-3-Clause", "ISC"])
    assert report2.is_compatible is True
    assert len(report2.conflicts) == 0


def test_compat_permissive_with_copyleft():
    report = check_license_compatibility(["MIT", "GPL-3.0-only"])
    assert report.is_compatible is True
    assert report.effective_license == "GPL-3.0-only"


def test_compat_apache2_and_gpl2_conflict():
    report = check_license_compatibility(["Apache-2.0", "GPL-2.0-only"])
    assert report.is_compatible is False
    assert len(report.conflicts) >= 1
    assert any("Apache-2.0 is incompatible with GPL-2.0-only" in c for c in report.conflicts)


def test_compat_gpl2_and_gpl3_conflict():
    report = check_license_compatibility(["GPL-2.0-only", "GPL-3.0-only"])
    assert report.is_compatible is False
    assert any("GPL-2.0-only is incompatible with GPL-3.0" in c for c in report.conflicts)


def test_compat_agpl_dominance():
    report = check_license_compatibility(["MIT", "AGPL-3.0-only"])
    assert report.is_compatible is True
    assert report.effective_license == "AGPL-3.0-only"


def test_compat_single_and_empty():
    empty = check_license_compatibility([])
    assert empty.is_compatible is True

    single = check_license_compatibility(["MIT"])
    assert single.is_compatible is True
    assert single.effective_license == "MIT"


def test_compat_weak_copyleft_and_or_later():
    # Weak copyleft
    rep_weak = check_license_compatibility(["MIT", "MPL-2.0"])
    assert rep_weak.is_compatible is True
    assert rep_weak.effective_license == "MPL-2.0"

    # GPL-2.0-or-later
    rep_or_later = check_license_compatibility(["MIT", "GPL-2.0-or-later"])
    assert rep_or_later.is_compatible is True
    assert rep_or_later.effective_license == "GPL-2.0-or-later"
