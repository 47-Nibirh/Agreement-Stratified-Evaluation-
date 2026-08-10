"""
Phase 2 / Stage B6 -- training-set channel statistics.

Blueprint v3.0 sec.4 PHASE 2 requires normalisation with *training-set*
statistics, not the ImageNet defaults. Statistics are computed at the final
preprocessing resolution (224x224 Lanczos) over the 3,722 complete-agreement
training images only -- never validation or test, which would leak.

Uses a streaming (sum, sum-of-squares) accumulation so the result is exact
rather than a running approximation.

Output: reports/phase2_norm_stats.json
Run:    python src/models/phase2_normstats.py
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
IMAGE_ROOT = ROOT / "Labeled Images"
OUT = ROOT / "reports" / "phase2_norm_stats.json"

SIZE = 224
IMAGENET_MEAN = [0.485, 0.456, 0.406]
IMAGENET_STD = [0.229, 0.224, 0.225]


def main() -> None:
    t0 = time.time()
    df = pd.read_csv(MANIFEST)
    tr = df[df.set_type == "Train"]
    n = len(tr)

    s = np.zeros(3, dtype=np.float64)
    ss = np.zeros(3, dtype=np.float64)
    npix = 0

    for i, rel in enumerate(tr["relpath"], 1):
        img = Image.open(IMAGE_ROOT / rel).convert("RGB").resize(
            (SIZE, SIZE), Image.Resampling.LANCZOS)
        a = np.asarray(img, dtype=np.float64) / 255.0
        s += a.sum(axis=(0, 1))
        ss += (a ** 2).sum(axis=(0, 1))
        npix += a.shape[0] * a.shape[1]
        if i % 500 == 0:
            print(f"  {i}/{n}", flush=True)

    mean = s / npix
    var = ss / npix - mean ** 2
    std = np.sqrt(var)

    out = {
        "generated": time.strftime("%Y-%m-%d %H:%M:%S"),
        "split_used": "Train (complete-agreement only)",
        "n_images": int(n),
        "n_pixels_per_channel": int(npix),
        "resample": "LANCZOS",
        "size": SIZE,
        "mean": [round(float(x), 6) for x in mean],
        "std": [round(float(x), 6) for x in std],
        "imagenet_mean": IMAGENET_MEAN,
        "imagenet_std": IMAGENET_STD,
        "abs_delta_mean": [round(abs(float(a) - b), 6)
                           for a, b in zip(mean, IMAGENET_MEAN)],
        "abs_delta_std": [round(abs(float(a) - b), 6)
                          for a, b in zip(std, IMAGENET_STD)],
        "runtime_sec": round(time.time() - t0, 1),
    }
    OUT.write_text(json.dumps(out, indent=2), encoding="utf-8")
    print("mean", out["mean"], "std", out["std"])
    print(f"wrote {OUT.name} in {out['runtime_sec']}s")


if __name__ == "__main__":
    main()
