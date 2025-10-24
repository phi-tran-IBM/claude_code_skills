# sca-protocol-skill (updated)

Implements the Scientific Coding Agent protocol as a Claude Skill with tightened enforcement:
AUTO/SAFE/DRY wrapper, Context Gate, CP discovery (task-scoped), TDD Guard,
QA Hard Gates (coverage ≥95% CP), Snapshot Save + Memory Sync, task-scoped IO.

## Quickstart
1. Set a task (PowerShell):
   ```powershell
   $env:TASK_ID="010"; $env:TASK_SLUG="code-analysis-optimization-debugging"
   $env:TASK_DIR="tasks\$($env:TASK_ID)-$($env:TASK_SLUG)"
   $env:AUTO="2"; $env:SAFE_MODE="on"; $env:DRY_RUN="off"
   ```
2. Run a phase (auto progression):
   ```powershell
   pwsh -NoProfile -File commands/run-phase.ps1 -Phase auto -AUTO $env:AUTO -SAFE_MODE $env:SAFE_MODE -DRY_RUN $env:DRY_RUN
   ```
3. Validate only:
   ```powershell
   pwsh -NoProfile -File commands/validate-only.ps1
   ```
4. Force snapshot:
   ```powershell
   pwsh -NoProfile -File commands/snapshot-save.ps1
   ```
5. Task management (single-argument Task form):
   - Create new task and validate:
     ```powershell
     pwsh -NoProfile -File commands/new-task-entrypoint.ps1 -Task "001-initial-setup" -Description "Bootstrap project"
     ```
   - Switch to an existing task and validate:
     ```powershell
     pwsh -NoProfile -File commands/use-task-entrypoint.ps1 -Task "001-initial-setup"
     ```
