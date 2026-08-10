"""
Phase 4 / Stage B -- deterministic 224x224 cache for the extended cohort.

Same code path as phase2_cache.py (decode -> RGB -> Lanczos 224 -> uint8), so
the tensors the Phase 4 configurations see are produced by the identical
preprocessing that produced the Phase 2 baseline. That is not merely a
convenience: C0 is the reference arm of this phase's comparison, so if the
pixels differed, every C-vs-C0 difference would be partly a preprocessing
difference.

GATE P4.2  byte-identity. Every image in this cache that is also in the Phase 2
cache (the 4,515 unanimous Train/Validation images) must decode to a
bit-identical uint8 array. The check is exhaustive, not sampled.

Outputs
  data/phase4_cache_224.npy    (6331, 224, 224, 3) uint8
  data/phase4_cache_index.csv
  reports/phase4_cache_gate.json
Run:  python src/models/phase4_cache.py
"""
from __future__ import annotations

import json
import time
from pathlib import Path

import numpy as np
import pandas as pd
from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
MANIFEST = ROOT / "data" / "phase4_train_manifest.csv"
CLASS_INDEX = ROOT / "data" / "phase2_class_index.json"
IMAGE_ROOT = ROOT / "Labeled Images"
CACHE = ROOT / "data" / "phase4_cache_224.npy"
INDEX = ROOT / "data" / "phase4_cache_index.csv"
P2_CACHE = ROOT / "data" / "phase2_cache_224.npy"
P2_INDEX = ROOT / "data" / "phase2_cache_index.csv"
GATE = ROOT / "reports" / "phase4_cache_gate.json"
SIZE = 224
ANN_COLS = ["vote_0", "vote_1", "vote_2", "vote_3"]


def main() -> None:
    t0 = time.time()
    df = pd.read_csv(MANIFEST).reset_index(drop=True)
    cls = json.load(open(CLASS_INDEX, encoding="utf-8"))
    df["y"] = df["majority_label"].map(cls).astype(int)
    for c in ANN_COLS:
        df[c + "_y"] = df[c].map(cls).astype(int)

    n = len(df)
    arr = np.lib.format.open_memmap(
        CACHE, mode="w+", dtype=np.uint8, shape=(n, SIZE, SIZE, 3))
    for i, rel in enumerate(df["relpath"]):
        img = Image.open(IMAGE_ROOT / rel).convert("RGB").resize(
            (SIZE, SIZE), Image.Resampling.LANCZOS)
        arr[i] = np.asarray(img, dtype=np.uint8)
        if (i + 1) % 1000 == 0:
            print(f"  {i + 1}/{n}", flush=True)
    arr.flush()

    cols = (["filename", "patient", "set_type", "tier", "majority_label", "y",
             "source_type"] + ANN_COLS + [c + "_y" for c in ANN_COLS])
    df[cols].to_csv(INDEX, index=False)

    # ---- GATE P4.2: byte-identity against the Phase 2 cache -----------------
    p2i = pd.read_csv(P2_INDEX)
    p2a = np.load(P2_CACHE, mmap_mode="r")
    p2_row = {f: i for i, f in enumerate(p2i.filename)}
    shared = [(i, p2_row[f]) for i, f in enumerate(df.filename) if f in p2_row]
    n_mismatch = 0
    for i4, i2 in shared:
        if not np.array_equal(np.asarray(arr[i4]), np.asarray(p2a[i2])):
            n_mismatch += 1
    if n_mismatch:
        raise SystemExit(f"GATE P4.2 FAILED: {n_mismatch}/{len(shared)} shared images "
                         f"differ from the Phase 2 cache")

    out = {
        "generated": time.strftime("%Y-%m-%d %H:%M:%S"),
        "n_images": int(n),
        "shape": [int(n), SIZE, SIZE, 3],
        "dtype": "uint8",
        "resample": "LANCZOS",
        "bytes": int(CACHE.stat().st_size),
        "by_split": {k: int(v) for k, v in df.set_type.value_counts().items()},
        "by_tier": {k: int(v) for k, v in df.tier.value_counts().items()},
        "gate_p4_2_byte_identity": {
            "n_shared_with_phase2_cache": len(shared),
            "n_mismatched": n_mismatch,
            "pass": True,
            "note": ("exhaustive comparison, not sampled; guarantees the Phase 4 "
                     "arms and the Phase 2 reference arm see identical pixels"),
        },
        "runtime_sec": round(time.time() - t0, 1),
    }
    GATE.write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(f"cached {n} images -> {CACHE.name} ({CACHE.stat().st_size / 1e6:.0f} MB)")
    print(f"GATE P4.2 PASS: {len(shared)}/{len(shared)} shared images byte-identical "
          f"to the Phase 2 cache")
    print(f"done in {out['runtime_sec']}s")


if __name__ == "__main__":
    main()
