"""Step 1 — download hourly waves and wind at the point.

- **ERA5** (ECMWF reanalysis, Climate Data Store point time-series service): significant wave height `hs`, mean
  wave period `tm` (ERA5 'mwp'), mean wave direction `dir` (coming from), 10 m wind `u10`, `v10` -> `wind_speed`,
  `wind_from`. Hourly, 0.5° wave grid (the nearest SEA cell is used), 0.25° atmosphere. No peak period and no
  directional spreading in this service.
- **Copernicus Marine** wave reanalysis + analysis (global WAVERYS 0.2° 3-hourly from 1980 and 1/12° recent
  analysis; or the Mediterranean model 1/24° hourly from 1985): `hs`, peak period `tp`, `tm10` (Tm-1,0, energy
  period), `tm02`, `dir`, and the wind-sea and primary-swell partitions.

Every download is cached in `outputs/_cache` by a hash of the request: running again only fetches what is new.
"""
import os, io, json, time, datetime as dt
import numpy as np
import pandas as pd
from .core import secret, req_hash, km
from .options import check

ERA5_TS = 'reanalysis-era5-single-levels-timeseries'
TS_GROUPS = {'waves': ['significant_height_of_combined_wind_waves_and_swell', 'mean_wave_period', 'mean_wave_direction'],
             'wind': ['10m_u_component_of_wind', '10m_v_component_of_wind']}      # waves and wind: separate requests
SHORT = {'swh': 'hs', 'mwp': 'tm', 'mwd': 'dir', 'u10': 'u10', 'v10': 'v10'}
CMEMS_REGIONS = {
    'global': dict(datasets=['cmems_mod_glo_wav_my_0.2deg_PT3H-i', 'cmems_mod_glo_wav_anfc_0.083deg_PT3H-i'], step_h=3,
                   search_deg=0.3, start='1980-01-01',
                   products='GLOBAL_MULTIYEAR_WAV_001_032 (WAVERYS), GLOBAL_ANALYSISFORECAST_WAV_001_027'),
    'med': dict(datasets=['cmems_mod_med_wav_my_4.2km_PT1H-i', 'cmems_mod_med_wav_anfc_4.2km_PT1H-i'], step_h=1,
                search_deg=0.1, start='1985-01-01',
                products='MEDSEA_MULTIYEAR_WAV_006_012, MEDSEA_ANALYSISFORECAST_WAV_006_017'),
}


class _TooLarge(Exception):
    pass


# ------------------------------------------------------------------------------------------------ ERA5
def cds_client():
    import cdsapi
    return cdsapi.Client(url=secret('CDS_URL', required=False) or 'https://cds.climate.copernicus.eu/api',
                         key=secret('CDS_KEY', purpose='ERA5 and GTSM from the Climate Data Store'), quiet=True)


def open_cds(path):
    """CDS NetCDF (sometimes delivered zipped) -> loaded xarray Dataset."""
    import xarray as xr, zipfile
    if zipfile.is_zipfile(path):
        with zipfile.ZipFile(path) as z:
            frames = [xr.open_dataset(io.BytesIO(z.read(n))).load() for n in z.namelist() if n.endswith('.nc')]
        return xr.merge(frames, compat='override')
    with xr.open_dataset(path) as ds:
        return ds.load()


def ts_frame(ds):
    df = ds.to_dataframe().reset_index()
    tcol = 'valid_time' if 'valid_time' in df else 'time'
    keep = {v: SHORT[v] for v in ds.data_vars if v in SHORT}
    out = df[[tcol] + list(keep) + [c for c in ('latitude', 'longitude') if c in df]].rename(columns={tcol: 'time', **keep})
    out['time'] = pd.to_datetime(out['time'], utc=True)
    return out


def ts_fetch(client, req, cache, label, a, b, retries):
    f = os.path.join(cache, f"era5ts_{label}_{a:%Y%m%d}-{b:%Y%m%d}_{req_hash({'d': ERA5_TS, **req})}.nc")
    if os.path.exists(f):
        return f
    for attempt in range(1, retries + 1):
        print(f'  ERA5 {label} {a}..{b}: requesting ...')
        try:
            client.retrieve(ERA5_TS, req, f + '.part')
            ds = open_cds(f + '.part')
            if not any(v in SHORT for v in ds.data_vars): raise ValueError(f'unexpected variables {list(ds.data_vars)}')
            os.replace(f + '.part', f)
            return f
        except Exception as e:
            if os.path.exists(f + '.part'): os.remove(f + '.part')
            msg = str(e).lower()
            if ('cost' in msg or 'too large' in msg or 'limit' in msg) and (b - a).days > 31: raise _TooLarge()
            if attempt == retries: raise
            print(f'    attempt {attempt} failed ({str(e)[:120]}); retrying in {30 * attempt} s'); time.sleep(30 * attempt)


def ts_range(client, label, lon, lat, a, b, cache, retries):
    req = {'variable': sorted(TS_GROUPS[label]), 'location': {'longitude': round(lon, 4), 'latitude': round(lat, 4)},
           'date': [f'{a:%Y-%m-%d}/{b:%Y-%m-%d}'], 'data_format': 'netcdf'}
    try:
        return [ts_fetch(client, req, cache, label, a, b, retries)]
    except _TooLarge:
        mid = a + (b - a) / 2
        print(f'    too large for the CDS -> splitting at {mid}')
        return ts_range(client, label, lon, lat, a, mid, cache, retries) + \
               ts_range(client, label, lon, lat, mid + dt.timedelta(days=1), b, cache, retries)


def era5_sea_cell(client, lon, lat, cache, d, retries):
    """Nearest ERA5 wave-grid cell with sea data: one month of Hs over a small box."""
    d = min(d, 1.0)
    req = {'variable': ['significant_height_of_combined_wind_waves_and_swell'],
           'area': [round(lat + d, 4), round(lon - d, 4), round(lat - d, 4), round(lon + d, 4)],
           'date': ['2020-01-01/2020-01-31'], 'data_format': 'netcdf'}
    df = ts_frame(open_cds(ts_fetch(client, req, cache, 'cellprobe', dt.date(2020, 1, 1), dt.date(2020, 1, 31), retries)))
    cells = df.groupby(['latitude', 'longitude'])['hs'].apply(lambda v: v.notna().mean()).reset_index()
    cells = cells[cells.hs > 0.9]
    if cells.empty: raise RuntimeError('No ERA5 wave (sea) cell near the point: move SITE["POINT"] offshore')
    d2 = (((cells.longitude - lon + 180) % 360) - 180) ** 2 + (cells.latitude - lat) ** 2
    c = cells.loc[d2.idxmin()]
    return float(c.longitude), float(c.latitude)


def era5_series(ctx, o, a, b):
    client = cds_client()
    cache = os.path.join(ctx.cache, 'era5'); os.makedirs(cache, exist_ok=True)
    clon, clat = era5_sea_cell(client, ctx.lon, ctx.lat, cache, o['ERA5_SEARCH_DEG'], o['CDS_RETRIES'])
    print(f'  ERA5 wave cell nearest to the point: {clon:.2f}, {clat:.2f} ({km(ctx.lon, ctx.lat, clon, clat):.0f} km)')
    chunks, y = [], a.year                                  # whole-year blocks (stable cache) + the current year
    while y < b.year:
        y1 = min(y + o['ERA5_TS_CHUNK_YEARS'] - 1, b.year - 1)
        chunks.append((max(a, dt.date(y, 1, 1)), dt.date(y1, 12, 31))); y = y1 + 1
    chunks.append((max(a, dt.date(b.year, 1, 1)), b))
    frames = {}
    for g in TS_GROUPS:
        files = [f for ca, cb in chunks for f in ts_range(client, g, clon, clat, ca, cb, cache, o['CDS_RETRIES'])]
        df = pd.concat([ts_frame(open_cds(f)) for f in files]).drop(columns=['latitude', 'longitude'], errors='ignore')
        frames[g] = df.drop_duplicates('time', keep='last').set_index('time').sort_index()
    out = frames['waves'].join(frames['wind'], how='outer')
    out['wind_speed'] = np.hypot(out.u10, out.v10)
    out['wind_from'] = (np.degrees(np.arctan2(out.u10, out.v10)) + 180) % 360    # direction the wind comes FROM
    out = out.reset_index()
    out = out[(out.time >= pd.Timestamp(a, tz='UTC')) & (out.time < pd.Timestamp(b, tz='UTC') + pd.Timedelta(days=1))]
    out['cell_lon'], out['cell_lat'] = clon, clat
    print(f'  ERA5: {len(out):,} hourly values {out.time.min():%Y-%m-%d} -> {out.time.max():%Y-%m-%d}')
    return out.reset_index(drop=True), dict(dataset=ERA5_TS, cell_lon=clon, cell_lat=clat,
                                            first=str(out.time.min()), last=str(out.time.max()))


# ------------------------------------------------------------------------------------------------ Copernicus Marine
def nearest_valid_cell(da, lon, lat, tdim='time'):
    latn = 'latitude' if 'latitude' in da.dims else 'lat'
    lonn = 'longitude' if 'longitude' in da.dims else 'lon'
    valid = da.notnull().any(tdim).transpose(latn, lonn).values
    lons, lats = np.meshgrid(da[lonn].values, da[latn].values)
    d2 = (((lons - lon + 180) % 360) - 180) ** 2 + (lats - lat) ** 2
    d2[~valid] = np.inf
    if not np.isfinite(d2).any(): return None
    iy, ix = np.unravel_index(np.argmin(d2), d2.shape)
    return {latn: iy, lonn: ix}, float(lons[iy, ix]), float(lats[iy, ix])


def cmems_series(ctx, o, a, b):
    import copernicusmarine as cm
    reg = CMEMS_REGIONS[ctx.site['REGION']]
    user = secret('CMEMS_USERNAME', purpose='Copernicus Marine'); pw = secret('CMEMS_PASSWORD', purpose='Copernicus Marine')
    d = o['CMEMS_SEARCH_DEG'] or reg['search_deg']
    t0 = max(a, dt.date.fromisoformat(reg['start'])).isoformat(); t1 = (b + dt.timedelta(days=1)).isoformat()
    now = pd.Timestamp.now(tz='UTC')
    cache = os.path.join(ctx.cache, 'cmems'); os.makedirs(cache, exist_ok=True)
    frames, info = [], []
    want = o['CMEMS_VARIABLES']
    core = [v for v in ('VHM0', 'VTPK', 'VTM10', 'VMDR') if v in want]
    for ds_id in reg['datasets']:
        key = req_hash(dict(ds=ds_id, v=want, lon=ctx.lon, lat=ctx.lat, d=d, t0=t0, t1=t1))
        f = os.path.join(cache, f'{ds_id}_{key}.csv')
        if os.path.exists(f):
            df = pd.read_csv(f, parse_dates=['time']); frames.append(df)
            print(f'  {ds_id}: {len(df):,} values re-used from the cache'); info.append(dict(dataset=ds_id, status='cached')); continue
        kw = dict(dataset_id=ds_id, minimum_longitude=ctx.lon - d, maximum_longitude=ctx.lon + d,
                  minimum_latitude=ctx.lat - d, maximum_latitude=ctx.lat + d, start_datetime=t0, end_datetime=t1,
                  username=user, password=pw)
        ds, err = None, ''
        for vars_ in (list(want), core, ['VHM0']):            # fewer variables if one is not in this dataset
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
        cell = nearest_valid_cell(ds['VHM0'].isel(time=slice(0, 48)), ctx.lon, ctx.lat)
        if cell is None:
            print(f'  {ds_id}: no sea cell near the point'); info.append(dict(dataset=ds_id, status='no_sea_cell')); continue
        sel, clon, clat = cell
        names = {v: c for v, c in want.items() if v in ds}
        pt = ds[list(names)].isel(**sel).load().to_dataframe().reset_index()
        df = pt[['time'] + list(names)].rename(columns=names)
        df['time'] = pd.to_datetime(df['time'], utc=True)
        df = df[df.time <= now].dropna(subset=['hs'])            # no forecasts
        df['dataset'] = ds_id; df['cell_lon'] = clon; df['cell_lat'] = clat
        df.to_csv(f + '.tmp', index=False); os.replace(f + '.tmp', f)
        print(f'  {ds_id}: {len(df):,} values {df.time.min():%Y-%m-%d} -> {df.time.max():%Y-%m-%d} at {clon:.3f}, {clat:.3f} '
              f'({km(ctx.lon, ctx.lat, clon, clat):.0f} km); variables {list(names.values())}')
        info.append(dict(dataset=ds_id, status='ok', first=str(df.time.min()), last=str(df.time.max()), cell_lon=clon,
                         cell_lat=clat, variables=list(names.values())))
        frames.append(df)
    if not frames: raise RuntimeError(f"No Copernicus Marine wave data (region {ctx.site['REGION']}: is the point inside it?)")
    out = pd.concat(frames)
    out['time'] = pd.to_datetime(out['time'], utc=True)
    out = out.drop_duplicates('time', keep='first').sort_values('time').reset_index(drop=True)   # reanalysis first
    return out, dict(products=reg['products'], datasets=info)


# ------------------------------------------------------------------------------------------------ run
def run(ctx, options=None):
    """Download (or re-use) ERA5 and Copernicus Marine series; saves them to <site>/data/."""
    o = check('download', options); ctx.opts['download'] = o
    a = dt.date.fromisoformat(o['START'])
    b = ctx.today - dt.timedelta(days=o['ERA5_LAG_DAYS'])
    if o['END']: b = min(b, dt.date.fromisoformat(o['END']))
    print(f'Period {a} -> {b}')
    if o['ERA5']:
        df, info = era5_series(ctx, o, a, b)
        df.to_csv(ctx.path('data', f"{ctx.site['NAME']}_ERA5_hourly.csv"), index=False)
        ctx.data['era5'] = df; ctx.note('era5', info)
    if o['CMEMS']:
        df, info = cmems_series(ctx, o, a, b)
        df.to_csv(ctx.path('data', f"{ctx.site['NAME']}_CMEMS_waves.csv"), index=False)
        ctx.data['cmems'] = df; ctx.note('cmems', info)
    return ctx


def load(ctx):
    """Series saved by run() (also in a new Colab session)."""
    for k, f in (('era5', 'ERA5_hourly'), ('cmems', 'CMEMS_waves')):
        p = ctx.path('data', f"{ctx.site['NAME']}_{f}.csv")
        if k not in ctx.data and os.path.exists(p):
            df = pd.read_csv(p); df['time'] = pd.to_datetime(df['time'], utc=True); ctx.data[k] = df
    return ctx
