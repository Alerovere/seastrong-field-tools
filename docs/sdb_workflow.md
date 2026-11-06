# Satellite-derived bathymetry workflow

## Overview

This page puts together the pieces used in SEASTRONG to map shallow-water depth from satellite images with the
[Bathymetrix-AI](https://github.com/Nasef2017/Bathymetrix-AI) QGIS plugin:

| Step | Tool | What it gives |
| --- | --- | --- |
| 1. Calm months and rough-sea days | [Wave climate](wave_climate.md) (Colab) | seasonal wave / wind tables; the list of rough-sea days at the Sentinel-2 overpass |
| 2. Image and context layers | `Earth_Engine/seastrong_sdb_inputs.js` (Earth Engine Code Editor) | Sentinel-2 composite, DEMs, habitats, land and mangrove polygons |
| 3. Training and validation depths | [ICESat-2 tool](icesat2_tool.md) (Colab) | cleaned ICESat-2 ATL24 depths, split into locked training / validation tracks |
| 4. Bathymetry | Bathymetrix-AI (QGIS) | the depth map and its errors |
| 5. Independent check | echosounder surveys ([Corridor mapping](corridor_mapping.md)) | errors against measured depths |

```{important}
Steps 1 and 3 run in **Google Colab**. Step 2 runs in the **Earth Engine Code Editor**
([code.earthengine.google.com](https://code.earthengine.google.com)), a web page with its own map and console: it is
**not** a Colab notebook and is not inside the downloaded tool zips. The only link between them is the list of
rough-sea days, copied from the Colab output into the script.
```

All products use the same area of interest, the same map projection (UTM zone of the site) and the same grid, so
they overlay exactly in QGIS.

---

## Before you start

- An **area of interest** polygon, both as an Earth Engine table asset (for step 2) and as a file in your Google
  Drive (GeoJSON, KML, shapefile or GeoPackage, for step 3). Keep it the same in both.
- Accounts: Google Earth Engine (noncommercial project), Copernicus Climate Data Store and Copernicus Marine
  (for step 1). ICESat-2 needs no account.
- One Drive folder for the Earth Engine exports, created **before** exporting (default `SEASTRONG_SDB_inputs`).

```{note}
Earth Engine noncommercial projects have a monthly computing allowance (150 EECU-hours on the free Community tier).
Above it everything still runs, but slowly ("restricted" or "limited" mode) until the 1st of the next month.
The script does the heavy work only when you export; the Contributor tier (with a Google Cloud billing account,
no charge for noncommercial Earth Engine use) raises the allowance to 1,000 hours.
```

---

## Step 1 — Choose the months and list the rough-sea days

1. Run the [Wave climate](wave_climate.md) notebook (steps 1–2) for an offshore point. The seasonal tables and roses
   show when waves and wind are lowest.
2. In the Earth Engine script, switch on `S2_MONTHS_CHART` (on by default) and run it: a chart shows, for each month,
   how often Sentinel-2 tiles are almost cloud-free. Choose `MONTHS` that are both calm and clear (southern Belize:
   February–April).
3. Run step 5 of the Wave climate notebook (*Sentinel-2 sea-state dates*) with the same `YEARS` and `MONTHS`. Copy
   the printed `var SEA_STATE_EXCLUDE = [...]` line.

## Step 2 — Sentinel-2 composite and context layers (Earth Engine)

**Get the script and the AOI into Earth Engine (once):**

1. Open [seastrong_sdb_inputs.js](https://github.com/Alerovere/seastrong-field-tools/blob/main/Earth_Engine/seastrong_sdb_inputs.js)
   on GitHub and click *Copy raw file* (or download it). It is always the latest version.
2. Open the [Earth Engine Code Editor](https://code.earthengine.google.com) and choose your Earth Engine Cloud
   project (top right).
3. Upload the AOI: *Assets → New → Shape files* (select the `.shp`, `.shx`, `.dbf` and `.prj` files, or a zip of
   them), give it a name and wait for the task to finish in the *Tasks* tab. Copy the asset ID
   (e.g. `projects/<your-project>/assets/AOI`).
4. *Scripts → New → File*, name it (e.g. `seastrong_sdb_inputs`), paste the script and *Save*.

**Set the options at the top of the script:** `AOI_ASSET` (the asset ID), `PREFIX`, `CRS` and `DRIVE_FOLDER`, and
paste the `SEA_STATE_EXCLUDE` line from step 1. Then click *Run*; the maps and tables appear in the Code Editor, and
each file is exported only when you click *Run* next to it in the *Tasks* tab.

When the script is updated in the repository, copy it again and paste it over your saved copy, keeping your option
lines (`AOI_ASSET`, `PREFIX`, `CRS`, `DRIVE_FOLDER`, the pasted date lists and `FIXED_OFFSETS`).

**The composite takes three runs** (each run takes seconds; the exports then run in the *Tasks* tab):

| Run | Settings | Result |
| --- | --- | --- |
| 1 | `EXCLUDE_DATES = null` | two tables: one row per date (water NIR = glint / haze, water B5 = turbidity, rain, reasons) and one line `var EXCLUDE_DATES = [...]` |
| 2 | paste that line; `FIXED_OFFSETS = null` | the brightness offsets between Sentinel-2 tiles are measured (Console) and a preview is shown; check the seams |
| 3 | paste the printed `FIXED_OFFSETS` line | exports: 12-band composite, QA raster, blue temporal standard deviation |

How the composite is made:

- one relative **orbit** only (same viewing and sun-glint geometry everywhere);
- clouds masked per pixel with **Cloud Score+**; glint / whitecaps masked over water (SWIR); a pixel of a date is
  used only if **all 12 bands** are valid;
- **dates dropped** for glint or haze (NIR over water), turbid plumes (B5 over water), heavy rain (CHIRPS, days
  before) and rough seas (the list from step 1);
- per pixel the **30th percentile** of the remaining dates (haze and glint are brighter, so a low percentile
  removes them better than the median); pixels with fewer than `MIN_VALID` clear observations in a tile are left
  empty, tile by tile;
- **tile matching**: ESA processes each 110 km tile separately, so neighbouring tiles differ slightly over dark
  water; each tile is shifted by the median difference over overlapping water.

The other parts of the script are switched on once with `RUN`:

| Switch | Exports |
| --- | --- |
| `DEM` | Copernicus DEM 2024 (DSM), FABDEM and DeltaDTM (bare earth), DSM − FABDEM, water mask; heights EGM2008 |
| `HABITATS` | Allen Coral Atlas benthic / geomorphic / reef mask (5 m), Global Mangrove Watch 2020, mangrove canopy height |
| `ICESAT2_FILES` | land polygons (from the Copernicus DEM water mask, AOI + 2 km) and mangrove polygons for the ICESat-2 tool |

## Step 3 — ICESat-2 training and validation depths

Copy the land polygons and mangrove polygons from the Earth Engine Drive folder next to your AOI file, then run the
[ICESat-2 tool](icesat2_tool.md) notebook with `SHORELINE_FILE` = the land polygons, `MANGROVE_FILE` = the mangrove
polygons and, optionally, `DEM_FILES` = the DEMs from step 2. You get `<NAME>_ATL24_train.gpkg` and
`<NAME>_ATL24_valid.gpkg`, split by whole satellite tracks that are locked once chosen.

## Step 4 — Bathymetrix-AI

| Bathymetrix-AI input | File |
| --- | --- |
| image | `S2_…_12band_Float32.tif` (default band order: Coastal 1, Blue 2, Green 3, Red 4, NIR 8, SWIR 11) |
| training depths (Phase 2) | `<NAME>_ATL24_train.gpkg`, field `ortho_h` (negative below EGM2008) |
| validation depths (Phase 5) | `<NAME>_ATL24_valid.gpkg` — never use it in the Phase 4 residual correction |

## Step 5 — Checks

- **QA raster**: band 1 = clear observations per pixel (aim for 10–30; below ~8 consider the median,
  `PERCENTILE = 50`), band 2 = source tile, band 3 = pixels pushed outside 0–1 by tile matching.
- **Blue temporal standard deviation**: high values (> ~0.01) = water that changed between dates (turbidity,
  residual clouds); depths there are less reliable.
- **Seams**: look at the blue band along tile edges in QGIS (bands 4-3-2 stretched 0–0.15 for true colour).
- **Errors by depth and habitat**: compare the depth map with the validation tracks and with echosounder data,
  split by depth band and by Allen Coral Atlas class (sand, seagrass, coral). Dark seagrass "saturates" at shallower
  depths than bright sand.
- **Datum**: ICESat-2 `ortho_h` and the DEMs are EGM2008 heights, not local mean sea level or chart datum; refer the
  echosounder depths to the same datum before comparing.

## Files in the repository

| Path | What |
| --- | --- |
| `Earth_Engine/seastrong_sdb_inputs.js` | the Earth Engine script (composite, DEMs, habitats, ICESat-2 files) |
| `Wave_climate/` | wave, wind and tide climate; rough-sea days (Colab) |
| `ICESat2_tool/` | ICESat-2 bathymetry and ground heights (Colab) |
