"""Phase 1, methodology, results, discussion, conclusion, references, appendix."""
from __future__ import annotations

import pandas as pd

from build_docx import (B, DARKRED, L, LA, LITDF, POW, PROV, PT, P, R,
                        bullet, callout, figure, h, para, rich, table)

THEME_LABEL = {
    "T1 Endoscopy report NLP": "Clinical NLP on endoscopy and pathology reports",
    "T2 Rule-based vs ML": "Rule-based versus machine-learning approaches",
    "T3 Weak supervision": "Weak supervision and silver-standard labels",
    "T4 Leakage & validity": "Data leakage and evaluation validity",
    "T5 Reporting standards": "Reporting standards and risk-of-bias appraisal",
}


def _cite(row) -> str:
    """Short in-text citation, APA style."""
    au = str(row["first_author"]).split(",")[0].strip()
    n = 0
    try:
        n = len(str(row["authors_full"]).split(";"))
    except Exception:
        pass
    yr = str(row["year"]).strip()
    if n >= 3:
        return f"{au} et al. ({yr})"
    if n == 2:
        second = str(row["authors_full"]).split(";")[1].split(",")[0].strip()
        return f"{au} and {second} ({yr})"
    return f"{au} ({yr})"


def sec_phase1(doc):
    h(doc, "2. Phase 1 - Literature Review and Problem Framing", 1, page_break=True)

    e, s, q = P["eligibility"], P["stages"], P["queries"]

    h(doc, "2.1 Introduction", 2)
    para(doc, "Phase 1 establishes what has already been done, identifies the genuine gap, and "
              "freezes the research questions before any model is fitted. It also serves a "
              "second and, given the Phase 0 outcome, more urgent purpose: to establish what "
              "performance is realistically attainable on authentic endoscopy text, so that "
              "the negative result obtained on the present corpus can be interpreted against a "
              "quantified external reference rather than an intuition.")

    h(doc, "2.2 Research Background", 2)
    para(doc, "Upper gastrointestinal endoscopy is the reference procedure for diagnosing "
              "peptic ulcer disease, gastritis, reflux oesophagitis, oesophageal varices and "
              "gastric neoplasia. Its output is predominantly narrative: an endoscopist "
              "dictates or types a description of the oesophagus, stomach and duodenum, "
              "records biopsy actions, and closes with a diagnostic impression and management "
              "advice. This narrative is clinically rich but computationally opaque, and the "
              "resulting inability to compute quality metrics or identify cohorts at scale "
              "without manual chart abstraction has motivated two decades of clinical natural "
              "language processing in gastroenterology.")

    h(doc, "2.3 Reproducible Search Protocol", 2)
    para(doc, f"The review follows PRISMA 2020 in structure while remaining proportionate to "
              f"Bachelor's level, as the blueprint specifies. The distinguishing feature of "
              f"this protocol is that the search was executed programmatically against the "
              f"NCBI E-utilities interface rather than through an interactive interface, so "
              f"the entire identification and screening pipeline is contained in a committed "
              f"script and can be re-executed by a third party. Six search strings were "
              f"specified in advance, one per sub-review theme, returning "
              f"{sum(v['total_hits'] for v in q.values()):,} hits in total.")

    rows = []
    for k, v in q.items():
        rows.append([k.split("_", 1)[0],
                     THEME_LABEL.get(
                         {"S1": "T1 Endoscopy report NLP",
                          "S2": "T1 Endoscopy report NLP",
                          "S3": "T2 Rule-based vs ML",
                          "S4": "T3 Weak supervision",
                          "S5": "T4 Leakage & validity",
                          "S6": "T5 Reporting standards"}[k.split("_", 1)[0]], ""),
                     f"{v['date_from']}-{v['date_to']}",
                     f"{v['total_hits']:,}", f"{v['retrieved']}"])
    table(doc, ["ID", "Sub-review theme", "Date window", "Total hits", "Retrieved"], rows,
          "Search strings executed against PubMed/MEDLINE. Full Boolean strings are reproduced "
          "verbatim in Appendix A.",
          widths=[1.3, 7.6, 2.6, 2.4, 2.1], font=8.0, align_right={3, 4},
          note=f"Executed on {P['run_date']} via the NCBI E-utilities API. Retrieval was "
               f"capped at {q['S1_endoscopy_nlp']['retmax']} relevance-ranked records per "
               f"string; this cap is a stated constraint of the protocol, not an omission.")

    para(doc, "Inclusion required a peer-reviewed English-language record reporting either a "
              "quantitative evaluation or an explicit methodological framework, and addressing "
              "clinical text processing, weak supervision, evaluation validity, or reporting "
              "standards. Exclusion criteria were image-only studies with no textual "
              "component, editorials and correspondence, records without a retrievable "
              "abstract, and preprints, which fail the peer-review requirement.")

    h(doc, "2.4 Screening, Eligibility and Study Selection", 2)
    para(doc, f"Cross-query de-duplication removed {s['duplicates_removed']} records, leaving "
              f"{s['records_after_deduplication']} unique records, of which "
              f"{s['records_metadata_retrieved']} yielded complete metadata. Title and "
              f"abstract screening excluded {s['records_excluded_at_screening']} records. The "
              f"remaining {s['records_passing_screen']} were assessed against theme-specific "
              f"eligibility criteria.")

    para(doc, "Three integrity filters were applied at the eligibility stage and are reported "
              "explicitly, because each removed records that a keyword-only procedure would "
              "have retained:")
    bullet(doc, f"Preprints ({e['records_excluded_preprint']} records) were excluded as not "
                f"peer reviewed, in accordance with the stated inclusion criterion.")
    bullet(doc, f"Homonym false positives ({e['records_excluded_homonym_false_positive']} "
                f"records) were excluded where a search term matched in an unrelated clinical "
                f"sense. The clearest instance was a narrative review of a snorkel breathing "
                f"technique in anaesthesia, retrieved by the term 'Snorkel', which in this "
                f"review denotes the weak-supervision framework.")
    bullet(doc, f"Duplicate and co-publications ({e['records_excluded_duplicate_copublication']} "
                f"records) were collapsed to a single record. Reporting guidelines are "
                f"frequently published simultaneously in several journals, and preprints "
                f"frequently reappear as journal articles.")

    para(doc, f"A further {e['records_excluded_primary_not_methodological']} records were "
              f"excluded from the leakage theme as primary model-development studies that "
              f"mentioned overfitting incidentally without constituting validity literature. "
              f"After a per-theme relevance cap - a stated pragmatic constraint appropriate to "
              f"the scale of a Bachelor's review, which set aside "
              f"{e['records_eligible_but_capped']} otherwise eligible records - "
              f"{e['records_included_from_pubmed']} studies were retained from PubMed. Six "
              f"foundational works in computer science and machine-learning methodology that "
              f"are not indexed in MEDLINE were added through the PRISMA 'other methods' arm, "
              f"giving {e['records_included_total']} included studies.")

    figure(doc, "F13_prisma_flow.png",
           "PRISMA 2020 flow diagram for the review. All counts are produced by the search and "
           "eligibility scripts rather than transcribed by hand.", width=5.9)

    table(doc, ["PRISMA stage", "Count"],
          [["Records identified in PubMed/MEDLINE (retrieved)", s["records_identified_total"]],
           ["Duplicate records removed before screening", s["duplicates_removed"]],
           ["Records screened on title and abstract", s["records_screened"]],
           ["Records excluded at screening", s["records_excluded_at_screening"]],
           ["Records assessed for eligibility", s["records_passing_screen"]],
           ["Excluded: failed theme-specific criteria", e["records_failing_theme_criteria"]],
           ["Excluded: preprint, not peer reviewed", e["records_excluded_preprint"]],
           ["Excluded: homonym false positive",
            e["records_excluded_homonym_false_positive"]],
           ["Excluded: duplicate or co-publication",
            e["records_excluded_duplicate_copublication"]],
           ["Excluded: primary study, not a methodological appraisal",
            e["records_excluded_primary_not_methodological"]],
           ["Excluded: eligible but outside the per-theme relevance cap",
            e["records_eligible_but_capped"]],
           ["Included from PubMed/MEDLINE", e["records_included_from_pubmed"]],
           ["Included through other methods (hand-searched)",
            e["records_included_other_methods"]],
           ["Total studies included", e["records_included_total"]]],
          "PRISMA stage counts.",
          widths=[11.0, 5.0], font=8.0, align_right={1})

    figure(doc, "F14_literature_distribution.png",
           "Distribution of the included studies by sub-review theme and by identification "
           "route.")
    figure(doc, "F15_publication_timeline.png",
           "Publication timeline of the included studies. The concentration after 2022 "
           "reflects the rapid recent growth of clinical natural language processing.",
           width=5.8)
    figure(doc, "F16_keyword_frequency.png",
           "Frequency of content terms across the titles of the included studies.", width=5.4)

    # ---- 2.5 sub-reviews ------------------------------------------------
    h(doc, "2.5 Clinical Natural Language Processing", 2)
    t1 = LITDF[LITDF.theme == "T1 Endoscopy report NLP"].sort_values("year")
    para(doc, f"Fourteen studies address natural language processing applied directly to "
              f"endoscopy, colonoscopy or associated pathology reports. Collectively they "
              f"establish the performance envelope against which the present study must be "
              f"read. Early work in this area was predominantly rule- and dictionary-based and "
              f"targeted colonoscopy quality metrics, particularly the adenoma detection rate, "
              f"whose manual computation is prohibitively labour intensive. "
              f"{_cite(t1.iloc[0])} demonstrated multi-centre quality measurement across "
              f"thirteen institutions, establishing that a single pipeline could generalise "
              f"across heterogeneous reporting formats.")
    para(doc, "Subsequent work broadened both the target and the method. Several of the "
              "included studies address adenoma and dysplasia identification, Barrett's "
              "oesophagus surveillance, inflammatory bowel disease activity scoring, and "
              "gastric disease information extraction. The most recent cohort applies large "
              "language models to case identification and clinical decision support, with "
              "external validation increasingly reported rather than assumed.")

    para(doc, "Two observations from this body of work bear directly on the present study. "
              "First, reported performance on genuine free text is consistently high but never "
              "perfect, typically falling between 0.80 and 0.98 on F1 or accuracy depending on "
              "the specificity of the target concept. A reported accuracy of 1.0000, as in the "
              "prior notebook audited in Phase 0, has no precedent in this literature and "
              "should itself be treated as diagnostic of an evaluation defect. Second, every "
              "one of these studies operates on narrative text with substantial lexical "
              "variability; none operates on a corpus with a 71-token vocabulary. The present "
              "dataset is therefore not a harder instance of the same problem but a different "
              "object.")

    rows = [[_cite(r), str(r["year"]), str(r["journal"])[:44], str(r["title"])[:96]]
            for _, r in t1.iterrows()]
    table(doc, ["Study", "Year", "Journal", "Title"], rows,
          "Included studies on clinical natural language processing for endoscopy and "
          "pathology reports.",
          widths=[3.2, 1.1, 4.8, 7.0], font=7.2)

    h(doc, "2.6 Endoscopy Report Classification", 2)
    para(doc, "Classification of endoscopy reports differs from general clinical text "
              "classification in three respects that the included literature makes explicit. "
              "The target concepts are drawn from a constrained clinical ontology, so "
              "vocabulary coverage is tractable. Negation and uncertainty are pervasive, "
              "because endoscopists document the absence of findings as carefully as their "
              "presence. And the ground truth is often itself derived from linked pathology "
              "reports rather than from independent adjudication, which introduces a "
              "dependency between label and feature that the better studies acknowledge and "
              "control.")
    para(doc, "That last point is the direct precedent for the Phase 0 leakage finding. Where "
              "a study derives its outcome from a pathology report and then supplies that same "
              "pathology report as a feature, the resulting performance is not a measure of "
              "diagnostic capability. Several of the included studies handle this correctly by "
              "holding out the pathology text; the present prior notebook did not.")

    h(doc, "2.7 Machine Learning in Healthcare", 2)
    para(doc, "The broader clinical machine-learning literature contributes the evaluative "
              "apparatus rather than the task. Sample-size requirements for clinical "
              "prediction models are now well specified, and the events-per-variable ratio of "
              f"{POW['events_per_variable']} measured in Phase 0 falls substantially below the "
              f"accepted minimum of {POW['riley_minimum_epv']}. Calibration is increasingly "
              f"regarded as more clinically consequential than discrimination, and net-benefit "
              f"or decision-curve analysis is expected by current reporting guidance for any "
              f"model proposed for clinical use.")

    h(doc, "2.8 Rule-Based versus Machine Learning Approaches", 2)
    t2 = LITDF[LITDF.theme == "T2 Rule-based vs ML"].sort_values("year")
    para(doc, f"Eight studies address the comparison between rule-based and learned approaches "
              f"to clinical text. The foundational contribution is {_cite(t2.iloc[0])}, whose "
              f"NegEx algorithm identifies negated findings in discharge summaries using a "
              f"small set of trigger terms and a limited scope window, and which remains in "
              f"production use decades later. Subsequent work extended negation scope "
              f"detection with sequence models and, most recently, with large language models.")
    para(doc, "The consistent finding across this literature is that rule-based systems remain "
              "competitive, and frequently superior, where the target vocabulary is closed and "
              "the corpus is small - precisely the conditions of the present dataset. This has "
              "a specific methodological consequence for the thesis. When the labels are "
              "themselves rule-derived, the rule is not merely a reasonable comparator; it is "
              "the correct one, since it defines the ceiling that any learned model is "
              "attempting to recover. A machine-learning result reported without that "
              "comparator is uninterpretable.")

    rows = [[_cite(r), str(r["year"]), str(r["journal"])[:44], str(r["title"])[:96]]
            for _, r in t2.iterrows()]
    table(doc, ["Study", "Year", "Journal", "Title"], rows,
          "Included studies on rule-based clinical natural language processing and negation "
          "handling.",
          widths=[3.2, 1.1, 4.8, 7.0], font=7.2)

    h(doc, "2.9 Weak Supervision and Silver-Standard Labels", 2)
    t3 = LITDF[LITDF.theme == "T3 Weak supervision"].sort_values("year")
    para(doc, "Nine studies address the creation of training labels without exhaustive manual "
              "annotation. This theme frames the present study's central problem most "
              "directly, because the prior notebook's labelling function is, in the "
              "terminology of this literature, a set of labelling functions applied without "
              "the accompanying methodology.")
    para(doc, "The Snorkel framework (Ratner et al., 2017) formalises the approach: multiple "
              "noisy, correlated and possibly conflicting labelling functions are written by a "
              "domain expert, and a generative model then estimates their individual "
              "accuracies and dependencies to produce probabilistic training labels. Two "
              "properties of that formalism are critical and both are absent from the prior "
              "notebook. First, conflicts between labelling functions are resolved by "
              "estimated reliability rather than by an arbitrary priority order. Second, the "
              "output is a probabilistic label carrying an explicit uncertainty, not a hard "
              "assignment. The prior notebook resolves its 61.62% conflict rate by fixed "
              "priority and emits hard labels, discarding exactly the information that the "
              "weak-supervision literature exists to preserve.")
    para(doc, "The included studies on silver-standard annotation and noisy labels reinforce "
              "the same point from the evaluation side: performance measured against "
              "programmatically generated labels measures agreement with the label-generating "
              "program, and is not interchangeable with performance measured against "
              "clinician adjudication. Reporting the former as though it were the latter is a "
              "category error, and it is the error embedded in the prior pipeline.")

    rows = [[_cite(r), str(r["year"]), str(r["journal"])[:44], str(r["title"])[:96]]
            for _, r in t3.iterrows()]
    table(doc, ["Study", "Year", "Journal", "Title"], rows,
          "Included studies on weak supervision, silver-standard annotation and noisy labels.",
          widths=[3.2, 1.1, 4.8, 7.0], font=7.2)

    h(doc, "2.10 Data Leakage in Clinical Artificial Intelligence", 2)
    t4 = LITDF[LITDF.theme == "T4 Leakage & validity"].sort_values("year")
    para(doc, "Eleven studies address leakage and evaluation validity. Kapoor and Narayanan "
              "(2023) provide the organising contribution: a survey of machine-learning-based "
              "science across seventeen fields, documenting 329 papers in which leakage "
              "produced irreproducible results, together with a taxonomy distinguishing lack "
              "of a clean separation between training and test data, the use of illegitimate "
              "features, and test sets that are not drawn from the distribution of interest. "
              "The Phase 0 finding is an instance of the second category in its most extreme "
              "form: the feature set contains the fields from which the outcome was "
              "constructed.")
    para(doc, "The clinical systematic reviews included under this theme quantify how common "
              "the problem is in practice. Across reviews of diabetes management models, "
              "medical imaging reproducibility, acute kidney injury prediction and several "
              "other domains, a consistent pattern emerges: a majority of published models are "
              "at high risk of bias on domains relating to analysis and outcome definition, "
              "and external validation is the exception rather than the rule. The methodological "
              "contributions included alongside them supply the corrective instruments - "
              "permutation testing for classifier significance (Ojala & Garriga, 2010), and "
              "principled multi-model comparison (Demsar, 2006). The permutation test applied "
              "in Section 1.6.1 is drawn directly from this literature.")

    rows = [[_cite(r), str(r["year"]), str(r["journal"])[:44], str(r["title"])[:96]]
            for _, r in t4.iterrows()]
    table(doc, ["Study", "Year", "Journal", "Title"], rows,
          "Included studies on data leakage, reproducibility and evaluation validity.",
          widths=[3.2, 1.1, 4.8, 7.0], font=7.2)

    h(doc, "2.11 Reporting Standards and Risk-of-Bias Appraisal", 2)
    t5 = LITDF[LITDF.theme == "T5 Reporting standards"].sort_values("year")
    para(doc, "Eight records establish the reporting framework adopted by this thesis. The "
              "TRIPOD statement and its artificial-intelligence extension specify what must be "
              "reported for a clinical prediction model; PROBAST supplies the corresponding "
              "risk-of-bias instrument. Datasheets for datasets and model cards extend the "
              "same transparency logic to the data and the trained artefact respectively, and "
              "both are adopted as Phase 10 deliverables in the governing blueprint.")
    rows = [[_cite(r), str(r["year"]), str(r["journal"])[:44], str(r["title"])[:96]]
            for _, r in t5.iterrows()]
    table(doc, ["Study", "Year", "Journal", "Title"], rows,
          "Included records on reporting standards and risk-of-bias appraisal.",
          widths=[3.2, 1.1, 4.8, 7.0], font=7.2)

    # ---- 2.12 comparison -------------------------------------------------
    h(doc, "2.12 Comparison of Existing Studies with the Present Work", 2)
    para(doc, "The following comparison positions the present study against representative "
              "prior work along the dimensions that determine whether a reported result is "
              "interpretable.")
    table(doc,
          ["Dimension", "Representative prior work", "Prior notebook (audited)",
           "Present study (Route A)"],
          [["Data source", "Institutional free-text endoscopy and pathology reports",
            "Single spreadsheet, provenance unverified",
            "Same spreadsheet, provenance formally recorded as unresolved"],
           ["Text character", "Genuine narrative, open vocabulary",
            "Treated as narrative", "Demonstrated to be 5-7 canned phrases per field, "
                                    "71-token vocabulary"],
           ["Label source", "Clinician adjudication or linked pathology, with agreement "
                            "statistics",
            "Regular expressions over the feature fields",
            "Same labels, audited and quantified as circular and 68% ambiguous"],
           ["Leakage control", "Label-constituent text withheld from features",
            "None; label-constituent fields supplied as features",
            "Feature provenance table; four fields blocked"],
           ["Baseline reported", "Usually a rule-based or manual-abstraction comparator",
            "None", "Majority class, stratified dummy, random noise, and permutation null"],
           ["Headline metric", "F1 or accuracy typically 0.80-0.98 with confidence intervals",
            f"Accuracy {L['E03_notebook_with_comments']['accuracy']:.4f}, no interval",
            f"Accuracy {L['E05_all_label_constituents_removed']['accuracy']:.4f} against a "
            f"{L['majority_baseline_disease_label']:.4f} baseline, with a permutation p-value"],
           ["Validity evidence", "External or temporal validation increasingly standard",
            "None", f"Permutation test (p = {PT['p_value']:.3f}); temporal validation "
                    f"feasible over {PROV['n_quarters']} quarters"]],
          "Comparison of prior work, the audited prior notebook, and the present study.",
          widths=[2.8, 4.4, 3.9, 4.9], font=7.3)

    # ---- 2.13 gap analysis ------------------------------------------------
    h(doc, "2.13 Research Gap Analysis", 2)
    para(doc, "Four gaps emerge from the reviewed literature. Each is stated as an addressable "
              "deficiency rather than as a claim of novelty.")
    table(doc, ["#", "Gap", "Evidence from the review", "Addressed by"],
          [["G1", "Performance on templated or highly structured clinical text is rarely "
                  "characterised; the literature almost exclusively studies open-vocabulary "
                  "narrative",
            "All 14 endoscopy NLP studies operate on genuine free text; none reports on a "
            "closed-phrase corpus", "RQ1, RQ2"],
           ["G2", "The effect of label-construction choices on reported performance is seldom "
                  "quantified, despite rule-derived labels being common",
            "The weak-supervision literature formalises label generation but rarely ablates "
            "the collapse strategy against reported metrics", "RQ3"],
           ["G3", "The share of reported performance attributable to circularity is almost "
                  "never measured, even where leakage is acknowledged",
            "Kapoor and Narayanan document leakage prevalence but few clinical studies report "
            "a with-and-without decomposition", "RQ4"],
           ["G4", "Negative results in clinical NLP are systematically under-reported, leaving "
                  "no published reference for what an inert corpus looks like",
            "No included study reports a corpus failing integrity testing; publication "
            "incentives favour positive findings", "All RQs"]],
          "Research gap matrix.",
          widths=[0.9, 4.6, 6.9, 2.6], font=7.4)

    para(doc, "Stated without the word 'novel' and in three sentences, as the blueprint "
              "requires: existing work establishes that clinical natural language processing "
              "performs well on genuine endoscopy narrative, but says little about what "
              "happens when the corpus is templated and the labels are programmatically "
              "derived from the features. The consequence is that a study in that situation "
              "has no published reference against which to interpret its results, and no "
              "standard decomposition for separating genuine signal from label circularity. "
              "This study supplies both for one corpus, with the measurement code released "
              "alongside the findings.")

    # ---- 2.14 research questions -----------------------------------------
    h(doc, "2.14 Research Questions", 2)
    para(doc, "Four research questions are frozen at the close of Phase 1. Each is answerable "
              "with the available data and each is mapped to specific planned experiments.")
    table(doc, ["RQ", "Statement", "Gap", "Experiments", "Answerable"],
          [["RQ1", "Can gastrointestinal diagnoses be automatically classified from structured "
                   "endoscopy report fields?", "G1",
            "E00-E02, E11", "Yes - and on this corpus the answer is negative, with evidence"],
           ["RQ2", "Does representation choice (one-hot, TF-IDF, embeddings, ClinicalBERT) "
                   "affect performance on templated clinical text?", "G1",
            "E08, E09", "Yes - all representations are expected to be statistically "
                        "equivalent"],
           ["RQ3", "What is the effect of label-construction choices, specifically "
                   "single-label collapse versus multi-label formulation, on reported "
                   "performance?", "G2",
            "E24-E26", "Yes - 61.62% multi-match rate makes this directly measurable"],
           ["RQ4", "How much of the reported performance in rule-labelled clinical natural "
                   "language processing is attributable to circularity?", "G3",
            "E03-E06", "Yes - already partially answered in Phase 0"]],
          "Research question mapping. Experiment identifiers refer to the registry in the "
          "governing blueprint.",
          widths=[1.1, 6.3, 1.1, 2.3, 4.2], font=7.4)

    callout(doc, "RQ3 and RQ4 convert the two defects discovered in Phase 0 into the two "
                 "contributions of the thesis. This is the mechanism by which an apparently "
                 "fatal data problem becomes a defensible research programme, and it is the "
                 "reason Phase 1 was scheduled after Phase 0 rather than before it.",
            title="Framing note")

    figure(doc, "F17_conceptual_framework.png",
           "Conceptual framework. Each layer of the pipeline carries a corresponding threat to "
           "validity; the validity layer supplies the controls, and the contribution follows "
           "from making those controls explicit.")

    h(doc, "2.15 Phase 1 Validation Checklist", 2)
    table(doc, ["Criterion", "Required standard", "Outcome"],
          [["Search reproducible", "String recorded verbatim and re-executable",
            "MET - executed by committed script; strings in Appendix A"],
           ["Stage counts recorded", "Counts at every screening stage",
            "MET - see PRISMA stage table"],
           ["Coverage adequate", "At least 25 papers in the extraction table",
            f"MET - {e['records_included_total']} included"],
           ["Realism anchor", "At least 5 papers on real endoscopy free text",
            f"MET - {len(LITDF[LITDF.theme == 'T1 Endoscopy report NLP'])} studies"],
           ["Framing anchor", "At least 3 papers on leakage or weak supervision",
            f"MET - {len(LITDF[LITDF.theme.isin(['T3 Weak supervision', 'T4 Leakage & validity'])])} studies"],
           ["Gap articulated", "Three sentences without the word 'novel'",
            "MET - Section 2.13"],
           ["RQs frozen", "Four questions, each mapped to at least one experiment",
            "MET - Section 2.14"],
           ["Reference management", "Structured export, no manual citation formatting",
            "MET - APA strings generated from retrieved metadata"]],
          "Phase 1 validation checklist against the blueprint success criteria.",
          widths=[3.6, 5.4, 7.0], font=7.8)

    h(doc, "2.16 Phase 1 Discussion", 2)
    para(doc, "The review's principal service to this thesis is calibration. Without it, an "
              "accuracy of 0.1608 reads as failure. With it, the same number reads as the "
              "expected outcome of applying sound methods to a corpus that fourteen comparable "
              "studies would not recognise as endoscopy text, and the interesting question "
              "shifts from 'why did the model fail' to 'what exactly is this corpus, and how "
              "did a reported accuracy of 1.0000 arise from it'. Both questions are answered "
              "in Phase 0.")
    para(doc, "A methodological limitation should be stated plainly. The blueprint specifies "
              "six databases; the search executed here covers PubMed/MEDLINE only. This is a "
              "material limitation for the computer-science themes in particular, since IEEE "
              "Xplore, the ACM Digital Library and arXiv index work that MEDLINE does not. It "
              "was partially mitigated by hand-searching six foundational works through the "
              "PRISMA other-methods arm, and the affected themes are those where the "
              "foundational literature is small, well known and stable rather than "
              "fast-moving. The limitation is nonetheless real and is recorded rather than "
              "minimised. Extending the search to the remaining databases is the first task of "
              "any revision.")
    para(doc, "A second limitation concerns the per-theme relevance cap. Retaining a fixed "
              f"number of the highest-scoring records per theme is a pragmatic device, and it "
              f"set aside {e['records_eligible_but_capped']} records that met every stated "
              f"eligibility criterion. The ranking function is documented and deterministic, "
              f"so the selection is reproducible, but it is a selection and not a census. A "
              f"full systematic review would retain all eligible records.")

    h(doc, "2.17 Phase 1 Conclusion", 2)
    para(doc, f"A reproducible search identified {e['records_included_total']} studies across "
              f"five themes. The literature establishes a realistic performance envelope of "
              f"0.80 to 0.98 on genuine endoscopy narrative, supplies the formal instruments "
              f"used in Phase 0, and demonstrates that rule-based comparators remain necessary "
              f"where labels are rule-derived. Four research questions have been frozen, each "
              f"mapped to planned experiments, with RQ3 and RQ4 carrying the study's "
              f"contribution.")


# ==========================================================================
def sec_methodology(doc):
    h(doc, "3. Methodology", 1, page_break=True)

    h(doc, "3.1 Overall Design", 2)
    para(doc, "The study follows CRISP-DM as its process framework, augmented by an integrity "
              "gate placed ahead of all modelling activity, and reports against TRIPOD+AI and "
              "PROBAST. The design principle governing both phases reported here is that every "
              "claim must be traceable to an executable artefact: each number in this document "
              "is produced by a committed script operating on a fingerprinted input, and the "
              "entire pipeline can be re-run end to end.")

    figure(doc, "F01_research_workflow.png",
           "Research workflow for Phases 0 and 1 and their relationship to the downstream "
           "phases they gate.")
    figure(doc, "F18_methodology_pipeline.png",
           "Methodology pipeline showing the seven executed stages and their deliverables.",
           width=6.0)

    h(doc, "3.2 Materials", 2)
    para(doc, f"The dataset is a single Excel workbook of {PROV['n_rows']:,} records and "
              f"{PROV['n_cols']} fields, fingerprinted by SHA-256 to fix the exact version "
              f"under analysis. The prior analysis under audit is a 94-cell Jupyter notebook. "
              f"Analysis was conducted in Python 3.14 using pandas, NumPy, SciPy, "
              f"scikit-learn and Matplotlib; the random seed was fixed at 42 throughout.")

    h(doc, "3.3 Statistical Methods", 2)
    table(doc, ["Purpose", "Method", "Justification"],
          [["Distributional plausibility", "Kolmogorov-Smirnov test; chi-square "
                                           "goodness-of-fit; one-way ANOVA",
            "Non-parametric and parametric tests of the uniformity hypothesis for a continuous "
            "clinical variable"],
           ["Categorical balance", "Chi-square against equiprobability",
            "Detects the equal-frequency signature of naive category sampling"],
           ["Association strength", "Bias-corrected Cramer's V (Bergsma); mutual information",
            "Effect size rather than significance; the bias correction is appropriate for "
            "sparse contingency tables"],
           ["Multiplicity control", "Bonferroni correction across 36 pairwise tests",
            "Conservative control of the family-wise error rate given exploratory testing"],
           ["Generative-process test", "Occupancy expectation with Monte-Carlo reference "
                                       "interval (2,000 simulations)",
            "Compares observed tuple diversity against the analytic expectation for uniform "
            "random sampling"],
           ["Model evaluation", "Stratified 5-fold cross-validated accuracy",
            "Appropriate where classes are near-balanced; reported alongside explicit "
            "baselines"],
           ["Significance of learning", "Label-permutation test, 1,000 iterations",
            "Ojala and Garriga (2010); the gold-standard null test for classifier performance"],
           ["Re-identification risk", "k-anonymity over the quasi-identifier set",
            "Standard disclosure-control measure"],
           ["Sample-size adequacy", "Events per variable against Riley et al. thresholds",
            "The accepted minimum-sample criterion for clinical prediction models"]],
          "Summary of statistical methods and their justification.",
          widths=[3.4, 5.2, 7.4], font=7.4)

    h(doc, "3.4 Literature Review Methods", 2)
    para(doc, "The review followed PRISMA 2020 in structure. Searches were executed against "
              "PubMed/MEDLINE through the NCBI E-utilities API on the date recorded in "
              "Appendix A. Screening applied declarative inclusion and exclusion criteria "
              "encoded in the selection script; eligibility applied theme-specific criteria "
              "with a documented relevance-ranking function. Because screening was executed "
              "programmatically by a single rule set rather than by two independent human "
              "reviewers, inter-rater agreement is not applicable; the corresponding "
              "transparency guarantee is that the rule set is inspectable and the outcome "
              "exactly reproducible. Bibliographic metadata, including volume, issue and "
              "pagination, was retrieved programmatically and APA reference strings were "
              "generated from it rather than typed.")

    h(doc, "3.5 Reproducibility", 2)
    table(doc, ["Artefact", "Path", "Role"],
          [["Integrity battery", "src/data/integrity.py",
            "All Phase 0 measurements; writes reports/phase0_results.json"],
           ["Literature search", "src/literature/search.py",
            "Executes the six search strings; writes PRISMA stage counts"],
           ["Eligibility assessment", "src/literature/eligibility.py",
            "Applies theme criteria and integrity filters; writes the extraction table"],
           ["Reference enrichment", "src/literature/enrich.py",
            "Retrieves pagination and generates APA strings"],
           ["Figure generation", "src/report/figures.py",
            "Regenerates all 19 figures with a fixed seed"],
           ["Report assembly", "src/report/build_docx.py",
            "Assembles this document from the artefacts above"],
           ["Results store", "reports/phase0_results.json",
            "Every Phase 0 measurement in machine-readable form"],
           ["Feature provenance", "docs/feature_provenance.csv",
            "The leakage firewall applied in later phases"],
           ["Extraction table", "literature/extraction_table.csv",
            "The 50 included studies with metadata and APA strings"]],
          "Reproducibility artefacts.",
          widths=[3.6, 5.2, 7.2], font=7.6,
          note="Executing the six scripts in the listed order regenerates every number, figure "
               "and table in this report from the fingerprinted source file.")


def sec_results(doc):
    h(doc, "4. Consolidated Results", 1, page_break=True)
    para(doc, "This section consolidates the quantitative outcomes of both phases. Detailed "
              "interpretation is given in the phase sections above and in the discussion "
              "below.")

    t6 = B["test6_combinatorial_coverage"]
    hb = L["honest_baselines_target_comments"]
    table(doc, ["Domain", "Result", "Value"],
          [["Integrity", "Synthetic-data battery tests failed", "6 of 6"],
           ["Integrity", "Maximum bias-corrected Cramer's V across 36 pairs",
            f"{B['test3_pairwise_independence']['max_offdiag_cramers_v']}"],
           ["Integrity", "Pairs significant after Bonferroni correction", "0 of 36"],
           ["Integrity", "Observed vs expected distinct finding tuples",
            f"{t6['observed_combinations']} vs {t6['expected_unique_if_random']} "
            f"(O/E {t6['observed_over_expected']})"],
           ["Integrity", "Corpus vocabulary across all narrative fields",
            f"{B['test5_summary']['corpus_vocabulary_size']} tokens"],
           ["Leakage", "Prior notebook accuracy as written",
            f"{L['E03_notebook_with_comments']['accuracy']:.4f}"],
           ["Leakage", "Accuracy with the diagnosis field removed",
            f"{L['E04_comments_removed']['accuracy']:.4f}"],
           ["Leakage", "Accuracy with all label-constituent fields removed",
            f"{L['E05_all_label_constituents_removed']['accuracy']:.4f}"],
           ["Leakage", "Majority baseline for the derived label",
            f"{L['majority_baseline_disease_label']:.4f}"],
           ["Leakage", "Feature combinations mapping to exactly one label",
            f"{L['determinism_check']['pct_deterministic']}%"],
           ["Signal", "Best honest model accuracy",
            f"{max(hb[k]['accuracy'] for k in hb if k.startswith('E0') and hb[k]['std'] is not None):.4f}"],
           ["Signal", "Majority-class baseline",
            f"{hb['majority_baseline']['accuracy']:.4f}"],
           ["Signal", "Permutation test p-value", f"{PT['p_value']:.3f}"],
           ["Signal", "Percentile of observed score within the null",
            f"{PT['percentile_of_real']:.0f}th"],
           ["Labels", "Records with exactly one rule match",
            f"{LA['n_unambiguous']} ({LA['pct_unambiguous']}%)"],
           ["Labels", "Records with two or more rule matches",
            f"{LA['n_multi_match']} ({LA['pct_multi_match']}%)"],
           ["Labels", "Records forced to 'Normal' with no rule match",
            f"{LA['n_zero_match_forced_normal']} ({LA['pct_zero_match']}%)"],
           ["Power", "Events per variable",
            f"{POW['events_per_variable']} (minimum {POW['riley_minimum_epv']})"],
           ["Privacy", "k-anonymity at monthly date granularity",
            f"k = {R['ethics']['k_anonymity_age5_sex_month']}"],
           ["Literature", "Studies included",
            f"{P['eligibility']['records_included_total']}"],
           ["Literature", "Studies on genuine endoscopy free text",
            f"{len(LITDF[LITDF.theme == 'T1 Endoscopy report NLP'])}"]],
          "Consolidated results across Phase 0 and Phase 1.",
          widths=[2.4, 8.6, 5.0], font=7.8)


def sec_discussion(doc):
    h(doc, "5. Discussion", 1, page_break=True)

    h(doc, "5.1 Principal Interpretation", 2)
    para(doc, "The two phases reported here jointly establish that the original research "
              "question, as posed, cannot be answered with the available data, and that the "
              "apparent evidence that it had been answered was an artefact of two independent "
              "methodological defects. That is an unwelcome result but a tractable one, and "
              "the response adopted is not to conceal it but to make its measurement the "
              "subject of the thesis.")
    para(doc, "The strongest single piece of evidence is not any individual test but the "
              "agreement between the occupancy calculation and the association analysis. If "
              "the finding fields were genuine clinical observations, they would be correlated "
              "with one another and with the diagnosis, and the number of distinct combinations "
              "observed would fall well below the number expected under independent sampling. "
              "Both predictions fail in the same direction and to the same degree. The "
              "convergence of an effect-size argument and a combinatorial argument on the same "
              "conclusion is what makes the finding robust to challenge.")

    h(doc, "5.2 Implications for the Thesis", 2)
    para(doc, "Three consequences follow for the remaining phases. First, no accuracy figure "
              "computed on a label-constituent feature set may be reported as a diagnostic "
              "result; the feature provenance table is binding. Second, the multi-label "
              "formulation is not an optional refinement but the clinically correct "
              "representation, since single-label collapse is inapplicable to 61.62% of the "
              "corpus. Third, tuning has near-zero expected return: with the observed score "
              "inside the permutation null, validation curves will be flat, and effort is "
              "better allocated to label engineering and error analysis, where the "
              "intellectual contribution actually lies.")

    h(doc, "5.3 Strengths", 2)
    for t in [
        "Every reported quantity is recomputed from a fingerprinted source file by committed "
        "code, so the audit is verifiable rather than asserted.",
        "The absence of signal is established by a formal permutation test rather than "
        "inferred from poor model performance.",
        "The leakage analysis decomposes the artefact across four fields rather than "
        "attributing it to one, correcting the expectation recorded in the governing "
        "blueprint.",
        "The literature search is executed programmatically and is re-runnable, and three "
        "integrity filters removed records that a keyword-only procedure would have retained.",
        "Label quality is audited independently of leakage, yielding a finding that "
        "generalises beyond this dataset.",
    ]:
        bullet(doc, t)

    h(doc, "5.4 Limitations", 2)
    para(doc, "The limitations are stated without mitigation language.")
    table(doc, ["#", "Limitation", "Consequence", "Mitigation"],
          [["L1", "No provenance statement was obtained from the data provider",
            "The synthetic-generation conclusion rests on internal statistical evidence alone "
            "and remains an inference, however strong",
            "Two further documented requests; record any response verbatim"],
           ["L2", "The literature search covers PubMed/MEDLINE only, not the six databases "
                  "specified in the blueprint",
            "Computer-science venues indexing relevant weak-supervision and leakage work are "
            "under-represented",
            "Six foundational works added by hand-search; extend to IEEE Xplore, ACM and arXiv "
            "in revision"],
           ["L3", "A per-theme relevance cap set aside eligible records",
            "The included set is a documented selection, not a census",
            "The ranking function is deterministic and the excluded set is retained in full"],
           ["L4", "Screening was performed by a single automated rule set, not by two "
                  "independent reviewers",
            "No inter-rater agreement statistic can be reported",
            "The rule set is inspectable and the outcome exactly reproducible"],
           ["L5", "Cross-validated accuracy is reported without bootstrap confidence intervals "
                  "at this stage",
            "Uncertainty around each point estimate is represented only by the fold standard "
            "deviation",
            "Bootstrap intervals are specified for Phase 8"],
           ["L6", "The events-per-variable ratio is below the accepted minimum",
            "The modelling problem is underpowered irrespective of algorithm choice",
            "Reported explicitly; constrains all downstream claims"]],
          "Limitations of the work reported in Phases 0 and 1.",
          widths=[0.9, 4.4, 5.2, 5.5], font=7.4)

    h(doc, "5.5 Comparison with the Governing Blueprint", 2)
    para(doc, "Three departures from the blueprint's stated expectations are recorded, each "
              "arising from direct measurement.")
    table(doc, ["Item", "Blueprint expectation", "Measured outcome", "Status"],
          [["Leakage delta on removing the diagnosis field",
            "Accuracy falls from 1.000 to approximately 0.19",
            f"Falls only to {L['E04_comments_removed']['accuracy']:.4f}; the finding fields "
            f"independently encode the labelling rules",
            "Corrected - leakage is multi-source"],
           ["Combinatorial coverage",
            "Near-maximal diversity, assessed against a 90% coverage threshold",
            f"{t6c(B)}", "Refined - occupancy expectation is the sharper test"],
           ["Cramer's V magnitudes",
            "Feature-target values up to 0.088 (uncorrected statistic)",
            "Maximum 0.0614 using the Bergsma bias correction",
            "Refined - the more conservative estimator supports the same conclusion"]],
          "Departures from the governing blueprint, with justification.",
          widths=[3.4, 4.4, 5.4, 2.8], font=7.4,
          note="Each departure was adopted because direct measurement contradicted or improved "
               "upon the anticipated value. The blueprint remains the governing protocol in "
               "all other respects.")


def t6c(B) -> str:
    t6 = B["test6_combinatorial_coverage"]
    return (f"{t6['coverage_pct']}% raw coverage, but {t6['observed_combinations']} observed "
            f"against {t6['expected_unique_if_random']} expected under uniform random "
            f"sampling (O/E {t6['observed_over_expected']})")


def sec_conclusion(doc):
    h(doc, "6. Conclusion", 1, page_break=True)
    para(doc, f"Phase 0 subjected the dataset to a six-test integrity battery, a leakage audit, "
              f"a label-construction audit, an ethics assessment and a formal test for the "
              f"presence of learnable signal. All six integrity tests returned outcomes "
              f"inconsistent with genuine clinical data. The corpus vocabulary comprises "
              f"{B['test5_summary']['corpus_vocabulary_size']} tokens across fields presented "
              f"as clinical narrative; all 36 pairwise associations are negligible and none "
              f"survives correction for multiple comparison; and the number of distinct "
              f"clinical-finding combinations matches the occupancy expectation for "
              f"independent uniform sampling to within one percent.")
    para(doc, f"The prior pipeline's reported accuracy of "
              f"{L['E03_notebook_with_comments']['accuracy']:.4f} was shown to be an artefact "
              f"of target leakage distributed across four fields rather than concentrated in "
              f"the diagnosis column, a finding that corrects the expectation recorded in the "
              f"governing blueprint. With every label-constituent field withheld, accuracy "
              f"falls to {L['E05_all_label_constituents_removed']['accuracy']:.4f}, below the "
              f"majority-class baseline. A {PT['n_permutations']:,}-iteration permutation test "
              f"places the observed score at the {PT['percentile_of_real']:.0f}th percentile "
              f"of the null distribution (p = {PT['p_value']:.3f}), formally establishing the "
              f"absence of a learnable relationship. Independently, the labelling function was "
              f"shown to produce an unambiguous label for only {LA['pct_unambiguous']}% of "
              f"records and to assert health without evidence for a further "
              f"{LA['pct_zero_match']}%.")
    para(doc, f"Phase 1 identified {P['eligibility']['records_included_total']} studies through "
              f"a reproducible search, establishing a realistic performance envelope of 0.80 "
              f"to 0.98 on genuine endoscopy narrative and supplying the formal instruments "
              f"used in Phase 0. Four research questions were frozen, of which two - the "
              f"effect of label-construction choices on reported performance, and the share of "
              f"reported performance attributable to circularity - convert the defects "
              f"discovered in Phase 0 into the contributions of the thesis.")
    para(doc, "The integrity gate did not clear, and Route A is in force. The work reported "
              "here is not a failed attempt at classification; it is a completed audit that "
              "establishes what can and cannot be claimed from this corpus, and it fixes the "
              "constraints under which the remaining phases will operate.")

    h(doc, "6.1 Immediate Next Actions", 2)
    for t in [
        "Send a second documented provenance request to the data provider and record any "
        "response verbatim in docs/data_provenance.md.",
        "Obtain a supervisor signature on the Route A decision and file the dated minute.",
        "Extend the literature search to IEEE Xplore, the ACM Digital Library and arXiv, and "
        "update the PRISMA counts.",
        "Begin Phase 2 (Data Understanding) under the feature provenance constraints "
        "established in Section 1.8.",
        "Design the Phase 3 multi-label taxonomy, treating the co-occurrence structure in the "
        "rule co-occurrence matrix as the starting point.",
        "Verify that the raw data file is excluded from version control before the first "
        "commit.",
    ]:
        bullet(doc, t)


def sec_references(doc):
    h(doc, "7. References", 1, page_break=True)
    para(doc, "References follow APA 7th edition. Bibliographic details for the "
              f"{len(LITDF)} included studies were retrieved programmatically from "
              "PubMed/MEDLINE and formatted from the retrieved metadata; digital object "
              "identifiers are given where the record supplies one.", italic=True, size=9)

    df = LITDF.copy()
    df["_sort"] = df["first_author"].astype(str).str.lower()
    df = df.sort_values("_sort")

    for _, r in df.iterrows():
        s = str(r["apa"])
        p = doc.add_paragraph()
        p.paragraph_format.left_indent = __import__("docx").shared.Inches(0.4)
        p.paragraph_format.first_line_indent = __import__("docx").shared.Inches(-0.4)
        p.paragraph_format.space_after = __import__("docx").shared.Pt(5)
        p.paragraph_format.line_spacing = 1.1
        # render *italic* segments
        parts = s.split("*")
        for i, seg in enumerate(parts):
            if not seg:
                continue
            run = p.add_run(seg)
            run.font.size = __import__("docx").shared.Pt(9.5)
            run.italic = (i % 2 == 1)

    h(doc, "7.1 Standards and Frameworks Cited", 2)
    for s in [
        "CRISP-DM: Cross-Industry Standard Process for Data Mining. Process framework "
        "governing the overall study design.",
        "PRISMA 2020: Preferred Reporting Items for Systematic Reviews and Meta-Analyses. "
        "Applied to the Phase 1 review structure.",
        "TRIPOD+AI: Transparent Reporting of a multivariable prediction model for Individual "
        "Prognosis Or Diagnosis, artificial-intelligence extension. Primary reporting "
        "checklist.",
        "PROBAST: Prediction model Risk Of Bias ASsessment Tool. Risk-of-bias instrument.",
        "Minimal Standard Terminology 3.0 for gastrointestinal endoscopy. Terminology anchor "
        "for the Phase 3 label taxonomy.",
        "ICD-10 K20-K31, Diseases of the oesophagus, stomach and duodenum. Diagnostic coding "
        "anchor.",
    ]:
        bullet(doc, s, size=9.5)


def sec_appendix(doc):
    h(doc, "Appendix A - Search Strings as Executed", 1, page_break=True)
    para(doc, f"Executed against PubMed/MEDLINE through the NCBI E-utilities API on "
              f"{P['run_date']}. Retrieval capped at 200 relevance-ranked records per string.",
              italic=True, size=9)
    for k, v in P["queries"].items():
        para(doc, k, bold=True, size=9.5, space_after=2)
        p = doc.add_paragraph()
        p.paragraph_format.left_indent = __import__("docx").shared.Inches(0.3)
        p.paragraph_format.space_after = __import__("docx").shared.Pt(3)
        run = p.add_run(v["search_string"])
        run.font.name = "Consolas"
        run.font.size = __import__("docx").shared.Pt(8)
        para(doc, f"Window {v['date_from']}-{v['date_to']}; {v['total_hits']:,} hits; "
                  f"{v['retrieved']} retrieved.", size=8.5, italic=True, space_after=9)

    h(doc, "Appendix B - Full Extraction Table", 1, page_break=True)
    para(doc, f"All {len(LITDF)} included studies with theme assignment and identification "
              f"route. Machine-readable form: literature/extraction_table.csv.",
         italic=True, size=9)
    df = LITDF.sort_values(["theme", "year"])
    rows = [[str(r["year"]), str(r["first_author"])[:24],
             str(r["title"])[:84], str(r["journal"])[:34],
             THEME_LABEL.get(r["theme"], r["theme"])[:30],
             str(r["pmid"]).split(".")[0] if str(r["pmid"]) not in ("nan", "") else "-"]
            for _, r in df.iterrows()]
    table(doc, ["Year", "First author", "Title", "Journal", "Theme", "PMID"], rows,
          "Complete extraction table of included studies.",
          widths=[1.0, 2.4, 5.6, 3.0, 2.6, 1.4], font=6.5)

    h(doc, "Appendix C - Labelling Function Under Audit", 1, page_break=True)
    para(doc, "The seven rules reproduced below are transcribed from cell 29 of the prior "
              "notebook and were re-implemented verbatim for the Phase 0 audit. Priority order "
              "for conflict resolution is the order listed.", italic=True, size=9)
    table(doc, ["#", "Label", "Condition", "Fields consulted"],
          [["1", "Gastric Ulcer",
            "'gastric ulcer' in Comments, or ('ulcer' and 'antrum' in Stomach)",
            "Comments, Stomach"],
           ["2", "Duodenal Ulcer",
            "'duodenal ulcer' in Comments, or ('ulcer' and ('bulb' or 'duodenum') in Duodenum)",
            "Comments, Duodenum"],
           ["3", "Gastritis", "'gastritis' in Comments", "Comments"],
           ["4", "Polyp", "'polyp' in Stomach or Oesophagus", "Stomach, Oesophagus"],
           ["5", "Esophageal Varices", "'varic' in Oesophagus", "Oesophagus"],
           ["6", "Esophagitis", "'erosion' or 'les lax' or 'erythema' in Oesophagus",
            "Oesophagus"],
           ["7", "Normal", "'normal' in all three finding fields, or 'normal upper gi' in "
                           "Comments", "Oesophagus, Stomach, Duodenum, Comments"],
           ["-", "Fallback", "If no rule matches, assign 'Normal'", "-"],
           ["-", "Conflict", "If several match, take the first in priority order", "-"]],
          "The labelling function under audit, transcribed from the prior notebook.",
          widths=[0.8, 3.0, 7.6, 4.6], font=7.4,
          note="Four of the seven rules consult the Comments field, and six consult a field "
               "that the prior notebook also supplies as a model input. This is the mechanism "
               "of the circularity quantified in Section 1.6.")
