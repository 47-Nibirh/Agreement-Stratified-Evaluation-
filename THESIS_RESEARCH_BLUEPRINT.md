# Master Research Blueprint — v3.6

## Agreement-Stratified Evaluation of Deep Learning for Anatomical Landmark Recognition in Upper Gastrointestinal Endoscopy

**Candidate:** 4th-year B.Sc. (CSE) thesis
**Corpus:** GastroHUN (Hospital Universitario Nacional de Colombia) — 8,834 images, 387 patients, 23 classes
**Version:** 3.6 — 2026-07-28
**Status:** ✅ Phases 0–6 complete; Phase 7 thesis DRAFT complete (Thesis.docx/.pdf, 44 pp); backbone generalisation tested
**Supersedes:** v3.2, v3.1, v3.0, and v2.0 archived at `superseded/THESIS_RESEARCH_BLUEPRINT_v2_peptic_ulcer.md`

---

## STATUS BOARD

| Phase | Title | Status | Deliverable |
|---|---|---|---|
| **0** | Data provenance & integrity gate | ✅ **COMPLETE** | `Phase0_Phase1_Report.docx/.pdf` §Phase 0 — verdict **PROCEED** (6 PASS, 2 CONDITIONAL) |
| **1** | Literature review & problem framing | ✅ **COMPLETE** | Same report §Phase 1 — PRISMA 2020, 82 studies included |
| **2** | Baseline reproduction | ✅ **COMPLETE** | `Phase2_Report.docx/.pdf` — verdict **PASS** (83.92 macro F1, Δ = −1.08 vs published 85.0 ± 1.5) |
| **3** | Agreement-stratified evaluation | ✅ **COMPLETE (rev. 2)** | `Phase3_Report.docx/.pdf` (28 pp) — RQ1 **supported for the 4/4→3/4 and 4/4→2-1-1 contrasts, not resolvable for 4/4→no-majority**. Raw annotator-marginalized macro F1 83.92→48.95→26.15→30.79 (gap 53.13 pts). Holding the *attainable ceiling* constant (100.0/74.2/44.6/40.2), the gaps are 17.98 pts (CI 12.49–24.37), 25.21 (16.11–34.11) and 7.38 (−3.08–18.85). Principal finding is calibration: ECE 9.2%→56.4%. |
| **4** | Soft-label & uncertainty training | ✅ **COMPLETE** | `Phase4_Report.docx/.pdf` — C0–C4 on a cohort held constant. **RQ2 accuracy NOT RESOLVED** (C2−C3 on the pooled contested stratum +1.40 pts, CI -0.88 to +3.61). **RQ2 calibration NOT SUPPORTED** (ΔECE +13.67 pts, CI +11.21 to +15.60 — the *control* is the better calibrated arm on contested images). **RQ3** supported for no configuration. **RQ4 NOT RESOLVED** at λ=1. |
| **5** | External validation | ✅ **COMPLETE** | `Phase5_Report.docx/.pdf` — HyperKvasir + GastroVision, 3,125 gastric + 13,997 out-of-protocol images, all five arms × 3 seeds, no adaptation. **First finding: the external label spaces cannot express wall × station at all**, so the endpoint is a pre-registered 2-way collapse, not 23-way. **P5-A TRANSFERS** (78.41 external vs 98.17 internal, drop -19.75 pts, CI -21.29 to -18.28; precision target met). **P5-B hypothesis FALSIFIED** — rejection 63.4% vs a 4.35% chance floor, and the soft-target arms reject far better than the hard-label ones. **P5-C PRESERVED** (ρ = 0.700) but C3 and C2 swap at the top: C2 is best externally (ECE 7.80 vs C3's 8.00). |
| **6** | Explainability & error analysis | ✅ **COMPLETE** | `Phase6_Report.docx/.pdf` — four pre-registered endpoints, no retraining. **P6-A: on contested images the model out-predicts a held-out annotator** (Δ = +0.0647 macro F1, CI +0.0281 to +0.1001) **but not the panel's own modal vote** — it recovers 24% of the headroom from the annotator (0.3902) to the modal-vote oracle (0.6700) and exceeds that oracle on no stratum (P6-AMD-5). So the attainable ceiling on contested images is 0.67 not 1.00 — much of the Phase 3 decline is the ceiling moving — while a real model shortfall against that reduced ceiling remains. **P6-B: wall geometry MIRRORS HUMAN GEOMETRY**, station geometry diverges by -8.19 pts (CI [-15.1, -2.85]); X3 settled — the human geometry is *undefined* on S-unanimous, so the Phase 3 comparison was cross-population. **P6-C1 NOT ESTIMABLE (vote entropy is constant on this stratum by construction)** (within-S-majority ρ = None). **P6-D: CONSISTENT WITH THE PHASE 5 RANKING** — external AURC separates the arms decisively (C2 0.1906 vs C3 0.3235) where internal AURC does not (0.0828 vs 0.0822). |
| **7** | Thesis writing & defence | 🟡 **DRAFT COMPLETE** | `Thesis.docx/.pdf` — 10 chapters, 31 figures, 23 tables. Two chapters written that existed nowhere before: **Ch.8 RQ5** (the audit protocol as an instrument — PARTIALLY SUPPORTED, only 1/4 fatal defects caught by any gate) and **Ch.9 synthesis**. Multiplicity declared (Holm, family-wise 0.05; RQ1 survives, RQ2/RQ4 already null). **Backbone generalisation: 3/3 claims replicate on EfficientNet-B0** — the RQ2 accuracy null, the calibration reversal in both directions, and the human-comparator position (20% of headroom vs ConvNeXt's 24%, neither exceeding the oracle). Geometry, attribution and the external endpoints remain single-architecture. |

### Completed task register

Everything below is done, measured and reproducible. **Do not redo it.**

- [x] **Dataset viability assessment** — 12 defects catalogued in the previous corpus; replacement decision in `DATASET_DECISION_REPORT.md` → `Dataset_Decision_Report.docx/.pdf`
- [x] **Replacement corpus acquired** — GastroHUN `Labeled Images` (2.71 GB) + `official_splits` + `metadata`
- [x] **G1 Provenance verified** — Sci Data 12:102 (2025), doi:10.1038/s41597-025-04401-5; ethics CEI-2019-06-10; informed consent; licence discrepancy resolved in favour of Figshare's CC BY 4.0
- [x] **G2 Physical integrity** — 8,834/8,834 decoded; 0 missing, 0 orphan, 0 corrupt, 0 folder/manifest mismatches
- [x] **G3 Duplication & contamination** — 0 exact (SHA-256) duplicates; exhaustive 39,015,361-pair perceptual scan; decision rule calibrated against synthetic-duplicate and class-matched controls; **0 cross-split duplicates confirmed**
- [x] **G4 Label architecture** — 4 independent annotators retained separately across 23 classes
- [x] **G5 Agreement quantified** — Fleiss κ = 0.7475, Krippendorff α = 0.7475, Gwet AC1 = 0.7475; all 6 pairwise κ with patient-clustered bootstrap CIs
- [x] **G6 Split integrity** — 0 patient overlaps; class χ² p = 0.99999; agreement χ² p = 0.784; per-patient κ Kruskal–Wallis p = 0.982
- [x] **G7 Power analysis** — 22/23 classes exceed ±10 pp Wilson half-width (CONDITIONAL)
- [x] **G8 Population description** — no age/sex anywhere in the release; 60.2% clinical-record coverage (CONDITIONAL)
- [x] **Disagreement decomposition** — original finding: 50.96% of disagreement is wall-within-station
- [x] **Phase 1 search executed** — 7 themed PubMed queries, 1,349 unique records, 82 studies included
- [x] **Reproducible pipeline built** — 11 scripts regenerate every number, figure and table
- [x] **Compute budget established** — GTX 1650 4 GB; ConvNeXt-Tiny feasible, ConvNeXt-Large not
- [x] **CUDA installed** — `torch==2.12.0+cu126` (cp314 caps cu128 at 2.11.0, a downgrade; cu126 offers the same version already installed)
- [x] **Hardware benchmarked, not assumed** — AMP float16 measured at 0.38× float32 throughput on this TU117 (no tensor cores); float32 adopted (pre-registration DEV-1)
- [x] **Consensus cohort verified** — 3,722/793/803 images, 23 classes (GATE 2); 5,318/5,318 filenames hash-resolved against Phase 0 inventory (GATE 3); two patients (train #278, test #101) contribute no unanimous image
- [x] **Training-set normalisation measured** — mean/SD differ from ImageNet defaults by up to 0.127 (red channel)
- [x] **Phase 2 pre-registered before training** — target 85.0 ± 1.5, 3 seeds, 1,000-resample patient-clustered bootstrap, diagnostic order fixed in `reports/phase2_prereg.json`
- [x] **Phase 2 executed — GATE 5 PASS** — 3-seed mean macro F1 83.92 (95% CI 81.47–86.20), Δ = −1.08 points; all runs stopped by early stopping (not the compute-imposed epoch cap)
- [x] **Descriptor's published stability margins shown to be a different quantity** — SEM of a 100-iteration bootstrap mean (∝ 1/√B), not a 95% interval on performance; ~9–11× narrower than the patient-clustered interval on the same quantity (measured per seed, `reports/phase2_test_metrics.json`)
- [x] **Phase 3 tier construction gated** — full 1,353-image official test split tagged with 5 agreement tiers from the 4-annotator vote matrix; counts (803/342/127/73/8) matched the pre-registered corpus-wide expectation exactly before any model touched the images
- [x] **Phase 3 consistency gate PASS** — S-unanimous-tier predictions from the new full-test-split inference path reproduce `phase2_predictions_seed{1,2,3}.csv` exactly, 803/803 images, all 3 seeds
- [x] **Phase 3 executed — RQ1 answered (raw scale, pre-registered)** — annotator-marginalized macro F1 falls 83.92 → 48.95 → 26.15 → 30.79 across S-unanimous (n=803) → S-majority (n=342) → S-plurality (n=127) → pooled S-no-majority (n=81); raw gap 53.13 points vs the 3.25-point architecture benchmark; decline not strictly monotonic (Spearman ρ = −0.80, p = 0.20, n=4 tiers)
- [x] **Phase 3B executed — RQ1 amended, and the omitted pre-registered sections supplied** — the primary metric's *attainable ceiling* (modal-vote oracle) falls 100.00 → 74.23 → 44.55 → 40.23 across the four tiers, so most of the raw decline is the ceiling moving. Ceiling-normalised, patient-clustered bootstrap gaps: 4/4−3/4 = 17.98 pts (95% CI 12.49–24.37) ✔, 4/4−2-1-1 = 25.21 (16.11–34.11) ✔, 4/4−no-majority = 7.38 (−3.08–18.85) ✘ (contains 0). The S-plurality reversal is **significant** ceiling-normalised (−17.83, CI −31.25 to −2.64), i.e. a real finding, not small-n noise
- [x] **Phase 3B — calibration by stratum (the principal new finding)** — ECE 9.15% → 38.23% → 56.40% → 49.05%; mean confidence falls only 9.34 points while expected accuracy falls 56.57. Predictive entropy vs annotator vote entropy: ρ = 0.320 pooled but 0.02–0.08 *within* tier — RQ3 must use the within-tier quantity
- [x] **Phase 3B — confound controls, both negative (i.e. the tier effect is real)** — class composition explains only 3.5–4.2% of the drop; acquisition-stream composition does not differ across tiers (χ² p = 0.298) and restricting to the dominant stream shifts the curve by ≤0.18 points (closes L4)
- [x] **Phase 3B — zero-support objection quantified and refuted** — all 23 classes are populated in every tier; restricting the macro average to present classes changes no tier's score
- ⚠️ **Phase 3 rev. 1 corrections (4), recorded in `reports/phase3b_amendment.json`** — (X1) the claim that the any-annotator hit rate 'shows no such reversal' was **false**: Table 2 gives 84.39/80.02/72.70/79.83, the same dip; (X2) any-hit is confounded by tier-varying acceptance-set size (1.00/2.00/3.00/2.20 distinct labels); (X3) the O3 'within 0.12 points' match is unsupportable — CIs are [83.18, 96.00] wall and [76.68, 93.36] station, and the station CI **contains** the human 93.1%, so the 7.5-pt shortfall and the Phase 6 Grad-CAM lead built on it are withdrawn to hypothesis status; (X4) the '16× the architecture benchmark' headline is a scale artefact — direction survives, magnitude does not
- [x] **Phase 3 confusion-structure comparison (O3)** — on the S-unanimous stratum, the model's wall-confusion geometry (89.68% circumferentially adjacent) is within 0.12 points of the human value (89.8%, Phase 0); its station-confusion geometry (85.57% neighbouring) trails the human value (93.1%) by 7.5 points — **superseded by X3 above: both comparisons are consistent with the human values once patient-clustered intervals are attached; neither difference is resolvable**

<!-- PHASE4-REGISTER:BEGIN -->

- [x] **Phase 4 cohort and cache gated** — extended cohort E = 5,228 train / 1,103 validation (majority-or-better), 28.8% contested; gates P4.1a–e pass, and all 4,515 images shared with the Phase 2 cache decode **bit-identically** (P4.2)
- [x] **Phase 4 pre-registered before training** — frozen 2026-07-27 11:48:21; ε for the C3 control **derived** by matching the probability mass C2 displaces from the modal label (0.072016 → ε = 0.075290; entropy matching would have given 0.021228), λ fixed a priori at unit weight, verdict rules fixed for RQ2/RQ3/RQ4
- [x] **Phase 4 executed — 12 runs, C1–C4 × 3 seeds** — every arm shares the backbone, schedule, augmentation, normalisation and selection criterion of Phase 2, so only the target differs. Annotator-marginalized macro F1 on the pooled contested stratum: C0 42.42 · C1 43.76 · C2 45.75 · C3 44.35 · C4 45.47
- [x] **RQ2 accuracy — NOT RESOLVED** — the pre-registered contrast is C2−C3, not C2−C1: beating an *equally soft but uninformative* target is what would localise the benefit in the disagreement pattern rather than in regularisation. Measured +1.40 pts (CI -0.88 to +3.61). Adding the contested images at a hard target (C1−C0) gives +1.34 pts (CI -0.68 to +3.53), but is confounded by C0's different validation set and longer training, so it is descriptive only
- [x] **RQ2 calibration — NOT SUPPORTED, and the reversal is the finding** — ECE on the pooled contested stratum: C0 43.96% · C1 43.61% · C2 33.08% · C3 19.41% · C4 32.71%. The generic control C3 is far better calibrated there than the vote-proportion arm C2 (Δ +13.67 pts, CI +11.21 to +15.60). But on the unanimous stratum the order reverses (C0 9.15% · C1 9.49% · C2 4.72% · C3 6.51% · C4 4.07%): uniform smoothing suppresses confidence globally, so it is *under*confident where annotators agree, whereas C2 is trained one-hot there and is nearly exact. **No configuration achieves acceptable calibration on contested images**, which relocates the Phase 3 finding from 'an artefact of consensus-only training' to a property of the problem
- [x] **RQ3 — the Phase 3 artefact reproduces in every configuration** — the pooled predictive-vs-vote entropy correlation stays several times the within-stratum value for every arm, confirming that the pooled quantity the literature would report mostly measures which stratum an image is in. Supported for no configuration on S-majority
- [x] **RQ4 — NOT RESOLVED at λ=1** — anatomical error distance C4−C2 = -0.00270 (CI -0.01062 to +0.00477). No λ sweep was run (P4-DEV-3), so this is evidence about unit weight, not about anatomy-aware losses in general
- [x] **Leave-one-annotator-out** — the RQ2 verdict is invariant to dropping any single annotator, FG2 included. Training-side LOAO declared unexecuted for budget rather than omitted
- ⚠️ **The pre-registered epoch cap bound** — 8 of 12 runs stopped at the cap rather than by early stopping. It applies identically to C1–C4 so the target contrasts are unaffected, but the absolute scores are lower bounds and C1−C0 is not a controlled comparison

<!-- PHASE4-REGISTER:END -->
---

## 1. What changed from v2.0, and why

v2.0 planned an NLP pipeline over free-text endoscopy reports using `Peptic Ulcer_Dataset.xlsx`. That plan is dead. The reasons are measured, not stylistic:

1. **No signal.** All feature–target Cramér's V ≤ 0.088; permutation test p = 0.7622. The observed feature–target association was indistinguishable from chance.
2. **Circular labels.** The target was built by regex over the same text fields that became the TF-IDF features. Dropping the obvious culprit column still left accuracy at 0.9165, because three other fields independently re-encoded the same rules.
3. **Not remediable.** By the Data Processing Inequality, I(T(X);Y) ≤ I(X;Y). With I(X;Y) ≈ 0, no preprocessing, augmentation or feature engineering can create signal.
4. **No public alternative for the NLP framing.** An extensive search found no public de-identified free-text endoscopy report corpus. This is settled — **do not re-litigate it.**

The pivot is therefore from **NLP-on-reports** to **imaging**, and the contribution moves from "build a classifier" to "evaluate classifiers where the literature has not looked."

> **Retained, not deleted.** The old corpus stays in the project as a *negative control* validating the Phase 0 audit protocol (RQ5). An audit that passes everything it is shown is not an audit. This comparison becomes a thesis chapter.

---

## 2. Corpus profile — measured facts

### 2.1 Structure

| Property | Value |
|---|---|
| Images | 8,834 (all JPEG, all RGB) |
| Patients | 387 |
| Classes | 23 (22 SSS landmarks + OTHERCLASS) |
| Images per patient | 22.83 ± 2.88 (range 7–32) |
| Resolutions | 1350×1080 (8,427) · 900×720 (407) |
| Payload | 2.71 GB |
| Provenance streams | direct capture 8,053 · video frame 781 |
| Official splits | Train 270 pt / Val 58 pt / Test 59 pt |

### 2.2 The label space is a (wall × station) grid

| | S1 Antrum | S2 Distal body | S3 Upper-mid body | S4 Retro. cardia/fundus | S5 Retro. lesser curv. | S6 Final view |
|---|---|---|---|---|---|---|
| **G** Greater curvature | G1 | G2 | G3 | G4 | — | — |
| **A** Anterior wall | A1 | A2 | A3 | A4 | A5 | A6 |
| **L** Lesser curvature | L1 | L2 | L3 | L4 | L5 | L6 |
| **P** Posterior wall | P1 | P2 | P3 | P4 | P5 | P6 |

Plus `OTHERCLASS` = image unsuitable for assessment.

**This structure is the thesis's main analytical lever, and it is not documented as such in the dataset descriptor.**

### 2.3 Agreement — the central measurements

| Statistic | Value |
|---|---|
| Fleiss' κ | 0.7475 |
| Krippendorff's α | 0.7475 |
| Gwet's AC1 | 0.7475 |
| Mean pairwise Cohen's κ | 0.7476 |

The three chance corrections coincide because the SSS protocol makes the class marginal near-uniform, so Σpⱼ² ≈ 1/K and the Fleiss and Gwet expectations become algebraically equal. **The kappa paradox does not apply here** — state this before an examiner asks why three different statistics agree to four decimal places.

| Pair | κ | Relationship |
|---|---|---|
| G1–G2 | 0.8031 | within team (gastroenterologists) |
| FG1–G1 | 0.7930 | between teams |
| FG1–G2 | 0.7627 | between teams |
| FG2–G1 | 0.7260 | between teams |
| FG2–G2 | 0.7209 | between teams |
| **FG1–FG2** | **0.6799** | within team (residents) |

**Seniority does not predict agreement.** Each resident agrees *more* with the gastroenterologists than with the other resident. FG2 is the outlier annotator on every measure. Any design treating "Team A" as a coherent unit is unsupported by the data.

### 2.4 The agreement cascade

| Tier | Images | % |
|---|---|---|
| All images | 8,834 | 100.00 |
| Triple agreement (≥3/4) | 7,476 | 84.63 |
| Team B agreement | 7,170 | 81.16 |
| Team A agreement | 6,126 | 69.35 |
| **Complete agreement (4/4)** | **5,318** | **60.20** |

Vote patterns: 4–0 = 5,318 (60.20%) · 3–1 = 2,158 (24.43%) · 2–1–1 = 744 (8.42%) · 2–2 = 539 (6.10%) · 1–1–1–1 = 75 (0.85%).
**614 images (6.95%) admit no majority label under any voting rule.**

### 2.5 Disagreement is anatomically structured — the original finding

| Disagreement type | % of 12,800 events |
|---|---|
| **Same station, different wall** | **50.96** |
| Landmark vs OTHERCLASS | 20.80 |
| Same wall, different station | 19.91 |
| Both differ | 8.33 |

Confirmatory test — mean pairwise κ recomputed at coarser granularity:

| Granularity | κ | Unanimity |
|---|---|---|
| Full (23 classes) | 0.7476 | 60.20% |
| **Station only (7)** | **0.8597** | **78.99%** |
| Wall only (5) | 0.7481 | 66.86% |

Collapsing the wall recovers nothing; collapsing the station recovers a lot. **Endoscopists know how deep the scope is and disagree about which way it points.** Further: 89.8% of wall confusions involve circumferentially *adjacent* walls, and 93.1% of station confusions involve *neighbouring* stations. Disagreement respects the geometry — which is what makes it modellable rather than merely noise.

### 2.6 OTHERCLASS is a subjective judgement

Per-annotator rejection rate: FG1 1.48% · G1 2.06% · G2 5.41% · FG2 8.90% — a 6.0× spread. Only 12.24% of images ever called unusable are called so unanimously. Quality assessment and anatomical classification are **different tasks** and should be modelled and evaluated separately.

### 2.7 Published baselines (the ceiling to contextualise)

| Model | Params | Macro F1 |
|---|---|---|
| ConvNeXt-Large | 200 M | 88.25 ± 0.22 |
| ConvNeXt-Tiny | 28 M | ~85 |
| ResNet152 | 60 M | 85.28 ± 0.27 |
| **ConvNeXt-Tiny trained on FG-agreement labels** | 28 M | **87.05 ± 0.21** |
| Best single annotator (G1) as training label | — | 84.82 ± 0.23 |
| Human expert band | — | 77.47–84.82 |

**Note the fourth row.** Changing *how the annotator labels are combined* moved F1 by 2.2 points — more than the gap between architecture families. The descriptor reports this as an aside. It is the direct precedent for Phase 4.

All of these are measured **only on the 60.2% complete-agreement subset.**

---

## 3. Research questions

| ID | Question | Hypothesis | Primary endpoint |
|---|---|---|---|
| **RQ1** | How does landmark-classification performance vary across strata of expert agreement? | Macro F1 declines monotonically from unanimous to no-majority strata, by more than the between-architecture difference | Macro F1 per stratum, patient-clustered bootstrap 95% CI |
| **RQ2** | Does training on soft targets from all four votes beat hard consensus labels? | Matches on the unanimous stratum, exceeds on contested strata, better calibrated throughout | Macro F1 by stratum; ECE |
| **RQ3** | Does predictive uncertainty track human disagreement, and survive a centre change? | Predictive entropy correlates positively with annotator vote entropy; ranking preserved externally | Spearman ρ(predictive entropy, vote entropy); external macro F1 |
| **RQ4** | Does an anatomy-aware loss exploiting the wall/station structure help on contested images? | Yes, concentrated on adjacent-wall confusions | Macro F1; adjacent-wall error rate |
| **RQ5** | Does the Phase 0 audit protocol discriminate a sound corpus from an unsound one? | Yes — demonstrated against the retired dataset as negative control | Gate verdicts on both corpora |

Hypotheses were fixed **before** any model was trained. Phase 0 deliberately measured no model performance so these remain genuine predictions.

---

## 4. Phase-by-phase methodology

### ✅ PHASE 0 — Data Provenance & Integrity Gate — **COMPLETE**

Eight criteria; verdict **PROCEED** (6 PASS, 2 CONDITIONAL). Full detail in `Phase0_Phase1_Report.docx` §Phase 0.

- Scripts: `src/data/gastrohun_inventory.py`, `gastrohun_agreement.py`, `gastrohun_structure.py`, `gastrohun_neardup.py`, `gastrohun_dup_calibration.py`
- Artefacts: `reports/gastrohun_*.json`

> **Methodological lesson to carry forward.** The contamination scan initially reported 54 cross-split "duplicate" pairs. That number was an artefact of an uncalibrated threshold. A first calibration attempt using a *randomly paired* null was also wrong — random pairs mostly compare different anatomical stations, setting an artificially low bar. Rebuilding the null as *class-matched* pairs and anchoring the decision rule on a *synthetic-duplicate positive control* reduced the count to **0**, and visual audit confirmed the flagged pairs were different patients photographed at the same landmark. **An uncalibrated threshold is not a measurement, and a threshold calibrated against the wrong comparison is not much better.** Apply this standard to every threshold in later phases.

### ✅ PHASE 1 — Literature Review & Problem Framing — **COMPLETE**

PRISMA 2020 across 7 themes; 1,382 records identified, 1,349 unique, 1,284 screened in, **82 included** (68 database + 14 hand-searched).

- Scripts: `src/literature/search_v2.py`, `eligibility_v2.py`, `enrich_v2.py`
- Artefacts: `literature_v2/prisma_counts.json`, `extraction_table.csv`

**Traps already hit and guarded — do not rediscover:**
- PubMed `efetch`: read the DOI from `./PubmedData/ArticleIdList/ArticleId`, **never** `.//ArticleId` — the latter also matches the article's own `<ReferenceList>` and returns a *cited* paper's DOI.
- A bare `CLAIM` search returns insurance-claims papers. Guarded.
- The stem `endoscop*` matches drug-induced sleep endoscopy, laryngoscopy and neuroendoscopy. Guarded for the three GI-specific themes.
- pandas 3.x keeps NaN through `.astype(str)`; `.fillna()` before any string join.
- A 64-character binary hash column is read back as an *integer* by `read_csv` unless `dtype=str` is forced.
- LibreOffice and pandoc are absent on this machine; Word COM via PowerShell is the working route for field updates and PDF export.

### ⬜ PHASE 2 — Baseline Reproduction

**Objective:** reproduce the published ConvNeXt-Tiny result on the complete-agreement subset, to validate the pipeline before changing anything.

**Success criterion:** macro F1 within ±1.5 points of the published ~85 on the 803-image consensus test set. If it does not reproduce, the pipeline is wrong — fix it before proceeding.

- Train 3,722 / Val 793 / Test 803 (complete-agreement only)
- ImageNet-pretrained ConvNeXt-Tiny; 224×224 Lanczos; normalise with **training-set** statistics
- Two-stage schedule: 10-epoch head warm-up at constant LR, then fine-tune the top 40% of feature layers for up to 100 epochs, early stopping on validation macro F1 (patience 10)
- AMP float16 + GradScaler (Turing has no BF16); batch 16–24, gradient accumulation as needed
- 100-iteration bootstrap on the test set, resampling **patients**

### ✅ PHASE 3 — Agreement-Stratified Evaluation (RQ1) — **COMPLETE**

**Result summary** (full detail in `Phase3_Report.docx` §3): annotator-marginalized
macro F1 83.92 (S-unanimous, n=803) → 48.95 (S-majority, n=342) → 26.15
(S-plurality, n=127) → 30.79 (pooled S-no-majority, n=81). Gap of 53.13 points
between S-unanimous and S-no-majority, 16× the 3.25-point published
ConvNeXt-Tiny/ConvNeXt-Large architecture gap — RQ1's magnitude claim strongly
supported. The decline is **not strictly monotonic** (Spearman ρ=−0.80,
p=0.20, n=4 tiers): S-plurality scores below the pooled tail, attributed to
macro-averaging noise over 23 classes at n≈100-130, not a genuine reversal
(the any-annotator hit rate shows no dip at that tier). Confusion-structure
comparison (O3): the model's wall-adjacent error share on S-unanimous
(89.68%) is within 0.12 points of the human value (89.8%); its
station-neighbouring share (85.57%) trails the human value (93.1%) by 7.5
points — carried forward as a Phase 6 Grad-CAM lead.

- Scripts: `src/models/phase3_{data,cache,eval,confusion}.py`
- Artefacts: `reports/phase3_{manifest_summary,stratified_metrics,confusion_structure}.json`, `reports/phase3_predictions_seed{1,2,3}.csv`
- Consistency gate: S-unanimous predictions reproduce `phase2_predictions_seed*.csv` exactly (803/803, all 3 seeds) — confirms the new evaluation path is wired correctly, not a new result.

Design notes retained below for reference (all pre-registered decisions were followed exactly as specified):

Take the Phase 2 model unchanged (3 seed checkpoints, frozen weights, no retraining) and evaluate it on strata it never trained or validated on. Phase 2 touched only the 60.2% complete-agreement subset; Phase 3 extends evaluation to the full official test split (1,353 images), stratified by how many of the 4 annotators agreed.

**Objectives**

- **O1.** Quantify macro F1 (and secondary metrics) separately for each agreement stratum of the test split, using the frozen Phase 2 checkpoints — no retraining.
- **O2.** Test RQ1's pre-registered hypothesis: macro F1 declines monotonically from S-unanimous to the no-majority stratum, by more than the between-architecture gap reported in the descriptor (ConvNeXt-Tiny vs ConvNeXt-Large ≈ 3.25 F1 points, §2.7).
- **O3.** Establish, quantitatively, whether the model's *errors* concentrate on the same wall/station-adjacent confusions that characterise *human* disagreement (§2.5) — a first, descriptive link to Phase 6.
- **O4.** Produce every stratum-level number, interval, and figure needed for the RQ1 chapter, fully reproducible from committed scripts and JSON artefacts, per the project's no-hand-typed-numbers rule (§8).

**n per test-split stratum** (computed from `official_splits/image_classification.csv`, Test rows only; matches the corpus-wide cascade in §2.4 exactly when summed):

| Stratum | Definition | n (test split) | n (corpus) |
|---|---|---|---|
| S-unanimous | 4/4 agree | 803 | 5,318 |
| S-majority | 3/4 agree | 342 | 2,158 |
| S-plurality | 2–1–1 (plurality winner, no majority) | 127 | 744 |
| S-tied | 2–2, no plurality winner | 73 | 539 |
| S-dispersed | all four differ | 8 | 75 |

803 + 342 + 127 + 73 + 8 = 1,353 = the full official test split. S-unanimous is exactly the Phase 2 test set (803 images) — the Phase 2 numbers are reused unchanged as the S-unanimous row, not recomputed.

**Pre-registered decisions (fixed here, before any evaluation script is run against these images):**

1. **Ground-truth definition per stratum.**
   - S-unanimous → the unanimous label (`Complete agreement` column).
   - S-majority → the 3/4 majority label (`Triple agreement` column).
   - S-plurality → the top-vote-getter (2 of 4 votes) as a *pseudo-label*, reported alongside — not instead of — the distribution-aware metrics below, since 2/4 is not a majority.
   - S-tied and S-dispersed → **no single-label ground truth exists.** Scored only by the two distribution-aware metrics below.
2. **Distribution-aware metrics (computed for every stratum, primary for S-tied/S-dispersed, secondary elsewhere):**
   - *Expected accuracy* = Σ over the 4 annotators of 1/4 × 𝟙[prediction == that annotator's label] (equivalently: the empirical probability mass the model's single prediction captures under the vote distribution).
   - *Any-annotator hit rate* = 𝟙[prediction ∈ the set of labels actually given by at least one annotator].
3. **Pooling rule, fixed now on corpus structure alone (before touching model outputs):** S-dispersed has only 8 test images — a patient-clustered bootstrap on 8 images is not informative alone. **S-tied and S-dispersed are pooled into a single S-no-majority stratum (n=81) for the primary RQ1 analysis and monotonicity test.** They are still reported separately as a descriptive breakdown, clearly labelled exploratory (n too small for a standalone CI).
4. **Primary RQ1 test:** macro F1 (using the pseudo/majority label where one exists, expected-accuracy-derived F1 surrogate for S-no-majority — see script docstring for the exact construction) across the four ordered strata {S-unanimous, S-majority, S-plurality, S-no-majority}, with monotonicity assessed via Spearman correlation between stratum order and macro F1, and pairwise patient-clustered bootstrap CIs on the S-unanimous − S-no-majority gap compared against the 3.25-point architecture benchmark.
5. **No retraining, no threshold tuning, no checkpoint reselection.** The 3 checkpoints already selected on Phase 2 validation macro F1 are used as-is. This is an evaluation-only phase by design (O1).
6. **Bootstrap:** patient-clustered, ≥1,000 resamples, same seed (`20260726`) and procedure as Phase 2 (§6), applied independently within each stratum.

⚠️ Consequently, the only new artefact this phase adds to the training pipeline is a **cache of the ~550 non-consensus test images** (1,353 − 803 already cached in Phase 2) through the identical 224×224 Lanczos + Phase-2-training-mean/SD preprocessing path — reusing, not reimplementing, `phase2_cache.py`'s logic.

### ⬜ PHASE 4 — Soft-Label & Uncertainty Training (RQ2, RQ3, RQ4)

| Config | Target construction | Purpose |
|---|---|---|
| C0 | Hard label, 4/4 subset only | Phase 2 reproduction (reference) |
| C1 | Majority label where one exists | Isolate the effect of adding contested images |
| C2 | Vote proportions across 4 annotators | Test RQ2 |
| **C3** | **Hard label + label smoothing** | **Control — the soft-target gain must exceed generic regularisation** |
| C4 | Soft targets + wall/station-structured penalty | Test RQ4 |

**C3 is not optional.** Without it, any C2 benefit is confounded with ordinary regularisation.

Uncertainty (RQ3): MC dropout as the cheap route; a 5-member deep ensemble trained **sequentially** if the budget allows. Report ECE and reliability diagrams. Correlate predictive entropy with per-image annotator vote entropy — the test the literature does not run, because it needs per-annotator labels.

Sensitivity analysis: leave-one-annotator-out, given FG2's outlier behaviour.

### ✅ PHASE 5 — External Validation (RQ3) — COMPLETE

HyperKvasir and GastroVision were acquired, hashed against the GastroHUN inventory (zero collisions) and mapped by a table frozen before any image was scored. **The blueprint's premise did not survive contact with the data.** GastroHUN's label space is wall × station; neither external corpus carries the wall axis, and neither has a class for four of the six stations. GastroVision has no retroflex-stomach class at all. A 23-way external validation is therefore not available from these corpora, and the phase was reframed — before scoring — into a 2-way anatomical collapse (P5-A), an out-of-protocol rejection endpoint (P5-B) and a calibration-ordering endpoint (P5-C).

- **P5-A TRANSFERS.** 78.41 binary macro F1 externally against 98.17 internally — a drop of -19.75 points, about twice the pre-registered expectation. Every arm met the pre-registered 3.0-point precision target, so these are powered verdicts rather than underpowered nulls.
- **P5-B: the pre-registered hypothesis was falsified, favourably.** Rejection was predicted at or below the 4.35% chance rate because GastroHUN's test split holds only 50 OTHERCLASS images in 1,353. It reached 63.4% for C2, and the arms separated sharply in the soft-target arms' favour. This benefit is invisible internally.
- **P5-C PRESERVED** (Spearman ρ = 0.700), but the top two arms exchange places. C3's under-confidence travelled essentially unchanged (-6.46 points externally against −6.45 internally), confirming the Phase 4 §4.2 claim that its calibration advantage was a global confidence shift — a property of the model, which follows it to a new centre and stops helping there.
- **Robustness.** Verdicts invariant to every ambiguous mapping flip: True.

**Carry-forward:** C2 is the recommended configuration, on external calibration and out-of-protocol rejection rather than internal accuracy. Report out-of-protocol rejection as a primary endpoint in Phases 6–7: it separated the arms where every internal endpoint failed to. Phase 5 intervals are image-level (no corpus publishes a case identifier) and must not be compared directly against the patient-clustered intervals of Phases 0–4.

**Phase 5B (self-training) is planned and gated on the above being frozen and committed.** Adapting to the external images before the clean transfer numbers exist would make the external validation circular.

### ✅ PHASE 6 — Explainability & Error Analysis — COMPLETE

The blueprint asked whether the model's residual error "reflects genuine visual ambiguity rather than model capacity". Answering that needs a comparator outside the model set, which no earlier phase had. Phase 6 introduces two — the annotators themselves, and the model's own confidence ordering — and keeps the attribution analysis quantitative so that it could fail. No retraining; the frozen checkpoints are re-used unchanged.

- **P6-A — the human comparator, and the phase's headline.** Each annotator is held out and scored against the other three; the model is scored against the same three, on the same images and the same patient resample. The frozen rule returns **ABOVE THE HUMAN PANEL** on the pooled contested stratum (Δ = +0.0647, CI +0.0281 to +0.1001). **Do not state this as 'the model beats the expert'.** Two asymmetries were found after scoring and then measured (P6-AMD-5): the model is optimised to predict *this* panel's consensus and the annotator is not; and the model *chooses* a label while the annotator is stuck with theirs. The modal vote of the same three references scores 0.6700 against 0.3902 for the annotator; the model reaches 0.4575, i.e. 24% of that headroom, and exceeds the oracle on **no** stratum. On the 2-1-1 stratum 50% of held-out annotators are singletons who cannot score well whatever their skill. **What P6-A establishes** is that the attainable ceiling on contested images is 0.67 rather than 1.00 — so much of the Phase 3 decline is the ceiling moving, as Phase 3B's ceiling-normalised analysis already found — while a substantial model shortfall against that reduced ceiling remains. The endpoint separates the two and sizes them. ⚠️ On S-unanimous the human side is 1.0 **by construction**, so that contrast is uninformative (P6-AMD-1).
- **P6-B — X3 settled, by a stronger argument than the one that raised it.** The amendment withdrew the Phase 3 claim because a model interval was compared against a human point estimate. Measuring both sides on the same images shows something more basic: S-unanimous contains **zero** annotator disagreement events, so the human geometry is *undefined* there. The Phase 3 comparison was cross-population, and neither the 0.12-point 'match' nor the 7.5-point 'shortfall' was ever like-for-like. Where the comparison *is* defined: wall geometry mirrors human geometry, station geometry diverges by -8.19 points (CI [-15.1, -2.85]) — a specific, nameable deficit rather than a general one.
- **P6-C — attribution scored, not displayed.** Grad-CAM dispersion against annotator vote entropy, *within* stratum: **NOT ESTIMABLE (vote entropy is constant on this stratum by construction)** (ρ = None, CI [None, None]). Evidence about Grad-CAM specifically; no method sweep was run, by design (P6-DEV-3).
- **P6-D — the Phase 5 carry-forward discharged.** Risk–coverage removes the single operating point Phase 5 was stuck at. Internally the arms barely separate (AURC 0.0828 for C2 against 0.0822 for C3); externally they separate decisively (0.1906 against 0.3235). The ordering agrees with Phase 5's rejection ranking: **CONSISTENT WITH THE PHASE 5 RANKING** (ρ = 1.0).

**Carry-forward to Phase 7.** The thesis's central claim is that agreement stratification separates a falling *reference standard* from a falling *classifier*, which the literature reports as one quantity. Both fall; the ceiling accounts for the larger share and a real model shortfall remains, and confidence degrades further and faster than discrimination. Report the human comparator curve **and the modal-vote oracle** beside every stratified performance figure — Phase 3's numbers mislead without the first, and the first misleads without the second. Use external AURC as the arm-selection endpoint; it is the only measurement in the project that separates the configurations decisively.

### ⬜ PHASE 7 — Thesis Writing & Defence

---

## 5. Model selection

⚠️ **v2.0 excluded deep learning on evidence-based grounds. That exclusion is void** — it applied to a 1,269-row tabular corpus, not to an 8,834-image imaging corpus.

| Model | Params | Fits 4 GB? | Role |
|---|---|---|---|
| **ConvNeXt-Tiny** | 28 M | ✅ | **Primary backbone** |
| ResNet-18 / 50 | 11 / 25 M | ✅ | Comparison |
| EfficientNet-B0 | 5 M | ✅ | Efficiency floor / fallback |
| ViT-B/16 | 86 M | ⚠️ tight | Optional, small batch |
| ConvNeXt-Large | 200 M | ❌ | **Cite as the published ceiling; do not attempt** |

---

## 6. Metrics

- **Primary:** macro F1 (near-balanced 23-class problem; matches the published baseline)
- **Secondary:** macro/weighted precision and recall; per-class F1 (**exploratory only** — see L1)
- **Calibration:** ECE, reliability diagrams, Brier score
- **Agreement:** Cohen's κ, Fleiss' κ, Krippendorff's α, Gwet's AC1
- **Uncertainty:** predictive entropy; Spearman ρ against annotator vote entropy
- **All intervals:** patient-clustered bootstrap, ≥1,000 resamples

⚠️ **Never resample images.** Phase 0 measured per-patient Fleiss κ at 0.7459 ± 0.1448 (range 0.069–1.000) — agreement varies systematically by patient, so images within a patient are not independent observations.

---

## 7. Compute budget

**NVIDIA GeForce GTX 1650, 4 GB VRAM, driver 592.82, compute capability 7.5 (Turing).**

⚠️ **Prerequisite:** the installed PyTorch is `2.12.0+cpu` — a CPU-only build, so `torch.cuda.is_available()` is `False`. **Install a CUDA wheel before Phase 2.**

- ConvNeXt-Tiny @ 224×224, AMP float16, batch 16–24 → fits
- No BF16 on Turing — use float16 + GradScaler
- Deep ensembles sequential, not parallel
- Estimated ~1 h per training run; Phase 4's five configurations ≈ 1 working day

---

## 8. Folder structure

```
Final defence/
├── Labeled Images/              # 387 patient dirs, 8,834 JPEGs
├── official_splits/             # image_classification.csv, sequence_classification.csv
├── metadata/                    # 3 JSON metadata files
├── src/
│   ├── data/                    # gastrohun_{inventory,agreement,structure,neardup,dup_calibration}.py
│   ├── literature/              # search_v2.py, eligibility_v2.py, enrich_v2.py
│   ├── models/                  # phase2_{data,cache,train,eval}.py, phase3_{data,cache,eval,confusion}.py
│   └── report/                  # figures_v2.py, figures_phase2.py, figures_phase3.py,
│                                 # build_docx_v2.py, build_phase2_docx.py, build_phase3_docx.py,
│                                 # content_phase*_v2.py, finalise_v2.py, finalise_phase2.py, finalise_phase3.py
├── reports/                     # gastrohun_*.json (Phase 0), phase2_*.json/csv, phase3_*.json/csv
├── literature_v2/               # PRISMA counts, extraction table
├── figures_v2/                  # 21 Phase 0/1 figures
├── figures_phase2/               # Phase 2 figures
├── figures_phase3/               # Phase 3 figures (F21-F24)
├── checkpoints/                  # phase2_convnext_tiny_seed{1,2,3}.pt (frozen; reused unchanged in Phase 3)
├── superseded/                  # archived v2.0 blueprint and the old report
├── Phase0_Phase1_Report.docx / .pdf
├── Phase2_Report.docx / .pdf
├── Phase3_Report.docx / .pdf
├── DATASET_DECISION_REPORT.md / Dataset_Decision_Report.docx / .pdf
└── THESIS_RESEARCH_BLUEPRINT.md (this file)
```

**Design principle:** no number is typed by hand. Every figure and table in the report is interpolated from a generated JSON or CSV artefact. Re-running the pipeline regenerates the document.

---

## 9. Regeneration pipeline

```bash
python src/data/gastrohun_inventory.py
python src/data/gastrohun_agreement.py
python src/data/gastrohun_structure.py
python src/data/gastrohun_neardup.py
python src/data/gastrohun_dup_calibration.py
python src/literature/search_v2.py
python src/literature/eligibility_v2.py
python src/literature/enrich_v2.py
python src/report/figures_v2.py
python src/report/build_docx_v2.py
python src/report/finalise_v2.py

# Phase 2
python src/models/phase2_data.py
python src/models/phase2_cache.py
python src/models/phase2_train.py --seed 1   # and --seed 2, --seed 3
python src/models/phase2_eval.py
python src/report/figures_phase2.py
python src/report/build_phase2_docx.py
python src/report/finalise_phase2.py

# Phase 3 (frozen Phase 2 checkpoints; no retraining)
python src/models/phase3_data.py
python src/models/phase3_cache.py
python src/models/phase3_eval.py
python src/models/phase3_confusion.py
python src/report/figures_phase3.py
python src/report/build_phase3_docx.py
python src/report/finalise_phase3.py
```

Runtime notes: the inventory decodes 8,834 JPEGs (~2.5 min); the near-duplicate scan is exhaustive over 39 M pairs with pixel verification (~12 min); calibration renders 8,000 control pairs (~5 min). Everything else runs in seconds.

---

## 10. Declared limitations

| ID | Limitation | Mitigation |
|---|---|---|
| L1 | 22/23 classes underpowered for per-class claims | Macro-averaged primary; per-class exploratory |
| L2 | No age or sex anywhere in the release | No demographic subgroup or fairness claim |
| L3 | Single centre, single vendor (Olympus) | Phase 5 external validation is required, not optional |
| L4 | Acquisition stream imbalanced across splits (χ² p = 1.9e-22) | Report per-split composition; sensitivity analysis excluding video frames |
| L5 | Review searched PubMed/MEDLINE only | CS works added via the PRISMA other-methods arm; declared |
| L6 | Clinical context for only 60.2% of patients | No claim linking landmark performance to disease status |
| L7 | Four annotators is a small panel | Soft targets treated as an ordinal ambiguity signal, not a calibrated probability |

---

## 11. Timeline

| Week | Phase | Milestone |
|---|---|---|
| ✅ — | 0–1 | Audit + review complete; report delivered |
| ✅ 1 | 2 | CUDA installed; baseline reproduces within ±1.5 F1 |
| ✅ 2–3 | 3 | RQ1 answered — the stratified performance curve |
| 4–6 | 4 | RQ2/RQ3/RQ4 — C0–C4 comparison, calibration, uncertainty |
| 7–8 | 5 | RQ3 external — HyperKvasir / GastroVision |
| 9 | 6 | Grad-CAM; model-vs-human confusion comparison |
| 10–12 | 7 | Thesis writing |
| 13–14 | — | Buffer, defence preparation |

---

## 12. Risk register

| Risk | Likelihood | Impact | Response |
|---|---|---|---|
| Baseline does not reproduce | Medium | High | Budget a week; check normalisation statistics and the exact consensus subset first |
| 4 GB VRAM insufficient even for ConvNeXt-Tiny | Low | High | Drop to 192×192, gradient accumulation, or EfficientNet-B0 |
| Contested strata too small for significance | Medium | Medium | Pre-specified pooling of S-tied and S-dispersed |
| Soft-label gain not separable from regularisation | Medium | Medium | The C3 control exists precisely for this |
| External landmark mapping too coarse to be meaningful | Medium | Medium | Report as a coarse-grained check with the mapping table stated; do not overclaim |
| Scope creep into sequence/video classification | Medium | Medium | Out of scope; the 96.86 GB video release is deliberately not downloaded |

---

## 13. Phase 3 implementation checklist

Execution order; each step gated on the previous one's validation criterion.

| # | Task | Input | Output | Validation criterion |
|---|---|---|---|---|
| P3.1 | Build full-test-split manifest with per-annotator votes and agreement tier | `official_splits/image_classification.csv`, `reports/gastrohun_hashes.csv` | `data/phase3_test_manifest.csv` | 1,353 rows; tier counts match the table in §4 Phase 3 exactly (803/342/127/73/8); 0 patient overlap with Phase 2 train/val (reuse Phase 0/2 patient sets) |
| P3.2 | Cache the ~550 non-consensus test images at 224×224 | `Labeled Images/`, P3.1 manifest | `data/phase3_cache_224.npy`, `data/phase3_cache_index.csv` | every cached image resolves against the Phase 0 SHA-256 inventory (GATE 3 re-applied); identical resize path to `phase2_cache.py` (Lanczos, RGB) |
| P3.3 | Run the 3 frozen Phase 2 checkpoints on the full 1,353-image test split | checkpoints `phase2_convnext_tiny_seed{1,2,3}.pt`, P3.1+P3.2 caches, `phase2_norm_stats.json` | `reports/phase3_predictions_seed{1,2,3}.csv` | S-unanimous-row predictions reproduce `phase2_predictions_seed*.csv` byte-for-byte (same 803 images, same model, same normalisation) — this is the internal consistency check that the new pipeline is wired correctly |
| P3.4 | Compute per-stratum metrics: macro F1, expected accuracy, any-annotator hit rate, patient-clustered bootstrap CI, per the pre-registered rule (§4 Phase 3) | P3.3 predictions, P3.1 tiers | `reports/phase3_stratified_metrics.json` | S-unanimous macro F1 equals the Phase 2 aggregate (83.92, §Phase 2) to rounding; monotonicity (Spearman ρ) and the S-unanimous−S-no-majority gap vs the 3.25-point architecture benchmark computed and reported regardless of direction |
| P3.5 | Confusion-structure comparison: adjacent-wall / neighbouring-station error share, model vs. the human figures from §2.5 | P3.3 predictions, `reports/gastrohun_structure.json` | `reports/phase3_confusion_structure.json` | adjacent-wall and neighbouring-station shares computed with the same definition as Phase 0 (89.8% / 93.1% benchmarks) |
| P3.6 | Generate figures: stratified performance curve with CIs, vote-pattern-vs-error scatter, model-vs-human confusion overlap, per-stratum reliability | P3.4, P3.5 | `figures_v2/F21`–`F24_*.png` | every number plotted traces to a JSON field; no hand-entered values |
| P3.7 | Write Phase 3 content module and build the DOCX/PDF | all of the above | `Phase3_Report.docx/.pdf` | ToC in §14 fully populated; every figure/table numbered and cross-referenced; verdict stated for RQ1 |
| P3.8 | Update blueprint status board and completed-task register | P3.7 | `THESIS_RESEARCH_BLUEPRINT.md` v3.2 | Phase 3 row moved to ✅ COMPLETE with verdict; Phase 4 pre-conditions (if any) noted |

## 14. Phase 3 report — Table of Contents

```
PHASE 3 REPORT
Agreement-Stratified Evaluation of the ConvNeXt-Tiny Landmark Classifier

Front matter
  Title page
  Abstract (structured: Background / Objective / Methods / Results / Conclusion)
  List of Figures
  List of Tables
  List of Abbreviations

1. Introduction
  1.1  Recap: Phase 0 corpus audit and Phase 2 baseline reproduction
  1.2  Motivation — why evaluate outside the training distribution's agreement tier
  1.3  Research question and pre-registered hypothesis (RQ1)
  1.4  Chapter roadmap

2. Methods
  2.1  Frozen model specification (unchanged from Phase 2: architecture, seeds, checkpoints)
  2.2  Full test-split composition and agreement tiers
     2.2.1  Tier definitions and construction from the 4-annotator vote matrix
     2.2.2  Pre-registered ground-truth rule per tier
     2.2.3  Pre-registered pooling rule (S-tied + S-dispersed -> S-no-majority)
  2.3  Preprocessing and inference pipeline
     2.3.1  Image cache extension (non-consensus test images)
     2.3.2  Normalisation and inference settings (unchanged from Phase 2)
     2.3.3  Internal consistency check against Phase 2 S-unanimous results
  2.4  Metrics
     2.4.1  Macro F1 and secondary metrics (single-label strata)
     2.4.2  Expected accuracy and any-annotator hit rate (no-majority strata)
     2.4.3  Patient-clustered bootstrap procedure
  2.5  Confusion-structure comparison protocol (model vs. human, §Phase 0 benchmarks)
  2.6  Statistical analysis plan
     2.6.1  Monotonicity test (Spearman rank correlation across ordered strata)
     2.6.2  Gap test: S-unanimous - S-no-majority vs. the architecture benchmark

3. Results
  3.1  Test-split stratum composition (Table 3.1)
  3.2  Per-stratum performance (Table 3.2; Figure 3.1 stratified performance curve with 95% CIs)
  3.3  Reproduction check: S-unanimous stratum vs. Phase 2 published-here result (Table 3.3)
  3.4  Monotonicity and gap test results (Table 3.4)
  3.5  Distribution-aware metrics on no-majority images (Table 3.5)
  3.6  Per-class behaviour across strata (exploratory; Figure 3.2)
  3.7  Confusion-structure comparison: model vs. human disagreement geometry (Table 3.6; Figure 3.3)
  3.8  Calibration by stratum (Figure 3.4; ECE, reliability diagrams)
  3.9  Sensitivity checks
     3.9.1  Per-seed stability across strata
     3.9.2  Acquisition-stream composition per stratum (link to L4)

4. Discussion
  4.1  Interpretation against RQ1's pre-registered hypothesis
  4.2  Where the model's degradation does, and does not, mirror human disagreement
  4.3  Implications for Phase 4 (soft-label training) design choices
  4.4  Comparison with the wider literature (Phase 1 findings on ground-truth construction)
  4.5  Limitations specific to this phase
     4.5.1  Small n in S-dispersed / pooled S-no-majority
     4.5.2  Pseudo-labels in S-plurality are not a validated ground truth
     4.5.3  Single-architecture, single-training-run generalisation (mitigated by 3 seeds)

5. Conclusion
  5.1  Answer to RQ1
  5.2  Carry-forward decisions for Phase 4

Appendices
  A. Full per-class, per-stratum metric tables
  B. Confusion matrices per stratum (23x23)
  C. Bootstrap distributions (diagnostic plots)
  D. Script and artefact manifest (reproducibility index)
  E. Pre-registration record (verbatim, timestamped before P3.3 ran)

References
```

## 15. Reporting standards

CLAIM (medical imaging AI) · TRIPOD+AI (prediction models) · STARD-AI (diagnostic accuracy) · PROBAST+AI (risk of bias) · PRISMA 2020 (the review).

Phase 1 found that the commonest omissions in this literature are missing external validation, incomplete population description, unexamined ground-truth construction, and absent calibration reporting. This design addresses three of the four directly; the fourth (population description) cannot be met on this corpus and is declared as L2 rather than passed over silently.

---

## 16. Phase 4 implementation checklist

Execution order; each step gated on the previous one's validation criterion. The
authoritative record of every gate is the JSON artefact it writes, not this table.
Full derivation of the design decisions is in `PHASE4_PLAN.md`.

| # | Task | Output | Validation criterion |
|---|---|---|---|
| P4.1 | Build the extended cohort E (majority-or-better Train/Validation) with the per-image 4-annotator vote matrix | `data/phase4_train_manifest.csv`, `reports/phase4_cohort.json` | **P4.1a** 5,228 / 1,103 with tier split 3,722+1,506 / 793+310 · **P4.1b** 23 classes, no annotator vote outside the fixed class index · **P4.1c** 0 patient overlap, including against the Phase 3 test split · **P4.1d** every filename in the Phase 0 SHA-256 inventory and on disk · **P4.1e** the 4/4 rows reproduce the Phase 2 cohort exactly |
| P4.2 | Cache the cohort at 224x224 through the identical Phase 2 path | `data/phase4_cache_224.npy`, `reports/phase4_cache_gate.json` | **P4.2** all 4,515 images shared with the Phase 2 cache decode **bit-identically** — exhaustive, not sampled |
| P4.3 | Build the anatomical (wall x station) distance matrix for C4 | `reports/phase4_distance_matrix.json`, `data/phase4_distance_matrix.npy` | **P4.3a** symmetric, zero diagonal, range [0,1] · **P4.3b** 240 adjacent / 120 opposite wall pairs match the Phase 0 definitions · **P4.3c** 138 neighbouring-station pairs match |
| P4.4 | Measure the real epoch cost on the extended cohort with the C4 penalty active | `reports/phase4_probe.json` | measured on this hardware, never projected from Phase 2 |
| P4.5 | **Freeze the pre-registration** | `reports/phase4_prereg.json` | refuses to overwrite an existing file; epsilon and lambda **derived** rather than chosen; verdict rules fixed for RQ2/RQ3/RQ4 before any training |
| P4.6 | Train C1-C4 x 3 seeds, seed-major order | `checkpoints/phase4_{cfg}_seed{k}.pt`, `reports/phase4_run_*.json` | every run records its realised stop reason, so a bound epoch cap is visible rather than hidden |
| P4.7 | Inference on the full 1,353-image test split + MC stochastic-depth sampling | `reports/phase4_predictions_*.csv`, `phase4_probs_*.npz`, `phase4_mc_*.npz`, `phase4_infer_gate.json` | **P4.6a** row order matches the Phase 3 cache index · **P4.6b** saved argmax equals the saved prediction · **P4.6c** architecture stochastic inventory verified at run time · C0's deterministic pass reproduces the Phase 3 predictions exactly |
| P4.8 | Agreement-stratified evaluation and the paired configuration contrasts (RQ2 accuracy) | `reports/phase4_stratified_metrics.json` | **P4.7** the C0 arm reproduces `phase3_stratified_metrics.json` to < 1e-9 |
| P4.9 | Calibration by configuration and stratum (RQ2 calibration — a **primary** endpoint per the Phase 3 carry-forward) | `reports/phase4_calibration.json` | C0 reproduces `phase3b_calibration.json` ECE per stratum |
| P4.10 | Uncertainty and the entropy correlation (RQ3) | `reports/phase4_uncertainty.json` | **within**-stratum rho is the primary quantity; S-unanimous reported as null, never 0; C0's pooled value reproduces Phase 3's 0.320 |
| P4.11 | Anatomy-aware loss analysis (RQ4) | `reports/phase4_structure_eval.json` | C0's wall-adjacent / station-neighbouring shares reproduce `phase3_confusion_structure.json` |
| P4.12 | Leave-one-annotator-out sensitivity | `reports/phase4_loao.json` | strata held fixed at the 4-annotator definition; the RQ2 verdict recomputed under each drop |
| P4.13 | Figures | `figures_phase4/P4_F25`-`F32_*.png` | every plotted value traces to a JSON field |
| P4.14 | Build the report | `Phase4_Report.docx` / `.pdf` | ToC/LoF/LoT populated; every verdict sentence selected from a pre-registered verdict field rather than pre-written |
| P4.15 | Update this blueprint and commit | `THESIS_RESEARCH_BLUEPRINT.md` v3.4 | Phase 4 row moved to complete with its verdicts; Phase 5 pre-conditions noted |

### Design decisions Phase 4 had to close, and why

The blueprint fixes the five configurations but not everything they need. Four gaps were
closed **before** the pre-registration was frozen:

1. **Cohort for C1-C4.** A hard label does not exist on the 2-2 and 1-1-1-1 tiers, so C3
   cannot be scored there. Cohort E is therefore held constant across C1-C4, making those
   four arms a pure target-construction contrast and C0 to C1 a separate cohort contrast.
   Cost: the 1,150 most ambiguous Train/Validation images never enter training.
2. **epsilon for C3.** Derived by matching the expected probability mass C2 displaces from
   the modal label (0.072016, giving epsilon = 0.075290), not set to a convention. Mass
   rather than entropy, because the gradient of the soft-target cross-entropy is (q - t),
   so the displaced mass *is* the perturbation. Entropy matching would have given 0.021228
   — a materially weaker control; both values are recorded.
3. **lambda for C4.** Fixed a priori at unit weight, no sweep (P4-DEV-3). RQ4 is therefore
   tested at one point in lambda-space and a null is evidence about unit weight only.
4. **Scale for the contrasts.** Ceiling normalisation was needed in Phase 3 because it
   compared *strata* with different attainable maxima. Phase 4 compares *configurations
   within a stratum*, where the ceiling is one shared positive constant that divides out
   of the difference; contrasts are therefore raw, with normalised levels tabulated
   alongside.

### Declared deviations (full text in `reports/phase4_prereg.json`)

| ID | Item | Adopted | Because |
|---|---|---|---|
| P4-DEV-1 | "MC dropout" (§4) | MC **stochastic depth** | torchvision ConvNeXt-Tiny has 0 `nn.Dropout` and 0 BatchNorm modules, verified at run time; its 18 `StochasticDepth` modules are the only stochastic mechanism, and it is the one the network was trained with |
| P4-DEV-2 | 5-member deep ensemble | 3 members | the blueprint made this explicitly conditional on budget; 4 configs x 3 seeds is already 12 runs |
| P4-DEV-3 | lambda for the C4 penalty | 1.0, no sweep | a 3-value sweep is 9 further runs |
| P4-DEV-4 | Dataloader workers | 2 (Phase 2 used 3) | 3 workers over the 953 MB cache reproducibly raised `CUDNN_STATUS_INTERNAL_ERROR_HOST_ALLOCATION_FAILED` on this 16 GB machine |

## 17. Phase 4 report — Table of Contents

```
PHASE 4 REPORT
Soft-Label and Uncertainty Training (RQ2, RQ3, RQ4)

Front matter
  Title page (pre-registered verdicts stated on it)
  Abstract (Background / Objective / Methods / Results / Conclusion)
  List of Figures - List of Tables - List of Abbreviations

1. Introduction
  1.1  What Phases 2 and 3 established, and what they leave open
  1.2  Why the target, and not the architecture
  1.3  Research questions and pre-registered hypotheses (RQ2, RQ3, RQ4)
  1.4  Chapter roadmap

2. Methods
  2.1  The configuration matrix C0-C4
     2.1.1  The extended cohort E, and why it is held constant
     2.1.2  Deriving epsilon: the control has to be matched, not guessed
     2.1.3  The anatomical distance matrix and the C4 penalty
  2.2  What is held fixed
     2.2.1  Compute budget and the epoch cap
  2.3  Evaluation
     2.3.1  Calibration and uncertainty estimators

3. Results
  3.1  Training behaviour of the five configurations
  3.2  RQ2, accuracy: performance by configuration and stratum
     3.2.1  The pre-registered contrasts
  3.3  RQ2, calibration
  3.4  RQ3: does predictive uncertainty track human disagreement?
  3.5  RQ4: the anatomy-aware loss
  3.6  Sensitivity
     3.6.1  Per-seed stability
     3.6.2  Leave-one-annotator-out, FG2 included

4. Discussion
  4.1  RQ2: what the control bought
  4.2  RQ2 calibration, and what it says about the Phase 3 finding
  4.3  RQ3
  4.4  RQ4
  4.5  Relation to the descriptor's own FG-agreement result (§2.7)
  4.6  Limitations specific to this phase
  4.7  Implications for Phases 5-7

5. Conclusion
  5.1  Answers to RQ2, RQ3, RQ4
  5.2  Carry-forward decisions

Appendices
  A. Per-configuration, per-stratum metric tables
  B. Training histories (every run, with realised stop reason)
  C. Pre-registration record and declared deviations
  D. Script and artefact manifest (reproducibility index)
  E. Analyses NOT executed, and what each would cost

References
```

## 18. Phase 4 regeneration pipeline

```bash
python src/models/phase4_data.py            # cohort E, gates P4.1a-e
python src/models/phase4_cache.py           # 224px cache, gate P4.2
python src/models/phase4_structure.py       # distance matrix, gates P4.3a-c
python src/models/phase4_train.py --probe   # measured epoch cost
python src/models/phase4_prereg.py          # FROZEN before any training
bash   src/models/phase4_run_all.sh         # C1-C4 x 3 seeds
python src/models/phase4_infer.py           # gates P4.6a-c, MC sampling
python src/models/phase4_eval.py            # RQ2 accuracy, gate P4.7
python src/models/phase4_calibration.py     # RQ2 calibration
python src/models/phase4_uncertainty.py     # RQ3
python src/models/phase4_structure_eval.py  # RQ4
python src/models/phase4_loao.py            # LOAO sensitivity
python src/report/figures_phase4.py
python src/report/build_phase4_docx.py
python src/report/finalise_phase4.py
python src/report/update_blueprint_phase4.py  # rewrites this file's status board
```

Runtime note: the 12 training runs dominate, at roughly 80-110 min each on the GTX 1650
(~17 h total). Everything downstream of them runs in minutes, except `phase4_infer.py`,
whose 20-sample MC pass over 15 checkpoints takes about an hour.
