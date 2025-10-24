# Core Hypothesis [HYP]
- Capability to prove:
- Primary metric(s): (name, definition, unit)
- **α / threshold(s):** (e.g., α=0.05; AUC≥0.90; Δ≥+3.0%)
- Baseline comparator(s):
- **Falsification test:** (what result would reject the hypothesis?)
- **Stopping criteria:** (what ends experimentation?)

# Scope
- Critical Path (CP): e.g., src/core/algorithm.py
- Exclusions (Deferred for production): (UI, full HPO, etc.)

# Power / CI Plan
- Method: (bootstrap N=… / test power … / CI type …)
- Sample size / runs: (N=…)
- **Risk counter-metrics:** (latency, memory, cost)
