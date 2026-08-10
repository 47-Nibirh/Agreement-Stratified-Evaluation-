"""
Phase 3B / Stage F -- protocol amendment and analysis-provenance record.

Why this file exists.

Phase 2 shipped a machine-readable pre-registration (`reports/phase2_prereg.json`,
written before training). Phase 3 did not: its pre-registration lives only in
THESIS_RESEARCH_BLUEPRINT.md, which is a living document that was edited to
v3.2 *after* the phase ran, and its Appendix E is a prose paragraph rather
than the "verbatim, timestamped before P3.3 ran" record the blueprint's own
sec.14 specifies. The pre-registration claim is therefore not independently
verifiable from the committed artefacts.

That cannot be repaired retroactively, and this file does not pretend to. What
it does instead is state, explicitly and per analysis, which of three
categories each Phase 3 / 3B number belongs to:

  PRE-REGISTERED, EXECUTED       specified in blueprint sec.4/sec.13/sec.14
                                 before the run, and delivered.
  PRE-REGISTERED, NOT EXECUTED   specified before the run, omitted from the
    -> NOW EXECUTED IN 3B        delivered report, and supplied here. These
                                 remain confirmatory: their specification
                                 predates the data.
  POST-HOC                       devised after seeing the Phase 3 results.
                                 Exploratory. Reported as hypothesis-
                                 generating, never as confirmatory tests.

The distinction matters for exactly one reason: the ceiling-normalisation
analysis materially changes the headline RQ1 claim, and it is POST-HOC. It is
labelled as such wherever it appears, and the original pre-registered raw-scale
result is reported alongside it rather than replaced by it.

Outputs
  reports/phase3b_amendment.json
Run:  python src/models/phase3b_amendment.py
"""
from __future__ import annotations

import hashlib
import json
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
REPORTS = ROOT / "reports"

REGISTER = [
    # (id, description, status, artefact, blueprint reference)
    ("A1", "Agreement-tier construction from the 4-annotator vote matrix; tier "
           "counts gated at 803/342/127/73/8 before any inference",
     "PRE-REGISTERED, EXECUTED", "phase3_manifest_summary.json", "sec.4 Phase 3; sec.13 P3.1"),
    ("A2", "Pooling of S-tied and S-dispersed into S-no-majority",
     "PRE-REGISTERED, EXECUTED", "phase3_manifest_summary.json", "sec.4 Phase 3 decision 3"),
    ("A3", "Consistency gate: S-unanimous predictions reproduce Phase 2 exactly",
     "PRE-REGISTERED, EXECUTED", "phase3_stratified_metrics.json", "sec.13 P3.3"),
    ("A4", "Per-stratum annotator-marginalized macro F1, expected accuracy, "
           "any-annotator hit rate, per-tier patient-clustered bootstrap CIs",
     "PRE-REGISTERED, EXECUTED", "phase3_stratified_metrics.json", "sec.13 P3.4"),
    ("A5", "Spearman monotonicity test across the four ordered tiers",
     "PRE-REGISTERED, EXECUTED", "phase3_stratified_metrics.json", "sec.4 Phase 3 decision 4"),
    ("A6", "O3 wall-adjacent / station-neighbouring error shares vs the Phase 0 "
           "human benchmarks",
     "PRE-REGISTERED, EXECUTED", "phase3_confusion_structure.json", "sec.13 P3.5"),

    ("B1", "Patient-clustered bootstrap CI on the S-unanimous - S-no-majority "
           "gap, and its comparison against the 3.25-point architecture "
           "benchmark. Explicitly required by pre-registered decision 4 and "
           "absent from the delivered report: the headline claim was published "
           "with no interval on the quantity actually claimed.",
     "PRE-REGISTERED, NOT EXECUTED -> NOW EXECUTED IN 3B",
     "phase3b_ceiling_gaps.json", "sec.4 Phase 3 decision 4"),
    ("B2", "Per-class behaviour across strata (§3.6) and the per-class "
           "per-stratum tables promised by Appendix A",
     "PRE-REGISTERED, NOT EXECUTED -> NOW EXECUTED IN 3B",
     "phase3b_perclass.json", "sec.14 §3.6, Appendix A"),
    ("B3", "Calibration by stratum: ECE, MCE, reliability diagrams (§3.8). "
           "Blueprint sec.15 names absent calibration reporting as one of the "
           "four literature gaps this design claims to address directly.",
     "PRE-REGISTERED, NOT EXECUTED -> NOW EXECUTED IN 3B",
     "phase3b_calibration.json", "sec.14 §3.8; sec.15"),
    ("B4", "Acquisition-stream composition per stratum and the within-stream "
           "sensitivity re-run (§3.9.2, limitation L4)",
     "PRE-REGISTERED, NOT EXECUTED -> NOW EXECUTED IN 3B",
     "phase3b_sensitivity.json", "sec.14 §3.9.2"),
    ("B5", "Per-stratum 23x23 confusion matrices (Appendix B)",
     "PRE-REGISTERED, NOT EXECUTED -> NOW EXECUTED IN 3B",
     "phase3b_confusion_matrices.npz", "sec.14 Appendix B"),
    ("B6", "Bootstrap distribution diagnostics (Appendix C)",
     "PRE-REGISTERED, NOT EXECUTED -> NOW EXECUTED IN 3B",
     "phase3b_ceiling_gaps.json", "sec.14 Appendix C"),

    ("C1", "ATTAINABLE-CEILING NORMALISATION of the primary metric. Devised "
           "after observing that the raw tier curve conflates model "
           "degradation with the falling maximum score a single-label "
           "predictor can obtain as annotators disagree. Materially changes "
           "the headline RQ1 magnitude claim. POST-HOC and reported as such; "
           "the pre-registered raw-scale result is retained alongside it.",
     "POST-HOC (EXPLORATORY)", "phase3b_ceiling_gaps.json", "not pre-registered"),
    ("C2", "Class-composition control: S-unanimous per-class accuracy "
           "re-weighted by each contested tier's class mix, to test whether "
           "the tier effect is a class-mix effect",
     "POST-HOC (EXPLORATORY)", "phase3b_perclass.json", "not pre-registered"),
    ("C3", "Predictive entropy vs annotator vote entropy correlation, within "
           "and across tiers. De-risks Phase 4 RQ3 before it is committed to.",
     "POST-HOC (EXPLORATORY)", "phase3b_calibration.json", "sec.4 Phase 4 RQ3 (early read)"),
    ("C4", "Patient-clustered intervals on the O3 geometry shares, replacing "
           "the point-difference comparison against the human benchmarks",
     "POST-HOC (EXPLORATORY)", "phase3b_sensitivity.json", "extends sec.13 P3.5"),
    ("C5", "Zero-support diagnostic: how many classes enter the 23-class macro "
           "average with no support, and the resulting deflation",
     "POST-HOC (EXPLORATORY)", "phase3b_perclass.json", "not pre-registered"),
]

CORRECTIONS = [
    {"id": "X1",
     "location": "Phase3_Report §4.1 and THESIS_RESEARCH_BLUEPRINT.md completed-task register",
     "claim": "the any-annotator hit rate 'shows no such reversal' and therefore "
              "the non-monotonicity at S-plurality is measurement noise",
     "status": "FACTUALLY INCORRECT",
     "evidence": "The report's own Table 2 gives any-hit 84.39 / 80.02 / 72.70 / 79.83 "
                 "across the four ordered tiers -- the identical dip at S-plurality "
                 "followed by recovery. The metric shows the same reversal it was "
                 "cited as not showing.",
     "replacement": "The non-monotonicity is assessed by the S-plurality - "
                    "S-no-majority bootstrap gap: -4.63 points, 95% CI [-9.29, +1.87] "
                    "on the raw scale (not distinguishable from zero), and -17.83 "
                    "points, 95% CI [-31.25, -2.64] on the ceiling-normalised scale "
                    "(significantly negative -- a genuine reversal, not noise)."},
    {"id": "X2",
     "location": "Phase3_Report §3.5, §4.1",
     "claim": "the any-annotator hit rate is a fair cross-tier comparator",
     "status": "CONFOUNDED",
     "evidence": "The size of the accepted label set differs by tier: mean distinct "
                 "annotator labels per image is 1.00 (S-unanimous), 2.00 (S-majority), "
                 "3.00 (S-plurality), 2.20 (S-no-majority). A prediction has up to "
                 "three times as many ways to score a hit on S-plurality as on "
                 "S-unanimous.",
     "replacement": "Any-hit retained as a descriptive statistic only, reported with "
                    "its acceptance-set size, and never used to adjudicate a "
                    "cross-tier comparison."},
    {"id": "X3",
     "location": "Phase3_Report §3.7, §4.2, Table 4",
     "claim": "the model's wall-confusion geometry is 'within 0.12 points' of the "
              "human value and its station geometry 'trails by 7.53 points'",
     "status": "OVERPRECISE / NOT SUPPORTED",
     "evidence": "Both shares are ratios over 65-72 wall errors and 64-69 station "
                 "errors. Patient-clustered 95% CIs are [83.18, 96.00] for wall and "
                 "[76.68, 93.36] for station. The station interval CONTAINS the human "
                 "value 93.1, so the 7.5-point shortfall -- and the Phase 6 Grad-CAM "
                 "lead built on it -- is not statistically supported.",
     "replacement": "Both comparisons reported as intervals. The wall result is "
                    "stated as consistent with the human value; the station result "
                    "is stated as underpowered, and the Phase 6 lead is downgraded "
                    "from a finding to an untested hypothesis."},
    {"id": "X4",
     "location": "Phase3_Report abstract, §3.4, §5.1; blueprint status board",
     "claim": "a 53.1-point gap, 16.3x the 3.25-point architecture benchmark",
     "status": "SCALE ARTEFACT (direction survives, magnitude does not)",
     "evidence": "The primary metric's attainable maximum falls with agreement "
                 "(oracle marginalized macro F1: 100.00 / 74.23 / 44.55 / 40.23). "
                 "Holding the ceiling constant, the S-unanimous - S-no-majority gap "
                 "is 7.38 points, 95% CI [-3.08, +18.85] -- it does not exclude zero "
                 "and does not exceed the 3.25 benchmark. The S-unanimous - "
                 "S-majority (17.98, CI [12.49, 24.37]) and S-unanimous - S-plurality "
                 "(25.21, CI [16.11, 34.11]) contrasts do both survive.",
     "replacement": "RQ1 is answered as supported for the 4/4 -> 3/4 and 4/4 -> 2-1-1 "
                    "contrasts at 5.5-7.8x the architecture benchmark, and NOT "
                    "supported for the 4/4 -> no-majority contrast the report led "
                    "with. Raw and ceiling-normalised scales are both reported."},
]


def sha256(p: Path) -> str | None:
    if not p.exists():
        return None
    h = hashlib.sha256()
    h.update(p.read_bytes())
    return h.hexdigest()


def main() -> None:
    t0 = time.time()
    artefacts = {}
    for name in sorted({r[3] for r in REGISTER}):
        p = REPORTS / name
        artefacts[name] = {
            "exists": p.exists(),
            "sha256": sha256(p),
            "modified_utc": (datetime.fromtimestamp(p.stat().st_mtime, timezone.utc)
                             .isoformat() if p.exists() else None),
            "bytes": p.stat().st_size if p.exists() else None,
        }

    out = {
        "generated": time.strftime("%Y-%m-%d %H:%M:%S"),
        "document": "Phase 3 protocol amendment and analysis-provenance record",
        "why": ("Phase 3 shipped without a machine-readable pre-registration file "
                "(Phase 2 had one) and with a prose Appendix E rather than the "
                "verbatim timestamped record its own blueprint sec.14 specifies. "
                "This record cannot restore a pre-registration after the fact; it "
                "classifies every analysis so a reader can tell confirmatory from "
                "exploratory."),
        "categories": {
            "PRE-REGISTERED, EXECUTED": "specified before the run and delivered",
            "PRE-REGISTERED, NOT EXECUTED -> NOW EXECUTED IN 3B":
                "specified before the run, omitted from the delivered report, "
                "supplied in Phase 3B; still confirmatory",
            "POST-HOC (EXPLORATORY)":
                "devised after seeing Phase 3 results; hypothesis-generating only",
        },
        "analysis_register": [
            {"id": i, "analysis": d, "status": s, "artefact": a, "blueprint_ref": r}
            for i, d, s, a, r in REGISTER],
        "corrections_to_the_delivered_report": CORRECTIONS,
        "counts": {
            "pre_registered_executed": sum(1 for r in REGISTER if r[2].startswith("PRE-REGISTERED, EXECUTED")),
            "pre_registered_not_executed_now_supplied": sum(1 for r in REGISTER if "NOT EXECUTED" in r[2]),
            "post_hoc": sum(1 for r in REGISTER if r[2].startswith("POST-HOC")),
            "corrections": len(CORRECTIONS),
        },
        "artefact_provenance": artefacts,
        "runtime_sec": round(time.time() - t0, 2),
    }
    (REPORTS / "phase3b_amendment.json").write_text(json.dumps(out, indent=2), encoding="utf-8")
    c = out["counts"]
    print(f"analysis register: {c['pre_registered_executed']} pre-registered+executed, "
          f"{c['pre_registered_not_executed_now_supplied']} pre-registered but omitted (now supplied), "
          f"{c['post_hoc']} post-hoc")
    print(f"corrections to the delivered report: {c['corrections']}")
    for k, v in artefacts.items():
        print(f"  {'OK ' if v['exists'] else 'MISSING'} {k}")


if __name__ == "__main__":
    main()
