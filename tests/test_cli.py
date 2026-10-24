"""Tests for license-doctor CLI commands."""

import json
from pathlib import Path
from click.testing import CliRunner
import pytest
from license_doctor.cli import cli


@pytest.fixture
def runner():
    return CliRunner()


class TestCLI:
    def test_version(self, runner):
        result = runner.invoke(cli, ["--version"])
        assert result.exit_code == 0
        assert "license-doctor" in result.output

    def test_validate_spdx_valid(self, runner):
        result = runner.invoke(cli, ["validate-spdx", "MIT OR Apache-2.0"])
        assert result.exit_code == 0
        assert "Valid SPDX Expression" in result.output

    def test_validate_spdx_invalid(self, runner):
        result = runner.invoke(cli, ["validate-spdx", "MIT OR Invaaaalid-License-123"])
        assert result.exit_code != 0
        assert "Invalid SPDX Expression" in result.output

    def test_validate_spdx_json(self, runner):
        result = runner.invoke(cli, ["validate-spdx", "MIT", "--json"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["is_valid"] is True
        assert data["expression"] == "MIT"

    def test_check_clean_project(self, runner, tmp_path):
        lic = tmp_path / "LICENSE"
        lic.write_text("MIT License\nCopyright (c) 2026", encoding="utf-8")
        code = tmp_path / "script.py"
        code.write_text("# SPDX-License-Identifier: MIT\n# SPDX-FileCopyrightText: 2026 Test\nprint('hello')\n", encoding="utf-8")

        result = runner.invoke(cli, ["check", str(tmp_path)])
        assert result.exit_code == 0
        assert "All checked files are compliant" in result.output

    def test_check_fail_missing_header(self, runner, tmp_path):
        lic = tmp_path / "LICENSE"
        lic.write_text("MIT License\nCopyright (c) 2026", encoding="utf-8")
        code = tmp_path / "script.py"
        code.write_text("print('no license header here')\n", encoding="utf-8")

        result = runner.invoke(cli, ["check", str(tmp_path)])
        assert result.exit_code != 0
        assert "License compliance check failed" in result.output

    def test_check_json_output(self, runner, tmp_path):
        lic = tmp_path / "LICENSE"
        lic.write_text("MIT License\nCopyright (c) 2026", encoding="utf-8")
        code = tmp_path / "script.py"
        code.write_text("# SPDX-License-Identifier: MIT\nprint('ok')\n", encoding="utf-8")

        result = runner.invoke(cli, ["check", str(tmp_path), "--json"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["root_license_found"] is True
        assert data["compliant_files"] == 1

    def test_fix_command(self, runner, tmp_path):
        lic = tmp_path / "LICENSE"
        lic.write_text("MIT License\nCopyright (c) 2026", encoding="utf-8")
        code = tmp_path / "script.js"
        code.write_text("console.log('hi');\n", encoding="utf-8")

        # Run fix
        result = runner.invoke(cli, ["fix", str(tmp_path), "--license", "MIT", "--owner", "TestCorp"])
        assert result.exit_code == 0
        assert "Injected headers in 1 files" in result.output

        content = code.read_text(encoding="utf-8")
        assert "SPDX-License-Identifier: MIT" in content
        assert "TestCorp" in content

        # Now check command should pass
        check_res = runner.invoke(cli, ["check", str(tmp_path)])
        assert check_res.exit_code == 0

    def test_fix_dry_run(self, runner, tmp_path):
        lic = tmp_path / "LICENSE"
        lic.write_text("MIT License\nCopyright (c) 2026", encoding="utf-8")
        code = tmp_path / "script.py"
        code.write_text("print('test')\n", encoding="utf-8")

        result = runner.invoke(cli, ["fix", str(tmp_path), "--dry-run", "--license", "MIT"])
        assert result.exit_code == 0
        assert "[DRY RUN]" in result.output

        # File was not modified
        assert "SPDX-License-Identifier" not in code.read_text(encoding="utf-8")

    def test_scan_command(self, runner, tmp_path):
        lic = tmp_path / "LICENSE"
        lic.write_text("MIT License\nCopyright (c) 2026", encoding="utf-8")
        code = tmp_path / "main.go"
        code.write_text("// SPDX-License-Identifier: MIT\npackage main\n", encoding="utf-8")

        result = runner.invoke(cli, ["scan", str(tmp_path)])
        assert result.exit_code == 0
        assert "Repository License Health Audit" in result.output
        assert "Compliance Rate" in result.output

    def test_scan_json(self, runner, tmp_path):
        lic = tmp_path / "LICENSE"
        lic.write_text("MIT License\nCopyright (c) 2026", encoding="utf-8")

        result = runner.invoke(cli, ["scan", str(tmp_path), "--json"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert "compliance_rate" in data
        assert "grade" in data
