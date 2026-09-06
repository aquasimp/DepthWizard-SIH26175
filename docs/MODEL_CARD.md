# DepthWizard v1.1.0 — Model Card: Depth Anything V2 Small Fine-Tuning

## 1. Executive Summary & ISRO / SAC Context
- **Problem Statement**: Smart India Hackathon 2026 · PS 26175 (ISRO / Space Applications Centre)
- **Title**: DepthWizard — Single-View Height Estimation and 3D Flythrough
- **Core Mission**: Estimate dense metric height (metres Above Ground Level, nDSM) from a single optical satellite/aerial image without requiring stereo pairs, multi-pass InSAR, or onboard LiDAR, and render interactive 3D flythrough environments.
- **v1.1.0 Release Objective**: Resolve the data quality and scale-up bottlenecks of v1.0.3 by scaling from 40 training crops to 3,817 quality-controlled crops (1,050 full tiles) across 3 canonical metropolitan areas (Washington DC, New York City, Philadelphia), training for 60 complete epochs on NVIDIA GeForce RTX 4050 GPU, and establishing verifiable, audited benchmarks on 1,071 held-out test crops.

---

## 2. Model Architecture & Parameter Audit

| Component | Specification | Parameter Count | Freeze Status |
| :--- | :--- | :--- | :--- |
| **Vision Backbone** | DINOv2 ViT-Small (`vits`, patch size 14, feature dim 64) | 22,056,576 (89.0%) | **100% Frozen** (`requires_grad=False`) |
| **Decoder Head** | Dense Prediction Transformer (DPT) 4-stage feature fusion | 2,728,513 (11.0%) | **Trainable** (`requires_grad=True`) |
| **Total Model** | Depth Anything V2 Small Metric DPT | **24,785,089** | 2.73M Active Parameters |

### Bitwise Weight Audit Verification
Conducted via `scripts/audit_weights_v110.py` and logged in `artifacts/v1.1.0/weight_diff_v1.1.0.json`:
- **Encoder Bitwise Identity**: **175 / 175 tensors (100.0%)** bitwise identical to official base weights (`models/depth_anything_v2_vits.pth`), with **Max Absolute Diff = 0.0**.
- **Decoder Evolution vs Base**: **60 / 64 tensors (93.8%)** updated by gradient descent (exceeds $\ge 90\%$ requirement).
- **Decoder Evolution vs v1.0.3**: **60 / 64 tensors (93.8%)** distinct from v1.0.3 checkpoint, with **Max Absolute Diff = 0.1109**.

---

## 3. Dataset Ingestion & Quality Control

Sourced from canonical Hugging Face repository `earthflow/GAMUS` (11.54 MB per tile triplet):

| Split | Ingested Tiles | Realized Crops (518x518) | Cities Represented | QC Drop Events | Valid Reference Pixels |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Train** | 1,050 | 3,817 | DC (1,226), NYC (1,191), PHL (1,400) | 383 crops dropped | ~980,000,000 px |
| **Validation** | 150 | 568 | DC (268), PHL (300) | 32 crops dropped | 148,930,000 px |
| **Held-Out Test** | 300 | 1,071 | DC (338), NYC (333), PHL (400) | 129 crops dropped | 35,139,491 px |
| **Total** | **1,500** | **5,456** | **DC, NYC, PHL** | **544 QC events** | **>1.16 Billion px** |

### Quality Control Invariants
- **Zero OMA / JAX Data**: Confirmed 0 files under `data/` containing Omaha or Jacksonville prefixes (corroborating `EarthNets/RSI-MMSegmentation` label quality curation).
- **NaN Rejection**: Crops with $>30\%$ nodata pixels are quarantined and dropped.
- **Unphysical Elevation Filter**: Crops containing heights $< -1.0\text{m}$ are rejected.
- **Split Separation**: Verified bitwise disjoint tile sets across train, val, and test splits (0 shared source tiles).

---

## 4. Training Convergence & Hyperparameters

- **Hardware**: NVIDIA GeForce RTX 4050 Laptop GPU (6,141 MiB VRAM, Performance State `P0`, 35W–49W)
- **Compute Throughput**: 478 batches / epoch (batch size 8) with AMP `torch.float16` forward ViT backbone and `fp32` loss evaluation.
- **Wall-Clock Duration**: 60 epochs completed in **12,348.04 seconds** (~205.8 minutes / ~3.43 hours; mean ~5.1 min/epoch).
- **Optimizer**: AdamW ($\text{base lr} = 3 \times 10^{-5}$, $\text{min lr} = 3 \times 10^{-6}$, weight decay $0.01$, gradient clip $1.0$).
- **Loss Function**: $\mathcal{L} = \mathcal{L}_{\text{SILog}}(\lambda=0.85, \epsilon=10^{-4}) + 0.5 \mathcal{L}_{1} + 0.5 \mathcal{L}_{\text{grad}}$.

### Epoch Convergence Highlights
- **Train Loss**: Monotonically decreased from `5.5885` $\to$ **`5.1660`**
- **Train RMSE**: Improved from `6.270m` $\to$ **`5.816m`**
- **Best Validation RMSE**: **`3.7333m`** (Epoch 48, saved to `models/v1.1.0/best.pt`)
- **Best Tall Structure RMSE ($\ge 15\text{m}$)**: **`7.7341m`** (Epoch 33, saved to `models/v1.1.0/best_tall.pt`)

---

## 5. Held-Out Test Split Benchmarks (1,071 Crops / 35.1M Pixels)

Evaluated across the full held-out test split (zero overlap with training or validation tiles):

### Overall Comparative Benchmark
| Metric | Zero-Shot Base (DAV2-S) | v1.0.3 Baseline | v1.1.0 Best Val (`best.pt`) | v1.1.0 Best Tall (`best_tall.pt`) | Delta (v1.1.0 vs v1.0.3) |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **Mean Bias** | `-5.1805m` | `-1.5609m` | **`-0.3007m`** | `-0.4204m` | **-1.2602m (Near zero)** |
| **MAE** | `5.3994m` | `3.9340m` | **`2.3645m`** | `2.4110m` | **-39.9% error reduction** |
| **RMSE** | `9.5459m` | `6.7508m` | **`4.4672m`** | `4.5352m` | **-33.8% error reduction** |
| **MedAE** | `0.9401m` | `1.7133m` | **`0.7084m`** | `0.7081m` | **-58.7% error reduction** |
| **LE90** | `16.7534m` | `10.8202m` | **`6.8767m`** | `7.1234m` | **-36.4% error reduction** |
| **NMAD** | `1.8400m` | `2.4683m` | **`1.0503m`** | `1.0470m` | **-57.5% error reduction** |
| **Pearson $r$** | `0.1590` | `0.5868` | **`0.8374`** | `0.8323` | **+0.2506 correlation boost** |
| **$\delta < 1.0\text{m}$** | `50.29%` | `36.22%` | **`54.24%`** | `54.04%` | **+18.02 percentage points** |
| **$\delta < 2.5\text{m}$** | `55.80%` | `58.60%` | **`69.60%`** | `68.93%` | **+11.00 percentage points** |

---

### City Breakdown (v1.0.3 vs v1.1.0 Best Val)
| City / Region | Test Pixels | v1.0.3 RMSE | v1.1.0 RMSE | v1.0.3 MAE | v1.1.0 MAE | v1.0.3 Pearson $r$ | v1.1.0 Pearson $r$ | v1.1.0 $\delta < 2.5\text{m}$ |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Washington DC** | 11,336,858 | `8.3790m` | **`4.9374m`** | `5.1842m` | **`2.9100m`** | `0.6252` | **`0.8774`** | **`61.59%`** |
| **New York City** | 10,386,233 | `7.2006m` | **`4.9738m`** | `4.5781m` | **`2.8074m`** | `0.4627` | **`0.7872`** | **`65.15%`** |
| **Philadelphia** | 13,416,400 | `4.4608m` | **`3.5378m`** | `2.3789m` | **`1.5607m`** | `0.4719` | **`0.7122`** | **`79.81%`** |

---

### Height-Band Stratification (v1.0.3 vs v1.1.0 Best Val)
| Height Band | Pixel Share | v1.0.3 RMSE | v1.1.0 RMSE | v1.0.3 MAE | v1.1.0 MAE | v1.1.0 MedAE | v1.1.0 $\delta < 2.5\text{m}$ |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **$0 - 2\text{m}$ (Ground / Surface)** | 53.3% | `3.1010m` | **`2.7428m`** | `1.5504m` | **`0.8663m`** | **`0.0625m`** | **`91.37%`** |
| **$2 - 5\text{m}$ (Low Vegetation)** | 9.5% | `3.7349m` | `4.1720m` | `2.3879m` | `3.0860m` | `2.5618m` | `48.30%` |
| **$5 - 15\text{m}$ (Residential / Mid-Rise)** | 25.1% | `6.2127m` | **`4.8132m`** | `5.1386m` | **`3.5108m`** | **`2.4529m`** | **`50.60%`** |
| **$15 - 30\text{m}$ (Tall Commercial)** | 10.2% | `13.5844m` | **`7.3037m`** | `11.9337m` | **`5.5435m`** | **`4.2755m`** | **`31.22%`** |
| **$> 30\text{m}$ (High-Rise / Skyscrapers)**| 1.9% | `23.5232m` | **`12.5969m`** | `19.5011m` | **`8.5520m`** | **`6.1178m`** | **`22.07%`** (vs 4.8%) |

---

### Semantic Land-Cover Class Performance (v1.0.3 vs v1.1.0 Best Val)
| Land-Cover Class | Test Pixels | v1.0.3 RMSE | v1.1.0 RMSE | v1.0.3 MAE | v1.1.0 MAE | v1.1.0 Pearson $r$ | v1.1.0 $\delta < 2.5\text{m}$ |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **1: Ground** | 5,696,265 | `2.6774m` | **`1.7937m`** | `1.3426m` | **`0.5475m`** | `0.4150` | **`93.34%`** |
| **2: Low Vegetation** | 5,892,708 | `3.5272m` | **`2.6262m`** | `1.9567m` | **`0.9970m`** | `0.1772` | **`88.82%`** |
| **3: Building** | 6,893,940 | `8.5270m` | **`5.4257m`** | `5.2030m` | **`3.2301m`** | **`0.7042`** | **`58.45%`** |
| **4: Water** | 374,995 | `4.6489m` | **`1.1068m`** | `2.2437m` | **`0.2622m`** | `0.2067` | **`98.07%`** |
| **5: Road** | 5,996,687 | `4.3408m` | **`3.2144m`** | `2.0373m` | **`1.2355m`** | **`0.7382`** | **`85.57%`** |
| **6: Tree Canopy** | 8,932,082 | `9.7745m` | **`6.3969m`** | `7.5797m` | **`4.7488m`** | **`0.7641`** | **`36.56%`** |

---

## 6. Checkpoint Directory & Deployment Artifacts

| Checkpoint Path | Epoch | Description | Val RMSE | Tall RMSE |
| :--- | :---: | :--- | :---: | :---: |
| `models/v1.1.0/best.pt` | **48** | Primary release checkpoint (best overall validation RMSE) | **`3.7333m`** | `7.8253m` |
| `models/v1.1.0/best_tall.pt` | **33** | Specialized checkpoint optimized for high-rise urban centers | `3.8574m` | **`7.7341m`** |
| `models/v1.1.0/last.pt` | **60** | Terminal training checkpoint | `3.7689m` | `7.8400m` |

---

## 7. Artifact Manifest
All artifacts generated during this session are saved and verifiable:
- **Evaluation Metrics JSON**: `artifacts/v1.1.0/metrics_v1.1.0.json`
- **Bitwise Weight Audit**: `artifacts/v1.1.0/weight_diff_v1.1.0.json`
- **Dataset Manifest & Stats**: `data/gamus/manifest.csv` and `artifacts/v1.1.0/dataset_stats_v1.1.0.json`
- **Quality Control Log**: `artifacts/v1.1.0/data_qc_report.json`
- **Training Logs**: `logs/v1.1.0/train_metrics.csv` and `logs/v1.1.0/train_metrics.jsonl`
- **Plots & Figures**:
  - `docs/assets/v1.1.0_training_curves.png`
  - `artifacts/v1.1.0/evaluation_error_cdf.png`
  - `artifacts/v1.1.0/evaluation_rmse_by_height.png`
  - `artifacts/v1.1.0/evaluation_tall_scatter.png`
  - `artifacts/v1.1.0/height_distribution.png`
- **Difference Rasters**: GeoTIFFs saved under `artifacts/v1.1.0/rasters/`
