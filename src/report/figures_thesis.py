"""
Phase 7 / P7.4 -- the thesis figure suite.

Phase-local figure numbering (F01-F20 for Phases 0-1, P2_F01-F11, P3_F21-F30,
P4_F25-F32, P5_F33-F37, P6_F38-F45) collides across phases: there are two F25s
and two F01 series. That is harmless inside a phase report and unusable inside
one document.

This script does NOT regenerate the figures. Every one of them was produced by
its phase's figure script from a JSON artefact and is already correct; redrawing
them here would create a second code path capable of disagreeing with the first.
It selects the subset the thesis argument actually needs, copies them into
figures_thesis/ under continuous numbering, and writes a registry recording the
mapping so any figure in the thesis can be traced back to the phase script that
drew it.

Selection principle: a figure earns its place by carrying a step in the thesis
argument, not by existing. Sixty-three figures exist; the thesis uses the subset
below and the phase reports remain in the repository as the full record.

Outputs
  figures_thesis/T##_*.png
  reports/phase7_figure_registry.json
Run:  python src/report/figures_thesis.py
"""
from __future__ import annotations

import json
import shutil
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUTDIR = ROOT / "figures_thesis"
REGISTRY = ROOT / "reports" / "phase7_figure_registry.json"

# (source dir, source file, thesis caption slug, chapter, why it earns its place)
PLAN = [
    ("figures_v2", "F19_conceptual_framework.png", "conceptual_framework", 1,
     "the thesis's framing: ground truth as a constructed object"),
    ("figures_v2", "F01_thesis_workflow.png", "workflow", 1,
     "the seven-phase structure and what each phase gates"),
    ("figures_v2", "F03_sss_taxonomy.png", "sss_taxonomy", 2,
     "the wall x station grid that is the thesis's main analytical lever"),
    ("figures_v2", "F05_kappa_matrix.png", "kappa_matrix", 2,
     "seniority does not predict agreement; FG1-FG2 is the weakest pair"),
    ("figures_v2", "F06_agreement_cascade.png", "agreement_cascade", 2,
     "only 60.2% of the corpus is unanimous -- the fact the literature evaluates on"),
    ("figures_v2", "F07_disagreement_decomposition.png", "disagreement_decomposition", 2,
     "50.96% of disagreement is wall-within-station: disagreement is structured"),
    ("figures_v2", "F09_otherclass.png", "otherclass", 2,
     "a 6x spread in rejection rate: quality judgement is a different task"),
    ("figures_v2", "F15b_dup_calibration.png", "dup_calibration", 2,
     "54 contamination pairs became 0 once the threshold was calibrated"),
    ("figures_v2", "F13_test_power.png", "test_power", 2,
     "22/23 classes underpowered -- the basis for limitation L1"),
    ("figures_v2", "F17_prisma.png", "prisma", 3,
     "PRISMA 2020 flow, 1,349 unique records to 82 included"),
    ("figures_v2", "F18_literature.png", "literature_gaps", 3,
     "the four commonest omissions this design addresses"),
    ("figures_phase2", "P2_F10_verdict.png", "baseline_reproduction", 4,
     "the pipeline reproduces the published baseline before anything is changed"),
    ("figures_phase3", "P3_F21_stratified_curve.png", "stratified_curve_raw", 4,
     "the raw stratified decline -- the number the literature would report"),
    ("figures_phase3", "P3_F25_ceiling_normalised_curve.png", "stratified_curve_ceiling", 4,
     "the same decline once the attainable ceiling is held constant"),
    ("figures_phase3", "P3_F26_pairwise_gap_forest.png", "gap_forest", 4,
     "RQ1's confirmatory endpoint with patient-clustered intervals"),
    ("figures_phase3", "P3_F27_calibration_by_stratum.png", "calibration_by_stratum", 4,
     "the calibration collapse: ECE 9.15% to 56.40% -- the durable finding"),
    ("figures_phase3", "P3_F30_confound_controls.png", "confound_controls", 4,
     "class and acquisition-stream composition do not explain the effect"),
    ("figures_phase4", "P4_F25_design.png", "config_design", 5,
     "five targets, one cohort, one thing varying"),
    ("figures_phase4", "P4_F27_contrast_forest.png", "rq2_forest", 5,
     "RQ2's pre-registered contrast against the matched control"),
    ("figures_phase4", "P4_F28_calibration.png", "calibration_by_config", 5,
     "the reversal: the control is better calibrated where it matters"),
    ("figures_phase4", "P4_F29_overconfidence.png", "overconfidence", 5,
     "confidence falls 9 points while accuracy falls 57"),
    ("figures_phase5", "P5_F33_label_space.png", "external_label_space", 6,
     "the label-space finding that precedes any transfer number"),
    ("figures_phase5", "P5_F35_transfer.png", "external_transfer", 6,
     "P5-A: transfer with a drop twice the pre-registered expectation"),
    ("figures_phase5", "P5_F36_rejection.png", "external_rejection", 6,
     "P5-B falsified favourably: rejection at 63.4% against a 4.35% floor"),
    ("figures_phase6", "P6_F38_human_comparator.png", "human_comparator", 7,
     "the model between an individual annotator and the modal-vote oracle"),
    ("figures_phase6", "P6_F39_confusion_geometry.png", "confusion_geometry", 7,
     "wall geometry mirrors humans; station geometry does not"),
    ("figures_phase6", "P6_F40_dispersion_vs_entropy.png", "attribution_not_estimable", 7,
     "why the pre-registered attribution endpoint cannot be computed"),
    ("figures_phase6", "P6_F41_attribution_stability.png", "attribution_stability", 7,
     "soft targets buy spatial consistency across seeds"),
    ("figures_phase6", "P6_F44_risk_coverage_external.png", "risk_coverage_external", 7,
     "the endpoint that actually separates the configurations"),
    ("figures_phase6", "P6_F45_synthesis.png", "endpoint_synthesis", 7,
     "no configuration wins everywhere -- the rows disagree"),
    ("figures_v2", "F16_negative_control.png", "negative_control", 8,
     "the retired corpus as the audit protocol's negative control"),
]


def main() -> None:
    t0 = time.time()
    OUTDIR.mkdir(exist_ok=True)
    for old in OUTDIR.glob("T*.png"):
        old.unlink()

    registry, missing = [], []
    n = 0
    for src_dir, src_file, slug, chapter, why in PLAN:
        src = ROOT / src_dir / src_file
        if not src.exists():
            missing.append(f"{src_dir}/{src_file}")
            continue
        n += 1
        dst_name = f"T{n:02d}_{slug}.png"
        shutil.copy2(src, OUTDIR / dst_name)
        registry.append({
            "thesis_figure": f"T{n:02d}",
            "file": dst_name,
            "chapter": chapter,
            "source_dir": src_dir,
            "source_file": src_file,
            "drawn_by": {
                "figures_v2": "src/report/figures_v2.py",
                "figures_phase2": "src/report/figures_phase2.py",
                "figures_phase3": "src/report/figures_phase3.py (and figures_phase3b.py)",
                "figures_phase4": "src/report/figures_phase4.py",
                "figures_phase5": "src/report/figures_phase5.py",
                "figures_phase6": "src/report/figures_phase6.py",
            }[src_dir],
            "why_it_earns_its_place": why,
        })

    payload = {
        "generated": time.strftime("%Y-%m-%d %H:%M:%S"),
        "phase": 7, "step": "P7.4",
        "principle": ("figures are SELECTED and RENUMBERED, never redrawn. Redrawing "
                      "would create a second code path capable of disagreeing with the "
                      "phase figure it duplicates. Each thesis figure traces to the "
                      "phase script that produced it, recorded below."),
        "n_selected": n,
        "n_available_total": sum(len(list((ROOT / d).glob("*.png")))
                                 for d in ("figures_v2", "figures_phase2", "figures_phase3",
                                           "figures_phase4", "figures_phase5", "figures_phase6")
                                 if (ROOT / d).exists()),
        "missing_sources": missing,
        "registry": registry,
        "runtime_sec": round(time.time() - t0, 1),
    }
    REGISTRY.write_text(json.dumps(payload, indent=1), encoding="utf-8")
    print(f"[P7.4] {n} figures selected from {payload['n_available_total']} available "
          f"-> {OUTDIR.name}/")
    by_ch = {}
    for r in registry:
        by_ch.setdefault(r["chapter"], []).append(r["thesis_figure"])
    for ch in sorted(by_ch):
        print(f"   chapter {ch}: {', '.join(by_ch[ch])}")
    if missing:
        print(f"[P7.4] WARNING missing sources: {missing}")


if __name__ == "__main__":
    main()
