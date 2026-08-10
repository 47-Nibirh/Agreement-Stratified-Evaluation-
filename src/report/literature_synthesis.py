"""
Phase 8 / P8.4 -- turn the review chapter's assertions into counted facts.

The review chapter previously said, without a number attached, that "the four
commonest omissions in this literature are missing external validation,
incomplete population description, unexamined ground-truth construction, and
absent calibration reporting". That is the load-bearing claim of the whole
thesis -- it is the gap the design occupies -- and it was an assertion.

This script counts it instead, by screening the title and abstract of every
included study for each reporting dimension.

WHAT THE COUNT IS, EXACTLY. It is a MENTION count, not a practice count: it
records whether a study's title or abstract mentions a dimension at all. That
makes every figure an UPPER BOUND on the fraction of studies that actually
report the thing -- a paper can mention calibration and not report it, but a
paper that never mentions it in its abstract is very unlikely to have made it a
reported endpoint. The bound is the useful direction: if only a small minority
even mention calibration, then at most that minority report it, and the gap
claim follows from the upper bound rather than from an assertion.

TWO LIMITATIONS, DECLARED. 14 of the 82 included studies ship no abstract in the
MEDLINE record, and those are reported as a separate denominator rather than
silently counted as absences. And an abstract-level screen is not a full-text
appraisal; it is reproducible and cheap, which a full-text appraisal of 82
papers by one undergraduate is not. Both are stated in the chapter.

Emits reports/phase8_lit_synthesis.json. No GPU.

Run:  python src/report/literature_synthesis.py
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
OUT = ROOT / "reports" / "phase8_lit_synthesis.json"

# Each dimension is a set of case-insensitive patterns. They are deliberately
# generous: a generous pattern makes the MENTION count larger, which makes the
# upper bound weaker, which makes the gap claim harder to sustain rather than
# easier. Erring toward over-counting is the conservative direction here.
DIMENSIONS = {
    "external_validation": [
        r"external(ly)? validat", r"independent (cohort|dataset|test set|centre|center)",
        r"multi-?cent(re|er)", r"external (cohort|dataset|test set)",
        r"temporal validation", r"out-of-distribution", r"domain shift",
        r"dataset shift", r"generalis(ability|ation)", r"generaliz(ability|ation)",
    ],
    "calibration": [
        r"calibrat", r"brier", r"reliability diagram",
        r"expected calibration error", r"\bECE\b",
    ],
    "ground_truth_construction": [
        r"inter-?observer", r"inter-?rater", r"multi-?annotator", r"multi-?rater",
        r"annotator", r"consensus", r"adjudicat", r"ground[- ]truth",
        r"\bkappa\b", r"label noise", r"noisy label", r"reference standard",
    ],
    "population_description": [
        r"\bage\b", r"\bsex\b", r"\bgender\b", r"demographic",
        r"patient characteristic", r"baseline characteristic",
    ],
    "uncertainty": [
        r"uncertaint", r"predictive entropy", r"bayesian", r"ensembl",
        r"conformal", r"monte[- ]carlo dropout", r"epistemic", r"aleatoric",
    ],
}

DIMENSION_LABEL = {
    "external_validation": "External validation or shift",
    "calibration": "Calibration of predicted probability",
    "ground_truth_construction": "How the reference standard was built",
    "population_description": "Population description (age / sex)",
    "uncertainty": "Predictive uncertainty",
}

# Which of these the thesis design addresses, and where.
ADDRESSED = {
    "external_validation": "Chapter 7 -- two external corpora, no adaptation",
    "calibration": "Chapters 5 and 6 -- ECE by stratum as a primary endpoint",
    "ground_truth_construction": "Chapters 3 and 5 -- the whole design",
    "population_description": "NOT ADDRESSED -- the corpus ships no age or sex",
    "uncertainty": "Chapters 6 and 8 -- soft targets and selective prediction",
}

# How much weight an abstract-level screen can bear, per dimension. This is not
# decoration: the population-description count comes out at exactly zero, and a
# zero reported without this caveat would be a considerably stronger claim than
# the evidence supports.
PROXY_QUALITY = {
    "external_validation": (
        "GOOD -- external validation is a headline claim and is stated in the "
        "abstract when it is done."),
    "calibration": (
        "GOOD -- calibration is reported as a result, and a study reporting it "
        "as an endpoint names it in the abstract."),
    "ground_truth_construction": (
        "MODERATE -- multi-reader designs are usually named, but a study that "
        "collapsed several readers to a consensus in one sentence of its "
        "methods may not mention it in the abstract at all."),
    "population_description": (
        "WEAK -- this is the one dimension where the proxy should not be "
        "trusted as an upper bound on practice. Cohort demographics live in a "
        "baseline-characteristics table in the full text, not in the abstract, "
        "so a study can describe its population fully and still never say "
        "'age' or 'sex' in the abstract. The count of zero should be read as "
        "'demographics are not a headline in this literature', not as 'no "
        "study describes its population'."),
    "uncertainty": (
        "GOOD -- uncertainty quantification is a method claim and is named."),
}


def _ascii(s: str) -> str:
    return unicodedata.normalize("NFKD", s or "").encode("ascii", "ignore").decode()


def main() -> None:
    t0 = time.time()
    with open(LIT / "extraction_table.csv", encoding="utf-8-sig") as f:
        rows = list(csv.DictReader(f))

    compiled = {d: [re.compile(p, re.I) for p in pats]
                for d, pats in DIMENSIONS.items()}

    with_abs = [r for r in rows if r["abstract"].strip()]
    no_abs = [r for r in rows if not r["abstract"].strip()]

    per_study = []
    for r in rows:
        text = _ascii(f"{r['title']} {r['abstract']}")
        hits = {d: bool(any(p.search(text) for p in ps))
                for d, ps in compiled.items()}
        per_study.append({
            "pmid": r["pmid"], "year": r["year"],
            "first_author": _ascii(r["first_author"]),
            "theme_code": _ascii(r["theme"])[:2],
            "has_abstract": bool(r["abstract"].strip()),
            "mentions": hits,
        })

    scored = [p for p in per_study if p["has_abstract"]]
    dim_counts = {}
    for d in DIMENSIONS:
        n = sum(1 for p in scored if p["mentions"][d])
        dim_counts[d] = {
            "label": DIMENSION_LABEL[d],
            "n_mentioning": n,
            "n_scored": len(scored),
            "pct_mentioning": round(100.0 * n / len(scored), 1),
            "pct_not_mentioning": round(100.0 * (len(scored) - n) / len(scored), 1),
            "addressed_by_this_thesis": ADDRESSED[d],
            "proxy_quality": PROXY_QUALITY[d],
        }

    # Themes, from the committed theme assignment rather than from the text.
    themes: dict[str, dict] = {}
    for r in rows:
        code = _ascii(r["theme"])[:2]
        themes.setdefault(code, {"code": code, "label": _ascii(r["theme"]),
                                 "n": 0, "years": []})
        themes[code]["n"] += 1
        if r["year"].strip().isdigit():
            themes[code]["years"].append(int(r["year"]))
    for t in themes.values():
        ys = t.pop("years")
        t["median_year"] = int(sorted(ys)[len(ys) // 2]) if ys else None

    years = [int(r["year"]) for r in rows if r["year"].strip().isdigit()]
    n_recent = sum(1 for y in years if y >= 2020)

    # The intersection that defines the gap: studies that both build a reference
    # standard from several readers AND say anything about calibration.
    both = sum(1 for p in scored
               if p["mentions"]["ground_truth_construction"]
               and p["mentions"]["calibration"])
    gt_only = sum(1 for p in scored if p["mentions"]["ground_truth_construction"])

    out = {
        "generated": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "phase": "8 / P8.4 literature synthesis",
        "method": (
            "case-insensitive regular-expression screen of title and abstract "
            "for each reporting dimension. Counts are MENTION counts and are "
            "therefore upper bounds on the fraction of studies that report the "
            "dimension. Patterns are deliberately generous, which weakens the "
            "bound rather than strengthening it."),
        "limitations": [
            f"{len(no_abs)} of {len(rows)} included studies ship no abstract in "
            f"the MEDLINE record and are excluded from the denominator rather "
            f"than counted as absences.",
            "an abstract-level screen is not a full-text appraisal; a study may "
            "mention a dimension without reporting it, so every count is an "
            "upper bound.",
        ],
        "n_included": len(rows),
        "n_with_abstract": len(with_abs),
        "n_without_abstract": len(no_abs),
        "n_published_2020_or_later": n_recent,
        "pct_published_2020_or_later": round(100.0 * n_recent / len(years), 1),
        "themes": dict(sorted(themes.items())),
        "dimensions": dict(sorted(dim_counts.items(),
                                  key=lambda kv: kv[1]["pct_mentioning"])),
        "gap_intersection": {
            "n_mentioning_ground_truth_construction": gt_only,
            "n_also_mentioning_calibration": both,
            "pct_of_those": round(100.0 * both / gt_only, 1) if gt_only else None,
            "reading": (
                "of the studies that engage with how the reference standard was "
                "built, this is the fraction that also say anything about "
                "whether predicted probabilities are trustworthy. It is the "
                "intersection this thesis occupies."),
        },
        "per_study": per_study,
        "runtime_sec": round(time.time() - t0, 2),
    }
    OUT.write_text(json.dumps(out, indent=1), encoding="utf-8")

    print(f"[P8.4] {len(rows)} included, {len(with_abs)} with abstracts")
    for d, v in out["dimensions"].items():
        print(f"       {v['label']:42s} {v['n_mentioning']:3d}/{v['n_scored']} "
              f"= {v['pct_mentioning']:5.1f}% mention")
    g = out["gap_intersection"]
    print(f"       intersection: {g['n_also_mentioning_calibration']}/"
          f"{g['n_mentioning_ground_truth_construction']} "
          f"({g['pct_of_those']}%) of reference-standard studies mention "
          f"calibration")
    print(f"[P8.4] wrote {OUT.name} in {out['runtime_sec']}s")


if __name__ == "__main__":
    main()
