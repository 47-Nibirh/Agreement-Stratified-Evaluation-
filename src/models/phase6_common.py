"""
Phase 6 -- shared primitives, and the gates that prove the new panel is wired
to the same rows Phases 3-5 scored.

Nothing here computes an endpoint. Its whole job is to hand every Phase 6
script the SAME 1,353 rows in the SAME order, carrying the vote matrix, the
stratum tags, the patient key and one prediction column per (arm, seed) -- and
to refuse to proceed if re-scoring the C0 arm through this panel fails to
reproduce the published Phase 3 numbers.

Metric primitives are imported from phase3b_common, whose selftest() asserts
equality with scikit-learn to 1e-12 at import time. Phase 6 therefore scores
with the identical code that produced the numbers it compares against.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from phase3b_common import (  # noqa: F401,E402
    ANN_COLS, BOOT_SEED, N_BOOT, TIER_ORDER, ci95, macro_f1,
    marginalized_macro_f1, votes_to_idx)

ROOT = Path(__file__).resolve().parents[2]
REPORTS = ROOT / "reports"
DATA = ROOT / "data"

PREREG = REPORTS / "phase6_prereg.json"
CACHE_INDEX = DATA / "phase3_cache_index.csv"
CLASS_INDEX = DATA / "phase2_class_index.json"
P3_METRICS = REPORTS / "phase3_stratified_metrics.json"

ARMS = ("C0", "C1", "C2", "C3", "C4")
SEEDS = (1, 2, 3)
CONTESTED = ("S-majority", "S-plurality", "S-no-majority")
POOLED_CONTESTED = "S-contested (pooled)"
STRATA = list(TIER_ORDER) + [POOLED_CONTESTED]

CONFIG_LABEL = {
    "C0": "C0 hard label, 4/4 cohort (Phase 2 reference)",
    "C1": "C1 hard majority label, extended cohort",
    "C2": "C2 vote proportions",
    "C3": "C3 hard label + matched label smoothing (control)",
    "C4": "C4 vote proportions + anatomical penalty",
}
CONFIG_SHORT = {"C0": "C0 hard 4/4", "C1": "C1 hard maj.", "C2": "C2 soft votes",
                "C3": "C3 smoothed", "C4": "C4 soft+anat."}

# Geometry -- taken UNCHANGED from phase3_confusion.py / phase4_structure.py.
# Gate P6.3b asserts these are identical to the Phase 4 definitions.
WALL_CYCLE = ["G", "A", "L", "P"]
WALL_ADJACENT = {"G-A", "A-G", "A-L", "L-A", "L-P", "P-L", "G-P", "P-G"}
OTHER = "OTHERCLASS"

N_BOOT_P6 = 1000


def prereg() -> dict:
    if not PREREG.exists():
        raise SystemExit("run phase6_prereg.py first -- nothing may be scored "
                         "before the pre-registration is frozen")
    return json.loads(PREREG.read_text(encoding="utf-8"))


def classes() -> dict:
    return json.loads(CLASS_INDEX.read_text(encoding="utf-8"))


def inv_classes() -> dict:
    return {v: k for k, v in classes().items()}


def pred_path(arm: str, seed: int) -> Path:
    """C0 is the frozen Phase 2 model carried through Phase 3; it was never
    retrained in Phase 4, so its predictions live in the Phase 3 artefacts."""
    if arm == "C0":
        return REPORTS / f"phase3_predictions_seed{seed}.csv"
    return REPORTS / f"phase4_predictions_{arm}_seed{seed}.csv"


def probs_path(arm: str, seed: int) -> Path:
    if arm == "C0":
        return REPORTS / f"phase3_probs_seed{seed}.npz"
    return REPORTS / f"phase4_probs_{arm}_seed{seed}.npz"


def ckpt_path(arm: str, seed: int) -> Path:
    if arm == "C0":
        return ROOT / "checkpoints" / f"phase2_convnext_tiny_seed{seed}.pt"
    return ROOT / "checkpoints" / f"phase4_{arm}_seed{seed}.pt"


def available_arms() -> list:
    return [a for a in ARMS if all(pred_path(a, s).exists() for s in SEEDS)]


# =====================================================================
def parse_label(label: str):
    """(wall, station) or (None, None) for OTHERCLASS."""
    if label == OTHER:
        return None, None
    return label[0], int(label[1:])


def vote_entropy(votes_idx: np.ndarray) -> np.ndarray:
    """Per-image Shannon entropy of the 4-annotator vote distribution, in nats.

    0 when all four agree; log(4) when all four differ. This is the human
    disagreement signal every Phase 6 correlation is measured against, and it
    is the same quantity Phase 4's RQ3 used.
    """
    n = votes_idx.shape[0]
    out = np.empty(n)
    for i in range(n):
        _, c = np.unique(votes_idx[i], return_counts=True)
        p = c / c.sum()
        out[i] = float(-(p * np.log(p)).sum())
    return out


def build_panel(arms=None) -> tuple[pd.DataFrame, dict]:
    """One row per test image, one prediction/confidence column per (arm, seed).

    GATE P6.1a -- row order identical to data/phase3_cache_index.csv. Every
    Phase 6 artefact (CAMs included) is written in this order, so any two of
    them can be joined positionally without a merge.
    """
    arms = list(arms or available_arms())
    if not arms:
        raise SystemExit("no arm has a complete set of predictions")

    cache = pd.read_csv(CACHE_INDEX)
    base = pd.read_csv(pred_path(arms[0], SEEDS[0]))
    if list(base.filename) != list(cache.filename):
        raise SystemExit("GATE P6.1a FAILED: prediction row order differs from "
                         "the cache index")

    keep = ["filename", "patient", "tier", "tier_pooled", "pseudo_label"] + list(ANN_COLS)
    panel = base[keep].copy()
    for a in arms:
        for s in SEEDS:
            d = pd.read_csv(pred_path(a, s))
            if list(d.filename) != list(panel.filename):
                raise SystemExit(f"GATE P6.1a FAILED: {a} seed{s} row order differs")
            panel[f"pred_{a}_{s}"] = d.y_pred.to_numpy()
            panel[f"label_pred_{a}_{s}"] = d.label_pred.to_numpy()
            panel[f"conf_{a}_{s}"] = d.confidence.to_numpy()

    cls = classes()
    votes = votes_to_idx(panel, cls)
    panel["vote_entropy"] = vote_entropy(votes)
    panel[POOLED_CONTESTED] = panel.tier_pooled.isin(CONTESTED)
    meta = {"arms": arms, "seeds": list(SEEDS), "n_images": len(panel),
            "gate_P6.1a": "PASS -- row order identical to phase3_cache_index.csv"}
    return panel, meta


def stratum_mask(panel: pd.DataFrame, stratum: str) -> np.ndarray:
    if stratum == POOLED_CONTESTED:
        return panel[POOLED_CONTESTED].to_numpy()
    return (panel.tier_pooled == stratum).to_numpy()


def votes_matrix(panel: pd.DataFrame) -> np.ndarray:
    return votes_to_idx(panel, classes())


# =====================================================================
def patient_resamples(patients: np.ndarray, n_boot: int = N_BOOT_P6,
                      seed: int = BOOT_SEED):
    """Row-index arrays for n_boot patient-clustered resamples.

    Precomputed once and reused for every quantity in a contrast, which is what
    makes the contrast PAIRED: both sides see the same patients.
    """
    rng = np.random.default_rng(seed)
    uniq = np.unique(patients)
    by_pat = {p: np.where(patients == p)[0] for p in uniq}
    for _ in range(n_boot):
        pick = rng.choice(uniq, len(uniq), replace=True)
        yield np.concatenate([by_pat[p] for p in pick])


def paired_ci(values_a, values_b) -> tuple:
    """95% CI on (a - b) from paired per-resample values."""
    d = np.asarray(values_a) - np.asarray(values_b)
    d = d[np.isfinite(d)]
    if d.size < 10:
        return (None, None), None
    return (float(np.percentile(d, 2.5)), float(np.percentile(d, 97.5))), float(d.mean())


def verdict_three_way(lo, hi, above: str, below: str, null: str) -> str:
    if lo is None:
        return "NOT ESTIMABLE"
    if lo > 0:
        return above
    if hi < 0:
        return below
    return null


# =====================================================================
def gate_p61b(panel: pd.DataFrame) -> dict:
    """GATE P6.1b -- re-scoring C0 through this panel must reproduce the
    published Phase 3 annotator-marginalized macro F1 per stratum.

    This is the whole point of the gate: if the panel were misaligned by even
    one row, this number would move. It does not move, so every later Phase 6
    number is computed on the rows Phase 3 published.
    """
    if "C0" not in available_arms():
        return {"status": "SKIPPED", "reason": "C0 predictions absent"}
    ref = json.loads(P3_METRICS.read_text(encoding="utf-8"))["aggregate_3seed"]
    cls = classes()
    k = len(cls)
    votes = votes_matrix(panel)
    out, worst = {}, 0.0
    for stratum in TIER_ORDER:
        m = stratum_mask(panel, stratum)
        vals = [marginalized_macro_f1(votes[m], panel[f"pred_C0_{s}"].to_numpy()[m], k)
                for s in SEEDS]
        got = float(np.mean(vals))
        want = ref[stratum]["annotator_marginalized_macro_f1_mean_3seed"]
        # the published artefact is rounded to 5 dp, so the gate is against
        # that rounding, not against an unattainable exactness
        delta = abs(round(got, 5) - want)
        worst = max(worst, delta)
        out[stratum] = {"recomputed": round(got, 5), "phase3_published": want,
                        "abs_delta": delta}
    status = "PASS" if worst < 1e-9 else "FAIL"
    if status == "FAIL":
        raise SystemExit(
            f"GATE P6.1b FAILED: C0 re-scored through the Phase 6 panel does not "
            f"reproduce phase3_stratified_metrics.json (worst delta {worst:.3e}). "
            f"The panel is not aligned to the rows Phase 3 scored; fix that before "
            f"any endpoint is computed.")
    return {"status": status, "worst_abs_delta": worst, "per_stratum": out}


def selftest() -> None:
    """Cheap invariants that would catch a definition drift silently changing a
    published number."""
    # geometry must match phase4_structure.py exactly (gate P6.3b)
    from phase4_structure import WALL_ADJACENT as P4_ADJ, WALL_CYCLE as P4_CYC
    assert WALL_ADJACENT == P4_ADJ, "wall adjacency drifted from Phase 4"
    assert WALL_CYCLE == P4_CYC, "wall cycle drifted from Phase 4"
    # vote entropy endpoints
    assert abs(vote_entropy(np.array([[3, 3, 3, 3]]))[0]) < 1e-12
    assert abs(vote_entropy(np.array([[0, 1, 2, 3]]))[0] - np.log(4)) < 1e-12


selftest()
