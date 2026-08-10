"""
Phase 4 report -- shared artefact access, formatting helpers, abbreviations,
appendices and references.

Every helper here reads from reports/phase4_*.json. There is deliberately no
literal result anywhere in this module: the narrative in build_phase4_docx.py
selects its wording from the pre-registered verdict fields, so the document
states whatever the experiment found rather than what the design hoped for.
"""
from __future__ import annotations

import json
from pathlib import Path

from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.shared import Pt

import build_docx as BD
from build_docx import GREY, bullet, callout, h, para, table

ROOT = Path(__file__).resolve().parents[2]
REP = ROOT / "reports"


def J(name, default=None):
    p = REP / name
    if not p.exists():
        return default
    return json.loads(p.read_text(encoding="utf-8"))


PRE = J("phase4_prereg.json")
COH = J("phase4_cohort.json")
CACHE = J("phase4_cache_gate.json")
DIST = J("phase4_distance_matrix.json")
PROBE = J("phase4_probe.json")
MET = J("phase4_stratified_metrics.json")
CAL = J("phase4_calibration.json")
UNC = J("phase4_uncertainty.json")
STR = J("phase4_structure_eval.json")
LOAO = J("phase4_loao.json")
INFER = J("phase4_infer_gate.json")
AMD = J("phase4_amendment.json")

TIERS = ["S-unanimous", "S-majority", "S-plurality", "S-no-majority"]
POOLED = "S-contested (pooled)"
STRATA = TIERS + [POOLED]
TIER_LABEL = {"S-unanimous": "S-unanimous (4/4)", "S-majority": "S-majority (3/4)",
              "S-plurality": "S-plurality (2-1-1)",
              "S-no-majority": "S-no-majority (2-2 / 1-1-1-1)",
              POOLED: "S-contested (all three pooled)"}
CFG_LABEL = {"C0": "C0 — hard label, 4/4 cohort (Phase 2 reference)",
             "C1": "C1 — hard majority label, extended cohort",
             "C2": "C2 — vote proportions",
             "C3": "C3 — hard label + mass-matched smoothing (control)",
             "C4": "C4 — vote proportions + anatomical penalty"}


def CFGS():
    return (MET or {}).get("configurations_evaluated", [])


def runs():
    out = {}
    for c in ("C1", "C2", "C3", "C4"):
        for s in (1, 2, 3):
            r = J(f"phase4_run_{c}_seed{s}.json")
            if r:
                out[(c, s)] = r
    for s in (1, 2, 3):
        r = J(f"phase2_run_seed{s}.json")
        if r:
            out[("C0", s)] = r
    return out


def pc(x, d=2):
    return f"{100 * x:.{d}f}"


def ci(pair, stratum=POOLED, src=None):
    """'+3.21 points (95% CI +1.04 to +5.38)' for a contrast in phase4_stratified_metrics."""
    src = src or MET
    d = src["contrasts"][pair]["by_stratum"][stratum]
    lo, hi = d["ci95_points_3seed_mean"]
    return (f"{d['diff_points_3seed_mean']:+.2f} points "
            f"(95% CI {lo:+.2f} to {hi:+.2f})")


def cid(pair, stratum=POOLED):
    """Same, for the anatomical-distance contrasts (not in points)."""
    d = STR["contrasts"][pair][stratum]
    lo, hi = d["ci95_3seed_mean"]
    return (f"{d['delta_distance_3seed_mean']:+.4f} "
            f"(95% CI {lo:+.4f} to {hi:+.4f})")


def cie(pair, stratum=POOLED):
    """Same, for the paired delta-ECE contrasts."""
    d = CAL["contrasts"][pair][stratum]
    lo, hi = d["ci95_points_3seed_mean"]
    return (f"{d['delta_ece_points_3seed_mean']:+.2f} points "
            f"(95% CI {lo:+.2f} to {hi:+.2f})")


def excl(pair, stratum=POOLED, src=None):
    src = src or MET
    return src["contrasts"][pair]["by_stratum"][stratum]["excludes_zero"]


def direction(pair, stratum=POOLED):
    d = MET["contrasts"][pair]["by_stratum"][stratum]
    lo, hi = d["ci95_points_3seed_mean"]
    if lo > 0:
        return "an improvement whose interval excludes zero"
    if hi < 0:
        return "a degradation whose interval excludes zero"
    return "a difference the data cannot separate from zero"


# =====================================================================
def abbreviations(doc) -> None:
    h(doc, "Abbreviations", level=1)
    rows = [
        ("AC1", "Gwet's first-order agreement coefficient"),
        ("AdamW", "Adam optimiser with decoupled weight decay"),
        ("AMP", "automatic mixed precision"),
        ("CI", "confidence interval"),
        ("CLAIM", "Checklist for Artificial Intelligence in Medical Imaging"),
        ("C0–C4", "the five Phase 4 training-target configurations"),
        ("ECE / MCE", "expected / maximum calibration error"),
        ("F1", "harmonic mean of precision and recall"),
        ("FG1, FG2", "the two resident annotators (Team A)"),
        ("G1, G2", "the two gastroenterologist annotators (Team B)"),
        ("LOAO", "leave-one-annotator-out"),
        ("MC", "Monte Carlo"),
        ("MC-SD", "Monte Carlo stochastic depth"),
        ("PRISMA", "Preferred Reporting Items for Systematic Reviews and Meta-Analyses"),
        ("RQ", "research question"),
        ("SSS", "Systematic Screening protocol for the Stomach"),
        ("STARD-AI", "Standards for Reporting Diagnostic accuracy studies, AI extension"),
        ("TRIPOD+AI", "Transparent Reporting of a multivariable prediction model, AI extension"),
        ("VRAM", "video memory"),
    ]
    table(doc, ["Abbreviation", "Expansion"], [[a, b] for a, b in rows],
          "Abbreviations used in this report.", widths=[3.2, 12.4], font=8.6)


# =====================================================================
def appendix_a_full_tables(doc) -> None:
    h(doc, "Appendix A. Per-configuration, per-stratum metric tables", level=2)
    if not MET:
        para(doc, "Not available: reports/phase4_stratified_metrics.json has not "
                  "been generated.")
        return
    agg = MET["aggregate_3seed"]
    for st in STRATA:
        table(doc,
              ["Configuration", "n", "Annot.-marg. F1 (%)", "SD over seeds",
               "Mean of per-seed 95% CIs", "% of attainable",
               "Expected acc. (%)", "Any-hit (%)"],
              [[CFG_LABEL[c], str(agg[c][st]["n_images"]),
                pc(agg[c][st]["annotator_marginalized_macro_f1_mean_3seed"]),
                pc(agg[c][st]["annotator_marginalized_macro_f1_sd_3seed"]),
                f"[{pc(agg[c][st]['ci95_mean_of_per_seed_bounds'][0])}, "
                f"{pc(agg[c][st]['ci95_mean_of_per_seed_bounds'][1])}]",
                pc(agg[c][st]["ceiling_normalised_macro_f1_mean_3seed"]),
                pc(agg[c][st]["expected_accuracy_mean_3seed"]),
                pc(agg[c][st]["any_annotator_hit_rate_mean_3seed"])]
               for c in CFGS()],
              f"Full metric set on the {TIER_LABEL[st]} stratum, 3-seed mean. "
              f"Attainable ceiling on this stratum: "
              f"{pc(MET['ceilings'][st]['oracle_marginalized_macro_f1_mean'])}%.",
              font=7.4,
              note="The interval column is the arithmetic mean of the three "
                   "per-seed patient-clustered intervals, not a calibrated "
                   "interval on the 3-seed mean. It describes the typical width of "
                   "a single seed's interval. No verdict is read off this column: "
                   "every pre-registered verdict comes from a paired bootstrap on "
                   "the configuration difference, reported in section 3.2.1.")


def appendix_b_training(doc) -> None:
    h(doc, "Appendix B. Training histories", level=2)
    R = runs()
    if not R:
        para(doc, "Not available: no Phase 4 run manifests found.")
        return
    rows = []
    for (c, s), r in sorted(R.items()):
        rows.append([c, str(s), str(r.get("n_epochs_run", "")),
                     str(r.get("best_epoch_overall", "")),
                     f"{r.get('best_val_macro_f1', 0):.5f}",
                     r.get("stop_reason", ""),
                     f"{r.get('wallclock_sec', 0) / 60:.0f}",
                     f"{r.get('peak_vram_mib', 0):.0f}"])
    table(doc,
          ["Config", "Seed", "Epochs run", "Best epoch", "Best val macro F1",
           "Stop reason", "Wallclock (min)", "Peak VRAM (MiB)"],
          rows,
          "Every Phase 4 training run, plus the three Phase 2 runs reused as C0. "
          "The selection criterion differs between C0 and C1–C4 (793-image "
          "unanimous validation subset versus the 1,103-image extended cohort), "
          "so the 'best val macro F1' column is comparable within C1–C4 but not "
          "against C0.",
          font=7.6,
          note="'epoch_cap' in the stop-reason column means the pre-registered "
               "fine-tuning cap bound before early stopping fired; the cap was "
               "derived from a measured epoch cost and a declared budget "
               "(pre-registration, epoch_cap_derivation). The same cap applies to "
               "every configuration, but it did not bind on them equally: compare "
               "the 'best epoch' column against 'epochs run' per arm, and see "
               "section 4.6 for what the resulting asymmetric censoring does to "
               "the RQ2 contrast.")


def appendix_c_prereg(doc) -> None:
    h(doc, "Appendix C. Pre-registration record", level=2)
    if not PRE:
        para(doc, "Not available.")
        return
    para(doc, f"Frozen at {PRE['frozen_at']}, before the first Phase 4 training run "
              f"and after the cohort, cache, distance matrix and timing probe "
              f"existed. The file is written by src/models/phase4_prereg.py, which "
              f"refuses to overwrite an existing pre-registration. Verbatim "
              f"statement:")
    callout(doc, PRE["statement"], title="Pre-registration statement")
    para(doc, "The full record is reports/phase4_prereg.json. Its operative "
              "clauses are reproduced below.")
    rq = PRE["research_questions"]
    for i, k in enumerate(("RQ2", "RQ3", "RQ4"), start=1):
        h(doc, f"C.{i} {k}", level=3)
        bullet(doc, f"Question: {rq[k]['question']}")
        if "primary_contrast" in rq[k]:
            bullet(doc, f"Primary contrast: {rq[k]['primary_contrast']}")
        key = "primary_endpoint" if "primary_endpoint" in rq[k] else "primary_quantity"
        bullet(doc, f"Primary endpoint: {rq[k][key]}")
        bullet(doc, f"Verdict rule: {rq[k]['verdict_rule']}")
    h(doc, "C.4 Declared deviations", level=3)
    table(doc, ["ID", "Item", "Blueprint", "Adopted", "Evidence", "Impact"],
          [[d["id"], d["item"], d["blueprint"], d["adopted"], d["evidence"], d["impact"]]
           for d in PRE["deviations"]],
          "Deviations from blueprint v3.3 §4 PHASE 4, each with the measurement "
          "or constraint that forced it.", font=7.0)
    h(doc, "C.5 Falsification", level=3)
    para(doc, PRE["falsification"])
    _amendment_section(doc)


def _amendment_section(doc) -> None:
    """C.6 -- post-hoc corrections, read from reports/phase4_amendment.json."""
    if not AMD:
        return
    h(doc, "C.6 Post-hoc corrections", level=3)
    para(doc, AMD["statement"])
    table(doc, ["ID", "Severity", "Item", "What the audit found", "Action"],
          [[a["id"], a["severity"], a["item"], a["found"], a["action"]]
           for a in AMD["amendments"]],
          "Corrections applied after the phase was first completed. The "
          "pre-registration itself was not modified, no model was retrained and no "
          "inference was re-run; the saved predictions were re-analysed with the "
          "interval procedure the pre-registration already specified.", font=7.0)
    vc = AMD["verdict_comparison"]
    rows = [["RQ2 accuracy (C2-C3)", str(vc["RQ2_accuracy"]["ci95_before"]),
             str(vc["RQ2_accuracy"]["ci95_after"]),
             vc["RQ2_accuracy"]["verdict_before"], vc["RQ2_accuracy"]["verdict_after"]],
            ["RQ2 calibration (C2-C3)", str(vc["RQ2_calibration"]["ci95_before"]),
             str(vc["RQ2_calibration"]["ci95_after"]),
             vc["RQ2_calibration"]["verdict_before"],
             vc["RQ2_calibration"]["verdict_after"]],
            ["RQ4 (C4-C2)", str(vc["RQ4"]["ci95_before"]), str(vc["RQ4"]["ci95_after"]),
             vc["RQ4"]["verdict_before"], vc["RQ4"]["verdict_after"]]]
    rows += [[f"RQ3 {c}", str(v["interval_before_mean_of_per_seed_bounds"]),
              str(v["interval_after_pooled_paired"]),
              v["verdict_before"], v["verdict_after"]]
             for c, v in vc["RQ3"]["per_configuration"].items()]
    table(doc, ["Endpoint", "Interval before", "Interval after",
                "Verdict before", "Verdict after"], rows,
          "Every pre-registered verdict before and after the corrections. Point "
          "estimates are unchanged throughout, because they are plug-in statistics "
          "that do not depend on the resample count; only the interval endpoints "
          "move, and no verdict changes.", font=7.2)
    for o in AMD.get("outstanding", []):
        bullet(doc, f"Still outstanding — {o['item']} ({o['status']}): {o['detail']}")


def appendix_d_manifest(doc) -> None:
    h(doc, "Appendix D. Script and artefact manifest", level=2)
    para(doc, "Executed in this order; each step is gated on the previous step's "
              "validation criterion, and every gate is recorded in the artefact it "
              "writes.")
    for s in ["python src/models/phase4_data.py            # cohort E, gates P4.1a-e",
              "python src/models/phase4_cache.py           # 224px cache, gate P4.2",
              "python src/models/phase4_structure.py       # distance matrix, gates P4.3a-c",
              "python src/models/phase4_train.py --probe   # measured epoch cost",
              "python src/models/phase4_prereg.py          # FROZEN before any training",
              "bash   src/models/phase4_run_all.sh         # C1-C4 x 3 seeds",
              "python src/models/phase4_infer.py           # gates P4.6a-c, MC sampling",
              "python src/models/phase4_eval.py            # RQ2 primary, gate P4.7",
              "python src/models/phase4_calibration.py     # RQ2 calibration endpoint",
              "python src/models/phase4_uncertainty.py     # RQ3",
              "python src/models/phase4_structure_eval.py  # RQ4",
              "python src/models/phase4_loao.py            # sensitivity",
              "python src/report/figures_phase4.py",
              "python src/report/build_phase4_docx.py",
              "python src/report/finalise_phase4.py",
              "python src/report/update_blueprint_phase4.py  # status board, from the "
              "verdict JSONs"]:
        bullet(doc, s)
    para(doc, "Shared numerical primitives live in src/models/phase3b_common.py "
              "(imported through phase4_common.py), whose selftest() asserts "
              "equality with scikit-learn to 1e-12 at import time. The Phase 4 "
              "loss module asserts at import time that its soft-target "
              "cross-entropy is bit-equal to nn.CrossEntropyLoss on one-hot "
              "targets, so the hard-label arms are not penalised by a different "
              "code path.")
    rows = []
    for name, what in [
            ("reports/phase4_cohort.json", "extended cohort E and gates P4.1a-e"),
            ("reports/phase4_cache_gate.json", "cache byte-identity gate P4.2"),
            ("reports/phase4_distance_matrix.json", "anatomical distance matrix, gates P4.3a-c"),
            ("reports/phase4_probe.json", "measured epoch cost on the extended cohort"),
            ("reports/phase4_prereg.json", "frozen pre-registration"),
            ("reports/phase4_run_{cfg}_seed{k}.json", "one manifest per training run"),
            ("reports/phase4_predictions_{cfg}_seed{k}.csv", "per-image predictions"),
            ("reports/phase4_probs_{cfg}_seed{k}.npz", "full 23-way softmax matrices"),
            ("reports/phase4_mc_{cfg}_seed{k}.npz", "MC stochastic-depth samples"),
            ("reports/phase4_infer_gate.json", "inference gates P4.6a-c"),
            ("reports/phase4_stratified_metrics.json", "RQ2 primary, all contrasts, gate P4.7"),
            ("reports/phase4_calibration.json", "RQ2 calibration endpoint"),
            ("reports/phase4_uncertainty.json", "RQ3"),
            ("reports/phase4_structure_eval.json", "RQ4"),
            ("reports/phase4_loao.json", "leave-one-annotator-out sensitivity")]:
        rows.append([name, what])
    table(doc, ["Artefact", "Contents"], rows,
          "Reproducibility index. Every number in this report is interpolated "
          "from one of these files; none is typed into the document source.",
          widths=[7.6, 8.0], font=7.8)


def appendix_e_unexecuted(doc) -> None:
    h(doc, "Appendix E. Analyses not executed, and what they would cost", level=2)
    para(doc, "Listing these is part of the result. An analysis that was planned "
              "and then quietly dropped is indistinguishable, to a reader, from "
              "one that was never planned.")
    rows = []
    if PRE:
        rows.append(["Training-side leave-one-annotator-out",
                     PRE["sensitivity_analyses"]["leave_one_annotator_out"]["not_executed"],
                     "phase4_train.py --drop-annotator {0,1,2,3} --config C2"])
        rows.append(["lambda sweep for the C4 structured penalty",
                     "lambda is fixed a priori at unit weight (P4-DEV-3). A sweep "
                     "over three values at three seeds is 9 further runs, roughly "
                     "13 h on this hardware. RQ4 is therefore tested at one point "
                     "in lambda-space.",
                     "phase4_train.py --config C4 (with LAMBDA edited in the "
                     "pre-registration, which would require a new, separately "
                     "timestamped pre-registration)"])
        rows.append(["5-member deep ensemble",
                     "the blueprint made this conditional on budget (P4-DEV-2). "
                     "Three members were trained per configuration, so the "
                     "reported ensemble effect is a lower bound.",
                     "two further seeds per configuration, 8 runs"])
        rows.append(["Entropy-matched instead of mass-matched label smoothing",
                     f"epsilon differs substantially between the two matching "
                     f"criteria "
                     f"({PRE['epsilon_derivation_detail']['epsilon_mass_matched']:.4f} "
                     f"vs "
                     f"{PRE['epsilon_derivation_detail']['epsilon_entropy_matched']:.4f}); "
                     f"only the mass-matched control was trained. The C3 verdict "
                     f"is therefore a verdict about mass-matched smoothing.",
                     "3 further runs"])
        rows.append(["Training on the no-majority images",
                     "the 1,150 Train/Validation images with no majority label are "
                     "excluded from every arm so that the C3 hard-label control "
                     "remains definable. A C2-only arm trained on the full split "
                     "would test whether the richest ambiguity signal helps, but "
                     "would have no matched control.",
                     "3 runs plus a new cache of 1,150 images"])
        rows.append(["Post-hoc temperature scaling",
                     "excluded by the pre-registration's scope list: it is a "
                     "separate calibration intervention and would confound the "
                     "C2-vs-C3 calibration contrast.",
                     "no training; a validation-set temperature fit per arm"])
        ec = PRE["epoch_cap_derivation"]
        warm, ft = ec["measured_warmup_epoch_sec"], ec["measured_finetune_epoch_sec"]
        n_runs, n_ft = 6, 70
        hours = (10 * warm + n_ft * ft) * n_runs / 3600.0
        rows.append([
            "Phase 4B — the convergence amendment (C2 and C3 retrained uncapped)",
            f"the pre-registered fine-tuning cap bound on 8 of 12 runs and did not "
            f"censor the arms equally (section 4.6): it bound on all three C2 runs, "
            f"whose best epochs were still at 39/41/41 of 44, against one of three "
            f"for C4. Retraining C2 and C3 with early stopping as the only stop "
            f"criterion would remove that confound from the RQ2 primary contrast. "
            f"It was costed and deliberately not run.",
            f"6 full runs from scratch, roughly {hours:.0f} h on this hardware at "
            f"{n_ft} fine-tuning epochs. NOT resumable from the existing "
            f"checkpoints: the cosine schedule is constructed with T_max equal to "
            f"the cap (phase4_train.py, cosine_T=max_ft), so raising the cap changes "
            f"the learning-rate curve across the whole fine-tuning phase and the "
            f"capped runs are not a prefix of uncapped ones. A within-4B C2-vs-C3 "
            f"contrast would be clean; a 4B-vs-Phase-4 comparison would be "
            f"confounded by the schedule change."])
    table(doc, ["Analysis", "Why it was not run", "What running it needs"], rows,
          "Declared gaps in this phase.", widths=[4.0, 8.0, 3.6], font=7.6)


def references(doc) -> None:
    h(doc, "References", level=1, page_break=True)
    refs = [
        "Bhandari, A., et al. (2025). GastroHUN: an Endoscopy Dataset of Complete "
        "Systematic Screening Protocol for the Stomach. Scientific Data, 12, 102. "
        "https://doi.org/10.1038/s41597-025-04401-5",
        "Gal, Y., & Ghahramani, Z. (2016). Dropout as a Bayesian approximation: "
        "Representing model uncertainty in deep learning. Proceedings of the 33rd "
        "International Conference on Machine Learning, 1050-1059.",
        "Guo, C., Pleiss, G., Sun, Y., & Weinberger, K. Q. (2017). On calibration "
        "of modern neural networks. Proceedings of the 34th International "
        "Conference on Machine Learning, 1321-1330.",
        "Huang, G., Sun, Y., Liu, Z., Sedra, D., & Weinberger, K. Q. (2016). Deep "
        "networks with stochastic depth. European Conference on Computer Vision, "
        "646-661.",
        "Lakshminarayanan, B., Pritzel, A., & Blundell, C. (2017). Simple and "
        "scalable predictive uncertainty estimation using deep ensembles. Advances "
        "in Neural Information Processing Systems, 30.",
        "Liu, Z., Mao, H., Wu, C.-Y., Feichtenhofer, C., Darrell, T., & Xie, S. "
        "(2022). A ConvNet for the 2020s. IEEE/CVF Conference on Computer Vision "
        "and Pattern Recognition, 11976-11986.",
        "Mongan, J., Moy, L., & Kahn, C. E. (2020). Checklist for Artificial "
        "Intelligence in Medical Imaging (CLAIM): A guide for authors and "
        "reviewers. Radiology: Artificial Intelligence, 2(2), e200029.",
        "Müller, R., Kornblith, S., & Hinton, G. (2019). When does label smoothing "
        "help? Advances in Neural Information Processing Systems, 32.",
        "Naeini, M. P., Cooper, G. F., & Hauskrecht, M. (2015). Obtaining well "
        "calibrated probabilities using Bayesian binning. Proceedings of the AAAI "
        "Conference on Artificial Intelligence, 29(1), 2901-2907.",
        "Page, M. J., et al. (2021). The PRISMA 2020 statement: An updated "
        "guideline for reporting systematic reviews. BMJ, 372, n71.",
        "Peterson, J. C., Battleday, R. M., Griffiths, T. L., & Russakovsky, O. "
        "(2019). Human uncertainty makes classification more robust. IEEE/CVF "
        "International Conference on Computer Vision, 9617-9626.",
        "Collins, G. S., et al. (2024). TRIPOD+AI statement: Updated guidance for "
        "reporting clinical prediction models that use regression or machine "
        "learning methods. BMJ, 385, e078378.",
        "Szegedy, C., Vanhoucke, V., Ioffe, S., Shlens, J., & Wojna, Z. (2016). "
        "Rethinking the Inception architecture for computer vision. IEEE Conference "
        "on Computer Vision and Pattern Recognition, 2818-2826.",
    ]
    for r in sorted(refs):
        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
        p.paragraph_format.left_indent = Pt(24)
        p.paragraph_format.first_line_indent = Pt(-24)
        p.paragraph_format.space_after = Pt(5)
        run = p.add_run(r)
        run.font.size = Pt(9.5)
    para(doc, "Phase 1's 82 included studies are catalogued in "
              "literature_v2/extraction_table.csv and referenced in the Phase 0/1 "
              "report; only works cited directly in this chapter are listed here.",
         size=8.5, italic=True, color=GREY)
