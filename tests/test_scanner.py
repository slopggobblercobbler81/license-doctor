"""Tests for Scanner, project license checks, and manifest analysis."""

from pathlib import Path
import pytest
from license_doctor.config import LicenseDoctorConfig
from license_doctor.models import ProjectReport, Severity
from license_doctor.project_scanner import (
    Scanner,
    detect_root_license_type,
    read_manifest_licenses,
    is_path_excluded,
    is_binary_file,
)


class TestRootLicenseDetection:
    def test_detect_mit_license(self):
        text = """MIT License

Copyright (c) 2026 Test Owner

Permission is hereby granted, free of charge, to any person obtaining a copy...
"""
        assert detect_root_license_type(text) == "MIT"

    def test_detect_apache_license(self):
        text = """Apache License
Version 2.0, January 2004
http://www.apache.org/licenses/
"""
        assert detect_root_license_type(text) == "Apache-2.0"

    def test_detect_gpl_license(self):
        text = "GNU GENERAL PUBLIC LICENSE\nVersion 3, 29 June 2007"
        assert detect_root_license_type(text) == "GPL-3.0-only"

    def test_detect_bsd_license(self):
        text = "Redistribution and use in source and binary forms... BSD 3-Clause License"
        assert detect_root_license_type(text) == "BSD-3-Clause"


class TestProjectScanner:
    def test_scanner_clean_repo(self, tmp_path):
        # Create LICENSE file
        lic_file = tmp_path / "LICENSE"
        lic_file.write_text("MIT License\nCopyright (c) 2026 Test", encoding="utf-8")

        # Create source file with compliant header
        src = tmp_path / "main.py"
        src.write_text("# SPDX-License-Identifier: MIT\n# SPDX-FileCopyrightText: 2026 Test\nprint(1)\n", encoding="utf-8")

        scanner = Scanner(tmp_path)
        report = scanner.scan()

        assert report.root_license_found is True
        assert report.root_license_detected == "MIT"
        assert report.total_files == 1
        assert report.compliant_files == 1
        assert report.missing_header_files == 0
        assert report.compliance_rate == 100.0
        assert report.grade == "A+"
        assert not report.has_errors

    def test_scanner_missing_root_license(self, tmp_path):
        src = tmp_path / "main.py"
        src.write_text("print('hello')", encoding="utf-8")

        scanner = Scanner(tmp_path)
        report = scanner.scan()

        assert report.root_license_found is False
        assert report.grade == "F"
        assert report.has_errors is True
        assert any(i.rule_id == "missing-root-license" for i in report.project_issues)

    def test_scanner_missing_header_and_autofix(self, tmp_path):
        lic_file = tmp_path / "LICENSE"
        lic_file.write_text("MIT License\nCopyright 2026", encoding="utf-8")

        py_file = tmp_path / "utils.py"
        py_file.write_text("def helper():\n    return 42\n", encoding="utf-8")

        scanner = Scanner(tmp_path)
        report_before = scanner.scan()
        assert report_before.missing_header_files == 1
        assert report_before.compliance_rate == 0.0

        # Dry-run fix
        fixed, updated = scanner.fix(license_id="MIT", owner="tester", dry_run=True)
        assert len(fixed) == 1
        assert "utils.py" in fixed[0]
        # File should remain unmodified
        assert "SPDX-License-Identifier" not in py_file.read_text(encoding="utf-8")

        # Actual fix
        fixed, updated = scanner.fix(license_id="MIT", owner="tester", dry_run=False)
        assert len(fixed) == 1
        content_after = py_file.read_text(encoding="utf-8")
        assert "SPDX-License-Identifier: MIT" in content_after

        # Re-scan
        report_after = scanner.scan()
        assert report_after.missing_header_files == 0
        assert report_after.compliant_files == 1
        assert report_after.compliance_rate == 100.0

    def test_scanner_manifest_detection(self, tmp_path):
        cargo = tmp_path / "Cargo.toml"
        cargo.write_text('[package]\nname = "demo"\nlicense = "MIT OR Apache-2.0"\n', encoding="utf-8")

        manifests = read_manifest_licenses(tmp_path)
        assert manifests.get("Cargo.toml") == "MIT OR Apache-2.0"

    def test_exclusion_logic(self, tmp_path):
        git_dir = tmp_path / ".git"
        git_dir.mkdir()
        (git_dir / "config").write_text("foo", encoding="utf-8")

        assert is_path_excluded(git_dir / "config", tmp_path, [".git"]) is True
        assert is_path_excluded(tmp_path / "src" / "index.js", tmp_path, [".git"]) is False
