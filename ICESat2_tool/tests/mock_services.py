"""Fake SlideRule (and Colab) for offline tests. Import BEFORE icesat2_tool. Synthetic AOI: 20 x 20 km box in
UTM 16N, land strip on the west edge, depth increasing eastwards."""
import sys, types, os, shutil, time, json
import numpy as np, pandas as pd, geopandas as gpd
import matplotlib; matplotlib.use('Agg')
from shapely.geometry import box

ROOT = os.environ.get('ICESAT2_TEST_DIR', '/tmp/fake_icesat2')
shutil.rmtree(ROOT, ignore_errors=True); os.makedirs(ROOT)
time.sleep = lambda s: None
E0, N0, SZ = 300000.0, 1780000.0, 20000.0
CALLS = []

aoi = gpd.GeoDataFrame({'name': ['AOI']}, geometry=[box(E0, N0, E0 + SZ, N0 + SZ)], crs='EPSG:32616').to_crs('EPSG:4326')
AOI_FILE = os.path.join(ROOT, 'aoi.geojson'); aoi.to_file(AOI_FILE, driver='GeoJSON')
land = gpd.GeoDataFrame({'name': ['land']}, geometry=[box(E0 - 5000, N0 - 5000, E0 + 300, N0 + SZ + 5000)], crs='EPSG:32616')
SHORE_FILE = os.path.join(ROOT, 'land.gpkg'); land.to_file(SHORE_FILE, driver='GPKG')
mang = gpd.GeoDataFrame({'name': ['mangrove']}, geometry=[box(E0, N0 + 5000, E0 + 1500, N0 + 15000)], crs='EPSG:32616')
MANG_FILE = os.path.join(ROOT, 'mangroves.geojson'); mang.to_crs('EPSG:4326').to_file(MANG_FILE, driver='GeoJSON')

def depth_at(e): return np.clip((e - E0 - 90) / SZ * 35, 0, None)

srm = types.ModuleType('sliderule'); srm.__version__ = '5.8.0'
srs = types.ModuleType('sliderule.sliderule'); srs.init = lambda **k: None; srs.get_version = lambda: {'server': 'mock'}
FAIL_ONCE = {2021}
def run(api, parms):
    CALLS.append(api)
    assert api == 'atl24x' and parms['atl24']['compact'] is False
    y = int(parms['t0'][:4])
    if y in FAIL_ONCE: FAIL_ONCE.discard(y); raise RuntimeError('transient 503')
    if y == 2018: return None
    rng = np.random.default_rng(y); recs = []
    for rgt in range(10 + (y % 3), 60, 4):
        n = 1500; e = rng.uniform(E0 + 30, E0 + SZ - 200, n); nn = N0 + 500 + (rgt - 10) * 380 + rng.normal(0, 5, n)
        d = depth_at(e) + rng.normal(0, 0.2, n); d[rng.random(n) < 0.01] += 8
        df = pd.DataFrame({'e': e, 'n': nn, 'rgt': rgt, 'cycle': y - 2015, 'spot': 1 + rgt % 6, 'surface_h': 0.1, 'ortho_h': 0.1 - d,
                           'class_ph': np.where(rng.random(n) < 0.03, 41, 40), 'confidence': rng.uniform(0.4, 1, n), 'x_atc': e,
                           'low_confidence_flag': 0, 'invalid_kd': 0, 'sensor_depth_exceeded': (d > 33).astype(int), 'sigma_tvu': 0.3})
        df.loc[rng.random(n) < 0.002, 'confidence'] = np.nan
        recs.append(df)
    df = pd.concat(recs, ignore_index=True)
    g = gpd.GeoDataFrame(df, geometry=gpd.points_from_xy(df.e, df.n), crs='EPSG:32616').to_crs('EPSG:4326').drop(columns=['e', 'n'])
    g.index = pd.DatetimeIndex([pd.Timestamp(f'{y}-03-01', tz='UTC')] * len(g), name='time')
    return g
srs.run = run
ic = types.ModuleType('sliderule.icesat2'); ic.SRT_LAND = 0
def atl08p(parms):
    CALLS.append('atl08p'); assert parms['pass_invalid'] is False
    y = int(parms['t0'][:4]); rng = np.random.default_rng(100 + y); n = 300
    e = rng.uniform(E0 + 100, E0 + 2000, n); nn = rng.uniform(N0 + 100, N0 + SZ - 100, n)
    g = gpd.GeoDataFrame({'rgt': rng.integers(1, 1300, n), 'cycle': 5, 'spot': 1, 'h_te_median': rng.normal(-10, 0.5, n),
                          'gnd_count': rng.integers(0, 30, n).astype(float), 'veg_count': rng.integers(0, 100, n),
                          'h_canopy': rng.uniform(3, 12, n), 'solar_elevation': rng.uniform(-30, 60, n)},
                         geometry=gpd.points_from_xy(e, nn), crs='EPSG:32616').to_crs('EPSG:4326')
    g.loc[0, 'gnd_count'] = np.nan
    g.index = pd.DatetimeIndex([pd.Timestamp(f'{y}-05-01', tz='UTC')] * n, name='time')
    return g
ic.atl08p = atl08p
srm.sliderule = srs; srm.icesat2 = ic
sys.modules['sliderule'] = srm; sys.modules['sliderule.sliderule'] = srs; sys.modules['sliderule.icesat2'] = ic
