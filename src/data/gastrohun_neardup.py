"""
Phase 0 / Step 3 - Near-duplicate and cross-split contamination audit.

Reads the cached hash table produced by gastrohun_inventory.py and searches for
perceptually near-identical image pairs. Two images that are near-identical but
sit on opposite sides of a train/test boundary constitute optimistic bias; this
is the single most common silent defect in endoscopy-imaging papers, because
consecutive video frames of the same anatomical site look almost identical.

Method
------
1. Exhaustive all-pairs Hamming distance on the 64-bit dHash, computed in
   blocks via matrix multiplication over +/-1 encoded bits (8834^2 / 2 = 39M
   pairs - tractable, so no LSH approximation and no false negatives).
2. Threshold sweep at Hamming <= 0, 2, 4, 6, 8 reported separately for
   within-patient, cross-patient-within-split, and cross-split pairs.
3. Every cross-split candidate at the operative threshold is re-verified at
   pixel level: images are decoded, resized to a common 256x256 grayscale
   canvas, and normalised RMS difference + Pearson correlation are computed.
   dHash collisions that are not genuine duplicates are thereby rejected.

Output: reports/gastrohun_neardup.json

Run:  python src/data/gastrohun_neardup.py
"""

from __future__ import annotations

import json
import time
from pathlib import Path

import numpy as np
import pandas as pd
from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
IMG_ROOT = ROOT / "Labeled Images"
HASHES = ROOT / "reports" / "gastrohun_hashes.csv"
SPLITS = ROOT / "official_splits" / "image_classification.csv"
OUT = ROOT / "reports" / "gastrohun_neardup.json"

THRESHOLDS = [0, 2, 4, 6, 8]
OPERATIVE = 6          # candidates at or below this are pixel-verified
RMS_DUP = 0.10         # normalised RMS below this => genuine duplicate
CORR_DUP = 0.95        # and Pearson correlation above this


def load_bits(df: pd.DataFrame) -> np.ndarray:
    return np.array([[int(c) for c in h] for h in df["dhash"]], dtype=np.int8)


def pixel_compare(pa: Path, pb: Path, size: int = 256) -> tuple[float, float]:
    with Image.open(pa) as ia, Image.open(pb) as ib:
        a = np.asarray(ia.convert("L").resize((size, size), Image.LANCZOS), dtype=np.float64)
        b = np.asarray(ib.convert("L").resize((size, size), Image.LANCZOS), dtype=np.float64)
    rms = float(np.sqrt(np.mean((a - b) ** 2)) / 255.0)
    av, bv = a.ravel() - a.mean(), b.ravel() - b.mean()
    denom = np.sqrt((av**2).sum() * (bv**2).sum())
    corr = float((av * bv).sum() / denom) if denom > 0 else 0.0
    return rms, corr


def main() -> None:
    t0 = time.time()
    # dhash is a 64-char binary string; force str so pandas does not read the
    # all-digit column as an integer and silently drop leading zeros.
    df = pd.read_csv(HASHES, dtype={"dhash": str, "sha256": str})
    df["dhash"] = df["dhash"].str.zfill(64)
    spl = pd.read_csv(SPLITS, index_col=0)
    lab = spl.set_index("filename")["Complete agreement"]
    df["consensus"] = df["filename"].map(lab)

    n = len(df)
    bits = load_bits(df)
    pm = (2 * bits - 1).astype(np.float32)      # {0,1} -> {-1,+1}

    pat = df["patient"].to_numpy()
    spt = df["set_type"].to_numpy()
    fn = df["filename"].to_numpy()
    folder = df["folder"].to_numpy()

    # ---- exhaustive pair scan in row blocks ------------------------------
    tally = {t: {"within_patient": 0, "cross_patient_same_split": 0, "cross_split": 0}
             for t in THRESHOLDS}
    candidates: list[tuple[int, int, int]] = []      # (i, j, hamming) cross-split
    cross_patient_cand: list[tuple[int, int, int]] = []

    BLK = 512
    for s in range(0, n, BLK):
        e = min(s + BLK, n)
        # hamming = (64 - dot) / 2
        dot = pm[s:e] @ pm.T
        ham = ((64.0 - dot) / 2.0).round().astype(np.int16)
        for local, i in enumerate(range(s, e)):
            row = ham[local]
            js = np.where(row <= max(THRESHOLDS))[0]
            js = js[js > i]                          # strict upper triangle only
            for j in js:
                h = int(row[j])
                same_pat = pat[i] == pat[j]
                same_spt = spt[i] == spt[j]
                for t in THRESHOLDS:
                    if h <= t:
                        if same_pat:
                            tally[t]["within_patient"] += 1
                        elif same_spt:
                            tally[t]["cross_patient_same_split"] += 1
                        else:
                            tally[t]["cross_split"] += 1
                if h <= OPERATIVE and not same_pat:
                    if not same_spt:
                        candidates.append((i, int(j), h))
                    else:
                        cross_patient_cand.append((i, int(j), h))
        if (s // BLK) % 4 == 0:
            print(f"  scanned {e}/{n} ({time.time()-t0:.0f}s)", flush=True)

    # ---- pixel-level verification of every cross-split candidate ---------
    verified = []
    for i, j, h in candidates:
        pa = IMG_ROOT / str(folder[i]) / fn[i]
        pb = IMG_ROOT / str(folder[j]) / fn[j]
        rms, corr = pixel_compare(pa, pb)
        verified.append(
            {
                "a": str(fn[i]), "b": str(fn[j]), "hamming": h,
                "patient_a": int(pat[i]), "patient_b": int(pat[j]),
                "split_a": str(spt[i]), "split_b": str(spt[j]),
                "label_a": (None if pd.isna(df["consensus"].iloc[i])
                            else str(df["consensus"].iloc[i])),
                "label_b": (None if pd.isna(df["consensus"].iloc[j])
                            else str(df["consensus"].iloc[j])),
                "rms": round(rms, 4), "corr": round(corr, 4),
                "is_duplicate": bool(rms < RMS_DUP and corr > CORR_DUP),
            }
        )
    true_dups = [v for v in verified if v["is_duplicate"]]

    # sample-verify the same-split cross-patient candidates for a false-positive rate
    rng = np.random.default_rng(20260726)
    sample = (rng.choice(len(cross_patient_cand),
                         size=min(300, len(cross_patient_cand)), replace=False)
              if cross_patient_cand else [])
    sampled = []
    for k in sample:
        i, j, h = cross_patient_cand[int(k)]
        rms, corr = pixel_compare(IMG_ROOT / str(folder[i]) / fn[i],
                                  IMG_ROOT / str(folder[j]) / fn[j])
        sampled.append({"hamming": h, "rms": round(rms, 4), "corr": round(corr, 4),
                        "is_duplicate": bool(rms < RMS_DUP and corr > CORR_DUP)})
    fp_rate = (round(100 * (1 - sum(s["is_duplicate"] for s in sampled) / len(sampled)), 2)
               if sampled else None)

    # ---- within-patient redundancy: how much is each patient's set duplicated? ----
    wp = tally[OPERATIVE]["within_patient"]
    n_pairs_within_possible = int(
        pd.Series(pat).value_counts().map(lambda c: c * (c - 1) // 2).sum()
    )

    res = {
        "generated": time.strftime("%Y-%m-%d %H:%M:%S"),
        "n_images": n,
        "n_pairs_examined": n * (n - 1) // 2,
        "method": "exhaustive 64-bit dHash Hamming + pixel verification",
        "threshold_sweep": {str(t): tally[t] for t in THRESHOLDS},
        "operative_threshold": OPERATIVE,
        "within_patient_pairs_possible": n_pairs_within_possible,
        "within_patient_neardup_rate_pct": round(100 * wp / n_pairs_within_possible, 4),
        "cross_split_candidates": len(candidates),
        "cross_split_verified_duplicates": len(true_dups),
        # full list, not a sample: the calibration step re-scores every one
        "cross_split_duplicate_examples": true_dups,
        "cross_split_rejected_examples": [v for v in verified if not v["is_duplicate"]][:10],
        "cross_split_rms_summary": {
            "min": round(float(min((v["rms"] for v in verified), default=float("nan"))), 4),
            "median": round(float(np.median([v["rms"] for v in verified])), 4) if verified else None,
            "max": round(float(max((v["rms"] for v in verified), default=float("nan"))), 4),
        },
        "cross_patient_same_split_candidates": len(cross_patient_cand),
        "cross_patient_sample_verified": len(sampled),
        "cross_patient_dhash_false_positive_pct": fp_rate,
        "decision_rules": {
            "rms_threshold": RMS_DUP,
            "corr_threshold": CORR_DUP,
            "duplicate_if": "rms < 0.10 AND pearson_r > 0.95",
        },
        "runtime_sec": round(time.time() - t0, 1),
    }
    OUT.write_text(json.dumps(res, indent=2), encoding="utf-8")
    print(json.dumps({k: v for k, v in res.items() if "examples" not in k}, indent=2))


if __name__ == "__main__":
    main()
