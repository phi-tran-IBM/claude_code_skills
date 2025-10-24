import os
from .workspace_guard import TaskPaths

def ensure_determinism(tp: TaskPaths):
    os.environ.setdefault("SEED","42")
    os.environ.setdefault("NP_SEED","42")
    os.environ.setdefault("TORCH_SEED","42")
    os.environ.setdefault("PYTHONHASHSEED","42")
