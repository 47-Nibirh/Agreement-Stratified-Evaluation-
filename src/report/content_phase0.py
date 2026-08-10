"""Executive summary and Phase 0 sections of the report."""
from __future__ import annotations

from docx.shared import RGBColor

from build_docx import (B, DARKRED, ETH, L, LA, POW, PROV, PT, P, R,
                        bullet, callout, figure, h, para, rich, table)


def sec_executive_summary(doc):
    h(doc, "Executive Summary", 1, page_break=True)

    para(doc, "This report documents the completion of Phase 0 (Data Provenance and "
              "Integrity Gate) and Phase 1 (Literature Review and Problem Framing) of a "
              "Bachelor's thesis on the automatic classification of gastrointestinal disease "
              "from upper gastrointestinal endoscopy reports. Both phases were executed as "
              "specified in the governing research blueprint. Every quantitative statement in "
              "this document was recomputed from the source data file or retrieved "
              "programmatically from a bibliographic database; no figure has been carried "
              "over from prior work without independent verification.")

    h(doc, "Principal Findings", 2)

    t6 = B["test6_combinatorial_coverage"]
    rich(doc, [("Finding 1 — The corpus is statistically inert and consistent with synthetic "
                "generation. ", {"b": True, "c": DARKRED}),
               (f"All six tests of the synthetic-data battery returned results incompatible "
                f"with genuine clinical data. Patient age is statistically indistinguishable "
                f"from a uniform distribution over [18, 90] (Kolmogorov-Smirnov "
                f"D = {B['test1_numeric_uniformity']['ks_statistic']}, "
                f"p = {B['test1_numeric_uniformity']['ks_p']}). Equiprobability across "
                f"categories could not be rejected in eight of nine categorical fields. Across "
                f"all 36 pairwise associations the largest bias-corrected Cramer's V was "
                f"{B['test3_pairwise_independence']['max_offdiag_cramers_v']}, and no pair "
                f"remained significant after Bonferroni correction. Decisively, the number of "
                f"distinct clinical-finding combinations observed "
                f"({t6['observed_combinations']}) matches the number expected had the fields "
                f"been drawn independently and uniformly at random "
                f"({t6['expected_unique_if_random']}; Monte-Carlo 95% interval "
                f"{t6['mc_95_interval_if_random'][0]}-{t6['mc_95_interval_if_random'][1]}).",
                {})])

    rich(doc, [("Finding 2 — Leakage in the prior notebook is multi-source, not "
                "single-column. ", {"b": True, "c": DARKRED}),
               (f"The existing pipeline reports a five-fold cross-validated accuracy of "
                f"{L['E03_notebook_with_comments']['accuracy']:.4f}. This is an artefact of "
                f"target leakage: the label is derived by regular expressions over fields that "
                f"are simultaneously supplied as model inputs. Critically, removing the "
                f"Comments field alone - the intuitive remedy - reduces accuracy only to "
                f"{L['E04_comments_removed']['accuracy']:.4f}, because the Oesophagus, Stomach "
                f"and Duodenum fields independently encode the same labelling rules. Only when "
                f"every label-constituent field is withheld does performance fall to "
                f"{L['E05_all_label_constituents_removed']['accuracy']:.4f}, below the "
                f"majority-class baseline of {L['majority_baseline_disease_label']:.4f}.",
                {})])

    rich(doc, [("Finding 3 — The labelling function is independently defective. ",
                {"b": True, "c": DARKRED}),
               (f"Beyond leakage, the rule set assigns ambiguous or unfounded labels. Only "
                f"{LA['pct_unambiguous']}% of records satisfy exactly one disease rule; "
                f"{LA['pct_multi_match']}% satisfy two or more and are silently collapsed by "
                f"priority order, discarding genuine comorbidity. A further "
                f"{LA['n_zero_match_forced_normal']} records ({LA['pct_zero_match']}%) satisfy "
                f"no rule at all and are defaulted to 'Normal', asserting health without "
                f"evidence.", {})])

    rich(doc, [("Finding 4 — The absence of signal is formally demonstrated, not merely "
                "observed. ", {"b": True, "c": DARKRED}),
               (f"A label-permutation test with {PT['n_permutations']:,} iterations places the "
                f"observed cross-validated accuracy ({PT['real_score']:.4f}) at the "
                f"{PT['percentile_of_real']:.0f}th percentile of the null distribution "
                f"(p = {PT['p_value']:.3f}). The dataset contains no learnable relationship "
                f"between admissible features and the diagnosis.", {})])

    h(doc, "Gate Decision", 2)
    para(doc, "The integrity gate did not clear. Proceeding as though the reported accuracy "
              "were a diagnostic result (Route C) is inadmissible. Route A - reframing the "
              "study as an auditable methodological investigation delivering an honest "
              "negative result together with a quantified account of how label construction "
              "and leakage manufacture apparent performance - is adopted and governs all "
              "downstream phases.")

    h(doc, "Literature Position", 2)
    e = P["eligibility"]
    para(doc, f"A reproducible search of PubMed/MEDLINE using six pre-specified strings "
              f"returned {sum(v['total_hits'] for v in P['queries'].values()):,} hits, of "
              f"which {P['stages']['records_after_deduplication']} unique records were "
              f"screened and {e['records_included_total']} studies were included after "
              f"eligibility assessment. The literature establishes that natural language "
              f"processing on genuine free-text endoscopy reports routinely achieves F1 and "
              f"accuracy in the 0.80-0.98 range, which frames the present corpus as anomalous "
              f"rather than the methods as inadequate. Two research questions identified "
              f"through gap analysis - the effect of label-construction choices on reported "
              f"performance, and the share of reported performance attributable to "
              f"circularity - are underserved in the existing literature and constitute this "
              f"study's contribution.")

    callout(doc, "A thesis that identifies a templated and statistically inert corpus, proves "
                 "circular and ambiguous labelling with the correct tests, and reframes its "
                 "contribution accordingly is methodologically stronger than one reporting "
                 "near-perfect accuracy without examining it. The evidence assembled here is "
                 "designed to be raised by the candidate before it is raised by an examiner.",
            title="Supervisory position")


def sec_phase0(doc):
    h(doc, "1. Phase 0 - Data Provenance and Integrity Gate", 1, page_break=True)

    h(doc, "1.1 Objectives", 2)
    para(doc, "Phase 0 establishes where the data came from and whether it behaves like "
              "genuine clinical data, before any modelling decision is taken. The CRISP-DM "
              "'Verify Data Quality' task is routinely reduced to counting missing values. In "
              "biomedical artificial intelligence it must additionally answer a prior "
              "question: did this data originate where it is believed to have originated? The "
              "specific objectives are:")
    for t in [
        "To obtain and record a written provenance statement for the dataset.",
        "To execute a six-test battery capable of distinguishing synthetically generated "
        "records from genuine clinical records.",
        "To trace, for every field, whether it participated in constructing the label, and to "
        "quantify the performance attributable to that participation.",
        "To audit the labelling function itself for ambiguity and unfounded assignment.",
        "To complete an ethics and de-identification assessment.",
        "To reach a documented, evidence-based route decision governing all later phases.",
    ]:
        bullet(doc, t)

    h(doc, "1.2 Background and the Importance of Data Integrity", 2)
    para(doc, "Clinical prediction models are increasingly developed from routinely collected "
              "health data, and the reporting literature has converged on the position that "
              "the credibility of such a model rests on the provenance and construction of its "
              "data at least as much as on its algorithm. The TRIPOD+AI statement and the "
              "PROBAST risk-of-bias instrument both place data source, participant selection "
              "and outcome definition ahead of model specification in their assessment order. "
              "Kapoor and Narayanan (2023) surveyed machine-learning-based science across "
              "seventeen fields and identified data leakage as a recurring and frequently "
              "undetected cause of irreproducible findings, proposing a taxonomy in which the "
              "most damaging form is the presence of information in the feature set that "
              "would not be available at prediction time, or that was itself used to define "
              "the outcome.")
    para(doc, "The dataset audited here exhibits precisely that failure mode, compounded by a "
              "second and less commonly discussed problem: the outcome is not an independently "
              "ascertained clinical fact but a construct produced by a hand-written rule set "
              "operating on the same fields offered as predictors. Where the label is a "
              "deterministic function of the features, a sufficiently expressive classifier "
              "does not learn medicine; it recovers the rule. Establishing this before "
              "modelling is the purpose of the integrity gate.")

    h(doc, "1.3 Data Provenance Verification", 2)
    para(doc, "The blueprint requires four items to be obtained in writing from the data "
              "provider: the source institution and endoscopy unit; the collection date range "
              "and whether sampling was consecutive; whether the file is a raw export, a "
              "de-identified derivative, or synthetically generated; and an ethics approval "
              "number, institutional review board waiver, or an explicit statement that the "
              "data are synthetic. At the time of writing no provenance statement has been "
              "obtained. The provenance position is recorded as unresolved, and the audit "
              "proceeds on internal evidence alone.")

    table(doc,
          ["Property", "Measured value"],
          [["File name", PROV["filename"]],
           ["SHA-256 fingerprint", PROV["sha256"]],
           ["File size (bytes)", f"{PROV['file_bytes']:,}"],
           ["Records x fields", f"{PROV['n_rows']:,} x {PROV['n_cols']}"],
           ["Exact duplicate rows", PROV["exact_duplicates"]],
           ["Duplicates ignoring Patient_ID", PROV["duplicates_excl_id"]],
           ["Unique patient identifiers", f"{PROV['unique_ids']:,} (0 collisions)"],
           ["Date range", f"{PROV['date_min']} to {PROV['date_max']}"],
           ["Temporal span", f"{PROV['date_span_days']} days across "
                             f"{PROV['n_quarters']} quarters"],
           ["Unparseable dates", PROV["dates_unparsed"]],
           ["Provenance statement", "NOT OBTAINED - recorded as unresolved"]],
          "Dataset summary and provenance fingerprint. The SHA-256 hash fixes the exact file "
          "version to which every result in this report refers.",
          widths=[5.4, 10.6],
          note="Computed by src/data/integrity.py. Recomputing the hash is sufficient to "
               "verify that a later copy of the dataset is byte-identical to the audited one.")

    para(doc, "The absence of a provenance statement is itself a finding. Under the "
              "blueprint's decision logic, a documented non-response is equivalent to an "
              "unconfirmed source for the purposes of the route decision.")

    h(doc, "1.4 Data Quality Assessment", 2)
    para(doc, "A complete field-level inventory was produced. The corpus contains no duplicate "
              "records and no identifier collisions, and every date parses cleanly under a "
              "single format mask. Missingness is confined to one field.")

    char = {
        "Patient_ID": "Surrogate identifier - drop before modelling",
        "Age": f"Integer 18-90; mean {R['age_summary']['mean']}, SD {R['age_summary']['std']}",
        "Sex": "Binary; Male 637 / Female 632",
        "Visit_Date": "Stored as text in dd-mm-yyyy format",
        "Indication": "Referral reason; the only field with missing values",
        "Medication": "Sedation agent - procedural, not diagnostic",
        "Oesophagus": "Closed set of 5 canned phrases",
        "Stomach": "Closed set of 7 canned phrases",
        "Duodenum": "Closed set of 5 canned phrases",
        "Biopsy": "Closed set of 4 canned phrases",
        "Comments": "Diagnosis field - the natural target",
        "Advice": "Post-hoc management - leakage risk",
    }
    rows = [[c["column"], c["dtype"], f"{c['unique']:,}",
             f"{c['missing']} ({c['missing_pct']}%)",
             f"{c['cardinality_ratio']:.4f}", char[c["column"]]]
            for c in R["column_audit"]]
    table(doc, ["Field", "Type", "Unique", "Missing", "Card. ratio", "Character"], rows,
          "Field-level data dictionary and quality audit. The cardinality ratio is the count "
          "of unique values divided by the number of records.",
          widths=[2.3, 1.2, 1.3, 1.9, 1.7, 7.6], font=7.6,
          note="Only Indication contains missing values (192 records, 15.13%). Missingness is "
               "confined to a single field and shows no association with the diagnosis field, "
               "consistent with a missing-completely-at-random mechanism.")

    figure(doc, "F03_cardinality.png",
           "Column cardinality on a logarithmic scale. Apart from the identifier, the date "
           "field and age, every field holds between two and seven distinct values. The fields "
           "presented as clinical narrative are closed categorical sets.")

    callout(doc, "These are not free-text clinical reports. They are categorical variables "
                 f"expressed as sentences. The entire corpus vocabulary across all narrative "
                 f"fields comprises {B['test5_summary']['corpus_vocabulary_size']} distinct "
                 f"tokens. Term-frequency weighting, lemmatisation and n-gram extraction "
                 f"therefore carry exactly the information of a one-hot encoding on this "
                 f"corpus, and natural language processing cannot be claimed as the "
                 f"methodological contribution of the thesis.",
            title="The central structural fact")

    h(doc, "1.5 Synthetic Data Detection", 2)
    para(doc, "Six tests were specified in advance, each targeting a property that genuine "
              "clinical data reliably exhibits and that naive synthetic generators reliably "
              "fail to reproduce. The battery was implemented once, executed in a single pass, "
              "and is re-runnable end to end.")

    t6 = B["test6_combinatorial_coverage"]
    t1 = B["test1_numeric_uniformity"]
    t3 = B["test3_pairwise_independence"]
    table(doc,
          ["#", "Test", "Method", "Result", "Verdict"],
          [["T1", "Numeric uniformity",
            "KS and chi-square goodness-of-fit of Age against Uniform[18, 90]",
            f"D = {t1['ks_statistic']}, p = {t1['ks_p']}; chi-square = {t1['gof_chi2']}, "
            f"df = {t1['gof_dof']}, p = {t1['gof_p']}", "FAIL"],
           ["T2", "Categorical balance",
            "Chi-square against equiprobability, each categorical field",
            "Equiprobability not rejected in 8 of 9 fields", "FAIL"],
           ["T3", "Pairwise independence", "Bias-corrected Cramer's V across all 36 pairs",
            f"max V = {t3['max_offdiag_cramers_v']}, mean V = "
            f"{t3['mean_offdiag_cramers_v']}; 0 of 36 significant after Bonferroni "
            f"(alpha = {t3['bonferroni_alpha']})", "FAIL"],
           ["T4", "Clinical plausibility",
            "Cross-tabulation of medically coupled findings against diagnosis",
            "No diagonal structure; Stomach x Comments chi-square = 32.45, df = 30, p = 0.347",
            "FAIL"],
           ["T5", "Cardinality", "Unique values per record for each narrative field",
            f"7 narrative fields with ratio below 0.01; total vocabulary = "
            f"{B['test5_summary']['corpus_vocabulary_size']} tokens", "FAIL"],
           ["T6", "Combinatorial coverage",
            "Observed distinct field tuples against the occupancy expectation under uniform "
            "random sampling",
            f"{t6['observed_combinations']} observed vs {t6['expected_unique_if_random']} "
            f"expected (O/E = {t6['observed_over_expected']}); Monte-Carlo 95% interval "
            f"{t6['mc_95_interval_if_random'][0]}-{t6['mc_95_interval_if_random'][1]}", "FAIL"]],
          "Results of the six-test synthetic-data battery. All six tests returned outcomes "
          "inconsistent with genuine clinical data.",
          widths=[0.9, 3.0, 4.6, 5.6, 1.5], font=7.4,
          note="A 'FAIL' verdict denotes failure to behave like authentic clinical data, not a "
               "failure of the test procedure.")

    figure(doc, "F02_integrity_gate_flowchart.png",
           "Integrity gate flowchart. Each test is evaluated in sequence against the raw "
           "dataset; the gate verdict follows from the aggregate outcome.", width=5.7)

    h(doc, "1.5.1 Test 1 - Numeric Plausibility of Age", 3)
    para(doc, f"Age in a genuine upper gastrointestinal endoscopy cohort is not uniformly "
              f"distributed. Referral is driven by symptom prevalence and comorbidity, both of "
              f"which rise with age, so real series characteristically peak between 45 and 65 "
              f"years. Here the Kolmogorov-Smirnov test against Uniform[18, 90] returns "
              f"D = {t1['ks_statistic']} with p = {t1['ks_p']}, providing no evidence against "
              f"uniformity, and a twelve-bin chi-square goodness-of-fit test agrees "
              f"(chi-square = {t1['gof_chi2']}, df = {t1['gof_dof']}, p = {t1['gof_p']}). A "
              f"one-way analysis of variance of age across the six diagnostic categories is "
              f"likewise non-significant (F = {t1['anova_F']}, p = {t1['anova_p']}), meaning "
              f"patients diagnosed with distinct pathologies are indistinguishable by age. "
              f"Both results are clinically implausible and are the expected signature of a "
              f"uniform random draw.")

    figure(doc, "F04_age_uniformity.png",
           "Age distribution against a uniform reference. Left: histogram with the "
           "Uniform[18, 90] expectation overlaid. Right: quantile-quantile plot; the "
           "observations lie along the 45-degree line, confirming uniformity.")

    h(doc, "1.5.2 Tests 2 and 3 - Balance and Pairwise Independence", 3)
    para(doc, "Genuine clinical categories are unbalanced, because disease prevalence is "
              "unbalanced. Here equiprobability could not be rejected in eight of the nine "
              "categorical fields, the sole exception being Indication (p = 0.0391), which "
              "does not survive correction for multiple comparison. More decisively, the "
              "fields are mutually independent.")

    rows = [[p["column"], p["k"], f"{p['min_count']}-{p['max_count']}",
             f"{p['imbalance_ratio']:.3f}", f"{p['chi2']:.2f}", p["dof"],
             f"{p['p']:.4f}", "Not rejected" if p["equiprobable_not_rejected"] else "Rejected"]
            for p in B["test2_categorical_balance"]]
    table(doc, ["Field", "k", "Count range", "Imbalance", "Chi-square", "df", "p",
                "Equiprobability"], rows,
          "Test of equiprobability within each categorical field. An imbalance ratio near 1.0 "
          "indicates near-equal category frequencies.",
          widths=[2.6, 0.9, 2.2, 1.8, 1.9, 0.9, 1.6, 3.0], font=7.6,
          align_right={1, 3, 4, 5, 6})

    para(doc, f"The association matrix is the core evidence figure of Phase 0. Cramer's V was "
              f"computed with the Bergsma bias correction, which is more conservative than the "
              f"uncorrected statistic and is appropriate for sparse contingency tables. Across "
              f"all 36 variable pairs the maximum value is {t3['max_offdiag_cramers_v']} and "
              f"the mean is {t3['mean_offdiag_cramers_v']}; values below 0.10 are "
              f"conventionally regarded as negligible. Two pairs reach p < 0.05 uncorrected "
              f"against a chance expectation of {t3['expected_by_chance']}, and neither "
              f"survives Bonferroni correction.")

    figure(doc, "F05_association_heatmaps.png",
           "Pairwise association structure. Left: bias-corrected Cramer's V for all 36 "
           "variable pairs, uniformly near zero. Right: corresponding chi-square p-values; "
           "asterisks mark the two pairs significant at the uncorrected 5% level, neither of "
           "which survives correction for multiple comparison.")

    rows = [[f["feature"], f"{f['chi2']:.2f}", f["dof"], f"{f['p']:.4f}",
             f"{f['cramers_v']:.4f}", f"{f['mi_nats']:.4f}"]
            for f in B["feature_target_association"]]
    table(doc, ["Feature", "Chi-square", "df", "p", "Cramer's V",
                "Mutual information (nats)"], rows,
          "Association between each candidate feature and the diagnosis field. Every effect "
          "size is negligible and every mutual information value is close to zero.",
          widths=[3.4, 2.4, 1.3, 2.2, 2.6, 4.1], font=7.8, align_right={1, 2, 3, 4, 5},
          note="Cramer's V is bias-corrected; values reported as 0.0000 arise where the "
               "correction reduces a negligible raw association to zero. Records with a "
               "missing Indication value were excluded pairwise from that row's test.")

    h(doc, "1.5.3 Test 4 - Clinical Plausibility", 3)
    para(doc, "This is the most persuasive test in the battery. In a genuine endoscopy record "
              "the stomach finding and the diagnostic impression are two records of the same "
              "observation: a report describing 'ulcer with recent bleeding' in the stomach "
              "field and 'bleeding peptic ulcer' in the diagnosis field is not a coincidence "
              "but a near-tautology. A cross-tabulation of these two fields in real data "
              "therefore shows pronounced diagonal structure. Here the two fields are "
              "statistically independent (chi-square = 32.45, df = 30, p = 0.347), and the "
              "mean maximum row proportion is 0.2128 against a uniform expectation of 0.1667. "
              "Independence between a finding and the diagnosis it directly implies cannot "
              "arise in authentic clinical data.")

    figure(doc, "F06_mosaic_stomach_diagnosis.png",
           "Stomach finding against diagnosis, row-normalised. The absence of a bright "
           "diagonal indicates that the recorded finding carries no information about the "
           "recorded diagnosis.")

    h(doc, "1.5.4 Tests 5 and 6 - Cardinality and Combinatorial Coverage", 3)
    para(doc, f"Seven fields presented as clinical narrative contain between two and seven "
              f"distinct sentences each, giving cardinality ratios below 0.01 and a combined "
              f"corpus vocabulary of {B['test5_summary']['corpus_vocabulary_size']} tokens. "
              f"Test 6 sharpens this into a formal comparison. Given "
              f"{t6['possible_combinations']} possible combinations of the four finding fields "
              f"and {PROV['n_rows']:,} records, the classical occupancy expectation for the "
              f"number of distinct combinations observed under independent uniform sampling is "
              f"{t6['expected_unique_if_random']}. The observed count is "
              f"{t6['observed_combinations']}, an observed-to-expected ratio of "
              f"{t6['observed_over_expected']}, falling well inside the Monte-Carlo 95% "
              f"interval of {t6['mc_95_interval_if_random'][0]}-"
              f"{t6['mc_95_interval_if_random'][1]} obtained from 2,000 simulated datasets. "
              f"Authentic clinical corpora fall far below this expectation, because clinically "
              f"coherent combinations recur and incoherent ones never occur. The corpus is "
              f"quantitatively indistinguishable from independent uniform draws.")

    h(doc, "1.6 Leakage Analysis", 2)
    para(doc, f"The prior analysis notebook derives its target, disease_label, by applying "
              f"seven regular-expression rules to the Comments, Oesophagus, Stomach and "
              f"Duodenum fields, then constructs the model input by concatenating those same "
              f"fields and vectorising the result. The label is therefore a deterministic "
              f"function of the input. This was confirmed directly: all "
              f"{L['determinism_check']['unique_feature_combinations']:,} unique feature "
              f"combinations map to exactly one label "
              f"({L['determinism_check']['pct_deterministic']}% deterministic).")

    para(doc, "Three experiments quantify the leak. Their pattern is more instructive than the "
              "headline number and constitutes a substantive correction to the expectation "
              "recorded in the blueprint.")

    maj = L["majority_baseline_disease_label"]
    table(doc,
          ["ID", "Configuration", "Fields supplied to the model", "5-fold CV accuracy",
           "Delta vs. baseline"],
          [["E03", "Notebook as written",
            "Indication, Oesophagus, Stomach, Duodenum, Biopsy, Comments, Medication",
            f"{L['E03_notebook_with_comments']['accuracy']:.4f} "
            f"(SD {L['E03_notebook_with_comments']['std']:.4f})",
            f"+{L['E03_notebook_with_comments']['accuracy'] - maj:.4f}"],
           ["E04", "Comments removed",
            "Indication, Oesophagus, Stomach, Duodenum, Biopsy, Medication",
            f"{L['E04_comments_removed']['accuracy']:.4f} "
            f"(SD {L['E04_comments_removed']['std']:.4f})",
            f"+{L['E04_comments_removed']['accuracy'] - maj:.4f}"],
           ["E05", "All label-constituent fields removed",
            "Indication, Medication, Biopsy",
            f"{L['E05_all_label_constituents_removed']['accuracy']:.4f} "
            f"(SD {L['E05_all_label_constituents_removed']['std']:.4f})",
            f"{L['E05_all_label_constituents_removed']['accuracy'] - maj:.4f}"],
           ["-", "Majority-class baseline", "-", f"{maj:.4f}", "0.0000"]],
          "Leakage audit. The target is the rule-derived disease_label and the baseline is the "
          "majority class of that label.",
          widths=[1.0, 3.6, 5.1, 3.1, 2.2], font=7.5)

    figure(doc, "F08_leakage_cascade.png",
           "The leakage cascade. Removing the Comments field alone leaves most of the artefact "
           "intact, because the finding fields independently encode the labelling rules. Only "
           "removing every label-constituent field exposes true performance, which lies below "
           "the majority-class baseline.", width=5.4)

    callout(doc, f"The blueprint anticipated that removing Comments would collapse accuracy "
                 f"from 1.000 to approximately 0.19. Direct measurement shows it falls only to "
                 f"{L['E04_comments_removed']['accuracy']:.4f}. The discrepancy is "
                 f"methodologically important: leakage in this pipeline is distributed across "
                 f"four fields rather than concentrated in one, so the intuitive "
                 f"single-column remedy is insufficient. The corrected figure is used "
                 f"throughout this report.",
            title="Correction to the anticipated result")

    para(doc, "The honest performance ceiling was then established using the diagnosis field "
              "itself as the target and only admissible features as inputs.")

    hb = L["honest_baselines_target_comments"]
    order = [("E00a", "Dummy classifier (most frequent)", "E00a_dummy_most_frequent"),
             ("E00b", "Dummy classifier (stratified)", "E00b_dummy_stratified"),
             ("E01", "Logistic regression, one-hot", "E01_logistic_regression"),
             ("E01b", "Random forest (300 trees)", "E01b_random_forest"),
             ("E01c", "Gradient boosting", "E01c_gradient_boosting"),
             ("E02", "TF-IDF with linear SVC on report text", "E02_tfidf_linearsvc")]
    rows = [[i, n, f"{hb[k]['accuracy']:.4f}",
             f"{hb[k]['std']:.4f}" if hb[k]["std"] is not None else "-",
             f"{hb[k]['accuracy'] - hb['majority_baseline']['accuracy']:+.4f}"]
            for i, n, k in order]
    rows.append(["-", "Majority-class baseline",
                 f"{hb['majority_baseline']['accuracy']:.4f}", "-", "0.0000"])
    rows.append(["-", "Random guessing (1 of 6)",
                 f"{hb['random_baseline']['accuracy']:.4f}", "-",
                 f"{hb['random_baseline']['accuracy'] - hb['majority_baseline']['accuracy']:+.4f}"])
    rows.append(["E07", "Random-noise features (sanity control)",
                 f"{L['E07_random_noise_control']['accuracy']:.4f}",
                 f"{L['E07_random_noise_control']['std']:.4f}",
                 f"{L['E07_random_noise_control']['accuracy'] - hb['majority_baseline']['accuracy']:+.4f}"])
    table(doc, ["ID", "Model", "Accuracy", "SD", "Delta vs. majority"], rows,
          "Honest baselines with the diagnosis field as target and only admissible features as "
          "input. No model exceeds the majority-class baseline.",
          widths=[1.3, 6.6, 2.4, 2.2, 2.5], font=7.9, align_right={2, 3, 4},
          note="E07 supplies Gaussian noise of identical shape to the one-hot design matrix. "
               "That it matches the trained models confirms the models are fitting noise.")

    figure(doc, "F19_honest_baselines.png",
           "Honest baseline performance. Every model, including gradient boosting and a "
           "term-frequency text classifier, performs at or below the majority-class baseline.",
           width=5.6)

    h(doc, "1.6.1 Formal Test for the Absence of Signal", 3)
    para(doc, f"Reporting that models perform poorly is weaker than demonstrating that no "
              f"learnable relationship exists. A label-permutation test was therefore "
              f"conducted following Ojala and Garriga (2010): the target was randomly permuted "
              f"and the full cross-validation repeated {PT['n_permutations']:,} times to build "
              f"an empirical null distribution. The observed accuracy of "
              f"{PT['real_score']:.4f} lies at the {PT['percentile_of_real']:.0f}th percentile "
              f"of that null (mean {PT['null_mean']:.4f}, SD {PT['null_std']:.4f}), giving "
              f"p = {PT['p_value']:.3f}. The null hypothesis that features and target are "
              f"independent cannot be rejected; the observed score in fact lies below the null "
              f"mean.")

    figure(doc, "F09_permutation_test.png",
           "Label-permutation null distribution over 1,000 iterations. The observed score "
           "falls inside the body of the null distribution, formally establishing the absence "
           "of a learnable feature-target relationship.", width=5.4)

    h(doc, "1.7 Label-Construction Audit", 2)
    para(doc, "Leakage and label quality are separate defects, and the second proved as "
              "consequential as the first. The labelling function evaluates seven independent "
              "rules and resolves conflicts by fixed priority order, defaulting to 'Normal' "
              "when no rule fires. Both behaviours are undocumented in the original code and "
              "both distort the resulting target.")

    d, pc = LA["match_count_distribution"], LA["match_count_pct"]
    table(doc, ["Rules satisfied simultaneously", "Records", "Percentage", "Consequence"],
          [["0", d["0"], f"{pc['0']}%",
            "Forced to 'Normal' by the fallback - health asserted without evidence"],
           ["1", d["1"], f"{pc['1']}%", "Unambiguous - the only cleanly labelled subset"],
           ["2", d["2"], f"{pc['2']}%", "Collapsed by priority order; comorbidity discarded"],
           ["3", d["3"], f"{pc['3']}%", "Collapsed by priority order; comorbidity discarded"],
           ["4", d["4"], f"{pc['4']}%", "Collapsed by priority order; comorbidity discarded"]],
          "Distribution of simultaneous rule matches produced by the labelling function.",
          widths=[4.4, 1.9, 2.2, 7.5], font=7.9, align_right={1, 2},
          note=f"Only {LA['pct_unambiguous']}% of the corpus carries an unambiguous single "
               f"label. Mean label cardinality among records matching at least one rule is "
               f"{LA['label_cardinality_mean']}.")

    figure(doc, "F10_rule_match_histogram.png",
           "Rule-match count distribution. The single-label formulation adopted by the prior "
           "notebook is appropriate for only a third of the corpus.", width=5.4)

    para(doc, f"The consequences are quantifiable. {LA['n_multi_match']} records "
              f"({LA['pct_multi_match']}%) satisfy two or more disease rules and are reduced "
              f"to a single label by priority order, so a patient recorded with both gastritis "
              f"and duodenal ulceration is represented as having only the higher-priority "
              f"condition. A further {LA['n_zero_match_forced_normal']} records "
              f"({LA['pct_zero_match']}%) satisfy no rule and are assigned 'Normal'. These are "
              f"not healthy patients; they are unclassifiable records. Any recall figure "
              f"subsequently reported for the 'Normal' class is corrupted by this "
              f"substitution.")

    figure(doc, "F11_label_cooccurrence.png",
           "Rule co-occurrence matrix. Structured off-diagonal mass demonstrates that "
           "multi-label formulation, not single-label collapse, is the clinically correct "
           "representation.", width=4.5)

    dist = LA["derived_label_distribution"]
    table(doc, ["Derived label", "Records", "Share of corpus"],
          [[k, v, f"{100 * v / PROV['n_rows']:.1f}%"] for k, v in dist.items()],
          "Distribution of the collapsed single-label target produced by the prior notebook.",
          widths=[5.0, 2.6, 3.0], font=8.0, align_right={1, 2},
          note=f"Imbalance ratio {LA['derived_imbalance_ratio']}:1. This distribution is "
               f"determined by the collapse procedure, not by disease prevalence.")

    h(doc, "1.8 Feature Provenance and the Leakage Firewall", 2)
    para(doc, "Every field was classified by its relationship to the label and by its "
              "temporality relative to the moment of prediction. This table is the operative "
              "control preventing leakage from re-entering during later phases: any field "
              "marked BLOCKED may not be supplied to a model trained on the rule-derived "
              "target.")
    rows = [[f["column"], f["class"], f["temporality"], f["admissibility"], f["justification"]]
            for f in R["feature_provenance"]]
    table(doc, ["Field", "Provenance class", "Temporality", "Admissibility", "Justification"],
          rows,
          "Feature provenance table. All twelve fields are classified; four are blocked as "
          "label-constituent or post-hoc.",
          widths=[2.2, 2.9, 2.4, 3.2, 5.3], font=7.3,
          note="Exported to docs/feature_provenance.csv. Advice is blocked as a post-hoc "
               "field: management is decided after the diagnosis is known, so its availability "
               "at prediction time cannot be assumed.")

    h(doc, "1.9 Ethics and De-identification", 2)
    para(doc, "An ethics and de-identification assessment was completed irrespective of the "
              "provenance outcome, because the appropriate handling of the file differs "
              "according to whether it is real or synthetic and that question is unresolved.")

    table(doc, ["Item", "Assessment", "Status", "Required action"],
          [["Direct identifiers",
            f"Patient_ID follows the pattern {ETH['patient_id_format']} and is strictly "
            f"sequential, consistent with a surrogate key rather than a medical record number",
            "Acceptable", "Confirm in writing that it is not a medical record number"],
           ["Quasi-identifier triple",
            "Age, Sex and Visit_Date jointly constitute a re-identification risk",
            "Attention required", "Bin age into 5-year bands and coarsen dates before release"],
           ["k-anonymity (age band, sex, visit month)",
            f"k = {ETH['k_anonymity_age5_sex_month']} across "
            f"{ETH['n_equivalence_classes_month']} equivalence classes; "
            f"{ETH['pct_classes_below_k5_month']}% of classes fall below k = 5",
            "FAILS k = 5", "Do not release at monthly granularity"],
           ["k-anonymity (age band, sex, visit year)",
            f"k = {ETH['k_anonymity_age5_sex_year']} across "
            f"{ETH['n_equivalence_classes_year']} equivalence classes; "
            f"{ETH['pct_classes_below_k5_year']}% of classes fall below k = 5",
            "Marginal", "Suppress or merge small classes before release"],
           ["Date shifting", "Not applied; dates are recorded verbatim", "Pending",
            "Apply a consistent per-patient offset if the data prove to be real"],
           ["Repository hygiene",
            "The source file must never be committed to version control", "Action required",
            "Add data/raw/ to .gitignore and verify with git log --all --stat"],
           ["Ethics statement", "Required in the thesis under every route", "Pending",
            "If synthetic, state so explicitly - that is a valid ethics statement"]],
          "Ethics and de-identification checklist.",
          widths=[3.4, 5.4, 2.2, 5.0], font=7.4,
          note="The k-anonymity results are a genuine finding: at monthly date granularity the "
               "dataset would not be safe to release even if fully synthetic, because "
               "releasing it as though it were patient data would misrepresent its risk "
               "profile.")

    h(doc, "1.10 Sample Size, Power and Split Integrity", 2)
    para(doc, "Two structural constraints were measured because they bound what any later "
              "phase can legitimately claim.")
    si = R["split_integrity"]
    table(doc, ["Property", "Measured value", "Reference standard", "Assessment"],
          [["Records", f"{POW['n_total']:,}", "-", "-"],
           ["Outcome classes", POW["n_classes"], "-", "-"],
           ["Smallest class", POW["smallest_class"], "-", "-"],
           ["One-hot predictors", POW["n_onehot_predictors"], "-", "-"],
           ["Events per variable", POW["events_per_variable"],
            f"Riley et al. minimum {POW['riley_minimum_epv']}", "INADEQUATE - underpowered"],
           ["Test-set size at 15%", POW["test_set_15pct"], "-", "-"],
           ["95% CI half-width at accuracy 0.18",
            f"{POW['ci_halfwidth_at_acc_018']} pp", "-",
            "Wide relative to any plausible effect"],
           ["95% CI half-width at accuracy 0.50",
            f"{POW['ci_halfwidth_at_acc_050']} pp", "-", "Wide"],
           ["Unique feature tuples", f"{si['unique_feature_tuples']:,}", "-", "-"],
           ["Rows sharing identical feature text",
            f"{si['n_rows_in_repeating_tuples']} ({si['pct_rows_affected']}%)",
            "Zero overlap between splits", "Grouped splitting mandatory"]],
          "Sample-size, power and split-integrity facts.",
          widths=[5.0, 3.4, 3.6, 4.0], font=7.6,
          note=f"An events-per-variable ratio of {POW['events_per_variable']} against an "
               f"accepted minimum of 10 to 20 means the modelling problem is underpowered "
               f"before any algorithmic choice is made.")

    h(doc, "1.11 Route Decision", 2)
    para(doc, "The blueprint specifies three routes and a decision procedure. The evidence "
              "assembled above determines the outcome without discretion: the provider has not "
              "confirmed the data as real, and the independence tests show zero signal.")

    table(doc, ["Criterion", "Route A - Reframe", "Route B - Re-collect", "Route C - Proceed"],
          [["Claim", "Rule-based and machine-learning pipeline for structuring templated "
                     "reports, with an honest negative result",
            "Automatic GI classification from genuine free-text reports",
            "High-accuracy automatic classification"],
           ["Effort", "4-6 weeks", "8-12 weeks plus ethics approval", "None"],
           ["Risk", "Low - every claim is defensible", "Medium - ethics timeline",
            "Fatal - the central claim is an artefact"],
           ["Publication ceiling", "Workshop or student track", "Journal or conference",
            "None"],
           ["Decision", "ADOPTED", "Pursue in parallel if time allows", "REJECTED"]],
          "Route comparison and decision.",
          widths=[2.8, 4.6, 4.4, 4.2], font=7.6)

    figure(doc, "F12_route_decision.png",
           "Route decision procedure, with the path taken by this study terminating in the "
           "Route A node.", width=5.8)

    h(doc, "1.12 Phase 0 Validation Checklist", 2)
    table(doc, ["Criterion", "Required standard", "Outcome"],
          [["Provenance resolved", "Written statement obtained, or documented non-response",
            "PARTIAL - non-response recorded; statement outstanding"],
           ["Battery complete", "6 of 6 tests executed and interpreted", "MET - 6 of 6"],
           ["Leakage quantified", "Numeric delta reported, not described qualitatively",
            f"MET - {L['E03_notebook_with_comments']['accuracy']:.4f} to "
            f"{L['E05_all_label_constituents_removed']['accuracy']:.4f}"],
           ["Feature classification", "All twelve fields classified",
            f"MET - {R['feature_provenance_summary']['n_classified']} of 12"],
           ["Absence of signal", "Formal test rather than description",
            f"MET - permutation test, p = {PT['p_value']:.3f}"],
           ["Label quality audited", "Ambiguity and default behaviour quantified",
            f"MET - {LA['pct_unambiguous']}% unambiguous"],
           ["Ethics checklist", "Completed", "MET - with two actions outstanding"],
           ["Route locked", "Supervisor-signed decision on file",
            "PENDING SIGNATURE - Route A recommended on the evidence"]],
          "Phase 0 validation checklist against the blueprint success criteria.",
          widths=[3.8, 5.4, 6.8], font=7.8)

    h(doc, "1.13 Phase 0 Discussion", 2)
    para(doc, "Three points deserve emphasis. First, no single test in the battery would be "
              "conclusive alone. Uniform age might reflect an unusual sampling frame; balanced "
              "classes might reflect deliberate case selection. What cannot be explained away "
              "is the conjunction: uniform age, balanced categories, mutual independence "
              "across all 36 variable pairs, absent findings-to-diagnosis coupling, a "
              "71-token vocabulary, and a distinct-tuple count matching the occupancy "
              "expectation for uniform random sampling to within one percent. Each is "
              "individually suspicious; jointly they admit only one parsimonious explanation.")
    para(doc, "Second, the leakage finding is more subtle than anticipated and is the more "
              "useful for it. A candidate who reports only that removing the diagnosis column "
              "destroys performance has demonstrated awareness of leakage. A candidate who "
              "demonstrates that removing the diagnosis column is insufficient, and identifies "
              "the three further fields through which the label re-enters, has demonstrated "
              "command of it. The distinction is exactly what separates a descriptive audit "
              "from a methodological contribution.")
    para(doc, "Third, the label-construction defect is independent of both the synthetic-data "
              "finding and the leakage finding, and would remain a problem even on authentic "
              "data. A labelling function that silently collapses 61.62% of its cases and "
              "invents a healthy category for a further 6.38% would corrupt any downstream "
              "evaluation regardless of corpus provenance. This is the finding with the widest "
              "applicability beyond the present dataset.")

    h(doc, "1.14 Phase 0 Conclusion", 2)
    para(doc, f"The integrity gate did not clear. The corpus is quantitatively "
              f"indistinguishable from independent uniform random draws; the prior pipeline's "
              f"reported accuracy of {L['E03_notebook_with_comments']['accuracy']:.4f} is "
              f"wholly attributable to target leakage distributed across four fields; the "
              f"labelling function produces an unambiguous label for only "
              f"{LA['pct_unambiguous']}% of records; and a "
              f"{PT['n_permutations']:,}-iteration permutation test formally fails to reject "
              f"the hypothesis that no learnable feature-target relationship exists "
              f"(p = {PT['p_value']:.3f}). Route A is adopted. All downstream phases proceed "
              f"under the feature provenance constraints established in Section 1.8, and no "
              f"performance figure derived from a label-constituent field may be reported as a "
              f"diagnostic result.")
