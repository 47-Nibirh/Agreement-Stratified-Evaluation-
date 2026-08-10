# Phase 6 — Content List and Implementation Checklist

**Derived from** `THESIS_RESEARCH_BLUEPRINT.md` v3.5 §4 PHASE 6, §2.5 (disagreement geometry),
§2.7, §6 (metrics), §10 (limitations), §15 (reporting standards), plus the Phase 3 rev-1
amendment X3 in `reports/phase3b_amendment.json` and the Phase 5 carry-forward in
`reports/phase5_carry_forward.json`.

Nothing below is invented. Each item traces to a blueprint clause, to a withdrawn claim that
must now be settled, or to a carry-forward decision.

---

## 0. What Phase 6 inherits, verified against the artefacts rather than assumed

Everything Phase 6 needs already exists on disk. This was checked, not presumed:

| Asset | Location | Verified |
|---|---|---|
| 18 frozen checkpoints | `checkpoints/phase2_convnext_tiny_seed{1,2,3}.pt` (= C0), `phase4_{C1..C4}_seed{1,2,3}.pt`, `phase5b_C2_seed{1,2,3}.pt` | present |
| Full test split, cached at 224 | `data/phase3_cache_224.npy` — `(1353, 224, 224, 3)` uint8 | shape confirmed |
| Per-image 4-annotator vote matrix | `data/phase3_cache_index.csv` — `vote_0..vote_3`, `tier`, `tier_pooled`, `patient` | columns confirmed |
| Per-arm class posteriors | `reports/phase3_probs_seed*.npz` (C0), `phase4_probs_C*_seed*.npz` — `(1353, 23)` | shape confirmed |
| Human confusion benchmarks | `reports/gastrohun_structure.json` — 12,800 disagreement events, wall/station pair tables | present |
| Anatomical geometry | `reports/phase4_distance_matrix.json`, `WALL_CYCLE`, `WALL_ADJACENT`, station axis | present |
| Metric primitives, sklearn-verified | `src/models/phase3b_common.py` (`selftest()` at import, 1e-12) | present |
| Patient-clustered bootstrap | `phase3b_common.patient_bootstrap`, seed 20260726, 1,000 resamples | present |
| CUDA | `torch 2.12.0+cu126`, GTX 1650 available | confirmed at runtime |

**Consequence: Phase 6 requires no retraining.** It is an inference-and-analysis phase, like
Phase 3. The only new compute is one Grad-CAM backward pass per (image × arm × seed).

### The three debts Phase 6 exists to settle

1. **X3 — the withdrawn O3 claim.** Phase 3 reported that the model's wall-confusion geometry
   (89.68%) sits "within 0.12 points" of the human value (89.8%) and that its station geometry
   (85.57%) trails the human 93.1% by 7.5 points. The rev-1 amendment withdrew both to
   hypothesis status: the intervals were [83.18, 96.00] and [76.68, 93.36], and the station
   interval **contains** the human value. Phase 6 must settle this with intervals on *both*
   sides of the comparison — the human benchmark is itself an estimate and has never been
   given one.
2. **The blueprint's actual Phase 6 question.** "Does the model's confusion matrix mirror the
   human confusion structure? If it does, that is strong evidence the residual error reflects
   genuine visual ambiguity rather than model capacity." Confusion geometry alone cannot
   answer this — it shows the errors have the same *shape*, not that they are the same
   *difficulty*. A human comparator is required, and none exists anywhere in the project.
3. **The Phase 5 carry-forward.** "Report out-of-protocol rejection as a primary endpoint in
   Phases 6–7: it separated the arms where every internal endpoint failed to." Phase 5
   measured rejection at a single operating point (`argmax == OTHERCLASS`). Phase 6 owes it a
   threshold-free treatment.

---

## 1. The finding that shapes this phase, stated before anything else

Phases 3–5 produced one durable result and three unresolved ones. The durable result is a
**calibration collapse**: across agreement strata, expected accuracy falls 56.57 points while
mean confidence falls 9.34, and no target construction in C0–C4 repairs it. The unresolved
ones — RQ2 accuracy (+1.40, CI −0.88 to +3.61), RQ3 (supported for no configuration), RQ4
(not resolved at λ=1) — are all *comparisons between models*.

Phase 6 changes the comparator. Instead of asking which target construction wins, it asks
what the errors **are**, and against **whom** they should be judged. That reframing is what
converts a chapter of nulls into a chapter of findings, and it is the reason the human
comparator (P6-A) is the first endpoint rather than an appendix.

**A pre-registered warning about Grad-CAM.** Attribution maps are the standard way this
chapter is written in the literature, and the standard way is not a measurement: a grid of
heatmaps invites the reader to agree with the author. Phase 6 therefore commits, before any
map is rendered, to scoring attribution *quantitatively* — dispersion, inter-seed stability,
inter-arm agreement — and to reporting those numbers whatever they say. Qualitative panels
appear only after the quantitative endpoint has been stated.

---

## 2. Endpoints and pre-registered verdict rules

Four endpoints. Each has a rule fixed in `reports/phase6_prereg.json` before any scoring runs.

### P6-A — The human comparator: does the model degrade the way a human does?

For each held-out annotator *a*, score annotator *a* as if they were a classifier, against the
remaining three annotators, with the identical metric applied to the model:

```
human_a  = mean over b != a of  macroF1( votes[:,b] , votes[:,a] )
model_a  = mean over b != a of  macroF1( votes[:,b] , model_prediction )
delta_a  = model_a - human_a
```

Averaged over the four held-out annotators, computed per stratum, paired patient-clustered
bootstrap (the same rows, the same resample, both sides scored before differencing).

This is exactly comparable by construction: same reference labels, same metric, same images,
same interval procedure. It is the first time in this project that the model has been placed
on the same axis as the people who produced its labels.

> **Verdict rule.** Per stratum: **BELOW THE HUMAN PANEL** if the CI on `delta` excludes 0
> below; **ABOVE** if it excludes 0 above; **INDISTINGUISHABLE FROM THE HUMAN PANEL** if it
> contains 0. The scientific interest is concentrated in the contested strata: if the model is
> indistinguishable from a human there while scoring 26–49 macro F1, the low absolute scores
> of Phase 3 are a property of the task, not of the model.

### P6-B — Confusion geometry, both sides given intervals (settles X3)

Model wall-adjacent and station-neighbouring error shares, per stratum, with patient-clustered
CIs — **and** the same two quantities recomputed for the human panel from the annotator
disagreement events on the same images, with the same interval procedure. Phase 0's 89.8% and
93.1% are corpus-wide point estimates with no interval; they are re-derived here on the test
split so that the two sides are commensurable.

> **Verdict rule.** Per axis per stratum: **MIRRORS HUMAN GEOMETRY** if the paired CI on
> (model share − human share) contains 0; **DIVERGES** if it excludes 0. Reported for all four
> strata, not only S-unanimous — Phase 3 measured this on S-unanimous alone, which is the one
> stratum where the model makes fewest errors.

### P6-C — Attribution as a measurement, not an illustration

Grad-CAM at the final ConvNeXt stage, for the predicted class, on all 1,353 test images ×
5 arms × 3 seeds. Three scored quantities per map:

- **dispersion** — normalised Shannon entropy of the CAM treated as a spatial distribution.
  High dispersion = the evidence is spread over the frame rather than localised.
- **inter-seed stability** — mean pairwise IoU of the top-20% attribution masks across the
  three seeds of one arm, per image.
- **inter-arm agreement** — mean pairwise IoU across arms at fixed seed, per image.

> **Primary verdict rule (P6-C1).** **SUPPORTED** if the *within-stratum* Spearman ρ between
> CAM dispersion and annotator vote entropy has a CI excluding 0 above, on **S-majority** — the
> same stratum Phase 4 pre-registered for RQ3, chosen for the same reason (it is the largest
> contested stratum with a defined reference label). Within-stratum, never pooled: Phase 3B
> established that the pooled correlation mostly measures which stratum an image is in.
>
> **Secondary (P6-C2).** Inter-seed stability compared between S-unanimous and the pooled
> contested stratum. **DEGRADES ON CONTESTED IMAGES** if the CI on the difference excludes 0.
>
> This is the endpoint that gives RQ3 a second chance on a different modality. Phase 4 found
> that *predictive* entropy does not track human disagreement within stratum (ρ = 0.02–0.08).
> Whether *spatial* attribution does is an open question, and a negative answer is as
> reportable as a positive one — it would say the model's uncertainty is not localised
> anywhere in the image.

### P6-D — Selective prediction: the Phase 5 carry-forward, done threshold-free

Risk–coverage curves per arm, internal (1,353 GastroHUN test images) and external (the Phase 5
panel, where out-of-protocol images make rejection the *correct* action), scored by max
softmax. Report AURC, coverage at 10% risk, and risk at 80% coverage.

> **Verdict rule.** Arms ranked by AURC with paired CIs. **CONSISTENT WITH THE PHASE 5
> RANKING** if the AURC ordering agrees with the Phase 5 rejection ordering (Spearman ρ over
> the five arms, CI excluding 0 above); otherwise **INCONSISTENT**, which would mean the
> single-operating-point rejection result did not generalise to the full curve.

---

## 3. Phase 6 content list (report table of contents)

```
PHASE 6 REPORT
Explainability and Error Analysis: What the Model's Mistakes Are, and Whose Standard to Judge Them By

Front matter
  Title page (with the four pre-registered verdicts stated on it)
  Abstract — Background / Objective / Methods / Results / Conclusion
  Table of Contents · List of Figures · List of Tables · Abbreviations

1. Introduction
  1.1  What Phases 3-5 settled, and the three debts they left
     1.1.1  X3: a withdrawn claim about confusion geometry
     1.1.2  The blueprint's question: ambiguity or capacity?
     1.1.3  The Phase 5 carry-forward on out-of-protocol rejection
  1.2  Why the comparator changes in this phase
  1.3  Endpoints and pre-registered verdict rules (P6-A, P6-B, P6-C, P6-D)
  1.4  Chapter roadmap

2. Methods
  2.1  What is held fixed: checkpoints, cache, preprocessing, seeds
     2.1.1  No retraining, no threshold tuning, no checkpoint reselection
  2.2  P6-A: the held-out-annotator construction
     2.2.1  Why annotator a must be scored against the other three, not all four
     2.2.2  Pairing, and why the same resample scores both sides
  2.3  P6-B: giving the human benchmark an interval
     2.3.1  Re-deriving the Phase 0 geometry on the test split
     2.3.2  Wall adjacency and station neighbouring, unchanged definitions
  2.4  P6-C: Grad-CAM as a scored quantity
     2.4.1  Layer choice, target class, and normalisation
     2.4.2  Dispersion, inter-seed stability, inter-arm agreement
     2.4.3  Why the primary correlation is within-stratum
  2.5  P6-D: risk-coverage, AURC, and the external panel
  2.6  Gate table (P6.0-P6.6) and the reproduction checks against Phases 3-5

3. Results
  3.1  P6-A: model versus the human panel, by stratum (Table 3.1; Figure F38)
     3.1.1  Per-held-out-annotator breakdown, FG2 included
  3.2  P6-B: confusion geometry with intervals on both sides (Table 3.2; Figure F39)
     3.2.1  Settlement of X3
     3.2.2  Geometry on the contested strata, which Phase 3 never measured
  3.3  P6-C: attribution
     3.3.1  Dispersion versus vote entropy, within stratum (Table 3.3; Figure F40)
     3.3.2  Inter-seed and inter-arm stability (Figure F41)
     3.3.3  Qualitative panels, shown only after the quantitative result (Figure F42)
  3.4  P6-D: risk-coverage, internal and external (Table 3.4; Figures F43, F44)
     3.4.1  Does the AURC ranking agree with Phase 5's rejection ranking?
  3.5  Cross-endpoint synthesis (Figure F45)
  3.6  Sensitivity
     3.6.1  Per-seed stability of every endpoint
     3.6.2  Leave-one-annotator-out on P6-A itself
     3.6.3  Arm sensitivity: does any verdict depend on which arm is read?

4. Discussion
  4.1  Ambiguity or capacity: what P6-A and P6-B jointly license
  4.2  What attribution did and did not explain
  4.3  Selective prediction as the deployable form of the calibration finding
  4.4  Relation to the Phase 3 calibration collapse and the Phase 4 nulls
  4.5  Limitations specific to this phase
     4.5.1  Grad-CAM is one attribution method among several
     4.5.2  Four annotators bound the precision of the human comparator
     4.5.3  Contested strata remain small (n = 342 / 127 / 81)
  4.6  Implications for Phase 7

5. Conclusion
  5.1  Answers to P6-A, P6-B, P6-C, P6-D
  5.2  Carry-forward decisions for the thesis chapter

Appendices
  A. Per-stratum, per-arm, per-seed metric tables
  B. Per-held-out-annotator comparator tables
  C. Pre-registration record and declared deviations
  D. Script and artefact manifest (reproducibility index)
  E. Analyses NOT executed, and what each would cost
References
```

### Figures

Phase 5 realised F33–F37 on disk; Phase 6 continues at F38.

| ID | Content | Source artefact |
|---|---|---|
| P6_F38 | Model vs human panel by stratum, with paired CIs | `phase6_human.json` |
| P6_F39 | Confusion geometry, model and human, both with intervals, all strata | `phase6_geometry.json` |
| P6_F40 | CAM dispersion vs annotator vote entropy, within stratum | `phase6_cam_eval.json` |
| P6_F41 | Inter-seed and inter-arm attribution stability by stratum | `phase6_cam_eval.json` |
| P6_F42 | Qualitative Grad-CAM panels: unanimous vs contested, correct vs error | `phase6_cams_*.npz` |
| P6_F43 | Risk–coverage curves, internal, per arm | `phase6_selective.json` |
| P6_F44 | Risk–coverage curves, external, per arm | `phase6_selective.json` |
| P6_F45 | Cross-endpoint synthesis: arm ranking under every Phase 3–6 endpoint | all of the above |

---

## 4. Implementation checklist (execution order, each gated on the previous)

| # | Task | Output | Validation criterion |
|---|---|---|---|
| **P6.0** | Freeze the pre-registration | `reports/phase6_prereg.json` | refuses to overwrite an existing file; all four verdict rules, the primary stratum, the CAM layer and the top-q threshold fixed before any scoring |
| **P6.1** | Shared primitives: panel build, wall/station parsing, vote entropy | `src/models/phase6_common.py` | **P6.1a** panel row order identical to `data/phase3_cache_index.csv` · **P6.1b** re-scoring C0 through the new panel reproduces `phase3_stratified_metrics.json` marginalized macro F1 to < 1e-9 |
| **P6.2** | P6-A human comparator | `reports/phase6_human.json` | **P6.2a** the 4-annotator-marginalized model score computed here equals the Phase 3 value to < 1e-9 · **P6.2b** every held-out-annotator score computed on the same rows as its paired model score |
| **P6.3** | P6-B confusion geometry with intervals on both sides | `reports/phase6_geometry.json` | **P6.3a** C0's S-unanimous wall/station shares reproduce `phase3_confusion_structure.json` exactly (89.68 / 85.57) · **P6.3b** adjacency definitions identical to `phase4_structure.py` |
| **P6.4** | Grad-CAM computation | `reports/phase6_cams_{arm}_seed{k}.npz` | **P6.4a** one map per image, finite, non-negative · **P6.4b** the class the CAM targets equals the saved argmax in the frozen prediction files, exactly · **P6.4c** row order matches the cache index |
| **P6.5** | P6-C attribution endpoints | `reports/phase6_cam_eval.json` | **P6.5a** within-stratum ρ is the primary quantity, pooled reported only as a labelled contrast · **P6.5b** IoU computed at the pre-registered top-q, no post-hoc q selection |
| **P6.6** | P6-D selective prediction | `reports/phase6_selective.json` | **P6.6a** risk at coverage 1.0 equals 1 − accuracy from the frozen predictions, to < 1e-9 · **P6.6b** external panel row order matches `data/phase5_cache_index.csv` |
| **P6.7** | Figures F38–F45 | `figures_phase6/P6_F38..F45_*.png` | every plotted value traces to a JSON field; nothing typed into the figure script |
| **P6.8** | Build the report | `Phase6_Report.docx` / `.pdf` | ToC/LoF/LoT populated; every verdict sentence selected from a pre-registered verdict field |
| **P6.9** | Update the blueprint and commit | `THESIS_RESEARCH_BLUEPRINT.md` v3.6 | Phase 6 row moved to complete with its four verdicts; Phase 7 pre-conditions noted |

---

## 5. Design decisions this phase has to close, and why

1. **Why annotator *a* is scored against the other three, not all four.** Scoring an annotator
   against a reference set that includes themselves guarantees an inflated result — one of the
   four terms is an identity. Excluding *a* from the reference costs a small amount of
   precision and buys a comparison that is not rigged. The model is then scored against the
   *same three*, so the two sides differ only in who produced the prediction.
2. **Why the human benchmark gets an interval.** Phase 0's 89.8% / 93.1% are point estimates
   over 12,800 disagreement events with no uncertainty attached. X3 was caused precisely by
   comparing an interval to a point. Both sides get patient-clustered intervals here, or the
   comparison is not a comparison.
3. **CAM layer and target class, fixed a priori.** Final ConvNeXt stage output
   (`features[-1]`), target = the model's own predicted class (not the reference label), so the
   map explains what the model *did*, not what it should have done. Top-q for IoU fixed at
   q = 20%. None of the three is tuned.
4. **Grad-CAM only.** No sweep over attribution methods. A negative P6-C result is therefore
   evidence about Grad-CAM specifically, and the report must say so — the same discipline
   applied to λ in P4-DEV-3.
5. **Max-softmax as the selective score.** The simplest and most widely reported confidence
   score, chosen so that P6-D measures the deployed model rather than a bolt-on detector.
   Entropy and margin are computed and tabulated as declared secondaries.

---

## 6. Standing rules carried into every Phase 6 script

- No retraining. No threshold tuning. No checkpoint reselection.
- Every interval patient-clustered, ≥1,000 resamples, seed 20260726, via
  `phase3b_common.patient_bootstrap` — except on the external panel, where Phase 5's
  image-level declaration (P5-DEV-3) applies unchanged and must be restated wherever an
  external interval is printed.
- Every phase-boundary reproduction gate runs and is recorded in the JSON it gates.
- No number typed into a report or a figure script.
- Every verdict selected from a frozen rule, never authored.
