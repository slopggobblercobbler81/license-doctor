# SPDX-FileCopyrightText: Copyright (c) 2026 slopggobblercobbler81
# SPDX-License-Identifier: MIT

"""Project license scanner and compliance auditor."""

from __future__ import annotations
import fnmatch
import json
import os
from pathlib import Path
from typing import Dict, Generator, List, Optional, Set, Tuple

from license_doctor.config import LicenseDoctorConfig
from license_doctor.headers import (
    HeaderInfo,
    detect_header,
    inject_license_header,
    update_copyright_year_in_content,
)
from license_doctor.languages import get_language_spec, LanguageSpec
from license_doctor.models import (
    FileReport,
    LicenseIssue,
    ProjectReport,
    Severity,
)
from license_doctor.spdx_data import SPDX_LICENSES, LOWER_SPDX_LICENSES

try:
    import tomllib
except ImportError:
    try:
        import tomli as tomllib
    except ImportError:
        import toml as tomllib


ROOT_LICENSE_CANDIDATES = [
    "LICENSE",
    "LICENSE.md",
    "LICENSE.txt",
    "LICENSE.rst",
    "LICENCE",
    "LICENCE.md",
    "LICENCE.txt",
    "COPYING",
    "COPYING.LESSER",
]


def detect_root_license_type(content: str) -> Optional[str]:
    """Simple heuristic to detect the license type of a root LICENSE file."""
    upper = content.upper()
    if "APACHE LICENSE" in upper and "VERSION 2.0" in upper:
        return "Apache-2.0"
    if "MIT LICENSE" in upper or "PERMISSION IS HEREBY GRANTED, FREE OF CHARGE" in upper:
        return "MIT"
    if "GNU GENERAL PUBLIC LICENSE" in upper:
        if "VERSION 3" in upper:
            return "GPL-3.0-only"
        if "VERSION 2" in upper:
            return "GPL-2.0-only"
        return "GPL-3.0-or-later"
    if "GNU LESSER GENERAL PUBLIC LICENSE" in upper:
        if "VERSION 3" in upper:
            return "LGPL-3.0-only"
        return "LGPL-2.1-only"
    if "BSD 3-CLAUSE" in upper or "NEITHER THE NAME OF THE COPYRIGHT HOLDER" in upper:
        return "BSD-3-Clause"
    if "BSD 2-CLAUSE" in upper:
        return "BSD-2-Clause"
    if "MOZILLA PUBLIC LICENSE" in upper and "2.0" in upper:
        return "MPL-2.0"
    if "CREATIVE COMMONS ZERO" in upper or "CC0 1.0" in upper:
        return "CC0-1.0"
    if "UNLICENSE" in upper:
        return "Unlicense"
    if "INTERNET SYSTEMS CONSORTIUM" in upper or "ISC LICENSE" in upper:
        return "ISC"
    return None


def read_manifest_licenses(root_dir: Path) -> Dict[str, str]:
    """Inspect standard package manifests for declared licenses."""
    manifests: Dict[str, str] = {}

    # 1. pyproject.toml
    pyproject = root_dir / "pyproject.toml"
    if pyproject.is_file():
        try:
            with open(pyproject, "rb") as f:
                data = tomllib.load(f)
            lic = data.get("project", {}).get("license")
            if isinstance(lic, str):
                manifests["pyproject.toml"] = lic
            elif isinstance(lic, dict) and "text" in lic:
                manifests["pyproject.toml"] = lic["text"]
            elif isinstance(lic, dict) and "file" in lic:
                manifests["pyproject.toml"] = f"file:{lic['file']}"
        except Exception:
            pass

    # 2. package.json
    pkg_json = root_dir / "package.json"
    if pkg_json.is_file():
        try:
            with open(pkg_json, "r", encoding="utf-8", errors="ignore") as f:
                data = json.load(f)
            lic = data.get("license")
            if lic:
                manifests["package.json"] = str(lic)
        except Exception:
            pass

    # 3. Cargo.toml
    cargo_toml = root_dir / "Cargo.toml"
    if cargo_toml.is_file():
        try:
            with open(cargo_toml, "rb") as f:
                data = tomllib.load(f)
            pkg = data.get("package", {})
            if "license" in pkg:
                manifests["Cargo.toml"] = str(pkg["license"])
            elif "license-file" in pkg:
                manifests["Cargo.toml"] = f"file:{pkg['license-file']}"
        except Exception:
            pass

    return manifests


def is_path_excluded(path: Path, root: Path, excludes: List[str]) -> bool:
    """Check if relative path matches any exclusion pattern."""
    try:
        rel_str = path.relative_to(root).as_posix()
    except ValueError:
        rel_str = path.as_posix()

    parts = rel_str.split("/")
    for pattern in excludes:
        # Check against entire relative path or any path component
        if fnmatch.fnmatch(rel_str, pattern) or fnmatch.fnmatch(path.name, pattern):
            return True
        for part in parts:
            if fnmatch.fnmatch(part, pattern):
                return True
    return False


def is_binary_file(file_path: Path) -> bool:
    """Check if file appears to be binary by scanning the first block."""
    try:
        with open(file_path, "rb") as f:
            chunk = f.read(1024)
            if b"\x00" in chunk:
                return True
    except Exception:
        return True
    return False


class Scanner:
    """Scans and verifies software license compliance across a codebase."""

    def __init__(self, root_dir: Path, config: Optional[LicenseDoctorConfig] = None):
        self.root_dir = root_dir.resolve()
        self.config = config or LicenseDoctorConfig.load_from_dir(self.root_dir)

    def scan(self, expected_license: Optional[str] = None) -> ProjectReport:
        target_license = expected_license or self.config.license

        # Check Root License file
        root_lic_file: Optional[Path] = None
        detected_root_type: Optional[str] = None
        for cand in ROOT_LICENSE_CANDIDATES:
            p = self.root_dir / cand
            if p.is_file():
                root_lic_file = p
                try:
                    content = p.read_text(encoding="utf-8", errors="ignore")
                    detected_root_type = detect_root_license_type(content)
                except Exception:
                    pass
                break

        # Check package manifests
        manifests = read_manifest_licenses(self.root_dir)

        # Fallback target_license from root or manifest if not specified
        if not target_license:
            if detected_root_type:
                target_license = detected_root_type
            elif manifests:
                first_man = next(iter(manifests.values()))
                if not first_man.startswith("file:"):
                    target_license = first_man

        report = ProjectReport(
            root_path=str(self.root_dir),
            root_license_found=root_lic_file is not None,
            root_license_file=root_lic_file.name if root_lic_file else None,
            root_license_detected=detected_root_type,
            manifest_licenses=manifests,
        )

        if not root_lic_file:
            report.project_issues.append(
                LicenseIssue(
                    file_path=str(self.root_dir),
                    rule_id="missing-root-license",
                    message="Missing root LICENSE or COPYING file in project repository root",
                    severity=Severity.ERROR,
                )
            )

        # Walk code files
        for file_path in self._find_source_files():
            file_rep = self._check_file(file_path, target_license)
            report.file_reports.append(file_rep)
            report.total_files += 1

            if file_rep.is_compliant:
                report.compliant_files += 1
            if not file_rep.has_header:
                report.missing_header_files += 1
            if file_rep.spdx_expression and not file_rep.spdx_valid:
                report.invalid_spdx_files += 1
            if file_rep.is_year_outdated:
                report.outdated_year_files += 1
            if file_rep.spdx_expression:
                report.detected_licenses.add(file_rep.spdx_expression)

        return report

    def _find_source_files(self) -> Generator[Path, None, None]:
        """Traverse directory finding supported non-binary, non-excluded source files."""
        for root, dirs, files in os.walk(self.root_dir):
            root_path = Path(root)

            # Filter out ignored dirs in place to prevent descending
            dirs[:] = [
                d
                for d in dirs
                if not is_path_excluded(root_path / d, self.root_dir, self.config.exclude)
            ]

            for f in files:
                fpath = root_path / f
                if is_path_excluded(fpath, self.root_dir, self.config.exclude):
                    continue

                spec = get_language_spec(fpath)
                if spec is None:
                    continue

                if is_binary_file(fpath):
                    continue

                yield fpath

    def _check_file(
        self,
        file_path: Path,
        expected_license: Optional[str] = None,
    ) -> FileReport:
        try:
            content = file_path.read_text(encoding="utf-8", errors="ignore")
        except Exception as e:
            rep = FileReport(
                file_path=str(file_path.relative_to(self.root_dir)),
                issues=[
                    LicenseIssue(
                        file_path=str(file_path.relative_to(self.root_dir)),
                        message=f"Unable to read file: {e}",
                        rule_id="read-error",
                        severity=Severity.ERROR,
                    )
                ],
            )
            return rep

        spec = get_language_spec(file_path)
        rel_str = str(file_path.relative_to(self.root_dir))

        h_info = detect_header(
            content=content,
            target_year=self.config.target_year,
        )

        rep = FileReport(
            file_path=rel_str,
            language=spec.name if spec else None,
            has_header=h_info.has_header,
            spdx_expression=h_info.spdx_expression,
            spdx_valid=h_info.spdx_validation.is_valid if h_info.spdx_validation else False,
            copyright_years=f"{h_info.copyright_start_year}-{h_info.copyright_end_year}"
            if h_info.copyright_start_year and h_info.copyright_start_year != h_info.copyright_end_year
            else (str(h_info.copyright_start_year) if h_info.copyright_start_year else None),
            copyright_holder=h_info.copyright_holder,
            is_year_outdated=h_info.is_year_outdated,
        )

        if not h_info.has_header:
            rep.issues.append(
                LicenseIssue(
                    file_path=rel_str,
                    rule_id="missing-header",
                    message="Missing SPDX license header or copyright statement",
                    severity=Severity.ERROR,
                    autofixable=True,
                )
            )
        else:
            if not h_info.spdx_expression:
                if self.config.require_spdx:
                    rep.issues.append(
                        LicenseIssue(
                            file_path=rel_str,
                            rule_id="missing-spdx-identifier",
                            message="Header contains copyright but lacks SPDX-License-Identifier",
                            severity=Severity.WARNING,
                            autofixable=True,
                        )
                    )
            else:
                val = h_info.spdx_validation
                if val and not val.is_valid:
                    for err in val.errors:
                        rep.issues.append(
                            LicenseIssue(
                                file_path=rel_str,
                                rule_id="invalid-spdx-expression",
                                message=f"Invalid SPDX expression '{h_info.spdx_expression}': {err}",
                                severity=Severity.ERROR,
                            )
                        )
                elif val and val.warnings:
                    for warn in val.warnings:
                        rep.issues.append(
                            LicenseIssue(
                                file_path=rel_str,
                                rule_id="deprecated-spdx-identifier",
                                message=warn,
                                severity=Severity.WARNING,
                            )
                        )

                # Check expected license match if specified
                if expected_license and val and val.is_valid:
                    # Compare expressions normalized
                    norm_found = val.normalized_expression.strip().lower()
                    norm_expected = expected_license.strip().lower()
                    if norm_found != norm_expected:
                        rep.issues.append(
                            LicenseIssue(
                                file_path=rel_str,
                                rule_id="mismatched-license",
                                message=f"License expression '{h_info.spdx_expression}' does not match expected '{expected_license}'",
                                severity=Severity.WARNING,
                            )
                        )

            # Check outdated copyright year
            if h_info.is_year_outdated:
                rep.issues.append(
                    LicenseIssue(
                        file_path=rel_str,
                        rule_id="outdated-copyright-year",
                        message=f"Copyright year is outdated: '{rep.copyright_years}' (current target: {self.config.target_year})",
                        severity=Severity.WARNING,
                        autofixable=True,
                    )
                )

        return rep

    def fix(
        self,
        license_id: Optional[str] = None,
        owner: Optional[str] = None,
        year: Optional[int] = None,
        update_years: bool = True,
        dry_run: bool = False,
    ) -> Tuple[List[str], List[str]]:
        """
        Autofix missing license headers and outdated copyright years.
        Returns (fixed_files, year_updated_files).
        """
        lic = license_id or self.config.license or "MIT"
        own = owner or self.config.owner
        target_y = year or self.config.target_year

        fixed_files: List[str] = []
        year_updated_files: List[str] = []

        for fpath in self._find_source_files():
            spec = get_language_spec(fpath)
            if not spec:
                continue

            try:
                content = fpath.read_text(encoding="utf-8")
            except Exception:
                continue

            rel_str = str(fpath.relative_to(self.root_dir))
            h_info = detect_header(content, target_year=target_y)

            modified = False
            new_content = content

            if not h_info.has_header:
                new_content = inject_license_header(
                    content=new_content,
                    language=spec,
                    spdx_license=lic,
                    owner=own,
                    year=target_y,
                )
                modified = True
                fixed_files.append(rel_str)
            elif h_info.is_year_outdated and update_years:
                updated, mod = update_copyright_year_in_content(new_content, target_year=target_y)
                if mod:
                    new_content = updated
                    modified = True
                    year_updated_files.append(rel_str)

            if modified and not dry_run:
                try:
                    fpath.write_text(new_content, encoding="utf-8")
                except Exception:
                    pass

        return fixed_files, year_updated_files
