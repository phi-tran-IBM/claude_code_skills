# SCA Protocol Skill - Setup & Usage Guide

## Overview

This skill implements the Scientific Coding Agent protocol with **zero environment variables** required. Task discovery is automatic via `.sca/profile.json` at your repository root.

**Key Features:**
- ✅ Auto task discovery (no manual env vars)
- ✅ SAFE/DRY mode enforcement
- ✅ Task-scoped CP discovery
- ✅ Strict gate enforcement (≥95% CP coverage, TDD Guard, etc.)
- ✅ Enhanced snapshot management

---

## Installation

### 1. Install Python Dependencies (Once)

From your project root:

```powershell
python -m pip install -U pytest pytest-cov mypy lizard ruff interrogate bandit detect-secrets pip-audit hypothesis
```

### 2. Verify Skill Location

Ensure this skill is located at:
```
C:\projects\Work Projects\sca-protocol-skill\
```

### 3. Verify Canonical Protocol

Ensure the protocol exists at:
```
C:\projects\Work Projects\.claude\full_protocol.md
```

---

## Quick Start (Zero Environment Variables)

### Create a New Task

From your **project root** (not the skill folder):

```powershell
pwsh -NoProfile -File "C:\projects\Work Projects\sca-protocol-skill\commands\new-task.ps1" `
  -TaskId 011 `
  -TaskSlug "risk-modeling-poc" `
  -Auto 2 `
  -Safe on `
  -Dry off
```

This creates:
- `tasks/011-risk-modeling-poc/` with subdirectories: `context/`, `artifacts/`, `qa/`, `reports/`
- `.sca/profile.json` at repo root (tracks current task + defaults)
- Copies context templates from the skill

### Switch to an Existing Task

```powershell
pwsh -NoProfile -File "C:\projects\Work Projects\sca-protocol-skill\commands\use-task.ps1" `
  -TaskId 010 `
  -TaskSlug "code-analysis-optimization-debugging"
```

### Check Current Task

```powershell
pwsh -NoProfile -File "C:\projects\Work Projects\sca-protocol-skill\commands\get-task.ps1"
```

Returns JSON:
```json
{
  "TASK_DIR": "C:\\projects\\Work Projects\\astra-graphrag\\tasks\\011-risk-modeling-poc",
  "AUTO": "2",
  "SAFE_MODE": "on",
  "DRY_RUN": "off"
}
```

---

## Running the Skill

All commands auto-discover the current task from `.sca/profile.json`.

### Validate All Gates (Safe Smoke Test)

```powershell
pwsh -NoProfile -File "C:\projects\Work Projects\sca-protocol-skill\commands\validate-only.ps1"
```

### Run Full Auto Progression

Runs context → P1 → P2 → P3 → P4 → P5 (based on AUTO level):

```powershell
pwsh -NoProfile -File "C:\projects\Work Projects\sca-protocol-skill\commands\run-phase.ps1" -Phase auto
```

### Run Specific Phase

```powershell
# Just context gate
pwsh -NoProfile -File "C:\projects\Work Projects\sca-protocol-skill\commands\run-phase.ps1" -Phase context

# Phase 3 (TDD + CP)
pwsh -NoProfile -File "C:\projects\Work Projects\sca-protocol-skill\commands\run-phase.ps1" -Phase 3
```

### Force Snapshot Save

```powershell
pwsh -NoProfile -File "C:\projects\Work Projects\sca-protocol-skill\commands\snapshot-save.ps1"
```

### Override Defaults (Optional)

```powershell
pwsh -NoProfile -File "C:\projects\Work Projects\sca-protocol-skill\commands\run-phase.ps1" `
  -Phase auto `
  -AUTO 3 `
  -SAFE_MODE off `
  -DRY_RUN on
```

---

## Required Context Files

Before running validation, fill these files in `tasks/<ID>-<slug>/context/`:

### 1. `hypothesis.md`
Define capability, metrics, thresholds, baselines.

### 2. `design.md`
Data strategy, verification strategy, domain-specific validation method.

### 3. `evidence.json`
≥3 P1 sources with:
- `synthesized_finding` (≤50 words)
- `url_or_doi`
- `retrieval_date` (YYYY-MM-DD)

### 4. `data_sources.json`
Input datasets with SHA256 hashes, PII flags.

### 5. `adr.md`
Architectural Decision Records.

### 6. `assumptions.md`
Domain/data/algorithm/resource assumptions.

### 7. `cp_paths.json`
Critical Path file patterns:
```json
["src/core/**/*.py"]
```

---

## Gate Enforcement

### Context Gate
- Validates all required context files exist and are complete
- Checks ≥3 P1 sources in `evidence.json`
- Validates synthesis ≤50 words, DOI/URL + retrieval date present

### CP Discovery
- Discovers Critical Path files from `context/cp_paths.json`
- Writes list to `qa/cp_list.txt`

### TDD Guard (Hard Gate)
- Each CP file must have tests referencing it
- Tests must include `@pytest.mark.cp`
- At least one `@given(...)` Hypothesis property test required
- Tests must be **newer** than implementation (TDD)

### Coverage (≥95% CP Line & Branch)
- Parses `qa/coverage.xml`
- Filters to CP files only
- Fails if line coverage < 95% or branch coverage < 95%

### Mypy Strict
- Applies `--strict` to CP directories
- Standard mypy to non-CP `src/`

### Complexity
- `lizard`: CCN ≤10, cognitive ≤15
- `interrogate`: docstring coverage ≥95%

### Security
- `detect-secrets --json`: zero secrets
- `bandit -ll`: zero findings
- `pip-audit`: zero vulnerabilities

### Memory Sync
- Validates `artifacts/state.json` and `artifacts/memory_sync.json` exist
- Checks memory_sync is not stale

---

## Artifacts Generated

### `artifacts/`
- `state.json` - Current phase, status, timestamp
- `memory_sync.json` - Full header for resumption
- `index.md` - Artifact index

### `qa/`
- `run_log.txt` - Command outputs
- `coverage.xml` - Coverage report
- `cp_list.txt` - Discovered CP files
- `pytest.txt` - Test results
- `mypy.txt` - Type check results
- `lizard_report.txt` - Complexity report
- `interrogate.txt` - Docstring coverage
- `secrets.json` - Secret scan results
- `bandit.json` - Security scan
- `pip_audit.txt` - Dependency audit

### `reports/`
- `<phase>_snapshot.md` - Phase completion snapshots

### `context/`
- `executive_summary.md` - Accumulated phase summaries
- `claims_index.json` - Evidence claims indexed

---

## Troubleshooting

### ❌ "No tasks found and no profile set"

**Solution:** Create a task first:
```powershell
pwsh -NoProfile -File "C:\projects\Work Projects\sca-protocol-skill\commands\new-task.ps1" -TaskId 001 -TaskSlug "my-task"
```

### ❌ "Context Gate: missing/empty: hypothesis.md, evidence.json..."

**Solution:** Fill required context files in `tasks/<ID>-<slug>/context/`.

### ❌ "Coverage below threshold: line=0.850, branch=0.820"

**Solution:** Add tests to cover CP modules. Run:
```powershell
pytest --cov=src --cov-branch --cov-report=term
```

### ❌ "TDD Guard failed: src/core/model.py: missing @pytest.mark.cp"

**Solution:** Add CP marker and Hypothesis property to tests:
```python
import pytest
from hypothesis import given
from hypothesis.strategies import integers

@pytest.mark.cp
def test_model_basic():
    ...

@pytest.mark.cp
@given(x=integers())
def test_model_property(x):
    ...
```

### ❌ "Memory sync: state.json or memory_sync.json missing"

**Solution:** Run a phase or snapshot-save to generate:
```powershell
pwsh -NoProfile -File "C:\projects\Work Projects\sca-protocol-skill\commands\snapshot-save.ps1"
```

### ❌ "secrets detected: 3"

**Solution:** Review `qa/secrets.json` and remove secrets or add to `.secrets.baseline`.

---

## Advanced: AUTO Levels

- **AUTO=0**: Manual confirmation required
- **AUTO=1**: Interactive mode
- **AUTO=2**: Auto-run single phase (default)
- **AUTO=3**: Multi-phase progression

Set defaults in `.sca/profile.json` or override per-run.

---

## Advanced: SAFE/DRY Modes

### SAFE_MODE=on (default)
Only allows commands in allowlist:
`pytest`, `ruff`, `mypy`, `lizard`, `pip-audit`, `python`, `bash`, `git`, `detect-secrets`, `bandit`, `interrogate`, `pip`

### DRY_RUN=on
Prevents write operations (useful for testing).

---

## File Structure

```
<project-root>/
├─ .sca/
│  └─ profile.json              # Current task + defaults
├─ tasks/
│  ├─ 001-example-task/
│  │  ├─ context/               # Required context files
│  │  ├─ artifacts/             # State + snapshots
│  │  ├─ qa/                    # Validation reports
│  │  └─ reports/               # Phase snapshots
│  └─ 002-another-task/
├─ src/                         # Your source code
└─ tests/                       # Your tests
```

---

## Integration with Claude Code

When using this skill in Claude Code IDE:

1. The skill will auto-discover tasks from `.sca/profile.json`
2. No environment variables needed
3. All outputs go to `tasks/<ID>-<slug>/qa/`
4. Snapshots preserve state across sessions

---

## Next Steps

1. ✅ Create or select a task
2. ✅ Fill required context files
3. ✅ Write CP code with tests (TDD)
4. ✅ Run `validate-only.ps1` to check gates
5. ✅ Fix any blocked gates
6. ✅ Run `run-phase.ps1 -Phase auto` for full progression

For issues or questions, refer to the canonical protocol:
`C:\projects\Work Projects\.claude\full_protocol.md`
