# Dataset Viability Assessment and Replacement Recommendation

## Phase 1.5 — Decision Report

**Project:** Fourth-year B.Sc. thesis, AI for upper gastrointestinal endoscopy
**Prepared:** 26 July 2026
**Status of prior work:** Phase 0 (integrity gate) and Phase 1 (literature review) complete — `Phase0_Phase1_Report.pdf`
**Decision required:** Continue with `Peptic Ulcer_Dataset.xlsx`, or replace it

---

## 0. Executive Summary

**Verdict: Do not continue with the current dataset. Replace it.**

The current dataset is not a weak dataset. It is a dataset with **zero measured predictive signal**, whose apparent 100% accuracy is an artefact of the label being computed from the features. Both properties are now quantified, not suspected:

| Question | Measured answer |
|---|---|
| Can any model beat chance on this data? | No. Best model 0.1608 vs. majority 0.1828, random 0.1667. Permutation test **p = 0.762** (24th percentile of the null) |
| Is the reported 100% accuracy real? | No. E03 = 1.0000 → E05 (label-constituent fields removed) = **0.2482**, *below* the 0.2671 majority baseline |
| Can preprocessing / feature engineering / augmentation fix it? | **No.** Not one of the twelve defects is remediable. Seven are structurally unfixable |
| Is it publishable as a diagnostic result? | **No.** It would not survive peer review, and presenting it as diagnostic accuracy would be a misrepresentation |

**Recommended replacement: GastroHUN** (*Scientific Data*, Nature, January 2025) — 8,834 upper-GI endoscopy images from 387 patients, **each image independently labelled by four expert annotators whose individual labels are all retained**, with official patient-level splits, ethics approval, informed consent, and a CC BY 4.0 licence.

**Recommended thesis direction:** exploit the four-annotator structure that no other public upper-GI dataset provides. GastroHUN's own authors state that their published benchmark **tests only on images where all four experts agreed** — an explicitly acknowledged, currently unfilled gap in an 18-month-old dataset. That gap is your thesis.

**Working title:**

> *Agreement-Aware Deep Learning for Systematic Screening of the Stomach: Treating Expert Disagreement as Signal Rather Than Noise in Upper Gastrointestinal Endoscopy*

**Critically: none of your Phase 0/Phase 1 work is lost.** The integrity battery, leakage firewall, permutation testing, grouped splitting, calibration and reporting machinery all transfer unchanged, and become a *methodological contribution* rather than scaffolding. Section 8 details the transfer.

---

# PART I — Complete Analysis of the Current Dataset

## 1.1 Provenance and Structure (measured)

| Property | Value |
|---|---|
| File | `Peptic Ulcer_Dataset.xlsx` |
| SHA-256 | `c259fb1fbe402f2223b1fd46fc7cd3eef2568270e32ce55ee21c42d190d8a301` |
| Size | 88,842 bytes |
| Shape | 1,269 rows × 12 columns |
| Exact duplicates | 0 |
| Unique `Patient_ID` | 1,269 (sequential surrogate `PID00001`…) |
| Date range | 2024-01-01 → 2025-10-12 (650 days, 8 quarters) |
| Documented provenance | **None.** No data dictionary, no collection protocol, no named source, no ethics approval, no consent statement |
| Total corpus vocabulary | **71 distinct words** |

The absence of provenance is itself a finding. A dataset with no attributable origin cannot support an ethics statement, and no reputable venue will publish a clinical claim derived from it.

## 1.2 The Twelve Defects

Each defect below is stated with the measurement that establishes it. Severity: **Fatal** = invalidates any clinical claim; **Severe** = invalidates a specific analysis; **Material** = degrades quality.

---

### D1 — Zero predictive signal (Fatal)

Every model tested on the honest task (predict `Comments` from the other fields, no label-constituent leakage) performs **at or below chance**:

| Model | 5-fold CV accuracy |
|---|---|
| Majority-class baseline | 0.1828 |
| Random baseline (1/6) | 0.1667 |
| Random-noise control | 0.1789 ± 0.0304 |
| Logistic regression | **0.1608 ± 0.0114** |
| Random forest | 0.1576 ± 0.0183 |
| Gradient boosting | 0.1615 ± 0.0139 |
| TF-IDF + LinearSVC | 0.1592 ± 0.0232 |

Every learner is **below the majority baseline**. A model fitted to pure random noise (0.1789) outperforms all of them.

The permutation test settles it. Over 1,000 label shuffles: null mean 0.1700, SD 0.0120. The observed 0.1608 sits at the **24th percentile**, **p = 0.7622**. Formally: we cannot reject the hypothesis that the features and the target are independent. The data behaves exactly as random-label data behaves.

---

### D2 — Circular label construction with multi-source leakage (Fatal)

The notebook derives `disease_label` by regular expression over `Comments`, `Oesophagus`, `Stomach`, `Duodenum` — then uses those same four fields as features. The ablation:

| Experiment | Features | Accuracy |
|---|---|---|
| E03 — as written | all, incl. `Comments` | **1.0000 ± 0.0000** |
| E04 — drop `Comments` | 5 fields | **0.9165 ± 0.0015** |
| E05 — drop all four label constituents | `Indication`, `Medication`, `Biopsy` | **0.2482 ± 0.0123** |
| Majority baseline | — | 0.2671 |

Two things to notice, in order of how badly they hurt at a defence:

1. **The obvious remedy fails.** Dropping `Comments` — the fix any examiner will propose first — still leaves 91.65%, because the three anatomical finding fields independently re-encode the same regex rules.
2. **When leakage is fully removed, the model falls *below* the majority baseline** (0.2482 < 0.2671). There is nothing underneath the leakage.

The determinism check confirms the mechanism: 1,258 unique feature combinations, **100% of which map to exactly one label**. The mapping is a lookup table, not a learned function. A 1.0000 accuracy with 0.0000 standard deviation across folds is the signature of a deterministic function, not a classifier.

---

### D3 — Statistical independence between clinically coupled fields (Fatal)

In real endoscopy, the impression follows near-deterministically from the findings. Here:

- 36 pairwise χ² tests between categorical fields: **2 significant** at uncorrected α = 0.05 (chance expectation 1.8). **Zero** survive Bonferroni correction (α = 0.001389).
- Maximum off-diagonal Cramér's V = **0.0639**; mean = **0.0181**. All below 0.10.
- Every feature-vs-target association ≤ 0.088.

The fields were sampled independently. This is not a property real clinical data can have.

---

### D4 — Clinically impossible records (Fatal)

- **220 records (17.3%)** state the impression *"Normal upper GI findings."* while simultaneously documenting a pathological stomach — e.g. *"Large ulcer with adherent clot."*
- **Zero records** describe a normal stomach. The `Normal` class is therefore empty in the realised task, and 220 records assert normality that the same record contradicts.

No clinician wrote these. No de-noising procedure can repair a record that contradicts itself, because there is no ground truth to repair it toward.

---

### D5 — Combinatorial occupancy consistent with uniform random generation (Fatal)

Across the four finding fields (5 × 7 × 5 × 4 = 700 possible combinations):

| Quantity | Value |
|---|---|
| Observed distinct combinations | 580 |
| Expected if sampled uniformly at random | 585.9 |
| Monte-Carlo 95% interval | [570, 601] |
| Observed / Expected | **0.9899** |

The observed occupancy is statistically indistinguishable from uniform random sampling. Real clinical data is enormously clustered — a handful of syndromic combinations dominate and most cells are empty. This is the single most direct quantitative evidence of synthetic generation, and it is far stronger than a raw coverage percentage.

Supporting evidence: `Age` is Uniform[18, 90] (KS D = 0.0225, **p = 0.5366**). Real endoscopy populations are right-skewed toward 55–75. Here the mean age is 53.8 — the midpoint of the sampling range.

---

### D6 — Defective label semantics (Severe)

Applying the notebook's own rules:

| Rules matched | Records | % |
|---|---|---|
| 0 | 81 | 6.38 |
| 1 | 406 | 31.99 |
| 2 | 528 | 41.61 |
| 3 | 233 | 18.36 |
| 4 | 21 | 1.65 |

- **782 records (61.6%)** satisfy two or more disease rules and are silently collapsed by priority order — the second and third diagnoses are discarded without record.
- **81 records (6.4%)** satisfy *no* rule and are defaulted to `Normal` by the `len(matches)==0` fallback. The pipeline **fabricates 81 healthy patients** out of unmatched text.
- Only **32.0%** of the corpus carries an unambiguous single label. Mean label cardinality = 1.89.

A single-label multi-class formulation is the wrong model of the data even on the data's own terms.

---

### D7 — Statistically underpowered (Severe)

| Quantity | Value |
|---|---|
| n | 1,269 |
| Classes (`Comments` target) | 6 |
| Smallest class | 190 |
| One-hot predictors | 33 |
| **Events per variable** | **5.76** |
| Riley et al. minimum | 10–20 |
| 15% test set | 190 records |
| 95% CI half-width at acc 0.18 | ±5.46 pp |
| 95% CI half-width at acc 0.50 | ±7.11 pp |

At EPV = 5.76 the model is underpowered by a factor of roughly 2–3.5×. A test set of 190 cannot distinguish 0.50 from 0.57 — so even a genuine effect could not be demonstrated at this sample size.

---

### D8 — Degenerate feature space (Severe)

Seven of the twelve columns have cardinality ratio below 0.01. `Medication` has 3 values; `Sex` 2; the finding fields 5–7 each. The entire corpus vocabulary is **71 words**.

This is fatal specifically for the NLP framing. TF-IDF over a 71-word closed vocabulary is not text mining — it is one-hot encoding with extra steps. There is no morphology, no negation, no hedging, no abbreviation, no misspelling, no dictation error: none of the phenomena that make clinical NLP a research problem exist in this corpus.

---

### D9 — Missing data (Material)

`Indication` is missing in **192 records (15.13%)**. All other columns are complete. Missingness is unexplained and, given synthetic generation, is almost certainly MCAR by construction — which perversely makes it *less* interesting than real clinical missingness, not more. It cannot support a missing-data methods contribution.

---

### D10 — Ethics and re-identification exposure (Severe, conditional)

| Quasi-identifier set | k-anonymity | Classes below k = 5 |
|---|---|---|
| (Age-5yr, Sex, Visit-month) | **k = 1** | **93.68%** of 570 classes |
| (Age-5yr, Sex, Visit-year) | k = 1 | 6.25% of 64 classes |

If the data were real, it would be **unpublishable and unshareable as-is**: nearly every record is uniquely identifiable on three ordinary quasi-identifiers. If it is synthetic, this is moot — but then there is no clinical claim to make. Either branch blocks publication.

There is no ethics approval, no consent documentation, and no data-use agreement on file.

---

### D11 — Split contamination risk (Material)

1,257 unique feature tuples across 1,269 rows; 12 tuples repeat, affecting 24 rows (1.89%). Random splitting places identical feature vectors on both sides of the split. Grouped splitting is mandatory. This one *is* fixable — it is listed for completeness, and because it is the only defect in this table that is.

---

### D12 — No external validity (Fatal)

There is no second site, no second time period usable as a true holdout, no comparator dataset, and no real-world population the data represents. A model trained here can be validated only against itself. Every modern reporting standard — TRIPOD+AI, CLAIM, STARD-AI — treats external validation as a core requirement for a clinical prediction claim.

---

## 1.3 Can These Be Fixed? Remediation Analysis

The user's question is the right one: are these defects *engineering* problems or *data* problems? Assessed technique by technique:

| Proposed remedy | Targets | Verdict | Technical reason it fails |
|---|---|---|---|
| **Drop leaking columns** | D2 | ❌ Fails | Measured. E05 = 0.2482 < 0.2671 majority. Removing leakage removes the entire signal, because the signal *was* the leakage |
| **Better feature engineering** | D1, D8 | ❌ Impossible | Feature engineering is a transformation of existing information. Mutual information between features and target is ~0 (all V ≤ 0.088); no measurable transformation increases the information content of a variable |
| **TF-IDF / n-grams / embeddings** | D8 | ❌ Fails | 71-word closed vocabulary, 5–7 fixed strings per field. Any text representation is a bijection onto one-hot codes. BERT on 71 words learns nothing beyond a lookup |
| **SMOTE / ADASYN** | D6 | ❌ Inapplicable | Imbalance ratio is 1.22:1 for `Comments` and 3.57:1 for the derived label — neither warrants resampling. Interpolating in one-hot space produces invalid records ("0.4 of an antral ulcer") and destroys calibration |
| **EDA / synonym replacement** | D7, D8 | ❌ Harmful | Substituting synonyms into a closed clinical vocabulary invents phrasings the source system cannot emit. Inflates apparent lexical diversity while adding zero information |
| **Back-translation** | D7 | ❌ Harmful | Round-trip translation corrupts clinical terminology and, again, adds no information — augmentation cannot create signal that the source lacks |
| **LLM paraphrase / synthetic expansion** | D7 | ❌ Harmful & circular | Generating more synthetic data from synthetic data. Would require disclosure at review and instantly invalidates the clinical claim |
| **Multi-label reformulation** | D6 | 🟡 Correct but insufficient | It *is* the right formulation, and it fixes D6. It does not touch D1–D5. A correctly formulated model of noise is still a model of noise |
| **Grouped / temporal splitting** | D11 | ✅ Works | The only fully remediable defect. Costs one line of code and fixes nothing else |
| **Calibration, Platt / isotonic** | — | 🟡 Applicable | You can calibrate a chance-level classifier. It remains chance-level |
| **Transfer learning / pretrained LM** | D1, D7 | ❌ Fails | Pretraining supplies a prior over language, not a relationship between these features and this target. The target is independent of the features (p = 0.762) |
| **Collect more of the same data** | D7 | ❌ Fails | More samples from a generator with zero signal converge on zero signal with tighter confidence intervals |
| **Obtain real labels for these records** | D1–D6 | ❌ Impossible | The *records themselves* are fabricated. There is no patient, no image, no procedure to relabel against |

**Conclusion of the remediation analysis:** of twelve defects, **one** (D11) is fixable. Seven are unfixable in principle because they are properties of the data-generating process, not of the pipeline. The remaining four are fixable only in form, not in consequence.

This is the decisive point, and it is worth stating precisely for your defence:

> Preprocessing, feature engineering, and augmentation are all **information-preserving or information-destroying** operations. None is information-*creating*. The Data Processing Inequality makes this formal: for any transformation *T* applied to features *X*, the mutual information *I(T(X); Y) ≤ I(X; Y)*. Here *I(X; Y) ≈ 0*, measured and confirmed by permutation test at p = 0.762. No amount of processing can raise a ceiling that sits at zero.

## 1.4 Suitability for Publication in a High-Quality Venue

Assessed against the criteria a reviewer would actually apply:

| Reviewer criterion | Status | Consequence |
|---|---|---|
| Data provenance documented | ❌ Absent | Desk reject at most clinical venues |
| Ethics approval / consent | ❌ Absent | Desk reject; required by ICMJE and by most CS venues with human data |
| Task is learnable from the data | ❌ Disproved (p = 0.762) | Fatal at review |
| Results free of leakage | ❌ 1.0000 → 0.2482 under ablation | Fatal — and this is the single most-checked failure mode in clinical ML review |
| External validation | ❌ Impossible | Fatal for a diagnostic claim |
| Sample size justified | ❌ EPV 5.76 vs. 10–20 | Major revision minimum |
| Clinical plausibility of records | ❌ 17.3% self-contradictory | Fatal |
| Reproducibility | ✅ Strong (your pipeline) | The one genuine strength |

**Assessment:** The dataset cannot support a clinical or diagnostic publication in any venue with peer review. 

One honest publication path *does* exist and should be acknowledged rather than dismissed: a **methodological / negative-result paper** — "a reproducible integrity-audit protocol that detects synthetic data and label leakage in clinical ML datasets", using this dataset as the worked case study. That is a real contribution, it is genuinely publishable at a workshop or student track, and your Phase 0 work already constitutes most of it. But it is a *methods* paper about auditing, not a thesis about upper GI endoscopy, and it will not by itself reach the grade band you are targeting. **The strongest outcome is to keep that audit as Chapter 3 of a thesis whose main contribution rests on real data.** Section 8 shows how.

---

# PART II — Project Feasibility Verdict

## 2.1 Decision

> **Do not continue with `Peptic Ulcer_Dataset.xlsx` as the substrate for the thesis's primary contribution. Replace it.**

## 2.2 The Reasons, Ranked by Force

1. **The task is provably unlearnable from this data.** Permutation test p = 0.7622; the observed score sits at the 24th percentile of the random-label null. This is not "weak performance" — it is a formal failure to reject independence. No modelling decision downstream of this fact can matter.

2. **The headline result is an identity function.** 1.0000 accuracy at 0.0000 variance, collapsing to 0.2482 — below the 0.2671 baseline — once the four label-constituent fields are removed. 100% of unique feature combinations map deterministically to one label. The model recovers a regular expression.

3. **The leakage is multi-source, so the intuitive fix does not work.** Removing `Comments` leaves 91.65%. An examiner who proposes the obvious remedy and sees 91.65% will assume the result is partially valid; the honest number is 24.82%, and you would have to explain that in the room.

4. **The records are internally contradictory.** 220 records (17.3%) declare normality while documenting pathology. There is no ground truth to clean toward.

5. **The generation process is measurably random.** Occupancy O/E = 0.9899 against a Monte-Carlo interval of [570, 601]; Age ~ Uniform[18,90] at p = 0.5366; all pairwise Cramér's V ≤ 0.0639 with zero associations surviving Bonferroni.

6. **The defects are not addressable by any technique available to you.** Twelve defects; one fixable. Section 1.3 works through each proposed remedy and the specific reason it fails.

7. **Publication is foreclosed on at least four independent grounds** — provenance, ethics, leakage, external validity — any one of which is sufficient for rejection.

8. **The risk profile at defence is asymmetric and severe.** If you present it and no one checks, you gain a grade you cannot defend. If one examiner asks "what happens if you drop the diagnosis column?", the entire result collapses in public. You have already done the work that lets you get ahead of this — use it.

## 2.3 What Survives

This is not a restart. The following transfer intact to any replacement dataset:

- `src/data/integrity.py` — the six-test synthetic-data battery, permutation testing, occupancy analysis, leakage ablation harness
- `src/literature/*` — the PRISMA search, screening, and extraction pipeline (50 included studies)
- `src/report/*` — the figure generation and document build chain
- The Phase 0/1 report itself — 46 pages that become **Chapter 3: Data Integrity Methodology**
- The blueprint's phase structure, validation checklists, and reporting-standard alignment

Your existing investment is in **method**, and method is portable. The only thing being discarded is the spreadsheet.

---

# PART III — Requirements for the Replacement Dataset

Rather than picking a popular dataset, I derived the selection criteria directly from the twelve defects. A candidate must close each one:

| # | Requirement | Derived from | Test |
|---|---|---|---|
| R1 | Real clinical data, documented provenance | D1, D5 | Named institution, collection period, published descriptor paper |
| R2 | Labels independent of the input representation | D2 | Labels assigned by humans viewing the raw data, not computed from fields |
| R3 | Demonstrated learnable signal | D1 | Published baseline substantially above chance |
| R4 | Clinically coherent records | D4 | Peer-reviewed descriptor; expert annotation |
| R5 | Label-quality evidence | D6 | Inter-rater agreement reported, ideally with per-annotator labels retained |
| R6 | Adequate sample size | D7 | ≥ 5,000 units; EPV ≥ 10 achievable |
| R7 | Rich feature space | D8 | Genuine high-dimensional input (images/video), not a closed token set |
| R8 | Ethics approval and consent, permissive licence | D10 | Documented IRB number; CC BY or equivalent |
| R9 | Patient-level identifiers | D11 | Grouped splitting possible; ideally official splits provided |
| R10 | External validation route | D12 | A second, independent dataset with overlapping classes |
| R11 | Upper-GI relevance | Continuity | Preserves the thesis topic and Phase 1 literature review |
| R12 | Feasible on student compute | Practicality | Trainable on a free-tier GPU (Colab/Kaggle) in reasonable time |

---

# PART IV — Candidate Datasets Surveyed

## 4.1 Considered and Rejected

**Real free-text endoscopy report corpora (to preserve the NLP framing).** I searched specifically for this, because it would be the minimum-disruption option. **No public, de-identified, free-text endoscopy report corpus exists.** The literature is explicit that there are no public datasets for benchmarking report-based endoscopy models; every published endoscopy-NLP study uses institutional data warehouses under local governance. MIMIC-IV contains clinical notes but requires PhysioNet credentialing plus CITI training (typically 2–6 weeks), is not endoscopy-specific, and its note module does not contain structured endoscopy reports. **Verdict: the NLP-on-reports framing cannot be rescued with public data within a thesis timeline.** This is the single most important negative finding of the search, and it is what forces the modality pivot.

**Kaggle "peptic ulcer" / "gastro" tabular datasets.** Surveyed; the same failure mode as your current file — undocumented provenance, template generation, no descriptor paper. Rejected under R1.

**GastroNet-5M** (4,820,653 images, ~500,000 procedures, 8 Dutch hospitals, 2012–2020; *Gastroenterology*, 2025). Superb resource, but it is a **self-supervised pretraining corpus**, largely unlabelled, requiring portal registration, and 5M images is far outside a bachelor's compute budget. **Retained as an optional pretrained-encoder source and as future work, not as the primary dataset.**

**Kvasir-Capsule, KID, SEE-AI, WCEBleedGen.** Capsule endoscopy — small bowel, not upper GI. Fails R11.

**Kvasir-SEG, PolypGen, SUN, LDPolypVideo.** Colonoscopy/polyp segmentation — lower GI. Fails R11. (PolypGen's 6-centre design is a good model for *how* to do external validation, and worth citing methodologically.)

**Kvasir v2** (8,000 images, 8 classes, 1,000 per class). Balanced and simple, but superseded by HyperKvasir, licensed only "for research and educational purposes" (weaker than CC BY), and heavily saturated in the literature — hundreds of papers report >95% on it. Fails the novelty test. **Useful only as a sanity-check baseline.**

## 4.2 Shortlisted

**GastroHUN** — *Scientific Data* (Nature), 12:102, January 2025. Hospital Universitario Nacional de Colombia.
**HyperKvasir** — *Scientific Data* (Nature), 7:283, 2020. Bærum Hospital, Norway.
**GastroVision** — MICCAI ML4MHD workshop, 2023. Bærum (Norway) + Karolinska (Sweden).
**Kvasir-VQA / Kvasir-VQA-x1** — SimulaMet, 2024/2025. Multimodal image+text, derived from HyperKvasir.

---

# PART V — Comparison Table

Current dataset versus the four shortlisted alternatives, on the twelve criteria requested.

| Criterion | **Peptic Ulcer_Dataset.xlsx** (current) | **GastroHUN** ⭐ | **HyperKvasir** | **GastroVision** | **Kvasir-VQA** |
|---|---|---|---|---|---|
| **Data quality** | ❌ Synthetic; occupancy O/E = 0.99 vs. random; Age ~ U[18,90], p = 0.54; 17.3% self-contradictory records | ✅ Real EGD, single tertiary centre, protocol-driven (SSS), peer-reviewed descriptor | ✅ Real gastro/colonoscopy, Bærum Hospital 2008–2016, peer-reviewed | ✅ Real, 2 centres / 2 countries | ✅ Inherits HyperKvasir images |
| **Number of samples** | ⚠️ 1,269 rows (EPV 5.76) | ✅ 8,834 images / 387 patients + 4,729 sequences + 237 videos (103.8 GB total) | ✅ 110,079 images (10,662 labelled) + 374 videos; **upper-GI labelled ≈ 3,450** | ⚠️ 8,000 images, 27 classes | ✅ 6,500 images / 58,849 QA pairs |
| **Feature quality** | ❌ 71-word closed vocabulary; 7/12 columns cardinality < 0.01 | ✅ Full-resolution endoscopic images + temporal sequences + video | ✅ Images, video, segmentation masks | ✅ Images + metadata CSV | ✅ Images + natural-language QA |
| **Label quality** | ❌ Regex-derived from the features; 61.6% multi-match collapsed; 81 fabricated `Normal` | ⭐ **4 independent expert annotators, all individual labels retained; pairwise κ ≈ 0.70–0.79; intra-rater re-labelling on 905 images (9.76%)** | ✅ Endoscopist-verified; single consensus label | ✅ Expert-verified; single label | ✅ Expert-informed QA pairs |
| **Missing values** | ⚠️ `Indication` 15.13% missing, unexplained | ✅ Complete for labelled images | ✅ Complete | ✅ Complete | ✅ Complete |
| **Class imbalance** | ⚠️ 1.22:1 (`Comments`), 3.57:1 (derived) — but on meaningless labels | ⚠️ Moderate across 22 landmarks + NA; manageable, quantified in descriptor | ⚠️ Severe (barretts = 41 vs. pylorus = 999) | ❌ Severe — 5 classes have < 6 images; published work restricted to 22 of 27 classes | ⚠️ Inherited |
| **Real-world applicability** | ❌ None — no real patients | ⭐ Direct: SSS completeness / blind-spot monitoring, the exact task with RCT evidence (blind-spot rate 22.46% → 5.86%) | ✅ Lesion & landmark recognition | ✅ Broad GI CAD | ✅ Clinical VQA / report generation |
| **Research novelty** | ❌ Nil | ⭐ **High — released Jan 2025, very low literature saturation; authors' own stated limitation (consensus-only testing) is an open gap** | ⚠️ Low — heavily benchmarked since 2020 | ✅ Moderate — less saturated | ⭐ High — active MediaEval Medico task |
| **Publication potential** | ❌ None for a clinical claim | ⭐ Journal / conference viable | ⚠️ Novelty must come from method, not data | ✅ Good | ✅ Good, but VLM compute is heavy |
| **Ethical considerations** | ❌ No approval, no consent, no provenance; k-anonymity = 1, 93.68% of classes below k = 5 | ⭐ IRB **CEI-2019-06-10**, Hospital Universitario Nacional de Colombia; **informed consent obtained**; **CC BY 4.0** | ✅ Norwegian DPA approved, consent exempt (fully anonymised); CC BY 4.0 | ✅ De-identified; CC BY 4.0 | ✅ CC BY (inherits) |
| **Metadata availability** | ❌ No data dictionary | ⭐ `metadata.zip` + `official_splits.zip`; per-annotator labels, agreement type, source type, resolution; patient age/sex; video-level clinical data incl. diagnoses, *H. pylori* status, OLGA staging† | ✅ Class folders + 3 official splits | ✅ `GastroVision_metadata.csv` | ✅ Structured QA schema |
| **ML / DL suitability** | ❌ Neither — no signal | ⭐ Excellent. Published baselines: ConvNeXt-L **macro F1 88.25 ± 0.22**; **ConvNeXt-T 87.58 at 28M params**; GRU sequences 85.14 ± 0.48; Transformer 86.30 ± 0.42. **Labelled-image set is only 2.8 GB** → free-tier GPU feasible | ✅ Excellent; baselines micro-F1 0.839–0.910, best MCC 0.902 | ✅ Good | ⚠️ Needs VLM-scale compute |

† The video-level clinical metadata (diagnoses, *H. pylori*, OLGA) is described in the descriptor paper; **confirm the exact fields against `metadata.zip` on download before building a research question on it.** Flagged as a verification item, not an assumption.

---

# PART VI — Final Recommendation

## 6.1 The Recommendation

> **Primary dataset: GastroHUN.**
> **External validation: HyperKvasir (+ GastroVision) on the shared upper-GI landmark classes.**
> **Optional pretraining: GastroNet-5M encoder, if compute allows.**

Adopt a **primary + external** design rather than a single dataset. This is what separates a strong thesis from an ordinary one, and it costs you little because the external sets are small and CC BY.

## 6.2 Why GastroHUN Is the Best Choice

**1. It closes all twelve defects.** Mapped explicitly:

| Defect | How GastroHUN closes it |
|---|---|
| D1 zero signal | Published baseline macro F1 88.25 vs. ~4.3% chance across 23 classes |
| D2 label leakage | Labels are human annotations of pixel data — structurally impossible to derive from the features |
| D3 independence | Real anatomy; images and labels are causally linked |
| D4 impossible records | Real procedures, expert-verified, peer-reviewed descriptor |
| D5 random generation | Real acquisition at a named institution with IRB approval |
| D6 label semantics | Four annotators per image, agreement levels explicit, ambiguity *measured* rather than hidden |
| D7 power | 8,834 images / 387 patients; 59 patients in the official test set |
| D8 degenerate features | Full-resolution images — genuinely high-dimensional |
| D9 missing data | Complete for the labelled set |
| D10 ethics | IRB CEI-2019-06-10 + informed consent + CC BY 4.0 |
| D11 splitting | **Official patient-level splits shipped**: 270 / 58 / 59 patients (70/15/15) |
| D12 external validity | HyperKvasir and GastroVision share landmark classes — cross-continent validation available |

**2. It is the only public upper-GI dataset that retains every annotator's individual labels.** Four experts — two gastroenterology fellows, two experienced gastroenterologists — independently labelled all 8,834 images, and *all four label sets are distributed*. Almost every public medical imaging dataset ships a single consensus label, discarding the disagreement. GastroHUN preserves it. This is the raw material for a contribution that simply cannot be made on other datasets.

**3. Its authors have publicly stated the gap you should fill.** From the descriptor's own limitations: testing was *"limited to complete-consensus samples; real-world variability not fully captured."* The published benchmark evaluates only on images where all four experts agreed — i.e. on the easy subset. Performance on the ambiguous majority is **unknown and unreported**. An open gap, named by the dataset's creators, in a dataset released 18 months ago, with almost no competing literature. That is close to an ideal thesis opportunity.

**4. The clinical framing is unusually strong.** The Systematic Screening Protocol for the Stomach exists because incomplete inspection causes missed gastric cancer. AI blind-spot monitoring (WISENSE / ENDOANGEL) reduced blind-spot rates from **22.46% to 5.86%** in a randomised controlled trial. Your work sits directly on that evidence chain — you are not inventing a use case, you are contributing to one with demonstrated patient benefit. Note also that GastroHUN's authors report their baseline performs *worst* on cardia, lesser curvature and posterior wall — **precisely the regions where missed gastric cancers are reported**. Targeting those classes is a clinically motivated, defensible contribution.

**5. It is feasible on your hardware.** You need `Labeled Images.zip` (2.8 GB), `metadata.zip` (2.1 MB) and `official_splits.zip` (0.4 MB) — **2.8 GB, not 103.8 GB**. ConvNeXt-Tiny reaches 87.58 macro F1 at 28M parameters, trainable on a free Colab/Kaggle T4. The video corpus is optional and can be deferred to future work.

**6. You inherit a strong published baseline.** ConvNeXt-L 88.25 ± 0.22 with a defined protocol, plus **human expert performance (F1 77.47–84.82)** as a reference band. You can position results against both a machine and a human benchmark — a rare luxury.

## 6.3 Licence Note — Resolve Before Publishing

The GitHub README states **CC BY-NC 4.0**; the authoritative Figshare record and the *Scientific Data* article state **CC BY 4.0**. I verified this directly against the Figshare API: `license: {name: "CC BY", url: creativecommons.org/licenses/by/4.0/}`. **Use CC BY 4.0, cite the Figshare DOI as your source of licence truth, and note the discrepancy in your data-availability statement.** If you plan any commercial-adjacent use, email the authors for written confirmation. This is exactly the kind of detail that distinguishes a careful thesis.

---

# PART VII — Download Links and Official Sources

## Primary — GastroHUN

| Resource | Link |
|---|---|
| **Dataset (official, Figshare)** | https://doi.org/10.6084/m9.figshare.27308133 |
| **Descriptor paper** (*Scientific Data* 12:102, 2025) | https://www.nature.com/articles/s41597-025-04401-5 |
| **Open-access full text (PMC)** | https://pmc.ncbi.nlm.nih.gov/articles/PMC11742658/ |
| **Code, splits, pretrained checkpoints** | https://github.com/Cimalab-unal/GastroHUN |
| **Licence** | CC BY 4.0 (per Figshare record) |
| **Ethics** | Hospital Universitario Nacional de Colombia, CEI-2019-06-10 |

**Files to download first** (2.8 GB total, not the full 103.8 GB):
- `Labeled Images.zip` — 2,820.5 MB — 8,834 images, 387 patients
- `metadata.zip` — 2.1 MB — per-annotator labels, agreement flags, demographics
- `official_splits.zip` — 0.4 MB — the 270/58/59 patient-level partition

Defer unless needed: `Labeled_Sequences_Group1–7` (~32 GB) and `Videoendoscopies_Group1–7` (~69 GB).

## External validation — HyperKvasir

| Resource | Link |
|---|---|
| **Dataset** | https://datasets.simula.no/hyper-kvasir/ |
| **OSF mirror** | https://doi.org/10.17605/OSF.IO/MH9SJ |
| **Code / GitHub** | https://github.com/simula/hyper-kvasir |
| **Paper** (*Scientific Data* 7:283, 2020) | https://www.nature.com/articles/s41597-020-00622-y |
| **Licence** | CC BY 4.0 |

Upper-GI labelled classes (verified counts: `pylorus` 999, `z-line` 932, `esophagitis-a` 403, `barretts` 41; plus `retroflex-stomach`, `esophagitis-b-d`, `barretts-short-segment` — **≈ 3,450 images total; confirm exact per-class counts from the distributed folder structure**).

## Secondary external — GastroVision

| Resource | Link |
|---|---|
| **Dataset (OSF)** | https://osf.io/84e7f/ |
| **Simula mirror** | https://datasets.simula.no/gastrovision/ |
| **GitHub** | https://github.com/DebeshJha/GastroVision |
| **Paper** (arXiv 2307.08140 / MICCAI ML4MHD 2023) | https://arxiv.org/abs/2307.08140 |
| **Licence** | CC BY 4.0 |

## Optional — pretraining and multimodal extensions

| Resource | Link |
|---|---|
| GastroNet-5M (4.8M images, 8 Dutch hospitals) | https://www.cortex.thetavision.nl/dataset-provider/listing/1/ |
| GastroNet-5M paper (*Gastroenterology*, 2025) | https://www.gastrojournal.org/article/S0016-5085(25)05797-X/fulltext |
| Kvasir-VQA | https://datasets.simula.no/kvasir-vqa/ · https://github.com/simula/Kvasir-VQA |
| Kvasir-VQA-x1 (arXiv 2506.09958) | https://arxiv.org/abs/2506.09958 |

---

# PART VIII — Proposed Research Direction

## 8.1 Thesis Title

**Primary recommendation:**

> **Agreement-Aware Deep Learning for Systematic Screening of the Stomach: Treating Expert Disagreement as Signal Rather Than Noise in Upper Gastrointestinal Endoscopy**

Alternatives, depending on where the results land:

- *Beyond Consensus: Evaluating Deep Learning for Gastric Landmark Recognition Across the Full Spectrum of Expert Agreement*
- *Uncertainty-Calibrated Anatomical Landmark Classification for Blind-Spot Monitoring in Gastroscopy: A Multi-Annotator Study with Cross-Continent External Validation*

## 8.2 The Gap

Public medical imaging datasets almost universally distribute a single consensus label, discarding inter-observer variability. Models trained and tested on consensus subsets are evaluated on the *easiest* cases and report optimistic performance. GastroHUN retains all four annotators' labels — and its own published benchmark still evaluates only on complete-consensus test images, a limitation its authors state explicitly. The behaviour of these models on the ambiguous majority of clinical images is unmeasured.

## 8.3 Research Questions

**RQ1 (Characterisation).** How does landmark-classification performance vary across agreement strata — 4/4, 3/4, 2/4 expert agreement? Quantify the optimism introduced by consensus-only evaluation.

**RQ2 (Method).** Does training on the empirical annotator distribution (soft labels) rather than majority-vote hard labels improve **calibration** (ECE, Brier), **selective prediction** (risk–coverage AUC), and **accuracy on ambiguous cases**, without degrading consensus-case accuracy?

**RQ3 (Human comparison).** At what selective-prediction coverage does the model exceed individual expert performance (reported band F1 77.47–84.82)? Where should a human-in-the-loop threshold be set?

**RQ4 (Generalisation).** Does an agreement-aware model transfer from Colombia (GastroHUN) to Norway/Sweden (HyperKvasir, GastroVision) on shared landmark classes — pylorus, retroflex-stomach, z-line? Quantify the cross-continent domain gap.

**RQ5 (Clinical translation).** Can per-landmark confidence be aggregated into an SSS **completeness / blind-spot score**, and what is its net benefit under decision-curve analysis?

**RQ6 (Methodological, from Phase 0).** Does the integrity-audit protocol developed in Phase 0 behave correctly on real data — i.e. does it *reject* the synthetic hypothesis for GastroHUN while accepting it for the peptic ulcer file? This validates your audit instrument as a contribution in its own right.

RQ6 is the move that converts your discarded work into an asset: the peptic ulcer dataset becomes the **negative control** that demonstrates your audit protocol works.

## 8.4 Experimental Plan

| ID | Experiment | Purpose |
|---|---|---|
| X0 | Run `integrity.py` on GastroHUN | RQ6 — audit protocol validation; establishes the contrast case |
| X1 | Reproduce ConvNeXt-Tiny baseline on official splits | Verify environment against published 87.58 macro F1 |
| X2 | Stratify test set by Fleiss' κ / agreement level; re-evaluate X1 | RQ1 — the core measurement |
| X3 | Hard-label (majority vote) vs. soft-label (annotator distribution) training | RQ2 |
| X4 | Label smoothing, distillation, and evidential/ensemble uncertainty variants | RQ2 ablations |
| X5 | Calibration: temperature scaling, Platt, isotonic; ECE + reliability diagrams | RQ2 |
| X6 | Risk–coverage / selective prediction vs. human F1 band | RQ3 |
| X7 | Zero-shot transfer to HyperKvasir + GastroVision landmark classes | RQ4 |
| X8 | Per-landmark error analysis focused on cardia / lesser curvature / posterior wall | Clinical targeting |
| X9 | Grad-CAM / attention maps reviewed against anatomical expectation | Explainability |
| X10 | SSS completeness score + decision-curve analysis | RQ5 |
| X11 | Permutation test and leakage ablation on the final pipeline | Carries the Phase 0 firewall forward |

## 8.5 Metrics and Reporting Standards

- **Primary:** macro F1 (comparable to the published baseline), per-class F1, MCC
- **Calibration:** Expected Calibration Error, Brier score, reliability diagrams
- **Uncertainty:** risk–coverage AUC, coverage at fixed risk
- **Agreement:** Fleiss' κ, Cohen's κ, model–human κ
- **Clinical:** net benefit / decision-curve analysis
- **Reporting:** CLAIM (2024 update), TRIPOD+AI, STARD-AI — all three already scoped in your Phase 1 review

## 8.6 Why This Reaches the Highest Grade Band

| Examiner question | Your answer |
|---|---|
| "Is the data real and ethically sourced?" | Yes — IRB CEI-2019-06-10, informed consent, CC BY 4.0, peer-reviewed descriptor |
| "How do you know there's no leakage?" | Labels are human annotations of pixels; plus X11 runs the ablation harness explicitly |
| "Did you validate externally?" | Yes — cross-continent, Colombia → Norway/Sweden |
| "Is this novel, or a re-run of a known benchmark?" | Novel: no published work evaluates GastroHUN across agreement strata; the gap is named by the dataset's own authors |
| "Are your splits sound?" | Official patient-level splits, 270/58/59; no patient crosses a boundary |
| "Is it clinically meaningful?" | SSS completeness is the basis of blind-spot monitoring, with RCT evidence (22.46% → 5.86%) |
| "What did you do about your first dataset?" | Audited it rigorously, proved it synthetic, published the protocol, and used it as a negative control — Chapter 3 |
| "Is it reproducible?" | Full pipeline, fixed seeds, official splits, public data, versioned code |

The last row is worth emphasising. Most fourth-year theses cannot answer "what did you do when your data turned out to be bad?" with anything but silence. You can answer it with a 46-page audit, a permutation test, and a reusable protocol. **Discovering the problem and handling it correctly is itself a demonstration of research maturity, and examiners reward it.**

## 8.7 Indicative Timeline (12 weeks)

| Weeks | Work |
|---|---|
| 1 | Download GastroHUN; verify checksums; run X0 audit; confirm metadata fields (incl. the OLGA/*H. pylori* verification item) |
| 2 | Environment, data loaders, reproduce X1 against the published baseline |
| 3–4 | X2 agreement stratification — the core result. Update Phase 1 review with 2025–26 multi-annotator literature |
| 5–7 | X3–X5 soft labels, uncertainty, calibration |
| 8 | X6 selective prediction vs. human band |
| 9 | X7 external validation |
| 10 | X8–X10 error analysis, explainability, clinical utility |
| 11 | X11 firewall checks; full pipeline re-run from clean clone |
| 12 | Write-up, CLAIM/TRIPOD+AI checklists, defence preparation |
| +2 | Buffer |

## 8.8 Risks and Mitigations

| Risk | Likelihood | Mitigation |
|---|---|---|
| Compute insufficient for ConvNeXt-L | Medium | ConvNeXt-Tiny reaches 87.58 at 28M params; EfficientNet-B0 as fallback. Report the constraint honestly |
| Agreement strata too small for stable estimates | Medium | Compute stratum sizes in week 3 before committing; bootstrap CIs; merge 2/4 and 3/4 strata if needed |
| Cross-dataset class mapping is imperfect (X7) | High | Restrict to unambiguous shared landmarks (pylorus, retroflex-stomach, z-line); document the mapping explicitly as a limitation |
| Video-level clinical metadata not as described | Low–Medium | Verified as a week-1 task; RQ1–RQ5 do not depend on it |
| Someone publishes the same idea first | Low | Low saturation now; prioritise X2 to secure the core result early |
| Supervisor resists changing datasets | Medium | Present Part I and Part II. The permutation p = 0.762 and the E03→E05 collapse are not matters of opinion |

---

# PART IX — Immediate Next Actions

1. **Take this report to your supervisor and get the dataset change signed off in writing.** Lead with two numbers: permutation test p = 0.7622, and E03 = 1.0000 → E05 = 0.2482 against a 0.2671 baseline.
2. **Download** `Labeled Images.zip`, `metadata.zip`, `official_splits.zip` from https://doi.org/10.6084/m9.figshare.27308133 (2.8 GB).
3. **Run X0** — point `src/data/integrity.py` at GastroHUN. Expect it to *reject* the synthetic hypothesis. That contrast is Chapter 3's punchline.
4. **Verify the metadata fields** in `metadata.zip` against the descriptor paper, especially the video-level clinical variables.
5. **Confirm the licence** as CC BY 4.0 from the Figshare record; note the GitHub discrepancy in your data-availability statement.
6. **Extend the Phase 1 search** to the 2025–26 literature on annotator disagreement and soft-label learning in medical imaging — your PRISMA pipeline runs unchanged with new query terms.
7. **Do not delete the peptic ulcer dataset or its audit.** It is now your negative control and your Chapter 3.

---

## Sources

- [GastroHUN: an Endoscopy Dataset of Complete Systematic Screening Protocol for the Stomach — *Scientific Data* 12:102 (2025)](https://www.nature.com/articles/s41597-025-04401-5) · [PMC full text](https://pmc.ncbi.nlm.nih.gov/articles/PMC11742658/) · [Figshare dataset, DOI 10.6084/m9.figshare.27308133](https://doi.org/10.6084/m9.figshare.27308133) · [GitHub](https://github.com/Cimalab-unal/GastroHUN)
- [HyperKvasir — *Scientific Data* 7:283 (2020)](https://www.nature.com/articles/s41597-020-00622-y) · [PMC full text](https://pmc.ncbi.nlm.nih.gov/articles/PMC7455694/) · [Simula datasets](https://datasets.simula.no/hyper-kvasir/) · [GitHub](https://github.com/simula/hyper-kvasir)
- [GastroVision — arXiv:2307.08140](https://arxiv.org/abs/2307.08140) · [OSF](https://osf.io/84e7f/) · [GitHub](https://github.com/DebeshJha/GastroVision) · [Simula](https://datasets.simula.no/gastrovision/)
- [Kvasir-VQA: A Text-Image Pair GI Tract Dataset](https://arxiv.org/pdf/2409.01437) · [Kvasir-VQA-x1 — arXiv:2506.09958](https://arxiv.org/html/2506.09958v1) · [GitHub](https://github.com/simula/Kvasir-VQA)
- [GastroNet-5M — *Gastroenterology* (2025)](https://www.gastrojournal.org/article/S0016-5085(25)05797-X/fulltext) · [PubMed](https://pubmed.ncbi.nlm.nih.gov/40749857/)
- [WISENSE / ENDOANGEL blind-spot monitoring RCT and quality-control review — *Gastroenterology Report*](https://academic.oup.com/gastro/article/9/3/185/6168570)
- [Deep learning-based anatomical site classification for upper GI endoscopy — PMC](https://www.ncbi.nlm.nih.gov/pmc/articles/PMC7316667/)
- [NLP for quality indicators in free-text colonoscopy reports — PMC](https://pmc.ncbi.nlm.nih.gov/articles/PMC9055472/) (establishes the absence of public endoscopy report corpora)
- [Benchmarking Real-World Medical Image Classification with Noisy Labels — arXiv:2512.09315](https://arxiv.org/html/2512.09315v1)
- [Deep learning with noisy labels in medical prediction problems: a scoping review — arXiv:2403.13111](https://arxiv.org/pdf/2403.13111)
- Current-dataset figures: `reports/phase0_results.json`, generated by `src/data/integrity.py`
