# Echosounder Bathymetry

## Overview

This tool processes depth data collected with a **Deeper Pro** echosounder and applies tide corrections using a reference tide gauge dataset. It exports corrected bathymetry points as CSV and GeoJSON files ready to use in GIS software such as QGIS or ArcGIS.

**Video tutorial:** [Watch on YouTube](https://youtu.be/1o9oEFoXRG4?si=4JF5xB074aj_Nsrq)

**Source code:** [github.com/Alerovere/seastrong-field-tools](https://github.com/Alerovere/seastrong-field-tools/tree/main/echosounder_bathymetry)

---

## Field gear and procedures

In SEASTRONG, bathymetry and bottom photography are collected simultaneously as part of the same field operation, using a simple floating platform that can be deployed by a single operator. The video tutorial above covers the full setup and field procedure for both datasets together. This page focuses on the bathymetry component only — for the photo geotagging workflow see the [Photo Geotagging](photo_geotagging.md) page.

The approach is intentionally low-cost and easy to deploy. It is not designed for high-resolution surveys, but to allow field teams to quickly collect georeferenced depth points over coral reefs and seagrass beds with minimal equipment and logistics.

### Equipment used for bathymetry

- **Deeper Pro echosounder** — a consumer-grade fish finder that records depth and GPS simultaneously, connecting via Wi-Fi to a smartphone
- **Smartphone** running the Deeper app
- **Swimming kickboard** — used as a floating platform; the Deeper Pro is mounted on the underside facing the water, and the smartphone sits on top
- **Dive mask and fins** — the operator swims while pushing the board along the transect

### Why this approach

The bathymetric points collected with this setup are used to **ground-truth and validate satellite-derived bathymetry** produced elsewhere in SEASTRONG. Satellite-derived bathymetry (SDB) relies on optical remote sensing and requires in-situ depth measurements for calibration and accuracy assessment. The Deeper Pro provides a rapid and affordable way to collect these ground-truth points across the shallow coral reef and seagrass habitats that are the focus of SEASTRONG corridor mapping.

This is why, at the end of the processing notebook, the corrected depth dataset is **split into two subsets**: one for calibration and one for independent validation of the satellite-derived bathymetry model. Keeping these two subsets separate is essential for an unbiased accuracy assessment.

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
