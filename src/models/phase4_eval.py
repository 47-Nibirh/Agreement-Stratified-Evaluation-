"""
Phase 4 / Stage G -- agreement-stratified evaluation and the pre-registered
configuration contrasts (RQ2 primary endpoint).

Every configuration is scored on the full 1,353-image official test split with
the Phase 3 metric set, stratum by stratum, plus one pooled contested stratum
(S-majority + S-plurality + S-no-majority, n=550) which the pre-registration
names as the single primary endpoint for RQ2.

Two scales are reported, exactly as the Phase 3 carry-forward decision requires:

  raw                the annotator-marginalized macro F1 itself
  ceiling-normalised the same quantity divided by the modal-vote oracle's score
                     on that stratum, i.e. the percentage of what any
                     single-label predictor could attain there

A note on which scale the CONTRASTS use. Ceiling normalisation was necessary in
Phase 3 because that phase compared different STRATA, whose attainable maxima
differ (100.0 / 74.2 / 44.6 / 40.2). This phase compares different
CONFIGURATIONS within the same stratum, where the ceiling is one and the same
positive number for both arms and therefore divides out of the difference. A
ceiling-normalised contrast is the raw contrast multiplied by 1/ceiling > 0, so
it cannot change a sign, a zero-crossing, or a verdict. The contrasts are
consequently reported on the raw scale, with the normalised per-configuration
levels tabulated alongside; this is a saving in computation, not in rigour, and
the identity is asserted numerically in the output.

All configuration contrasts use the PAIRED patient-clustered bootstrap of
phase4_common: one patient resample, both arms scored on those same rows, then
differenced.

Outputs
  reports/phase4_stratified_metrics.json
Run:  python src/models/phase4_eval.py
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from phase4_common import (  # noqa: E402
    ANN_COLS, BOOT_SEED, CONFIGS, CONFIG_LABEL, N_BOOT_P4, N_BOOT_PAIR,
    POOLED_CONTESTED, REPORTS, SEEDS, STRATA, TIER_ORDER, any_hit_rate, available_configs,
    build_panel, ci95, classes, expected_accuracy, macro_f1,
    marginalized_macro_f1, max_expected_accuracy, modal_oracle,
    paired_bootstrap, patient_resamples, prereg, stratum_mask, verdict,
    votes_to_idx)

N_TIE = 200

# (treatment, control, what the contrast isolates)
CONTRASTS = [
    ("C1", "C0", "cohort effect: adding the 3/4 contested images at a hard target"),
    ("C2", "C1", "softening the target on the images where annotators disagreed"),
    ("C2", "C3", "PRIMARY RQ2: targeted softening vs equally-soft generic smoothing"),
    ("C3", "C1", "generic regularisation alone"),
    ("C4", "C2", "PRIMARY RQ4: the anatomical structured penalty"),
    ("C4", "C1", "soft targets and the anatomical penalty together"),
]


def main() -> None:
    t0 = time.time()
    cls = classes()
    k = len(cls)
    pre = prereg()
    cfgs = available_configs()
    panel, meta = build_panel(cfgs)
    V = votes_to_idx(panel, cls)
    pat = panel.patient.to_numpy()

    def f1_of(cfg, seed):
        p = panel[f"pred_{cfg}_{seed}"].to_numpy()
        return lambda rows: marginalized_macro_f1(V[rows], p[rows], k)

    # ---- attainable ceiling per stratum (model-independent) -----------------
    ceilings = {}
    for st in STRATA:
        m = stratum_mask(panel, st)
        Vs = V[m]
        rng = np.random.default_rng(BOOT_SEED)
        f1s = [marginalized_macro_f1(Vs, modal_oracle(Vs, rng), k) for _ in range(N_TIE)]
        ceilings[st] = {
            "n_images": int(m.sum()),
            "n_patients": int(len(np.unique(pat[m]))),
            "oracle_marginalized_macro_f1_mean": round(float(np.mean(f1s)), 5),
            "oracle_marginalized_macro_f1_sd_over_tiebreaks": round(float(np.std(f1s, ddof=1)), 5),
            "max_expected_accuracy_exact": round(max_expected_accuracy(Vs), 5),
        }

    # ---- per configuration, per seed, per stratum ---------------------------
    per_seed = {}
    for cfg in cfgs:
        per_seed[cfg] = {}
        for s in SEEDS:
            pred = panel[f"pred_{cfg}_{s}"].to_numpy()
            entry = {}
            for st in STRATA:
                m = stratum_mask(panel, st)
                rows = np.where(m)[0]
                Vs, ps = V[rows], pred[rows]
                marg = marginalized_macro_f1(Vs, ps, k)
                e = {
                    "n_images": int(len(rows)),
                    "annotator_marginalized_macro_f1": round(marg, 5),
                    "ceiling_normalised_macro_f1": round(
                        marg / ceilings[st]["oracle_marginalized_macro_f1_mean"], 5),
                    "expected_accuracy": round(expected_accuracy(Vs, ps), 5),
                    "any_annotator_hit_rate": round(any_hit_rate(Vs, ps), 5),
                }
                sub = panel.iloc[rows]
                if sub.pseudo_label.notna().all():
                    y = sub.pseudo_label.map(cls).to_numpy()
                    e["single_label_macro_f1"] = round(macro_f1(y, ps, k), 5)
                    e["single_label_accuracy"] = round(float((y == ps).mean()), 5)
                fn = f1_of(cfg, s)
                bs = np.array([fn(rows[loc]) for loc in
                               patient_resamples(pat[rows], N_BOOT_P4)])
                e["annotator_marginalized_macro_f1_ci95"] = [round(x, 5) for x in ci95(bs)]
                entry[st] = e
            per_seed[cfg][s] = entry

    # ---- 3-seed aggregate ---------------------------------------------------
    aggregate = {}
    for cfg in cfgs:
        aggregate[cfg] = {}
        for st in STRATA:
            vals = np.array([per_seed[cfg][s][st]["annotator_marginalized_macro_f1"]
                             for s in SEEDS])
            a = {
                "n_images": per_seed[cfg][SEEDS[0]][st]["n_images"],
                "n_patients": ceilings[st]["n_patients"],
                "annotator_marginalized_macro_f1_mean_3seed": round(float(vals.mean()), 5),
                "annotator_marginalized_macro_f1_sd_3seed": round(float(vals.std(ddof=1)), 5),
                "ceiling_normalised_macro_f1_mean_3seed": round(float(np.mean(
                    [per_seed[cfg][s][st]["ceiling_normalised_macro_f1"] for s in SEEDS])), 5),
                "expected_accuracy_mean_3seed": round(float(np.mean(
                    [per_seed[cfg][s][st]["expected_accuracy"] for s in SEEDS])), 5),
                "any_annotator_hit_rate_mean_3seed": round(float(np.mean(
                    [per_seed[cfg][s][st]["any_annotator_hit_rate"] for s in SEEDS])), 5),
                "ci95_mean_of_per_seed_bounds": [
                    round(float(np.mean([per_seed[cfg][s][st]
                                         ["annotator_marginalized_macro_f1_ci95"][i]
                                         for s in SEEDS])), 5) for i in (0, 1)],
            }
            if "single_label_macro_f1" in per_seed[cfg][SEEDS[0]][st]:
                a["single_label_macro_f1_mean_3seed"] = round(float(np.mean(
                    [per_seed[cfg][s][st]["single_label_macro_f1"] for s in SEEDS])), 5)
            aggregate[cfg][st] = a

    # ---- paired configuration contrasts ------------------------------------
    contrasts = {}
    for tre, con, what in CONTRASTS:
        if tre not in cfgs or con not in cfgs:
            continue
        contrasts[f"{tre} - {con}"] = {"isolates": what, "by_stratum": {}}
        for st in STRATA:
            m = stratum_mask(panel, st)
            per = []
            for s in SEEDS:
                d = paired_bootstrap(panel, m, f1_of(tre, s), f1_of(con, s),
                                     n_boot=N_BOOT_PAIR)
                rows = np.where(m)[0]
                plug = 100 * (f1_of(tre, s)(rows) - f1_of(con, s)(rows))
                per.append({"seed": s,
                            "diff_points_plugin": round(float(plug), 3),
                            "diff_points_boot_mean": round(100 * float(d.mean()), 3),
                            "ci95_points": [round(100 * x, 3) for x in ci95(d)]})
            lo = float(np.mean([p["ci95_points"][0] for p in per]))
            hi = float(np.mean([p["ci95_points"][1] for p in per]))
            pt = float(np.mean([p["diff_points_plugin"] for p in per]))
            signs = {int(np.sign(p["diff_points_plugin"])) for p in per}
            contrasts[f"{tre} - {con}"]["by_stratum"][st] = {
                "diff_points_3seed_mean": round(pt, 3),
                "ci95_points_3seed_mean": [round(lo, 3), round(hi, 3)],
                "excludes_zero": bool(lo > 0 or hi < 0),
                "sign_consistent_across_seeds": len(signs) == 1,
                "per_seed": per,
                "ceiling_normalised_diff_points": round(
                    pt / ceilings[st]["oracle_marginalized_macro_f1_mean"], 3),
            }
        print(f"  contrast {tre} - {con} done", flush=True)

    # ---- GATE P4.7: the C0 arm must reproduce Phase 3 exactly ---------------
    # C0 is not retrained here, so its stratified scores are Phase 3's scores.
    # If they differed at all, the panel would be mis-joined or the metric
    # primitives would have drifted, and every contrast built on C0 would be
    # meaningless. Checked before any verdict is issued.
    # Compared PER SEED, not on the seed mean: a per-seed identity is the
    # stricter statement, and it stays valid when the sweep is run on a subset
    # of seeds (a 1-seed mean could never equal a 3-seed mean, which would make
    # a mean-based gate fire spuriously on a partial run).
    gate_c0 = {"checked": False}
    p3f = REPORTS / "phase3_stratified_metrics.json"
    if "C0" in cfgs and p3f.exists():
        p3 = json.loads(p3f.read_text(encoding="utf-8"))["per_seed_stratum"]
        dev = {}
        for s in SEEDS:
            for st in TIER_ORDER:
                dev[f"seed{s}/{st}"] = abs(
                    p3[str(s)][st]["annotator_marginalized_macro_f1"]
                    - per_seed["C0"][s][st]["annotator_marginalized_macro_f1"])
        worst = max(dev.values())
        if worst > 1e-9:
            raise SystemExit(f"GATE P4.7 FAILED: C0 differs from Phase 3 by {worst:.2e} "
                             f"({dev})")
        gate_c0 = {"checked": True, "pass": True,
                   "comparison": "per seed and per stratum, against "
                                 "phase3_stratified_metrics.json per_seed_stratum",
                   "max_abs_deviation_from_phase3": float(worst),
                   "n_comparisons": len(dev),
                   "note": ("the C0 rows of this table are literally the Phase 3 "
                            "numbers, recomputed through the Phase 4 code path")}

    # ---- pre-registered verdicts -------------------------------------------
    verdicts = {}
    key = "C2 - C3"
    if key in contrasts:
        c = contrasts[key]["by_stratum"][POOLED_CONTESTED]
        verdicts["RQ2_primary"] = {
            "endpoint": pre["research_questions"]["RQ2"]["primary_endpoint"],
            "contrast": key,
            "stratum": POOLED_CONTESTED,
            "diff_points": c["diff_points_3seed_mean"],
            "ci95_points": c["ci95_points_3seed_mean"],
            "verdict": verdict(*c["ci95_points_3seed_mean"]),
            "rule": pre["research_questions"]["RQ2"]["verdict_rule"],
        }
        verdicts["RQ2_by_stratum"] = {
            st: {"diff_points": contrasts[key]["by_stratum"][st]["diff_points_3seed_mean"],
                 "ci95_points": contrasts[key]["by_stratum"][st]["ci95_points_3seed_mean"],
                 "verdict": verdict(*contrasts[key]["by_stratum"][st]["ci95_points_3seed_mean"])}
            for st in STRATA}
    if "C2 - C1" in contrasts:
        c = contrasts["C2 - C1"]["by_stratum"]["S-unanimous"]
        verdicts["RQ2_parity_on_unanimous"] = {
            "endpoint": "C2 - C1 on S-unanimous; the hypothesis predicts PARITY, so "
                        "an interval containing zero is the predicted outcome",
            "diff_points": c["diff_points_3seed_mean"],
            "ci95_points": c["ci95_points_3seed_mean"],
            "parity_holds": bool(not c["excludes_zero"]),
        }
    if "C4 - C2" in contrasts:
        c = contrasts["C4 - C2"]["by_stratum"][POOLED_CONTESTED]
        verdicts["RQ4_macro_f1_side_condition"] = {
            "endpoint": "C4 - C2 macro F1 on the pooled contested stratum; the RQ4 "
                        "rule requires that this does NOT exclude zero from below",
            "diff_points": c["diff_points_3seed_mean"],
            "ci95_points": c["ci95_points_3seed_mean"],
            "accuracy_preserved": bool(c["ci95_points_3seed_mean"][1] >= 0),
            "note": "the RQ4 primary endpoint is the anatomical error distance, "
                    "computed in phase4_structure_eval.py",
        }

    out = {
        "generated": time.strftime("%Y-%m-%d %H:%M:%S"),
        "purpose": "agreement-stratified evaluation of the Phase 4 configurations "
                   "and the pre-registered paired contrasts",
        "configurations_evaluated": cfgs,
        "configurations_missing": [c for c in CONFIGS if c not in cfgs],
        "config_labels": {c: CONFIG_LABEL[c] for c in cfgs},
        "seeds": list(SEEDS),
        "partial_sweep": bool(tuple(SEEDS) != (1, 2, 3)),
        "strata": STRATA,
        "pooled_contested_definition": "S-majority + S-plurality + S-no-majority",
        "n_boot_per_stratum": N_BOOT_P4,
        "n_boot_paired": N_BOOT_PAIR,
        "boot_unit": "patient", "boot_seed": BOOT_SEED,
        "scale_note": (
            "configuration contrasts are reported on the raw scale. Within a "
            "stratum the attainable ceiling is a single positive constant shared by "
            "both arms, so ceiling normalisation rescales the difference by "
            "1/ceiling and cannot change its sign or whether its interval contains "
            "zero. Ceiling-normalised LEVELS are tabulated per configuration."),
        "gate_p4_7_c0_reproduces_phase3": gate_c0,
        "ceilings": ceilings,
        "per_seed": per_seed,
        "aggregate_3seed": aggregate,
        "contrasts": contrasts,
        "verdicts": verdicts,
        "runtime_sec": round(time.time() - t0, 1),
    }
    (REPORTS / "phase4_stratified_metrics.json").write_text(
        json.dumps(out, indent=2), encoding="utf-8")

    print("\n--- annotator-marginalized macro F1 (%), 3-seed mean --------------")
    hdr = f"  {'config':6s}" + "".join(f"{st.replace('S-', '')[:11]:>13s}" for st in STRATA)
    print(hdr)
    for cfg in cfgs:
        print(f"  {cfg:6s}" + "".join(
            f"{100 * aggregate[cfg][st]['annotator_marginalized_macro_f1_mean_3seed']:13.2f}"
            for st in STRATA))
    print("\n--- paired contrasts on the pooled contested stratum (points) -----")
    for kk, v in contrasts.items():
        c = v["by_stratum"][POOLED_CONTESTED]
        print(f"  {kk:10s} {c['diff_points_3seed_mean']:+7.2f}  "
              f"CI [{c['ci95_points_3seed_mean'][0]:+.2f}, {c['ci95_points_3seed_mean'][1]:+.2f}]  "
              f"excl.0={c['excludes_zero']}")
    if "RQ2_primary" in verdicts:
        print(f"\n  RQ2 PRIMARY VERDICT: {verdicts['RQ2_primary']['verdict']}")
    print(f"done in {out['runtime_sec']}s")


if __name__ == "__main__":
    main()
