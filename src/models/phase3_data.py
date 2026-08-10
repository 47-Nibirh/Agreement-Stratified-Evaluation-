"""
Phase 3 / Stage A -- full test-split manifest with agreement tiers.

Extends Phase 2's evaluation from the 60.2% complete-agreement subset to the
full 1,353-image official test split, tagging every image with its agreement
tier from the 4-annotator vote matrix and a per-tier pseudo/majority label
where the pre-registration (blueprint v3.1 sec.4 Phase 3) defines one.

Tiers (pre-registered, fixed before any model touches these images):
  S-unanimous   4/4 agree             -> ground truth = unanimous label
  S-majority    3/4 agree             -> ground truth = majority label
  S-plurality   2-1-1                 -> pseudo-label = top-vote-getter (2/4)
  S-tied        2-2, no plurality     -> no single label (pooled below)
  S-dispersed   all four differ      -> no single label (pooled below)
  S-no-majority = S-tied U S-dispersed, pooled per the pre-registered rule
                  (S-dispersed alone has n=8 in the test split)

Gate: tier counts on the Test split must equal 803/342/127/73/8 exactly
(these were computed and pre-registered from official_splits/ before this
script existed; a mismatch means the vote-matrix logic is wrong, not that
the pre-registration should change).

Outputs
  data/phase3_test_manifest.csv
  reports/phase3_manifest_summary.json
Run:  python src/models/phase3_data.py
"""
from __future__ import annotations

import json
import time
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
SPLITS = ROOT / "official_splits" / "image_classification.csv"
HASHES = ROOT / "reports" / "gastrohun_hashes.csv"
CLASS_INDEX = ROOT / "data" / "phase2_class_index.json"
DATA = ROOT / "data"
REPORTS = ROOT / "reports"
OUT_MANIFEST = DATA / "phase3_test_manifest.csv"
OUT_SUMMARY = REPORTS / "phase3_manifest_summary.json"

ANN = ["FG1 (Team A)", "FG2 (Team A)", "G1 (Team B)", "G2 (Team B)"]
EXPECTED_TIER_COUNTS = {
    "S-unanimous": 803, "S-majority": 342, "S-plurality": 127,
    "S-tied": 73, "S-dispersed": 8,
}


def classify_tier(row) -> tuple[str, str | None, list[str]]:
    votes = [row[a] for a in ANN]
    vc = pd.Series(votes).value_counts()
    counts = sorted(vc.values, reverse=True)
    if counts[0] == 4:
        return "S-unanimous", vc.index[0], votes
    if counts[0] == 3:
        return "S-majority", vc.index[0], votes
    if counts[0] == 2 and len(counts) > 1 and counts[1] == 2:
        return "S-tied", None, votes
    if counts[0] == 2:
        return "S-plurality", vc.index[0], votes
    return "S-dispersed", None, votes


def main() -> None:
    t0 = time.time()
    df = pd.read_csv(SPLITS, index_col=0)
    df["patient"] = df["num patient"].astype(int)
    test = df[df["set_type"] == "Test"].reset_index(drop=True)

    tiers, labels, vote_lists = [], [], []
    for _, row in test.iterrows():
        tier, label, votes = classify_tier(row)
        tiers.append(tier)
        labels.append(label)
        vote_lists.append(votes)
    test["tier"] = tiers
    test["pseudo_label"] = labels
    for i, a in enumerate(ANN):
        test[f"vote_{i}"] = [v[i] for v in vote_lists]

    got = test["tier"].value_counts().to_dict()
    for k, v in EXPECTED_TIER_COUNTS.items():
        if got.get(k, 0) != v:
            raise SystemExit(f"TIER GATE FAILED: {k} expected {v}, got {got.get(k, 0)}")

    test["tier_pooled"] = test["tier"].replace(
        {"S-tied": "S-no-majority", "S-dispersed": "S-no-majority"})

    # resolve folder/relpath from the Phase 0 hash inventory, same as phase2_data.py
    hsh = pd.read_csv(HASHES, dtype={"sha256": str, "dhash": str})
    folder = hsh.set_index("filename")["folder"].astype(str).to_dict()
    test["folder"] = test["filename"].map(folder)
    unresolved = test["folder"].isna().sum()
    if unresolved:
        raise SystemExit(f"{unresolved} test filenames not found in Phase 0 hash inventory")
    test["relpath"] = test["folder"] + "/" + test["filename"]

    cls = json.load(open(CLASS_INDEX, encoding="utf-8"))
    unresolved_labels = sorted(set(l for l in test["pseudo_label"].dropna()) - set(cls))
    if unresolved_labels:
        raise SystemExit(f"labels not in Phase 2 class index: {unresolved_labels}")

    keep = ["filename", "relpath", "patient", "tier", "tier_pooled", "pseudo_label",
            "vote_0", "vote_1", "vote_2", "vote_3"]
    test[keep].to_csv(OUT_MANIFEST, index=False)

    summary = {
        "generated": time.strftime("%Y-%m-%d %H:%M:%S"),
        "n_test_images": int(len(test)),
        "n_test_patients": int(test["patient"].nunique()),
        "tier_counts": {k: int(v) for k, v in got.items()},
        "tier_counts_expected": EXPECTED_TIER_COUNTS,
        "tier_pooled_counts": {k: int(v) for k, v in test["tier_pooled"].value_counts().items()},
        "gate_pass": True,
        "runtime_sec": round(time.time() - t0, 1),
    }
    OUT_SUMMARY.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(f"tier counts: {got}")
    print(f"pooled: {summary['tier_pooled_counts']}")
    print(f"wrote {OUT_MANIFEST.name}, {OUT_SUMMARY.name} in {summary['runtime_sec']}s")


if __name__ == "__main__":
    main()
