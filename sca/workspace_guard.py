import pathlib

class TaskPaths:
    def __init__(self, task_dir: str):
        self.root = pathlib.Path(task_dir)
        self.context = self.root / "context"
        self.artifacts = self.root / "artifacts"
        self.qa = self.root / "qa"
        self.reports = self.root / "reports"

    def ensure(self):
        for p in (self.context, self.artifacts, self.qa, self.reports):
            p.mkdir(parents=True, exist_ok=True)

def assert_task_scoped_write(path: pathlib.Path, tp: 'TaskPaths'):
    try:
        path.resolve().relative_to(tp.root.resolve())
    except Exception:
        raise RuntimeError(f"Write blocked outside TASK_DIR: {path}")
