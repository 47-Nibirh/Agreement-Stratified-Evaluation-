"""
Phase 1 - Eligibility Assessment and Extraction Table
=====================================================
Second PRISMA stage. Takes `literature/screened_included.csv` (records passing
the title/abstract screen) and applies theme-specific eligibility criteria plus
an explicit relevance-ranking rule, producing the final extraction table.

Eligibility criteria are declarative and auditable: each theme defines
REQUIRED term groups (all groups must match) and SCORING terms used only to
rank, never to include or exclude. A per-theme cap is then applied as a stated
pragmatic constraint appropriate to a Bachelor's-level review.

Records identified outside PubMed (foundational computer-science and reporting
-standard works not indexed in MEDLINE) are added at the "other methods" arm of
the PRISMA 2020 flow.

Run:  python src/literature/eligibility.py
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
LIT = ROOT / "literature"

# --------------------------------------------------------------------------
# Theme-specific eligibility criteria.
#   "require": list of term-groups; a record must match >=1 term in EVERY group
#   "score":   terms adding to the relevance score (ranking only)
#   "cap":     maximum records retained for the extraction table
# --------------------------------------------------------------------------
CRITERIA = {
    "T1 Endoscopy report NLP": {
        "require": [
            ["endoscop", "colonoscop", "gastroscop", "egd", "gastrointestinal",
             "barrett", "peptic ulcer", "gastritis", "esophag", "oesophag"],
            ["report", "free-text", "free text", "narrative", "unstructured",
             "documentation", "pathology report"],
            ["natural language processing", " nlp", "text classification",
             "information extraction", "text mining", "machine learning",
             "large language model"],
        ],
        "score": ["endoscopy report", "colonoscopy report", "free-text", "f1",
                  "sensitivity", "specificity", "accuracy", "validation",
                  "annotat", "gold standard", "kappa"],
        "cap": 14,
    },
    "T2 Rule-based vs ML": {
        "require": [
            ["negex", "ctakes", "medspacy", "context algorithm", "rule-based",
             "regular expression", "negation"],
            ["clinical", "biomedical", "medical", "electronic health record",
             "radiology", "pathology", "discharge summary"],
        ],
        "score": ["negation", "negex", "ctakes", "medspacy", "rule-based",
                  "compare", "versus", "outperform", "f1", "baseline"],
        "cap": 8,
    },
    "T3 Weak supervision": {
        "require": [
            ["weak supervision", "weakly supervised", "labeling function",
             "labelling function", "snorkel", "silver standard",
             "distant supervision", "noisy label", "programmatic label"],
            ["clinical", "biomedical", "medical", "electronic health record",
             "phenotyp", "text", "note"],
        ],
        "score": ["snorkel", "labeling function", "silver standard",
                  "weak supervision", "phenotyp", "f1", "label quality",
                  "noisy label"],
        "cap": 8,
    },
    "T4 Leakage & validity": {
        "require": [
            ["data leakage", "information leakage", "target leakage",
             "overoptimism", "optimistic bias", "overfitting",
             "reproducib", "spurious"],
            ["machine learning", "prediction model", "artificial intelligence",
             "deep learning", "classifier"],
            # A primary model-development paper that merely mentions
            # "overfitting" is not validity literature. Require the record to
            # be a review / methodological appraisal, or to name leakage
            # explicitly in the title.
            ["review", "leakage", "reproducib", "pitfall", "risk of bias",
             "methodolog", "appraisal", "quality assessment", "taxonomy"],
        ],
        "score": ["leakage", "overoptimism", "optimistic", "inflated",
                  "reproducib", "validation", "pitfall", "taxonomy",
                  "systematic review"],
        "cap": 8,
        "title_or_type_gate": True,
    },
    "T5 Reporting standards": {
        "require": [
            ["tripod", "probast", "reporting guideline", "model card",
             "risk of bias", "checklist", "datasheet"],
            ["prediction model", "machine learning", "artificial intelligence",
             "clinical", "diagnostic"],
        ],
        "score": ["tripod+ai", "tripod", "probast", "checklist", "guideline",
                  "risk of bias", "statement", "explanation and elaboration"],
        "cap": 6,
    },
}

# --------------------------------------------------------------------------
# Records identified through other methods (not indexed in PubMed/MEDLINE).
# These are foundational works in computer science and machine-learning
# methodology, cited directly in the blueprint's Appendix B.
# --------------------------------------------------------------------------
OTHER_SOURCES = [
    {"pmid": "", "year": "2023",
     "first_author": "Kapoor, S.",
     "authors_full": "Kapoor, S.; Narayanan, A.",
     "title": "Leakage and the reproducibility crisis in machine-learning-based science",
     "journal": "Patterns", "doi": "10.1016/j.patter.2023.100804",
     "theme": "T4 Leakage & validity", "source": "Hand-searched (CS venue)"},
    {"pmid": "", "year": "2017",
     "first_author": "Ratner, A.",
     "authors_full": "Ratner, A.; Bach, S. H.; Ehrenberg, H.; Fries, J.; Wu, S.; Re, C.",
     "title": "Snorkel: Rapid training data creation with weak supervision",
     "journal": "Proceedings of the VLDB Endowment", "doi": "10.14778/3157794.3157797",
     "theme": "T3 Weak supervision", "source": "Hand-searched (CS venue)"},
    {"pmid": "", "year": "2006",
     "first_author": "Demsar, J.",
     "authors_full": "Demsar, J.",
     "title": "Statistical comparisons of classifiers over multiple data sets",
     "journal": "Journal of Machine Learning Research", "doi": "",
     "theme": "T4 Leakage & validity", "source": "Hand-searched (CS venue)"},
    {"pmid": "", "year": "2010",
     "first_author": "Ojala, M.",
     "authors_full": "Ojala, M.; Garriga, G. C.",
     "title": "Permutation tests for studying classifier performance",
     "journal": "Journal of Machine Learning Research", "doi": "",
     "theme": "T4 Leakage & validity", "source": "Hand-searched (CS venue)"},
    {"pmid": "", "year": "2021",
     "first_author": "Gebru, T.",
     "authors_full": "Gebru, T.; Morgenstern, J.; Vecchione, B.; Vaughan, J. W.; "
                     "Wallach, H.; Daume III, H.; Crawford, K.",
     "title": "Datasheets for datasets",
     "journal": "Communications of the ACM", "doi": "10.1145/3458723",
     "theme": "T5 Reporting standards", "source": "Hand-searched (CS venue)"},
    {"pmid": "", "year": "2019",
     "first_author": "Mitchell, M.",
     "authors_full": "Mitchell, M.; Wu, S.; Zaldivar, A.; Barnes, P.; Vasserman, L.; "
                     "Hutchinson, B.; Spitzer, E.; Raji, I. D.; Gebru, T.",
     "title": "Model cards for model reporting",
     "journal": "Proceedings of the Conference on Fairness, Accountability, "
                "and Transparency (FAT* '19)", "doi": "10.1145/3287560.3287596",
     "theme": "T5 Reporting standards", "source": "Hand-searched (CS venue)"},
]


def matches(blob: str, groups: list[list[str]]) -> bool:
    return all(any(t in blob for t in g) for g in groups)


def relevance(blob: str, terms: list[str]) -> int:
    return sum(blob.count(t) for t in terms)


# --------------------------------------------------------------------------
# Post-hoc integrity filters on the eligible set
# --------------------------------------------------------------------------
PREPRINT_JOURNALS = ["medrxiv", "biorxiv", "arxiv", "research square", "ssrn"]

# Homonym guards: a term whose surface form also occurs in unrelated clinical
# contexts is only admissible when a discipline term co-occurs.
HOMONYM_GUARDS = {
    "snorkel": ["weak supervision", "labeling function", "labelling function",
                "training data", "machine learning", "supervision source",
                "generative model", "data programming"],
}


def homonym_false_positive(blob: str) -> str | None:
    for term, required in HOMONYM_GUARDS.items():
        if term in blob and not any(r in blob for r in required):
            return (f"Homonym false positive: '{term}' occurs in an unrelated "
                    f"clinical sense")
    return None


def norm_title(t: str) -> str:
    """Normalised title key for detecting duplicate/co-publications."""
    t = re.sub(r"[^a-z0-9 ]", " ", str(t).lower())
    return " ".join(t.split())[:110]


def title_or_type_gate(row) -> bool:
    """For T4: keep only reviews/methodological appraisals or explicit leakage work."""
    title = str(row.get("title", "")).lower()
    ptypes = str(row.get("pub_types", "")).lower()
    strong = ["leakage", "reproducib", "pitfall", "overoptimism", "optimistic bias"]
    if any(s in title for s in strong):
        return True
    return ("review" in ptypes or "review" in title
            or "scoping" in title or "meta-analysis" in ptypes)


def main() -> None:
    df = pd.read_csv(LIT / "screened_included.csv", encoding="utf-8")
    df["abstract"] = df["abstract"].fillna("")
    df["blob"] = (df.title.fillna("") + " " + df.abstract).str.lower()

    # ---- global integrity filters applied before theme criteria ---------
    df["_journal_l"] = df.journal.fillna("").str.lower()
    pre = df[df._journal_l.apply(lambda j: any(p in j for p in PREPRINT_JOURNALS))].copy()
    pre["exclusion_reason"] = "Preprint - not peer reviewed (inclusion criterion)"
    df = df[~df.index.isin(pre.index)]

    df["_homonym"] = df.blob.apply(homonym_false_positive)
    hom = df[df._homonym.notna()].copy()
    hom["exclusion_reason"] = hom["_homonym"]
    df = df[df._homonym.isna()]

    global_rejects = [pre, hom]
    print(f"  Global filters: {len(pre)} preprints, {len(hom)} homonym false positives removed")

    kept, rejected = [], list(global_rejects)
    for theme, crit in CRITERIA.items():
        sub = df[df.theme == theme].copy()
        ok = sub[sub.blob.apply(lambda b: matches(b, crit["require"]))].copy()
        no = sub[~sub.blob.apply(lambda b: matches(b, crit["require"]))].copy()
        no["exclusion_reason"] = "Did not meet theme-specific eligibility criteria"
        rejected.append(no)

        if crit.get("title_or_type_gate"):
            gate = ok.apply(title_or_type_gate, axis=1)
            fail = ok[~gate].copy()
            fail["exclusion_reason"] = ("Primary model-development study, not a "
                                        "methodological/validity appraisal")
            rejected.append(fail)
            ok = ok[gate].copy()

        # De-duplicate co-publications and preprint/journal pairs by title.
        ok["_tkey"] = ok.title.apply(norm_title)
        dup = ok[ok.duplicated("_tkey", keep="first")].copy()
        dup["exclusion_reason"] = "Duplicate / co-publication of an included record"
        rejected.append(dup)
        ok = ok.drop_duplicates("_tkey", keep="first")

        ok["relevance_score"] = ok.blob.apply(lambda b: relevance(b, crit["score"]))
        ok = ok.sort_values(["relevance_score", "year"], ascending=[False, False])
        head, tail = ok.head(crit["cap"]).copy(), ok.iloc[crit["cap"]:].copy()
        tail["exclusion_reason"] = ("Eligible but not retained: outside per-theme "
                                    "relevance cap for a Bachelor's-level review")
        rejected.append(tail)
        head["source"] = "PubMed/MEDLINE"
        kept.append(head)
        print(f"  {theme:28s} screened={len(sub):4d} eligible={len(ok):4d} "
              f"retained={len(head):3d}")

    inc = pd.concat(kept, ignore_index=True)
    rej = pd.concat(rejected, ignore_index=True)

    other = pd.DataFrame(OTHER_SOURCES)
    other["relevance_score"] = None
    final = pd.concat([inc, other], ignore_index=True)

    cols = ["pmid", "year", "first_author", "authors_full", "title", "journal",
            "doi", "theme", "source", "relevance_score", "abstract"]
    for c in cols:
        if c not in final.columns:
            final[c] = ""
    final = final[cols].sort_values(["theme", "year"], ascending=[True, True])
    final.to_csv(LIT / "extraction_table.csv", index=False, encoding="utf-8")
    rej.to_csv(LIT / "eligibility_excluded.csv", index=False, encoding="utf-8")

    prisma = json.loads((LIT / "prisma_counts.json").read_text(encoding="utf-8"))
    prisma["eligibility"] = {
        "records_assessed_for_eligibility": int(len(df) + len(pre) + len(hom)),
        "records_excluded_preprint": int(len(pre)),
        "records_excluded_homonym_false_positive": int(len(hom)),
        "records_excluded_duplicate_copublication": int(
            (rej.exclusion_reason == "Duplicate / co-publication of an included record").sum()),
        "records_excluded_primary_not_methodological": int(
            (rej.exclusion_reason == "Primary model-development study, not a "
                                     "methodological/validity appraisal").sum()),
        "records_failing_theme_criteria": int(
            (rej.exclusion_reason == "Did not meet theme-specific eligibility criteria").sum()),
        "records_eligible_but_capped": int(
            (rej.exclusion_reason.str.startswith("Eligible but not retained")).sum()),
        "exclusion_reason_counts": rej.exclusion_reason.value_counts().to_dict(),
        "records_included_from_pubmed": int(len(inc)),
        "records_included_other_methods": int(len(other)),
        "records_included_total": int(len(final)),
        "per_theme_caps": {k: v["cap"] for k, v in CRITERIA.items()},
        "theme_counts_final": final.theme.value_counts().to_dict(),
        "year_counts_final": final.year.astype(str).value_counts().sort_index().to_dict(),
    }
    (LIT / "prisma_counts.json").write_text(json.dumps(prisma, indent=2),
                                            encoding="utf-8")

    print(f"\n  FINAL INCLUDED: {len(final)}  "
          f"(PubMed {len(inc)} + other methods {len(other)})")
    print(final.theme.value_counts().to_string())
    print(f"\n  -> {LIT/'extraction_table.csv'}")


if __name__ == "__main__":
    main()
