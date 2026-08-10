# Phase 5 — Content List and Implementation Checklist

**Derived from** `THESIS_RESEARCH_BLUEPRINT.md` v3.4 §4 PHASE 5, §3 (RQ3 external half),
§6 (metrics), §7 (compute), §10 (limitations), §15 (reporting standards), plus the
Phase 4 carry-forward decisions in `Phase4_Report.docx` §4.7 / §5.2 and the outstanding
items in `reports/phase4_amendment.json`.

Nothing below is invented. Each item traces to a blueprint clause or to a Phase 4
carry-forward decision; the trace is given in the right-hand column.

---

## 0. The finding that shapes this phase, stated before anything else

The blueprint says HyperKvasir and GastroVision "share coarse upper-GI categories with
the SSS set — pylorus, retroflex stomach view, Z-line", and instructs us to build a
mapping table and state its coarseness as a limitation. Checked against the actual
GastroHUN taxonomy in `reports/gastrohun_structure.json`, the coarseness is more severe
than "coarse", and it is structural rather than a matter of degree:

**GastroHUN's label space is wall × station.** Four walls (Anterior, Greater curvature,
Lesser curvature, Posterior) × six stations (Antrum, Distal gastric body, Upper-middle
gastric body, Retroflexion–cardia/fundus, Retroflexion–lesser curvature exposed, Final
aligned view), plus OTHERCLASS = 23 classes. Every one of the 22 anatomical classes is a
**stomach** station.

**Neither external corpus carries the wall dimension at all**, and neither has a class
for four of the six stations:

*Verified against the extracted corpora, not against the papers. GastroVision counts are
realised (`reports/phase5_provenance.json`, 8,000 images / 27 classes, gate P5.1c passed
with zero hash overlap against GastroHUN). HyperKvasir counts are filled in when P5.1
re-runs on its archive.*

| External label | Present in | n (GastroVision) | Maps to GastroHUN as |
|---|---|---|---|
| retroflex-stomach | **HyperKvasir only** | — (absent) | the retroflexion station group {A4, A5, G4, L4, L5, P4, P5} — **station group only, wall unrecoverable** |
| Retroflex rectum | GastroVision | 68 | lower GI — **not** a stomach retroflexion; out of protocol → OTHERCLASS |
| Pylorus | HyperKvasir, GastroVision | 394 | **no counterpart.** The pylorus is distal to the antrum and is not an SSS station. Nearest is station 1 (Antrum), which is a different view |
| Normal stomach | GastroVision | 970 | any forward-viewing gastric station — **too coarse to map to a station** |
| Gastric polyps | GastroVision | 67 | in-stomach but pathology-defined; station unrecoverable |
| Z-line / GE junction | HyperKvasir, GastroVision | 331 | outside the gastric protocol → OTHERCLASS |
| Duodenal bulb | GastroVision | 206 | outside the gastric protocol → OTHERCLASS |
| Normal esophagus | GastroVision | 141 | outside the gastric protocol → OTHERCLASS |
| Esophageal pathology (Barrett's, esophagitis, varices) | GastroVision | 212 | outside the gastric protocol → OTHERCLASS |
| All lower-GI classes (colon, cecum, ileum, rectum, …) | GastroVision | ~5,100 | outside the gastric protocol → OTHERCLASS |

**Correction against the first draft of this plan, and it changes the division of labour
between the two corpora.** GastroVision ships `Retroflex rectum` but has **no
retroflex-stomach class at all**. The retroflexion signal that P5-A depends on therefore
comes from **HyperKvasir alone**. GastroVision's contribution to Phase 5 is not P5-A but
P5-B: roughly 6,000 of its 8,000 images are definitively *not* gastric SSS stations, which
makes it by far the strongest out-of-protocol rejection corpus available — and a far
better test of that endpoint than GastroHUN itself, which contains almost no true
out-of-protocol images.

**Consequence, and it must be pre-registered rather than discovered:** the external
corpora cannot test 23-way station classification. They cannot even test 6-way station
classification. What they can support is a **collapsed-granularity transfer test** plus
an **out-of-protocol rejection test**. Phase 5 is therefore reframed, before any external
image is scored, as:

- **P5-A Retroflexion transfer.** Can the model distinguish a retroflexion view from a
  forward gastric view on external images? This is a 2-way collapse of the station axis,
  and it is the only anatomical distinction the external data encodes at all. It rests on
  HyperKvasir's `retroflex-stomach` class alone (see the correction below), with
  GastroVision's `Normal stomach` and `Pylorus` supplying the forward-view side.
- **P5-B Out-of-protocol rejection.** Given an image that is not a gastric SSS station at
  all (Z-line, duodenal bulb, esophagus, and every lower-GI class), does the model route
  it to OTHERCLASS, or does it confidently assert a station? This is a calibration and
  safety endpoint, and it is the one Phase 5 question the external data answers *better*
  than GastroHUN can, because GastroHUN contains almost no true out-of-protocol images.
- **P5-C Calibration transfer.** Does the Phase 4 calibration ordering survive the domain
  shift? This is the endpoint with the most to say, and it needs no fine-grained labels:
  ECE against the collapsed label is well defined wherever P5-A is.

The 23-way claim the thesis wants — "the model generalises to other centres" — **is not
available from these corpora at station granularity, and Phase 5 will say so.** Per the
blueprint's own instruction, a degradation is a publishable result; so is a demonstration
that the external label spaces cannot express the question.

---

## 1. What the blueprint actually asks for

| Blueprint clause | Requirement |
|---|---|
| §4 PHASE 5 | HyperKvasir + GastroVision; explicit mapping table; state coarseness as a limitation; report the performance drop |
| §4 PHASE 5, bold | "**A degradation is an expected and publishable result, not a failure.**" |
| §3 RQ3 | the external half: is the uncertainty *ranking* preserved outside the training distribution |
| §6 | primary macro F1; ECE / reliability / Brier; **all intervals patient-clustered, ≥1,000 resamples** |
| §7 | GTX 1650 4 GB — Phase 5 is inference-only, so the budget is not binding |
| §10 | L1 (per-class exploratory only), L7 (four annotators is a small panel) |
| §15 | CLAIM, TRIPOD+AI, STARD-AI, PROBAST+AI |
| Status board (line 22) | "pre-condition: carry the best-*calibrated* arm, not the most accurate (Phase 4 §4.7)" |
| Phase 4 §4.7 (2) | report the agreement-stratified curve externally if per-annotator labels exist, and state plainly that it cannot if they do not |
| `phase4_amendment.json` outstanding (1) | pre-register a target precision — Phase 4 had none on a 550-image endpoint |

Two clauses cannot be met as literally written. Each is a **declared deviation** to be
recorded in `reports/phase5_prereg.json`, not a silent substitution:

- **"Carry the best-calibrated arm" → carry all five arms (P5-DEV-1).** The status board
  reads the Phase 4 §4.7 guidance as selecting one arm. That guidance was written before
  it was noticed that RQ3's external half asks whether the *ranking* is preserved, and a
  ranking cannot be tested with one arm. Phase 5 is inference-only — 5 arms × 3 seeds is
  15 forward passes over a few thousand images, minutes of GPU time — so the constraint
  that motivated selecting a single arm does not exist here.
  There is a second reason. "Best calibrated" resolves to C3 on the pooled contested
  stratum (ECE 19.41 vs C2's 33.08), but C3 buys that by suppressing confidence globally
  and is **6.45 points under-confident on unanimous images**, where C2 (+4.38) and C4
  (+3.92) are near-exact. Carrying C3 alone would carry forward the arm whose calibration
  is an artefact of global under-confidence. Carrying all five makes that visible instead
  of hiding it.
- **Per-annotator external labels → unavailable (P5-DEV-2).** Neither corpus ships
  per-annotator votes, so no agreement-stratified curve, no vote entropy, and therefore
  **no external ρ(predictive entropy, vote entropy)**. Phase 4 §4.7 (2) requires this be
  stated plainly rather than substituted. RQ3's external half is consequently tested as
  *ranking preservation across arms and across strata-free uncertainty levels*, not as a
  reproduction of the within-stratum correlation.

---

## 2. Phase 5 content list (report table of contents)

```
PHASE 5 REPORT
External Validation and the Limits of the Available Label Spaces (RQ3)

Front matter
  Title page (with the pre-registered verdicts stated on it)
  Abstract — Background / Objective / Methods / Results / Conclusion
  Table of Contents · List of Figures · List of Tables · Abbreviations

1. Introduction
  1.1  What Phase 4 established, and what external data can and cannot test
  1.2  Why the label space, not the model, is the binding constraint here
  1.3  Research questions and pre-registered hypotheses (P5-A, P5-B, P5-C)
  1.4  Chapter roadmap

2. Methods
  2.1  The external corpora
     2.1.1  HyperKvasir: provenance, licence, class inventory, what was taken
     2.1.2  GastroVision: provenance, licence, class inventory, what was taken
     2.1.3  Patient//case identifiers, and what clustering is possible externally
  2.2  The mapping table
     2.2.1  Construction rules, and the three classes of mapping decision
     2.2.2  What the mapping destroys: the wall axis and four of six stations
     2.2.3  The collapsed label space actually evaluated
  2.3  What is held fixed (preprocessing, normalisation, the five arms, the seeds)
     2.3.1  Domain shift that is NOT the model's fault: resolution, scope, vendor
  2.4  Evaluation
     2.4.1  Endpoints for P5-A, P5-B, P5-C, and the pre-registered precision target
  (gate table: P5.1a-d, P5.2a-c, P5.3a-b, P5.5a-c, P5.6)

3. Results
  3.1  Corpus inventory and the realised mapping
  3.2  P5-A: retroflexion transfer, per arm, with the internal-to-external drop
  3.3  P5-B: out-of-protocol rejection — OTHERCLASS routing and confidence on
       images that are not gastric stations at all
  3.4  P5-C: calibration transfer — is the Phase 4 ECE ordering preserved?
  3.5  Uncertainty ranking preservation (RQ3 external half, as redefined by P5-DEV-2)
  3.6  Sensitivity
     3.6.1  Per-seed stability
     3.6.2  Corpus-by-corpus breakout (HyperKvasir vs GastroVision separately)
     3.6.3  Mapping sensitivity: the ambiguous decisions re-run both ways

4. Discussion
  4.1  What the degradation means, and what it does not
  4.2  The label-space finding as a result in its own right
  4.3  Why out-of-protocol rejection is the deployment-relevant endpoint
  4.4  Relation to the Phase 4 calibration finding
  4.5  Limitations specific to this phase
  4.6  Implications for Phases 6-7

5. Conclusion
  5.1  Answers to P5-A, P5-B, P5-C
  5.2  Carry-forward decisions

Appendices
  A. The full mapping table, every external class, with the decision and its rationale
  B. Per-corpus, per-arm, per-endpoint metric tables
  C. Pre-registration record, with the declared deviations
  D. Script and artefact manifest (reproducibility index)
  E. Analyses NOT executed, and what each would cost
References
```

### Figures

| ID | Content | Source artefact |
|---|---|---|
| P5_F33 | Label-space Venn / Sankey: GastroHUN 23 classes vs the two external corpora | `phase5_mapping.json` |
| P5_F34 | Corpus inventory: class counts retained and discarded, per corpus | `phase5_cohort.json` |
| P5_F35 | P5-A retroflexion transfer by arm, internal vs external, with the drop | `phase5_transfer.json` |
| P5_F36 | P5-B out-of-protocol: OTHERCLASS rate and confidence distribution | `phase5_rejection.json` |
| P5_F37 | P5-C reliability curves, internal vs external, per arm | `phase5_calibration.json` |
| P5_F38 | ECE ordering preservation: Phase 4 rank vs Phase 5 rank | `phase5_calibration.json` |
| P5_F39 | Uncertainty ranking preservation across arms | `phase5_uncertainty.json` |
| P5_F40 | Mapping sensitivity: verdicts under each ambiguous decision | `phase5_sensitivity.json` |

---

## 3. Implementation checklist (execution order, each gated on the previous)

| # | Task | Output | Validation criterion | Status |
|---|---|---|---|---|
| P5.0 | **Freeze the carry-forward decision** from Phase 4 artefacts alone, before any external image is on disk | `reports/phase5_carry_forward.json` | decision derived from `phase4_calibration.json` + `phase4_stratified_metrics.json`; script refuses to overwrite | ⬜ |
| P5.1 | Acquire HyperKvasir + GastroVision; record provenance, licence, checksum | `data/raw/`, `reports/phase5_provenance.json` | **P5.1a** SHA-256 of every archive recorded · **P5.1b** licence and citation captured per corpus · **P5.1c** no image overlaps the GastroHUN inventory by hash · **P5.1d** counts match the published papers | ⬜ **BLOCKED — needs the download** |
| P5.2 | Build the mapping table | `reports/phase5_mapping.json` | **P5.2a** every external class assigned exactly one decision from {map-to-station-group, map-to-OTHERCLASS, discard-out-of-scope} · **P5.2b** every decision carries a written rationale · **P5.2c** the ambiguous decisions are flagged for the P5.6 sensitivity re-run | ⬜ |
| P5.3 | Build the external cohort and cache at 224px through the **Phase 2 path unchanged** | `data/phase5_cache_224.npy`, `reports/phase5_cohort.json` | **P5.3a** same Lanczos resize, same Phase 2 TRAINING normalisation statistics — recomputing them would silently adapt the model to the new domain · **P5.3b** cache index reproducible from the manifest | ⬜ |
| P5.4 | **Freeze the pre-registration** | `reports/phase5_prereg.json` | script refuses to overwrite; endpoints, verdict rules and the **precision target** fixed before any external inference | ⬜ |
| P5.5 | Inference: 5 arms × 3 seeds over the external cache | `reports/phase5_probs_*.npz`, `phase5_infer_gate.json` | **P5.5a** row order matches the cache index · **P5.5b** saved argmax equals saved prediction · **P5.5c** re-scoring the GastroHUN test split through this code path reproduces the Phase 4 predictions bit-identically | ⬜ |
| P5.6 | P5-A transfer evaluation | `reports/phase5_transfer.json` | intervals are case-clustered where a case id exists, image-level otherwise **and declared as such** | ⬜ |
| P5.7 | P5-B out-of-protocol rejection | `reports/phase5_rejection.json` | OTHERCLASS routing rate + confidence on known out-of-protocol images | ⬜ |
| P5.8 | P5-C calibration transfer | `reports/phase5_calibration.json` | ECE/MCE/Brier definitions inherited unchanged from Phase 3B/4 | ⬜ |
| P5.9 | Uncertainty ranking preservation | `reports/phase5_uncertainty.json` | reports plainly that external vote entropy does not exist (P5-DEV-2) | ⬜ |
| P5.10 | Mapping sensitivity | `reports/phase5_sensitivity.json` | every ambiguous mapping decision re-run both ways; verdict stability reported | ⬜ |
| P5.11 | Figures | `figures_phase5/P5_F33…F40_*.png` | every plotted value traces to a JSON field; no hand-entered numbers | ⬜ |
| P5.12 | Build the report | `Phase5_Report.docx` / `.pdf` | ToC/LoF/LoT populated; every verdict sentence selected from a pre-registered verdict field | ⬜ |
| P5.13 | Update the blueprint and commit | `THESIS_RESEARCH_BLUEPRINT.md` v3.5 | Phase 5 row moved to ✅ with its verdicts; Phase 6 pre-conditions noted | ⬜ |

### Phase 5B — self-training arm (runs only after P5.13 is committed)

Approved as a **separate, later comparison against the frozen Phase 5 numbers**, never
as a replacement for them. The ordering is not a preference; it is what keeps the
external validation valid. Once the model has been adapted to the external images, no
un-adapted transfer number can be recovered from it, and any generalisation claim made
from adapted predictions is circular — the model would be scored against labels it
helped produce. P5.14 is therefore gated on the Phase 5 artefacts already being frozen
and committed.

| # | Task | Output | Validation criterion | Status |
|---|---|---|---|---|
| P5.14 | **Freeze the 5B pre-registration** | `reports/phase5b_prereg.json` | refuses to overwrite; confidence threshold, pseudo-label construction, number of rounds and stopping rule all fixed **before** any pseudo-label is generated; the Phase 5 numbers are named as the frozen comparator | ⬜ |
| P5.15 | Generate pseudo-labels on the external images from the frozen C2 arm | `reports/phase5b_pseudolabels.json` | **P5.15a** pseudo-labels derive from the committed Phase 5 checkpoints, hash-verified · **P5.15b** the confidence threshold is the pre-registered one, not tuned · **P5.15c** the external images used for adaptation are disjoint from the held-out external evaluation split, and the split is drawn **before** pseudo-labelling | ⬜ |
| P5.16 | Self-training rounds | `checkpoints/phase5b_*.pt`, `reports/phase5b_run_*.json` | every round writes its realised stop reason; **no early stopping on the external evaluation split** | ⬜ |
| P5.17 | Evaluate the adapted arm against the frozen Phase 5 baseline | `reports/phase5b_eval.json` | paired, ≥1,000 resamples, on the held-out external split only; reports confirmation-bias diagnostics (pseudo-label accuracy vs final accuracy, per class) | ⬜ |
| P5.18 | Report 5B as an appendix to the Phase 5 report, or a short standalone | `Phase5B_Report.docx` / `.pdf` | states explicitly that 5B measures transfer-**after**-adaptation and cannot be quoted as a generalisation result | ⬜ |

Three risks to be pre-registered in P5.14 rather than discovered in P5.17:

- **Confirmation bias.** Self-training reinforces whatever the model already believes.
  On a label space this collapsed (§0), the model's confident external predictions are
  concentrated on exactly the distinctions that survived the mapping, so the pseudo-label
  distribution will be narrow. P5.17 must report pseudo-label accuracy per class, not
  only final accuracy.
- **The evaluation split must be carved out first.** If adaptation and evaluation share
  external images, 5B measures memorisation.
- **A gain here does not undo the Phase 5 result.** If adaptation recovers performance,
  the honest statement is "the domain gap is closable with unlabeled target data", not
  "the model generalises".

---

## 4. Design decisions this phase has to make, and why

1. **Which arms transfer?** All five (P5-DEV-1). Inference-only cost makes single-arm
   selection pointless, and ranking preservation is untestable with one arm.

2. **At what granularity?** The collapsed granularity the external labels support, fixed
   in §0 above and frozen in the mapping table before any scoring. Reporting a 23-way
   external macro F1 would be reporting a number whose denominator is meaningless.

3. **What is the clustering unit for intervals?** GastroHUN intervals are
   patient-clustered because Phase 0 measured per-patient Fleiss κ at 0.7459 ± 0.1448.
   HyperKvasir ships no patient identifier; GastroVision's is partial. Where no case id
   exists the interval is image-level and **must be labelled as such**, because an
   image-level interval on endoscopic frames is optimistic. This is a declared weakness,
   not a silent substitution.

4. **What precision counts as adequate?** Phase 4's outstanding item. Phase 5
   pre-registers a target half-width on the P5-A endpoint and reports whether the
   realised precision met it — so that a null is interpretable as either "no effect" or
   "underpowered", which Phase 4 could not distinguish.

5. **Is a drop a failure?** No, per the blueprint. The pre-registration states the
   expected direction and magnitude of the drop **before** it is measured, so that the
   observed drop can be compared against a stated expectation rather than rationalised
   afterwards.

---

## 5. Standing rules carried into every Phase 5 script

- No number is typed by hand; the report interpolates from JSON/CSV artefacts.
- Every interval is **≥1,000 resamples** (blueprint §6; the Phase 4 shortfall corrected in
  `phase4_amendment.json` P4-AMD-1 must not recur), clustered by case where a case id
  exists and declared image-level where none does.
- Preprocessing and normalisation statistics are the Phase 2 training-set ones,
  **unchanged**. Recomputing them on the external corpora would adapt the model to the
  target domain and destroy the meaning of the transfer test.
- No fine-tuning, no adaptation, no threshold tuning on external data. Phase 5 measures
  transfer, not transfer-after-adaptation.
- Any threshold is calibrated against a control, per the Phase 0 methodological lesson.
- A negative or unresolved result is reported as the finding, not smoothed over.
