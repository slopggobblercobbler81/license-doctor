"""Header detection, parsing, generation, and injection."""

from __future__ import annotations
import datetime
import re
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Tuple

from license_doctor.languages import LanguageSpec, get_language_spec
from license_doctor.spdx_validator import validate_spdx_expression, SPDXValidationResult

# Regex to find SPDX-License-Identifier
SPDX_IDENTIFIER_REGEX = re.compile(
    r"SPDX-License-Identifier:\s*([^\r\n*#/]+)",
    re.IGNORECASE,
)

# Regex to find Copyright statements
COPYRIGHT_REGEX = re.compile(
    r"(?:SPDX-FileCopyrightText:\s*)?(?:Copyright|©|\(c\)|\(C\))\s+(?:\(c\)|\(C\)|©)?\s*([0-9]{4}(?:\s*[-–]\s*[0-9]{4})?)\s*(?:by\s+)?([^\r\n*#/]+)?",
    re.IGNORECASE,
)

# Alternative simple year pattern in copyright lines:
YEAR_RANGE_REGEX = re.compile(r"(\d{4})\s*[-–]\s*(\d{4})")
SINGLE_YEAR_REGEX = re.compile(r"\b(19\d{2}|20\d{2})\b")


@dataclass
class HeaderInfo:
    """Information detected from a file header."""
    has_header: bool
    spdx_expression: Optional[str] = None
    spdx_validation: Optional[SPDXValidationResult] = None
    copyright_line: Optional[str] = None
    copyright_start_year: Optional[int] = None
    copyright_end_year: Optional[int] = None
    copyright_holder: Optional[str] = None
    is_year_outdated: bool = False
    header_line_start: int = 0
    header_line_end: int = 0


COMMENT_LINE_REGEX = re.compile(r"^\s*(?:#|//|/\*|\*|<!--|--|;|\bREM\b)")

# Lines defining variables or regexes should not be parsed as headers
CODE_LINE_IGNORE_REGEX = re.compile(r"^\s*(?:[A-Za-z_][A-Za-z0-9_]*\s*=|const |let |var |static |final )")


def detect_header(
    content: str,
    target_year: Optional[int] = None,
    max_lines: int = 40,
) -> HeaderInfo:
    """Detect and analyze license and copyright headers in the given file text."""
    if target_year is None:
        target_year = datetime.datetime.now().year

    lines = content.splitlines()[:max_lines]
    spdx_expr: Optional[str] = None
    copyright_line: Optional[str] = None
    start_year: Optional[int] = None
    end_year: Optional[int] = None
    holder: Optional[str] = None
    first_header_line = -1
    last_header_line = -1

    for idx, line in enumerate(lines):
        # File license headers must be at file top-level (not indented inside functions/classes)
        if line.startswith(" ") or line.startswith("\t"):
            continue

        # Ignore code variable assignments or regex definitions
        if CODE_LINE_IGNORE_REGEX.match(line):
            continue

        # Check SPDX Identifier
        spdx_match = SPDX_IDENTIFIER_REGEX.search(line)
        if spdx_match and not spdx_expr:
            matched_id = spdx_match.group(1).strip()
            # Must look like an SPDX expression (letters, numbers, dash, dot, parens, operators)
            if re.match(r"^[A-Za-z0-9\.\-\+\(\)\s]+$", matched_id):
                spdx_expr = matched_id
                if first_header_line == -1:
                    first_header_line = idx
                last_header_line = max(last_header_line, idx)

        # Check Copyright
        c_match = COPYRIGHT_REGEX.search(line)
        if c_match and not copyright_line:
            copyright_line = line.strip()
            raw_years = c_match.group(1).strip()
            raw_holder = c_match.group(2).strip() if c_match.group(2) else None
            if raw_holder:
                clean_holder = re.sub(r"[\s*#/->]+$", "", raw_holder).strip()
                if clean_holder:
                    holder = clean_holder

            # Parse years
            range_match = YEAR_RANGE_REGEX.search(raw_years)
            if range_match:
                start_year = int(range_match.group(1))
                end_year = int(range_match.group(2))
            else:
                single_match = SINGLE_YEAR_REGEX.search(raw_years)
                if single_match:
                    start_year = int(single_match.group(1))
                    end_year = start_year

            if first_header_line == -1:
                first_header_line = idx
            last_header_line = max(last_header_line, idx)

    # If copyright year was not caught by main regex, try fallback scan in comment lines
    if not start_year and any("copyright" in l.lower() for l in lines[:20]):
        for idx, line in enumerate(lines[:20]):
            if CODE_LINE_IGNORE_REGEX.match(line):
                continue
            if "copyright" in line.lower():
                years = SINGLE_YEAR_REGEX.findall(line)
                if years:
                    parsed_years = [int(y) for y in years]
                    start_year = min(parsed_years)
                    end_year = max(parsed_years)
                    if not copyright_line:
                        copyright_line = line.strip()
                    if first_header_line == -1:
                        first_header_line = idx
                    last_header_line = max(last_header_line, idx)
                    break

    has_header = spdx_expr is not None or copyright_line is not None

    spdx_val = None
    if spdx_expr:
        spdx_val = validate_spdx_expression(spdx_expr)

    is_outdated = False
    if end_year is not None and target_year is not None:
        if end_year < target_year:
            is_outdated = True

    return HeaderInfo(
        has_header=has_header,
        spdx_expression=spdx_expr,
        spdx_validation=spdx_val,
        copyright_line=copyright_line,
        copyright_start_year=start_year,
        copyright_end_year=end_year,
        copyright_holder=holder,
        is_year_outdated=is_outdated,
        header_line_start=max(0, first_header_line),
        header_line_end=max(0, last_header_line),
    )


def generate_header_lines(
    spdx_license: str,
    owner: Optional[str] = None,
    year: Optional[int] = None,
    start_year: Optional[int] = None,
) -> List[str]:
    """Generate canonical header lines."""
    if year is None:
        year = datetime.datetime.now().year

    if start_year and start_year < year:
        year_str = f"{start_year}-{year}"
    else:
        year_str = str(year)

    lines = []
    if owner:
        lines.append(f"SPDX-FileCopyrightText: Copyright (c) {year_str} {owner}")
    lines.append(f"SPDX-License-Identifier: {spdx_license}")
    return lines


def format_header_for_language(
    language: LanguageSpec,
    spdx_license: str,
    owner: Optional[str] = None,
    year: Optional[int] = None,
    start_year: Optional[int] = None,
    use_block: bool = False,
) -> str:
    """Format header block string ready to be prepended to code."""
    lines = generate_header_lines(
        spdx_license=spdx_license,
        owner=owner,
        year=year,
        start_year=start_year,
    )
    return language.format_header(lines, use_block=use_block)


def find_header_insertion_index(content: str) -> int:
    """
    Find character index where the license header should be inserted,
    preserving shebangs, encoding cookies, and XML declarations.
    """
    lines = content.splitlines(keepends=True)
    if not lines:
        return 0

    idx = 0
    # Check Shebang on line 1
    if lines[0].startswith("#!"):
        idx += len(lines[0])
        # Check if line 2 is encoding cookie (e.g. in Python)
        if len(lines) > 1 and re.search(r"coding[:=]\s*([-\w.]+)", lines[1]):
            idx += len(lines[1])
        return idx

    # Check XML declaration
    if lines[0].startswith("<?xml"):
        idx += len(lines[0])
        return idx

    # Check encoding cookie on line 1
    if re.search(r"coding[:=]\s*([-\w.]+)", lines[0]):
        idx += len(lines[0])
        return idx

    return 0


def update_copyright_year_in_content(
    content: str,
    target_year: int,
) -> Tuple[str, bool]:
    """
    Find outdated copyright year in content and update it to end with target_year.
    e.g. 2018-2022 -> 2018-2026, or 2021 -> 2021-2026.
    Returns (updated_content, was_modified).
    """
    lines = content.splitlines(keepends=True)
    modified = False
    new_lines = []

    for i, line in enumerate(lines[:50]):
        if modified:
            new_lines.append(line)
            continue

        # Top-level comment lines only
        if line.startswith(" ") or line.startswith("\t") or CODE_LINE_IGNORE_REGEX.match(line):
            new_lines.append(line)
            continue

        c_match = COPYRIGHT_REGEX.search(line)
        if c_match:
            raw_years = c_match.group(1).strip()
            range_match = YEAR_RANGE_REGEX.search(raw_years)
            if range_match:
                sy = int(range_match.group(1))
                ey = int(range_match.group(2))
                if ey < target_year:
                    new_year_str = f"{sy}-{target_year}"
                    updated_line = line.replace(raw_years, new_year_str)
                    new_lines.append(updated_line)
                    modified = True
                    continue
            else:
                single_match = SINGLE_YEAR_REGEX.search(raw_years)
                if single_match:
                    sy = int(single_match.group(1))
                    if sy < target_year:
                        new_year_str = f"{sy}-{target_year}"
                        # Replace the year occurrence
                        updated_line = line.replace(str(sy), new_year_str, 1)
                        new_lines.append(updated_line)
                        modified = True
                        continue

        new_lines.append(line)

    new_lines.extend(lines[50:])
    return "".join(new_lines), modified


def inject_license_header(
    content: str,
    language: LanguageSpec,
    spdx_license: str,
    owner: Optional[str] = None,
    year: Optional[int] = None,
    use_block: bool = False,
) -> str:
    """
    Inject a fresh license header into content at the proper position.
    """
    header_text = format_header_for_language(
        language=language,
        spdx_license=spdx_license,
        owner=owner,
        year=year,
        use_block=use_block,
    )

    insert_pos = find_header_insertion_index(content)
    if insert_pos == 0:
        # Prepend
        if content and not content.startswith("\n"):
            return f"{header_text}\n{content}"
        return f"{header_text}{content}"
    else:
        prefix = content[:insert_pos]
        suffix = content[insert_pos:]
        if not prefix.endswith("\n"):
            prefix = prefix + "\n"
        if suffix and not suffix.startswith("\n"):
            suffix = f"\n{suffix}"
        return f"{prefix}\n{header_text}{suffix.lstrip()}"
