"""
Phase 4 / Stage K -- leave-one-annotator-out sensitivity.

Blueprint sec.2.3 records that FG2 is the outlier annotator on every measure:
its agreement with the other resident (kappa 0.6799) is the lowest pair in the
panel, and it rejects 8.90% of images as unusable against FG1's 1.48% -- a 6.0x
spread. Every Phase 3 and Phase 4 number is an average over the four annotator
columns, so the obvious objection is that one atypical rater is driving the
result. This script tests that objection instead of dismissing it.

What is varied, and what is not. Only the METRIC is recomputed: the
annotator-marginalized macro F1, the expected accuracy and the vote entropy are
rebuilt from three annotator columns instead of four. The agreement STRATA stay
as defined by the full four-annotator vote matrix, and no model is retrained.
Holding the strata fixed is the point -- it keeps every configuration scored on
exactly the same images, so the comparison isolates the effect of the rater on
the measurement rather than confounding it with a change of cohort.

What is NOT done, and what it would cost. A training-side LOAO would rebuild
the C2 target vectors from three annotators and retrain; the pre-registration
records this as unexecuted for budget (4 further runs, ~5 h) with the command
already implemented as `phase4_train.py --drop-annotator k`. Nothing here
substitutes for it, and the distinction is kept explicit in the output.

Outputs
  reports/phase4_loao.json
Run:  python src/models/phase4_loao.py
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import numpy as np
from scipy.stats import spearmanr

sys.path.insert(0, str(Path(__file__).resolve().parent))
from phase4_common import (  # noqa: E402
    ANN_COLS, BOOT_SEED, CONFIG_LABEL, CONTESTED, POOLED_CONTESTED, REPORTS,
    SEEDS, STRATA, available_configs, build_panel, ci95, classes, macro_f1,
    patient_resamples, prereg, probs_path, stratum_mask, verdict, votes_to_idx)

ANNOTATORS = ["FG1 (Team A)", "FG2 (Team A)", "G1 (Team B)", "G2 (Team B)"]
N_BOOT_LOAO = 1000  # pre-registered minimum; see phase4_common.N_BOOT_PAIR


def entropy(p, axis=-1):
    q = np.clip(p, 1e-12, 1.0)
    return -(q * np.log(q)).sum(axis=axis)


def marg_f1_subset(Vsub, pred, k):
    return float(np.mean([macro_f1(Vsub[:, a], pred, k) for a in range(Vsub.shape[1])]))


def main() -> None:
    t0 = time.time()
    cls = classes()
    k = len(cls)
    pre = prereg()
    cfgs = available_configs()
    panel, _ = build_panel(cfgs)
    V = votes_to_idx(panel, cls)
    pat = panel.patient.to_numpy()

    pe = {}
    for cfg in cfgs:
        for s in SEEDS:
            pe[(cfg, s)] = entropy(np.load(probs_path(cfg, s),
                                           allow_pickle=True)["probs"].astype(np.float64))

    subsets = {"all4": list(range(4))}
    for a in range(4):
        subsets[f"drop_{ANNOTATORS[a].split()[0]}"] = [j for j in range(4) if j != a]

    # ---- per subset, per configuration, per stratum -------------------------
    results = {}
    for sname, cols in subsets.items():
        Vs = V[:, cols]
        vent = np.array([entropy(np.bincount(r, minlength=k) / len(cols)) for r in Vs])
        block = {}
        for cfg in cfgs:
            row = {}
            for st in STRATA:
                rows = np.where(stratum_mask(panel, st))[0]
                f1 = [marg_f1_subset(Vs[rows], panel[f"pred_{cfg}_{s}"].to_numpy()[rows], k)
                      for s in SEEDS]
                acc = [float((Vs[rows] == panel[f"pred_{cfg}_{s}"].to_numpy()[rows, None]).mean())
                       for s in SEEDS]
                rec = {"n_images": int(len(rows)),
                       "annotator_marginalized_macro_f1_3seed": round(float(np.mean(f1)), 5),
                       "sd_3seed": round(float(np.std(f1, ddof=1)), 5),
                       "expected_accuracy_3seed": round(float(np.mean(acc)), 5)}
                if st in CONTESTED or st == POOLED_CONTESTED:
                    rr = []
                    for s in SEEDS:
                        if np.unique(vent[rows]).size >= 2:
                            rr.append(spearmanr(pe[(cfg, s)][rows], vent[rows])[0])
                    rec["entropy_spearman_rho_3seed"] = (
                        round(float(np.mean(rr)), 5) if rr else None)
                row[st] = rec
            block[cfg] = row
        block["_mean_vote_entropy_by_stratum"] = {
            st: round(float(vent[stratum_mask(panel, st)].mean()), 5) for st in STRATA}
        results[sname] = block

    # ---- does the RQ2 verdict survive each drop? ----------------------------
    verdict_stability = {}
    if "C2" in cfgs and "C3" in cfgs:
        for sname, cols in subsets.items():
            Vs = V[:, cols]
            m = stratum_mask(panel, POOLED_CONTESTED)
            rows = np.where(m)[0]
            per = []
            for s in SEEDS:
                pa = panel[f"pred_C2_{s}"].to_numpy()
                pb = panel[f"pred_C3_{s}"].to_numpy()
                plug = 100 * (marg_f1_subset(Vs[rows], pa[rows], k)
                              - marg_f1_subset(Vs[rows], pb[rows], k))
                d = []
                for loc in patient_resamples(pat[rows], N_BOOT_LOAO):
                    r = rows[loc]
                    d.append(marg_f1_subset(Vs[r], pa[r], k) - marg_f1_subset(Vs[r], pb[r], k))
                per.append({"seed": s, "diff_points_plugin": round(float(plug), 3),
                            "ci95_points": [round(100 * x, 3) for x in ci95(np.asarray(d))]})
            lo = float(np.mean([p["ci95_points"][0] for p in per]))
            hi = float(np.mean([p["ci95_points"][1] for p in per]))
            verdict_stability[sname] = {
                "diff_points_3seed_mean": round(float(np.mean(
                    [p["diff_points_plugin"] for p in per])), 3),
                "ci95_points_3seed_mean": [round(lo, 3), round(hi, 3)],
                "verdict": verdict(lo, hi),
                "per_seed": per,
            }
            print(f"  RQ2 verdict under {sname} done", flush=True)

    base = verdict_stability.get("all4", {}).get("verdict")
    stable = (all(v["verdict"] == base for v in verdict_stability.values())
              if verdict_stability else None)

    out = {
        "generated": time.strftime("%Y-%m-%d %H:%M:%S"),
        "purpose": "leave-one-annotator-out sensitivity of the Phase 4 metrics and "
                   "of the RQ2 verdict",
        "motivation": pre["sensitivity_analyses"]["leave_one_annotator_out"]["motivation"],
        "what_varies": ("only the metric: marginalization, expected accuracy and vote "
                        "entropy are rebuilt from 3 annotator columns. The strata "
                        "remain defined by the full 4-annotator vote matrix and no "
                        "model is retrained."),
        "training_side_loao_not_executed":
            pre["sensitivity_analyses"]["leave_one_annotator_out"]["not_executed"],
        "annotators": ANNOTATORS,
        "configurations_evaluated": cfgs,
        "config_labels": {c: CONFIG_LABEL[c] for c in cfgs},
        "seeds": list(SEEDS),
        "partial_sweep": bool(tuple(SEEDS) != (1, 2, 3)),
        "n_boot": N_BOOT_LOAO, "boot_unit": "patient", "boot_seed": BOOT_SEED,
        "by_subset": results,
        "rq2_verdict_stability": verdict_stability,
        "rq2_verdict_invariant_to_dropping_any_single_annotator": stable,
        "runtime_sec": round(time.time() - t0, 1),
    }
    (REPORTS / "phase4_loao.json").write_text(json.dumps(out, indent=2), encoding="utf-8")

    print("\n--- annotator-marginalized macro F1 (%) on the pooled contested "
          "stratum, by LOAO subset ---")
    names = list(subsets)
    print(f"  {'config':6s}" + "".join(f"{nm:>13s}" for nm in names))
    for cfg in cfgs:
        print(f"  {cfg:6s}" + "".join(
            f"{100 * results[nm][cfg][POOLED_CONTESTED]['annotator_marginalized_macro_f1_3seed']:13.2f}"
            for nm in names))
    if verdict_stability:
        print("\n--- RQ2 (C2 - C3) verdict stability ------------------------------")
        for nm, v in verdict_stability.items():
            print(f"  {nm:14s} {v['diff_points_3seed_mean']:+7.2f} pts  "
                  f"CI [{v['ci95_points_3seed_mean'][0]:+.2f}, "
                  f"{v['ci95_points_3seed_mean'][1]:+.2f}]  {v['verdict']}")
        print(f"  invariant to dropping any single annotator: {stable}")
    print(f"done in {out['runtime_sec']}s")


if __name__ == "__main__":
    main()
