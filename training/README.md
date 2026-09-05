# Training Module: Metric nDSM Fine-Tuning on GAMUS

This directory contains the pipeline for fine-tuning the DPT decoder head of Depth Anything V2 Small on the GAMUS dataset to predict metric nDSM (metres above ground level).

## Key Architecture & Setup
- **Backbone**: Frozen DINOv2 ViT-S encoder (`requires_grad_(False)`).
- **Decoder**: DPT head fine-tuned with AdamW ($3 \times 10^{-4}$), cosine schedule, 5% warmup.
- **Loss**: Masked SILog ($\lambda = 0.85$) + L1 + multi-scale gradient matching.
- **Data Normalization**: 0.33 m/px canonical GSD, 518x518 crops.

## Workflows
1. `prepare_gamus.py`: Download stratified subset from Hugging Face (`earthflow/GAMUS`).
2. `train_head.py --config configs/dav2s_gamus_smoke.yaml`: Overfit test on 20 tiles (RMSE < 1.0 m).
3. `train_head.py --config configs/dav2s_gamus_ft.yaml`: Full fine-tuning run.
4. `eval_checkpoint.py`: Validation evaluation against baseline.
