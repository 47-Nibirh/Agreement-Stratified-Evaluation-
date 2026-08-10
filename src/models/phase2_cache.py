"""
Phase 2 / Stage C1 -- deterministic preprocessing cache.

The cohort is decoded once, resampled to 224x224 with Lanczos exactly as the
Phase 2 specification requires, and written to a uint8 memmap. Every epoch
thereafter reads from the cache, so preprocessing is performed identically for
every seed and every configuration and cannot drift between runs.

This is a performance decision with a methodological benefit: the resampling
is applied once, so train, validation and test images pass through the same
code path, and later phases can reuse the identical tensor cache.

Outputs
  data/phase2_cache_224.npy    (5318, 224, 224, 3) uint8
  data/phase2_cache_index.csv  row order, labels, splits, patients
Run:  python src/models/phase2_cache.py
"""
from __future__ import annotations

import json
import time
from pathlib import Path

import numpy as np
import pandas as pd
from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
MANIFEST = ROOT / "data" / "phase2_consensus_manifest.csv"
CLASS_INDEX = ROOT / "data" / "phase2_class_index.json"
IMAGE_ROOT = ROOT / "Labeled Images"
CACHE = ROOT / "data" / "phase2_cache_224.npy"
INDEX = ROOT / "data" / "phase2_cache_index.csv"
SIZE = 224


def main() -> None:
    t0 = time.time()
    df = pd.read_csv(MANIFEST).reset_index(drop=True)
    cls = json.load(open(CLASS_INDEX, encoding="utf-8"))
    df["y"] = df["label"].map(cls).astype(int)

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

    df[["filename", "patient", "set_type", "label", "y", "source_type"]].to_csv(
        INDEX, index=False)
    print(f"cached {n} images -> {CACHE.name} "
          f"({CACHE.stat().st_size / 1e6:.0f} MB) in {time.time() - t0:.1f}s")


if __name__ == "__main__":
    main()
