"""Dual-license and multi-license compatibility evaluator."""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Optional, Set, Tuple

from .spdx import LicenseCategory, SPDX_DATABASE


@dataclass
class CompatibilityReport:
    licenses: List[str]
    is_compatible: bool
    effective_license: Optional[str]
    conflicts: List[str] = field(default_factory=list)
    notes: List[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "licenses": self.licenses,
            "is_compatible": self.is_compatible,
            "effective_license": self.effective_license,
            "conflicts": self.conflicts,
            "notes": self.notes,
        }


def check_license_compatibility(licenses: List[str]) -> CompatibilityReport:
    """Evaluate compatibility when combining multiple licensed works into a single project."""
    if not licenses:
        return CompatibilityReport(
            licenses=[],
            is_compatible=True,
            effective_license=None,
            notes=["No licenses provided."],
        )

    # Normalize IDs
    normalized: List[str] = []
    for lic in licenses:
        match = next((k for k in SPDX_DATABASE if k.lower() == lic.lower()), None)
        normalized.append(match if match else lic)

    unique_lics = list(dict.fromkeys(normalized))
    if len(unique_lics) == 1:
        return CompatibilityReport(
            licenses=unique_lics,
            is_compatible=True,
            effective_license=unique_lics[0],
            notes=[f"Single license: {unique_lics[0]}"],
        )

    conflicts: List[str] = []
    notes: List[str] = []
    effective_license: Optional[str] = None

    categories = {lic: SPDX_DATABASE.get(lic, None) for lic in unique_lics}

    # Special well-known conflict: Apache-2.0 with GPL-2.0-only
    has_apache2 = "Apache-2.0" in unique_lics
    has_gpl2_only = "GPL-2.0-only" in unique_lics

    if has_apache2 and has_gpl2_only:
        conflicts.append(
            "Apache-2.0 is incompatible with GPL-2.0-only because GPLv2 patent clauses conflict with Apache 2.0 patent license terms (FSF recognized conflict)."
        )

    # Check GPL-2.0-only with GPL-3.0
    has_gpl3 = any("GPL-3.0" in lic for lic in unique_lics)
    if has_gpl2_only and has_gpl3:
        conflicts.append(
            "GPL-2.0-only is incompatible with GPL-3.0 because code licensed strictly under GPLv2 cannot be re-licensed or linked with GPLv3 code."
        )

    # Check AGPL-3.0 combinations
    has_agpl3 = any("AGPL-3.0" in lic for lic in unique_lics)

    # Check copyleft hierarchy
    all_permissive = all(
        categories[lic] and categories[lic].category in (LicenseCategory.PERMISSIVE, LicenseCategory.PUBLIC_DOMAIN)
        for lic in unique_lics
    )

    if all_permissive:
        # If Apache-2.0 is in permissive set, Apache-2.0 terms dominate due to patent grants
        if has_apache2:
            effective_license = "Apache-2.0"
            notes.append("Permissive combination: Apache-2.0 terms apply to combined work, preserving MIT/BSD notices.")
        else:
            effective_license = unique_lics[0]
            notes.append(f"Permissive combination: Compatible under {effective_license} with attribution retained.")
    elif conflicts:
        effective_license = None
    else:
        # Copyleft combination
        if has_agpl3:
            effective_license = next(lic for lic in unique_lics if "AGPL-3.0" in lic)
            notes.append(f"Network copyleft combination: Effective combined work is governed by {effective_license}.")
        elif has_gpl3:
            effective_license = next(lic for lic in unique_lics if "GPL-3.0" in lic)
            notes.append(f"Strong copyleft combination: Effective combined work is governed by {effective_license}.")
        elif "GPL-2.0-or-later" in unique_lics:
            effective_license = "GPL-2.0-or-later"
            notes.append("Copyleft combination: Effective combined work is governed by GPL-2.0-or-later.")
        elif any(categories[lic] and categories[lic].category == LicenseCategory.WEAK_COPYLEFT for lic in unique_lics):
            weak_lic = next(lic for lic in unique_lics if categories[lic] and categories[lic].category == LicenseCategory.WEAK_COPYLEFT)
            effective_license = weak_lic
            notes.append(f"Weak copyleft component: {weak_lic} files remain under weak copyleft while project may retain permissive container.")

    is_compat = len(conflicts) == 0

    return CompatibilityReport(
        licenses=unique_lics,
        is_compatible=is_compat,
        effective_license=effective_license,
        conflicts=conflicts,
        notes=notes,
    )
