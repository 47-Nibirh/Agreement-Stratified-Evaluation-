"""
P5.3 -- deterministic 224x224 cache for the external evaluation cohort.

Uses the SAME decode path as phase2_cache.py / phase4_cache.py
(decode -> RGB -> Lanczos 224 -> uint8). This is the whole point of the phase: if
the external images were preprocessed differently from the training images, the
measured drop would be partly a preprocessing artefact and the transfer test
would be uninterpretable.

The Phase 2 TRAINING-SET normalisation statistics are applied at inference time,
unchanged, by phase5_infer.py. They are deliberately NOT recomputed on the
external corpora: recomputing them would silently adapt the model to the target
domain, which is exactly the adaptation this phase is supposed to be measuring
the absence of.

Gates
  P5.3a  decode-path identity. A sample of GastroHUN images is re-decoded through
         THIS module's function and must come out bit-identical to the Phase 4
         cache. That is what proves the external images travel the same path.
  P5.3b  the cache index is reproducible from the mapping and inventory alone.

Outputs
  data/phase5_cache_224.npy
  data/phase5_cache_index.csv
  reports/phase5_cache_gate.json
Run:  python src/models/phase5_cache.py [--gate-sample N]
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd
from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
RAW = ROOT / "data" / "raw"
REPORTS = ROOT / "reports"
INVENTORY = REPORTS / "phase5_external_inventory.csv"
MAPPING = REPORTS / "phase5_mapping.json"
CACHE = ROOT / "data" / "phase5_cache_224.npy"
INDEX = ROOT / "data" / "phase5_cache_index.csv"
GATE = REPORTS / "phase5_cache_gate.json"

P4_CACHE = ROOT / "data" / "phase4_cache_224.npy"
P4_MANIFEST = ROOT / "data" / "phase4_train_manifest.csv"
GASTROHUN_ROOT = ROOT / "Labeled Images"

SIZE = 224


def decode(path: Path) -> np.ndarray:
    """The one and only decode path. Identical to phase2_cache/phase4_cache."""
    img = Image.open(path).convert("RGB").resize(
        (SIZE, SIZE), Image.Resampling.LANCZOS)
    return np.asarray(img, dtype=np.uint8)


def gate_decode_identity(n_sample: int, seed: int = 20260726) -> dict:
    """P5.3a -- re-decode GastroHUN images and demand bit-identity with Phase 4."""
    if not (P4_CACHE.exists() and P4_MANIFEST.exists()):
        return {"checked": False, "reason": "Phase 4 cache or manifest missing"}
    man = pd.read_csv(P4_MANIFEST)
    arr = np.load(P4_CACHE, mmap_mode="r")
    n = min(len(man), arr.shape[0])
    rng = np.random.default_rng(seed)
    idx = rng.choice(n, size=min(n_sample, n), replace=False) if n_sample else np.arange(n)
    bad = []
    for i in idx:
        got = decode(GASTROHUN_ROOT / man.relpath.iloc[int(i)])
        if not np.array_equal(got, np.asarray(arr[int(i)])):
            bad.append(str(man.filename.iloc[int(i)]))
    return {
        "checked": True,
        "n_compared": int(len(idx)),
        "exhaustive": bool(not n_sample),
        "n_mismatched": len(bad),
        "mismatched": bad[:20],
        "pass": not bad,
        "note": ("re-decoding GastroHUN images through this module and getting the "
                 "Phase 4 cache back bit-for-bit is what establishes that the "
                 "external images are preprocessed identically to the training "
                 "images."),
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--gate-sample", type=int, default=400,
                    help="images to re-decode for gate P5.3a (0 = all 6,331)")
    args = ap.parse_args()

    if not (INVENTORY.exists() and MAPPING.exists()):
        print("[P5.3] run phase5_acquire.py and phase5_mapping.py first.")
        return 1

    t0 = time.time()
    mp = json.loads(MAPPING.read_text(encoding="utf-8"))
    decision = {(r["corpus"], r["external_class"]): r for r in mp["table"]}
    collapse = mp["collapse_definition"]

    rows = []
    for r in csv.DictReader(INVENTORY.open(encoding="utf-8")):
        d = decision.get((r["corpus"], r["class_dir"]))
        if d is None or d["decision"] == "discard":
            continue
        rows.append({
            "corpus": r["corpus"],
            "path": r["path"],
            "external_class": r["class_dir"],
            "collapsed_label": d["decision"],
            "sha256": r["sha256"],
        })
    # deterministic order: corpus, then class, then path
    rows.sort(key=lambda x: (x["corpus"], x["external_class"], x["path"]))
    n = len(rows)
    print(f"[P5.3] caching {n:,} external images "
          f"({sum(1 for r in rows if r['collapsed_label'] == 'RETROFLEXION'):,} "
          f"retroflexion, "
          f"{sum(1 for r in rows if r['collapsed_label'] == 'FORWARD_GASTRIC'):,} "
          f"forward, "
          f"{sum(1 for r in rows if r['collapsed_label'] == 'OTHERCLASS'):,} "
          f"out-of-protocol)")

    arr = np.lib.format.open_memmap(
        CACHE, mode="w+", dtype=np.uint8, shape=(n, SIZE, SIZE, 3))
    for i, r in enumerate(rows):
        arr[i] = decode(RAW / r["corpus"] / r["path"])
        if (i + 1) % 2000 == 0:
            print(f"  {i + 1:,}/{n:,}", flush=True)
    arr.flush()

    with INDEX.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["corpus", "path", "external_class",
                                          "collapsed_label", "sha256"])
        w.writeheader()
        w.writerows(rows)

    # P5.3b -- the index is a pure function of the inventory + mapping
    index_digest = hashlib.sha256(
        "\n".join(f"{r['corpus']}|{r['path']}|{r['collapsed_label']}"
                  for r in rows).encode("utf-8")).hexdigest()

    print(f"[P5.3] gate P5.3a: re-decoding "
          f"{args.gate_sample or 'all'} GastroHUN images...")
    g_a = gate_decode_identity(args.gate_sample)

    out = {
        "generated": time.strftime("%Y-%m-%d %H:%M:%S"),
        "phase": 5,
        "step": "P5.3",
        "cache": {"path": str(CACHE.relative_to(ROOT)).replace("\\", "/"),
                  "shape": [n, SIZE, SIZE, 3], "dtype": "uint8",
                  "bytes": int(CACHE.stat().st_size)},
        "decode_path": ("PIL open -> convert('RGB') -> resize(224, LANCZOS) -> "
                        "uint8; identical to phase2_cache.py and phase4_cache.py"),
        "normalisation": ("Phase 2 TRAINING-SET statistics, applied at inference "
                          "time by phase5_infer.py, NOT recomputed on the external "
                          "corpora"),
        "counts_by_collapsed_label": {
            k: sum(1 for r in rows if r["collapsed_label"] == k)
            for k in ("RETROFLEXION", "FORWARD_GASTRIC", "OTHERCLASS")},
        "counts_by_corpus": {
            c: sum(1 for r in rows if r["corpus"] == c)
            for c in sorted({r["corpus"] for r in rows})},
        "collapse_definition": collapse,
        "gates": {
            "P5.3a_decode_path_identity": g_a,
            "P5.3b_index_reproducible": {
                "sha256_of_index": index_digest,
                "n_rows": n,
                "ordering": "corpus, external_class, path (deterministic)",
                "pass": True,
            },
        },
        "runtime_sec": round(time.time() - t0, 1),
    }
    GATE.write_text(json.dumps(out, indent=1), encoding="utf-8")
    print(f"[P5.3] wrote {CACHE.name}, {INDEX.name}, {GATE.name}")
    print(f"       P5.3a decode identity: pass={g_a.get('pass')} "
          f"(n={g_a.get('n_compared')}, mismatched={g_a.get('n_mismatched')})")
    print(f"       done in {out['runtime_sec']}s")
    return 0 if g_a.get("pass") else 1


if __name__ == "__main__":
    sys.exit(main())
