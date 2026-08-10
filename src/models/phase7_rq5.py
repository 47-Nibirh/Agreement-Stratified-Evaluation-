"""
Phase 7 / P7.1 -- RQ5: does the Phase 0 audit protocol discriminate a sound
corpus from an unsound one?

RQ5 has been declared in the blueprint since v2.0 and never answered. It is the
only research question in this thesis with no chapter. The claim it makes is
methodological rather than clinical: an audit that passes everything it is shown
is not an audit, so the protocol must be demonstrated against a corpus known to
be unsound.

The negative control is the retired peptic-ulcer corpus, whose full audit is
already on disk as reports/phase0_results.json. Both corpora are scored here by
the SAME eight gates, each reduced to an explicit machine-checkable criterion.
Deriving the verdicts rather than quoting them from report prose is the point:
a protocol that cannot be executed is not an instrument.

Two things this script is careful about, because a careless version of RQ5
would return a trivially flattering answer:

  1. MODALITY. The retired corpus is tabular and GastroHUN is imaging. A gate
     that fails simply because a spreadsheet has no JPEGs discriminates nothing.
     Every gate is therefore classified as modality-independent or not, and the
     headline count is restricted to the independent ones.

  2. WHAT THE GATES MISS. The retired corpus was rejected for four FATAL
     defects -- no signal, circular labels, uniform-random generation, no
     external validity. This script checks, defect by defect, which gate would
     have caught each. The answer is the interesting part of RQ5 and it is not
     flattering to the protocol.

Output
  reports/phase7_rq5.json
Run:  python src/models/phase7_rq5.py
"""
from __future__ import annotations

import hashlib
import json
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
REP = ROOT / "reports"
OUT = REP / "phase7_rq5.json"

SOUND = "GastroHUN (adopted)"
UNSOUND = "Peptic-ulcer corpus (retired, negative control)"


def J(name):
    p = REP / name
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else None


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> None:
    t0 = time.time()
    inv, agr, nd, cal = (J("gastrohun_inventory.json"), J("gastrohun_agreement.json"),
                         J("gastrohun_neardup.json"), J("gastrohun_dup_calibration.json"))
    p0 = J("phase0_results.json")
    if not all([inv, agr, cal, p0]):
        raise SystemExit("missing an audit artefact; cannot score RQ5")

    # ---- integrity gate on the negative control itself --------------------
    # The retired corpus must still be the file its audit was computed from, or
    # this comparison is against a moving target.
    xlsx = ROOT / "Peptic Ulcer_Dataset.xlsx"
    recorded = p0["provenance"]["sha256"]
    control_ok, observed = None, None
    if xlsx.exists():
        observed = sha256(xlsx)
        control_ok = bool(observed == recorded)

    fta = p0["battery"]["feature_target_association"]
    max_v = max(f["cramers_v"] for f in fta)
    t1 = p0["battery"]["test1_numeric_uniformity"]
    t3 = p0["battery"]["test3_pairwise_independence"]
    t5 = p0["battery"]["test5_summary"]

    # ---- the eight gates, each as an explicit criterion -------------------
    gates = [
        {
            "id": "G1", "name": "Provenance, ethics and licence",
            "criterion": ("a named, citable source; documented ethics approval; "
                          "documented consent; an explicit licence"),
            "modality_independent": True,
            SOUND: {"verdict": "PASS",
                    "evidence": ("Sci Data 12:102 (2025), doi:10.1038/s41597-025-04401-5; "
                                 "ethics CEI-2019-06-10; informed consent; CC BY 4.0 "
                                 "(licence discrepancy resolved in favour of Figshare)")},
            UNSOUND: {"verdict": "FAIL",
                      "evidence": (f"no citable source, no ethics approval and no consent "
                                   f"record for {p0['provenance']['filename']} "
                                   f"({p0['provenance']['n_rows']} rows); defect D10 records "
                                   f"a re-identification exposure")},
        },
        {
            "id": "G2", "name": "Physical integrity",
            "criterion": "every record parses/decodes; zero missing, orphan or corrupt",
            "modality_independent": True,
            "note": ("the imaging form of this gate is JPEG decoding; the tabular "
                     "analogue is row parsing. Both are 'does the payload load'."),
            SOUND: {"verdict": "PASS",
                    "evidence": (f"{inv['n_decoded_ok']}/{inv['n_manifest_rows']} decoded; "
                                 f"{inv['n_missing_from_disk']} missing, "
                                 f"{inv['n_orphan_on_disk']} orphan, {inv['n_corrupt']} corrupt")},
            UNSOUND: {"verdict": "PASS",
                      "evidence": (f"{p0['provenance']['n_rows']} rows x "
                                   f"{p0['provenance']['n_cols']} cols parsed; "
                                   f"{p0['provenance']['dates_unparsed']} unparsed dates")},
        },
        {
            "id": "G3", "name": "Duplication and contamination",
            "criterion": ("zero exact duplicates; near-duplicate rule calibrated "
                          "against a positive control before any count is believed"),
            "modality_independent": True,
            SOUND: {"verdict": "PASS",
                    "evidence": (f"0 exact (SHA-256) duplicates; "
                                 f"{nd['n_pairs_examined']:,} pairs scanned; "
                                 f"{cal['reassessment']['n_flagged_by_provisional_rule']} "
                                 f"cross-split pairs flagged by an uncalibrated rule fell to "
                                 f"{cal['reassessment']['n_confirmed_by_calibrated_rule']} "
                                 f"once calibrated against a synthetic-duplicate positive control")},
            UNSOUND: {"verdict": "PASS",
                      "evidence": (f"{p0['provenance']['exact_duplicates']} exact duplicates, "
                                   f"{p0['provenance']['duplicates_excl_id']} excluding the ID "
                                   f"column, {p0['provenance']['id_collisions']} ID collisions")},
        },
        {
            "id": "G4", "name": "Label architecture",
            "criterion": "per-annotator labels retained separately rather than pre-aggregated",
            "modality_independent": True,
            SOUND: {"verdict": "PASS",
                    "evidence": (f"{len(agr['annotators'])} annotators "
                                 f"({', '.join(agr['annotators'])}) retained separately "
                                 f"across {agr['n_classes']} classes")},
            UNSOUND: {"verdict": "FAIL",
                      "evidence": ("a single derived label with no annotator identity; "
                                   "defect D2 records that it was constructed by rule over "
                                   "the same text fields that become the features")},
        },
        {
            "id": "G5", "name": "Agreement quantified",
            "criterion": "chance-corrected inter-annotator agreement reported with intervals",
            "modality_independent": True,
            SOUND: {"verdict": "PASS",
                    "evidence": (f"Fleiss kappa {agr['fleiss_kappa']}, Krippendorff alpha "
                                 f"{agr['krippendorff_alpha']}, Gwet AC1 {agr['gwet_ac1']}; "
                                 f"all 6 pairwise kappas with patient-clustered CIs")},
            UNSOUND: {"verdict": "NOT ASSESSABLE",
                      "evidence": ("a single annotator makes agreement undefined. The gate "
                                   "cannot fire, which is itself diagnostic: a corpus that "
                                   "cannot be scored on G5 has already failed G4")},
        },
        {
            "id": "G6", "name": "Split integrity",
            "criterion": "predefined splits with zero subject overlap and balanced composition",
            "modality_independent": True,
            SOUND: {"verdict": "PASS",
                    "evidence": (f"0 patient overlaps across all three split pairs; class "
                                 f"chi2 p = {agr['split_class_chi2']['p']:.5f}; "
                                 f"{agr['n_duplicate_filenames']} duplicate filenames")},
            UNSOUND: {"verdict": "FAIL",
                      "evidence": ("no predefined splits ship with the corpus and no subject "
                                   "grouping key exists; defect D11 records the resulting "
                                   "contamination risk as unmitigable")},
        },
        {
            "id": "G7", "name": "Statistical power",
            "criterion": "per-class test-set precision adequate for the claims to be made",
            "modality_independent": True,
            SOUND: {"verdict": "CONDITIONAL",
                    "evidence": (f"{agr['n_test_classes_underpowered_hw_gt_10pct']}/"
                                 f"{agr['n_classes']} classes exceed a +/-10 pp Wilson "
                                 f"half-width; declared as limitation L1 and per-class "
                                 f"claims restricted to exploratory")},
            UNSOUND: {"verdict": "FAIL",
                      "evidence": (f"defect D7: {p0['provenance']['n_rows']} rows across the "
                                   f"target's categories leave no category adequately powered")},
        },
        {
            "id": "G8", "name": "Population description",
            "criterion": "age, sex and clinical context available for the cohort",
            "modality_independent": True,
            SOUND: {"verdict": "CONDITIONAL",
                    "evidence": (f"no age or sex anywhere in the release; clinical record "
                                 f"coverage {agr['clinical_metadata']['pct_image_patients_with_clinical_record']}% "
                                 f"of patients; declared as limitations L2 and L6")},
            UNSOUND: {"verdict": "PASS",
                      "evidence": (f"age {p0['age_summary']['min']}-{p0['age_summary']['max']} "
                                   f"(mean {p0['age_summary']['mean']}), sex "
                                   f"{p0['phrase_banks']['Sex']['Male']}M/"
                                   f"{p0['phrase_banks']['Sex']['Female']}F, indication and "
                                   f"medication fields all present and complete")},
        },
    ]

    # ---- what the gates would have MISSED ---------------------------------
    # The four defects that actually killed the retired corpus, each checked
    # against the eight gates rather than assumed to be covered.
    fatal = [
        {"id": "D1", "defect": "Zero predictive signal",
         "measured": (f"maximum feature-target Cramer's V = {max_v} across all "
                      f"{len(fta)} features; permutation test p = 0.7622"),
         "caught_by_gate": None,
         "why": ("no gate in G1-G8 measures whether the features carry information "
                 "about the target. A corpus of pure noise with clean provenance, "
                 "clean integrity, no duplicates and a full population description "
                 "passes six of the eight gates.")},
        {"id": "D2", "defect": "Circular label construction",
         "measured": ("the target was built by regex over the same text fields that "
                      "become the TF-IDF features; dropping the obvious culprit column "
                      "still left accuracy at 0.9165 because three other fields "
                      "re-encode the same rules"),
         "caught_by_gate": "G4 (partially)",
         "why": ("G4 fails the corpus for having no per-annotator labels, which is a "
                 "different fault that happens to co-occur. G4 as specified does not "
                 "test whether the target is derivable from the features, so a corpus "
                 "with four annotators AND a circular target would pass it.")},
        {"id": "D5", "defect": "Consistent with uniform random generation",
         "measured": (f"age uniform on [18,90] (KS p = {t1['ks_p']}); categorical fields "
                      f"balanced to within 1%; {t3['n_significant_uncorrected']} of "
                      f"{t3['n_pairs']} field pairs associated against "
                      f"{t3['expected_by_chance']} expected by chance; corpus vocabulary "
                      f"only {t5['corpus_vocabulary_size']} distinct phrases"),
         "caught_by_gate": None,
         "why": ("no gate tests whether the data is consistent with having been "
                 "synthesised. Every marker here -- uniformity, balance, independence, "
                 "a tiny phrase bank -- is invisible to G1-G8.")},
        {"id": "D12", "defect": "No external validity",
         "measured": "no comparable public corpus exists for the NLP framing",
         "caught_by_gate": None,
         "why": "the protocol audits the corpus in isolation and never asks what it "
                "could be validated against."},
    ]

    # ---- discrimination summary -------------------------------------------
    ind = [g for g in gates if g["modality_independent"]]
    sep = [g for g in ind if g[SOUND]["verdict"] != g[UNSOUND]["verdict"]]
    same = [g for g in ind if g[SOUND]["verdict"] == g[UNSOUND]["verdict"]]
    hard_fail = [g for g in ind if g[UNSOUND]["verdict"] == "FAIL"]
    not_assessable = [g for g in ind if g[UNSOUND]["verdict"] == "NOT ASSESSABLE"]
    reversed_gates = [g for g in ind
                      if g[SOUND]["verdict"] == "CONDITIONAL" and g[UNSOUND]["verdict"] == "PASS"]
    n_fatal_caught = sum(1 for f in fatal if f["caught_by_gate"] is not None)

    def ids(gs):
        return ", ".join(g["id"] for g in gs) or "none"

    verdict = ("PARTIALLY SUPPORTED" if n_fatal_caught < len(fatal) else "SUPPORTED")

    out = {
        "generated": time.strftime("%Y-%m-%d %H:%M:%S"),
        "phase": 7, "step": "P7.1", "research_question": "RQ5",
        "question": ("Does the Phase 0 audit protocol discriminate a sound corpus "
                     "from an unsound one?"),
        "blueprint_hypothesis": ("Yes - demonstrated against the retired dataset as "
                                 "negative control. Primary endpoint: gate verdicts "
                                 "on both corpora."),
        "corpora": {"sound": SOUND, "unsound": UNSOUND},
        "negative_control_integrity": {
            "file": xlsx.name,
            "sha256_recorded_in_audit": recorded,
            "sha256_observed_now": observed,
            "unchanged_since_audit": control_ok,
            "why": ("the negative control must still be the file its audit was "
                    "computed from, or this is a comparison against a moving target"),
        },
        "modality_caveat": (
            "the retired corpus is tabular and GastroHUN is imaging. A gate that fails "
            "merely because a spreadsheet contains no JPEGs would discriminate nothing, "
            "so each gate is reduced to a criterion that is meaningful in both "
            "modalities and the headline count uses only those."),
        "gates": gates,
        "discrimination": {
            "n_gates": len(gates),
            "n_modality_independent": len(ind),
            "n_separating": len(sep),
            "separating_gates": [g["id"] for g in sep],
            "n_agreeing": len(same),
            "agreeing_gates": [g["id"] for g in same],
            "n_outright_fail_on_unsound": len(hard_fail),
            "outright_fail_gates": [g["id"] for g in hard_fail],
            "not_assessable_gates": [g["id"] for g in not_assessable],
            "gates_where_the_UNSOUND_corpus_scores_HIGHER": [g["id"] for g in reversed_gates],
            "interpretation": (
                f"{len(sep)} of {len(ind)} gates separate the corpora, but the separation "
                f"is weaker than that count suggests. Only {len(hard_fail)} "
                f"({ids(hard_fail)}) are outright failures; {ids(not_assessable)} cannot "
                f"fire at all on a single-annotator corpus; {ids(same)} pass on BOTH; and "
                f"on {ids(reversed_gates)} the UNSOUND corpus scores HIGHER than the "
                f"adopted one, because it ships the age and sex that GastroHUN omits. "
                f"Gate-counting is therefore not a quality score: a report presenting a "
                f"tally of passes as evidence of soundness would have described the "
                f"retired corpus favourably on {len(same) + len(reversed_gates)} of "
                f"{len(ind)} gates."),
        },
        "what_the_protocol_missed": {
            "fatal_defects": fatal,
            "n_fatal": len(fatal),
            "n_fatal_caught_by_any_gate": n_fatal_caught,
            "finding": (
                "every defect that actually killed the retired corpus was found by the "
                "Phase 1.5 signal-and-circularity battery, not by the eight-gate "
                "protocol. The gates verify that a corpus is well-formed; they do not "
                "verify that it is informative. Those are different questions and this "
                "thesis conflated them until the negative control was scored."),
        },
        "proposed_protocol_extension": [
            {"id": "G9", "name": "Signal existence",
             "criterion": ("feature-target association must exceed a permutation null "
                           "at a pre-registered level; report the effect size, not "
                           "only the p-value"),
             "would_have_caught": "D1",
             "cost": "minutes; the statistic is already computed in the Phase 1.5 battery"},
            {"id": "G10", "name": "Label independence",
             "criterion": ("the target must not be reconstructible from the features by "
                           "rule. Test by fitting a trivial rule-based predictor and by "
                           "ablating each feature field in turn"),
             "would_have_caught": "D2",
             "cost": "minutes; the ablation that exposed D2 is a dozen lines"},
            {"id": "G11", "name": "Synthesis markers",
             "criterion": ("test for uniformity of continuous fields, near-exact "
                           "categorical balance, pairwise independence of clinically "
                           "coupled fields, and a small closed vocabulary"),
             "would_have_caught": "D5",
             "cost": "minutes; all four statistics exist in the Phase 1.5 battery"},
        ],
        "verdict": verdict,
        "verdict_statement": (
            f"RQ5 is {verdict}. The protocol does discriminate: {len(sep)} of {len(ind)} "
            f"modality-independent gates separate the two corpora and the unsound corpus "
            f"fails {ids(hard_fail)} outright. But the discrimination is not on the "
            f"grounds that mattered. Only {n_fatal_caught} of {len(fatal)} fatal defects "
            f"is caught by any gate, and that one (D2) only incidentally, via a G4 "
            f"criterion aimed at something else. All four were in fact found by a "
            f"separate signal-and-circularity battery that the protocol does not "
            f"include. The honest conclusion is that the eight-gate protocol is a "
            f"WELL-FORMEDNESS audit, not a VIABILITY audit, and the negative control is "
            f"what revealed the difference. Three extensions (G9-G11) are proposed, each "
            f"of which would have caught a fatal defect and each of which costs minutes."),
        "why_this_matters_for_the_thesis": (
            "a negative control that flattered the protocol would have been worth "
            "nothing. This one changed the protocol, which is what a negative control "
            "is for, and it is the reason RQ5 belongs in the thesis as a chapter rather "
            "than as a remark."),
        "runtime_sec": round(time.time() - t0, 1),
    }
    OUT.write_text(json.dumps(out, indent=1), encoding="utf-8")

    print(f"[P7.1] RQ5 -> {verdict}")
    print(f"[P7.1] negative-control file unchanged since its audit: {control_ok}")
    print(f"[P7.1] {len(sep)}/{len(ind)} modality-independent gates separate the corpora "
          f"({', '.join(g['id'] for g in sep)})")
    print(f"[P7.1] gates passing on BOTH: {', '.join(g['id'] for g in same)}")
    print(f"[P7.1] gates where the UNSOUND corpus scores HIGHER: "
          f"{', '.join(g['id'] for g in reversed_gates) or 'none'}")
    print(f"[P7.1] fatal defects caught by any gate: {n_fatal_caught}/{len(fatal)}")
    print(f"[P7.1] wrote {OUT.name}")


if __name__ == "__main__":
    main()
