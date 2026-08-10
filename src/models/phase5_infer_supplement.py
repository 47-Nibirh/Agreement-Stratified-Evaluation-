"""
P5.5b -- inference over the discarded-image supplement.

Same arms, same seeds, same frozen checkpoints and the same forward path as
phase5_infer.py. Needed only so the P5.10 `discard -> OTHERCLASS` sensitivity
flips are executable; these predictions play no part in the primary analysis.

Outputs
  reports/phase5_probs_disc_{cfg}_seed{s}.npz
Run:  python src/models/phase5_infer_supplement.py
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd
import torch

sys.path.insert(0, str(Path(__file__).resolve().parent))
from phase5_infer import ckpt_path, forward_probs, make_loader  # noqa: E402
from phase2_train import build_model  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
REPORTS = ROOT / "reports"
CLASS_INDEX = ROOT / "data" / "phase2_class_index.json"
NORM = REPORTS / "phase2_norm_stats.json"
PREREG = REPORTS / "phase5_prereg.json"
CACHE = ROOT / "data" / "phase5_cache_discarded_224.npy"
INDEX = ROOT / "data" / "phase5_cache_discarded_index.csv"


def main() -> int:
    t0 = time.time()
    if not CACHE.exists():
        print("[P5.5b] run phase5_cache_supplement.py first.")
        return 1
    pre = json.loads(PREREG.read_text(encoding="utf-8"))
    arms, seeds = pre["arms"]["carried"], pre["arms"]["seeds"]
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    cls = json.loads(CLASS_INDEX.read_text(encoding="utf-8"))
    ns = json.loads(NORM.read_text(encoding="utf-8"))

    n = len(pd.read_csv(INDEX))
    loader = make_loader(CACHE, n, ns)
    print(f"[P5.5b] {n:,} discarded images, arms {arms} x seeds {seeds}", flush=True)

    done = 0
    for cfg in arms:
        for seed in seeds:
            out = REPORTS / f"phase5_probs_disc_{cfg}_seed{seed}.npz"
            if out.exists():
                done += 1
                continue
            path = ckpt_path(cfg, seed)
            if not path.exists():
                print(f"[P5.5b] MISSING {path.name}", flush=True)
                continue
            blob = torch.load(path, map_location="cpu", weights_only=False)
            model = build_model(len(cls))
            model.load_state_dict(blob["state_dict"])
            model.to(device).eval()
            prob = forward_probs(model, loader, device)
            np.savez_compressed(out, probs=prob,
                                pred=prob.argmax(1).astype(np.int16))
            done += 1
            print(f"  {cfg} seed{seed}: {len(prob):,} rows -> {out.name} "
                  f"({done}/{len(arms) * len(seeds)})", flush=True)
            del model
            if device.type == "cuda":
                torch.cuda.empty_cache()
    print(f"[P5.5b] done in {time.time() - t0:.1f}s", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
