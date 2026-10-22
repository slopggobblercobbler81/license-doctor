# license-doctor 🩺

[![CI](https://github.com/slopggobblercobbler81/license-doctor/actions/workflows/ci.yml/badge.svg)](https://github.com/slopggobblercobbler81/license-doctor/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python: 3.8+](https://img.shields.io/badge/python-3.8%2B-blue)](https://www.python.org/)

Production-grade **SPDX license identifier validator**, source file header auditor, dual-license compatibility checker, and template generator for open-source repositories and CI/CD pipelines.

---

## Why license-doctor?

Open source compliance and license hygiene are essential for enterprise software, package registries, and supply chain security:
- **Non-standard identifiers**: Using `GPL-3.0` or `Apache2.0` instead of canonical SPDX IDs (`GPL-3.0-only`, `Apache-2.0`) breaks automated SBOM tools.
- **Missing file headers**: Source code files distributed without `SPDX-License-Identifier` headers leave ambiguous copyright status when copied or reused.
- **Licensing conflicts**: Combining incompatible licenses (such as `Apache-2.0` and `GPL-2.0-only`) creates legal liabilities that cannot be resolved without code removal.
- **Inconsistent multi-licensing**: Mismatched file-level licenses contradicting the repository's root `LICENSE`.

`license-doctor` validates, audits, enforces, and auto-fixes licensing across any codebase with zero external dependencies.

---

## Features

- **🔍 SPDX Expression Validator (`validate`)**:
  - Full syntax and semantic parser for compound expressions (`AND`, `OR`, `WITH`, parentheses).
  - Validates identifiers and exceptions against the official SPDX database.
  - Suggests canonical replacements for deprecated or colloquial IDs (`GPL-3.0` -> `GPL-3.0-only`).
  - Normalizes case inconsistencies (`mit` -> `MIT`).

- **🛡️ Source Header Auditor (`audit`)**:
  - Scans Python, JavaScript, TypeScript, Go, Rust, C/C++, Java, Swift, Kotlin, and shell scripts.
  - Detects `SPDX-License-Identifier` headers and copyright notices.
  - Flags files with inconsistent licenses differing from the root `LICENSE`.
  - Enforces minimum coverage thresholds (`--min-coverage 95.0`) in CI.
  - Auto-injects missing headers using language-aware comment prefixes with `--fix`.

- **⚖️ License Compatibility Checker (`compat`)**:
  - Evaluates combinations of Permissive, Weak Copyleft, Strong Copyleft, and Network Copyleft licenses.
  - Flags known legal conflicts (e.g. Apache-2.0 with GPL-2.0-only, GPL-2.0-only with GPL-3.0).
  - Determines the effective governing license for the combined work.

- **📄 Template Generator (`generate`)**:
  - Generates legally accurate open-source license templates (MIT, Apache-2.0, BSD-2-Clause, BSD-3-Clause, ISC, Unlicense).
  - Automatically interpolates current year and copyright holder.

---

## Installation

Install via pip:

```bash
pip install license-doctor
```

Or install from source:

```bash
git clone https://github.com/slopggobblercobbler81/license-doctor.git
cd license-doctor
pip install -e .
```

---

## CLI Usage

### 1. Validate SPDX License Expressions

Validate simple or complex license expressions:

```bash
# Single identifier
license-doctor validate "MIT"

# Compound expression with exception
license-doctor validate "(MIT OR Apache-2.0) AND GPL-3.0-or-later WITH Classpath-exception-2.0"

# Output validation report as JSON
license-doctor validate "Apache-2.0" --json
```

### 2. Audit Codebase for License Headers

Scan source files for compliance:

```bash
# Scan current repository
license-doctor audit

# Enforce minimum 90% header coverage in CI
license-doctor audit --min-coverage 90.0

# Automatically inject missing SPDX headers across all files
license-doctor audit --fix --license MIT

# Output audit report as JSON
license-doctor audit --json
```

### 3. Check Multi-License Compatibility

Evaluate compatibility when combining multiple dependencies or components:

```bash
# Compatible permissive combination
license-doctor compat MIT Apache-2.0

# Copyleft combination
license-doctor compat MIT GPL-3.0-only

# Detect licensing conflicts
license-doctor compat Apache-2.0 GPL-2.0-only
```

### 4. Generate Standard LICENSE Files

Generate official open-source license files:

```bash
# List available templates
license-doctor generate --list

# Write MIT license to LICENSE file
license-doctor generate MIT --holder "Your Organization" --out LICENSE

# Output Apache-2.0 to stdout
license-doctor generate Apache-2.0 --holder "Jane Doe"
```

---

## GitHub Actions CI Integration

Integrate `license-doctor` into your pull request workflows:

```yaml
name: License Compliance Audit

on:
  pull_request:
    branches: [main]
  push:
    branches: [main]

jobs:
  license-audit:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: "3.12"

      - name: Install license-doctor
        run: pip install license-doctor

      - name: Audit License Headers
        run: license-doctor audit . --min-coverage 85.0
```

---

## Python API Usage

Use `license-doctor` programmatically:

```python
from license_doctor import (
    validate_spdx_expression,
    check_license_compatibility,
    generate_license,
    audit_repository,
)

# Validate expression
report = validate_spdx_expression("MIT OR Apache-2.0")
print(f"Valid: {report.is_valid}, Identifiers: {report.identifiers}")

# Check compatibility
compat = check_license_compatibility(["MIT", "Apache-2.0"])
print(f"Compatible: {compat.is_compatible}, Effective: {compat.effective_license}")

# Generate template
license_text = generate_license("MIT", holder="Acme Corp", year=2026)
```

---

## Development & Testing

Run the test suite with `pytest`:

```bash
pip install -e ".[dev]"
pytest -v --cov=license_doctor
```

---

## License

This project is licensed under the [MIT License](LICENSE).
