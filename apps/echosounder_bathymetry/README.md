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
docker run --rm -p 8501:8501 -v ~:/host seastrong-echosounder
```

Then open http://localhost:8501.

That `-v ~:/host` mounts your whole Mac home folder into the container at
`/host`, read-write. In the app, both the FES2022 folder and the output
folder are click-through browsers rooted at `/host` -- you navigate and pick
subfolders visually instead of typing container paths from memory (there's
also a "jump to path" box if you'd rather paste one, e.g.
`/host/Documents/ocean_tide_20241025`). One mount now covers both the
FES2022 input and the output location below -- you don't need separate `-v`
flags for each.

If you'd rather not share your whole home folder, mount a narrower parent
folder instead (anything that contains both your FES2022 data and where you
want outputs written), e.g. `-v ~/Documents:/host`.

### Saving results to your Mac

By default, results are only offered as a download (.zip) at the end of the
run -- they live inside the container and disappear once it stops. To have
them written straight to a folder on your Mac instead, tick "Also save
results to a folder on this machine" in the app's "3. Output location"
section and browse (or type a new folder name) under `/host` -- e.g. picking
`/host/seastrong_outputs`. Give the survey a site name too (e.g.
`corridor3_mangrove`); results land in
`<folder you picked>/corridor3_mangrove/` on your Mac, one subfolder per
site name so repeated runs don't overwrite each other. Leave the checkbox
unticked to just use the download button instead.

### Getting FES2022 data

FES2022 is not bundled here. Request it from AVISO:
<https://www.aviso.altimetry.fr/en/data/products/auxiliary-products/global-tide-fes.html>

Real downloads don't all come laid out the same way, so the app doesn't
require one exact folder structure. It searches the folder you point it at
for all 34 `<constituent>_fes2022.nc` files (plain or gzip `.nc.gz` --
either is fine), trying, in order: pyTMD's own default nested layout
(`fes2022b/ocean_tide_<date>/`), one level of `fes2022b/` only, a dated
`ocean_tide_<date>/` folder directly, and a flat folder with no subfolders
at all. Whichever one actually has all the files is used automatically --
you don't need to reorganize your copy to match a specific layout. The
app's "What files does this look for?" panel spells this out, and if none
of them match, the error after running lists exactly what was tried and how
many files were found in each place.

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
import in `app.py` resolves. Without Docker there's no `/host` mount, so the
folder pickers fall back to plain text boxes for the FES2022 and output
folders.)

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

apps/_shared/
  folder_picker.py    # click-through folder browser used above, shared
                       # across tools that need to point at a local folder
```
