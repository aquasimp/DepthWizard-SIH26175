# 02 — Model Card: Depth Anything V2 Small (Fine-Tuned on GAMUS)

## 1. Problem Statement Context (ISRO / SAC SIH 2026 Problem Statement 26175)
Recorded from `https://github.com/IMG-PROCESS-SAC/SIH2026`:
- **Title**: DepthWizard — Single-View Height Estimation and 3D Flythrough
- **Organization**: Indian Space Research Organisation (ISRO) / Space Applications Centre (SAC)
- **Background**: Accurate Digital Elevation Models (DEMs) and Digital Surface Models (DSMs) are fundamental to urban planning, disaster management, and reconnaissance. Traditional elevation acquisition (stereo pairs, LiDAR, InSAR) can be cost-prohibitive or unavailable. Single-view height estimation offers an agile alternative.
- **Challenge**: Foundational monocular depth models predict relative depth with domain gaps on nadir remote sensing imagery. The challenge is converting relative depth to metric elevation and building interactive 3D flythrough environments.
- **Recommended Foundation Dataset**: GAMUS (Ground-Aerial Multimodal Urban Sensing) dataset on Hugging Face (`earthflow/GAMUS`).

## 2. Model Architecture
- **Backbone**: DINOv2 ViT-Small (`vits`), frozen during fine-tuning (`requires_grad_(False)`).
  - Config: `{'encoder': 'vits', 'features': 64, 'out_channels': [48, 96, 192, 384]}`
  - Parameters: 24.8 Million
  - Permissive License: **Apache-2.0**
- **Decoder Head**: Dense Prediction Transformer (DPT) head adapted for metric height regression.
  - Training Resolution: $518 \times 518$ px.
  - Target Ground Sample Distance (GSD): Canonical 0.33 m/px.

## 3. Training & Dataset Facts
- **Dataset**: GAMUS (`https://huggingface.co/datasets/earthflow/GAMUS`)
  - 11,507 tiles of $1024 \times 1024$ at 0.33 m GSD.
  - Co-registered RGB + nDSM (Above-Ground Height in metres).
  - 6-class semantic labels: ground, low-vegetation, building, water, road, tree.
  - Five US metropolitan regions (Washington DC, Oakland, Jacksonville, etc.).
  - Official splits: 6,304 train / 1,059 val / 4,144 test.
  - License: CC-BY-4.0.
- **Loss Function**:
  $$\mathcal{L} = \mathcal{L}_{\mathrm{SILog}}(\lambda=0.85) + \mathcal{L}_{1} + 0.5 \sum_{s=1}^4 w_s \mathcal{L}_{\mathrm{grad}}^{(s)}$$
  where $w = [1.0, 0.5, 0.25, 0.125]$ across 4 spatial scales.

## 4. Licensing
- **Model Code & Weights**: Apache-2.0 (Depth Anything V2 Small).
- **Training Annotations**: CC-BY-4.0 (GAMUS).
- **DepthWizard Suite**: MIT License.
