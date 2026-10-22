"""Unit tests for repository license header auditor and auto-fix injector."""

import pytest
from pathlib import Path
from license_doctor.auditor import (
    audit_file,
    audit_repository,
    detect_root_license,
    inject_spdx_header,
)


def test_detect_root_license(tmp_path):
    license_file = tmp_path / "LICENSE"
    license_file.write_text("Permission is hereby granted, free of charge ... MIT", encoding="utf-8")
    assert detect_root_license(tmp_path) == "MIT"

    apache_file = tmp_path / "LICENSE"
    apache_file.write_text("Apache License\nVersion 2.0, January 2004", encoding="utf-8")
    assert detect_root_license(tmp_path) == "Apache-2.0"


def test_audit_file_with_spdx_header(tmp_path):
    py_file = tmp_path / "app.py"
    py_file.write_text("""# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Author

def main():
    pass
""", encoding="utf-8")

    result = audit_file(py_file, expected_license="MIT")
    assert result.has_spdx_header is True
    assert result.spdx_license == "MIT"
    assert result.has_copyright is True
    assert result.is_consistent is True


def test_audit_file_inconsistent_license(tmp_path):
    py_file = tmp_path / "util.py"
    py_file.write_text("# SPDX-License-Identifier: GPL-3.0-only\n", encoding="utf-8")

    result = audit_file(py_file, expected_license="MIT")
    assert result.has_spdx_header is True
    assert result.spdx_license == "GPL-3.0-only"
    assert result.is_consistent is False


def test_audit_repository(tmp_path):
    (tmp_path / "LICENSE").write_text("Permission is hereby granted ... MIT", encoding="utf-8")
    (tmp_path / "one.py").write_text("# SPDX-License-Identifier: MIT\n", encoding="utf-8")
    (tmp_path / "two.js").write_text("// SPDX-License-Identifier: MIT\n", encoding="utf-8")
    (tmp_path / "three.go").write_text("// Missing license header\npackage main\n", encoding="utf-8")

    report = audit_repository(tmp_path)
    assert report.total_scanned == 3
    assert report.with_spdx_headers == 2
    assert report.without_spdx_headers == 1
    assert round(report.coverage_percent, 1) == 66.7
    assert report.root_license == "MIT"


def test_inject_spdx_header_python(tmp_path):
    py_file = tmp_path / "script.py"
    py_file.write_text("print('hello')", encoding="utf-8")

    injected = inject_spdx_header(py_file, "Apache-2.0")
    assert injected is True
    content = py_file.read_text(encoding="utf-8")
    assert content.startswith("# SPDX-License-Identifier: Apache-2.0\n")

    # Second injection should be skipped
    assert inject_spdx_header(py_file, "Apache-2.0") is False


def test_inject_spdx_header_with_shebang(tmp_path):
    sh_file = tmp_path / "run.sh"
    sh_file.write_text("#!/usr/bin/env bash\necho 1", encoding="utf-8")

    injected = inject_spdx_header(sh_file, "MIT")
    assert injected is True
    lines = sh_file.read_text(encoding="utf-8").splitlines()
    assert lines[0] == "#!/usr/bin/env bash"
    assert lines[1] == "# SPDX-License-Identifier: MIT"


def test_detect_root_license_other_formats(tmp_path):
    # BSD-3
    f_bsd3 = tmp_path / "LICENSE"
    f_bsd3.write_text("Redistribution and use in source and binary forms\nNeither the name of the copyright holder\n", encoding="utf-8")
    assert detect_root_license(tmp_path) == "BSD-3-Clause"

    # BSD-2
    f_bsd2 = tmp_path / "LICENSE"
    f_bsd2.write_text("Redistribution and use in source and binary forms\nAll rights reserved\n", encoding="utf-8")
    assert detect_root_license(tmp_path) == "BSD-2-Clause"

    # MPL-2.0
    f_mpl = tmp_path / "LICENSE"
    f_mpl.write_text("Mozilla Public License\nVersion 2.0\n", encoding="utf-8")
    assert detect_root_license(tmp_path) == "MPL-2.0"

    # GPL-3.0
    f_gpl3 = tmp_path / "LICENSE"
    f_gpl3.write_text("GNU GENERAL PUBLIC LICENSE\nVersion 3\n", encoding="utf-8")
    assert detect_root_license(tmp_path) == "GPL-3.0-only"

    # GPL-2.0
    f_gpl2 = tmp_path / "LICENSE"
    f_gpl2.write_text("GNU GENERAL PUBLIC LICENSE\nVersion 2\n", encoding="utf-8")
    assert detect_root_license(tmp_path) == "GPL-2.0-only"


def test_inject_unsupported_extension(tmp_path):
    txt_file = tmp_path / "data.unsupported"
    txt_file.write_text("random content", encoding="utf-8")
    assert inject_spdx_header(txt_file, "MIT") is False
