# Wave climate (`wave_climate`)

Wave, wind, tide and storm-surge climate at an offshore point, as tables per month and per season, with
representative seasonal cases and ready-made **XBeach** boundary files. Runs in Google Colab from a folder in your
Google Drive. No Earth Engine.

User guide: [seastrong-field-tools.readthedocs.io → Wave climate](https://seastrong-field-tools.readthedocs.io/en/latest/wave_climate.html)

## Get it

Download **[Wave_climate.zip](https://github.com/Alerovere/seastrong-field-tools/releases/download/wave-climate-latest/Wave_climate.zip)**
(only this tool, latest released version), unzip it, upload the `Wave_climate` folder anywhere in your Google Drive and
open `notebooks/wave_climate_colab.ipynb` from there (*Open with → Google Colaboratory*). Results go to
`Wave_climate/outputs/<NAME>/`.

Credentials as Colab Secrets: `CDS_KEY` (Climate Data Store), `CMEMS_USERNAME`, `CMEMS_PASSWORD` (Copernicus Marine).
Outside Colab, environment variables with the same names.

## Steps

| Step | What it does | Data |
|---|---|---|
| `wc.download.run` | full records at the point; cached | Copernicus Marine waves (Hs, Tp, Tm-1,0, Tm02, direction, wind-sea and swell); ERA5 waves and 10 m wind (CDS point time series) |
| `wc.climate.run` | statistics per month and season, Hs × direction, wind × direction, Hs × Tp, roses, ERA5 vs Copernicus Marine | — |
| `wc.tides.run` | harmonic analysis, tidal levels (HAT … LAT), spring / neap ranges, tide type; daily-maximum surge per season | GTSM v3 reanalysis (Deltares), CDS `sis-water-level-change-timeseries-cmip6` |
| `wc.cases.run` | typical / energetic / storm case per season; XBeach `jonswap.txt`, `wind.txt`, `tide.txt`, params lines; Excel workbook | — |

```python
import wave_climate as wc
ctx = wc.setup(SITE)                     # SITE = dict(NAME=..., POINT=(lon, lat), REGION='global', OUTPUT_DIR=...)
wc.download.run(ctx, DOWNLOAD)
wc.climate.run(ctx, CLIMATE)             # CLIMATE['SEASONS'] = {'Northers': [11, 12, 1, 2], ...}
wc.tides.run(ctx, TIDES, seasons=CLIMATE['SEASONS'])
wc.cases.run(ctx, CASES)
```

All options, with defaults and comments, are in the notebook (defaults in `src/wave_climate/options.py`).

## Outputs (`outputs/<NAME>/`)

- `<NAME>_wave_wind_tide_climate.xlsx`: every table, README sheet first;
- `tables/*.csv`, `figures/*.png|pdf`, `data/*.csv` (the downloaded point series);
- `xbeach/<season>_<level>/`: `jonswap.txt`, `wind.txt`, `tide.txt`, `params_boundary.txt`;
- `sources.json`: datasets, model cells and GTSM point used, with their distance from the point.

Conventions: Hs and levels in m, periods in s, wind in m/s, directions nautical **coming from**; levels relative to
the GTSM model mean sea level (1986–2005), not chart datum.

## Limitations

- Offshore model data: not valid inside lagoons or behind reefs; transform to the XBeach boundary if it is in shallow water.
- No directional spreading in these sources (`SPREADING_S` is your choice); ERA5's point service has no peak period.
- GTSM files are global: the tide step downloads large files and keeps only the nearest point.
- Hurricanes are poorly resolved by ERA5 and the wave reanalyses; P99 is not a design storm.

## Releasing a new version (maintainer)

Raise `version` in `pyproject.toml` and `__version__` in `src/wave_climate/__init__.py`, push, then publish a GitHub
release tagged `wave-climate-v<version>`. The workflow `.github/workflows/wave_climate_release.yml` attaches
`Wave_climate.zip` to it and to the rolling release `wave-climate-latest` (the download link above).

## Tests

Offline, with fake services: `python tests/test_mock_run.py` and `python tests/test_notebook.py`.

## Sources

ERA5 (Hersbach et al. 2020; CDS time-series dataset); Copernicus Marine GLOBAL_MULTIYEAR_WAV_001_032,
GLOBAL_ANALYSISFORECAST_WAV_001_027, MEDSEA_MULTIYEAR_WAV_006_012, MEDSEA_ANALYSISFORECAST_WAV_006_017; GTSM v3
reanalysis (Muis et al. 2020; CDS doi:10.24381/cds.a6d42d60); UTide (Codiga 2011).
