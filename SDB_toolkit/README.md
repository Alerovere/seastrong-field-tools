# SDB toolkit (`seastrong_toolkit`)

User guide: [seastrong-field-tools.readthedocs.io → SDB toolkit](https://seastrong-field-tools.readthedocs.io/en/latest/sdb_toolkit.html)


Python package behind the SEASTRONG WP1 Colab workflow (Earth Engine + Copernicus + ICESat-2). It produces:

- Sentinel-2 composites for satellite-derived bathymetry (Bathymetrix-AI input);
- wave, wind and rain records;
- a pre-screening that suggests the composite months;
- elevation and habitat layers;
- water-motion tracers;
- ICESat-2 bathymetry and mangrove heights.

| Step | Module | Output folder in Google Drive |
|---|---|---|
| Waves, wind, rain at a point (ERA5 time-series service + Copernicus Marine, global or Mediterranean) | `waves` | `<FOLDER_ROOT>__00_Waves__<hash>` |
| Pre-screening: which months for the Sentinel-2 composite | `prescreen` | `…__00b_Prescreen_S2_months__<hash>` |
| Sentinel-2 composite (date screening, tile matching, QA) | `s2` | `…__01_S2_composite_SDB__<hash>` |
| Copernicus DEM 2024_1 DSM, FABDEM, DeltaDTM, masks | `dem` | `…__02_DEM_DSM__<hash>` |
| Allen Coral Atlas, Global Mangrove Watch, canopy height | `habitats` | `…__03_Habitats__<hash>` |
| Turbidity / temperature tracers, HYCOM, ERA5 wind | `transport` | `…__04_Transport_overview__<hash>` |
| ICESat-2 ATL24 QC, locked validation tracks, SDB depth limit, ATL08 mangroves | `icesat2` | `…__05_ICESat2__<hash>` |

## Use in Colab

[![Open in Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/Alerovere/seastrong-field-tools/blob/main/SDB_toolkit/notebooks/seastrong_toolkit_colab.ipynb)

Open `notebooks/seastrong_toolkit_colab.ipynb` (button above) and set `CONFIG` in its first cell (the repository and
folder are already set). The notebook then:

1. clones this repository and installs the package from `SDB_toolkit/`, using a constraints file so Colab's own `google-auth` and related packages are never replaced;
2. writes an example settings file to your Drive if you don't have one yet;
3. runs the steps:

```python
import seastrong_toolkit as st
ctx = st.setup('/content/drive/MyDrive/SEASTRONG/config_belize_south.yaml')
st.waves.run(ctx)
st.prescreen.run(ctx)    # look at the ranking, then set s2.MONTHS in the YAML
ctx = st.setup(CONFIG, login=False, mount_drive=False)   # reload edited settings
st.s2.run(ctx)
```

**Credentials** come only from Colab Secrets (key icon on the left):

| Secret | Use |
|---|---|
| `EE_PROJECT` | Earth Engine project |
| `EE_SERVICE_ACCOUNT_JSON` | optional: Earth Engine service-account key |
| `CDS_KEY` (+ optional `CDS_URL`) | ERA5 from the Climate Data Store |
| `CMEMS_USERNAME`, `CMEMS_PASSWORD` | Copernicus Marine |

They are never written to code, settings files or outputs.

## Settings and re-runs

- `src/seastrong_toolkit/defaults.yaml` lists every setting and what it means. Your YAML only needs the values that differ.
- Each step's folder name contains a **hash of its settings**, of the project settings and of the steps it uses. So:
  - **same settings:** the step re-uses its folder, and finished Earth Engine exports and stages are not repeated;
  - **changed settings** (e.g. `s2.MONTHS`): only that step and the steps downstream of it (`icesat2`) get new folders.
- Every folder has a `manifest.json` with:
  - settings and package versions;
  - Earth Engine task IDs;
  - files with SHA-256 and raster grid;
  - coverage and status.
- ERA5 and SlideRule downloads are cached in `<FOLDER_ROOT>__cache` by request hash.
- `run(ctx, force=True)` repeats a step anyway.
- `project.RUN_TAG` forces new folders for everything.

## Developing

- Set `DEV_CLONE` in the notebook to clone the repository into Drive and install it in editable mode.
- With `%autoreload`, an edited `.py` file is picked up without restarting.
- Offline end-to-end tests with fake services:

```bash
cd SDB_toolkit && pip install -e .[test]
python tests/test_mock_run.py      # or: pytest -q tests
```

## Data sources

ERA5 (Hersbach et al. 2020; C3S CDS, time-series dataset doi:10.24381/1cf1ad76), Copernicus Marine (GLOBAL_MULTIYEAR_WAV_001_032,
GLOBAL_ANALYSISFORECAST_WAV_001_027, MEDSEA_MULTIYEAR_WAV_006_012, MEDSEA_ANALYSISFORECAST_WAV_006_017, OCEANCOLOUR_GLO_BGC_L3_MY_009_103,
OCEANCOLOUR_MED_BGC_L3_MY_009_143), Copernicus Sentinel-2, Landsat Collection 2, Cloud Score+, CHIRPS, Copernicus DEM GLO-30 (2024_1),
FABDEM, DeltaDTM, Allen Coral Atlas, Global Mangrove Watch, HYCOM, ICESat-2 ATL24/ATL08 via SlideRule. Each README lists the
references for its products.
