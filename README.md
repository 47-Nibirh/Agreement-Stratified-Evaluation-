# Agreement-Stratified Evaluation of Deep Learning for Anatomical Landmark Recognition in Upper Gastrointestinal Endoscopy

B.Sc. thesis, Department of Computer Science and Engineering, Daffodil International University.

**Authors:** Fatin Sadab Nibirh, MD Himel Rahman
**Supervisor:** Ms. Shayla Sharmin (Assistant Professor) · **Co-supervisor:** Dr. Md. Zahid Hasan (Associate Professor)

---

## The claim

Reported accuracy for endoscopy landmark classifiers is measured almost entirely on images that every expert labels the same way. That is a minority of the problem. This thesis re-evaluates a reproduced baseline stratified by inter-annotator agreement, and then separates how much of the resulting collapse is model failure and how much is irreducible label ambiguity.

## Headline results

| | |
|---|---|
| Corpus | GastroHUN — 8,834 images, 387 patients, 23 classes, 4 independent annotators |
| Non-unanimous share of corpus | **39.8%** (60.2% unanimous) |
| Reproduction gate | **83.9%** macro-F1 vs. published 85.0% (Δ −1.09 pt, inside the pre-registered ±1.5 pt band) → PASS |
| Agreement-stratified macro-F1 | 83.9% unanimous → 49.0% majority → 26.2% plurality → 30.8% no-majority |
| Headline gap | **53.1 points** (unanimous − no-majority), against a **3.25-point** architecture-choice benchmark |
| Ceiling-normalised gap | 7.4 pt, 95% CI [−3.1, 18.8] — includes zero, so most of the collapse is label ambiguity, not model error |
| Backbone generalisation | 3/3 primary claims replicate on EfficientNet-B0 (4.0 M params) vs. ConvNeXt-Tiny (28 M) |
| External validation | 3,125 out-of-distribution gastric images |
| Literature review | PRISMA: 1,382 records identified → 82 studies included (84.1% published since 2020) |

All intervals are patient-clustered bootstrap (1,000 resamples, resampling unit = patient), aggregated over 3 seeds.

## Method commitments

- **Pre-registration.** Every phase declares its hypothesis, endpoint, and verdict rule in a `reports/phase*_prereg.json` before the analysis runs. Amendments are recorded as separate artefacts, not edits.
- **Reproduction gate.** The published baseline had to be reproduced inside a declared tolerance band before any novel claim was permitted.
- **Patient-disjoint splits.** Zero patient overlap across train/validation/test; verified as a hard gate (`reports/phase2_split_provenance.json`).
- **No hand-typed numbers.** Every figure in the thesis, the progress report, and the slide decks is interpolated from the JSON/CSV artefacts by `src/report/`. Regenerating an artefact regenerates the documents.

## Layout

```
src/            pipeline — audit, training, inference, analysis, document generation
reports/        every pre-registration, metric, gate verdict and prediction artefact
figures_*/      generated figures, per phase
literature_v2/  PRISMA counts and the extraction table
metadata/       GastroHUN metadata and official split definitions
docs/           supporting documentation
*.docx / *.pdf  generated thesis, per-phase reports, defence decks
```

Reproduce the headline numbers:

```bash
python -c "import sys; sys.path.insert(0,'src/report'); from phase1_facts import facts; print(facts()['baseline'])"
```

## Not in this repository

- **Raw endoscopy images** (2.9 GB). Obtain them from the original GastroHUN release, below.
- **Model checkpoints** (~111 MB each) and the 224 px preprocessing caches — regenerable from `src/`.
- **The retired negative-control corpus.** Its own audit records a severe re-identification exposure (k-anonymity = 1 across 93.68% of quasi-identifier classes, no ethics approval, no consent), which is why it was retired. Only aggregate audit statistics are published here; the file itself is withheld. See `DATASET_DECISION_REPORT.md` §D10.

## Data attribution

Panesso-Ortiz et al., *GastroHUN: an Endoscopy Dataset of Complete Systematic Screening Protocol for the Stomach*, Scientific Data **12**:102 (2025). doi:[10.1038/s41597-025-04401-5](https://doi.org/10.1038/s41597-025-04401-5). Licensed CC BY 4.0; ethics approval CEI-2019-06-10 with informed consent. Metadata and split definitions redistributed here under that licence.

## Environment

Python 3.14.5 · PyTorch 2.12.0+cu126 (CUDA 12.6) · torchvision · NumPy · pandas · scikit-learn · SciPy · Pillow · Matplotlib · python-docx · python-pptx
