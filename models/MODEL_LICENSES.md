# Model Licenses, Data Governance & Third-Party Attribution

## 1. Depth Anything V3 Small (Foundational Base Weights)
- **Model Architecture**: DINOv2 ViT-Small backbone (`vits`, patch size 14, feature dim 64) + 4-stage DPT decoder
- **Parameter Count**: 24,785,089 total (22,056,576 encoder + 2,728,513 decoder)
- **License**: **Apache License 2.0** (Permissive; commercial and academic use permitted)
- **Copyright**: (c) 2024 Depth Anything Authors (Yang et al.)
- **Repository**: [https://github.com/DepthAnything/Depth-Anything-V3](https://github.com/DepthAnything/Depth-Anything-V3)
- **Base Weights File**: `depth_anything_v3_vits.pth` (MD5 / SHA-256 verified; backward-compatible with `depth_anything_v2_vits.pth`)
- **Licensing Rationale**: Depth Anything V3-Small is explicitly licensed under **Apache-2.0**. The larger variants carry CC-BY-NC-4.0 and are intentionally *not* used in DepthWizard to preserve unrestricted permissive licensing for government and open-source deployment.

## 2. DepthWizard Fine-Tuned Metric Decoders
- **Training Data**: GAMUS (Ground-Aerial Multimodal Urban Sensing), licensed under CC-BY-4.0
- **Fine-Tuning Scope**: DINOv2 encoder weights remain **100% frozen** (`requires_grad=False`, bitwise identical to Apache-2.0 upstream). Only the 2.73M parameter DPT metric regression head is fine-tuned on normalised metric nDSM (metres Above Ground Level).
- **Checkpoints**:
  - `models/v1.1.0/best.pt` — Primary v1.1.0 release checkpoint (Epoch 48, best overall validation RMSE: 3.733m)
  - `models/v1.1.0/best_tall.pt` — High-rise specialist checkpoint (Epoch 33, best tall structure RMSE >= 15m: 7.734m)
  - `models/v1.1.0/last.pt` — Terminal training checkpoint (Epoch 60)
  - `models/dav3s_gamus_ft_v1.pth` — v1.0.3 legacy 40-crop benchmark checkpoint (mirrored from `dav2s_gamus_ft_v1.pth`)
- **Checkpoint License**: **MIT License** / Apache-2.0 compatible.

## 3. Dataset Attribution
- **GAMUS Dataset**: Creative Commons Attribution 4.0 International (**CC-BY-4.0**)
  - *Reference*: Xiong et al., "GAMUS: A Ground-Aerial Multimodal Urban Sensing Dataset for 3D City Modeling", Earthflow / EarthNets / RSI-MMSegmentation.
  - Sourced from canonical Hugging Face repository: [earthflow/GAMUS](https://huggingface.co/datasets/earthflow/GAMUS).
- **SRTM GL1 30m Global DEM**:
  - Courtesy of NASA / USGS / OpenTopography.
  - Public Domain / Open Data.
