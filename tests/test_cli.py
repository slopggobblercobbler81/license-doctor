"""Unit tests for license-doctor CLI commands."""

import json
import pytest
from pathlib import Path
from license_doctor.cli import main


def test_cli_version(capsys):
    with pytest.raises(SystemExit) as exc:
        main(["--version"])
    assert exc.value.code == 0
    captured = capsys.readouterr()
    assert "license-doctor 0.1.0" in captured.out or "license-doctor 0.1.0" in captured.err


def test_cli_validate_success(capsys):
    code = main(["validate", "MIT OR Apache-2.0"])
    assert code == 0
    captured = capsys.readouterr()
    assert "[VALID]" in captured.out
    assert "MIT, Apache-2.0" in captured.out


def test_cli_validate_failure(capsys):
    code = main(["validate", "Invalid-Lic-XYZ"])
    assert code == 1
    captured = capsys.readouterr()
    assert "[INVALID]" in captured.out


def test_cli_validate_json(capsys):
    code = main(["validate", "MIT", "--json"])
    assert code == 0
    captured = capsys.readouterr()
    data = json.loads(captured.out)
    assert data["is_valid"] is True
    assert data["identifiers"] == ["MIT"]


def test_cli_compat_success(capsys):
    code = main(["compat", "MIT", "Apache-2.0"])
    assert code == 0
    captured = capsys.readouterr()
    assert "[COMPATIBLE]" in captured.out
    assert "Apache-2.0" in captured.out


def test_cli_compat_failure(capsys):
    code = main(["compat", "Apache-2.0", "GPL-2.0-only"])
    assert code == 1
    captured = capsys.readouterr()
    assert "[INCOMPATIBLE]" in captured.out


def test_cli_compat_json(capsys):
    code = main(["compat", "MIT", "BSD-3-Clause", "--json"])
    assert code == 0
    captured = capsys.readouterr()
    data = json.loads(captured.out)
    assert data["is_compatible"] is True


def test_cli_generate_stdout(capsys):
    code = main(["generate", "MIT", "--holder", "Acme", "--year", "2026"])
    assert code == 0
    captured = capsys.readouterr()
    assert "MIT License" in captured.out
    assert "Copyright (c) 2026 Acme" in captured.out


def test_cli_generate_file(tmp_path):
    out_file = tmp_path / "LICENSE"
    code = main(["generate", "BSD-2-Clause", "--holder", "Alice", "-o", str(out_file)])
    assert code == 0
    assert out_file.exists()
    assert "BSD 2-Clause License" in out_file.read_text(encoding="utf-8")


def test_cli_generate_list(capsys):
    code = main(["generate", "--list"])
    assert code == 0
    captured = capsys.readouterr()
    assert "Available license templates:" in captured.out
    assert "MIT" in captured.out


def test_cli_generate_error(capsys):
    code = main(["generate", "NonexistentLicense"])
    assert code == 1
    captured = capsys.readouterr()
    assert "Unknown license template" in captured.err


def test_cli_audit_and_fix(tmp_path, capsys):
    (tmp_path / "main.py").write_text("print(1)", encoding="utf-8")
    (tmp_path / "util.js").write_text("console.log(1);", encoding="utf-8")

    # Initial audit without headers
    code_init = main(["audit", str(tmp_path), "--license", "MIT"])
    assert code_init == 0
    captured_init = capsys.readouterr()
    assert "Missing Headers     : 2" in captured_init.out

    # Audit with --min-coverage failure
    code_fail = main(["audit", str(tmp_path), "--license", "MIT", "--min-coverage", "90"])
    assert code_fail == 1

    # Auto-fix injection
    code_fix = main(["audit", str(tmp_path), "--license", "MIT", "--fix"])
    assert code_fix == 0
    captured_fix = capsys.readouterr()
    assert "Auto-injected Headers: 2 files" in captured_fix.out

    # Re-audit should now have 100% coverage
    code_re = main(["audit", str(tmp_path), "--license", "MIT", "--min-coverage", "90"])
    assert code_re == 0


def test_cli_audit_json(tmp_path, capsys):
    (tmp_path / "index.ts").write_text("// SPDX-License-Identifier: MIT\n", encoding="utf-8")
    code = main(["audit", str(tmp_path), "--license", "MIT", "--json"])
    assert code == 0
    captured = capsys.readouterr()
    data = json.loads(captured.out)
    assert data["total_scanned"] == 1
    assert data["with_spdx_headers"] == 1
    assert data["coverage_percent"] == 100.0


def test_cli_default_audit_invocation(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "test.py").write_text("# SPDX-License-Identifier: MIT\n", encoding="utf-8")
    code = main([])
    assert code == 0


def test_cli_validate_warning(capsys):
    code = main(["validate", "GPL-3.0"])
    assert code == 0
    captured = capsys.readouterr()
    assert "[VALID]" in captured.out
    assert "Canonical form: GPL-3.0-only" in captured.out


def test_cli_generate_missing_arg(capsys):
    code = main(["generate"])
    assert code == 1
    captured = capsys.readouterr()
    assert "License identifier required" in captured.err


def test_cli_audit_missing_dir(capsys):
    code = main(["audit", "nonexistent_dir_xyz"])
    assert code == 1
    captured = capsys.readouterr()
    assert "not a valid directory" in captured.err


def test_cli_audit_fix_without_license(tmp_path, capsys):
    (tmp_path / "main.py").write_text("x = 1", encoding="utf-8")
    code = main(["audit", str(tmp_path), "--fix"])
    assert code == 1
    captured = capsys.readouterr()
    assert "Cannot auto-fix without target license" in captured.err
