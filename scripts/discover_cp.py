from sca.cp_discovery import discover_cp
import os
for f in discover_cp(os.environ.get("TASK_DIR",".")): print(f)
