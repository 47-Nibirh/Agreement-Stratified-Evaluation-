"""
Phase 1 (v2) - Eligibility assessment and extraction table.

Second PRISMA 2020 stage for the revised, imaging-oriented review. Takes
`literature_v2/screened_included.csv` and applies theme-specific eligibility
criteria plus an explicit relevance ranking, producing the final extraction
table.

Criteria are declarative and auditable:
  "require" - list of term groups; a record must match >=1 term in EVERY group
  "score"   - terms contributing to the relevance score (ranking ONLY, never
              inclusion/exclusion)
  "cap"     - maximum records retained, a stated pragmatic constraint

Foundational computer-science and reporting-standard works that MEDLINE does
not index are injected through the PRISMA "identified via other methods" arm
and flagged with source='other methods'.

Run:  python src/literature/eligibility_v2.py
"""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
LIT = ROOT / "literature_v2"

# --------------------------------------------------------------------------
# Homonym guard. "endoscop*" matches many procedures that have nothing to do
# with the luminal GI tract. Screening on the stem alone admitted drug-induced
# sleep endoscopy, laryngoscopy and neuroendoscopy papers to T1/T3 on the first
# pass; these are excluded explicitly and the exclusion is counted in PRISMA.
# --------------------------------------------------------------------------
NON_GI_ENDOSCOPY = [
    "drug-induced sleep endoscopy", "sleep endoscopy", "obstructive sleep apnea",
    "laryngoscop", "rhinoscop", "sinus", "otoscop", "bronchoscop",
    "neuroendoscop", "ventriculoscop", "cistern", "aqueduct",
    "hysteroscop", "cystoscop", "arthroscop", "thoracoscop", "fetoscop",
]
# Themes for which the record must be about the luminal GI tract.
GI_REQUIRED_THEMES = {
    "T1 Landmark recognition in UGI endoscopy",
    "T2 Endoscopic quality & blind-spot audit",
    "T3 Inter-observer variability in endoscopy",
}
GI_TERMS = [
    "gastro", "gastric", "stomach", "endoscopy", "colonoscop", "esophag",
    "oesophag", "duoden", "colorectal", "colon", "barrett", "polyp",
    "upper gastrointestinal", "gastrointestinal tract", "egd", "capsule endoscopy",
]

CRITERIA = {
    "T1 Landmark recognition in UGI endoscopy": {
        "require": [
            ["endoscop", "gastroscop", "egd", "esophagogastroduodenoscop",
             "upper gastrointestinal", "gastric", "stomach"],
            ["deep learning", "convolutional", "neural network",
             "artificial intelligence", "machine learning", "transformer"],
            ["anatomic", "landmark", "site", "region", "classification",
             "recognition", "localiz", "localis"],
        ],
        "score": ["anatomical site", "landmark", "gastric site", "convolutional",
                  "accuracy", "f1", "kappa", "real-time", "prospective",
                  "external validation", "systematic screening"],
        "cap": 12,
    },
    "T2 Endoscopic quality & blind-spot audit": {
        "require": [
            ["endoscop", "gastroscop", "esophagogastroduodenoscop", "egd"],
            ["blind spot", "photodocumentation", "quality", "completeness",
             "coverage", "monitoring", "audit", "protocol"],
            ["deep learning", "artificial intelligence", "neural network",
             "machine learning", "automat"],
        ],
        "score": ["blind spot", "photodocumentation", "quality control",
                  "randomized", "randomised", "trial", "coverage", "wisense",
                  "detection rate", "systematic screening"],
        "cap": 10,
    },
    "T3 Inter-observer variability in endoscopy": {
        "require": [
            ["endoscop", "gastroscop", "gastrointestinal", "gastric", "colon",
             "esophag", "oesophag", "barrett"],
            ["interobserver", "inter-observer", "interrater", "inter-rater",
             "observer variation", "observer agreement", "reproducibility"],
            ["kappa", "agreement", "reliability", "concordance", "variability"],
        ],
        "score": ["kappa", "fleiss", "krippendorff", "interobserver agreement",
                  "expert", "endoscopist", "classification", "substantial",
                  "moderate agreement"],
        "cap": 10,
    },
    "T4 Noisy / soft / multi-annotator labels": {
        "require": [
            ["noisy label", "label noise", "soft label", "annotator",
             "inter-observer variability", "crowdsourc", "label uncertainty",
             "disagreement", "multiple readers", "consensus"],
            ["deep learning", "machine learning", "neural network",
             "medical imaging", "medical image", "segmentation", "classification"],
        ],
        "score": ["multi-annotator", "soft label", "label noise", "annotator",
                  "disagreement", "consensus", "majority vote", "distillation",
                  "uncertainty", "dice", "f1", "calibration"],
        "cap": 12,
    },
    "T5 Uncertainty & calibration": {
        "require": [
            ["uncertainty", "calibration", "conformal", "selective prediction",
             "ensemble", "dropout", "confidence"],
            ["medical", "clinical", "diagnos", "imaging", "image", "radiol",
             "patholog", "endoscop"],
            ["deep learning", "neural network", "artificial intelligence",
             "machine learning"],
        ],
        "score": ["expected calibration error", "temperature scaling",
                  "conformal prediction", "deep ensemble", "monte carlo dropout",
                  "brier", "reliability diagram", "selective", "abstention",
                  "out-of-distribution"],
        "cap": 8,
    },
    "T6 External validation & dataset shift": {
        "require": [
            ["external validation", "externally validated", "dataset shift",
             "distribution shift", "domain shift", "out-of-distribution",
             "domain adaptation", "transportability", "geographic validation",
             "temporal validation"],
            # must concern IMAGE-based AI, not any prediction model whatsoever
            ["imaging", "medical image", "image-based", "radiograph", "ct ",
             "mri", "endoscop", "histolog", "patholog", "photograph", "camera",
             "convolutional", "computer vision"],
            ["deep learning", "artificial intelligence", "machine learning",
             "neural network", "convolutional"],
        ],
        "score": ["external validation", "endoscop", "gastro", "multicenter",
                  "multicentre", "performance drop", "degradation",
                  "domain adaptation", "geographic", "temporal validation",
                  "out-of-distribution", "unseen"],
        "cap": 8,
    },
    "T7 Reporting standards for medical AI": {
        "require": [
            # a NAMED standard, not the bare word "checklist"
            ["tripod", "stard", "probast", "consort-ai", "spirit-ai", "quadas",
             "claim checklist", "checklist for artificial intelligence",
             "reporting guideline", "decide-ai"],
            ["artificial intelligence", "machine learning", "deep learning",
             "prediction model", "diagnostic accuracy", "medical imaging"],
            ["adherence", "completeness", "reporting", "risk of bias",
             "quality assessment", "guideline", "checklist", "appraisal"],
        ],
        "score": ["adherence", "completeness of reporting", "risk of bias",
                  "tripod+ai", "tripod-ai", "claim", "stard-ai", "probast",
                  "imaging", "endoscop", "consensus statement", "reporting quality"],
        "cap": 8,
    },
}

# --------------------------------------------------------------------------
# PRISMA "identified via other methods": foundational works MEDLINE does not
# index (core computer-vision architectures, agreement statistics, the
# competing public GI datasets, and the AI reporting standards themselves).
# --------------------------------------------------------------------------
OTHER_METHODS = [
    dict(pmid="", year="2022", theme="T1 Landmark recognition in UGI endoscopy",
         title="A ConvNet for the 2020s",
         journal="Proceedings of the IEEE/CVF Conference on Computer Vision and Pattern Recognition (CVPR)",
         doi="10.1109/CVPR52688.2022.01167",
         first_author="Liu, Z.", authors_full="Liu, Z.; Mao, H.; Wu, C.-Y.; Feichtenhofer, C.; Darrell, T.; Xie, S.",
         note="ConvNeXt; the architecture family giving the GastroHUN baseline."),
    dict(pmid="", year="2016", theme="T1 Landmark recognition in UGI endoscopy",
         title="Deep Residual Learning for Image Recognition",
         journal="Proceedings of the IEEE Conference on Computer Vision and Pattern Recognition (CVPR)",
         doi="10.1109/CVPR.2016.90",
         first_author="He, K.", authors_full="He, K.; Zhang, X.; Ren, S.; Sun, J.",
         note="ResNet; the comparison backbone in the GastroHUN benchmark."),
    dict(pmid="", year="2021", theme="T1 Landmark recognition in UGI endoscopy",
         title="An Image is Worth 16x16 Words: Transformers for Image Recognition at Scale",
         journal="International Conference on Learning Representations (ICLR)",
         doi="10.48550/arXiv.2010.11929",
         first_author="Dosovitskiy, A.", authors_full="Dosovitskiy, A.; Beyer, L.; Kolesnikov, A.; et al.",
         note="Vision Transformer; alternative backbone family."),
    dict(pmid="", year="1971", theme="T3 Inter-observer variability in endoscopy",
         title="Measuring nominal scale agreement among many raters",
         journal="Psychological Bulletin",
         doi="10.1037/h0031619",
         first_author="Fleiss, J. L.", authors_full="Fleiss, J. L.",
         note="Fleiss' kappa; the multi-rater agreement statistic used in Phase 0."),
    dict(pmid="", year="1960", theme="T3 Inter-observer variability in endoscopy",
         title="A Coefficient of Agreement for Nominal Scales",
         journal="Educational and Psychological Measurement",
         doi="10.1177/001316446002000104",
         first_author="Cohen, J.", authors_full="Cohen, J.",
         note="Cohen's kappa; the pairwise agreement statistic."),
    dict(pmid="", year="2007", theme="T3 Inter-observer variability in endoscopy",
         title="Answering the Call for a Standard Reliability Measure for Coding Data",
         journal="Communication Methods and Measures",
         doi="10.1080/19312450709336664",
         first_author="Hayes, A. F.", authors_full="Hayes, A. F.; Krippendorff, K.",
         note="Krippendorff's alpha; used as a chance-correction robustness check."),
    dict(pmid="", year="2008", theme="T3 Inter-observer variability in endoscopy",
         title="Computing inter-rater reliability and its variance in the presence of high agreement",
         journal="British Journal of Mathematical and Statistical Psychology",
         doi="10.1348/000711006X126600",
         first_author="Gwet, K. L.", authors_full="Gwet, K. L.",
         note="Gwet's AC1; paradox-robust chance correction."),
    dict(pmid="", year="2017", theme="T5 Uncertainty & calibration",
         title="On Calibration of Modern Neural Networks",
         journal="Proceedings of the 34th International Conference on Machine Learning (ICML)",
         doi="10.48550/arXiv.1706.04599",
         first_author="Guo, C.", authors_full="Guo, C.; Pleiss, G.; Sun, Y.; Weinberger, K. Q.",
         note="Temperature scaling; the calibration baseline."),
    dict(pmid="", year="2017", theme="T5 Uncertainty & calibration",
         title="Simple and Scalable Predictive Uncertainty Estimation using Deep Ensembles",
         journal="Advances in Neural Information Processing Systems (NeurIPS) 30",
         doi="10.48550/arXiv.1612.01474",
         first_author="Lakshminarayanan, B.", authors_full="Lakshminarayanan, B.; Pritzel, A.; Blundell, C.",
         note="Deep ensembles; uncertainty baseline."),
    dict(pmid="", year="2016", theme="T5 Uncertainty & calibration",
         title="Dropout as a Bayesian Approximation: Representing Model Uncertainty in Deep Learning",
         journal="Proceedings of the 33rd International Conference on Machine Learning (ICML)",
         doi="10.48550/arXiv.1506.02142",
         first_author="Gal, Y.", authors_full="Gal, Y.; Ghahramani, Z.",
         note="MC dropout; uncertainty baseline."),
    dict(pmid="", year="2016", theme="T4 Noisy / soft / multi-annotator labels",
         title="Rethinking the Inception Architecture for Computer Vision",
         journal="Proceedings of the IEEE Conference on Computer Vision and Pattern Recognition (CVPR)",
         doi="10.1109/CVPR.2016.308",
         first_author="Szegedy, C.", authors_full="Szegedy, C.; Vanhoucke, V.; Ioffe, S.; Shlens, J.; Wojna, Z.",
         note="Label smoothing; the simplest soft-label regulariser."),
    dict(pmid="", year="2015", theme="T4 Noisy / soft / multi-annotator labels",
         title="Distilling the Knowledge in a Neural Network",
         journal="NeurIPS Deep Learning and Representation Learning Workshop",
         doi="10.48550/arXiv.1503.02531",
         first_author="Hinton, G.", authors_full="Hinton, G.; Vinyals, O.; Dean, J.",
         note="Soft-target training; theoretical basis for soft-label supervision."),
    dict(pmid="", year="2020", theme="T1 Landmark recognition in UGI endoscopy",
         title="HyperKvasir, a comprehensive multi-class image and video dataset for gastrointestinal endoscopy",
         journal="Scientific Data",
         doi="10.1038/s41597-020-00622-y",
         first_author="Borgli, H.", authors_full="Borgli, H.; Thambawita, V.; Smedsrud, P. H.; et al.",
         note="Candidate external-validation cohort (shared landmarks)."),
    dict(pmid="", year="2023", theme="T1 Landmark recognition in UGI endoscopy",
         title="GastroVision: A Multi-class Endoscopy Image Dataset for Computer Aided Gastrointestinal Disease Detection",
         journal="ICML Workshop on Machine Learning for Multimodal Healthcare Data",
         doi="10.1007/978-3-031-47679-2_10",
         first_author="Jha, D.", authors_full="Jha, D.; Sharma, V.; Dasu, N.; et al.",
         note="Second candidate external-validation cohort."),
]


def norm(s: object) -> str:
    return "" if pd.isna(s) else str(s).lower()


def main() -> None:
    df = pd.read_csv(LIT / "screened_included.csv")
    df["blob"] = (df["title"].map(norm) + " " + df["abstract"].map(norm))

    kept, dropped = [], []
    for theme, crit in CRITERIA.items():
        sub = df[df["theme"] == theme].copy()
        if sub.empty:
            continue
        ok = []
        for _, r in sub.iterrows():
            b = r["blob"]
            hit = next((t for t in NON_GI_ENDOSCOPY if t in b), None)
            if hit and theme in GI_REQUIRED_THEMES:
                dropped.append({
                    "pmid": r["pmid"], "title": r["title"], "theme": theme,
                    "reason": f"Non-GI endoscopy homonym ('{hit.strip()}')",
                })
                continue
            if theme in GI_REQUIRED_THEMES and not any(t in b for t in GI_TERMS):
                dropped.append({
                    "pmid": r["pmid"], "title": r["title"], "theme": theme,
                    "reason": "Not a luminal GI-tract study",
                })
                continue
            missing = [gi for gi, grp in enumerate(crit["require"])
                       if not any(t in b for t in grp)]
            if missing:
                dropped.append({
                    "pmid": r["pmid"], "title": r["title"], "theme": theme,
                    "reason": f"Eligibility: no term matched required group(s) {missing}",
                })
            else:
                ok.append(r)
        okdf = pd.DataFrame(ok)
        if okdf.empty:
            continue
        okdf["relevance"] = [
            sum(t in b for t in crit["score"]) for b in okdf["blob"]
        ]
        # deterministic ordering: relevance, then recency, then pmid
        okdf["_yr"] = pd.to_numeric(okdf["year"], errors="coerce").fillna(0)
        okdf = okdf.sort_values(["relevance", "_yr", "pmid"],
                                ascending=[False, False, True])
        cap = crit["cap"]
        for i, (_, r) in enumerate(okdf.iterrows()):
            if i < cap:
                kept.append(r)
            else:
                dropped.append({
                    "pmid": r["pmid"], "title": r["title"], "theme": theme,
                    "reason": f"Below per-theme relevance cap (rank {i+1} > cap {cap})",
                })

    out = pd.DataFrame(kept)
    out["source"] = "database search (PubMed/MEDLINE)"
    out["note"] = ""

    om = pd.DataFrame(OTHER_METHODS)
    om["source"] = "other methods (hand-searched, not MEDLINE-indexed)"
    om["relevance"] = None
    om["screen_decision"] = "include"
    om["pub_types"] = ""
    om["themes_all"] = om["theme"]
    om["abstract"] = ""
    om["n_authors"] = om["authors_full"].str.count(";") + 1

    cols = ["pmid", "year", "first_author", "authors_full", "n_authors", "title",
            "journal", "doi", "theme", "themes_all", "relevance", "source",
            "note", "abstract"]
    for c in cols:
        if c not in out.columns:
            out[c] = ""
        if c not in om.columns:
            om[c] = ""
    final = pd.concat([out[cols], om[cols]], ignore_index=True)
    final = final.sort_values(["theme", "year"], ascending=[True, False])
    final.to_csv(LIT / "extraction_table.csv", index=False, encoding="utf-8")

    pd.DataFrame(dropped).to_csv(LIT / "eligibility_excluded.csv",
                                 index=False, encoding="utf-8")

    prisma = json.loads((LIT / "prisma_counts.json").read_text(encoding="utf-8"))
    def _count(pred) -> int:
        return int(sum(1 for d in dropped if pred(d["reason"])))

    buckets = {
        "excluded_non_gi_homonym": _count(lambda r: r.startswith("Non-GI")),
        "excluded_not_luminal_gi": _count(lambda r: r.startswith("Not a luminal")),
        "excluded_failed_criteria": _count(lambda r: r.startswith("Eligibility")),
        "excluded_below_cap": _count(lambda r: r.startswith("Below")),
    }
    assert sum(buckets.values()) == len(dropped), (
        f"PRISMA accounting does not reconcile: "
        f"{sum(buckets.values())} bucketed vs {len(dropped)} excluded"
    )
    prisma["eligibility"] = {
        "records_assessed_for_eligibility": int(len(df)),
        "excluded_at_eligibility": int(len(dropped)),
        **buckets,
        "included_from_database_search": int(len(out)),
        "included_from_other_methods": int(len(om)),
        "total_included_in_review": int(len(final)),
        "per_theme_caps": {k: v["cap"] for k, v in CRITERIA.items()},
        "per_theme_included": final["theme"].value_counts().to_dict(),
        "cap_note": "Per-theme totals exceed the cap where hand-searched "
                    "'other methods' records were added on top of the capped "
                    "database-search yield.",
    }
    (LIT / "prisma_counts.json").write_text(json.dumps(prisma, indent=2),
                                            encoding="utf-8")

    print(f"assessed {len(df)}  ->  included {len(final)} "
          f"({len(out)} database + {len(om)} other methods)")
    print(json.dumps(prisma["eligibility"]["per_theme_included"], indent=1))
    yrs = pd.to_numeric(final["year"], errors="coerce").dropna().astype(int)
    print("year range:", int(yrs.min()), "-", int(yrs.max()))


if __name__ == "__main__":
    main()
