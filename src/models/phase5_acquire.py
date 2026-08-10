"""
P5.1 -- acquire, verify and inventory the external corpora.

Extracts whatever external archives are present in data/raw, inventories every
image, and runs the four P5.1 gates. Corpus-agnostic by design: it discovers the
class structure from the directory tree rather than assuming it, so the mapping
table in P5.2 is built from what the corpora actually contain and not from what
the papers say they contain.

Gates
  P5.1a  SHA-256 of every source archive recorded
  P5.1b  licence and citation captured per corpus
  P5.1c  no external image collides with the GastroHUN inventory by SHA-256
         (a collision would mean the "external" test set is not external)
  P5.1d  realised image counts recorded per corpus and per class

Run:  python src/models/phase5_acquire.py [--extract] [--limit-hash N]
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import sys
import time
import zipfile
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RAW = ROOT / "data" / "raw"
REPORTS = ROOT / "reports"
OUT = REPORTS / "phase5_provenance.json"
INVENTORY = REPORTS / "phase5_external_inventory.csv"
GASTROHUN_HASHES = REPORTS / "gastrohun_hashes.csv"

IMG_EXT = {".jpg", ".jpeg", ".png", ".bmp", ".tif", ".tiff"}

# Provenance is recorded here rather than inferred, so the report can cite the
# corpora correctly and state their licences. Sizes are verified against the
# archives actually on disk; a mismatch is reported, never silently accepted.
CORPORA = {
    "hyperkvasir": {
        "archive": "hyper-kvasir-labeled-images.zip",
        "expected_bytes": 3928814344,
        "name": "HyperKvasir (labeled images)",
        "source_url": ("https://datasets.simula.no/downloads/hyper-kvasir/"
                       "hyper-kvasir-labeled-images.zip"),
        "landing_page": "https://datasets.simula.no/hyper-kvasir/",
        "licence": "CC BY 4.0",
        "citation": ("Borgli et al. (2020). HyperKvasir, a comprehensive multi-class "
                     "image and video dataset for gastrointestinal endoscopy. "
                     "Scientific Data 7, 283."),
        "centre": "Baerum Hospital, Vestre Viken Health Trust, Norway",
    },
    "gastrovision": {
        "archive": "Gastrovision.zip",
        "expected_bytes": 1791000000,  # approximate; the realised size is authoritative
        "expected_bytes_is_approximate": True,
        "name": "GastroVision",
        "source_url": "https://osf.io/download/gvx3q/",
        "landing_page": "https://osf.io/84e7f/",
        "licence": "CC BY-NC 4.0",
        "citation": ("Jha et al. (2023). GastroVision: A Multi-class Endoscopy Image "
                     "Dataset for Computer Aided Gastrointestinal Disease Detection. "
                     "ICML Workshop on Machine Learning for Multimodal Healthcare Data."),
        "centre": ("Baerum Hospital (Norway) and Karolinska University Hospital "
                   "(Sweden)"),
    },
}


def sha256_file(path: Path, chunk: int = 1 << 20) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(chunk), b""):
            h.update(block)
    return h.hexdigest()


def extract(archive: Path, dest: Path) -> dict:
    dest.mkdir(parents=True, exist_ok=True)
    marker = dest / ".extracted"
    if marker.exists():
        return {"extracted_now": False, "reason": "already extracted"}
    with zipfile.ZipFile(archive) as z:
        names = z.namelist()
        z.extractall(dest)
    marker.write_text(f"{archive.name}\n{time.strftime('%Y-%m-%d %H:%M:%S')}\n",
                      encoding="utf-8")
    return {"extracted_now": True, "n_members": len(names)}


def inventory(root: Path) -> list[dict]:
    """Every image under `root`, with its class taken from the parent directory."""
    rows = []
    for p in sorted(root.rglob("*")):
        if not p.is_file() or p.suffix.lower() not in IMG_EXT:
            continue
        rel = p.relative_to(root)
        parts = rel.parts
        rows.append({
            "path": str(rel).replace("\\", "/"),
            "class_dir": parts[-2] if len(parts) >= 2 else "",
            "group_dir": parts[-3] if len(parts) >= 3 else "",
            "bytes": p.stat().st_size,
        })
    return rows


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--extract", action="store_true",
                    help="unzip the archives (needs ~12 GB free)")
    ap.add_argument("--limit-hash", type=int, default=0,
                    help="hash only the first N images per corpus (0 = all)")
    ap.add_argument("--only", default="", help="restrict to one corpus key")
    args = ap.parse_args()

    if not GASTROHUN_HASHES.exists():
        print(f"[P5.1] missing {GASTROHUN_HASHES}; run Phase 0 first.")
        return 1

    gh = set()
    with GASTROHUN_HASHES.open(encoding="utf-8") as f:
        for r in csv.DictReader(f):
            gh.add(r["sha256"])
    print(f"[P5.1] GastroHUN inventory: {len(gh):,} distinct SHA-256")

    corpora, all_rows = {}, []
    for key, meta in CORPORA.items():
        if args.only and key != args.only:
            continue
        arch = RAW / meta["archive"]
        rec = dict(meta)
        rec["archive_present"] = arch.exists()
        if not arch.exists():
            print(f"[P5.1] {key}: archive not present, skipping ({meta['archive']})")
            corpora[key] = rec
            continue

        size = arch.stat().st_size
        rec["realised_bytes"] = size
        rec["size_matches_expected"] = (
            None if meta.get("expected_bytes_is_approximate")
            else size == meta["expected_bytes"])
        # An archive smaller than expected is almost always a download still in
        # flight. Hashing or extracting it would record a hash for a file that no
        # longer exists a minute later, so refuse rather than warn.
        if rec["size_matches_expected"] is False and size < meta["expected_bytes"]:
            rec["skipped"] = (
                f"archive is {size:,} of an expected {meta['expected_bytes']:,} bytes "
                f"-- incomplete, most likely still downloading. Re-run this step once "
                f"it finishes.")
            print(f"[P5.1] {key}: SKIPPED -- {rec['skipped']}")
            corpora[key] = rec
            continue
        if rec["size_matches_expected"] is False:
            print(f"[P5.1] WARNING {key}: archive is {size:,} bytes, expected "
                  f"{meta['expected_bytes']:,}. Changed upstream.")
        print(f"[P5.1] {key}: hashing archive ({size / 1e9:.2f} GB)...")
        rec["archive_sha256"] = sha256_file(arch)  # gate P5.1a

        dest = RAW / key
        if args.extract:
            print(f"[P5.1] {key}: extracting -> {dest}")
            rec["extraction"] = extract(arch, dest)
        rec["extracted"] = dest.exists() and (dest / ".extracted").exists()

        if rec["extracted"]:
            rows = inventory(dest)
            for r in rows:
                r["corpus"] = key
            all_rows.extend(rows)
            rec["n_images"] = len(rows)  # gate P5.1d
            rec["classes"] = dict(sorted(Counter(r["class_dir"] for r in rows).items()))
            rec["groups"] = dict(sorted(Counter(r["group_dir"] for r in rows).items()))
            print(f"[P5.1] {key}: {len(rows):,} images across "
                  f"{len(rec['classes'])} class directories")
        corpora[key] = rec

    # ---- gate P5.1c: no external image is a GastroHUN image ------------------
    collisions, hashed = [], 0
    if all_rows:
        by_corpus: dict[str, list[dict]] = {}
        for r in all_rows:
            by_corpus.setdefault(r["corpus"], []).append(r)
        for key, rows in by_corpus.items():
            sel = rows[:args.limit_hash] if args.limit_hash else rows
            print(f"[P5.1] {key}: hashing {len(sel):,} images for the overlap gate...")
            for i, r in enumerate(sel):
                digest = sha256_file(RAW / key / r["path"])
                r["sha256"] = digest
                hashed += 1
                if digest in gh:
                    collisions.append({"corpus": key, "path": r["path"],
                                       "sha256": digest})
                if (i + 1) % 2000 == 0:
                    print(f"         {i + 1:,}/{len(sel):,}")

        with INVENTORY.open("w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=["corpus", "path", "class_dir",
                                              "group_dir", "bytes", "sha256"])
            w.writeheader()
            for r in all_rows:
                w.writerow({k: r.get(k, "") for k in w.fieldnames})
        print(f"[P5.1] inventory -> {INVENTORY}")

    gates = {
        "P5.1a_archive_sha256_recorded": all(
            "archive_sha256" in c for c in corpora.values() if c.get("archive_present")),
        "P5.1b_licence_and_citation_captured": all(
            c.get("licence") and c.get("citation") for c in corpora.values()),
        "P5.1c_no_overlap_with_gastrohun": {
            "checked": bool(all_rows),
            "n_images_hashed": hashed,
            "exhaustive": bool(all_rows) and not args.limit_hash,
            "n_collisions": len(collisions),
            "collisions": collisions[:50],
            "pass": bool(all_rows) and not collisions,
        },
        "P5.1d_counts_recorded": {k: c.get("n_images") for k, c in corpora.items()},
    }

    out = {
        "generated": time.strftime("%Y-%m-%d %H:%M:%S"),
        "phase": 5,
        "step": "P5.1",
        "purpose": "acquisition, provenance and inventory of the external corpora",
        "gastrohun_reference_hashes": len(gh),
        "corpora": corpora,
        "gates": gates,
        "note": ("class_dir is the immediate parent directory of each image and is "
                 "the raw label as the corpus ships it. No mapping is applied here; "
                 "P5.2 builds the mapping table from this inventory."),
    }
    OUT.write_text(json.dumps(out, indent=1), encoding="utf-8")
    print(f"[P5.1] wrote {OUT}")
    for k, v in gates.items():
        print(f"       {k}: {v if not isinstance(v, dict) else v.get('pass', v)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
