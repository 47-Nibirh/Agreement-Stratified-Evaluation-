"""
Phase 4 / Stage H -- calibration by configuration and agreement stratum.

Phase 3's principal finding was not an accuracy failure but a calibration
failure: the frozen baseline's expected calibration error rose from 9.15% on
unanimous images to 56.40% on 2-1-1 images, with mean confidence falling only
9.34 points while expected accuracy fell 56.57. The Phase 3 carry-forward
decision therefore promoted calibration to a PRIMARY Phase 4 endpoint, and
that is how it is treated here.

Definitions are inherited verbatim from phase3b_calibration.py so the numbers
are comparable across phases:

  target      expected accuracy = the probability mass the model's single
              prediction captures under the empirical 4-vote distribution. It
              is the only target defined on every stratum, and it is the honest
              target for a confidence score: claiming 0.95 on an image where
              two of four experts would disagree is overconfident by
              construction.
  ECE / MCE   10 equal-width bins on the top-1 probability.
  Brier       reported twice. `brier_top1` is Phase 3B's quantity, the squared
              error of the top-1 probability against expected accuracy.
              `brier_vector` is the full 23-dimensional Brier score against the
              vote distribution, ||p - t||^2, which is the stricter and more
              standard multi-class form and is added here because Phase 4's
              treatment arms are trained on exactly that vote distribution.

The C2-vs-C3 contrast is the pre-registered calibration verdict: label
smoothing is itself a calibration intervention, so beating C1 would prove
little. Contrasts use the paired patient-clustered bootstrap.

Outputs
  reports/phase4_calibration.json
Run:  python src/models/phase4_calibration.py
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from phase4_common import (  # noqa: E402
    BOOT_SEED, CONFIG_LABEL, POOLED_CONTESTED, REPORTS, SEEDS, STRATA,
    available_configs, build_panel, ci95, classes, paired_bootstrap,
    patient_resamples, prereg, probs_path, stratum_mask, verdict, votes_to_idx)

N_BINS = 10
N_BOOT_CAL = 1000  # pre-registered minimum; see phase4_common.N_BOOT_PAIR


def binned(conf, target, n_bins=N_BINS):
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


def ece_mce(conf, target, n_bins=N_BINS):
    n = len(conf)
    if n == 0:
        return float("nan"), float("nan")
    e = mx = 0.0
    for r in binned(conf, target, n_bins):
        if r["n"]:
            d = abs(r["mean_target"] - r["mean_confidence"])
            e += r["n"] / n * d
            mx = max(mx, d)
    return e, mx


def main() -> None:
    t0 = time.time()
    cls = classes()
    k = len(cls)
    pre = prereg()
    cfgs = available_configs()
    panel, _ = build_panel(cfgs)
    V = votes_to_idx(panel, cls)
    pat = panel.patient.to_numpy()
    n = len(panel)

    # vote distribution as a (n, k) target, and per-image expected accuracy
    Tv = np.zeros((n, k), dtype=np.float64)
    for a in range(V.shape[1]):
        Tv[np.arange(n), V[:, a]] += 0.25

    store = {}
    for cfg in cfgs:
        for s in SEEDS:
            blob = np.load(probs_path(cfg, s), allow_pickle=True)
            P = blob["probs"].astype(np.float64)
            if list(blob["filename"]) != list(panel.filename):
                raise SystemExit(f"{cfg} seed{s}: probability row order differs from the panel")
            pred = panel[f"pred_{cfg}_{s}"].to_numpy()
            if int((P.argmax(1) != pred).sum()):
                raise SystemExit(f"{cfg} seed{s}: probability argmax disagrees with y_pred")
            store[(cfg, s)] = {
                "conf": P.max(1),
                "exp_acc": (V == pred[:, None]).mean(axis=1),
                "brier_vec": ((P - Tv) ** 2).sum(1),
            }

    def ece_of(cfg, s):
        d = store[(cfg, s)]
        return lambda rows: ece_mce(d["conf"][rows], d["exp_acc"][rows])[0]

    # ---- per configuration, per seed, per stratum ---------------------------
    per_seed = {}
    for cfg in cfgs:
        per_seed[cfg] = {}
        for s in SEEDS:
            d = store[(cfg, s)]
            entry = {}
            for st in STRATA:
                rows = np.where(stratum_mask(panel, st))[0]
                conf, exp = d["conf"][rows], d["exp_acc"][rows]
                e, m = ece_mce(conf, exp)
                sub = panel.iloc[rows]
                rec = {
                    "n_images": int(len(rows)),
                    "mean_confidence": round(float(conf.mean()), 5),
                    "expected_accuracy": round(float(exp.mean()), 5),
                    "overconfidence_points": round(100 * float(conf.mean() - exp.mean()), 3),
                    "ece_vs_expected_accuracy": round(e, 5),
                    "mce_vs_expected_accuracy": round(m, 5),
                    "brier_top1_vs_expected_accuracy": round(float(((conf - exp) ** 2).mean()), 5),
                    "brier_vector_vs_vote_distribution": round(
                        float(d["brier_vec"][rows].mean()), 5),
                    "reliability_bins_vs_expected_accuracy": binned(conf, exp),
                }
                if sub.pseudo_label.notna().all():
                    hard = (sub.pseudo_label.map(cls).to_numpy()
                            == panel[f"pred_{cfg}_{s}"].to_numpy()[rows]).astype(float)
                    eh, mh = ece_mce(conf, hard)
                    rec.update({"hard_label_accuracy": round(float(hard.mean()), 5),
                                "ece_vs_hard_label": round(eh, 5),
                                "mce_vs_hard_label": round(mh, 5),
                                "reliability_bins_vs_hard_label": binned(conf, hard)})
                entry[st] = rec
            per_seed[cfg][s] = entry

    # ---- 3-seed aggregate + per-stratum ECE interval ------------------------
    aggregate = {}
    for cfg in cfgs:
        aggregate[cfg] = {}
        for st in STRATA:
            keys = ("mean_confidence", "expected_accuracy", "overconfidence_points",
                    "ece_vs_expected_accuracy", "mce_vs_expected_accuracy",
                    "brier_top1_vs_expected_accuracy",
                    "brier_vector_vs_vote_distribution")
            vals = {kk: [per_seed[cfg][s][st][kk] for s in SEEDS] for kk in keys}
            a = {kk: round(float(np.mean(v)), 5) for kk, v in vals.items()}
            a["n_images"] = per_seed[cfg][SEEDS[0]][st]["n_images"]
            a["ece_sd_across_seeds"] = round(
                float(np.std(vals["ece_vs_expected_accuracy"], ddof=1)), 5)
            rows = np.where(stratum_mask(panel, st))[0]
            bs = np.array([ece_of(cfg, SEEDS[0])(rows[loc]) for loc in
                           patient_resamples(pat[rows], N_BOOT_CAL)])
            a["ece_ci95_seed1"] = [round(x, 5) for x in ci95(bs)]
            aggregate[cfg][st] = a

    # ---- paired calibration contrasts ---------------------------------------
    PAIRS = [("C2", "C3"), ("C2", "C1"), ("C3", "C1"), ("C1", "C0"), ("C4", "C2")]
    contrasts = {}
    for tre, con in PAIRS:
        if tre not in cfgs or con not in cfgs:
            continue
        contrasts[f"{tre} - {con}"] = {}
        for st in STRATA:
            m = stratum_mask(panel, st)
            per = []
            for s in SEEDS:
                d = paired_bootstrap(panel, m, ece_of(tre, s), ece_of(con, s),
                                     n_boot=N_BOOT_CAL)
                rows = np.where(m)[0]
                plug = 100 * (ece_of(tre, s)(rows) - ece_of(con, s)(rows))
                per.append({"seed": s, "delta_ece_points_plugin": round(float(plug), 3),
                            "ci95_points": [round(100 * x, 3) for x in ci95(d)]})
            lo = float(np.mean([p["ci95_points"][0] for p in per]))
            hi = float(np.mean([p["ci95_points"][1] for p in per]))
            pt = float(np.mean([p["delta_ece_points_plugin"] for p in per]))
            contrasts[f"{tre} - {con}"][st] = {
                "delta_ece_points_3seed_mean": round(pt, 3),
                "ci95_points_3seed_mean": [round(lo, 3), round(hi, 3)],
                "excludes_zero": bool(lo > 0 or hi < 0),
                "better_calibrated": bool(hi < 0),
                "sign_consistent_across_seeds": len(
                    {int(np.sign(p["delta_ece_points_plugin"])) for p in per}) == 1,
                "per_seed": per,
            }
        print(f"  calibration contrast {tre} - {con} done", flush=True)

    verdicts = {}
    if "C2 - C3" in contrasts:
        c = contrasts["C2 - C3"][POOLED_CONTESTED]
        verdicts["RQ2_calibration"] = {
            "contrast": "C2 - C3", "stratum": POOLED_CONTESTED,
            "delta_ece_points": c["delta_ece_points_3seed_mean"],
            "ci95_points": c["ci95_points_3seed_mean"],
            "verdict": verdict(*c["ci95_points_3seed_mean"], favour_negative=True),
            "rule": pre["research_questions"]["RQ2"]["calibration_verdict_rule"],
        }

    out = {
        "generated": time.strftime("%Y-%m-%d %H:%M:%S"),
        "purpose": "calibration by configuration and agreement stratum; RQ2's "
                   "pre-registered calibration endpoint",
        "definitions_inherited_from": "src/models/phase3b_calibration.py",
        "configurations_evaluated": cfgs,
        "config_labels": {c: CONFIG_LABEL[c] for c in cfgs},
        "n_bins": N_BINS, "n_boot": N_BOOT_CAL, "boot_unit": "patient",
        "boot_seed": BOOT_SEED, "seeds": list(SEEDS),
        "partial_sweep": bool(tuple(SEEDS) != (1, 2, 3)),
        "primary_target": "expected accuracy under the 4-annotator vote distribution",
        "per_seed": per_seed,
        "aggregate_3seed": aggregate,
        "contrasts": contrasts,
        "verdicts": verdicts,
        "headline": {
            "ece_by_config_and_stratum_pct": {
                c: {st: round(100 * aggregate[c][st]["ece_vs_expected_accuracy"], 2)
                    for st in STRATA} for c in cfgs},
            "overconfidence_points_by_config_and_stratum": {
                c: {st: aggregate[c][st]["overconfidence_points"] for st in STRATA}
                for c in cfgs},
        },
        "runtime_sec": round(time.time() - t0, 1),
    }
    (REPORTS / "phase4_calibration.json").write_text(json.dumps(out, indent=2),
                                                     encoding="utf-8")

    print("\n--- ECE (%) vs expected accuracy, 3-seed mean ---------------------")
    print(f"  {'config':6s}" + "".join(f"{st.replace('S-', '')[:11]:>13s}" for st in STRATA))
    for c in cfgs:
        print(f"  {c:6s}" + "".join(
            f"{100 * aggregate[c][st]['ece_vs_expected_accuracy']:13.2f}" for st in STRATA))
    if verdicts:
        v = verdicts["RQ2_calibration"]
        print(f"\n  RQ2 calibration verdict ({v['contrast']} on {v['stratum']}): "
              f"{v['verdict']}  dECE = {v['delta_ece_points']:+.2f} pts "
              f"CI {v['ci95_points']}")
    print(f"done in {out['runtime_sec']}s")


if __name__ == "__main__":
    main()
