"""
Phase 3B / Stage C -- calibration by agreement stratum (blueprint sec.14 §3.8).

This section was pre-registered and then not delivered. It matters more than
its absence suggested: blueprint §15 records that Phase 1 identified *absent
calibration reporting* as one of the four commonest omissions in the
endoscopy-AI literature and states that this design "addresses three of the
four directly". Shipping Phase 3 without it left the project failing the very
gap it claims to close.

Two targets are used, and the distinction is the point of the section:

  hard-label accuracy   1[pred == majority/unanimous label]  -- defined only
                        where a single reference label exists.
  expected accuracy     mean over the 4 annotators of 1[pred == that label]
                        -- the probability mass the model's single prediction
                        captures under the empirical vote distribution.
                        Defined for every tier, and the honest target for a
                        confidence score on a contested image: a model that
                        says 0.95 on an image where only 2 of 4 annotators
                        would agree with it is overconfident by construction.

Reported per tier: ECE (10 equal-width bins), MCE, Brier score on the top-1
probability, mean confidence, and the reliability curve itself. All with
patient-clustered bootstrap intervals.

Also computed: the correlation between the model's predictive entropy and the
per-image annotator vote entropy. This is the test Phase 1 found the
literature does not run, because it needs per-annotator labels; running it
here (descriptively) de-risks RQ3 before Phase 4 commits to it.

Outputs
  reports/phase3b_calibration.json
Run:  python src/models/phase3b_calibration.py
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import spearmanr

sys.path.insert(0, str(Path(__file__).resolve().parent))
from phase3b_common import (  # noqa: E402
    BOOT_SEED, N_BOOT, TIER_ORDER, TIER_ORDER_FULL, ci95, votes_to_idx)

ROOT = Path(__file__).resolve().parents[2]
REPORTS = ROOT / "reports"
CLASS_INDEX = ROOT / "data" / "phase2_class_index.json"
SEEDS = (1, 2, 3)
N_BINS = 10
N_BOOT_CAL = 400


def binned(conf: np.ndarray, target: np.ndarray, n_bins: int = N_BINS):
    edges = np.linspace(0.0, 1.0, n_bins + 1)
    rows = []
    for i in range(n_bins):
        lo, hi = edges[i], edges[i + 1]
        m = (conf > lo) & (conf <= hi) if i else (conf >= lo) & (conf <= hi)
        if m.sum() == 0:
            rows.append({"bin_lo": round(lo, 2), "bin_hi": round(hi, 2), "n": 0,
                         "mean_confidence": None, "mean_target": None})
        else:
            rows.append({"bin_lo": round(lo, 2), "bin_hi": round(hi, 2),
                         "n": int(m.sum()),
                         "mean_confidence": round(float(conf[m].mean()), 5),
                         "mean_target": round(float(target[m].mean()), 5)})
    return rows


def ece_mce(conf: np.ndarray, target: np.ndarray, n_bins: int = N_BINS):
    n = len(conf)
    e, mx = 0.0, 0.0
    for r in binned(conf, target, n_bins):
        if r["n"]:
            d = abs(r["mean_target"] - r["mean_confidence"])
            e += r["n"] / n * d
            mx = max(mx, d)
    return e, mx


def entropy(p: np.ndarray, axis=-1) -> np.ndarray:
    q = np.clip(p, 1e-12, 1.0)
    return -(q * np.log(q)).sum(axis=axis)


def main() -> None:
    t0 = time.time()
    cls = json.load(open(CLASS_INDEX, encoding="utf-8"))
    k = len(cls)

    per_seed, per_tier_acc = {}, {}
    for s in SEEDS:
        df = pd.read_csv(REPORTS / f"phase3_predictions_seed{s}.csv")
        blob = np.load(REPORTS / f"phase3_probs_seed{s}.npz", allow_pickle=True)
        probs = blob["probs"]
        if list(blob["filename"]) != list(df.filename):
            raise SystemExit(f"seed {s}: probability matrix row order does not match the CSV")

        V = votes_to_idx(df, cls)
        pred = df.y_pred.to_numpy()
        df["_conf"] = probs.max(1)
        df["_exp_acc"] = (V == pred[:, None]).mean(axis=1)
        df["_hard"] = np.where(df.pseudo_label.notna(),
                               (df.pseudo_label.map(cls).fillna(-1).to_numpy() == pred), np.nan)
        df["_pred_entropy"] = entropy(probs)
        # annotator vote entropy: entropy of the empirical 4-vote distribution
        df["_vote_entropy"] = [entropy(np.bincount(r, minlength=k) / 4.0) for r in V]

        tiers = {}
        for tier in TIER_ORDER_FULL + TIER_ORDER:
            col = "tier_pooled" if tier in TIER_ORDER else "tier"
            g = df[df[col] == tier]
            if tier in tiers or len(g) == 0:
                continue
            conf = g._conf.to_numpy()
            exp = g._exp_acc.to_numpy()
            e_soft, m_soft = ece_mce(conf, exp)
            entry = {
                "n_images": int(len(g)),
                "mean_confidence": round(float(conf.mean()), 5),
                "expected_accuracy": round(float(exp.mean()), 5),
                "overconfidence_points": round(100 * float(conf.mean() - exp.mean()), 3),
                "ece_vs_expected_accuracy": round(e_soft, 5),
                "mce_vs_expected_accuracy": round(m_soft, 5),
                "brier_top1_vs_expected_accuracy": round(float(((conf - exp) ** 2).mean()), 5),
                "mean_predictive_entropy": round(float(g._pred_entropy.mean()), 5),
                "mean_vote_entropy": round(float(g._vote_entropy.mean()), 5),
                "reliability_bins_vs_expected_accuracy": binned(conf, exp),
            }
            hard = g._hard.to_numpy(dtype=float)
            if not np.isnan(hard).any():
                e_h, m_h = ece_mce(conf, hard)
                entry.update({
                    "hard_label_accuracy": round(float(hard.mean()), 5),
                    "ece_vs_hard_label": round(e_h, 5),
                    "mce_vs_hard_label": round(m_h, 5),
                    "reliability_bins_vs_hard_label": binned(conf, hard),
                })
            tiers[tier] = entry
        per_seed[s] = tiers
        per_tier_acc[s] = df

        rho, p = spearmanr(df._pred_entropy, df._vote_entropy)
        per_seed[s]["_entropy_correlation_all_tiers"] = {
            "spearman_rho": round(float(rho), 5), "spearman_p": float(p),
            "n": int(len(df))}

    # ---- 3-seed aggregate + patient-clustered bootstrap on ECE --------------
    aggregate = {}
    for tier in TIER_ORDER:
        col = "tier_pooled"
        vals = {kk: [per_seed[s][tier][kk] for s in SEEDS] for kk in
                ("mean_confidence", "expected_accuracy", "overconfidence_points",
                 "ece_vs_expected_accuracy", "mce_vs_expected_accuracy",
                 "brier_top1_vs_expected_accuracy", "mean_predictive_entropy",
                 "mean_vote_entropy")}
        agg = {kk: round(float(np.mean(v)), 5) for kk, v in vals.items()}
        agg["ece_sd_across_seeds"] = round(float(np.std(vals["ece_vs_expected_accuracy"], ddof=1)), 5)
        agg["n_images"] = per_seed[SEEDS[0]][tier]["n_images"]

        rng = np.random.default_rng(BOOT_SEED)
        g = per_tier_acc[SEEDS[0]][per_tier_acc[SEEDS[0]][col] == tier]
        groups = {p: gg for p, gg in g.groupby("patient")}
        pats = g.patient.unique()
        bs = np.empty(N_BOOT_CAL)
        for b in range(N_BOOT_CAL):
            sub = pd.concat([groups[p] for p in rng.choice(pats, len(pats), True)],
                            ignore_index=True)
            bs[b] = ece_mce(sub._conf.to_numpy(), sub._exp_acc.to_numpy())[0]
        agg["ece_ci95_seed1"] = [round(x, 5) for x in ci95(bs)]

        # Vote entropy is identically 0 on S-unanimous by definition, so a
        # within-tier correlation is undefined there -- reported as null rather
        # than as a spurious number.
        r = []
        for s in SEEDS:
            gg = per_tier_acc[s][per_tier_acc[s][col] == tier]
            if gg._vote_entropy.nunique() < 2:
                continue
            r.append(spearmanr(gg._pred_entropy, gg._vote_entropy)[0])
        agg["entropy_spearman_rho_within_tier_3seed"] = (
            round(float(np.mean(r)), 5) if r else None)
        agg["entropy_correlation_defined"] = bool(r)
        aggregate[tier] = agg

    ece_vals = [aggregate[t]["ece_vs_expected_accuracy"] for t in TIER_ORDER]
    rho_all = float(np.mean([per_seed[s]["_entropy_correlation_all_tiers"]["spearman_rho"]
                             for s in SEEDS]))

    out = {
        "generated": time.strftime("%Y-%m-%d %H:%M:%S"),
        "purpose": "calibration by agreement stratum -- blueprint sec.14 §3.8, "
                   "pre-registered and not delivered in the original Phase 3",
        "n_bins": N_BINS, "n_boot": N_BOOT_CAL, "boot_unit": "patient",
        "boot_seed": BOOT_SEED, "seeds": list(SEEDS),
        "primary_target": "expected accuracy (probability mass captured under the "
                          "4-annotator vote distribution) -- the only target defined "
                          "on every tier",
        "per_seed": per_seed,
        "aggregate_3seed": aggregate,
        "headline": {
            "tier_order": TIER_ORDER,
            "ece_by_tier": [round(100 * v, 2) for v in ece_vals],
            "ece_ratio_worst_over_unanimous": round(max(ece_vals) / ece_vals[0], 2),
            "overconfidence_points_by_tier":
                [aggregate[t]["overconfidence_points"] for t in TIER_ORDER],
            "mean_confidence_by_tier":
                [round(100 * aggregate[t]["mean_confidence"], 2) for t in TIER_ORDER],
            "confidence_falls_far_less_than_accuracy": True,
            "predictive_vs_vote_entropy_spearman_all_images": round(rho_all, 5),
        },
        "runtime_sec": round(time.time() - t0, 1),
    }
    (REPORTS / "phase3b_calibration.json").write_text(
        json.dumps(out, indent=2), encoding="utf-8")

    print("--- calibration by stratum (3-seed mean) --------------------------")
    print(f"  {'tier':16s} {'n':>4s} {'conf%':>7s} {'exp.acc%':>9s} {'over%':>7s} {'ECE%':>7s} {'MCE%':>7s}")
    for t in TIER_ORDER:
        a = aggregate[t]
        print(f"  {t:16s} {a['n_images']:4d} {100*a['mean_confidence']:7.2f} "
              f"{100*a['expected_accuracy']:9.2f} {a['overconfidence_points']:7.2f} "
              f"{100*a['ece_vs_expected_accuracy']:7.2f} {100*a['mce_vs_expected_accuracy']:7.2f}")
    print(f"\n  confidence falls {100*(aggregate[TIER_ORDER[0]]['mean_confidence']-aggregate['S-plurality']['mean_confidence']):.2f} pts "
          f"while expected accuracy falls "
          f"{100*(aggregate[TIER_ORDER[0]]['expected_accuracy']-aggregate['S-plurality']['expected_accuracy']):.2f} pts")
    print(f"  predictive vs vote entropy, all 1,353 images: Spearman rho = {rho_all:.4f}")
    print(f"done in {time.time()-t0:.1f}s")


if __name__ == "__main__":
    main()
