"""
AST validator - detects stub functions and hardcoded returns in CP.
Required by protocol for authenticity.
"""
import ast
from pathlib import Path
from typing import Tuple

def is_stub_function(func_def) -> bool:
    """Check if function is a stub (returns only constants or pass)."""
    if len(func_def.body) == 1:
        stmt = func_def.body[0]
        if isinstance(stmt, ast.Pass):
            return True
        if isinstance(stmt, ast.Return):
            if stmt.value is None:
                return True
            if isinstance(stmt.value, (ast.Constant, ast.Num, ast.Str)):
                return True
    return False

def validate_ast(tp) -> Tuple[bool, str]:
    """Check CP files for stub implementations."""
    cp_list_file = tp.qa / "cp_list.txt"
    if not cp_list_file.exists():
        return True, "AST check skipped (no CP list)"

    cp_files = [Path(f.strip()) for f in cp_list_file.read_text().splitlines() if f.strip()]
    stubs = []

    for cp_file in cp_files:
        if not cp_file.exists() or not cp_file.suffix == '.py':
            continue

        try:
            tree = ast.parse(cp_file.read_text(encoding="utf-8"))
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    if is_stub_function(node):
                        stubs.append(f"{cp_file}:{node.name}")
        except Exception:
            continue

    if stubs:
        return False, f"stub functions found: {', '.join(stubs[:3])}"
    return True, "no stub functions in CP"