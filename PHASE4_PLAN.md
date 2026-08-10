# Phase 4 — Content List and Implementation Checklist

**Derived from** `THESIS_RESEARCH_BLUEPRINT.md` v3.3 §4 PHASE 4, §3 (RQ2/RQ3/RQ4), §6
(metrics), §7 (compute), §8 (folder structure), §10 (limitations), §15 (reporting
standards), plus the eight carry-forward decisions recorded in `Phase3_Report.docx` §5.2.

Nothing below is invented. Each item traces to a blueprint clause or to a Phase 3
carry-forward decision; the trace is given in the right-hand column.

---

## 1. What the blueprint actually asks for

| Blueprint clause | Requirement |
|---|---|
| §4 PHASE 4 table | Five configurations C0–C4 with the stated target constructions |
| §4 PHASE 4, bold | "**C3 is not optional.** Without it, any C2 benefit is confounded with ordinary regularisation." |
| §4 PHASE 4, RQ3 ¶ | MC dropout as the cheap route; 5-member deep ensemble *if the budget allows*; ECE and reliability diagrams; correlate predictive entropy with per-image annotator vote entropy |
| §4 PHASE 4, last line | Sensitivity analysis: leave-one-annotator-out, given FG2's outlier behaviour |
| §3 | RQ2 endpoint = macro F1 by stratum + ECE; RQ3 = Spearman ρ(predictive, vote entropy); RQ4 = macro F1 + adjacent-wall error rate |
| §6 | Primary macro F1; calibration via ECE, reliability, Brier; **all intervals patient-clustered, ≥1,000 resamples**; never resample images |
| §7 | GTX 1650 4 GB; sequential ensembles; ~1 h/run |
| §10 | L1 (per-class exploratory only), L7 (four annotators is a small panel — soft targets are an ordinal ambiguity signal, not a calibrated probability) |
| §15 | CLAIM, TRIPOD+AI, STARD-AI, PROBAST+AI |
| Phase 3 §5.2 (1) | Use the full agreement-tier structure when constructing C1–C4 targets |
| Phase 3 §5.2 (2) | Retain C3 — label smoothing is itself a calibration intervention |
| Phase 3 §5.2 (3) | **Pre-register calibration as a primary endpoint, not a secondary one** |
| Phase 3 §5.2 (4) | **Report the WITHIN-tier entropy correlation as RQ3's primary quantity** |
| Phase 3 §5.2 (5) | Pre-register the ceiling-normalised metric alongside the raw one |
| Phase 3 §5.2 (6) | Treat the station-geometry gap as an untested hypothesis, not a lead |

Two clauses could not be met as literally written, and each is a *declared deviation*
in `reports/phase4_prereg.json` rather than a silent substitution:

- **MC dropout → MC stochastic depth (P4-DEV-1).** torchvision's ConvNeXt-Tiny contains
  0 `nn.Dropout` modules; verified at run time and recorded in
  `reports/phase4_infer_gate.json`. Its only stochastic component is `StochasticDepth`
  (18 modules, p up to 0.1), and it has no BatchNorm, so returning exactly those modules
  to training mode samples the mechanism the network was trained with.
- **5-member ensemble → 3 members (P4-DEV-2).** The blueprint made this explicitly
  conditional on budget. 4 configurations × 3 seeds is already 12 runs.

---

## 2. Phase 4 content list (report table of contents)

```
PHASE 4 REPORT
Soft-Label and Uncertainty Training (RQ2, RQ3, RQ4)

Front matter
  Title page (with the pre-registered verdicts stated on it)
  Abstract — Background / Objective / Methods / Results / Conclusion
  Table of Contents · List of Figures · List of Tables · Abbreviations

1. Introduction
  1.1  What Phases 2 and 3 established, and what they leave open
  1.2  Why the target, and not the architecture
  1.3  Research questions and pre-registered hypotheses (RQ2, RQ3, RQ4)
  1.4  Chapter roadmap

2. Methods
  2.1  The configuration matrix C0–C4
     2.1.1  The extended cohort E, and why it is held constant
     2.1.2  Deriving epsilon: the control has to be matched, not guessed
     2.1.3  The anatomical distance matrix and the C4 penalty
  2.2  What is held fixed (backbone, schedule, augmentation, normalisation, loss)
     2.2.1  Compute budget and the epoch cap
  2.3  Evaluation
     2.3.1  Calibration and uncertainty estimators
  (gate table: P4.1a–e, P4.2, P4.3a–c, P4.6a–c, P4.7)

3. Results
  3.1  Training behaviour of the five configurations
  3.2  RQ2, accuracy: performance by configuration and stratum
     3.2.1  The pre-registered contrasts (forest plot + table + per-stratum breakout)
  3.3  RQ2, calibration: ECE / MCE / Brier / reliability / overconfidence
  3.4  RQ3: within-stratum vs pooled entropy correlation; MC decomposition; ensembles
  3.5  RQ4: anatomical error distance; error geometry vs the Phase 0 human benchmark
  3.6  Sensitivity
     3.6.1  Per-seed stability
     3.6.2  Leave-one-annotator-out, FG2 included

4. Discussion
  4.1  RQ2: what the control bought
  4.2  RQ2 calibration, and what it says about the Phase 3 finding
  4.3  RQ3
  4.4  RQ4
  4.5  Relation to the descriptor's own FG-agreement result (blueprint §2.7)
  4.6  Limitations specific to this phase
  4.7  Implications for Phases 5–7

5. Conclusion
  5.1  Answers to RQ2, RQ3, RQ4
  5.2  Carry-forward decisions

Appendices
  A. Per-configuration, per-stratum metric tables (all five strata)
  B. Training histories (every run, with realised stop reason)
  C. Pre-registration record, with the declared deviations
  D. Script and artefact manifest (reproducibility index)
  E. Analyses NOT executed, and what each would cost
References
```

### Figures

| ID | Content | Source artefact |
|---|---|---|
| P4_F25 | Design schematic: what each configuration changes | `phase4_cohort.json`, `phase4_prereg.json` |
| P4_F26 | Stratified curves per configuration, raw + ceiling-normalised | `phase4_stratified_metrics.json` |
| P4_F27 | Forest plot of every pre-registered contrast × stratum | `phase4_stratified_metrics.json` |
| P4_F28 | ECE by configuration × stratum; reliability curves | `phase4_calibration.json` |
| P4_F29 | Confidence vs expected accuracy — the overconfidence gap | `phase4_calibration.json` |
| P4_F30 | RQ3: within-stratum vs pooled ρ; MC uncertainty decomposition | `phase4_uncertainty.json` |
| P4_F31 | RQ4: anatomical error distance; error geometry vs human | `phase4_structure_eval.json` |
| P4_F32 | Per-seed spread; LOAO verdict stability | `phase4_stratified_metrics.json`, `phase4_loao.json` |

---

## 3. Implementation checklist (execution order, each gated on the previous)

| # | Task | Output | Validation criterion | Status |
|---|---|---|---|---|
| P4.1 | Build extended cohort E with the per-image vote matrix | `data/phase4_train_manifest.csv`, `reports/phase4_cohort.json` | **P4.1a** 5,228 / 1,103 and tier split 3,722+1,506 / 793+310 · **P4.1b** 23 classes, no vote outside the fixed class index · **P4.1c** 0 patient overlap incl. against the Phase 3 test split · **P4.1d** every filename in the Phase 0 SHA-256 inventory and on disk · **P4.1e** the 4/4 rows reproduce the Phase 2 cohort exactly | ✅ PASS |
| P4.2 | Cache the cohort at 224×224 through the Phase 2 path | `data/phase4_cache_224.npy`, `reports/phase4_cache_gate.json` | **P4.2** all 4,515 images shared with the Phase 2 cache decode **bit-identically** (exhaustive, not sampled) | ✅ PASS |
| P4.3 | Build the anatomical distance matrix for C4 | `reports/phase4_distance_matrix.json`, `data/phase4_distance_matrix.npy` | **P4.3a** symmetric, zero diagonal, range [0,1] · **P4.3b** 240 adjacent / 120 opposite wall pairs match Phase 0 · **P4.3c** 138 neighbouring-station pairs match Phase 0 | ✅ PASS |
| P4.4 | Measure real epoch cost on the extended cohort (C4 arm, the most expensive) | `reports/phase4_probe.json` | measured, not projected from Phase 2 | ✅ PASS |
| P4.5 | **Freeze the pre-registration** | `reports/phase4_prereg.json` | script refuses to overwrite an existing file; epsilon and lambda **derived**, not chosen; verdict rules fixed for RQ2/RQ3/RQ4 | ✅ PASS |
| P4.6 | Train C1–C4 × seeds 1–3 (12 runs, seed-major order) | `checkpoints/phase4_*.pt`, `reports/phase4_run_*.json` | every run writes a manifest with its realised stop reason | ⏳ running |
| P4.7 | Inference on the full test split + MC stochastic-depth sampling | `reports/phase4_predictions_*.csv`, `phase4_probs_*.npz`, `phase4_mc_*.npz`, `phase4_infer_gate.json` | **P4.6a** row order matches the Phase 3 cache index · **P4.6b** saved argmax equals saved prediction · **P4.6c** architecture stochastic inventory verified · C0's deterministic pass reproduces the Phase 3 predictions exactly | ⬜ |
| P4.8 | Agreement-stratified evaluation and the paired contrasts (RQ2 accuracy) | `reports/phase4_stratified_metrics.json` | **P4.7** the C0 arm reproduces `phase3_stratified_metrics.json` to <1e-9 | ⬜ |
| P4.9 | Calibration by configuration and stratum (RQ2 calibration) | `reports/phase4_calibration.json` | C0 reproduces `phase3b_calibration.json` ECE per stratum | ⬜ |
| P4.10 | Uncertainty and the entropy correlation (RQ3) | `reports/phase4_uncertainty.json` | within-stratum ρ reported as primary; S-unanimous reported as null, never 0; pooled value reproduces Phase 3's 0.320 for C0 | ⬜ |
| P4.11 | Anatomy-aware loss analysis (RQ4) | `reports/phase4_structure_eval.json` | C0's wall-adjacent / station-neighbouring shares reproduce `phase3_confusion_structure.json` | ⬜ |
| P4.12 | Leave-one-annotator-out sensitivity | `reports/phase4_loao.json` | strata held fixed at the 4-annotator definition; RQ2 verdict recomputed under each drop | ⬜ |
| P4.13 | Figures | `figures_phase4/P4_F25…F32_*.png` | every plotted value traces to a JSON field; no hand-entered numbers | ⬜ |
| P4.14 | Build the report | `Phase4_Report.docx` / `.pdf` | ToC/LoF/LoT populated; every verdict sentence selected from a pre-registered verdict field, not pre-written | ⬜ |
| P4.15 | Update the blueprint and commit | `THESIS_RESEARCH_BLUEPRINT.md` v3.4 | Phase 4 row moved to ✅ with its verdicts; Phase 5 pre-conditions noted | ⬜ |

*(Status column is updated in place as the pipeline runs; the authoritative record of
each gate is the JSON artefact it writes, not this table.)*

---

## 4. Design decisions this phase had to make, and why

The blueprint fixes the five configurations but not everything they need. Four gaps had
to be closed, and each was closed **before** the pre-registration was frozen:

1. **Which cohort do C1–C4 train on?** A hard label does not exist on the 2-2 and
   1-1-1-1 tiers, so C3 cannot be scored there. Cohort E (majority-or-better) is
   therefore held constant across C1–C4, making those four arms a pure
   target-construction contrast, and C0→C1 a separate cohort contrast. Cost: the 1,150
   most ambiguous Train/Validation images never enter training — declared in Appendix E.

2. **What epsilon for C3?** Choosing a conventional 0.1 would make the control arbitrary.
   Epsilon is *derived* by matching the expected probability mass C2 displaces from the
   modal label (0.072016 → epsilon = 0.075290). Mass rather than entropy, because the
   gradient of the soft-target cross-entropy is (q − t): the displaced mass *is* the
   perturbation. Entropy matching would have given 0.021228, a materially weaker control;
   both are recorded.

3. **What lambda for C4?** Fixed a priori at unit weight, no sweep (P4-DEV-3). A sweep
   costs 9 runs. Consequence: RQ4 is tested at one point in lambda-space, and a null is
   evidence about unit weight, not about anatomy-aware losses generally.

4. **On what scale are configuration contrasts reported?** Phase 3 needed ceiling
   normalisation because it compared *strata* with different attainable maxima. Phase 4
   compares *configurations within a stratum*, where the ceiling is one shared positive
   constant that divides out of the difference. Contrasts are therefore reported raw,
   with ceiling-normalised levels tabulated alongside — a saving in computation, not in
   rigour.

---

## 5. Standing rules carried into every Phase 4 script

- No number is typed by hand; the report interpolates from JSON/CSV artefacts.
- Every interval is a **patient-clustered** bootstrap. Images are never resampled
  (Phase 0 measured per-patient Fleiss κ at 0.7459 ± 0.1448).
- Every configuration-vs-configuration difference uses a **paired** bootstrap: one
  patient resample, both arms scored on those rows, then differenced.
- Any threshold is calibrated against a control, per the Phase 0 methodological lesson.
- A negative or unresolved result is reported as the finding, not smoothed over.
