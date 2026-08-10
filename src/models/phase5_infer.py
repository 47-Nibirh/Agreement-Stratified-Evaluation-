"""
P5.5 -- inference over the external cache, five arms x three seeds.

Reuses the Phase 2/4 model builder, dataset and forward path unchanged. No
fine-tuning, no adaptation, no threshold tuning: the checkpoints are loaded and
run, and that is all. The Phase 2 TRAINING-SET normalisation statistics are
applied here, deliberately not recomputed on the external corpora.

Gates
  P5.5a  row order matches data/phase5_cache_index.csv
  P5.5b  the saved argmax equals the saved prediction
  P5.5c  BIT-IDENTITY. Every arm is additionally re-scored on the GastroHUN test
         split through THIS code path and must reproduce the Phase 4 saved
         probabilities exactly. If it does not, the external numbers were
         produced by a different pipeline than the internal comparator and the
         drop would be uninterpretable.

Outputs
  reports/phase5_probs_{cfg}_seed{s}.npz
  reports/phase5_infer_gate.json
Run:  python src/models/phase5_infer.py
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd
import torch
from torch.utils.data import DataLoader

sys.path.insert(0, str(Path(__file__).resolve().parent))
from phase2_train import CohortDataset, build_model  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
REPORTS = ROOT / "reports"
CKPT = ROOT / "checkpoints"
CLASS_INDEX = ROOT / "data" / "phase2_class_index.json"
NORM = REPORTS / "phase2_norm_stats.json"
PREREG = REPORTS / "phase5_prereg.json"

CACHE = ROOT / "data" / "phase5_cache_224.npy"
INDEX = ROOT / "data" / "phase5_cache_index.csv"
GATE = REPORTS / "phase5_infer_gate.json"

# internal comparator, for gate P5.5c
P3_CACHE = ROOT / "data" / "phase3_cache_224.npy"
P3_INDEX = ROOT / "data" / "phase3_cache_index.csv"

BATCH = 32


def ckpt_path(cfg: str, seed: int) -> Path:
    return (CKPT / f"phase2_convnext_tiny_seed{seed}.pt" if cfg == "C0"
            else CKPT / f"phase4_{cfg}_seed{seed}.pt")


def forward_probs(model, loader, device) -> np.ndarray:
    """Identical to phase4_infer.forward_probs."""
    chunks = []
    with torch.no_grad():
        for x, _ in loader:
            x = x.to(device)
            with torch.autocast("cuda", dtype=torch.float16,
                                enabled=device.type == "cuda"):
                out = model(x)
            chunks.append(torch.softmax(out.float(), 1).cpu().numpy())
    return np.concatenate(chunks).astype(np.float32)


def make_loader(cache: Path, n: int, ns: dict) -> DataLoader:
    ds = CohortDataset(cache, np.arange(n), np.zeros(n, dtype=int), False,
                       ns["mean"], ns["std"])
    return DataLoader(ds, batch_size=BATCH, shuffle=False, num_workers=0)


def main() -> int:
    t0 = time.time()
    if not PREREG.exists():
        print("[P5.5] pre-registration missing; run phase5_prereg.py first.")
        return 1
    pre = json.loads(PREREG.read_text(encoding="utf-8"))
    arms, seeds = pre["arms"]["carried"], pre["arms"]["seeds"]

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    cls = json.loads(CLASS_INDEX.read_text(encoding="utf-8"))
    ns = json.loads(NORM.read_text(encoding="utf-8"))
    print(f"[P5.5] device={device} arms={arms} seeds={seeds}")

    idx = pd.read_csv(INDEX)
    n_ext = len(idx)
    ext_loader = make_loader(CACHE, n_ext, ns)

    n_int = len(pd.read_csv(P3_INDEX))
    int_loader = make_loader(P3_CACHE, n_int, ns)
    print(f"[P5.5] external {n_ext:,} images | internal comparator {n_int:,} images")

    runs, identity = {}, {}
    for cfg in arms:
        for seed in seeds:
            path = ckpt_path(cfg, seed)
            if not path.exists():
                print(f"[P5.5] MISSING checkpoint {path.name}, skipping")
                continue
            blob = torch.load(path, map_location="cpu", weights_only=False)
            model = build_model(len(cls))
            model.load_state_dict(blob["state_dict"])
            model.to(device).eval()

            # ---- gate P5.5c: reproduce the Phase 4 internal probabilities ----
            ref = REPORTS / f"phase4_probs_{cfg}_seed{seed}.npz"
            if ref.exists():
                got = forward_probs(model, int_loader, device)
                want = np.load(ref)["probs"].astype(np.float32)
                same_shape = got.shape == want.shape
                bit = bool(same_shape and np.array_equal(got, want))
                identity[f"{cfg}_seed{seed}"] = {
                    "bit_identical": bit,
                    "max_abs_diff": (float(np.abs(got - want).max())
                                     if same_shape else None),
                    "n_argmax_disagreements": (int((got.argmax(1) != want.argmax(1)).sum())
                                               if same_shape else None),
                }
                print(f"  {cfg} seed{seed}: internal identity bit={bit} "
                      f"maxdiff={identity[f'{cfg}_seed{seed}']['max_abs_diff']}")

            # ---- external inference -----------------------------------------
            prob = forward_probs(model, ext_loader, device)
            pred = prob.argmax(1).astype(np.int16)
            out = REPORTS / f"phase5_probs_{cfg}_seed{seed}.npz"
            np.savez_compressed(out, probs=prob, pred=pred)
            runs[f"{cfg}_seed{seed}"] = {
                "n": int(len(prob)),
                "argmax_matches_saved_pred": bool((prob.argmax(1) == pred).all()),
                "mean_top1_confidence": round(float(prob.max(1).mean()), 5),
                "artefact": out.name,
            }
            print(f"  {cfg} seed{seed}: external {len(prob):,} rows -> {out.name} "
                  f"(mean top-1 conf {prob.max(1).mean():.4f})")
            del model
            if device.type == "cuda":
                torch.cuda.empty_cache()

    gates = {
        "P5.5a_row_order_matches_index": {
            "n_index_rows": n_ext,
            "pass": all(r["n"] == n_ext for r in runs.values()),
        },
        "P5.5b_argmax_equals_saved_pred": {
            "pass": all(r["argmax_matches_saved_pred"] for r in runs.values()),
        },
        "P5.5c_reproduces_phase4_internal_probs": {
            "checked": len(identity),
            "n_bit_identical": sum(1 for v in identity.values() if v["bit_identical"]),
            "pass": bool(identity) and all(v["bit_identical"] for v in identity.values()),
            "per_arm": identity,
            "note": ("re-scoring the GastroHUN test split through this module must "
                     "reproduce the Phase 4 probabilities exactly; otherwise the "
                     "external numbers and the internal comparator would come from "
                     "different pipelines and the drop would be uninterpretable."),
        },
    }

    out = {
        "generated": time.strftime("%Y-%m-%d %H:%M:%S"),
        "phase": 5, "step": "P5.5",
        "device": str(device),
        "arms": arms, "seeds": seeds,
        "n_external_images": n_ext,
        "n_internal_comparator_images": n_int,
        "normalisation": "Phase 2 training-set statistics, unchanged",
        "adaptation": "none -- checkpoints loaded and run as-is",
        "runs": runs,
        "gates": gates,
        "runtime_sec": round(time.time() - t0, 1),
    }
    GATE.write_text(json.dumps(out, indent=1), encoding="utf-8")
    print(f"[P5.5] wrote {GATE}")
    for k, v in gates.items():
        print(f"       {k}: pass={v.get('pass')}")
    print(f"       done in {out['runtime_sec']}s")
    return 0 if all(v.get("pass") for v in gates.values()) else 1


if __name__ == "__main__":
    sys.exit(main())
