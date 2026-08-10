"""
P5.14 -- draw the held-out external split and freeze the Phase 5B pre-registration.

Order matters and is enforced by this script doing both things at once: the
evaluation split is drawn HERE, before a single pseudo-label exists. If the split
were drawn afterwards it could be chosen, knowingly or not, to suit the result,
and 5B would measure memorisation rather than adaptation.

Refuses to overwrite. Run once, before phase5b_pseudolabel.py.

Run:  python src/models/phase5b_prereg.py
"""
from __future__ import annotations

import hashlib
import json
import sys
import time
from collections import Counter
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
REPORTS = ROOT / "reports"
DATA = ROOT / "data"
OUT = REPORTS / "phase5b_prereg.json"
SPLIT = DATA / "phase5b_split.csv"

EXT_INDEX = DATA / "phase5_cache_index.csv"
P5_PREREG = REPORTS / "phase5_prereg.json"

ARM = "C2"
SEEDS = (1, 2, 3)
EVAL_FRACTION = 0.40
SPLIT_SEED = 20260726
CONF_THRESHOLD = 0.90
N_ROUNDS = 1
CAP_FINETUNE = 12
PATIENCE = 5


def main() -> int:
    if OUT.exists():
        print(f"[P5.14] {OUT.name} already exists; refusing to overwrite.")
        print("        The split and the protocol are frozen.")
        return 1
    for p in (EXT_INDEX, P5_PREREG):
        if not p.exists():
            print(f"[P5.14] missing {p}")
            return 1

    p5 = json.loads(P5_PREREG.read_text(encoding="utf-8"))
    idx = pd.read_csv(EXT_INDEX)

    # ---- draw the split, stratified by (corpus, collapsed label) ------------
    rng = np.random.default_rng(SPLIT_SEED)
    idx["_stratum"] = idx["corpus"] + "|" + idx["collapsed_label"]
    role = np.empty(len(idx), dtype=object)
    for st, grp in idx.groupby("_stratum"):
        pos = grp.index.to_numpy()
        perm = rng.permutation(len(pos))
        n_eval = int(round(EVAL_FRACTION * len(pos)))
        role[pos[perm[:n_eval]]] = "eval"
        role[pos[perm[n_eval:]]] = "adapt"
    idx["role"] = role
    assert not pd.isna(idx["role"]).any()

    out_cols = ["corpus", "path", "external_class", "collapsed_label", "role"]
    idx[out_cols].to_csv(SPLIT, index=False, encoding="utf-8")
    digest = hashlib.sha256(
        "\n".join(f"{r.corpus}|{r.path}|{r.role}"
                  for r in idx.itertuples()).encode("utf-8")).hexdigest()

    counts = {r: dict(Counter(idx.loc[idx.role == r, "collapsed_label"]))
              for r in ("adapt", "eval")}
    print(f"[P5.14] split: {int((idx.role == 'adapt').sum()):,} adapt / "
          f"{int((idx.role == 'eval').sum()):,} eval")
    for r in ("adapt", "eval"):
        print(f"        {r}: {counts[r]}")

    doc = {
        "frozen_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "phase": "5B",
        "title": "Self-training adaptation to the external corpora",
        "statement": (
            "This document fixes every decision that could otherwise be made after "
            "seeing the result, and it draws the held-out evaluation split before "
            "any pseudo-label exists. Phase 5B measures transfer-AFTER-adaptation. "
            "It does not and cannot produce a generalisation claim: a gain here "
            "means the domain gap is closable with unlabelled target data, not that "
            "the model generalises. The Phase 5 numbers remain the generalisation "
            "result, and they are frozen and committed."),
        "gated_on": {
            "phase5_frozen_and_committed": True,
            "why": ("adapting to the external images before the clean transfer "
                    "numbers exist would make the external validation circular and "
                    "unrecoverable -- once the model has seen the target domain, no "
                    "un-adapted number can be reconstructed from it."),
        },
        "comparator": {
            "baseline": ("the frozen Phase 5 predictions for the same arm and seeds, "
                         "restricted to the held-out eval split"),
            "restriction_declared": (
                "the headline Phase 5 numbers were computed on ALL evaluated "
                "external images; the 5B comparison recomputes the baseline on the "
                "eval split only, from the same frozen prediction files, so that "
                "both sides of the contrast are scored on identical rows. No "
                "re-inference and no re-selection is involved."),
        },
        "arm": ARM,
        "arm_rationale": ("C2 is the configuration Phase 5 recommends, on external "
                          "calibration and out-of-protocol rejection."),
        "seeds": list(SEEDS),
        "split": {
            "unit": "IMAGE",
            "eval_fraction": EVAL_FRACTION,
            "seed": SPLIT_SEED,
            "stratified_by": "corpus x collapsed label",
            "n_adapt": int((idx.role == "adapt").sum()),
            "n_eval": int((idx.role == "eval").sum()),
            "counts_by_collapsed_label": counts,
            "artefact": "data/phase5b_split.csv",
            "sha256": digest,
            "declared_weakness": (
                "the split is image-level because neither corpus publishes a patient "
                "or case identifier. Frames from the same procedure can therefore "
                "fall on both sides of the split, which makes the ADAPTED arm look "
                "better than it would under a patient-level split. Any 5B gain is "
                "consequently an UPPER BOUND on what adaptation buys, and the report "
                "must say so."),
        },
        "pseudo_labels": {
            "source": f"the frozen {ARM} checkpoints, checkpoints/phase4_{ARM}_seed*.pt",
            "construction": ("23-way argmax on the adapt-split images, taken as a "
                             "hard label; the model's own prediction, per seed"),
            "confidence_threshold": CONF_THRESHOLD,
            "threshold_fixed_a_priori": True,
            "threshold_rationale": (
                "0.90 on the 23-way top-1 probability, chosen before any pseudo-label "
                "was generated and not tuned. A threshold selected after seeing "
                "retention rates or downstream accuracy would make the whole phase "
                "post-hoc."),
            "images_below_threshold": "discarded, not down-weighted",
        },
        "training": {
            "warm_start_from": f"the frozen {ARM} checkpoint for the matching seed",
            "mixture": ("pseudo-labelled external images CONCATENATED with the "
                        "original GastroHUN cohort E, at natural proportions"),
            "mixture_rationale": (
                "training on external pseudo-labels alone would let the model drift "
                "off the labelled task entirely; keeping cohort E in the mixture "
                "means a 5B loss on the internal endpoints is attributable to "
                "adaptation rather than to simple forgetting."),
            "rounds": N_ROUNDS,
            "schedule": (f"fine-tune the top 40% of feature modules at 1e-4 with "
                         f"cosine annealing, cap {CAP_FINETUNE} epochs, patience "
                         f"{PATIENCE}"),
            "model_selection": (
                "macro F1 on the GastroHUN extended VALIDATION cohort (n = 1,103), "
                "exactly as in Phase 4"),
            "model_selection_rule": (
                "selection NEVER touches the external eval split. Early stopping on "
                "the split the result is read from would be the single easiest way "
                "to manufacture a gain here, and it is forbidden."),
        },
        "endpoints": {
            "P5-A": ("binary macro F1 over {RETROFLEXION, FORWARD_GASTRIC} on the "
                     "eval split, adapted minus baseline"),
            "P5-B": ("out-of-protocol rejection rate on the eval split, adapted "
                     "minus baseline"),
            "P5-C": "ECE on the eval split, adapted minus baseline",
            "internal_retention": (
                "the same GastroHUN test-split endpoints Phase 4 used, to detect "
                "catastrophic forgetting; reported whatever the external result"),
        },
        "verdict_rules": {
            "P5-A": ("ADAPTATION HELPS if the paired 95% CI of (adapted - baseline) "
                     "excludes 0 above; HURTS if it excludes 0 below; NOT RESOLVED "
                     "if it contains 0."),
            "P5-B": "same rule, applied to the rejection rate.",
            "P5-C": ("BETTER CALIBRATED if the paired CI of (adapted - baseline) ECE "
                     "excludes 0 below zero."),
            "forgetting": ("REGRESSION ON THE SOURCE DOMAIN if the internal macro F1 "
                           "falls with a CI excluding 0 below."),
        },
        "interval_procedure": {
            "method": "paired bootstrap, 1,000 resamples, seed 20260726",
            "unit": "IMAGE",
            "pairing": ("one resample of eval-split rows is drawn and BOTH the "
                        "adapted and the baseline predictions are scored on those "
                        "same rows before differencing"),
        },
        "confirmation_bias_diagnostics": {
            "required": True,
            "quantities": [
                "pseudo-label accuracy against the collapsed ground truth, overall "
                "and per collapsed class, on the adapt split",
                "retention rate at the confidence threshold, per collapsed class",
                "the collapsed-class distribution of the pseudo-labels against the "
                "true distribution -- self-training narrows what it is already "
                "confident about, and on a label space this collapsed the narrowing "
                "may be severe",
            ],
            "why": ("self-training reinforces what the model already believes. "
                    "Reporting only the final accuracy would hide whether a gain "
                    "came from learning or from the evaluation inheriting the "
                    "model's own biases."),
        },
        "scope_exclusions": [
            "no change to the frozen Phase 5 mapping, collapse or endpoints",
            "no re-inference of the Phase 5 baseline; the committed prediction files "
            "are subset, not regenerated",
            "no threshold tuning, no temperature scaling",
            "no adaptation of any arm other than " + ARM,
        ],
        "falsification": (
            "the premise of this phase is falsified if adaptation does not improve "
            "the external endpoints, or if it improves them only at the cost of a "
            "significant regression on the GastroHUN test split. Either outcome is "
            "reported as the finding."),
        "inherited_from_phase5": {
            "collapse": p5["label_space"]["collapse"],
            "interval_weakness": p5["interval_procedure"]["declared_weakness"],
        },
    }
    OUT.write_text(json.dumps(doc, indent=1), encoding="utf-8")
    print(f"[P5.14] FROZEN -> {OUT}")
    print(f"        arm {ARM}, seeds {list(SEEDS)}, threshold {CONF_THRESHOLD}, "
          f"{N_ROUNDS} round(s)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
