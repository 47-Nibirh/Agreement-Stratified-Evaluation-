"""
P5.8 -- calibration transfer (P5-C).

Does the Phase 4 calibration ORDERING of the five arms survive the domain shift?

Two definitional differences from Phase 4 are declared here rather than buried,
because they mean absolute external ECE is NOT directly comparable to absolute
internal ECE, even though the ordering is:

  1. Phase 4 scored ECE against annotator-marginalised EXPECTED accuracy. The
     external corpora ship no per-annotator votes, so external correctness is
     plain 0/1 against the collapsed label.
  2. Confidence is the 23-way top-1 probability, but correctness is judged at
     collapsed granularity. A model can be right about the group while its
     23-way top-1 mass is split across members of that group, which reads as
     under-confidence. ECE on the COLLAPSED group mass is therefore reported
     alongside as the secondary definition.

The verdict is a rank correlation, which is invariant to both.

Outputs
  reports/phase5_calibration.json
Run:  python src/models/phase5_calibration.py
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import numpy as np
from scipy.stats import spearmanr

sys.path.insert(0, str(Path(__file__).resolve().parent))
from phase5_common import (  # noqa: E402
    N_BOOT, REPORTS, available_arms, ci95, collapse_vector, collapsed_pred,
    external_panel, ext_probs_path, image_resamples, prereg)

OUT = REPORTS / "phase5_calibration.json"
P4_CAL = REPORTS / "phase4_calibration.json"
N_BINS = 10
POOLED = "S-contested (pooled)"


def ece(conf: np.ndarray, correct: np.ndarray, n_bins: int = N_BINS) -> float:
    edges = np.linspace(0.0, 1.0, n_bins + 1)
    idx = np.clip(np.digitize(conf, edges[1:-1], right=False), 0, n_bins - 1)
    total = 0.0
    for b in range(n_bins):
        m = idx == b
        if not m.any():
            continue
        total += m.mean() * abs(conf[m].mean() - correct[m].mean())
    return float(total)


def mce(conf: np.ndarray, correct: np.ndarray, n_bins: int = N_BINS) -> float:
    edges = np.linspace(0.0, 1.0, n_bins + 1)
    idx = np.clip(np.digitize(conf, edges[1:-1], right=False), 0, n_bins - 1)
    gaps = [abs(conf[idx == b].mean() - correct[idx == b].mean())
            for b in range(n_bins) if (idx == b).any()]
    return float(max(gaps)) if gaps else 0.0


def main() -> int:
    t0 = time.time()
    pre = prereg()
    seeds = pre["arms"]["seeds"]
    arms = available_arms(seeds)
    if not arms:
        print("[P5.8] no arm has a complete set of external predictions yet.")
        return 1

    cv = collapse_vector()
    ext = external_panel()
    truth = ext["collapsed_label"].to_numpy()
    n = len(ext)
    groups = sorted({str(g) for g in cv})
    gidx = {g: np.array([i for i, x in enumerate(cv) if x == g]) for g in groups}

    per_seed, agg, cache = {}, {}, {}
    for cfg in arms:
        per_seed[cfg] = {}
        for s in seeds:
            p = np.load(ext_probs_path(cfg, s))["probs"]
            pred = collapsed_pred(p, cv)
            correct = (pred == truth).astype(float)
            conf_top1 = p.max(1)
            # collapsed group mass for the PREDICTED group
            mass = np.stack([p[:, gidx[g]].sum(1) for g in groups], axis=1)
            conf_group = mass.max(1)
            cache[(cfg, s)] = (conf_top1, conf_group, correct)
            per_seed[cfg][s] = {
                "accuracy_collapsed": round(float(correct.mean()), 5),
                "mean_top1_confidence": round(float(conf_top1.mean()), 5),
                "ece_top1": round(100 * ece(conf_top1, correct), 3),
                "mce_top1": round(100 * mce(conf_top1, correct), 3),
                "ece_group_mass": round(100 * ece(conf_group, correct), 3),
                "overconfidence_points": round(
                    100 * float(conf_top1.mean() - correct.mean()), 3),
                "brier_top1": round(float(np.mean((conf_top1 - correct) ** 2)), 5),
            }
        e = [per_seed[cfg][s]["ece_top1"] for s in seeds]
        reps = []
        for loc in image_resamples(n):
            reps.append(float(np.mean(
                [100 * ece(cache[(cfg, s)][0][loc], cache[(cfg, s)][2][loc])
                 for s in seeds])))
        agg[cfg] = {
            "ece_top1_mean_3seed": round(float(np.mean(e)), 3),
            "ece_top1_ci95": [round(x, 3) for x in ci95(np.asarray(reps))],
            "ece_group_mass_mean_3seed": round(float(np.mean(
                [per_seed[cfg][s]["ece_group_mass"] for s in seeds])), 3),
            "accuracy_collapsed_mean_3seed": round(float(np.mean(
                [per_seed[cfg][s]["accuracy_collapsed"] for s in seeds])), 5),
            "overconfidence_points_mean_3seed": round(float(np.mean(
                [per_seed[cfg][s]["overconfidence_points"] for s in seeds])), 3),
        }
        print(f"  {cfg}: external ECE {agg[cfg]['ece_top1_mean_3seed']:6.2f} "
              f"CI {agg[cfg]['ece_top1_ci95']}  acc "
              f"{agg[cfg]['accuracy_collapsed_mean_3seed']:.4f}  overconf "
              f"{agg[cfg]['overconfidence_points_mean_3seed']:+.2f}")

    # ---- P5-C verdict: does the ordering survive? ---------------------------
    internal = {}
    if P4_CAL.exists():
        p4 = json.loads(P4_CAL.read_text(encoding="utf-8"))["aggregate_3seed"]
        internal = {c: round(100 * p4[c][POOLED]["ece_vs_expected_accuracy"], 3)
                    for c in arms if c in p4}

    verdict = {"computable": False}
    if len(internal) == len(arms) and len(arms) >= 3:
        int_v = [internal[c] for c in arms]
        ext_v = [agg[c]["ece_top1_mean_3seed"] for c in arms]
        rho, p = spearmanr(int_v, ext_v)
        best_int = min(internal, key=internal.get)
        best_ext = min(agg, key=lambda c: agg[c]["ece_top1_mean_3seed"])
        verdict = {
            "computable": True,
            "arms": arms,
            "internal_ece_points": internal,
            "external_ece_points": {c: agg[c]["ece_top1_mean_3seed"] for c in arms},
            "internal_rank_order": sorted(arms, key=lambda c: internal[c]),
            "external_rank_order": sorted(
                arms, key=lambda c: agg[c]["ece_top1_mean_3seed"]),
            "spearman_rho": round(float(rho), 5),
            "spearman_p": float(p),
            "lowest_ece_internal": best_int,
            "lowest_ece_external": best_ext,
            "lowest_ece_arm_preserved": best_int == best_ext,
            "verdict": ("PRESERVED" if rho >= 0.7 else
                        "PARTIALLY PRESERVED" if rho >= 0.3 else "NOT PRESERVED"),
            "rule": pre["research_questions"]["P5-C"]["verdict_rule"],
        }
        print(f"\n  internal order {verdict['internal_rank_order']}")
        print(f"  external order {verdict['external_rank_order']}")
        print(f"  Spearman rho {rho:.4f} -> {verdict['verdict']}")

    out = {
        "generated": time.strftime("%Y-%m-%d %H:%M:%S"),
        "phase": 5, "step": "P5.8",
        "endpoint": pre["research_questions"]["P5-C"]["primary_endpoint"],
        "hypothesis": pre["research_questions"]["P5-C"]["hypothesis"],
        "n_images": n, "n_bins": N_BINS,
        "n_boot": N_BOOT, "boot_unit": "image",
        "boot_unit_caveat": pre["interval_procedure"]["declared_weakness"],
        "definitional_differences_from_phase4": [
            ("Phase 4 scored ECE against annotator-marginalised EXPECTED accuracy; "
             "the external corpora ship no per-annotator votes, so external "
             "correctness is plain 0/1 against the collapsed label."),
            ("confidence is the 23-way top-1 probability while correctness is judged "
             "at collapsed granularity, so mass split across members of the correct "
             "group reads as under-confidence. ECE on the collapsed group mass is "
             "reported alongside as the secondary definition."),
            ("consequence: absolute external ECE is NOT directly comparable to "
             "absolute internal ECE. The P5-C verdict is a RANK correlation, which "
             "is invariant to both differences."),
        ],
        "arms": arms, "seeds": seeds,
        "per_seed": per_seed,
        "aggregate_3seed": agg,
        "verdict_P5C": verdict,
        "runtime_sec": round(time.time() - t0, 1),
    }
    OUT.write_text(json.dumps(out, indent=1), encoding="utf-8")
    print(f"[P5.8] wrote {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
