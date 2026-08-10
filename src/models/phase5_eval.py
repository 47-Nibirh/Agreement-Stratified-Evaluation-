"""
P5.6 / P5.7 -- the transfer endpoint (P5-A) and the out-of-protocol rejection
endpoint (P5-B), scored against the frozen pre-registration.

Verdicts are read off the pre-registered rules mechanically. Every interval is a
1,000-resample IMAGE-LEVEL bootstrap, which is a declared weakness (P5-DEV-3),
not an oversight: neither corpus ships a usable grouping key.

Outputs
  reports/phase5_transfer.json
  reports/phase5_rejection.json
Run:  python src/models/phase5_eval.py
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from phase5_common import (  # noqa: E402
    FORWARD, GASTRIC, N_BOOT, OTHER, REPORTS, RETRO, available_arms,
    binary_macro_f1, ci95, classes, collapse_vector, collapsed_pred,
    external_panel, ext_probs_path, halfwidth, image_resamples, int_probs_path,
    internal_panel, prereg)

TRANSFER = REPORTS / "phase5_transfer.json"
REJECTION = REPORTS / "phase5_rejection.json"

MAJORITY_FLOOR = 50.0  # pre-registered floor for P5-A


def main() -> int:
    t0 = time.time()
    pre = prereg()
    seeds = pre["arms"]["seeds"]
    arms = available_arms(seeds)
    if not arms:
        print("[P5.6] no arm has a complete set of external predictions yet.")
        return 1
    print(f"[P5.6] arms {arms} x seeds {seeds}")

    cv = collapse_vector()
    ext = external_panel()
    ext_truth = ext["collapsed_label"].to_numpy()
    ext_corpus = ext["corpus"].to_numpy()
    gastric_mask = np.isin(ext_truth, list(GASTRIC))
    oop_mask = ext_truth == OTHER

    inte = internal_panel()
    int_truth = inte["collapsed_label"].to_numpy()
    int_gastric = np.isin(int_truth, list(GASTRIC))

    print(f"[P5.6] external: {gastric_mask.sum():,} gastric, {oop_mask.sum():,} "
          f"out-of-protocol | internal comparator: {int_gastric.sum():,} gastric")

    # =====================================================================
    # P5-A  transfer
    # =====================================================================
    per_seed, ext_pred_cache = {}, {}
    for cfg in arms:
        per_seed[cfg] = {}
        for s in seeds:
            ep = np.load(ext_probs_path(cfg, s))["probs"]
            epred = collapsed_pred(ep, cv)
            ext_pred_cache[(cfg, s)] = (ep, epred)

            ip = np.load(int_probs_path(cfg, s))["probs"]
            ipred = collapsed_pred(ip, cv)

            ext_f1 = 100 * binary_macro_f1(ext_truth[gastric_mask],
                                           epred[gastric_mask])
            int_f1 = 100 * binary_macro_f1(int_truth[int_gastric],
                                           ipred[int_gastric])
            recog = float((epred[gastric_mask] != OTHER).mean())
            rec_rows = gastric_mask & (epred != OTHER)
            f1_recognised = (100 * binary_macro_f1(ext_truth[rec_rows],
                                                   epred[rec_rows])
                             if rec_rows.sum() > 10 else None)
            by_corpus = {}
            for c in sorted(set(ext_corpus)):
                m = gastric_mask & (ext_corpus == c)
                if m.sum() > 10:
                    by_corpus[c] = {
                        "n": int(m.sum()),
                        "macro_f1": round(100 * binary_macro_f1(ext_truth[m],
                                                                epred[m]), 3),
                        "n_retroflexion": int((ext_truth[m] == RETRO).sum()),
                    }
            per_seed[cfg][s] = {
                "external_macro_f1": round(ext_f1, 3),
                "internal_macro_f1": round(int_f1, 3),
                "drop_points": round(ext_f1 - int_f1, 3),
                "gastric_recognition_rate": round(recog, 5),
                "macro_f1_among_recognised": (round(f1_recognised, 3)
                                              if f1_recognised is not None else None),
                "by_corpus": by_corpus,
            }
            print(f"  {cfg} seed{s}: external {ext_f1:6.2f}  internal {int_f1:6.2f}  "
                  f"drop {ext_f1 - int_f1:+6.2f}  recognised {recog:.3f}")

    # ---- bootstrap on the 3-seed mean, shared resamples across seeds --------
    g_rows = np.where(gastric_mask)[0]
    agg = {}
    for cfg in arms:
        reps_ext, reps_drop = [], []
        int_mean = float(np.mean([per_seed[cfg][s]["internal_macro_f1"]
                                  for s in seeds]))
        preds = [ext_pred_cache[(cfg, s)][1][g_rows] for s in seeds]
        truth_g = ext_truth[g_rows]
        for loc in image_resamples(len(g_rows)):
            vals = [100 * binary_macro_f1(truth_g[loc], p[loc]) for p in preds]
            m = float(np.mean(vals))
            reps_ext.append(m)
            reps_drop.append(m - int_mean)
        ci_ext = ci95(np.asarray(reps_ext))
        ci_drop = ci95(np.asarray(reps_drop))
        ext_mean = float(np.mean([per_seed[cfg][s]["external_macro_f1"]
                                  for s in seeds]))
        hw = halfwidth(ci_ext)
        target = pre["precision_target"]["max_ci95_halfwidth_points"]
        underpowered = hw is not None and hw > target
        if underpowered:
            verdict = "UNDERPOWERED"
        elif ci_ext[0] is not None and ci_ext[0] > MAJORITY_FLOOR:
            verdict = "TRANSFERS"
        else:
            verdict = "DOES NOT TRANSFER"
        agg[cfg] = {
            "external_macro_f1_mean_3seed": round(ext_mean, 3),
            "external_ci95": [round(x, 3) for x in ci_ext],
            "ci95_halfwidth_points": round(hw, 3) if hw is not None else None,
            "precision_target_points": target,
            "meets_precision_target": (not underpowered) if hw is not None else None,
            "internal_macro_f1_mean_3seed": round(int_mean, 3),
            "drop_points": round(ext_mean - int_mean, 3),
            "drop_ci95": [round(x, 3) for x in ci_drop],
            "gastric_recognition_rate_mean": round(float(np.mean(
                [per_seed[cfg][s]["gastric_recognition_rate"] for s in seeds])), 5),
            "verdict": verdict,
        }
        print(f"  {cfg}: external {ext_mean:.2f} CI {ci_ext} | drop "
              f"{ext_mean - int_mean:+.2f} | {verdict}")

    head = pre["arms"]["headline_arm"]
    exp_drop = -10.0
    out_a = {
        "generated": time.strftime("%Y-%m-%d %H:%M:%S"),
        "phase": 5, "step": "P5.6",
        "endpoint": pre["research_questions"]["P5-A"]["primary_endpoint"],
        "verdict_rule": pre["research_questions"]["P5-A"]["verdict_rule"],
        "majority_class_floor": MAJORITY_FLOOR,
        "n_gastric_external": int(gastric_mask.sum()),
        "n_retroflexion": int((ext_truth == RETRO).sum()),
        "n_forward": int((ext_truth == FORWARD).sum()),
        "n_gastric_internal_comparator": int(int_gastric.sum()),
        "n_boot": N_BOOT, "boot_unit": "image",
        "boot_unit_caveat": pre["interval_procedure"]["declared_weakness"],
        "arms": arms, "seeds": seeds,
        "per_seed": per_seed,
        "aggregate_3seed": agg,
        "headline_arm": head,
        "verdict": agg[head]["verdict"] if head in agg else None,
        "pre_registered_expected_drop_points": exp_drop,
        "expected_drop_realised": (
            agg[head]["drop_points"] < exp_drop if head in agg else None),
        "runtime_sec": round(time.time() - t0, 1),
    }
    TRANSFER.write_text(json.dumps(out_a, indent=1), encoding="utf-8")
    print(f"[P5.6] wrote {TRANSFER}")

    # =====================================================================
    # P5-B  out-of-protocol rejection
    # =====================================================================
    t1 = time.time()
    chance = pre["research_questions"]["P5-B"]["chance_rate"]
    cls_inv = {v: k for k, v in classes().items()}
    o_rows = np.where(oop_mask)[0]
    rej_seed, rej_agg = {}, {}
    for cfg in arms:
        rej_seed[cfg] = {}
        for s in seeds:
            ep, epred = ext_pred_cache[(cfg, s)]
            sel = epred[o_rows] == OTHER
            conf = ep[o_rows].max(1)
            asserted = ep[o_rows].argmax(1)
            top = np.bincount(asserted, minlength=len(cls_inv)).argmax()
            rej_seed[cfg][s] = {
                "rejection_rate": round(float(sel.mean()), 5),
                "mean_top1_confidence": round(float(conf.mean()), 5),
                "mean_top1_confidence_when_not_rejected": round(
                    float(conf[~sel].mean()), 5) if (~sel).any() else None,
                "most_asserted_class": cls_inv[int(top)],
            }
        rates = [rej_seed[cfg][s]["rejection_rate"] for s in seeds]
        preds = [ext_pred_cache[(cfg, s)][1][o_rows] for s in seeds]
        reps = []
        for loc in image_resamples(len(o_rows)):
            reps.append(float(np.mean([(p[loc] == OTHER).mean() for p in preds])))
        ci = ci95(np.asarray(reps))
        verdict = ("REJECTS OUT-OF-PROTOCOL IMAGES" if ci[0] is not None
                   and ci[0] > chance else "DOES NOT REJECT")
        rej_agg[cfg] = {
            "rejection_rate_mean_3seed": round(float(np.mean(rates)), 5),
            "ci95": [round(x, 5) for x in ci],
            "chance_rate": chance,
            "exceeds_chance": bool(ci[0] is not None and ci[0] > chance),
            "mean_top1_confidence_mean_3seed": round(float(np.mean(
                [rej_seed[cfg][s]["mean_top1_confidence"] for s in seeds])), 5),
            "verdict": verdict,
        }
        print(f"  {cfg}: rejection {np.mean(rates):.4f} CI {ci} "
              f"(chance {chance:.4f}) conf "
              f"{rej_agg[cfg]['mean_top1_confidence_mean_3seed']:.4f} -> {verdict}")

    out_b = {
        "generated": time.strftime("%Y-%m-%d %H:%M:%S"),
        "phase": 5, "step": "P5.7",
        "endpoint": pre["research_questions"]["P5-B"]["primary_endpoint"],
        "verdict_rule": pre["research_questions"]["P5-B"]["verdict_rule"],
        "hypothesis": pre["research_questions"]["P5-B"]["hypothesis"],
        "n_out_of_protocol": int(oop_mask.sum()),
        "chance_rate": chance,
        "n_boot": N_BOOT, "boot_unit": "image",
        "boot_unit_caveat": pre["interval_procedure"]["declared_weakness"],
        "arms": arms, "seeds": seeds,
        "per_seed": rej_seed,
        "aggregate_3seed": rej_agg,
        "headline_arm": head,
        "verdict": rej_agg[head]["verdict"] if head in rej_agg else None,
        "hypothesis_supported": (
            not rej_agg[head]["exceeds_chance"] if head in rej_agg else None),
        "runtime_sec": round(time.time() - t1, 1),
    }
    REJECTION.write_text(json.dumps(out_b, indent=1), encoding="utf-8")
    print(f"[P5.7] wrote {REJECTION}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
