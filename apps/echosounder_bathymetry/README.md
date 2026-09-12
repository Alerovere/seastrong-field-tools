# Echosounder Bathymetry (GUI tool)

A standalone, browser-based version of the `Process_Echosounder_Data.ipynb`
workflow: merges Deeper Pro echosounder depth data with a tide correction and
exports calibration/validation CSV + GeoJSON for satellite-derived
bathymetry work. See the [readthedocs page](https://seastrong-field-tools.readthedocs.io/en/latest/echosounder_bathymetry.html)
for the field method and why this exists in SEASTRONG.

This is the first tool built on the `apps/` pattern described in
[`../README.md`](../README.md) -- same idea as the old Colab notebook, now
as a browser-based GUI.

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

This tool runs directly on your Mac in its own conda environment -- no
Docker. You'll need [Anaconda](https://www.anaconda.com/download) or
[Miniconda](https://docs.conda.io/en/latest/miniconda.html) installed
first; if you already use Anaconda for other things, this creates a
separate environment (`seastrong-echosounder`) and won't touch it.

**Double-click `Launch Echosounder Bathymetry.command`** in this folder.
The first time, it creates the conda environment and installs everything
needed (a few minutes); every time after that it starts in a few seconds.
Your browser opens automatically at http://localhost:8501.

To stop it, close the Terminal window that opened, or press `Ctrl+C` in it.

### First-time macOS security prompt

The first time you double-click it, macOS will likely refuse to run it
("cannot be opened because it is from an unidentified developer"). To allow
it once: right-click (or Control-click) the file → **Open** → **Open** in
the dialog that appears. You only need to do this once; after that,
double-clicking works normally.

### Running from Terminal instead

If you'd rather not use the launcher:

```
conda create -n seastrong-echosounder python=3.11   # first time only
conda activate seastrong-echosounder
cd apps/echosounder_bathymetry
pip install -r requirements.txt                       # first time, or after an update
streamlit run app.py
```

### Saving results to your Mac

By default, results are only offered as a download (.zip) at the end of the
run -- they live in a temporary folder and disappear once the app stops. To
have them written straight to a folder on your Mac instead, tick "Also save
results to a folder on this machine" in the app's "3. Output location"
section and browse to (or type/create) a folder there. Give the survey a
site name too (e.g. `corridor3_mangrove`); results land in
`<folder you picked>/corridor3_mangrove/`, one subfolder per site name so
repeated runs don't overwrite each other. Leave the checkbox unticked to
just use the download button instead.

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

Since the app now runs natively (not in a container), the folder browser
in "2. Tide data" shows your actual Mac folders directly -- browse straight
to wherever you saved the FES2022 download, no path translation needed.

The predicted tide is relative to FES2022's mean sea level reference (not
necessarily your local chart datum), and it's the astronomical tide only --
it won't capture storm surge or other meteorological effects the way a real
tide gauge would. Fine for correcting relative depth across a short survey;
worth keeping in mind for anything that needs an absolute datum.

## Layout

```
echosounder_bathymetry/
  Launch Echosounder Bathymetry.command   # double-click this to run
  app.py              # Streamlit UI (thin -- no processing logic here)
  core/
    bathymetry_tide_processing.py   # same processing code as scripts/ in the
                                     # notebook version, plus a variant that
                                     # accepts a pre-built tide dataframe
    fes_tide.py                     # FES2022 prediction via pyTMD
  requirements.txt

apps/_shared/
  folder_picker.py    # click-through folder browser used above, shared
                       # across tools that need to point at a local folder
```
