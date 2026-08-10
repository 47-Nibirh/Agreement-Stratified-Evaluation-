"""
Shared primitives for the Phase 5 evaluation scripts.

Everything the endpoints need in one place: the frozen collapse, the external
panel, the internal comparator panel, and the image-level bootstrap the
pre-registration declares (P5-DEV-3).
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.metrics import f1_score

ROOT = Path(__file__).resolve().parents[2]
REPORTS = ROOT / "reports"
DATA = ROOT / "data"

PREREG = REPORTS / "phase5_prereg.json"
MAPPING = REPORTS / "phase5_mapping.json"
EXT_INDEX = DATA / "phase5_cache_index.csv"
INT_INDEX = DATA / "phase3_cache_index.csv"
CLASS_INDEX = DATA / "phase2_class_index.json"

RETRO = "RETROFLEXION"
FORWARD = "FORWARD_GASTRIC"
OTHER = "OTHERCLASS"
GASTRIC = (RETRO, FORWARD)

N_BOOT = 1000
BOOT_SEED = 20260726


def prereg() -> dict:
    return json.loads(PREREG.read_text(encoding="utf-8"))


def mapping() -> dict:
    return json.loads(MAPPING.read_text(encoding="utf-8"))


def classes() -> dict:
    return json.loads(CLASS_INDEX.read_text(encoding="utf-8"))


def collapse_vector() -> np.ndarray:
    """Length-23 array mapping each class index to its collapsed group name."""
    coll = mapping()["collapse_definition"]
    out = np.empty(len(classes()), dtype=object)
    for group, spec in coll.items():
        for i in spec["class_indices"]:
            out[i] = group
    assert all(x is not None for x in out), "collapse does not cover all 23 classes"
    return out


def ext_probs_path(cfg: str, seed: int) -> Path:
    return REPORTS / f"phase5_probs_{cfg}_seed{seed}.npz"


def int_probs_path(cfg: str, seed: int) -> Path:
    """Internal (GastroHUN test split) probabilities for the comparator.

    C0 was never retrained in Phase 4 -- it is the Phase 2 checkpoint carried
    through -- so its test-split probabilities live in the Phase 3 artefacts.
    Both files have the same keys, the same 1,353 rows and the same row order.
    """
    if cfg == "C0":
        return REPORTS / f"phase3_probs_seed{seed}.npz"
    return REPORTS / f"phase4_probs_{cfg}_seed{seed}.npz"


def available_arms(seeds) -> list[str]:
    arms = prereg()["arms"]["carried"]
    return [c for c in arms if all(ext_probs_path(c, s).exists() for s in seeds)]


def external_panel() -> pd.DataFrame:
    """One row per evaluated external image, with its frozen collapsed label."""
    return pd.read_csv(EXT_INDEX)


def internal_panel() -> pd.DataFrame:
    """The 1,353-image GastroHUN test split, with a collapsed truth column.

    The truth is the modal (pseudo) label collapsed through the SAME frozen
    mapping, so the internal comparator and the external endpoint are the same
    measurement on two populations.
    """
    df = pd.read_csv(INT_INDEX)
    cls = classes()
    cv = collapse_vector()
    # The 1-1-1-1 (S-no-majority) test images have no modal label at all, so
    # they have no collapsed truth either. The pre-registration restricts the
    # internal comparator to "images whose modal label is a gastric station",
    # which excludes them by its own wording rather than by a later choice.
    idx = df["pseudo_label"].map(cls)
    df["y_true_idx"] = idx.astype("Int64")
    df["collapsed_label"] = [
        "UNDEFINED" if pd.isna(i) else cv[int(i)] for i in idx]
    return df


def collapsed_pred(probs: np.ndarray, cv: np.ndarray) -> np.ndarray:
    """Collapse the 23-way ARGMAX, not the summed mass.

    Taking the argmax first and then collapsing measures what the deployed model
    would actually output. Summing the probability mass within each group before
    the argmax would be a different (and more forgiving) classifier than the one
    Phases 2-4 evaluated, so it is not used for the primary endpoint.
    """
    return cv[probs.argmax(1)]


def binary_macro_f1(truth: np.ndarray, pred: np.ndarray) -> float:
    """Macro F1 over {RETROFLEXION, FORWARD_GASTRIC}.

    `pred` may contain OTHERCLASS; those rows are simply wrong for whichever
    class the image truly is, which is what the pre-registration specifies.
    """
    labels = list(GASTRIC)
    return float(f1_score(truth, pred, labels=labels, average="macro",
                          zero_division=0))


def image_resamples(n: int, n_boot: int = N_BOOT, seed: int = BOOT_SEED):
    """Image-level resamples. P5-DEV-3: no grouping key exists externally, so
    these intervals are OPTIMISTIC relative to the patient-clustered intervals
    of Phases 0-4 and may not be compared against them directly."""
    rng = np.random.default_rng(seed)
    for _ in range(n_boot):
        yield rng.integers(0, n, n)


def ci95(v: np.ndarray) -> list:
    v = np.asarray([x for x in v if np.isfinite(x)])
    if v.size < 10:
        return [None, None]
    return [float(np.percentile(v, 2.5)), float(np.percentile(v, 97.5))]


def halfwidth(ci: list) -> float | None:
    if ci[0] is None:
        return None
    return (ci[1] - ci[0]) / 2.0
