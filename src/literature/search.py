"""
Phase 1 - Reproducible Literature Search (PRISMA-style)
=======================================================
Executes the search protocol of THESIS_RESEARCH_BLUEPRINT.md section 4.2.1
against PubMed/MEDLINE via the NCBI E-utilities API, records the record count
at every PRISMA stage, de-duplicates, applies an explicit title/abstract
screen, and writes `literature/extraction_table.csv`.

The search is executed programmatically so that a third party can re-run this
file and obtain the same counts (subject to PubMed's growing index; the
execution date is stamped into the output).

Run:  python src/literature/search.py
"""

from __future__ import annotations

import json
import re
import time
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from datetime import date
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
LIT = ROOT / "literature"
LIT.mkdir(parents=True, exist_ok=True)

EUTILS = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
TOOL = "bsc-thesis-lit-review"
EMAIL = "fnibirh@gmail.com"

# --------------------------------------------------------------------------
# Search strategy: one query per sub-review theme (blueprint section 4.2.2)
# --------------------------------------------------------------------------
QUERIES = {
    "S1_endoscopy_nlp": (
        '("endoscopy report"[All Fields] OR "endoscopic report"[All Fields] OR '
        '"colonoscopy report"[All Fields] OR "endoscopy reports"[All Fields] OR '
        '"colonoscopy reports"[All Fields]) AND '
        '("natural language processing"[All Fields] OR "text classification"[All Fields] '
        'OR "machine learning"[All Fields] OR "information extraction"[All Fields])'
    ),
    "S2_gi_nlp_broad": (
        '"natural language processing"[All Fields] AND '
        '(endoscopy[All Fields] OR colonoscopy[All Fields] OR gastroenterology[All Fields] '
        'OR "peptic ulcer"[All Fields] OR gastritis[All Fields] OR "Barrett esophagus"[All Fields]) '
        'AND (classification[All Fields] OR extraction[All Fields] OR "quality"[All Fields])'
    ),
    "S3_rulebased_clinical_nlp": (
        '("rule-based"[All Fields] OR cTAKES[All Fields] OR medspacy[All Fields] OR '
        'NegEx[All Fields] OR "negation detection"[All Fields] OR "regular expression"[All Fields]) '
        'AND "natural language processing"[All Fields] AND '
        '(clinical[All Fields] OR biomedical[All Fields] OR "electronic health record"[All Fields])'
    ),
    "S4_weak_supervision": (
        '("weak supervision"[All Fields] OR "weakly supervised"[All Fields] OR '
        '"labeling functions"[All Fields] OR snorkel[All Fields] OR "silver standard"[All Fields] '
        'OR "distant supervision"[All Fields] OR "noisy labels"[All Fields]) AND '
        '(clinical[All Fields] OR biomedical[All Fields] OR "electronic health record"[All Fields])'
    ),
    "S5_leakage_validity": (
        '("data leakage"[All Fields] OR "information leakage"[All Fields] OR '
        '"target leakage"[All Fields] OR "overoptimism"[All Fields] OR '
        '"optimistic bias"[All Fields] OR "reproducibility"[All Fields]) AND '
        '("machine learning"[All Fields] OR "prediction model"[All Fields] OR "artificial intelligence"[All Fields]) '
        'AND (clinical[All Fields] OR medical[All Fields] OR health[All Fields])'
    ),
    "S6_reporting_standards": (
        '(TRIPOD[All Fields] OR PROBAST[All Fields] OR "reporting guideline"[All Fields] '
        'OR "model card"[All Fields] OR "risk of bias"[All Fields]) AND '
        '("prediction model"[All Fields] OR "machine learning"[All Fields] OR "artificial intelligence"[All Fields])'
    ),
}

DATE_FROM, DATE_TO = "2015", "2026"
# S3/S4/S6 include foundational work that predates the primary window; the
# window is relaxed for those themes and this is recorded in the protocol.
RELAXED = {"S3_rulebased_clinical_nlp": "2001",
           "S4_weak_supervision": "2010",
           "S6_reporting_standards": "2010"}

MAX_PER_QUERY = 200


def _get(url: str) -> bytes:
    for attempt in range(4):
        try:
            with urllib.request.urlopen(url, timeout=60) as r:
                return r.read()
        except Exception as e:  # transient NCBI throttling
            if attempt == 3:
                raise
            print(f"    retry {attempt + 1} after {e}")
            time.sleep(2 + 2 * attempt)
    raise RuntimeError("unreachable")


def esearch(term: str, date_from: str, date_to: str, retmax: int) -> tuple[int, list[str]]:
    q = urllib.parse.urlencode({
        "db": "pubmed", "term": term, "retmode": "json", "retmax": retmax,
        "mindate": date_from, "maxdate": date_to, "datetype": "pdat",
        "tool": TOOL, "email": EMAIL, "sort": "relevance",
    })
    d = json.loads(_get(f"{EUTILS}/esearch.fcgi?{q}"))["esearchresult"]
    return int(d["count"]), d.get("idlist", [])


def efetch(pmids: list[str]) -> list[dict]:
    out = []
    for i in range(0, len(pmids), 100):
        chunk = pmids[i:i + 100]
        q = urllib.parse.urlencode({
            "db": "pubmed", "id": ",".join(chunk), "retmode": "xml",
            "tool": TOOL, "email": EMAIL,
        })
        root = ET.fromstring(_get(f"{EUTILS}/efetch.fcgi?{q}"))
        for art in root.iter("PubmedArticle"):
            out.append(_parse(art))
        time.sleep(0.4)
    return out


def _text(node, path, default=""):
    el = node.find(path)
    return "".join(el.itertext()).strip() if el is not None else default


def _parse(art) -> dict:
    pmid = _text(art, ".//PMID")
    title = _text(art, ".//ArticleTitle")
    abstract = " ".join("".join(a.itertext()).strip()
                        for a in art.findall(".//Abstract/AbstractText"))
    journal = _text(art, ".//Journal/Title")
    year = (_text(art, ".//JournalIssue/PubDate/Year")
            or _text(art, ".//JournalIssue/PubDate/MedlineDate")[:4]
            or _text(art, ".//ArticleDate/Year"))
    authors = []
    for a in art.findall(".//AuthorList/Author"):
        ln, ini = _text(a, "LastName"), _text(a, "Initials")
        if ln:
            authors.append(f"{ln}, {'. '.join(ini)}." if ini else ln)
    # The DOI must be read from the article's own identifier list. A bare
    # ".//ArticleId" search also matches every entry in the article's
    # <ReferenceList>, which yields the DOI of a cited paper instead.
    doi = ""
    for aid in art.findall("./PubmedData/ArticleIdList/ArticleId"):
        if aid.get("IdType") == "doi":
            doi = (aid.text or "").strip()
            break
    if not doi:
        for el in art.findall("./MedlineCitation/Article/ELocationID"):
            if el.get("EIdType") == "doi":
                doi = "".join(el.itertext()).strip()
                break
    ptypes = [ "".join(p.itertext()).strip()
               for p in art.findall(".//PublicationTypeList/PublicationType")]
    return {"pmid": pmid, "title": title, "abstract": abstract, "journal": journal,
            "year": year, "authors": authors, "n_authors": len(authors),
            "doi": doi, "pub_types": ptypes,
            "language": _text(art, ".//Language", "eng")}


# --------------------------------------------------------------------------
# Screening criteria (blueprint section 4.2.1)
# --------------------------------------------------------------------------
EXCLUDE_TYPES = {"Editorial", "Comment", "Letter", "News", "Published Erratum",
                 "Retraction of Publication", "Biography", "Historical Article"}

TOPIC_TERMS = [
    "natural language processing", " nlp", "text classification", "machine learning",
    "deep learning", "text mining", "information extraction", "large language model",
    "weak supervision", "weakly supervised", "labeling function", "snorkel",
    "silver standard", "distant supervision", "noisy label", "data leakage",
    "information leakage", "overoptimism", "optimistic bias", "tripod", "probast",
    "rule-based", "negex", "ctakes", "medspacy", "negation", "reporting guideline",
    "risk of bias", "artificial intelligence", "prediction model", "regular expression",
]
EVAL_TERMS = ["accuracy", "sensitivity", "specificity", "f1", "f-1", "precision",
              "recall", "auc", "auroc", "c-statistic", "kappa", "ppv", "npv",
              "performance", "validat", "evaluat", "benchmark", "checklist",
              "guideline", "framework", "taxonomy", "review"]
IMAGE_ONLY = ["image classification", "computer vision", "convolutional neural network",
              "capsule endoscopy image", "video", "polyp detection in image"]


def screen(rec: dict) -> tuple[str, str]:
    """Return (decision, reason) for the title/abstract screening stage."""
    blob = f"{rec['title']} {rec['abstract']}".lower()
    if rec["language"] and rec["language"].lower() not in ("eng", "english"):
        return "exclude", "Not English"
    if set(rec["pub_types"]) & EXCLUDE_TYPES:
        return "exclude", "Editorial/comment/letter (not a primary study or review)"
    if not rec["abstract"]:
        return "exclude", "No abstract available for screening"
    if not any(t in blob for t in TOPIC_TERMS):
        return "exclude", "Off-topic: no NLP/ML/leakage/weak-supervision content"
    if any(t in blob for t in IMAGE_ONLY) and "text" not in blob and "report" not in blob:
        return "exclude", "Image-only study (no free-text or report data)"
    if not any(t in blob for t in EVAL_TERMS):
        return "exclude", "No quantitative evaluation or methodological framework reported"
    return "include", ""


THEME_MAP = {
    "S1_endoscopy_nlp": "T1 Endoscopy report NLP",
    "S2_gi_nlp_broad": "T1 Endoscopy report NLP",
    "S3_rulebased_clinical_nlp": "T2 Rule-based vs ML",
    "S4_weak_supervision": "T3 Weak supervision",
    "S5_leakage_validity": "T4 Leakage & validity",
    "S6_reporting_standards": "T5 Reporting standards",
}


def main() -> None:
    run_date = date.today().isoformat()
    prisma = {"run_date": run_date, "database": "PubMed/MEDLINE (NCBI E-utilities)",
              "queries": {}}

    all_ids: dict[str, set[str]] = {}
    for key, term in QUERIES.items():
        dfrom = RELAXED.get(key, DATE_FROM)
        n, ids = esearch(term, dfrom, DATE_TO, MAX_PER_QUERY)
        all_ids[key] = set(ids)
        prisma["queries"][key] = {
            "search_string": term, "date_from": dfrom, "date_to": DATE_TO,
            "total_hits": n, "retrieved": len(ids), "retmax": MAX_PER_QUERY,
        }
        print(f"  {key}: {n} hits, retrieved {len(ids)}")
        time.sleep(0.4)

    # ---- PRISMA stage 1: identification --------------------------------
    identified = sum(len(v) for v in all_ids.values())
    union = set().union(*all_ids.values())
    duplicates = identified - len(union)
    print(f"\n  Identified (with overlap): {identified}")
    print(f"  Unique after de-duplication: {len(union)}  (removed {duplicates})")

    # ---- fetch and screen ----------------------------------------------
    print(f"\n  Fetching metadata for {len(union)} records ...")
    recs = efetch(sorted(union))
    print(f"  Retrieved {len(recs)} full records")

    theme_of = {}
    for key, ids in all_ids.items():
        for i in ids:
            theme_of.setdefault(i, THEME_MAP[key])

    rows = []
    for r in recs:
        dec, reason = screen(r)
        rows.append({
            "pmid": r["pmid"], "year": r["year"], "title": r["title"],
            "journal": r["journal"], "doi": r["doi"],
            "first_author": r["authors"][0] if r["authors"] else "",
            "n_authors": r["n_authors"],
            "authors_full": "; ".join(r["authors"]),
            "theme": theme_of.get(r["pmid"], "unassigned"),
            "pub_types": "; ".join(r["pub_types"]),
            "screen_decision": dec, "exclusion_reason": reason,
            "abstract": r["abstract"],
        })

    df = pd.DataFrame(rows)
    df.to_csv(LIT / "search_results_all.csv", index=False, encoding="utf-8")

    inc = df[df.screen_decision == "include"].copy()
    exc = df[df.screen_decision == "exclude"]
    prisma["stages"] = {
        "records_identified_total": identified,
        "duplicates_removed": duplicates,
        "records_after_deduplication": len(union),
        "records_metadata_retrieved": len(recs),
        "records_screened": len(df),
        "records_excluded_at_screening": int(len(exc)),
        "records_passing_screen": int(len(inc)),
        "exclusion_reasons": exc.exclusion_reason.value_counts().to_dict(),
    }
    prisma["theme_counts_passing_screen"] = inc.theme.value_counts().to_dict()
    prisma["year_counts_passing_screen"] = (
        inc.year.value_counts().sort_index().to_dict())

    (LIT / "prisma_counts.json").write_text(
        json.dumps(prisma, indent=2), encoding="utf-8")
    inc.to_csv(LIT / "screened_included.csv", index=False, encoding="utf-8")

    print(f"\n  Screened: {len(df)}   Excluded: {len(exc)}   Passed: {len(inc)}")
    print("  Exclusion reasons:")
    for k, v in prisma["stages"]["exclusion_reasons"].items():
        print(f"    {v:4d}  {k}")
    print("  Theme distribution of records passing screen:")
    for k, v in prisma["theme_counts_passing_screen"].items():
        print(f"    {v:4d}  {k}")
    print(f"\n  -> {LIT/'prisma_counts.json'}")


if __name__ == "__main__":
    main()
