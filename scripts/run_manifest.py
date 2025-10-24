import json, pathlib, subprocess, os
root = pathlib.Path(os.getenv("TASK_DIR","."))
p = root/"artifacts"; p.mkdir(parents=True, exist_ok=True)
m={"git": subprocess.getoutput("git rev-parse --short HEAD || echo no-git"),
   "coverage": str(root/"qa"/"coverage.xml"),
   "lizard":   str(root/"qa"/"lizard_report.txt"),
   "bandit":   str(root/"qa"/"bandit.json"),
   "secrets":  str(root/"qa"/"secrets.json")}
(p/"run_manifest.json").write_text(json.dumps(m,indent=2))
print(str(p/"run_manifest.json"))
