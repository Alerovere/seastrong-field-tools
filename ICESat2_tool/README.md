# ICESat-2 tool (`icesat2_tool`)

ICESat-2 lidar for coastal mapping, downloaded with [SlideRule](https://slideruleearth.io) (no account) and cleaned
with transparent rules. Runs in Google Colab from a folder in your Google Drive. No Earth Engine.

- **ATL24 bathymetry**: seabed photons with one flag column per quality rule, and **training / validation** files
  split by whole satellite tracks chosen once and **locked**, ready for the Bathymetrix-AI QGIS plugin
  (depth field `ortho_h`, m relative to EGM2008, negative below).
- **ATL08 / PhoREAL**: ground elevation and canopy height per 100 m segment (e.g. inside mangrove polygons), with a
  verified ellipsoid → EGM2008 conversion and optional comparison with your DEMs.

User guide: [seastrong-field-tools.readthedocs.io → ICESat-2 tool](https://seastrong-field-tools.readthedocs.io/en/latest/icesat2_tool.html)

## Get it

Download **[ICESat2_tool.zip](https://github.com/Alerovere/seastrong-field-tools/releases/download/icesat2-tool-latest/ICESat2_tool.zip)**
(only this tool, latest released version), unzip it, upload the `ICESat2_tool` folder anywhere in your Google Drive and
open `notebooks/icesat2_colab.ipynb` from there. Results go to `ICESat2_tool/outputs/<NAME>/`.

## Inputs

| Input | Required | Use |
|---|---|---|
| AOI polygon (GeoJSON, KML, shapefile, GeoPackage) | yes | area of interest |
| land polygons or coastline lines (`SHORELINE_FILE`) | no | exact on-land / near-shore rejection; without it these rules are not applied |
| mangrove polygons (`MANGROVE_FILE`) | no | keep only ATL08 segments in mangroves |
| DEMs in EGM2008 heights (`DEM_FILES`) | no | DEM − ICESat-2 ground comparison |

```python
import icesat2_tool as it
ctx = it.setup(dict(NAME='Belize_south', AOI_FILE='.../aoi.geojson', OUTPUT_DIR=OUTPUTS))
it.atl24.run(ctx, ATL24)
it.atl08.run(ctx, ATL08)
```

All options, with defaults and comments, are in the notebook (defaults in `src/icesat2_tool/options.py`).

## Outputs (`outputs/<NAME>/`)

- `<NAME>_ATL24_all_with_QC_flags.gpkg`: every photon with `f_missing`, `f_class`, `f_atl24`, `f_depth`, `f_land`,
  `f_shore`, `f_spike`, `f_xtrack`, `qc_indep_ok`, `qc_ok`, `set`;
- `<NAME>_ATL24_train.gpkg`, `<NAME>_ATL24_valid.gpkg`: clean photons for Bathymetrix-AI;
- `<NAME>_ICESat2_holdout_lock.json`: the locked validation rule (keep it; delete it only to start a new hold-out);
- `<NAME>_ATL08_ground_canopy.gpkg`; coverage tables; `figures/`; `README_<NAME>_ATL24.md`, `README_<NAME>_ATL08.md`.

## Not included

The SDB depth limit (Stumpf-ratio saturation) and the optically-shallow map of the earlier SDB toolkit: they need
the Sentinel-2 composite and are left to Bathymetrix-AI / your Earth Engine workflow.

## Releasing a new version (maintainer)

No manual step is needed: every push to `main` that changes `ICESat2_tool/` runs `.github/workflows/icesat2_tool_release.yml`, which builds
`ICESat2_tool.zip` (this folder without `tests/`) and uploads it to the rolling release `icesat2-tool-latest` (the download link above)
and, the first time a version appears, to a fixed release `icesat2-tool-v<version>`. For a new fixed version, raise `version` in
`pyproject.toml` and `__version__` in `src/icesat2_tool/__init__.py` before pushing. To rebuild by hand: *Actions → ICESat-2 tool zip → Run workflow*.

## Tests

Offline, with a fake SlideRule: `python tests/test_mock_run.py` and `python tests/test_notebook.py`.

## Sources

ICESat-2 ATL24 (NSIDC, doi:10.5067/ATLAS/ATL24.001), ATL03 / ATL08 (NSIDC); SlideRule (Shean et al. 2023, JOSS
8(81):4982); PhoREAL (Neuenschwander et al.); PROJ / EGM2008 (NGA).
