"""
Error code definitions and message permutations for logs_app.

Each error code maps to:
- severity: string (INFO, WARNING, ERROR, CRITICAL)
- templates: list of message templates (permutations). Templates may include Python-style
  format placeholders (e.g. "{file}", "{reason}") which will be filled from params.

Permutation selection is deterministic based on the provided params so the same inputs
produce the same permutation index.
"""

from typing import Dict, List, Optional
import hashlib

# Example error code registry. Add codes as needed.
# Keep list lengths fixed per code to ensure a fixed number of permutations.
ERROR_CODES: Dict[str, Dict[str, object]] = {
    "E001": {
        "severity": "ERROR",
        "templates": [
            "Failed to open file {file}: {reason}",
            "Could not access {file} due to {reason}",
            "File {file} could not be opened ({reason})"
        ],
    },
    "E002": {
        "severity": "WARNING",
        "templates": [
            "Configuration {key} missing, using default",
            "Missing config {key}; default applied",
        ],
    },
    "E003": {
        "severity": "CRITICAL",
        "templates": [
            "Unhandled exception in {module}: {exception}",
            "Critical failure in {module} - {exception}",
            "Module {module} crashed: {exception}"
        ],
    },
    # Add additional error codes here...
}


def format_from_error_code(error_code: str, params: Optional[Dict[str, object]] = None) -> Dict[str, str]:
    """
    Given an error_code and optional params, return a dict with:
      - severity: mapped severity
      - message: formatted message selected from permutations deterministically

    Deterministic selection:
      - If params is present, create a stable hash from the concatenated
        sorted key/value pairs to pick an index.
      - Otherwise, index 0 is used.
    """
    meta = ERROR_CODES.get(error_code)
    if not meta:
        # Fallback for unknown codes
        return {"severity": "ERROR", "message": f"Unknown error code: {error_code}"}

    severity = meta.get("severity", "ERROR")
    templates: List[str] = meta.get("templates", [])
    if not templates:
        return {"severity": severity, "message": f"{error_code}"}

    if not params:
        idx = 0
    else:
        # Build deterministic string from sorted items
        items = "|".join(f"{k}={params.get(k)}" for k in sorted(params.keys()))
        h = hashlib.md5(items.encode("utf-8")).hexdigest()
        idx = int(h, 16) % len(templates)

    template = templates[idx]
    try:
        message = template.format(**(params or {}))
    except Exception:
        # If formatting fails, fall back to a safe representation
        message = template + " " + str(params or {})
    return {"severity": severity, "message": message}