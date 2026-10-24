"""Tests for license header detection, insertion, and copyright year updating."""

import pytest
from pathlib import Path
from license_doctor.headers import (
    detect_header,
    generate_header_lines,
    format_header_for_language,
    find_header_insertion_index,
    update_copyright_year_in_content,
    inject_license_header,
)
from license_doctor.languages import get_language_spec


class TestHeaderDetection:
    def test_spdx_identifier_detection(self):
        content = """# SPDX-License-Identifier: MIT
def hello():
    pass
"""
        info = detect_header(content, target_year=2026)
        assert info.has_header is True
        assert info.spdx_expression == "MIT"
        assert info.spdx_validation.is_valid is True

    def test_copyright_detection_and_years(self):
        content = """// Copyright (c) 2021-2024 Jane Doe. All rights reserved.
// SPDX-License-Identifier: Apache-2.0

package main
"""
        info = detect_header(content, target_year=2026)
        assert info.has_header is True
        assert info.spdx_expression == "Apache-2.0"
        assert info.copyright_start_year == 2021
        assert info.copyright_end_year == 2024
        assert "Jane Doe" in (info.copyright_holder or "")
        assert info.is_year_outdated is True

    def test_copyright_current_year(self):
        content = """# SPDX-FileCopyrightText: Copyright (c) 2026 slopggobblercobbler81
# SPDX-License-Identifier: MIT
"""
        info = detect_header(content, target_year=2026)
        assert info.has_header is True
        assert info.copyright_end_year == 2026
        assert info.is_year_outdated is False

    def test_no_header(self):
        content = """def add(a, b):
    return a + b
"""
        info = detect_header(content)
        assert info.has_header is False
        assert info.spdx_expression is None


class TestHeaderInsertion:
    def test_find_insertion_index_shebang(self):
        shebang_content = "#!/usr/bin/env python3\n\nimport os\n"
        idx = find_header_insertion_index(shebang_content)
        assert idx == len("#!/usr/bin/env python3\n")

    def test_find_insertion_index_xml(self):
        xml_content = '<?xml version="1.0" encoding="UTF-8"?>\n<note></note>\n'
        idx = find_header_insertion_index(xml_content)
        assert idx == len('<?xml version="1.0" encoding="UTF-8"?>\n')

    def test_find_insertion_index_plain(self):
        plain_content = "def add(a, b):\n    return a + b\n"
        idx = find_header_insertion_index(plain_content)
        assert idx == 0

    def test_inject_header_shebang(self):
        content = "#!/usr/bin/env python3\nprint('hello')\n"
        spec = get_language_spec(Path("test.py"))
        result = inject_license_header(
            content=content,
            language=spec,
            spdx_license="MIT",
            owner="slopggobblercobbler81",
            year=2026,
        )
        assert result.startswith("#!/usr/bin/env python3\n")
        assert "# SPDX-License-Identifier: MIT" in result
        assert "# SPDX-FileCopyrightText: Copyright (c) 2026 slopggobblercobbler81" in result
        assert "print('hello')" in result

    def test_inject_header_plain_js(self):
        content = "console.log('hello world');\n"
        spec = get_language_spec(Path("app.js"))
        result = inject_license_header(
            content=content,
            language=spec,
            spdx_license="Apache-2.0",
            owner="Acme Corp",
            year=2026,
        )
        assert result.startswith("// SPDX-FileCopyrightText: Copyright (c) 2026 Acme Corp\n// SPDX-License-Identifier: Apache-2.0\n")
        assert "console.log('hello world');" in result

    def test_update_copyright_year_range(self):
        old_content = "// Copyright (c) 2019-2022 Jane Doe\n// SPDX-License-Identifier: MIT\n"
        new_content, modified = update_copyright_year_in_content(old_content, target_year=2026)
        assert modified is True
        assert "2019-2026" in new_content
        assert "2019-2022" not in new_content

    def test_update_copyright_single_year(self):
        old_content = "# Copyright (c) 2021 Acme Corp\n# SPDX-License-Identifier: MIT\n"
        new_content, modified = update_copyright_year_in_content(old_content, target_year=2026)
        assert modified is True
        assert "2021-2026" in new_content
