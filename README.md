# license-doctor 🩺

[![CI](https://github.com/slopggobblercobbler81/license-doctor/actions/workflows/ci.yml/badge.svg)](https://github.com/slopggobblercobbler81/license-doctor/actions)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](https://opensource.org/licenses/MIT)
[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![Code Style: Black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

A fast, production-grade CLI utility and audit toolkit to scan source code trees, validate SPDX 3.20+ license identifiers, detect missing license files, verify file header compliance, audit outdated copyright years, and autofix headers across multi-language projects.

---

## 🌟 Key Features

- **SPDX 3.20+ Validation**: Validates all canonical SPDX identifiers, deprecations, and custom references (`LicenseRef-*`).
- **Compound SPDX Expressions**: Parses logical license expressions with `AND`, `OR`, `WITH <exception>`, and parentheses grouping (e.g. `(MIT OR Apache-2.0) AND CC0-1.0`).
- **Multi-Language Header Support**: Automatically detects and formats headers for 25+ programming languages and file formats:
  - Hash-comments `#`: Python, Shell/Bash, Ruby, Perl, YAML, TOML, Dockerfile, Makefile, R, Julia.
  - Slashes `//` & `/* */`: JavaScript, TypeScript, Go, Rust, C, C++, Java, Kotlin, Swift, Scala, C#, PHP, Dart, Zig.
  - XML/HTML comments `<!-- -->`: HTML, XML, SVG, Vue, Svelte.
  - Dashes `--`: SQL, Lua, Haskell.
  - Semicolons `;`: INI, Lisp, Clojure.
- **Shebang & Prolog Preservation**: Safely injects headers *after* `#!/bin/sh`, Python encoding cookies (`# -*- coding: utf-8 -*-`), and XML declarations (`<?xml ... ?>`).
- **Outdated Copyright Detection**: Identifies stale copyright years (e.g. `2018-2022`) and updates them automatically to match the current target year (e.g. `2018-2026`).
- **Repository Health Auditing**: Scans root license files (`LICENSE`, `COPYING`), manifest files (`pyproject.toml`, `package.json`, `Cargo.toml`), and computes an overall compliance grade (`A+` to `F`).
- **CI/CD Ready**: First-class `--json` output and strict exit codes (`0` for success, `1` for failures) ideal for GitHub Actions and pre-commit hooks.

---

## 📦 Installation

```bash
# Install from source repository
git clone https://github.com/slopggobblercobbler81/license-doctor.git
cd license-doctor
pip install .
```

Or install in editable mode for active development:
```bash
pip install -e ".[test]"
```

---

## 🚀 Quickstart & Commands

### 1. `license-doctor check`
Audits files for license headers, valid SPDX expressions, and up-to-date copyright notices.

```bash
# Check current directory
license-doctor check

# Check specific path with strict mode (fails on warnings/stale years)
license-doctor check src/ --strict

# Enforce expected license and copyright owner
license-doctor check . --license MIT --owner "slopggobblercobbler81"

# JSON output for CI pipelines
license-doctor check . --json
```

### 2. `license-doctor fix`
Autofixes missing headers and refreshes outdated copyright year ranges across your repository.

```bash
# Autofix all files with default configuration
license-doctor fix

# Preview changes without modifying disk
license-doctor fix --dry-run

# Specify target license and copyright holder
license-doctor fix --license Apache-2.0 --owner "Acme Corp" --year 2026
```

### 3. `license-doctor scan`
Provides a holistic license health audit of your project, detecting root licenses, package manifests, and compliance statistics.

```bash
# Run repository health audit
license-doctor scan

# Export audit report to JSON
license-doctor scan --json
```

### 4. `license-doctor validate-spdx`
Validates SPDX 3.20+ license identifiers or complex boolean expressions.

```bash
# Validate simple license
license-doctor validate-spdx MIT

# Validate compound expression
license-doctor validate-spdx "(MIT OR Apache-2.0) AND CC0-1.0"

# Validate with exception
license-doctor validate-spdx "GPL-2.0-or-later WITH Classpath-exception-2.0"
```

---

## ⚙️ Configuration

`license-doctor` can be configured via a `.license-doctor.toml` file or directly inside your `pyproject.toml`.

### In `.license-doctor.toml`:
```toml
license = "MIT"
owner = "slopggobblercobbler81"
target_year = 2026
require_spdx = true
require_copyright = true
exclude = [
    "vendor/**",
    "docs/**",
    "tests/fixtures/**",
]
```

### In `pyproject.toml`:
```toml
[tool.license-doctor]
license = "MIT"
owner = "slopggobblercobbler81"
target_year = 2026
exclude = [
    "tests/fixtures",
]
```

---

## 🛡️ Pre-Commit Hook Integration

Add `license-doctor` to your `.pre-commit-config.yaml`:

```yaml
repos:
  - repo: https://github.com/slopggobblercobbler81/license-doctor
    rev: v0.1.0
    hooks:
      - id: license-doctor-check
        name: License Compliance Check
        entry: license-doctor check
        language: python
        types: [text]
```

---

## 🧪 Testing

Run the comprehensive test suite with coverage:
```bash
pytest -v --cov=license_doctor
```

---

## 📄 License

Distributed under the [MIT License](LICENSE). Copyright (c) 2026 slopggobblercobbler81.
