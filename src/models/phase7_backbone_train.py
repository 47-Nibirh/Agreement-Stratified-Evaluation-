"""
Phase 7 / P7.0-B -- backbone generalisation: does any of this depend on ConvNeXt?

Every result in this thesis was produced by one architecture. The two findings
the defence will lean on hardest -- the calibration reversal between C2 and C3,
and the human-comparator position of the model between an individual annotator
and the modal-vote oracle -- are both single-backbone claims. "Is this a
ConvNeXt artefact?" is the first question a sharp examiner asks, and at present
the thesis has no answer.

This script re-runs the target-construction contrast on a SECOND backbone and
changes nothing else. It does not fork phase4_train.py: it imports it and
substitutes the model constructor, so the cohort, the cache, the normalisation,
the augmentation, the two-stage schedule, the loss, the early-stopping rule, the
epoch cap and the seeds are literally the Phase 4 code path. Any difference in
the result is a difference between architectures, because nothing else can move.

Why EfficientNet-B0
  - the blueprint's own model table (sec.5) lists it as the efficiency floor and
    an approved fallback, so it is not a new modelling decision
  - torchvision exposes it with a `.features` Sequential and a `.classifier`
    head, which is the interface phase4_train.resolve_top_layers and main()
    already use, so the substitution touches one function
  - 5 M parameters against ConvNeXt-Tiny's 28 M: a genuinely different capacity
    and a genuinely different inductive bias (inverted residuals with squeeze-
    excitation, BatchNorm, and a Dropout head), which is what makes it a test
    rather than a re-run

Arms: C1, C2, C3. C1 is the hard-label reference on cohort E, C2 the
vote-proportion arm, C3 the matched-epsilon control. That triple is the minimum
that reproduces the Phase 4 calibration finding. C0 is omitted because it trains
on a different cohort (4/4 only) and would add a second data path for no gain
here; C4 is omitted because RQ4 was not resolved at unit lambda and a second
backbone at the same single lambda would not resolve it either.

NOTE on the run manifests: phase4_train writes "phase": 4 into every manifest.
These runs carry tag "_b0", so their checkpoints and manifests are
phase4_{config}_b0_seed{k}, distinct from the Phase 4 files, and the tag is the
field that identifies them as Phase 7 work.

Usage:  python src/models/phase7_backbone_train.py --config C2 --seed 1
"""
from __future__ import annotations

import sys
from pathlib import Path

import torch.nn as nn
from torchvision.models import EfficientNet_B0_Weights, efficientnet_b0

sys.path.insert(0, str(Path(__file__).resolve().parent))
import phase4_train as P4  # noqa: E402

TAG = "_b0"


def build_model_b0(n_classes: int):
    """EfficientNet-B0 with the head resized, mirroring phase4_train.build_model.

    ConvNeXt-Tiny's head is classifier[2] (LayerNorm2d, Flatten, Linear);
    EfficientNet-B0's is classifier[1] (Dropout, Linear). That index is the only
    architecture-specific difference this substitution needs.
    """
    m = efficientnet_b0(weights=EfficientNet_B0_Weights.IMAGENET1K_V1)
    m.classifier[1] = nn.Linear(m.classifier[1].in_features, n_classes)
    return m


def main() -> None:
    # main() resolves build_model from its own module globals at call time, so
    # rebinding the name here is sufficient and no Phase 4 file is modified.
    P4.build_model = build_model_b0

    if "--tag" not in sys.argv:
        sys.argv += ["--tag", TAG]
    P4.main()


if __name__ == "__main__":
    main()
