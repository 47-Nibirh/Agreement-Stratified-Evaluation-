"""
Phase 3B / Stage B -- attainable-ceiling normalisation and the pre-registered
pairwise gap intervals.

Two defects in the delivered Phase 3 are repaired here.

(1) CEILING NON-COMPARABILITY.  Phase 3 argued that the annotator-marginalized
    macro F1 is comparable across tiers because it reduces to plain macro F1
    at the S-unanimous limit.  Continuity at that limit does not make the
    scale comparable: the metric's *attainable maximum* falls with agreement.
    A perfect single-label classifier scores 1.00 expected accuracy on
    S-unanimous but at most 0.75 on S-majority (3/4 votes), 0.50 on
    S-plurality (2/4) and 0.475 on the pooled no-majority tier -- because a
    single label cannot match four disagreeing annotators.  Part of the
    reported 53.1-point "collapse" is therefore the ceiling moving, not the
    model degrading.  This script computes, per tier:

      ceiling  = the modal-vote oracle (best achievable single-label
                 predictor, ties broken at random over N_TIE draws)
      observed = the frozen model
      normalised = observed / ceiling

    and re-states RQ1's magnitude claim on the normalised scale, where the
    3.25-point architecture benchmark is also renormalised by the S-unanimous
    ceiling (=1.0) so the comparison stays like-for-like.

(2) MISSING PRE-REGISTERED INTERVAL.  Blueprint sec.4 Phase 3, pre-registered
    decision 4 requires "pairwise patient-clustered bootstrap CIs on the
    S-unanimous - S-no-majority gap compared against the 3.25-point
    architecture benchmark".  The delivered phase reported per-tier CIs but
    no interval on any gap, so the headline claim had no inferential support.
    All 6 pairwise tier gaps are computed here, per seed, with the same
    patient-clustered bootstrap (1,000 resamples, seed 20260726), on both the
    raw and the ceiling-normalised metric.

Outputs
  reports/phase3b_ceiling_gaps.json
Run:  python src/models/phase3b_ceiling.py
"""
from __future__ import annotations

import itertools
import json
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from phase3b_common import (  # noqa: E402
    ANN_COLS, ARCH_GAP_BENCHMARK, BOOT_SEED, N_BOOT, TIER_ORDER, TIER_ORDER_FULL,
    any_hit_rate, ci95, expected_accuracy, macro_f1, marginalized_macro_f1,
    max_expected_accuracy, modal_oracle, patient_bootstrap, votes_to_idx)

ROOT = Path(__file__).resolve().parents[2]
REPORTS = ROOT / "reports"
CLASS_INDEX = ROOT / "data" / "phase2_class_index.json"
SEEDS = (1, 2, 3)
N_TIE = 200          # random tie-breaks for the oracle on 2-2 images (point estimate)
N_TIE_BOOT = 10      # tie-break realisations carried inside each bootstrap draw
N_BOOT_GAP = 500     # per pair, per seed, per scale (patient-clustered)


def main() -> None:
    t0 = time.time()
    cls = json.load(open(CLASS_INDEX, encoding="utf-8"))
    k = len(cls)
    dfs = {s: pd.read_csv(REPORTS / f"phase3_predictions_seed{s}.csv") for s in SEEDS}

    # ---- 1. attainable ceilings (model-independent: they depend only on votes)
    base = dfs[SEEDS[0]]
    ceilings = {}
    for tier in TIER_ORDER + ["S-tied", "S-dispersed"]:
        col = "tier_pooled" if tier in TIER_ORDER else "tier"
        g = base[base[col] == tier]
        V = votes_to_idx(g, cls)
        rng = np.random.default_rng(BOOT_SEED)
        f1s = [marginalized_macro_f1(V, modal_oracle(V, rng), k) for _ in range(N_TIE)]
        ceilings[tier] = {
            "n_images": int(len(g)),
            "max_expected_accuracy_exact": round(max_expected_accuracy(V), 5),
            "oracle_marginalized_macro_f1_mean": round(float(np.mean(f1s)), 5),
            "oracle_marginalized_macro_f1_sd_over_tiebreaks": round(float(np.std(f1s, ddof=1)), 5),
            "mean_distinct_labels_per_image": round(float(
                np.mean([len(np.unique(r)) for r in V])), 4),
        }

    # ---- 2. observed vs ceiling, 3-seed mean --------------------------------
    normalised = {}
    for tier in TIER_ORDER:
        obs_f1, obs_acc, obs_hit = [], [], []
        for s in SEEDS:
            g = dfs[s][dfs[s].tier_pooled == tier]
            V = votes_to_idx(g, cls)
            p = g.y_pred.to_numpy()
            obs_f1.append(marginalized_macro_f1(V, p, k))
            obs_acc.append(expected_accuracy(V, p))
            obs_hit.append(any_hit_rate(V, p))
        cf1 = ceilings[tier]["oracle_marginalized_macro_f1_mean"]
        cac = ceilings[tier]["max_expected_accuracy_exact"]
        normalised[tier] = {
            "observed_marginalized_macro_f1": round(float(np.mean(obs_f1)), 5),
            "ceiling_marginalized_macro_f1": cf1,
            "ceiling_normalised_macro_f1": round(float(np.mean(obs_f1)) / cf1, 5),
            "observed_expected_accuracy": round(float(np.mean(obs_acc)), 5),
            "ceiling_expected_accuracy": cac,
            "ceiling_normalised_expected_accuracy": round(float(np.mean(obs_acc)) / cac, 5),
            "observed_any_hit_rate": round(float(np.mean(obs_hit)), 5),
        }

    raw = [normalised[t]["observed_marginalized_macro_f1"] for t in TIER_ORDER]
    nrm = [normalised[t]["ceiling_normalised_macro_f1"] for t in TIER_ORDER]
    nac = [normalised[t]["ceiling_normalised_expected_accuracy"] for t in TIER_ORDER]

    # ---- 3. pairwise gaps with patient-clustered bootstrap CIs ---------------
    # Oracle predictions are a property of the vote matrix, not of the model, so
    # they are precomputed once per image and carried through the resampling as
    # extra columns. The ceiling must be recomputed INSIDE each bootstrap draw:
    # holding it fixed at the full-tier value while the numerator is resampled
    # breaks the pairing and inflates the ratio (a resample with duplicated
    # patients covers fewer distinct classes, which depresses any macro F1 --
    # numerator and denominator have to absorb that together).
    ORACLE_COLS = []
    for j in range(N_TIE_BOOT):
        rng = np.random.default_rng(BOOT_SEED + 1000 + j)
        col = f"_oracle{j}"
        ORACLE_COLS.append(col)
        for s in SEEDS:
            dfs[s][col] = modal_oracle(votes_to_idx(dfs[s], cls), rng)

    def gap_ci(df, tA, tB, normalise):
        rng = np.random.default_rng(BOOT_SEED)
        out = np.empty(N_BOOT_GAP)
        parts = {}
        for t in (tA, tB):
            g = df[df.tier_pooled == t]
            parts[t] = ({p: gg for p, gg in g.groupby("patient")}, g.patient.unique())
        for b in range(N_BOOT_GAP):
            vals = {}
            for t in (tA, tB):
                grp, pats = parts[t]
                sub = pd.concat([grp[p] for p in rng.choice(pats, len(pats), True)],
                                ignore_index=True)
                V = votes_to_idx(sub, cls)
                obs = marginalized_macro_f1(V, sub.y_pred.to_numpy(), k)
                if normalise:
                    ceil = float(np.mean([marginalized_macro_f1(V, sub[c].to_numpy(), k)
                                          for c in ORACLE_COLS]))
                    obs = obs / ceil if ceil > 0 else np.nan
                vals[t] = obs
            out[b] = vals[tA] - vals[tB]
        return out[~np.isnan(out)]

    pairs = list(itertools.combinations(TIER_ORDER, 2))
    gaps = {}
    for tA, tB in pairs:
        for scale in ("raw", "ceiling_normalised"):
            norm = scale == "ceiling_normalised"
            per_seed = []
            for s in SEEDS:
                bs = gap_ci(dfs[s], tA, tB, norm)
                plug = []
                for t in (tA, tB):
                    g = dfs[s][dfs[s].tier_pooled == t]
                    V = votes_to_idx(g, cls)
                    v = marginalized_macro_f1(V, g.y_pred.to_numpy(), k)
                    if norm:
                        v /= ceilings[t]["oracle_marginalized_macro_f1_mean"]
                    plug.append(v)
                per_seed.append({"seed": s,
                                 "gap_points_plugin": round(100 * (plug[0] - plug[1]), 3),
                                 "gap_points_boot_mean": round(100 * float(bs.mean()), 3),
                                 "ci95_points": [round(100 * x, 3) for x in ci95(bs)]})
            pooled_lo = float(np.mean([d["ci95_points"][0] for d in per_seed]))
            pooled_hi = float(np.mean([d["ci95_points"][1] for d in per_seed]))
            pooled_pt = float(np.mean([d["gap_points_plugin"] for d in per_seed]))
            gaps[f"{tA} - {tB} [{scale}]"] = {
                "per_seed": per_seed,
                "gap_points_boot_mean_3seed": round(float(np.mean(
                    [d["gap_points_boot_mean"] for d in per_seed])), 3),
                "gap_points_3seed_mean": round(pooled_pt, 3),
                "ci95_points_3seed_mean": [round(pooled_lo, 3), round(pooled_hi, 3)],
                "excludes_zero": bool(pooled_lo > 0 or pooled_hi < 0),
                "lower_bound_exceeds_architecture_benchmark":
                    bool(pooled_lo > ARCH_GAP_BENCHMARK),
            }
        print(f"  gap {tA} - {tB} done", flush=True)

    key_raw = gaps["S-unanimous - S-no-majority [raw]"]
    key_nrm = gaps["S-unanimous - S-no-majority [ceiling_normalised]"]

    out = {
        "generated": time.strftime("%Y-%m-%d %H:%M:%S"),
        "purpose": ("attainable-ceiling normalisation of the Phase 3 primary metric, "
                    "and the pre-registered pairwise patient-clustered bootstrap gap "
                    "intervals that the delivered Phase 3 did not compute"),
        "n_boot": N_BOOT_GAP, "boot_unit": "patient", "boot_seed": BOOT_SEED,
        "n_tiebreaks_for_oracle": N_TIE,
        "ceilings": ceilings,
        "observed_vs_ceiling": normalised,
        "rq1_restated": {
            "tier_order": TIER_ORDER,
            "raw_marginalized_macro_f1": [round(100 * v, 2) for v in raw],
            "ceiling_normalised_macro_f1_pct_of_attainable": [round(100 * v, 2) for v in nrm],
            "ceiling_normalised_expected_accuracy_pct_of_attainable":
                [round(100 * v, 2) for v in nac],
            "raw_gap_points": round(100 * (raw[0] - raw[-1]), 2),
            "raw_gap_ci95_points": key_raw["ci95_points_3seed_mean"],
            "ceiling_normalised_gap_points": round(100 * (nrm[0] - nrm[-1]), 2),
            "ceiling_normalised_gap_ci95_points": key_nrm["ci95_points_3seed_mean"],
            "architecture_benchmark_points": ARCH_GAP_BENCHMARK,
            "raw_gap_lower_bound_exceeds_benchmark":
                key_raw["lower_bound_exceeds_architecture_benchmark"],
            "ceiling_normalised_gap_lower_bound_exceeds_benchmark":
                key_nrm["lower_bound_exceeds_architecture_benchmark"],
            "strictly_monotonic_raw": bool(all(raw[i] >= raw[i + 1] for i in range(3))),
            "strictly_monotonic_ceiling_normalised":
                bool(all(nrm[i] >= nrm[i + 1] for i in range(3))),
        },
        "pairwise_gaps": gaps,
        "runtime_sec": round(time.time() - t0, 1),
    }
    (REPORTS / "phase3b_ceiling_gaps.json").write_text(
        json.dumps(out, indent=2), encoding="utf-8")

    print("\n--- attainable ceiling per tier -----------------------------------")
    for t in TIER_ORDER:
        c = ceilings[t]; nn = normalised[t]
        print(f"  {t:16s} n={c['n_images']:4d}  ceiling F1={100*c['oracle_marginalized_macro_f1_mean']:6.2f}"
              f"  observed={100*nn['observed_marginalized_macro_f1']:6.2f}"
              f"  -> {100*nn['ceiling_normalised_macro_f1']:6.2f}% of attainable")
    print("\n--- RQ1 restated --------------------------------------------------")
    print(f"  raw gap                 {100*(raw[0]-raw[-1]):6.2f} pts  95% CI {key_raw['ci95_points_3seed_mean']}")
    print(f"  ceiling-normalised gap  {100*(nrm[0]-nrm[-1]):6.2f} pts  95% CI {key_nrm['ci95_points_3seed_mean']}")
    print(f"  benchmark {ARCH_GAP_BENCHMARK} pts exceeded by the normalised LOWER bound: "
          f"{key_nrm['lower_bound_exceeds_architecture_benchmark']}")
    print(f"  monotonic (raw / normalised): {out['rq1_restated']['strictly_monotonic_raw']} / "
          f"{out['rq1_restated']['strictly_monotonic_ceiling_normalised']}")
    print(f"\n  S-plurality - S-no-majority [raw]: "
          f"{gaps['S-plurality - S-no-majority [raw]']['gap_points_3seed_mean']} pts "
          f"CI {gaps['S-plurality - S-no-majority [raw]']['ci95_points_3seed_mean']} "
          f"excludes 0: {gaps['S-plurality - S-no-majority [raw]']['excludes_zero']}")
    print(f"done in {time.time()-t0:.1f}s")


if __name__ == "__main__":
    main()
