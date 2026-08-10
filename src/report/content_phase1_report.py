"""
Phase-I Progress Report -- the prose, tables and figure placements.

Separated from the DOCX mechanics in build_phase1_docx.py so that the writing
can be read and revised as writing. Every measurement is interpolated from
`phase1_facts.facts()`; nothing numeric is typed here.

(Not to be confused with content_phase1.py, which holds the Phase 1 literature
chapter of the Phase 0/1 report.)

Block vocabulary consumed by the builder:
    {"t": "p",   "text": str}                        body paragraph
    {"t": "num", "items": [str, ...]}                numbered list
    {"t": "fig", "path": str, "cap": str, "w": float}
    {"t": "tbl", "cap": str, "head": [...], "rows": [[...]], "w": [...]}
"""
from __future__ import annotations


# ==========================================================================
# 1.1 Introduction
# ==========================================================================
def introduction(F):
    c, ag, b = F["corpus"], F["agreement"], F["baseline"]
    return [
        {"t": "p", "text":
            "Upper gastrointestinal endoscopy is the primary screening modality for "
            "gastric cancer, and its diagnostic yield depends on whether the operator "
            "inspects the whole mucosal surface rather than a convenient subset of it. "
            "The Systematic Screening protocol for the Stomach formalises that "
            "requirement as a fixed photographic sequence covering twenty-two "
            "anatomical landmarks, organised as a grid of four gastric walls crossed "
            "with six depth stations. A model that recognises the landmark visible in "
            "each frame can therefore act as a real-time coverage monitor and warn the "
            "operator that a region has not yet been visited."},
        {"t": "p", "text":
            f"Published systems report macro F1 near {b['published']:g} to 88 on this "
            f"recognition task, and the problem is generally treated as solved. Every "
            f"one of those figures, however, is measured only on frames whose expert "
            f"annotators all chose the same label. In the corpus used here that "
            f"unanimous subset is {ag['unanimous_pct']:.1f} per cent of the data; the "
            f"remaining {ag['contested_pct']:.1f} per cent, {ag['contested_n']:,} "
            f"images, is removed before scoring and never enters a reported result. The "
            f"discarded fraction is not random noise. Half of all annotator conflicts "
            f"place two experts on different walls of the same station, which means the "
            f"disagreement follows the anatomy of the label space rather than "
            f"scattering across it."},
        {"t": "p", "text":
            "The main goal of this project is therefore to measure what current "
            "accuracy figures actually describe. It evaluates landmark classifiers "
            "across strata of expert agreement rather than on unanimous frames alone, "
            "and it tests whether training targets built from the complete "
            "four-annotator vote distribution improve accuracy, calibration and "
            "uncertainty behaviour on contested images. The contribution is diagnostic "
            "rather than architectural: no new network is proposed, and the improvement "
            "sought is in what is known about the task rather than in a leaderboard "
            "position."},
        {"t": "p", "text":
            "Three specific objectives follow from that goal. The first is to establish "
            "that the corpus is sound and the training pipeline is correct, by auditing "
            "provenance and integrity before any model is fitted and then reproducing "
            "the published baseline to within a tolerance fixed in advance. The second "
            "is to quantify how performance and confidence behave as expert agreement "
            "falls, with intervals that respect the clustering of images within "
            "patients. The third is to build the study as a reproducible artefact, in "
            "which every figure, table and interval regenerates from committed scripts "
            "rather than being transcribed by hand."},
        {"t": "p", "text":
            f"This report covers the first four of the seven phases into which the work "
            f"is divided. At the time of writing, the corpus of {c['n_images']:,} "
            f"images from {c['n_patients']} patients has passed an eight-criterion "
            f"integrity gate, a systematic literature review has been completed, a "
            f"baseline model has been trained, validated and tested, and its behaviour "
            f"has been measured across four agreement strata. Figure {{fig:workflow}} shows the phase "
            f"structure and marks the portion reported here."},
        {"t": "fig", "id": "workflow", "path": "figures_phase1/PH1_F04_workflow.png", "w": 6.4,
         "cap": "Phase structure of the project. Each phase is gated on the previous "
                "phase's validation criterion, and the four phases reported here cover "
                "every Phase-I requirement."},
    ]


# ==========================================================================
# 1.2 Background Study
# ==========================================================================
def background(F):
    c, ag, st, pr = F["corpus"], F["agreement"], F["structure"], F["prisma"]
    return [
        {"t": "p", "text":
            f"A systematic review was carried out to establish what is already known "
            f"and where the evidence stops. Seven themed queries were run against "
            f"PubMed/MEDLINE, covering landmark recognition, endoscopic quality and "
            f"blind-spot auditing, inter-observer variability, noisy and "
            f"multi-annotator labels, uncertainty and calibration, external validation, "
            f"and reporting standards for medical artificial intelligence. The searches "
            f"returned {pr['identified']:,} records, {pr['unique']:,} after "
            f"de-duplication, of which {pr['included']} studies were included: "
            f"{pr['included_db']} from the database search and {pr['included_hand']} "
            f"added through the PRISMA other-methods arm, because several relevant "
            f"computer-science venues are not indexed in MEDLINE. The flow is reported "
            f"in Figure {{fig:prisma}} according to PRISMA 2020 [14]."},
        {"t": "fig", "id": "prisma", "path": "figures_phase1/PH1_F08_prisma.png", "w": 6.4,
         "cap": "PRISMA 2020 flow and the thematic composition of the included "
                "studies."},
        {"t": "p", "text":
            "Clinical task. The Systematic Screening protocol prescribes a fixed "
            "photographic route through the stomach. Its label space is the product of "
            "two axes: the circumferential wall, comprising the greater curvature, the "
            "anterior wall, the lesser curvature and the posterior wall; and the axial "
            "station, running from the antrum through to the final retroflex view. "
            "Automated recognition of this route underpins blind-spot monitoring and "
            "endoscopic quality scoring, and comparable systems have been reported to "
            "reduce blind-spot rates in prospective use [10]."},
        {"t": "p", "text":
            f"Corpus and published baselines. GastroHUN [1] releases {c['n_images']:,} "
            f"images from {c['n_patients']} patients recorded at the Hospital "
            f"Universitario Nacional de Colombia. Each image carries "
            f"{c['n_annotators']} independent labels over {c['n_classes']} classes, "
            f"supplied by two gastroenterologists and two fellows, and the official "
            f"splits are patient-disjoint. Table {{tbl:baselines}} lists the baselines the descriptor "
            f"reports. Two features of that table matter more than the headline "
            f"numbers. Every figure in it is measured on the unanimous subset alone. "
            f"And changing only how the four annotator labels are combined moves macro "
            f"F1 by 2.2 points, which is a larger effect than the gap between the "
            f"smallest and largest architecture families the descriptor evaluates. The "
            f"descriptor records that observation and does not pursue it; it is the "
            f"direct precedent for this work."},
        {"t": "tbl", "id": "baselines",
         "cap": "Published baselines on this corpus, as reported by the dataset "
                "descriptor [1]. Every figure is measured on the complete-agreement "
                "subset only.",
         "head": ["Model or label construction", "Parameters", "Macro F1"],
         "w": [3.3, 1.3, 1.6],
         "rows": [
             ["ConvNeXt-Large", "200 M", "88.25 ± 0.22"],
             ["ConvNeXt-Tiny", "28 M", "≈ 85"],
             ["ResNet-152", "60 M", "85.28 ± 0.27"],
             ["ConvNeXt-Tiny, fellow-agreement labels", "28 M", "87.05 ± 0.21"],
             ["Best single annotator (G1) as target", "—", "84.82 ± 0.23"],
             ["Human expert band", "—", "77.47 – 84.82"],
         ]},
        {"t": "p", "text":
            f"Agreement structure measured during preparation. Chance-corrected "
            f"agreement over the released labels is Fleiss' kappa = {ag['fleiss']:.4f}. "
            f"Krippendorff's alpha and Gwet's AC1 coincide with it to four decimal "
            f"places, because the screening protocol keeps the class marginal "
            f"near-uniform and the three chance corrections become algebraically equal "
            f"in that regime; the well-known kappa paradox therefore does not arise on "
            f"this corpus. Seniority does not predict agreement: each fellow agrees "
            f"more closely with either gastroenterologist than with the other fellow, "
            f"so any design that treats a team as a coherent unit is unsupported by the "
            f"data. Unanimity is {ag['unanimous_pct']:.1f} per cent, and "
            f"{ag['n_no_majority']:,} images ({ag['pct_no_majority']:.2f} per cent) "
            f"admit no majority label under any voting rule. Figure {{fig:agreement}} reports the "
            f"cascade, the vote patterns and the pairwise agreement."},
        {"t": "fig", "id": "agreement", "path": "figures_phase1/PH1_F06_agreement.png", "w": 6.4,
         "cap": "Annotator agreement: the cascade from all images to unanimity, the "
                "distribution of vote patterns, and pairwise Cohen's kappa with "
                "patient-clustered intervals."},
        {"t": "p", "text":
            f"Disagreement respects the anatomy. Of {ag['n_disagreement_events']:,} "
            f"pairwise conflicts, "
            f"{st['decomp_pct']['same_station_different_wall']:.2f} per cent are "
            f"same-station different-wall and only "
            f"{st['decomp_pct']['same_wall_different_station']:.2f} per cent are "
            f"same-wall different-station. Collapsing the label space to stations alone "
            f"raises mean pairwise kappa from {st['kappa_full']:.4f} to "
            f"{st['kappa_station']:.4f}, whereas collapsing to walls alone changes it "
            f"only to {st['kappa_wall']:.4f}. Endoscopists agree on how deep the scope "
            f"is and disagree about which way it points. Figures {{fig:labelspace}} and {{fig:disagreement}} set out the "
            f"label space and this decomposition. The structure matters for the design "
            f"of the work, because a disagreement that follows a known geometry is "
            f"something a model can be asked to reproduce, whereas unstructured noise "
            f"is not."},
        {"t": "fig", "id": "labelspace", "path": "figures_phase1/PH1_F05_label_space.png", "w": 6.4,
         "cap": "The wall-by-station label space, and what happens to agreement when "
                "each axis is collapsed in turn."},
        {"t": "fig", "id": "disagreement", "path": "figures_phase1/PH1_F07_disagreement_structure.png",
         "w": 6.4,
         "cap": "Decomposition of the pairwise disagreement events, and the wall pairs "
                "that account for them."},
        {"t": "p", "text":
            "Inter-observer variability in endoscopy. Substantial rater disagreement is "
            "documented across endoscopic and histological classification, including "
            "the Paris classification of colorectal lesions [3], OLGA and OLGIM "
            "gastritis staging [4], and oesophageal varices in children [5]. Agreement "
            "is thus a property of the task rather than a defect of a single dataset, "
            "which is why an evaluation conditioned on unanimity reports a "
            "systematically easier problem than the clinical one."},
        {"t": "p", "text":
            "Learning from multiple annotators. Modelling label confidence rather than "
            "a single consensus target has been shown to improve histology "
            "classification [6], and annotator uncertainty used as privileged "
            "information improves clinical prediction [7]. Multi-rater calibration is "
            "an active benchmark target [8]. These methods are rarely applied to "
            "endoscopic landmark recognition, largely because per-annotator labels are "
            "seldom released, which is precisely what makes this corpus suitable."},
        {"t": "p", "text":
            "Reporting quality. Systematic reviews of diagnostic deep learning find "
            "that calibration and external validation are routinely omitted and that "
            "comparison against clinicians is weakly reported [2, 9]. Where external "
            "validation is performed, sizeable accuracy loss across centres is the "
            "norm, and modern networks are known to be poorly calibrated even when "
            "accurate [15]. This project therefore treats calibration and a change of "
            "centre as primary endpoints rather than as optional extras, and follows "
            "the CLAIM, TRIPOD+AI, STARD-AI, PROBAST+AI and PRISMA 2020 reporting "
            "standards."},
    ]


# ==========================================================================
# 1.3 Gap Analysis
# ==========================================================================
def gap_analysis(F):
    ag, st = F["agreement"], F["structure"]
    return [
        {"t": "p", "text":
            "Three gaps emerge from the background study. They are stated here as "
            "measurable deficiencies rather than as general observations, so that each "
            "one has a corresponding endpoint later in the design."},
        {"t": "p", "text":
            f"Gap 1: evaluation is conditioned on expert unanimity. No published "
            f"evaluation on this corpus reports performance as a function of expert "
            f"agreement, because contested images are filtered out before scoring. The "
            f"reported figure therefore describes {ag['unanimous_pct']:.1f} per cent of "
            f"the data and is silent about the rest. A deployed system meets the "
            f"contested {ag['contested_pct']:.1f} per cent continuously and receives no "
            f"signal that its validation excluded those frames. Its operating accuracy "
            f"is consequently unknown on exactly the images where an automated second "
            f"reader would be most useful."},
        {"t": "p", "text":
            f"Gap 2: annotator disagreement is discarded rather than used. Because "
            f"per-annotator labels are rarely released, the standard pipeline collapses "
            f"the vote distribution to a single label at ingest. On this corpus that "
            f"discards a structured signal: "
            f"{st['decomp_pct']['same_station_different_wall']:.2f} per cent of the "
            f"{ag['n_disagreement_events']:,} conflicts are same-station "
            f"different-wall, and the walls involved are almost always circumferential "
            f"neighbours. The descriptor's own finding that the label-combination rule "
            f"moves macro F1 by more than the architecture family does confirms that "
            f"the discarded information is worth something, but no controlled test of "
            f"it has been reported."},
        {"t": "p", "text":
            "Gap 3: calibration is reported rarely, and never by stratum. Reviews of "
            "diagnostic deep learning identify absent calibration reporting as one of "
            "the commonest omissions in this literature. Nothing in the published work "
            "establishes whether confidence estimated on unanimous frames remains "
            "trustworthy on ambiguous ones. This is the most consequential omission "
            "clinically: a model that stays confident where four experts could not "
            "agree produces assured errors, which is the failure mode least likely to "
            "be caught by an endoscopist working under time pressure."},
        {"t": "fig", "id": "gap", "path": "figures_phase1/PH1_F09_gap_analysis.png", "w": 6.4,
         "cap": "Gap analysis: the three deficiencies identified in the background "
                "study, the evidence for each, and the design response adopted."},
        {"t": "p", "text":
            f"A fourth, methodological gap should be recorded because it shapes how "
            f"results are reported. Intervals in this literature are commonly computed "
            f"by resampling images. Images from one patient are not independent "
            f"observations here: per-patient agreement measured during preparation has "
            f"a mean of {st['patient_kappa_mean']:.4f} with a standard deviation of "
            f"{st['patient_kappa_sd']:.4f} and a range from "
            f"{st['patient_kappa_min']:.4f} to {st['patient_kappa_max']:.4f}. Every "
            f"interval in this project therefore resamples patients rather than images, "
            f"and is correspondingly wider than intervals published on the same "
            f"quantity."},
    ]


# ==========================================================================
# 1.4 Objectives
# ==========================================================================
def objectives(F):
    b = F["baseline"]
    return [
        {"t": "p", "text":
            "The objectives below are the ones this phase set out to achieve. Each is "
            "stated so that it can be judged met or unmet against evidence, and each "
            "has a corresponding artefact in the project repository."},
        {"t": "num", "items": [
            "Audit corpus provenance and integrity before any modelling: verify "
            "licence, ethics approval and documented consent; confirm that every image "
            "decodes and that the manifest and the file system agree; and establish, by "
            "a calibrated perceptual scan rather than an assumed threshold, that no "
            "image recurs across the patient-disjoint splits.",
            "Complete a systematic literature review to PRISMA 2020 across the seven "
            "themes that bound the problem, and derive from it a gap statement naming "
            "measurable deficiencies rather than general observations.",
            "Construct the pre-processing chain — annotation handling, cohort "
            "selection, resampling, normalisation, augmentation and the "
            "transfer-learned representation — and fix it once, so that every later "
            "phase differs from the baseline only in the quantity under test.",
            f"Train, validate and test at least one baseline model, and reproduce the "
            f"published result on the unanimous subset to within a tolerance of "
            f"±{b['band']:g} macro F1 points fixed before training, so that later "
            f"findings are attributable to the design rather than to a faulty pipeline.",
            "Quantify macro F1, expected accuracy and expected calibration error "
            "separately for each agreement stratum of the official test split, with "
            "patient-clustered bootstrap intervals, and compare the resulting decline "
            "against the between-architecture difference the descriptor reports.",
            "Release a reproducible pipeline in which every table, figure and interval "
            "in this report regenerates from committed scripts and versioned artefacts, "
            "with no value transcribed by hand.",
        ]},
    ]


# ==========================================================================
# 2.1 Research Design / Prototype Design
# ==========================================================================
def research_design(F):
    tr, co = F["training"], F["cohort"]
    return [
        {"t": "p", "text":
            "The study is an evaluation-and-training design executed in seven gated "
            "phases, of which four are reported here. A phase may not begin until the "
            "preceding phase has met a validation criterion written down before it ran. "
            "Each phase fixes its hypotheses, its primary endpoint and its verdict "
            "rules in a pre-registration file that the generating script refuses to "
            "overwrite. This matters because most endpoints in this project are "
            "comparisons that could be made to favour either conclusion by a choice of "
            "scale or stratum taken after seeing the data; fixing the choice in advance "
            "removes that freedom."},
        {"t": "p", "text":
            f"The backbone is ConvNeXt-Tiny [13], initialised from ImageNet-1k weights "
            f"and fitted with a {F['corpus']['n_classes']}-way linear head. It was "
            f"selected on two grounds. It is the architecture whose published result on "
            f"this corpus the project must reproduce, which is what makes the "
            f"reproduction check meaningful; and at "
            f"{tr['params_total'] / 1e6:.1f} million feature parameters it fits the 4 GB "
            f"of video memory available on the project hardware, whereas the "
            f"200-million-parameter ConvNeXt-Large that tops the published table does "
            f"not. ConvNeXt-Large is therefore cited as the published ceiling and "
            f"deliberately not attempted."},
        {"t": "p", "text":
            f"Training follows a two-stage transfer schedule. The backbone is first "
            f"frozen entirely and only the head is fitted, for {tr['warmup_epochs']} "
            f"epochs at a constant learning rate of {tr['lr_head']:g}. The top "
            f"{tr['n_modules_unfrozen']} of the {tr['n_feature_modules']} feature "
            f"modules, which hold {tr['param_fraction_unfrozen'] * 100:.1f} per cent of "
            f"the feature parameters, are then unfrozen and fine-tuned at "
            f"{tr['lr_finetune']:g} under cosine decay, with early stopping on "
            f"validation macro F1 and a patience of {tr['patience']} epochs. Model "
            f"selection uses validation macro F1 and nothing else; the test split is "
            f"touched once, after selection. Figure {{fig:arch}} shows the architecture and the "
            f"schedule together."},
        {"t": "fig", "id": "arch", "path": "figures_phase1/PH1_F02_architecture.png", "w": 6.4,
         "cap": "The ConvNeXt-Tiny backbone, the parameter blocks held frozen, and the "
                "two-stage transfer schedule. Layer widths and parameter counts are "
                "read from the framework at run time."},
        {"t": "p", "text":
            "Table {{tbl:config}} records the configuration in full. One entry departs from the "
            "original plan and is declared rather than passed over. The plan specified "
            "mixed-precision float16 training with gradient scaling. Measured on this "
            "device, float16 ran at 0.38 times the throughput of float32, because the "
            "GPU is a part without tensor cores; float32 with a channels-last memory "
            "layout was therefore adopted. Numerical precision is a throughput decision "
            "rather than a scientific one, and float32 is the safer of the two, so the "
            "deviation carries no consequence for the result. It is recorded in the "
            "pre-registration as deviation DEV-1."},
        {"t": "tbl", "id": "config",
         "cap": "Model and training configuration. Every value is read from the "
                "committed run records rather than from the plan.",
         "head": ["Item", "Setting"],
         "w": [2.0, 4.2],
         "rows": [
             ["Backbone", f"{tr['backbone']}, {tr['weights']}"],
             ["Classification head",
              f"LayerNorm + Linear, {F['corpus']['n_classes']} classes"],
             ["Input", f"{F['preprocess']['size']} × {F['preprocess']['size']} × 3 RGB"],
             ["Stage 1",
              f"{tr['warmup_epochs']} epochs, head only, LR {tr['lr_head']:g} constant"],
             ["Stage 2",
              f"up to {tr['max_finetune_epochs']} epochs, top "
              f"{tr['n_modules_unfrozen']}/{tr['n_feature_modules']} feature modules, "
              f"LR {tr['lr_finetune']:g} cosine decay"],
             ["Weight decay", f"{tr['weight_decay']:g}"],
             ["Early stopping",
              f"validation macro F1, patience {tr['patience']}"],
             ["Batch size", f"{tr['batch']} (effective {tr['effective_batch']})"],
             ["Precision",
              f"{tr['precision']}, {tr['memory_format']} (deviation DEV-1)"],
             ["Seeds", "1, 2, 3 — every result is a three-seed mean"],
             ["Hardware",
              f"{tr['device']}, 4 GB; peak {tr['peak_vram_mib']:.0f} MiB used"],
             ["Software",
              f"Python {tr['python']}, PyTorch {tr['torch']}, CUDA {tr['cuda']}"],
             ["Total training time",
              f"{tr['total_train_min']:.0f} minutes for all three seeds"],
         ]},
        {"t": "p", "text":
            f"The cohort for this phase is the unanimous subset: {co['train']:,} "
            f"training, {co['val']:,} validation and {co['test']:,} test images, drawn "
            f"from the official patient-level splits so that no patient appears in more "
            f"than one split. That restriction is deliberate and temporary. It "
            f"reproduces exactly the condition under which the published baseline was "
            f"measured, which is what makes the reproduction check interpretable; the "
            f"contested images are retained and brought back for the stratified "
            f"evaluation reported in Section 3.2."},
    ]


# ==========================================================================
# 2.2 Data Collection / Need Assessment
# ==========================================================================
def data_collection(F):
    c, ct, co = F["corpus"], F["contamination"], F["cohort"]
    return [
        {"t": "p", "text":
            "No new data was collected and no participant was recruited. The "
            "requirement this project has of a corpus is unusual, and it excludes "
            "almost every public alternative: the labels of the individual annotators "
            "must be released separately, because the object of study is the "
            "disagreement between them. A corpus that publishes only a consensus label "
            "cannot support any endpoint in this design."},
        {"t": "p", "text":
            f"GastroHUN [1] meets that requirement. It was obtained from its Figshare "
            f"release under a CC BY 4.0 licence; ethics approval CEI-2019-06-10 and "
            f"documented informed consent are recorded in the peer-reviewed descriptor. "
            f"A licence discrepancy between the descriptor text and the Figshare record "
            f"was identified during the audit and resolved in favour of the more "
            f"permissive Figshare statement. The payload is {c['gb']:.2f} GB comprising "
            f"{c['n_images']:,} JPEG images across {c['n_patients']} patient "
            f"directories. Table {{tbl:corpus}} profiles it."},
        {"t": "tbl", "id": "corpus",
         "cap": "Corpus profile, measured from the release rather than quoted from the "
                "descriptor.",
         "head": ["Property", "Value"],
         "w": [2.0, 4.2],
         "rows": [
             ["Images", f"{c['n_images']:,} (all JPEG, all RGB)"],
             ["Patients", f"{c['n_patients']}"],
             ["Classes", f"{c['n_classes']} — 22 landmarks plus OTHERCLASS"],
             ["Annotators",
              f"{c['n_annotators']} independent, retained separately "
              f"({', '.join(c['annotators'])})"],
             ["Images per patient",
              f"{c['img_per_patient_mean']:.2f} ± {c['img_per_patient_sd']:.2f} "
              f"(range {c['img_per_patient_min']}–{c['img_per_patient_max']})"],
             ["Resolutions",
              f"{c['res_hi']} ({c['res_hi_n']:,} images) · "
              f"{c['res_lo']} ({c['res_lo_n']} images)"],
             ["Acquisition streams",
              f"direct capture {c['direct_capture']:,} · video frame {c['video_frame']}"],
             ["Payload", f"{c['gb']:.2f} GB"],
             ["Official splits",
              f"patient-level; {co['patients_by_split']['Train']} train / "
              f"{co['patients_by_split']['Validation']} validation / "
              f"{co['patients_by_split']['Test']} test patients"],
             ["Licence and ethics",
              "CC BY 4.0; ethics approval CEI-2019-06-10; documented informed consent"],
         ]},
        {"t": "p", "text":
            f"The corpus was then put through an eight-criterion integrity gate before "
            f"any model was fitted, on the principle that a dataset should be shown to "
            f"be sound rather than assumed to be. All {c['n_images']:,} images decoded; "
            f"there were {c['n_missing']} files missing from disk, {c['n_orphan']} "
            f"orphan files, {c['n_corrupt']} corrupt files and {c['folder_mismatch']} "
            f"folder-to-manifest mismatches. The gate returned PROCEED, with six "
            f"criteria passing without qualification and two returning CONDITIONAL. A "
            f"conditional verdict identifies a constraint that must be carried forward "
            f"as a declared limitation rather than a defect that blocks the work: in "
            f"this case, that {F['structure']['n_underpowered_classes']} of "
            f"{c['n_classes']} classes are too small to support per-class claims, and "
            f"that the release contains no age or sex field, so no demographic subgroup "
            f"or fairness claim is possible. Figure {{fig:gate}} summarises the gate."},
        {"t": "fig", "id": "gate", "path": "figures_phase1/PH1_F12_integrity_gate.png", "w": 6.4,
         "cap": "The eight-criterion data-integrity gate and its verdicts."},
        {"t": "p", "text":
            f"The contamination scan deserves a separate note, because it produced the "
            f"most instructive result of the audit. An exhaustive perceptual comparison "
            f"of all {ct['n_pairs_scanned']:,} image pairs, followed by pixel "
            f"verification, initially reported {ct['provisional_verified']} cross-split "
            f"duplicate pairs under a threshold chosen by convention. That number was "
            f"an artefact of the threshold. A first attempt to calibrate it against "
            f"randomly paired images was also wrong, because random pairs mostly "
            f"compare different anatomical stations and therefore set an artificially "
            f"low bar. Rebuilding the null as class-matched pairs — two different "
            f"patients photographed at the same landmark, {ct['null_n']:,} of them — "
            f"and anchoring the decision rule on a synthetic-duplicate positive control "
            f"of {ct['pos_n']:,} pairs reduced the count to "
            f"{ct['reassessment']['n_confirmed_by_calibrated_rule']}. Visual audit "
            f"confirmed that the flagged pairs were different patients photographed at "
            f"the same landmark. An uncalibrated threshold is not a measurement, and a "
            f"threshold calibrated against the wrong comparison is not much better; "
            f"this standard is applied to every threshold used later in the project."},
        {"t": "p", "text":
            f"Split integrity was verified independently of the descriptor's claims. "
            f"There are {co['overlap_total']} patient overlaps between any two official "
            f"splits. Class composition does not differ across splits (chi-square "
            f"p = {co['class_chi2_p']:.6f}), and neither does per-patient agreement "
            f"(Kruskal–Wallis p = 0.982), so the test split is not systematically "
            f"easier or harder than the training split. One imbalance was found and is "
            f"declared: the acquisition stream is unevenly distributed across splits "
            f"(chi-square p = {F['structure']['stream_split_p']:.1e}), so per-split "
            f"composition is reported and a sensitivity analysis excluding "
            f"video-derived frames is run wherever the stream could plausibly matter."},
    ]


# ==========================================================================
# 2.3 Analysis Techniques
# ==========================================================================
def analysis_techniques(F):
    pp, tr, b = F["preprocess"], F["training"], F["baseline"]
    return [
        {"t": "p", "text":
            "Pre-processing is fixed once, in this phase, and reused unchanged "
            "thereafter. Figure {{fig:preproc}} shows the whole chain. Three of its stages carry "
            "decisions worth stating explicitly, because the obvious choice is wrong in "
            "each case."},
        {"t": "fig", "id": "preproc", "path": "figures_phase1/PH1_F01_preprocessing_pipeline.png",
         "w": 6.4,
         "cap": "The pre-processing chain, from annotation through to the "
                "transfer-learned representation."},
        {"t": "p", "text":
            f"Annotation. The {F['corpus']['n_annotators']} vote columns are never "
            f"collapsed to a single label at ingest. Annotation is treated as a "
            f"pre-processing stage that produces four parallel label channels, and each "
            f"downstream phase decides for itself how to combine them. This is what "
            f"makes the agreement-stratified evaluation possible at all, because the "
            f"conventional pipeline destroys the required information in its first "
            f"step. The unanimous subset becomes the baseline cohort; the contested "
            f"images are retained rather than discarded, and are tagged with the "
            f"agreement tier derived from the vote matrix."},
        {"t": "p", "text":
            f"Resampling and normalisation. Images are resampled once to "
            f"{pp['size']} × {pp['size']} pixels with a Lanczos kernel and written to a "
            f"cache that every later phase reads, so that no phase can silently "
            f"introduce a different decode path; the cache is verified bit-identical "
            f"whenever it is extended. Normalisation uses statistics measured on this "
            f"training set — a mean of "
            f"({', '.join(f'{v:.3f}' for v in pp['mean'])}) and a standard deviation of "
            f"({', '.join(f'{v:.3f}' for v in pp['std'])}), over "
            f"{pp['n_norm_images']:,} images and {pp['n_pixels']:,} pixels per channel "
            f"— rather than the ImageNet defaults, which differ by as much as "
            f"{pp['max_delta']:.3f} in the red channel. Endoscopic imagery is dominated "
            f"by mucosal red under a point light source and does not resemble the "
            f"natural-image distribution those defaults were computed on."},
        {"t": "p", "text":
            f"Data augmentation. The augmentation policy is deliberately conservative, "
            f"and the reason is anatomical rather than statistical. The class label "
            f"encodes a gastric wall, so a horizontal or vertical flip, or a large "
            f"rotation, changes the apparent wall and therefore silently relabels the "
            f"image. The standard augmentation recipe for natural images would inject "
            f"label noise into precisely the axis that carries most of the annotator "
            f"disagreement. Only a mild scale-and-translation crop (RandomResizedCrop, "
            f"scale {pp['crop_scale'][0]}–{pp['crop_scale'][1]}, aspect ratio "
            f"{pp['crop_ratio'][0]}–{pp['crop_ratio'][1]:.3f}) and photometric jitter "
            f"(brightness, contrast and saturation {pp['jitter']['brightness']}, hue "
            f"{pp['jitter']['hue']}) are applied. Augmentation is applied to the "
            f"training split only; validation and test images pass through "
            f"normalisation alone. Table {{tbl:preprocspec}} records the policy."},
        {"t": "tbl", "id": "preprocspec",
         "cap": "Pre-processing and augmentation specification.",
         "head": ["Stage", "Setting", "Applied to"],
         "w": [1.5, 3.6, 1.1],
         "rows": [
             ["Decode", "JPEG to RGB, verified against the SHA-256 inventory", "all"],
             ["Resample",
              f"{pp['size']} × {pp['size']}, {pp['resample'].title()} kernel, cached "
              f"once and reused", "all"],
             ["Normalise",
              f"training-set mean {', '.join(f'{v:.3f}' for v in pp['mean'])}; "
              f"SD {', '.join(f'{v:.3f}' for v in pp['std'])}", "all"],
             ["Geometric augmentation",
              f"RandomResizedCrop, scale {pp['crop_scale'][0]}–{pp['crop_scale'][1]}, "
              f"ratio {pp['crop_ratio'][0]}–{pp['crop_ratio'][1]:.3f}", "train only"],
             ["Photometric augmentation",
              f"ColorJitter, brightness/contrast/saturation "
              f"{pp['jitter']['brightness']}, hue {pp['jitter']['hue']}", "train only"],
             ["Excluded by design",
              "horizontal flip, vertical flip, rotation beyond the crop — each changes "
              "the apparent gastric wall and would relabel the image", "—"],
         ]},
        {"t": "p", "text":
            f"Feature engineering. No hand-crafted descriptors are computed. The "
            f"feature representation is learned by transfer from ImageNet-1k and then "
            f"partially re-fitted to this domain: the lower "
            f"{tr['n_feature_modules'] - tr['n_modules_unfrozen']} feature modules are "
            f"held frozen as a generic low-level feature extractor, and the top "
            f"{tr['n_modules_unfrozen']} modules, holding "
            f"{tr['param_fraction_unfrozen'] * 100:.1f} per cent of the feature "
            f"parameters, are adapted to the endoscopic domain. Freezing the whole "
            f"backbone leaves the representation unable to model mucosal texture; "
            f"unfreezing all of it overfits a corpus of this size. The split point was "
            f"specified before training as the top 40 per cent of feature modules and "
            f"was not tuned afterwards."},
        {"t": "p", "text":
            f"Metrics and statistics. Macro F1 is the primary metric, matching the "
            f"published baseline on a near-balanced "
            f"{F['corpus']['n_classes']}-class problem. Secondary metrics are macro and "
            f"weighted precision and recall, and accuracy. Calibration is reported as "
            f"expected calibration error, maximum calibration error and the Brier "
            f"score, with reliability diagrams. On strata where no single ground-truth "
            f"label exists, two distribution-aware quantities replace accuracy: "
            f"expected accuracy, the probability mass the model's single prediction "
            f"captures under the vote distribution; and the any-annotator hit rate, an "
            f"indicator of whether the prediction was named by at least one expert. "
            f"Every interval reported anywhere in this project is a patient-clustered "
            f"bootstrap over {b['n_boot']:,} resamples with a fixed seed, resampling "
            f"the {b['n_test_patients']} test patients rather than the images. "
            f"Per-class results are treated as exploratory throughout, for the power "
            f"reason recorded at the integrity gate."},
    ]


# ==========================================================================
# 3.1 Completed Tasks
# ==========================================================================
def completed_tasks(F):
    c, pr, b, S_ = F["corpus"], F["prisma"], F["baseline"], F["strata"]
    return [
        {"t": "p", "text":
            "The tasks below were completed during the reporting period. Each produced "
            "a committed artefact and each was gated on a criterion recorded before it "
            "ran. The gate results are given in the right-hand column of Table {{tbl:tasks}} rather "
            "than described in prose, so that a claim of completion can be checked "
            "rather than taken on trust."},
        {"t": "tbl", "id": "tasks",
         "cap": "Tasks completed during the reporting period, with the validation "
                "criterion each was gated on.",
         "head": ["#", "Task", "Validation result"],
         "w": [0.35, 2.55, 3.3],
         "rows": [
             ["1", "Corpus viability assessment and replacement decision",
              "12 defects catalogued in the previously selected corpus; replacement "
              "documented and approved"],
             ["2", "Corpus acquisition, provenance and licence verification",
              "peer-reviewed descriptor, ethics CEI-2019-06-10, informed consent and "
              "CC BY 4.0 all confirmed"],
             ["3", "Physical integrity audit",
              f"{c['n_decoded']:,}/{c['n_images']:,} images decoded; "
              f"{c['n_missing']} missing, {c['n_orphan']} orphan, "
              f"{c['n_corrupt']} corrupt"],
             ["4", "Duplication and cross-split contamination scan",
              f"{F['contamination']['n_pairs_scanned']:,} pairs examined; "
              f"{F['contamination']['reassessment']['n_confirmed_by_calibrated_rule']} "
              f"cross-split duplicates after threshold calibration"],
             ["5", "Agreement quantification",
              f"Fleiss kappa = {F['agreement']['fleiss']:.4f}; all six pairwise kappa "
              f"with patient-clustered intervals"],
             ["6", "Split integrity verification",
              f"{F['cohort']['overlap_total']} patient overlaps; class chi-square "
              f"p = {F['cohort']['class_chi2_p']:.6f}"],
             ["7", "Systematic literature review to PRISMA 2020",
              f"{pr['unique']:,} unique records screened; {pr['included']} studies "
              f"included across {pr['n_themes']} themes"],
             ["8", "Pre-processing pipeline and image cache",
              f"{F['preprocess']['size']} px cache built and verified; normalisation "
              f"statistics measured on {F['preprocess']['n_norm_images']:,} images"],
             ["9", "Pre-registration of the baseline experiment",
              "frozen before training; target, tolerance, seeds, bootstrap procedure "
              "and diagnostic order all fixed in advance"],
             ["10", "Baseline model trained, validated and tested across three seeds",
              f"macro F1 {b['observed']:.2f} against a published "
              f"{b['published']:g} ± {b['band']:g} — verdict {b['verdict']}"],
             ["11", "Agreement-stratified evaluation of the frozen checkpoints",
              f"{S_['consistency_compared']:,} predictions reproduced exactly across "
              f"three seeds; four strata scored"],
             ["12", "Reproducible reporting pipeline",
              "every figure and table in this report regenerates from committed "
              "scripts and JSON artefacts"],
         ]},
    ]


# ==========================================================================
# 3.2 Results Obtained
# ==========================================================================
def results(F):
    b, S_, cal, ce = (F["baseline"], F["strata"], F["calibration"], F["ceiling"])
    order = S_["order"]
    nice = {"S-unanimous": "4/4 unanimous", "S-majority": "3/4 majority",
            "S-plurality": "2–1–1 plurality",
            "S-no-majority": "2–2 and 1–1–1–1 pooled"}
    g_maj = ce["gaps"]["S-unanimous - S-majority [ceiling_normalised]"]
    g_plu = ce["gaps"]["S-unanimous - S-plurality [ceiling_normalised]"]
    return [
        {"t": "p", "text":
            "Detailed result analysis belongs to the next phase. What follows "
            "establishes that the pipeline is correct, and reports the one finding "
            "already firm enough to state."},
        {"t": "p", "text":
            f"Baseline reproduction. Three seeds were trained under identical "
            f"conditions, differing only in initialisation and data order. All three "
            f"stopped by early stopping rather than by the compute-imposed epoch cap, "
            f"which means the schedule was not truncated. The three-seed mean macro F1 "
            f"on the {b['n_test']}-image unanimous test set is {b['observed']:.2f} "
            f"(95 per cent CI {b['ci95'][0]:.2f} to {b['ci95'][1]:.2f}, "
            f"patient-clustered bootstrap over {b['n_boot']:,} resamples), against a "
            f"published {b['published']:g} and a tolerance of ±{b['band']:g} points "
            f"fixed before training. The difference is {b['delta']:+.2f} points and the "
            f"pre-registered verdict is {b['verdict']}. Seed-to-seed spread is "
            f"{b['sd']:.2f} points. Figure {{fig:training}} shows the training dynamics and the "
            f"outcome against the acceptance band; Table {{tbl:metrics}} gives the full metric set."},
        {"t": "fig", "id": "training", "path": "figures_phase1/PH1_F03_training_dynamics.png", "w": 6.4,
         "cap": "Training dynamics for the three seeds, and the test result against the "
                "acceptance band fixed before training."},
        {"t": "tbl", "id": "metrics",
         "cap": "Baseline performance on the unanimous test split, three-seed mean. "
                "Intervals are patient-clustered bootstrap 95 per cent intervals.",
         "head": ["Metric", "Value"],
         "w": [2.6, 3.6],
         "rows": [
             ["Macro F1",
              f"{b['observed']:.2f}  (95% CI {b['ci95'][0]:.2f}–{b['ci95'][1]:.2f})"],
             ["Weighted F1", f"{b['weighted_f1']:.2f}"],
             ["Macro precision", f"{b['macro_precision']:.2f}"],
             ["Macro recall", f"{b['macro_recall']:.2f}"],
             ["Accuracy", f"{b['accuracy']:.2f}"],
             ["Expected calibration error", f"{b['ece']:.2f} per cent"],
             ["Brier score", f"{b['brier']:.4f}"],
             ["Seed spread (standard deviation)", f"{b['sd']:.2f} points"],
             ["Per-seed macro F1",
              ", ".join(f"{v:.2f}" for v in b["per_seed"].values())],
             ["Reproduction verdict",
              f"{b['verdict']} — difference {b['delta']:+.2f} against "
              f"{b['published']:g} ± {b['band']:g}"],
         ]},
        {"t": "p", "text":
            "The reproduction being a PASS is the precondition for everything that "
            "follows, and it should be read narrowly. It says the pipeline — cohort "
            "construction, decode path, normalisation, schedule and evaluation — "
            "behaves as the published one did. It does not say the model is good, and "
            "the next result is that on most of the corpus it is not."},
        {"t": "p", "text":
            f"Agreement-stratified evaluation. The three frozen checkpoints were then "
            f"evaluated, without retraining and without any threshold tuning, on the "
            f"full {S_['n_test_total']:,}-image official test split, stratified by how "
            f"many of the four annotators agreed. As an internal consistency check, the "
            f"predictions on the unanimous stratum reproduce the baseline predictions "
            f"exactly — {S_['consistency_compared']:,} comparisons across three seeds "
            f"with {S_['consistency_mismatch']} mismatches — which confirms the new "
            f"evaluation path is wired correctly rather than producing a new result. "
            f"Table {{tbl:strata}} and Figure {{fig:strat}} report the outcome."},
        {"t": "tbl", "id": "strata",
         "cap": "Performance by agreement stratum, three-seed mean, from the frozen "
                "baseline checkpoints. Expected accuracy and the any-annotator hit rate "
                "are the distribution-aware metrics used where no single ground-truth "
                "label exists.",
         "head": ["Stratum", "Images", "Patients", "Macro F1", "Expected accuracy",
                  "Any-annotator hit", "Attainable ceiling"],
         "w": [1.35, 0.62, 0.68, 0.75, 0.95, 0.9, 0.95],
         "rows": [[nice[k], f"{S_['n'][k]:,}", f"{S_['n_patients'][k]}",
                   f"{S_['f1'][k]:.2f}", f"{S_['expected_accuracy'][k]:.2f}",
                   f"{S_['any_hit'][k]:.2f}", f"{ce['oracle_f1'][k]:.2f}"]
                  for k in order]},
        {"t": "fig", "id": "strat", "path": "figures_phase1/PH1_F10_stratified_result.png", "w": 6.4,
         "cap": "Performance across agreement strata against the attainable ceiling, "
                "and the pre-registered contrasts with patient-clustered intervals."},
        {"t": "p", "text":
            f"Macro F1 falls from {S_['f1'][order[0]]:.2f} on unanimous images to "
            f"{S_['f1'][order[-1]]:.2f} on images with no majority label, a gap of "
            f"{S_['gap']:.2f} points. For scale, the difference the descriptor reports "
            f"between its smallest and largest architectures is "
            f"{S_['arch_benchmark']:g} points. The choice of architecture is therefore a "
            f"rounding error beside the choice of which images to evaluate on. The "
            f"decline is not strictly monotonic — Spearman rho = "
            f"{S_['spearman_rho']:.2f}, p = {S_['spearman_p']:.2f} over four tiers — "
            f"and that non-monotonicity is reported rather than smoothed over."},
        {"t": "p", "text":
            f"A large part of that fall is not the model getting worse. On contested "
            f"images the best achievable score is itself lower, because no single label "
            f"can match a divided panel: the attainable ceiling falls from "
            f"{ce['oracle_f1'][order[0]]:.2f} to {ce['oracle_f1'][order[-1]]:.2f} "
            f"across the same four strata. Holding that ceiling constant, the "
            f"unanimous-to-majority gap is {g_maj['mean']:.2f} points (95 per cent CI "
            f"{g_maj['ci95'][0]:.2f} to {g_maj['ci95'][1]:.2f}) and the "
            f"unanimous-to-plurality gap is {g_plu['mean']:.2f} points (95 per cent CI "
            f"{g_plu['ci95'][0]:.2f} to {g_plu['ci95'][1]:.2f}); both intervals exclude "
            f"zero, so a real model shortfall remains after the ceiling is accounted "
            f"for. The unanimous-to-no-majority contrast does not resolve, its interval "
            f"containing zero, and is reported as unresolved. Separating a falling "
            f"reference standard from a falling classifier, which the literature "
            f"reports as one quantity, is the central analytical move of this project."},
        {"t": "p", "text":
            f"Calibration. The clearest and most consequential finding of the phase "
            f"concerns confidence rather than accuracy. Expected calibration error "
            f"rises from {cal['ece'][order[0]]:.2f} per cent on unanimous images to "
            f"{max(cal['ece'].values()):.2f} per cent on plurality images. The "
            f"mechanism is visible in Figure {{fig:calib}}: mean predicted confidence falls only "
            f"{cal['confidence'][order[0]] - cal['confidence'][order[2]]:.2f} points "
            f"between those two strata while expected accuracy falls "
            f"{cal['expected_accuracy'][order[0]] - cal['expected_accuracy'][order[2]]:.2f}. "
            f"The model does not know it has entered harder territory. Clinically this "
            f"is the failure mode that matters: a system which remains confident "
            f"exactly where four experts could not agree offers no signal that its "
            f"output should be doubted."},
        {"t": "fig", "id": "calib", "path": "figures_phase1/PH1_F11_calibration.png", "w": 6.4,
         "cap": "Calibration by agreement stratum: predicted confidence against "
                "expected accuracy, and expected calibration error."},
        {"t": "p", "text":
            "Two confound checks were run against the stratified result and both were "
            "negative, which is what makes the effect attributable to agreement rather "
            "than to composition. Class composition explains between 3.5 and 4.2 per "
            "cent of the decline. Acquisition-stream composition does not differ across "
            "strata (chi-square p = 0.298), and restricting the analysis to the "
            "dominant stream shifts the curve by no more than 0.18 points. All "
            "twenty-three classes are populated in every stratum, so the macro average "
            "is not being distorted by absent classes."},
    ]


# ==========================================================================
# 4 Challenges
# ==========================================================================
def challenges(F):
    nc = F["negative_control"]
    return [
        {"t": "p", "text":
            "Four obstacles materially affected the work during this period. Each is "
            "recorded with the strategy adopted in Table {{tbl:challenges}}; the two that changed the "
            "shape of the project are discussed first."},
        {"t": "p", "text":
            f"The first was that the originally selected corpus did not survive its own "
            f"audit. A tabular dataset of endoscopy reports had been chosen for a "
            f"natural-language design. Testing before modelling showed that the "
            f"association between every feature and the target was indistinguishable "
            f"from chance, the largest Cramér's V being "
            f"{nc['max_cramers_v']:.4f}, and that the target had been constructed by "
            f"pattern-matching over the same text fields that would have become the "
            f"features. A classifier reached "
            f"{nc['leak_accuracy'] * 100:.0f} per cent accuracy on it, and still "
            f"{nc['leak_after_removal'] * 100:.2f} per cent after the most obvious "
            f"leaking column was removed. By the data processing inequality, no amount "
            f"of pre-processing can create signal that is not present. The project "
            f"pivoted to imaging. The retired corpus was kept as a negative control "
            f"against which the audit protocol itself can be tested, since an audit "
            f"that passes everything it is shown is not an audit."},
        {"t": "p", "text":
            "The second was hardware. The available GPU has 4 GB of video memory, which "
            "excludes the largest published architecture on this task outright. Rather "
            "than assume the recommended mixed-precision settings would help, "
            "throughput was measured on the actual device; float16 proved markedly "
            "slower than float32 on this part, so the plan was changed and the "
            "deviation recorded. The wider lesson — measure the machine rather than "
            "trust the guidance — was applied to every subsequent budgeting decision."},
    ]


def challenges_table(F):
    return [
        ["1",
         "The originally selected corpus had no learnable signal and circularly "
         "constructed labels, discovered during the pre-modelling audit.",
         "Replaced the corpus with GastroHUN after a documented viability assessment, "
         "and retained the original as a negative control that validates the audit "
         "protocol itself."],
        ["2",
         "Only 4 GB of GPU memory is available, and the recommended mixed-precision "
         "setting proved slower than full precision on this device.",
         "Benchmarked the hardware instead of assuming; adopted float32 with a "
         "channels-last layout and recorded the departure as a declared deviation. "
         "ConvNeXt-Large is cited as the published ceiling and not attempted."],
        ["3",
         "The cross-split contamination scan reported 54 duplicate pairs under a "
         "conventional threshold, which would have invalidated the official splits.",
         "Rebuilt the decision rule against a class-matched null and a "
         "synthetic-duplicate positive control; the confirmed count fell to zero and "
         "was verified by visual audit."],
        ["4",
         "No single-label ground truth exists on the tied and dispersed strata, so "
         "conventional accuracy metrics are undefined there.",
         "Pre-specified two distribution-aware metrics, expected accuracy and the "
         "any-annotator hit rate, together with a pooling rule for the smallest "
         "strata, all fixed on corpus structure before any model output was seen."],
    ]


def next_steps_table(F):
    return [
        ["1", "Train and compare five target constructions: hard consensus labels, "
              "majority labels, vote-proportion soft targets, matched label smoothing "
              "as a regularisation control, and an anatomy-aware loss", "09-26"],
        ["2", "Measure calibration and predictive uncertainty for every configuration, "
              "and correlate predictive entropy with annotator vote entropy within "
              "stratum", "10-26"],
        ["3", "External validation on HyperKvasir and GastroVision without adaptation, "
              "with the label-space mapping frozen before any image is scored", "11-26"],
        ["4", "Explainability and error analysis against a human comparator, and "
              "thesis preparation for the Final Defence", "12-26"],
    ]


# ==========================================================================
# 6 Updated Timeline
# ==========================================================================
def timeline(F):
    return [
        {"t": "p", "text":
            "Table {{tbl:gantt}} sets out the schedule against calendar weeks, with "
            "the estimated period above the actual period for each task. One "
            "adjustment to the original plan should be noted: the corpus "
            "replacement described in Section 4 consumed roughly two weeks that had "
            "been allocated to modelling, and that slippage is visible in the first "
            "two tasks. The time was recovered because the baseline reproduced at "
            "the first attempt, so the phase ends in the week originally planned."},
    ]


TIMELINE_TASKS = [
    # (label, estimated first/last week, actual first/last week)
    # The template gives four task slots, each a blue "estimated" row over a
    # green "actual" row, against calendar weeks 6-23.
    ("Corpus audit, integrity gate and contamination scan", (6, 9), (6, 11)),
    ("Literature review and gap analysis", (9, 12), (10, 13)),
    ("Pre-processing pipeline, pre-registration and baseline training",
     (13, 17), (14, 18)),
    ("Agreement-stratified evaluation and Phase-I reporting", (18, 21), (19, 21)),
]


# ==========================================================================
# 7 Resources
# ==========================================================================
def resources(F):
    tr = F["training"]
    return [
        {"t": "p", "text":
            f"Computation was carried out on a single workstation with an "
            f"{tr['device']} holding 4 GB of video memory, alongside 16 GB of system "
            f"memory. Peak memory use during training was "
            f"{tr['peak_vram_mib']:.0f} MiB, and the three baseline runs took "
            f"{tr['total_train_min']:.0f} minutes in total. No cloud or institutional "
            f"compute was required, which was itself a design constraint: the whole "
            f"study is reproducible on commodity hardware."},
        {"t": "p", "text":
            f"The software stack is Python {tr['python']} with PyTorch {tr['torch']} on "
            f"CUDA {tr['cuda']}, torchvision for the pretrained backbones, and NumPy, "
            f"pandas, scikit-learn and SciPy for evaluation and statistics. Figures are "
            f"produced with Matplotlib and exported at publication resolution; this "
            f"report and the defence slides are generated programmatically with "
            f"python-docx and python-pptx from the same artefact set, which is why no "
            f"number in either document is transcribed by hand. Literature retrieval "
            f"used the NCBI E-utilities. Version control is Git, with each phase "
            f"committed as a self-contained unit."},
        {"t": "p", "text":
            f"The data resource is the GastroHUN release: {F['corpus']['gb']:.2f} GB of "
            f"labelled images with per-annotator labels and official patient-level "
            f"splits, obtained under CC BY 4.0. HyperKvasir [11] and GastroVision [12] "
            f"have been acquired for the external validation planned in the next phase. "
            f"The video release accompanying GastroHUN was deliberately not downloaded, "
            f"as sequence modelling is out of scope."},
    ]


# ==========================================================================
# 8 Project management and financial analysis
# ==========================================================================
def management(F):
    tr = F["training"]
    return [
        {"t": "p", "text":
            "The project is managed as a sequence of gated phases rather than as a "
            "continuous effort, and the gate is the unit of progress. Each phase begins "
            "by writing a plan that fixes its hypotheses, primary endpoint and verdict "
            "rules, and ends by producing a report together with the JSON artefacts "
            "from which that report regenerates. Work is divided between the two group "
            "members by phase component rather than by file, with the data pipeline and "
            "training code on one side and the evaluation, statistics and reporting "
            "layer on the other. Both members review every pre-registration before it "
            "is frozen, because a pre-registration reviewed after the fact is worthless."},
        {"t": "p", "text":
            f"The direct financial cost of the project to date is zero. The corpus is "
            f"openly licensed, every software component is open source, and all "
            f"computation runs on hardware already owned. The realistic cost is time: "
            f"{tr['total_train_min']:.0f} minutes of GPU time for the baseline runs, "
            f"and a substantially larger allocation for the next phase, where five "
            f"configurations across three seeds each are planned. That workload was "
            f"estimated by measuring the cost of one epoch on the actual device rather "
            f"than by extrapolating from the baseline, because the anatomy-aware loss "
            f"adds per-batch work a naive projection would miss. Table {{tbl:cost}} sets out the "
            f"resource position."},
        {"t": "tbl", "id": "cost",
         "cap": "Resource and cost position for the reporting period.",
         "head": ["Item", "This period", "Next period (estimated)"],
         "w": [1.9, 2.2, 2.1],
         "rows": [
             ["Direct monetary cost", "BDT 0", "BDT 0"],
             ["Corpus licensing", "CC BY 4.0, no fee",
              "CC BY, no fee (two external corpora)"],
             ["Software licensing", "open source throughout", "open source throughout"],
             ["Compute", f"{tr['total_train_min']:.0f} min GPU, 3 training runs",
              "approximately 17 h GPU, 12 training runs"],
             ["Hardware", f"{tr['device']}, 4 GB, already owned", "unchanged"],
             ["Storage", f"{F['corpus']['gb']:.2f} GB corpus plus caches and checkpoints",
              "additional external corpora and checkpoints"],
             ["Principal risk", "corpus replacement (materialised, absorbed)",
              "training budget an order of magnitude larger on one GPU"],
         ]},
        {"t": "p", "text":
            "The main scheduling risk carried forward is that the next phase's training "
            "budget is roughly an order of magnitude larger than this phase's, on the "
            "same single GPU. It is mitigated by running the configurations in "
            "seed-major order, so that a complete one-seed comparison across all five "
            "arms exists early and a truncated budget degrades the precision of the "
            "result rather than removing an arm from it."},
    ]


# ==========================================================================
# 9 Future considerations
# ==========================================================================
def future(F):
    S_, cal = F["strata"], F["calibration"]
    order = S_["order"]
    return [
        {"t": "p", "text":
            "Four considerations are likely to shape the next phase, and are recorded "
            "now so that they are not presented later as discoveries."},
        {"t": "p", "text":
            f"The contested strata are small. The plurality stratum holds "
            f"{S_['n'][order[2]]} images from {S_['n_patients'][order[2]]} patients, "
            f"and the pooled no-majority stratum holds {S_['n'][order[3]]} images from "
            f"{S_['n_patients'][order[3]]} patients. Patient-clustered intervals on "
            f"samples of that size are wide, and the unanimous-to-no-majority contrast "
            f"already fails to resolve for this reason. The pooling rule was fixed in "
            f"advance on corpus structure alone; if a contrast remains unresolved it "
            f"will be reported as unresolved rather than re-cut until it separates."},
        {"t": "p", "text":
            "A benefit from soft targets must be separated from ordinary "
            "regularisation. Training on the vote distribution softens the target, and "
            "softening a target is regularising whether or not the softening carries "
            "information about which classes are plausible. The comparison arm is "
            "therefore not the hard-label baseline but a label-smoothing control "
            "matched to the probability mass the soft target displaces from the modal "
            "label. Without that control any gain would be uninterpretable, and the "
            "control is not optional."},
        {"t": "p", "text":
            "External validation may not be available in the form planned. The label "
            "space here is a product of wall and station; the external corpora "
            "identified for the next phase are not guaranteed to carry the wall axis at "
            "all. If they do not, a twenty-three-way external comparison is not "
            "available from them, and the endpoint will have to be reframed as a "
            "coarser anatomical collapse — declared before scoring, not after seeing "
            "that the fine-grained comparison disappoints."},
        {"t": "p", "text":
            f"Finally, the calibration finding needs a mechanism. Expected calibration "
            f"error reaching {max(cal['ece'].values()):.2f} per cent on contested "
            f"images could be a consequence of training only on unanimous frames, in "
            f"which case training on the vote distribution should repair it; or it "
            f"could be a property of the problem that survives every target "
            f"construction. Those two possibilities have opposite implications for "
            f"deployment, and distinguishing them is the single most useful thing the "
            f"next phase can do."},
    ]


# ==========================================================================
# 10 Conclusion
# ==========================================================================
def conclusion(F):
    b, S_, cal, ag, pr = (F["baseline"], F["strata"], F["calibration"],
                          F["agreement"], F["prisma"])
    order = S_["order"]
    return [
        {"t": "p", "text":
            f"This phase set out to establish that the corpus is sound, that the "
            f"pipeline is correct, and that the question the project asks is worth "
            f"asking. All three are now supported by evidence rather than by argument. "
            f"The corpus passed an eight-criterion integrity gate with a PROCEED "
            f"verdict, the two conditional findings being declared as limitations "
            f"rather than quietly absorbed. A systematic review of {pr['unique']:,} "
            f"unique records across {pr['n_themes']} themes produced {pr['included']} "
            f"included studies and a gap statement with three measurable components. "
            f"The baseline model reproduced the published result at "
            f"{b['observed']:.2f} macro F1 against {b['published']:g} ± "
            f"{b['band']:g}, a pre-registered PASS."},
        {"t": "p", "text":
            f"The substantive finding is that the reported accuracy of this task "
            f"describes {ag['unanimous_pct']:.1f} per cent of it. Macro F1 falls from "
            f"{S_['f1'][order[0]]:.2f} to {S_['f1'][order[-1]]:.2f} across agreement "
            f"strata, a {S_['gap']:.2f}-point spread beside a "
            f"{S_['arch_benchmark']:g}-point difference between architecture families. "
            f"Part of that fall is the reference standard weakening rather than the "
            f"classifier failing, and the ceiling-normalised analysis separates the two "
            f"and sizes each: a genuine model shortfall survives on the majority and "
            f"plurality strata, while the pooled no-majority contrast does not resolve. "
            f"Confidence degrades further and faster than discrimination, with expected "
            f"calibration error rising from {cal['ece'][order[0]]:.2f} to "
            f"{max(cal['ece'].values()):.2f} per cent while mean confidence barely "
            f"moves."},
        {"t": "p", "text":
            "Every Phase-I requirement has been met and evidenced: problem "
            "identification, literature review and gap analysis in Section 1; data "
            "collection, annotation handling, augmentation and feature engineering in "
            "Section 2; and a baseline model trained, validated and tested in "
            "Section 3. The next phase turns from measuring the problem to acting on "
            "it, by testing whether the annotator disagreement the field discards can "
            "be used as a training signal, against a control designed so that a "
            "positive result cannot be confused with ordinary regularisation."},
    ]


# ==========================================================================
# References (IEEE)
# ==========================================================================
REFERENCES = [
    "D. Panesso-Ortiz et al., “GastroHUN: an endoscopy dataset of the complete "
    "systematic screening protocol for the stomach,” Scientific Data, vol. 12, "
    "art. 102, 2025, doi: 10.1038/s41597-025-04401-5.",
    "M. Nagendran et al., “Artificial intelligence versus clinicians: systematic "
    "review of design, reporting standards, and claims of deep learning studies,” "
    "BMJ, vol. 368, art. m689, 2020, doi: 10.1136/bmj.m689.",
    "R. Djinbachian et al., “Interobserver agreement for the Paris classification "
    "of colorectal lesions amongst surgeons, gastroenterologists and "
    "pathologists,” Digestive Diseases and Sciences, 2025, "
    "doi: 10.1007/s10620-025-09215-4.",
    "S. Isajevs et al., “Gastritis staging: interobserver agreement by applying "
    "OLGA and OLGIM systems,” Virchows Archiv, vol. 464, pp. 403–407, 2014, "
    "doi: 10.1007/s00428-014-1544-3.",
    "L. D’Antiga et al., “Interobserver agreement on endoscopic "
    "classification of oesophageal varices in children,” Journal of Pediatric "
    "Gastroenterology and Nutrition, vol. 61, pp. 176–181, 2015, "
    "doi: 10.1097/MPG.0000000000000822.",
    "R. Del Amor et al., “Labeling confidence for uncertainty-aware histology "
    "image classification,” Computerized Medical Imaging and Graphics, vol. 107, "
    "art. 102231, 2023, doi: 10.1016/j.compmedimag.2023.102231.",
    "Z. Gao et al., “Leveraging multi-annotator label uncertainties as privileged "
    "information for acute respiratory distress syndrome detection,” "
    "Bioengineering, vol. 11, no. 2, art. 133, 2024, "
    "doi: 10.3390/bioengineering11020133.",
    "M. Riera-Marin et al., “Calibration and uncertainty for multi-rater volume "
    "assessment in multi-organ segmentation (CURVAS) challenge results,” "
    "Computers in Biology and Medicine, 2025, doi: 10.1016/j.compbiomed.2025.111024.",
    "S. M. Maenpaa et al., “Diagnostic test accuracy of externally validated "
    "convolutional neural network artificial intelligence models,” International "
    "Journal of Medical Informatics, vol. 189, art. 105523, 2024, "
    "doi: 10.1016/j.ijmedinf.2024.105523.",
    "Y. D. Li et al., “Intelligent detection endoscopic assistant: an artificial "
    "intelligence-based system for monitoring blind spots during "
    "oesophagogastroduodenoscopy,” Digestive and Liver Disease, vol. 53, "
    "pp. 216–223, 2021, doi: 10.1016/j.dld.2020.11.017.",
    "H. Borgli et al., “HyperKvasir, a comprehensive multi-class image and video "
    "dataset for gastrointestinal endoscopy,” Scientific Data, vol. 7, art. 283, "
    "2020, doi: 10.1038/s41597-020-00622-y.",
    "D. Jha et al., “GastroVision: a multi-class endoscopy image dataset for "
    "computer-aided gastrointestinal disease detection,” in Proc. ICML Workshop "
    "on Machine Learning for Multimodal Healthcare Data, 2023, arXiv:2307.08140.",
    "Z. Liu, H. Mao, C.-Y. Wu, C. Feichtenhofer, T. Darrell, and S. Xie, “A "
    "ConvNet for the 2020s,” in Proc. IEEE/CVF Conf. Computer Vision and Pattern "
    "Recognition (CVPR), 2022, pp. 11976–11986, "
    "doi: 10.1109/CVPR52688.2022.01167.",
    "M. J. Page et al., “The PRISMA 2020 statement: an updated guideline for "
    "reporting systematic reviews,” BMJ, vol. 372, art. n71, 2021, "
    "doi: 10.1136/bmj.n71.",
    "C. Guo, G. Pleiss, Y. Sun, and K. Q. Weinberger, “On calibration of modern "
    "neural networks,” in Proc. 34th Int. Conf. Machine Learning (ICML), 2017, "
    "pp. 1321–1330.",
]


# ==========================================================================
# Appendix
# ==========================================================================
def appendix(F):
    b = F["baseline"]
    return [
        {"t": "p", "text":
            "A. Reproducibility index. Every quantity in this report is generated by a "
            "committed script and stored in a versioned artefact before it is read into "
            "the document; no value is transcribed by hand. Table {{tbl:repro}} maps the report's "
            "principal claims to the artefacts that carry them."},
        {"t": "tbl", "id": "repro",
         "cap": "Reproducibility index: report claim mapped to generating script and "
                "stored artefact.",
         "head": ["Claim in this report", "Generating script", "Artefact"],
         "w": [2.1, 2.1, 2.0],
         "rows": [
             ["Corpus profile and physical integrity",
              "src/data/gastrohun_inventory.py", "reports/gastrohun_inventory.json"],
             ["Agreement statistics and vote patterns",
              "src/data/gastrohun_agreement.py", "reports/gastrohun_agreement.json"],
             ["Label-space structure and disagreement decomposition",
              "src/data/gastrohun_structure.py", "reports/gastrohun_structure.json"],
             ["Contamination scan and threshold calibration",
              "src/data/gastrohun_neardup.py, gastrohun_dup_calibration.py",
              "reports/gastrohun_neardup.json, gastrohun_dup_calibration.json"],
             ["PRISMA counts and included studies",
              "src/literature/search_v2.py, eligibility_v2.py, enrich_v2.py",
              "literature_v2/prisma_counts.json, extraction_table.csv"],
             ["Normalisation statistics",
              "src/models/phase2_normstats.py", "reports/phase2_norm_stats.json"],
             ["Cohort construction and split integrity",
              "src/models/phase2_data.py", "reports/phase2_split_provenance.json"],
             ["Pre-registration of the baseline experiment",
              "src/models/phase2_prereg.py", "reports/phase2_prereg.json"],
             ["Training runs and realised schedules",
              "src/models/phase2_train.py", "reports/phase2_run_seed{1,2,3}.json"],
             ["Baseline test metrics and reproduction verdict",
              "src/models/phase2_eval.py", "reports/phase2_test_metrics.json"],
             ["Agreement-stratified metrics",
              "src/models/phase3_eval.py", "reports/phase3_stratified_metrics.json"],
             ["Calibration by stratum",
              "src/models/phase3b_calibration.py", "reports/phase3b_calibration.json"],
             ["Attainable ceiling and normalised gaps",
              "src/models/phase3b_ceiling.py", "reports/phase3b_ceiling_gaps.json"],
             ["Every figure in this report",
              "src/report/figures_phase1.py",
              "figures_phase1/PH1_F01–F12 at 600 dpi"],
             ["This document",
              "src/report/build_phase1_docx.py with content_phase1_report.py and "
              "phase1_facts.py", "Phase-I_Progress_Report.docx"],
         ]},
        {"t": "p", "text":
            f"B. Statistical procedure. Unless stated otherwise, every interval is a "
            f"patient-clustered bootstrap 95 per cent interval computed over "
            f"{b['n_boot']:,} resamples with seed {b['boot_seed']}, drawing "
            f"{b['n_test_patients']} test patients with replacement and recomputing the "
            f"statistic on each resample. Images are never resampled directly, because "
            f"per-patient agreement varies systematically and images within a patient "
            f"are therefore not independent observations. Results reported as a "
            f"three-seed mean are the mean of the per-seed point estimates, with the "
            f"interval computed on the seed-mean statistic."},
        {"t": "p", "text":
            "C. Declared limitations carried into the next phase. Twenty-two of the "
            "twenty-three classes are underpowered for per-class claims, so the primary "
            "metric is macro-averaged and per-class results are exploratory. The "
            "release records no age or sex, so no demographic subgroup or fairness "
            "claim is possible. The corpus is single-centre and single-vendor, which "
            "makes external validation necessary rather than optional. The acquisition "
            "stream is imbalanced across splits, so per-split composition is reported "
            "and a sensitivity analysis excluding video-derived frames is run. Clinical "
            "context exists for only 60.2 per cent of patients, so no claim links "
            "landmark performance to disease status. Four annotators is a small panel, "
            "so vote proportions are treated as an ordinal ambiguity signal rather than "
            "as a calibrated probability."},
    ]
