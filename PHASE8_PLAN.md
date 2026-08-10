# Phase 8 — Q1 Readiness: Content List and Implementation Checklist

**Derived from** `THESIS_RESEARCH_BLUEPRINT.md` v3.6, `PHASE7_PLAN.md`, the built `Thesis.docx`
(10 chapters, 31 figures, 23 tables), and a reviewer-calibrated audit of that document against
the expectations of a Q1 medical-imaging or medical-informatics journal.

Phase 7 produced a thesis. Phase 8 produces a *submittable* one. These are different objects and
the gap between them is eight specific, closable defects — not a general call for "more work".

---

## 0. What Phase 8 is, and what it is not

**It is not** new modelling in search of a positive result. The thesis's central claim survives
review; what does not survive is the evidence *around* it — an absent bibliography, a headline
statistic reported without an interval, a claim of irreparability that never tested the cheapest
standard repair, and a null reported as "not resolved" without a margin that would let a reader
distinguish equivalence from insufficient power.

**It is** the conversion of six defensible-in-a-viva weaknesses into publishable ones, plus the
one defect (W1) that is disqualifying in any venue and costs marks at the defence itself.

### The audit that produced this plan

| # | Blocker | Severity | Work package |
|---|---|---|---|
| 1 | **No references and no in-text citations anywhere in `Thesis.docx`.** `build_thesis_docx.py` emits no bibliography; Ch. 3 reviews 82 studies and cites none of them. The novelty claim in §1.4 is therefore unassessable by a reader. | **Fatal** | W1 |
| 2 | ECE at n = 127 and n = 81 over 23 classes is a badly biased estimator, reported with no interval, no debiasing and no bin-count sensitivity. The thesis's own "durable finding" rests on it. | High | W2 |
| 3 | No post-hoc calibration arm. "No target construction repairs it" never tested temperature scaling, which is free and standard. Declared as unexecuted in the Phase 4 appendix; absent from the thesis entirely, including its costed future-work table. | High | W3 |
| 4 | The target-construction family is two constructions wide (vote proportions vs. matched smoothing). No aggregation model, no annotator-specific heads. The claim reaches further than the family supports. | High | W4 |
| 5 | 8 of 12 Phase 4 runs stopped at the compute-imposed epoch cap; absolute scores are declared lower bounds. | Medium | W5 |
| 6 | The nulls have no equivalence margin. RQ2's CI is [-0.88, 3.68] — 4.5 points wide. Without a derived margin a reviewer reads "underpowered", not "equivalent", regardless of the pre-registration. | High | W6 |
| 7 | §9.4 recommends a deployment (abstaining assistant) with no risk-controlled operating point. AURC ranks arms; it does not give a threshold with a guarantee. | Medium | W7 |
| 8 | **Internal inconsistency.** Appendix C declares *all* Phase 5 external endpoints exploratory, yet the Abstract, the central claim and §9.4 all rest on external AURC (0.1906 vs 0.3235). A confirmatory headline cannot stand on a self-declared exploratory endpoint. | High | W8 |

---

## 1. The integrity constraint that shapes everything below

Every analysis in Phase 8 is being specified **after** its subject matter has been seen. That is a
materially weaker epistemic position than Phases 2–6 occupied, and the project's own standards do
not permit it to be papered over.

Three rules follow, and they are binding:

1. **The confirmatory family is closed.** It was fixed in `reports/phase7_multiplicity.json`: one
   primary endpoint per RQ, Holm at family-wise 0.05. Nothing produced in Phase 8 may be added to
   it. Phase 8 endpoints form a **separate, secondary, declared-post-hoc family** with its own
   correction and its own label.
2. **Pre-specified is not the same as blind, and the difference is declared.** Each Phase 8
   analysis is still frozen in a pre-registration before it runs — that constrains the analyst — but
   `reports/phase8_prereg.json` must carry the field `blind_to_related_results: false` with a
   sentence naming what was already known. A reader must be able to discount it correctly.
3. **Every threshold and margin is derived, not chosen.** This is the Phase 4 ε discipline applied
   to Phase 8. A margin selected after seeing a confidence interval is not a margin, it is a
   verdict written backwards. W6 specifies the derivation and freezes it before the interval is
   recomputed.

A new **Appendix G — Post-hoc analyses added after the thesis was drafted, and why they are not
confirmatory** carries this into the document. It is the same instinct that put X1–X4 in the
running text rather than an appendix, applied one level up.

---

## 2. Work packages

### W1 — Bibliography and positioning **(critical path; do this first)**

Two separate faults are being fixed: the document has no references, and Chapter 3 does not
position the contribution against the work that most threatens it.

**W1a — the reference list, generated not typed.**
`literature_v2/extraction_table.csv` already holds 82 rows with a rendered `apa` column. A
bibliography built from that column obeys the project's no-hand-typed-numbers rule exactly as the
tables do. Citation keys are the PMID; the build script resolves each in-text key against the
table and fails on a miss.

**W1b — the supplementary search arm.** The 82 records are PubMed/MEDLINE only (declared as L5).
The literature that actually threatens the novelty claim is not in PubMed. A targeted arm must be
run and folded into the PRISMA flow as *other methods*, with the counts updated rather than
silently grown. It must cover, at minimum:

- annotator-aggregation models — Dawid–Skene and its successors;
- learning from multiple/noisy annotators — crowd layers, annotator-specific heads, per-rater
  modelling;
- label-distribution and soft-label learning in medical imaging;
- **evaluation against ambiguous or non-existent ground truth** — plausibility/annotator-set
  based evaluation, and any prior use of an attainable-ceiling or oracle correction;
- multi-reader multi-case (MRMC) reader-study methodology, which is the clinical-imaging
  tradition this thesis's human comparator sits in;
- selective prediction and conformal prediction under distribution shift.

**W1c — §3.4, the positioning section that does not currently exist.** A table of the form
*prior work → what it established → what it did not do → what this thesis adds*, one row per
closest competitor. The §1.4 novelty claim ("to our knowledge this comparison has not previously
been reported for this task") is then either supported by named citations or **downgraded in
wording**. The narrowing phrase "for this task" is exactly the kind of carve-out a reviewer
attacks; it must be earned or dropped.

> ⚠️ **This work package can reduce the thesis's headline contribution, and it is scheduled first
> for that reason.** If prior work already reports an attainable-ceiling correction for ambiguous
> ground truth, then the contribution is the *combination* — ceiling + held-out-annotator comparator
> + oracle bound, applied to a corpus that retains per-annotator labels — not the ceiling idea
> itself, and Chapters 1, 9 and 10 must say so. Finding this out now is cheap. Finding it out from
> Reviewer 2 costs a submission cycle.

### W2 — Calibration estimator hardening

The 9.2% → 56.4% collapse is almost certainly real. It is currently reported in a form that cannot
survive a statistical referee: a point estimate from a binned plug-in estimator with known upward
bias, at sample sizes where that bias is largest, with no interval.

Compute, on the frozen Phase 4 probability files (no GPU, no retraining):

- ECE with **patient-clustered bootstrap 95% CIs**, 1,000 resamples, same seed and procedure as
  everywhere else in the project;
- a **debiased** ECE estimator alongside the plug-in value, with the bias estimate reported;
- **equal-mass (adaptive) binning** beside the equal-width binning currently used;
- **bin-count sensitivity** at {5, 10, 15, 20} — the claim must not depend on the choice;
- **classwise ECE**, since a 23-class problem hides per-class miscalibration in the top-label
  statistic;
- **Brier score with its Murphy decomposition** into reliability / resolution / uncertainty. The
  blueprint §6 promised Brier and the thesis never reports it. The decomposition is also the
  cleanest way to show *why* the collapse happens: resolution falls with the stratum while
  reliability degrades separately.

**Regression gate:** at the original equal-width binning and bin count, the C0 unanimous value must
reproduce `reports/phase3b_calibration.json` exactly. If it does not, the new code is wrong, not
the old number.

**Frozen verdict rule (before running):** the calibration collapse is CONFIRMED if the
debiased unanimous-minus-contested ECE gap has a CI excluding zero under **all four** bin counts
and **both** binning schemes. Anything less is reported as bin-dependent and the claim is softened.

### W3 — The post-hoc calibration arm **(highest scientific value in Phase 8)**

The thesis says no target construction repairs calibration and then reasons from that to "a
property of the problem" and from there to the deployment recommendation in §9.4. The inferential
chain skips the standard repair.

**Design.** Fit a single temperature per arm on a validation set that **includes contested
images** — the Phase 4 cohort E validation split, 1,103 images — and apply it to the frozen test
predictions. No retraining, no checkpoint reselection.

Three variants, in increasing optimism, all reported:

| Variant | What it is | What it bounds |
|---|---|---|
| T-single | one temperature per arm, fitted on contested-inclusive validation | what a deployment could actually do |
| T-vector | vector scaling (per-class), same fit | whether the failure is a single global scale |
| T-oracle | one temperature per arm **per stratum**, fitted on test | the ceiling of any post-hoc rescaling; not deployable, since strata are unknown at inference |

The T-single-to-T-oracle gap is itself a finding: it separates "confidence is on the wrong scale"
from "confidence carries no stratum information at all", and only the second supports the thesis's
current wording.

**Technical note that saves a GPU pass.** Temperature scaling needs logits and the project saved
probabilities. This is recoverable exactly: logits are `log p` up to a per-image additive constant,
and that constant cancels in the softmax, so `softmax(log p / T)` equals the T-scaled softmax of
the original logits. Compute in float64 and **gate on `min(p) > 0`** — if any saved probability has
underflowed to zero the recovery is invalid for that row and a re-inference pass is required for
that arm. The gate decides; do not assume.

**Frozen verdict rule, with a derived threshold (before running).** "Repair" means the post-scaling
contested-stratum ECE falls within the 95% CI of the *unanimous*-stratum ECE of the same arm —
i.e. contested images become as well calibrated as agreed ones. The reference level is derived from
the data, not chosen. Outcomes and their consequences, both written down now:

- **No repair** → the thesis's claim survives and is *strengthened*, because the standard remedy
  was tested and failed. Wording upgrades from "no target construction repairs it" to "neither
  target construction nor post-hoc rescaling repairs it".
- **Partial or full repair** → the central claim must be reworded. "A property of the problem"
  becomes "not repairable by target construction, and repairable post hoc only to degree X", and
  §9.4's recommendation changes from abstention-only to rescale-then-abstain.

The second outcome is a real possibility. It is better found here than in review, and a plan that
only works if the result goes one way is not a plan.

### W4 — Widening the target-construction family

Two constructions do not license a claim about target construction in general. Add two arms, on
cohort E, with backbone, schedule, augmentation, normalisation, selection criterion and seeds
identical to C1–C4 — the same discipline that made C2–C3 a clean contrast:

- **C5 — Dawid–Skene posterior targets.** Fit an annotator confusion-matrix model over the four
  annotators; train on the posterior label distribution. This is the standard aggregation baseline
  and its absence is the first thing an ML referee will name.
- **C6 — annotator-specific heads.** Four heads, one per annotator, sharing a trunk; marginalise
  over heads at inference. This models the annotators rather than their votes, and it is the only
  arm in the project that could exploit FG2's declared outlier behaviour instead of averaging it
  away.

6 runs (2 arms × 3 seeds). The RQ2-family statement then reaches "no target construction among
seven, including the standard aggregation baseline", which is a Q1-grade negative result rather
than a two-arm one.

**Constraint:** C5 and C6 must be trained under whichever epoch policy W5 settles, and if W5 is
dropped for budget they inherit the existing cap and the existing lower-bound caveat. Arms trained
under different caps are not comparable and must not be tabulated together.

### W5 — Removing the epoch-cap caveat

Re-run the capped Phase 4 runs with the cap raised until early stopping fires on every run.
**Gate:** every run's recorded `stop_reason` is `early_stopping`. If any run still caps, the caveat
is re-declared rather than quietly dropped.

This is the **first thing to cut if the budget runs short.** The cap applies identically across
arms, so every contrast the thesis actually relies on already holds; what the re-run buys is the
removal of a lower-bound caveat on absolute scores. Useful, not load-bearing.

### W6 — Equivalence margins, derived

Three of five RQs returned nulls. Reported as "NOT RESOLVED" with a raw interval, a reviewer cannot
tell equivalence from insufficient power — and will assume the latter.

**The margin must be derived before the test is recomputed.** Two anchors, both external to the
result being tested:

1. **Resolution anchor (primary).** 2 × the measured seed-to-seed SD of the endpoint on the same
   stratum — the smallest difference this pipeline can distinguish from its own noise. Computed
   from existing per-seed artefacts.
2. **Practical anchor (reported alongside).** The descriptor's 3.25-point between-architecture
   macro-F1 gap, already used as a benchmark in Phase 3. A difference smaller than the gap between
   architecture families is not a difference anyone would act on.

Freeze both, then run **TOST** for RQ2 and RQ4. Three possible verdicts, all of which must be
acceptable in advance:

- CI inside δ → **EQUIVALENT within a stated margin.** This is a result, and it is what makes a
  null publishable.
- CI excludes 0 → the null was wrong.
- CI wider than δ → **INCONCLUSIVE — underpowered at this sample size**, stated in exactly those
  words, with the n required for δ reported.

The third outcome is likely for at least one endpoint. Say it plainly; a thesis that can name its
own underpowered endpoints is more credible than one that cannot.

### W7 — Risk-controlled selective prediction

§9.4 recommends deploying an abstaining assistant and supplies a ranking, not an operating point.
Convert it:

- split-conformal / Learn-then-Test on a calibration partition of the external panel, producing a
  **threshold with a guaranteed selective risk** at pre-registered target levels (e.g. 5% and 10%
  error among accepted images);
- report **achieved coverage per arm at each guaranteed risk level** — that is the number a
  clinical reader wants, and no table in the thesis currently contains it;
- **declared limitation, carried in the text wherever the guarantee appears:** exchangeability is
  violated because the external splits are image-level and frames from one procedure can fall on
  both sides. The guarantee is approximate and optimistic, for the same reason and to the same
  degree as the image-level intervals already declared in §6.3.

Cost is CPU-only on existing probability files.

### W8 — Consistency repair and document rebuild

**W8a — the multiplicity inconsistency.** Two legitimate resolutions; take the second.

- *Promote* the external endpoints into a secondary confirmatory family with its own Holm
  correction. Defensible, but retrospective promotion of an endpoint the project already declared
  exploratory is precisely the move the thesis criticises elsewhere.
- **Reword instead.** The Abstract, the central claim, §9.4 and Ch. 10 mark the external
  separation as *exploratory and directionally consistent across two independent endpoints*
  (single-operating-point rejection in Ch. 6 and AURC in Ch. 7, ρ = 1.0). Two agreeing exploratory
  endpoints are worth stating; they are not worth stating as confirmed. Appendix C stands as
  written, which is the point.

**W8b — the document.** `build_thesis_docx.py` gains a References section and in-text citation
resolution; Chapters 3, 4, 5, 7, 9 and 10 absorb W1–W7; Appendix G is added; the future-work table
in §10.3 drops the items Phase 8 executed and gains what Phase 8 could not.

---

## 3. Implementation checklist

Execution order; each step gated on the previous one's validation criterion. The authoritative
record of every gate is the JSON artefact it writes, not this table.

| # | Task | Output | Validation criterion |
|---|---|---|---|
| P8.0 | **Freeze the Phase 8 pre-registration** — every verdict rule, margin derivation and threshold in W2, W3, W6, W7 fixed before any of them runs | `reports/phase8_prereg.json` | refuses to overwrite; carries `blind_to_related_results: false` with the naming sentence; every rule stated as a computable predicate, not prose |
| P8.1 | Supplementary literature arm (W1b), PRISMA counts amended | `literature_v2/prisma_counts_v3.json`, `extraction_table_v3.csv` | new records enter through the *other methods* arm with the flow diagram updated, never appended silently; each of the six required topics returns ≥1 included record or a recorded null result |
| P8.2 | Bibliography generator (W1a) | `reports/phase8_bibliography.json` | every reference rendered from the extraction table's `apa` column; zero hand-typed reference strings; build fails on any in-text key with no matching row |
| P8.3 | Positioning section §3.4 (W1c) | `src/report/content_thesis_ch3.py` | one row per closest prior work; the §1.4 novelty claim explicitly either survives with named citations or is rewritten; the decision is recorded, not implied |
| P8.4 | Calibration hardening (W2) | `reports/phase8_calibration.json` | C0 unanimous ECE reproduces `phase3b_calibration.json` at original binning; CIs are patient-clustered, 1,000 resamples, seed `20260726`; verdict returned under all four bin counts and both schemes |
| P8.5 | Logit-recovery gate for W3 | `reports/phase8_logit_gate.json` | `min(p) > 0` verified per arm per seed in float64; any failing arm is re-inferred rather than approximated |
| P8.6 | Temperature / vector / oracle scaling (W3) | `reports/phase8_posthoc_calibration.json` | temperatures fitted on cohort E validation only, never on test; T-oracle explicitly labelled non-deployable in the artefact itself; verdict selected by the P8.0 rule |
| P8.7 | Equivalence margins derived and frozen (W6) | `reports/phase8_margins.json` | both anchors computed from pre-existing artefacts; written before P8.8 runs; script refuses to run after `phase8_tost.json` exists |
| P8.8 | TOST for RQ2 and RQ4 (W6) | `reports/phase8_tost.json` | verdict is one of EQUIVALENT / NOT-NULL / INCONCLUSIVE by the frozen rule; required-n reported whenever INCONCLUSIVE |
| P8.9 | Risk-controlled selection (W7) | `reports/phase8_conformal.json` | coverage at each guaranteed risk level, per arm, internal and external; exchangeability caveat present as a field in the artefact so the text cannot omit it |
| P8.10 | Epoch-cap re-runs (W5) | `checkpoints/phase8_*`, `reports/phase8_epoch_gate.json` | every re-run records `stop_reason == early_stopping`, else the caveat is re-declared |
| P8.11 | C5 Dawid–Skene targets built (W4) | `reports/phase8_ds_posteriors.json` | model fitted on the 4-annotator matrix over cohort E only; converges; the unanimous rows reduce to one-hot within tolerance — if they do not, the fit is wrong |
| P8.12 | C5 and C6 trained, 3 seeds each (W4) | `checkpoints/phase8_C{5,6}_seed{1,2,3}.pt` | cohort, cache, normalisation, augmentation, schedule, selection criterion and epoch policy identical to the arms they are tabulated with |
| P8.13 | C5/C6 inference and evaluation | `reports/phase8_family_eval.json` | reuses `phase4_eval.py` unchanged; the C2 and C3 rows reproduce `phase4_stratified_metrics.json` to < 1e-9 as a wiring check |
| P8.14 | Secondary-family multiplicity | `reports/phase8_multiplicity.json` | Phase 8 endpoints corrected within their own family; explicitly disjoint from `phase7_multiplicity.json`; no Phase 7 verdict altered |
| P8.15 | Figures | `figures_thesis/T32`–`T3n` | continuous numbering from T31; every plotted value traces to a Phase 8 JSON field |
| P8.16 | Rebuild thesis with references, Appendix G, and W8a rewording | `Thesis.docx` / `.pdf` | References section populated and non-empty; zero uncited references; zero unresolved citation keys; Abstract and §9.4 no longer state an exploratory endpoint as confirmed |
| P8.17 | Blueprint update and tag | `THESIS_RESEARCH_BLUEPRINT.md` v4.0 | Phase 8 row complete with verdicts; repository tagged |

> The table above is the **gate list**. The atomic steps that satisfy each gate are broken out as
> micro-phases with tickable TODOs in **§10**. Work from §10; use this table to check whether a
> package is allowed to close.

---

## 4. Regeneration pipeline

```bash
# Gate everything on the pre-registration
python src/models/phase8_prereg.py            # FROZEN before anything below runs

# W1 — literature and bibliography (critical path)
python src/literature/search_v3.py            # supplementary arm, other-methods
python src/literature/eligibility_v3.py       # PRISMA counts amended
python src/report/phase8_bibliography.py      # references generated from extraction table

# W2/W3 — calibration, no GPU
python src/models/phase8_calibration.py       # debiased ECE, CIs, Brier decomposition
python src/models/phase8_logit_gate.py        # min(p) > 0 per arm
python src/models/phase8_posthoc_cal.py       # T-single, T-vector, T-oracle

# W6 — margins then test, in that order and never the reverse
python src/models/phase8_margins.py           # derived, frozen
python src/models/phase8_tost.py

# W7 — risk-controlled selection
python src/models/phase8_conformal.py

# W5/W4 — the GPU work
bash   src/models/phase8_epoch_rerun.sh       # W5, drop first if budget-bound
python src/models/phase8_ds_targets.py        # C5 targets
bash   src/models/phase8_run_all.sh           # C5, C6 x 3 seeds
python src/models/phase8_family_eval.py

# Assemble
python src/models/phase8_multiplicity.py
python src/report/figures_thesis.py           # extended, T32+
python src/report/build_thesis_docx.py        # now emits References and Appendix G
python src/report/finalise_thesis.py
python src/report/update_blueprint_phase8.py
```

---

## 5. Budget

GTX 1650, 4 GB, the same machine that produced every earlier number.

| Package | GPU | Analyst | Cut if short? |
|---|---|---|---|
| W1 bibliography + positioning | — | 4–6 days | **No — disqualifying** |
| W2 calibration hardening | — | 1–2 days | No |
| W3 post-hoc calibration | ~0–1 h | 2 days | No |
| W6 equivalence margins | — | 1–2 days | No |
| W8 consistency + rebuild | — | 3–4 days | No |
| W7 conformal selection | — | 2 days | Second to cut |
| W4 C5/C6 arms | ~9 h | 3 days | Third to cut |
| W5 epoch-cap re-runs | ~22 h | 1 day | **First to cut** |

**Minimum viable Q1 set:** W1, W2, W3, W6, W8 — roughly two to three weeks of analyst time and
about an hour of GPU. Everything expensive is optional; everything disqualifying is cheap. That
ordering is not a coincidence, it is what the audit found.

---

## 6. What this is submitted as

Do not submit the thesis as a paper. Two papers come out of it, and they have different referees.

**Paper A — methods.** Agreement-stratified evaluation with the attainable ceiling, the
held-out-annotator comparator and the modal-vote oracle. Chapters 4 and 7, the backbone
replication (§9.2a), and W2/W3/W6 as the statistical spine. This is the contribution.
Target band: *Medical Image Analysis* / *IEEE TMI* if W1 leaves the novelty claim intact;
*Computers in Biology and Medicine* / *Artificial Intelligence in Medicine* /
*Journal of Biomedical Informatics* if it does not.

**Paper B — meta-research.** The audit protocol scored against a known-unsound negative control,
the 1-of-4 fatal-defect detection rate, and the three proposed gates G9–G11. Chapter 8, standing
alone. Short, unusual, and it is the rare paper whose result is that its own instrument was
mis-specified. Target: dataset-quality, reproducibility and research-integrity venues.

---

## 7. Risk register

| Risk | Likelihood | Impact | Response |
|---|---|---|---|
| **W1 finds prior work already reporting a ceiling/oracle correction** | Medium | High | Reframe the contribution as the *combination* (ceiling + human comparator + oracle bound on a per-annotator corpus) and rewrite Ch. 1, 9, 10 accordingly. The evidence base is unaffected; only the novelty wording is. Scheduled first so the rewrite is cheap. |
| **W3 finds temperature scaling substantially repairs contested calibration** | Medium | High | The central claim is reworded, not withdrawn: target construction still fails, and §9.4 becomes rescale-then-abstain. Both outcomes are pre-written into P8.0 so neither can be spun. |
| W6 returns INCONCLUSIVE rather than EQUIVALENT | Medium-high | Medium | State it in those words with the required n. An honestly-named underpowered endpoint is survivable; a null dressed as equivalence is not. |
| C5 Dawid–Skene fails to converge on 4 annotators | Low-medium | Low | 4 raters is thin for confusion-matrix estimation. If it degenerates, report the degeneracy as a finding about the method's data appetite and keep C6. |
| The rebuild breaks the no-hand-typed-numbers invariant under time pressure | Medium | High | P8.16 fails the build on any unresolved citation key or uncited reference; the same gate discipline that has held for seven phases holds here. |
| Scope creep into a second corpus | Medium | Medium | Out of scope. No public UGI corpus with per-annotator labels has been identified; if that changes it is Phase 9, not Phase 8. |

---

## 8. What will still not be Q1 after all of this, and must be declared

Phase 8 closes what is closable. These are not closable with the data in hand, and the thesis is
stronger for naming them than for hedging:

- **Single centre, single vendor, 387 patients.** External validation exists but is degraded to a
  2-way collapse because neither external corpus carries the wall axis.
- **Four annotators** bound the human comparator; the held-out construction leaves a reference
  panel of three.
- **No age or sex anywhere in the release**, so no demographic or fairness analysis is possible —
  and this is one of the four reporting gaps Chapter 3 identifies in the literature, which the
  thesis must keep declaring rather than quietly meeting.
- **No patient-level key in either external corpus**, so external intervals stay image-level and
  the conformal guarantee of W7 stays approximate.
- **No prospective evaluation.** The deployment claim in §9.4 is an operating characteristic, not
  evidence of clinical benefit, and only a clinical study changes that.

Top-tier Q1 (*MedIA*, *TMI*, *npj Digital Medicine*) realistically requires a second corpus with
per-annotator labels. Phase 8 gets the work to the applied Q1 band on its own merits; it does not
manufacture a multi-centre study out of a single-centre one.

---

## 9. Standing rules (carried from Phase 7, extended)

- No number typed by hand — now including every reference string, which comes from the extraction
  table like every other artefact.
- Every verdict selected from a frozen pre-registration field.
- Corrections and amendments are integrated where the claim is made, not quarantined.
- **New:** every Phase 8 result carries its post-hoc status in the artefact itself, not only in the
  prose, so the label cannot be lost in a rebuild.
- **New:** no Phase 7 verdict may be altered by a Phase 8 analysis. If a Phase 8 result contradicts
  one, both are reported and the contradiction is discussed. Overwriting a frozen verdict with a
  later, unblinded analysis is the one thing this project has never done.

---

## 10. Micro-phases and TODO lists

Atomic execution units. Each micro-phase is a single sitting's work with one artefact and one
check. A micro-phase is **done** when its check passes, not when its TODOs are ticked — the TODOs
are the route, the check is the gate.

Estimates are analyst-hours unless marked GPU.

---

### P8.0 — Pre-registration freeze **(blocks everything)**

**P8.0.1 — Enumerate every rule that must be frozen** · 2 h · → `src/models/phase8_prereg.py`

- [ ] Copy the structure of `src/models/phase4_prereg.py`, including its refuse-to-overwrite guard
- [ ] Write W2's verdict predicate: collapse CONFIRMED iff debiased gap CI excludes 0 under bins ∈ {5,10,15,20} × {equal-width, equal-mass}
- [ ] Write W3's repair predicate: post-scaling contested ECE ∈ 95% CI of the same arm's unanimous ECE
- [ ] Write W6's margin *derivation formula* (not its value — the value is computed at P8.7)
- [ ] Write W7's target risk levels (5%, 10%) and the coverage reporting format
- [ ] Add `blind_to_related_results: false` plus the sentence naming what was already known when these rules were written
- [ ] Add `confirmatory_family: "phase8_secondary"` and assert it is disjoint from `reports/phase7_multiplicity.json`

**Check:** the file refuses a second write; every rule is a computable predicate over named JSON
fields, not prose. Grep the artefact for any rule containing a number that does not also appear as
a derivation. If one exists, it was chosen, not derived — fix it before proceeding.

---

### W1 — Bibliography and positioning · ~5 days · **critical path**

#### W1.1 — Citation infrastructure · 6 h · → `src/report/phase8_bibliography.py`

- [ ] Load `literature_v2/extraction_table.csv` with `dtype=str` (the Phase 1 trap: a hash column read back as int)
- [ ] Key each record by PMID; assert 82 unique keys, 0 nulls in `apa`
- [ ] Emit `reports/phase8_bibliography.json` as `{key: {apa, doi, year, first_author, theme}}`
- [ ] Write `cite(key)` and `render_bibliography(used_keys)` helpers for the content modules
- [ ] `render_bibliography` sorts by first author then year, and **raises** on any key not in the table
- [ ] Add the reverse check: any table row never cited is listed in a `uncited` field

**Check:** `render_bibliography` on a deliberately bad key raises rather than emitting a blank.

#### W1.2 — Supplementary search arm · 8 h · → `src/literature/search_v3.py`

- [ ] Fork `search_v2.py`; keep the PubMed guards (the `endoscop*` stem trap, the bare `CLAIM` trap, the `./PubmedData/ArticleIdList/ArticleId` DOI path)
- [ ] Add the six required topics as themes T8–T13: annotator aggregation · learning from multiple annotators · label-distribution learning · evaluation under ambiguous ground truth · MRMC reader studies · conformal/selective prediction under shift
- [ ] Search outside PubMed for these — they are largely CS venues, which is exactly why L5 exists
- [ ] Record every query string and its hit count in `literature_v2/search_v3_log.json`
- [ ] Deduplicate against the existing 82 by DOI **and** by normalised title

**Check:** each of T8–T13 returns either ≥1 record or an explicit recorded null. A silently empty
theme is a failed search, not an absent literature.

#### W1.3 — Screen and extract · 10 h · → `src/literature/eligibility_v3.py`

- [ ] Apply the v2 eligibility criteria unchanged; log every exclusion with its reason
- [ ] Extract, for each included record, the field that actually matters here: **does it correct for an attainable ceiling, an oracle bound, or annotator-set plausibility when scoring?**
- [ ] Flag every record answering yes as `novelty_threat: true`
- [ ] `.fillna()` before any string join (pandas 3.x keeps NaN through `.astype(str)`)
- [ ] Append to `literature_v2/extraction_table_v3.csv`, preserving all 19 original columns

**Check:** the count of `novelty_threat: true` records is written to the artefact whether it is 0
or 20. This number decides W1.6.

#### W1.4 — PRISMA amendment · 3 h · → `literature_v2/prisma_counts_v3.json`

- [ ] New records enter through the **other methods** arm, never the database arm
- [ ] Recompute identified / unique / screened / included; the v2 numbers stay visible as the prior row
- [ ] Regenerate the PRISMA figure (thesis T10) from the amended counts
- [ ] Add one sentence to Ch. 3 stating the review was extended after the first draft and why

**Check:** old and new counts both appear in the artefact. A PRISMA diagram that silently grew is
worse than one that never grew.

#### W1.5 — §3.4 positioning · 10 h · → `src/report/content_thesis_ch3.py`

- [ ] Build the table: *prior work → what it established → what it does not do → what this thesis adds*, one row per `novelty_threat` record plus the closest non-threat neighbours
- [ ] Every row cites via `cite(key)`; no free-text author names
- [ ] Write the paragraph that names the closest single piece of prior work and states the delta in one sentence
- [ ] Insert citations into Chapters 1–2 and 4–10 where a claim about "the literature" is currently unsourced — grep the thesis text for *the literature*, *commonly*, *rarely published*, *almost universally*

**Check:** zero occurrences of an unsourced claim about what the literature does. Grep is the test.

#### W1.6 — Novelty adjudication · 3 h · → `reports/phase8_novelty.json`

- [ ] If `novelty_threat` count is 0 → §1.4 stands; record the searches that failed to find a threat
- [ ] If ≥1 → rewrite §1.4 from "has not previously been reported for this task" to the **combination** claim (ceiling + held-out-annotator comparator + oracle bound on a per-annotator corpus), and propagate to the Abstract, §9.1 and §10.2
- [ ] Record the decision and its trigger in the artefact, so the wording can be traced to evidence
- [ ] Delete the phrase "for this task" wherever it survives as an unearned carve-out

**Check:** the §1.4 wording in the built document matches the branch the artefact recorded.

---

### W2 — Calibration hardening · ~3 days · no GPU

#### W2.1 — Regression harness · 3 h · → `src/models/phase8_calibration.py`

- [ ] Import `phase4_common.py`; load `reports/phase4_probs_C*_seed*.npz` and the Phase 3 stratum index
- [ ] Reimplement plug-in ECE and reproduce `reports/phase3b_calibration.json` C0 unanimous **exactly** at the original binning
- [ ] Fail loudly on mismatch — the old number is the reference, the new code is the suspect

**Check:** exact reproduction before any new estimator is written.

#### W2.2 — Estimator suite · 6 h

- [ ] Equal-mass (adaptive) binning beside equal-width
- [ ] Bin counts {5, 10, 15, 20}
- [ ] A debiased ECE estimator, with the estimated bias reported as its own field
- [ ] Classwise ECE across all 23 classes
- [ ] Sweep every arm × stratum × estimator into one long-format table

**Check:** the 8 (bins × schemes) variants of the headline gap are all present in the artefact,
including any that disagree.

#### W2.3 — Patient-clustered CIs · 4 h

- [ ] 1,000 resamples, seed `20260726`, resampling **patients** — never images (blueprint §6)
- [ ] Attach CIs to every ECE, every classwise ECE, and to the unanimous-minus-contested **gap**
- [ ] Store the bootstrap distributions for the diagnostic appendix

**Check:** no ECE appears anywhere in the artefact without an interval beside it.

#### W2.4 — Brier decomposition · 4 h

- [ ] Brier score per arm per stratum
- [ ] Murphy decomposition into reliability / resolution / uncertainty
- [ ] State which component drives the stratum collapse — this is the mechanism the thesis currently asserts from mean-confidence-vs-accuracy alone

**Check:** reliability + resolution + uncertainty reconstructs the Brier score to < 1e-9.

#### W2.5 — Verdict and figure · 3 h

- [ ] Apply the P8.0 predicate; write the verdict field
- [ ] Figure T32: the collapse with intervals, one panel per binning scheme
- [ ] If the verdict is bin-dependent, **say so in Ch. 4** and soften §4.3's "durable finding" wording

**Check:** the Ch. 4 sentence is selected by the verdict field, not written by hand.

---

### W3 — Post-hoc calibration · ~2.5 days · ≤1 GPU h

#### W3.1 — Logit recovery gate · 3 h · → `src/models/phase8_logit_gate.py`

- [ ] For every arm × seed, load probabilities in **float64** and compute `min(p)`
- [ ] Pass if `min(p) > 0`; recovery `logits = log(p)` is then exact up to the additive constant that cancels in softmax
- [ ] Any failing arm is queued for a re-inference pass, not approximated
- [ ] Verify on one arm that `softmax(log(p)/1.0)` reproduces `p` to < 1e-9

**Check:** the artefact records pass/fail per arm. Do not assume; the gate decides.

#### W3.2 — Fit harness · 4 h · → `src/models/phase8_posthoc_cal.py`

- [ ] Fit temperature by NLL on the **cohort E validation split** (1,103 images, contested-inclusive) — never on test
- [ ] Assert the fitted split's image IDs are disjoint from the 1,353-image test split
- [ ] Record the fitted T per arm; a T far from 1 is itself reportable

**Check:** a hard assertion on test-set leakage, in code, not in a comment.

#### W3.3 — The three variants · 4 h

- [ ] T-single (one T per arm) — the deployable number
- [ ] T-vector (per-class scaling) — tests whether the failure is a single global scale
- [ ] T-oracle (one T per arm **per stratum**, fitted on test) — the ceiling of any rescaling; tag `deployable: false` in the artefact itself
- [ ] Recompute the full W2 estimator suite post-scaling for each variant

**Check:** T-oracle can never be read out of the artefact without its non-deployable flag.

#### W3.4 — Verdict and branch · 3 h

- [ ] Apply the P8.0 repair predicate
- [ ] **No-repair branch** → Ch. 5 §5.3 upgrades to "neither target construction nor post-hoc rescaling repairs it"; §9.1 strengthens
- [ ] **Repair branch** → rewrite the central claim (§1.3, Abstract, §9.1) to "not repairable by target construction, repairable post hoc to degree X"; §9.4 becomes rescale-then-abstain; §10.3 gains the follow-up
- [ ] Record which branch fired and the value of X

**Check:** both branch texts existed in `content_thesis_ch5.py` **before** the verdict was read.

#### W3.5 — Figure · 2 h

- [ ] T33: contested-stratum ECE before and after each scaling variant, per arm, with the unanimous-stratum reference band drawn across it
- [ ] Every plotted value traces to a `phase8_posthoc_calibration.json` field

---

### W6 — Equivalence margins · ~2 days · no GPU

Scheduled before the GPU work because it can be finished while runs are queued.

#### W6.1 — Anchor computation · 4 h · → `src/models/phase8_margins.py`

- [ ] Resolution anchor: 2 × seed-to-seed SD of the RQ2 and RQ4 endpoints on the pooled contested stratum, from the existing per-seed artefacts
- [ ] Practical anchor: the descriptor's 3.25-point between-architecture macro-F1 gap
- [ ] Both computed from artefacts that predate this plan — assert no test-set quantity from the *current* interval enters the derivation

**Check:** neither anchor is a round number someone could have picked.

#### W6.2 — Freeze · 1 h

- [ ] Write `reports/phase8_margins.json`; refuse to overwrite
- [ ] Add the guard: the script **exits non-zero if `reports/phase8_tost.json` already exists**, so the margin can never be recomputed after seeing the test

**Check:** run the guard deliberately, confirm it blocks.

#### W6.3 — TOST · 4 h · → `src/models/phase8_tost.py`

- [ ] Two one-sided tests against δ for RQ2 (C2−C3 accuracy) and RQ4 (C4−C2 anatomical distance)
- [ ] Patient-clustered bootstrap, same seed and procedure
- [ ] Return exactly one of EQUIVALENT / NOT-NULL / INCONCLUSIVE per endpoint

**Check:** the verdict is selected by the frozen predicate; no branch is written by hand.

#### W6.4 — Wording and power · 3 h

- [ ] Every INCONCLUSIVE verdict is accompanied by the **n required** to reach δ at 80% power
- [ ] Ch. 5 §5.4 and Ch. 10 Table 17 restated from "NOT RESOLVED" to the TOST verdict
- [ ] If any endpoint is INCONCLUSIVE, add it to the §9.3 threat table at its honest severity

**Check:** the phrase "not resolved" no longer appears without either a margin or an explicit
underpowered declaration beside it.

---

### W7 — Risk-controlled selection · ~2 days · no GPU

#### W7.1 — Calibration split · 3 h · → `src/models/phase8_conformal.py`

- [ ] Partition the external panel into calibration and evaluation halves
- [ ] Since no case key exists, the split is image-level — record this in the artefact as a field, not a comment
- [ ] Reuse the scoring path from `src/models/phase6_selective.py`; do not reimplement it

#### W7.2 — Guarantee · 5 h

- [ ] Split-conformal / Learn-then-Test threshold at target selective risk ∈ {5%, 10%}
- [ ] Per arm, internal and external
- [ ] Report **achieved coverage at each guaranteed risk level** — the number a clinical reader wants and that no current table contains

#### W7.3 — Caveat plumbing · 2 h

- [ ] Add `exchangeability_violated: true` with its reason as a required field
- [ ] Make the Ch. 7 and §9.4 text render that field, so a rebuild cannot drop the caveat
- [ ] Figure T34: coverage-at-guaranteed-risk by arm

**Check:** deleting the caveat sentence from the content module breaks the build.

---

### W5 — Epoch-cap re-runs · ~22 GPU h · **first to cut**

#### W5.1 — Policy · 2 h

- [ ] Decide: re-run only the 8 capped runs, or all 12. **All 12** — a mixed-policy table is not comparable
- [ ] Record the amendment as `P8-DEV-1` with its reason
- [ ] Confirm C5/C6 (W4) will train under the same policy or the same cap, never a mix

#### W5.2 — Execute · 22 GPU h

- [ ] Raise the cap; keep every other hyperparameter, seed and selection criterion identical
- [ ] Log the realised `stop_reason` per run, as Phase 4 did

#### W5.3 — Gate · 2 h

- [ ] Assert `stop_reason == "early_stopping"` on all runs
- [ ] If any still caps, **re-declare the caveat** rather than dropping it
- [ ] Recompute the affected absolute scores; verify the *contrasts* moved within their intervals — if a contrast flips, that is a finding and Ch. 5 must report it

---

### W4 — Widening the family · ~2.5 days + ~9 GPU h

#### W4.1 — Dawid–Skene fit · 6 h · → `src/models/phase8_ds_targets.py`

- [ ] Fit the confusion-matrix model over the 4 annotators on cohort E **only** — never on test
- [ ] Report convergence and the per-annotator confusion matrices; FG2's should be visibly different, which is a check on the fit
- [ ] Assert unanimous rows reduce to near-one-hot posteriors; if they do not, the fit is wrong
- [ ] If it degenerates on 4 raters, record that as a finding about the method's data appetite and proceed with C6 alone

#### W4.2 — C5 training · 2 h setup + GPU

- [ ] Follow the `phase7_backbone_train.py` precedent: import the Phase 4 code and rebind **only** the target constructor
- [ ] Cohort, cache, normalisation, augmentation, schedule, early stopping, epoch policy, seeds identical

#### W4.3 — C6 annotator heads · 8 h setup + GPU

- [ ] Four heads on the shared trunk, one per annotator; per-head cross-entropy against that annotator's own label
- [ ] Marginalise over heads at inference; record the marginalisation rule in the pre-registration before running
- [ ] Verify parameter count and trainable-layer fraction match the other arms in **parameter** terms (the W1-style matching used for EfficientNet-B0)

#### W4.4 — Runs · ~9 GPU h

- [ ] C5 × 3 seeds, C6 × 3 seeds, seed-major order
- [ ] Every run records its realised stop reason

#### W4.5 — Evaluation · 4 h

- [ ] Run `phase4_eval.py` unchanged over the extended arm set
- [ ] **Wiring gate:** C2 and C3 rows reproduce `reports/phase4_stratified_metrics.json` to < 1e-9
- [ ] Recompute the RQ2-family statement across seven arms
- [ ] Recompute W2 and W3 for C5 and C6 so the calibration claim covers the full family

---

### W8 — Consistency and rebuild · ~4 days

#### W8.1 — Multiplicity rewording · 4 h

- [ ] Grep the thesis text for every use of the external AURC (0.1906 / 0.3235) and the rejection rates
- [ ] In Abstract, §1.3, §9.1, §9.4, §10.2: mark them **exploratory and directionally consistent across two independent endpoints** (Ch. 6 rejection, Ch. 7 AURC, ρ = 1.0)
- [ ] Leave Appendix C exactly as written — it was right, the prose was wrong
- [ ] Add one sentence explaining why two agreeing exploratory endpoints are worth stating but not worth calling confirmed

#### W8.2 — References into the build · 5 h

- [ ] Add a References section to `src/report/build_thesis_docx.py`, rendered from `phase8_bibliography.json`
- [ ] Resolve every in-text `cite(key)` at build time
- [ ] **Build fails** on: any unresolved key, any reference with no citation, an empty References section

#### W8.3 — Chapter updates · 8 h

- [ ] Ch. 3: §3.4 positioning, amended PRISMA
- [ ] Ch. 4: W2 intervals, Brier decomposition, verdict-selected §4.3 wording
- [ ] Ch. 5: W3 branch text, W4 seven-arm family, W6 TOST verdicts, epoch-cap status from W5
- [ ] Ch. 7: W7 coverage table with its caveat
- [ ] Ch. 9: threat table updated; §9.1 alternative readings re-answered against the new evidence
- [ ] Ch. 10: Table 17 verdicts restated; §10.3 drops what Phase 8 executed, gains what it could not

#### W8.4 — Appendix G · 3 h

- [ ] "Post-hoc analyses added after the thesis was drafted, and why they are not confirmatory"
- [ ] One row per Phase 8 endpoint: what was known when it was specified, and its secondary-family correction
- [ ] Cross-reference Appendix C so a reader meets the boundary between the two families in both places

#### W8.5 — Build gates · 3 h

- [ ] ToC / LoF / LoT repopulate (Word COM via PowerShell — LibreOffice and pandoc are absent on this machine)
- [ ] `phase7_register.py` extended to the Phase 8 artefacts; **every** number still resolves from JSON
- [ ] Grep the built text for any numeral not present in a register artefact
- [ ] Figure numbering continuous through T34+

#### W8.6 — Close · 2 h

- [ ] `THESIS_RESEARCH_BLUEPRINT.md` → v4.0, Phase 8 row with verdicts
- [ ] Commit and tag
- [ ] Split Paper A and Paper B drafts from the rebuilt chapters (§6)

---

### Master schedule

Critical path is W1 → W8. Everything else parallelises against it.

| Day | Primary (analyst) | Background (GPU) |
|---|---|---|
| 1 | P8.0 freeze · W1.1 citation infra | — |
| 2–3 | W1.2 search · W1.3 screen | — |
| 4 | W1.4 PRISMA · W1.6 adjudication | — |
| 5 | W1.5 positioning | — |
| 6 | W2.1–W2.2 estimators | W5.2 epoch re-runs (if funded) |
| 7 | W2.3–W2.5 CIs, Brier, verdict | W5.2 continues |
| 8 | W3.1–W3.2 logit gate, fit | W5.2 continues |
| 9 | W3.3–W3.5 variants, branch | W5.3 gate |
| 10 | W6.1–W6.2 margins, freeze | W4.1 DS fit |
| 11 | W6.3–W6.4 TOST, power | W4.4 C5/C6 runs |
| 12 | W7.1–W7.3 conformal | W4.4 continues |
| 13 | W4.5 family eval | — |
| 14–15 | W8.1–W8.2 rewording, references | — |
| 16–17 | W8.3 chapters | — |
| 18 | W8.4–W8.6 appendix, gates, tag | — |

**Minimum viable Q1 path** (drop W4, W5, W7): days 1–9 and 14–18 — **14 working days, ~1 GPU hour.**

### Master TODO — package level

- [ ] **P8.0** Pre-registration frozen, post-hoc status declared
- [ ] **W1** References exist · PRISMA amended · §3.4 written · novelty claim adjudicated
- [ ] **W2** Every ECE carries an interval · verdict holds under all binnings · Brier decomposed
- [ ] **W3** Logit gate passed · three scaling variants run · branch fired and text matches
- [ ] **W6** Margins derived before the test · TOST verdicts replace "not resolved"
- [ ] **W7** Coverage at guaranteed risk reported · exchangeability caveat structurally enforced
- [ ] **W5** *(optional)* Every run early-stopped, or the caveat re-declared
- [ ] **W4** *(optional)* Seven-arm family · wiring gate < 1e-9 · claim restated
- [ ] **W8** Inconsistency repaired · build fails on uncited references · Appendix G · v4.0 tagged
