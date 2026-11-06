# ICESat-2 tool: lidar depths and ground heights

## Overview

The **ICESat-2 tool** (`ICESat2_tool/`, Python package `icesat2_tool`) downloads ICESat-2 lidar data for an area with
[SlideRule](https://slideruleearth.io) (no account needed) and prepares:

- **ATL24 bathymetry**: seabed photons with one flag column per quality rule, and **training** and **validation**
  files split by whole satellite tracks that are chosen once and **locked**, ready for the
  [Bathymetrix-AI](https://github.com/Nasef2017/Bathymetrix-AI) QGIS plugin (see [Satellite-derived bathymetry workflow](sdb_workflow.md));
- **ATL08 / PhoREAL** ground elevation and canopy height per 100 m segment, e.g. over mangroves, converted to
  EGM2008 heights with a verified geoid transformation.

It runs in Google Colab from a folder in your Google Drive and does not use Earth Engine.

---

## Getting the tool

1. Download **[ICESat2_tool.zip](https://github.com/Alerovere/seastrong-field-tools/releases/download/icesat2-tool-latest/ICESat2_tool.zip)** (only this tool, latest version) and unzip it.
2. Upload the `ICESat2_tool` folder anywhere in your Google Drive.
3. Open `ICESat2_tool/notebooks/icesat2_colab.ipynb` from Drive (*Open with → Google Colaboratory*).
4. In the install cell set `TOOLKIT_DIR` to that folder and run the cells in order. Results go to
   `ICESat2_tool/outputs/<NAME>/`.

## Inputs

| Input | Required | Use |
| --- | --- | --- |
| area of interest polygon (GeoJSON, KML, shapefile, GeoPackage) | yes | where to download and clip |
| land polygons or coastline lines (`SHORELINE_FILE`) | no | reject photons on land or within `SHORE_BUFFER` m of it |
| mangrove polygons (`MANGROVE_FILE`) | no | keep only ATL08 segments in mangroves |
| DEMs in EGM2008 heights (`DEM_FILES`) | no | compare DEM and ICESat-2 ground |

```{note}
Without a shoreline file, photons on land or at the water's edge are removed only by ATL24's own classification and
the depth and spike rules. Around reef islands, mangrove fringes and river mouths a digitised shoreline (or
OpenStreetMap land polygons) makes the cleaning much more reliable.
```

---

## ATL24: how the photons are cleaned

The order keeps validation honest: validation tracks are fixed **before** any rule that compares tracks.

| Flag | Rejects a photon when |
| --- | --- |
| `f_missing` | a required value is missing or not finite |
| `f_class` | not classified as seabed (40), or confidence < `MIN_CONFIDENCE` |
| `f_atl24` | ATL24 marks it unreliable (low confidence, invalid Kd, deeper than clarity allows) or vertical uncertainty > `MAX_SIGMA_TVU` |
| `f_depth` | depth < `DEPTH_MIN` or > `DEPTH_MAX` |
| `f_land`, `f_shore` | on land, or closer than `SHORE_BUFFER` to it (only with `SHORELINE_FILE`) |
| `f_spike` | jumps from its neighbours along the track |
| `f_xtrack` | disagrees with ≥ `XT_MIN_PASSES` other **training** passes nearby (information only on validation tracks) |

**Validation tracks.** Whole reference ground tracks go to validation by a rule `rgt % m == k`, chosen once to give
about `VALID_SHARE` of the photons with a similar depth distribution, and saved in
`<NAME>_ICESat2_holdout_lock.json`. Later runs re-use it and assign new tracks by the same rule, so a track never
moves from validation to training. If no split is possible (too few tracks), no training / validation files are
written.

## Outputs

| File (`outputs/<NAME>/`) | Use |
| --- | --- |
| `<NAME>_ATL24_train.gpkg` | Bathymetrix-AI Phase 2 training; depth field **`ortho_h`** (m, EGM2008, negative below) |
| `<NAME>_ATL24_valid.gpkg` | Bathymetrix-AI Phase 5 validation (never in the Phase 4 residual correction) |
| `<NAME>_ATL24_all_with_QC_flags.gpkg` | every photon with its flags, to inspect in QGIS |
| `<NAME>_ICESat2_holdout_lock.json` | the locked validation rule (keep it with the project) |
| `<NAME>_ATL08_ground_canopy.gpkg` | ground (`ground_h_egm08`), canopy heights, QC |
| coverage CSVs, `figures/`, `README_<NAME>_*.md` | what was downloaded, QC summary, method |

## Limitations

- `ortho_h` and the converted ground heights are relative to EGM2008, not local mean sea level or chart datum; the
  tide at each pass is not removed.
- Thresholds are starting values: look at the flags in QGIS before training.
- Cross-track agreement can remove real relief or seabed change.
- Under dense mangrove canopy few photons reach the ground.
- The SDB depth limit and optically-shallow map of the earlier SDB toolkit (now removed) are not included (they need the
  Sentinel-2 composite).

## Sources

ICESat-2 ATL24 (NSIDC, doi:10.5067/ATLAS/ATL24.001), ATL03 / ATL08 (NSIDC); SlideRule (Shean et al. 2023, JOSS
8(81):4982); PhoREAL (Neuenschwander et al.); PROJ / EGM2008 (NGA).
