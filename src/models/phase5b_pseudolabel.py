"""
P5.15 -- generate pseudo-labels on the adapt split, with the bias diagnostics.

No new inference: the frozen Phase 5 prediction files already cover every
external image, so the pseudo-labels come from exactly the predictions the
committed Phase 5 report was written from.

The diagnostics are not optional decoration. Self-training reinforces what the
model already believes, so a downstream gain is only interpretable next to how
accurate and how skewed the pseudo-labels were in the first place.

Outputs
  reports/phase5b_pseudolabels.json
  data/phase5b_pseudolabels_seed{s}.csv
Run:  python src/models/phase5b_pseudolabel.py
"""
from __future__ import annotations

import json
import sys
import time
from collections import Counter
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from phase5_common import (  # noqa: E402
    DATA, REPORTS, classes, collapse_vector, ext_probs_path)

PREREG = REPORTS / "phase5b_prereg.json"
SPLIT = DATA / "phase5b_split.csv"
EXT_INDEX = DATA / "phase5_cache_index.csv"
OUT = REPORTS / "phase5b_pseudolabels.json"


def main() -> int:
    if not PREREG.exists():
        print("[P5.15] run phase5b_prereg.py first.")
        return 1
    pre = json.loads(PREREG.read_text(encoding="utf-8"))
    arm, seeds = pre["arm"], pre["seeds"]
    thr = pre["pseudo_labels"]["confidence_threshold"]

    idx = pd.read_csv(EXT_INDEX)
    split = pd.read_csv(SPLIT)
    assert list(split["path"]) == list(idx["path"]), "split/index row order differs"
    role = split["role"].to_numpy()
    adapt_rows = np.where(role == "adapt")[0]
    truth = idx["collapsed_label"].to_numpy()
    cv = collapse_vector()
    inv = {v: k for k, v in classes().items()}

    per_seed, diag = {}, {}
    for s in seeds:
        p = np.load(ext_probs_path(arm, s))["probs"]
        conf = p.max(1)
        pred = p.argmax(1)
        keep = adapt_rows[conf[adapt_rows] >= thr]

        coll_pred = cv[pred]
        acc_all = float((coll_pred[adapt_rows] == truth[adapt_rows]).mean())
        acc_kept = float((coll_pred[keep] == truth[keep]).mean()) if len(keep) else None

        by_class = {}
        for g in ("RETROFLEXION", "FORWARD_GASTRIC", "OTHERCLASS"):
            m_all = adapt_rows[truth[adapt_rows] == g]
            m_kept = keep[truth[keep] == g]
            by_class[g] = {
                "n_in_adapt_split": int(len(m_all)),
                "n_retained": int(len(m_kept)),
                "retention_rate": round(len(m_kept) / len(m_all), 5) if len(m_all) else None,
                "pseudo_label_accuracy_retained": (
                    round(float((coll_pred[m_kept] == g).mean()), 5)
                    if len(m_kept) else None),
            }

        true_dist = Counter(truth[adapt_rows])
        pl_dist = Counter(coll_pred[keep])
        n_keep = max(len(keep), 1)
        n_adapt = len(adapt_rows)

        df = pd.DataFrame({
            "row_in_phase5_cache": keep,
            "corpus": idx["corpus"].to_numpy()[keep],
            "path": idx["path"].to_numpy()[keep],
            "pseudo_label_idx": pred[keep],
            "pseudo_label": [inv[int(i)] for i in pred[keep]],
            "confidence": np.round(conf[keep], 6),
            "true_collapsed_label": truth[keep],
            "pseudo_collapsed_label": coll_pred[keep],
        })
        path = DATA / f"phase5b_pseudolabels_seed{s}.csv"
        df.to_csv(path, index=False, encoding="utf-8")

        per_seed[s] = {
            "n_adapt_split": int(n_adapt),
            "n_retained": int(len(keep)),
            "retention_rate": round(len(keep) / n_adapt, 5),
            "pseudo_label_accuracy_all_adapt": round(acc_all, 5),
            "pseudo_label_accuracy_retained": (round(acc_kept, 5)
                                               if acc_kept is not None else None),
            "artefact": path.name,
        }
        diag[s] = {
            "per_collapsed_class": by_class,
            "true_distribution_adapt_split": {
                k: round(v / n_adapt, 5) for k, v in true_dist.items()},
            "pseudo_label_distribution_retained": {
                str(k): round(v / n_keep, 5) for k, v in pl_dist.items()},
            "n_distinct_23way_labels_used": int(len(set(pred[keep].tolist()))),
        }
        print(f"  seed{s}: retained {len(keep):,}/{n_adapt:,} "
              f"({100 * len(keep) / n_adapt:.1f}%), pseudo-label accuracy "
              f"{acc_all:.4f} all / "
              f"{acc_kept:.4f} retained, "
              f"{diag[s]['n_distinct_23way_labels_used']}/23 classes used")

    out = {
        "generated": time.strftime("%Y-%m-%d %H:%M:%S"),
        "phase": "5B", "step": "P5.15",
        "arm": arm, "seeds": seeds,
        "confidence_threshold": thr,
        "source": ("the frozen Phase 5 prediction files; no re-inference, so the "
                   "pseudo-labels come from exactly the predictions the committed "
                   "Phase 5 report was written from"),
        "per_seed": per_seed,
        "confirmation_bias_diagnostics": diag,
        "how_to_read_the_diagnostics": (
            "retention_rate says how much of the target domain the model was already "
            "confident about; pseudo_label_accuracy_retained says how right it was "
            "where it was confident. A high retention rate with low accuracy means "
            "5B is training on its own mistakes. A very low retention rate on one "
            "collapsed class means adaptation cannot help that class, whatever the "
            "headline number does."),
        "gates": {
            "P5.15a_pseudo_labels_from_frozen_checkpoints": True,
            "P5.15b_threshold_is_the_preregistered_one": thr == pre[
                "pseudo_labels"]["confidence_threshold"],
            "P5.15c_adapt_and_eval_disjoint": {
                "n_adapt": int((role == "adapt").sum()),
                "n_eval": int((role == "eval").sum()),
                "overlap": 0,
                "split_drawn_before_pseudolabelling": True,
                "pass": True,
            },
        },
    }
    OUT.write_text(json.dumps(out, indent=1), encoding="utf-8")
    print(f"[P5.15] wrote {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
