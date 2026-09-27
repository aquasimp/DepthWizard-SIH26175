# DepthWizard — CRITICAL WINNING DATA FOR SIH 2026 PPT

---

## ACCURACY (50% of your score)

| What | Number | Why Judges Care |
|---|---|---|
| **Median Absolute Error** | **0.71 m** | Sub-metre from ONE photo — THIS IS YOUR HEADLINE |
| **RMSE** | **4.47 m** | Overall error across all terrain types |
| **MAE** | **2.36 m** | Average pixel-level error |
| **Global Bias** | **-0.30 m** | Near-zero = no systematic over/under estimation |
| **Pearson Correlation** | **0.837** | Strong agreement with real LiDAR |
| **69.60%** of pixels | within **2.5m** of LiDAR truth | 7 out of 10 pixels are accurate |
| **54.24%** of pixels | within **1.0m** of truth | Over half are sub-metre |
| **Ground class accuracy** | **93.34%** within 2.5m, MedAE **0.04m** | 4-centimetre ground accuracy |
| **Water class accuracy** | **98.07%** within 2.5m | Near-perfect |
| **Building RMSE** | **5.43m** (down from 8.53m) | **36.4% improvement** on structures |
| **Philadelphia best** | MedAE **0.31m**, RMSE **3.54m**, **79.81%** < 2.5m | Your strongest demo city |

---

## MODEL DATA

| What | Number |
|---|---|
| **Backbone** | DINOv2 ViT-S (pretrained on 142M images) |
| **Total params** | 24.78M, but only **2.73M trainable** (11%) |
| **Backbone frozen** | **175/175 tensors bitwise identical** to official weights |
| **Model size** | **98 MB** — runs on any laptop |
| **Inference speed (GPU)** | **0.75 seconds** per tile |
| **Inference speed (CPU)** | 4-7 seconds (field-deployable) |
| **VRAM usage** | Under **1.5 GB** |
| **Full pipeline** | **2.6 seconds** end-to-end (upload to 3D view) |

---

## TRAINING DATA

| What | Number |
|---|---|
| **Training crops** | **3,817** (95x scale-up from v1.0.3's 40 crops) |
| **Test crops** | **1,071** held-out (zero leakage) |
| **Test pixels evaluated** | **35.1 Million** LiDAR-verified pixels |
| **Total pixels processed** | **1.16 Billion+** |
| **Cities** | **3** — Washington DC, NYC, Philadelphia |
| **QC drops** | **544 defective crops rejected** (strict quality control) |
| **Training time** | **3.43 hours** on a single RTX 4050 laptop GPU |
| **Epochs** | 60 (best checkpoint at Epoch 48) |
| **Ground truth source** | Airborne LiDAR nDSM (real, not synthetic) |

---

## KEY INNOVATIONS (What sets you apart)

1. **Adaptive Dual-Head Ensemble** — Base head for ground/residential (sub-metre), specialist head for tall buildings (46.2% error reduction), fused via smooth sigmoid gate
2. **4-Tier Scale Calibration** — SRTM, GCP, RANSAC, Relative — handles ANY input type
3. **Identity UV Mapping** — Zero texture projection error by mathematical design
4. **Cosine-feathered tiling** — Seamless large-image inference with zero seam artifacts
5. **Composite Loss** — SILog + L1 + Multi-Scale Gradient (sharp edges + metric accuracy)

---

## VERIFICATION (Shows you're legit)

| What | Result |
|---|---|
| **Automated tests** | **75/75 passed**, 0 failures |
| **Bitwise weight audit** | 175/175 backbone tensors = official weights |
| **Scope fence** | 74 baseline files, **0 violations** |
| **Difference raster verification** | NumPy vs GDAL = **bitwise exact match** |
| **Documentation** | **11 technical documents** shipped |

---

## COST COMPARISON (Judges love this)

| Method | Cost | Time | DepthWizard |
|---|---|---|---|
| LiDAR survey | 50-100 Lakhs | Weeks | **0 per image, 2.6 seconds** |
| Stereo satellite | 5-15 Lakhs, 2+ passes | Days | **1 pass, instant** |
| InSAR | 10-30 Lakhs | Multiple revisits | **Single image** |

---

## CITY-WISE RESULTS (Proves generalization)

| City | RMSE | MAE | MedAE | Pearson r | within 2.5m |
|---|---|---|---|---|---|
| **Washington DC** | 4.94m | 2.91m | 1.33m | **0.877** | 61.59% |
| **New York City** | 4.97m | 2.81m | 0.83m | 0.787 | 65.15% |
| **Philadelphia** | **3.54m** | **1.56m** | **0.31m** | 0.712 | **79.81%** |

---

## HEIGHT-BAND RESULTS (Shows where model excels)

| Height Band | Pixel Share | RMSE | MedAE | within 2.5m |
|---|---|---|---|---|
| **0-2m** (Ground) | 53.3% | 2.74m | **0.06m** | **91.37%** |
| **2-5m** (Low Veg) | 9.5% | 4.17m | 2.56m | 48.30% |
| **5-15m** (Mid-Rise) | 25.1% | 4.81m | 2.45m | 50.60% |
| **15-30m** (Tall) | 10.2% | 7.30m | 4.28m | 31.22% |
| **>30m** (Skyscrapers) | 1.9% | 12.60m | 6.12m | 22.07% |

---

## LAND-COVER CLASS RESULTS

| Class | RMSE | MAE | within 2.5m |
|---|---|---|---|
| **Ground** | **1.79m** | **0.55m** | **93.34%** |
| **Low Vegetation** | 2.63m | 1.00m | 88.82% |
| **Buildings** | 5.43m | 3.23m | 58.45% |
| **Water** | **1.11m** | **0.26m** | **98.07%** |
| **Roads** | 3.21m | 1.24m | 85.57% |
| **Tree Canopy** | 6.40m | 4.75m | 36.56% |

---

## VERSION IMPROVEMENT (Shows progress)

| Metric | v1.0.3 (40 crops) | v1.1.0 (3,817 crops) | Improvement |
|---|---|---|---|
| MedAE | 1.71m | **0.71m** | **-58.7%** |
| RMSE | 6.75m | **4.47m** | **-33.8%** |
| MAE | 3.93m | **2.36m** | **-39.9%** |
| Pearson r | 0.587 | **0.837** | **+0.25** |
| within 2.5m | 58.60% | **69.60%** | **+11 pp** |
| Building RMSE | 8.53m | **5.43m** | **-36.4%** |
| Tall (15-30m) RMSE | 13.58m | **7.30m** | **-46.2%** |

---

## THE ONE SENTENCE TO MEMORIZE

> "DepthWizard achieves 71-centimetre median accuracy from a single photograph, validated against 35 million LiDAR pixels across 3 cities — no stereo, no LiDAR, no multi-pass — in 2.6 seconds."
