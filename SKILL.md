# SCA Protocol Skill v0.3.0

Scientific Coding Agent protocol skill with full task management, session tracking, and workflow execution.

## Authority
`C:\projects\Work Projects\.claude\full_protocol.md` is the canonical specification. If memory and file disagree, **the file wins**.

## Entrypoints

### Workflow Execution
- **`run_phase`** - Execute a workflow phase (context → 1 → 2 → 3 → 4 → 5) with validation and session tracking
- **`validate_only`** - Run validation gates without executing workflow phases
- **`snapshot_save`** - Save current task state and memory sync to artifacts

### Task Management (NEW)
All task management operations include full session tracking, validation gates, and event logging.

- **`get_task`** - Get current task information with validation
  - Natural language: "what is my current task", "current task status", "show current task"
  - Returns: Task metadata, validation status, session/run IDs
  - Validates: workspace + context gates

- **`new_task`** - Create a new task with directory structure and validation
  - Natural language: "create new task", "new task for X", "start task"
  - Parameters: either a single `Task` key in `<id>-<slug>` format (e.g., `001-initial-setup`) or separate `TaskId` and `TaskSlug`. `Description` optional.
  - Creates: `tasks/<id>-<slug>/` with context/, artifacts/, qa/, reports/ directories
  - Validates: workspace + context gates (context will fail initially until populated)

- **`use_task`** - Switch to a different task with validation
  - Natural language: "switch to task X", "use task X", "change task"
  - Parameters: either a single `Task` key in `<id>-<slug>` format or separate `TaskId` and `TaskSlug`.
  - Updates: `.sca/profile.json` current_task
  - Validates: workspace + context gates on target task

- **`list_tasks`** - List all tasks in current directory with metadata
  - Natural language: "list tasks", "show tasks", "what tasks exist", "available tasks"
  - Scope: Current directory `./tasks/` only (not parent repositories)
  - Returns: Array of tasks with task_id, is_current, last_phase, last_status, session_id, last_run_id
  - Validates: workspace gate on current directory

## Session Tracking

All entrypoints (workflow + task management) implement full traceability per protocol v13.7 §11:

- **session_id**: Persistent UUID per task (survives multiple invocations)
- **run_id**: Unique timestamped ID per invocation (`YYYYMMDD-HHMMSS-<uuid8>`)
- **Artifacts**: run_context.json, run_manifest.json, run_events.jsonl, run_log.txt
- **Event logging**: All operations logged with start/complete/fail status

## Validation Gates

Task management operations run the same validation gates as workflow execution:
- **Workspace gate**: Required directories (context/, artifacts/, qa/, reports/) exist
- **Context gate**: Valid hypothesis.md, design.md, evidence.json, data_sources.json, adr.md, assumptions.md, cp_paths.json
- **Traceability gate**: (workflow only) Run artifacts exist and are valid

## File Scope

All writes are confined to `<TASK_DIR>\{context,artifacts,qa,reports}`. No modifications outside task directories.

## Multi-Level Repository Support

The skill supports nested project hierarchies:
- Discovers `.sca/profile.json` by walking up directory tree
- Creates local `tasks/` directories without duplicating `.sca/` scaffolding
- Each project can have local tasks while sharing parent configuration
