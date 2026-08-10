"""
Phase 3B / Stage D -- per-class behaviour across strata, per-stratum confusion
matrices, and the class-composition control.

Restores blueprint sec.14 §3.6 and Appendices A and B, and adds the confound
check the original Phase 3 needed but did not run.

Three things are computed.

1. PER-CLASS, PER-STRATUM METRICS (§3.6, Appendix A).  The delivered
   Appendix A was titled "Full per-class, per-stratum metric tables" but
   contained four tier-level summary lines and no per-class number at all.
   Here: annotator-marginalized per-class F1, support, and predicted count
   for all 23 classes x 4 tiers x 3 seeds.

2. PER-STRATUM CONFUSION MATRICES (Appendix B).  23x23, built against each
   annotator in turn and averaged, so they are defined on the tiers with no
   single ground truth as well.

3. CLASS-COMPOSITION CONTROL (new, post-hoc, declared as such).  The tiers do
   not contain the same mix of classes -- Phase 0 showed disagreement
   concentrates on particular anatomical boundaries -- so "performance drops
   with agreement" could in principle be "performance drops because contested
   tiers over-represent classes the model was already bad at". The control
   re-weights the model's *S-unanimous* per-class accuracy by each contested
   tier's own class mix, giving the expected accuracy that class composition
   alone would predict. The residual is the part of the drop that class mix
   cannot explain.

Also reports the zero-support diagnostic: how many of the 23 classes are
absent from a tier and therefore enter the macro average as a hard 0. This
is the mechanical-deflation objection to the primary metric, and it is
quantified here rather than assumed either way.

Outputs
  reports/phase3b_perclass.json
  reports/phase3b_confusion_matrices.npz
Run:  python src/models/phase3b_perclass.py
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from phase3b_common import TIER_ORDER, macro_f1, marginalized_macro_f1, votes_to_idx  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
REPORTS = ROOT / "reports"
CLASS_INDEX = ROOT / "data" / "phase2_class_index.json"
SEEDS = (1, 2, 3)


def per_class_f1(y: np.ndarray, p: np.ndarray, k: int) -> np.ndarray:
    tp = np.bincount(y[y == p], minlength=k)
    nt = np.bincount(y, minlength=k)
    npd = np.bincount(p, minlength=k)
    den = nt + npd
    f1 = np.zeros(k)
    nz = den > 0
    f1[nz] = 2.0 * tp[nz] / den[nz]
    return f1


def main() -> None:
    t0 = time.time()
    cls = json.load(open(CLASS_INDEX, encoding="utf-8"))
    k = len(cls)
    names = sorted(cls, key=cls.get)
    dfs = {s: pd.read_csv(REPORTS / f"phase3_predictions_seed{s}.csv") for s in SEEDS}

    # ---- 1 + 2: per-class metrics and confusion matrices --------------------
    per_class, mats = {}, {}
    for tier in TIER_ORDER:
        f1_stack, sup_stack, pred_stack = [], [], []
        cm_stack = []
        for s in SEEDS:
            g = dfs[s][dfs[s].tier_pooled == tier]
            V = votes_to_idx(g, cls)
            p = g.y_pred.to_numpy()
            f1_stack.append(np.mean([per_class_f1(V[:, a], p, k) for a in range(4)], axis=0))
            sup_stack.append(np.mean([np.bincount(V[:, a], minlength=k) for a in range(4)], axis=0))
            pred_stack.append(np.bincount(p, minlength=k))
            cm = np.zeros((k, k))
            for a in range(4):
                np.add.at(cm, (V[:, a], p), 0.25)
            cm_stack.append(cm)
        f1m = np.mean(f1_stack, axis=0)
        supm = np.mean(sup_stack, axis=0)
        predm = np.mean(pred_stack, axis=0)
        mats[tier] = np.mean(cm_stack, axis=0)

        absent = [names[i] for i in range(k) if supm[i] == 0 and predm[i] == 0]
        per_class[tier] = {
            "n_images": int((dfs[SEEDS[0]].tier_pooled == tier).sum()),
            "classes": names,
            "marginalized_per_class_f1_3seed": [round(float(v), 5) for v in f1m],
            "mean_annotator_support_3seed": [round(float(v), 3) for v in supm],
            "mean_predicted_count_3seed": [round(float(v), 3) for v in predm],
            "n_classes_with_zero_support_and_zero_prediction": len(absent),
            "zero_support_classes": absent,
            "macro_f1_all_23_classes": round(float(f1m.mean()), 5),
            "macro_f1_present_classes_only": round(float(
                f1m[[i for i in range(k) if not (supm[i] == 0 and predm[i] == 0)]].mean()), 5),
            "n_classes_with_zero_f1": int((f1m == 0).sum()),
            "worst5_classes": [names[i] for i in np.argsort(f1m)[:5]],
            "best5_classes": [names[i] for i in np.argsort(f1m)[-5:][::-1]],
        }
        per_class[tier]["zero_support_deflation_points"] = round(
            100 * (per_class[tier]["macro_f1_present_classes_only"]
                   - per_class[tier]["macro_f1_all_23_classes"]), 3)

    np.savez_compressed(REPORTS / "phase3b_confusion_matrices.npz",
                        classes=np.array(names),
                        **{t.replace("-", "_"): mats[t] for t in TIER_ORDER})

    # ---- 3: class-composition control ---------------------------------------
    # S-unanimous per-class accuracy, averaged over seeds (the unanimous label
    # is unambiguous, so this is a clean per-class difficulty estimate).
    su_acc = np.full(k, np.nan)
    for i in range(k):
        hits, tot = 0, 0
        for s in SEEDS:
            g = dfs[s][dfs[s].tier == "S-unanimous"]
            m = g.vote_0.map(cls).to_numpy() == i
            hits += int((g.y_pred.to_numpy()[m] == i).sum())
            tot += int(m.sum())
        if tot:
            su_acc[i] = hits / tot

    control = {}
    for tier in TIER_ORDER:
        exp_if_mix, observed, covered = [], [], []
        for s in SEEDS:
            g = dfs[s][dfs[s].tier_pooled == tier]
            V = votes_to_idx(g, cls)
            # every annotator vote is one unit of "class mass" in this tier
            flat = V.reshape(-1)
            vals = su_acc[flat]
            covered.append(float(np.isfinite(vals).mean()))
            exp_if_mix.append(float(np.nanmean(vals)))
            observed.append(float((V == g.y_pred.to_numpy()[:, None]).mean()))
        control[tier] = {
            "expected_accuracy_predicted_by_class_mix_alone": round(float(np.mean(exp_if_mix)), 5),
            "observed_expected_accuracy": round(float(np.mean(observed)), 5),
            "unexplained_by_class_mix_points": round(
                100 * float(np.mean(exp_if_mix) - np.mean(observed)), 3),
            "share_of_drop_explained_by_class_mix_pct": None,
            "class_mass_covered_by_s_unanimous_estimates": round(float(np.mean(covered)), 5),
        }
    base_pred = control["S-unanimous"]["expected_accuracy_predicted_by_class_mix_alone"]
    base_obs = control["S-unanimous"]["observed_expected_accuracy"]
    for tier in TIER_ORDER[1:]:
        c = control[tier]
        total_drop = base_obs - c["observed_expected_accuracy"]
        mix_drop = base_pred - c["expected_accuracy_predicted_by_class_mix_alone"]
        c["share_of_drop_explained_by_class_mix_pct"] = round(
            100 * mix_drop / total_drop, 2) if total_drop else None

    out = {
        "generated": time.strftime("%Y-%m-%d %H:%M:%S"),
        "purpose": "per-class behaviour across strata (blueprint §3.6, Appendix A), "
                   "per-stratum confusion matrices (Appendix B), and the "
                   "class-composition confound control (post-hoc)",
        "seeds": list(SEEDS), "n_classes": k,
        "per_class_by_tier": per_class,
        "class_composition_control": control,
        "zero_support_summary": {
            t: {"n_absent_classes": per_class[t]["n_classes_with_zero_support_and_zero_prediction"],
                "deflation_points": per_class[t]["zero_support_deflation_points"]}
            for t in TIER_ORDER},
        "runtime_sec": round(time.time() - t0, 1),
    }
    (REPORTS / "phase3b_perclass.json").write_text(json.dumps(out, indent=2), encoding="utf-8")

    print("--- zero-support deflation of the 23-class macro average ----------")
    for t in TIER_ORDER:
        z = per_class[t]
        print(f"  {t:16s} absent classes={z['n_classes_with_zero_support_and_zero_prediction']:2d}"
              f"  classes with F1=0: {z['n_classes_with_zero_f1']:2d}"
              f"  macro(23)={100*z['macro_f1_all_23_classes']:6.2f}"
              f"  macro(present)={100*z['macro_f1_present_classes_only']:6.2f}"
              f"  deflation={z['zero_support_deflation_points']:+5.2f} pts")
    print("\n--- class-composition control -------------------------------------")
    for t in TIER_ORDER:
        c = control[t]
        print(f"  {t:16s} predicted by class mix alone={100*c['expected_accuracy_predicted_by_class_mix_alone']:6.2f}%"
              f"  observed={100*c['observed_expected_accuracy']:6.2f}%"
              f"  unexplained={c['unexplained_by_class_mix_points']:+6.2f} pts"
              f"  (class mix explains {c['share_of_drop_explained_by_class_mix_pct']}% of the drop)")
    print(f"done in {time.time()-t0:.1f}s")


if __name__ == "__main__":
    main()
