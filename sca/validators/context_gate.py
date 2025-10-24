import json
from pathlib import Path

REQ = [
    "hypothesis.md",
    "design.md",
    "evidence.json",
    "data_sources.json",
    "adr.md",
    "assumptions.md",
]


def validate_context_gate(tp) -> tuple[bool, str]:
    ctx: Path = tp.context
    missing = [
        n
        for n in REQ
        if not (ctx / n).exists() or not (ctx / n).read_text(encoding="utf-8").strip()
    ]
    if missing:
        return False, f"ContextGate: missing/empty: {', '.join(missing)}"
    try:
        E = json.loads((ctx / "evidence.json").read_text(encoding="utf-8"))
        sources = E.get("sources", E) if isinstance(E, dict) else E
        if isinstance(sources, dict):
            sources = sources.get("sources", [])

        # Require at least 3 high-priority sources
        p1 = sum(1 for e in sources if e.get("priority") == "P1" or e.get("source_type") == "P1")
        if p1 < 3:
            return False, "ContextGate: evidence.json needs >= 3 P1 sources"

        for i, e in enumerate(sources, 1):
            sf = e.get("synthesis", "") or e.get("synthesized_finding", "")
            if not sf or len(sf.split()) > 50:
                return False, f"ContextGate: E[{i}] synthesis missing/too long (max 50 words)"
            url_doi = e.get("url") or e.get("doi") or e.get("url_or_doi")
            ret_date = e.get("retrieved_date") or e.get("retrieval_date")
            if not url_doi or not ret_date:
                return False, f"ContextGate: E[{i}] missing url/doi or retrieval_date"
    except Exception as ex:
        return False, f"ContextGate: invalid evidence.json ({ex})"
    return True, "ContextGate ok"

