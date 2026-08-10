"""
Phase 3B -- shared metric primitives.

Everything here is a drop-in numerical equivalent of what phase3_eval.py did
with scikit-learn, rewritten with bincount so that the 6 pairwise x 3 seed x
1,000-resample patient-clustered bootstraps this phase adds are affordable on
the project's hardware. `selftest()` asserts equality against sklearn to 1e-12
and is run at import time by every Phase 3B script, so the speed-up can never
silently change a published number.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

ANN_COLS = ["vote_0", "vote_1", "vote_2", "vote_3"]
TIER_ORDER = ["S-unanimous", "S-majority", "S-plurality", "S-no-majority"]
TIER_ORDER_FULL = ["S-unanimous", "S-majority", "S-plurality", "S-tied", "S-dispersed"]
ARCH_GAP_BENCHMARK = 3.25
BOOT_SEED = 20260726
N_BOOT = 1000


def macro_f1(y: np.ndarray, p: np.ndarray, k: int) -> float:
    """macro F1 over the full k-class label set, zero_division=0.

    Identical to sklearn.metrics.f1_score(average='macro', labels=range(k),
    zero_division=0): a class absent from both y and p contributes 0.
    """
    tp = np.bincount(y[y == p], minlength=k)
    nt = np.bincount(y, minlength=k)
    np_ = np.bincount(p, minlength=k)
    den = nt + np_
    f1 = np.zeros(k)
    nz = den > 0
    f1[nz] = 2.0 * tp[nz] / den[nz]
    return float(f1.mean())


def marginalized_macro_f1(votes_idx: np.ndarray, pred: np.ndarray, k: int) -> float:
    """Annotator-marginalized macro F1 (Phase 3 primary metric).

    votes_idx: (n,4) int class indices, one column per annotator.
    """
    return float(np.mean([macro_f1(votes_idx[:, a], pred, k) for a in range(4)]))


def expected_accuracy(votes_idx: np.ndarray, pred: np.ndarray) -> float:
    return float((votes_idx == pred[:, None]).mean())


def any_hit_rate(votes_idx: np.ndarray, pred: np.ndarray) -> float:
    return float((votes_idx == pred[:, None]).any(axis=1).mean())


def votes_to_idx(df: pd.DataFrame, cls: dict) -> np.ndarray:
    return np.stack([df[c].map(cls).to_numpy() for c in ANN_COLS], axis=1)


def modal_oracle(votes_idx: np.ndarray, rng: np.random.Generator) -> np.ndarray:
    """Per-image label with the most annotator votes; ties broken at random.

    This is the *achievable* reference predictor: the best a single-label
    classifier can do image-by-image under the vote distribution. It is a
    lower bound on the supremum of macro F1 (macro F1 does not decompose
    per image) and an exact maximiser of expected accuracy.
    """
    n = votes_idx.shape[0]
    out = np.empty(n, dtype=int)
    for i in range(n):
        v, c = np.unique(votes_idx[i], return_counts=True)
        best = v[c == c.max()]
        out[i] = best[0] if len(best) == 1 else rng.choice(best)
    return out


def max_expected_accuracy(votes_idx: np.ndarray) -> float:
    """Exact supremum of expected accuracy for any single-label predictor."""
    n = votes_idx.shape[0]
    best = np.empty(n)
    for i in range(n):
        _, c = np.unique(votes_idx[i], return_counts=True)
        best[i] = c.max() / 4.0
    return float(best.mean())


def patient_bootstrap(df: pd.DataFrame, fn, n_boot: int = N_BOOT,
                      seed: int = BOOT_SEED) -> np.ndarray:
    """Patient-clustered bootstrap; `fn` maps a resampled frame to a scalar."""
    rng = np.random.default_rng(seed)
    pats = df["patient"].unique()
    groups = {p: g for p, g in df.groupby("patient")}
    vals = np.empty(n_boot)
    for b in range(n_boot):
        sub = pd.concat([groups[p] for p in rng.choice(pats, len(pats), True)],
                        ignore_index=True)
        vals[b] = fn(sub)
    return vals


def ci95(v: np.ndarray) -> list:
    return [float(np.percentile(v, 2.5)), float(np.percentile(v, 97.5))]


def selftest() -> None:
    from sklearn.metrics import f1_score
    rng = np.random.default_rng(0)
    for k, n in ((23, 400), (23, 40), (5, 30)):
        y = rng.integers(0, k, n)
        p = rng.integers(0, k, n)
        a = macro_f1(y, p, k)
        b = f1_score(y, p, average="macro", labels=list(range(k)), zero_division=0)
        assert abs(a - b) < 1e-12, f"macro_f1 mismatch: {a} vs {b}"


selftest()
