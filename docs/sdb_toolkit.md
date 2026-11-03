# SDB toolkit: satellite-derived bathymetry inputs

## Overview

The **SDB toolkit** (`SDB_toolkit/`, Python package `seastrong_toolkit`) prepares everything needed for
**satellite-derived bathymetry (SDB)** with the [Bathymetrix-AI](https://github.com/Nasef2017/Bathymetrix-AI) QGIS plugin,
plus context layers for the seascape maps of Work Package 1. It runs in Google Colab and uses Google Earth Engine,
the Copernicus Climate Data Store (ERA5), Copernicus Marine and ICESat-2 (via SlideRule).

| Step | What it produces | Used for |
| --- | --- | --- |
| `waves` | Full hourly records at a point offshore: ERA5 waves, wind and rain; Copernicus Marine waves (global or Mediterranean model) | screening, wave climate |
| `prescreen` | Which months give the most usable Sentinel-2 images (calm sea, little rain, clear sky, low turbidity) | choosing the composite months |
| `s2` | 12-band Sentinel-2 composite (reflectance 0–1) for the chosen months, with bad dates removed and tile seams matched | Bathymetrix-AI input image |
| `dem` | Copernicus DEM (2024_1), FABDEM, DeltaDTM, water mask | land / intertidal context |
| `habitats` | Allen Coral Atlas, Global Mangrove Watch, mangrove canopy height | habitat context, error analysis |
| `transport` | Turbidity and temperature tracer maps, regional currents and wind | water-motion overview |
| `icesat2` | Cleaned ICESat-2 depths split into training / validation tracks; depth limit of SDB; mangrove ground heights | Bathymetrix-AI training and validation |

```{note}
The toolkit downloads and processes data automatically, but it does not choose for you: you look at the
pre-screening results, decide the composite months, and check the outputs in QGIS before using them.
```

---

## Before you start

You need free accounts at:

- **Google Earth Engine** (a Cloud project registered for Earth Engine);
- **Copernicus Climate Data Store** (accept the licence of *ERA5 hourly time-series data on single levels* and of *ERA5 hourly data on single levels*);
- **Copernicus Marine**.

Store the log-in details as **Colab Secrets** (key icon in Colab's left sidebar; switch on *Notebook access* for each):

| Secret | Value |
| --- | --- |
| `EE_PROJECT` | Earth Engine Cloud project ID |
| `EE_SERVICE_ACCOUNT_JSON` | *(optional)* service-account key, to log in to Earth Engine without the Google pop-up |
| `CDS_KEY` | Climate Data Store personal access token |
| `CMEMS_USERNAME`, `CMEMS_PASSWORD` | Copernicus Marine log-in |

Secrets stay with your Google account: they are never written into the notebook, the settings file or the outputs.

You also need the **area of interest (AOI)** as an Earth Engine table asset or a GeoJSON file in your Google Drive (WGS84).

---

## Running the toolkit

1. Open the notebook: [![Open in Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/Alerovere/seastrong-field-tools/blob/main/SDB_toolkit/notebooks/seastrong_toolkit_colab.ipynb)
2. In the first cell, set `CONFIG` to where your settings file should live in Drive.
3. Run the install cell, then the setup cell. The first time, an **example settings file** is written to `CONFIG`:
   edit it (AOI, file prefix, wave point, region), then run the setup cell again.
4. Run the steps in order: `waves` → `prescreen` → (choose months) → `s2` → `dem`, `habitats` → `icesat2`.
   `transport` is independent and slow (hours of Earth Engine exports).

### Settings file

The settings file only contains what differs from the defaults. The most important entries:

| Setting | Meaning |
| --- | --- |
| `project: AOI_ASSET` or `AOI_GEOJSON` | the area of interest |
| `project: WAVE_REGION` | `global` (e.g. Belize, Seychelles, Fiji) or `med` (Mediterranean Copernicus Marine model) |
| `waves: POINT` | longitude, latitude of a deep-water point seaward of the reef |
| `s2: MONTHS` | first and last month of the composite (choose with the pre-screening) |
| `s2: YEARS` | years of the composite |
| `s2: ORBIT` | Sentinel-2 relative orbit (one orbit avoids seams between viewing geometries) |

All other settings, with explanations, are in `SDB_toolkit/src/seastrong_toolkit/defaults.yaml`.

### Re-running steps

Every step writes to its own Google Drive folder, named with a short code of its settings, e.g.
`SEASTRONG_Belize_south__01_S2_composite_SDB__6b029b39`. If you run a step again **with the same settings**, it
re-uses that folder and does not repeat finished downloads or exports. If you **change** a setting (e.g. the
composite months), the step and the steps that depend on it get new folders; older results are never overwritten.
After editing the settings file, reload it with the cell under *After editing the settings file*.

Each folder contains a `README_*.md` (method, settings, limitations, sources) and a `manifest.json` (all settings,
software versions, Earth Engine task IDs and file checksums).

---

## Choosing the composite months (pre-screening)

The pre-screening looks at several years of conditions that spoil the colour of the seabed in satellite images:
waves, wind, rain (ERA5 and CHIRPS), clouds, sun glint and turbidity (Sentinel-2 and Landsat), and ocean-colour
transparency (Copernicus Marine).

- A **good day** has waves, wind and rain at or below their usual level for the site (by default the 75th
  percentile of all days of the year), and never above fixed limits (waves 1.5 m, wind 6 m/s, rain 25 mm in 5 days).
- A **usable Sentinel-2 image** is taken on a good day, with at least 60 % of the AOI water cloud-free and low turbidity.

The step shows a calendar of good days, a month-by-condition chart and a ranking of 2-, 3- and 4-month windows by the
number of usable images per year (with the spread between years). Pick a window, write it into `s2: MONTHS`, reload the
settings and run `s2`. Within the chosen months, `s2` still removes the individual bad dates.

---

## Outputs for Bathymetrix-AI

| File (Drive folder) | Use in Bathymetrix-AI |
| --- | --- |
| `S2_…_12band_Float32.tif` (`01_S2_composite_SDB`) | input image; default band order (Coastal 1, Blue 2, Green 3, Red 4, NIR 8, SWIR 11) |
| `…_ATL24_train.gpkg` (`05_ICESat2`) | training depths, field `ortho_h` (negative below EGM2008) |
| `…_ATL24_valid.gpkg` (`05_ICESat2`) | validation depths (tracks never used for training) |
| `…_EXPLORATORY_optically_shallow.gpkg` (`05_ICESat2`) | optional mask of the area where the image can still "see" the seabed (exploratory) |

Validate the final bathymetry also against **echosounder data** referred to the same vertical datum (see
[Corridor mapping](corridor_mapping.md)).

---

## Limitations

- ERA5 and Copernicus Marine are models at 0.08–0.5° resolution: they describe the open sea outside the reef, not the lagoon.
- Turbidity from satellite reflectance is a relative index, not a measured concentration.
- Heights and depths refer to EGM2008, which is not local mean sea level or chart datum.
- The maximum depth that SDB can retrieve depends on water clarity and bottom type; the toolkit estimates one value for the whole AOI.
