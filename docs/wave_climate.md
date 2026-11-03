# Wave climate and XBeach boundary conditions

## Overview

The **Wave climate** tool (`Wave_climate/`, Python package `wave_climate`) gives the wave, wind, tide and storm-surge
climate at a point offshore of a site, **per month and per season**, and turns it into **representative cases** with
ready-made **XBeach** boundary files. It runs in Google Colab from a folder in your Google Drive and does not use
Earth Engine.

| Data | Source | Coverage |
| --- | --- | --- |
| waves: Hs, peak period Tp, Tm-1,0, Tm02, direction, wind-sea and swell | Copernicus Marine wave reanalysis + analysis (global 0.2° / 1/12°, 3-hourly; Mediterranean 1/24°, hourly) | 1980 (Med 1985) → now |
| waves: Hs, mean period, direction; 10 m wind | ERA5, Climate Data Store point time-series service | 1940 → ~6 days ago, hourly |
| tide, storm surge | GTSM v3 reanalysis (Deltares), Climate Data Store | 1950 → 2024 |

---

## Before you start

You need free accounts at the **Copernicus Climate Data Store** (accept the licences of *ERA5 hourly time-series data
on single levels* and *Global sea level change time series from 1950 to 2050…*) and **Copernicus Marine**. Store the
log-in details as **Colab Secrets** (key icon in Colab's left sidebar; switch on *Notebook access*):

| Secret | Value |
| --- | --- |
| `CDS_KEY` | Climate Data Store personal access token |
| `CMEMS_USERNAME`, `CMEMS_PASSWORD` | Copernicus Marine log-in |

## Getting the tool

1. Download **[Wave_climate.zip](https://github.com/Alerovere/seastrong-field-tools/releases/download/wave-climate-latest/Wave_climate.zip)** (only this tool, latest version) and unzip it.
2. Upload the `Wave_climate` folder anywhere in your Google Drive.
3. Open `Wave_climate/notebooks/wave_climate_colab.ipynb` from Drive (*Open with → Google Colaboratory*).
4. In the install cell set `TOOLKIT_DIR` to that folder and run the cells in order. Results go to
   `Wave_climate/outputs/<NAME>/`.

---

## Steps

1. **Site**: the point (lon, lat) offshore, in open water beyond reefs and islands, near where your XBeach grid
   starts; the Copernicus Marine region (`global` or `med`).
2. **Download** waves and wind (5–20 minutes the first time, then cached).
3. **Climate**: statistics per month and per season (`SEASONS`, your own groups of months, e.g. for Belize *Northers*
   Nov–Feb, *Dry* Mar–May, *Wet* Jun–Nov), Hs × direction, wind × direction and Hs × Tp tables, roses, box plots, and
   a comparison of ERA5 and Copernicus Marine.
4. **Tide and surge**: one year of GTSM tide → harmonic analysis (UTide) → 19-year prediction → tidal levels (HAT,
   MHWS, MHHW, MHW, MHWN, MSL, MLWN, MLW, MLLW, MLWS, LAT), spring and neap ranges, tide type; 30 years of
   daily-maximum surge → percentiles per season and annual maxima.
5. **Cases**: for each season, typical (Hs P50), energetic (P90) and storm (P99) conditions; Tp, direction and wind
   are taken from records with a similar Hs, so they occur together; water level = representative spring (or mean,
   neap) tidal day + surge at the same percentile.

## Outputs

| File (`outputs/<NAME>/`) | Content |
| --- | --- |
| `<NAME>_wave_wind_tide_climate.xlsx` | every table, README sheet first |
| `tables/*.csv` | the same tables as CSV |
| `figures/*.png`, `*.pdf` | monthly box plots, wave and wind roses per season, Hs–Tp per season, tide and surge |
| `xbeach/<case>/` | `jonswap.txt` (`wbctype = jonstable`), `wind.txt`, `tide.txt` (`zs0file`), `params_boundary.txt` |
| `data/*.csv` | the downloaded point series |
| `sources.json` | datasets, model cells and GTSM point used, with distances |

Conventions: Hs and water levels in m, periods in s, wind in m/s; directions **nautical, coming from**; water levels
relative to the **GTSM model mean sea level (1986–2005)**.

```{note}
GTSM files are global (the Climate Data Store cannot cut an area). The tide step downloads them, keeps only the
point nearest to the site and deletes them: expect several minutes per year requested the first time.
```

---

## Using the cases in XBeach

- Paste the lines of `params_boundary.txt` into your `params.txt`; copy the three boundary files next to it.
- Check `thetanaut` and the grid rotation `alfa`: directions are nautical (coming from).
- Shift the water levels to the vertical datum of your bathymetry (GTSM MSL is not chart datum).
- `SPREADING_S` (directional spreading) and `GAMMA` (JONSWAP peak enhancement) are not in the data: choose them
  (≈10 for wind sea, 20–30+ for swell; γ = 3.3 standard). The `swell_share_of_energy` column helps.
- The waves are offshore model values: if the XBeach boundary is in shallow water, transform them first (e.g. SWAN).

## Limitations

- Model data at 0.2–0.5° (waves, wind) and GTSM's coastal resolution (~0.1°): not valid inside lagoons or behind
  reefs; compare with local measurements (see [Wave attenuation](wave_attenuation.md)) and a tide gauge if available.
- Hurricanes are poorly resolved by ERA5 and the wave reanalyses: P99 is not a design storm.
- GTSM has no wave set-up, river discharge or seasonal steric sea-level cycle.
- Using the same percentile for waves and surge is cautious: they do not always peak together.

## Sources

ERA5 (Hersbach et al. 2020); Copernicus Marine GLOBAL_MULTIYEAR_WAV_001_032, GLOBAL_ANALYSISFORECAST_WAV_001_027,
MEDSEA_MULTIYEAR_WAV_006_012, MEDSEA_ANALYSISFORECAST_WAV_006_017; GTSM v3 reanalysis (Muis et al. 2020;
doi:10.24381/cds.a6d42d60); UTide (Codiga 2011).
