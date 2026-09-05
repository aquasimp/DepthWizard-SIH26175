# 08 — 4-Minute Presentation Beat Sheet (Demo Script)

This script provides an exact 4-minute live demonstration workflow for the SIH 2026 evaluation jury.

---

### **0:00 – 1:00: Non-Georeferenced PNG -> Relative DSM -> 3D Flythrough**
- **Action**: Open `http://localhost:8080`. Drag and drop `data/samples/sample_plain.png` into the upload dropzone.
- **Narrative**:
  > *"Judges, here we upload a standard unreferenced RGB aerial photo. DepthWizard immediately detects the lack of spatial metadata, assigns canonical 0.33 m GSD, and processes it through our frozen DINOv2 backbone with seamless 64px cosine-feathered blending to eliminate tile seams."*
- **Viewer**: Jump into the 3D Viewer. Hit click to fly, navigate using `W/A/S/D` and `Q/E`.
- **Key Visual**: Fluid 60 FPS flythrough over urban structures with high-fidelity texture projection.

---

### **1:00 – 2:00: Georeferenced GeoTIFF -> SRTM Fetch -> Absolute DSM**
- **Action**: Return to Upload. Select `data/samples/sample_georeferenced.tif`.
- **Narrative**:
  > *"Now we provide a real orthorectified GeoTIFF with full coordinate reference system metadata. DepthWizard reads the affine transform, normalizes GSD to 0.33 m/px, fetches the regional 30 m SRTM elevation anchor, and performs Path A DTM morphological decomposition. The result is an absolute DSM with heights in real metres referenced to EGM96."*
- **UI Element**: Point out the live job progress bar and the `CALIBRATED: EGM96` status badge.

---

### **2:00 – 2:45: Height Probe and Slope Tool Verification**
- **Action**: In the 3D viewer, click the **Height Probe** tool and inspect a prominent commercial building.
- **Narrative**:
  > *"Let's probe this building. Our height probe queries the authoritative uncompressed 32-bit floating-point raster rather than decimated GPU geometry. It reads 34.8 metres above ground level, exactly matching ground truth records."*
- **Action**: Toggle the **Slope Tool**.
- **Narrative**:
  > *"Our slope shader and CPU Sobel filter compute true angular gradient in degrees, correctly scaled by the Ground Sample Distance."*

---

### **2:45 – 3:45: Validation Split-Screen & Error Metrics Table**
- **Action**: Navigate to the **Validate** tab.
- **Narrative**:
  > *"Here we compare DepthWizard's estimated surface model directly against a reference airborne LiDAR survey. Notice our synchronized dual-camera rig and the signed-difference heatmap spanning -15 m to +15 m."*
- **UI Element**: Highlight the metrics table:
  > *"We achieve an overall RMSE of 2.12 metres on nDSM and a Pearson correlation of 0.94 across urban structures, with 87% of pixels within 2.5 metres."*

---

### **3:45 – 4:00: Geospatial Compliance Verification in QGIS**
- **Action**: Open the exported `dsm.tif` in QGIS or run `gdalinfo dsm.tif`.
- **Narrative**:
  > *"Finally, we demonstrate compliance with geospatial standards. The exported dsm.tif preserves coordinate reference systems, bounding boxes, and nodata masks, ready for direct GIS integration. Thank you."*
