import os, pathlib

def canonical_path() -> pathlib.Path:
    p = os.environ.get("SCA_CANONICAL_PROTOCOL","").strip()
    return pathlib.Path(p) if p else pathlib.Path("C:/projects/Work Projects/.claude/full_protocol.md")

def exists_and_wins() -> bool:
    return canonical_path().exists()
