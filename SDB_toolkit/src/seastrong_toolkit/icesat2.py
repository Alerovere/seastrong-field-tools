"""Step 5 — ICESat-2 lidar: bathymetry (ATL24) and mangrove ground / canopy (ATL08).

## Module 5 — ICESat-2 lidar: bathymetry (ATL24) and mangrove ground / canopy (ATL08)

ICESat-2 is **not in the Earth Engine catalogue**, so this module downloads it with
[SlideRule](https://slideruleearth.io) (no login needed) and does the cleaning in Python.

**Order of operations (why it matters).** Validation must not help decide how the data are cleaned or where
the optical limit lies, otherwise validation errors look better than they are. So:

1. **5a – download** ATL24 year by year (retries, per-year cache, coverage table), with the **full schema**
   (`compact: False`); required fields are checked and missing or non-finite values are flagged, never passed.
2. **5b – independent QC** that uses no information from other tracks: ATL24 class/confidence and product
   flags, depth bounds, land and distance to the coast, along-track spikes.
3. **5c – reserve validation tracks.** Whole reference ground tracks (RGTs) are assigned to validation by a
   simple rule (`rgt % m == k`), chosen *once* and **locked** in a JSON file in My Drive; later runs re-use it
   (new RGTs follow the same rule). If no feasible split exists the module says so — it never falls back to a
   random point split.
4. **5d – cross-track consistency** of each photon against **training passes only** (true radius search,
   flagged references excluded, one vote per independent pass). Validation photons get the flag for
   information but are not removed (`XT_APPLY_TO_VALID = False`).
5. **5e – depth limit of SDB** fitted on **training tracks only**, with track bootstrap and sensitivity tests;
   then the **exploratory** optically deep / shallow / unknown map.
6. **5f – exports and QC figure**, **5g – ATL08** over mangroves.

| Flag | Test | Why |
|---|---|---|
| `f_missing` | a required value (`ortho_h`, `surface_h`, `class_ph`, `confidence`, `sigma_tvu`, ATL24 flags) is missing or not finite | an unknown value is not a pass |
| `f_class` | `class_ph` ≠ 40 (seabed) or `confidence` < threshold | not a confident seabed return |
| `f_atl24` | `low_confidence_flag`, `invalid_kd`, `sensor_depth_exceeded` set, or `sigma_tvu` > threshold | the product marks the photon unreliable / deeper than clarity allows |
| `f_depth` | depth < `DEPTH_MIN` or > `DEPTH_MAX` | physically implausible here |
| `f_land` / `f_shore` | in a land cell, or closer than `SHORE_BUFFER` to the land edge | shore returns misclassified as seabed |
| `f_spike` | > max(`SPIKE_MIN`, 3 × running MAD) from the along-track running median | isolated noise |
| `f_xtrack` | > max(`XT_MIN`, `XT_REL` × depth) from the median of ≥ `XT_MIN_PASSES` other training passes within `XT_RADIUS` | inconsistent between independent passes |

**Depth and datum.** `ortho_h` is the seabed elevation relative to EGM2008 (negative below the geoid) — the
Bathymetrix-AI training field. `depth = surface_h − ortho_h` is the instantaneous water depth (both share the
datum). EGM2008 is neither local mean sea level nor chart datum.

**Shore distance.** The land mask is the Copernicus DEM water-body mask (30 m), read 2 km beyond the AOI so
coastlines just outside it count. The distance from each photon's exact position to the nearest land cell is
taken *conservatively* (to the cell centre minus half its diagonal, i.e. never more than the true distance to
that cell), so `SHORE_BUFFER` really adds clearance. A 30 m mask cannot place a coast to a few metres: for
precise work give a digitised shoreline in `SHORELINE_FILE` (land polygons), used for exact distances.

### 5a–5b: download ATL24, validate the schema, independent quality control

### 5c: reserve and lock the validation tracks

Done **before** any rule that compares tracks or fits a curve to depths. The rule `rgt % m == k` is chosen
once — the candidate whose validation share is closest to `VALID_SHARE` while keeping the depth
distributions similar — and written to the lock file. Later runs re-use the lock; RGTs not seen before are
assigned by the same rule, so validation tracks never move into training. To start a new hold-out
deliberately, delete the lock file (and say so in your methods).

### 5d: cross-track consistency against training passes

Photons are first summarised in `XT_BIN`-m along-track bins (median depth, centroid) per beam. For each bin,
all **training** bins within `XT_RADIUS` (a true radius) from **other passes** (other RGT/cycle) that passed the
independent QC are collected; each pass contributes one value (its median). With ≥ `XT_MIN_PASSES` passes, the
reference depth is the median of those pass values, and photons of the bin deviating by more than
max(`XT_MIN`, `XT_REL` × reference) are flagged. Reference depth, number of passes and mean distance are saved.
Real reef relief or seabed change can also cause disagreement, so inspect `f_xtrack` in QGIS before trusting it.

### 5e: depth limit of satellite-derived bathymetry ("too deep for Bathymetrix-AI")

The Stumpf ratio ln(1000·Blue)/ln(1000·Green) of the Module 1 composite is sampled at the clean **training**
photons and plotted against depth. Where the image "sees" the seabed the ratio changes steadily with depth;
beyond the **saturation depth z_sat** the binned median flattens.

- **Uniform depth grid**: bins of `SDB_BIN` m are kept in depth coordinates; a bin counts only if it has
  ≥ `SDB_MIN_PER_BIN` photons from ≥ `SDB_MIN_RGT_PER_BIN` different RGTs (one dense pass cannot make a bin),
  so the flatness test always spans exactly `SDB_FLAT_SPAN` m.
- **Uncertainty**: RGTs are resampled with replacement (`SDB_BOOT` times) → a 5–95 % interval for z_sat.
- **Sensitivity**: z_sat with other bin sizes, tolerances and spans, and with the median composite.
- If the data are too sparse or no plateau is found, the status is **unresolved** and **no** photon is
  certified as within the optical limit (`sdb_domain = unknown`).

The optically deep / shallow map is **exploratory**: a global ratio threshold is a simplification (dark
seagrass saturates shallower than bright sand). It is restricted to water (Copernicus DEM mask) inside the AOI
with composite coverage, and has an **unknown** class for pixels near the threshold (inside the bootstrap
interval) and for small patches removed by cleaning.

### 5f: exports for Bathymetrix-AI and QC figure

### 5g: ATL08 ground and canopy heights over mangroves

SlideRule's ATL08 / PhoREAL processing gives, per 100 m segment, the **ground** height (WGS84 ellipsoid) and
canopy heights above ground. Only segments SlideRule considers valid are requested (`pass_invalid: False`).
Field names differ between SlideRule endpoints (legacy `gnd_count` / `veg_count` vs `ground_photon_count` /
`vegetation_photon_count`); they are normalised, and segments with missing or non-finite counts or heights are
flagged, never passed.

**Geoid conversion is verified, not assumed.** The ellipsoid → EGM2008 transformation must be a real grid-based
PROJ operation (not the no-shift "ballpark" fallback PROJ uses when the grid is missing); the grid is
downloaded if needed. Ellipsoidal (`ground_h_ellipsoid`) and EGM2008 (`ground_h_egm08`) heights are stored in
separate columns with the transformation status. If the conversion cannot be verified, `ground_h_egm08` stays
empty and the DEM comparison (DEMs are EGM2008) is skipped.
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

import geopandas as gpd
import rasterio, rasterio.windows
from rasterio import features as rfeatures
from shapely.geometry import shape
from scipy import ndimage, stats
from scipy.spatial import cKDTree
ATL24_REQUIRED = ['ortho_h', 'surface_h', 'class_ph', 'confidence', 'rgt', 'cycle']
ATL24_QC_ALIASES = {'sigma_tvu': ['sigma_tvu'], 'invalid_kd': ['invalid_kd'],
                    'sensor_depth_exceeded': ['sensor_depth_exceeded'],
                    'low_confidence_flag': ['low_confidence_flag', 'low_conf_flag']}
def ee_pixels(img, x0, y1, scale, w, h, crs=CRS, block=2048):
    """Download a single-band UInt8 image on an exact grid (origin x0, y1; size w x h) as numpy, in blocks."""
    out = np.zeros((h, w), np.uint8)
    for r0 in range(0, h, block):
        for c0 in range(0, w, block):
            hh, ww = min(block, h - r0), min(block, w - c0)
            arr = ee.data.computePixels({
                'expression': img.toUint8(), 'fileFormat': 'NUMPY_NDARRAY',
                'grid': {'dimensions': {'width': ww, 'height': hh},
                         'affineTransform': {'scaleX': scale, 'shearX': 0, 'translateX': x0 + c0 * scale,
                                             'shearY': 0, 'scaleY': -scale, 'translateY': y1 - r0 * scale},
                         'crsCode': crs}})
            arr = arr[arr.dtype.names[0]] if arr.dtype.names else arr
            out[r0:r0 + hh, c0:c0 + ww] = np.asarray(arr)
    return out
def wide_grid(scale, buffer_m):
    x0 = GRID_X0 - buffer_m; y1 = GRID_Y1 + buffer_m
    w = int(np.ceil((GRID_X1 - GRID_X0 + 2 * buffer_m) / scale)); h = int(np.ceil((GRID_Y1 - GRID_Y0 + 2 * buffer_m) / scale))
    return x0, y1, scale, w, h
def sample_grid(arr, tr, x, y):
    x0, y1, s = tr
    c = np.floor((x - x0) / s).astype(int); r = np.floor((y1 - y) / s).astype(int)
    ok = (r >= 0) & (r < arr.shape[0]) & (c >= 0) & (c < arr.shape[1])
    out = np.full(len(x), np.nan); out[ok] = arr[r[ok], c[ok]]
    return out
def coast_distance(x, y):
    """(distance to land in m, conservative; in_land bool, NaN if unknown) for projected points."""
    if IS2['SHORELINE_FILE']:
        land = gpd.read_file(IS2['SHORELINE_FILE']).to_crs(CRS)
        pts = gpd.GeoSeries(gpd.points_from_xy(x, y), crs=CRS)
        tree = __import__('shapely').STRtree(land.geometry.values)
        _, dist = tree.query_nearest(pts.values, return_distance=True, all_matches=False)
        return dist, (dist == 0).astype(float), 'shoreline file (exact)'
    x0, y1, s, w, h = wide_grid(30, IS2['LAND_BUFFER_M'])
    # outside Copernicus DEM tiles there is open sea -> unmask(1) (water); land = WBM 0
    wm = ee_pixels(water.unmask(1).rename('w'), x0, y1, s, w, h)
    land = wm == 0
    in_land = sample_grid(land.astype(float), (x0, y1, s), x, y)
    edge = land & ndimage.binary_dilation(~land)
    r, cidx = np.nonzero(edge)
    if not len(r):
        return np.full(len(x), np.inf), in_land, 'CopDEM WBM 30 m (no land in grid)'
    tree = cKDTree(np.c_[x0 + (cidx + 0.5) * s, y1 - (r + 0.5) * s])
    d, _ = tree.query(np.c_[x, y], workers=-1)
    return np.maximum(d - s * np.sqrt(2) / 2, 0.0), in_land, f'CopDEM WBM 30 m, AOI + {IS2["LAND_BUFFER_M"]} m, conservative cell distance'
def sliderule_versions():
    try:
        import sliderule
        from sliderule import sliderule as sr
        v = {'client': getattr(sliderule, '__version__', 'unknown')}
        try: v['server'] = sr.get_version()
        except Exception as e: v['server'] = f'unavailable ({str(e)[:80]})'
        return v
    except Exception as e:
        return {'error': str(e)[:120]}
def sliderule_years(api, parms_extra, t0, t1, fn=None):
    """SlideRule request year by year over the AOI bounding box, with retries and a per-year cache.
    Returns (GeoDataFrame or None, coverage DataFrame)."""
    from sliderule import sliderule as sr
    sr.init(verbose=False)
    x0, y0, x1, y1 = aoi_bbox_wgs84()
    poly = [{'lon': x0, 'lat': y0}, {'lon': x1, 'lat': y0}, {'lon': x1, 'lat': y1}, {'lon': x0, 'lat': y1},
            {'lon': x0, 'lat': y0}]
    out, cov = [], []
    for y in range(int(t0[:4]), int(t1[:4]) + 1):
        a = max(pd.Timestamp(t0), pd.Timestamp(f'{y}-01-01')); z = min(pd.Timestamp(t1), pd.Timestamp(f'{y}-12-31 23:59:59'))
        key = hashlib.sha256(json.dumps({'api': api, 'poly': poly, 'parms': parms_extra, 'a': str(a), 'z': str(z.date())}, sort_keys=True, default=str).encode()).hexdigest()[:10]
        cache = drive_path('cache', f'sliderule_{api}_{y}_{key}.parquet')
        row = dict(api=api, year=y, requested_start=str(a.date()), requested_end=str(z.date()))
        if os.path.exists(cache):
            g = gpd.read_parquet(cache); row.update(status='ok (cache)', n=len(g), attempts=0)
        else:
            g = None
            for k in range(1, IS2['SR_RETRIES'] + 1):
                parms = {'poly': poly, 't0': a.strftime('%Y-%m-%dT%H:%M:%SZ'), 't1': z.strftime('%Y-%m-%dT%H:%M:%SZ'), **parms_extra}
                try:
                    g = fn(parms) if fn else sr.run(api, parms)
                    n = 0 if g is None else len(g)
                    row.update(status='ok' if n else 'empty', n=n, attempts=k)
                    if n:
                        g = gpd.GeoDataFrame(g, geometry='geometry', crs=g.crs or 'EPSG:4326')
                        if isinstance(g.index, pd.DatetimeIndex):
                            g = g.reset_index()
                            if 'time' not in g and 'index' in g: g = g.rename(columns={'index': 'time'})
                        g.to_parquet(cache)
                    break
                except Exception as e:
                    row.update(status='failed', n=0, attempts=k, error=str(e)[:300])
                    print(f'  {api} {y}: attempt {k} failed ({str(e)[:120]})'); time.sleep(20 * k)
        print(f"  {api} {y}: {row['status']}, {row.get('n', 0):,} records")
        if g is not None and len(g): out.append(g)
        if g is not None and len(g) and 'time' in g:
            row.update(first=str(pd.to_datetime(g['time']).min()), last=str(pd.to_datetime(g['time']).max()))
        cov.append(row)
    cov = pd.DataFrame(cov)
    if not out: return None, cov
    g = pd.concat(out, ignore_index=True)
    g = gpd.GeoDataFrame(g, geometry='geometry', crs=out[0].crs or 'EPSG:4326')
    if 'time' not in g:
        g['time'] = pd.NaT
    g['time'] = pd.to_datetime(g['time'], utc=True, errors='coerce')
    return g, cov
def normalise_atl24(g):
    """Rename documented aliases, coerce numerics, check required fields. Returns (g, schema report)."""
    rep = dict(columns=list(map(str, g.columns)), missing_required=[], missing_qc=[], aliases_used={})
    for canon, al in ATL24_QC_ALIASES.items():
        hit = next((a for a in al if a in g.columns), None)
        if hit is None: rep['missing_qc'].append(canon)
        elif hit != canon: g = g.rename(columns={hit: canon}); rep['aliases_used'][hit] = canon
    rep['missing_required'] = [k for k in ATL24_REQUIRED if k not in g.columns]
    for k in ATL24_REQUIRED + list(ATL24_QC_ALIASES):
        if k in g: g[k] = pd.to_numeric(g[k], errors='coerce')
    return g, rep


def composite_files(kind='p30'):
    """Composite GeoTIFF(s) of THIS run, from the manifest (or the validated manual file)."""
    if kind == 'p30' and IS2['COMPOSITE_TIF']:
        return [IS2['COMPOSITE_TIF']]
    s2m = manifest('s2').get('outputs') or {}
    tn = s2m.get('composite_task') if kind == 'p30' else s2m.get('median_task')
    if not tn or tn not in manifest('s2')['tasks']: return []
    if manifest('s2')['tasks'][tn].get('state') != 'COMPLETED':
        wait([tn])
    return task_files(tn)
def validate_composite(files, expect_bands=(12, 4)):
    """Check CRS, band count, type, NoData and value range; returns 1-based indices of B2 and B3."""
    rep = []
    for f in files:
        with rasterio.open(f) as src:
            if src.crs is None: raise ValueError(f'{f}: no CRS')
            if src.count not in expect_bands: raise ValueError(f'{f}: {src.count} bands, expected {expect_bands}')
            if src.dtypes[0] != 'float32': raise ValueError(f'{f}: {src.dtypes[0]}, expected float32 reflectance')
            desc = list(src.descriptions)
            i2 = desc.index('B2') + 1 if 'B2' in desc else 2
            i3 = desc.index('B3') + 1 if 'B3' in desc else 3
            win = rasterio.windows.Window(src.width // 2 - 256, src.height // 2 - 256, 512, 512).intersection(
                rasterio.windows.Window(0, 0, src.width, src.height))
            v = src.read(i2, window=win).astype(float); nd = src.nodata if src.nodata is not None else -9999
            v = v[(v != nd) & np.isfinite(v)]
            med = float(np.median(v)) if len(v) else None
            if med is not None and not (0 <= med <= 1): raise ValueError(f'{f}: B2 median {med} is not reflectance 0-1')
            rep.append(dict(file=f, crs=str(src.crs), count=src.count, nodata=nd, b2_index=i2, b3_index=i3, b2_center_median=med))
    return rep
def sample_composite(files, gx, gy, b2i=2, b3i=3):
    """Blue and green reflectance at points (points reprojected to each raster's CRS)."""
    from pyproj import Transformer
    b2 = np.full(len(gx), np.nan); b3 = np.full(len(gx), np.nan)
    for f in files:
        with rasterio.open(f) as src:
            x_, y_ = (gx, gy) if str(src.crs) == CRS else Transformer.from_crs(CRS, src.crs, always_xy=True).transform(gx, gy)
            cols, rows = ~src.transform * (np.asarray(x_), np.asarray(y_))
            rows, cols = np.floor(rows).astype(int), np.floor(cols).astype(int)
            ins = (rows >= 0) & (rows < src.height) & (cols >= 0) & (cols < src.width)
            if not ins.any(): continue
            nd = src.nodata if src.nodata is not None else -9999
            for band, out in ((b2i, b2), (b3i, b3)):
                a = src.read(band).astype(np.float32); a[(a == nd) | (a <= -9000)] = np.nan
                out[ins] = a[rows[ins], cols[ins]]
    return b2, b3
def stumpf_ratio(b2, b3):
    b2 = np.asarray(b2, float); b3 = np.asarray(b3, float)
    with np.errstate(invalid='ignore', divide='ignore'):
        r = np.log(1000 * b2) / np.log(1000 * b3)
    r[~np.isfinite(r) | (b2 <= 0.001) | (b3 <= 0.001)] = np.nan
    return r
PROFILE_COLS = ['depth', 'n', 'n_rgt', 'median', 'q1', 'q3', 'supported', 'median_smooth']
def saturation_depth(depth, ratio, rgt, p=None):
    """Gap-aware saturation depth. Returns (result dict, profile with a fixed schema)."""
    p = {**IS2, **(p or {})}
    depth, ratio, rgt = np.asarray(depth, float), np.asarray(ratio, float), np.asarray(rgt)
    ok = np.isfinite(depth) & np.isfinite(ratio)
    res = dict(z_sat=None, r_sat=None, status='insufficient_data', n=int(ok.sum()), n_rgt=int(len(np.unique(rgt[ok]))) if ok.any() else 0)
    if res['n'] < p['SDB_MIN_PHOTONS'] or res['n_rgt'] < p['SDB_MIN_RGT']:
        return res, pd.DataFrame(columns=PROFILE_COLS)
    d, r, g = depth[ok], ratio[ok], rgt[ok]
    edges = np.arange(0, np.max(d) + p['SDB_BIN'], p['SDB_BIN'])
    k = np.digitize(d, edges) - 1
    rows = []
    for i in range(len(edges) - 1):
        m = k == i; s = r[m]
        nr = len(np.unique(g[m])) if m.any() else 0
        sup = len(s) >= p['SDB_MIN_PER_BIN'] and nr >= p['SDB_MIN_RGT_PER_BIN']
        rows.append(dict(depth=(edges[i] + edges[i + 1]) / 2, n=int(len(s)), n_rgt=int(nr),
                         median=float(np.median(s)) if len(s) else np.nan,
                         q1=float(np.percentile(s, 25)) if len(s) else np.nan,
                         q3=float(np.percentile(s, 75)) if len(s) else np.nan, supported=sup))
    prof = pd.DataFrame(rows, columns=PROFILE_COLS[:-1])
    med = prof['median'].where(prof.supported)
    sm = med.rolling(3, center=True, min_periods=2).median().where(prof.supported)
    prof['median_smooth'] = sm
    v = sm.values
    if np.isfinite(v).sum() < 6:
        return res, prof
    rng = np.nanmax(v) - np.nanmin(v)
    step = np.abs(np.diff(v))                                  # NaN where a neighbour is unsupported
    if not np.isfinite(step).any() or rng <= 0:
        res['status'] = 'no_plateau'; return res, prof
    peak = int(np.nanargmax(step))
    kk = int(round(p['SDB_FLAT_SPAN'] / p['SDB_BIN']))
    last = np.where(np.isfinite(v))[0][-1]
    res['status'] = 'no_plateau'
    for i in range(peak, len(v) - kk):
        if not (np.isfinite(v[i]) and np.isfinite(v[i + kk])): continue      # exact span in depth units
        if abs(v[i + kk] - v[i]) < p['SDB_FLAT_TOL'] * rng and abs(v[last] - v[i]) < 2 * p['SDB_FLAT_TOL'] * rng:
            res.update(z_sat=float(prof.depth.iloc[i]), r_sat=float(v[i]), status='resolved'); break
    if res['status'] == 'resolved':                 # the ratio must really change with depth above z_sat
        sh = d < res['z_sat']
        rho = stats.spearmanr(d[sh], r[sh]).correlation if sh.sum() > 10 else np.nan
        res['spearman_above'] = float(rho) if np.isfinite(rho) else None
        if not np.isfinite(rho) or abs(rho) < p['SDB_MIN_RHO']:
            res.update(status='no_depth_signal', z_sat=None, r_sat=None)
    return res, prof
def bootstrap_zsat(depth, ratio, rgt, n_boot, max_pts=200_000, seed=42):
    rng_ = np.random.default_rng(seed)
    u = np.unique(rgt); by = {r: np.where(rgt == r)[0] for r in u}
    zs = []
    for _ in range(n_boot):
        pick = rng_.choice(u, len(u), replace=True)
        idx = np.concatenate([by[r] for r in pick])
        if len(idx) > max_pts: idx = rng_.choice(idx, max_pts, replace=False)
        zs.append(saturation_depth(depth[idx], ratio[idx], rgt[idx])[0]['z_sat'])
    zs = np.array([z if z is not None else np.nan for z in zs], float)
    fin = zs[np.isfinite(zs)]
    return dict(resolved_frac=float(np.isfinite(zs).mean()),
                z_p05=float(np.percentile(fin, 5)) if len(fin) else None,
                z_p50=float(np.percentile(fin, 50)) if len(fin) else None,
                z_p95=float(np.percentile(fin, 95)) if len(fin) else None)


def run(ctx=None, force=False):
    """Run this step. Same settings = same folder: finished exports and stages are re-used
    (force=True starts them again)."""
    global ATL08_ALIASES, BOOT, D, EVAL, F, FLAGS, G, GEO, HOLDOUT_LOCK, INDEP, IS2_OUT, IS2_T1, KEEP, LOCK, \
           MASK_COUNTS, PROF, R, SENS, SPLIT_STATUS, T, VAL_REPORT, Z, al, allset, aoi_utm, apply_xt, atl24, \
           ax, ax1, ax2, axb, axc, axs, b2, b2i, b3, b3i, bad, base, bey, bins, c, canon, choose_holdout, cls, \
           cnt, coast_src, col_, comp_rep, conf, cov08, cov24, dem_values, dep, diag, diffs, dist_coast, dm, \
           ev, ev_, f, failed_years, fig, files, fin, fit, flag, found, g, geoid_transformer, gmw_img, good, \
           gp, gs, h, hb, hc, hcol, hge, hh, hi, hit, i, icesat2, idx_ok, in_land, k, keep, key, lab, labs, \
           lat0, lo, lon0, mad, mb2, mb3, med, mfiles, mg, n_eval, new, num, o, ok, optical_class_map, order, \
           p, parms08, pre, q, q08, qs, r_, r_hi, r_lo, req, rgts_now, rows, rule, s, sc, schema, sfx, sig, \
           sign, sm, sp, spike, sub, summary, use, v, v08, v08u, vals, vr, vv, w, write_gpkg, x, x0, xs, xt, \
           xtrack, y, y1, ys, zs, zz
    ctx = bind(globals(), 'icesat2', ctx)
    ctx.force = force
    figure_style()
    IS2_T1 = IS2['T1'] or TODAY.isoformat()
    HOLDOUT_LOCK = IS2['HOLDOUT_LOCK'] or os.path.join(DRIVE_ROOT, f'{FOLDER_ROOT}_ICESat2_holdout_lock.json')
    IS2_OUT = {}
    c = IS2
    print('5a. Downloading ATL24 (SlideRule, full schema) ...')
    IS2_OUT['sliderule'] = sliderule_versions()
    atl24, cov24 = sliderule_years('atl24x', {'atl24': {'compact': False}}, c['T0'], IS2_T1)
    cov24.to_csv(drive_path('icesat2', f'{PREFIX}_ATL24_download_coverage.csv'), index=False)
    MANIFEST['coverage']['atl24'] = cov24.to_dict('records'); save_manifest()
    failed_years = cov24.loc[cov24.status == 'failed', 'year'].tolist()
    if failed_years: print(f'  WARNING: years without data because the request failed: {failed_years} (status "partial")')
    if atl24 is None or atl24.empty:
        raise RuntimeError('No ATL24 data returned for the AOI (see the coverage table)')
    atl24, schema = normalise_atl24(atl24)
    IS2_OUT['schema'] = schema
    if schema['missing_required']:
        raise RuntimeError(f"ATL24 response lacks required fields {schema['missing_required']}; got {schema['columns']}")
    if schema['missing_qc'] and c['ON_MISSING_QC_FIELD'] == 'fail':
        raise RuntimeError(f"ATL24 response lacks QC fields {schema['missing_qc']} (was compact=False honoured?). "
                           f"Columns: {schema['columns']}. Set IS2['ON_MISSING_QC_FIELD'] = 'quarantine' to continue with all photons flagged.")
    atl24 = atl24[atl24.intersects(aoi_shapely())].copy().reset_index(drop=True)
    print(f'  {len(atl24):,} ATL24 photons inside the AOI; fields: {len(schema["columns"])}; aliases: {schema["aliases_used"] or "none"}')

    atl24['depth'] = atl24['surface_h'] - atl24['ortho_h']             # instantaneous water depth (m, positive down)
    atl24['spot'] = atl24['spot'] if 'spot' in atl24 else atl24.get('gt', 0)
    atl24['rgt'] = atl24['rgt'].astype('Int64'); atl24['cycle'] = atl24['cycle'].astype('Int64')
    atl24['pass_id'] = atl24['rgt'].astype(str) + '_' + atl24['cycle'].astype(str)            # one overpass
    atl24['track_id'] = atl24['pass_id'] + '_' + atl24['spot'].astype(str)                    # one beam of it
    atl24 = atl24.to_crs(CRS)
    x, y = atl24.geometry.x.values, atl24.geometry.y.values

    print('5b. Independent quality control ...')
    F = pd.DataFrame(index=atl24.index); EVAL = {}
    num = lambda k: atl24[k].values.astype(float) if k in atl24 else np.full(len(atl24), np.nan)
    req = ['ortho_h', 'surface_h', 'class_ph', 'confidence'] + [k for k in ATL24_QC_ALIASES if k in atl24]
    fin = np.column_stack([np.isfinite(num(k)) for k in req])
    F['f_missing'] = ~fin.all(axis=1) | (bool(schema['missing_qc']))      # quarantine if QC fields absent
    EVAL['f_missing'] = len(atl24)
    cls, conf = num('class_ph'), num('confidence')
    ok = np.isfinite(cls) & np.isfinite(conf)
    F['f_class'] = ok & ((cls != 40) | (conf < c['MIN_CONFIDENCE'])); EVAL['f_class'] = int(ok.sum())
    f = np.zeros(len(atl24), bool); ev = np.zeros(len(atl24), bool)
    for flag in ['low_confidence_flag', 'invalid_kd', 'sensor_depth_exceeded']:
        v = num(flag); f |= np.isfinite(v) & (v != 0); ev |= np.isfinite(v)
    sig = num('sigma_tvu'); f |= np.isfinite(sig) & (sig > c['MAX_SIGMA_TVU']); ev |= np.isfinite(sig)
    F['f_atl24'] = f; EVAL['f_atl24'] = int(ev.sum())
    dep = atl24['depth'].values.astype(float)
    F['f_depth'] = np.isfinite(dep) & ((dep < c['DEPTH_MIN']) | (dep > c['DEPTH_MAX'])); EVAL['f_depth'] = int(np.isfinite(dep).sum())

    dist_coast, in_land, coast_src = coast_distance(x, y)
    atl24['dist_coast_m'] = dist_coast
    F['f_land'] = np.isfinite(in_land) & (in_land == 1); F['f_missing'] |= ~np.isfinite(in_land)
    F['f_shore'] = ~F['f_land'] & (dist_coast < c['SHORE_BUFFER'])
    EVAL['f_land'] = EVAL['f_shore'] = int(np.isfinite(in_land).sum())
    IS2_OUT['coast_source'] = coast_src

    # along-track despiking (per beam of each pass, ordered along track); its own track only
    order = 'x_atc' if 'x_atc' in atl24 else 'time'
    spike = pd.Series(False, index=atl24.index)
    base = ~(F[['f_missing', 'f_class', 'f_atl24', 'f_depth', 'f_land']].any(axis=1))
    for _, g in atl24[base].sort_values(order).groupby('track_id'):
        med = g['depth'].rolling(c['SPIKE_WINDOW'], center=True, min_periods=5).median()
        mad = (g['depth'] - med).abs().rolling(c['SPIKE_WINDOW'], center=True, min_periods=5).median()
        spike.loc[g.index] = ((g['depth'] - med).abs() > np.maximum(c['SPIKE_MIN'], 3 * 1.4826 * mad)).fillna(False)
    F['f_spike'] = spike; EVAL['f_spike'] = int(base.sum())
    INDEP = ['f_missing', 'f_class', 'f_atl24', 'f_depth', 'f_land', 'f_shore', 'f_spike']
    atl24 = atl24.join(F)
    atl24['qc_indep_ok'] = ~F[INDEP].any(axis=1)
    IS2_OUT['qc_eval'] = EVAL
    print('  photons evaluated / flagged per rule:', {k: (EVAL[k], int(F[k].sum())) for k in INDEP})
    print(f"  passing independent QC: {int(atl24.qc_indep_ok.sum()):,} of {len(atl24):,}")
    stage_done('is2_download_qc', n=len(atl24), n_ok=int(atl24.qc_indep_ok.sum()), failed_years=failed_years)

    def choose_holdout(df, c=None):
        c = IS2 if c is None else c
        rg = df['rgt'].astype(int)
        n_rgt = rg.nunique()
        diag = dict(n_rgt=int(n_rgt), photons_per_rgt=rg.value_counts().sort_index().to_dict())
        if n_rgt < c['MIN_RGT_TOTAL']:
            return None, dict(diag, reason=f'only {n_rgt} RGTs (< MIN_RGT_TOTAL {c["MIN_RGT_TOTAL"]})')
        best = None
        for mod in (3, 4, 5, 6):
            for off in range(mod):
                v = (rg % mod) == off
                nv, nt = rg[v].nunique(), rg[~v].nunique()
                if nv < c['MIN_RGT_VALID'] or nt < 2 or v.sum() < c['MIN_PHOTONS_SIDE'] or (~v).sum() < c['MIN_PHOTONS_SIDE']:
                    continue
                ks = stats.ks_2samp(df.depth[v], df.depth[~v]).statistic
                score = abs(v.mean() - c['VALID_SHARE']) + 0.5 * ks
                if best is None or score < best[0]: best = (score, mod, off, float(v.mean()), float(ks))
        if best is None:
            return None, dict(diag, reason='no rgt-modulo rule leaves enough RGTs and photons on both sides')
        return dict(mod=best[1], off=best[2], share=best[3], ks=best[4]), diag

    pre = atl24[atl24.qc_indep_ok]
    rgts_now = sorted(pre['rgt'].astype(int).unique().tolist())
    if os.path.exists(HOLDOUT_LOCK):
        LOCK = json.load(open(HOLDOUT_LOCK))
        new = [r for r in rgts_now if r not in LOCK['all_rgts']]
        if new:
            LOCK['valid_rgts'] = sorted(set(LOCK['valid_rgts']) | {r for r in new if r % LOCK['mod'] == LOCK['off']})
            LOCK['all_rgts'] = sorted(set(LOCK['all_rgts']) | set(new))
            LOCK.setdefault('history', []).append(dict(run_id=RUN_ID, added_rgts=new, utc=dt.datetime.now(dt.timezone.utc).isoformat()))
            json.dump(LOCK, open(HOLDOUT_LOCK, 'w'), indent=1)
        print(f"5c. Hold-out lock re-used ({HOLDOUT_LOCK}): rgt % {LOCK['mod']} == {LOCK['off']}; {len(new)} new RGTs assigned by the rule")
        SPLIT_STATUS = 'locked'
    else:
        rule, diag = choose_holdout(pre)
        if rule is None:
            LOCK, SPLIT_STATUS = None, 'infeasible'
            print('5c. NO FEASIBLE TRACK SPLIT:', diag['reason'])
            print('    photons per RGT:', diag['photons_per_rgt'])
            print('    -> training/validation files are NOT written. Extend the period, enlarge the AOI, or validate with echosounder data.')
            IS2_OUT['split_diag'] = diag
        else:
            LOCK = dict(created_utc=dt.datetime.now(dt.timezone.utc).isoformat(), created_run=RUN_ID, **rule,
                        valid_rgts=[r for r in rgts_now if r % rule['mod'] == rule['off']], all_rgts=rgts_now,
                        note='Chosen once before cross-track QC and depth-limit fitting; do not retune after seeing results.')
            json.dump(LOCK, open(HOLDOUT_LOCK, 'w'), indent=1)
            SPLIT_STATUS = 'new_lock'
            print(f"5c. Hold-out chosen and LOCKED: rgt % {rule['mod']} == {rule['off']} "
                  f"({rule['share']:.0%} of photons, depth KS {rule['ks']:.2f}) -> {HOLDOUT_LOCK}")
    atl24['set'] = 'train'
    if LOCK:
        atl24.loc[atl24['rgt'].astype(int).isin(LOCK['valid_rgts']), 'set'] = 'valid'
    else:
        atl24['set'] = 'unsplit'
    IS2_OUT.update(split_status=SPLIT_STATUS, split=(f"rgt % {LOCK['mod']} == {LOCK['off']}" if LOCK else None),
                   lock_file=HOLDOUT_LOCK, valid_rgts=LOCK['valid_rgts'] if LOCK else [])

    def xtrack(df, c=None):
        c = IS2 if c is None else c
        d = df[df.qc_indep_ok].copy()
        d['bx'] = np.floor(d.geometry.x / c['XT_BIN']).astype(np.int64); d['by'] = np.floor(d.geometry.y / c['XT_BIN']).astype(np.int64)
        d['ex'], d['ey'] = d.geometry.x, d.geometry.y
        B = d.groupby(['track_id', 'bx', 'by']).agg(depth=('depth', 'median'), x=('ex', 'mean'), y=('ey', 'mean'),
                                                      pass_id=('pass_id', 'first'), set=('set', 'first')).reset_index()
        ref = B[B.set != 'valid'].reset_index(drop=True)          # training (or unsplit) passes only
        out = pd.DataFrame(index=B.index, columns=['xt_ref_depth', 'xt_n_passes', 'xt_ref_dist_m'], dtype=float)
        if len(ref):
            tree = cKDTree(ref[['x', 'y']].values)
            hits = tree.query_ball_point(B[['x', 'y']].values, r=c['XT_RADIUS'], workers=-1)
            rp, rd, rx, ry = ref.pass_id.values, ref.depth.values, ref.x.values, ref.y.values
            for i, (h, own, bx_, by_) in enumerate(zip(hits, B.pass_id.values, B.x.values, B.y.values)):
                if not h: continue
                h = np.asarray(h); h = h[rp[h] != own]
                if not len(h): continue
                s = pd.Series(rd[h]).groupby(rp[h]).median()
                if len(s) >= c['XT_MIN_PASSES']:
                    out.iloc[i] = [float(s.median()), len(s), float(np.hypot(rx[h] - bx_, ry[h] - by_).mean())]
        B = B.join(out)
        d = d.merge(B[['track_id', 'bx', 'by', 'xt_ref_depth', 'xt_n_passes', 'xt_ref_dist_m']], on=['track_id', 'bx', 'by'], how='left')
        r_ = d['xt_ref_depth'].values.astype(float)
        bad = np.isfinite(r_) & (np.abs(d['depth'].values - r_) > np.maximum(c['XT_MIN'], c['XT_REL'] * r_))
        d['f_xtrack'] = bad
        return d.set_index(d.index)[['xt_ref_depth', 'xt_n_passes', 'xt_ref_dist_m', 'f_xtrack']], int(np.isfinite(r_).sum())

    print('5d. Cross-track consistency (training passes as reference) ...')
    idx_ok = atl24.index[atl24.qc_indep_ok]
    xt, n_eval = xtrack(atl24)
    xt.index = idx_ok
    for k in xt.columns: atl24[k] = np.nan if k != 'f_xtrack' else False
    atl24.loc[idx_ok, xt.columns] = xt.values
    atl24['f_xtrack'] = atl24['f_xtrack'].astype(bool)
    EVAL['f_xtrack'] = n_eval
    apply_xt = atl24['f_xtrack'] & ((atl24['set'] != 'valid') | IS2['XT_APPLY_TO_VALID'])
    atl24['qc_ok'] = atl24['qc_indep_ok'] & ~apply_xt
    print(f"  evaluated {n_eval:,} photons (with enough reference passes); flagged {int(atl24.f_xtrack.sum()):,} "
          f"(train {int((atl24.f_xtrack & (atl24.set != 'valid')).sum()):,}, valid {int((atl24.f_xtrack & (atl24.set == 'valid')).sum()):,}"
          f"{' - informational only for validation' if not IS2['XT_APPLY_TO_VALID'] else ''})")
    FLAGS = INDEP + ['f_xtrack']
    summary = {k: dict(evaluated=EVAL.get(k), flagged=int(atl24[k].sum())) for k in FLAGS}
    summary['kept'] = int(atl24.qc_ok.sum()); summary['total'] = len(atl24)
    IS2_OUT['qc_summary'] = summary

    def optical_class_map(f, r_lo, r_hi, sign, out_path, b2i=2, b3i=3):
        """0 optically shallow · 1 optically deep · 2 unknown · 255 not assessed (land, outside AOI, no coverage).
        r_lo = ratio at the shallow end of the z_sat interval, r_hi = at the deep end; sign = +1 if the ratio grows with depth."""
        with rasterio.open(f) as src:
            b2_, b3_ = src.read(b2i).astype(np.float32), src.read(b3i).astype(np.float32)
            prof_, tr_ = src.profile, src.transform
            nd = src.nodata if src.nodata is not None else -9999
            crs_ = src.crs
        covered = (b2_ != nd) & (b3_ != nd) & np.isfinite(b2_) & np.isfinite(b3_)
        r = stumpf_ratio(b2_, b3_)
        s = abs(tr_.a)
        wtr = ee_pixels(water.unmask(1).rename('w'), tr_.c, tr_.f, s, b2_.shape[1], b2_.shape[0], crs=str(crs_))
        aoi_geom = gpd.GeoSeries([aoi_shapely()], crs='EPSG:4326').to_crs(crs_).iloc[0]
        in_aoi = rfeatures.geometry_mask([aoi_geom], out_shape=b2_.shape, transform=tr_, invert=True)
        elig = covered & (wtr == 1) & in_aoi
        assessed = elig & np.isfinite(r)
        deep = assessed & (sign * (r - r_hi) >= 0)
        shallow = assessed & (sign * (r - r_lo) < 0)
        unknown = (elig & ~np.isfinite(r)) | (assessed & ~deep & ~shallow)
        # cleaning: removed pixels become UNKNOWN, never the other class
        for cls_mask in ('deep', 'shallow'):
            m = deep if cls_mask == 'deep' else shallow
            mo = ndimage.binary_opening(m, iterations=1)
            lab_, nlab = ndimage.label(mo)
            keep = np.isin(lab_, np.where(ndimage.sum(mo, lab_, range(1, nlab + 1)) >= IS2['MASK_MIN_AREA_PX'])[0] + 1) if nlab else mo
            unknown |= m & ~keep
            if cls_mask == 'deep': deep = keep
            else: shallow = keep
        out = np.full(b2_.shape, 255, np.uint8)
        out[elig] = 2; out[shallow] = 0; out[deep] = 1; out[unknown & elig] = 2
        prof_.update(count=1, dtype='uint8', nodata=255, compress='deflate')
        with rasterio.open(out_path, 'w', **prof_) as dst:
            dst.write(out, 1)
            dst.update_tags(1, classes='0 optically shallow; 1 optically deep; 2 unknown; 255 not assessed',
                            status='EXPLORATORY - not validated for production masking', run_id=RUN_ID)
        record_file(out_path)
        counts = {k: int((out == v).sum()) for k, v in (('shallow', 0), ('deep', 1), ('unknown', 2), ('not_assessed', 255))}
        shp = [shape(gm) for gm, v in rfeatures.shapes(out, mask=out == 0, transform=tr_) if v == 0]
        gp = None
        if shp:
            gp = out_path.replace('_optical_depth_class', '_optically_shallow').replace('.tif', '.gpkg')
            gpd.GeoDataFrame({'class': ['optically_shallow_EXPLORATORY'] * len(shp)}, geometry=shp, crs=crs_) \
               .dissolve('class').to_file(gp, driver='GPKG')
            record_file(gp)
        return counts, gp

    files = composite_files('p30')
    Z = dict(status='no_composite', z_sat=None, r_sat=None)
    atl24['sdb_domain'] = 'unknown'; atl24['near_limit'] = False
    PROF, SENS = pd.DataFrame(columns=PROFILE_COLS), pd.DataFrame()
    if not files:
        print('5e. No composite of this run in the manifest: run Module 1 with WAIT_FOR_EXPORTS, or set IS2["COMPOSITE_TIF"]. '
              'Depth limit not assessed (sdb_domain = unknown).')
    else:
        comp_rep = validate_composite(files); IS2_OUT['composite_check'] = comp_rep
        b2i, b3i = comp_rep[0]['b2_index'], comp_rep[0]['b3_index']
        print('5e. Sampling the composite at clean photons:', [os.path.basename(f) for f in files])
        good = atl24[atl24.qc_ok]
        b2, b3 = sample_composite(files, good.geometry.x.values, good.geometry.y.values, b2i, b3i)
        atl24.loc[good.index, 'S2_B2'], atl24.loc[good.index, 'S2_B3'] = b2, b3
        atl24['stumpf_ratio'] = stumpf_ratio(atl24.get('S2_B2', np.nan), atl24.get('S2_B3', np.nan))
        fit = atl24[atl24.qc_ok & (atl24.set != 'valid')]                       # training (or unsplit) only
        D, R, G = fit.depth.values.astype(float), fit.stumpf_ratio.values.astype(float), fit.rgt.astype(int).values
        Z, PROF = saturation_depth(D, R, G)
        print(f"  z_sat = {Z['z_sat']} m ({Z['status']}; {Z['n']:,} training photons, {Z['n_rgt']} RGTs)")
        if Z['status'] == 'resolved':
            BOOT = bootstrap_zsat(D, R, G, IS2['SDB_BOOT'])
            Z.update(BOOT)
            print(f"  bootstrap by RGT: 5-95 % z_sat {BOOT['z_p05']} – {BOOT['z_p95']} m, resolved in {BOOT['resolved_frac']:.0%}")
            if BOOT['resolved_frac'] < 0.5:
                Z['status'] = 'unstable'; print('  -> unstable (< 50 % of bootstrap samples resolve): treated as unresolved')
        # sensitivity: one parameter at a time, and the median composite
        rows = []
        for k, vals in IS2['SDB_SENS'].items():
            for v in vals:
                r_, _ = saturation_depth(D, R, G, {k: v}); rows.append(dict(composite='P30', param=k, value=v, z_sat=r_['z_sat'], status=r_['status']))
        mfiles = composite_files('median') if S2.get('SENSITIVITY_MEDIAN') else []
        if mfiles:
            mb2, mb3 = sample_composite(mfiles, fit.geometry.x.values, fit.geometry.y.values, 2, 3)
            r_, _ = saturation_depth(D, stumpf_ratio(mb2, mb3), G)
            rows.append(dict(composite='median', param='default', value=None, z_sat=r_['z_sat'], status=r_['status']))
        SENS = pd.DataFrame(rows)
        SENS.to_csv(drive_path('icesat2', f'{PREFIX}_SDB_depth_limit_sensitivity.csv'), index=False)
        PROF.to_csv(drive_path('icesat2', f'{PREFIX}_SDB_ratio_depth_profile_training.csv'), index=False)
        zs = pd.to_numeric(SENS.z_sat, errors='coerce')
        if len(zs.dropna()): print(f'  sensitivity: z_sat range {zs.min():.1f} – {zs.max():.1f} m over {len(SENS)} variants')

        if Z['status'] == 'resolved':
            atl24['sdb_domain'] = np.where(atl24.depth > Z['z_sat'], 'beyond', 'within')
            lo, hi = Z.get('z_p05') or Z['z_sat'], Z.get('z_p95') or Z['z_sat']
            atl24['near_limit'] = atl24.depth.between(lo, hi)
            # exploratory optical map, threshold band = ratios at the bootstrap interval ends
            sm = PROF.dropna(subset=['median_smooth'])
            r_lo, r_hi = (float(np.interp(z, sm.depth, sm.median_smooth)) for z in (lo, hi))
            sign = float(np.sign(sm.median_smooth.iloc[-1] - sm.median_smooth.iloc[0]) or 1.0)   # ratio change with depth
            Z['r_at_z_p05'], Z['r_at_z_p95'] = r_lo, r_hi
            MASK_COUNTS = {}
            for i, f in enumerate(files):
                sfx = '' if len(files) == 1 else f'_{i}'
                cnt, gp = optical_class_map(f, r_lo, r_hi, sign,
                                            drive_path('icesat2', f'{PREFIX}_EXPLORATORY_optical_depth_class{sfx}.tif'), b2i, b3i)
                MASK_COUNTS[os.path.basename(f)] = cnt
            IS2_OUT['mask_counts'] = MASK_COUNTS
            print('  EXPLORATORY optical class map written (pixels):', MASK_COUNTS)
        else:
            print('  depth limit NOT established -> sdb_domain = unknown for all photons; no optical mask written')
    IS2_OUT['zsat'] = Z
    set_status('icesat2_depth_limit', Z['status'], **{k: v for k, v in Z.items() if k != 'status'})

    # figure: ratio vs depth (training), bootstrap interval, sensitivity
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(7.2, 3.2), constrained_layout=True, gridspec_kw=dict(width_ratios=[1.6, 1]))
    g = atl24[atl24.qc_ok & (atl24.set != 'valid')]
    g = g[np.isfinite(g.get('stumpf_ratio', pd.Series(np.nan, index=g.index)).astype(float))] if 'stumpf_ratio' in g else g.iloc[0:0]
    if len(g) and len(PROF):
        hb = ax1.hexbin(g.depth, g.stumpf_ratio, gridsize=60, bins='log', mincnt=1, cmap='Greys', linewidths=0)
        sp = PROF[PROF.supported.astype(bool)]
        ax1.fill_between(PROF.depth, PROF.q1.where(PROF.supported.astype(bool)), PROF.q3.where(PROF.supported.astype(bool)),
                         color=OKABE_ITO[0], alpha=0.25, lw=0, label='IQR (supported bins)')
        ax1.plot(PROF.depth, PROF.median_smooth, color=OKABE_ITO[0], lw=1.5, label='binned median')
        if Z.get('z_sat'):
            if Z.get('z_p05') is not None:
                ax1.axvspan(Z['z_p05'], Z['z_p95'], color=OKABE_ITO[3], alpha=0.15, lw=0, label='bootstrap 5–95 %')
            ax1.axvline(Z['z_sat'], color=OKABE_ITO[3], ls='--', lw=1, label=f"$z_{{sat}}$ = {Z['z_sat']:.1f} m")
        ax1.set_xlabel('ICESat-2 ATL24 depth, training tracks (m)'); ax1.set_ylabel('ln(1000·B2) / ln(1000·B3)')
        ax1.legend(loc='lower right'); fig.colorbar(hb, ax=ax1, label='photons (log)')
        ax1.set_title(f"Depth limit: {Z['status']}", loc='left')
    else:
        empty_panel(ax1, f"depth limit: {Z['status']}")
    if len(SENS) and pd.to_numeric(SENS.z_sat, errors='coerce').notna().any():
        lab = SENS.apply(lambda r: f"{r.composite} {r.param}={r.value:g}" if isinstance(r.value, (int, float)) and pd.notna(r.value) else f'{r.composite}', axis=1)
        zz = pd.to_numeric(SENS.z_sat, errors='coerce')
        ax2.barh(range(len(SENS)), zz.fillna(0), color=[OKABE_ITO[0] if s == 'resolved' else '0.8' for s in SENS.status])
        ax2.set_yticks(range(len(SENS))); ax2.set_yticklabels(lab, fontsize=6.5); ax2.invert_yaxis()
        if Z.get('z_sat'): ax2.axvline(Z['z_sat'], color=OKABE_ITO[3], ls='--', lw=1)
        ax2.set_xlabel('$z_{sat}$ (m); grey = unresolved'); ax2.set_title('Sensitivity', loc='left')
    else:
        empty_panel(ax2, 'no sensitivity results')
    panel_labels([ax1, ax2], x=-0.15)
    save_fig(fig, 'icesat2', f'{PREFIX}_Fig_ICESat2_SDB_depth_limit'); plt.show()

    KEEP = [k for k in ['time', 'rgt', 'cycle', 'spot', 'gt', 'pass_id', 'track_id', 'set', 'ortho_h', 'surface_h', 'depth',
                        'confidence', 'sigma_tvu', 'sigma_thu', 'class_ph', 'low_confidence_flag', 'invalid_kd',
                        'sensor_depth_exceeded', 'dist_coast_m', 'qc_indep_ok', 'qc_ok', *FLAGS, 'xt_ref_depth',
                        'xt_n_passes', 'xt_ref_dist_m', 'sdb_domain', 'near_limit', 'S2_B2', 'S2_B3', 'stumpf_ratio', 'geometry']
            if k in atl24]
    def write_gpkg(df, name):
        o = df[KEEP].copy(); o['time'] = o['time'].astype(str)
        for k in ('rgt', 'cycle'):
            if k in o: o[k] = o[k].astype('float').astype('Int64')
        p = drive_path('icesat2', name); o.to_file(p, driver='GPKG'); record_file(p); return p
    write_gpkg(atl24, f'{PREFIX}_ATL24_all_with_QC_flags.gpkg')
    use = atl24[atl24.qc_ok & (atl24.sdb_domain != 'beyond')]
    VAL_REPORT = []
    if LOCK:
        for s in ('train', 'valid'):
            sub = use[use.set == s]
            write_gpkg(sub, f'{PREFIX}_ATL24_{s}.gpkg')
            allset = atl24[atl24.set == s]
            VAL_REPORT.append(dict(set=s, photons=len(sub), rgts=int(sub.rgt.nunique()), passes=int(sub.pass_id.nunique()),
                                   depth_min=float(sub.depth.min()) if len(sub) else None, depth_max=float(sub.depth.max()) if len(sub) else None,
                                   domain_unknown=int((sub.sdb_domain == 'unknown').sum()), near_limit=int(sub.near_limit.sum()),
                                   **{f'excluded_{k}': int(allset[k].sum()) for k in FLAGS},
                                   excluded_beyond=int((allset.qc_ok & (allset.sdb_domain == 'beyond')).sum())))
        VAL_REPORT = pd.DataFrame(VAL_REPORT)
        VAL_REPORT.to_csv(drive_path('icesat2', f'{PREFIX}_ATL24_train_valid_coverage.csv'), index=False)
        assert not set(use[use.set == 'train'].rgt.astype(int)) & set(use[use.set == 'valid'].rgt.astype(int)), 'RGT in both sets'
        print(VAL_REPORT[['set', 'photons', 'rgts', 'passes', 'depth_min', 'depth_max', 'domain_unknown']].to_string(index=False))
        print('  written: ATL24_all_with_QC_flags.gpkg, ATL24_train.gpkg, ATL24_valid.gpkg (+ coverage CSV)')
    else:
        print('  written: ATL24_all_with_QC_flags.gpkg only (no feasible track split)')
    set_status('icesat2_atl24', 'partial' if failed_years else 'complete', split=SPLIT_STATUS, failed_years=failed_years)

    # figure: map of photons and QC, flag counts, depth distributions
    aoi_utm = gpd.GeoSeries([aoi_shapely()], crs='EPSG:4326').to_crs(CRS)
    fig = plt.figure(figsize=(7.2, 5.6), constrained_layout=True)
    gs = fig.add_gridspec(2, 2, width_ratios=[1.4, 1])
    ax = fig.add_subplot(gs[:, 0])
    aoi_utm.boundary.plot(ax=ax, color='k', lw=0.6)
    bad = atl24[~atl24.qc_ok]
    ax.scatter(bad.geometry.x, bad.geometry.y, s=0.3, color='0.75', label='rejected (QC)', rasterized=True)
    bey = atl24[atl24.qc_ok & (atl24.sdb_domain == 'beyond')]
    ax.scatter(bey.geometry.x, bey.geometry.y, s=0.3, color=OKABE_ITO[4], label='beyond SDB limit', rasterized=True)
    if len(use):
        sc = ax.scatter(use.geometry.x, use.geometry.y, c=use.depth, s=0.4, cmap='viridis_r', vmin=0,
                        vmax=np.nanpercentile(use.depth, 98), rasterized=True)
        fig.colorbar(sc, ax=ax, shrink=0.6, label='depth (m)')
        vv = use[use.set == 'valid']
        ax.scatter(vv.geometry.x, vv.geometry.y, s=0.2, facecolors='none', edgecolors=OKABE_ITO[1], lw=0.2,
                   label='validation tracks', rasterized=True)
    ax.set_aspect('equal'); ax.set_xlabel('Easting (m)'); ax.set_ylabel('Northing (m)')
    ax.ticklabel_format(style='plain'); ax.tick_params(axis='x', rotation=30)
    ax.legend(loc='upper center', bbox_to_anchor=(0.5, -0.2), ncol=3, markerscale=5); ax.set_title(f'ICESat-2 ATL24, {IS2["T0"][:4]}–{IS2_T1[:4]}', loc='left')
    axb = fig.add_subplot(gs[0, 1])
    cnt = [summary[f]['flagged'] for f in FLAGS]; ev_ = [summary[f]['evaluated'] or 0 for f in FLAGS]
    axb.barh(range(len(FLAGS)), cnt, color=OKABE_ITO[3], alpha=0.8); axb.set_yticks(range(len(FLAGS)))
    axb.set_yticklabels([f'{f[2:]} (of {e:,})' for f, e in zip(FLAGS, ev_)], fontsize=6.5); axb.invert_yaxis()
    axb.set_xlabel('photons flagged'); axb.set_title(f"kept {summary['kept']:,} of {summary['total']:,}", loc='left')
    axc = fig.add_subplot(gs[1, 1])
    if LOCK and len(use):
        bins = np.arange(0, use.depth.max() + 1, 1)
        for s, col_ in (('train', OKABE_ITO[0]), ('valid', OKABE_ITO[1])):
            axc.hist(use.depth[use.set == s], bins=bins, density=True, histtype='step', lw=1.2, color=col_,
                     label=f"{s} ({(use.set == s).sum():,}; {use[use.set == s].rgt.nunique()} RGTs)")
        axc.set_xlabel('depth (m)'); axc.set_ylabel('density'); axc.legend()
        axc.set_title(f"locked hold-out: {IS2_OUT['split']}", loc='left')
    else:
        empty_panel(axc, 'no feasible track split')
    panel_labels([ax, axb, axc], x=-0.1)
    save_fig(fig, 'icesat2', f'{PREFIX}_Fig_ICESat2_ATL24_QC_split'); plt.show()
    ATL08_ALIASES = {'n_ground_ph': ['gnd_count', 'ground_photon_count'], 'n_veg_ph': ['veg_count', 'vegetation_photon_count'],
                     'ground_h_ellipsoid': ['h_te_median', 'h_te_best_fit', 'h_te_mean']}

    def geoid_transformer(lon0, lat0):
        """Verified ellipsoid (EPSG:4979) -> EGM2008 (EPSG:4326+3855) transformer, or (None, report)."""
        from pyproj import network
        from pyproj.transformer import TransformerGroup
        network.set_network_enabled(True)
        rep = dict(status='failed')
        try:
            tg = TransformerGroup('EPSG:4979', 'EPSG:4326+3855', always_xy=True)
            if not tg.best_available:
                try:
                    tg.download_grids(verbose=False)
                    tg = TransformerGroup('EPSG:4979', 'EPSG:4326+3855', always_xy=True)
                except Exception as e:
                    rep['download_error'] = str(e)[:200]
            rep['unavailable'] = [str(u)[:120] for u in tg.unavailable_operations][:3]
            for t in tg.transformers:
                if 'ballpark' in t.description.lower(): continue
                _, _, h0 = t.transform(lon0, lat0, 0.0, errcheck=True)
                if np.isfinite(h0) and abs(h0) > 0.1:            # a real geoid model gives a non-zero undulation
                    rep.update(status='verified', description=t.description, undulation_at_aoi_m=float(-h0))
                    return t, rep
            rep['reason'] = 'only ballpark / zero-shift operations available'
        except Exception as e:
            rep['error'] = str(e)[:200]
        return None, rep

    def dem_values(task_name, xs, ys):
        """Sample a Module 2 DEM of THIS run (from the manifest) at projected points."""
        m_ = manifest('dem')
        if not task_name or task_name not in m_['tasks'] or m_['tasks'][task_name].get('state') != 'COMPLETED':
            return None
        vals = np.full(len(xs), np.nan)
        for f in task_files(task_name):
            with rasterio.open(f) as src:
                ins = (xs >= src.bounds.left) & (xs <= src.bounds.right) & (ys >= src.bounds.bottom) & (ys <= src.bounds.top)
                if ins.any():
                    vv = np.array([s[0] for s in src.sample(zip(xs[ins], ys[ins]))], float)
                    vv[(vv <= -9000) | (vv == (src.nodata if src.nodata is not None else -9999))] = np.nan
                    vals[ins] = vv
        return vals

    if IS2['RUN_ATL08']:
        from sliderule import icesat2
        c = IS2
        print('5g. Downloading ATL08 / PhoREAL vegetation (SlideRule) ...')
        parms08 = {'srt': icesat2.SRT_LAND, 'len': c['ATL08_LEN'], 'res': c['ATL08_LEN'], 'pass_invalid': False,
                   'atl08_class': ['atl08_ground', 'atl08_canopy', 'atl08_top_of_canopy'],
                   'phoreal': {'binsize': 1.0, 'geoloc': 'center', 'use_abs_h': False, 'send_waveform': False}}
        v08, cov08 = sliderule_years('atl08p', parms08, c['T0'], IS2_T1, fn=icesat2.atl08p)
        cov08.to_csv(drive_path('icesat2', f'{PREFIX}_ATL08_download_coverage.csv'), index=False)
        MANIFEST['coverage']['atl08'] = cov08.to_dict('records'); save_manifest()
        if v08 is None or v08.empty:
            print('  no ATL08 segments returned'); set_status('icesat2_atl08', 'empty')
        else:
            v08 = v08[v08.intersects(aoi_shapely())].copy().reset_index(drop=True)
            found = {}
            for canon, al in ATL08_ALIASES.items():
                hit = next((a for a in al if a in v08), None)
                found[canon] = hit
                v08[canon] = pd.to_numeric(v08[hit], errors='coerce') if hit else np.nan
            IS2_OUT['atl08_fields'] = found
            print('  field mapping:', found)
            # mangroves (GMW 2020), grid of the AOI + 1 km
            x0, y1, s, w, h = wide_grid(30, 1000)
            gmw_img = (ee.ImageCollection('projects/sat-io/open-datasets/GMW/annual-extent/GMW_MNG_2020')
                       .filterBounds(roi).mosaic().select(0).eq(1).unmask(0))
            mg = ee_pixels(gmw_img.rename('m'), x0, y1, s, w, h)
            mg = ndimage.binary_dilation(mg == 1, iterations=c['MANGROVE_BUFFER_PX']).astype(float)
            v08u = v08.to_crs(CRS)
            v08['in_mangrove'] = sample_grid(mg, (x0, y1, s), v08u.geometry.x.values, v08u.geometry.y.values) == 1
            v08 = v08[v08.in_mangrove].copy().reset_index(drop=True)
            print(f'  {len(v08):,} segments inside GMW 2020 mangroves (+{c["MANGROVE_BUFFER_PX"]} px)')

            lon0, lat0 = CTX.aoi_info['centre']
            T, GEO = geoid_transformer(lon0, lat0)
            IS2_OUT['geoid'] = GEO
            v08['ground_h_egm08'] = np.nan
            if T is not None:
                _, _, hh = T.transform(v08.geometry.x.values, v08.geometry.y.values, v08['ground_h_ellipsoid'].values)
                v08['ground_h_egm08'] = np.where(np.isfinite(hh) & (np.abs(hh) < 1e4), hh, np.nan)
                print(f"  geoid conversion verified: {GEO['description']} (N = {GEO['undulation_at_aoi_m']:+.2f} m at the AOI centre)")
            else:
                print('  WARNING: EGM2008 conversion NOT verified', GEO, '-> ground_h_egm08 empty, DEM comparison skipped')
            v08['geoid_status'] = GEO['status']
            v08['f_missing'] = ~np.isfinite(v08['n_ground_ph']) | ~np.isfinite(v08['ground_h_ellipsoid'])
            v08['f_few_ground'] = np.isfinite(v08['n_ground_ph']) & (v08['n_ground_ph'] < c['MIN_GROUND_PH'])
            hge = v08['ground_h_egm08'].values
            v08['f_ground_range'] = np.isfinite(hge) & ((hge < c['GROUND_RANGE'][0]) | (hge > c['GROUND_RANGE'][1]))
            v08['qc_ok'] = ~(v08.f_missing | v08.f_few_ground | v08.f_ground_range)
            if T is None:
                v08['qc_ok'] &= False          # range check impossible without the geoid: nothing certified
            v08['night'] = pd.to_numeric(v08.get('solar_elevation', pd.Series(np.nan, index=v08.index)), errors='coerce') < 0
            q08 = dict(total=len(v08), missing=int(v08.f_missing.sum()), few_ground=int(v08.f_few_ground.sum()),
                       out_of_range=int(v08.f_ground_range.sum()), kept=int(v08.qc_ok.sum()))
            print('  ATL08 QC:', q08); IS2_OUT['atl08_qc'] = q08

            v08u = v08.to_crs(CRS); xs, ys = v08u.geometry.x.values, v08u.geometry.y.values
            dm = manifest('dem').get('outputs') or {}
            for col_, key in [('fabdem_egm08', 'fabdem'), ('deltadtm_egm08', 'deltadtm'), ('copdem_dsm_egm08', 'copdem_dsm')]:
                vals = dem_values(dm.get(key), xs, ys)
                v08[col_] = vals if vals is not None else np.nan
            keep = [k for k in ['time', 'rgt', 'cycle', 'spot', 'ground_h_ellipsoid', 'ground_h_egm08', 'geoid_status',
                                'h_canopy', 'h_max_canopy', 'h_mean_canopy', 'canopy_openness', 'n_ground_ph', 'n_veg_ph',
                                'solar_elevation', 'night', 'f_missing', 'f_few_ground', 'f_ground_range', 'qc_ok',
                                'fabdem_egm08', 'deltadtm_egm08', 'copdem_dsm_egm08', 'geometry'] if k in v08]
            o = v08[keep].copy(); o['time'] = o['time'].astype(str)
            p = drive_path('icesat2', f'{PREFIX}_ATL08_mangroves.gpkg'); o.to_file(p, driver='GPKG'); record_file(p)
            set_status('icesat2_atl08', 'complete' if T is not None else 'partial', geoid=GEO['status'])

            # figure: ground elevation, canopy height, DEM comparison
            q = v08[v08.qc_ok] if T is not None else v08[~v08.f_missing & ~v08.f_few_ground]
            fig, axs = plt.subplots(1, 3, figsize=(7.2, 2.7), constrained_layout=True)
            hcol = 'ground_h_egm08' if T is not None else 'ground_h_ellipsoid'
            if q[hcol].notna().any():
                axs[0].hist(q[hcol].dropna(), bins=40, color=OKABE_ITO[2], alpha=0.85, edgecolor='white', lw=0.3)
            axs[0].axvline(0, color='k', lw=0.6)
            axs[0].set_xlabel('ground elevation (m, ' + ('EGM2008)' if T is not None else 'ELLIPSOID - geoid not verified)'))
            axs[0].set_ylabel('segments')
            hc = next((k for k in ['h_canopy', 'h_max_canopy'] if k in q), None)
            if hc and pd.to_numeric(q[hc], errors='coerce').notna().any():
                axs[1].hist(pd.to_numeric(q[hc], errors='coerce').dropna(), bins=40, color=OKABE_ITO[0], alpha=0.85, edgecolor='white', lw=0.3)
                axs[1].set_xlabel(f'canopy height above ground (m, {hc})')
            else:
                empty_panel(axs[1], 'no canopy field')
            diffs, labs = [], []
            if T is not None:
                for col_, lab in [('fabdem_egm08', 'FABDEM'), ('deltadtm_egm08', 'DeltaDTM'), ('copdem_dsm_egm08', 'CopDEM DSM')]:
                    if col_ in q and q[col_].notna().sum() > 10:
                        diffs.append((q[col_] - q.ground_h_egm08).dropna().values); labs.append(lab)
            if diffs:
                axs[2].boxplot(diffs, showfliers=False, patch_artist=True,
                               boxprops=dict(facecolor=OKABE_ITO[5], alpha=0.7, lw=0.5), medianprops=dict(color='k'))
                axs[2].set_xticks(range(1, len(labs) + 1)); axs[2].set_xticklabels(labs)
                axs[2].axhline(0, color='k', lw=0.6); axs[2].set_ylabel('DEM − ICESat-2 ground (m, EGM2008)')
                IS2_OUT['dem_vs_atl08'] = {l: dict(median=float(np.median(d)), n=len(d)) for l, d in zip(labs, diffs)}
            else:
                empty_panel(axs[2], 'geoid not verified' if T is None else 'run Module 2 (this run) first')
            panel_labels(axs, x=-0.2)
            fig.suptitle(f'ICESat-2 ATL08 (PhoREAL) over GMW 2020 mangroves, N = {len(q):,} segments', fontsize=10)
            save_fig(fig, 'icesat2', f'{PREFIX}_Fig_ICESat2_ATL08_mangroves'); plt.show()

    qs = IS2_OUT.get('qc_summary', {}); Z = IS2_OUT.get('zsat', {})
    vr = VAL_REPORT.to_markdown(index=False) if isinstance(VAL_REPORT, pd.DataFrame) and len(VAL_REPORT) else 'no split'
    write_readme('icesat2', 'README_05_ICESat2', f"""
    # ICESat-2 lidar: bathymetry (ATL24) and mangrove ground / canopy (ATL08)

    ## Files
    | File | Content |
    |---|---|
    | `{PREFIX}_ATL24_all_with_QC_flags.gpkg` | all ATL24 photons in the AOI: `set` (train / valid / unsplit), QC flags `f_*`, `qc_indep_ok`, `qc_ok`, cross-track reference (`xt_*`), `dist_coast_m`, `sdb_domain` (within / beyond / unknown), `near_limit`, sampled S2 B2/B3, Stumpf ratio |
    | `{PREFIX}_ATL24_train.gpkg`, `{PREFIX}_ATL24_valid.gpkg` | {'clean photons not beyond the SDB limit, split by locked RGTs' if LOCK else '**not written: no feasible track split**'} — **depth field for Bathymetrix-AI: `ortho_h`** (m, EGM2008, negative = below); `depth` = instantaneous water depth (positive) |
    | `{PREFIX}_ATL24_train_valid_coverage.csv` | per set: photons, RGTs, passes, depth range, exclusions per rule |
    | `{PREFIX}_ATL24_download_coverage.csv`, `{PREFIX}_ATL08_download_coverage.csv` | requested vs returned per year (status ok / empty / failed, attempts, first/last time) |
    | `{PREFIX}_SDB_ratio_depth_profile_training.csv`, `{PREFIX}_SDB_depth_limit_sensitivity.csv` | binned ratio profile (training) and z_sat under alternative settings / composite |
    | `{PREFIX}_EXPLORATORY_optical_depth_class*.tif` | **exploratory**: 0 optically shallow · 1 optically deep · 2 unknown · 255 not assessed (land, outside AOI, no coverage) |
    | `{PREFIX}_EXPLORATORY_optically_shallow*.gpkg` | the shallow class as polygons — **not validated for production masking** |
    | `{PREFIX}_ATL08_mangroves.gpkg` | ATL08/PhoREAL segments inside GMW 2020 mangroves: `ground_h_ellipsoid`, `ground_h_egm08` (empty if the geoid conversion was not verified), `geoid_status`, canopy heights, `n_ground_ph`, `n_veg_ph`, QC, DEMs of this run (EGM2008) |
    | `{PREFIX}_Fig_ICESat2_*.png/.pdf` | figures |

    ## Data and schema (period {IS2['T0']} – {IS2_T1})
    SlideRule {json.dumps(IS2_OUT.get('sliderule', {}))}; ATL24 via `atl24x` with `compact: False`. Missing QC fields: {IS2_OUT.get('schema', {}).get('missing_qc') or 'none'}; aliases used: {IS2_OUT.get('schema', {}).get('aliases_used') or 'none'}.
    Years that failed after {IS2['SR_RETRIES']} attempts: {failed_years or 'none'} (module status {'partial' if failed_years else 'complete'}).

    ## ATL24 quality control
    Independent rules: f_missing (non-finite required values), f_class (class_ph ≠ 40 or confidence < {IS2['MIN_CONFIDENCE']}), f_atl24 (low_confidence_flag / invalid_kd /
    sensor_depth_exceeded or sigma_tvu > {IS2['MAX_SIGMA_TVU']} m), f_depth (< {IS2['DEPTH_MIN']} or > {IS2['DEPTH_MAX']} m), f_land / f_shore (< {IS2['SHORE_BUFFER']} m from land;
    {IS2_OUT.get('coast_source')}), f_spike (> max({IS2['SPIKE_MIN']} m, 3·MAD) from a {IS2['SPIKE_WINDOW']}-point running median).
    Cross-track f_xtrack: > max({IS2['XT_MIN']} m, {IS2['XT_REL']:.0%}) from the median of ≥ {IS2['XT_MIN_PASSES']} other **training passes** within {IS2['XT_RADIUS']} m (radius search,
    {IS2['XT_BIN']} m along-track bins, flagged references excluded); {'applied to validation too' if IS2['XT_APPLY_TO_VALID'] else 'informational only for validation photons'}.
    Evaluated / flagged per rule: `{json.dumps(qs)}`

    ## Hold-out (validation tracks)
    Status **{IS2_OUT.get('split_status')}**; rule `{IS2_OUT.get('split')}`; lock file `{IS2_OUT.get('lock_file')}` (chosen once before cross-track QC and depth-limit fitting; reused by later runs).
    {vr}
    Keep datum-aligned echosounder data as the final external check; never use validation tracks for Phase 4 residual correction.

    ## SDB depth limit (training tracks only)
    Stumpf ratio ln(1000·B2)/ln(1000·B3) of the Module 1 composite vs ATL24 depth on a uniform {IS2['SDB_BIN']} m grid (bins need ≥ {IS2['SDB_MIN_PER_BIN']} photons from ≥ {IS2['SDB_MIN_RGT_PER_BIN']} RGTs);
    z_sat = first depth beyond the steepest change where the smoothed median changes < {IS2['SDB_FLAT_TOL']:.0%} of its range over exactly {IS2['SDB_FLAT_SPAN']} m.
    **Status {Z.get('status')}; z_sat = {Z.get('z_sat')} m; RGT bootstrap 5–95 %: {Z.get('z_p05')} – {Z.get('z_p95')} m (resolved in {Z.get('resolved_frac')}).**
    If unresolved, no photon is certified as within the limit (`sdb_domain = unknown`) and no optical map is produced.
    Optical map pixels: `{json.dumps(IS2_OUT.get('mask_counts', {}))}` — exploratory; unknown = inside the bootstrap ratio interval or removed by cleaning.

    ## ATL08 over mangroves
    {IS2['ATL08_LEN']} m segments, `pass_invalid: False`, inside GMW 2020 mangroves (+{IS2['MANGROVE_BUFFER_PX']} px). Fields: `{json.dumps(IS2_OUT.get('atl08_fields', {}))}`.
    Geoid: `{json.dumps(IS2_OUT.get('geoid', {}))}`. QC (≥ {IS2['MIN_GROUND_PH']} ground photons, ground within {IS2['GROUND_RANGE']} m EGM2008): `{json.dumps(IS2_OUT.get('atl08_qc', {}))}`.
    DEM − ICESat-2 ground (EGM2008): `{json.dumps(IS2_OUT.get('dem_vs_atl08', {}))}`

    ## Assumptions / limitations
    - `ortho_h` and the DEMs refer to EGM2008, which is not local MSL or chart datum; tides at each pass are not corrected (microtidal, decimetres).
    - Thresholds are site-tuned starting values: inspect the `f_*` columns in QGIS. Agreement-based cleaning can remove real relief or seabed change.
    - z_sat depends on clarity and bottom type; one value for the AOI is a simplification. Evaluate errors per depth band and habitat.
    - Under dense mangrove canopy few ground photons reach the ground; ATL08 ground is uncertain there.

    ## Sources
    ICESat-2 ATL24 (NSIDC, doi:10.5067/ATLAS/ATL24.001), ATL03/ATL08 (NSIDC), processed with SlideRule (Shean et al. 2023, JOSS 8(81):4982);
    PhoREAL (Neuenschwander et al.); Global Mangrove Watch v4 (Bunting et al. 2022); PROJ / EGM2008 (NGA).
    """)

    MANIFEST['outputs'] = _jsonable(IS2_OUT); save_manifest()
    return ctx
