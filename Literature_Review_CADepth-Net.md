# Literature Review

**Paper:** Yan, J., Zhao, H., Bu, P., & Jin, Y. (2021). *Channel-Wise Attention-Based Network for Self-Supervised Monocular Depth Estimation.* arXiv:2112.13047.

## Problem Statement

Depth from a single image is useful for robotics, self-driving cars, and augmented reality. Supervised methods need large amounts of ground-truth depth from expensive LiDAR, so self-supervised methods use video or stereo pairs as the training signal instead. But existing self-supervised methods learn scene structure only implicitly, and their U-Net decoder fuses high-level and low-level features by simple concatenation. This loses detail and causes a performance bottleneck and blurry artefacts at depth boundaries.

## Key Contributions

1. **CADepth-Net**, a U-Net network for self-supervised monocular depth estimation, built on Monodepth2 with a ResNet encoder and a separate pose network.
2. **Structure Perception Module (SPM)** — self-attention across the *channel* dimension. It measures similarity between channel maps, turns it into a discrimination score, and updates each channel as a weighted sum of all channels. This captures long-range dependencies and gives each channel depth information from distant regions.
3. **Detail Emphasis Module (DEM)** — in the decoder, it concatenates low-level and high-level features, pools them, and computes a channel weight vector with a sigmoid. The weights emphasise features describing object boundaries and fuse the two levels better.
4. **Experiments** on KITTI and Make3D, with ablation studies and feature-map visualisations.

## Advantages

- State-of-the-art on KITTI at every resolution. At 640×192 (mono): Abs Rel 0.105 and δ<1.25 of 0.892, versus Monodepth2's 0.115 / 0.877.
- Gains hold across resolutions (416×128 to 1280×384) and across mono and mono+stereo training.
- SPM adds **no extra parameters** and almost no time (22.52 → 22.80 ms), so the gain comes from better scene understanding, not a bigger model.
- Ablation shows both modules help, on both ResNet18 and ResNet50.
- Generalises to the unseen Make3D dataset without retraining.
- 28 ms inference on an RTX 3090, fast enough for real-time use.
- Sharper thin structures (poles, signs, pedestrians) in the qualitative results.

## Limitations

- DEM is expensive: 34.57 M → 58.34 M parameters and 22.52 → 28.41 ms, for a small gain over SPM alone.
- Depth is only relative — all results use per-image median ground-truth scaling at test time.
- Still assumes a static scene and moving camera; moving objects are only masked out, not modelled.
- Tested only on outdoor driving scenes; no indoor, night, or bad-weather results.
- Needs ImageNet pre-trained encoder weights, so it is not fully free of external supervision.
- Single runs, no variance reported, and the margin over the closest methods is often only 0.001–0.004 Abs Rel.

## Future Research Directions

- Make DEM lighter, so sharper edges do not cost double the parameters.
- Predict absolute (metric) depth, removing the need for median scaling.
- Model dynamic objects explicitly instead of masking them out.
- Test on indoor scenes and other conditions to check how far channel attention transfers.
- Combine channel-wise with spatial attention, which the paper compares but does not fuse.
- Try the same modules with transformer-based backbones.
