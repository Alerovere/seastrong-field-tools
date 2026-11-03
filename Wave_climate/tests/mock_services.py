"""Fake Colab, CDS (ERA5 time series + GTSM) and Copernicus Marine for offline tests. Import BEFORE wave_climate."""
import sys, types, os, io, zipfile, shutil, time
import numpy as np, pandas as pd, xarray as xr
import matplotlib; matplotlib.use('Agg')

ROOT = os.environ.get('WAVE_CLIMATE_TEST_DIR', '/tmp/fake_wave_climate')
shutil.rmtree(ROOT, ignore_errors=True); os.makedirs(ROOT)
time.sleep = lambda s: None
LOG = {'cds': [], 'cmems': []}
LON0, LAT0 = -88.30, 16.10

# ---------------- Colab ----------------
SECRETS = {'CDS_KEY': 'xxxx-key', 'CMEMS_USERNAME': 'user', 'CMEMS_PASSWORD': 'pw'}
g = types.ModuleType('google'); gc = types.ModuleType('google.colab')
def _get(n):
    if n not in SECRETS: raise KeyError(n)
    return SECRETS[n]
gc.userdata = types.SimpleNamespace(get=_get); gc.drive = types.SimpleNamespace(mount=lambda p: None)
sys.modules['google'] = g; sys.modules['google.colab'] = gc

def seasonal(t, a, b):          # a + b * (winter northers Nov-Feb)
    return a + b * np.isin(t.month, [11, 12, 1, 2])

# ---------------- CDS ----------------
cds = types.ModuleType('cdsapi')
class Client:
    def __init__(s, url=None, key=None, quiet=False): assert key == 'xxxx-key'
    def retrieve(s, ds, req, target):
        LOG['cds'].append((ds, req))
        if ds == 'reanalysis-era5-single-levels-timeseries':
            a, b = [pd.Timestamp(x) for x in req['date'][0].split('/')]
            t = pd.date_range(a, b + pd.Timedelta(hours=23), freq='1h'); rng = np.random.default_rng(len(t)); n = len(t)
            if 'area' in req:
                N, W, S, E = req['area']
                lat = np.arange(np.ceil(S * 2) / 2, N + 1e-6, 0.5); lon = np.arange(np.ceil(W * 2) / 2, E + 1e-6, 0.5)
                hs = 1 + rng.normal(0, 0.05, (n, len(lat), len(lon))); hs[:, :, lon < -88.4] = np.nan
                xr.Dataset({'swh': (('valid_time', 'latitude', 'longitude'), hs)}, coords={'valid_time': t, 'latitude': lat, 'longitude': lon}).to_netcdf(target); return
            if 'mean_wave_period' in req['variable']:
                hs = np.clip(seasonal(t, 0.9, 0.5) + 0.3 * np.sin(np.arange(n) / 40) + rng.normal(0, 0.15, n), 0.1, None)
                v = {'swh': hs, 'mwp': 3.5 + 2 * hs + rng.normal(0, 0.3, n), 'mwd': (90 + rng.normal(0, 25, n) - 40 * np.isin(t.month, [12, 1])) % 360}
            else:
                v = {'u10': rng.normal(-5, 1.5, n) * seasonal(t, 1, 0.3), 'v10': rng.normal(1, 1.5, n) - 3 * np.isin(t.month, [12, 1])}
            xr.Dataset({k: (('valid_time',), x) for k, x in v.items()}, coords={'valid_time': t}).to_netcdf(target); return
        if ds == 'sis-water-level-change-timeseries-cmip6':
            assert req['experiment'] == 'reanalysis'
            var = req['variable'][0]; agg = req['temporal_aggregation'][0]
            st_lon = LON0 + np.linspace(-1, 1, 41); st_lat = LAT0 + np.linspace(-1, 1, 41) * 0.3
            buf = io.BytesIO(); z = zipfile.ZipFile(buf, 'w')
            for y in req['year']:
                for m in req['month']:
                    a = pd.Timestamp(f'{y}-{m}-01'); b = a + pd.offsets.MonthBegin(1)
                    if var == 'tidal_elevation':
                        t = pd.date_range(a, b, freq='1h' if agg == 'hourly' else '10min', inclusive='left')
                        h = (t - pd.Timestamp('2000-01-01')) / pd.Timedelta(hours=1)
                        x = (0.08 * np.cos(2 * np.pi * h / 12.4206 - 1) + 0.03 * np.cos(2 * np.pi * h / 12.0) +
                             0.06 * np.cos(2 * np.pi * h / 23.9345 - 2) + 0.05 * np.cos(2 * np.pi * h / 25.8193))
                    else:
                        t = pd.date_range(a, b, freq='1D', inclusive='left'); rng = np.random.default_rng(int(y) * 13 + int(m))
                        x = np.abs(rng.gamma(2, 0.02, len(t))) * seasonal(t, 1, 0.8)
                    data = np.repeat(np.asarray(x)[:, None], len(st_lon), axis=1).astype('float32')
                    dsx = xr.Dataset({'waterlevel': (('time', 'stations'), data)},
                                     coords={'time': t, 'station_x_coordinate': ('stations', st_lon), 'station_y_coordinate': ('stations', st_lat)})
                    z.writestr(f'reanalysis_{var}_{y}_{m}_v3.nc', dsx.to_netcdf())
            z.close(); open(target, 'wb').write(buf.getvalue()); return
        raise ValueError(ds)
cds.Client = Client; sys.modules['cdsapi'] = cds

# ---------------- Copernicus Marine ----------------
cm = types.ModuleType('copernicusmarine')
def open_dataset(dataset_id, variables, minimum_longitude, maximum_longitude, minimum_latitude, maximum_latitude,
                 start_datetime, end_datetime, username=None, password=None, coordinates_selection_method=None):
    assert username == 'user' and password == 'pw'
    LOG['cmems'].append((dataset_id, tuple(variables)))
    if 'anfc' in dataset_id and any(v.endswith('_SW1') for v in variables): raise ValueError('variable VHM0_SW1 not found')
    a0 = pd.Timestamp('2024-11-06') if 'anfc' in dataset_id else pd.Timestamp('1980-01-01')
    a1 = pd.Timestamp('2026-11-11') if 'anfc' in dataset_id else pd.Timestamp('2026-08-31')
    t = pd.date_range(max(pd.Timestamp(start_datetime), a0), min(pd.Timestamp(end_datetime), a1), freq='3h')
    lat = np.arange(minimum_latitude, maximum_latitude, 0.2); lon = np.arange(minimum_longitude, maximum_longitude, 0.2)
    rng = np.random.default_rng(len(t)); n = len(t)
    hs = np.clip(seasonal(t, 0.85, 0.5) + 0.3 * np.sin(np.arange(n) / 13) + rng.normal(0, 0.15, n), 0.1, None)
    base = {'VHM0': hs, 'VTPK': 5 + 3 * hs + rng.normal(0, 1, n), 'VTM10': 4 + 2 * hs, 'VTM02': 3.5 + 1.8 * hs,
            'VMDR': (90 + rng.normal(0, 25, n) - 40 * np.isin(t.month, [12, 1])) % 360,
            'VHM0_WW': hs * 0.8, 'VTM01_WW': 3 + hs, 'VMDR_WW': (95 + rng.normal(0, 30, n)) % 360,
            'VHM0_SW1': hs * 0.6, 'VTM01_SW1': 8 + rng.normal(0, 1, n), 'VMDR_SW1': (80 + rng.normal(0, 10, n)) % 360}
    out = {}
    for v in variables:
        a = np.repeat(np.repeat(base[v][:, None, None], len(lat), 1), len(lon), 2).astype('float32'); a[:, 0, :] = np.nan
        out[v] = (('time', 'latitude', 'longitude'), a)
    return xr.Dataset(out, coords={'time': t, 'latitude': lat, 'longitude': lon})
cm.open_dataset = open_dataset; sys.modules['copernicusmarine'] = cm
