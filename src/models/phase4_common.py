"""
Phase 4 -- shared loading, stratum definitions and the paired bootstrap.

Every Phase 4 configuration is evaluated on the SAME 1,353 test images in the
SAME row order (the Phase 3 cache index). That is what makes the paired
bootstrap below both possible and correct: one patient resample is drawn, and
every configuration is scored on exactly those rows before differencing, so
the interval measures the difference between two models on the same patients
rather than the sum of two independent sampling errors.

`build_panel()` returns one wide frame carrying the vote matrix once and a
prediction/confidence column per (configuration, seed). Row alignment is
asserted, not assumed.

The metric primitives are imported from phase3b_common so that Phase 4 scores
are computed by the identical code that produced the Phase 3 numbers this
phase compares against; that module's selftest() asserts equality with
scikit-learn to 1e-12 at import time.
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from phase3b_common import (  # noqa: F401,E402
    ANN_COLS, ARCH_GAP_BENCHMARK, BOOT_SEED, N_BOOT, TIER_ORDER, TIER_ORDER_FULL,
    any_hit_rate, ci95, expected_accuracy, macro_f1, marginalized_macro_f1,
    max_expected_accuracy, modal_oracle, votes_to_idx)

ROOT = Path(__file__).resolve().parents[2]
REPORTS = ROOT / "reports"
CLASS_INDEX = ROOT / "data" / "phase2_class_index.json"
PREREG = REPORTS / "phase4_prereg.json"

CONFIGS = ("C0", "C1", "C2", "C3", "C4")
NEW_CONFIGS = ("C1", "C2", "C3", "C4")

# The pre-registered seed set is (1, 2, 3). PHASE4_SEEDS exists so the whole
# downstream pipeline can be integration-tested on a partial sweep while the
# remaining runs are still training; every output JSON records the seed list it
# actually used, so a partial run can never be mistaken for the real one.
SEEDS = tuple(int(x) for x in os.environ.get("PHASE4_SEEDS", "1,2,3").split(","))

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
                "C3": "C3 smoothed", "C4": "C4 soft + anat."}

N_BOOT_P4 = 1000
# Blueprint sec.6 and the frozen pre-registration both require >=1,000 resamples
# for EVERY interval, paired contrasts included. An earlier run used 500 here as a
# throughput shortcut; that was an undeclared departure from the pre-registration,
# so the count is restored to the pre-registered value.
N_BOOT_PAIR = 1000


def prereg() -> dict:
    return json.loads(PREREG.read_text(encoding="utf-8"))


def classes() -> dict:
    return json.loads(CLASS_INDEX.read_text(encoding="utf-8"))


def pred_path(config: str, seed: int) -> Path:
    """C0 is the frozen Phase 2 model; its full-test-split predictions already
    exist as the Phase 3 artefacts and are reused rather than recomputed."""
    if config == "C0":
        return REPORTS / f"phase3_predictions_seed{seed}.csv"
    return REPORTS / f"phase4_predictions_{config}_seed{seed}.csv"


def probs_path(config: str, seed: int) -> Path:
    if config == "C0":
        return REPORTS / f"phase3_probs_seed{seed}.npz"
    return REPORTS / f"phase4_probs_{config}_seed{seed}.npz"


def mc_path(config: str, seed: int) -> Path:
    if config == "C0":
        return REPORTS / f"phase4_mc_C0_seed{seed}.npz"
    return REPORTS / f"phase4_mc_{config}_seed{seed}.npz"


def available_configs() -> list:
    """Configurations whose full seed set has been inferred. Analysis scripts
    degrade gracefully rather than half-reporting a partly-trained sweep."""
    out = []
    for c in CONFIGS:
        if all(pred_path(c, s).exists() for s in SEEDS):
            out.append(c)
    return out


def build_panel(configs=None) -> tuple[pd.DataFrame, dict]:
    """Wide frame: one row per test image, one prediction column per (config, seed)."""
    configs = list(configs or available_configs())
    if not configs:
        raise SystemExit("no configuration has a complete set of predictions yet")
    base = pd.read_csv(pred_path(configs[0], SEEDS[0]))
    keep = ["filename", "patient", "tier", "tier_pooled", "pseudo_label"] + list(ANN_COLS)
    panel = base[keep].copy()
    for c in configs:
        for s in SEEDS:
            d = pd.read_csv(pred_path(c, s))
            if list(d.filename) != list(panel.filename):
                raise SystemExit(f"{c} seed{s}: row order differs from the panel")
            panel[f"pred_{c}_{s}"] = d.y_pred.to_numpy()
            panel[f"conf_{c}_{s}"] = d.confidence.to_numpy()
    panel[POOLED_CONTESTED] = panel.tier_pooled.isin(CONTESTED)
    return panel, {"configs": configs, "seeds": list(SEEDS)}


def stratum_mask(panel: pd.DataFrame, stratum: str) -> np.ndarray:
    if stratum == POOLED_CONTESTED:
        return panel[POOLED_CONTESTED].to_numpy()
    return (panel.tier_pooled == stratum).to_numpy()


def patient_resamples(patients: np.ndarray, n_boot: int, seed: int = BOOT_SEED):
    """Yield row-index arrays for `n_boot` patient-clustered resamples.

    Precomputing the index arrays once and reusing them for every configuration
    is what makes the comparison paired.
    """
    rng = np.random.default_rng(seed)
    uniq = np.unique(patients)
    by_pat = {p: np.where(patients == p)[0] for p in uniq}
    for _ in range(n_boot):
        pick = rng.choice(uniq, len(uniq), replace=True)
        yield np.concatenate([by_pat[p] for p in pick])


def paired_bootstrap(panel: pd.DataFrame, mask: np.ndarray, fn_a, fn_b,
                     n_boot: int = N_BOOT_PAIR, seed: int = BOOT_SEED):
    """95% CI on fn_a - fn_b, both evaluated on the same patient resample.

    fn_* take an integer row-index array (into the FULL panel) and return a scalar.
    """
    rows = np.where(mask)[0]
    pats = panel.patient.to_numpy()[rows]
    diffs = []
    for local in patient_resamples(pats, n_boot, seed):
        r = rows[local]
        diffs.append(fn_a(r) - fn_b(r))
    d = np.asarray([x for x in diffs if np.isfinite(x)])
    return d


def verdict(lo: float, hi: float, favour_negative: bool = False) -> str:
    """Pre-registered three-way verdict from an interval on a difference."""
    if lo > 0:
        return "NOT SUPPORTED" if favour_negative else "SUPPORTED"
    if hi < 0:
        return "SUPPORTED" if favour_negative else "NOT SUPPORTED"
    return "NOT RESOLVED"
