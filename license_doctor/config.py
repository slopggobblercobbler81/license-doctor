# SPDX-FileCopyrightText: Copyright (c) 2026 slopggobblercobbler81
# SPDX-License-Identifier: MIT

"""Configuration management for license-doctor."""

from __future__ import annotations
import datetime
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional

try:
    import tomllib  # Python 3.11+
except ImportError:
    try:
        import tomli as tomllib  # Python 3.7-3.10
    except ImportError:
        import toml as tomllib  # Fallback


DEFAULT_EXCLUDES = [
    ".git",
    ".hg",
    ".svn",
    ".idea",
    ".vscode",
    "__pycache__",
    "*.pyc",
    "node_modules",
    "vendor",
    "dist",
    "build",
    ".tox",
    ".venv",
    "venv",
    "env",
    "*.egg-info",
    "target",  # Rust
    ".mypy_cache",
    ".pytest_cache",
    "*.min.js",
    "*.min.css",
]


@dataclass
class LicenseDoctorConfig:
    license: Optional[str] = None
    owner: Optional[str] = None
    target_year: int = field(default_factory=lambda: datetime.datetime.now().year)
    exclude: List[str] = field(default_factory=lambda: list(DEFAULT_EXCLUDES))
    require_spdx: bool = True
    require_copyright: bool = True
    auto_detect_owner: bool = True

    @classmethod
    def load_from_dir(cls, directory: Path) -> LicenseDoctorConfig:
        """Load configuration from .license-doctor.toml or pyproject.toml."""
        cfg = cls()

        # Check .license-doctor.toml
        dot_conf = directory / ".license-doctor.toml"
        if dot_conf.is_file():
            try:
                with open(dot_conf, "rb") as f:
                    data = tomllib.load(f)
                return cls._from_dict(data)
            except Exception:
                pass

        # Check pyproject.toml
        pyproject = directory / "pyproject.toml"
        if pyproject.is_file():
            try:
                with open(pyproject, "rb") as f:
                    data = tomllib.load(f)
                tool_data = data.get("tool", {}).get("license-doctor", {})
                if tool_data:
                    return cls._from_dict(tool_data)
                # Fallback: extract license/authors from pyproject project section
                project_sec = data.get("project", {})
                if "license" in project_sec and not cfg.license:
                    lic = project_sec["license"]
                    if isinstance(lic, str):
                        cfg.license = lic
                    elif isinstance(lic, dict) and "text" in lic:
                        cfg.license = lic["text"]
                if "authors" in project_sec and not cfg.owner:
                    authors = project_sec["authors"]
                    if isinstance(authors, list) and len(authors) > 0 and "name" in authors[0]:
                        cfg.owner = authors[0]["name"]
            except Exception:
                pass

        return cfg

    @classmethod
    def _from_dict(cls, data: dict) -> LicenseDoctorConfig:
        cfg = cls()
        if "license" in data:
            cfg.license = str(data["license"])
        if "owner" in data:
            cfg.owner = str(data["owner"])
        if "target_year" in data:
            cfg.target_year = int(data["target_year"])
        if "exclude" in data:
            excludes = list(DEFAULT_EXCLUDES)
            for item in data["exclude"]:
                if item not in excludes:
                    excludes.append(item)
            cfg.exclude = excludes
        if "require_spdx" in data:
            cfg.require_spdx = bool(data["require_spdx"])
        if "require_copyright" in data:
            cfg.require_copyright = bool(data["require_copyright"])
        return cfg
