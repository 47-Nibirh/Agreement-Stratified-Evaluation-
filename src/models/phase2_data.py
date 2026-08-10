"""
Phase 2 / Stage B -- consensus cohort construction and verification.

Builds the complete-agreement (4/4) cohort under the official patient-level
splits, verifies it against the Phase 0 integrity artefacts, fixes the class
index that every later phase must reuse, and tabulates the composition needed
for limitation L4 (acquisition-stream imbalance across splits).

Gates enforced here (blueprint v3.0 sec.4 PHASE 2):
  GATE 2  3,722 / 793 / 803 images and 23 classes present
  GATE 3  every cohort filename resolves against the Phase 0 SHA-256 inventory

Outputs
  data/phase2_consensus_manifest.csv
  data/phase2_class_index.json
  reports/phase2_split_provenance.json

Run:  python src/models/phase2_data.py
"""
from __future__ import annotations

import json
import time
from pathlib import Path

import pandas as pd
from scipy.stats import chi2_contingency

ROOT = Path(__file__).resolve().parents[2]
SPLITS = ROOT / "official_splits" / "image_classification.csv"
META = ROOT / "metadata" / "gastrohun-image-metadata.json"
HASHES = ROOT / "reports" / "gastrohun_hashes.csv"
IMAGE_ROOT = ROOT / "Labeled Images"

DATA = ROOT / "data"
REPORTS = ROOT / "reports"
MANIFEST = DATA / "phase2_consensus_manifest.csv"
CLASS_INDEX = DATA / "phase2_class_index.json"
OUT = REPORTS / "phase2_split_provenance.json"

ANN = ["FG1 (Team A)", "FG2 (Team A)", "G1 (Team B)", "G2 (Team B)"]
CONSENSUS = "Complete agreement"
EXPECTED = {"Train": 3722, "Validation": 793, "Test": 803}
EXPECTED_CLASSES = 23


def main() -> None:
    t0 = time.time()
    DATA.mkdir(exist_ok=True)
    REPORTS.mkdir(exist_ok=True)

    df = pd.read_csv(SPLITS, index_col=0)
    df["patient"] = df["num patient"].astype(int)

    meta = pd.DataFrame(json.load(open(META, encoding="utf-8")))
    df = df.merge(meta[["filename", "source_type", "width", "height"]],
                  on="filename", how="left")

    n_all = len(df)
    all_by_split = df.groupby("set_type").size().to_dict()

    # ---- B1  consensus cohort -------------------------------------------
    coh = df[df[CONSENSUS].notna()].copy()
    coh["label"] = coh[CONSENSUS].astype(str)

    # ---- B2  GATE 2 ------------------------------------------------------
    got = coh.groupby("set_type").size().to_dict()
    gate2_counts = {k: int(got.get(k, 0)) for k in EXPECTED}
    classes = sorted(coh["label"].unique().tolist())
    gate2 = (gate2_counts == EXPECTED) and (len(classes) == EXPECTED_CLASSES)
    if not gate2:
        raise SystemExit(f"GATE 2 FAILED: counts={gate2_counts} n_classes={len(classes)}")

    # ---- B3  split provenance -------------------------------------------
    pats = {s: set(g["patient"]) for s, g in coh.groupby("set_type")}
    pats_all = {s: set(g["patient"]) for s, g in df.groupby("set_type")}
    overlaps = {
        "train_val": sorted(pats["Train"] & pats["Validation"]),
        "train_test": sorted(pats["Train"] & pats["Test"]),
        "val_test": sorted(pats["Validation"] & pats["Test"]),
    }
    if any(overlaps.values()):
        raise SystemExit(f"PATIENT LEAKAGE in consensus cohort: {overlaps}")

    # patients that vanish once the cohort is restricted to 4/4 agreement
    lost = {s: sorted(pats_all[s] - pats[s]) for s in pats_all}

    # ---- B4  GATE 3  hash resolution ------------------------------------
    hsh = pd.read_csv(HASHES, dtype={"sha256": str, "dhash": str})
    known = set(hsh["filename"])
    unresolved = sorted(set(coh["filename"]) - known)
    gate3 = len(unresolved) == 0
    if not gate3:
        raise SystemExit(f"GATE 3 FAILED: {len(unresolved)} filenames not in Phase 0 inventory")

    # duplicate filenames inside the cohort would silently corrupt a split
    dup_names = int(coh["filename"].duplicated().sum())
    if dup_names:
        raise SystemExit(f"GATE 3 FAILED: {dup_names} duplicated filenames in cohort")

    # ---- B5  class index -------------------------------------------------
    class_index = {c: i for i, c in enumerate(classes)}
    CLASS_INDEX.write_text(json.dumps(class_index, indent=2), encoding="utf-8")

    # ---- relative image paths -------------------------------------------
    folder = hsh.set_index("filename")["folder"].astype(str).to_dict()
    coh["folder"] = coh["filename"].map(folder)
    coh["relpath"] = coh["folder"] + "/" + coh["filename"]

    missing = [p for p in coh["relpath"].head(0)]  # verified in full below
    n_exist = sum((IMAGE_ROOT / p).exists() for p in coh["relpath"])
    if n_exist != len(coh):
        # fall back: locate by glob for the few that do not follow folder/label
        fixed = 0
        for i, r in coh.iterrows():
            p = IMAGE_ROOT / r["relpath"]
            if not p.exists():
                hits = list((IMAGE_ROOT / r["folder"]).rglob(r["filename"]))
                if hits:
                    coh.at[i, "relpath"] = str(hits[0].relative_to(IMAGE_ROOT)).replace("\\", "/")
                    fixed += 1
                else:
                    missing.append(r["filename"])
        n_exist = sum((IMAGE_ROOT / p).exists() for p in coh["relpath"])
    if n_exist != len(coh):
        raise SystemExit(f"GATE 3 FAILED: {len(coh) - n_exist} cohort images not on disk")

    # ---- B7  composition tables -----------------------------------------
    class_by_split = (coh.groupby(["set_type", "label"]).size()
                      .unstack(fill_value=0).astype(int))
    stream_by_split = (coh.groupby(["set_type", "source_type"]).size()
                       .unstack(fill_value=0).astype(int))
    chi2_s, p_s, _, _ = chi2_contingency(stream_by_split.values)
    chi2_c, p_c, _, _ = chi2_contingency(class_by_split.values)

    imgs_per_pat = coh.groupby(["set_type", "patient"]).size()

    out = {
        "generated": time.strftime("%Y-%m-%d %H:%M:%S"),
        "gate2_pass": bool(gate2),
        "gate3_pass": bool(gate3),
        "corpus": {"n_images": int(n_all),
                   "by_split": {k: int(v) for k, v in all_by_split.items()},
                   "n_patients": int(df["patient"].nunique())},
        "cohort": {
            "n_images": int(len(coh)),
            "by_split": gate2_counts,
            "retention_pct": round(100 * len(coh) / n_all, 2),
            "retention_pct_by_split": {
                k: round(100 * gate2_counts[k] / all_by_split[k], 2) for k in EXPECTED},
            "n_classes": len(classes),
            "classes": classes,
            "n_patients": int(coh["patient"].nunique()),
            "patients_by_split": {s: len(v) for s, v in pats.items()},
            "patients_by_split_corpus": {s: len(v) for s, v in pats_all.items()},
            "patients_lost_to_consensus": {s: v for s, v in lost.items() if v},
            "images_per_patient": {
                s: {"min": int(g.min()), "max": int(g.max()),
                    "mean": round(float(g.mean()), 2), "std": round(float(g.std()), 2)}
                for s, g in imgs_per_pat.groupby(level=0)},
        },
        "patient_overlap": {k: v for k, v in overlaps.items()},
        "hash_resolution": {"n_cohort": int(len(coh)),
                            "n_resolved": int(len(coh) - len(unresolved)),
                            "n_unresolved": len(unresolved),
                            "n_duplicate_filenames": dup_names,
                            "n_present_on_disk": int(n_exist)},
        "class_by_split": {s: {c: int(v) for c, v in row.items()}
                           for s, row in class_by_split.iterrows()},
        "class_split_chi2": round(float(chi2_c), 2),
        "class_split_p": float(p_c),
        "stream_by_split": {s: {c: int(v) for c, v in row.items()}
                            for s, row in stream_by_split.iterrows()},
        "stream_split_chi2": round(float(chi2_s), 2),
        "stream_split_p": float(p_s),
        "test_class_support": {c: int(v) for c, v in
                               coh[coh.set_type == "Test"]["label"].value_counts().items()},
        "runtime_sec": round(time.time() - t0, 1),
    }
    OUT.write_text(json.dumps(out, indent=2), encoding="utf-8")

    cols = ["filename", "relpath", "patient", "set_type", "label",
            "source_type", "width", "height"]
    coh[cols].to_csv(MANIFEST, index=False)

    print(f"GATE 2 pass  {gate2_counts}  classes={len(classes)}")
    print(f"GATE 3 pass  {n_exist}/{len(coh)} images resolved on disk")
    print(f"patients  cohort={out['cohort']['patients_by_split']}  "
          f"corpus={out['cohort']['patients_by_split_corpus']}")
    print(f"lost to consensus filtering: {out['cohort']['patients_lost_to_consensus']}")
    print(f"stream x split chi2={chi2_s:.2f} p={p_s:.3g}")
    print(f"wrote {MANIFEST.name}, {CLASS_INDEX.name}, {OUT.name} "
          f"in {out['runtime_sec']}s")


if __name__ == "__main__":
    main()
