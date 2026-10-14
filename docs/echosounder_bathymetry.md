# Echosounder Bathymetry (Processing)

## Overview

This tool processes depth data collected with a **Deeper Pro** echosounder and applies tide corrections using a reference tide gauge dataset. It exports corrected bathymetry points as CSV and GeoJSON files ready to use in GIS software such as QGIS or ArcGIS.

**Video tutorial:** [Watch on YouTube](https://youtu.be/1o9oEFoXRG4?si=4JF5xB074aj_Nsrq)

**Source code:** [github.com/Alerovere/seastrong-field-tools](https://github.com/Alerovere/seastrong-field-tools/tree/main/echosounder_bathymetry)

---

## Field data

The depth points are collected with the [depth and bottom photos survey](depth_bottom_photos.md), together with the bottom photos. This page covers the processing only.

### Calibration and validation

The depth points are used to **calibrate and validate satellite-derived bathymetry** (see [Corridor mapping](corridor_mapping.md)). This is why, at the end of the processing, the corrected depth dataset is **split into two subsets**: one for calibration and one for independent validation of the satellite-derived bathymetry model. Keeping these two subsets separate is essential for an unbiased accuracy assessment.

---

## What the tool does

The processing workflow is implemented in `Process_Echosounder_Data.ipynb` and runs in Google Colab. It calls the core script `bathymetry_tide_processing.py`.

### Inputs

| File | Description |
|------|-------------|
| Deeper Pro scan CSV | Exported from the Deeper app; contains timestamp, depth, latitude, longitude |
| Tide gauge CSV | Water level measurements from a reference tide gauge station |

### Processing steps

| Step | Description |
|------|-------------|
| 1 | Install libraries and connect Google Drive |
| 2 | Set paths to input files |
| 3 | Preview and check the data — counts rows with and without GPS fix |
| 4 | Configure Deeper Pro column names (note: the app exports `longtitude` with a typo — this is intentional and matched by the script) |
| 5 | Set tide gauge column names |
| 6 | Set processing and export options |
| 7 | Run the full processing workflow — merges depth with tide gauge water level, applies correction, and splits the dataset into calibration and validation subsets |
| 8 | Inspect and plot results — depth profile, tide water level, corrected depth histogram, and interactive map |

### Outputs

- **Calibration CSV/GeoJSON** — subset of corrected depth points for satellite-derived bathymetry model calibration
- **Validation CSV/GeoJSON** — independent subset for accuracy assessment of the satellite-derived bathymetry model

---

## Why we do this in SEASTRONG

In **WP1 — Task 1.2** (Mapping the physical environment within corridors), bathymetry maps are a core deliverable. SEASTRONG produces these maps primarily through satellite-derived bathymetry, but this requires field-collected depth points for calibration and validation. The Deeper Pro dataset provides exactly this ground-truth layer across the shallow habitats of each cross-shelf corridor.

In **WP4 — Task 4.5** (The role of spatial connectivity in coastal protection), the bathymetry data is also used to set up and calibrate the hydrodynamic model (XBeach), which simulates wave propagation and attenuation across mangrove forests, seagrass beds, and coral reefs under different connectivity and climate scenarios.

---

## Running the tool

Open the notebook directly in Google Colab — no local Python installation is required.

- **Notebook**: `Process_Echosounder_Data.ipynb`
- **Core script**: `bathymetry_tide_processing.py`

Mount your Google Drive, place your input files in a project folder, and follow the step-by-step instructions in each cell. Cells requiring user input are clearly marked with a `✏️ EDIT HERE` block.
