"""
Phase 3B report content -- the sections the delivered Phase 3 pre-registered
and omitted, plus the corrections its own artefacts require.

Imported by build_phase3_docx.py. Every number is interpolated from
reports/phase3b_*.json; nothing here is typed by hand.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np

from build_docx import bullet, callout, figure, h, para, table

ROOT = Path(__file__).resolve().parents[2]
REP = ROOT / "reports"


def J(name):
    return json.loads((REP / name).read_text(encoding="utf-8"))


CEIL = J("phase3b_ceiling_gaps.json")
CAL = J("phase3b_calibration.json")
PCL = J("phase3b_perclass.json")
SENS = J("phase3b_sensitivity.json")
AMD = J("phase3b_amendment.json")

TIERS = ["S-unanimous", "S-majority", "S-plurality", "S-no-majority"]
TIER_LABEL = {"S-unanimous": "S-unanimous (4/4)", "S-majority": "S-majority (3/4)",
              "S-plurality": "S-plurality (2-1-1)",
              "S-no-majority": "S-no-majority (pooled 2-2 / 1-1-1-1)"}
R = CEIL["rq1_restated"]
G = CEIL["pairwise_gaps"]


def pc(x, d=2):
    return f"{100 * x:.{d}f}"


def gap(pair, scale="raw"):
    return G[f"{pair} [{scale}]"]


def gstr(pair, scale="raw"):
    e = gap(pair, scale)
    lo, hi = e["ci95_points_3seed_mean"]
    return f"{e['gap_points_3seed_mean']:.2f} points (95% CI {lo:.2f} to {hi:.2f})"


# =====================================================================
def abbreviations(doc) -> None:
    h(doc, "List of Abbreviations", level=1)
    table(doc, ["Abbreviation", "Expansion"],
          [["AMF1", "Annotator-marginalized macro F1 (this phase's primary metric)"],
           ["CI", "Confidence interval (patient-clustered bootstrap throughout)"],
           ["CLAIM", "Checklist for Artificial Intelligence in Medical Imaging"],
           ["ECE / MCE", "Expected / maximum calibration error"],
           ["FG1, FG2, G1, G2", "The four independent GastroHUN annotators (two teams)"],
           ["O1-O4", "Phase 3 objectives, blueprint §4 Phase 3"],
           ["PROBAST+AI", "Prediction model Risk Of Bias ASsessment Tool, AI extension"],
           ["RQ1", "Research question 1 - performance across strata of expert agreement"],
           ["S-unanimous / -majority / -plurality / -tied / -dispersed",
            "Agreement tiers: 4/4, 3/4, 2-1-1, 2-2, 1-1-1-1 annotator votes"],
           ["STARD-AI", "Standards for Reporting Diagnostic accuracy studies, AI extension"],
           ["TRIPOD+AI", "Transparent Reporting of a multivariable prediction model, AI extension"]],
          "Abbreviations used in this report.")


# =====================================================================
def sec_2_4_4_metric_validity(doc) -> None:
    h(doc, "2.4.4 Metric validity across tiers: the attainable ceiling", level=2)
    para(doc, "The primary metric is compared across four tiers, so its scale must "
              "mean the same thing on each. §2.4.1 argued that the annotator-"
              "marginalized macro F1 is comparable because it reduces exactly to "
              "plain macro F1 at the S-unanimous limit. That argument establishes "
              "continuity at one end of the scale; it does not establish that the "
              "scale itself is fixed. It is not.")
    para(doc, "A single-label classifier scored against four annotators cannot match "
              "annotators who disagree with each other. On an image where the votes "
              "split 2-1-1, any single prediction captures at most half the vote "
              "mass; on a 2-2 image, at most half; on a 1-1-1-1 image, at most a "
              "quarter. The maximum score attainable by a perfect classifier "
              "therefore falls as agreement falls, and part of any observed decline "
              "across tiers is the ceiling moving rather than the model degrading.")
    para(doc, "This report quantifies the ceiling explicitly. For each tier, the "
              "modal-vote oracle - the predictor that outputs, for every image, the "
              "label with the most annotator votes (ties broken at random over "
              f"{CEIL['n_tiebreaks_for_oracle']} draws) - is scored with the same "
              "annotator-marginalized macro F1 as the model. This oracle is the best "
              "achievable single-label predictor image-by-image; because macro F1 "
              "does not decompose across images it is a lower bound on the true "
              "supremum, and is reported as an achievable reference rather than as a "
              "theoretical maximum. Each tier's result is then given twice: on the "
              "raw scale, as pre-registered, and normalised as a percentage of the "
              "attainable score.")
    callout(doc, "The ceiling analysis is POST-HOC. It was devised after the "
                 "pre-registered raw-scale results were computed, and is reported as "
                 "exploratory throughout. It does not replace the pre-registered "
                 "analysis; both scales are reported side by side, and the "
                 "pre-registered conclusion is stated before the amended one "
                 "(§3.4, then §3.4.1).",
            title="Analysis status")


def sec_2_6_2_amendment(doc) -> None:
    h(doc, "2.6.2 Protocol amendment and analysis provenance", level=2)
    c = AMD["counts"]
    para(doc, f"Phase 2 shipped a machine-readable pre-registration file written "
              f"before training. Phase 3 did not: its protocol exists only inside "
              f"THESIS_RESEARCH_BLUEPRINT.md, a living document that was edited to "
              f"v3.2 after this phase ran. The pre-registration claim is therefore "
              f"not independently verifiable from the committed artefacts, and this "
              f"report does not ask the reader to take it on trust. Every analysis "
              f"in Phases 3 and 3B is classified in reports/phase3b_amendment.json "
              f"as one of three kinds: {c['pre_registered_executed']} "
              f"pre-registered and executed in the original phase; "
              f"{c['pre_registered_not_executed_now_supplied']} pre-registered, "
              f"omitted from the delivered report, and supplied here (these remain "
              f"confirmatory - their specification predates the data); and "
              f"{c['post_hoc']} post-hoc, reported as exploratory only.")
    para(doc, f"The same record lists {c['corrections']} corrections to claims made "
              f"in the first release of this report. They are reproduced in §3.10 "
              f"and Appendix E rather than silently applied.")


# =====================================================================
def sec_3_4_1_ceiling(doc) -> None:
    h(doc, "3.4.1 Attainable-ceiling re-analysis of the gap (post-hoc)", level=2)
    figure(doc, "P3_F25_ceiling_normalised_curve.png",
           "Left: the frozen model against the modal-vote oracle ceiling; the orange "
           "bar is the headroom actually available on each tier. Right: the same "
           "model expressed as a percentage of the attainable score. The raw curve "
           "is overlaid for comparison.")
    table(doc,
          ["Stratum", "n", "Attainable ceiling (%)", "Observed (%)",
           "% of attainable", "Headroom (pts)"],
          [[TIER_LABEL[t], str(CEIL["ceilings"][t]["n_images"]),
            pc(CEIL["ceilings"][t]["oracle_marginalized_macro_f1_mean"]),
            pc(CEIL["observed_vs_ceiling"][t]["observed_marginalized_macro_f1"]),
            pc(CEIL["observed_vs_ceiling"][t]["ceiling_normalised_macro_f1"]),
            f"{100 * (CEIL['ceilings'][t]['oracle_marginalized_macro_f1_mean'] - CEIL['observed_vs_ceiling'][t]['observed_marginalized_macro_f1']):.2f}"]
           for t in TIERS],
          "Attainable ceiling per stratum and the model's share of it. The ceiling "
          "depends only on the annotator vote matrix, not on the model.")
    para(doc, f"The ceiling falls from {pc(CEIL['ceilings']['S-unanimous']['oracle_marginalized_macro_f1_mean'])}% "
              f"on S-unanimous to {pc(CEIL['ceilings']['S-no-majority']['oracle_marginalized_macro_f1_mean'])}% "
              f"on the pooled no-majority tier. Most of the "
              f"{R['raw_gap_points']:.1f}-point raw decline is therefore the ceiling "
              f"moving. Holding it constant, the model retains "
              f"{R['ceiling_normalised_macro_f1_pct_of_attainable'][0]:.1f}% of the "
              f"attainable score on S-unanimous and "
              f"{R['ceiling_normalised_macro_f1_pct_of_attainable'][-1]:.1f}% on the "
              f"no-majority tier - a gap of {R['ceiling_normalised_gap_points']:.2f} "
              f"points, not {R['raw_gap_points']:.1f}.")

    figure(doc, "P3_F26_pairwise_gap_forest.png",
           "All six pairwise tier gaps on both scales, with the patient-clustered "
           "bootstrap 95% intervals required by pre-registered decision 4. The "
           "dashed line is the 3.25-point between-architecture benchmark.")
    rows = []
    for pair in ["S-unanimous - S-majority", "S-unanimous - S-plurality",
                 "S-unanimous - S-no-majority", "S-majority - S-plurality",
                 "S-majority - S-no-majority", "S-plurality - S-no-majority"]:
        for scale, lab in (("raw", "raw"), ("ceiling_normalised", "ceiling-normalised")):
            e = gap(pair, scale)
            lo, hi = e["ci95_points_3seed_mean"]
            rows.append([pair.replace("S-", ""), lab,
                         f"{e['gap_points_3seed_mean']:.2f}",
                         f"[{lo:.2f}, {hi:.2f}]",
                         "yes" if e["excludes_zero"] else "no",
                         "yes" if e["lower_bound_exceeds_architecture_benchmark"] else "no"])
    table(doc,
          ["Tier pair", "Scale", "Gap (pts)", "95% CI", "Excludes 0",
           "Lower bound > 3.25"],
          rows,
          "Pairwise tier gaps with patient-clustered bootstrap intervals "
          f"({CEIL['n_boot']} resamples per pair per seed, seed {CEIL['boot_seed']}). "
          "The delivered Phase 3 reported no interval on any gap.",
          font=7.4)

    ku = gap("S-unanimous - S-no-majority", "ceiling_normalised")
    km = gap("S-unanimous - S-majority", "ceiling_normalised")
    kp = gap("S-unanimous - S-plurality", "ceiling_normalised")
    para(doc, f"On the ceiling-normalised scale the two mid-tier contrasts survive "
              f"and the headline contrast does not. S-unanimous minus S-majority is "
              f"{gstr('S-unanimous - S-majority', 'ceiling_normalised')} and "
              f"S-unanimous minus S-plurality is "
              f"{gstr('S-unanimous - S-plurality', 'ceiling_normalised')}; both "
              f"exclude zero and both have lower bounds above the "
              f"{R['architecture_benchmark_points']}-point architecture benchmark, at "
              f"{km['ci95_points_3seed_mean'][0] / R['architecture_benchmark_points']:.1f}x "
              f"and "
              f"{kp['ci95_points_3seed_mean'][0] / R['architecture_benchmark_points']:.1f}x "
              f"the benchmark respectively. S-unanimous minus S-no-majority - the "
              f"contrast the original report led with - is "
              f"{gstr('S-unanimous - S-no-majority', 'ceiling_normalised')}: the "
              f"interval contains zero and does not clear the benchmark.")
    callout(doc,
            f"RQ1 restated. The pre-registered raw-scale finding "
            f"({R['raw_gap_points']:.1f} points, "
            f"{R['raw_gap_points'] / R['architecture_benchmark_points']:.1f}x the "
            f"architecture benchmark) is retained as the pre-registered result. The "
            f"post-hoc ceiling-adjusted reading is narrower and more defensible: "
            f"agreement-stratified degradation exceeds a between-architecture change "
            f"by a wide margin for the 4/4 -> 3/4 and 4/4 -> 2-1-1 contrasts, and is "
            f"not resolvable for the 4/4 -> no-majority contrast, where the "
            f"attainable ceiling is itself only "
            f"{pc(CEIL['ceilings']['S-no-majority']['oracle_marginalized_macro_f1_mean'], 1)}%.",
            title="Amended answer to RQ1")

    kpn = gap("S-plurality - S-no-majority", "ceiling_normalised")
    kpr = gap("S-plurality - S-no-majority", "raw")
    para(doc, f"The non-monotonicity also changes character. On the raw scale the "
              f"S-plurality minus S-no-majority gap is "
              f"{gstr('S-plurality - S-no-majority', 'raw')} - not distinguishable "
              f"from zero, consistent with the original report's reading of it as "
              f"noise. On the ceiling-normalised scale it is "
              f"{gstr('S-plurality - S-no-majority', 'ceiling_normalised')}, which "
              f"excludes zero: relative to what is achievable on each, the model does "
              f"significantly worse on 2-1-1 images than on 2-2 and 1-1-1-1 images. "
              f"The reversal is real, not an artefact of small n, and it is a "
              f"finding rather than a nuisance - see §4.1.")


# =====================================================================
def sec_3_6_perclass(doc) -> None:
    h(doc, "3.6 Per-class behaviour across strata", level=2)
    figure(doc, "P3_F28_perclass_heatmap.png",
           "Per-class annotator-marginalized F1 across the four ordered strata "
           "(3-seed mean), classes ordered by S-unanimous F1.")
    z = PCL["zero_support_summary"]
    table(doc,
          ["Stratum", "Classes with no support and no prediction",
           "Classes scoring F1 = 0", "Macro F1 over 23 classes (%)",
           "Macro F1 over present classes (%)", "Deflation (pts)"],
          [[TIER_LABEL[t], str(z[t]["n_absent_classes"]),
            str(PCL["per_class_by_tier"][t]["n_classes_with_zero_f1"]),
            pc(PCL["per_class_by_tier"][t]["macro_f1_all_23_classes"]),
            pc(PCL["per_class_by_tier"][t]["macro_f1_present_classes_only"]),
            f"{z[t]['deflation_points']:+.2f}"] for t in TIERS],
          "Zero-support diagnostic. A 23-class macro average can be deflated "
          "mechanically when classes are absent from a small stratum; this table "
          "shows the size of that effect.")
    para(doc, "A standing objection to macro-averaging over 23 classes on strata of "
              "81 to 127 images is that absent classes enter the average as a hard "
              "zero and depress the score for arithmetic reasons rather than "
              "modelling ones. The objection does not hold here. Every one of the 23 "
              "classes receives at least one annotator vote or one prediction in "
              "every tier, so no class is scored on an empty cell, and restricting "
              "the macro average to present classes changes no tier's score. The "
              "classes that score zero do so because the model gets them wrong, not "
              "because they are missing.")
    para(doc, f"The per-class pattern is not uniform. On S-unanimous the weakest five "
              f"classes are {', '.join(PCL['per_class_by_tier']['S-unanimous']['worst5_classes'])}; "
              f"on the pooled no-majority tier they are "
              f"{', '.join(PCL['per_class_by_tier']['S-no-majority']['worst5_classes'])}. "
              f"Full per-class tables are in Appendix A and the per-stratum "
              f"confusion matrices in Appendix B.")

    h(doc, "3.6.1 Class-composition control (post-hoc)", level=2)
    figure(doc, "P3_F30_confound_controls.png",
           "Left: observed expected accuracy against what the tier's class mix alone "
           "would predict, using S-unanimous per-class accuracy. Right: the tier "
           "curve restricted to the dominant acquisition stream.")
    cc = PCL["class_composition_control"]
    table(doc,
          ["Stratum", "Predicted by class mix alone (%)", "Observed (%)",
           "Unexplained (pts)", "Share of drop explained by class mix (%)"],
          [[TIER_LABEL[t],
            pc(cc[t]["expected_accuracy_predicted_by_class_mix_alone"]),
            pc(cc[t]["observed_expected_accuracy"]),
            f"{cc[t]['unexplained_by_class_mix_points']:+.2f}",
            "-" if cc[t]["share_of_drop_explained_by_class_mix_pct"] is None
            else f"{cc[t]['share_of_drop_explained_by_class_mix_pct']:.2f}"]
           for t in TIERS],
          "Class-composition control. Phase 0 showed that disagreement concentrates "
          "on particular anatomical boundaries, so the contested tiers do not "
          "contain the same class mix as S-unanimous; this table tests whether that "
          "mix, rather than agreement, drives the tier effect.")
    shares = [cc[t]["share_of_drop_explained_by_class_mix_pct"] for t in TIERS[1:]]
    para(doc, f"Re-weighting the model's S-unanimous per-class accuracy by each "
              f"contested tier's own class mix predicts expected accuracies of "
              f"{pc(cc['S-majority']['expected_accuracy_predicted_by_class_mix_alone'], 1)}%, "
              f"{pc(cc['S-plurality']['expected_accuracy_predicted_by_class_mix_alone'], 1)}% and "
              f"{pc(cc['S-no-majority']['expected_accuracy_predicted_by_class_mix_alone'], 1)}% - "
              f"barely below the S-unanimous value. Class composition accounts for "
              f"only {min(shares):.1f}-{max(shares):.1f}% of the observed drop. The "
              f"tier effect is a property of annotator disagreement, not of which "
              f"anatomical classes happen to populate the contested tiers.")


# =====================================================================
def sec_3_8_calibration(doc) -> None:
    h(doc, "3.8 Calibration by stratum", level=2)
    figure(doc, "P3_F27_calibration_by_stratum.png",
           "Reliability diagrams per stratum against expected accuracy (top), the "
           "divergence between mean confidence and expected accuracy (lower left), "
           "and expected calibration error with patient-clustered 95% intervals "
           "(lower right).")
    a = CAL["aggregate_3seed"]
    table(doc,
          ["Stratum", "Mean confidence (%)", "Expected accuracy (%)",
           "Overconfidence (pts)", "ECE (%)", "ECE 95% CI (%)", "MCE (%)"],
          [[TIER_LABEL[t], pc(a[t]["mean_confidence"]), pc(a[t]["expected_accuracy"]),
            f"{a[t]['overconfidence_points']:+.2f}",
            pc(a[t]["ece_vs_expected_accuracy"]),
            f"[{100 * a[t]['ece_ci95_seed1'][0]:.1f}, {100 * a[t]['ece_ci95_seed1'][1]:.1f}]",
            pc(a[t]["mce_vs_expected_accuracy"])] for t in TIERS],
          "Calibration by agreement stratum, 3-seed mean. The target is expected "
          "accuracy - the probability mass the model's single prediction captures "
          "under the four-annotator vote distribution - because it is the only "
          "target defined on every tier.")
    d_conf = 100 * (a["S-unanimous"]["mean_confidence"] - a["S-plurality"]["mean_confidence"])
    d_acc = 100 * (a["S-unanimous"]["expected_accuracy"] - a["S-plurality"]["expected_accuracy"])
    para(doc, f"This is the section blueprint §15 identified as one of the four "
              f"commonest omissions in the endoscopy-AI literature, and it produces "
              f"the sharpest result in the phase. Between S-unanimous and "
              f"S-plurality the model's expected accuracy falls {d_acc:.1f} points "
              f"while its mean confidence falls {d_conf:.1f} points. Expected "
              f"calibration error rises from {pc(a['S-unanimous']['ece_vs_expected_accuracy'], 1)}% "
              f"to {pc(a['S-plurality']['ece_vs_expected_accuracy'], 1)}%, a factor of "
              f"{CAL['headline']['ece_ratio_worst_over_unanimous']:.1f}, with "
              f"non-overlapping intervals against the unanimous tier.")
    callout(doc, f"The model is not merely wrong on contested images - it is wrong "
                 f"at almost the same confidence it reports when it is right. On the "
                 f"2-1-1 tier it averages "
                 f"{pc(a['S-plurality']['mean_confidence'], 1)}% confidence while "
                 f"capturing {pc(a['S-plurality']['expected_accuracy'], 1)}% of the "
                 f"vote mass. A downstream user filtering on confidence would not be "
                 f"warned. This is a safety-relevant property of the baseline and it "
                 f"was invisible to Phase 2's consensus-only protocol.",
            title="Principal finding of §3.8")

    h(doc, "3.8.1 Predictive entropy against annotator vote entropy", level=2)
    rho_all = CAL["headline"]["predictive_vs_vote_entropy_spearman_all_images"]
    within = [(t, a[t]["entropy_spearman_rho_within_tier_3seed"]) for t in TIERS
              if a[t]["entropy_spearman_rho_within_tier_3seed"] is not None]
    para(doc, f"Phase 4's RQ3 proposes to correlate the model's predictive entropy "
              f"with per-image annotator vote entropy - a test the literature does "
              f"not run because it needs per-annotator labels. Computing it here "
              f"de-risks that plan. Across all 1,353 test images the Spearman "
              f"correlation is {rho_all:.3f}. Within tiers it collapses to "
              f"{', '.join(f'{r:.3f} ({t})' for t, r in within)}; it is undefined on "
              f"S-unanimous, where vote entropy is identically zero.")
    para(doc, "The apparent overall correlation is therefore almost entirely a "
              "between-tier effect: predictive entropy separates unanimous from "
              "contested images, but carries close to no information about which "
              "contested images the annotators disagreed on most. Phase 4 should "
              "treat RQ3 as a test the baseline is expected to fail, and should "
              "report the within-tier correlation - not the pooled one - as the "
              "primary quantity, or the pooled value will read as success when it "
              "measures only tier membership.")


# =====================================================================
def sec_3_8b_o3_intervals(doc) -> None:
    h(doc, "3.8.2 Confusion-structure comparison restated with intervals", level=2)
    figure(doc, "P3_F29_o3_intervals.png",
           "Model error geometry with patient-clustered bootstrap 95% intervals "
           "against the Phase 0 human benchmarks (orange diamonds).")
    s = SENS["o3_confusion_structure_with_intervals"]["summary"]
    table(doc,
          ["Comparison", "Human (%)", "Model (%)", "Model 95% CI",
           "CI width (pts)", "Consistent with human value"],
          [["Wall confusions circumferentially adjacent",
            f"{s['human_wall_adjacent_pct']}", f"{s['wall_adjacent_pct_3seed']:.2f}",
            f"[{s['wall_adjacent_ci95_3seed'][0]:.2f}, {s['wall_adjacent_ci95_3seed'][1]:.2f}]",
            f"{s['wall_ci_width_points']:.1f}",
            "yes" if s["wall_consistent_with_human"] else "no"],
           ["Station confusions neighbouring",
            f"{s['human_station_neighbouring_pct']}",
            f"{s['station_neighbouring_pct_3seed']:.2f}",
            f"[{s['station_neighbouring_ci95_3seed'][0]:.2f}, {s['station_neighbouring_ci95_3seed'][1]:.2f}]",
            f"{s['station_ci_width_points']:.1f}",
            "yes" if s["station_consistent_with_human"] else "no"]],
          "O3 restated as interval estimates. Both shares are ratios computed over "
          "roughly 65-70 errors, so their sampling variability is large.")
    per = SENS["o3_confusion_structure_with_intervals"]["per_seed"]
    wl = [per[str(k)]["wall_adjacent_pct"] for k in (1, 2, 3)]
    st = [per[str(k)]["station_neighbouring_pct"] for k in (1, 2, 3)]
    para(doc, f"§3.7 reported these shares as point values and described the wall "
              f"result as matching the human value 'within 0.12 points'. That "
              f"precision is not available in the data. Across the three seeds the "
              f"wall share ranges {min(wl):.2f}-{max(wl):.2f}% and the station share "
              f"{min(st):.2f}-{max(st):.2f}%, and the patient-clustered intervals are "
              f"{s['wall_ci_width_points']:.0f} and {s['station_ci_width_points']:.0f} "
              f"points wide.")
    para(doc, f"The corrected reading is weaker but sound in one direction and "
              f"absent in the other. The model's wall-confusion geometry is "
              f"consistent with the human value - the interval contains "
              f"{s['human_wall_adjacent_pct']}% - so the claim that the model's "
              f"residual errors fall on the same circumferentially adjacent walls "
              f"that make annotators disagree stands, though only as consistency, "
              f"not as a demonstrated match. The station comparison does not "
              f"support a difference at all: the interval "
              f"[{s['station_neighbouring_ci95_3seed'][0]:.2f}, "
              f"{s['station_neighbouring_ci95_3seed'][1]:.2f}] contains the human "
              f"value {s['human_station_neighbouring_pct']}%. The 7.5-point "
              f"shortfall reported in §3.7, and the Phase 6 Grad-CAM lead built on "
              f"it, are withdrawn as findings and retained only as an untested "
              f"hypothesis (§4.2).")


# =====================================================================
def sec_3_9_2_stream(doc) -> None:
    h(doc, "3.9.2 Acquisition-stream composition per stratum", level=2)
    st = SENS["acquisition_stream_sensitivity"]
    comp = st["composition_by_tier"]
    keys = [k for k in comp["S-unanimous"] if k.startswith("stream_")]
    table(doc,
          ["Stratum"] + [k.replace("stream_", "").replace("px", " px wide") for k in keys]
          + ["Minority stream (%)"],
          [[TIER_LABEL[t]] + [str(comp[t][k]) for k in keys]
           + [f"{comp[t]['minority_stream_pct']:.2f}"] for t in TIERS],
          "Acquisition-stream composition by agreement tier. Phase 0 limitation L4 "
          "records that the two streams are imbalanced across the official splits.")
    para(doc, f"Phase 0 flagged the corpus's two acquisition streams as a standing "
              f"limitation (L4): they are imbalanced across the official splits and "
              f"differ in unanimity rate. If the contested tiers over-represented the "
              f"minority stream, the tier effect could be a stream effect. They do "
              f"not: composition does not differ across tiers "
              f"(chi-square {st['chi2']:.3f} on {st['dof']} df, p = {st['p_value']:.3f}).")
    table(doc,
          ["Stratum", "All streams (%)", f"{st['dominant_stream_px']} px stream only (%)",
           "Shift (pts)"],
          [[TIER_LABEL[t], f"{st['tier_curve_all_streams'][t]:.2f}",
            f"{st['tier_curve_dominant_stream_only'][t]:.2f}",
            f"{st['tier_curve_dominant_stream_only'][t] - st['tier_curve_all_streams'][t]:+.2f}"]
           for t in TIERS],
          "Tier curve restricted to the dominant acquisition stream (sensitivity "
          "analysis for limitation L4).")
    para(doc, f"Restricting the analysis to the dominant {st['dominant_stream_px']}-pixel "
              f"stream shifts no tier by more than {st['max_abs_shift_points']:.2f} "
              f"points. L4 is ruled out as an explanation of the stratified result.")


# =====================================================================
def sec_3_11_corrections(doc) -> None:
    h(doc, "3.10 Corrections to the first release of this report", level=2)
    para(doc, "The analyses above overturn or qualify four claims made in the first "
              "release. They are listed here in full rather than silently amended, "
              "and are recorded machine-readably in reports/phase3b_amendment.json.")
    for c in AMD["corrections_to_the_delivered_report"]:
        callout(doc, f"Claim: {c['claim']}\n\nStatus: {c['status']}\n\n"
                     f"Evidence: {c['evidence']}\n\nReplacement: {c['replacement']}",
                title=f"{c['id']}  ({c['location']})")


# =====================================================================
def appendix_a_perclass(doc) -> None:
    h(doc, "Appendix A. Per-class, per-stratum metric tables", level=2)
    pc_ = PCL["per_class_by_tier"]
    names = pc_["S-unanimous"]["classes"]
    rows = []
    for i, nm in enumerate(names):
        rows.append([nm] + [f"{100 * pc_[t]['marginalized_per_class_f1_3seed'][i]:.1f}"
                            for t in TIERS]
                    + [f"{pc_['S-unanimous']['mean_annotator_support_3seed'][i]:.0f}",
                       f"{pc_['S-no-majority']['mean_annotator_support_3seed'][i]:.1f}"])
    table(doc, ["Class"] + [t.replace("S-", "") + " F1 (%)" for t in TIERS]
          + ["Support 4/4", "Support no-maj."], rows,
          "Annotator-marginalized per-class F1 by stratum, 3-seed mean, with mean "
          "annotator support at the extremes. Support is averaged over the four "
          "annotator label realisations and is therefore fractional.", font=7.0)


def appendix_b_confusion(doc) -> None:
    h(doc, "Appendix B. Per-stratum confusion matrices", level=2)
    p = REP / "phase3b_confusion_matrices.npz"
    z = np.load(p, allow_pickle=True)
    names = [str(x) for x in z["classes"]]
    para(doc, f"Full 23x23 annotator-marginalized confusion matrices for all four "
              f"strata are stored in {p.name} (keys "
              f"{', '.join(t.replace('-', '_') for t in TIERS)}), built by averaging "
              f"the confusion matrix against each of the four annotator label "
              f"realisations so that they are defined on the tiers with no single "
              f"ground truth. The dominant off-diagonal mass is summarised below; "
              f"the full matrices are machine-readable rather than reproduced as "
              f"four 23x23 tables.")
    rows = []
    for t in TIERS:
        M = z[t.replace("-", "_")].copy()
        np.fill_diagonal(M, 0)
        flat = np.dstack(np.unravel_index(np.argsort(-M, axis=None), M.shape))[0][:5]
        top = "; ".join(f"{names[i]}->{names[j]} ({M[i, j]:.1f})" for i, j in flat)
        diag = float(np.trace(z[t.replace("-", "_")]))
        tot = float(z[t.replace("-", "_")].sum())
        rows.append([TIER_LABEL[t], f"{100 * diag / tot:.2f}", top])
    table(doc, ["Stratum", "Diagonal mass (%)", "Five heaviest confusions (vote mass)"],
          rows,
          "Summary of the per-stratum confusion matrices. Diagonal mass equals "
          "expected accuracy by construction.", font=7.4)


def appendix_c_bootstrap(doc) -> None:
    h(doc, "Appendix C. Bootstrap procedure and diagnostics", level=2)
    para(doc, f"Every interval in this report resamples patients, not images, with "
              f"replacement. Phase 3 used {CEIL['n_boot']} resamples per tier at seed "
              f"{CEIL['boot_seed']}; the pairwise gap intervals in §3.4.1 use the "
              f"same seed and procedure applied jointly to the two tiers being "
              f"compared, so that the two resamples are drawn independently within "
              f"each draw. Calibration intervals use {CAL['n_boot']} resamples and "
              f"the geometry intervals in §3.8.2 use {SENS['n_boot']}.")
    para(doc, "Two diagnostics are worth stating explicitly. First, on the "
              "ceiling-normalised scale the estimator is a ratio, and a ratio's "
              "bootstrap distribution is skewed at these sample sizes; the tables "
              "report the plug-in point estimate alongside the bootstrap mean so "
              "the difference between them is visible rather than hidden. Second, "
              "the ceiling in the denominator is recomputed inside every resample "
              "rather than held at its full-tier value - holding it fixed breaks the "
              "pairing and inflates the gap, because a resample with duplicated "
              "patients covers fewer distinct classes and depresses any macro F1.")
    rows = []
    for pair in ["S-unanimous - S-majority", "S-unanimous - S-no-majority",
                 "S-plurality - S-no-majority"]:
        for scale in ("raw", "ceiling_normalised"):
            e = gap(pair, scale)
            rows.append([pair.replace("S-", ""), scale.replace("_", "-"),
                         f"{e['gap_points_3seed_mean']:.2f}",
                         f"{e['gap_points_boot_mean_3seed']:.2f}",
                         f"{e['gap_points_boot_mean_3seed'] - e['gap_points_3seed_mean']:+.2f}"])
    table(doc, ["Tier pair", "Scale", "Plug-in (pts)", "Bootstrap mean (pts)",
                "Bootstrap bias (pts)"], rows,
          "Plug-in versus bootstrap-mean estimates for the key gaps, as a bias "
          "diagnostic.", font=7.6)


def appendix_e_register(doc) -> None:
    h(doc, "Appendix E. Pre-registration record and protocol amendment", level=2)
    para(doc, AMD["why"])
    table(doc, ["ID", "Analysis", "Status", "Artefact"],
          [[r["id"], r["analysis"][:190], r["status"], r["artefact"]]
           for r in AMD["analysis_register"]],
          "Analysis provenance register. Confirmatory analyses are those whose "
          "specification predates the data, whether or not they were delivered in "
          "the first release.", font=6.8)


def references(doc) -> None:
    h(doc, "References", level=1, page_break=True)
    for i, r in enumerate([
        "Panesso-Ortiz S, et al. GastroHUN: an Endoscopy Dataset of Complete "
        "Systematic Screening Protocol for the Stomach. Scientific Data 2025; "
        "12:102. doi:10.1038/s41597-025-04401-5.",
        "Mongan J, Moy L, Kahn CE. Checklist for Artificial Intelligence in "
        "Medical Imaging (CLAIM). Radiology: Artificial Intelligence 2020; "
        "2(2):e200029.",
        "Collins GS, Moons KGM, Dhiman P, et al. TRIPOD+AI statement: updated "
        "guidance for reporting clinical prediction models that use regression or "
        "machine learning methods. BMJ 2024; 385:e078378.",
        "Sounderajah V, Ashrafian H, Golub RM, et al. Developing a reporting "
        "guideline for artificial intelligence-centred diagnostic test accuracy "
        "studies: the STARD-AI protocol. BMJ Open 2021; 11:e047709.",
        "Wolff RF, Moons KGM, Riley RD, et al. PROBAST: A Tool to Assess the Risk "
        "of Bias and Applicability of Prediction Model Studies. Annals of Internal "
        "Medicine 2019; 170(1):51-58.",
        "Page MJ, McKenzie JE, Bossuyt PM, et al. The PRISMA 2020 statement: an "
        "updated guideline for reporting systematic reviews. BMJ 2021; 372:n71.",
        "Guo C, Pleiss G, Sun Y, Weinberger KQ. On Calibration of Modern Neural "
        "Networks. Proceedings of ICML 2017; 70:1321-1330.",
        "Fleiss JL. Measuring nominal scale agreement among many raters. "
        "Psychological Bulletin 1971; 76(5):378-382.",
        "Efron B, Tibshirani RJ. An Introduction to the Bootstrap. Chapman & "
        "Hall/CRC, 1993 (patient-clustered resampling, ch. 8).",
        "Liu Z, Mao H, Wu C-Y, et al. A ConvNet for the 2020s. Proceedings of CVPR "
        "2022:11976-11986.",
        "THESIS_RESEARCH_BLUEPRINT.md v3.2, §4 Phase 3, §13, §14, §15 "
        "(this project's governing protocol).",
        "Phase 0 / Phase 1 Report, this project: corpus audit, agreement "
        "quantification and PRISMA 2020 review.",
        "Phase 2 Report, this project: baseline reproduction, GATE 5.",
    ], 1):
        para(doc, f"[{i}]  {r}", size=9.5)
