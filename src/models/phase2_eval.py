"""
Phase 2 / Stage E5-E12 -- test-set evaluation, patient-clustered uncertainty
and the reproduction verdict.

The test set is touched once per seed, after model selection has been made on
validation macro F1. All intervals are obtained by resampling PATIENTS, never
images: Phase 0 measured per-patient Fleiss kappa at 0.7459 +/- 0.1448, so
images within a patient are not independent observations (blueprint sec.6).

Metrics: macro F1 (primary); macro/weighted precision and recall; accuracy;
per-class F1 and recall with Wilson intervals (exploratory, limitation L1);
23x23 confusion matrix. ECE / Brier are recorded as a descriptive baseline for
later comparison, not as a Phase 2 claim.

Outputs
  reports/phase2_test_metrics.json
  reports/phase2_predictions_seed<k>.csv
Run:  python src/models/phase2_eval.py
"""
from __future__ import annotations

import json
import time
from pathlib import Path

import numpy as np
import pandas as pd
import torch
import torch.nn as nn
from sklearn.metrics import (accuracy_score, confusion_matrix, f1_score,
                             precision_score, recall_score)
from torch.utils.data import DataLoader

from phase2_train import CohortDataset, build_model

ROOT = Path(__file__).resolve().parents[2]
CACHE = ROOT / "data" / "phase2_cache_224.npy"
INDEX = ROOT / "data" / "phase2_cache_index.csv"
CLASS_INDEX = ROOT / "data" / "phase2_class_index.json"
NORM = ROOT / "reports" / "phase2_norm_stats.json"
PREREG = ROOT / "reports" / "phase2_prereg.json"
CKPT = ROOT / "checkpoints"
REPORTS = ROOT / "reports"
OUT = REPORTS / "phase2_test_metrics.json"

N_BOOT = 1000
BOOT_SEED = 20260726
N_BINS = 15


def wilson(k: int, n: int, z: float = 1.96):
    if n == 0:
        return (float("nan"), float("nan"))
    p = k / n
    d = 1 + z ** 2 / n
    c = (p + z ** 2 / (2 * n)) / d
    h = z * np.sqrt(p * (1 - p) / n + z ** 2 / (4 * n ** 2)) / d
    return (max(0.0, c - h), min(1.0, c + h))


def ece_and_brier(prob: np.ndarray, y: np.ndarray, n_bins: int = N_BINS):
    conf = prob.max(1)
    pred = prob.argmax(1)
    correct = (pred == y).astype(float)
    edges = np.linspace(0, 1, n_bins + 1)
    ece, bins = 0.0, []
    for i in range(n_bins):
        m = (conf > edges[i]) & (conf <= edges[i + 1])
        if m.sum() == 0:
            bins.append({"bin": i, "n": 0, "conf": None, "acc": None})
            continue
        c, a = float(conf[m].mean()), float(correct[m].mean())
        ece += m.mean() * abs(a - c)
        bins.append({"bin": i, "lo": round(edges[i], 3), "hi": round(edges[i + 1], 3),
                     "n": int(m.sum()), "conf": round(c, 4), "acc": round(a, 4)})
    onehot = np.zeros_like(prob)
    onehot[np.arange(len(y)), y] = 1.0
    brier = float(((prob - onehot) ** 2).sum(1).mean())
    return float(ece), brier, bins


def patient_bootstrap(df: pd.DataFrame, n_classes: int, n_boot: int = N_BOOT):
    """Resample patients with replacement; recompute macro F1 each time."""
    rng = np.random.default_rng(BOOT_SEED)
    pats = df["patient"].unique()
    by_pat = {p: g for p, g in df.groupby("patient")}
    labels = list(range(n_classes))
    vals = np.empty(n_boot)
    for b in range(n_boot):
        pick = rng.choice(pats, size=len(pats), replace=True)
        sub = pd.concat([by_pat[p] for p in pick], ignore_index=True)
        vals[b] = f1_score(sub.y_true, sub.y_pred, average="macro",
                           labels=labels, zero_division=0)
    return vals


def published_style_interval(df: pd.DataFrame, n_classes: int, B: int = 100):
    """Reproduce the descriptor's own stability procedure, for comparability.

    Sci Data 12:102 (2025): '100 iterations applied to the testing set. At each
    iteration, 50% of the complete consensus-labeled samples for each patient
    were randomly and independently selected', with the interval formed as
    mean +/- t(0.975, B-1) * s / sqrt(B).

    That last quantity is the standard error of the bootstrap MEAN, which
    shrinks as 1/sqrt(B) and is therefore not a 95% interval on model
    performance. It is computed here only so that the published margins of
    roughly +/-0.2 can be compared with something constructed the same way.
    """
    from scipy.stats import t as tdist
    rng = np.random.default_rng(BOOT_SEED)
    labels = list(range(n_classes))
    by_pat = [g.index.to_numpy() for _, g in df.groupby("patient")]
    vals = np.empty(B)
    for b in range(B):
        take = np.concatenate([rng.choice(ix, size=max(1, len(ix) // 2),
                                          replace=False) for ix in by_pat])
        sub = df.loc[take]
        vals[b] = f1_score(sub.y_true, sub.y_pred, average="macro",
                           labels=labels, zero_division=0)
    mean = float(vals.mean())
    sem = float(vals.std(ddof=1) / np.sqrt(B))
    moe = float(tdist.ppf(0.975, B - 1) * sem)
    return {"mean": round(100 * mean, 4), "margin_of_error": round(100 * moe, 4),
            "sd_across_iterations": round(100 * float(vals.std(ddof=1)), 4),
            "n_iterations": B,
            "procedure": "descriptor replication: 50% within-patient subsample, "
                         "interval = mean +/- t*s/sqrt(B)"}


def metrics_for(df: pd.DataFrame, n_classes: int) -> dict:
    lab = list(range(n_classes))
    t, p = df.y_true.values, df.y_pred.values
    return {
        "macro_f1": float(f1_score(t, p, average="macro", labels=lab, zero_division=0)),
        "weighted_f1": float(f1_score(t, p, average="weighted", labels=lab, zero_division=0)),
        "macro_precision": float(precision_score(t, p, average="macro", labels=lab, zero_division=0)),
        "macro_recall": float(recall_score(t, p, average="macro", labels=lab, zero_division=0)),
        "weighted_precision": float(precision_score(t, p, average="weighted", labels=lab, zero_division=0)),
        "weighted_recall": float(recall_score(t, p, average="weighted", labels=lab, zero_division=0)),
        "accuracy": float(accuracy_score(t, p)),
    }


def main() -> None:
    t0 = time.time()
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    cls = json.load(open(CLASS_INDEX, encoding="utf-8"))
    inv = {v: k for k, v in cls.items()}
    n_classes = len(cls)
    ns = json.load(open(NORM, encoding="utf-8"))
    idx = pd.read_csv(INDEX)
    arr = np.load(CACHE, mmap_mode="r")
    rows = np.where(idx.set_type == "Test")[0]
    ds = CohortDataset(CACHE, rows, idx.y.values[rows], False,
                       ns["mean"], ns["std"])
    loader = DataLoader(ds, batch_size=24, shuffle=False, num_workers=0)

    ckpts = sorted(CKPT.glob("phase2_convnext_tiny_seed*.pt"))
    if not ckpts:
        raise SystemExit("no checkpoints found; run phase2_train.py first")

    per_seed, boot_store = {}, {}
    for cp in ckpts:
        blob = torch.load(cp, map_location="cpu", weights_only=False)
        seed = int(blob["seed"])
        model = build_model(n_classes)
        model.load_state_dict(blob["state_dict"])
        model.to(device).eval()

        probs = []
        with torch.no_grad():
            for x, _ in loader:
                x = x.to(device)
                with torch.autocast("cuda", dtype=torch.float16,
                                    enabled=device.type == "cuda"):
                    out = model(x)
                probs.append(torch.softmax(out.float(), 1).cpu().numpy())
        prob = np.concatenate(probs)
        pred = prob.argmax(1)
        true = idx.y.values[rows]

        pdf = pd.DataFrame({
            "filename": idx.filename.values[rows],
            "patient": idx.patient.values[rows],
            "y_true": true, "y_pred": pred,
            "label_true": [inv[i] for i in true],
            "label_pred": [inv[i] for i in pred],
            "confidence": prob.max(1),
        })
        pdf.to_csv(REPORTS / f"phase2_predictions_seed{seed}.csv", index=False)

        m = metrics_for(pdf, n_classes)
        boot = patient_bootstrap(pdf, n_classes)
        boot_store[seed] = boot
        pub = published_style_interval(pdf, n_classes)
        ece, brier, bins = ece_and_brier(prob, true)

        percls = []
        cm = confusion_matrix(true, pred, labels=list(range(n_classes)))
        for c in range(n_classes):
            sup = int(cm[c].sum())
            tp = int(cm[c, c])
            lo, hi = wilson(tp, sup)
            percls.append({
                "class": inv[c], "support": sup,
                "recall": round(tp / sup, 4) if sup else None,
                "recall_wilson_lo": round(lo, 4), "recall_wilson_hi": round(hi, 4),
                "wilson_half_width_pp": round(100 * (hi - lo) / 2, 2),
                "precision": round(float(precision_score(
                    true, pred, labels=[c], average="macro", zero_division=0)), 4),
                "f1": round(float(f1_score(
                    true, pred, labels=[c], average="macro", zero_division=0)), 4),
            })

        per_seed[seed] = {
            **{k: round(v, 5) for k, v in m.items()},
            "macro_f1_boot_mean": round(float(boot.mean()), 5),
            "macro_f1_boot_sd": round(float(boot.std(ddof=1)), 5),
            "macro_f1_ci95": [round(float(np.percentile(boot, 2.5)), 5),
                              round(float(np.percentile(boot, 97.5)), 5)],
            "published_style_interval": pub,
            "ece": round(ece, 5), "brier": round(brier, 5),
            "reliability_bins": bins,
            "per_class": percls,
            "confusion_matrix": cm.tolist(),
        }
        print(f"seed {seed}: macro F1 = {m['macro_f1']:.4f}  "
              f"CI [{per_seed[seed]['macro_f1_ci95'][0]:.4f}, "
              f"{per_seed[seed]['macro_f1_ci95'][1]:.4f}]  ECE={ece:.4f}",
              flush=True)

    seeds = sorted(per_seed)
    f1s = np.array([per_seed[s]["macro_f1"] for s in seeds])
    boot_mean = np.mean([boot_store[s] for s in seeds], axis=0)   # seed-mean dist

    # ---- reproduction verdict -------------------------------------------
    pre = json.load(open(PREREG, encoding="utf-8"))
    target = pre["published_macro_f1"]
    band = pre["acceptance_band_points"]
    obs = float(f1s.mean()) * 100
    delta = obs - target
    verdict = "PASS" if abs(delta) <= band else "FAIL"

    out = {
        "generated": time.strftime("%Y-%m-%d %H:%M:%S"),
        "n_test_images": int(len(rows)),
        "n_test_patients": int(idx.patient.values[rows].__len__() and
                               pd.Series(idx.patient.values[rows]).nunique()),
        "n_boot": N_BOOT, "boot_unit": "patient", "boot_seed": BOOT_SEED,
        "seeds": seeds,
        "per_seed": per_seed,
        "aggregate": {
            "macro_f1_mean": round(float(f1s.mean()), 5),
            "macro_f1_sd": round(float(f1s.std(ddof=1)), 5) if len(f1s) > 1 else None,
            "macro_f1_min": round(float(f1s.min()), 5),
            "macro_f1_max": round(float(f1s.max()), 5),
            "macro_f1_range_points": round(float(100 * (f1s.max() - f1s.min())), 3),
            "seed_mean_boot_ci95": [round(float(np.percentile(boot_mean, 2.5)), 5),
                                    round(float(np.percentile(boot_mean, 97.5)), 5)],
        },
        "reproduction": {
            "published_macro_f1": target,
            "published_sd": pre.get("published_sd"),
            "published_source": pre["published_source"],
            "published_condition": pre["published_condition"],
            "acceptance_band_points": band,
            "observed_macro_f1": round(obs, 3),
            "delta_points": round(delta, 3),
            "abs_delta_points": round(abs(delta), 3),
            "verdict": verdict,
        },
        "runtime_sec": round(time.time() - t0, 1),
    }
    OUT.write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(f"\nGATE 5  observed {obs:.2f} vs published {target} "
          f"(band +/-{band}) -> {verdict}")


if __name__ == "__main__":
    main()
