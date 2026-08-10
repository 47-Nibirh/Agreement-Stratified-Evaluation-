"""
Fetch volume / issue / pagination for the included PubMed records and build
APA 7th-edition reference strings for the extraction table.

Run:  python src/literature/enrich.py
"""
from __future__ import annotations

import time
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
LIT = ROOT / "literature"
EUTILS = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"


def _text(node, path, default=""):
    el = node.find(path)
    return "".join(el.itertext()).strip() if el is not None else default


def fetch(pmids: list[str]) -> dict[str, dict]:
    out: dict[str, dict] = {}
    for i in range(0, len(pmids), 100):
        chunk = pmids[i:i + 100]
        q = urllib.parse.urlencode({"db": "pubmed", "id": ",".join(chunk),
                                    "retmode": "xml", "tool": "bsc-thesis",
                                    "email": "fnibirh@gmail.com"})
        with urllib.request.urlopen(f"{EUTILS}/efetch.fcgi?{q}", timeout=90) as r:
            root = ET.fromstring(r.read())
        for art in root.iter("PubmedArticle"):
            pmid = _text(art, "./MedlineCitation/PMID")
            # The DOI must come from the article's own identifier list; a bare
            # ".//ArticleId" search also matches the article's <ReferenceList>
            # and returns the DOI of a cited paper instead.
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
            out[pmid] = {
                "volume": _text(art, ".//JournalIssue/Volume"),
                "issue": _text(art, ".//JournalIssue/Issue"),
                "pages": _text(art, ".//Pagination/MedlinePgn")
                         or _text(art, ".//Pagination/StartPage"),
                "elocation": _text(art, ".//ELocationID"),
                "doi": doi,
            }
        time.sleep(0.4)
    return out


def apa_authors(raw: str) -> str:
    """PubMed 'Last, F. M.; Last, F.' -> APA 7 author string."""
    if not raw or pd.isna(raw):
        return ""
    parts = [a.strip() for a in str(raw).split(";") if a.strip()]
    if not parts:
        return ""
    if len(parts) > 20:                       # APA 7: first 19 ... last
        parts = parts[:19] + ["..."] + [parts[-1]]
    if len(parts) == 1:
        return parts[0]
    if "..." in parts:
        i = parts.index("...")
        return ", ".join(parts[:i]) + ", ... " + parts[-1]
    return ", ".join(parts[:-1]) + ", & " + parts[-1]


def title_case_sentence(t: str) -> str:
    """APA uses sentence case for article titles; keep the first character."""
    t = str(t).strip().rstrip(".")
    return t


def _clean(v) -> str:
    """Empty string for missing values; pandas turns NaN into the text 'nan'."""
    s = str(v or "").strip()
    return "" if s.lower() in ("nan", "none", "<na>") else s


def build_apa(row) -> str:
    au = apa_authors(row.get("authors_full", ""))
    yr = _clean(row.get("year")) or "n.d."
    ti = title_case_sentence(row.get("title", ""))
    jr = _clean(row.get("journal"))
    vol = _clean(row.get("volume"))
    iss = _clean(row.get("issue"))
    pg = _clean(row.get("pages"))
    doi = _clean(row.get("doi"))
    eloc = _clean(row.get("elocation"))

    s = f"{au} ({yr}). {ti}."
    if jr:
        s += f" *{jr}*"
        if vol:
            s += f", *{vol}*"
            if iss:
                s += f"({iss})"
        if pg:
            s += f", {pg}"
        elif eloc and not vol:
            s += f", {eloc}"
        s += "."
    if doi:
        s += f" https://doi.org/{doi}"
    return s.replace("..", ".").strip()


def main() -> None:
    df = pd.read_csv(LIT / "extraction_table.csv")
    pm = [str(p) for p in df.pmid.dropna().tolist() if str(p).strip() not in ("", "nan")]
    pm = [p.split(".")[0] for p in pm]
    print(f"  enriching {len(pm)} PubMed records ...")
    meta = fetch(pm)

    for c in ["volume", "issue", "pages", "elocation"]:
        df[c] = ""
    n_doi_fixed = 0
    for i, row in df.iterrows():
        p = str(row.pmid).split(".")[0]
        if p in meta:
            for c, v in meta[p].items():
                if c == "doi":
                    if v and v != str(row.get("doi", "")).strip():
                        n_doi_fixed += 1
                    if v:
                        df.at[i, "doi"] = v
                else:
                    df.at[i, c] = v
    print(f"  corrected {n_doi_fixed} DOI values against the article identifier list")

    # Manual bibliographic detail for the hand-searched non-MEDLINE works.
    manual = {
        "Leakage and the reproducibility crisis in machine-learning-based science":
            ("4", "9", "100804"),
        "Snorkel: Rapid training data creation with weak supervision": ("11", "3", "269-282"),
        "Statistical comparisons of classifiers over multiple data sets": ("7", "", "1-30"),
        "Permutation tests for studying classifier performance": ("11", "", "1833-1863"),
        "Datasheets for datasets": ("64", "12", "86-92"),
        "Model cards for model reporting": ("", "", "220-229"),
    }
    for i, row in df.iterrows():
        key = str(row.title).strip()
        if key in manual:
            df.at[i, "volume"], df.at[i, "issue"], df.at[i, "pages"] = manual[key]

    df["apa"] = df.apply(build_apa, axis=1)
    df = df.sort_values("first_author", key=lambda s: s.astype(str).str.lower())
    df.to_csv(LIT / "extraction_table.csv", index=False, encoding="utf-8")
    print(f"  wrote {len(df)} records with APA strings")
    for s in df.apa.head(4):
        print("   -", s[:150])


if __name__ == "__main__":
    main()
