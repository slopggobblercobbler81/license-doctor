# SPDX-FileCopyrightText: Copyright (c) 2026 slopggobblercobbler81
# SPDX-License-Identifier: MIT

"""Tests for configuration loading (.license-doctor.toml and pyproject.toml)."""

from pathlib import Path
import pytest
from license_doctor.config import LicenseDoctorConfig


class TestConfig:
    def test_default_config(self):
        cfg = LicenseDoctorConfig()
        assert cfg.target_year >= 2024
        assert ".git" in cfg.exclude
        assert cfg.require_spdx is True

    def test_load_from_dot_toml(self, tmp_path):
        dot_file = tmp_path / ".license-doctor.toml"
        dot_file.write_text(
            """
license = "Apache-2.0"
owner = "Test Org"
target_year = 2027
exclude = ["build_custom", "temp"]
require_spdx = false
""",
            encoding="utf-8",
        )

        cfg = LicenseDoctorConfig.load_from_dir(tmp_path)
        assert cfg.license == "Apache-2.0"
        assert cfg.owner == "Test Org"
        assert cfg.target_year == 2027
        assert "build_custom" in cfg.exclude
        assert cfg.require_spdx is False

    def test_load_from_pyproject_tool_section(self, tmp_path):
        pyproj = tmp_path / "pyproject.toml"
        pyproj.write_text(
            """
[tool.license-doctor]
license = "BSD-3-Clause"
owner = "BSD Authors"
""",
            encoding="utf-8",
        )

        cfg = LicenseDoctorConfig.load_from_dir(tmp_path)
        assert cfg.license == "BSD-3-Clause"
        assert cfg.owner == "BSD Authors"

    def test_load_from_pyproject_standard_metadata(self, tmp_path):
        pyproj = tmp_path / "pyproject.toml"
        pyproj.write_text(
            """
[project]
name = "sample"
license = "MIT"
authors = [{ name = "Author Name" }]
""",
            encoding="utf-8",
        )

        cfg = LicenseDoctorConfig.load_from_dir(tmp_path)
        assert cfg.license == "MIT"
        assert cfg.owner == "Author Name"
