"""
P5.10 -- mapping sensitivity.

The pre-registration commits to re-running every mapping decision flagged
ambiguous for an endpoint under test with its recorded alternative, and
recomputing the verdict under each. This executes exactly that, one flip at a
time and then all flips together.

The flips are not free choices made here: they are the `alternative_decision_for_
sensitivity` field frozen in reports/phase5_mapping.json before any image was
scored. This script reads them; it does not invent them.

Outputs
  reports/phase5_sensitivity.json
Run:  python src/models/phase5_sensitivity.py
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from phase5_common import (  # noqa: E402
    DATA, GASTRIC, N_BOOT, OTHER, REPORTS, available_arms, binary_macro_f1,
    ci95, collapse_vector, collapsed_pred, external_panel, ext_probs_path,
    halfwidth, image_resamples, mapping, prereg)

OUT = REPORTS / "phase5_sensitivity.json"
DISC_INDEX = DATA / "phase5_cache_discarded_index.csv"
MAJORITY_FLOOR = 50.0


def disc_probs_path(cfg: str, seed: int) -> Path:
    return REPORTS / f"phase5_probs_disc_{cfg}_seed{seed}.npz"


def main() -> int:
    t0 = time.time()
    pre, mp = prereg(), mapping()
    seeds = pre["arms"]["seeds"]
    arms = available_arms(seeds)
    head = pre["arms"]["headline_arm"]
    if head not in arms:
        print(f"[P5.10] headline arm {head} has no external predictions yet.")
        return 1

    cv = collapse_vector()
    ext = external_panel()
    truth = ext["collapsed_label"].to_numpy()
    ecls = ext["external_class"].to_numpy()
    ecorp = ext["corpus"].to_numpy()

    flips = [f for f in mp["gates"]["P5.2c_ambiguous_decisions_flagged"][
        "ambiguous_classes"] if f["affects_an_endpoint"]]
    print(f"[P5.10] {len(flips)} pre-registered flips, arms {arms}")

    # ---- discarded-image predictions, needed for discard -> OTHERCLASS -------
    have_disc = DISC_INDEX.exists() and all(
        disc_probs_path(c, s).exists() for c in arms for s in seeds)
    if have_disc:
        disc = pd.read_csv(DISC_INDEX)
        dcls, dcorp = disc["external_class"].to_numpy(), disc["corpus"].to_numpy()
        dpred = {(c, s): collapsed_pred(np.load(disc_probs_path(c, s))["probs"], cv)
                 for c in arms for s in seeds}
    else:
        print("[P5.10] discarded-image predictions absent: the discard->OTHERCLASS "
              "flips cannot be executed. Run phase5_cache_supplement.py and "
              "phase5_infer_supplement.py.")

    epred = {(c, s): collapsed_pred(np.load(ext_probs_path(c, s))["probs"], cv)
             for c in arms for s in seeds}

    def p5a(drop_classes) -> dict:
        """Binary macro F1 on the gastric set, minus any dropped classes."""
        m = np.isin(truth, list(GASTRIC))
        for corpus, cls in drop_classes:
            m &= ~((ecorp == corpus) & (ecls == cls))
        rows = np.where(m)[0]
        t = truth[rows]
        preds = [epred[(head, s)][rows] for s in seeds]
        point = float(np.mean([100 * binary_macro_f1(t, p) for p in preds]))
        reps = [float(np.mean([100 * binary_macro_f1(t[loc], p[loc]) for p in preds]))
                for loc in image_resamples(len(rows))]
        ci = ci95(np.asarray(reps))
        hw = halfwidth(ci)
        target = pre["precision_target"]["max_ci95_halfwidth_points"]
        verdict = ("UNDERPOWERED" if hw is not None and hw > target
                   else "TRANSFERS" if ci[0] is not None and ci[0] > MAJORITY_FLOOR
                   else "DOES NOT TRANSFER")
        return {"n_images": int(len(rows)), "macro_f1": round(point, 3),
                "ci95": [round(x, 3) for x in ci],
                "halfwidth": round(hw, 3) if hw is not None else None,
                "verdict": verdict}

    def p5b(add_classes) -> dict | None:
        """Rejection rate on out-of-protocol, plus any classes promoted into it."""
        if add_classes and not have_disc:
            return None
        base = np.where(truth == OTHER)[0]
        parts = [[epred[(head, s)][base] for s in seeds]]
        n = len(base)
        if add_classes:
            dm = np.zeros(len(dcls), dtype=bool)
            for corpus, cls in add_classes:
                dm |= (dcorp == corpus) & (dcls == cls)
            drows = np.where(dm)[0]
            n += len(drows)
            parts.append([dpred[(head, s)][drows] for s in seeds])
        preds = [np.concatenate([p[i] for p in parts]) for i in range(len(seeds))]
        point = float(np.mean([(p == OTHER).mean() for p in preds]))
        reps = [float(np.mean([(p[loc] == OTHER).mean() for p in preds]))
                for loc in image_resamples(n)]
        ci = ci95(np.asarray(reps))
        chance = pre["research_questions"]["P5-B"]["chance_rate"]
        return {"n_images": int(n), "rejection_rate": round(point, 5),
                "ci95": [round(x, 5) for x in ci],
                "exceeds_chance": bool(ci[0] is not None and ci[0] > chance),
                "verdict": ("REJECTS OUT-OF-PROTOCOL IMAGES"
                            if ci[0] is not None and ci[0] > chance
                            else "DOES NOT REJECT")}

    baseline = {"P5-A": p5a([]), "P5-B": p5b([])}
    print(f"  baseline  P5-A {baseline['P5-A']['macro_f1']:.2f} "
          f"{baseline['P5-A']['verdict']} | P5-B "
          f"{baseline['P5-B']['rejection_rate']:.4f} {baseline['P5-B']['verdict']}")

    results, all_drop, all_add = {}, [], []
    for f in flips:
        key = f"{f['corpus']}/{f['class']}"
        pair = (f["corpus"], f["class"])
        rec = {"flip": f, "P5-A": None, "P5-B": None}
        if f["primary"] in GASTRIC and f["alternative"] == "discard":
            all_drop.append(pair)
            rec["P5-A"] = p5a([pair])
            rec["changed_P5A_verdict"] = (
                rec["P5-A"]["verdict"] != baseline["P5-A"]["verdict"])
        elif f["primary"] == "discard" and f["alternative"] == OTHER:
            all_add.append(pair)
            rec["P5-B"] = p5b([pair])
            rec["changed_P5B_verdict"] = (
                None if rec["P5-B"] is None
                else rec["P5-B"]["verdict"] != baseline["P5-B"]["verdict"])
        results[key] = rec
        shown = rec["P5-A"] or rec["P5-B"]
        print(f"  flip {key:45} -> {shown['verdict'] if shown else 'not executable'}")

    combined = {
        "P5-A": p5a(all_drop) if all_drop else None,
        "P5-B": p5b(all_add) if all_add else None,
    }

    verdicts_invariant = all(
        (r.get("changed_P5A_verdict") in (False, None)) and
        (r.get("changed_P5B_verdict") in (False, None)) for r in results.values())

    out = {
        "generated": time.strftime("%Y-%m-%d %H:%M:%S"),
        "phase": 5, "step": "P5.10",
        "purpose": ("re-run every pre-registered ambiguous mapping decision with its "
                    "frozen alternative and recompute the verdict"),
        "headline_arm": head, "arms": arms, "seeds": seeds,
        "n_boot": N_BOOT, "boot_unit": "image",
        "discarded_predictions_available": bool(have_disc),
        "baseline": baseline,
        "per_flip": results,
        "all_flips_combined": combined,
        "verdicts_invariant_to_every_single_flip": bool(verdicts_invariant),
        "note": ("the alternatives are read from the frozen mapping's "
                 "alternative_decision_for_sensitivity field, fixed before any image "
                 "was scored; this script does not choose them."),
        "runtime_sec": round(time.time() - t0, 1),
    }
    OUT.write_text(json.dumps(out, indent=1), encoding="utf-8")
    print(f"[P5.10] wrote {OUT}")
    print(f"        verdicts invariant to every single flip: {verdicts_invariant}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
