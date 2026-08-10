"""
Phase 8 / P8.3 -- the reference list, generated.

The thesis previously contained no bibliography and no in-text citations, which
made every statement about "the literature" unsourced. The material to fix that
was already committed: literature_v2/extraction_table.csv carries all 82 included
studies with a populated APA string, volume, pages and DOI.

This module numbers them into a single reference list and hands the document
builder two functions:

    cite("guo")            -> "[26]"        one marker
    cite("guo", "gal")     -> "[19, 26]"    several, sorted, de-duplicated
    cite_theme("T5")       -> "[17, 19, ...]"  every study in a themed search
    references()           -> the ordered list of formatted entries

Keys are short slugs derived from first author and year, so the prose says
cite("guo") rather than a number, and renumbering can never desynchronise the
text from the list.

Two sets are merged into one numbering:

    review      the 82 PRISMA-included studies (extraction_table.csv)
    additional  the corpus descriptor, the reporting guideline, and two method
                papers, from literature_v2/additional_references.json -- things a
                thesis must cite that were never candidates for review inclusion

The split is preserved on every entry so Appendix F can report how many of each
were actually cited, and so the PRISMA count of 82 is never inflated by a
reference that did not come through screening.

Emits reports/phase8_bibliography.json.

Run:  python src/report/bibliography.py       (regenerates and prints a summary)
"""
from __future__ import annotations

import csv
import json
import re
import time
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
LIT = ROOT / "literature_v2"
EXTRACTION = LIT / "extraction_table.csv"
ADDITIONAL = LIT / "additional_references.json"
OUT = ROOT / "reports" / "phase8_bibliography.json"


def _ascii(s: str) -> str:
    """Transliterate accented characters, e.g. 'Maenpaa' from 'Mäenpää'.

    The extraction table is valid UTF-8. An earlier version of this function
    tried a cp1252 -> utf-8 round trip to repair mojibake and destroyed every
    accented surname instead ('Mäenpää' -> 'Menp'), because re-encoding correct
    text to cp1252 produces bytes that are not valid UTF-8. Decomposing and
    dropping the combining marks is the correct operation and is a no-op on text
    that was already ASCII.
    """
    if not s:
        return ""
    return unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode()


def _surname(first_author: str) -> str:
    return _ascii(first_author).split(",")[0].strip().lower()


def _slug(first_author: str, year: str, taken: set) -> str:
    base = re.sub(r"[^a-z]", "", _surname(first_author)) or "anon"
    if base not in taken:
        return base
    for suffix in "abcdefghijklmnopqrstuvwxyz":
        cand = f"{base}{_ascii(year)[-2:]}{suffix}" if f"{base}{_ascii(year)[-2:]}" in taken \
            else f"{base}{_ascii(year)[-2:]}"
        if cand not in taken:
            return cand
    raise RuntimeError(f"cannot allocate a unique key for {first_author} {year}")


def _format(rec: dict) -> str:
    """Prefer the committed APA string; fall back to assembling the fields."""
    apa = _ascii(rec.get("apa", "")).strip()
    if apa:
        return re.sub(r"\s+", " ", apa.replace("*", ""))
    bits = [f"{_ascii(rec.get('authors_full', ''))} ({_ascii(rec.get('year',''))}).",
            f"{_ascii(rec.get('title','')).rstrip('.')}.",
            f"{_ascii(rec.get('journal',''))}"]
    if rec.get("volume"):
        bits.append(f", {_ascii(rec['volume'])}")
    if rec.get("pages"):
        bits.append(f", {_ascii(rec['pages'])}")
    out = "".join(bits).rstrip(",. ") + "."
    if rec.get("doi"):
        out += f" https://doi.org/{_ascii(rec['doi'])}"
    return re.sub(r"\s+", " ", out)


def _load() -> list[dict]:
    entries: list[dict] = []

    with open(EXTRACTION, encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            entries.append({
                "set": "review",
                "theme": _ascii(row.get("theme", "")),
                "theme_code": _ascii(row.get("theme", ""))[:2],
                "relevance": row.get("relevance", ""),
                "pmid": row.get("pmid", ""),
                "year": row.get("year", ""),
                "first_author": _ascii(row.get("first_author", "")),
                "title": _ascii(row.get("title", "")),
                "journal": _ascii(row.get("journal", "")),
                "doi": row.get("doi", ""),
                "apa": row.get("apa", ""),
                "volume": row.get("volume", ""),
                "pages": row.get("pages", ""),
                "note": _ascii(row.get("note", "")),
            })

    add = json.loads(ADDITIONAL.read_text(encoding="utf-8"))
    for rec in add["references"]:
        e = {k: rec.get(k, "") for k in
             ("pmid", "year", "first_author", "title", "journal", "doi", "apa",
              "volume", "pages", "note")}
        e["set"] = "additional"
        e["subset"] = rec.get("set", "")
        e["theme"] = ""
        e["theme_code"] = ""
        e["relevance"] = ""
        e["explicit_key"] = rec["key"]
        entries.append(e)

    # One stable order for the whole list: surname, then year.
    entries.sort(key=lambda e: (_surname(e["first_author"]), _ascii(e["year"])))

    taken: set = set()
    for i, e in enumerate(entries, start=1):
        key = e.get("explicit_key") or _slug(e["first_author"], e["year"], taken)
        taken.add(key)
        e["key"] = key
        e["n"] = i
        e["formatted"] = _format(e)
    return entries


_ENTRIES = _load()
_BY_KEY = {e["key"]: e for e in _ENTRIES}
_CITED: set = set()


def cite(*keys: str) -> str:
    """In-text marker for one or more references, e.g. '[12, 26]'."""
    ns = []
    for k in keys:
        e = _BY_KEY.get(k)
        if e is None:
            raise KeyError(
                f"unknown citation key {k!r}. Available keys include: "
                f"{', '.join(sorted(_BY_KEY)[:12])} ...")
        _CITED.add(k)
        ns.append(e["n"])
    return "[" + ", ".join(str(n) for n in sorted(set(ns))) + "]"


def cite_theme(code: str, limit: int | None = None, min_relevance: float = 0.0) -> str:
    """Marker spanning a themed search, highest-relevance first."""
    pool = [e for e in _ENTRIES if e["theme_code"] == code]
    if min_relevance:
        pool = [e for e in pool
                if e["relevance"] and float(e["relevance"]) >= min_relevance]
    pool.sort(key=lambda e: (-(float(e["relevance"]) if e["relevance"] else 0),
                             e["n"]))
    if limit:
        pool = pool[:limit]
    if not pool:
        raise KeyError(f"no references for theme {code!r}")
    for e in pool:
        _CITED.add(e["key"])
    return "[" + ", ".join(str(n) for n in sorted(e["n"] for e in pool)) + "]"


def key_for_theme(code: str, n: int = 1, min_relevance: float = 0.0) -> list[str]:
    pool = [e for e in _ENTRIES if e["theme_code"] == code]
    if min_relevance:
        pool = [e for e in pool
                if e["relevance"] and float(e["relevance"]) >= min_relevance]
    pool.sort(key=lambda e: (-(float(e["relevance"]) if e["relevance"] else 0),
                             e["n"]))
    return [e["key"] for e in pool[:n]]


def references() -> list[dict]:
    return list(_ENTRIES)


def cited_keys() -> set:
    return set(_CITED)


def coverage() -> dict:
    rev = [e for e in _ENTRIES if e["set"] == "review"]
    add = [e for e in _ENTRIES if e["set"] == "additional"]
    return {
        "n_total": len(_ENTRIES),
        "n_review_set": len(rev),
        "n_additional_set": len(add),
        "n_cited": len(_CITED),
        "n_review_cited": sum(1 for e in rev if e["key"] in _CITED),
        "n_additional_cited": sum(1 for e in add if e["key"] in _CITED),
        "uncited_review_keys": sorted(e["key"] for e in rev
                                      if e["key"] not in _CITED),
    }


def main() -> None:
    payload = {
        "generated": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "phase": "8 / P8.3 bibliography",
        "sources": {
            "review": "literature_v2/extraction_table.csv (PRISMA-included studies)",
            "additional": "literature_v2/additional_references.json",
        },
        "principle": (
            "no reference is typed into the document. The builder calls "
            "cite(key) and the number is resolved here, so the in-text markers "
            "and the reference list cannot disagree and renumbering is "
            "automatic."),
        "n_total": len(_ENTRIES),
        "n_review_set": sum(1 for e in _ENTRIES if e["set"] == "review"),
        "n_additional_set": sum(1 for e in _ENTRIES if e["set"] == "additional"),
        "entries": [
            {k: e[k] for k in ("n", "key", "set", "theme_code", "relevance",
                               "year", "first_author", "title", "journal",
                               "doi", "pmid", "formatted")}
            for e in _ENTRIES],
    }
    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text(json.dumps(payload, indent=1), encoding="utf-8")
    print(f"[P8.3] {payload['n_total']} references "
          f"({payload['n_review_set']} review + "
          f"{payload['n_additional_set']} additional)")
    for e in _ENTRIES[:3]:
        print(f"   [{e['n']}] {e['key']:14s} {e['formatted'][:88]}")
    print(f"[P8.3] wrote {OUT.name}")


if __name__ == "__main__":
    main()
