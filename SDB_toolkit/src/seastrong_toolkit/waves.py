"""Step 0 — waves, wind and rain at a point (Copernicus Marine + ERA5, direct services).

## Module 0 — Offshore wave time series at a point (Copernicus Marine + ERA5, direct services)

Two wave records at a deep-water point, downloaded from the providers' own services:

| Source | Variables | Resolution | Period | Access |
|---|---|---|---|---|
| **Copernicus Marine**, `WAVE_REGION = 'global'`: WAVERYS reanalysis + global analysis/forecast | Hs (VHM0), peak period (VTPK), mean period Tm-10 (VTM10), mean direction (VMDR) | 0.2° / 0.083°, 3-hourly | 1980 → now | `copernicusmarine` toolbox, Colab Secrets `CMEMS_USERNAME` / `CMEMS_PASSWORD` |
| **Copernicus Marine**, `WAVE_REGION = 'med'`: Mediterranean Sea Waves reanalysis (+ interim) + analysis/forecast | same variables | 1/24° (~4.2 km), **hourly** | 1985 → now | same |
| **ERA5** (ECMWF, ocean-wave model WAM) | Hs, mean period, mean direction, 10 m wind (+ peak period with the gridded API) | 0.5° wave grid, 0.25° atmosphere, **hourly** | 1940 → ~5 days ago | `cdsapi`, Colab Secret `CDS_KEY` |

**What is downloaded.** With `W['MODE'] = 'full'` (default) the **entire record** of each source is saved
for later wave-climate work (ERA5 from `ERA5_START`, Copernicus Marine from the start of the product);
Module 1 uses the subset at each image date. `'screening'` fetches only the Sentinel-2 months.
Copernicus Marine analysis/forecast data are cut at the present time (no forecasts are stored).

**ERA5 via the point time-series service** (`W['ERA5_API'] = 'timeseries'`, default). The CDS offers
*ERA5 hourly time-series data on single levels* (`reanalysis-era5-single-levels-timeseries`): data for one
grid point, stored as time series, so decades come back in one small request instead of hundreds of
gridded downloads. Two limitations: it has no peak wave period (only Hs, mean period and mean direction
among the wave variables), and the wave and wind variables must be requested separately. Because the
service returns the *nearest grid point* — which near a coast can be a land point of the 0.5° wave grid —
the notebook first downloads one month of Hs over a small box (≤ 2° × 2°, the service limit), picks the
nearest sea cell, and then requests the time series exactly at that cell. Requests cover
`ERA5_TS_CHUNK_YEARS` years (the current year separately, so earlier chunks stay cached), are halved if the
CDS refuses them, and end at today − `ERA5_LAG_DAYS` (or your `W['END']`). `'gridded'` keeps the previous
route (`reanalysis-era5-single-levels`, month chunks of a small area, with peak period).

Every ERA5 file is named by a hash of the *complete* request, downloaded to a temporary file, checked
(variables present, first/last time) and only then moved into the cache. Data younger than
`ERA5T_REFRESH_DAYS` are provisional ERA5T and are re-downloaded when the cached copy is older than
`ERA5T_MAX_AGE_DAYS`.

**How to read the comparison.** WAVERYS is driven by ERA5 winds, so ERA5 vs Copernicus Marine is a
**model-to-model comparison**, not an independent validation: agreement shows consistency, not accuracy.
Statistics are given separately for each Copernicus Marine product (reanalysis vs analysis/forecast),
because they are different models at different resolutions. A wave-accuracy claim needs observations
(buoys, altimetry).
"""
import os, re, io, json, time, hashlib, calendar, datetime as dt
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from .core import (bind, manifest, save_manifest, stage_done, stage_get, set_status, require, drive_path,
                   export_image, export_table, wait, task_files, task_status, read_task_csv, record_file,
                   write_readme, find_task, TERMINAL_BAD, OKABE_ITO, panel_labels, save_fig, empty_panel,
                   figure_style, dir_to, in_months, years_filter, aoi_shapely, aoi_bbox_wgs84, _jsonable,
                   secret, CMEMS_REGIONS)
try:
    import ee
except ImportError:  # documentation builds
    ee = None

# Settings and shared objects, set by bind() when run() is called (see core.bind)
AOI_LABEL = CFG = COPDEM_COLLECTION = CRS = CTX = DEM = DRIVE_ROOT = FOLDER_ROOT = GRID_X0 = GRID_X1 = GRID_Y0 \
    = GRID_Y1 = HAB = IS2 = MANIFEST = P = PREFIX = RUN_ID = S2 = TODAY = TR = W = WAIT_FOR_EXPORTS = aoi_fc = \
    centre = chirps = era5_gee = roi = water = None

import calendar, io
ERA5_DATASET = 'reanalysis-era5-single-levels'
ERA5_TS_DATASET = 'reanalysis-era5-single-levels-timeseries'
TS_GROUPS = {'waves': ['significant_height_of_combined_wind_waves_and_swell', 'mean_wave_period', 'mean_wave_direction'],
             'wind': ['10m_u_component_of_wind', '10m_v_component_of_wind', 'total_precipitation']}   # cannot be combined
SHORT_NAMES = {'swh': 'hs', 'mwp': 'tm', 'pp1d': 'tp', 'mwd': 'mwd', 'u10': 'u10', 'v10': 'v10', 'tp': 'rain_mm'}
SCALE = {'rain_mm': 1000.0}          # ERA5 total precipitation: m (hourly accumulation) -> mm
def data_end(lag_days):
    """Last complete day to request: today - lag, or W['END'] if earlier."""
    end = TODAY - dt.timedelta(days=lag_days)
    if W['END']:
        end = min(end, dt.date.fromisoformat(W['END']))
    return end
def wave_periods(end, source):
    """Inclusive (start, end) date periods to download for 'era5' or 'cmems'."""
    if W['MODE'] == 'full':
        start = W['ERA5_START'] if source == 'era5' else (W['CMEMS_START'] or CMEMS_REGIONS[W['REGION']]['start'])
        return [(dt.date.fromisoformat(start), end)]
    out = []
    for y in range(W['SCREENING_YEARS'][0], W['SCREENING_YEARS'][1] + 1):
        a = dt.date(y, W['SCREENING_MONTHS'][0], 1) - dt.timedelta(days=1)
        b = dt.date(y, W['SCREENING_MONTHS'][1], calendar.monthrange(y, W['SCREENING_MONTHS'][1])[1])
        if a <= end: out.append((a, min(b, end)))
    return out
def month_specs(periods):
    """(year, month, first_day, last_day) for every calendar month touched by the periods."""
    specs = []
    for a, b in periods:
        y, m = a.year, a.month
        while (y, m) <= (b.year, b.month):
            d0 = a.day if (y, m) == (a.year, a.month) else 1
            d1 = b.day if (y, m) == (b.year, b.month) else calendar.monthrange(y, m)[1]
            specs.append((y, m, d0, d1))
            y, m = (y + 1, 1) if m == 12 else (y, m + 1)
    return specs
def era5_chunks(specs):
    """Group full months of the same year into chunks of <= ERA5_CHUNK_MONTHS; partial months alone."""
    chunks, cur = [], []
    for y, m, d0, d1 in specs:
        full = d0 == 1 and d1 == calendar.monthrange(y, m)[1]
        if full and cur and cur[-1][0] == y and cur[-1][1] == m - 1 and len(cur) < W['ERA5_CHUNK_MONTHS'] and cur[-1][4]:
            cur.append((y, m, d0, d1, full)); continue
        if cur: chunks.append(cur)
        cur = [(y, m, d0, d1, full)]
    if cur: chunks.append(cur)
    return chunks
def era5_request(variables, chunk, area):
    y = chunk[0][0]; months = [c[1] for c in chunk]
    days = range(1, 32) if all(c[4] for c in chunk) else range(chunk[0][2], chunk[0][3] + 1)
    return {'product_type': ['reanalysis'], 'variable': sorted(variables), 'year': [str(y)],
            'month': [f'{m:02d}' for m in months], 'day': [f'{d:02d}' for d in days],
            'time': [f'{h:02d}:00' for h in range(24)], 'area': [round(a, 4) for a in area],
            'data_format': 'netcdf', 'download_format': 'unarchived'}
def _chunk_dates(chunk):
    a = dt.date(chunk[0][0], chunk[0][1], chunk[0][2]); b = dt.date(chunk[-1][0], chunk[-1][1], chunk[-1][3])
    return a, b
def _validate_nc(path, variables, a, b):
    """Open the NetCDF, check the expected variables and return (first, last, n_times)."""
    import xarray as xr
    with xr.open_dataset(path) as ds:
        tdim = 'valid_time' if 'valid_time' in ds.dims else 'time'
        have = {SHORT_NAMES.get(v) for v in ds.data_vars}
        want = {W['ERA5_VARIABLES'][v] for v in variables}
        if not want <= have:
            raise ValueError(f'missing variables {want - have}')
        t = pd.to_datetime(ds[tdim].values)
    return t.min(), t.max(), len(t)
def era5_fetch(client, group, variables, chunk, area, cache):
    """Download one chunk (cached by request hash); split if the CDS says it is too large."""
    req = era5_request(variables, chunk, area)
    h = hashlib.sha256(json.dumps({'dataset': ERA5_DATASET, **req}, sort_keys=True).encode()).hexdigest()[:12]
    a, b = _chunk_dates(chunk)
    f = os.path.join(cache, f'era5_{group}_{a:%Y%m%d}-{b:%Y%m%d}_{h}.nc'); meta_f = f + '.json'
    provisional = b >= TODAY - dt.timedelta(days=W['ERA5T_REFRESH_DAYS'])
    if os.path.exists(f) and os.path.exists(meta_f):
        meta = json.load(open(meta_f))
        age = (dt.datetime.now(dt.timezone.utc) - pd.Timestamp(meta['downloaded_utc'])).days
        if not (provisional and age > W['ERA5T_MAX_AGE_DAYS']):
            return [f]
        print(f'  ERA5 {group} {a}..{b}: provisional (ERA5T), cached copy {age} days old -> refreshing')

    def split():
        if len(chunk) > 1:
            k = len(chunk) // 2
            return era5_fetch(client, group, variables, chunk[:k], area, cache) + \
                   era5_fetch(client, group, variables, chunk[k:], area, cache)
        y, m, d0, d1, _ = chunk[0]                      # one month still too large: halve the days
        if d1 <= d0: raise RuntimeError(f'ERA5 request for {a} refused even for one day')
        mid = (d0 + d1) // 2
        return era5_fetch(client, group, variables, [(y, m, d0, mid, False)], area, cache) + \
               era5_fetch(client, group, variables, [(y, m, mid + 1, d1, False)], area, cache)

    if os.path.exists(f + '.toolarge'):               # remembered from an earlier run
        return split()
    for attempt in range(1, W['CDS_RETRIES'] + 1):
        print(f'  ERA5 {group} {a}..{b}: requesting (queued on the CDS) ...')
        try:
            client.retrieve(ERA5_DATASET, req, f + '.part')
            t0, t1, n = _validate_nc(f + '.part', variables, a, b)
            os.replace(f + '.part', f)
            exp_last = pd.Timestamp(b) + pd.Timedelta(hours=23)
            json.dump(dict(request=req, dataset=ERA5_DATASET, downloaded_utc=dt.datetime.now(dt.timezone.utc).isoformat(),
                           first=str(t0), last=str(t1), n_times=n, provisional=provisional,
                           complete=bool(t0 <= pd.Timestamp(a) and t1 >= exp_last)), open(meta_f, 'w'), indent=1)
            return [f]
        except Exception as e:
            msg = str(e).lower()
            if os.path.exists(f + '.part'): os.remove(f + '.part')
            if 'cost' in msg or 'too large' in msg:
                print('    too large for the CDS -> splitting'); open(f + '.toolarge', 'w').close()
                return split()
            if attempt == W['CDS_RETRIES']: raise
            print(f'    attempt {attempt} failed ({str(e)[:120]}); retrying in {30 * attempt} s'); time.sleep(30 * attempt)
def nearest_valid_cell(da, lon, lat, tdim):
    """Index (iy, ix) of the cell nearest to (lon, lat) that has data at some time."""
    latn = 'latitude' if 'latitude' in da.dims else 'lat'
    lonn = 'longitude' if 'longitude' in da.dims else 'lon'
    valid = da.notnull().any(tdim).transpose(latn, lonn).values
    lons, lats = np.meshgrid(da[lonn].values, da[latn].values)
    d2 = (((lons - lon + 180) % 360) - 180) ** 2 + (lats - lat) ** 2
    d2[~valid] = np.inf
    if not np.isfinite(d2).any():
        return None
    iy, ix = np.unravel_index(np.argmin(d2), d2.shape)
    return {latn: iy, lonn: ix}, float(lons[iy, ix]), float(lats[iy, ix])
def era5_point_frame(files, lon, lat, cell=None):
    """Read cached chunks and return a time-indexed frame at the chosen cell (wave cell found on first use)."""
    import xarray as xr
    frames = []
    for f in files:
        with xr.open_dataset(f) as ds:
            if 'expver' in ds.dims: ds = ds.max('expver')        # ERA5 / ERA5T stacked in older files
            tdim = 'valid_time' if 'valid_time' in ds.dims else 'time'
            cols = {v: SHORT_NAMES[v] for v in ds.data_vars if v in SHORT_NAMES}
            if not cols: continue
            if cell is None:
                if 'swh' not in ds: continue
                cell = nearest_valid_cell(ds['swh'], lon, lat, tdim)
                if cell is None: raise RuntimeError('No ERA5 wave cell near the point: move W["POINT"] offshore')
            _, clon, clat = cell
            latn = 'latitude' if 'latitude' in ds.dims else 'lat'; lonn = 'longitude' if 'longitude' in ds.dims else 'lon'
            pt = ds.sel({latn: clat, lonn: clon}, method='nearest').load()
            frames.append(pd.DataFrame({c: pt[v].values * SCALE.get(c, 1.0) for v, c in cols.items()},
                                       index=pd.to_datetime(pt[tdim].values, utc=True)))
    out = pd.concat(frames).sort_index() if frames else pd.DataFrame()
    return out[~out.index.duplicated(keep='last')], cell
def cds_client():
    import cdsapi
    key = secret('CDS_KEY', purpose='ERA5 from the Climate Data Store')
    url = secret('CDS_URL', required=False) or 'https://cds.climate.copernicus.eu/api'
    return cdsapi.Client(url=url, key=key, quiet=True)
def era5_series_gridded(lon, lat, periods):
    client = cds_client()
    d = W['ERA5_SEARCH_DEG']
    area = [lat + d, lon - d, lat - d, lon + d]       # N W S E
    cache = drive_path('cache', 'era5'); os.makedirs(cache, exist_ok=True)
    groups = [('waves', ERA5_WAVE_VARS)] + ([('wind', ERA5_WIND_VARS)] if W['ERA5_WIND'] and ERA5_WIND_VARS else [])
    files = {g: [] for g, _ in groups}
    for chunk in era5_chunks(month_specs(periods)):
        for g, vars_ in groups:
            files[g] += era5_fetch(client, g, list(vars_), chunk, area, cache)
    waves, cell = era5_point_frame(files['waves'], lon, lat)
    out = waves
    if files.get('wind'):
        wind, _ = era5_point_frame(files['wind'], lon, lat, cell)
        out = waves.join(wind, how='outer')
    if {'u10', 'v10'} <= set(out.columns):
        out['wind_speed'] = np.hypot(out.u10, out.v10)
        out['wind_from'] = (np.degrees(np.arctan2(out.u10, out.v10)) + 180) % 360
    out.index.name = 'time'
    out = out.reset_index()
    out['source'] = 'ERA5'; out['cell_lon'] = cell[1]; out['cell_lat'] = cell[2]
    print(f'  ERA5: {len(out):,} hourly values {out.time.min()} -> {out.time.max()} at {cell[1]:.2f}, {cell[2]:.2f}')
    return out, sorted(files['waves'] + files.get('wind', []))
def open_cds_nc(path):
    """Open a CDS NetCDF (the service may deliver it zipped); returns a loaded xarray Dataset."""
    import xarray as xr, zipfile
    if zipfile.is_zipfile(path):
        with zipfile.ZipFile(path) as z:
            names = [n for n in z.namelist() if n.endswith('.nc')]
            if not names: raise ValueError(f'{path}: zip without NetCDF')
            frames = [xr.open_dataset(io.BytesIO(z.read(n))).load() for n in names]
        return xr.merge(frames, compat='override')
    with xr.open_dataset(path) as ds:
        return ds.load()
def ts_frame(ds):
    """Time-series dataset -> DataFrame indexed by UTC time with short column names (+ lat/lon if present)."""
    df = ds.to_dataframe().reset_index()
    tcol = 'valid_time' if 'valid_time' in df else 'time'
    keep = {v: SHORT_NAMES[v] for v in ds.data_vars if v in SHORT_NAMES}
    out = df[[tcol] + list(keep) + [c for c in ('latitude', 'longitude') if c in df]].rename(columns={tcol: 'time', **keep})
    out['time'] = pd.to_datetime(out['time'], utc=True)
    for k, f in SCALE.items():
        if k in out: out[k] = out[k] * f
    return out
def ts_fetch(client, req, cache, label, a, b, provisional):
    """One cached time-series request (hash of the full request; atomic write; validated)."""
    h = hashlib.sha256(json.dumps({'dataset': ERA5_TS_DATASET, **req}, sort_keys=True).encode()).hexdigest()[:12]
    f = os.path.join(cache, f'era5ts_{label}_{a:%Y%m%d}-{b:%Y%m%d}_{h}.nc'); meta_f = f + '.json'
    if os.path.exists(f) and os.path.exists(meta_f):
        meta = json.load(open(meta_f))
        age = (dt.datetime.now(dt.timezone.utc) - pd.Timestamp(meta['downloaded_utc'])).days
        if not (provisional and age > W['ERA5T_MAX_AGE_DAYS']):
            return f
        print(f'  ERA5 {label} {a}..{b}: provisional (ERA5T), cached copy {age} days old -> refreshing')
    for attempt in range(1, W['CDS_RETRIES'] + 1):
        print(f'  ERA5 time series {label} {a}..{b}: requesting ...')
        try:
            client.retrieve(ERA5_TS_DATASET, req, f + '.part')
            ds = open_cds_nc(f + '.part')
            have = {SHORT_NAMES.get(v) for v in ds.data_vars}
            want = {W['ERA5_VARIABLES'].get(v) for v in req['variable']}
            if not want <= have: raise ValueError(f'missing variables {want - have}; got {list(ds.data_vars)}')
            t = ts_frame(ds)['time']
            os.replace(f + '.part', f)
            json.dump(dict(request=req, dataset=ERA5_TS_DATASET, downloaded_utc=dt.datetime.now(dt.timezone.utc).isoformat(),
                           first=str(t.min()), last=str(t.max()), n_times=int(t.nunique()), provisional=provisional,
                           complete=bool(t.min() <= pd.Timestamp(a, tz='UTC') and t.max() >= pd.Timestamp(b, tz='UTC') + pd.Timedelta(hours=23))),
                      open(meta_f, 'w'), indent=1)
            return f
        except Exception as e:
            msg = str(e).lower()
            if os.path.exists(f + '.part'): os.remove(f + '.part')
            if ('cost' in msg or 'too large' in msg or 'limit' in msg) and (b - a).days > 31:
                raise _TooLarge()
            if attempt == W['CDS_RETRIES']: raise
            print(f'    attempt {attempt} failed ({str(e)[:120]}); retrying in {30 * attempt} s'); time.sleep(30 * attempt)
class _TooLarge(Exception):
    pass
def ts_range(client, label, variables, lon, lat, a, b, cache):
    """Time series for [a, b] at (lon, lat); halves the date range while the CDS refuses it."""
    req = {'variable': sorted(variables), 'location': {'longitude': round(lon, 4), 'latitude': round(lat, 4)},
           'date': [f'{a:%Y-%m-%d}/{b:%Y-%m-%d}'], 'data_format': 'netcdf'}
    provisional = b >= TODAY - dt.timedelta(days=W['ERA5T_REFRESH_DAYS'])
    try:
        return [ts_fetch(client, req, cache, label, a, b, provisional)]
    except _TooLarge:
        mid = a + (b - a) / 2
        print(f'    too large for the CDS -> splitting at {mid}')
        return (ts_range(client, label, variables, lon, lat, a, mid, cache) +
                ts_range(client, label, variables, lon, lat, mid + dt.timedelta(days=1), b, cache))
def ts_chunks(a, b):
    """Blocks of ERA5_TS_CHUNK_YEARS whole years (stable cache keys) + the current, still-growing year."""
    out, y = [], a.year
    while y < b.year:
        y1 = min(y + W['ERA5_TS_CHUNK_YEARS'] - 1, b.year - 1)
        out.append((max(a, dt.date(y, 1, 1)), dt.date(y1, 12, 31))); y = y1 + 1
    out.append((max(a, dt.date(b.year, 1, 1)), b))
    return out
def era5_ts_cell(client, lon, lat, cache):
    """Nearest SEA cell of the ERA5 wave grid: one month of Hs over a small box (time-series 'area' option)."""
    d = min(W['ERA5_SEARCH_DEG'], 1.0)                       # service limit: 2 x 2 degrees
    req = {'variable': ['significant_height_of_combined_wind_waves_and_swell'],
           'area': [round(lat + d, 4), round(lon - d, 4), round(lat - d, 4), round(lon + d, 4)],
           'date': ['2020-01-01/2020-01-31'], 'data_format': 'netcdf'}
    f = ts_fetch(client, req, cache, 'cellprobe', dt.date(2020, 1, 1), dt.date(2020, 1, 31), False)
    df = ts_frame(open_cds_nc(f))
    cells = df.groupby(['latitude', 'longitude'])['hs'].apply(lambda v: v.notna().mean()).reset_index()
    cells = cells[cells.hs > 0.9]
    if cells.empty: raise RuntimeError('No ERA5 wave cell near the point: move W["POINT"] offshore')
    d2 = (((cells.longitude - lon + 180) % 360) - 180) ** 2 + (cells.latitude - lat) ** 2
    c = cells.loc[d2.idxmin()]
    return float(c.longitude), float(c.latitude)
def era5_series_ts(lon, lat, periods):
    client = cds_client()
    cache = drive_path('cache', 'era5'); os.makedirs(cache, exist_ok=True)
    clon, clat = era5_ts_cell(client, lon, lat, cache)
    print(f'  ERA5 wave cell nearest to the point: {clon:.2f}, {clat:.2f}')
    groups = ['waves'] + (['wind'] if W['ERA5_WIND'] else [])
    files = {g: [] for g in groups}
    for pa, pb in periods:
        for a, b in (ts_chunks(pa, pb) if W['MODE'] == 'full' else [(pa, pb)]):
            for g in groups:
                files[g] += ts_range(client, g, TS_GROUPS[g], clon, clat, a, b, cache)
    frames = {}
    for g in groups:
        df = pd.concat([ts_frame(open_cds_nc(f)) for f in files[g]]).drop(columns=['latitude', 'longitude'], errors='ignore')
        frames[g] = df.drop_duplicates('time', keep='last').set_index('time').sort_index()
    out = frames['waves'].join(frames['wind'], how='outer') if 'wind' in frames else frames['waves']
    if {'u10', 'v10'} <= set(out.columns):
        out['wind_speed'] = np.hypot(out.u10, out.v10)
        out['wind_from'] = (np.degrees(np.arctan2(out.u10, out.v10)) + 180) % 360
    out.index.name = 'time'
    out = out.reset_index()
    out['source'] = 'ERA5 (time-series service)'; out['cell_lon'] = clon; out['cell_lat'] = clat
    print(f'  ERA5: {len(out):,} hourly values {out.time.min()} -> {out.time.max()}')
    return out, sorted(files['waves'] + files.get('wind', []))
def era5_series(lon, lat, periods):
    return era5_series_ts(lon, lat, periods) if W['ERA5_API'] == 'timeseries' else era5_series_gridded(lon, lat, periods)
def cmems_series(lon, lat, periods):
    """Point series of all W['CMEMS_VARIABLES'] from each dataset of the chosen region, cut at 'now'."""
    import copernicusmarine as cm
    user = secret('CMEMS_USERNAME', purpose='Copernicus Marine')
    pw = secret('CMEMS_PASSWORD', purpose='Copernicus Marine')
    t0 = min(p[0] for p in periods).isoformat(); t1 = (max(p[1] for p in periods) + dt.timedelta(days=1)).isoformat()
    now = pd.Timestamp.now(tz='UTC')
    frames, info = [], []
    d = W['CMEMS_SEARCH_DEG']
    for ds_id in W['CMEMS_DATASETS']:
        kw = dict(dataset_id=ds_id, minimum_longitude=lon - d, maximum_longitude=lon + d,
                  minimum_latitude=lat - d, maximum_latitude=lat + d, start_datetime=t0, end_datetime=t1,
                  username=user, password=pw)               # credentials passed per request, nothing stored on disk
        ds = None
        for vars_ in (list(W['CMEMS_VARIABLES']), ['VHM0']):     # fall back to Hs only if a variable is missing
            try:
                try:
                    ds = cm.open_dataset(variables=vars_, coordinates_selection_method='inside', **kw)
                except TypeError:
                    ds = cm.open_dataset(variables=vars_, **kw)
                break
            except Exception as e:
                err = str(e)
        if ds is None:
            print(f'  {ds_id}: not available ({err[:150]})'); info.append(dict(dataset=ds_id, status='failed', error=err[:300])); continue
        tdim = 'time'
        # nearest sea cell from the first two days only (does not load the whole box over the whole record)
        cell = nearest_valid_cell(ds['VHM0'].isel({tdim: slice(0, 48)}), lon, lat, tdim)
        if cell is None:
            print(f'  {ds_id}: no sea cell near the point'); info.append(dict(dataset=ds_id, status='no_sea_cell')); continue
        sel, clon, clat = cell
        names = {v: c for v, c in W['CMEMS_VARIABLES'].items() if v in ds}
        pt = ds[list(names)].isel(**sel).load().to_dataframe().reset_index()
        df = pt[[tdim] + list(names)].rename(columns={tdim: 'time', **names})
        df['time'] = pd.to_datetime(df['time'], utc=True)
        df = df[df.time <= now].dropna(subset=['hs'])           # no forecasts
        df['source'] = ds_id; df['cell_lon'] = clon; df['cell_lat'] = clat
        print(f'  {ds_id}: {len(df):,} values {df.time.min()} -> {df.time.max()} at {clon:.3f}, {clat:.3f}; vars {list(names)}')
        info.append(dict(dataset=ds_id, status='ok', first=str(df.time.min()), last=str(df.time.max()), variables=list(names),
                         cell_lon=clon, cell_lat=clat, attrs={k: str(v)[:200] for k, v in ds.attrs.items()
                                                                 if k in ('title', 'source', 'product_version', 'references')}))
        frames.append(df)
    if not frames: raise RuntimeError(f'No Copernicus Marine wave data downloaded (region {W["REGION"]}: is W["POINT"] inside it?)')
    out = pd.concat(frames).drop_duplicates('time', keep='first').sort_values('time').reset_index(drop=True)
    return out, info
def yearly(periods):
    """Split long periods into calendar years (for readable coverage tables)."""
    out = []
    for a, b in periods:
        for y in range(a.year, b.year + 1):
            out.append((max(a, dt.date(y, 1, 1)), min(b, dt.date(y, 12, 31))))
    return out
def keep_periods(df, periods):
    m = np.zeros(len(df), bool)
    for a, b in periods:
        m |= (df['time'] >= pd.Timestamp(a, tz='UTC')) & (df['time'] < pd.Timestamp(b, tz='UTC') + pd.Timedelta(days=1))
    return df[m].reset_index(drop=True)
def coverage_table(df, periods, nominal_h, label):
    """Requested vs actual coverage per period: n values, expected, first/last, largest gap."""
    rows = []
    for a, b in periods:
        t0, t1 = pd.Timestamp(a, tz='UTC'), pd.Timestamp(b, tz='UTC') + pd.Timedelta(hours=24 - nominal_h)
        t1 = min(t1, pd.Timestamp.now(tz='UTC').floor(f'{nominal_h}h') - pd.Timedelta(hours=nominal_h))   # nothing expected after 'now'
        s = df.loc[(df.time >= t0) & (df.time <= t1), 'time'].sort_values() if df is not None else pd.Series([], dtype='datetime64[ns, UTC]')
        exp = int((t1 - t0) / pd.Timedelta(hours=nominal_h)) + 1
        hrs = ((s - t0) / pd.Timedelta(hours=1)).values if len(s) else np.array([])     # unit-safe (ns / us)
        gaps = np.diff(np.r_[0.0, hrs, (t1 - t0) / pd.Timedelta(hours=1)])
        rows.append(dict(source=label, requested_start=str(a), requested_end=str(b), n=len(s), expected=exp,
                         first=str(s.min()) if len(s) else None, last=str(s.max()) if len(s) else None,
                         max_gap_h=float(gaps.max()) if len(gaps) else None,
                         status='complete' if len(s) >= exp and gaps.max() <= 1.5 * nominal_h else ('partial' if len(s) else 'missing')))
    return pd.DataFrame(rows)
def window_stats(series, t_end, hours, nominal_h, how='max'):
    """Statistic of `series` (time-indexed) in the window (t_end - hours, t_end]; with sample count,
    largest gap (h, incl. window edges) and status ok / partial / missing."""
    t0 = t_end - pd.Timedelta(hours=hours)
    s = series[(series.index > t0) & (series.index <= t_end)].dropna()
    if not len(s): return np.nan, 0, float(hours), 'missing'
    hrs = ((s.index - t0) / pd.Timedelta(hours=1)).values               # unit-safe (ns / us)
    gap = float(np.diff(np.r_[0.0, hrs, float(hours)]).max())
    val = float(s.max() if how == 'max' else s.mean())
    return val, len(s), gap, ('ok' if gap <= 1.5 * nominal_h else 'partial')
def load_series(required=True):
    """Series saved by the waves step with the current settings: {'era5': DataFrame, 'cmems': DataFrame}."""
    st = manifest('waves')['stages'].get('waves')
    if not st:
        if required:
            raise RuntimeError("The waves step has not been run with the current settings: run seastrong_toolkit.waves.run(ctx) first")
        return {}
    out = {}
    for k in ('cmems', 'era5'):
        if st.get(f'{k}_csv') and os.path.exists(st[f'{k}_csv']):
            df = pd.read_csv(st[f'{k}_csv']); df['time'] = pd.to_datetime(df['time'], utc=True); out[k] = df
    return out
def waves_to_gee_asset(waves, asset_id):
    """Optional: upload the series as a GEE table (time_ms, hs) for the Code Editor script."""
    feats = [ee.Feature(None, {'time_ms': int(t.value // 1_000_000), 'hs': float(h)})
             for t, h in zip(waves['time'], waves['hs'])]
    chunks = [feats[i:i + 5000] for i in range(0, len(feats), 5000)]
    fc = ee.FeatureCollection([ee.FeatureCollection(c) for c in chunks]).flatten()
    t = ee.batch.Export.table.toAsset(collection=fc, description='waves_to_asset', assetId=asset_id)
    t.start(); return t


def run(ctx=None, force=False):
    """Run this step. Same settings = same folder: finished exports and stages are re-used
    (force=True starts them again)."""
    global CMEMS_END, COV_WAVES, ERA5_END, ERA5_WAVE_VARS, ERA5_WIND_VARS, P_CMEMS, P_ERA5, STATS_WAVES, \
           WAVES_CMEMS, WAVES_ERA5, WAVE_SERIES, _c, _ld, _nc, ax_a, ax_b, ax_c, ax_d, ax_e, b, bottom, bp, \
           cls, cm_info, cm_lab, cmap, col, comp_txt, cov, d, d_, data, dd, dirs, done, era5_cols, era5_files, \
           fig, freq, g, gs, hb, hs, i, idx, k, lab, lat, lim, lon, lw, m, months, ok, p, pos, sect, sel, src, \
           txt, width, x
    ctx = bind(globals(), 'waves', ctx)
    ctx.force = force
    figure_style()
    ERA5_WIND_VARS = {k: v for k, v in W['ERA5_VARIABLES'].items() if v in ('u10', 'v10', 'rain_mm')}   # atmospheric grid
    ERA5_WAVE_VARS = {k: v for k, v in W['ERA5_VARIABLES'].items() if k not in ERA5_WIND_VARS}  # wave grid
    WAVE_SERIES = {}          # 'era5' / 'cmems' -> DataFrame (used by the Module 1 screen)
    WAVES_CMEMS, WAVES_ERA5, STATS_WAVES = None, None, {}
    lon, lat = W['POINT']
    if W['REGION'] == 'med' and not (-18.125 <= lon <= 36.29 and 30.19 <= lat <= 45.98):
        raise ValueError(f"W['POINT'] {W['POINT']} is outside the Mediterranean wave model domain: set WAVE_REGION = 'global' or move the point")
    ERA5_END = data_end(W['ERA5_LAG_DAYS']); CMEMS_END = data_end(0)
    P_ERA5, P_CMEMS = wave_periods(ERA5_END, 'era5'), wave_periods(CMEMS_END, 'cmems')
    print(f"Mode '{W['MODE']}', Copernicus Marine region '{W['REGION']}', ERA5 API '{W['ERA5_API']}': "
          f"ERA5 {P_ERA5[0][0]} -> {ERA5_END}, Copernicus Marine {P_CMEMS[0][0]} -> {CMEMS_END}")
    done = stage_get('waves')
    cov = []
    if done:                                     # resumed run: read the saved series
        print('  waves stage already done in this run: reading saved CSVs')
        _ld = load_series()
        WAVES_CMEMS, WAVES_ERA5 = _ld.get('cmems'), _ld.get('era5')
    else:
        if W['CMEMS']:
            print('Copernicus Marine waves')
            WAVES_CMEMS, cm_info = cmems_series(lon, lat, P_CMEMS)
            WAVES_CMEMS = keep_periods(WAVES_CMEMS, P_CMEMS)
            p = drive_path('waves', f'{PREFIX}_CMEMS_waves_point.csv'); WAVES_CMEMS.to_csv(p, index=False); record_file(p)
            MANIFEST['coverage']['cmems_datasets'] = cm_info
        if W['ERA5']:
            print('ERA5 waves (Climate Data Store)')
            WAVES_ERA5, era5_files = era5_series(lon, lat, P_ERA5)
            WAVES_ERA5 = keep_periods(WAVES_ERA5, P_ERA5)
            p = drive_path('waves', f'{PREFIX}_ERA5_waves_point.csv'); WAVES_ERA5.to_csv(p, index=False); record_file(p)
            MANIFEST['coverage']['era5_cache_files'] = [os.path.basename(f) for f in era5_files]
    if W['CMEMS']: cov.append(coverage_table(WAVES_CMEMS, yearly(P_CMEMS), W['CMEMS_STEP_H'], 'CMEMS ' + W['REGION']))
    if W['ERA5']: cov.append(coverage_table(WAVES_ERA5, yearly(P_ERA5), 1, 'ERA5'))
    COV_WAVES = pd.concat(cov, ignore_index=True) if cov else pd.DataFrame()
    COV_WAVES.to_csv(drive_path('waves', f'{PREFIX}_waves_coverage.csv'), index=False)
    _c = COV_WAVES[['source', 'requested_start', 'requested_end', 'n', 'expected', 'max_gap_h', 'status']]
    _nc = _c[_c.status != 'complete']
    print(_c.to_string(index=False) if len(_c) <= 20 else
          (_nc.to_string(index=False) + '\n' if len(_nc) else '') + f'  ({int((_c.status == "complete").sum())} complete years not listed)')
    MANIFEST['coverage']['waves'] = COV_WAVES.to_dict('records')
    if not done:
        stage_done('waves', cmems_csv=drive_path('waves', f'{PREFIX}_CMEMS_waves_point.csv') if WAVES_CMEMS is not None else None,
                   era5_csv=drive_path('waves', f'{PREFIX}_ERA5_waves_point.csv') if WAVES_ERA5 is not None else None)
    set_status('waves', 'complete' if len(COV_WAVES) and (COV_WAVES.status == 'complete').all() else 'partial',
               sources=[s for s, d in (('cmems', WAVES_CMEMS), ('era5', WAVES_ERA5)) if d is not None])
    if WAVES_CMEMS is not None: WAVE_SERIES['cmems'] = WAVES_CMEMS
    if WAVES_ERA5 is not None: WAVE_SERIES['era5'] = WAVES_ERA5

    # ---------------- model-to-model comparison, per Copernicus Marine product ----------------
    comp_txt = ''
    if WAVES_CMEMS is not None and WAVES_ERA5 is not None:
        m = WAVES_CMEMS[['time', 'hs', 'source']].merge(WAVES_ERA5[['time', 'hs']], on='time', suffixes=('_cmems', '_era5'))
        for src, g in m.groupby('source'):
            d_ = g.hs_era5 - g.hs_cmems
            STATS_WAVES[src] = dict(n=len(g), bias=float(d_.mean()), rmse=float(np.sqrt((d_ ** 2).mean())),
                                    r=float(g.hs_era5.corr(g.hs_cmems)),
                                    si=float(np.sqrt(((d_ - d_.mean()) ** 2).mean()) / g.hs_cmems.mean()))
        comp_txt = '; '.join(f"{k}: N={v['n']}, ERA5−CMEMS bias {v['bias']:+.2f} m, RMSE {v['rmse']:.2f} m, "
                             f"SI {v['si']:.2f}, r={v['r']:.2f}" for k, v in STATS_WAVES.items())
        print('  model comparison (not validation):', comp_txt)

    # ---------------- publication figure ----------------
    fig = plt.figure(figsize=(7.2, 8.0))
    gs = fig.add_gridspec(3, 2, height_ratios=[1, 1.25, 1.25], hspace=0.62, wspace=0.42)
    ax_a = fig.add_subplot(gs[0, :])
    cm_lab = f"Copernicus Marine {'Med' if W['REGION'] == 'med' else 'global'} ({W['CMEMS_STEP_H']}-hourly)"
    for d, lab, col, lw in [(WAVES_ERA5, 'ERA5 (hourly)', OKABE_ITO[0], 0.35),
                            (WAVES_CMEMS, cm_lab, OKABE_ITO[1], 0.5)]:
        if d is not None:
            dd = d.set_index('time')['hs']
            dd = dd.reindex(pd.date_range(dd.index.min(), dd.index.max(), freq='1h' if 'ERA5' in lab else f"{W['CMEMS_STEP_H']}h"))   # gaps -> breaks
            ax_a.plot(dd.index, dd.values, lw=lw, color=col, label=lab, alpha=0.85)
    ax_a.set_ylim(top=ax_a.get_ylim()[1] * 1.3)                 # headroom for the legend
    ax_a.set_ylabel('$H_s$ (m)'); ax_a.legend(loc='upper left', ncol=2)
    ax_a.set_title(f'Significant wave height offshore of the reef ({lat:.2f}°N, {abs(lon):.2f}°W)'
                   + (' — screening months only' if W['MODE'] == 'screening' else ', full records'), loc='left')

    ax_b = fig.add_subplot(gs[1, 0])
    if STATS_WAVES:
        hb = ax_b.hexbin(m.hs_cmems, m.hs_era5, gridsize=40, mincnt=1, cmap='viridis', bins='log', linewidths=0)
        lim = [0, np.nanpercentile(np.r_[m.hs_cmems, m.hs_era5], 99.9) * 1.05]
        ax_b.plot(lim, lim, 'k--', lw=0.8); ax_b.set_xlim(lim); ax_b.set_ylim(lim); ax_b.set_aspect('equal')
        ax_b.set_xlabel('Copernicus Marine $H_s$ (m)'); ax_b.set_ylabel('ERA5 $H_s$ (m)')
        ax_b.set_title('Model comparison', loc='left')
        txt = '\n'.join(f"{('reanalysis' if '_my_' in k else 'analysis/fc')}: N={v['n']:,}\n  bias {v['bias']:+.2f} m, "
                        f"RMSE {v['rmse']:.2f} m\n  SI {v['si']:.2f}, r {v['r']:.2f}" for k, v in STATS_WAVES.items())
        ax_b.text(0.04, 0.96, txt, transform=ax_b.transAxes, va='top', fontsize=6.5, bbox=dict(fc='white', ec='none', alpha=0.8))
        fig.colorbar(hb, ax=ax_b, shrink=0.8, label='count')
    else:
        empty_panel(ax_b, 'needs both sources')

    ax_c = fig.add_subplot(gs[1, 1])
    months = np.arange(1, 13)
    for k, (d, lab, col) in enumerate([(WAVES_ERA5, 'ERA5', OKABE_ITO[0]), (WAVES_CMEMS, 'CMEMS', OKABE_ITO[1])]):
        if d is None: continue
        data = [d.loc[d.time.dt.month == mo, 'hs'].dropna().values for mo in months]
        pos = [mo + (k - 0.5) * 0.36 for mo, x in zip(months, data) if len(x)]
        bp = ax_c.boxplot([x for x in data if len(x)], positions=pos, widths=0.32, patch_artist=True,
                          showfliers=False, medianprops=dict(color='k', lw=0.8), whiskerprops=dict(lw=0.6), capprops=dict(lw=0.6))
        for b in bp['boxes']: b.set(facecolor=col, alpha=0.7, lw=0.5)
        ax_c.plot([], [], 's', color=col, alpha=0.7, label=lab)
    ax_c.axvspan(W['SCREENING_MONTHS'][0] - 0.5, W['SCREENING_MONTHS'][1] + 0.5, color='0.85', zorder=0, label='composite months (SCREENING_MONTHS)')
    ax_c.set_xticks(months); ax_c.set_xticklabels(list('JFMAMJJASOND'))
    ax_c.set_ylabel('$H_s$ (m)'); ax_c.set_title('Monthly distribution', loc='left')
    ax_c.legend(loc='upper center', bbox_to_anchor=(0.5, -0.12), ncol=3)

    ax_d = fig.add_subplot(gs[2, 0], projection='polar')
    if WAVES_ERA5 is not None and 'mwd' in WAVES_ERA5:
        ok = WAVES_ERA5[['mwd', 'hs']].dropna()
        dirs = np.deg2rad(ok['mwd'].values); hs = ok['hs'].values
        sect = np.deg2rad(np.arange(0, 360, 22.5)); width = np.deg2rad(22.5)
        cls = [0, 0.5, 1.0, 1.5, 2.0, np.inf]; bottom = np.zeros(len(sect))
        idx = np.round(dirs / width).astype(int) % 16
        cmap = plt.get_cmap('viridis', len(cls) - 1)
        for i in range(len(cls) - 1):
            sel = (hs >= cls[i]) & (hs < cls[i + 1])
            freq = np.bincount(idx[sel], minlength=16) / max(len(hs), 1) * 100
            ax_d.bar(sect, freq, width=width * 0.95, bottom=bottom, color=cmap(i), edgecolor='white', lw=0.3,
                     label=f'{cls[i]}–{cls[i + 1]:g} m' if np.isfinite(cls[i + 1]) else f'> {cls[i]} m')
            bottom += freq
        ax_d.set_theta_zero_location('N'); ax_d.set_theta_direction(-1)
        ax_d.set_title('ERA5 wave rose (from, % of time)', loc='left', pad=14)
        ax_d.tick_params(axis='y', labelsize=6.5)
        ax_d.legend(loc='upper center', bbox_to_anchor=(0.5, -0.16), ncol=3, fontsize=7)
    else:
        ax_d.set_axis_off()

    ax_e = fig.add_subplot(gs[2, 1])
    for d, lab, col in [(WAVES_ERA5, 'ERA5', OKABE_ITO[0]), (WAVES_CMEMS, 'CMEMS', OKABE_ITO[1])]:
        if d is None: continue
        x = np.sort(d['hs'].dropna().values); ax_e.plot(x, 1 - np.arange(len(x)) / len(x), color=col, label=lab)
    ax_e.axvline(W['PLOT_HS_THRESHOLD'], color=OKABE_ITO[3], ls='--', lw=0.9, label=f"screen threshold {W['PLOT_HS_THRESHOLD']} m")
    ax_e.set_yscale('log'); ax_e.set_xlabel('$H_s$ (m)'); ax_e.set_ylabel('exceedance probability')
    ax_e.set_title('Exceedance', loc='left'); ax_e.legend(loc='lower left')
    panel_labels([ax_a, ax_b, ax_c, ax_d, ax_e])
    save_fig(fig, 'waves', f'{PREFIX}_Fig_waves_ERA5_vs_CMEMS'); plt.show()

    era5_cols = ', '.join(c for c in ['hs', 'tm', 'tp', 'mwd', 'u10', 'v10', 'wind_speed', 'wind_from', 'rain_mm']
                          if WAVES_ERA5 is not None and c in WAVES_ERA5.columns)
    write_readme('waves', 'README_00_Waves', f"""
    # Offshore wave time series at a point

    ## Files
    | File | Content |
    |---|---|
    | `{PREFIX}_CMEMS_waves_point.csv` | Copernicus Marine ({W['REGION']}): `time` (UTC), `hs` (VHM0, m), `tp` (VTPK, peak period s), `tm10` (VTM10, mean period Tm-10 s), `mwd` (VMDR, deg, coming FROM), `source` (dataset ID), `cell_lon`, `cell_lat` |
    | `{PREFIX}_ERA5_waves_point.csv` | ERA5 hourly: `time` (UTC), {era5_cols} (`rain_mm` total precipitation of the hour, mm; `hs` m; `tm` mean period Tm01 s; `tp` peak period s (gridded API only); `mwd` deg, waves coming FROM; `u10`/`v10` m/s; `wind_from` deg), `cell_lon`, `cell_lat` |
    | `{PREFIX}_waves_coverage.csv` | requested vs actual coverage per year and source: values, expected values, first/last time, largest gap, status |
    | `{PREFIX}_Fig_waves_ERA5_vs_CMEMS.png/.pdf` | (a) time series, (b) model comparison per CMEMS product, (c) monthly distributions, (d) ERA5 wave rose, (e) exceedance with the screening threshold |
    | `../{FOLDER_ROOT}__cache/era5/` (shared cache folder) | ERA5 NetCDF files named by request hash, each with a `.json` sidecar (request, download time, first/last time, provisional flag); `era5ts_cellprobe_*` = one month over the search box used to pick the sea cell |

    ## Method
    - Mode **{W['MODE']}**: ERA5 {P_ERA5[0][0]} → {ERA5_END} (end capped ~{W['ERA5_LAG_DAYS']} days before download){'' if W['MODE'] == 'full' else ', S2 months only'}; Copernicus Marine {P_CMEMS[0][0]} → {CMEMS_END} (cut at download time, no forecasts).
    - Requested point {W['POINT']} (lon, lat); for each product the **nearest model cell with data** (CMEMS ±{W['CMEMS_SEARCH_DEG']}°, ERA5 ±{W['ERA5_SEARCH_DEG']}°); cell coordinates are in the CSVs.
    - Copernicus Marine, region **{W['REGION']}** ({CMEMS_REGIONS[W['REGION']]['products']}; copernicusmarine toolbox, direct service): {', '.join(W['CMEMS_DATASETS'])}, {W['CMEMS_STEP_H']}-hourly; overlaps resolved in that order. Nearest sea cell chosen from the first two days of data.
    - ERA5 (CDS API, direct service): {('point time-series service `' + ERA5_TS_DATASET + '` at the nearest sea cell of the 0.5° wave grid (found from one month of Hs over ±' + str(min(W['ERA5_SEARCH_DEG'], 1.0)) + '°), requests of ' + str(W['ERA5_TS_CHUNK_YEARS']) + ' years (current year separate), waves and wind separately; no peak period in this service') if W['ERA5_API'] == 'timeseries' else ('gridded `' + ERA5_DATASET + '`, ≤ ' + str(W['ERA5_CHUNK_MONTHS']) + '-month requests, waves and wind separately')}; validated before caching; ERA5T data refreshed after {W['ERA5T_MAX_AGE_DAYS']} days. DOI time-series dataset: 10.24381/1cf1ad76.
    - Module 1 wave screen uses **{W['SCREEN_SOURCE']}** {'(larger of the two in each window)' if W['SCREEN_SOURCE'] == 'max' else ''}.
    - Model comparison (common times, per CMEMS product): {comp_txt or 'n/a'}

    ## Assumptions / limitations
    - **ERA5 vs Copernicus Marine is a model comparison, not validation**: WAVERYS is forced by ERA5 winds (and the
      Mediterranean wave models are also ECMWF-forced), so the records are not independent. Use buoy or altimeter data for accuracy statements.
    - Offshore, deep-water conditions seaward of the barrier reef; lagoon waves are smaller and mostly local wind-sea.
    - Coarse grids (ERA5 waves 0.5°, CMEMS 0.2°/0.083°): reef sheltering not resolved; the nearest valid cell may be
      kilometres from the point. ERA5 underestimates peak Hs in tropical cyclones.
    - Reanalysis and analysis/forecast segments of CMEMS are different models; small discontinuities at the switch.
    - Coverage gaps are listed in `{PREFIX}_waves_coverage.csv`; partial coverage is reported, not hidden.

    ## Sources
    - Hersbach, H. et al. (2020) The ERA5 global reanalysis. QJRMS 146:1999–2049; ERA5 hourly data on single levels,
      Copernicus Climate Change Service (C3S) Climate Data Store, doi:10.24381/cds.adbb2d47. Contains modified Copernicus Climate Change Service information.
    - E.U. Copernicus Marine Service Information: {'Mediterranean Sea Waves Reanalysis (MEDSEA_MULTIYEAR_WAV_006_012) and Mediterranean Sea Waves Analysis and Forecast (MEDSEA_ANALYSISFORECAST_WAV_006_017); for the global products used otherwise:' if W['REGION'] == 'med' else ''} Global Ocean Waves Reanalysis WAVERYS (GLOBAL_MULTIYEAR_WAV_001_032) and
      Global Ocean Waves Analysis and Forecast (GLOBAL_ANALYSISFORECAST_WAV_001_027, doi:10.48670/moi-00017).
    """)
    return ctx
