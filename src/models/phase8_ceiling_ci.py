"""
Phase 8 / P8.2 -- an interval for the attainable ceiling itself.

WHAT THIS IS NOT. It is not a correction to RQ1. The ceiling-normalised gap
reported in Chapter 4 already propagates ceiling uncertainty: phase3b_ceiling.py
recomputes the ceiling inside every bootstrap draw rather than holding it at its
full-tier value, precisely so that numerator and denominator absorb the same
resampling shock. That construction is correct and is unchanged here.

WHAT IT IS. Chapter 4's per-stratum table reports the ceiling as a bare point
estimate. The ceiling is a sample statistic like any other -- it is the modal
vote of four annotators on the particular patients who happen to be in the test
split -- so it has sampling error, and a table that prints it to four decimals
without an interval invites the reader to treat it as a known constant. This
script gives it the same patient-clustered interval every other quantity in the
thesis carries, so the table can show one.

Both estimands from P8.1 are bootstrapped, because both appear in the document:

    panel_ceiling  -- modal-of-4 scored against all four   (Chapter 4)
    loo_oracle     -- modal-of-3 scored against those three (Chapter 7)

Tie-breaks are re-randomised inside each draw for the same reason the ceiling is
recomputed inside each draw: a tie-break held fixed across resamples would
understate the spread.

Emits reports/phase8_ceiling_ci.json. No GPU.

Run:  python src/models/phase8_ceiling_ci.py
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from phase3b_common import (  # noqa: E402
    BOOT_SEED, TIER_ORDER, ci95, macro_f1, marginalized_macro_f1, modal_oracle,
    votes_to_idx)

ROOT = Path(__file__).resolve().parents[2]
REPORTS = ROOT / "reports"
CLASS_INDEX = ROOT / "data" / "phase2_class_index.json"
OUT = REPORTS / "phase8_ceiling_ci.json"

POOLED = "S-contested (pooled)"
CONTESTED = ("S-majority", "S-plurality", "S-no-majority")
N_BOOT_CEIL = 1000
N_TIE_IN_BOOT = 10


def _loo_oracle(V: np.ndarray, k: int, rng: np.random.Generator) -> float:
    folds = []
    for a in range(4):
        refs = [b for b in range(4) if b != a]
        sub = V[:, refs]
        n = sub.shape[0]
        pred = np.empty(n, dtype=int)
        for i in range(n):
            v, c = np.unique(sub[i], return_counts=True)
            best = v[c == c.max()]
            pred[i] = best[0] if len(best) == 1 else rng.choice(best)
        folds.append(float(np.mean([macro_f1(V[:, b], pred, k) for b in refs])))
    return float(np.mean(folds))


def main() -> None:
    t0 = time.time()
    cls = json.load(open(CLASS_INDEX, encoding="utf-8"))
    k = len(cls)
    df = pd.read_csv(REPORTS / "phase3_predictions_seed1.csv")

    masks = {t: (df.tier_pooled == t).to_numpy() for t in TIER_ORDER}
    masks[POOLED] = np.logical_or.reduce([masks[t] for t in CONTESTED])

    out_rows = {}
    for tier, m in masks.items():
        g = df[m]
        groups = {p: gg for p, gg in g.groupby("patient")}
        pats = g.patient.unique()
        rng = np.random.default_rng(BOOT_SEED)
        panel_b = np.empty(N_BOOT_CEIL)
        loo_b = np.empty(N_BOOT_CEIL)
        for b in range(N_BOOT_CEIL):
            sub = pd.concat([groups[p] for p in rng.choice(pats, len(pats), True)],
                            ignore_index=True)
            V = votes_to_idx(sub, cls)
            panel_b[b] = float(np.mean([
                marginalized_macro_f1(V, modal_oracle(V, rng), k)
                for _ in range(N_TIE_IN_BOOT)]))
            loo_b[b] = _loo_oracle(V, k, rng)

        V_full = votes_to_idx(g, cls)
        rng_pt = np.random.default_rng(BOOT_SEED)
        panel_pt = float(np.mean([
            marginalized_macro_f1(V_full, modal_oracle(V_full, rng_pt), k)
            for _ in range(200)]))
        loo_pt = _loo_oracle(V_full, k, np.random.default_rng(20260729))

        out_rows[tier] = {
            "n_images": int(m.sum()),
            "n_patients": int(len(pats)),
            "panel_ceiling": {
                "point": round(panel_pt, 5),
                "boot_mean": round(float(panel_b.mean()), 5),
                "ci95": [round(x, 5) for x in ci95(panel_b)],
                "half_width": round(float(np.diff(ci95(panel_b))[0] / 2), 5),
            },
            "loo_oracle": {
                "point": round(loo_pt, 5),
                "boot_mean": round(float(loo_b.mean()), 5),
                "ci95": [round(x, 5) for x in ci95(loo_b)],
                "half_width": round(float(np.diff(ci95(loo_b))[0] / 2), 5),
            },
        }

    out = {
        "generated": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "phase": "8 / P8.2 ceiling interval",
        "scope": (
            "presentational, not a correction. RQ1's ceiling-normalised gap "
            "already recomputes the ceiling inside each bootstrap draw "
            "(phase3b_ceiling.py, gap_ci), so ceiling uncertainty is already "
            "propagated into the confirmatory endpoint. This artefact exists so "
            "that the per-stratum table can print an interval beside the "
            "ceiling instead of a bare point estimate."),
        "method": (
            f"patient-clustered bootstrap, {N_BOOT_CEIL} resamples, seed "
            f"{BOOT_SEED}; tie-breaks re-randomised within each draw "
            f"({N_TIE_IN_BOOT} realisations for the panel ceiling) so the "
            f"interval carries tie-break variance as well as patient "
            f"variance."),
        "estimands": {
            "panel_ceiling": "modal-of-4 against all four annotators (Chapter 4)",
            "loo_oracle": "modal-of-3 against those same three (Chapter 7)",
        },
        "by_stratum": out_rows,
        "runtime_sec": round(time.time() - t0, 1),
    }
    OUT.write_text(json.dumps(out, indent=1), encoding="utf-8")

    print(f"[P8.2] {'stratum':22s} {'n':>5s} {'panel ceiling':>24s} "
          f"{'LOO oracle':>24s}")
    for t, r in out_rows.items():
        p, l = r["panel_ceiling"], r["loo_oracle"]
        print(f"       {t:22s} {r['n_images']:5d} "
              f"{p['point']:.4f} [{p['ci95'][0]:.4f}, {p['ci95'][1]:.4f}]   "
              f"{l['point']:.4f} [{l['ci95'][0]:.4f}, {l['ci95'][1]:.4f}]")
    print(f"[P8.2] wrote {OUT.name} in {out['runtime_sec']}s")


if __name__ == "__main__":
    main()
