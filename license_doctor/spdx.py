"""SPDX license identifier database, compound expression parser, and validator."""

from __future__ import annotations
import enum
import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Tuple


class LicenseCategory(str, enum.Enum):
    PERMISSIVE = "permissive"
    WEAK_COPYLEFT = "weak_copyleft"
    STRONG_COPYLEFT = "strong_copyleft"
    NETWORK_COPYLEFT = "network_copyleft"
    PUBLIC_DOMAIN = "public_domain"
    PROPRIETARY = "proprietary"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class LicenseMeta:
    id: str
    name: str
    category: LicenseCategory
    osi_approved: bool = True
    fsf_free: bool = True


# Standard curated database of common & official SPDX license identifiers
SPDX_DATABASE: Dict[str, LicenseMeta] = {
    "MIT": LicenseMeta("MIT", "MIT License", LicenseCategory.PERMISSIVE),
    "Apache-2.0": LicenseMeta("Apache-2.0", "Apache License 2.0", LicenseCategory.PERMISSIVE),
    "BSD-2-Clause": LicenseMeta("BSD-2-Clause", "BSD 2-Clause \"Simplified\" License", LicenseCategory.PERMISSIVE),
    "BSD-3-Clause": LicenseMeta("BSD-3-Clause", "BSD 3-Clause \"New\" or \"Revised\" License", LicenseCategory.PERMISSIVE),
    "ISC": LicenseMeta("ISC", "ISC License", LicenseCategory.PERMISSIVE),
    "0BSD": LicenseMeta("0BSD", "BSD Zero Clause License", LicenseCategory.PERMISSIVE),
    "Unlicense": LicenseMeta("Unlicense", "The Unlicense", LicenseCategory.PUBLIC_DOMAIN),
    "CC0-1.0": LicenseMeta("CC0-1.0", "Creative Commons Zero v1.0 Universal", LicenseCategory.PUBLIC_DOMAIN),
    "MPL-2.0": LicenseMeta("MPL-2.0", "Mozilla Public License 2.0", LicenseCategory.WEAK_COPYLEFT),
    "LGPL-2.1-only": LicenseMeta("LGPL-2.1-only", "GNU Lesser General Public License v2.1 only", LicenseCategory.WEAK_COPYLEFT),
    "LGPL-2.1-or-later": LicenseMeta("LGPL-2.1-or-later", "GNU Lesser General Public License v2.1 or later", LicenseCategory.WEAK_COPYLEFT),
    "LGPL-3.0-only": LicenseMeta("LGPL-3.0-only", "GNU Lesser General Public License v3.0 only", LicenseCategory.WEAK_COPYLEFT),
    "LGPL-3.0-or-later": LicenseMeta("LGPL-3.0-or-later", "GNU Lesser General Public License v3.0 or later", LicenseCategory.WEAK_COPYLEFT),
    "GPL-2.0-only": LicenseMeta("GPL-2.0-only", "GNU General Public License v2.0 only", LicenseCategory.STRONG_COPYLEFT),
    "GPL-2.0-or-later": LicenseMeta("GPL-2.0-or-later", "GNU General Public License v2.0 or later", LicenseCategory.STRONG_COPYLEFT),
    "GPL-3.0-only": LicenseMeta("GPL-3.0-only", "GNU General Public License v3.0 only", LicenseCategory.STRONG_COPYLEFT),
    "GPL-3.0-or-later": LicenseMeta("GPL-3.0-or-later", "GNU General Public License v3.0 or later", LicenseCategory.STRONG_COPYLEFT),
    "AGPL-3.0-only": LicenseMeta("AGPL-3.0-only", "GNU Affero General Public License v3.0 only", LicenseCategory.NETWORK_COPYLEFT),
    "AGPL-3.0-or-later": LicenseMeta("AGPL-3.0-or-later", "GNU Affero General Public License v3.0 or later", LicenseCategory.NETWORK_COPYLEFT),
    "EPL-2.0": LicenseMeta("EPL-2.0", "Eclipse Public License 2.0", LicenseCategory.WEAK_COPYLEFT),
    "BSL-1.0": LicenseMeta("BSL-1.0", "Boost Software License 1.0", LicenseCategory.PERMISSIVE),
    "Zlib": LicenseMeta("Zlib", "zlib License", LicenseCategory.PERMISSIVE),
    "CC-BY-4.0": LicenseMeta("CC-BY-4.0", "Creative Commons Attribution 4.0 International", LicenseCategory.PERMISSIVE),
    "CC-BY-SA-4.0": LicenseMeta("CC-BY-SA-4.0", "Creative Commons Attribution Share Alike 4.0 International", LicenseCategory.WEAK_COPYLEFT),
}

# Standard exceptions allowed after 'WITH'
SPDX_EXCEPTIONS: Set[str] = {
    "Classpath-exception-2.0",
    "LLVM-exception",
    "Autoconf-exception-3.0",
    "GCC-exception-3.1",
    "Bison-exception-2.2",
    "Bootloader-exception",
    "Font-exception-2.0",
}

# Deprecated or colloquial identifiers mapped to modern canonical SPDX IDs
DEPRECATED_MAPPINGS: Dict[str, str] = {
    "GPL-2.0": "GPL-2.0-only",
    "GPL-3.0": "GPL-3.0-only",
    "LGPL-2.1": "LGPL-2.1-only",
    "LGPL-3.0": "LGPL-3.0-only",
    "AGPL-3.0": "AGPL-3.0-only",
    "BSD-2-clause": "BSD-2-Clause",
    "BSD-3-clause": "BSD-3-Clause",
    "Apache2.0": "Apache-2.0",
    "Apache-2": "Apache-2.0",
    "MIT-License": "MIT",
}


@dataclass
class ValidationIssue:
    message: str
    is_error: bool = True
    token: Optional[str] = None
    suggestion: Optional[str] = None


@dataclass
class ExpressionValidationReport:
    raw_expression: str
    is_valid: bool
    identifiers: List[str] = field(default_factory=list)
    exceptions: List[str] = field(default_factory=list)
    issues: List[ValidationIssue] = field(default_factory=list)
    canonical_expression: Optional[str] = None

    @property
    def errors(self) -> List[ValidationIssue]:
        return [i for i in self.issues if i.is_error]

    @property
    def warnings(self) -> List[ValidationIssue]:
        return [i for i in self.issues if not i.is_error]

    def to_dict(self) -> dict:
        return {
            "expression": self.raw_expression,
            "is_valid": self.is_valid,
            "canonical_expression": self.canonical_expression,
            "identifiers": self.identifiers,
            "exceptions": self.exceptions,
            "errors": [{"message": e.message, "token": e.token, "suggestion": e.suggestion} for e in self.errors],
            "warnings": [{"message": w.message, "token": w.token, "suggestion": w.suggestion} for w in self.warnings],
        }


def tokenize_spdx(expression: str) -> List[str]:
    """Tokenize a compound SPDX expression into parentheses, operators, and license IDs."""
    tokens: List[str] = []
    # Match parentheses, operators, and identifiers
    pattern = re.compile(r"\(|\)|AND|OR|WITH|[A-Za-z0-9._+-]+", re.IGNORECASE)
    for match in pattern.finditer(expression):
        val = match.group(0)
        upper = val.upper()
        if upper in ("AND", "OR", "WITH"):
            tokens.append(upper)
        else:
            tokens.append(val)
    return tokens


def validate_spdx_expression(expression: str) -> ExpressionValidationReport:
    """Validate a single or compound SPDX license expression according to SPDX 3.0 specs."""
    expr = expression.strip()
    if not expr:
        return ExpressionValidationReport(
            raw_expression="",
            is_valid=False,
            issues=[ValidationIssue(message="Empty license expression.")],
        )

    tokens = tokenize_spdx(expr)
    if not tokens:
        return ExpressionValidationReport(
            raw_expression=expr,
            is_valid=False,
            issues=[ValidationIssue(message="No valid tokens found in expression.")],
        )

    identifiers: List[str] = []
    exceptions: List[str] = []
    issues: List[ValidationIssue] = []
    canonical_tokens: List[str] = []

    paren_depth = 0
    expect_operand = True  # At start, we expect an identifier or '('
    expect_exception = False

    for idx, token in enumerate(tokens):
        if token == "(":
            if not expect_operand:
                issues.append(ValidationIssue(message=f"Unexpected '(' at token {idx + 1}.", token=token))
            paren_depth += 1
            canonical_tokens.append("(")
            expect_operand = True
            continue

        if token == ")":
            if expect_operand:
                issues.append(ValidationIssue(message=f"Unexpected ')' after operator at token {idx + 1}.", token=token))
            paren_depth -= 1
            if paren_depth < 0:
                issues.append(ValidationIssue(message="Mismatched closing parenthesis ')'.", token=token))
            canonical_tokens.append(")")
            expect_operand = False
            continue

        if token in ("AND", "OR"):
            if expect_operand:
                issues.append(ValidationIssue(message=f"Unexpected operator '{token}' without preceding license.", token=token))
            canonical_tokens.append(token)
            expect_operand = True
            expect_exception = False
            continue

        if token == "WITH":
            if expect_operand or idx == 0:
                issues.append(ValidationIssue(message="Unexpected 'WITH' without preceding license identifier.", token=token))
            canonical_tokens.append("WITH")
            expect_exception = True
            expect_operand = False
            continue

        # Otherwise, token is an identifier or exception
        if expect_exception:
            # Must be an exception
            exceptions.append(token)
            expect_exception = False
            expect_operand = False

            if token not in SPDX_EXCEPTIONS:
                issues.append(
                    ValidationIssue(
                        message=f"Unknown or unapproved license exception '{token}'.",
                        token=token,
                        is_error=True,
                    )
                )
            canonical_tokens.append(token)
            continue

        if not expect_operand:
            issues.append(
                ValidationIssue(
                    message=f"Missing operator (AND / OR) between identifiers near '{token}'.",
                    token=token,
                )
            )

        # Check license identifier
        # Strip trailing '+' if present (e.g. Apache-2.0+)
        base_id = token[:-1] if token.endswith("+") else token

        if base_id in DEPRECATED_MAPPINGS:
            suggested = DEPRECATED_MAPPINGS[base_id]
            if token.endswith("+"):
                suggested = suggested.replace("-only", "-or-later")
            issues.append(
                ValidationIssue(
                    message=f"Identifier '{token}' is deprecated or non-canonical. Use '{suggested}'.",
                    token=token,
                    is_error=False,
                    suggestion=suggested,
                )
            )
            canonical_tokens.append(suggested)
            identifiers.append(suggested)
        elif base_id in SPDX_DATABASE:
            canonical_tokens.append(token)
            identifiers.append(token)
        else:
            # Case-insensitive lookup
            matched_key = next((k for k in SPDX_DATABASE if k.lower() == base_id.lower()), None)
            if matched_key:
                proper_id = matched_key + ("+" if token.endswith("+") else "")
                issues.append(
                    ValidationIssue(
                        message=f"License identifier '{token}' has incorrect casing. Standard is '{proper_id}'.",
                        token=token,
                        is_error=False,
                        suggestion=proper_id,
                    )
                )
                canonical_tokens.append(proper_id)
                identifiers.append(proper_id)
            else:
                issues.append(
                    ValidationIssue(
                        message=f"Unknown or non-standard SPDX license identifier '{token}'.",
                        token=token,
                        is_error=True,
                    )
                )
                canonical_tokens.append(token)
                identifiers.append(token)

        expect_operand = False

    if paren_depth != 0:
        issues.append(ValidationIssue(message=f"Unclosed parentheses: {paren_depth} open parenthesis remain."))

    if expect_operand:
        issues.append(ValidationIssue(message="Expression terminates prematurely with trailing operator."))

    has_errors = any(i.is_error for i in issues)
    canonical_expr = " ".join(canonical_tokens) if not has_errors else None

    return ExpressionValidationReport(
        raw_expression=expr,
        is_valid=not has_errors,
        identifiers=identifiers,
        exceptions=exceptions,
        issues=issues,
        canonical_expression=canonical_expr,
    )
