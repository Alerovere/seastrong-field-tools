# Photo Geotagging

## Overview

This tool geotags time-lapse photos taken during fieldwork using a GPX track recorded simultaneously with a GNSS device. It matches each photo to the closest GPS position based on timestamps, and writes the coordinates directly into the image EXIF metadata. It contributes to **Task 1.2** (mapping the physical environment within corridors) and **Task 1.3** (baseline characterisation of biodiversity, condition, and spatial connectivity within corridors).

---

## Field gear and procedures

> 🎬 *This section will be expanded with content from the field video tutorial. Transcript coming soon.*

---

## What the tool does

> 📓 *This section describes the processing workflow implemented in `Geotag_Bottom_Pictures.ipynb`. To be completed.*

---

## Why we do this in SEASTRONG

Spatially referenced bottom photographs provide a ground-truth layer for habitat mapping within SEASTRONG cross-shelf corridors. In **WP1**, geotagged photos are used alongside drone imagery and bathymetry data to characterise ecosystem extent, condition, and biodiversity along transects. Having accurate GPS coordinates embedded in each image allows photos to be directly imported into GIS software (e.g., QGIS) and linked to other spatial datasets collected in the same corridors.

---

## Running the tool

The processing workflow is implemented as a Google Colab notebook:

- **Notebook**: `Geotag_Bottom_Pictures.ipynb`
- **Core script**: `photo_gpx_geotagging.py`

To run the tool, open the notebook in Google Colab, mount your Google Drive, and follow the step-by-step instructions in each cell.

---

## Video tutorial

> 🎬 *Link to YouTube tutorial coming soon.*
