# Echosounder Bathymetry (GUI tool)

A standalone, browser-based version of the `Process_Echosounder_Data.ipynb`
workflow: merges Deeper Pro echosounder depth data with a tide correction and
exports calibration/validation CSV + GeoJSON for satellite-derived
bathymetry work. See the [readthedocs page](https://seastrong-field-tools.readthedocs.io/en/latest/echosounder_bathymetry.html)
for the field method and why this exists in SEASTRONG.

This is the first tool built on the `apps/` pattern described in
[`../README.md`](../README.md) -- same idea, now as a Docker container
instead of a Colab notebook.

## What's new vs. the notebook

Tide input now supports two sources:

1. **Tide-gauge CSV** -- same as the notebook: upload a file with a
   water-level column and either a combined datetime column or separate
   date/time columns.
2. **FES2022 global tide model** -- predicts the tide at your survey
   coordinates instead of needing a nearby tide gauge at all. Requires a
   local copy of the FES2022 model data (see below) and the corridor's
   latitude/longitude.

Everything downstream (matching, calibration/validation split, CSV/GeoJSON
export, plots, map) is identical regardless of which tide source you use --
both are converted to the same `timestamp, water_level` shape before the
rest of the pipeline runs.

## Running it

```
docker build -f apps/echosounder_bathymetry/Dockerfile -t seastrong-echosounder apps/
docker run --rm -p 8501:8501 seastrong-echosounder
```

Then open http://localhost:8501.

To use the FES2022 option, mount your local FES2022 data as a read-only
volume rather than copying it into the image (it's tens of GB):

```
docker run --rm -p 8501:8501 \
    -v /path/to/fes2022:/data/fes2022:ro \
    seastrong-echosounder
```

Then enter `/data/fes2022` as the "FES2022 model folder" in the app.

### Getting FES2022 data

FES2022 is not bundled here. Request it from AVISO:
<https://www.aviso.altimetry.fr/en/data/products/auxiliary-products/global-tide-fes.html>

Point the app at the folder that contains `fes2022b/` inside it, and don't
reorganize the files -- the app's "What files does this look for?" panel
shows the exact relative paths it expects, read live from the pinned pyTMD
version so it can't drift out of sync with what's actually installed.

The predicted tide is relative to FES2022's mean sea level reference (not
necessarily your local chart datum), and it's the astronomical tide only --
it won't capture storm surge or other meteorological effects the way a real
tide gauge would. Fine for correcting relative depth across a short survey;
worth keeping in mind for anything that needs an absolute datum.

## Running without Docker (development)

```
cd apps
pip install -r echosounder_bathymetry/requirements.txt
streamlit run echosounder_bathymetry/app.py
```

(Run from the `apps/` folder, or add it to `PYTHONPATH`, so the `_shared`
import in `app.py` resolves.)

## Layout

```
echosounder_bathymetry/
  app.py              # Streamlit UI (thin -- no processing logic here)
  core/
    bathymetry_tide_processing.py   # same processing code as scripts/ in the
                                     # notebook version, plus a variant that
                                     # accepts a pre-built tide dataframe
    fes_tide.py                     # FES2022 prediction via pyTMD
  Dockerfile
  requirements.txt
```
