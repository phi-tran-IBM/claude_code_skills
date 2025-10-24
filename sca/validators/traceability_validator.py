"""
Traceability validator - ensures run tracking artifacts are present and valid.

Required by full_protocol.md §5 and §11:
- qa/run_log.txt (tee'd stdout/stderr)
- artifacts/run_context.json (run metadata)
- artifacts/run_manifest.json (QA artifact pointers)
- artifacts/run_events.jsonl (event stream)
"""

from __future__ import annotations
import json
from pathlib import Path
from typing import Tuple


REQUIRED_ARTIFACTS = [
    ("qa/run_log.txt", "text"),
    ("artifacts/run_context.json", "json"),
    ("artifacts/run_manifest.json", "json"),
    ("artifacts/run_events.jsonl", "jsonl")
]


def validate_traceability(tp) -> Tuple[bool, str]:
    """
    Validate that all required traceability artifacts exist and are valid.

    Args:
        tp: TaskPaths object

    Returns:
        (True, message) if valid, (False, error) if invalid
    """
    task_dir = tp.root.resolve()
    missing = []
    invalid = []

    for rel_path, kind in REQUIRED_ARTIFACTS:
        artifact_path = task_dir / rel_path

        # Check existence
        if not artifact_path.exists():
            missing.append(rel_path)
            continue

        # Check not empty
        if artifact_path.stat().st_size == 0:
            invalid.append(f"{rel_path} (empty)")
            continue

        # Validate JSON/JSONL structure
        if kind == "json":
            try:
                data = json.loads(artifact_path.read_text(encoding="utf-8"))
                # Validate required fields based on artifact type
                if "run_context" in rel_path:
                    if not all(k in data for k in ["run_id", "session_id", "task_id", "phase"]):
                        invalid.append(f"{rel_path} (missing required fields)")
                elif "run_manifest" in rel_path:
                    if not all(k in data for k in ["run_id", "session_id", "artifacts"]):
                        invalid.append(f"{rel_path} (missing required fields)")
            except Exception as e:
                invalid.append(f"{rel_path} (invalid JSON: {e})")

        elif kind == "jsonl":
            try:
                # Validate that each line is valid JSON
                with artifact_path.open("r", encoding="utf-8") as f:
                    for i, line in enumerate(f, 1):
                        if line.strip():  # Skip empty lines
                            json.loads(line)
            except Exception as e:
                invalid.append(f"{rel_path} (invalid JSONL at line {i}: {e})")

    # Report errors
    if missing:
        return False, f"Traceability: missing artifacts: {', '.join(missing)}"

    if invalid:
        return False, f"Traceability: invalid artifacts: {', '.join(invalid)}"

    return True, "Traceability artifacts ok"
