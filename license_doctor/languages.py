# SPDX-FileCopyrightText: Copyright (c) 2026 slopggobblercobbler81
# SPDX-License-Identifier: MIT

"""Language definitions and comment styles for source file license header compliance."""

from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple


@dataclass(frozen=True)
class LanguageSpec:
    name: str
    extensions: Tuple[str, ...]
    filenames: Tuple[str, ...]
    line_comment: Optional[str] = None
    block_start: Optional[str] = None
    block_prefix: Optional[str] = None
    block_end: Optional[str] = None

    def format_header(self, lines: List[str], use_block: bool = False) -> str:
        """Format the given text lines into comment syntax for this language."""
        if use_block and self.block_start and self.block_end:
            prefix = self.block_prefix or ""
            formatted = [self.block_start]
            for line in lines:
                if line:
                    formatted.append(f"{prefix}{line}")
                else:
                    formatted.append(prefix.rstrip())
            formatted.append(self.block_end)
            return "\n".join(formatted) + "\n"
        elif self.line_comment is not None:
            formatted = []
            for line in lines:
                if line:
                    formatted.append(f"{self.line_comment} {line}")
                else:
                    formatted.append(self.line_comment)
            return "\n".join(formatted) + "\n"
        elif self.block_start and self.block_end:
            # Fall back to block comment if no line comment
            prefix = self.block_prefix or ""
            formatted = [self.block_start]
            for line in lines:
                if line:
                    formatted.append(f"{prefix}{line}")
                else:
                    formatted.append(prefix.rstrip())
            formatted.append(self.block_end)
            return "\n".join(formatted) + "\n"
        else:
            # Default hash comment
            return "\n".join(f"# {line}" if line else "#" for line in lines) + "\n"


LANGUAGES: List[LanguageSpec] = [
    # Hash-style comments
    LanguageSpec(
        name="Python",
        extensions=(".py", ".pyi", ".pyx", ".pyd"),
        filenames=(),
        line_comment="#",
    ),
    LanguageSpec(
        name="Shell",
        extensions=(".sh", ".bash", ".zsh", ".ksh"),
        filenames=(),
        line_comment="#",
    ),
    LanguageSpec(
        name="Ruby",
        extensions=(".rb", ".rake", "Gemfile"),
        filenames=("Gemfile", "Rakefile"),
        line_comment="#",
    ),
    LanguageSpec(
        name="Perl",
        extensions=(".pl", ".pm"),
        filenames=(),
        line_comment="#",
    ),
    LanguageSpec(
        name="YAML",
        extensions=(".yaml", ".yml"),
        filenames=(),
        line_comment="#",
    ),
    LanguageSpec(
        name="TOML",
        extensions=(".toml",),
        filenames=(),
        line_comment="#",
    ),
    LanguageSpec(
        name="Dockerfile",
        extensions=(".dockerfile",),
        filenames=("Dockerfile", "Containerfile"),
        line_comment="#",
    ),
    LanguageSpec(
        name="Makefile",
        extensions=(".mk",),
        filenames=("Makefile", "GNUmakefile"),
        line_comment="#",
    ),
    LanguageSpec(
        name="R",
        extensions=(".r", ".R"),
        filenames=(),
        line_comment="#",
    ),
    LanguageSpec(
        name="Julia",
        extensions=(".jl",),
        filenames=(),
        line_comment="#",
    ),

    # C / C++ / Java / JS / TS / Go / Rust family
    LanguageSpec(
        name="JavaScript",
        extensions=(".js", ".jsx", ".mjs", ".cjs"),
        filenames=(),
        line_comment="//",
        block_start="/*",
        block_prefix=" * ",
        block_end=" */",
    ),
    LanguageSpec(
        name="TypeScript",
        extensions=(".ts", ".tsx", ".mts", ".cts"),
        filenames=(),
        line_comment="//",
        block_start="/*",
        block_prefix=" * ",
        block_end=" */",
    ),
    LanguageSpec(
        name="Go",
        extensions=(".go",),
        filenames=(),
        line_comment="//",
        block_start="/*",
        block_prefix=" * ",
        block_end=" */",
    ),
    LanguageSpec(
        name="Rust",
        extensions=(".rs",),
        filenames=(),
        line_comment="//",
        block_start="/*",
        block_prefix=" * ",
        block_end=" */",
    ),
    LanguageSpec(
        name="C",
        extensions=(".c", ".h"),
        filenames=(),
        line_comment="//",
        block_start="/*",
        block_prefix=" * ",
        block_end=" */",
    ),
    LanguageSpec(
        name="C++",
        extensions=(".cpp", ".cxx", ".cc", ".hpp", ".hxx", ".hh"),
        filenames=(),
        line_comment="//",
        block_start="/*",
        block_prefix=" * ",
        block_end=" */",
    ),
    LanguageSpec(
        name="Java",
        extensions=(".java",),
        filenames=(),
        line_comment="//",
        block_start="/*",
        block_prefix=" * ",
        block_end=" */",
    ),
    LanguageSpec(
        name="Kotlin",
        extensions=(".kt", ".kts"),
        filenames=(),
        line_comment="//",
        block_start="/*",
        block_prefix=" * ",
        block_end=" */",
    ),
    LanguageSpec(
        name="Scala",
        extensions=(".scala", ".sc"),
        filenames=(),
        line_comment="//",
        block_start="/*",
        block_prefix=" * ",
        block_end=" */",
    ),
    LanguageSpec(
        name="Swift",
        extensions=(".swift",),
        filenames=(),
        line_comment="//",
        block_start="/*",
        block_prefix=" * ",
        block_end=" */",
    ),
    LanguageSpec(
        name="C#",
        extensions=(".cs",),
        filenames=(),
        line_comment="//",
        block_start="/*",
        block_prefix=" * ",
        block_end=" */",
    ),
    LanguageSpec(
        name="PHP",
        extensions=(".php",),
        filenames=(),
        line_comment="//",
        block_start="/*",
        block_prefix=" * ",
        block_end=" */",
    ),
    LanguageSpec(
        name="Dart",
        extensions=(".dart",),
        filenames=(),
        line_comment="//",
        block_start="/*",
        block_prefix=" * ",
        block_end=" */",
    ),
    LanguageSpec(
        name="Zig",
        extensions=(".zig",),
        filenames=(),
        line_comment="//",
    ),

    # CSS / Styles
    LanguageSpec(
        name="CSS",
        extensions=(".css", ".scss", ".sass", ".less"),
        filenames=(),
        block_start="/*",
        block_prefix=" * ",
        block_end=" */",
    ),

    # XML / HTML
    LanguageSpec(
        name="HTML",
        extensions=(".html", ".htm", ".xhtml", ".vue", ".svelte"),
        filenames=(),
        block_start="<!--",
        block_prefix="  ",
        block_end="-->",
    ),
    LanguageSpec(
        name="XML",
        extensions=(".xml", ".svg", ".xsd", ".xsl"),
        filenames=(),
        block_start="<!--",
        block_prefix="  ",
        block_end="-->",
    ),

    # SQL / Lua / Haskell
    LanguageSpec(
        name="SQL",
        extensions=(".sql",),
        filenames=(),
        line_comment="--",
    ),
    LanguageSpec(
        name="Lua",
        extensions=(".lua",),
        filenames=(),
        line_comment="--",
    ),
    LanguageSpec(
        name="Haskell",
        extensions=(".hs", ".lhs"),
        filenames=(),
        line_comment="--",
    ),

    # Lisp / Assembly / INI
    LanguageSpec(
        name="INI",
        extensions=(".ini", ".cfg"),
        filenames=(),
        line_comment=";",
    ),
    LanguageSpec(
        name="Lisp",
        extensions=(".lisp", ".el", ".clj"),
        filenames=(),
        line_comment=";",
    ),
]

# Lookup caches
EXTENSION_MAP: Dict[str, LanguageSpec] = {}
FILENAME_MAP: Dict[str, LanguageSpec] = {}

for spec in LANGUAGES:
    for ext in spec.extensions:
        EXTENSION_MAP[ext.lower()] = spec
    for fname in spec.filenames:
        FILENAME_MAP[fname.lower()] = spec


def get_language_spec(path: Path) -> Optional[LanguageSpec]:
    """Detect LanguageSpec for a given file path based on name or extension."""
    name_lower = path.name.lower()
    if name_lower in FILENAME_MAP:
        return FILENAME_MAP[name_lower]

    suffix = path.suffix.lower()
    if suffix in EXTENSION_MAP:
        return EXTENSION_MAP[suffix]

    # Handle multi-dot extensions like .tar.gz if needed, or dockerfile.*
    if path.name.lower().startswith("dockerfile"):
        return FILENAME_MAP.get("dockerfile")

    return None
