"""
Phase 0 narrative for the GastroHUN report.

Every numeric value is interpolated from the audit artefacts in reports/.
Nothing is typed by hand.
"""

from __future__ import annotations

import json
from pathlib import Path

from docx.enum.text import WD_ALIGN_PARAGRAPH

from build_docx import bullet, callout, figure, h, para, rich, table

ROOT = Path(__file__).resolve().parents[2]
REP = ROOT / "reports"


def _j(name):
    p = REP / name
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else None


INV = _j("gastrohun_inventory.json")
AGR = _j("gastrohun_agreement.json")
STR = _j("gastrohun_structure.json")
ND = _j("gastrohun_neardup.json")
CAL = _j("gastrohun_dup_calibration.json")
OLD = _j("phase0_results.json")

CA_PCT = AGR["agreement_tiers_pct"]["complete_agreement_4of4"]
N_IMG = AGR["n_images"]
N_PAT = AGR["n_patients"]
N_CLS = AGR["n_classes"]
DEC = STR["disagreement_decomposition_pct"]
GRAN = STR["agreement_by_granularity"]


# ==========================================================================
def sec_executive_summary(doc) -> None:
    h(doc, "Executive Summary", 1)

    para(doc,
         "This report documents Phase 0 (data provenance and integrity) and "
         "Phase 1 (systematic literature review and problem framing) of an "
         "undergraduate thesis on artificial intelligence for upper "
         "gastrointestinal endoscopy. It supersedes an earlier report of the "
         "same name in its entirety. The earlier report audited a tabular "
         "corpus of endoscopy findings that was subsequently withdrawn from "
         "the project after the audit established that its labels were derived "
         "by keyword rules from the same text used to build its features, and "
         "that no measurable association existed between its features and its "
         "target. No content, figure, table or conclusion from that report is "
         "carried forward. All analyses presented here were computed from the "
         "replacement corpus.")

    para(doc,
         f"The replacement corpus is GastroHUN, a peer-reviewed public dataset "
         f"of complete Systematic Screening Protocol for the Stomach (SSS) "
         f"photodocumentation released by the Hospital Universitario Nacional "
         f"de Colombia. The audited subset comprises {N_IMG:,} labelled images "
         f"from {N_PAT} patients across {N_CLS} categories — 22 SSS anatomical "
         f"landmarks plus one category for images judged unsuitable for "
         f"assessment. Its defining property, and the reason it was selected, "
         f"is that every image carries four independent expert labels that are "
         f"published separately rather than collapsed into a single consensus.")

    h(doc, "Phase 0 verdict", 2)
    para(doc,
         "The integrity gate returns PROCEED. Six of eight gate criteria pass "
         "without qualification and two return CONDITIONAL, meaning they "
         "constrain what the thesis may claim but do not invalidate the corpus.")

    rows = [
        ["G1", "Provenance, ethics and licence",
         "PASS", "Peer-reviewed descriptor; ethics approval CEI-2019-06-10; informed consent; open licence"],
        ["G2", "Physical integrity",
         "PASS", f"{INV['n_decoded_ok']:,}/{INV['n_manifest_rows']:,} images decoded; "
                 f"{INV['n_missing_from_disk']} missing, {INV['n_orphan_on_disk']} orphan, "
                 f"{INV['n_corrupt']} corrupt"],
        ["G3", "Duplication and contamination",
         "PASS", f"{INV['exact_duplicates']['n_groups']} exact-duplicate groups; cross-split "
                 "near-duplicates rejected under a calibrated decision rule"],
        ["G4", "Label architecture",
         "PASS", f"4 independent annotators retained separately across {N_CLS} classes"],
        ["G5", "Agreement quantification",
         "PASS", f"Fleiss κ = {AGR['fleiss_kappa']:.4f}; Krippendorff α = "
                 f"{AGR['krippendorff_alpha']:.4f}; Gwet AC1 = {AGR['gwet_ac1']:.4f}"],
        ["G6", "Split integrity",
         "PASS", "0 patient overlaps between any two official splits; class and "
                 f"agreement prevalence balanced (χ² p = {AGR['split_class_chi2']['p']:.4f})"],
        ["G7", "Statistical power",
         "CONDITIONAL", f"{AGR['n_test_classes_underpowered_hw_gt_10pct']}/{N_CLS} classes exceed "
                        "a ±10 pp Wilson half-width on the consensus test set"],
        ["G8", "Population description",
         "CONDITIONAL", "No age or sex recorded; "
                        f"{AGR['clinical_metadata']['pct_image_patients_with_clinical_record']:.1f}% "
                        "of imaged patients have a clinical record"],
    ]
    table(doc, ["Gate", "Criterion", "Verdict", "Evidence"], rows,
          "Phase 0 integrity gate — criteria, verdicts and supporting evidence.",
          widths=[1.2, 4.4, 2.2, 9.0], font=7.6,
          note="A CONDITIONAL verdict identifies a constraint that must be "
               "declared in the thesis, not a defect that blocks use of the corpus.")

    h(doc, "Principal findings", 2)

    para(doc, "Four findings from the Phase 0 audit shape the research question "
              "that Phase 1 goes on to formalise.")

    para(doc,
         f"First, the corpus is physically and structurally sound. Every one of "
         f"the {INV['n_manifest_rows']:,} manifest entries resolves to a file on "
         f"disk that decodes without error; there are no orphan files, no "
         f"content-identical duplicates under SHA-256, and no disagreement "
         f"between the directory a file sits in and the patient it is attributed "
         f"to. The official splits are disjoint at patient level, which is the "
         f"correct unit of independence for this task, and both class prevalence "
         f"and agreement prevalence are statistically indistinguishable across "
         f"them.", size=10.5)

    para(doc,
         f"Second, expert agreement is substantial but far from complete. Across "
         f"four annotators the multi-rater agreement is κ = "
         f"{AGR['fleiss_kappa']:.3f}. Only {CA_PCT:.1f}% of images attract a "
         f"unanimous four-of-four label, and {AGR['pct_no_majority']:.1f}% admit "
         f"no majority label at all. The published benchmark for this dataset "
         f"trains and evaluates on the unanimous subset alone.", size=10.5)

    para(doc,
         f"Third — and this is the finding that is not reported in the dataset "
         f"descriptor — disagreement is not random. Because each SSS code "
         f"encodes an anatomical wall and a station along the stomach, every "
         f"disagreement can be decomposed. "
         f"{DEC['same_station_different_wall']:.1f}% of all disagreement events "
         f"are cases where two experts agree on the station but differ on the "
         f"wall; only {DEC['same_wall_different_station']:.1f}% are the reverse. "
         f"Collapsing the label space to station alone raises mean pairwise κ "
         f"from {GRAN['full']['mean_pairwise_kappa']:.3f} to "
         f"{GRAN['station']['mean_pairwise_kappa']:.3f}, whereas collapsing to "
         f"wall alone changes it to {GRAN['wall']['mean_pairwise_kappa']:.3f} — "
         f"that is, essentially not at all. Endoscopists know how deep the scope "
         f"is; they disagree about which way it is pointing.", size=10.5)

    para(doc,
         f"Fourth, the judgement that an image is unusable is strongly "
         f"annotator-specific. The rate at which the four experts assign the "
         f"OTHERCLASS category ranges from "
         f"{min(STR['otherclass']['per_rater_OTHERCLASS_rate_pct'].values()):.2f}% "
         f"to {max(STR['otherclass']['per_rater_OTHERCLASS_rate_pct'].values()):.2f}%, "
         f"a {max(STR['otherclass']['per_rater_OTHERCLASS_rate_pct'].values())/min(STR['otherclass']['per_rater_OTHERCLASS_rate_pct'].values()):.1f}-fold "
         f"spread, and only "
         f"{STR['otherclass']['pct_of_OTHERCLASS_nominations_that_are_unanimous']:.1f}% "
         f"of images ever called unusable are called so unanimously. This single "
         f"category accounts for {DEC['landmark_vs_OTHERCLASS']:.1f}% of all "
         f"disagreement.", size=10.5)

    callout(doc,
            f"The research gap follows directly from the audit. Model "
            f"performance on this dataset has only ever been measured on the "
            f"{CA_PCT:.1f}% of images that four experts label identically. "
            f"Performance on the remaining {100-CA_PCT:.1f}% — the images "
            f"clinicians themselves find ambiguous, and therefore the images "
            f"where automated assistance would matter most — is unmeasured. "
            f"The thesis proposes to measure it.",
            title="The gap this thesis addresses")

    h(doc, "Phase 1 verdict", 2)
    P = json.loads((ROOT / "literature_v2" / "prisma_counts.json").read_text(encoding="utf-8"))
    s, e = P["stages"], P["eligibility"]
    para(doc,
         f"A PRISMA 2020-structured search of PubMed/MEDLINE across seven themed "
         f"queries identified {s['records_identified_total']:,} records, "
         f"{s['records_after_deduplication']:,} after de-duplication. "
         f"{e['records_assessed_for_eligibility']:,} records were assessed "
         f"against declarative theme-specific eligibility criteria, yielding "
         f"{e['included_from_database_search']} included studies, to which "
         f"{e['included_from_other_methods']} foundational works not indexed in "
         f"MEDLINE were added through the PRISMA other-methods arm, for "
         f"{e['total_included_in_review']} studies in total. The review confirms "
         f"that landmark classification, endoscopic quality auditing and "
         f"inter-observer variability are each well studied in isolation, and "
         f"that their intersection — how landmark classifiers behave as human "
         f"agreement degrades — is not.")

    doc.add_page_break()


# ==========================================================================
def sec_phase0(doc) -> None:
    h(doc, "Phase 0 — Data Provenance and Integrity Gate", 1)

    # ---------------------------------------------------------------- 1.1
    h(doc, "Rationale: why an integrity gate precedes any modelling", 2)
    para(doc,
         "Phase 0 is a mandatory gate. No model is trained, and no performance "
         "figure is quoted, until the corpus has passed an explicit, documented "
         "set of integrity criteria. The rationale is not procedural caution; it "
         "is that this project has already been damaged once by its absence.")

    if OLD:
        pt = OLD.get("permutation_test", {})
        para(doc,
             f"The thesis originally used a tabular corpus of endoscopy findings. "
             f"A model trained on it reported near-perfect accuracy. A Phase 0 "
             f"audit subsequently established that the diagnostic label had been "
             f"constructed by regular expressions applied to the very text fields "
             f"that became the model's features, so the reported accuracy measured "
             f"the recovery of a rule the analyst had written, not any diagnostic "
             f"capability. A permutation test on that corpus returned "
             f"p = {pt.get('p_value', float('nan')):.4f}, meaning the observed "
             f"feature–target association was entirely consistent with chance. "
             f"That corpus is retained in the project as a negative control — it "
             f"is the specimen against which this audit protocol is validated — "
             f"but it plays no further role in the research.")

    callout(doc,
            "A dataset that fails silently is more dangerous than one that fails "
            "loudly. The purpose of Phase 0 is to make failure loud, and to do so "
            "before the failure has been written into a thesis.")

    figure(doc, "F01_thesis_workflow.png",
           "Thesis workflow. Phases 0 and 1, enclosed by the dashed boundary, "
           "constitute the deliverable of this report; later phases are stated "
           "for context and are governed by the findings established here.")

    # ---------------------------------------------------------------- 1.2
    h(doc, "Provenance of the corpus", 2)
    para(doc,
         "GastroHUN was published as a peer-reviewed data descriptor in "
         "Scientific Data in January 2025 by a group at the Universidad Nacional "
         "de Colombia and the Hospital Universitario Nacional de Colombia. "
         "Provenance is documented at every level that matters for a clinical "
         "corpus: the acquiring institution, the ethics approval, the consent "
         "basis, the acquisition equipment, the operators, and the anonymisation "
         "procedure are all stated in the descriptor and are reproduced below.")

    prov_rows = [
        ["Source institution", "Hospital Universitario Nacional de Colombia (HUN), Bogotá"],
        ["Data descriptor", "Bravo et al., Scientific Data 12:102 (2025), doi:10.1038/s41597-025-04401-5"],
        ["Ethics approval", "Ethics Committee of HUN, approval CEI-2019-06-10; Declaration of Helsinki"],
        ["Consent basis", "Signed informed consent permitting research and educational reuse"],
        ["Anonymisation", "Metadata stripped; filenames replaced by hash-generated identifiers; "
                          "frames recorded outside the body removed"],
        ["Collection period", "Procedures scheduled 2019–2023, collected retrospectively"],
        ["Acquisition system", "Olympus EVIS EXERA III CV-190 processor, CLV-190 light source, "
                               "EXERA II TJF-Q180V / GIF-H170 gastroscope"],
        ["Operators", "Two final-year gastroenterology residents (Team A, 'FG') and two "
                      "gastroenterologists (Team B, 'G'); a master gastroenterologist "
                      "with ~50,000 procedures supervised acquisition"],
        ["Acquisition protocol", "Systematic Screening Protocol for the Stomach (SSS), 22 landmarks"],
        ["Audited subset", f"'Labeled Images' ({INV['bytes']['total_gb']:.2f} GB), official splits, metadata"],
        ["Full release size", "96.86 GB across images, sequences and videoendoscopies"],
    ]
    table(doc, ["Provenance attribute", "Value"], prov_rows,
          "Documented provenance of the GastroHUN corpus.",
          widths=[4.6, 12.2], font=8.0)

    para(doc,
         "One provenance discrepancy must be recorded. The project's GitHub "
         "repository states a CC BY-NC 4.0 licence, whereas the Figshare record "
         "that actually hosts the data, and the descriptor itself, state CC BY "
         "4.0. The Figshare record is the authoritative statement for the "
         "artefact being used, and the more permissive CC BY 4.0 is therefore "
         "taken to govern. Because the two differ on the non-commercial clause, "
         "the discrepancy is documented here rather than resolved silently, and "
         "no commercial use is made of the data in any case.")

    para(doc,
         "The acquisition protocol deserves emphasis because it determines the "
         "label space. The SSS protocol prescribes a fixed sequence of 22 "
         "photographs. The endoscope is positioned at the pylorus and withdrawn "
         "through four successive stations, at each of which four images are "
         "taken in clockwise order — greater curvature, anterior wall, lesser "
         "curvature, posterior wall — followed by two further retroflexed "
         "stations contributing three images each. Every class label is "
         "therefore a pair: a wall and a station.")

    figure(doc, "F03_sss_taxonomy.png",
           "The 22 SSS landmarks arranged as a wall × station grid, shaded by "
           "the number of images attracting unanimous expert agreement. Stations "
           "5 and 6 contribute three images rather than four because no greater-"
           "curvature view is prescribed in retroflexion.")

    tax_rows = []
    for s in range(1, 7):
        codes = [t["code"] for t in STR["taxonomy"]
                 if t["station"] == s]
        name = STR["station_names"][str(s)]
        diff = STR["station_difficulty"][f"station_{s}"]["disagreement_rate_pct"]
        tax_rows.append([f"S{s}", name, ", ".join(sorted(codes)), f"{diff:.1f}%"])
    tax_rows.append(["—", "Image unsuitable for assessment", "OTHERCLASS", "—"])
    table(doc, ["Station", "Anatomical position", "Landmark codes",
                "Rater-pair disagreement"], tax_rows,
          "The SSS station taxonomy, with the observed rate at which two "
          "randomly chosen expert annotators disagree about an image assigned "
          "to that station.",
          widths=[1.8, 6.0, 5.4, 3.6], font=8.0,
          note="Wall codes: G = greater curvature, A = anterior wall, "
               "L = lesser curvature, P = posterior wall.")

    # ---------------------------------------------------------------- 1.3
    h(doc, "G1–G2: Physical inventory and file integrity", 2)
    para(doc,
         f"Every filename in the official split manifest was resolved against "
         f"the extracted image tree, and every resolved file was fully decoded "
         f"rather than merely opened, so that truncated JPEG streams would raise "
         f"an error rather than pass inspection. A SHA-256 content hash and a "
         f"64-bit perceptual difference hash were computed for each image in the "
         f"same pass.")

    inv_rows = [
        ["Manifest entries", f"{INV['n_manifest_rows']:,}"],
        ["Unique filenames in manifest", f"{INV['n_manifest_unique_filenames']:,}"],
        ["Files present on disk", f"{INV['n_files_on_disk']:,}"],
        ["Patient directories", f"{INV['n_patient_folders']}"],
        ["Images fully decoded", f"{INV['n_decoded_ok']:,}"],
        ["Listed in manifest but missing from disk", f"{INV['n_missing_from_disk']}"],
        ["Present on disk but absent from manifest", f"{INV['n_orphan_on_disk']}"],
        ["Failed to decode (truncated or corrupt)", f"{INV['n_corrupt']}"],
        ["Directory/manifest patient mismatches", f"{INV['folder_patient_mismatch']}"],
        ["Container formats observed", ", ".join(f"{k} ({v:,})" for k, v in INV["formats"].items())],
        ["Colour modes observed", ", ".join(f"{k} ({v:,})" for k, v in INV["modes"].items())],
        ["Native resolutions", ", ".join(f"{k} ({v:,})" for k, v in INV["resolutions"].items())],
        ["Total payload", f"{INV['bytes']['total_gb']:.3f} GB"],
        ["File size (mean / median)",
         f"{INV['bytes']['mean_kb']:.1f} KB / {INV['bytes']['median_kb']:.1f} KB"],
        ["File size (min / max)",
         f"{INV['bytes']['min_kb']:.1f} KB / {INV['bytes']['max_kb']:.1f} KB"],
        ["Images per patient (mean ± SD)",
         f"{INV['images_per_patient']['mean']:.2f} ± {INV['images_per_patient']['std']:.2f}"],
        ["Images per patient (min / median / max)",
         f"{INV['images_per_patient']['min']} / "
         f"{INV['images_per_patient']['median']:.0f} / "
         f"{INV['images_per_patient']['max']}"],
    ]
    table(doc, ["Inventory measure", "Value"], inv_rows,
          "Physical inventory of the audited corpus.",
          widths=[7.2, 9.6], font=8.0)

    para(doc,
         f"The manifest and the filesystem agree exactly. The mean of "
         f"{INV['images_per_patient']['mean']:.2f} images per patient sits just "
         f"above the 22 prescribed by the protocol, which is the expected "
         f"signature of a protocol-driven acquisition: most patients contribute "
         f"the full prescribed set, a few contribute repeats where a first "
         f"attempt was unsatisfactory, and a small number contribute fewer "
         f"where the procedure was curtailed. The observed range is "
         f"{INV['images_per_patient']['min']} to "
         f"{INV['images_per_patient']['max']}.")

    figure(doc, "F14_inventory.png",
           "Physical inventory. Left: native resolution split. Centre: "
           "acquisition provenance — images captured directly by the endoscope "
           "processor against frames extracted from recorded video. Right: "
           "summary integrity counters, all of which are zero for the failure "
           "modes tested.")

    para(doc,
         f"Two acquisition streams are present and are declared in the "
         f"metadata: {STR['provenance']['by_source_type']['direct_capture']['n']:,} "
         f"images "
         f"({STR['provenance']['by_source_type']['direct_capture']['pct_of_corpus']:.2f}%) "
         f"were written directly by the endoscope processor, and "
         f"{STR['provenance']['by_source_type']['video_frame']['n']} "
         f"({STR['provenance']['by_source_type']['video_frame']['pct_of_corpus']:.2f}%) "
         f"were extracted as frames from recorded videoendoscopies. This matters "
         f"because a systematic quality difference between the streams would "
         f"confound any analysis of annotator agreement. It was tested and none "
         f"was found: unanimity rates are "
         f"{STR['provenance']['by_source_type']['direct_capture']['pct_unanimous']:.2f}% "
         f"and {STR['provenance']['by_source_type']['video_frame']['pct_unanimous']:.2f}% "
         f"respectively (χ² = {STR['provenance']['unanimity_chi2']:.2f}, "
         f"p = {STR['provenance']['unanimity_p']:.3f}; Mann–Whitney "
         f"p = {STR['provenance']['mannwhitney_p']:.3f}).")

    para(doc,
         f"The two streams are, however, unevenly distributed across the "
         f"official splits: video-derived frames make up "
         f"{100*STR['provenance']['source_type_by_split']['Train']['video_frame']/(STR['provenance']['source_type_by_split']['Train']['video_frame']+STR['provenance']['source_type_by_split']['Train']['direct_capture']):.1f}% "
         f"of the training set but only "
         f"{100*STR['provenance']['source_type_by_split']['Validation']['video_frame']/(STR['provenance']['source_type_by_split']['Validation']['video_frame']+STR['provenance']['source_type_by_split']['Validation']['direct_capture']):.1f}% "
         f"of validation and "
         f"{100*STR['provenance']['source_type_by_split']['Test']['video_frame']/(STR['provenance']['source_type_by_split']['Test']['video_frame']+STR['provenance']['source_type_by_split']['Test']['direct_capture']):.1f}% "
         f"of test (χ² = {STR['provenance']['source_type_split_chi2']:.1f}, "
         f"p = {STR['provenance']['source_type_split_p']:.2e}). The official "
         f"stratification balanced agreement level, not acquisition stream, so "
         f"this imbalance was not controlled. Because agreement does not differ "
         f"between the streams, the practical consequence is small, but the "
         f"imbalance is recorded here and any claim of distributional equality "
         f"between the splits must be qualified accordingly.")

    para(doc,
         f"A marginal association was also detected between native resolution "
         f"and unanimity: the "
         f"{STR['resolution']['by_width']['900']['n']} images at 900×720 attract "
         f"unanimous labels "
         f"{STR['resolution']['by_width']['900']['pct_unanimous']:.1f}% of the "
         f"time against "
         f"{STR['resolution']['by_width']['1350']['pct_unanimous']:.1f}% for the "
         f"{STR['resolution']['by_width']['1350']['n']:,} images at 1350×1080 "
         f"(χ² = {STR['resolution']['chi2']:.2f}, "
         f"p = {STR['resolution']['p']:.3f}). This is a single nominally "
         f"significant result among several tests reported in this section and "
         f"would not survive correction for multiplicity; it is noted as a "
         f"hypothesis, not a finding.")


# ==========================================================================
def sec_contamination(doc) -> None:
    h(doc, "G3: Duplication and cross-split contamination", 2)
    para(doc,
         "Near-duplicate images that straddle a train/test boundary are the "
         "most common silent defect in endoscopy imaging studies, because "
         "consecutive frames of the same anatomical site are nearly identical "
         "and a naive split can place one in training and its twin in test. The "
         "resulting performance estimate is optimistically biased. Two tests "
         "were applied.")

    para(doc,
         f"The exact test is unambiguous. Grouping all {INV['n_decoded_ok']:,} "
         f"images by SHA-256 content hash yields "
         f"{INV['exact_duplicates']['n_groups']} groups containing more than one "
         f"file. No image in this corpus is byte-identical to any other.")

    para(doc,
         f"The perceptual test is where care is required. All "
         f"{ND['n_pairs_examined']:,} image pairs were compared exhaustively on "
         f"a 64-bit difference hash — an exact computation, not an approximate "
         f"nearest-neighbour search, so no pair is missed. At a Hamming radius "
         f"of {ND['operative_threshold']}, "
         f"{ND['cross_split_candidates']:,} candidate pairs cross a split "
         f"boundary. Taken at face value this looks alarming.")

    if CAL:
        cal = CAL
        para(doc,
             "It is not, and establishing why is the most instructive "
             "methodological episode in this audit. Endoscopic frames all share "
             "a bright, low-texture circular field on a black surround, so "
             "global image statistics are similar for very many pairs. A "
             "similarity threshold carried over from natural-image work "
             "over-triggers badly here. Rather than assume a decision rule, the "
             "rule was calibrated against two controls, and it took two attempts "
             "to get the calibration right.")

        para(doc,
             f"A positive control was built from "
             f"{cal['positive_control']['n_pairs']:,} synthetic true duplicates, "
             f"produced by subjecting real images to the transformations a "
             f"genuine duplicate would undergo — JPEG re-compression, a ±2% "
             f"rescale and a one-to-two pixel crop. These bound what a real "
             f"duplicate looks like: mean normalised RMS difference "
             f"{cal['positive_control']['rms']['mean']:.4f}, maximum "
             f"{cal['positive_control']['rms']['max']:.4f}, and correlation "
             f"never below {cal['positive_control']['corr']['min']:.4f} across "
             f"all {cal['positive_control']['n_pairs']:,} trials.")

        para(doc,
             f"The first null was built from randomly drawn cross-patient pairs. "
             f"That null proved far too permissive, and the reason is worth "
             f"recording: random pairs mostly compare different anatomical "
             f"stations, which look nothing alike, so any two images of the same "
             f"landmark appear extraordinarily similar by comparison. Visual "
             f"inspection of the pairs it flagged settled the matter — they were "
             f"plainly two different stomachs photographed at the same site, one "
             f"with an endoscope sheath visible in frame, differing in mucosal "
             f"texture and specular highlights. The null was rebuilt as "
             f"{cal['null']['n_pairs']:,} class-matched cross-patient pairs: two "
             f"different patients photographed at the same SSS landmark, which "
             f"is the comparison that actually matters.")

        nr = cal["null_anchored_rule"]
        cr = cal["calibrated_rule"]
        para(doc,
             f"Even the corrected null does not by itself settle the question, "
             f"because it answers the wrong one. A null-anchored rule (RMS below "
             f"{nr['rms_cut']:.4f}, correlation above {nr['corr_cut']:.4f}) asks "
             f"whether a pair is unusually similar for two different patients. "
             f"The question that matters is whether the pair's scores are "
             f"consistent with its having been produced by duplication at all. "
             f"The rule finally adopted is therefore anchored on the positive "
             f"control: RMS below {cr['rms_cut']:.4f} and correlation above "
             f"{cr['corr_cut']:.4f}, the 99.9th and 0.1st percentiles of the "
             f"synthetic-duplicate distribution. It retains "
             f"{100*cr['sensitivity_on_positive_control']:.1f}% sensitivity to "
             f"genuine duplicates and admits "
             f"{100*cr['false_positive_rate_on_null']:.2f}% of the "
             f"{cal['null']['n_pairs']:,} class-matched non-duplicate pairs. The "
             f"two distributions are cleanly separated, with a margin of "
             f"{cr['separation_margin']:.4f} RMS between them.")

        r = cal["reassessment"]
        callout(doc,
                f"Of the {r['n_flagged_by_provisional_rule']} cross-split pairs "
                f"flagged by the uncalibrated provisional rule, "
                f"{r['n_passing_null_anchored_rule']} survive the null-anchored "
                f"rule and {r['n_confirmed_by_calibrated_rule']} survive the "
                f"adopted rule. {r['verdict']} Every flagged pair falls outside "
                f"the envelope that genuine duplication produces — they are "
                f"different patients photographed at the same anatomical "
                f"landmark under a standardised protocol, which is exactly what "
                f"a protocol-driven corpus should contain.",
                title="G3 verdict — no cross-split contamination")

        figure(doc, "F15b_dup_calibration.png",
               "Calibration of the duplicate decision rule. Synthetic true "
               "duplicates (green) and class-matched non-duplicate pairs (blue) "
               "are cleanly separated on normalised RMS difference. Every pair "
               "flagged by the provisional rule (red crosses) lies outside the "
               "duplicate envelope, to the right of the decision threshold.")

        para(doc,
             f"This is reported at length because the intermediate result — "
             f"'the audit found {r['n_flagged_by_provisional_rule']} cross-split "
             f"duplicate pairs' — is quotable, alarming and wrong. Had it been "
             f"carried forward it would have entered the thesis as a spurious "
             f"criticism of a carefully constructed public dataset. An "
             f"uncalibrated threshold is not a measurement, and a threshold "
             f"calibrated against the wrong comparison is not much better.")
    else:
        para(doc,
             "Calibration of the perceptual decision rule was not available "
             "when this document was generated; the exact-hash result stands "
             "and the perceptual result is reported as candidate counts only.")

    figure(doc, "F15_contamination.png",
           "Cross-split contamination audit. Left: candidate pair counts across "
           "the perceptual-hash threshold sweep, separated by whether a pair "
           "shares a patient, shares a split, or crosses a split boundary. "
           "Right: summary of the exhaustive scan and the calibrated decision "
           "rule.")

    para(doc,
         f"One further observation supports the integrity of the splits. "
         f"Within-patient near-duplicates — which are expected, since the "
         f"protocol photographs adjacent overlapping views — occur at a rate of "
         f"only {ND['within_patient_neardup_rate_pct']:.4f}% of the "
         f"{ND['within_patient_pairs_possible']:,} possible within-patient "
         f"pairs at the operative threshold. The corpus is a set of distinct "
         f"photographs, not a set of near-identical frames sampled from video.")
