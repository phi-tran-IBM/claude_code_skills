import platform, sys, subprocess, pathlib, os
root = pathlib.Path(os.getenv("TASK_DIR","."))
qa = root/"qa"; qa.mkdir(parents=True, exist_ok=True)
seeds = "\n".join([
  f"SEED={os.getenv('SEED','')}",
  f"NP_SEED={os.getenv('NP_SEED','')}",
  f"TORCH_SEED={os.getenv('TORCH_SEED','')}",
  f"PYTHONHASHSEED={os.getenv('PYTHONHASHSEED','')}"
])
(qa/"env.txt").write_text("\n".join([
  f"python={platform.python_version()}",
  f"platform={platform.platform()}",
  subprocess.run([sys.executable,"-m","pip","--version"],capture_output=True,text=True).stdout.strip(),
  seeds
]))
(qa/"pip_freeze.txt").write_text(
  subprocess.run([sys.executable,"-m","pip","freeze","--all"],capture_output=True,text=True).stdout
)
