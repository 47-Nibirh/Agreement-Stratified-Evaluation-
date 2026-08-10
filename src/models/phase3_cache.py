"""
Phase 3 / Stage B -- preprocessing cache for the full test split.

Identical resize path to phase2_cache.py (RGB, 224x224, Lanczos) applied to
all 1,353 official test images (not just the 803-image complete-agreement
subset Phase 2 cached). This is what lets Phase 3 evaluate the frozen Phase 2
checkpoints on strata they were never validated against.

Outputs
  data/phase3_cache_224.npy    (1353, 224, 224, 3) uint8
  data/phase3_cache_index.csv  row order matching phase3_test_manifest.csv
Run:  python src/models/phase3_cache.py
"""
from __future__ import annotations

import time
from pathlib import Path

import numpy as np
import pandas as pd
from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
MANIFEST = ROOT / "data" / "phase3_test_manifest.csv"
IMAGE_ROOT = ROOT / "Labeled Images"
CACHE = ROOT / "data" / "phase3_cache_224.npy"
INDEX = ROOT / "data" / "phase3_cache_index.csv"
SIZE = 224


def main() -> None:
    t0 = time.time()
    df = pd.read_csv(MANIFEST).reset_index(drop=True)
    n = len(df)

    missing = [p for p in df["relpath"] if not (IMAGE_ROOT / p).exists()]
    if missing:
        raise SystemExit(f"{len(missing)} manifest images not found on disk, e.g. {missing[:5]}")

    arr = np.lib.format.open_memmap(
        CACHE, mode="w+", dtype=np.uint8, shape=(n, SIZE, SIZE, 3))
    for i, rel in enumerate(df["relpath"]):
        img = Image.open(IMAGE_ROOT / rel).convert("RGB").resize(
            (SIZE, SIZE), Image.Resampling.LANCZOS)
        arr[i] = np.asarray(img, dtype=np.uint8)
        if (i + 1) % 250 == 0:
            print(f"  {i + 1}/{n}", flush=True)
    arr.flush()

    df.to_csv(INDEX, index=False)
    print(f"cached {n} images -> {CACHE.name} "
          f"({CACHE.stat().st_size / 1e6:.0f} MB) in {time.time() - t0:.1f}s")


if __name__ == "__main__":
    main()
