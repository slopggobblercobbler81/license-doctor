"""Command Line Interface for license-doctor."""

from __future__ import annotations
import argparse
import json
import os
import sys
from pathlib import Path
from typing import List, Optional, Sequence

from . import __version__
from .spdx import validate_spdx_expression, SPDX_DATABASE
from .compatibility import check_license_compatibility
from .generator import generate_license, list_available_templates
from .auditor import audit_repository, inject_spdx_header, detect_root_license


def _print_colored(text: str, color: str = "") -> None:
    colors = {
        "red": "\033[91m",
        "green": "\033[92m",
        "yellow": "\033[93m",
        "blue": "\033[94m",
        "bold": "\033[1m",
        "reset": "\033[0m",
    }
    try:
        if sys.stdout.isatty():
            sys.stdout.write(f"{colors.get(color, '')}{text}{colors['reset']}\n")
        else:
            sys.stdout.write(f"{text}\n")
    except UnicodeEncodeError:
        encoding = sys.stdout.encoding or "ascii"
        fallback = text.encode(encoding, errors="replace").decode(encoding)
        sys.stdout.write(f"{fallback}\n")


def safe_relpath(path: str | Path) -> str:
    """Safely compute relative path across different drives on Windows."""
    try:
        return os.path.relpath(str(path), os.getcwd())
    except (ValueError, OSError):
        return str(path)


def cmd_validate(args: argparse.Namespace) -> int:
    """Execute 'validate' command."""
    expr = args.expression.strip()
    report = validate_spdx_expression(expr)

    if args.json:
        print(json.dumps(report.to_dict(), indent=2))
        return 0 if report.is_valid else 1

    print(f"Validating SPDX Expression: {expr}")
    if report.is_valid:
        _print_colored("[VALID] Expression is syntactically correct and standard.", "green")
        if report.canonical_expression and report.canonical_expression != expr:
            print(f"Canonical form: {report.canonical_expression}")
        if report.identifiers:
            print(f"Identifiers: {', '.join(report.identifiers)}")
        if report.warnings:
            for w in report.warnings:
                _print_colored(f"[WARN] {w.message}", "yellow")
        return 0
    else:
        _print_colored("[INVALID] License expression contains errors:", "red")
        for err in report.errors:
            _print_colored(f"  - {err.message}", "red")
            if err.suggestion:
                print(f"    Suggestion: {err.suggestion}")
        for w in report.warnings:
            _print_colored(f"  [WARN] {w.message}", "yellow")
        return 1


def cmd_audit(args: argparse.Namespace) -> int:
    """Execute 'audit' command."""
    target_dir = Path(args.path).resolve() if args.path else Path.cwd()
    if not target_dir.is_dir():
        sys.stderr.write(f"Error: Path '{target_dir}' is not a valid directory.\n")
        return 1

    expected_lic = args.license or detect_root_license(target_dir)
    report = audit_repository(target_dir, expected_license=expected_lic)

    # In-place auto-fix if requested
    fixed_count = 0
    if args.fix:
        if not expected_lic:
            sys.stderr.write("Error: Cannot auto-fix without target license. Specify --license <ID> or create root LICENSE.\n")
            return 1

        for r in report.results:
            if not r.has_spdx_header:
                p = Path(r.file_path)
                if inject_spdx_header(p, expected_lic):
                    fixed_count += 1
        # Re-audit after fixes
        report = audit_repository(target_dir, expected_license=expected_lic)

    if args.json:
        d = report.to_dict()
        d["fixed_count"] = fixed_count
        print(json.dumps(d, indent=2))
    else:
        print("==================================================")
        print("           LICENSE HEADER AUDIT REPORT            ")
        print("==================================================")
        print(f"Directory Scanned   : {safe_relpath(target_dir)}")
        print(f"Detected Project Lic: {report.root_license or 'None'}")
        print(f"Total Source Files  : {report.total_scanned}")
        print(f"Files with Headers  : {report.with_spdx_headers} ({report.coverage_percent:.1f}%)")
        print(f"Missing Headers     : {report.without_spdx_headers}")
        if fixed_count > 0:
            _print_colored(f"Auto-injected Headers: {fixed_count} files", "green")
        print("--------------------------------------------------")

        if report.license_distribution:
            print("License Distribution:")
            for lic, count in report.license_distribution.items():
                print(f"  {lic.ljust(25)} : {count:4d} files")

        missing = [r for r in report.results if not r.has_spdx_header]
        if missing:
            print("\nMissing License Headers (Sample):")
            for m in missing[:10]:
                print(f"  [MISSING] {safe_relpath(m.file_path)}")
            if len(missing) > 10:
                print(f"  ... and {len(missing) - 10} more files.")
        print("==================================================")

    if args.min_coverage is not None and report.coverage_percent < args.min_coverage:
        sys.stderr.write(
            f"\nCoverage check failed: {report.coverage_percent:.1f}% < threshold {args.min_coverage}%\n"
        )
        return 1

    return 0


def cmd_compat(args: argparse.Namespace) -> int:
    """Execute 'compat' command."""
    licenses = args.licenses
    report = check_license_compatibility(licenses)

    if args.json:
        print(json.dumps(report.to_dict(), indent=2))
        return 0 if report.is_compatible else 1

    print(f"Evaluating Compatibility: {' + '.join(licenses)}")
    if report.is_compatible:
        _print_colored("[COMPATIBLE] Licenses can be combined in a single project.", "green")
        if report.effective_license:
            print(f"Effective Project License: {report.effective_license}")
        for note in report.notes:
            print(f"  Note: {note}")
        return 0
    else:
        _print_colored("[INCOMPATIBLE] Licensing conflict detected:", "red")
        for conflict in report.conflicts:
            _print_colored(f"  - {conflict}", "red")
        return 1


def cmd_generate(args: argparse.Namespace) -> int:
    """Execute 'generate' command."""
    if args.list:
        print("Available license templates:")
        for t in list_available_templates():
            meta = SPDX_DATABASE.get(t)
            cat = f"({meta.category.value})" if meta else ""
            print(f"  - {t.ljust(15)} {cat}")
        return 0

    if not args.license:
        sys.stderr.write("Error: License identifier required. Use --list to see available templates.\n")
        return 1

    try:
        text = generate_license(license_id=args.license, holder=args.holder, year=args.year)
    except ValueError as e:
        sys.stderr.write(f"Error: {e}\n")
        return 1

    if args.out:
        out_path = Path(args.out)
        out_path.write_text(text, encoding="utf-8")
        _print_colored(f"License generated and written to {out_path}", "green")
    else:
        print(text)

    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="license-doctor",
        description="Production-grade SPDX license identifier validator, header auditor, and compatibility checker.",
    )
    parser.add_argument("--version", action="version", version=f"license-doctor {__version__}")

    subparsers = parser.add_subparsers(dest="command", help="Command to execute")

    # validate command
    p_val = subparsers.add_parser("validate", help="Validate an SPDX license identifier or compound expression")
    p_val.add_argument("expression", help="License expression (e.g. 'MIT', 'Apache-2.0 OR MIT')")
    p_val.add_argument("--json", action="store_true", help="Output validation report as JSON")

    # audit command
    p_aud = subparsers.add_parser("audit", help="Audit repository source files for license headers")
    p_aud.add_argument("path", nargs="?", default=".", help="Path to repository directory (default: .)")
    p_aud.add_argument("--license", help="Expected project license identifier")
    p_aud.add_argument("--min-coverage", type=float, help="Fail if header coverage percentage is below threshold")
    p_aud.add_argument("--fix", action="store_true", help="Auto-inject missing SPDX headers into source files")
    p_aud.add_argument("--json", action="store_true", help="Output results as JSON")

    # compat command
    p_comp = subparsers.add_parser("compat", help="Check compatibility when combining multiple licenses")
    p_comp.add_argument("licenses", nargs="+", help="License identifiers to combine (e.g. MIT Apache-2.0)")
    p_comp.add_argument("--json", action="store_true", help="Output results as JSON")

    # generate command
    p_gen = subparsers.add_parser("generate", help="Generate standard LICENSE file template")
    p_gen.add_argument("license", nargs="?", help="License identifier (e.g. MIT, Apache-2.0, BSD-3-Clause)")
    p_gen.add_argument("--holder", help="Copyright holder name or organization")
    p_gen.add_argument("--year", help="Copyright year (default: current year)")
    p_gen.add_argument("-o", "--out", help="Output file path (default: stdout)")
    p_gen.add_argument("--list", action="store_true", help="List all available license templates")

    return parser


def main(argv: Optional[List[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if not args.command or args.command == "audit":
        if not args.command:
            args = parser.parse_args(["audit"] + (argv or []))
        return cmd_audit(args)
    elif args.command == "validate":
        return cmd_validate(args)
    elif args.command == "compat":
        return cmd_compat(args)
    elif args.command == "generate":
        return cmd_generate(args)

    parser.print_help()
    return 1


if __name__ == "__main__":
    sys.exit(main())
