"""
P5.4 -- freeze the Phase 5 pre-registration.

Refuses to overwrite an existing pre-registration, exactly as phase4_prereg.py
does. Run AFTER the corpora, the mapping and the cache exist (so the endpoints
can be defined against realised counts rather than guesses) and BEFORE any
external image has been scored by any model.

Run:  python src/models/phase5_prereg.py
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
OUT = REPORTS / "phase5_prereg.json"

MAPPING = REPORTS / "phase5_mapping.json"
CACHE_GATE = REPORTS / "phase5_cache_gate.json"
PROVENANCE = REPORTS / "phase5_provenance.json"
CARRY = REPORTS / "phase5_carry_forward.json"
INDEX = ROOT / "data" / "phase5_cache_index.csv"

# Pre-registered precision target. Phase 4's amendment records the absence of one
# as an outstanding defect: a null there could not be distinguished from an
# underpowered study. Fixed here, before any external number exists.
PRECISION_TARGET_HALFWIDTH_POINTS = 3.0

# Chance rate for a 23-way head. Used as the pre-registered floor for P5-B.
CHANCE_RATE = 1.0 / 23.0


def main() -> int:
    if OUT.exists():
        print(f"[P5.4] {OUT.name} already exists; refusing to overwrite.")
        print("       A pre-registration that can be rewritten is not a "
              "pre-registration.")
        return 1

    for p in (MAPPING, CACHE_GATE, PROVENANCE, CARRY, INDEX):
        if not p.exists():
            print(f"[P5.4] missing {p}; run the earlier steps first.")
            return 1

    mp = json.loads(MAPPING.read_text(encoding="utf-8"))
    cg = json.loads(CACHE_GATE.read_text(encoding="utf-8"))
    prov = json.loads(PROVENANCE.read_text(encoding="utf-8"))
    carry = json.loads(CARRY.read_text(encoding="utf-8"))

    rows = list(csv.DictReader(INDEX.open(encoding="utf-8")))
    n_by_label = Counter(r["collapsed_label"] for r in rows)
    n_gastric = n_by_label["RETROFLEXION"] + n_by_label["FORWARD_GASTRIC"]

    out = {
        "frozen_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "phase": 5,
        "title": "External validation and the limits of the available label spaces",
        "statement": (
            "This document fixes every decision that could otherwise be made after "
            "seeing the result. It is written after the corpora, the mapping table "
            "and the 224px cache exist -- so that endpoints are defined against "
            "realised counts rather than guesses -- and before any external image "
            "has been scored by any model. The script that writes it refuses to "
            "overwrite an existing copy."),
        "governing_blueprint": "THESIS_RESEARCH_BLUEPRINT.md v3.4, sec.4 PHASE 5",
        "inputs_already_frozen": {
            "carry_forward": "reports/phase5_carry_forward.json",
            "mapping": "reports/phase5_mapping.json",
            "cache_gate": "reports/phase5_cache_gate.json",
            "provenance": "reports/phase5_provenance.json",
        },

        "corpora": {
            k: {"name": v.get("name"), "licence": v.get("licence"),
                "n_images": v.get("n_images"), "centre": v.get("centre"),
                "archive_sha256": v.get("archive_sha256")}
            for k, v in prov["corpora"].items()},
        "no_overlap_with_gastrohun": prov["gates"]["P5.1c_no_overlap_with_gastrohun"],

        "label_space": {
            "why_not_23_way": mp["why_not_23_way"],
            "collapse": mp["collapse_definition"],
            "n_evaluated": len(rows),
            "n_by_collapsed_label": dict(n_by_label),
            "n_discarded_as_indeterminate":
                mp["endpoints"]["P5-B"]["n_discarded_as_indeterminate"],
        },

        "arms": {
            "carried": carry["decision"]["carry"],
            "seeds": carry["decision"]["seeds"],
            "headline_arm": carry["decision"]["primary_arm_for_headline_numbers"],
            "control_arm": "C3, retained explicitly as the calibration control and "
                           "not as a candidate model",
            "no_retraining": True,
            "checkpoints": "the Phase 2 (C0) and Phase 4 (C1-C4) checkpoints, unchanged",
        },

        "preprocessing": {
            "decode_path": cg["decode_path"],
            "normalisation": cg["normalisation"],
            "gate_p5_3a": cg["gates"]["P5.3a_decode_path_identity"],
            "no_adaptation": (
                "no fine-tuning, no domain adaptation, no self-training, no threshold "
                "tuning and no post-hoc temperature scaling on external data. Phase 5 "
                "measures transfer, not transfer-after-adaptation. The Phase 5B "
                "self-training arm is a separate, later comparison against the "
                "numbers this pre-registration governs, and may not begin until they "
                "are committed."),
        },

        "interval_procedure": {
            "method": "nonparametric bootstrap, 1,000 resamples, seed 20260726",
            "unit": "IMAGE",
            "declared_weakness": (
                "Phases 0-4 clustered every interval by patient, because Phase 0 "
                "measured per-patient Fleiss kappa at 0.7459 +/- 0.1448 and images "
                "within a patient are not independent. Neither external corpus ships "
                "a usable grouping key: HyperKvasir's 'Video file' column has 10,662 "
                "distinct values over 10,662 images, one per image, and GastroVision "
                "ships none. Phase 5 intervals are therefore image-level and are "
                "OPTIMISTIC -- narrower than a correctly clustered interval would be. "
                "This is declared here rather than discovered later, and no Phase 5 "
                "interval may be compared directly against a Phase 0-4 interval."),
            "n_boot": 1000,
            "seed": 20260726,
        },

        "precision_target": {
            "endpoint": "P5-A primary",
            "max_ci95_halfwidth_points": PRECISION_TARGET_HALFWIDTH_POINTS,
            "rationale": (
                "reports/phase4_amendment.json records the absence of a pre-registered "
                "precision target as an outstanding Phase 4 defect: a NOT RESOLVED "
                "verdict there cannot be distinguished from an underpowered one. "
                "Phase 5 fixes a target in advance, so that a null is interpretable."),
            "rule": (
                "if the realised half-width exceeds the target, the verdict is "
                "reported as UNDERPOWERED rather than as a null, and the report says "
                "how many images would have been needed."),
        },

        "research_questions": {
            "P5-A": {
                "question": ("does the retroflexion-vs-forward distinction transfer to "
                             "external centres?"),
                "n_images": n_gastric,
                "n_retroflexion": n_by_label["RETROFLEXION"],
                "n_forward": n_by_label["FORWARD_GASTRIC"],
                "primary_endpoint": (
                    "binary macro F1 over {RETROFLEXION, FORWARD_GASTRIC} on the "
                    f"{n_gastric:,} external gastric images. The model's 23-way argmax "
                    "is collapsed through the frozen mapping; an OTHERCLASS prediction "
                    "counts as INCORRECT for whichever class the image truly is, so "
                    "the endpoint penalises both confusing the two views and failing "
                    "to recognise a gastric view at all."),
                "internal_comparator": (
                    "the identical collapse applied to the 1,353-image GastroHUN test "
                    "split, same arms, same seeds, restricted to images whose modal "
                    "label is a gastric station"),
                "primary_quantity": "external minus internal, in macro F1 points",
                "hypothesis": (
                    "a DROP is expected and is the publishable result (blueprint "
                    "sec.4 PHASE 5). The pre-registered expectation is a drop of more "
                    "than 10 points, because the external corpora are different "
                    "centres, different vendors and different framing conventions, "
                    "and because the retroflexion class is defined by endoscope "
                    "orientation rather than by mucosal appearance."),
                "verdict_rule": (
                    "TRANSFERS if the external binary macro F1 exceeds 50.0 (the "
                    "majority-class floor on this 2-class problem) with a 95% CI "
                    "excluding it; DOES NOT TRANSFER if the CI includes or falls "
                    "below it; UNDERPOWERED if the half-width exceeds the precision "
                    "target."),
                "secondary_endpoints": [
                    "gastric recognition rate: the fraction NOT routed to OTHERCLASS",
                    "binary macro F1 among recognised images only, which separates "
                    "the two failure modes",
                    "per-corpus breakout, since all retroflexion images come from "
                    "HyperKvasir",
                ],
            },
            "P5-B": {
                "question": ("given an image that is not a gastric SSS station at all, "
                             "does the model route it to OTHERCLASS or confidently "
                             "assert a station?"),
                "n_images": n_by_label["OTHERCLASS"],
                "primary_endpoint": ("out-of-protocol rejection rate: the fraction of "
                                     "the out-of-protocol images assigned OTHERCLASS"),
                "chance_rate": round(CHANCE_RATE, 5),
                "hypothesis": (
                    "the rejection rate will be LOW -- plausibly at or below the "
                    f"{CHANCE_RATE:.1%} chance rate of a 23-way head. GastroHUN "
                    "contains almost no true out-of-protocol images and OTHERCLASS is "
                    "a minority class its own annotators disagree about, so the model "
                    "has had no opportunity to learn a rejection behaviour. This "
                    "predicts confident misassignment, which is the deployment-"
                    "relevant failure and the endpoint on which the external data is "
                    "more informative than GastroHUN itself."),
                "verdict_rule": (
                    "REJECTS OUT-OF-PROTOCOL IMAGES if the rejection rate exceeds the "
                    f"{CHANCE_RATE:.5f} chance rate with a 95% CI excluding it; DOES "
                    "NOT if the CI includes or falls below chance."),
                "secondary_endpoints": [
                    "mean top-1 confidence on out-of-protocol images, per arm -- a "
                    "model that is wrong AND confident is worse than one that is "
                    "merely wrong",
                    "the station most often asserted on out-of-protocol images",
                    "per-corpus and per-external-class breakout",
                ],
            },
            "P5-C": {
                "question": "is the Phase 4 calibration ordering preserved under shift?",
                "primary_endpoint": (
                    "Spearman rank correlation between the five arms' ECE ordering "
                    "internally (Phase 4, pooled contested stratum) and externally "
                    "(this phase, all evaluated images)"),
                "secondary_endpoints": [
                    "does C3 remain the lowest-ECE arm externally?",
                    "does C3's under-confidence on easy images persist externally?",
                    "absolute ECE per arm, internal vs external",
                ],
                "hypothesis": (
                    "the ordering is expected to be broadly preserved, because C3's "
                    "low ECE is produced by a global confidence shift (Phase 4 "
                    "sec.4.2) and a global shift is a property of the model rather "
                    "than of the data it is shown. If the ordering does NOT survive, "
                    "that is evidence the Phase 4 calibration result was "
                    "dataset-specific, which would be the more important finding."),
                "verdict_rule": (
                    "PRESERVED if the Spearman rank correlation is >= 0.7; PARTIALLY "
                    "PRESERVED if 0.3 to 0.7; NOT PRESERVED if < 0.3."),
            },
        },

        "sensitivity_analyses": {
            "mapping_ambiguity": {
                "executed": ("every mapping decision flagged ambiguous for an endpoint "
                             "under test is re-run with its recorded alternative, and "
                             "each verdict is recomputed"),
                "n_ambiguous_affecting_an_endpoint": mp["gates"][
                    "P5.2c_ambiguous_decisions_flagged"][
                    "n_ambiguous_for_an_endpoint_under_test"],
                "classes": mp["gates"]["P5.2c_ambiguous_decisions_flagged"][
                    "ambiguous_classes"],
            },
            "per_corpus": ("every endpoint is reported for HyperKvasir and "
                           "GastroVision separately as well as pooled, because the "
                           "corpora contribute asymmetrically: all retroflexion "
                           "images come from HyperKvasir and most out-of-protocol "
                           "images from GastroVision"),
            "per_seed": "every headline number is reported per seed and at the 3-seed mean",
        },

        "deviations": [
            {
                "id": "P5-DEV-1",
                "item": "which arm is carried into external validation",
                "blueprint": ("status board: 'carry the best-calibrated arm, not the "
                              "most accurate (Phase 4 sec.4.7)'"),
                "adopted": "all five arms x 3 seeds",
                "evidence": carry["literal_rule_evaluation"]["why"],
                "impact": ("none adverse. Phase 5 is inference-only, so carrying five "
                           "arms costs 15 forward passes; and RQ3's external half is a "
                           "question about RANKING, which one arm cannot answer."),
            },
            {
                "id": "P5-DEV-2",
                "item": "external agreement-stratified curve and external vote entropy",
                "blueprint": ("Phase 4 sec.4.7: report the agreement-stratified curve "
                              "externally if per-annotator labels exist, and state "
                              "plainly that it cannot if they do not"),
                "adopted": ("not computed; stated plainly instead, as that clause "
                            "instructs"),
                "evidence": ("neither corpus ships per-annotator votes, so there is no "
                             "external vote entropy and no external agreement "
                             "stratification. The within-stratum rho that is RQ3's "
                             "internal primary quantity has no external counterpart."),
                "impact": ("RQ3's external half is tested as calibration-ordering "
                           "preservation (P5-C) rather than as a reproduction of the "
                           "entropy correlation."),
            },
            {
                "id": "P5-DEV-3",
                "item": "interval clustering unit",
                "blueprint": ("sec.6: all intervals patient-clustered, >=1,000 "
                              "resamples"),
                "adopted": "image-level bootstrap, 1,000 resamples",
                "evidence": ("no usable grouping key exists in either corpus; "
                             "HyperKvasir's 'Video file' column is unique per image "
                             "and GastroVision ships none."),
                "impact": ("Phase 5 intervals are optimistic relative to Phases 0-4 "
                           "and may not be compared directly against them. The "
                           ">=1,000 resample requirement is met."),
            },
            {
                "id": "P5-DEV-4",
                "item": "granularity of the external endpoint",
                "blueprint": ("sec.4 PHASE 5: build an explicit mapping table, state "
                              "its coarseness as a limitation, report the performance "
                              "drop"),
                "adopted": ("a 2-way anatomical collapse plus an out-of-protocol "
                            "rejection endpoint, instead of any station-level metric"),
                "evidence": mp["limitation_to_state_in_the_report"],
                "impact": ("Phase 5 cannot and does not test 23-way station "
                           "classification externally. This is a property of the "
                           "available public data, not of the model, and it is "
                           "reported as a finding in its own right."),
            },
        ],

        "falsification": (
            "P5-A is falsified as a transfer claim if the external binary macro F1 "
            "does not exceed the 50-point majority-class floor. P5-B's hypothesis is "
            "falsified if the model DOES reject out-of-protocol images above chance, "
            "which would be a better result than predicted and would have to be "
            "reported as such. P5-C is falsified if the calibration ordering does not "
            "survive the shift, which would downgrade the Phase 4 calibration finding "
            "to a dataset-specific one."),

        "scope_exclusions": [
            "no retraining of any arm",
            "no fine-tuning or domain adaptation on external data",
            "no self-training (that is Phase 5B, gated on these numbers being frozen)",
            "no threshold tuning or post-hoc temperature scaling on external data",
            "no Grad-CAM (Phase 6)",
            "no station-level external metric (P5-DEV-4)",
        ],

        "artefacts_to_be_produced": [
            "reports/phase5_infer_gate.json", "reports/phase5_probs_*.npz",
            "reports/phase5_transfer.json", "reports/phase5_rejection.json",
            "reports/phase5_calibration.json", "reports/phase5_uncertainty.json",
            "reports/phase5_sensitivity.json", "figures_phase5/P5_F33..F40_*.png",
            "Phase5_Report.docx", "Phase5_Report.pdf",
        ],
    }

    OUT.write_text(json.dumps(out, indent=1), encoding="utf-8")
    print(f"[P5.4] FROZEN -> {OUT}")
    print(f"       arms {out['arms']['carried']} x seeds {out['arms']['seeds']}")
    print(f"       P5-A  {n_gastric:,} gastric images "
          f"({n_by_label['RETROFLEXION']:,} retro / "
          f"{n_by_label['FORWARD_GASTRIC']:,} forward)")
    print(f"       P5-B  {n_by_label['OTHERCLASS']:,} out-of-protocol images, "
          f"chance rate {CHANCE_RATE:.4f}")
    print(f"       precision target: half-width <= "
          f"{PRECISION_TARGET_HALFWIDTH_POINTS} points on P5-A")
    print(f"       {len(out['deviations'])} declared deviations")
    return 0


if __name__ == "__main__":
    sys.exit(main())
