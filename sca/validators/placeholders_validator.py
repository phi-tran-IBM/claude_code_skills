"""
Placeholder validator - blocks TODO/FIXME/PLACEHOLDER in CP code.
Required by protocol v13.8.
"""
import re
from pathlib import Path
from typing import Tuple

FORBIDDEN_TERMS = [r"\bTODO\b", r"\bFIXME\b", r"\bPLACEHOLDER\b", r"\bHARDCODED\b"]
ALLOW_MARKER = "@allow-const"

def validate_placeholders(tp) -> Tuple[bool, str]:
    """Check CP files for forbidden placeholder terms."""
    cp_list_file = tp.qa / "cp_list.txt"
    if not cp_list_file.exists():
        return True, "placeholders check skipped (no CP list)"

    cp_files = [Path(f.strip()) for f in cp_list_file.read_text().splitlines() if f.strip()]
    pattern = re.compile("|".join(FORBIDDEN_TERMS), re.IGNORECASE)

    violations = []
    for cp_file in cp_files:
        if not cp_file.exists():
            continue

        try:
            content = cp_file.read_text(encoding="utf-8", errors="ignore")
            for i, line in enumerate(content.splitlines(), 1):
                if ALLOW_MARKER in line:
                    continue
                match = pattern.search(line)
                if match:
                    violations.append(f"{cp_file}:{i} - found '{match.group()}'")
        except Exception as e:
            continue

    if violations:
        return False, f"placeholders found in CP: {'; '.join(violations[:3])}"
    return True, "no placeholders in CP"