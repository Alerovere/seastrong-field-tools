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
2. Run the install cell and the import cell.
3. In the **project cell**, set the area of interest, the map projection (UTM zone), the file and folder names and the
   Copernicus Marine region, then run it (this logs in to Earth Engine and mounts Google Drive).
4. Go through the steps in order: `waves` → `prescreen` → (choose the months) → `s2` → `dem`, `habitats` → `icesat2`.
   `transport` is independent and slow (hours of Earth Engine exports).

### How each step is laid out

Every step has four cells:

| Cell | What it contains |
| --- | --- |
| Explanation | what the step does, which data it uses, how to choose each option |
| Options | a Python dictionary with **every** option of the step, its default value and a comment; change values here |
| Run | runs the step and saves the results to Google Drive |
| Report | a plain-language summary of the results and, where something looks unusual, a **suggested option change** with the reason |

Nothing is changed automatically: you read the report, decide, edit the options cell and run the step again. A misspelt
option name stops with a hint instead of being ignored. `ctx.show('s2')` lists the options a step will use and marks
those that differ from the defaults.

### Re-running steps

Every step writes to its own Google Drive folder, named with a short code of its options, e.g.
`SEASTRONG_Belize_south__01_S2_composite_SDB__6b029b39`. If you run a step again **with the same options**, it
re-uses that folder and does not repeat finished downloads or exports. If you **change** an option (e.g. the
composite months), the step and the steps that depend on it get new folders; older results are never overwritten.

Each folder contains a `README_*.md` (method, options, limitations, sources) and a `manifest.json` (all options,
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
number of usable images per year (with the spread between years). Pick a window, write it into `MONTHS` in the Sentinel-2
options cell and run step 1. Within the chosen months, `s2` still removes the individual bad dates.

---

## Choosing the Sentinel-2 date thresholds

The Sentinel-2 step checks every date in two ways:

- **Image checks** measure the problem in the image itself: near-infrared over water (sun glint, haze; `SCENE_MAX_NIR`)
  and red edge B5 over water (turbid water; `SCENE_MAX_B5`). Put these thresholds where the main group of dates ends and
  the scattered tail begins (screening figure).
- **Indirect checks** (rain, wind, offshore waves) only guess that the water might be bad. They are worth keeping only if
  they remove dates that really have more turbid water. The report and the figure *indirect checks* test exactly this:
  they compare B5 of the dates above and below each threshold. *Useful* — keep the check; *no evidence* — relax it or
  switch it off, as the report suggests.

**How many images?** What matters is the number of clear observations per pixel (QA raster, band 1), not the number of
dates. For the default low-percentile (P30) composite, about **10–30 clear observations per pixel** is the sweet spot;
below ~8 use the median (`PERCENTILE=50`). If you have more than enough, be strict. The report's **best images** set
tightens the image checks to the better half of your dates and estimates the clear observations that would remain
(target `TARGET_CLEAR_OBS`).

**Image-by-image check.** `st.s2.checker(ctx)` shows every date with clear water as a true-colour thumbnail of the AOI,
best first, with its screening values and the automatic verdict, and **Accept / Reject / Auto** buttons. Your choices are
saved at once to `<FOLDER_ROOT>__S2_image_decisions.csv` in My Drive and override the automatic checks the next time the
Sentinel-2 step runs (a new composite folder; the Earth Engine screening table is re-used). Reject dates with visible
clouds or shadows over water, haze, sun glint, turbid plumes over the area to map, whitecaps or missing data.

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
