# Model Licenses and Governance

## Depth Anything V2 Small
- **Model Architecture**: DINOv2 ViT-Small backbone + DPT decoder
- **Parameters**: 24.8 Million
- **License**: Apache License 2.0 (Permissive, commercial and non-commercial use permitted)
- **Source**: https://github.com/DepthAnything/Depth-Anything-V2
- **Weights File**: `depth_anything_v2_vits.pth` (MD5 / SHA256 verified)
- **Licensing Note**: Depth Anything V2-Small is explicitly licensed under **Apache-2.0**. (V2-Base, V2-Large, and V2-Giant carry CC-BY-NC-4.0 and are intentionally NOT used in DepthWizard to preserve permissive licensing).

## GAMUS Fine-Tuned nDSM Decoder (`dav2s_gamus_ft_v1.pth`)
- **Training Data**: GAMUS (Ground-Aerial Multimodal Urban Sensing), CC-BY-4.0
- **Fine-Tuning Scope**: DINOv2 encoder weights remain frozen (Apache-2.0). Only the DPT decoder head is fine-tuned on metric nDSM (metres above ground).
- **License**: MIT / Apache-2.0 compatible.
