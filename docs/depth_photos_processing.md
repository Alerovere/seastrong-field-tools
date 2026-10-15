# Depth and Bottom Photos: Processing

## Overview

This page covers the processing of the data collected with the [depth and bottom photos survey](depth_bottom_photos.md). Two notebooks are used, one for each dataset:

| Dataset | Notebook | Core script | Result |
| --- | --- | --- | --- |
| Depth points | `Process_Echosounder_Data.ipynb` | `bathymetry_tide_processing.py` | Tide-corrected depth points, split into a calibration and a validation set |
| Bottom photos | `Geotag_Bottom_Pictures.ipynb` | `photo_gpx_geotagging.py` | Photos with GPS position in the metadata, and a map layer of their positions |

All outputs are CSV, GeoJSON or geotagged JPG files that open directly in QGIS or ArcGIS.

**Video tutorial:** [Watch on YouTube](https://youtu.be/1o9oEFoXRG4?si=4JF5xB074aj_Nsrq)

**Source code:** [echosounder_bathymetry](https://github.com/Alerovere/seastrong-field-tools/tree/main/echosounder_bathymetry) and [photo_geotagging](https://github.com/Alerovere/seastrong-field-tools/tree/main/photo_geotagging) on GitHub.

---

## Inputs

| File | From | Used for |
| --- | --- | --- |
| Deeper scan (CSV) | Deeper app | Depths |
| GPS track (GPX) | Handheld GNSS | Photo positions |
| Bottom photos (JPG) | Camera | Photos |
| Reference photo and the GPS time shown in it | Camera; time written in the field form | Photo clock offset |
| Water level record (CSV) | Reference tide gauge | Tide correction of depths |

Put all files of one survey in a folder named with the survey ID (e.g. `BZ140327C1bathy`), and keep the [file names](field_resources.md#naming-rules).

---

## Running the notebooks

Both notebooks run in **Google Colab**: no local Python installation is needed.

1. Open the notebook in Colab and connect your Google Drive.
2. Put the input files in a project folder on the Drive.
3. Run the cells in order. Cells that need your input are marked with a `✏️ EDIT HERE` block.

---

## 1. Depth points: tide correction

| Step | What happens |
| --- | --- |
| 1–2 | Install libraries, connect Google Drive, set the paths to the scan and the water level files |
| 3 | Preview the data: counts of rows with and without GPS fix |
| 4–5 | Set the column names of the Deeper scan and of the water level file. The Deeper app exports `longtitude` with a typo: this is expected and matched by the script |
| 6 | Set the processing and export options |
| 7 | Run the processing: each depth is matched with the water level at the same time, corrected for the tide, and the dataset is split into a calibration and a validation set |
| 8 | Check the results: depth profile, water level, histogram of corrected depths, interactive map |

**Outputs:** a **calibration** set and a **validation** set of corrected depth points, each as CSV and GeoJSON. The calibration set is used to fit the satellite-derived bathymetry, the validation set only to assess its accuracy: never mix them, or the accuracy will be overestimated.

---

## 2. Bottom photos: geotagging

The camera clock and the GNSS clock are not synchronised. The notebook computes the offset between them from the reference photo (see [Field procedure](depth_bottom_photos.md#field-procedure)), applies it to all photos, and gives each photo the position of the GPS track at the same time.

| Step | What happens |
| --- | --- |
| 1–3 | Install libraries, connect Google Drive, load the functions, set the paths to the photos and the GPX track |
| 4 | Load the photos and the GPS track |
| 5–6 | Display the reference photo, type the time shown on the GNSS screen, and compute the clock offset |
| 7 | Match each photo to the closest GPS position, within a **maximum time difference**. The notebook has a table to choose this value from the logging interval of the GPS |
| 8 | Write the position into the photo metadata (EXIF), in a copy of the photos or in the originals |
| 9–10 | Export the photo positions as GeoJSON and show them on an interactive map |

**Outputs:** the **geotagged photos** and a **GeoJSON** file with one point per photo.

**Check:** repeat steps 5–6 with the end-of-survey reference photo. The offset should be the same as at the start, within a second or two; if not, the camera clock drifted during the survey.
