"""
Phase 0 / Step 1 - Physical inventory and file-level integrity audit of GastroHUN.

Walks the `Labeled Images` tree, verifies every file listed in the official
split manifest exists on disk, decodes each JPEG to confirm it is not truncated,
records true pixel dimensions, and computes both an exact content hash (SHA-256)
and a perceptual hash (dHash, 8x8) for duplicate / near-duplicate detection.

Output: reports/gastrohun_inventory.json  (+ reports/gastrohun_hashes.csv)

Run:  python src/data/gastrohun_inventory.py
"""

from __future__ import annotations

import hashlib
import json
import os
import sys
import time
from collections import Counter
from pathlib import Path

import numpy as np
import pandas as pd
from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
IMG_ROOT = ROOT / "Labeled Images"
SPLITS = ROOT / "official_splits" / "image_classification.csv"
OUT_DIR = ROOT / "reports"
OUT_DIR.mkdir(exist_ok=True)


def dhash(img: Image.Image, size: int = 8) -> str:
    """Difference hash: 64-bit perceptual fingerprint, robust to rescaling/compression."""
    g = img.convert("L").resize((size + 1, size), Image.LANCZOS)
    a = np.asarray(g, dtype=np.int16)
    bits = (a[:, 1:] > a[:, :-1]).flatten()
    return "".join("1" if b else "0" for b in bits)


def hamming(a: str, b: str) -> int:
    return sum(1 for x, y in zip(a, b) if x != y)


def main() -> None:
    manifest = pd.read_csv(SPLITS, index_col=0)
    manifest["patient"] = manifest["num patient"].astype(int)

    # ---- 1. what is actually on disk -------------------------------------
    on_disk: dict[str, Path] = {}
    dir_counts: Counter[str] = Counter()
    for d in sorted(IMG_ROOT.iterdir()):
        if not d.is_dir():
            continue
        for f in d.iterdir():
            if f.is_file():
                on_disk[f.name] = f
                dir_counts[d.name] += 1

    manifest_names = set(manifest["filename"])
    disk_names = set(on_disk)

    missing = sorted(manifest_names - disk_names)      # listed but absent
    orphan = sorted(disk_names - manifest_names)       # present but unlisted

    # ---- 2. decode every image, hash it ----------------------------------
    rows = []
    corrupt = []
    t0 = time.time()
    total = len(manifest)
    for i, (_, r) in enumerate(manifest.iterrows()):
        fn = r["filename"]
        p = on_disk.get(fn)
        if p is None:
            continue
        try:
            raw = p.read_bytes()
            sha = hashlib.sha256(raw).hexdigest()
            with Image.open(p) as im:
                im.load()                      # forces full decode -> catches truncation
                w, h = im.size
                mode = im.mode
                fmt = im.format
                ph = dhash(im)
        except Exception as exc:                # noqa: BLE001
            corrupt.append({"filename": fn, "error": f"{type(exc).__name__}: {exc}"})
            continue
        rows.append(
            {
                "filename": fn,
                "patient": int(r["patient"]),
                "set_type": r["set_type"],
                "folder": p.parent.name,
                "bytes": len(raw),
                "width": w,
                "height": h,
                "mode": mode,
                "format": fmt,
                "sha256": sha,
                "dhash": ph,
            }
        )
        if (i + 1) % 1000 == 0:
            el = time.time() - t0
            print(f"  {i+1}/{total} decoded ({el:.0f}s)", flush=True)

    df = pd.DataFrame(rows)
    df.to_csv(OUT_DIR / "gastrohun_hashes.csv", index=False)

    # ---- 3. folder-vs-manifest patient consistency ------------------------
    folder_mismatch = int((df["folder"].astype(int) != df["patient"]).sum())

    # ---- 4. exact duplicates ---------------------------------------------
    dup_groups = (
        df.groupby("sha256")
        .agg(n=("filename", "size"),
             files=("filename", list),
             patients=("patient", lambda s: sorted(set(s))),
             splits=("set_type", lambda s: sorted(set(s))))
        .query("n > 1")
        .sort_values("n", ascending=False)
    )
    exact_dups = dup_groups.reset_index().to_dict("records")
    exact_dup_cross_split = [d for d in exact_dups if len(d["splits"]) > 1]
    exact_dup_cross_patient = [d for d in exact_dups if len(d["patients"]) > 1]

    # ---- 5. near-duplicates (dHash Hamming <= 4) -------------------------
    # Bucket by hash prefix to keep the comparison tractable, then compare
    # exhaustively inside each bucket and across the 8 single-bit neighbours
    # of the prefix (standard multi-index LSH for Hamming radius search).
    hashes = df["dhash"].to_numpy()
    names = df["filename"].to_numpy()
    pats = df["patient"].to_numpy()
    splits_arr = df["set_type"].to_numpy()

    bits = np.array([[int(c) for c in h] for h in hashes], dtype=np.uint8)

    near_pairs = []
    # 4 bands of 16 bits: any pair within Hamming 4 must match >=1 band exactly
    # (pigeonhole: 4 differing bits cannot cover 5 bands, use 5 bands of 12/13)
    n_bands = 5
    edges = np.linspace(0, 64, n_bands + 1).astype(int)
    seen: set[tuple[int, int]] = set()
    for b in range(n_bands):
        lo, hi = edges[b], edges[b + 1]
        keys = ["".join(map(str, row)) for row in bits[:, lo:hi]]
        buckets: dict[str, list[int]] = {}
        for idx, k in enumerate(keys):
            buckets.setdefault(k, []).append(idx)
        for _, idxs in buckets.items():
            if len(idxs) < 2 or len(idxs) > 400:      # skip degenerate mega-buckets
                continue
            arr = np.array(idxs)
            sub = bits[arr]
            d = (sub[:, None, :] != sub[None, :, :]).sum(axis=2)
            ii, jj = np.where(np.triu(d, 1) > -1)
            for a, c in zip(ii, jj):
                if d[a, c] > 4:
                    continue
                p = (int(arr[a]), int(arr[c]))
                if p in seen:
                    continue
                seen.add(p)
                near_pairs.append(
                    {
                        "a": str(names[p[0]]), "b": str(names[p[1]]),
                        "hamming": int(d[a, c]),
                        "patient_a": int(pats[p[0]]), "patient_b": int(pats[p[1]]),
                        "split_a": str(splits_arr[p[0]]), "split_b": str(splits_arr[p[1]]),
                    }
                )

    near_cross_patient = [p for p in near_pairs if p["patient_a"] != p["patient_b"]]
    near_cross_split = [p for p in near_pairs if p["split_a"] != p["split_b"]]

    # ---- 6. summary -------------------------------------------------------
    res = {
        "generated": time.strftime("%Y-%m-%d %H:%M:%S"),
        "image_root": str(IMG_ROOT),
        "n_manifest_rows": int(len(manifest)),
        "n_manifest_unique_filenames": int(manifest["filename"].nunique()),
        "n_files_on_disk": int(len(disk_names)),
        "n_patient_folders": int(len(dir_counts)),
        "n_decoded_ok": int(len(df)),
        "n_missing_from_disk": len(missing),
        "missing_examples": missing[:20],
        "n_orphan_on_disk": len(orphan),
        "orphan_examples": orphan[:20],
        "n_corrupt": len(corrupt),
        "corrupt": corrupt[:20],
        "folder_patient_mismatch": folder_mismatch,
        "formats": df["format"].value_counts().to_dict(),
        "modes": df["mode"].value_counts().to_dict(),
        "resolutions": {
            f"{w}x{h}": int(c)
            for (w, h), c in df.groupby(["width", "height"]).size().sort_values(ascending=False).items()
        },
        "bytes": {
            "total_gb": round(df["bytes"].sum() / 1024**3, 3),
            "mean_kb": round(df["bytes"].mean() / 1024, 2),
            "median_kb": round(df["bytes"].median() / 1024, 2),
            "min_kb": round(df["bytes"].min() / 1024, 2),
            "max_kb": round(df["bytes"].max() / 1024, 2),
        },
        "images_per_patient": {
            "min": int(df.groupby("patient").size().min()),
            "max": int(df.groupby("patient").size().max()),
            "mean": round(float(df.groupby("patient").size().mean()), 2),
            "median": float(df.groupby("patient").size().median()),
            "std": round(float(df.groupby("patient").size().std()), 2),
        },
        "exact_duplicates": {
            "n_groups": len(exact_dups),
            "n_extra_files": int(sum(d["n"] - 1 for d in exact_dups)),
            "n_groups_cross_patient": len(exact_dup_cross_patient),
            "n_groups_cross_split": len(exact_dup_cross_split),
            "examples": exact_dups[:15],
        },
        "near_duplicates_dhash_le4": {
            "n_pairs": len(near_pairs),
            "n_pairs_cross_patient": len(near_cross_patient),
            "n_pairs_cross_split": len(near_cross_split),
            "cross_split_examples": near_cross_split[:15],
            "cross_patient_examples": near_cross_patient[:15],
        },
        "runtime_sec": round(time.time() - t0, 1),
    }

    with open(OUT_DIR / "gastrohun_inventory.json", "w", encoding="utf-8") as fh:
        json.dump(res, fh, indent=2)

    print(json.dumps({k: v for k, v in res.items()
                      if k not in ("resolutions",)}, indent=2)[:4000])


if __name__ == "__main__":
    sys.exit(main())
