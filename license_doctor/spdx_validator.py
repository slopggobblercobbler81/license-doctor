# SPDX-FileCopyrightText: Copyright (c) 2026 slopggobblercobbler81
# SPDX-License-Identifier: MIT

"""SPDX 3.20+ Expression Parser and Validator."""

from __future__ import annotations
import difflib
import re
from typing import List, Optional, Set, Tuple

from license_doctor.spdx_data import (
    SPDX_LICENSES,
    SPDX_EXCEPTIONS,
    LOWER_SPDX_LICENSES,
    LOWER_SPDX_EXCEPTIONS,
    LOWER_DEPRECATED,
)


class SPDXValidationError(Exception):
    """Raised when an SPDX expression fails validation."""
    pass


class SPDXValidationResult:
    """Result of SPDX validation."""

    def __init__(
        self,
        is_valid: bool,
        expression: str,
        normalized_expression: str = "",
        errors: Optional[List[str]] = None,
        warnings: Optional[List[str]] = None,
        detected_licenses: Optional[Set[str]] = None,
        detected_exceptions: Optional[Set[str]] = None,
    ):
        self.is_valid = is_valid
        self.expression = expression
        self.normalized_expression = normalized_expression or expression
        self.errors = errors or []
        self.warnings = warnings or []
        self.detected_licenses = detected_licenses or set()
        self.detected_exceptions = detected_exceptions or set()

    def to_dict(self) -> dict:
        return {
            "is_valid": self.is_valid,
            "expression": self.expression,
            "normalized_expression": self.normalized_expression,
            "errors": self.errors,
            "warnings": self.warnings,
            "detected_licenses": sorted(list(self.detected_licenses)),
            "detected_exceptions": sorted(list(self.detected_exceptions)),
        }


def suggest_spdx_id(identifier: str) -> List[str]:
    """Suggest close SPDX license matches for a given identifier."""
    # Strip plus if present
    base_id = identifier[:-1] if identifier.endswith("+") else identifier
    all_known = list(SPDX_LICENSES) + list(LOWER_DEPRECATED.keys())
    matches = difflib.get_close_matches(base_id, all_known, n=3, cutoff=0.6)
    return matches


def validate_license_id(lic_id: str) -> Tuple[bool, str, Optional[str], Optional[str]]:
    """
    Validate a single license identifier.
    Returns: (is_valid, canonical_name, warning_msg, error_msg)
    """
    cleaned = lic_id.strip()
    if not cleaned:
        return False, cleaned, None, "Empty license identifier"

    lower_cleaned = cleaned.lower()
    # Check deprecated identifier on full string first (e.g. GPL-3.0+)
    if lower_cleaned in LOWER_DEPRECATED:
        orig, replacement = LOWER_DEPRECATED[lower_cleaned]
        return (
            True,
            replacement,
            f"SPDX identifier '{orig}' is deprecated. Recommended replacement: '{replacement}'",
            None,
        )

    has_plus = cleaned.endswith("+")
    base = cleaned[:-1] if has_plus else cleaned

    # Check Custom LicenseRef
    if base.startswith("LicenseRef-") or ":LicenseRef-" in base:
        # Custom license reference valid per SPDX spec
        ref_part = base.split("LicenseRef-")[-1]
        if re.match(r"^[a-zA-Z0-9\.\-]+$", ref_part):
            return True, cleaned, None, None
        return False, cleaned, None, f"Invalid LicenseRef identifier format: '{cleaned}'"

    # Exact match in canonical set
    if base in SPDX_LICENSES:
        return True, cleaned, None, None

    # Check case-insensitive canonical match
    lower_base = base.lower()
    if lower_base in LOWER_SPDX_LICENSES:
        canonical = LOWER_SPDX_LICENSES[lower_base] + ("+" if has_plus else "")
        return True, canonical, f"Case mismatch: '{cleaned}' normalized to '{canonical}'", None

    # Check deprecated identifier on base
    if lower_base in LOWER_DEPRECATED:
        orig, replacement = LOWER_DEPRECATED[lower_base]
        # If it had a +, suggest the or-later variant
        if has_plus and not replacement.endswith("-or-later"):
            replacement = replacement.replace("-only", "-or-later")
        return (
            True,
            replacement,
            f"SPDX identifier '{orig}' is deprecated. Recommended replacement: '{replacement}'",
            None,
        )

    # Not found - build helpful error with suggestions
    suggestions = suggest_spdx_id(base)
    msg = f"Unknown SPDX license identifier: '{cleaned}'"
    if suggestions:
        msg += f". Did you mean: {', '.join(suggestions)}?"
    return False, cleaned, None, msg


def validate_exception_id(exc_id: str) -> Tuple[bool, str, Optional[str], Optional[str]]:
    """
    Validate an SPDX license exception identifier.
    Returns: (is_valid, canonical_name, warning_msg, error_msg)
    """
    cleaned = exc_id.strip()
    if not cleaned:
        return False, cleaned, None, "Empty license exception identifier"

    if cleaned in SPDX_EXCEPTIONS:
        return True, cleaned, None, None

    lower = cleaned.lower()
    if lower in LOWER_SPDX_EXCEPTIONS:
        canonical = LOWER_SPDX_EXCEPTIONS[lower]
        return True, canonical, f"Case mismatch in exception: '{cleaned}' normalized to '{canonical}'", None

    suggestions = difflib.get_close_matches(cleaned, list(SPDX_EXCEPTIONS), n=2, cutoff=0.6)
    msg = f"Unknown SPDX license exception: '{cleaned}'"
    if suggestions:
        msg += f". Did you mean: {', '.join(suggestions)}?"
    return False, cleaned, None, msg


class _Tokenizer:
    """Tokenize SPDX expressions into tokens: identifiers, operators, parentheses."""

    def __init__(self, text: str):
        self.text = text
        self.tokens: List[str] = []
        self._tokenize()

    def _tokenize(self):
        # We want to tokenize: '(', ')', and whitespace-separated terms.
        # Also preserve LicenseRef tokens.
        raw = self.text
        # Insert spaces around parentheses
        spaced = raw.replace("(", " ( ").replace(")", " ) ")
        self.tokens = [t for t in spaced.split() if t]


class SPDXParser:
    """Recursive descent parser for SPDX 3.20+ expressions."""

    def __init__(self, expression: str):
        self.original_expression = expression.strip()
        self.tokens = _Tokenizer(self.original_expression).tokens
        self.pos = 0
        self.errors: List[str] = []
        self.warnings: List[str] = []
        self.licenses: Set[str] = set()
        self.exceptions: Set[str] = set()

    def peek(self) -> Optional[str]:
        if self.pos < len(self.tokens):
            return self.tokens[self.pos]
        return None

    def consume(self) -> str:
        tok = self.tokens[self.pos]
        self.pos += 1
        return tok

    def parse(self) -> SPDXValidationResult:
        if not self.tokens:
            return SPDXValidationResult(
                is_valid=False,
                expression=self.original_expression,
                errors=["Empty SPDX expression"],
            )

        try:
            normalized = self._parse_or_expr()
            if self.pos < len(self.tokens):
                unexpected = self.tokens[self.pos]
                self.errors.append(f"Unexpected token after expression: '{unexpected}'")
                return SPDXValidationResult(
                    is_valid=False,
                    expression=self.original_expression,
                    errors=self.errors,
                    warnings=self.warnings,
                )

            is_valid = len(self.errors) == 0
            return SPDXValidationResult(
                is_valid=is_valid,
                expression=self.original_expression,
                normalized_expression=normalized,
                errors=self.errors,
                warnings=self.warnings,
                detected_licenses=self.licenses,
                detected_exceptions=self.exceptions,
            )
        except SPDXValidationError as exc:
            self.errors.append(str(exc))
            return SPDXValidationResult(
                is_valid=False,
                expression=self.original_expression,
                errors=self.errors,
                warnings=self.warnings,
                detected_licenses=self.licenses,
                detected_exceptions=self.exceptions,
            )

    def _parse_or_expr(self) -> str:
        left = self._parse_and_expr()
        while self.peek() and self.peek().upper() == "OR":
            op_tok = self.consume()
            if op_tok != "OR":
                self.warnings.append(f"Operator '{op_tok}' normalized to 'OR'")
            if self.peek() is None or self.peek().upper() in ("OR", "AND", "WITH") or self.peek() == ")":
                raise SPDXValidationError("Expected expression after 'OR'")
            right = self._parse_and_expr()
            left = f"{left} OR {right}"
        return left

    def _parse_and_expr(self) -> str:
        left = self._parse_with_expr()
        while self.peek() and self.peek().upper() == "AND":
            op_tok = self.consume()
            if op_tok != "AND":
                self.warnings.append(f"Operator '{op_tok}' normalized to 'AND'")
            if self.peek() is None or self.peek().upper() in ("OR", "AND", "WITH") or self.peek() == ")":
                raise SPDXValidationError("Expected expression after 'AND'")
            right = self._parse_with_expr()
            left = f"{left} AND {right}"
        return left

    def _parse_with_expr(self) -> str:
        left = self._parse_primary()
        if self.peek() and self.peek().upper() == "WITH":
            op_tok = self.consume()
            if op_tok != "WITH":
                self.warnings.append(f"Operator '{op_tok}' normalized to 'WITH'")
            exc_token = self.peek()
            if exc_token is None or exc_token.upper() in ("OR", "AND", "WITH") or exc_token in ("(", ")"):
                raise SPDXValidationError("Expected exception identifier after 'WITH'")
            exc_token = self.consume()
            is_valid, canon_exc, warn, err = validate_exception_id(exc_token)
            if warn:
                self.warnings.append(warn)
            if err:
                self.errors.append(err)
            self.exceptions.add(canon_exc)
            return f"{left} WITH {canon_exc}"
        return left

    def _parse_primary(self) -> str:
        token = self.peek()
        if token is None:
            raise SPDXValidationError("Unexpected end of expression")

        if token == "(":
            self.consume()  # '('
            expr = self._parse_or_expr()
            if self.peek() != ")":
                raise SPDXValidationError("Missing closing parenthesis ')'")
            self.consume()  # ')'
            return f"({expr})"

        if token.upper() in ("OR", "AND", "WITH") or token == ")":
            raise SPDXValidationError(f"Unexpected operator or delimiter: '{token}'")

        # It is a license identifier
        lic_token = self.consume()
        is_valid, canon_lic, warn, err = validate_license_id(lic_token)
        if warn:
            self.warnings.append(warn)
        if err:
            self.errors.append(err)
        self.licenses.add(canon_lic)
        return canon_lic


def validate_spdx_expression(expr: str) -> SPDXValidationResult:
    """Parse and validate an SPDX expression."""
    parser = SPDXParser(expr)
    return parser.parse()
