# Phase 7 — Thesis Document: Content List and Implementation Checklist

**Derived from** `THESIS_RESEARCH_BLUEPRINT.md` v3.6 §3 (research questions), §4 PHASE 7,
§10 (limitations), §15 (reporting standards), plus the carry-forward decisions in
`reports/phase5_carry_forward.json` and the Phase 6 §5.2 carry-forwards.

Phases 0–6 produced seven standalone reports totalling well over a hundred pages. Phase 7 is
not a summary of them. It is a single argument, and the reports become its evidence base.

---

## 0. The thesis has one claim, and everything is arranged to support it

Six phases produced one durable positive result, one reframing result, and a set of
pre-registered nulls. Written as six chapters of "we tried X, it did not work", that is a
weak thesis. Written around what the nulls jointly establish, it is a strong one:

> **Expert-agreement stratification separates two things the literature reports as one: a
> reference standard that ceases to exist, and a classifier that falls short of what
> remains of it. As annotator agreement falls, the attainable ceiling drops from 1.00 to
> 0.67 — so most of the apparent performance collapse is the ceiling moving — while the
> model still recovers only a quarter of the distance from an individual annotator to that
> ceiling. Confidence degrades further and faster than discrimination, no target
> construction repairs it, and the endpoint that separates configurations is not accuracy
> but the model's willingness to decline.**

Every chapter earns a clause of that sentence:

| Clause | Earned by |
|---|---|
| "separates two things the literature reports as one" | Ch. 4 (Phase 3), Ch. 7 (P6-A) |
| "a reference standard that ceases to exist" | Ch. 7 (P6-A oracle; the P6-A/P6-B degeneracies) |
| "a classifier that falls short of what remains" | Ch. 7 (24% of headroom recovered), Ch. 4 (Phase 3B ceiling-normalised gaps) |
| "confidence degrades further and faster" | Ch. 4 (ECE 9.15% → 56.40%) |
| "no target construction repairs it" | Ch. 5 (C0–C4, the matched C3 control) |
| "not accuracy but the willingness to decline" | Ch. 6 (Phase 5), Ch. 7 (P6-D) |
| the audit that made any of it trustworthy | Ch. 2 (Phase 0), Ch. 8 (RQ5) |

> ⚠️ **Wording discipline, carried from P6-AMD-5.** The thesis must never state P6-A as
> "the model beats the expert". The frozen rule returned ABOVE THE HUMAN PANEL, but the
> model exceeds the modal-vote oracle on no stratum, and on the 2-1-1 stratum half of all
> held-out annotators are singletons who cannot score well whatever their skill. Use the
> `qualified_verdict` field of `reports/phase6_human.json`, never `verdict_summary`.

**Two chapters do not yet exist and must be written from artefacts that already exist on
disk:** the RQ5 negative-control chapter (Ch. 8) and the synthesis (Ch. 9).

---

## 1. What is already written, and what Phase 7 must add

| Source | Status | Phase 7 action |
|---|---|---|
| `Phase0_Phase1_Report` (audit + PRISMA review) | complete | recast as Ch. 2 and Ch. 3; drop the phase framing |
| `Phase2_Report` (baseline reproduction) | complete | compress into Ch. 4 §1 — it is a validity check, not a finding |
| `Phase3_Report` + 3B amendment | complete | Ch. 4, with the X1–X4 corrections integrated in the text rather than appended |
| `Phase4_Report` | complete | Ch. 5 |
| `Phase5_Report` + 5B | complete | Ch. 6 |
| `Phase6_Report` | complete | Ch. 7 |
| **RQ5 negative control** | ⚠️ **never written** | **Ch. 8 — new. Artefacts exist (`DATASET_DECISION_REPORT.md`, both audits)** |
| **Synthesis and defence of the central claim** | ⚠️ **never written** | **Ch. 9 — new** |
| **Multiplicity declaration** | ⚠️ **never made** | Appendix; one primary endpoint per RQ named, everything else exploratory |

---

## 2. Thesis content list

```
AGREEMENT-STRATIFIED EVALUATION OF DEEP LEARNING FOR ANATOMICAL
LANDMARK RECOGNITION IN UPPER GASTROINTESTINAL ENDOSCOPY

Front matter
  Title page · Declaration · Certificate · Acknowledgements
  Abstract (structured)
  Table of Contents · List of Figures · List of Tables · Abbreviations

1. Introduction
  1.1  Clinical context: the Systematic Screening of the Stomach protocol
  1.2  The problem the literature does not report: ground truth is constructed
  1.3  The central claim of this thesis
  1.4  Contributions
  1.5  Thesis roadmap

2. Corpus Audit and Data Provenance (Phase 0)
  2.1  Why an audit chapter precedes any modelling chapter
  2.2  The eight gates, and the two that returned CONDITIONAL
  2.3  Agreement structure: three chance corrections that coincide, and why
  2.4  Disagreement is anatomically structured — the (wall × station) finding
  2.5  The near-duplicate scan, and the lesson about uncalibrated thresholds

3. Literature Review (Phase 1)
  3.1  PRISMA 2020 protocol and the seven themed searches
  3.2  What 82 included studies do and do not report
  3.3  The four commonest omissions, and which this thesis addresses

4. Agreement-Stratified Evaluation (Phases 2–3)
  4.1  Baseline reproduction as a validity check
  4.2  Stratum construction from the four-annotator vote matrix
  4.3  The ceiling problem, and why raw stratified scores mislead
  4.4  Results: discrimination and the calibration collapse
  4.5  Corrections to the first analysis (X1–X4), and what survived

5. Target Construction and Uncertainty (Phase 4)
  5.1  Five configurations, one cohort, one thing varying
  5.2  Deriving the control rather than choosing it
  5.3  Results: the control wins on calibration, and what that means
  5.4  Why RQ2, RQ3 and RQ4 are reported as unresolved

6. External Validation (Phase 5, 5B)
  6.1  The label-space finding, which precedes any transfer number
  6.2  Transfer, rejection, and calibration ordering
  6.3  Self-training: what adaptation bought and what it cost

7. Explainability and Error Analysis (Phase 6)
  7.1  Changing the comparator
  7.2  The human comparator, and the reframing of Chapter 4
  7.3  Confusion geometry, and the settlement of X3
  7.4  Attribution: a measurement that could not be made, and one that could
  7.5  Selective prediction as the deployable endpoint

8. The Audit Protocol as an Instrument (RQ5)  ** NEW **
  8.1  An audit that passes everything it sees is not an audit
  8.2  The retired corpus as negative control
  8.3  Gate-by-gate comparison of the two corpora
  8.4  What the protocol detected, and what it would have missed

9. Synthesis  ** NEW **
  9.1  The central claim, defended against each alternative reading
  9.2  What the nulls establish that a positive result would not have
  9.3  Threats to validity, ranked by severity
  9.4  What a clinician could deploy from this, and under what conditions

10. Conclusions and Future Work
  10.1  Answers to RQ1–RQ5
  10.2  Contributions restated against the literature of Chapter 3
  10.3  Future work, costed

Appendices
  A. Pre-registration records, all phases, verbatim with freeze timestamps
  B. Declared deviations and amendments, all phases (P4-DEV, P5-DEV, P6-DEV, X1–X4, P6-AMD)
  C. Multiplicity: primary endpoint per RQ, everything else exploratory  ** NEW **
  D. Full per-class, per-stratum, per-arm metric tables
  E. Script and artefact manifest — the reproducibility index
  F. Analyses NOT executed, and what each would cost
References
```

---

## 3. Implementation checklist

| # | Task | Output | Validation criterion |
|---|---|---|---|
| P7.1 | RQ5 negative-control analysis from the existing audit artefacts | `reports/phase7_rq5.json` | gate-by-gate verdicts for both corpora produced by one script; no hand-entered verdicts |
| P7.2 | Multiplicity declaration | `reports/phase7_multiplicity.json` | one named primary endpoint per RQ; Holm-adjusted intervals for the primary family |
| P7.3 | Cross-phase results register | `reports/phase7_register.json` | every headline number in the thesis resolved from a phase artefact, keyed by chapter |
| P7.4 | Thesis figure suite (renumbered F1–Fn, continuous) | `figures_thesis/` | every figure traced to a JSON field; phase-local numbering retired |
| P7.5 | Chapter content modules | `src/report/content_thesis_ch*.py` | one module per chapter, no number typed |
| P7.6 | Build the thesis | `Thesis.docx` / `.pdf` | ToC/LoF/LoT populated; every verdict rule-selected |
| P7.7 | Defence deck | `Defence.pptx` | 20 slides; every claim traceable to a thesis figure |
| P7.8 | Final blueprint update and tag | `THESIS_RESEARCH_BLUEPRINT.md` v4.0 | Phase 7 complete; repository tagged |

---

## 4. Standing rules

- No number typed by hand; the thesis interpolates from the same JSON artefacts the phase
  reports used, so the two can never disagree.
- Every verdict selected from a frozen pre-registration field.
- Corrections and amendments are integrated into the running text where the claim is made,
  not quarantined in an appendix — a reader must meet the correction where they would
  otherwise be misled.
- Phase-local figure numbering (F1–F45) is retired and replaced by continuous thesis
  numbering; the phase reports remain in the repository as the audit trail.
