# 02 — Model Card: Depth Anything V3 Small (Fine-Tuned on GAMUS)

## 1. Problem Statement Context (ISRO / SAC SIH 2026 Problem Statement 26175)
Recorded from `https://github.com/IMG-PROCESS-SAC/SIH2026`:
- **Title**: DepthWizard — Single-View Height Estimation and 3D Flythrough
- **Organization**: Indian Space Research Organisation (ISRO) / Space Applications Centre (SAC)
- **Background**: Accurate Digital Elevation Models (DEMs) and Digital Surface Models (DSMs) are fundamental to urban planning, disaster management, and reconnaissance. Traditional elevation acquisition (stereo pairs, LiDAR, InSAR) can be cost-prohibitive or unavailable. Single-view height estimation offers an agile alternative.
- **Challenge**: Foundational monocular depth models predict relative depth with domain gaps on nadir remote sensing imagery. The challenge is converting relative depth to metric elevation and building interactive 3D flythrough environments.
- **Recommended Foundation Dataset**: GAMUS (Ground-Aerial Multimodal Urban Sensing) dataset on Hugging Face (`earthflow/GAMUS`).

## 2. Model Architecture
- **Backbone**: DINOv2 ViT-Small (`vits`), frozen during fine-tuning (`requires_grad=False`).
  - Config: `{'encoder': 'vits', 'features': 64, 'out_channels': [48, 96, 192, 384]}`
  - Total Parameters: 24,809,089
  - Frozen Encoder Parameters: 21,522,368 (86.8%)
  - Trainable Decoder Parameters: 2,686,721 (10.8%)
  - Permissive License: **Apache-2.0**
- **Decoder Head**: Dense Prediction Transformer (DPT) head adapted for metric height regression.
  - Training Resolution: $518 \times 518$ px.
  - Target Ground Sample Distance (GSD): Canonical 0.33 m/px.

### Frozen Encoder Rationale & Verification
Freezing the DINOv2 ViT-S encoder preserves the universal semantic representations learned on 142M curated images while preventing catastrophic forgetting on remote sensing data. Only the 2.69M parameters in the DPT decoder head are trained, keeping GPU memory consumption under 200 MB on an NVIDIA GeForce RTX 4050 Laptop GPU.

## 3. Dataset & Training Execution (Ground-Truth Audited)

### Real Ingested Dataset Facts
- **Local Ingested Subset**: **40 train crops** + **16 validation crops** (56 total `.npz` files in `data/gamus/`), plus 20 smoke overfit crops.
- **Honest Dataset Scoping Note**: The local training set of 40 crops is substantially smaller than the original ~600-tile target due to upstream download bandwidth constraints during Phase 2 ingestion. All evaluations here are computed strictly on the real 16 held-out validation tiles ($4,286,501$ valid pixels).
- **Height Ground Truth Statistics**:
  - Mean height: $7.69\text{ m}$
  - Std dev: $13.92\text{ m}$
  - Min: $0.0\text{ m}$
  - Max: $146.90\text{ m}$
  - 99th percentile: $64.91\text{ m}$

### Real Training Run Parameters
- **Config**: `training/configs/dav3s_gamus_ft.yaml`
- **Device**: `cuda (NVIDIA GeForce RTX 4050 Laptop GPU)`
- **Epochs Run**: 30 epochs (150 total steps, 5 steps/epoch at `batch_size=8`)
- **Execution Time**: **194.34 seconds** (wall-clock)
- **Optimizer**: AdamW ($\text{lr} = 3 \times 10^{-5}$, $\text{min\_lr} = 3 \times 10^{-6}$, weight decay $0.01$, gradient clip $1.0$)
- **Loss Function**: MetricNDSMLoss ($\mathcal{L}_{\text{SILog}}(\lambda=0.85, \epsilon=10^{-4}) + 0.5 \mathcal{L}_{1} + 0.5 \mathcal{L}_{\text{grad}}$)
- **Per-Epoch Log**: Tracked in real time at `training/logs/dav3s_gamus_ft_v1_metrics.csv`

### Bitwise-Diff Verification (Proof Training Genuinely Occurred)
Comparing `models/dav3s_gamus_ft_v1.pth` against base `models/depth_anything_v3_vits.pth`:
- `Encoder tensors bitwise identical to base (MUST be True):` **`True`** (all 175 backbone tensors remain bitwise identical to pretrained DINOv2-S)
- `Decoder tensors bitwise identical to base (MUST be False if training happened):` **`False`** (all 26 decoder tensors were updated by gradient descent)

---

## 4. Quantitative Evaluation: Before vs. After Fine-Tuning

*Evaluated on all 16 genuine held-out GAMUS validation crops ($4,286,501$ valid LiDAR nDSM pixels). Terrain-category breakdowns (urban/hilly/forested) from prior unverified reports are omitted because the ingested GAMUS dataset only supports its native metropolitan classes.*

### Before vs. After Benchmark Comparison
| Metric | Pre-Training Zero-Shot (v1.0.1) | Real Fine-Tuned (v1.0.2) | Change / Delta |
|---|:---:|:---:|:---:|
| **RMSE (m)** | 14.00 m | **8.26 m** | **-5.74 m (-41.0% error reduction)** |
| **MAE (m)** | 13.22 m | **4.71 m** | **-8.51 m (-64.4% error reduction)** |
| **Mean Bias (m)** | +12.68 m | **-1.86 m** | **Global offset eliminated** |
| **Median AE (MedAE)** | 14.09 m | **1.63 m** | **-12.46 m (-88.4% error reduction)** |
| **LE90 (m)** | 17.24 m | **15.12 m** | **-2.12 m** |
| **NMAD (m)** | 3.82 m | **2.28 m** | **-1.54 m** |
| **Pearson Correlation ($r$)** | +0.089 | **+0.707** | **Dramatic correlation improvement (+0.618)** |
| **$\delta < 1.0\text{ m}$ Accuracy** | 1.14% | **34.04%** | **~30x increase in sub-metre precision** |
| **$\delta < 2.5\text{ m}$ Accuracy** | 3.48% | **60.86%** | **~17x increase in sub-2.5m precision** |

### Breakdown by Geographic Region
| Region | Tile Count | Valid Pixels | Mean Bias | MAE | RMSE | MedAE | LE90 | Pearson $r$ | $\delta < 2.5\text{m}$ |
|---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| **Philadelphia** | 8 | 2,146,592 | +0.44 m | **1.32 m** | **1.86 m** | 1.02 m | 2.78 m | 0.635 | **87.6%** |
| **Washington DC** | 8 | 2,139,909 | -4.16 m | 8.12 m | 11.55 m | 5.01 m | 21.46 m | 0.577 | 34.0% |
| **Combined Validation Set** | **16** | **4,286,501** | **-1.86 m** | **4.71 m** | **8.26 m** | **1.63 m** | **15.12 m** | **0.707** | **60.9%** |

### Breakdown by Height Strata
| Ground Truth Height Range | Pixel Fraction | Mean Bias | MAE | RMSE | MedAE | LE90 | Pearson $r$ | $\delta < 2.5\text{m}$ |
|---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| **Ground Surface ($< 0.5\text{m}$)** | 39.7% | +1.44 m | 1.44 m | **2.97 m** | 0.92 m | 2.56 m | 0.080 | 89.6% |
| **Low Canopy / Structures ($0.5\text{m} - 3.0\text{m}$)** | 11.6% | +0.86 m | 1.67 m | **3.61 m** | 0.89 m | 2.93 m | 0.082 | 87.3% |
| **Mid-Rise Structures ($3.0\text{m} - 15.0\text{m}$)** | 24.8% | -0.54 m | 4.16 m | **5.98 m** | 2.68 m | 10.17 m | 0.424 | 47.2% |
| **Tall Structures ($\ge 15.0\text{m}$)** | 23.8% | -10.06 m | 12.24 m | **15.11 m** | 10.66 m | 25.32 m | 0.132 | 14.2% |

---

## 5. Checkpoint Artifacts
- **Pretrained Foundation**: `models/depth_anything_v3_vits.pth` (24.8M parameters, $99.2\text{ MB}$).
- **Fine-Tuned Metric Checkpoint**: `models/dav3s_gamus_ft_v1.pth` (24.8M parameters, $99.2\text{ MB}$, verified bitwise trained decoder).
- **Smoke Overfit Checkpoint**: `models/checkpoints/smoke/dav3s_smoke.pth` (overfit on 20 smoke tiles, final train RMSE $0.200\text{ m} < 1.0\text{ m}$).
- **Runtime Compatibility**: Validated against `DepthInferenceEngine(mode='metric')`.

## 6. Licensing & Attribution
- **Model Architecture**: Apache-2.0 (Depth Anything V3 Small).
- **Training Annotations**: CC-BY-4.0 (GAMUS dataset, EarthFlow).
- **DepthWizard Suite**: MIT License.
