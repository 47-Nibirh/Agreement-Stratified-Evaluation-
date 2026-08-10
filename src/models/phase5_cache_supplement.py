"""
P5.3b -- supplementary cache for the images the mapping DISCARDED.

Closes a gap between the P5.3 implementation and the P5.4 pre-registration. The
pre-registration commits to re-running every mapping decision flagged ambiguous
for an endpoint under test with its recorded alternative. Four of those five
flips are `discard -> OTHERCLASS` (Accessory tools, Blood in lumen, Angiectasia,
Erythema), which cannot be scored at all if the discarded images were never
cached -- and P5.3 excluded them.

This caches exactly those images, using the identical decode path, so the P5.10
sensitivity re-run is actually executable rather than merely promised. It does
not change the primary analysis: these images remain discarded in the primary,
exactly as the frozen mapping says.

Outputs
  data/phase5_cache_discarded_224.npy
  data/phase5_cache_discarded_index.csv
Run:  python src/models/phase5_cache_supplement.py
"""
from __future__ import annotations

import csv
import json
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from phase5_cache import decode, SIZE  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
RAW = ROOT / "data" / "raw"
REPORTS = ROOT / "reports"
INVENTORY = REPORTS / "phase5_external_inventory.csv"
MAPPING = REPORTS / "phase5_mapping.json"
CACHE = ROOT / "data" / "phase5_cache_discarded_224.npy"
INDEX = ROOT / "data" / "phase5_cache_discarded_index.csv"


def main() -> int:
    if not (INVENTORY.exists() and MAPPING.exists()):
        print("[P5.3b] run phase5_acquire.py and phase5_mapping.py first.")
        return 1
    t0 = time.time()
    mp = json.loads(MAPPING.read_text(encoding="utf-8"))
    dec = {(r["corpus"], r["external_class"]): r for r in mp["table"]}

    rows = []
    for r in csv.DictReader(INVENTORY.open(encoding="utf-8")):
        d = dec.get((r["corpus"], r["class_dir"]))
        if d is None or d["decision"] != "discard":
            continue
        rows.append({
            "corpus": r["corpus"],
            "path": r["path"],
            "external_class": r["class_dir"],
            "primary_decision": "discard",
            "sensitivity_alternative": d["alternative_decision_for_sensitivity"],
            "ambiguous_for": ",".join(d["ambiguous_for"]),
            "sha256": r["sha256"],
        })
    rows.sort(key=lambda x: (x["corpus"], x["external_class"], x["path"]))
    n = len(rows)
    print(f"[P5.3b] caching {n:,} discarded images for the P5.10 sensitivity re-run")

    arr = np.lib.format.open_memmap(
        CACHE, mode="w+", dtype=np.uint8, shape=(n, SIZE, SIZE, 3))
    for i, r in enumerate(rows):
        arr[i] = decode(RAW / r["corpus"] / r["path"])
        if (i + 1) % 500 == 0:
            print(f"  {i + 1:,}/{n:,}", flush=True)
    arr.flush()

    with INDEX.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=[
            "corpus", "path", "external_class", "primary_decision",
            "sensitivity_alternative", "ambiguous_for", "sha256"])
        w.writeheader()
        w.writerows(rows)

    by_class = {}
    for r in rows:
        by_class.setdefault(f"{r['corpus']}/{r['external_class']}", 0)
        by_class[f"{r['corpus']}/{r['external_class']}"] += 1
    print(f"[P5.3b] wrote {CACHE.name} and {INDEX.name} in "
          f"{time.time() - t0:.1f}s")
    for k, v in sorted(by_class.items()):
        print(f"        {v:6,d}  {k}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
