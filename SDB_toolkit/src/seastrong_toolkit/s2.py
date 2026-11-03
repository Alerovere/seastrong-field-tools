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
3. **Screen whole dates** that would bias the seabed colour: glint or haze (high NIR over water), river
   plumes (high red-edge B5), runoff after rain (CHIRPS, days before the image), wind-stirred water and
   rough seas (Module 0 ERA5 / Copernicus Marine, in a window **ending at the image's acquisition time**).
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
                   secret, CMEMS_REGIONS)
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
SCREEN_COLS = ['date', 'tiles', 't_first_ms', 't_last_ms', 'water_nir', 'water_b5', 'n_water_px',
               'rain_mm', 'rain_days', 'wind_ms_gee', 'wind_n_gee']
def s2_screening_table(col, c):
    """Per-date statistics: acquisition times, water NIR / B5, rain [day-N, day), GEE wind (optional)."""
    rain_region = roi.bounds().buffer(c['RAIN_BUFFER'])
    wind_region = roi.bounds().buffer(c['WIND_BUFFER'])
    def row(d):
        day = ee.Date(d)                                   # midnight UTC of the acquisition day
        imgs = col.filter(ee.Filter.eq('date', d))
        t_last = ee.Date(imgs.aggregate_max('system:time_start'))
        wat = imgs.mosaic().select(['B8', 'B5']).updateMask(water)
        st = wat.reduceRegion(reducer=ee.Reducer.median().combine(ee.Reducer.count(), None, True),
                              geometry=roi, scale=c['SCENE_STAT_SCALE'], maxPixels=1e9, bestEffort=True, tileScale=16)
        rcol = chirps.filterDate(day.advance(-c['RAIN_DAYS'], 'day'), day)       # whole days before the image
        rain = ee.Algorithms.If(rcol.size().eq(c['RAIN_DAYS']),
            rcol.sum().reduceRegion(reducer=ee.Reducer.mean(), geometry=rain_region, scale=5566,
                                    maxPixels=1e9, bestEffort=True).get('precipitation'), None)
        props = {'date': d, 'tiles': imgs.size(), 't_first_ms': imgs.aggregate_min('system:time_start'),
                 't_last_ms': imgs.aggregate_max('system:time_start'), 'water_nir': st.get('B8_median'),
                 'water_b5': st.get('B5_median'), 'n_water_px': st.get('B8_count'),
                 'rain_mm': rain, 'rain_days': rcol.size()}
        if c['WIND_FILTER'] and c['WIND_SOURCE'] == 'gee':
            w = era5_gee.filterDate(t_last.advance(-c['WIND_WINDOW_H'], 'hour'), t_last.advance(1, 'second'))
            spd = w.map(lambda i: i.expression('hypot(b("u"), b("v"))').rename('s'))
            props['wind_ms_gee'] = ee.Algorithms.If(w.size().gt(0), spd.mean().reduceRegion(
                reducer=ee.Reducer.mean(), geometry=wind_region, scale=27830, maxPixels=1e9, bestEffort=True).get('s'), None)
            props['wind_n_gee'] = w.size()
        return ee.Feature(None, props)
    dates = col.aggregate_array('date').distinct().sort()
    return ee.FeatureCollection(dates.map(row))
def s2_decide(df, c):
    """Apply all date checks. Each check is 'pass', 'fail' or 'missing'; missing follows MISSING_POLICY."""
    df = df.copy()
    t1 = pd.to_datetime(df['t_last_ms'], unit='ms', utc=True)
    span_h = (df['t_last_ms'] - df['t_first_ms']).fillna(0) / 3.6e6
    # waves: per source, window (first acquisition - WAVE_WINDOW_H, last acquisition]
    srcs = {'cmems': ['cmems'], 'era5': ['era5'], 'max': ['era5', 'cmems']}[W['SCREEN_SOURCE']]
    if c['WAVE_FILTER']:
        for s in srcs:
            ser = WAVE_SERIES[s].set_index('time')['hs'] if s in WAVE_SERIES else pd.Series(dtype=float)
            res = [window_stats(ser, t, c['WAVE_WINDOW_H'] + h, 1 if s == 'era5' else W['CMEMS_STEP_H']) for t, h in zip(t1, span_h)]
            df[f'hs_{s}'], df[f'hs_{s}_n'], df[f'hs_{s}_maxgap_h'], df[f'hs_{s}_status'] = map(list, zip(*res))
        st = df[[f'hs_{s}_status' for s in srcs]]
        df['hs_m'] = df[[f'hs_{s}' for s in srcs]].max(axis=1, skipna=True)
        df['hs_status'] = np.where((st == 'ok').all(axis=1), 'ok', np.where((st == 'missing').all(axis=1), 'missing', 'partial'))
    if c['WIND_FILTER']:
        if c['WIND_SOURCE'] == 'cds':
            ser = WAVE_SERIES['era5'].set_index('time')['wind_speed']
            res = [window_stats(ser, t, c['WIND_WINDOW_H'] + h, 1, how='mean') for t, h in zip(t1, span_h)]
            df['wind_ms'], df['wind_n'], df['wind_maxgap_h'], df['wind_status'] = map(list, zip(*res))
        else:
            df['wind_ms'], df['wind_n'] = df['wind_ms_gee'], df['wind_n_gee']
            df['wind_status'] = np.where(df['wind_ms'].notna(), 'ok', 'missing')

    checks = [('water', 'glint', c['GLINT_FILTER'], 'water_nir', c['SCENE_MAX_NIR']),
              ('water', 'turbid', c['TURBIDITY_FILTER'], 'water_b5', c['SCENE_MAX_B5']),
              ('rain', 'rain', c['RAIN_FILTER'], 'rain_mm', c['RAIN_MAX_MM']),
              ('wind', 'wind', c['WIND_FILTER'], 'wind_ms', c['WIND_MAX_MS']),
              ('waves', 'waves', c['WAVE_FILTER'], 'hs_m', c['WAVE_MAX_HS'])]
    reasons = [[] for _ in range(len(df))]; unchecked = [[] for _ in range(len(df))]
    rule_counts = {}
    for kind, name, on, colname, thr in checks:
        if not on: continue
        v = pd.to_numeric(df[colname], errors='coerce').values
        miss = ~np.isfinite(v); fail = np.isfinite(v) & (v > thr)
        df[f'chk_{name}'] = np.where(miss, 'missing', np.where(fail, 'fail', 'pass'))
        rule_counts[name] = dict(evaluated=int((~miss).sum()), failed=int(fail.sum()), missing=int(miss.sum()))
        for i in np.where(fail)[0]: reasons[i].append(name)
        for i in np.where(miss)[0]:
            (reasons[i].append(f'no_{name}_data') if c['MISSING_POLICY'][kind] == 'drop' else unchecked[i].append(name))
    df['reason'] = [','.join(sorted(set(r))) for r in reasons]
    df['unchecked'] = [','.join(u) for u in unchecked]
    df['kept'] = df['reason'] == ''
    partial = (df.get('hs_status', 'ok') == 'partial') | (df.get('wind_status', 'ok') == 'partial')
    df['screen_status'] = np.where(df['unchecked'] != '', 'unchecked', np.where(partial, 'partial', 'complete'))
    return df, rule_counts
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


def run(ctx=None, force=False):
    """Run this step. Same settings = same folder: finished exports and stages are re-used
    (force=True starts them again)."""
    global S2_HASH, S2_RESULT, WAVE_SERIES, ax, axs, b4, c, col, col_kept, comp, count, exclude, fig, \
           flags_txt, img_, invalid, k, kw, lab, med, n, name, names, nm, off_diag, offsets, on, outs, p, \
           parts, qa, raw, rule_counts, s2_raw, scr, src_tile, st_, t, tag, thr, tn, tstd, v, vars_, vcol
    ctx = bind(globals(), 's2', ctx)
    ctx.force = force
    figure_style()
    WAVE_SERIES = load_series(required=S2['WAVE_FILTER'] or (S2['WIND_FILTER'] and S2['WIND_SOURCE'] == 'cds'))
    S2_HASH = hashlib.sha256(json.dumps(_jsonable(S2), sort_keys=True).encode()).hexdigest()[:6]
    S2_RESULT = {}
    c, tag = S2, s2_tag(S2)
    if c['WAVE_FILTER'] and not any(s in WAVE_SERIES for s in {'cmems': ['cmems'], 'era5': ['era5'], 'max': ['era5', 'cmems']}[W['SCREEN_SOURCE']]):
        raise RuntimeError('WAVE_FILTER is on but no Module 0 wave series is loaded: run Module 0 or set S2["WAVE_FILTER"] = False')
    if c['WIND_FILTER'] and c['WIND_SOURCE'] == 'cds' and ('era5' not in WAVE_SERIES or 'wind_speed' not in WAVE_SERIES['era5']):
        raise RuntimeError('WIND_SOURCE = "cds" needs ERA5 wind from Module 0 (W["ERA5_WIND"] = True), or set WIND_SOURCE = "gee"')
    s2_raw, col = s2_collection(c)
    print('Images per tile:', s2_raw.aggregate_histogram('MGRS_TILE').getInfo())

    # (a)+(b) screening -> excluded dates
    scr, rule_counts = None, {}
    if c['EXCLUDE_DATES'] is not None:
        exclude = list(c['EXCLUDE_DATES'])
    elif stage_get('s2_screening'):
        st_ = stage_get('s2_screening'); exclude = st_['exclude']; rule_counts = st_['rule_counts']
        scr = pd.read_csv(st_['decided_csv']); print('  screening already done in this run:', len(exclude), 'dates excluded')
    else:
        name = f'S2_date_screening_h{S2_HASH}'
        tn = export_table(s2_screening_table(col, c), 's2', name,
                          selectors=SCREEN_COLS if (c['WIND_FILTER'] and c['WIND_SOURCE'] == 'gee') else SCREEN_COLS[:-2])
        wait([name])
        raw = read_task_csv(name)
        scr, rule_counts = s2_decide(raw, c)
        p = drive_path('s2', name + '_decided.csv'); scr.to_csv(p, index=False); record_file(p)
        exclude = scr.loc[~scr['kept'], 'date'].tolist()
        stage_done('s2_screening', exclude=exclude, rule_counts=rule_counts, decided_csv=p)
    if scr is not None:
        print(f'Dates: {len(scr)} | dropped {len(exclude)} | per rule (evaluated / failed / missing):')
        for k, v in rule_counts.items(): print(f"   {k:7s} {v['evaluated']:4d} / {v['failed']:4d} / {v['missing']:4d}")
        print('   screening status:', scr['screen_status'].value_counts().to_dict())
        # ---------------- figure: screening variables and thresholds ----------------
        vars_ = [('water_nir', 'median water NIR (B8)', c['SCENE_MAX_NIR'], c['GLINT_FILTER']),
                 ('water_b5', 'median water red edge (B5)', c['SCENE_MAX_B5'], c['TURBIDITY_FILTER']),
                 ('rain_mm', f"rain, {c['RAIN_DAYS']} days before (mm)", c['RAIN_MAX_MM'], c['RAIN_FILTER']),
                 ('wind_ms', f"ERA5 wind, {c['WIND_WINDOW_H']} h before (m s$^{{-1}}$)", c['WIND_MAX_MS'], c['WIND_FILTER']),
                 ('hs_m', f"offshore $H_s$, {c['WAVE_WINDOW_H']} h before (m)", c['WAVE_MAX_HS'], c['WAVE_FILTER'])]
        fig, axs = plt.subplots(2, 3, figsize=(7.2, 4.6), constrained_layout=True)
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
    | `S2_date_screening_h{S2_HASH}*.csv` | per date: acquisition times, water NIR/B5 (+ pixel count), rain (+ days available), wind and Hs per source with sample count, largest gap and status, check results (`chk_*`: pass / fail / missing), reason, unchecked, kept |
    | `S2_{tag}_tile_offsets_diagnostics.csv` | per tile: overlap water pixels, offset and IQR per band, flags (unsupported / large / pushes water below 0) |
    | `{PREFIX}_Fig_S2_date_screening.png/.pdf` | screening variables with thresholds and missing counts, kept / dropped dates |

    Native band resolutions are 10 m (B2–B4, B8), 20 m (B5–B7, B8A, B11, B12) and 60 m (B1, B9); all are delivered on the 10 m grid (nearest neighbour), so B1 detail is 60 m.

    ## Method
    1. Sentinel-2 L2A (COPERNICUS/S2_SR_HARMONIZED; 2A/2B/2C), months {c['MONTHS']} of {c['YEARS']}{f", relative orbit {c['ORBIT']} only" if c['ORBIT'] else ''}.
    2. Tile cloud < {c['MAX_TILE_CLOUD']} %; Cloud Score+ cs_cdf ≥ {c['CS_THRESHOLD']}; reflectance = DN/10000; water pixels with B11 > {c['PIXEL_MAX_SWIR']} masked; an observation is used only where all 12 bands are valid.
    3. Date screening (water = Copernicus DEM water body mask): glint (median water B8 > {c['SCENE_MAX_NIR']}), turbidity (median water B5 > {c['SCENE_MAX_B5']}), rain (CHIRPS sum of the {c['RAIN_DAYS']} whole days before the acquisition day > {c['RAIN_MAX_MM']} mm, AOI + {c['RAIN_BUFFER']/1000:.0f} km), wind (ERA5 {'point series from Module 0 (CDS)' if c['WIND_SOURCE'] == 'cds' else 'area mean in GEE, AOI + ' + str(c['WIND_BUFFER']//1000) + ' km'}, mean over the {c['WIND_WINDOW_H']} h ending at acquisition > {c['WIND_MAX_MS']} m/s), waves (offshore Hs, source {W['SCREEN_SOURCE']}, max over the {c['WAVE_WINDOW_H']} h ending at acquisition > {c['WAVE_MAX_HS']} m). Missing-data policy: `{json.dumps(c['MISSING_POLICY'])}`.
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
    Copernicus Sentinel-2 (ESA); Cloud Score+ (Pasquarella et al. 2023); CHIRPS (Funk et al. 2015); ERA5 (Hersbach et al. 2020);
    Copernicus DEM GLO-30 water body mask; Copernicus Marine global waves (Module 0).
    """)
    if WAIT_FOR_EXPORTS:
        wait(names)
        for n in names: task_files(n)
        set_status('s2', 'complete' if (scr is None or (scr['screen_status'] != 'unchecked').all()) else 'partial',
                   unchecked_dates=int((scr['screen_status'] == 'unchecked').sum()) if scr is not None else None)
    return ctx
