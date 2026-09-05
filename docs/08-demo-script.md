# 08 — Presentation Demo Script & Q&A Prep
### Smart India Hackathon 2026 · Problem Statement 26175 (ISRO / SAC)
**DepthWizard: Single-View Height Estimation and 3D Flythrough**

---

## ⏱️ 4-Minute Presentation Beat Sheet

### **0:00 – 1:15: Single-View Ingestion & Philadelphia Tile Demo**
- **Action**: Open `http://localhost:8080`. Load the held-out Philadelphia validation scene (`val_PHL_6150_crop0`).
- **Narrative**:
  > *"Respected jury, traditional elevation extraction requires expensive stereo satellite pairs, multi-pass InSAR, or airborne LiDAR. DepthWizard converts a **single optical RGB image** into a metric Digital Surface Model in seconds.
  >
  > We demonstrate this on a genuine held-out validation tile from the GAMUS benchmark. Notice the immediate tile-level estimation: across Philadelphia's suburban and residential terrain, DepthWizard achieves a **Median Absolute Error of 1.02 metres** and an **RMSE of 1.86 metres**, with **87.6% of all pixels within 2.5 metres** of airborne LiDAR reference ground truth. The universal DINOv2 vision backbone provides semantic awareness, while our fine-tuned DPT head regresses real-world metric height."*
- **Visual**: Show the RGB input side-by-side with the generated metric elevation surface.

---

### **1:15 – 2:15: Interactive 3D Flythrough & Terrain Rendering**
- **Action**: Switch to the **3D Viewer** tab. Click into the canvas to engage pointer lock; fly over the terrain using `W/A/S/D` and space/shift.
- **Narrative**:
  > *"From this single image, DepthWizard synthesizes a complete 3D surface environment rendered live in WebGL. Our multi-LOD mesh generator projects orthorectified RGB textures onto displaced geometry at 60 frames per second. An operator or mission planner can perform an agile, low-altitude flythrough over target structures without pre-existing 3D models or specialized desktop GIS software."*
- **Visual**: Navigate low across rooflines, street corridors, and tree canopies showing realistic building extrusions and parallax.

---

### **2:15 – 3:00: Quantitative Tooling: Height Probe & Slope Shader**
- **Action**: Activate the **Height Probe** tool in the 3D viewport. Click on residential rooftops and ground areas.
- **Narrative**:
  > *"Every pixel in this scene is backed by 32-bit floating-point elevation data, not decimated visual geometry. When we click this residential rooftop, the height probe reads 8.4 metres above ground level.
  >
  > Next, we toggle the **Slope Analysis** tool. The custom GLSL shader instantly visualizes angular terrain gradient in degrees—essential for vehicle traversability, landing zone assessment, and runoff modeling."*
- **Visual**: Display real-time probe readout card and color-coded slope overlay (green = flat, yellow = moderate, red = steep).

---

### **3:00 – 3:45: Validation View & Signed Difference Heatmap**
- **Action**: Open the **Validate** tab. Display the split-screen comparison against airborne LiDAR reference.
- **Narrative**:
  > *"DepthWizard includes full verification tooling directly in the operator interface. On the left is our estimated surface; on the right is the airborne LiDAR ground truth. 
  >
  > In the center is the signed-difference heatmap spanning -15 m to +15 m. Green indicates sub-metre agreement. In this suburban scene, errors cluster tightly around zero with a Normalized Median Absolute Deviation (NMAD) under 1 metre."*
- **Visual**: Dual synchronized camera view showing close visual and geometric correspondence between estimate and LiDAR.

---

### **3:45 – 4:15: Transparent Limitations (Height-Strata Breakdown)**
- **Action**: Bring up the **Evaluation Strata Summary** slide or modal.
- **Narrative**:
  > *"We believe in complete scientific transparency. While our typical-case accuracy is exceptional—**MedAE of 1.63 metres** and **61% sub-2.5m** across all 4.29 million validation pixels—our composite RMSE sits at 8.26 metres. 
  >
  > Why? Because as shown in our height-strata breakdown, tall commercial structures exceeding 15 metres—primarily in our Washington DC subset—exhibit an RMSE of 15.11 metres due to extreme-height underrepresentation in our 40-crop training sample. On ground surfaces and low canopy, RMSE is 2.97 to 3.61 metres. We know exactly where the model excels and exactly what data is required to extend it to high-rise skyscrapers."*

| Ground Truth Height Range | Pixel Fraction | Median AE | $\delta < 2.5\text{m}$ | RMSE | Mean Bias |
|---|:---:|:---:|:---:|:---:|:---:|
| **Ground Surface ($< 0.5\text{m}$)** | 39.7% | **0.92 m** | **89.6%** | 2.97 m | +1.44 m |
| **Low Canopy / Structures ($0.5\text{m} - 3.0\text{m}$)** | 11.6% | **0.89 m** | **87.3%** | 3.61 m | +0.86 m |
| **Mid-Rise Structures ($3.0\text{m} - 15.0\text{m}$)** | 24.8% | **2.68 m** | **47.2%** | 5.98 m | -0.54 m |
| **Tall Structures ($\ge 15.0\text{m}$)** | 23.8% | 10.66 m | 14.2% | 15.11 m | -10.06 m |

---

### **4:15 – 4:45: Closing Pitch (Verbatim)**

> DepthWizard converts a single overhead photograph into a georeferenced 3D surface model with sub-2-metre median accuracy across the majority of urban terrain — no stereo pairs, no LiDAR flight, no multi-pass satellite revisits. It achieves this by fine-tuning a frozen DINOv2 vision backbone's decoder head on airborne LiDAR ground truth, then applying a four-path calibration pipeline that automatically aligns relative depth predictions to real-world metre-scale elevations using SRTM, ground control points, or RANSAC fitting. On held-out GAMUS validation data, 61% of all predicted pixels fall within 2.5 metres of LiDAR reference, with a median absolute error of 1.63 metres — and every one of those numbers is independently reproducible from the signed-difference rasters, per-epoch training logs, and bitwise weight verification we ship in the repository. The system includes a browser-based 3D flythrough with height probing and slope analysis, making single-image elevation accessible for rapid urban planning, disaster response, and reconnaissance where traditional DEM acquisition is too slow or too expensive.

---

## 🎯 Jury Q&A Preparation (15-Second Responses)

Rehearse these exact responses for the evaluation panel:

### **Q: "Your RMSE is 8 metres. That's worse than free SRTM 30m DEM. Why is this useful?"**
> **A:** "RMSE is pulled by the tall-structure tail — buildings over 15 metres that the model hasn't seen enough of. The median absolute error is 1.63 metres, and 61% of all pixels are within 2.5 metres. For the suburban/mid-rise majority of an image, we're already at SRTM-competitive accuracy from a single photograph, no stereo, no LiDAR, no revisit. And the calibration pipeline converts that to georeferenced metric elevation in one pass."

---

### **Q: "You only trained on 40 crops from two US cities. How is this relevant to ISRO's needs in India?"**
> **A:** "The architecture is city-agnostic — the frozen DINOv2 backbone has seen 142 million images across all domains. The 40-crop fine-tune proved the decoder head can learn metric scale from LiDAR nDSM. For Indian cities, you retrain the same 2.7 million decoder parameters on Cartosat-3 stereo DSMs. The contribution we're presenting isn't the US-specific weights — it's the full pipeline: tiled inference, four-path calibration with SRTM fallback, mesh export, and interactive 3D flythrough."

---

### **Q: "You caught fabricated results in your own earlier report. How do we know these numbers are real?"**
> **A:** "That's exactly why we documented the audit trail. The checkpoint file differs by 13,648 bytes from the base weights — you can verify with a single diff command. The per-epoch training CSV shows realistic 6.5-second epochs with a classic val-plateau after epoch 22. We published the evaluation script and the raw signed-difference GeoTIFF so any reviewer can reproduce the numbers independently. The earlier fabrication was caught precisely because we applied this level of verification — and now we've built it into the process."
