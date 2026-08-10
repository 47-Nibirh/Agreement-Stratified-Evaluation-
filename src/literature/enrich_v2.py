"""
Phase 1 (v2) - Reference enrichment.

Reuses the PubMed enrichment and APA-7 formatting logic already validated in
`enrich.py` (including the DOI-parsing fix: the DOI must be read from
./PubmedData/ArticleIdList/ArticleId, never from a bare .//ArticleId, which
also matches the article's own <ReferenceList>) and points it at the revised
`literature_v2/` extraction table.

Run:  python src/literature/enrich_v2.py
"""

from __future__ import annotations

from pathlib import Path

import enrich  # same package directory

ROOT = Path(__file__).resolve().parents[2]

if __name__ == "__main__":
    enrich.LIT = ROOT / "literature_v2"
    enrich.main()
