"""
Phase 4 / Stage A -- extended training cohort and per-image vote matrix.

Phase 2 trained on the 60.2% complete-agreement subset. Phase 3 measured what
that costs when the model meets contested images (raw annotator-marginalized
macro F1 83.92 -> 26-49 outside the unanimous tier). Phase 4 changes the
TRAINING TARGET, not the architecture, and therefore needs a cohort that
contains contested images and a per-image record of how the four annotators
actually voted.

Cohort definition (pre-registered, blueprint v3.3 sec.4 PHASE 4)
---------------------------------------------------------------
E = "extended cohort" = every image in the Train/Validation splits carrying a
    MAJORITY label, i.e. agreement tier S-unanimous (4/4) or S-majority (3/4).

E is held CONSTANT across C1, C2, C3 and C4 so that those four configurations
differ only in how the target vector is built from the votes. The reason is
the C3 control: a hard label is undefined on the 2-2 and 1-1-1-1 tiers, so a
cohort that included them could not be scored by C3 at all, and any C2 gain
would then be confounded with the extra images rather than with the softness
of the target. C0 (Phase 2, 4/4 only) is the reference arm; C0 -> C1 isolates
the cohort change, C1 -> {C2, C3, C4} isolates the target change.

Gates enforced here
  GATE P4.1a  |E n Train| = 5228, |E n Validation| = 1103   (counts computed
              from official_splits/ alone; they equal the corpus-wide cascade
              of blueprint sec.2.4 restricted to those splits)
  GATE P4.1b  23 classes present among the Train majority labels
  GATE P4.1c  0 patient overlap Train/Validation, and 0 overlap of either with
              the Phase 3 test split
  GATE P4.1d  every cohort filename resolves against the Phase 0 SHA-256
              inventory and exists on disk (GATE 3 re-applied)
  GATE P4.1e  the S-unanimous rows of E reproduce the Phase 2 consensus
              manifest exactly (same filenames, same labels)

Outputs
  data/phase4_train_manifest.csv
  reports/phase4_cohort.json
Run:  python src/models/phase4_data.py
"""
from __future__ import annotations

import json
import time
from collections import Counter
from pathlib import Path

import pandas as pd
from scipy.stats import chi2_contingency

ROOT = Path(__file__).resolve().parents[2]
SPLITS = ROOT / "official_splits" / "image_classification.csv"
META = ROOT / "metadata" / "gastrohun-image-metadata.json"
HASHES = ROOT / "reports" / "gastrohun_hashes.csv"
IMAGE_ROOT = ROOT / "Labeled Images"
P2_MANIFEST = ROOT / "data" / "phase2_consensus_manifest.csv"
P3_MANIFEST = ROOT / "data" / "phase3_test_manifest.csv"
CLASS_INDEX = ROOT / "data" / "phase2_class_index.json"

DATA = ROOT / "data"
REPORTS = ROOT / "reports"
OUT_MANIFEST = DATA / "phase4_train_manifest.csv"
OUT_SUMMARY = REPORTS / "phase4_cohort.json"

ANN = ["FG1 (Team A)", "FG2 (Team A)", "G1 (Team B)", "G2 (Team B)"]
EXPECTED = {"Train": 5228, "Validation": 1103}
EXPECTED_TIERS = {"Train": {"S-unanimous": 3722, "S-majority": 1506},
                  "Validation": {"S-unanimous": 793, "S-majority": 310}}
EXPECTED_CLASSES = 23


def classify_tier(votes) -> tuple[str, str | None]:
    """Identical rule to phase3_data.classify_tier, applied to Train/Val."""
    vc = Counter(votes)
    counts = sorted(vc.values(), reverse=True)
    top = max(vc, key=lambda kk: (vc[kk],))
    if counts[0] == 4:
        return "S-unanimous", top
    if counts[0] == 3:
        return "S-majority", top
    if counts[0] == 2 and len(counts) > 1 and counts[1] == 2:
        return "S-tied", None
    if counts[0] == 2:
        return "S-plurality", top
    return "S-dispersed", None


def main() -> None:
    t0 = time.time()
    df = pd.read_csv(SPLITS, index_col=0)
    df["patient"] = df["num patient"].astype(int)
    meta = pd.DataFrame(json.load(open(META, encoding="utf-8")))
    df = df.merge(meta[["filename", "source_type", "width", "height"]],
                  on="filename", how="left")

    tiers, labels = [], []
    for _, r in df.iterrows():
        t, lab = classify_tier([r[a] for a in ANN])
        tiers.append(t)
        labels.append(lab)
    df["tier"] = tiers
    df["majority_label"] = labels

    trainval = df[df.set_type.isin(["Train", "Validation"])].copy()
    coh = trainval[trainval.tier.isin(["S-unanimous", "S-majority"])].copy()

    # ---- GATE P4.1a / P4.1b ------------------------------------------------
    got = coh.groupby("set_type").size().to_dict()
    got = {k: int(got.get(k, 0)) for k in EXPECTED}
    if got != EXPECTED:
        raise SystemExit(f"GATE P4.1a FAILED: cohort counts {got} != {EXPECTED}")
    tier_by_split = {s: {t: int(v) for t, v in g.tier.value_counts().items()}
                     for s, g in coh.groupby("set_type")}
    if tier_by_split != EXPECTED_TIERS:
        raise SystemExit(f"GATE P4.1a FAILED: tier split {tier_by_split} != {EXPECTED_TIERS}")

    classes = sorted(coh[coh.set_type == "Train"]["majority_label"].unique().tolist())
    if len(classes) != EXPECTED_CLASSES:
        raise SystemExit(f"GATE P4.1b FAILED: {len(classes)} classes in the training cohort")
    cls = json.load(open(CLASS_INDEX, encoding="utf-8"))
    if sorted(cls) != classes:
        raise SystemExit("GATE P4.1b FAILED: cohort classes differ from the Phase 2 class index")
    # every annotator vote must also be in the fixed index, since C2/C4 place
    # probability mass on minority votes
    stray = sorted(set(coh[ANN].to_numpy().ravel()) - set(cls))
    if stray:
        raise SystemExit(f"GATE P4.1b FAILED: annotator votes outside the class index: {stray}")

    # ---- GATE P4.1c --------------------------------------------------------
    pats = {s: set(g.patient) for s, g in coh.groupby("set_type")}
    test_pats = set(pd.read_csv(P3_MANIFEST)["patient"])
    overlaps = {
        "train_val": sorted(pats["Train"] & pats["Validation"]),
        "train_test": sorted(pats["Train"] & test_pats),
        "val_test": sorted(pats["Validation"] & test_pats),
    }
    if any(overlaps.values()):
        raise SystemExit(f"GATE P4.1c FAILED: patient leakage {overlaps}")

    # ---- GATE P4.1d --------------------------------------------------------
    hsh = pd.read_csv(HASHES, dtype={"sha256": str, "dhash": str})
    folder = hsh.set_index("filename")["folder"].astype(str).to_dict()
    coh["folder"] = coh["filename"].map(folder)
    n_unresolved = int(coh["folder"].isna().sum())
    if n_unresolved:
        raise SystemExit(f"GATE P4.1d FAILED: {n_unresolved} filenames absent from the Phase 0 inventory")
    coh["relpath"] = coh["folder"] + "/" + coh["filename"]
    n_exist = sum((IMAGE_ROOT / p).exists() for p in coh["relpath"])
    if n_exist != len(coh):
        raise SystemExit(f"GATE P4.1d FAILED: {len(coh) - n_exist} cohort images not on disk")
    n_dup = int(coh["filename"].duplicated().sum())
    if n_dup:
        raise SystemExit(f"GATE P4.1d FAILED: {n_dup} duplicated filenames in the cohort")

    # ---- GATE P4.1e --------------------------------------------------------
    p2 = pd.read_csv(P2_MANIFEST)
    p2 = p2[p2.set_type.isin(["Train", "Validation"])]
    u = coh[coh.tier == "S-unanimous"]
    if set(u.filename) != set(p2.filename):
        raise SystemExit("GATE P4.1e FAILED: S-unanimous rows differ from the Phase 2 cohort")
    merged = u.merge(p2[["filename", "label"]], on="filename")
    n_lab_mismatch = int((merged.majority_label != merged.label).sum())
    if n_lab_mismatch:
        raise SystemExit(f"GATE P4.1e FAILED: {n_lab_mismatch} label mismatches vs Phase 2")

    # ---- vote columns, in the same order phase3_data.py used ---------------
    for i, a in enumerate(ANN):
        coh[f"vote_{i}"] = coh[a]

    # ---- descriptive composition ------------------------------------------
    class_by_split = (coh.groupby(["set_type", "majority_label"]).size()
                      .unstack(fill_value=0).astype(int))
    stream_by_split = (coh.groupby(["set_type", "source_type"]).size()
                       .unstack(fill_value=0).astype(int))
    chi2_c, p_c, _, _ = chi2_contingency(class_by_split.values)
    chi2_s, p_s, _, _ = chi2_contingency(stream_by_split.values)

    # how much soft signal C2/C4 actually receive: on a 3/4 image the target
    # is (0.75, 0.25), on a 4/4 image it is one-hot.
    frac_contested = {s: round(float((g.tier == "S-majority").mean()), 5)
                      for s, g in coh.groupby("set_type")}
    minority_labels = coh[coh.tier == "S-majority"].apply(
        lambda r: [v for v in (r[a] for a in ANN) if v != r["majority_label"]][0], axis=1)
    minority_pairs = Counter(
        f"{a}|{b}" for a, b in zip(coh[coh.tier == "S-majority"]["majority_label"],
                                   minority_labels))

    keep = ["filename", "relpath", "patient", "set_type", "tier", "majority_label",
            "vote_0", "vote_1", "vote_2", "vote_3", "source_type", "width", "height"]
    coh[keep].to_csv(OUT_MANIFEST, index=False)

    out = {
        "generated": time.strftime("%Y-%m-%d %H:%M:%S"),
        "purpose": ("extended (majority-or-better) training cohort for the Phase 4 "
                    "C1-C4 configurations; cohort held constant across configurations "
                    "so that only the target construction varies"),
        "gates": {"P4.1a_counts": True, "P4.1b_classes": True,
                  "P4.1c_no_patient_overlap": True, "P4.1d_hash_and_disk": True,
                  "P4.1e_matches_phase2_consensus": True},
        "cohort_definition": "tier in {S-unanimous (4/4), S-majority (3/4)}, Train+Validation",
        "n_images": int(len(coh)),
        "by_split": got,
        "tier_by_split": tier_by_split,
        "phase2_cohort_by_split": {"Train": 3722, "Validation": 793},
        "growth_vs_phase2": {s: round(got[s] / EXPECTED_TIERS[s]["S-unanimous"], 4)
                             for s in got},
        "n_patients_by_split": {s: len(v) for s, v in pats.items()},
        "n_classes": len(classes),
        "classes": classes,
        "patient_overlap": overlaps,
        "hash_resolution": {"n_cohort": int(len(coh)), "n_unresolved": n_unresolved,
                            "n_present_on_disk": int(n_exist),
                            "n_duplicate_filenames": n_dup},
        "fraction_contested_by_split": frac_contested,
        "class_by_split": {s: {c: int(v) for c, v in row.items()}
                           for s, row in class_by_split.iterrows()},
        "class_split_chi2": round(float(chi2_c), 3),
        "class_split_p": float(p_c),
        "stream_by_split": {s: {c: int(v) for c, v in row.items()}
                            for s, row in stream_by_split.iterrows()},
        "stream_split_chi2": round(float(chi2_s), 3),
        "stream_split_p": float(p_s),
        "top_majority_minority_pairs": dict(minority_pairs.most_common(15)),
        "excluded_trainval_images": {
            "n": int(len(trainval) - len(coh)),
            "by_tier": {t: int(v) for t, v in
                        trainval[~trainval.tier.isin(["S-unanimous", "S-majority"])]
                        .tier.value_counts().items()},
            "reason": ("no majority label exists, so the C1/C3 hard-label arms are "
                       "undefined on them; excluding them from every arm keeps the "
                       "C2-vs-C3 contrast a pure target-construction contrast"),
        },
        "runtime_sec": round(time.time() - t0, 1),
    }
    OUT_SUMMARY.write_text(json.dumps(out, indent=2), encoding="utf-8")

    print(f"GATE P4.1a-e PASS   cohort {got}  tiers {tier_by_split}")
    print(f"  classes={len(classes)}  patients={out['n_patients_by_split']}")
    print(f"  contested fraction: {frac_contested}")
    print(f"  excluded from Train/Val: {out['excluded_trainval_images']}")
    print(f"wrote {OUT_MANIFEST.name}, {OUT_SUMMARY.name} in {out['runtime_sec']}s")


if __name__ == "__main__":
    main()
