"""
P5.2 -- build the external-to-GastroHUN mapping table.

Every one of the 50 external class directories gets exactly one decision, and
every decision carries a written rationale. Nothing is mapped by string
similarity; each row below is an anatomical judgement recorded in full so a
reviewer can disagree with a specific line rather than with the table as a whole.

The mapping is deliberately NOT a 23-way assignment. GastroHUN's label space is
wall x station and neither external corpus carries the wall axis, so the target
space here is the collapse the external labels can actually express:

    RETROFLEXION    GastroHUN stations 4-5   {A4,A5,G4,L4,L5,P4,P5}
    FORWARD_GASTRIC GastroHUN stations 1,2,3,6 {A1,A2,A3,A6,G1,G2,G3,L1,L2,L3,L6,
                                                P1,P2,P3,P6}
    OTHERCLASS      not a gastric SSS station at all
    (discard)       in-stomach or indeterminate, but not assignable to either
                    station group without guessing

Ambiguity is recorded PER ENDPOINT, because a label can be unambiguous on one
axis and ambiguous on another. "Pylorus" is not an SSS station, so it is
ambiguous for station identity; but it is unambiguously a forward view, so it is
NOT ambiguous for P5-A, which only asks retroflex-vs-forward.

Gates
  P5.2a  every external class directory receives exactly one decision
  P5.2b  every decision carries a rationale
  P5.2c  ambiguous decisions are flagged, with the alternative recorded, so
         P5.10 can re-run them the other way

Run:  python src/models/phase5_mapping.py
"""
from __future__ import annotations

import csv
import json
import sys
import time
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
REPORTS = ROOT / "reports"
INVENTORY = REPORTS / "phase5_external_inventory.csv"
CLASS_INDEX = ROOT / "data" / "phase2_class_index.json"
STRUCTURE = REPORTS / "gastrohun_structure.json"
OUT = REPORTS / "phase5_mapping.json"

RETRO_STATIONS = {4, 5}
FORWARD_STATIONS = {1, 2, 3, 6}

# Endpoints Phase 5 actually tests. Station identity is deliberately absent: the
# station axis is not recoverable from either external corpus, which is the
# central finding of this phase rather than an oversight.
ENDPOINTS_UNDER_TEST = {"P5-A", "P5-B", "P5-C"}

R = "RETROFLEXION"
F = "FORWARD_GASTRIC"
O = "OTHERCLASS"
D = "discard"

# (decision, rationale, ambiguous_for, alternative_decision)
LOWER_GI = "lower gastrointestinal tract; not a gastric SSS station"
ESOPH = "oesophagus or the oesophago-gastric junction; proximal to the gastric protocol"
THERAP = "therapeutic/interventional frame from the lower GI tract"

MAP: dict[tuple[str, str], tuple] = {
    # ---- HyperKvasir, upper GI anatomical landmarks --------------------------
    ("hyperkvasir", "retroflex-stomach"): (
        R, "retroflexed view of the gastric cardia/fundus. This is the only class "
           "in either corpus that unambiguously denotes a stomach retroflexion, and "
           "P5-A rests on it.", [], None),
    ("hyperkvasir", "pylorus"): (
        F, "forward view of the pyloric ring from the antrum. The pylorus is distal "
           "to the antrum and is NOT itself an SSS station, so this cannot be "
           "assigned a station; but the endoscope orientation is unambiguously "
           "forward, which is all P5-A requires.", ["station_identity"], None),
    ("hyperkvasir", "z-line"): (
        O, ESOPH + ". The Z-line is the squamocolumnar junction, outside the gastric "
           "protocol, so a correctly behaving model should route it to OTHERCLASS.",
        [], None),
    # ---- HyperKvasir, upper GI pathology (all oesophageal) -------------------
    ("hyperkvasir", "barretts"): (O, ESOPH, [], None),
    ("hyperkvasir", "barretts-short-segment"): (O, ESOPH, [], None),
    ("hyperkvasir", "esophagitis-a"): (O, ESOPH, [], None),
    ("hyperkvasir", "esophagitis-b-d"): (O, ESOPH, [], None),
    # ---- HyperKvasir, lower GI ----------------------------------------------
    ("hyperkvasir", "cecum"): (O, LOWER_GI, [], None),
    ("hyperkvasir", "ileum"): (O, LOWER_GI, [], None),
    ("hyperkvasir", "retroflex-rectum"): (
        O, LOWER_GI + ". Note this is a RECTAL retroflexion, not a gastric one; it "
           "must not be pooled with retroflex-stomach.", [], None),
    ("hyperkvasir", "hemorrhoids"): (O, LOWER_GI, [], None),
    ("hyperkvasir", "polyps"): (O, LOWER_GI, [], None),
    ("hyperkvasir", "ulcerative-colitis-grade-0-1"): (O, LOWER_GI, [], None),
    ("hyperkvasir", "ulcerative-colitis-grade-1"): (O, LOWER_GI, [], None),
    ("hyperkvasir", "ulcerative-colitis-grade-1-2"): (O, LOWER_GI, [], None),
    ("hyperkvasir", "ulcerative-colitis-grade-2"): (O, LOWER_GI, [], None),
    ("hyperkvasir", "ulcerative-colitis-grade-2-3"): (O, LOWER_GI, [], None),
    ("hyperkvasir", "ulcerative-colitis-grade-3"): (O, LOWER_GI, [], None),
    ("hyperkvasir", "bbps-0-1"): (
        O, "bowel-preparation quality score from the lower GI tract", [], None),
    ("hyperkvasir", "bbps-2-3"): (
        O, "bowel-preparation quality score from the lower GI tract", [], None),
    ("hyperkvasir", "impacted-stool"): (O, LOWER_GI, [], None),
    ("hyperkvasir", "dyed-lifted-polyps"): (O, THERAP, [], None),
    ("hyperkvasir", "dyed-resection-margins"): (O, THERAP, [], None),

    # ---- GastroVision, stomach ----------------------------------------------
    ("gastrovision", "Normal stomach"): (
        F, "normal gastric mucosa. GastroVision has NO retroflex-stomach class, so "
           "retroflexed gastric frames in this corpus have nowhere else to be filed "
           "and may be present here. Treated as forward for the primary analysis and "
           "re-run as discarded in P5.10.", ["P5-A"], D),
    ("gastrovision", "Pylorus"): (
        F, "forward view of the pyloric ring; same reasoning as the HyperKvasir "
           "pylorus class.", ["station_identity"], None),
    ("gastrovision", "Gastric polyps"): (
        D, "anatomically gastric, but the label is pathology-defined and the frame "
           "is centred on a lesion rather than on an SSS station, so neither the "
           "station nor the retroflex/forward axis is recoverable.", [], O),
    ("gastrovision", "Ulcer"): (
        D, "site not specified by the label; gastric and duodenal ulcers are both "
           "present in this class, so it cannot be assigned.", [], O),
    # ---- GastroVision, duodenum and oesophagus -------------------------------
    ("gastrovision", "Duodenal bulb"): (
        O, "distal to the pylorus, outside the gastric protocol", [], None),
    ("gastrovision", "Gastroesophageal_junction_normal z-line"): (O, ESOPH, [], None),
    ("gastrovision", "Normal esophagus"): (O, ESOPH, [], None),
    ("gastrovision", "Barrett's esophagus"): (O, ESOPH, [], None),
    ("gastrovision", "Esophagitis"): (O, ESOPH, [], None),
    ("gastrovision", "Esophageal varices"): (O, ESOPH, [], None),
    # ---- GastroVision, lower GI ---------------------------------------------
    ("gastrovision", "Cecum"): (O, LOWER_GI, [], None),
    ("gastrovision", "Colon diverticula"): (O, LOWER_GI, [], None),
    ("gastrovision", "Colon polyps"): (O, LOWER_GI, [], None),
    ("gastrovision", "Colorectal cancer"): (O, LOWER_GI, [], None),
    ("gastrovision", "Ileocecal valve"): (O, LOWER_GI, [], None),
    ("gastrovision", "Mucosal inflammation large bowel"): (O, LOWER_GI, [], None),
    ("gastrovision", "Normal mucosa and vascular pattern in the large bowel"):
        (O, LOWER_GI, [], None),
    ("gastrovision", "Resected polyps"): (O, THERAP, [], None),
    ("gastrovision", "Resection margins"): (O, THERAP, [], None),
    ("gastrovision", "Retroflex rectum"): (
        O, LOWER_GI + ". RECTAL retroflexion; must not be pooled with a gastric "
           "retroflexion.", [], None),
    ("gastrovision", "Small bowel_terminal ileum"): (O, LOWER_GI, [], None),
    ("gastrovision", "Dyed-lifted-polyps"): (O, THERAP, [], None),
    ("gastrovision", "Dyed-resection-margins"): (O, THERAP, [], None),
    # ---- GastroVision, indeterminate location --------------------------------
    ("gastrovision", "Accessory tools"): (
        D, "the frame is dominated by an instrument and the label says nothing about "
           "which tract is being viewed, so it can be neither a station nor a "
           "confident out-of-protocol negative.", ["P5-B"], O),
    ("gastrovision", "Blood in lumen"): (
        D, "site not specified by the label; may be upper or lower GI.", ["P5-B"], O),
    ("gastrovision", "Angiectasia"): (
        D, "site not specified; angiectasia occurs in the stomach and the small "
           "bowel alike.", ["P5-B"], O),
    ("gastrovision", "Erythema"): (
        D, "site not specified by the label.", ["P5-B"], O),
}


def main() -> int:
    if not INVENTORY.exists():
        print(f"[P5.2] missing {INVENTORY}; run phase5_acquire.py first.")
        return 1

    rows = list(csv.DictReader(INVENTORY.open(encoding="utf-8")))
    present = Counter((r["corpus"], r["class_dir"]) for r in rows)

    cls_index = json.loads(CLASS_INDEX.read_text(encoding="utf-8"))
    taxo = json.loads(STRUCTURE.read_text(encoding="utf-8"))["taxonomy"]
    retro = sorted(t["code"] for t in taxo if t.get("station") in RETRO_STATIONS)
    forward = sorted(t["code"] for t in taxo if t.get("station") in FORWARD_STATIONS)
    other = sorted(t["code"] for t in taxo if t.get("station") is None)
    assert len(retro) + len(forward) + len(other) == len(cls_index) == 23

    target_codes = {R: retro, F: forward, O: other, D: []}
    target_idx = {g: sorted(cls_index[c] for c in codes)
                  for g, codes in target_codes.items()}

    # ---- gate P5.2a: exactly one decision per observed class -----------------
    unmapped = sorted(k for k in present if k not in MAP)
    unused = sorted(k for k in MAP if k not in present)

    table, tally = [], Counter()
    for (corpus, cdir), n in sorted(present.items()):
        if (corpus, cdir) not in MAP:
            continue
        decision, rationale, ambig, alt = MAP[(corpus, cdir)]
        table.append({
            "corpus": corpus,
            "external_class": cdir,
            "n_images": n,
            "decision": decision,
            "gastrohun_target_group": decision if decision != D else None,
            "gastrohun_target_codes": target_codes[decision],
            "rationale": rationale,
            "ambiguous_for": ambig,
            "alternative_decision_for_sensitivity": alt,
        })
        tally[decision] += n

    by_endpoint = {
        "P5-A": {
            "question": ("retroflexion vs forward gastric view, on external images "
                         "that are gastric at all"),
            "positive_class": R,
            "n_retroflexion": sum(r["n_images"] for r in table if r["decision"] == R),
            "n_forward": sum(r["n_images"] for r in table if r["decision"] == F),
            "contributing_classes": [
                f"{r['corpus']}/{r['external_class']} ({r['decision']}, n={r['n_images']})"
                for r in table if r["decision"] in (R, F)],
            "note": ("every retroflexion image comes from HyperKvasir; GastroVision "
                     "has no retroflex-stomach class."),
        },
        "P5-B": {
            "question": ("does the model route an image that is not a gastric SSS "
                         "station to OTHERCLASS, or does it confidently assert a "
                         "station?"),
            "n_out_of_protocol": tally[O],
            "n_discarded_as_indeterminate": tally[D],
            "note": ("discarded classes are those whose label does not fix the "
                     "anatomical site; including them would score the model against "
                     "a negative we cannot ourselves verify. They are re-included in "
                     "the P5.10 sensitivity re-run."),
        },
        "P5-C": {
            "question": "is the Phase 4 calibration ordering preserved under shift?",
            "evaluated_on": ("the union of the P5-A and P5-B images, where a "
                             "collapsed ground truth exists"),
        },
    }

    out = {
        "generated": time.strftime("%Y-%m-%d %H:%M:%S"),
        "phase": 5,
        "step": "P5.2",
        "purpose": "external-to-GastroHUN label mapping at the granularity the "
                   "external corpora can actually express",
        "why_not_23_way": (
            "GastroHUN's label space is wall x station. Neither external corpus "
            "carries the wall axis, and neither has a class for four of the six "
            "stations. A 23-way external macro F1 would have a meaningless "
            "denominator, so the target space is collapsed to the distinctions the "
            "external labels encode, and that collapse is fixed here, before any "
            "external image is scored."),
        "collapse_definition": {
            "RETROFLEXION": {"stations": sorted(RETRO_STATIONS), "codes": retro,
                             "class_indices": target_idx[R]},
            "FORWARD_GASTRIC": {"stations": sorted(FORWARD_STATIONS), "codes": forward,
                                "class_indices": target_idx[F]},
            "OTHERCLASS": {"codes": other, "class_indices": target_idx[O]},
        },
        "n_external_classes": len(table),
        "n_external_images": sum(present.values()),
        "images_by_decision": dict(tally),
        "endpoints": by_endpoint,
        "table": table,
        "gates": {
            "P5.2a_every_class_has_exactly_one_decision": {
                "pass": not unmapped,
                "n_classes_observed": len(present),
                "n_classes_mapped": len(table),
                "unmapped": unmapped,
                "mapped_but_not_observed": unused,
            },
            "P5.2b_every_decision_has_a_rationale": {
                "pass": all(r["rationale"] for r in table)},
            # A class ambiguous for an ENDPOINT UNDER TEST must carry an alternative,
            # so P5.10 can re-run it the other way. Ambiguity that touches no
            # endpoint -- "station_identity", which Phase 5 does not test because the
            # station axis is not recoverable externally at all -- needs none, and is
            # recorded separately rather than being waved through the same gate.
            "P5.2c_ambiguous_decisions_flagged": {
                "pass": all(r["alternative_decision_for_sensitivity"] is not None
                            for r in table
                            if set(r["ambiguous_for"]) & ENDPOINTS_UNDER_TEST),
                "endpoints_under_test": sorted(ENDPOINTS_UNDER_TEST),
                "n_ambiguous": sum(1 for r in table if r["ambiguous_for"]),
                "n_ambiguous_for_an_endpoint_under_test": sum(
                    1 for r in table
                    if set(r["ambiguous_for"]) & ENDPOINTS_UNDER_TEST),
                "missing_alternative": [
                    f"{r['corpus']}/{r['external_class']}" for r in table
                    if set(r["ambiguous_for"]) & ENDPOINTS_UNDER_TEST
                    and r["alternative_decision_for_sensitivity"] is None],
                "ambiguous_classes": [
                    {"corpus": r["corpus"], "class": r["external_class"],
                     "ambiguous_for": r["ambiguous_for"],
                     "affects_an_endpoint": bool(
                         set(r["ambiguous_for"]) & ENDPOINTS_UNDER_TEST),
                     "primary": r["decision"],
                     "alternative": r["alternative_decision_for_sensitivity"]}
                    for r in table if r["ambiguous_for"]],
            },
        },
        "limitation_to_state_in_the_report": (
            "The wall axis of the GastroHUN label space is unrecoverable from either "
            "external corpus, and four of the six stations have no external "
            "counterpart. Phase 5 therefore tests a 2-way anatomical collapse and an "
            "out-of-protocol rejection endpoint. It does NOT and cannot test 23-way "
            "station classification externally. This is a property of the available "
            "public data, not of the model."),
    }

    OUT.write_text(json.dumps(out, indent=1), encoding="utf-8")
    print(f"[P5.2] wrote {OUT}")
    print(f"       classes observed {len(present)}, mapped {len(table)}")
    if unmapped:
        print(f"       UNMAPPED (gate P5.2a FAILS): {unmapped}")
    for k, v in sorted(tally.items()):
        print(f"       {k:16} {v:6,d} images")
    a = by_endpoint["P5-A"]
    print(f"       P5-A: {a['n_retroflexion']:,} retroflexion vs "
          f"{a['n_forward']:,} forward")
    print(f"       P5-B: {by_endpoint['P5-B']['n_out_of_protocol']:,} out-of-protocol, "
          f"{by_endpoint['P5-B']['n_discarded_as_indeterminate']:,} discarded")
    print(f"       ambiguous decisions flagged: "
          f"{out['gates']['P5.2c_ambiguous_decisions_flagged']['n_ambiguous']}")
    return 0 if not unmapped else 1


if __name__ == "__main__":
    sys.exit(main())
