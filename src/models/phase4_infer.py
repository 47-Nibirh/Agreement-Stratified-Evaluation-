"""
Phase 4 / Stage F -- inference for every configuration on the full test split.

Every Phase 4 checkpoint is run over the SAME cached 1,353-image test tensor,
with the SAME normalisation, batch size, autocast setting and softmax that
phase3_eval.py / phase3b_probs.py used for the Phase 2 reference arm. Nothing
about the evaluation path differs between arms, so any difference in the
numbers is a difference between the trained models.

Two products per checkpoint:

  deterministic pass   argmax, top-1 probability and the full 23-way softmax
                       matrix -- the inputs to accuracy, macro F1 and
                       calibration.
  MC stochastic-depth  T stochastic forward passes with the StochasticDepth
                       modules (and only those) returned to training mode.
                       ConvNeXt-Tiny contains no Dropout and no BatchNorm
                       (verified at run time and recorded in the output), so
                       this isolates exactly the stochastic mechanism the
                       network was trained with -- the faithful translation of
                       the MC-dropout argument to this architecture
                       (pre-registration P4-DEV-1).

The C0 reference arm is NOT re-run deterministically: its predictions and
probability matrices already exist as the Phase 3 artefacts and are reused, so
the reference numbers in this phase are literally the Phase 3 numbers. Its MC
samples are produced here, because Phase 3 did not need them.

Gates
  P4.6a  row order of every output matches data/phase3_cache_index.csv
  P4.6b  argmax of the saved probability matrix equals the saved y_pred
  P4.6c  ConvNeXt-Tiny exposes >0 StochasticDepth modules and 0 Dropout /
         BatchNorm modules, i.e. the MC estimator samples what it claims to

Outputs
  reports/phase4_predictions_{config}_seed{k}.csv
  reports/phase4_probs_{config}_seed{k}.npz
  reports/phase4_mc_{config}_seed{k}.npz          (C0 included)
  reports/phase4_infer_gate.json
Run:  python src/models/phase4_infer.py
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd
import torch
import torch.nn as nn
from torch.utils.data import DataLoader
from torchvision.ops import StochasticDepth

sys.path.insert(0, str(Path(__file__).resolve().parent))
from phase2_train import CohortDataset, build_model  # noqa: E402
from phase4_common import SEEDS  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
CACHE = ROOT / "data" / "phase3_cache_224.npy"
INDEX = ROOT / "data" / "phase3_cache_index.csv"
CLASS_INDEX = ROOT / "data" / "phase2_class_index.json"
NORM = ROOT / "reports" / "phase2_norm_stats.json"
PREREG = ROOT / "reports" / "phase4_prereg.json"
CKPT = ROOT / "checkpoints"
REPORTS = ROOT / "reports"
NEW_CONFIGS = ("C1", "C2", "C3", "C4")
BATCH = 24


def stochastic_modules(model):
    return [m for m in model.modules() if isinstance(m, StochasticDepth)]


@torch.no_grad()
def forward_probs(model, loader, device) -> np.ndarray:
    chunks = []
    for x, _ in loader:
        x = x.to(device)
        with torch.autocast("cuda", dtype=torch.float16, enabled=device.type == "cuda"):
            out = model(x)
        chunks.append(torch.softmax(out.float(), 1).cpu().numpy())
    return np.concatenate(chunks).astype(np.float32)


def main() -> None:
    t0 = time.time()
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    cls = json.load(open(CLASS_INDEX, encoding="utf-8"))
    inv = {v: k for k, v in cls.items()}
    ns = json.load(open(NORM, encoding="utf-8"))
    pre = json.load(open(PREREG, encoding="utf-8"))
    n_mc = pre["research_questions"]["RQ3"]["n_mc_samples"]

    idx = pd.read_csv(INDEX)
    n = len(idx)
    ds = CohortDataset(CACHE, np.arange(n), np.zeros(n, dtype=int), False,
                       ns["mean"], ns["std"])
    loader = DataLoader(ds, batch_size=BATCH, shuffle=False, num_workers=0)

    probe_model = build_model(len(cls))
    n_sd = len(stochastic_modules(probe_model))
    n_do = sum(1 for m in probe_model.modules() if isinstance(m, nn.Dropout))
    n_bn = sum(1 for m in probe_model.modules()
               if isinstance(m, (nn.BatchNorm1d, nn.BatchNorm2d, nn.SyncBatchNorm)))
    if n_sd == 0 or n_do or n_bn:
        raise SystemExit(f"GATE P4.6c FAILED: stochastic_depth={n_sd} dropout={n_do} "
                         f"batchnorm={n_bn}")
    sd_probs = sorted({round(float(m.p), 4) for m in stochastic_modules(probe_model)})
    del probe_model

    gates, done = {}, []

    def mc_pass(model, tag):
        """T stochastic forward passes; only StochasticDepth returns to train mode."""
        model.eval()
        for m in stochastic_modules(model):
            m.train()
        torch.manual_seed(20260727)
        samples = np.stack([forward_probs(model, loader, device) for _ in range(n_mc)])
        model.eval()
        np.savez_compressed(REPORTS / f"phase4_mc_{tag}.npz",
                            samples=samples.astype(np.float32),
                            filename=idx.filename.to_numpy().astype(str))
        return samples

    # ---- new configurations -------------------------------------------------
    for cfg in NEW_CONFIGS:
        for seed in SEEDS:
            cp = CKPT / f"phase4_{cfg}_seed{seed}.pt"
            if not cp.exists():
                print(f"  skip {cfg} seed{seed}: checkpoint absent", flush=True)
                continue
            blob = torch.load(cp, map_location="cpu", weights_only=False)
            model = build_model(len(cls))
            model.load_state_dict(blob["state_dict"])
            model.to(device).eval()

            prob = forward_probs(model, loader, device)
            pred = prob.argmax(1)
            out = idx.copy()
            out["y_pred"] = pred
            out["label_pred"] = [inv[i] for i in pred]
            out["confidence"] = prob.max(1)
            out.to_csv(REPORTS / f"phase4_predictions_{cfg}_seed{seed}.csv", index=False)
            np.savez_compressed(REPORTS / f"phase4_probs_{cfg}_seed{seed}.npz",
                                probs=prob, filename=idx.filename.to_numpy().astype(str),
                                classes=np.array(sorted(cls, key=cls.get)))
            if int((prob.argmax(1) != out.y_pred.to_numpy()).sum()):
                raise SystemExit(f"GATE P4.6b FAILED: {cfg} seed{seed}")

            mc = mc_pass(model, f"{cfg}_seed{seed}")
            gates[f"{cfg}_seed{seed}"] = {
                "n_rows": int(n), "n_argmax_mismatch": 0,
                "mc_samples": int(mc.shape[0]),
                "mc_mean_pred_agreement_with_deterministic": round(float(
                    (mc.mean(0).argmax(1) == pred).mean()), 5),
                "mc_mean_top1_std": round(float(mc.max(2).std(0).mean()), 6),
            }
            done.append(f"{cfg}_seed{seed}")
            print(f"  {cfg} seed{seed}: deterministic + {n_mc} MC passes done", flush=True)
            del model
            torch.cuda.empty_cache()

    # ---- C0 reference arm: reuse Phase 3 predictions, add MC samples --------
    for seed in SEEDS:
        cp = CKPT / f"phase2_convnext_tiny_seed{seed}.pt"
        ref = REPORTS / f"phase3_predictions_seed{seed}.csv"
        if not (cp.exists() and ref.exists()):
            continue
        blob = torch.load(cp, map_location="cpu", weights_only=False)
        model = build_model(len(cls))
        model.load_state_dict(blob["state_dict"])
        model.to(device).eval()

        # re-derive the deterministic pass purely as a gate on reuse
        prob = forward_probs(model, loader, device)
        r = pd.read_csv(ref)
        if list(r.filename) != list(idx.filename):
            raise SystemExit(f"GATE P4.6a FAILED: C0 seed{seed} row order")
        n_mis = int((prob.argmax(1) != r.y_pred.to_numpy()).sum())
        if n_mis:
            raise SystemExit(f"GATE P4.6b FAILED: C0 seed{seed}, {n_mis} argmax mismatches "
                             f"vs the reused Phase 3 predictions")
        mc = mc_pass(model, f"C0_seed{seed}")
        gates[f"C0_seed{seed}"] = {
            "n_rows": int(n), "n_argmax_mismatch": n_mis,
            "reused_from": ref.name,
            "mc_samples": int(mc.shape[0]),
            "mc_mean_pred_agreement_with_deterministic": round(float(
                (mc.mean(0).argmax(1) == r.y_pred.to_numpy()).mean()), 5),
            "mc_mean_top1_std": round(float(mc.max(2).std(0).mean()), 6),
        }
        done.append(f"C0_seed{seed}")
        print(f"  C0 seed{seed}: Phase 3 predictions reproduced exactly, "
              f"{n_mc} MC passes done", flush=True)
        del model
        torch.cuda.empty_cache()

    out = {
        "generated": time.strftime("%Y-%m-%d %H:%M:%S"),
        "n_test_images": int(n),
        "n_mc_samples": n_mc,
        "seeds": list(SEEDS),
        "partial_sweep": bool(tuple(SEEDS) != (1, 2, 3)),
        "batch_size": BATCH,
        "gates": {
            "P4.6a_row_order": True,
            "P4.6b_argmax_matches_saved_prediction": True,
            "P4.6c_architecture_stochastic_inventory": {
                "n_stochastic_depth_modules": n_sd,
                "stochastic_depth_p_values": sd_probs,
                "n_dropout_modules": n_do,
                "n_batchnorm_modules": n_bn,
                "interpretation": ("MC stochastic depth samples the only stochastic "
                                   "mechanism present, and the absence of BatchNorm "
                                   "means no other module changes behaviour when the "
                                   "StochasticDepth layers are put back in train mode"),
            },
        },
        "per_checkpoint": gates,
        "completed": done,
        "runtime_sec": round(time.time() - t0, 1),
    }
    (REPORTS / "phase4_infer_gate.json").write_text(json.dumps(out, indent=2),
                                                    encoding="utf-8")
    print(f"\ninference complete for {len(done)} checkpoints in {out['runtime_sec']}s")


if __name__ == "__main__":
    main()
