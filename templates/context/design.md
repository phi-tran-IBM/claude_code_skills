# Minimal Architecture [DES]

## Data Strategy
- Sources: (link to data_sources.json)
- Splits: (train/valid/test %, temporal windows if backtesting)
- Leakage guards: (time-based split, group-aware split, target shift checks)
- Normalization/Transforms: (fit on train only; params saved)

## Verification Strategy
- **Differential tests:** (inputs/perturbations → expected deltas) → mapped to tests/test_authenticity.py
- **Sensitivity sweeps:** (parameter grid/range, step, expected monotonicity)
- **Domain-specific method:** (k-fold=k, walk-forward windows=W, Monte Carlo N=…)
- **Success thresholds:** (repeat the α/thresholds from HYP)
