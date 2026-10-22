"""Source code file license header auditor and auto-fix injector."""

from __future__ import annotations
import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Set, Tuple

SPDX_HEADER_REGEX = re.compile(
    r"(?:SPDX-License-Identifier:\s*([A-Za-z0-9._+-]+(?:\s+(?:AND|OR|WITH)\s+[A-Za-z0-9._+-]+)*))",
    re.IGNORECASE,
)
COPYRIGHT_REGEX = re.compile(
    r"(?:copyright\s+(?:\(c\)\s+)?(?:(?:\d{4}-)?\d{4}\s+)?([A-Za-z0-9._\- ]+))",
    re.IGNORECASE,
)

COMMENT_PREFIX_BY_EXT: Dict[str, str] = {
    ".py": "#",
    ".sh": "#",
    ".bash": "#",
    ".rb": "#",
    ".pl": "#",
    ".yaml": "#",
    ".yml": "#",
    ".toml": "#",
    ".r": "#",
    ".js": "//",
    ".ts": "//",
    ".jsx": "//",
    ".tsx": "//",
    ".c": "//",
    ".cpp": "//",
    ".cc": "//",
    ".cxx": "//",
    ".h": "//",
    ".hpp": "//",
    ".cs": "//",
    ".go": "//",
    ".rs": "//",
    ".java": "//",
    ".kt": "//",
    ".swift": "//",
    ".php": "//",
    ".sql": "--",
    ".lua": "--",
    ".hs": "--",
}


@dataclass
class FileAuditResult:
    file_path: str
    has_spdx_header: bool
    spdx_license: Optional[str] = None
    has_copyright: bool = False
    copyright_holder: Optional[str] = None
    is_consistent: bool = True
    error_message: Optional[str] = None


@dataclass
class AuditReport:
    total_scanned: int
    with_spdx_headers: int
    without_spdx_headers: int
    coverage_percent: float
    results: List[FileAuditResult] = field(default_factory=list)
    license_distribution: Dict[str, int] = field(default_factory=dict)
    root_license: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "total_scanned": self.total_scanned,
            "with_spdx_headers": self.with_spdx_headers,
            "without_spdx_headers": self.without_spdx_headers,
            "coverage_percent": round(self.coverage_percent, 2),
            "root_license": self.root_license,
            "license_distribution": self.license_distribution,
            "missing_sample": [r.file_path for r in self.results if not r.has_spdx_header][:20],
        }


def detect_root_license(repo_path: Path) -> Optional[str]:
    """Detect root LICENSE file and identify primary SPDX license if possible."""
    candidates = ["LICENSE", "LICENSE.md", "LICENSE.txt", "COPYING"]
    for cand in candidates:
        f = repo_path / cand
        if f.is_file():
            text = f.read_text(encoding="utf-8", errors="ignore")
            # Look for SPDX header
            spdx_match = SPDX_HEADER_REGEX.search(text)
            if spdx_match:
                return spdx_match.group(1).strip()
            # Fast heuristic keywords
            if "Apache License" in text and ("Version 2.0" in text or "2.0" in text):
                return "Apache-2.0"
            if "MIT License" in text or "Permission is hereby granted" in text:
                return "MIT"
            if "Redistribution and use in source and binary forms" in text:
                if "Neither the name of the copyright holder" in text:
                    return "BSD-3-Clause"
                return "BSD-2-Clause"
            if "Mozilla Public License" in text and "2.0" in text:
                return "MPL-2.0"
            if "GNU GENERAL PUBLIC LICENSE" in text:
                if "Version 3" in text:
                    return "GPL-3.0-only"
                if "Version 2" in text:
                    return "GPL-2.0-only"
    return None


def audit_file(file_path: Path, expected_license: Optional[str] = None) -> FileAuditResult:
    """Audit a single source file for license headers."""
    rel_str = str(file_path)
    try:
        content = file_path.read_text(encoding="utf-8", errors="ignore")
    except Exception as e:
        return FileAuditResult(file_path=rel_str, has_spdx_header=False, error_message=str(e))

    # Only scan first 40 lines for license header
    first_lines = "\n".join(content.splitlines()[:40])

    spdx_match = SPDX_HEADER_REGEX.search(first_lines)
    spdx_lic = spdx_match.group(1).strip() if spdx_match else None

    cr_match = COPYRIGHT_REGEX.search(first_lines)
    cr_holder = cr_match.group(1).strip() if cr_match else None

    is_consistent = True
    if expected_license and spdx_lic:
        is_consistent = (expected_license.lower() == spdx_lic.lower())

    return FileAuditResult(
        file_path=rel_str,
        has_spdx_header=bool(spdx_lic),
        spdx_license=spdx_lic,
        has_copyright=bool(cr_match),
        copyright_holder=cr_holder,
        is_consistent=is_consistent,
    )


def audit_repository(
    repo_path: Path,
    expected_license: Optional[str] = None,
    include_extensions: Optional[Set[str]] = None,
) -> AuditReport:
    """Audit source files across a repository directory."""
    extensions = include_extensions or set(COMMENT_PREFIX_BY_EXT.keys())
    ignored_dirs = {".git", ".pytest_cache", ".mypy_cache", "__pycache__", "node_modules", "venv", ".venv", "dist", "build"}

    root_lic = expected_license or detect_root_license(repo_path)

    results: List[FileAuditResult] = []
    distribution: Dict[str, int] = {}
    with_headers = 0

    for root, dirs, files in os.walk(repo_path):
        dirs[:] = [d for d in dirs if d not in ignored_dirs]
        for fn in files:
            ext = os.path.splitext(fn)[1].lower()
            if ext in extensions:
                p = Path(root) / fn
                res = audit_file(p, expected_license=root_lic)
                results.append(res)
                if res.has_spdx_header:
                    with_headers += 1
                    if res.spdx_license:
                        distribution[res.spdx_license] = distribution.get(res.spdx_license, 0) + 1

    total = len(results)
    cov = (with_headers / total * 100.0) if total > 0 else 100.0

    return AuditReport(
        total_scanned=total,
        with_spdx_headers=with_headers,
        without_spdx_headers=total - with_headers,
        coverage_percent=cov,
        results=results,
        license_distribution=distribution,
        root_license=root_lic,
    )


def inject_spdx_header(file_path: Path, license_id: str) -> bool:
    """Inject an SPDX-License-Identifier header into a source file using appropriate comment syntax.
    
    Returns True if injected, False if already present or unsupported.
    """
    ext = file_path.suffix.lower()
    prefix = COMMENT_PREFIX_BY_EXT.get(ext)
    if not prefix:
        return False

    content = file_path.read_text(encoding="utf-8", errors="ignore")
    if SPDX_HEADER_REGEX.search(content[:500]):
        return False  # Already present

    header_line = f"{prefix} SPDX-License-Identifier: {license_id}\n"
    lines = content.splitlines(keepends=True)

    # Check for shebang on first line (e.g. #!/usr/bin/env python3)
    if lines and lines[0].startswith("#!"):
        new_lines = [lines[0], header_line] + lines[1:]
    else:
        new_lines = [header_line] + lines

    file_path.write_text("".join(new_lines), encoding="utf-8")
    return True
