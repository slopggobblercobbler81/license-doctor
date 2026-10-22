"""license-doctor: Production-grade SPDX license identifier validator, header auditor, and compatibility checker."""

__version__ = "0.1.0"

from .spdx import (
    SPDX_DATABASE,
    LicenseCategory,
    LicenseMeta,
    ExpressionValidationReport,
    validate_spdx_expression,
)
from .compatibility import (
    CompatibilityReport,
    check_license_compatibility,
)
from .generator import (
    generate_license,
    list_available_templates,
)
from .auditor import (
    AuditReport,
    FileAuditResult,
    audit_file,
    audit_repository,
    inject_spdx_header,
    detect_root_license,
)

__all__ = [
    "SPDX_DATABASE",
    "LicenseCategory",
    "LicenseMeta",
    "ExpressionValidationReport",
    "validate_spdx_expression",
    "CompatibilityReport",
    "check_license_compatibility",
    "generate_license",
    "list_available_templates",
    "AuditReport",
    "FileAuditResult",
    "audit_file",
    "audit_repository",
    "inject_spdx_header",
    "detect_root_license",
    "__version__",
]
