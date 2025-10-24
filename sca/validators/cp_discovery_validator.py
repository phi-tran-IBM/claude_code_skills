from ..cp_discovery import discover_cp

def validate_cp_discovery(tp) -> tuple[bool,str]:
    # Pass repo_root derived from task structure
    repo_root = str(tp.root.parent.parent)
    files = discover_cp(str(tp.root), repo_root)
    (tp.qa/"cp_list.txt").write_text("\n".join(map(str,files)))
    if not files: return False, "CP discovery: no files in CP set"
    return True, f"CP discovery ok ({len(files)} files)"
