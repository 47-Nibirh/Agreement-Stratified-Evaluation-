"""
Phase 1 (v2) - Reproducible literature search for the GastroHUN-based thesis.

This REPLACES src/literature/search.py, whose six themes were built around
NLP on free-text endoscopy reports. That research question was retired with the
previous dataset. The revised review covers seven themes matching the imaging
and label-agreement question now being asked:

  T1  AI for upper GI endoscopy: anatomical landmark / site recognition
  T2  Endoscopic quality metrics, blind-spot monitoring, photodocumentation audit
  T3  Inter-observer variability and agreement statistics in endoscopy
  T4  Learning from noisy, soft, or multi-annotator labels
  T5  Uncertainty quantification and calibration in medical imaging AI
  T6  External validation, dataset shift, and generalisability of medical AI
  T7  Reporting standards for diagnostic and prognostic AI (CLAIM/TRIPOD+AI/STARD-AI)

Search is executed against PubMed/MEDLINE through NCBI E-utilities and every
PRISMA 2020 stage count is recorded so a third party can re-run and reproduce.

Run:  python src/literature/search_v2.py
"""

from __future__ import annotations

import json
import time
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from datetime import date
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
LIT = ROOT / "literature_v2"
LIT.mkdir(parents=True, exist_ok=True)

EUTILS = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
TOOL = "bsc-thesis-lit-review-v2"
EMAIL = "fnibirh@gmail.com"

QUERIES = {
    "T1_landmark_recognition": (
        '(endoscopy[All Fields] OR gastroscopy[All Fields] OR '
        '"esophagogastroduodenoscopy"[All Fields] OR EGD[All Fields] OR '
        '"upper gastrointestinal"[All Fields]) AND '
        '("anatomical site"[All Fields] OR "anatomical landmark"[All Fields] OR '
        '"anatomical classification"[All Fields] OR "site recognition"[All Fields] OR '
        '"landmark classification"[All Fields] OR "gastric sites"[All Fields] OR '
        '"image classification"[All Fields]) AND '
        '("deep learning"[All Fields] OR "convolutional neural network"[All Fields] OR '
        '"artificial intelligence"[All Fields] OR "machine learning"[All Fields])'
    ),
    "T2_quality_blindspot": (
        '(endoscopy[All Fields] OR gastroscopy[All Fields] OR '
        '"esophagogastroduodenoscopy"[All Fields]) AND '
        '("blind spot"[All Fields] OR "blind spots"[All Fields] OR '
        '"photodocumentation"[All Fields] OR "quality control"[All Fields] OR '
        '"quality indicator"[All Fields] OR "completeness"[All Fields] OR '
        '"systematic screening protocol"[All Fields] OR "mucosal exposure"[All Fields]) AND '
        '("deep learning"[All Fields] OR "artificial intelligence"[All Fields] OR '
        '"neural network"[All Fields] OR "monitoring system"[All Fields])'
    ),
    "T3_interobserver": (
        '(endoscopy[All Fields] OR gastroscopy[All Fields] OR gastrointestinal[All Fields]) AND '
        '("interobserver"[All Fields] OR "inter-observer"[All Fields] OR '
        '"interrater"[All Fields] OR "inter-rater"[All Fields] OR '
        '"observer variation"[MeSH Terms] OR "observer agreement"[All Fields]) AND '
        '(kappa[All Fields] OR agreement[All Fields] OR reliability[All Fields] OR '
        'variability[All Fields])'
    ),
    "T4_noisy_soft_labels": (
        '("noisy labels"[All Fields] OR "label noise"[All Fields] OR '
        '"soft labels"[All Fields] OR "soft label"[All Fields] OR '
        '"multiple annotators"[All Fields] OR "multi-annotator"[All Fields] OR '
        '"annotator disagreement"[All Fields] OR "label uncertainty"[All Fields] OR '
        '"crowdsourced labels"[All Fields] OR "inter-observer variability"[All Fields]) AND '
        '("deep learning"[All Fields] OR "machine learning"[All Fields] OR '
        '"neural network"[All Fields] OR "medical imaging"[All Fields] OR '
        '"segmentation"[All Fields] OR "classification"[All Fields])'
    ),
    "T5_uncertainty_calibration": (
        '("uncertainty quantification"[All Fields] OR "predictive uncertainty"[All Fields] OR '
        '"model calibration"[All Fields] OR "calibration"[All Fields] OR '
        '"conformal prediction"[All Fields] OR "selective prediction"[All Fields] OR '
        '"deep ensembles"[All Fields] OR "Monte Carlo dropout"[All Fields]) AND '
        '("medical imaging"[All Fields] OR "medical image"[All Fields] OR '
        '"clinical"[All Fields] OR "diagnosis"[All Fields]) AND '
        '("deep learning"[All Fields] OR "neural network"[All Fields] OR '
        '"artificial intelligence"[All Fields])'
    ),
    "T6_external_validation": (
        '("external validation"[All Fields] OR "generalisability"[All Fields] OR '
        '"generalizability"[All Fields] OR "dataset shift"[All Fields] OR '
        '"distribution shift"[All Fields] OR "domain shift"[All Fields] OR '
        '"multicenter validation"[All Fields] OR "out-of-distribution"[All Fields]) AND '
        '("medical imaging"[All Fields] OR "medical image"[All Fields] OR '
        '"endoscopy"[All Fields] OR "diagnostic accuracy"[All Fields]) AND '
        '("deep learning"[All Fields] OR "artificial intelligence"[All Fields] OR '
        '"machine learning"[All Fields])'
    ),
    "T7_reporting_standards": (
        '(CLAIM[All Fields] OR "TRIPOD"[All Fields] OR "STARD"[All Fields] OR '
        '"PROBAST"[All Fields] OR "CONSORT-AI"[All Fields] OR "SPIRIT-AI"[All Fields] OR '
        '"reporting guideline"[All Fields] OR "checklist"[All Fields]) AND '
        '("artificial intelligence"[All Fields] OR "machine learning"[All Fields] OR '
        '"deep learning"[All Fields] OR "prediction model"[All Fields] OR '
        '"diagnostic accuracy"[All Fields])'
    ),
}

DATE_FROM, DATE_TO = "2015", "2026"
RELAXED = {"T3_interobserver": "2005", "T7_reporting_standards": "2010"}
MAX_PER_QUERY = 220

THEME_MAP = {
    "T1_landmark_recognition": "T1 Landmark recognition in UGI endoscopy",
    "T2_quality_blindspot": "T2 Endoscopic quality & blind-spot audit",
    "T3_interobserver": "T3 Inter-observer variability in endoscopy",
    "T4_noisy_soft_labels": "T4 Noisy / soft / multi-annotator labels",
    "T5_uncertainty_calibration": "T5 Uncertainty & calibration",
    "T6_external_validation": "T6 External validation & dataset shift",
    "T7_reporting_standards": "T7 Reporting standards for medical AI",
}


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
    # DOI must come from the article's OWN identifier list. A bare ".//ArticleId"
    # also matches every entry inside <ReferenceList> and would return the DOI of
    # a cited paper instead. This bug corrupted 22/44 refs in the first review.
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
    ptypes = ["".join(p.itertext()).strip()
              for p in art.findall(".//PublicationTypeList/PublicationType")]
    return {"pmid": pmid, "title": title, "abstract": abstract, "journal": journal,
            "year": year, "authors": authors, "n_authors": len(authors),
            "doi": doi, "pub_types": ptypes,
            "language": _text(art, ".//Language", "eng")}


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


# --------------------------------------------------------------------------
# Screening criteria
# --------------------------------------------------------------------------
EXCLUDE_TYPES = {"Editorial", "Comment", "Letter", "News", "Published Erratum",
                 "Retraction of Publication", "Biography", "Historical Article"}

TOPIC_TERMS = [
    "deep learning", "machine learning", "artificial intelligence", "neural network",
    "convolutional", "transformer", "computer vision", "image classification",
    "interobserver", "inter-observer", "interrater", "inter-rater", "kappa",
    "observer agreement", "observer variation", "label noise", "noisy label",
    "soft label", "annotator", "crowdsourc", "uncertainty", "calibration",
    "conformal", "external validation", "generalis", "generaliz", "dataset shift",
    "domain shift", "distribution shift", "out-of-distribution", "tripod", "claim",
    "stard", "probast", "reporting guideline", "checklist", "blind spot",
    "photodocumentation", "quality indicator", "endoscop",
]
EVAL_TERMS = ["accuracy", "sensitivity", "specificity", "f1", "f-1", "precision",
              "recall", "auc", "auroc", "c-statistic", "kappa", "ppv", "npv",
              "performance", "validat", "evaluat", "benchmark", "checklist",
              "guideline", "framework", "taxonomy", "review", "agreement",
              "concordance", "reliability", "calibration"]

# Homonym traps observed in the previous review: guard explicitly.
HOMONYM_TRAPS = [
    ("claim", ["insurance claim", "claims database", "claims data",
               "administrative claims", "medicare claims"]),
    ("stard", ["stardust", "starch"]),
]


def screen(rec: dict) -> tuple[str, str]:
    blob = f"{rec['title']} {rec['abstract']}".lower()
    if rec["language"] and rec["language"].lower() not in ("eng", "english"):
        return "exclude", "Not English"
    if set(rec["pub_types"]) & EXCLUDE_TYPES:
        return "exclude", "Editorial/comment/letter (not a primary study or review)"
    if not rec["abstract"]:
        return "exclude", "No abstract available for screening"
    for _, traps in HOMONYM_TRAPS:
        if any(t in blob for t in traps):
            return "exclude", "Homonym match (e.g. insurance 'claims', not CLAIM checklist)"
    if not any(t in blob for t in TOPIC_TERMS):
        return "exclude", "Off-topic: no AI/agreement/validation/reporting content"
    if not any(t in blob for t in EVAL_TERMS):
        return "exclude", "No quantitative evaluation or methodological framework reported"
    if "veterinary" in blob or "rats" in blob or "mice" in blob:
        return "exclude", "Non-human study"
    return "include", ""


def main() -> None:
    run_date = date.today().isoformat()
    prisma = {"run_date": run_date,
              "database": "PubMed/MEDLINE (NCBI E-utilities)",
              "protocol_note": "Replaces the retired NLP-on-reports protocol; "
                               "themes realigned to the GastroHUN imaging question.",
              "queries": {}}

    all_ids: dict[str, set[str]] = {}
    for key, term in QUERIES.items():
        dfrom = RELAXED.get(key, DATE_FROM)
        n, ids = esearch(term, dfrom, DATE_TO, MAX_PER_QUERY)
        all_ids[key] = set(ids)
        prisma["queries"][key] = {
            "theme": THEME_MAP[key], "search_string": term,
            "date_from": dfrom, "date_to": DATE_TO,
            "total_hits": n, "retrieved": len(ids), "retmax": MAX_PER_QUERY,
        }
        print(f"  {key}: {n} hits, retrieved {len(ids)}")
        time.sleep(0.4)

    identified = sum(len(v) for v in all_ids.values())
    union = set().union(*all_ids.values())
    duplicates = identified - len(union)
    print(f"\n  Identified (with overlap): {identified}")
    print(f"  Unique after de-duplication: {len(union)}  (removed {duplicates})")

    print(f"\n  Fetching metadata for {len(union)} records ...")
    recs = efetch(sorted(union))
    print(f"  Retrieved {len(recs)} full records")

    theme_of: dict[str, str] = {}
    theme_all: dict[str, list[str]] = {}
    for key, ids in all_ids.items():
        for i in ids:
            theme_of.setdefault(i, THEME_MAP[key])
            theme_all.setdefault(i, []).append(THEME_MAP[key])

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
            "themes_all": "; ".join(sorted(set(theme_all.get(r["pmid"], [])))),
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
    prisma["year_counts_passing_screen"] = inc.year.value_counts().sort_index().to_dict()

    (LIT / "prisma_counts.json").write_text(json.dumps(prisma, indent=2), encoding="utf-8")
    inc.to_csv(LIT / "screened_included.csv", index=False, encoding="utf-8")

    print(f"\n  Screened: {len(df)}   Excluded: {len(exc)}   Passed: {len(inc)}")
    for k, v in prisma["stages"]["exclusion_reasons"].items():
        print(f"    {v:4d}  {k}")
    print("  Theme distribution:")
    for k, v in prisma["theme_counts_passing_screen"].items():
        print(f"    {v:4d}  {k}")


if __name__ == "__main__":
    main()
