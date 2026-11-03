"""Step 1 — Sentinel-2 composite for satellite-derived bathymetry (Bathymetrix-AI input).

## Module 1 — Sentinel-2 composite for satellite-derived bathymetry

Output: one **12-band Float32** GeoTIFF (reflectance, NoData −9999, 10 m, aligned grid) in the
Bathymetrix-AI default band order (Coastal 1, Blue 2, Green 3, Red 4, NIR 8, SWIR 11), plus a QA raster
(clear observations, source tile, invalid-reflectance flag) and the blue-band temporal standard deviation
of the tile actually used at each pixel.

### What this module does, step by step

1. **Collect** all Sentinel-2 L2A images over the AOI in the composite months of each year, optionally
   from one relative orbit only (avoids seams from different viewing / sun-glint geometry).
2. **Mask** clouds pixel by pixel (Cloud Score+) and sun glint / whitecaps over water (SWIR > threshold).
   An observation is used only where **all 12 bands** are valid (one common mask), so every band of the
   composite comes from the same set of observations.
3. **Screen whole dates**, cheapest first (`SCREENING = 'metadata+aoi'`):
   (i) **tile metadata** (seconds, no pixels): cloud, shadow and thin-cirrus percentages and the sun-glint angle that
   ESA stores with every 110 km tile; (ii) **weather** from the waves step (no Earth Engine): rain, wind and rough seas
   in a window **ending at the image's acquisition time**; (iii) **image check** in Earth Engine, only for the dates
   that passed (i) and (ii): glint or haze (high NIR over AOI water) and river plumes (high red-edge B5). Image
   statistics are cached date by date, so a date is never sent to Earth Engine twice with the same options.
   Each check records whether it could be evaluated; a check without data is never counted as a pass —
   `MISSING_POLICY` decides whether such a date is dropped or kept as *unchecked*.
4. **Composite** per MGRS tile with a low percentile (residual haze and glint are brighter, so P30
   suppresses them better than the median). **`MIN_VALID` is applied to each tile before the tiles are
   mosaicked**, so where the first tile has too few clear observations the next tile fills in.
5. **Match tiles**: ESA corrects each 110 km tile separately; over dark water neighbouring tiles differ by a
   small constant. Each tile is shifted to the tiles before it with the median difference over overlap water.
   Offsets with too little support or larger than `OFFSET_MAX` are flagged in a diagnostics table.
6. **Export** on the aligned grid.

**Reading the outputs.** In QGIS show bands 4-3-2 stretched 0–0.15. `QA` band 1 = clear observations
(NoData where < `MIN_VALID`), band 2 = source tile (1 = first in `GROUPS`), band 3 = 1 where any band left
0–1 after tile matching. Where `B2_TemporalStd` is high (> ~0.01) the water changed a lot between dates.

**Sensitivity.** A bandwise percentile can build a spectrum that never occurred on one date, and additive
offsets change band ratios slightly. With `SENSITIVITY_MEDIAN = True` a median B1–B4 composite (same
dates, same offsets) is exported too; Module 5 recomputes the depth limit with it.
"""
import os, re, io, json, time, hashlib, calendar, datetime as dt
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from .core import (bind, manifest, save_manifest, stage_done, stage_get, set_status, require, drive_path,
                   export_image, export_table, wait, task_files, task_status, read_task_csv, record_file,
                   write_readme, find_task, TERMINAL_BAD, OKABE_ITO, panel_labels, save_fig, empty_panel,
                   figure_style, dir_to, in_months, years_filter, aoi_shapely, aoi_bbox_wgs84, _jsonable,
                   secret, CMEMS_REGIONS, decisions_path, load_decisions, applicable_decisions,
                   s2_tile_metadata, metadata_by_date)
try:
    import ee
except ImportError:  # documentation builds
    ee = None
from .waves import window_stats, load_series

# Settings and shared objects, set by bind() when run() is called (see core.bind)
AOI_LABEL = CFG = COPDEM_COLLECTION = CRS = CTX = DEM = DRIVE_ROOT = FOLDER_ROOT = GRID_X0 = GRID_X1 = GRID_Y0 \
    = GRID_Y1 = HAB = IS2 = MANIFEST = P = PREFIX = RUN_ID = S2 = TODAY = TR = W = WAIT_FOR_EXPORTS = aoi_fc = \
    centre = chirps = era5_gee = roi = water = None

BANDS = ['B1', 'B2', 'B3', 'B4', 'B5', 'B6', 'B7', 'B8', 'B8A', 'B9', 'B11', 'B12']
def s2_tag(c):
    mn = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
    return (f"{c['YEARS'][0]}_{mn[c['MONTHS'][0]-1]}_{c['YEARS'][1]}_{mn[c['MONTHS'][1]-1]}"
            + ('_Median' if c['PERCENTILE'] == 50 else f"_P{c['PERCENTILE']}")
            + (f"_R{c['ORBIT']}" if c['ORBIT'] is not None else '')
            + ('_B1isB2' if c['B1_FROM_B2'] else '')
            + (('_TileMatched' if c['GROUP_BY'] == 'MGRS_TILE' else '_OrbitMatched') if len(c['GROUPS']) > 1 else '')
            + f'_h{S2_HASH}')
def s2_collection(c):
    s2 = (ee.ImageCollection('COPERNICUS/S2_SR_HARMONIZED').filterBounds(roi)
          .filterDate(f"{c['YEARS'][0]}-01-01", f"{c['YEARS'][1] + 1}-01-01")
          .filter(in_months(c['MONTHS']))
          .filter(ee.Filter.lt('CLOUDY_PIXEL_PERCENTAGE', c['MAX_TILE_CLOUD'])))
    if c['ORBIT'] is not None:
        s2 = s2.filter(ee.Filter.eq('SENSING_ORBIT_NUMBER', c['ORBIT']))
    cs = ee.ImageCollection('GOOGLE/CLOUD_SCORE_PLUS/V1/S2_HARMONIZED')

    def prep(img):
        out = (img.select(BANDS).updateMask(img.select('cs_cdf').gte(c['CS_THRESHOLD']))
               .divide(10000).toFloat())
        if c['GLINT_FILTER']:
            out = out.updateMask(water.And(out.select('B11').gt(c['PIXEL_MAX_SWIR'])).Not())
        out = out.updateMask(out.mask().reduce(ee.Reducer.min()))          # common mask: all bands valid
        return (out.copyProperties(img, ['system:time_start', 'MGRS_TILE', 'SENSING_ORBIT_NUMBER'])
                .set('date', ee.Date(img.get('system:time_start')).format('YYYY-MM-dd')))
    return s2, s2.linkCollection(cs, ['cs_cdf']).map(prep)

def make_composite(col, pct, bands=BANDS):
    comp = (col.select(bands).median() if pct == 50
            else col.select(bands).reduce(ee.Reducer.percentile([pct])).rename(bands))
    comp = comp.updateMask(comp.mask().reduce(ee.Reducer.min()))
    empty = ee.Image.constant([0] * len(bands)).rename(bands).updateMask(0).toFloat()
    return ee.Image(ee.Algorithms.If(col.size().gt(0), comp.toFloat(), empty))
def make_count(col):
    return ee.Image(ee.Algorithms.If(col.size().gt(0),
        col.select('B2').count().rename('valid_count').toInt16(),
        ee.Image.constant(0).rename('valid_count').toInt16().updateMask(0)))
def priority_mosaic(imgs):           # first element ends up on top
    return ee.ImageCollection(list(reversed(imgs))).mosaic()
def tile_parts(col, c, offsets, pct=None, bands=BANDS):
    """Per group: composite (+offset), count, source index, temporal std; all masked by the tile's own
    MIN_VALID eligibility BEFORE the priority mosaic."""
    pct = c['PERCENTILE'] if pct is None else pct
    groups = c['GROUPS'] if len(c['GROUPS']) > 1 else [None]
    parts = []
    for i, g in enumerate(groups):
        gc = col if g is None else col.filter(ee.Filter.eq(c['GROUP_BY'], g))
        cnt = make_count(gc)
        elig = cnt.gte(c['MIN_VALID']) if c['MIN_VALID'] > 0 else cnt.gt(0)
        o = offsets.get(str(g), {}) if g is not None else {}
        comp = make_composite(gc, pct, bands).add(ee.Image.constant([o.get(b, 0.0) for b in bands])).rename(bands).toFloat()
        parts.append(dict(comp=comp.updateMask(elig), count=cnt.updateMask(elig),
                          src=ee.Image.constant(i + 1).toInt16().rename('source_tile').updateMask(elig),
                          tstd=gc.select('B2').reduce(ee.Reducer.stdDev()).rename('B2_temporal_std').updateMask(elig)))
    return parts
def s2_measure_offsets(col, c):
    """Offsets per group to the groups before it, with support, spread and plausibility flags."""
    keys = [str(g) for g in c['GROUPS']]
    parts = tile_parts(col, c, {})
    area = roi.bounds().buffer(c['MATCH_BUFFER'])
    R = dict(geometry=area, scale=c['OFFSET_SCALE'], crs=CRS, maxPixels=1e9, bestEffort=True, tileScale=16)
    matched, offsets = [parts[0]['comp']], {keys[0]: {b: 0.0 for b in BANDS}}
    diag = [dict(group=keys[0], role='reference', n_water=None, flag='')]
    for i in range(1, len(parts)):
        comp, cur = parts[i]['comp'], priority_mosaic(matched)
        both = cur.select('B2').mask().And(comp.select('B2').mask())
        wat = cur.normalizedDifference(['B3', 'B8']).gt(c['WATER_NDWI']).And(cur.select('B8').lt(c['WATER_NIR']))
        diff = cur.subtract(comp)
        n = both.And(wat).selfMask().rename('n').reduceRegion(reducer=ee.Reducer.count(), **R).get('n').getInfo() or 0
        flag = ''
        if n >= c['MIN_MATCH_PIXELS']:
            msk = both.And(wat)
        elif c['NO_WATER_FALLBACK'] == 'all':
            msk, flag = both, 'no_water_all_overlap'
        elif c['NO_WATER_FALLBACK'] == 'error':
            raise RuntimeError(f'Tile {keys[i]}: only {n} overlap water pixels (< {c["MIN_MATCH_PIXELS"]})')
        else:
            msk, flag = None, 'unsupported_zero'
        if msk is not None:
            q = diff.updateMask(msk).reduceRegion(reducer=ee.Reducer.percentile([25, 50, 75]), **R).getInfo()
            lo = comp.updateMask(msk).reduceRegion(reducer=ee.Reducer.percentile([2]), **R).getInfo()
            off = {b: float(q.get(f'{b}_p50') or 0.0) for b in BANDS}
            iqr = {b: (q.get(f'{b}_p75') or 0) - (q.get(f'{b}_p25') or 0) for b in BANDS}
            neg = [b for b in BANDS if lo.get(b) is not None and lo[b] + off[b] < 0]
        else:
            off, iqr, neg = {b: 0.0 for b in BANDS}, {b: None for b in BANDS}, []
        big = [b for b in BANDS if abs(off[b]) > c['OFFSET_MAX']]
        flag = ','.join(x for x in [flag, ('large:' + '/'.join(big)) if big else '',
                                    ('below0:' + '/'.join(neg)) if neg else ''] if x)
        offsets[keys[i]] = off
        diag.append(dict(group=keys[i], role='matched', n_water=n, flag=flag,
                         **{f'off_{b}': off[b] for b in BANDS}, **{f'iqr_{b}': iqr[b] for b in BANDS}))
        print(f'  {keys[i]}: {n} overlap water pixels, B2 offset {off["B2"]:+.5f} (IQR {iqr["B2"]}) {flag}')
        matched.append(comp.add(ee.Image.constant([off[b] for b in BANDS])).rename(BANDS).toFloat())
    return offsets, pd.DataFrame(diag)


# ================================================================================ date screening
# 1. metadata (seconds, no pixels): one row per date from the image properties of every tile;
# 2. weather (no Earth Engine): rain, wind, waves from the waves step, in windows ending at the acquisition time;
# 3. image check (Earth Engine): glint and turbidity of the AOI water, only for the dates that passed 1 + 2.
AOI_COLS = ['date', 'water_nir', 'water_b5', 'n_water_px']

def metadata_table(c):
    """(tiles, dates): tile metadata of the collection used by the composite, and one row per date."""
    tiles = s2_tile_metadata(roi, c['YEARS'], c['MONTHS'], c['ORBIT'], c['MAX_TILE_CLOUD'])
    return tiles, metadata_by_date(tiles)

def add_weather(df, c):
    """Waves, wind (ERA5 point series) and rain (ERA5 point series) for each date, from the waves step."""
    df = df.copy()
    t1 = pd.to_datetime(df['t_last_ms'], unit='ms', utc=True)
    span_h = (df['t_last_ms'] - df['t_first_ms']).fillna(0) / 3.6e6
    # waves: per source, window (first acquisition - WAVE_WINDOW_H, last acquisition]
    srcs = {'cmems': ['cmems'], 'era5': ['era5'], 'max': ['era5', 'cmems']}[W['SCREEN_SOURCE']]
    if c['WAVE_FILTER']:
        for s in srcs:
            ser = WAVE_SERIES[s].set_index('time')['hs'] if s in WAVE_SERIES else pd.Series(dtype=float)
            res = [window_stats(ser, t, c['WAVE_WINDOW_H'] + h, 1 if s == 'era5' else W['CMEMS_STEP_H']) for t, h in zip(t1, span_h)]
            df[f'hs_{s}'], df[f'hs_{s}_n'], df[f'hs_{s}_maxgap_h'], df[f'hs_{s}_status'] = map(list, zip(*res)) if res else ([],) * 4
        st = df[[f'hs_{s}_status' for s in srcs]]
        df['hs_m'] = df[[f'hs_{s}' for s in srcs]].max(axis=1, skipna=True)
        df['hs_status'] = np.where((st == 'ok').all(axis=1), 'ok', np.where((st == 'missing').all(axis=1), 'missing', 'partial'))
    if c['WIND_FILTER'] and c['WIND_SOURCE'] == 'cds':
        ser = WAVE_SERIES['era5'].set_index('time')['wind_speed']
        res = [window_stats(ser, t, c['WIND_WINDOW_H'] + h, 1, how='mean') for t, h in zip(t1, span_h)]
        df['wind_ms'], df['wind_n'], df['wind_maxgap_h'], df['wind_status'] = map(list, zip(*res)) if res else ([],) * 4
    if c['RAIN_SOURCE'] == 'era5':
        n = c['RAIN_DAYS']; e = WAVE_SERIES.get('era5')
        if e is not None and 'rain_mm' in e:
            r = e.set_index('time')['rain_mm'].dropna().sort_index()
            day = r[~r.index.duplicated()].resample('1D').sum(min_count=20)          # NaN if < 20 hours of the day
            day.index = day.index.tz_localize(None)
            roll = day.rolling(n, min_periods=n).sum().shift(1)                       # whole days [d-N, d)
            df['rain_mm'] = roll.reindex(pd.to_datetime(df['date'])).values
        else:
            df['rain_mm'] = np.nan
        df['rain_days'] = np.where(pd.notna(df['rain_mm']), n, 0)
    return df

def check_list(c):
    """(name, missing-policy group, stage, on, column, threshold, fails when 'above' / 'below')."""
    rain_stage = 'meta' if c['RAIN_SOURCE'] == 'era5' else 'aoi'
    wind_stage = 'meta' if c['WIND_SOURCE'] == 'cds' else 'aoi'
    return [('cloud', 'meta', 'meta', c['META_MAX_CLOUD'] is not None, 'meta_cloud', c['META_MAX_CLOUD'], 'above'),
            ('shadow', 'meta', 'meta', c['META_MAX_SHADOW'] is not None, 'meta_shadow', c['META_MAX_SHADOW'], 'above'),
            ('cirrus', 'meta', 'meta', c['META_MAX_CIRRUS'] is not None, 'meta_cirrus', c['META_MAX_CIRRUS'], 'above'),
            ('glint_angle', 'meta', 'meta', c['META_MIN_GLINT_ANGLE'] is not None, 'glint_angle', c['META_MIN_GLINT_ANGLE'], 'below'),
            ('rain', 'rain', rain_stage, c['RAIN_FILTER'], 'rain_mm', c['RAIN_MAX_MM'], 'above'),
            ('wind', 'wind', wind_stage, c['WIND_FILTER'], 'wind_ms', c['WIND_MAX_MS'], 'above'),
            ('waves', 'waves', 'meta', c['WAVE_FILTER'], 'hs_m', c['WAVE_MAX_HS'], 'above'),
            ('glint', 'water', 'aoi', c['GLINT_FILTER'], 'water_nir', c['SCENE_MAX_NIR'], 'above'),
            ('turbid', 'water', 'aoi', c['TURBIDITY_FILTER'], 'water_b5', c['SCENE_MAX_B5'], 'above')]

def apply_checks(df, c, stage=None):
    """Each check is 'pass', 'fail', 'missing' (no data: MISSING_POLICY decides) or 'not evaluated' (image checks on
    dates that were not sent to Earth Engine). Your Accept / Reject decisions (column 'manual') override everything.
    stage='meta': only the metadata and weather checks (to choose the dates for the image check)."""
    df = df.copy()
    aoi_ok = df['aoi_evaluated'].astype(bool).values if 'aoi_evaluated' in df else np.ones(len(df), bool)
    reasons = [[] for _ in range(len(df))]; unchecked = [[] for _ in range(len(df))]
    rule_counts = {}
    for name, group, stg, on, colname, thr, side in check_list(c):
        if not on or (stage == 'meta' and stg != 'meta'): continue
        v = pd.to_numeric(df[colname], errors='coerce').values if colname in df else np.full(len(df), np.nan)
        ne = (~aoi_ok) if stg == 'aoi' else np.zeros(len(df), bool)
        miss = ~np.isfinite(v) & ~ne
        fail = np.isfinite(v) & ((v > thr) if side == 'above' else (v < thr)) & ~ne
        df[f'chk_{name}'] = np.where(ne, 'not evaluated', np.where(miss, 'missing', np.where(fail, 'fail', 'pass')))
        rule_counts[name] = dict(evaluated=int((~miss & ~ne).sum()), failed=int(fail.sum()), missing=int(miss.sum()),
                                 not_evaluated=int(ne.sum()))
        for i in np.where(fail)[0]: reasons[i].append(name)
        for i in np.where(miss)[0]:
            (reasons[i].append(f'no_{name}_data') if c['MISSING_POLICY'].get(group, 'drop') == 'drop' else unchecked[i].append(name))
    df['reason'] = [','.join(sorted(set(r))) for r in reasons]
    df['unchecked'] = [','.join(u) for u in unchecked]
    df['kept'] = df['reason'] == ''
    if 'manual' in df:
        man = df['manual'].fillna('').astype(str)
        df.loc[man == 'accept', 'kept'] = True
        rej = man == 'reject'
        df.loc[rej, 'kept'] = False
        df.loc[rej, 'reason'] = [','.join([x for x in r.split(',') if x] + ['manual_reject']) for r in df.loc[rej, 'reason']]
    partial = (df.get('hs_status', 'ok') == 'partial') | (df.get('wind_status', 'ok') == 'partial')
    df['screen_status'] = np.where(df['unchecked'] != '', 'unchecked',
                                   np.where(df['kept'] & ~aoi_ok, 'metadata only', np.where(partial, 'partial', 'complete')))
    return df, rule_counts

def set_manual(df, c):
    """Column 'manual': your Accept / Reject choices from the image checker (if MANUAL_DECISIONS)."""
    df = df.copy(); df['manual'] = ''
    if c.get('MANUAL_DECISIONS'):
        dec = dict((d, v) for d, v in applicable_decisions(CFG))
        df['manual'] = [dec.get(str(d), '') if dec.get(str(d)) in ('accept', 'reject') else '' for d in df['date']]
    return df

def aoi_keys(c):
    k = ['MAX_TILE_CLOUD', 'CS_THRESHOLD', 'ORBIT', 'GLINT_FILTER', 'PIXEL_MAX_SWIR', 'SCENE_STAT_SCALE', 'RAIN_SOURCE']
    if c['RAIN_SOURCE'] == 'chirps': k += ['RAIN_DAYS', 'RAIN_BUFFER']
    if c['WIND_FILTER'] and c['WIND_SOURCE'] == 'gee': k += ['WIND_SOURCE', 'WIND_WINDOW_H', 'WIND_BUFFER']
    return k

def screening_hash(c):
    """Hash of the options that change the Earth Engine image statistics of a date (not the thresholds)."""
    proj = {k: v for k, v in CFG['project'].items() if k not in ('DRIVE_ROOT', 'RUN_TAG')}
    return hashlib.sha256(json.dumps(_jsonable(dict(p=proj, s={k: c[k] for k in aoi_keys(c)})), sort_keys=True).encode()).hexdigest()[:10]

def aoi_columns(c):
    return AOI_COLS + (['rain_mm', 'rain_days'] if c['RAIN_SOURCE'] == 'chirps' else []) + \
           (['wind_ms_gee', 'wind_n_gee'] if c['WIND_FILTER'] and c['WIND_SOURCE'] == 'gee' else [])

def aoi_table(col, c, dates):
    """Earth Engine: median NIR / B5 of clear AOI water (+ CHIRPS rain, ERA5 area wind if chosen) for these dates."""
    rain_region = roi.bounds().buffer(c['RAIN_BUFFER'])
    wind_region = roi.bounds().buffer(c['WIND_BUFFER'])
    def row(d):
        day = ee.Date(d)
        imgs = col.filter(ee.Filter.eq('date', d))
        wat = imgs.mosaic().select(['B8', 'B5']).updateMask(water)
        st = wat.reduceRegion(reducer=ee.Reducer.median().combine(ee.Reducer.count(), None, True),
                              geometry=roi, scale=c['SCENE_STAT_SCALE'], maxPixels=1e9, bestEffort=True, tileScale=16)
        props = {'date': d, 'water_nir': st.get('B8_median'), 'water_b5': st.get('B5_median'), 'n_water_px': st.get('B8_count')}
        if c['RAIN_SOURCE'] == 'chirps':
            rcol = chirps.filterDate(day.advance(-c['RAIN_DAYS'], 'day'), day)       # whole days before the image
            props['rain_mm'] = ee.Algorithms.If(rcol.size().eq(c['RAIN_DAYS']),
                rcol.sum().reduceRegion(reducer=ee.Reducer.mean(), geometry=rain_region, scale=5566,
                                        maxPixels=1e9, bestEffort=True).get('precipitation'), None)
            props['rain_days'] = rcol.size()
        if c['WIND_FILTER'] and c['WIND_SOURCE'] == 'gee':
            t_last = ee.Date(imgs.aggregate_max('system:time_start'))
            w = era5_gee.filterDate(t_last.advance(-c['WIND_WINDOW_H'], 'hour'), t_last.advance(1, 'second'))
            spd = w.map(lambda i: i.expression('hypot(b("u"), b("v"))').rename('s'))
            props['wind_ms_gee'] = ee.Algorithms.If(w.size().gt(0), spd.mean().reduceRegion(
                reducer=ee.Reducer.mean(), geometry=wind_region, scale=27830, maxPixels=1e9, bestEffort=True).get('s'), None)
            props['wind_n_gee'] = w.size()
        return ee.Feature(None, props)
    return ee.FeatureCollection(ee.List(list(dates)).map(row))

def aoi_stats(col, c, dates):
    """Image statistics per date, kept in the cache folder date by date: only dates never evaluated with these
    options go to Earth Engine (changing months, thresholds or decisions re-uses the dates already done)."""
    h = screening_hash(c)
    cache = os.path.join(DRIVE_ROOT, CTX.folders['cache'], 's2_screening'); os.makedirs(cache, exist_ok=True)
    path = os.path.join(cache, f'aoi_{h}.csv')
    cols = aoi_columns(c)
    have = pd.read_csv(path, dtype={'date': str}) if os.path.exists(path) else pd.DataFrame(columns=cols)
    need = sorted(set(map(str, dates)) - set(have['date'].astype(str)))
    if not need:
        print(f'  image statistics of all {len(dates)} dates re-used from the cache ({os.path.basename(path)})')
    else:
        print(f'  Earth Engine: image statistics for {len(need)} dates ({len(set(dates)) - len(need)} already in the cache)')
        name = f"S2_AOI_stats_{h}_{hashlib.sha256(' '.join(need).encode()).hexdigest()[:6]}"
        export_table(aoi_table(col, c, need), 's2', name, selectors=cols)
        wait([name], every=20)
        new = read_task_csv(name); new['date'] = new['date'].astype(str)
        new = new[new['date'].isin(need)]
        lost = [d for d in need if d not in set(new['date'])]
        if lost: new = pd.concat([new, pd.DataFrame({'date': lost})], ignore_index=True)     # evaluated, no data
        have = pd.concat([have, new[[x for x in cols if x in new]]], ignore_index=True).drop_duplicates('date', keep='last')
        have.sort_values('date').to_csv(path + '.tmp', index=False); os.replace(path + '.tmp', path)
    have['date'] = have['date'].astype(str)
    return have[have['date'].isin(set(map(str, dates)))]

def screening(c, col):
    """All dates of the composite months with metadata, weather and (where evaluated) image statistics, checked.
    Returns (table, rule_counts, tiles)."""
    if c['SCREENING'] not in ('metadata+aoi', 'metadata', 'aoi'):
        raise ValueError("S2['SCREENING'] must be 'metadata+aoi', 'metadata' or 'aoi'")
    if c['SCREENING'] == 'metadata' and (c['RAIN_SOURCE'] == 'chirps' or (c['WIND_FILTER'] and c['WIND_SOURCE'] == 'gee')):
        raise ValueError("With SCREENING = 'metadata' nothing is computed in Earth Engine: use RAIN_SOURCE = 'era5' and WIND_SOURCE = 'cds'")
    tiles, df = metadata_table(c)
    if not len(df):
        raise RuntimeError('No Sentinel-2 image matches YEARS, MONTHS, ORBIT and MAX_TILE_CLOUD over the AOI')
    print(f"  metadata: {len(tiles)} tile images on {len(df)} dates (tiles: {tiles.MGRS_TILE.value_counts().to_dict()})")
    df = set_manual(add_weather(df, c), c)
    df['aoi_evaluated'] = False
    if c['SCREENING'] != 'metadata':
        if c['SCREENING'] == 'aoi':
            want = df['date'].tolist()
        else:
            pre, _ = apply_checks(df, c, stage='meta')
            want = pre.loc[pre['kept'], 'date'].tolist()
            print(f"  metadata + weather checks: {len(want)} of {len(df)} dates go on to the image check in Earth Engine")
        if want:
            df = df.merge(aoi_stats(col, c, want), on='date', how='left')
        df['aoi_evaluated'] = df['date'].isin(want)
        if c['WIND_FILTER'] and c['WIND_SOURCE'] == 'gee':
            df['wind_ms'], df['wind_n'] = df.get('wind_ms_gee'), df.get('wind_n_gee')
            df['wind_status'] = np.where(pd.notna(df['wind_ms']), 'ok', 'missing')
    for k in ('water_nir', 'water_b5', 'n_water_px'):
        if k not in df: df[k] = np.nan
    df, rule_counts = apply_checks(df, c)
    return add_quality(df), rule_counts, tiles

QUALITY_VARS = [('water_nir', 1), ('water_b5', 1), ('rain_mm', 1), ('wind_ms', 1), ('hs_m', 1), ('meta_cirrus', 1),
                ('glint_angle', -1)]

def add_quality(df):
    """clear_share: clear AOI water of the date relative to the clearest date (image check);
    clear_est: clear_share where evaluated, otherwise 1 - tile cloud / 100;
    quality_score 0 (best) .. 100 (worst): mean percentile rank of the available variables (glint / haze, turbidity,
    rain, wind, waves, cirrus, glint angle, cloudiness)."""
    df = df.copy()
    nw = pd.to_numeric(df.get('n_water_px'), errors='coerce') if 'n_water_px' in df else pd.Series(np.nan, index=df.index)
    df['clear_share'] = nw / nw.max() if nw.notna().any() and nw.max() > 0 else np.nan
    est = 1 - pd.to_numeric(df.get('meta_cloud'), errors='coerce') / 100 if 'meta_cloud' in df else pd.Series(np.nan, index=df.index)
    df['clear_est'] = pd.to_numeric(df['clear_share'], errors='coerce').fillna(est).clip(0, 1)
    ranks = []
    for v, sign in QUALITY_VARS + [('clear_est', -1)]:
        if v not in df: continue
        x = pd.to_numeric(df[v], errors='coerce')
        if x.notna().sum() < 2: continue
        r = x.rank(pct=True)
        ranks.append(r if sign > 0 else 1 - r + 1 / x.notna().sum())
    df['quality_score'] = (pd.concat(ranks, axis=1).mean(axis=1, skipna=True) * 100).round(1) if ranks else np.nan
    return df

# column, option, switch (None: on when the option is set), label, compared with, which side is 'bad'
PROXIES = [('rain_mm', 'RAIN_MAX_MM', 'RAIN_FILTER', 'rain', 'water_b5', 'above'),
           ('wind_ms', 'WIND_MAX_MS', 'WIND_FILTER', 'wind', 'water_b5', 'above'),
           ('hs_m', 'WAVE_MAX_HS', 'WAVE_FILTER', 'waves', 'water_b5', 'above'),
           ('meta_cloud', 'META_MAX_CLOUD', None, 'tile cloud', 'water_nir', 'above'),
           ('meta_cirrus', 'META_MAX_CIRRUS', None, 'cirrus', 'water_nir', 'above'),
           ('glint_angle', 'META_MIN_GLINT_ANGLE', None, 'glint angle', 'water_nir', 'below')]
TARGET_LAB = {'water_b5': 'B5', 'water_nir': 'NIR'}

def proxy_check(df, c):
    """Do the indirect checks (rain, wind, waves, tile metadata) predict turbid or glinty water on these dates?
    Compares the image value (B5 for turbidity, NIR for glint / haze) of clear water between dates on the 'bad'
    and the 'good' side of each threshold (or of the median when a metadata check is switched off)."""
    from scipy import stats
    rows = []
    direct_fail = ((pd.to_numeric(df['water_b5'], errors='coerce') > c['SCENE_MAX_B5']) |
                   (pd.to_numeric(df['water_nir'], errors='coerce') > c['SCENE_MAX_NIR']))
    for col_, opt, flag, lab, tgt, side in PROXIES:
        if col_ not in df or tgt not in df: continue
        x = pd.to_numeric(df[col_], errors='coerce'); y = pd.to_numeric(df[tgt], errors='coerce')
        ok = x.notna() & y.notna()
        if ok.sum() == 0 and x.notna().sum() == 0: continue
        thr = c[opt]; split = thr if thr is not None else (float(x[ok].median()) if ok.any() else np.nan)
        bad = ok & ((x > split) if side == 'above' else (x < split)); good = ok & ~bad
        r = dict(check=lab, option=opt, threshold=thr, split=split, split_at='threshold' if thr is not None else 'median',
                 enabled=bool(c[flag]) if flag else thr is not None, compared_with=TARGET_LAB[tgt], side=side,
                 n_bad=int(bad.sum()), n_good=int(good.sum()))
        r['spearman'] = float(stats.spearmanr(x[ok], y[ok]).correlation) if ok.sum() > 5 else np.nan
        if bad.sum() >= 3 and good.sum() >= 3:
            r['median_bad'], r['median_good'] = float(y[bad].median()), float(y[good].median())
            r['ratio'] = r['median_bad'] / r['median_good'] if r['median_good'] else np.nan
            r['p_value'] = float(stats.mannwhitneyu(y[bad], y[good], alternative='greater').pvalue)
            r['also_failed_direct'] = float(direct_fail[bad].mean())      # share the image checks catch anyway
            what = 'turbid' if tgt == 'water_b5' else 'glinty or hazy'
            if r['p_value'] < 0.05 and r['ratio'] > 1.1:
                r['verdict'] = f'useful: dates on the bad side have more {what} water'
                if r['also_failed_direct'] > 0.8:
                    r['verdict'] += ' (but the image checks already catch most of them)'
            else:
                r['verdict'] = f'no evidence: dates on the bad side are not more {what}'
        else:
            r['verdict'] = 'too few image-checked dates on one side to judge'
        rows.append(r)
    return pd.DataFrame(rows)

def proxy_figure(df, c, pc):
    labs = {'rain_mm': f"rain, {c['RAIN_DAYS']} days before (mm)", 'wind_ms': f"wind, {c['WIND_WINDOW_H']} h before (m s$^{{-1}}$)",
            'hs_m': f"offshore $H_s$, {c['WAVE_WINDOW_H']} h before (m)", 'meta_cloud': 'tile cloud (%)',
            'meta_cirrus': 'tile thin cirrus (%)', 'glint_angle': 'glint angle (°)'}
    items = [p for p in PROXIES if p[0] in df and len(pc) and (pc.check == p[3]).any()]
    if not items: return
    nc = 3; nr = int(np.ceil(len(items) / nc))
    fig, axs = plt.subplots(nr, nc, figsize=(7.2, 2.5 * nr), constrained_layout=True, squeeze=False)
    kept = df['kept'].astype(bool)
    for ax, (col_, opt, flag, lab, tgt, side) in zip(axs.ravel(), items):
        x = pd.to_numeric(df[col_], errors='coerce'); y = pd.to_numeric(df[tgt], errors='coerce')
        ax.scatter(x[kept], y[kept], s=9, color=OKABE_ITO[2], label='kept', alpha=0.8)
        ax.scatter(x[~kept], y[~kept], s=9, color=OKABE_ITO[3], label='dropped', alpha=0.8)
        ax.axhline(c['SCENE_MAX_B5' if tgt == 'water_b5' else 'SCENE_MAX_NIR'], color='0.3', ls=':', lw=0.9, label=f'{TARGET_LAB[tgt]} threshold')
        r = pc[pc.check == lab].iloc[0]
        if pd.notna(r.split):
            ax.axvline(r.split, color=OKABE_ITO[3], ls='--' if r.split_at == 'threshold' else ':', lw=0.9,
                       label=f'{lab} {r.split_at}')
        ax.set_xlabel(labs[col_]); ax.set_ylabel(f'median water {TARGET_LAB[tgt]}', fontsize=7)
        v = r.verdict.split(':')[0]
        ax.set_title(f"{lab}: {v}" + (f"\n×{r.ratio:.2f}, p={r.p_value:.2g}" if pd.notna(r.get('ratio', np.nan)) else ''),
                     loc='left', fontsize=8)
    for ax in axs.ravel()[len(items):]: ax.set_visible(False)
    axs.ravel()[0].legend(fontsize=6, loc='upper right')
    panel_labels(axs.ravel()[:len(items)], x=-0.15)
    save_fig(fig, 's2', f'{PREFIX}_Fig_S2_indirect_checks'); plt.show()

def strict_suggestion(df, c):
    """'Best images' thresholds: image checks at the median of the image-checked dates; indirect checks at their
    median only where they proved useful. Returns (thresholds, summary)."""
    d = df[pd.to_numeric(df['water_nir'], errors='coerce').notna()]
    pc = proxy_check(df, c)
    th = {}
    if len(d) >= 5:
        th['SCENE_MAX_NIR'] = round(float(pd.to_numeric(d.water_nir).median()), 4)
        th['SCENE_MAX_B5'] = round(float(pd.to_numeric(d.water_b5).median()), 4)
    for col_, opt, flag, lab, tgt, side in PROXIES:
        r = pc[pc.check == lab]
        if len(r) and r.iloc[0].verdict.startswith('useful'):
            th[opt] = round(float(pd.to_numeric(d[col_], errors='coerce').median()), 2)
    flags = {f: True for col_, opt, f, *_ in PROXIES if f and opt in th}
    if th: flags.update(GLINT_FILTER=True, TURBIDITY_FILTER=True)
    cur = apply_checks(df, c)[0]['kept']
    strict = apply_checks(df, {**c, **th, **flags})[0]['kept']
    obs = lambda k: float(pd.to_numeric(df.loc[k, 'clear_est'], errors='coerce').sum()) if 'clear_est' in df else np.nan
    tighter = {k: v for k, v in th.items()
               if c[k] is None or (v > c[k] if k == 'META_MIN_GLINT_ANGLE' else v < c[k])}
    return th, dict(dates_current=int(cur.sum()), dates_strict=int(strict.sum()), clear_obs_current=obs(cur),
                    clear_obs_strict=obs(strict), target=c['TARGET_CLEAR_OBS'], tighter=tighter, image_checked=len(d))


# ================================================================================ image-by-image checker
def thumb_url(date, c, size=360):
    """True-colour thumbnail of the AOI on one date (all tiles of that date and orbit, no cloud mask), AOI outlined."""
    d0 = ee.Date(date)
    col_ = (ee.ImageCollection('COPERNICUS/S2_SR_HARMONIZED').filterBounds(roi).filterDate(d0, d0.advance(1, 'day')))
    if c['ORBIT'] is not None:
        col_ = col_.filter(ee.Filter.eq('SENSING_ORBIT_NUMBER', c['ORBIT']))
    vis = col_.mosaic().visualize(bands=['B4', 'B3', 'B2'], min=0, max=1500, gamma=1.3)
    outline = ee.Image().byte().paint(aoi_fc, 1, 2).visualize(palette=['ff00ff'])
    return vis.blend(outline).getThumbURL({'region': roi.bounds(), 'dimensions': size, 'format': 'png'})

def save_decision(date, decision, note=''):
    path = decisions_path(CFG)
    d = load_decisions(CFG)
    orb = 'all' if S2['ORBIT'] is None else str(S2['ORBIT'])
    d = d[~((d.date.astype(str) == str(date)) & (d.orbit.astype(str) == orb))]
    if decision in ('accept', 'reject'):
        d = pd.concat([d, pd.DataFrame([dict(date=str(date), orbit=orb, decision=decision, note=note,
                                             decided_utc=dt.datetime.now(dt.timezone.utc).isoformat(timespec='seconds'))])])
    d.sort_values(['orbit', 'date']).to_csv(path + '.tmp', index=False); os.replace(path + '.tmp', path)

def checker(ctx=None, page_size=12, size=360, show_first='all'):
    """Gallery of the screened dates, best first, with Accept / Reject / Auto buttons.
    Decisions are saved at once to <FOLDER_ROOT>__S2_image_decisions.csv in the outputs folder; run the S2 options
    cell and st.s2.run(ctx) again to make a composite that uses them. Accepting a date that has not had the image
    check yet sends it to Earth Engine at the next run (only that date)."""
    import ipywidgets as wg
    from IPython.display import display
    try:
        from google.colab import output; output.enable_custom_widget_manager()
    except Exception:
        pass
    global WAVE_SERIES
    ctx = bind(globals(), 's2', ctx)
    c = S2
    WAVE_SERIES = load_series(required=c['WAVE_FILTER'] or (c['WIND_FILTER'] and c['WIND_SOURCE'] == 'cds') or c['RAIN_SOURCE'] == 'era5')
    s2_raw, col_ = s2_collection(c)
    auto_c = dict(c, MANUAL_DECISIONS=False)              # automatic result, without your decisions
    df, _, _ = screening(auto_c, col_)
    df = df.rename(columns={'kept': 'auto_kept', 'reason': 'auto_reason'})
    df = df.sort_values(['quality_score', 'date']).reset_index(drop=True)
    dec = dict((d, v) for d, v in applicable_decisions(CFG))
    state = dict(page=0, filt=show_first)
    out = wg.Output()
    summary = wg.HTML()
    lim = {'meta_cloud': (c['META_MAX_CLOUD'], 'above'), 'meta_cirrus': (c['META_MAX_CIRRUS'], 'above'),
           'glint_angle': (c['META_MIN_GLINT_ANGLE'], 'below'), 'water_nir': (c['SCENE_MAX_NIR'], 'above'),
           'water_b5': (c['SCENE_MAX_B5'], 'above'), 'rain_mm': (c['RAIN_MAX_MM'], 'above'),
           'wind_ms': (c['WIND_MAX_MS'], 'above'), 'hs_m': (c['WAVE_MAX_HS'], 'above')}
    short = {'meta_cloud': 'tile cloud %', 'meta_cirrus': 'cirrus %', 'glint_angle': 'glint°', 'water_nir': 'NIR',
             'water_b5': 'B5', 'rain_mm': 'rain', 'wind_ms': 'wind', 'hs_m': 'Hs'}

    def final(r):
        v = dec.get(r.date)
        return True if v == 'accept' else False if v == 'reject' else bool(r.auto_kept)

    def refresh_summary():
        k = sum(final(r) for r in df.itertuples())
        n_acc = sum(v == 'accept' for v in dec.values()); n_rej = sum(v == 'reject' for v in dec.values())
        summary.value = (f"<b>{len(df)}</b> dates · image-checked <b>{int(df.aoi_evaluated.sum())}</b> · automatically kept "
                         f"<b>{int(df.auto_kept.sum())}</b> · your decisions: <b>{n_acc}</b> accepted, <b>{n_rej}</b> rejected · "
                         f"the composite would use <b>{k}</b> dates. Decisions file: <code>{decisions_path(CFG)}</code>")

    def view():
        f = state['filt']
        if f == 'automatically kept': return df[df.auto_kept]
        if f == 'automatically dropped': return df[~df.auto_kept]
        if f == 'image-checked': return df[df.aoi_evaluated]
        if f == 'decided by you': return df[df.date.isin(dec)]
        return df

    def card(r):
        vals = []
        for k, lab in short.items():
            x = pd.to_numeric(getattr(r, k, np.nan), errors='coerce')
            if pd.isna(x): continue
            thr, side = lim[k]
            bad = thr is not None and ((x > thr) if side == 'above' else (x < thr))
            vals.append(f"<span style='color:{'#D55E00' if bad else 'inherit'}'>{lab} {x:.3g}</span>")
        verdict = 'kept' if r.auto_kept else f"dropped ({r.auto_reason})"
        clear = (f"clear water {r.clear_share:.0%}" if pd.notna(r.clear_share) else
                 f"no image check" if not r.aoi_evaluated else 'no clear water')
        html = wg.HTML(f"<b>{r.date}</b> · score {r.quality_score:.0f} · {clear} · tiles {r.tile_list}<br>"
                       f"<span style='font-size:11px'>{' · '.join(vals)}<br>auto: {verdict}</span>")
        try:
            img = wg.HTML(f"<img src='{thumb_url(r.date, c, size)}' width='{size}'>")
        except Exception as e:
            img = wg.HTML(f'<i>thumbnail failed: {str(e)[:80]}</i>')
        cur = dec.get(r.date, 'auto')
        tb = wg.ToggleButtons(options=[('Auto', 'auto'), ('Accept', 'accept'), ('Reject', 'reject')], value=cur,
                              style={'button_width': '80px'})
        def on_change(ch, date=r.date):
            save_decision(date, ch['new'])
            if ch['new'] == 'auto': dec.pop(date, None)
            else: dec[date] = ch['new']
            refresh_summary()
        tb.observe(on_change, names='value')
        return wg.VBox([img, html, tb], layout=wg.Layout(border='1px solid #ccc', padding='4px', margin='3px', width=f'{size + 14}px'))

    def show():
        v = view(); n_pages = max(1, int(np.ceil(len(v) / page_size)))
        state['page'] = min(state['page'], n_pages - 1)
        page = v.iloc[state['page'] * page_size:(state['page'] + 1) * page_size]
        pager.value = f"page {state['page'] + 1} / {n_pages} ({len(v)} dates)"
        with out:
            out.clear_output(wait=True)
            display(wg.HBox([card(r) for r in page.itertuples()], layout=wg.Layout(flex_flow='row wrap')))

    prev_b, next_b = wg.Button(description='◀ previous'), wg.Button(description='next ▶')
    pager = wg.HTML()
    filt = wg.Dropdown(options=['all', 'automatically kept', 'automatically dropped', 'image-checked', 'decided by you'],
                       value=show_first, description='show')
    def go(delta):
        state['page'] = max(0, state['page'] + delta); show()
    prev_b.on_click(lambda _: go(-1)); next_b.on_click(lambda _: go(+1))
    filt.observe(lambda ch: (state.update(filt=ch['new'], page=0), show()), names='value')
    refresh_summary()
    print('Dates are sorted by quality score (0 = best; dates without the image check are scored on metadata and weather only). '
          'Values in orange fail the current threshold. Thumbnails: all tiles of the date, no cloud masking, '
          'reflectance 0–0.15; magenta = AOI. A thumbnail is computed by Earth Engine only when its page is shown.')
    display(wg.VBox([summary, wg.HBox([prev_b, next_b, pager, filt]), out]))
    show()
    return df


def run(ctx=None, force=False):
    """Run this step. Same settings = same folder: finished exports and stages are re-used
    (force=True starts them again)."""
    global S2_HASH, S2_RESULT, pc, WAVE_SERIES, ax, axs, b4, c, col, col_kept, comp, count, exclude, fig, \
           flags_txt, img_, invalid, k, kw, lab, med, n, name, names, nm, off_diag, offsets, on, outs, p, \
           parts, qa, raw, rule_counts, s2_raw, scr, src_tile, st_, t, tag, thr, tn, tstd, v, vars_, vcol
    ctx = bind(globals(), 's2', ctx)
    ctx.force = force
    figure_style()
    WAVE_SERIES = load_series(required=S2['WAVE_FILTER'] or (S2['WIND_FILTER'] and S2['WIND_SOURCE'] == 'cds') or S2['RAIN_SOURCE'] == 'era5')
    S2_HASH = hashlib.sha256(json.dumps(_jsonable(S2), sort_keys=True).encode()).hexdigest()[:6]
    S2_RESULT = {}
    c, tag = S2, s2_tag(S2)
    if c['WAVE_FILTER'] and not any(s in WAVE_SERIES for s in {'cmems': ['cmems'], 'era5': ['era5'], 'max': ['era5', 'cmems']}[W['SCREEN_SOURCE']]):
        raise RuntimeError('WAVE_FILTER is on but no Module 0 wave series is loaded: run Module 0 or set S2["WAVE_FILTER"] = False')
    if c['WIND_FILTER'] and c['WIND_SOURCE'] == 'cds' and ('era5' not in WAVE_SERIES or 'wind_speed' not in WAVE_SERIES['era5']):
        raise RuntimeError('WIND_SOURCE = "cds" needs ERA5 wind from Module 0 (W["ERA5_WIND"] = True), or set WIND_SOURCE = "gee"')
    if c['RAIN_FILTER'] and c['RAIN_SOURCE'] == 'era5' and ('era5' not in WAVE_SERIES or 'rain_mm' not in WAVE_SERIES['era5']):
        raise RuntimeError('RAIN_SOURCE = "era5" needs ERA5 rain from the waves step (total_precipitation in ERA5_VARIABLES), or set RAIN_SOURCE = "chirps"')
    s2_raw, col = s2_collection(c)

    # (a)+(b) screening -> excluded dates
    scr, rule_counts = None, {}
    if c['EXCLUDE_DATES'] is not None:
        exclude = list(c['EXCLUDE_DATES'])
    elif stage_get('s2_screening'):
        st_ = stage_get('s2_screening'); exclude = st_['exclude']; rule_counts = st_['rule_counts']
        scr = pd.read_csv(st_['decided_csv']); print('  screening already done with these options:', len(exclude), 'dates excluded')
    else:
        print(f"Date screening ({c['SCREENING']}):")
        scr, rule_counts, tiles = screening(c, col)
        p = drive_path('s2', f'S2_tile_metadata_h{S2_HASH}.csv'); tiles.to_csv(p, index=False); record_file(p)
        n_man = int((scr.manual != '').sum())
        if n_man: print(f"  your decisions applied to {n_man} dates ({int((scr.manual == 'accept').sum())} accepted, {int((scr.manual == 'reject').sum())} rejected)")
        p = drive_path('s2', f'S2_date_screening_h{S2_HASH}_decided.csv'); scr.to_csv(p, index=False); record_file(p)
        exclude = scr.loc[~scr['kept'], 'date'].tolist()
        stage_done('s2_screening', exclude=exclude, rule_counts=rule_counts, decided_csv=p)
    if scr is not None:
        print(f'Dates: {len(scr)} | image-checked {int(scr.aoi_evaluated.sum())} | dropped {len(exclude)} | '
              'per check (evaluated / failed / missing / not evaluated):')
        for k, v in rule_counts.items():
            print(f"   {k:11s} {v['evaluated']:4d} / {v['failed']:4d} / {v['missing']:4d} / {v.get('not_evaluated', 0):4d}")
        print('   screening status:', scr['screen_status'].value_counts().to_dict())
        # ---------------- figure: screening variables and thresholds ----------------
        vars_ = [('meta_cloud', 'tile cloud, metadata (%)', c['META_MAX_CLOUD'], c['META_MAX_CLOUD'] is not None),
                 ('water_nir', 'median water NIR (B8)', c['SCENE_MAX_NIR'], c['GLINT_FILTER']),
                 ('water_b5', 'median water red edge (B5)', c['SCENE_MAX_B5'], c['TURBIDITY_FILTER']),
                 ('rain_mm', f"rain, {c['RAIN_DAYS']} days before (mm)", c['RAIN_MAX_MM'], c['RAIN_FILTER']),
                 ('wind_ms', f"ERA5 wind, {c['WIND_WINDOW_H']} h before (m s$^{{-1}}$)", c['WIND_MAX_MS'], c['WIND_FILTER']),
                 ('hs_m', f"offshore $H_s$, {c['WAVE_WINDOW_H']} h before (m)", c['WAVE_MAX_HS'], c['WAVE_FILTER'])]
        fig, axs = plt.subplots(2, 4, figsize=(7.2, 4.4), constrained_layout=True)
        axs.ravel()[-2].set_visible(False)
        for ax, (vcol, lab, thr, on) in zip(axs.ravel(), vars_):
            v = pd.to_numeric(scr[vcol], errors='coerce').dropna() if vcol in scr else pd.Series(dtype=float)
            if len(v):
                ax.hist(v, bins=30, color=OKABE_ITO[0], alpha=0.8, edgecolor='white', lw=0.3)
            if on: ax.axvline(thr, color=OKABE_ITO[3], ls='--', lw=1, label=f'threshold {thr:g}')
            nm = len(scr) - len(v)
            ax.set_xlabel(lab); ax.set_ylabel('dates')
            ax.legend(loc='upper right', title=f'missing: {nm}' if nm else None, title_fontsize=7)
        ax = axs.ravel()[-1]
        t = pd.to_datetime(scr['date'])
        ax.scatter(t[scr.kept], np.ones(scr.kept.sum()), s=8, color=OKABE_ITO[2], label=f'kept ({scr.kept.sum()})')
        ax.scatter(t[~scr.kept], np.zeros((~scr.kept).sum()), s=8, color=OKABE_ITO[3], label=f'dropped ({(~scr.kept).sum()})')
        ax.set_yticks([0, 1]); ax.set_yticklabels(['dropped', 'kept']); ax.set_ylim(-0.6, 1.8)
        ax.legend(loc='upper center', ncol=2); ax.tick_params(axis='x', rotation=45)
        panel_labels(axs, x=-0.18)
        fig.suptitle(f'Sentinel-2 date screening, {c["YEARS"][0]}–{c["YEARS"][1]} months {c["MONTHS"][0]}–{c["MONTHS"][1]}', fontsize=10)
        save_fig(fig, 's2', f'{PREFIX}_Fig_S2_date_screening'); plt.show()
        # ---------------- do the indirect checks (rain, wind, waves) predict turbid water? ----------------
        pc = proxy_check(scr, c)
        p = drive_path('s2', f'S2_{tag}_indirect_checks.csv'); pc.to_csv(p, index=False); record_file(p)
        print('Indirect checks vs the image (turbidity B5, glint / haze NIR) on the image-checked dates:')
        for r in pc.itertuples(): print(f'   {r.check:11s} {r.verdict}')
        proxy_figure(scr, c, pc)
    col_kept = col.filter(ee.Filter.inList('date', exclude or ['none']).Not())

    # (c) tile offsets (with diagnostics), checkpointed
    off_diag = None
    if len(c['GROUPS']) > 1 and c['FIXED_OFFSETS'] is None:
        if stage_get('s2_offsets'):
            offsets = stage_get('s2_offsets')['offsets']; print('  offsets already measured in this run')
        else:
            print('Measuring tile offsets ...')
            offsets, off_diag = s2_measure_offsets(col_kept, c)
            p = drive_path('s2', f'S2_{tag}_tile_offsets_diagnostics.csv'); off_diag.to_csv(p, index=False); record_file(p)
            stage_done('s2_offsets', offsets=offsets, flags=off_diag['flag'].tolist())
    else:
        offsets = c['FIXED_OFFSETS'] or {}

    # (d) build + export
    parts = tile_parts(col_kept, c, offsets)
    comp = priority_mosaic([p['comp'] for p in parts]).select(BANDS)
    count = priority_mosaic([p['count'] for p in parts])
    src_tile = priority_mosaic([p['src'] for p in parts])
    tstd = priority_mosaic([p['tstd'] for p in parts])
    if c['B1_FROM_B2']:
        comp = comp.addBands(comp.select(['B2'], ['B1']), None, True).select(BANDS)
    invalid = comp.lt(0).Or(comp.gt(1)).reduce(ee.Reducer.max()).rename('invalid_reflectance').toInt16()
    qa = ee.Image.cat([count.rename('valid_count'), src_tile, invalid]).toInt16()
    outs = [(comp, f'S2_{tag}_12band_Float32', {}),
            (qa, f'S2_{tag}_QA', dict(nodata=-1, to_float=False)),
            (tstd, f'S2_{tag}_B2_TemporalStd', {})]
    if c['SENSITIVITY_MEDIAN']:
        b4 = ['B1', 'B2', 'B3', 'B4']
        med = priority_mosaic([p['comp'] for p in tile_parts(col_kept, c, offsets, pct=50, bands=b4)])
        outs.append((med, f'S2_{tag}_Median_B1-B4_sensitivity', {}))
    names = []
    for img_, nm, kw in outs:
        export_image(img_, 's2', nm, c['SCALE'], **kw); names.append(nm)
    S2_RESULT = dict(composite=comp, count=count, tstd=tstd, exclude=exclude, offsets=offsets, tasks=names,
                     tag=tag, b1_from_b2=c['B1_FROM_B2'])
    MANIFEST['outputs'] = dict(tag=tag, composite_task=names[0], qa_task=names[1], median_task=names[3] if c['SENSITIVITY_MEDIAN'] else None,
                          b1_from_b2=c['B1_FROM_B2'], excluded_dates=exclude, offsets=offsets, rule_counts=rule_counts)
    save_manifest()
    flags_txt = '; '.join(f"{r.group}: {r.flag}" for r in off_diag.itertuples() if r.flag) if off_diag is not None else ''

    write_readme('s2', 'README_01_S2_composite_SDB', f"""
    # Sentinel-2 dry-season composite for satellite-derived bathymetry (Bathymetrix-AI input)

    ## Files
    | File | Content |
    |---|---|
    | `S2_{tag}_12band_Float32.tif` | surface reflectance, Float32, NoData −9999, {c['SCALE']} m, {CRS}, aligned grid. Bands 1 B1 coastal · 2 B2 blue · 3 B3 green · 4 B4 red · 5 B5 · 6 B6 · 7 B7 · 8 B8 NIR · 9 B8A · 10 B9 · 11 B11 SWIR1 · 12 B12 SWIR2 (= Bathymetrix-AI defaults: Coastal 1, Blue 2, Green 3, Red 4, NIR 8, SWIR 11){' — **band 1 is a copy of B2 (B1_FROM_B2): the coastal band is NOT a real B1 observation**' if c['B1_FROM_B2'] else ''} |
    | `S2_{tag}_QA.tif` | Int16, NoData −1: band 1 clear observations of the tile used (≥ {c['MIN_VALID']}), band 2 source tile (1..{max(1, len(c['GROUPS']))} = {', '.join(map(str, c['GROUPS'])) or 'all'}), band 3 = 1 where any band is < 0 or > 1 after tile matching |
    | `S2_{tag}_B2_TemporalStd.tif` | temporal std of blue reflectance **of the tile used at each pixel** |
    | `S2_{tag}_Median_B1-B4_sensitivity.tif` | {'median composite of B1–B4 (same dates and offsets), for sensitivity tests' if c['SENSITIVITY_MEDIAN'] else 'not produced'} |
    | `S2_date_screening_h{S2_HASH}*.csv` | per date: tiles, acquisition times, tile metadata (cloud, shadow, cirrus, no-data %, glint angle), rain, wind and Hs per source with sample count, largest gap and status, image check (`aoi_evaluated`; water NIR/B5 + clear-water pixel count), check results (`chk_*`: pass / fail / missing / not evaluated), reason, unchecked, your decision (`manual`), kept, quality score |
    | `S2_tile_metadata_h{S2_HASH}.csv` | every tile image used: metadata as provided by ESA (percentages refer to the whole 110 km tile) |
    | `S2_{tag}_indirect_checks.csv`, `{PREFIX}_Fig_S2_indirect_checks.png/.pdf` | do rain, wind and waves predict turbid water (B5) on these dates? medians above/below each threshold, Mann-Whitney p, verdict |
    | `{FOLDER_ROOT}__S2_image_decisions.csv` (My Drive) | your Accept / Reject choices from the image checker (applied: {S2['MANUAL_DECISIONS']}) |
    | `S2_{tag}_tile_offsets_diagnostics.csv` | per tile: overlap water pixels, offset and IQR per band, flags (unsupported / large / pushes water below 0) |
    | `{PREFIX}_Fig_S2_date_screening.png/.pdf` | screening variables with thresholds and missing counts, kept / dropped dates |

    Native band resolutions are 10 m (B2–B4, B8), 20 m (B5–B7, B8A, B11, B12) and 60 m (B1, B9); all are delivered on the 10 m grid (nearest neighbour), so B1 detail is 60 m.

    ## Method
    1. Sentinel-2 L2A (COPERNICUS/S2_SR_HARMONIZED; 2A/2B/2C), months {c['MONTHS']} of {c['YEARS']}{f", relative orbit {c['ORBIT']} only" if c['ORBIT'] else ''}.
    2. Tile cloud < {c['MAX_TILE_CLOUD']} %; Cloud Score+ cs_cdf ≥ {c['CS_THRESHOLD']}; reflectance = DN/10000; water pixels with B11 > {c['PIXEL_MAX_SWIR']} masked; an observation is used only where all 12 bands are valid.
    3. Date screening, mode `{c['SCREENING']}`: (i) tile metadata, no pixels processed (mean over the tiles of the date: cloud ≤ {c['META_MAX_CLOUD']} %, shadow ≤ {c['META_MAX_SHADOW']} %, thin cirrus ≤ {c['META_MAX_CIRRUS']} %, glint angle ≥ {c['META_MIN_GLINT_ANGLE']}°; None = not used); (ii) weather; (iii) image check in Earth Engine {'for all dates' if c['SCREENING'] == 'aoi' else 'not done' if c['SCREENING'] == 'metadata' else 'only for the dates that passed (i) and (ii), plus dates you accepted'} (water = Copernicus DEM water body mask): glint (median water B8 > {c['SCENE_MAX_NIR']}), turbidity (median water B5 > {c['SCENE_MAX_B5']}), rain ({'ERA5 at the waves point' if c['RAIN_SOURCE'] == 'era5' else f"CHIRPS, AOI + {c['RAIN_BUFFER']/1000:.0f} km"}, sum of the {c['RAIN_DAYS']} whole days before the acquisition day > {c['RAIN_MAX_MM']} mm), wind (ERA5 {'point series from Module 0 (CDS)' if c['WIND_SOURCE'] == 'cds' else 'area mean in GEE, AOI + ' + str(c['WIND_BUFFER']//1000) + ' km'}, mean over the {c['WIND_WINDOW_H']} h ending at acquisition > {c['WIND_MAX_MS']} m/s), waves (offshore Hs, source {W['SCREEN_SOURCE']}, max over the {c['WAVE_WINDOW_H']} h ending at acquisition > {c['WAVE_MAX_HS']} m). Missing-data policy: `{json.dumps(c['MISSING_POLICY'])}`.
       Per rule (evaluated / failed / missing): `{json.dumps(rule_counts)}`.
    4. Excluded dates ({len(exclude)}): {', '.join(exclude) if exclude else 'none'}.
    5. {'Median' if c['PERCENTILE'] == 50 else f"{c['PERCENTILE']}th percentile"} per pixel and tile; each tile masked where it has < {c['MIN_VALID']} clear observations **before** the tile mosaic.
    6. Seam removal: {f"one composite per {c['GROUP_BY']} ({', '.join(map(str, c['GROUPS']))}), each shifted by the per-band median difference over overlap water (NDWI > {c['WATER_NDWI']}, B8 < {c['WATER_NIR']}, {c['OFFSET_SCALE']} m) to the tiles before it; offsets with < {c['MIN_MATCH_PIXELS']} pixels: {c['NO_WATER_FALLBACK']}; |offset| > {c['OFFSET_MAX']} flagged." if len(c['GROUPS']) > 1 else 'none.'}
       Offsets (reflectance): `{json.dumps(offsets)}`. Flags: {flags_txt or 'none'}.
    7. Export grid: {CRS}, origin ({GRID_X0:.0f}, {GRID_Y1:.0f}), {c['SCALE']} m (crsTransform), shared by all products of this run.

    ## Assumptions
    - Seabed and dry-season water column stable enough over the year range for a multi-year composite.
    - Tile differences are additive per band (separate atmospheric correction per MGRS tile).

    ## Limitations
    - A bandwise percentile can combine bands from different dates; additive offsets slightly change band ratios. Compare with the median composite before relying on one depth limit.
    - The composite mixes dates and tide levels: use a fixed vertical datum for training depths.
    - Thresholds are empirical; check the screening CSV. ERA5, CHIRPS and the wave models are area / point proxies.
    - Sen2Cor is not optimised for water; very shallow bright and turbid areas are less reliable (TemporalStd, QA).

    ## Sources
    Copernicus Sentinel-2 (ESA) and its tile metadata; Cloud Score+ (Pasquarella et al. 2023); CHIRPS (Funk et al. 2015); ERA5 (Hersbach et al. 2020);
    Copernicus DEM GLO-30 water body mask; Copernicus Marine global waves (Module 0).
    """)
    if WAIT_FOR_EXPORTS:
        wait(names)
        for n in names: task_files(n)
        set_status('s2', 'complete' if (scr is None or (scr['screen_status'] != 'unchecked').all()) else 'partial',
                   unchecked_dates=int((scr['screen_status'] == 'unchecked').sum()) if scr is not None else None)
    return ctx

