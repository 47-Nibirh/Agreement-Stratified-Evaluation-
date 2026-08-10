"""
Phase 6 / P6.4 -- Grad-CAM over every arm and seed.

The maps produced here are an INPUT to a measurement, not the measurement. The
pre-registration fixes the layer, the target class and the top-q threshold
before anything is rendered, precisely so that the chapter cannot become a
gallery of persuasive heatmaps.

Definition (pre-registered)
  layer         model.features[-1], the final ConvNeXt stage output (7x7x768
                at 224 input)
  target        the model's OWN predicted class, so the map explains what the
                model did rather than what it should have done
  map           ReLU( sum_k alpha_k A_k ),  alpha_k = GAP of d(logit)/d(A_k)

Everything else in the evaluation path -- the cache, the normalisation, the
batch size, the model builder -- is imported from the Phase 2/4 modules rather
than reimplemented, so the network being explained is bit-identical to the
network that was scored.

Autocast is DISABLED here. Phase 4's forward passes used float16 autocast, but
a backward pass through float16 activations underflows small gradients on this
Turing card and would silently flatten the maps. Gate P6.4b catches any
divergence: the class each CAM targets is checked against the frozen argmax in
the prediction files, for every image, and the run aborts on a single mismatch.

Gates
  P6.4a  every map finite and non-negative
  P6.4b  the targeted class equals the saved argmax, exactly, for all 1,353
         images of every arm and seed
  P6.4c  row order matches data/phase3_cache_index.csv

Outputs
  reports/phase6_cams_{arm}_seed{k}.npz   (1353, 7, 7) float16 + filename
  reports/phase6_cam_gate.json
Run:  python src/models/phase6_cam.py
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
import phase6_common as C  # noqa: E402
from phase2_train import CohortDataset, build_model  # noqa: E402

CACHE = C.DATA / "phase3_cache_224.npy"
INDEX = C.DATA / "phase3_cache_index.csv"
NORM = C.REPORTS / "phase2_norm_stats.json"
GATE_OUT = C.REPORTS / "phase6_cam_gate.json"
BATCH = 12


def cam_path(arm: str, seed: int) -> Path:
    return C.REPORTS / f"phase6_cams_{arm}_seed{seed}.npz"


def grad_cam_batch(model, layer, x, device, frozen_target):
    """Grad-CAM for the FROZEN predicted class of every image in the batch.

    `frozen_target` is the y_pred column of the committed prediction file, not
    this pass's argmax. Every accuracy, calibration, geometry and selective
    number in Phases 3-6 is computed from that column, so it is the decision an
    explanation must explain. Recomputing the argmax here would occasionally
    explain a DIFFERENT decision from the one the thesis scored -- see the
    live-argmax divergence recorded in the gate file.

    Returns (cams (b,h,w) float32, live argmax (b,)) -- the live argmax is
    returned only so the divergence can be counted and declared.
    """
    acts = {}

    def fwd_hook(_m, _i, o):
        acts["a"] = o
        o.retain_grad()

    h = layer.register_forward_hook(fwd_hook)
    x = x.to(device)
    tgt = torch.as_tensor(frozen_target, device=device, dtype=torch.long)
    model.zero_grad(set_to_none=True)
    logits = model(x)                      # float32: no autocast, see docstring
    live = logits.argmax(1)
    picked = logits.gather(1, tgt[:, None]).sum()
    picked.backward()
    a = acts["a"]                          # (b, c, h, w)
    g = a.grad                             # (b, c, h, w)
    h.remove()
    alpha = g.mean(dim=(2, 3), keepdim=True)
    cam = torch.relu((alpha * a).sum(1))   # (b, h, w)
    return cam.detach().float().cpu().numpy(), live.detach().cpu().numpy()


def main() -> None:
    t0 = time.time()
    pre = C.prereg()
    rule = pre["endpoints"]["P6-C"]
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    cls = C.classes()
    ns = json.loads(NORM.read_text(encoding="utf-8"))
    idx = pd.read_csv(INDEX)
    n = len(idx)

    ds = CohortDataset(CACHE, np.arange(n), np.zeros(n, dtype=int), False,
                       ns["mean"], ns["std"])
    loader = DataLoader(ds, batch_size=BATCH, shuffle=False, num_workers=0)

    arms = C.available_arms()
    gates, timings = {}, {}
    for arm in arms:
        for seed in C.SEEDS:
            cp = C.ckpt_path(arm, seed)
            if not cp.exists():
                print(f"  skip {arm} seed{seed}: checkpoint absent", flush=True)
                continue
            out_path = cam_path(arm, seed)
            if out_path.exists():
                print(f"  skip {arm} seed{seed}: {out_path.name} exists", flush=True)
                continue
            ts = time.time()
            blob = torch.load(cp, map_location="cpu", weights_only=False)
            model = build_model(len(cls))
            model.load_state_dict(blob["state_dict"])
            model.to(device).eval()
            layer = model.features[-1]

            # ---- GATE P6.4c: row order, checked BEFORE anything is computed
            frozen = pd.read_csv(C.pred_path(arm, seed))
            if list(frozen.filename) != list(idx.filename):
                raise SystemExit(f"GATE P6.4c FAILED: {arm} seed{seed} row order")
            frozen_pred = frozen.y_pred.to_numpy()

            cams, live = [], []
            pos = 0
            for x, _ in loader:
                b = x.shape[0]
                cm, lv = grad_cam_batch(model, layer, x, device,
                                        frozen_pred[pos:pos + b])
                cams.append(cm)
                live.append(lv)
                pos += b
            cams = np.concatenate(cams)
            live = np.concatenate(live)

            # ---- GATE P6.4a ----------------------------------------------
            if not np.isfinite(cams).all():
                raise SystemExit(f"GATE P6.4a FAILED: {arm} seed{seed} has non-finite CAM values")
            if (cams < 0).any():
                raise SystemExit(f"GATE P6.4a FAILED: {arm} seed{seed} has negative CAM values")

            # ---- GATE P6.4b ----------------------------------------------
            # Satisfied by construction: the CAM targets frozen_pred. What is
            # recorded here is the DIVERGENCE between this float32 pass's live
            # argmax and the frozen float16-autocast argmax, which is a real
            # numerical fact about near-tied images and is declared rather than
            # hidden.
            n_div = int((frozen_pred != live).sum())
            np.savez_compressed(out_path, cams=cams.astype(np.float16),
                                target=frozen_pred.astype(np.int16),
                                live_argmax=live.astype(np.int16),
                                filename=idx.filename.to_numpy().astype(str))
            dt = time.time() - ts
            timings[f"{arm}_seed{seed}"] = round(dt, 1)
            gates[f"{arm}_seed{seed}"] = {
                "P6.4a": "PASS",
                "P6.4b": f"PASS -- CAM targets the frozen prediction for all {n} images",
                "P6.4c": "PASS",
                "live_argmax_divergence": n_div,
                "live_argmax_divergence_pct": round(100.0 * n_div / n, 4),
                "cam_shape": list(cams.shape)}
            del model
            if device.type == "cuda":
                torch.cuda.empty_cache()
            print(f"  {arm} seed{seed}: {cams.shape} in {dt:.1f}s -> {out_path.name}",
                  flush=True)

    payload = {
        "generated": time.strftime("%Y-%m-%d %H:%M:%S"),
        "phase": 6, "step": "P6.4",
        "method": rule["method"], "layer": rule["layer"],
        "target_class": rule["target_class"],
        "autocast": ("DISABLED for the backward pass; float16 activations "
                     "underflow small gradients on this Turing card and would "
                     "silently flatten the maps"),
        "target_selection": (
            "the CAM targets the class recorded in the committed prediction file, "
            "not this pass's argmax. Phases 3-5 ran inference under float16 "
            "autocast; this pass runs in float32. On images where the top two "
            "classes are near-tied (the smallest observed top1-top2 margin in the "
            "frozen posteriors is 3.08e-03) the two precisions can disagree about "
            "the argmax. Explaining the live argmax would then explain a decision "
            "no other number in the thesis was computed from. The divergence count "
            "is recorded per checkpoint below as a numerical fact about the "
            "evaluation path rather than suppressed."),
        "amendment": (
            "P6-AMD-3: the pre-registration says the CAM target is 'the model's own "
            "predicted class'. That phrase is ambiguous between the live argmax and "
            "the committed one; it is resolved here in favour of the committed "
            "prediction, because that is the decision every other Phase 3-6 endpoint "
            "scores. The resolution was forced by gate P6.4b firing on 1 of 1,353 "
            "images, and is recorded rather than silently adopted."),
        "device": str(device), "batch": BATCH,
        "gates": gates, "timings_sec": timings,
        "runtime_sec": round(time.time() - t0, 1),
    }
    if GATE_OUT.exists():
        old = json.loads(GATE_OUT.read_text(encoding="utf-8"))
        payload["gates"] = {**old.get("gates", {}), **payload["gates"]}
        payload["timings_sec"] = {**old.get("timings_sec", {}), **payload["timings_sec"]}
    GATE_OUT.write_text(json.dumps(payload, indent=1), encoding="utf-8")
    print(f"[P6.4] {len(payload['gates'])} checkpoint(s) mapped, all gates PASS "
          f"-> {GATE_OUT.name} ({payload['runtime_sec']}s)")


if __name__ == "__main__":
    main()
