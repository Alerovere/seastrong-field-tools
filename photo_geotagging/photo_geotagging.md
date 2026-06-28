# Photo Geotagging

## Overview

This tool geotags time-lapse photos taken during fieldwork by matching each image to the closest GPS position from a simultaneously recorded GNSS track. GPS coordinates are written directly into the photo EXIF metadata, making the images immediately usable in GIS software such as QGIS or ArcGIS.

**Video tutorial:** [Watch on YouTube](https://youtu.be/1o9oEFoXRG4?si=4JF5xB074aj_Nsrq)

**Source code:** [github.com/Alerovere/seastrong-field-tools](https://github.com/Alerovere/seastrong-field-tools/tree/main/photo_geotagging)

---

## Field gear and procedures

Bottom photography and bathymetry are collected simultaneously as part of the same field operation. The video tutorial above covers the full setup and field procedure for both datasets together. This page focuses on the photo geotagging component only — for the bathymetry processing workflow see the [Echosounder Bathymetry](echosounder_bathymetry.md) page.

### Equipment used for bottom photography

- **GoPro camera** (or similar action camera) in a waterproof housing — set to timelapse mode and mounted on the underside of the kickboard, facing downward to photograph the bottom
- **Deeper Pro echosounder** — the GPS track recorded by the Deeper app during the bathymetry survey is also used as the GNSS track for photo geotagging, exported as a GPX file
- **Swimming kickboard** — the same floating platform used for the echosounder survey

### Why this approach

The geotagged bottom photos provide a ground-truth layer for habitat mapping within SEASTRONG cross-shelf corridors. Having accurate GPS coordinates embedded in each image allows photos to be directly imported into GIS software and spatially linked to other datasets collected along the same transect — including the bathymetry points, drone imagery, and ecosystem condition assessments.

A key challenge in this workflow is that the GoPro and the GNSS device have independent clocks that are rarely perfectly synchronised. To correct for this, the notebook uses a **reference photo** — taken at the start of the survey while the GNSS screen is visible — to calculate the time offset between the two devices and apply it to the entire photo sequence.

---

## What the tool does

The processing workflow is implemented in `Geotag_Bottom_Pictures.ipynb` and runs in Google Colab. It calls the core script `photo_gpx_geotagging.py`.

### Inputs

| File | Description |
|------|-------------|
| GoPro timelapse photos | Folder of `.JPG` images with camera timestamps in EXIF metadata |
| GPX file | GNSS track exported from the Deeper app or a separate GNSS logger |
| Reference photo | One photo from the sequence showing the GNSS screen, used for clock synchronisation |

### Processing steps

| Step | Description |
|------|-------------|
| 1 | Install libraries and connect Google Drive |
| 2 | Load the geotagging functions |
| 3 | Set paths to input data |
| 4 | Load the photos and the GNSS track |
| 5 | Display the reference photo |
| 6 | Enter the GNSS time shown in the reference photo and calculate the clock offset |
| 7 | Match each photo to the closest GPS position in the track, within a user-defined maximum time delta |
| 8 | Write GPS coordinates into photo EXIF metadata — either copying to a new folder or overwriting originals |
| 9 | Export photo positions as GeoJSON |
| 10 | Display the geotagged photo positions on an interactive map |

### Outputs

- **Geotagged photos** — original images with GPS coordinates written into EXIF metadata, ready for import into QGIS or ArcGIS
- **GeoJSON file** — photo positions as point features, one per image, importable directly into GIS software

---

## Why we do this in SEASTRONG

In **WP1 — Task 1.2** (Mapping the physical environment within corridors), geotagged bottom photos are used alongside drone imagery and bathymetry data to characterise ecosystem extent and condition along transects within each cross-shelf corridor. Spatially referenced photos allow visual ground-truthing of habitat classifications derived from remote sensing.

In **WP1 — Task 1.3** (Baseline characterisation of biodiversity, condition, and spatial connectivity within corridors), the same photo dataset contributes to documenting ecosystem condition and benthic community structure, providing a visual and spatially explicit record that complements quantitative survey data collected by divers.

---

## Running the tool

Open the notebook directly in Google Colab — no local Python installation is required.

- **Notebook**: `Geotag_Bottom_Pictures.ipynb`
- **Core script**: `photo_gpx_geotagging.py`

Mount your Google Drive, place your input files in a project folder, and follow the step-by-step instructions in each cell. Cells requiring user input are clearly marked with a `✏️ EDIT HERE` block. Pay particular attention to **Step 7**, which includes a decision table for choosing the maximum time delta based on your GNSS logging interval.
