"""
Phase 0 narrative, part 2: agreement, disagreement structure, split integrity,
power, population, and the gate verdict.
"""

from __future__ import annotations

from build_docx import callout, figure, h, para, table
from content_phase0_v2 import (AGR, CA_PCT, DEC, GRAN, INV, N_CLS, N_IMG,
                               N_PAT, OLD, STR)


def sec_agreement(doc) -> None:
    h(doc, "G4–G5: Label architecture and inter-annotator agreement", 2)

    para(doc,
         f"The property that distinguishes GastroHUN from every other public "
         f"upper-gastrointestinal dataset is that it does not collapse its "
         f"annotators. Four experts labelled all {N_IMG:,} images independently "
         f"under a quadruple-blind protocol, and all four label columns are "
         f"published. Two annotators were final-year gastroenterology residents "
         f"(Team A, denoted FG1 and FG2, each with roughly 500 documented "
         f"procedures); two were gastroenterologists (Team B, denoted G1 and "
         f"G2, each with at least 1,000 procedures). This makes disagreement a "
         f"measurable quantity rather than a hidden one, and it is the raw "
         f"material for everything the thesis proposes.")

    para(doc,
         "Agreement was quantified with three chance-corrected statistics "
         "rather than one, because each fails in a different way. Fleiss' kappa "
         "is the standard multi-rater coefficient but behaves badly when "
         "category prevalence is skewed. Krippendorff's alpha handles arbitrary "
         "rater counts and missing data. Gwet's AC1 was designed specifically to "
         "remain stable under the prevalence conditions that distort kappa.")

    agr_rows = [
        ["Fleiss' κ", f"{AGR['fleiss_kappa']:.4f}", "Multi-rater, all four annotators"],
        ["Krippendorff's α (nominal)", f"{AGR['krippendorff_alpha']:.4f}",
         "Multi-rater, coincidence-matrix formulation"],
        ["Gwet's AC1", f"{AGR['gwet_ac1']:.4f}", "Prevalence-robust chance correction"],
        ["Mean pairwise Cohen's κ", f"{GRAN['full']['mean_pairwise_kappa']:.4f}",
         "Mean over all six annotator pairs"],
        ["Mean within-team κ", f"{AGR['kappa_within_team_mean']:.4f}",
         "FG1–FG2 and G1–G2 only"],
        ["Mean between-team κ", f"{AGR['kappa_between_team_mean']:.4f}",
         "The four resident–gastroenterologist pairs"],
        ["Raw (uncorrected) agreement", f"{GRAN['full']['mean_raw_agreement']:.4f}",
         "Proportion of rater pairs assigning an identical label"],
    ]
    table(doc, ["Statistic", "Value", "Definition applied"], agr_rows,
          f"Inter-annotator agreement across {N_CLS} categories and "
          f"{N_IMG:,} images.",
          widths=[5.4, 3.0, 8.4], font=8.0)

    para(doc,
         f"The three chance-corrected coefficients agree to three decimal "
         f"places ({AGR['fleiss_kappa']:.4f}, {AGR['krippendorff_alpha']:.4f} "
         f"and {AGR['gwet_ac1']:.4f}). This is not a coincidence, and it is "
         f"worth explaining, because a reader who knows these statistics "
         f"normally diverge will otherwise suspect an implementation error. "
         f"Fleiss' expected agreement is Σpⱼ², whereas Gwet's is "
         f"(1 − Σpⱼ²)/(K − 1). Those two quantities are algebraically equal "
         f"exactly when the marginal distribution is uniform, that is when "
         f"Σpⱼ² = 1/K. The SSS protocol prescribes a fixed photographic set per "
         f"patient, so the marginal class distribution is near-uniform by "
         f"construction and the two chance corrections converge. The practical "
         f"consequence is favourable: the well-known kappa paradox, in which "
         f"high observed agreement yields a low kappa under skewed prevalence, "
         f"does not arise here, and the reported kappa can be read at face "
         f"value.")

    figure(doc, "F05_kappa_matrix.png",
           "Pairwise Cohen's κ between the four annotators. Left: the full "
           "matrix. Right: the same six values ranked with patient-clustered "
           "bootstrap 95% confidence intervals; within-team pairs in red. "
           "Intervals resample patients rather than images, because images from "
           "one patient are not independent observations.")

    pw = AGR["pairwise_cohen_kappa"]
    pw_rows = []
    for k, v in sorted(pw.items(), key=lambda kv: -kv[1]["kappa"]):
        pw_rows.append([
            k.replace("-", " – "),
            "within team" if k in ("FG1-FG2", "G1-G2") else "between teams",
            f"{v['kappa']:.4f}",
            f"[{v['ci95'][0]:.4f}, {v['ci95'][1]:.4f}]",
            f"{v['raw_agreement']:.4f}",
        ])
    table(doc, ["Annotator pair", "Relationship", "Cohen's κ",
                "95% CI (patient bootstrap)", "Raw agreement"], pw_rows,
          "All six pairwise agreement coefficients, ranked.",
          widths=[3.4, 3.2, 2.4, 4.6, 3.2], font=8.0,
          note="Intervals from 400 patient-clustered bootstrap resamples; all "
               "images belonging to a resampled patient move together.")

    callout(doc,
            f"The two gastroenterologists are the most concordant pair "
            f"(G1–G2, κ = {pw['G1-G2']['kappa']:.4f}); the two residents are "
            f"the least concordant pair (FG1–FG2, κ = "
            f"{pw['FG1-FG2']['kappa']:.4f}). Crucially, each resident agrees "
            f"more with the gastroenterologists than with the other resident: "
            f"FG1 agrees with G1 at κ = {pw['FG1-G1']['kappa']:.4f} but with "
            f"its own teammate at only {pw['FG1-FG2']['kappa']:.4f}. Seniority "
            f"is therefore not the dominant axis of disagreement; individual "
            f"annotator idiosyncrasy is. Any design that treats 'Team A' as a "
            f"coherent unit assumes something the data does not support.",
            title="Team structure does not predict agreement")

    tvd = AGR["prevalence_total_variation_distance"]
    para(doc,
         f"The marginal label distributions point the same way. Total variation "
         f"distance between annotators' overall class prevalence vectors is "
         f"largest for the within-team pair FG1–FG2 ({tvd['FG1-FG2']:.4f}) and "
         f"smallest for the between-team pair FG1–G1 ({tvd['FG1-G1']:.4f}). "
         f"FG2 is the outlying annotator on every measure computed here.")

    h(doc, "The agreement cascade and what the benchmark discards", 3)

    t, tp = AGR["agreement_tiers"], AGR["agreement_tiers_pct"]
    tier_rows = [
        ["All labelled images", f"{t['all_images']:,}", "100.00%", "Complete corpus"],
        ["Triple agreement (≥3 of 4)", f"{t['triple_agreement_3of4']:,}",
         f"{tp['triple_agreement_3of4']:.2f}%", "At least three annotators concur"],
        ["Team B agreement (G1 = G2)", f"{t['G_team_agreement']:,}",
         f"{tp['G_team_agreement']:.2f}%", "Both gastroenterologists concur"],
        ["Team A agreement (FG1 = FG2)", f"{t['FG_team_agreement']:,}",
         f"{tp['FG_team_agreement']:.2f}%", "Both residents concur"],
        ["Complete agreement (4 of 4)", f"{t['complete_agreement_4of4']:,}",
         f"{tp['complete_agreement_4of4']:.2f}%",
         "Unanimous — the published benchmark's training and test set"],
    ]
    table(doc, ["Consensus tier", "Images", "% of corpus", "Definition"], tier_rows,
          "The agreement cascade. Each tier is a different but defensible "
          "definition of ground truth, and they differ by thousands of images.",
          widths=[5.0, 2.4, 2.6, 6.8], font=8.0)

    figure(doc, "F06_agreement_cascade.png",
           "Left: the agreement-tier cascade, with the unanimous subset used by "
           "the published benchmark marked. Right: the distribution of voting "
           "patterns across the four annotators.")

    vp, vpp = AGR["vote_patterns"], AGR["vote_patterns_pct"]
    vp_rows = [
        ["4–0", "All four agree", f"{vp.get('4', 0):,}", f"{vpp.get('4', 0):.2f}%", "Unambiguous"],
        ["3–1", "One dissenter", f"{vp.get('3-1', 0):,}", f"{vpp.get('3-1', 0):.2f}%", "Clear majority"],
        ["2–1–1", "Two agree, two differ", f"{vp.get('2-1-1', 0):,}",
         f"{vpp.get('2-1-1', 0):.2f}%", "Plurality only"],
        ["2–2", "Two-way tie", f"{vp.get('2-2', 0):,}", f"{vpp.get('2-2', 0):.2f}%",
         "No majority exists"],
        ["1–1–1–1", "All four differ", f"{vp.get('1-1-1-1', 0):,}",
         f"{vpp.get('1-1-1-1', 0):.2f}%", "No majority exists"],
    ]
    table(doc, ["Pattern", "Meaning", "Images", "% of corpus", "Resolvable by voting?"],
          vp_rows, "Voting patterns across the four independent expert labels.",
          widths=[2.2, 4.4, 2.4, 2.6, 5.2], font=8.0,
          note=f"{AGR['n_no_majority']:,} images ({AGR['pct_no_majority']:.2f}%) "
               f"admit no majority label under any voting rule.")

    para(doc,
         f"The consequence for the published benchmark is direct. Restricting "
         f"training and evaluation to the unanimous subset discards "
         f"{t['all_images'] - t['complete_agreement_4of4']:,} images — "
         f"{100 - tp['complete_agreement_4of4']:.1f}% of the corpus. That is a "
         f"defensible choice for a clean baseline, and the descriptor's authors "
         f"state the limitation themselves, noting that the approach 'misses a "
         f"much more variable real-world scenario'. But it means the headline "
         f"macro F1 of 88.25 characterises performance on the easiest "
         f"three-fifths of the data, and nothing is known about the rest.")

    figure(doc, "F12_class_attrition.png",
           "Proportion of each class's annotator nominations discarded by the "
           "complete-agreement filter. Attrition is markedly non-uniform.")

    att = AGR["class_attrition_under_consensus"]
    worst = sorted(att.items(), key=lambda kv: -(kv[1]["attrition_pct"] or 0))[:8]
    table(doc, ["Class", "Nominated by ≥1 annotator", "Retained at 4/4",
                "Attrition"],
          [[c, f"{v['nominated_by_any_rater']:,}",
            f"{v['kept_under_complete_agreement']:,}",
            f"{v['attrition_pct']:.1f}%"] for c, v in worst],
          "The eight classes most heavily depleted by the complete-agreement "
          "filter.",
          widths=[2.6, 4.8, 4.4, 3.2], font=8.0,
          note="Attrition is measured against the number of images any "
               "annotator assigned to the class, since no consensus label "
               "exists for the discarded images.")

    figure(doc, "F04_class_distribution.png",
           "Per-annotator class distributions overlaid on the complete-"
           "agreement subset. The gap between the lines and the bars is exactly "
           "the material the consensus filter removes.")


def sec_structure(doc) -> None:
    h(doc, "The structure of disagreement", 2)

    para(doc,
         "Aggregate agreement statistics report how often experts disagree. "
         "They do not report what experts disagree about. Because every SSS "
         "code decomposes into a wall and a station, that question can be "
         "answered directly, and the answer is the most substantive original "
         "finding of this audit. It is not reported in the dataset descriptor.")

    para(doc,
         f"Each of the {STR['n_disagreement_pair_events']:,} annotator-pair "
         f"disagreement events was classified into one of four categories: the "
         f"pair agreed on the station but differed on the wall; agreed on the "
         f"wall but differed on the station; differed on both; or one annotator "
         f"rejected the image as unusable while the other assigned a landmark.")

    d = STR["disagreement_decomposition"]
    table(doc, ["Disagreement type", "Events", "% of total", "Interpretation"],
          [["Same station, different wall", f"{d['same_station_different_wall']:,}",
            f"{DEC['same_station_different_wall']:.2f}%",
            "Rotational ambiguity about the gastric axis"],
           ["Landmark vs OTHERCLASS", f"{d['landmark_vs_OTHERCLASS']:,}",
            f"{DEC['landmark_vs_OTHERCLASS']:.2f}%",
            "Disagreement about usability, not anatomy"],
           ["Same wall, different station", f"{d['same_wall_different_station']:,}",
            f"{DEC['same_wall_different_station']:.2f}%",
            "Depth ambiguity along the gastric axis"],
           ["Both differ", f"{d['different_wall_and_station']:,}",
            f"{DEC['different_wall_and_station']:.2f}%", "Unstructured disagreement"]],
          "Decomposition of every annotator-pair disagreement event by "
          "anatomical axis.",
          widths=[5.0, 2.4, 2.4, 7.0], font=8.0)

    figure(doc, "F07_disagreement_decomposition.png",
           "Left: disagreement decomposed by anatomical axis. Centre: agreement "
           "recomputed at three label granularities. Right: which walls are "
           "confused with which, with circumferentially adjacent pairs "
           "highlighted.")

    para(doc,
         f"Over half of all disagreement — "
         f"{DEC['same_station_different_wall']:.1f}% — consists of two experts "
         f"who agree on how far the endoscope has been withdrawn but differ on "
         f"which wall it faces. Only {DEC['same_wall_different_station']:.1f}% "
         f"is the converse. A confirmatory test makes the asymmetry "
         f"unmistakable. Collapsing the {N_CLS}-class space to station alone "
         f"raises mean pairwise kappa from "
         f"{GRAN['full']['mean_pairwise_kappa']:.4f} to "
         f"{GRAN['station']['mean_pairwise_kappa']:.4f}, and unanimity from "
         f"{STR['unanimity_rate_pct_by_granularity']['full']:.2f}% to "
         f"{STR['unanimity_rate_pct_by_granularity']['station']:.2f}%. "
         f"Collapsing to wall alone moves kappa to "
         f"{GRAN['wall']['mean_pairwise_kappa']:.4f} — indistinguishable from "
         f"the full label space. Removing the wall distinction removes almost "
         f"all the difficulty; removing the station distinction removes almost "
         f"none of it.")

    wp = STR["wall_confusion_pairs"]
    adjacent = {"A-G", "A-L", "L-P", "G-P"}
    n_adj = sum(v for k, v in wp.items() if k in adjacent)
    n_opp = sum(v for k, v in wp.items() if k not in adjacent)
    table(doc, ["Wall pair", "Circumferential relation", "Events",
                "% of wall confusions"],
          [[k.replace("-", " ↔ "), "adjacent" if k in adjacent else "opposite",
            f"{v:,}", f"{100*v/(n_adj+n_opp):.2f}%"] for k, v in wp.items()],
          "Which walls are confused with which. The protocol photographs the "
          "walls in clockwise order — greater curvature, anterior, lesser "
          "curvature, posterior — so 'adjacent' means adjacent on that circle.",
          widths=[3.2, 4.4, 2.8, 4.0], font=8.0,
          note=f"Circumferentially adjacent pairs account for "
               f"{100*n_adj/(n_adj+n_opp):.1f}% of wall confusions; "
               f"diametrically opposite pairs for {100*n_opp/(n_adj+n_opp):.1f}%.")

    gap = STR["station_gap_distribution"]
    adj_station = 100 * gap.get("1", 0) / sum(gap.values())
    callout(doc,
            f"Disagreement follows the geometry of the stomach. "
            f"{100*n_adj/(n_adj+n_opp):.1f}% of wall confusions involve walls "
            f"adjacent on the circumference, and {adj_station:.1f}% of station "
            f"confusions involve neighbouring stations. Expert disagreement is "
            f"locally structured rather than arbitrary: annotators are not "
            f"guessing, they are resolving a genuinely continuous viewing "
            f"geometry onto a discrete label set. This is the empirical "
            f"justification for treating the label space as structured — a "
            f"distance-aware or hierarchical loss is warranted by the data, not "
            f"merely by intuition.",
            title="Disagreement is anatomically structured")

    figure(doc, "F08_station_difficulty.png",
           "Left: rater-pair disagreement rate by anatomical station. Right: "
           "the station confusion matrix, with confusion confined almost "
           "entirely to the adjacent-station band.")

    sd = STR["station_difficulty"]
    hardest = max(range(1, 7), key=lambda s: sd[f"station_{s}"]["disagreement_rate_pct"])
    easiest = min(range(1, 7), key=lambda s: sd[f"station_{s}"]["disagreement_rate_pct"])
    para(doc,
         f"Station-level difficulty varies more than twofold. The hardest is "
         f"station {hardest} ({sd[f'station_{hardest}']['name']}) at "
         f"{sd[f'station_{hardest}']['disagreement_rate_pct']:.1f}%; the "
         f"easiest is station {easiest} ({sd[f'station_{easiest}']['name']}) at "
         f"{sd[f'station_{easiest}']['disagreement_rate_pct']:.1f}%. This "
         f"aligns with the published baseline's own error profile: the "
         f"descriptor reports reduced model accuracy 'in the middle body (L3, "
         f"P3, and G3)' — station 3, among the hardest stations for the human "
         f"annotators measured here. Model error and human disagreement "
         f"concentrate in the same anatomy, which is itself evidence that the "
         f"residual error reflects genuine visual ambiguity rather than "
         f"insufficient model capacity.")

    h(doc, "OTHERCLASS: a quality judgement, not an anatomical one", 3)

    oc = STR["otherclass"]
    rates = oc["per_rater_OTHERCLASS_rate_pct"]
    para(doc,
         f"The twenty-third category marks an image as unsuitable for "
         f"assessment. It behaves quite differently from the anatomical classes "
         f"and accounts for {DEC['landmark_vs_OTHERCLASS']:.1f}% of all "
         f"disagreement, making it the second-largest single source.")

    oc_rows = [[f"Rate for annotator {k}", f"{v:.2f}%"] for k, v in rates.items()]
    oc_rows += [
        ["Images ever called OTHERCLASS",
         f"{oc['n_images_any_rater_called_OTHERCLASS']:,}"],
        ["Of which unanimous",
         f"{oc['n_images_unanimous_OTHERCLASS']:,} "
         f"({oc['pct_of_OTHERCLASS_nominations_that_are_unanimous']:.2f}%)"],
    ]
    table(doc, ["Measure", "Value"], oc_rows,
          "The OTHERCLASS quality judgement, by annotator.",
          widths=[8.4, 4.0], font=8.0)

    figure(doc, "F09_otherclass.png",
           "Left: per-annotator rate of rejecting an image as unusable. Right: "
           "of all images any annotator rejected, the fraction rejected "
           "unanimously.")

    para(doc,
         f"The spread is a factor of {max(rates.values())/min(rates.values()):.1f} "
         f"between the most and least permissive annotator, and only "
         f"{oc['pct_of_OTHERCLASS_nominations_that_are_unanimous']:.1f}% of "
         f"rejections are unanimous. On this evidence, 'is this image good "
         f"enough?' is a substantially subjective judgement. That has a concrete "
         f"implication for the automated-audit application motivating the "
         f"dataset: a system certifying an examination as complete makes the "
         f"same judgement, and cannot be more objective than the labels it was "
         f"trained on. Quality assessment and anatomical classification are "
         f"different tasks and should be modelled and evaluated separately.")


def sec_splits_power(doc) -> None:
    h(doc, "G6: Integrity of the official splits", 2)

    para(doc,
         "The descriptor supplies official train/validation/test splits "
         "stratified by patient, allocating cases to quartiles of per-patient "
         "Fleiss kappa so that agreement level is balanced across partitions. "
         "Both properties were verified independently rather than assumed.")

    ss = AGR["split_summary"]
    table(doc, ["Split", "Images", "% images", "Patients", "% patients",
                "4/4 subset", "% 4/4", "Img/patient"],
          [[s, f"{ss[s]['n_images']:,}", f"{ss[s]['pct_images']:.2f}%",
            f"{ss[s]['n_patients']}", f"{ss[s]['pct_patients']:.2f}%",
            f"{ss[s]['n_complete_agreement']:,}",
            f"{ss[s]['pct_complete_agreement']:.2f}%",
            f"{ss[s]['images_per_patient_mean']:.2f}"]
           for s in ("Train", "Validation", "Test")],
          "Composition of the official splits.",
          widths=[2.2, 2.0, 1.9, 1.9, 1.9, 2.0, 1.7, 2.0], font=7.8)

    ov = AGR["split_patient_overlaps"]
    overlap_txt = "; ".join(f"{k.replace('-', ' ∩ ')} = {len(v)}" for k, v in ov.items())
    para(doc,
         f"Patient-level disjointness holds exactly ({overlap_txt}). No patient "
         f"contributes images to more than one split, and there are "
         f"{AGR['n_duplicate_filenames']} duplicate filenames anywhere in the "
         f"manifest. This is the correct unit of independence: splitting at "
         f"image level would place different photographs of the same stomach on "
         f"both sides of the boundary and inflate every performance estimate.")

    para(doc,
         f"Balance was tested rather than asserted. Class prevalence across the "
         f"three splits gives χ² = {AGR['split_class_chi2']['chi2']:.2f} on "
         f"{AGR['split_class_chi2']['dof']} degrees of freedom "
         f"(p = {AGR['split_class_chi2']['p']:.4f}, Cramér's V = "
         f"{AGR['split_class_chi2']['cramers_v']:.4f}); prevalence of complete "
         f"agreement gives χ² = {AGR['split_agreement_chi2']['chi2']:.2f} "
         f"(p = {AGR['split_agreement_chi2']['p']:.4f}); per-patient Fleiss "
         f"kappa across splits gives Kruskal–Wallis H = "
         f"{STR['per_patient_agreement']['kruskal_h']:.3f} "
         f"(p = {STR['per_patient_agreement']['kruskal_p']:.4f}). All three are "
         f"comfortably non-significant, which here is the desired result: the "
         f"stratification the descriptor claims did in fact work.")

    figure(doc, "F11_split_integrity.png",
           "Official split integrity. Left: image and patient shares against "
           "the intended 70/15/15 allocation. Centre: prevalence of complete "
           "agreement by split. Right: verification of patient-level "
           "disjointness and distributional balance.")

    pa = STR["per_patient_agreement"]
    para(doc,
         f"Per-patient agreement is itself informative. Computing Fleiss kappa "
         f"within each of the {pa['n_patients_scored']} patients gives a mean of "
         f"{pa['mean']:.4f} (SD {pa['sd']:.4f}) across a range from "
         f"{pa['min']:.4f} to {pa['max']:.4f}. "
         f"{pa['n_above_0.8_almost_perfect']} patients "
         f"({100*pa['n_above_0.8_almost_perfect']/pa['n_patients_scored']:.1f}%) "
         f"reach almost-perfect agreement while {pa['n_below_0.4_poor']} fall "
         f"below 0.40. Difficulty is therefore partly a property of the patient "
         f"— of how a particular stomach photographed on the day — and not only "
         f"of the individual image. Any resampling procedure must respect this "
         f"by resampling patients, which is why every interval in this report "
         f"is patient-clustered.")

    figure(doc, "F10_patient_agreement.png",
           "Left: distribution of per-patient Fleiss κ against conventional "
           "interpretive bands. Right: mean per-patient κ by official split, "
           "confirming the agreement-stratified allocation.")

    h(doc, "G7: Statistical power of the evaluation set", 2)

    para(doc,
         f"The consensus test set contains "
         f"{ss['Test']['n_complete_agreement']:,} images across {N_CLS} "
         f"classes. Per-class precision was estimated as the half-width of a "
         f"95% Wilson score interval at an assumed per-class accuracy of 0.85, "
         f"approximately the level the published baselines attain.")

    pw = AGR["test_set_power"]
    smallest = sorted(pw.items(), key=lambda kv: kv[1]["n_test"])[:6]
    table(doc, ["Class", "Test images (4/4)", "95% Wilson half-width at p = 0.85"],
          [[c, f"{v['n_test']}", f"±{100*v['wilson_half_width_at_p85']:.1f} pp"]
           for c, v in smallest],
          "The six most sparsely represented classes in the consensus test set.",
          widths=[3.0, 4.4, 6.4], font=8.0)

    figure(doc, "F13_test_power.png",
           "Per-class precision of the consensus test set. The dashed line "
           "marks a ±10 percentage-point half-width; classes above it cannot "
           "support confident per-class claims.")

    callout(doc,
            f"{AGR['n_test_classes_underpowered_hw_gt_10pct']} of {N_CLS} "
            f"classes have a 95% interval half-width wider than ±10 percentage "
            f"points. The consensus test set is adequately powered for "
            f"aggregate macro-averaged comparison but not for confident "
            f"per-class claims. The thesis will therefore report macro-averaged "
            f"metrics as primary endpoints, treat per-class figures as "
            f"exploratory, and attach patient-clustered bootstrap intervals "
            f"throughout.",
            title="G7 verdict — CONDITIONAL")

    h(doc, "G8: Population description", 2)

    cm = AGR["clinical_metadata"]
    para(doc,
         f"Patient-level clinical context exists for "
         f"{cm['n_patients_with_videoendoscopy_record']} of the "
         f"{cm['n_patients_with_images']} imaged patients "
         f"({cm['pct_image_patients_with_clinical_record']:.1f}%), carried in "
         f"the videoendoscopy metadata. Within that subset "
         f"{cm['h_pylori_reported']} records report Helicobacter pylori status "
         f"({cm['h_pylori_positive']} positive) and {cm['olga_reported']} carry "
         f"an OLGA atrophic-gastritis stage.")

    table(doc, ["Population attribute", "Value"],
          [["Patients contributing images", f"{cm['n_patients_with_images']}"],
           ["Patients with a clinical record",
            f"{cm['n_patients_with_videoendoscopy_record']} "
            f"({cm['pct_image_patients_with_clinical_record']:.1f}%)"],
           ["H. pylori reported / missing",
            f"{cm['h_pylori_reported']} / {cm['h_pylori_missing']}"],
           ["H. pylori positive", f"{cm['h_pylori_positive']}"],
           ["OLGA stage reported / missing",
            f"{cm['olga_reported']} / {cm['olga_missing']}"],
           ["Distinct free-text findings narratives",
            f"{cm['n_unique_free_text_findings']}"],
           ["Distinct diagnosis strings", f"{cm['n_unique_diagnoses_strings']}"],
           ["Age recorded", "No"],
           ["Sex recorded", "No"]],
          "Availability of patient-level clinical and demographic context.",
          widths=[8.0, 5.4], font=8.0)

    callout(doc,
            "Neither age nor sex is recorded anywhere in the release. This "
            "follows from the anonymisation strategy but has two firm "
            "consequences that must be declared. First, no demographic subgroup "
            "or fairness analysis is possible on this corpus, and the thesis "
            "will not claim one. Second, CLAIM and TRIPOD+AI both require a "
            "description of the study population; that item can be satisfied "
            "only at the level of the recruiting institution and its stated "
            "referral pathway, and the thesis will say so explicitly rather "
            "than leave the item silently unmet.",
            title="G8 verdict — CONDITIONAL")

    para(doc,
         f"One incidental observation is recorded for future work. The "
         f"videoendoscopy metadata contains {cm['n_unique_free_text_findings']} "
         f"distinct free-text endoscopic findings narratives in English, "
         f"structured by organ. During the dataset search preceding this work, "
         f"an extensive effort failed to locate any public de-identified "
         f"free-text endoscopy report corpus, and that absence is what pushed "
         f"the project from a natural-language framing toward imaging. This is "
         f"such a corpus, albeit a very small one. At "
         f"{cm['n_patients_with_videoendoscopy_record']} patients it cannot "
         f"support the original research question and it is not pursued here, "
         f"but it is a genuine secondary resource and is noted as such.")


def sec_gate_verdict(doc) -> None:
    h(doc, "Gate verdict and validation of the audit protocol", 2)

    figure(doc, "F02_integrity_gate.png",
           "The Phase 0 integrity gate applied to GastroHUN, with the verdict "
           "and supporting evidence for each of the eight criteria.")

    para(doc,
         "The gate returns PROCEED. The corpus is physically intact, correctly "
         "partitioned, honestly documented and — critically for the research "
         "question — retains the per-annotator label structure the thesis "
         "depends on. Two criteria return CONDITIONAL. Neither blocks the "
         "research; both constrain its claims and are carried into the "
         "limitations rather than resolved.")

    cm = AGR["clinical_metadata"]
    table(doc, ["ID", "Limitation", "Evidence", "Mitigation carried forward"],
          [["L1", "Per-class test precision",
            f"{AGR['n_test_classes_underpowered_hw_gt_10pct']}/{N_CLS} classes exceed "
            "a ±10 pp half-width on the consensus test set",
            "Macro-averaged metrics as primary; per-class exploratory; "
            "patient-clustered bootstrap intervals throughout"],
           ["L2", "No demographic data",
            "Age and sex absent from the entire release",
            "No demographic subgroup or fairness claim; population described "
            "at institutional level only"],
           ["L3", "Single centre, single vendor",
            "One hospital; Olympus EVIS EXERA III throughout",
            "External validation on HyperKvasir and GastroVision shared "
            "landmarks treated as a required phase, not an extension"],
           ["L4", "Acquisition stream imbalance across splits",
            f"Video-derived frames unevenly allocated "
            f"(χ² p = {STR['provenance']['source_type_split_p']:.1e})",
            "Report per-split source composition; test sensitivity of "
            "conclusions to excluding video-derived frames"],
           ["L5", "Review restricted to one database",
            "Phase 1 searched PubMed/MEDLINE only",
            "Foundational computer-science works added via the PRISMA "
            "other-methods arm; declared as a review limitation"],
           ["L6", "Clinical context incomplete",
            f"{cm['pct_image_patients_with_clinical_record']:.1f}% of imaged "
            "patients have a clinical record; H. pylori and OLGA missing for "
            "a substantial minority",
            "No claim linking landmark performance to disease status"]],
          "Declared limitations arising from Phase 0, with the mitigation "
          "adopted for each.",
          widths=[1.0, 3.4, 5.6, 6.8], font=7.6)

    h(doc, "The audit protocol validated against a negative control", 3)

    para(doc,
         "An audit that passes everything shown to it is not an audit. The "
         "protocol applied here was first applied to the corpus this project "
         "previously used, and it failed that corpus on the criteria that "
         "matter. That contrast is the evidence that the gate discriminates.")

    figure(doc, "F16_negative_control.png",
           "The same Phase 0 criteria applied to the retired corpus and to "
           "GastroHUN. The protocol separates the two cleanly, including on the "
           "two criteria GastroHUN itself does not meet.")

    if OLD:
        pt = OLD.get("permutation_test", {})
        para(doc,
             f"The retired corpus failed on provenance (no verifiable source, "
             f"no ethics statement), on label construction (the target was "
             f"derived by regular expressions from the very fields that became "
             f"the features), and on signal: a permutation test returned "
             f"p = {pt.get('p_value', float('nan')):.4f}, so the observed "
             f"feature–target association was indistinguishable from chance. "
             f"GastroHUN passes all three. That the same protocol nevertheless "
             f"returns two CONDITIONAL verdicts on GastroHUN, rather than a "
             f"clean sweep, is itself reassurance that it measures something.")

    doc.add_page_break()
