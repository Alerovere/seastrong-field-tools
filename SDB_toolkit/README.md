# SDB toolkit (`seastrong_toolkit`)

User guide: [seastrong-field-tools.readthedocs.io → SDB toolkit](https://seastrong-field-tools.readthedocs.io/en/latest/sdb_toolkit.html)


Python package behind the SEASTRONG WP1 Colab workflow (Earth Engine + Copernicus + ICESat-2). It produces:

- Sentinel-2 composites for satellite-derived bathymetry (Bathymetrix-AI input);
- wave, wind and rain records;
- a pre-screening that suggests the composite months;
- elevation and habitat layers;
- water-motion tracers;
- ICESat-2 bathymetry and mangrove heights.

| Step | Module | Output folder (in `outputs/`) |
|---|---|---|
| Waves, wind, rain at a point (ERA5 time-series service + Copernicus Marine, global or Mediterranean) | `waves` | `<FOLDER_ROOT>__00_Waves__<hash>` |
| Pre-screening: which months for the Sentinel-2 composite | `prescreen` | `…__00b_Prescreen_S2_months__<hash>` |
| Sentinel-2 composite (date screening, tile matching, QA) | `s2` | `…__01_S2_composite_SDB__<hash>` |
| Copernicus DEM 2024_1 DSM, FABDEM, DeltaDTM, masks | `dem` | `…__02_DEM_DSM__<hash>` |
| Allen Coral Atlas, Global Mangrove Watch, canopy height | `habitats` | `…__03_Habitats__<hash>` |
| Turbidity / temperature tracers, HYCOM, ERA5 wind | `transport` | `…__04_Transport_overview__<hash>` |
| ICESat-2 ATL24 QC, locked validation tracks, SDB depth limit, ATL08 mangroves | `icesat2` | `…__05_ICESat2__<hash>` |

## Use in Colab, from a folder in your Google Drive

1. Download the repository (*Code → Download ZIP*), unzip it and upload `SDB_toolkit/` (or the whole repository)
   anywhere in your Google Drive.
2. Open `SDB_toolkit/notebooks/seastrong_toolkit_colab.ipynb` from Drive (*Open with → Google Colaboratory*).
3. In the install cell set `TOOLKIT_DIR` to that folder. The code is imported from it, and every result goes to
   `SDB_toolkit/outputs/` (ignored by git). Nothing is fetched from GitHub while you work; `UPDATE_FROM_GITHUB = True`
   replaces the code files with the latest version when you choose to (outputs are kept, old code is backed up).

All options are set **in the notebook**: every step has an explanation cell, an options cell listing every option
with its default and a comment, a run cell and a report cell. The report summarises the results in plain language and
suggests option changes when something looks unusual; nothing is changed automatically.

```python
import seastrong_toolkit as st
ctx = st.setup(PROJECT)                  # PROJECT = dict(AOI_ASSET=..., CRS=..., PREFIX=..., FOLDER_ROOT=..., ...)
ctx.set('waves', WAVES); st.waves.run(ctx); st.waves.report(ctx)
ctx.set('prescreen', PRESCREEN); st.prescreen.run(ctx); st.prescreen.report(ctx)
ctx.set('s2', S2); st.s2.run(ctx); st.s2.report(ctx)      # S2['MONTHS'] chosen from the pre-screening
```

After the Sentinel-2 step, `st.s2.checker(ctx)` opens an image-by-image gallery with Accept / Reject buttons
(decisions saved to `<FOLDER_ROOT>__S2_image_decisions.csv` in `outputs/` and applied at the next run).

**Earth Engine is used as little as possible.** Sentinel-2 dates are first screened on the tile metadata (cloud,
shadow, cirrus, sun-glint angle; read in seconds, no pixels) and on the weather from the waves step; only the dates
that pass get the Earth Engine image check (glint and turbidity of the AOI water), cached date by date
(`S2['SCREENING']`: `'metadata+aoi'` default, `'metadata'`, `'aoi'`). The pre-screening counts clear images from the
tile metadata only (`PRESCREEN['SCENES'] = 'metadata'`), with no Earth Engine export.

`ctx.show('s2')` prints the options a step will use and marks those that differ from the defaults
(`src/seastrong_toolkit/defaults.yaml`). A misspelt option name stops with a hint.

**Credentials** come only from Colab Secrets (key icon on the left):

| Secret | Use |
|---|---|
| `EE_PROJECT` | Earth Engine project |
| `EE_SERVICE_ACCOUNT_JSON` | optional: Earth Engine service-account key |
| `CDS_KEY` (+ optional `CDS_URL`) | ERA5 from the Climate Data Store |
| `CMEMS_USERNAME`, `CMEMS_PASSWORD` | Copernicus Marine |

They are never written to code, notebooks or outputs.

## Options and re-runs

- Each step's Drive folder name contains a **hash of its options**, of the project options and of the steps it uses. So:
  - **same options:** the step re-uses its folder, and finished Earth Engine exports and downloads are not repeated;
  - **changed options** (e.g. `S2['MONTHS']`): only that step and the steps downstream of it (`icesat2`) get new folders.
- Every folder has a `manifest.json` with the options, package versions, Earth Engine task IDs, files (SHA-256, raster
  grid), coverage and status, and a `README_*.md` describing the method and limitations.
- ERA5 and SlideRule downloads are cached in `<FOLDER_ROOT>__cache` by request hash; Sentinel-2 image statistics per date.
- Earth Engine finds export folders by name anywhere in Drive. If it writes to `My Drive/<folder>` instead, the toolkit
  moves the files into `outputs/<folder>`; keep no same-name folders at the top of My Drive (the project cell warns).
- `st.<step>.run(ctx, force=True)` repeats a step anyway; `PROJECT['RUN_TAG']` forces new folders for everything.

## Developing

- Edit the `.py` files in your Drive copy (`src/seastrong_toolkit/`); with `%autoreload` they are picked up without restarting.
- After editing the code without autoreload: `st.reload()`, then run the project and options cells again.
- Offline end-to-end tests with fake services (the second one runs the notebook's own cells):

```bash
cd SDB_toolkit && pip install -e .[test]
python tests/test_mock_run.py
python tests/test_notebook.py
```

## Data sources

ERA5 (Hersbach et al. 2020; C3S CDS, time-series dataset doi:10.24381/1cf1ad76), Copernicus Marine (GLOBAL_MULTIYEAR_WAV_001_032,
GLOBAL_ANALYSISFORECAST_WAV_001_027, MEDSEA_MULTIYEAR_WAV_006_012, MEDSEA_ANALYSISFORECAST_WAV_006_017, OCEANCOLOUR_GLO_BGC_L3_MY_009_103,
OCEANCOLOUR_MED_BGC_L3_MY_009_143), Copernicus Sentinel-2, Landsat Collection 2, Cloud Score+, CHIRPS, Copernicus DEM GLO-30 (2024_1),
FABDEM, DeltaDTM, Allen Coral Atlas, Global Mangrove Watch, HYCOM, ICESat-2 ATL24/ATL08 via SlideRule. Each README lists the
references for its products.
