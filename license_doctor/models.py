# SPDX-FileCopyrightText: Copyright (c) 2026 slopggobblercobbler81
# SPDX-License-Identifier: MIT

"""Data models and report structures."""

from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Set


class Severity(str, Enum):
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


@dataclass
class LicenseIssue:
    file_path: str
    message: str
    rule_id: str
    severity: Severity = Severity.ERROR
    line_number: Optional[int] = None
    autofixable: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "file_path": self.file_path,
            "line_number": self.line_number,
            "rule_id": self.rule_id,
            "message": self.message,
            "severity": self.severity.value,
            "autofixable": self.autofixable,
        }


@dataclass
class FileReport:
    file_path: str
    language: Optional[str] = None
    has_header: bool = False
    spdx_expression: Optional[str] = None
    spdx_valid: bool = False
    copyright_years: Optional[str] = None
    copyright_holder: Optional[str] = None
    is_year_outdated: bool = False
    issues: List[LicenseIssue] = field(default_factory=list)

    @property
    def is_compliant(self) -> bool:
        return self.has_header and self.spdx_valid and not self.is_year_outdated and not any(
            i.severity == Severity.ERROR for i in self.issues
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "file_path": self.file_path,
            "language": self.language,
            "has_header": self.has_header,
            "spdx_expression": self.spdx_expression,
            "spdx_valid": self.spdx_valid,
            "copyright_years": self.copyright_years,
            "copyright_holder": self.copyright_holder,
            "is_year_outdated": self.is_year_outdated,
            "is_compliant": self.is_compliant,
            "issues": [i.to_dict() for i in self.issues],
        }


@dataclass
class ProjectReport:
    root_path: str
    root_license_found: bool = False
    root_license_file: Optional[str] = None
    root_license_detected: Optional[str] = None
    manifest_licenses: Dict[str, str] = field(default_factory=dict)
    total_files: int = 0
    compliant_files: int = 0
    missing_header_files: int = 0
    invalid_spdx_files: int = 0
    outdated_year_files: int = 0
    file_reports: List[FileReport] = field(default_factory=list)
    project_issues: List[LicenseIssue] = field(default_factory=list)
    detected_licenses: Set[str] = field(default_factory=set)

    @property
    def compliance_rate(self) -> float:
        if self.total_files == 0:
            return 100.0 if self.root_license_found else 0.0
        return round((self.compliant_files / self.total_files) * 100.0, 1)

    @property
    def grade(self) -> str:
        if not self.root_license_found:
            return "F"
        rate = self.compliance_rate
        if rate == 100.0 and not self.outdated_year_files and not self.invalid_spdx_files:
            return "A+"
        elif rate >= 90.0:
            return "A"
        elif rate >= 75.0:
            return "B"
        elif rate >= 50.0:
            return "C"
        return "F"

    @property
    def has_errors(self) -> bool:
        if not self.root_license_found:
            return True
        if any(i.severity == Severity.ERROR for i in self.project_issues):
            return True
        for f in self.file_reports:
            if any(i.severity == Severity.ERROR for i in f.issues):
                return True
        return False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "root_path": self.root_path,
            "root_license_found": self.root_license_found,
            "root_license_file": self.root_license_file,
            "root_license_detected": self.root_license_detected,
            "manifest_licenses": self.manifest_licenses,
            "total_files": self.total_files,
            "compliant_files": self.compliant_files,
            "missing_header_files": self.missing_header_files,
            "invalid_spdx_files": self.invalid_spdx_files,
            "outdated_year_files": self.outdated_year_files,
            "compliance_rate": self.compliance_rate,
            "grade": self.grade,
            "has_errors": self.has_errors,
            "detected_licenses": sorted(list(self.detected_licenses)),
            "project_issues": [i.to_dict() for i in self.project_issues],
            "file_reports": [f.to_dict() for f in self.file_reports],
        }
