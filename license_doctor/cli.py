# SPDX-FileCopyrightText: Copyright (c) 2026 slopggobblercobbler81
# SPDX-License-Identifier: MIT

"""Command-line interface for license-doctor."""

from __future__ import annotations
import json
import sys
from pathlib import Path
from typing import Optional

import click
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from license_doctor import __version__
from license_doctor.config import LicenseDoctorConfig
from license_doctor.models import Severity
from license_doctor.project_scanner import Scanner
from license_doctor.spdx_validator import validate_spdx_expression

console = Console()
err_console = Console(stderr=True)


@click.group()
@click.version_option(__version__, prog_name="license-doctor")
def cli():
    """license-doctor: Production-grade CLI utility to scan, validate, and autofix software licenses."""
    pass


@cli.command()
@click.argument("path", default=".", type=click.Path(exists=True, file_okay=False, dir_okay=True))
@click.option("--license", "-l", "expected_license", help="Expected SPDX license identifier (e.g. MIT, Apache-2.0).")
@click.option("--owner", "-o", help="Expected copyright owner / author.")
@click.option("--year", "-y", type=int, help="Target copyright year (defaults to current year).")
@click.option("--strict", is_flag=True, help="Treat warnings as errors.")
@click.option("--json", "json_output", is_flag=True, help="Output results in JSON format.")
def check(
    path: str,
    expected_license: Optional[str],
    owner: Optional[str],
    year: Optional[int],
    strict: bool,
    json_output: bool,
):
    """Check repository license compliance, header validity, and copyright years."""
    root_dir = Path(path).resolve()
    config = LicenseDoctorConfig.load_from_dir(root_dir)
    if expected_license:
        config.license = expected_license
    if owner:
        config.owner = owner
    if year:
        config.target_year = year

    scanner = Scanner(root_dir, config)
    report = scanner.scan(expected_license=config.license)

    if json_output:
        click.echo(json.dumps(report.to_dict(), indent=2))
        has_fail = report.has_errors or (strict and report.outdated_year_files > 0)
        sys.exit(1 if has_fail else 0)

    # Rich human-readable output
    console.print(Panel.fit(
        f"[bold cyan]license-doctor[/bold cyan] v{__version__} — Compliance Check\n"
        f"[dim]Scanning:[/dim] {root_dir}",
        border_style="cyan"
    ))

    # Root License Status
    if report.root_license_found:
        lic_desc = f"[green]Found[/green] ({report.root_license_file})"
        if report.root_license_detected:
            lic_desc += f" -> [cyan]{report.root_license_detected}[/cyan]"
        console.print(f" Root License: {lic_desc}")
    else:
        console.print(" Root License: [bold red]MISSING[/bold red] (No LICENSE or COPYING file found)")

    # Manifest Licenses
    if report.manifest_licenses:
        for man_file, man_lic in report.manifest_licenses.items():
            console.print(f" Manifest ({man_file}): [magenta]{man_lic}[/magenta]")

    # File Issues Table
    total_issues = 0
    issues_table = Table(title="File License Issues", expand=True, show_lines=False)
    issues_table.add_column("File", style="dim", no_wrap=False)
    issues_table.add_column("Rule", style="cyan")
    issues_table.add_column("Severity", justify="center")
    issues_table.add_column("Details", style="white")

    for f in report.file_reports:
        for issue in f.issues:
            total_issues += 1
            sev_badge = (
                "[bold red]ERROR[/bold red]"
                if issue.severity == Severity.ERROR
                else "[bold yellow]WARN[/bold yellow]"
            )
            issues_table.add_row(f.file_path, issue.rule_id, sev_badge, issue.message)

    for p_issue in report.project_issues:
        total_issues += 1
        issues_table.add_row("<project root>", p_issue.rule_id, "[bold red]ERROR[/bold red]", p_issue.message)

    if total_issues > 0:
        console.print()
        console.print(issues_table)

    console.print()
    # Summary
    rate_color = "green" if report.compliance_rate >= 90 else ("yellow" if report.compliance_rate >= 70 else "red")
    console.print(
        f"Summary: [bold]{report.compliant_files}/{report.total_files}[/bold] source files compliant "
        f"([{rate_color}]{report.compliance_rate}%[/{rate_color}]) | "
        f"Missing headers: [red]{report.missing_header_files}[/red] | "
        f"Outdated years: [yellow]{report.outdated_year_files}[/yellow] | "
        f"Grade: [bold {rate_color}]{report.grade}[/bold {rate_color}]"
    )

    has_fail = report.has_errors or (strict and report.outdated_year_files > 0)
    if has_fail:
        console.print("\n[bold red][X] License compliance check failed.[/bold red] Run [bold green]license-doctor fix[/bold green] to autofix missing headers.")
        sys.exit(1)
    else:
        console.print("\n[bold green][OK] All checked files are compliant![/bold green]")
        sys.exit(0)


@cli.command()
@click.argument("path", default=".", type=click.Path(exists=True, file_okay=False, dir_okay=True))
@click.option("--license", "-l", "license_id", help="SPDX license identifier to inject (e.g. MIT, Apache-2.0).")
@click.option("--owner", "-o", help="Copyright owner / author to inject.")
@click.option("--year", "-y", type=int, help="Target copyright year (defaults to current year).")
@click.option("--dry-run", is_flag=True, help="Preview changes without writing to disk.")
@click.option("--no-update-years", is_flag=True, help="Do not update outdated copyright years.")
def fix(
    path: str,
    license_id: Optional[str],
    owner: Optional[str],
    year: Optional[int],
    dry_run: bool,
    no_update_years: bool,
):
    """Autofix missing license headers and update outdated copyright years."""
    root_dir = Path(path).resolve()
    config = LicenseDoctorConfig.load_from_dir(root_dir)
    if license_id:
        config.license = license_id
    if owner:
        config.owner = owner
    if year:
        config.target_year = year

    scanner = Scanner(root_dir, config)
    chosen_lic = config.license or "MIT"
    chosen_owner = config.owner

    console.print(Panel.fit(
        f"[bold cyan]license-doctor[/bold cyan] v{__version__} — Autofix Mode\n"
        f"[dim]Directory:[/dim] {root_dir}\n"
        f"[dim]License:[/dim] [green]{chosen_lic}[/green] | [dim]Owner:[/dim] {chosen_owner or '<none>'}",
        border_style="cyan"
    ))

    fixed_files, year_updated = scanner.fix(
        license_id=chosen_lic,
        owner=chosen_owner,
        year=config.target_year,
        update_years=not no_update_years,
        dry_run=dry_run,
    )

    if fixed_files:
        console.print(f"\n[bold green]{'[DRY RUN] Would inject' if dry_run else 'Injected'} headers in {len(fixed_files)} files:[/bold green]")
        for f in fixed_files:
            console.print(f"  + {f}")

    if year_updated:
        console.print(f"\n[bold yellow]{'[DRY RUN] Would update' if dry_run else 'Updated'} copyright years in {len(year_updated)} files:[/bold yellow]")
        for f in year_updated:
            console.print(f"  ~ {f}")

    if not fixed_files and not year_updated:
        console.print("\n[bold green][OK] No fixes needed; files are already up to date![/bold green]")
    else:
        action = "Preview completed." if dry_run else "Autofix completed successfully."
        console.print(f"\n[bold cyan][OK] {action}[/bold cyan]")


@cli.command()
@click.argument("path", default=".", type=click.Path(exists=True, file_okay=False, dir_okay=True))
@click.option("--json", "json_output", is_flag=True, help="Output results in JSON format.")
def scan(path: str, json_output: bool):
    """Generate comprehensive license health audit report for repository."""
    root_dir = Path(path).resolve()
    config = LicenseDoctorConfig.load_from_dir(root_dir)
    scanner = Scanner(root_dir, config)
    report = scanner.scan()

    if json_output:
        click.echo(json.dumps(report.to_dict(), indent=2))
        return

    console.print(Panel.fit(
        f"[bold cyan]license-doctor[/bold cyan] v{__version__} — Repository License Health Audit\n"
        f"[dim]Target:[/dim] {root_dir}",
        border_style="cyan"
    ))

    # Health metrics overview
    overview_table = Table(show_header=False, box=None)
    overview_table.add_column("Property", style="bold cyan")
    overview_table.add_column("Value")

    root_val = (
        f"[green]Present[/green] ({report.root_license_file}) - [bold]{report.root_license_detected or 'Custom'}[/bold]"
        if report.root_license_found
        else "[red]Missing[/red]"
    )
    overview_table.add_row("Root License File", root_val)

    if report.manifest_licenses:
        man_strs = [f"{k}: [magenta]{v}[/magenta]" for k, v in report.manifest_licenses.items()]
        overview_table.add_row("Package Manifests", ", ".join(man_strs))

    overview_table.add_row("Total Source Files", str(report.total_files))
    overview_table.add_row("Header Compliant Files", f"[green]{report.compliant_files}[/green]")
    overview_table.add_row("Missing Headers", f"[red]{report.missing_header_files}[/red]")
    overview_table.add_row("Outdated Copyrights", f"[yellow]{report.outdated_year_files}[/yellow]")
    overview_table.add_row("SPDX Licenses Detected", ", ".join(sorted(report.detected_licenses)) or "None")

    rate_color = "green" if report.compliance_rate >= 90 else ("yellow" if report.compliance_rate >= 70 else "red")
    overview_table.add_row("Compliance Rate", f"[{rate_color}]{report.compliance_rate}%[/{rate_color}]")
    overview_table.add_row("Health Grade", f"[bold {rate_color}]{report.grade}[/bold {rate_color}]")

    console.print(overview_table)


@cli.command("validate-spdx")
@click.argument("expression")
@click.option("--json", "json_output", is_flag=True, help="Output validation in JSON format.")
def validate_spdx_cmd(expression: str, json_output: bool):
    """Validate an SPDX 3.20+ license expression string."""
    res = validate_spdx_expression(expression)

    if json_output:
        click.echo(json.dumps(res.to_dict(), indent=2))
        sys.exit(0 if res.is_valid else 1)

    if res.is_valid:
        console.print(f"[bold green][OK] Valid SPDX Expression:[/bold green] [cyan]{res.normalized_expression}[/cyan]")
        if res.warnings:
            for w in res.warnings:
                console.print(f"  [yellow]Notice:[/yellow] {w}")
        if res.detected_licenses:
            console.print(f"  [dim]Licenses:[/dim] {', '.join(sorted(res.detected_licenses))}")
        if res.detected_exceptions:
            console.print(f"  [dim]Exceptions:[/dim] {', '.join(sorted(res.detected_exceptions))}")
        sys.exit(0)
    else:
        console.print(f"[bold red][X] Invalid SPDX Expression:[/bold red] '{expression}'")
        for err in res.errors:
            console.print(f"  [red]Error:[/red] {err}")
        sys.exit(1)


def main():
    cli()


if __name__ == "__main__":
    main()
