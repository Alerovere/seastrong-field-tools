"""Fake Earth Engine, Colab, CDS, Copernicus Marine and SlideRule services for offline end-to-end tests.

Import this module BEFORE seastrong_toolkit. Synthetic AOI: 20 x 20 km box in UTM 16N with a land strip on the
west edge; depth increases eastwards. Nothing here contacts a real service."""
import sys, types, os, json, shutil, time, re
import numpy as np, pandas as pd
import matplotlib; matplotlib.use('Agg')
import xarray as xr, rasterio, geopandas as gpd
from rasterio.transform import from_origin
from shapely.geometry import box

ROOT = os.environ.get('SEASTRONG_TEST_DRIVE', '/tmp/fake_drive')
shutil.rmtree(ROOT, ignore_errors=True); os.makedirs(ROOT)
time.sleep = lambda s: None
E0, N0, SZ = 300000.0, 1780000.0, 20000.0
LOG = {'cds': [], 'tasks': {}}
FORCE_STATE = {}            # description -> state (to test CANCELLED)

# ---------------- Earth Engine ----------------
class Info:
    def __getitem__(s, k): return {'precision': 'float'}
    def __bool__(s): return False
    def __gt__(s, o): return False
    def __repr__(s): return '<mock>'
class Any:
    def __getattr__(s, n): return s
    def __call__(s, *a, **k): return s
    def getInfo(s): return Info()
    def __iter__(s): return iter([])
A = Any()
ee = types.ModuleType('ee'); ee.__getattr__ = lambda n: A
ee.Initialize = lambda *a, **k: None; ee.Authenticate = lambda *a, **k: None
class Dct:
    def __init__(s, d): s.d = d
    def getInfo(s):
        if 'area_km2' in s.d:
            g = gpd.GeoSeries([box(E0, N0, E0 + SZ, N0 + SZ)], crs='EPSG:32616').to_crs('EPSG:4326').iloc[0]
            x0, y0, x1, y1 = g.bounds
            return {'area_km2': 400.0, 'bounds_crs': [[[E0, N0], [E0 + SZ, N0], [E0 + SZ, N0 + SZ], [E0, N0 + SZ], [E0, N0]]],
                    'bounds_wgs84': [[[x0, y0], [x1, y0], [x1, y1], [x0, y1], [x0, y0]]],
                    'geojson': g.__geo_interface__, 'centre': [(x0 + x1) / 2, (y0 + y1) / 2]}
        if 'first' in s.d: return {'first': '1992-10-02', 'last': '2024-09-05'}
        return {}
    def __getattr__(s, n): return A
ee.Dictionary = lambda d=None, *a: Dct(d or {})

def _write_tif(p, count, dtype, nodata, fill):
    w = h = int(SZ / 10) if 'S2_' in os.path.basename(p) else int(SZ / 30)
    s = SZ / w
    arr = fill(count, h, w, s).astype(dtype)
    with rasterio.open(p, 'w', driver='GTiff', width=w, height=h, count=count, dtype=dtype, crs='EPSG:32616',
                       transform=from_origin(E0, N0 + SZ, s, s), nodata=nodata) as dst:
        dst.write(arr)
        if count == 12: dst.descriptions = tuple(['B1', 'B2', 'B3', 'B4', 'B5', 'B6', 'B7', 'B8', 'B8A', 'B9', 'B11', 'B12'])

def depth_at(e): return np.clip((e - E0 - 90) / SZ * 35, 0, None)
def comp_fill(count, h, w, s):
    x = E0 + (np.arange(w) + 0.5) * s; d = depth_at(x)
    b3 = 0.02 + 0.08 * np.exp(-0.25 * np.minimum(d, 15)); b2 = 0.03 + 0.08 * np.exp(-0.12 * np.minimum(d, 15))
    B = np.full((count, h, w), 0.01, np.float32); B[1] = b2[None]; B[2] = b3[None]
    B[:, :, :3] = 0.2                             # land strip
    return B

class Task:
    n = 0
    def __init__(s, kind, k): Task.n += 1; s.id = f'T{Task.n:04d}'; s.k = k; s.kind = kind
    def start(s):
        k = s.k; d = os.path.join(ROOT, k['folder']); os.makedirs(d, exist_ok=True); nm = k['fileNamePrefix']
        LOG['tasks'][s.id] = (k['description'], FORCE_STATE.get(k['description'], 'COMPLETED'))
        if s.kind == 'table':
            ext = k['fileFormat'].lower(); p = os.path.join(d, f'{nm}.{ext}')
            if 'S2_AOI_stats' in nm:                  # all S2 dates (the toolkit keeps only those it asked for)
                dates = S2_DATES; rng = np.random.default_rng(0)
                cloud = META.groupby('date').CLOUDY_PIXEL_PERCENTAGE.mean().reindex(dates.strftime('%Y-%m-%d')).values
                df = pd.DataFrame({'date': dates.strftime('%Y-%m-%d'),
                                   'water_nir': rng.uniform(0, 0.04, len(dates)) + cloud / 2000, 'water_b5': rng.uniform(0, 0.04, len(dates)),
                                   'n_water_px': (1000 * (1 - cloud / 100)).round(), 'rain_mm': rng.gamma(1, 10, len(dates)), 'rain_days': 5})
                df.loc[3, 'water_nir'] = np.nan; df.loc[5, 'rain_mm'] = np.nan
                LOG.setdefault('aoi_exports', []).append(nm)
                df[k.get('selectors') or df.columns].to_csv(p, index=False)
            elif '_prescreen_CHIRPS' in nm:
                d = pd.date_range('2017-01-01', '2026-10-31', freq='D'); rng = np.random.default_rng(3)
                wet = np.isin(d.month, [6, 7, 8, 9, 10, 11])
                pd.DataFrame({'time_ms': d.as_unit('ns').asi8 // 1_000_000, 'rain': rng.gamma(0.6, 12 if True else 1, len(d)) * np.where(wet, 2.5, 0.4)}).to_csv(p, index=False)
            elif '_prescreen_S2' in nm or '_prescreen_LANDSAT' in nm or '_prescreen_HLS' in nm:
                s2_ = '_prescreen_S2' in nm
                d = pd.date_range('2017-01-03' if s2_ else '1990-01-05', '2026-10-25', freq='5D' if s2_ else '8D'); rng = np.random.default_rng(4)
                wet = np.isin(d.month, [6, 7, 8, 9, 10, 11]); n = len(d)
                clear = np.clip(rng.beta(2, 2, n) + np.where(wet, -0.3, 0.2), 0, 1)
                pd.DataFrame({'time_ms': (d + pd.Timedelta(hours=16, minutes=20)).as_unit('ns').asi8 // 1_000_000,
                              'sensor': 'S2' if s2_ else rng.choice(['L5', 'L8'], n), 'n_water_aoi': 4000, 'n_water': 4000, 'n_clear': (clear * 4000).round(),
                              'n_glint': (rng.uniform(0, 0.1, n) * clear * 4000).round(),
                              'red': 0.02 + np.where(wet, 0.03, 0.0) + rng.gamma(2, 0.004, n), 'nir': 0.01}).to_csv(p, index=False)
            elif 'habitat_areas' in nm:
                pd.DataFrame({'system:index': [0], 'seagrass_km2': [12.3], 'coral_algae_km2': [4.5], 'aca_mapped_km2': [50.0],
                              'mangrove_km2': [7.7], 'scale_aca_m': [5], 'scale_gmw_m': [10], '.geo': ['']}).to_csv(p, index=False)
            elif '_dates_' in nm:
                rng = np.random.default_rng(1); n = 300
                pd.DataFrame({'date': pd.date_range('2000-01-01', periods=n, freq='16D').strftime('%Y-%m-%d'),
                              'year': rng.integers(1990, 2026, n), 'month': rng.integers(1, 13, n),
                              'sensor': rng.choice(['L5', 'L8'], n), 'wind_speed': rng.uniform(0, 10, n),
                              'wind_from': rng.uniform(0, 360, n), 'rain_mm': rng.gamma(1, 10, n), 'rain_days': 5,
                              'st_ref': np.nan, 'st_ref_cover': np.nan}).to_csv(p, index=False)
            else:
                open(p, 'w').write('{"type":"FeatureCollection","features":[]}' if ext == 'geojson' else 'a\n1\n')
        else:
            p = os.path.join(d, f'{nm}.tif')
            if '12band' in nm: _write_tif(p, 12, 'float32', -9999, comp_fill)
            elif 'Median_B1-B4' in nm: _write_tif(p, 4, 'float32', -9999, lambda c, h, w, s: comp_fill(12, h, w, s)[:4] * 1.02)
            elif nm.endswith('_QA'):
                _write_tif(p, 3, 'int16', -1, lambda c, h, w, s: np.stack([np.full((h, w), 9), np.ones((h, w)), np.zeros((h, w))]))
            elif 'FABDEM' in nm or 'DeltaDTM' in nm or 'DSM' in nm:
                _write_tif(p, 1, 'float32', -9999, lambda c, h, w, s: np.full((1, h, w), 1.5))
            else: _write_tif(p, 1, 'float32', -9999, lambda c, h, w, s: np.zeros((1, h, w)))
class Batch:
    class Export:
        class image:
            @staticmethod
            def toDrive(**k):
                assert 'crsTransform' in k and 'scale' not in k, 'export must use the aligned grid'
                return Task('image', k)
        class table:
            @staticmethod
            def toDrive(**k): return Task('table', k)
            @staticmethod
            def toAsset(**k): return A
ee.batch = Batch
def getTaskStatus(tid):
    desc, st = LOG['tasks'][tid]
    return [{'id': tid, 'state': st, 'description': desc, 'creation_timestamp_ms': 0,
             **({'error_message': 'cancelled by user'} if st != 'COMPLETED' else {})}]
def computePixels(req):
    g = req['grid']; w, h = g['dimensions']['width'], g['dimensions']['height']; a = g['affineTransform']
    x = a['translateX'] + (np.arange(w) + 0.5) * a['scaleX']
    arr = np.broadcast_to((x >= E0 + 90).astype(np.uint8)[None, :], (h, w)).copy()   # land west of E0+90 m
    return arr
# Sentinel-2 tile metadata: two tiles every 5 days since 2017, orbit 40; cloudier in the wet season (Jun-Nov)
S2_DATES = pd.date_range('2017-01-02', '2026-10-28', freq='5D')
def _meta():
    rng = np.random.default_rng(7); rows = []
    for d in S2_DATES:
        wet = d.month in (6, 7, 8, 9, 10, 11)
        for tile in ('16QCD', '16PCC'):
            t = int((d + pd.Timedelta(hours=16, minutes=20, seconds=5 * (tile == '16PCC'))).tz_localize('UTC').value // 1_000_000)
            rows.append({'time_ms': t, 'MGRS_TILE': tile, 'SENSING_ORBIT_NUMBER': 40, 'SPACECRAFT_NAME': 'Sentinel-2A',
                         'CLOUDY_PIXEL_PERCENTAGE': float(np.clip(rng.beta(2, 3) * 100 + (30 if wet else -10), 0, 100)),
                         'CLOUD_SHADOW_PERCENTAGE': rng.uniform(0, 5), 'THIN_CIRRUS_PERCENTAGE': rng.uniform(0, 10),
                         'NODATA_PIXEL_PERCENTAGE': 0.0, 'WATER_PERCENTAGE': 60.0,
                         'MEAN_SOLAR_ZENITH_ANGLE': 40 + 15 * np.cos(2 * np.pi * d.dayofyear / 365), 'MEAN_SOLAR_AZIMUTH_ANGLE': 140.0,
                         'MEAN_INCIDENCE_ZENITH_ANGLE_B8': rng.uniform(2, 11), 'MEAN_INCIDENCE_AZIMUTH_ANGLE_B8': rng.choice([105.0, 285.0]),
                         'geo': None})
    return pd.DataFrame(rows)
META = _meta()
META['date'] = pd.to_datetime(META.time_ms, unit='ms', utc=True).dt.strftime('%Y-%m-%d')
def computeFeatures(params):
    LOG['meta_calls'] = LOG.get('meta_calls', 0) + 1
    assert params['fileFormat'] == 'PANDAS_DATAFRAME'
    return META.drop(columns='date').copy()
ee.data = types.SimpleNamespace(getTaskStatus=getTaskStatus, computePixels=computePixels, computeFeatures=computeFeatures)
sys.modules['ee'] = ee

# ---------------- Colab ----------------
SECRETS = {'EE_PROJECT': 'demo-project', 'CDS_KEY': 'xxxx-key', 'CMEMS_USERNAME': 'user', 'CMEMS_PASSWORD': 'pw'}
g = types.ModuleType('google'); gc = types.ModuleType('google.colab')
gc.drive = types.SimpleNamespace(mount=lambda p: None)
def _get(n):
    if n not in SECRETS: raise KeyError(n)
    return SECRETS[n]
gc.userdata = types.SimpleNamespace(get=_get)
sys.modules['google'] = g; sys.modules['google.colab'] = gc

# ---------------- CDS ----------------
cds = types.ModuleType('cdsapi')
class Client:
    def __init__(s, url=None, key=None, quiet=False): assert key == 'xxxx-key'
    def retrieve(s, ds, req, target):
        LOG['cds'].append((ds, req))
        if ds == 'reanalysis-era5-single-levels-timeseries':
            a, b = [pd.Timestamp(x) for x in req['date'][0].split('/')]
            assert b.date() <= (pd.Timestamp.now('UTC') - pd.Timedelta(days=5)).date(), f'future date requested {b}'
            wave = 'mean_wave_period' in req['variable']
            assert not (wave and '10m_u_component_of_wind' in req['variable']), 'waves and wind combined'
            assert 'peak_wave_period' not in req['variable']
            if (b - a).days > 365 * 25: raise Exception('400 Client Error: request too large, cost limits exceeded')
            t = pd.date_range(a, b + pd.Timedelta(hours=23), freq='1h'); rng = np.random.default_rng(len(t))
            if 'area' in req:
                N, Wl, S, E = req['area']; assert N - S <= 2 and E - Wl <= 2
                lat = np.arange(np.ceil(S * 2) / 2, N + 1e-6, 0.5); lon = np.arange(np.ceil(Wl * 2) / 2, E + 1e-6, 0.5)
                hs = 1.0 + rng.normal(0, 0.05, (len(t), len(lat), len(lon))); hs[:, :, lon < -88.4] = np.nan   # land west
                xr.Dataset({'swh': (('valid_time', 'latitude', 'longitude'), hs)},
                           coords={'valid_time': t, 'latitude': lat, 'longitude': lon}).to_netcdf(target); return
            loc = req['location']; assert loc['longitude'] >= -88.4, 'location on a land cell'
            n = len(t); hs = 1.0 + 0.4 * np.sin(np.arange(n) / 50) + rng.normal(0, 0.05, n)
            v = ({'swh': hs, 'mwp': hs * 4, 'mwd': rng.uniform(60, 120, n)} if wave else
                 {'u10': rng.normal(-5, 1, n) * (1 + 0.4 * np.isin(t.month, [10, 11, 12, 1])), 'v10': rng.normal(1, 1, n),
                  'tp': rng.gamma(0.3, 0.0002, n) * (1 + 3 * np.isin(t.month, [6, 7, 8, 9, 10, 11]))})
            xr.Dataset({k: (('valid_time',), x) for k, x in v.items()},
                       coords={'valid_time': t, 'latitude': loc['latitude'], 'longitude': loc['longitude']}).to_netcdf(target)
            return
        if len(req['month']) > 2: raise Exception('403 Client Error: Forbidden: cost limits exceeded')
        y = int(req['year'][0]); times = []
        for m in req['month']:
            for d in req['day']:
                try: day = pd.Timestamp(year=y, month=int(m), day=int(d))
                except ValueError: continue
                assert day.date() <= (pd.Timestamp.now('UTC') - pd.Timedelta(days=5)).date(), f'future date requested {day}'
                times += list(pd.date_range(day, periods=24, freq='1h'))
        N, Wl, S, E = req['area']; lat = np.arange(S, N + 1e-6, 0.5); lon = np.arange(Wl, E + 1e-6, 0.5)
        t = pd.DatetimeIndex(times); sh = (len(t), len(lat), len(lon))
        rng = np.random.default_rng(len(t))
        if 'mean_wave_period' in req['variable']:
            hs = 1.0 + 0.4 * np.sin(np.arange(len(t)) / 50)[:, None, None] + rng.normal(0, 0.05, sh); hs[:, :, 0] = np.nan
            v = {'swh': hs, 'mwp': hs * 4, 'pp1d': hs * 6, 'mwd': rng.uniform(60, 120, sh)}
        else:
            v = {'u10': rng.normal(-5, 1, sh), 'v10': rng.normal(1, 1, sh)}
        xr.Dataset({k: (('valid_time', 'latitude', 'longitude'), a) for k, a in v.items()},
                   coords={'valid_time': t, 'latitude': lat, 'longitude': lon}).to_netcdf(target)
cds.Client = Client; sys.modules['cdsapi'] = cds

# ---------------- Copernicus Marine ----------------
cm = types.ModuleType('copernicusmarine')
CM_CALLS = []
def open_dataset(dataset_id, variables, minimum_longitude, maximum_longitude, minimum_latitude, maximum_latitude,
                 start_datetime, end_datetime, username=None, password=None, coordinates_selection_method=None):
    assert username == 'user' and password == 'pw'
    CM_CALLS.append(dataset_id)
    if dataset_id.startswith('cmems_obs-oc'):
        t = pd.date_range(max(pd.Timestamp(start_datetime), pd.Timestamp('2016-04-26')), pd.Timestamp(end_datetime), freq='D')
        lat = np.arange(minimum_latitude, maximum_latitude, 0.04); lon = np.arange(minimum_longitude, maximum_longitude, 0.04)
        rng = np.random.default_rng(5); wet = np.isin(t.month, [6, 7, 8, 9, 10, 11])
        a = (1 + 3 * wet)[:, None, None] * rng.gamma(2, 1, (len(t), len(lat), len(lon))); a[rng.random(a.shape) < 0.6] = np.nan
        return xr.Dataset({v: (('time', 'latitude', 'longitude'), a * (1 if v == 'SPM' else 0.1)) for v in variables},
                          coords={'time': t, 'latitude': lat, 'longitude': lon})
    med = '_med_' in dataset_id
    a0 = pd.Timestamp('2024-11-06') if 'anfc' in dataset_id else pd.Timestamp('1985-01-01' if med else '1980-01-01')
    a1 = pd.Timestamp('2026-11-11') if 'anfc' in dataset_id else pd.Timestamp('2026-09-30' if med else '2026-08-31')
    t = pd.date_range(max(pd.Timestamp(start_datetime), a0), min(pd.Timestamp(end_datetime), a1), freq='1h' if med else '3h')
    st = 1 / 24 if med else 0.2
    lat = np.arange(minimum_latitude, maximum_latitude, st); lon = np.arange(minimum_longitude, maximum_longitude, st)
    hs = (1.0 + 0.4 * np.sin(np.arange(len(t)) * 3 / 50)[:, None, None] + np.zeros((len(t), len(lat), len(lon)))).astype('float32'); hs[:, 0, :] = np.nan
    v = {'VHM0': hs, 'VTPK': hs * 6, 'VTM10': hs * 4, 'VMDR': hs * 80}
    return xr.Dataset({k: (('time', 'latitude', 'longitude'), v[k]) for k in variables}, coords={'time': t, 'latitude': lat, 'longitude': lon},
                      attrs={'title': dataset_id})
cm.open_dataset = open_dataset; sys.modules['copernicusmarine'] = cm

# ---------------- SlideRule ----------------
srm = types.ModuleType('sliderule'); srm.__version__ = '5.8.0'
srs = types.ModuleType('sliderule.sliderule'); srs.init = lambda **k: None; srs.get_version = lambda: {'server': 'mock'}
FAIL_ONCE = {2021}
def run(api, parms):
    y = int(parms['t0'][:4])
    if y in FAIL_ONCE: FAIL_ONCE.discard(y); raise RuntimeError('transient 503')
    if y == 2018: return None
    full = parms.get('atl24', {}).get('compact') is False
    rng = np.random.default_rng(y); recs = []
    for rgt in range(10 + (y % 3), 60, 4):
        n = 1500; e = rng.uniform(E0 + 30, E0 + SZ - 200, n); nn = N0 + 500 + (rgt - 10) * 380 + rng.normal(0, 5, n)
        d = depth_at(e) + rng.normal(0, 0.2, n); d[rng.random(n) < 0.01] += 8
        df = pd.DataFrame({'e': e, 'n': nn, 'rgt': rgt, 'cycle': y - 2015, 'spot': 1 + rgt % 6, 'surface_h': 0.1, 'ortho_h': 0.1 - d,
                           'class_ph': np.where(rng.random(n) < 0.03, 41, 40), 'confidence': rng.uniform(0.4, 1, n),
                           'x_atc': e})
        df.loc[rng.random(n) < 0.002, 'confidence'] = np.nan
        if full:
            df['low_confidence_flag'] = 0; df['invalid_kd'] = 0; df['sensor_depth_exceeded'] = (d > 33).astype(int); df['sigma_tvu'] = 0.3
        recs.append(df)
    df = pd.concat(recs, ignore_index=True)
    gg = gpd.GeoDataFrame(df, geometry=gpd.points_from_xy(df.e, df.n), crs='EPSG:32616').to_crs('EPSG:4326').drop(columns=['e', 'n'])
    gg.index = pd.DatetimeIndex([pd.Timestamp(f'{y}-03-01', tz='UTC')] * len(gg), name='time')
    return gg
srs.run = run
ic = types.ModuleType('sliderule.icesat2'); ic.SRT_LAND = 0
def atl08p(parms):
    assert parms['pass_invalid'] is False
    y = int(parms['t0'][:4]); rng = np.random.default_rng(100 + y); n = 300
    e = rng.uniform(E0 + 100, E0 + 2000, n); nn = rng.uniform(N0 + 100, N0 + SZ - 100, n)
    gg = gpd.GeoDataFrame({'rgt': rng.integers(1, 1300, n), 'cycle': 5, 'spot': 1, 'h_te_median': rng.normal(-10, 0.5, n),
                           'gnd_count': rng.integers(0, 30, n).astype(float), 'veg_count': rng.integers(0, 100, n),
                           'h_canopy': rng.uniform(3, 12, n), 'solar_elevation': rng.uniform(-30, 60, n)},
                          geometry=gpd.points_from_xy(e, nn), crs='EPSG:32616').to_crs('EPSG:4326')
    gg.loc[0, 'gnd_count'] = np.nan
    gg.index = pd.DatetimeIndex([pd.Timestamp(f'{y}-05-01', tz='UTC')] * n, name='time')
    return gg
ic.atl08p = atl08p
srm.sliderule = srs; srm.icesat2 = ic
sys.modules['sliderule'] = srm; sys.modules['sliderule.sliderule'] = srs; sys.modules['sliderule.icesat2'] = ic

