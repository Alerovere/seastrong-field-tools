"""Step 4 — water-motion overview (tracers + regional currents).

## Module 4 — Water-motion overview (tracers + regional currents)

**Observed tracer patterns, not currents.** A turbidity-like signal (sediment plumes) and water temperature
show where water goes on average and under given conditions (wind sector, after rain, season). HYCOM /
ERA5 give regional context only.

**What the tracer index is — and is not.** The index T = A·ρ/(1 − ρ/C) uses the Dogliotti et al. (2015)
red-band form, but it is applied to *land surface reflectance* (Sentinel-2 L2A, HLS, Landsat C2), not to
water-leaving reflectance with an aquatic atmospheric correction, and it is not locally calibrated. It is
therefore a **relative turbidity tracer index (RTI, unitless)**, not turbidity in FNU. Use it to compare
places and conditions *within one sensor family*, not as concentrations or for long-term trends.

**How the maps work.** Each clear water observation gets an index value. Each pixel's clear-water baseline
(10th percentile) is computed **separately for each sensor** (Landsat 5/7/8/9, HLS L30/S30, S2A/B/C), which
removes most inter-sensor offsets and the static bottom signal; what remains are plumes. A pixel counts as a
plume when the anomaly exceeds `PLUME_DT` **or when the red signal saturates the index** (ρ ≥ 0.9·C: very
turbid water is a plume, not missing data). Exported fractions say how often observations were saturated or
rejected by the SWIR glint test (which can also remove genuinely turbid water). Every conditioned map
(dry/wet, wind sectors, after rain / no rain) comes with its **own observation count** and is masked where
it has fewer than `MIN_SUPPORT` observations.

**Rain** is the CHIRPS sum over the `RAIN_DAYS` whole days *before* the acquisition day ([day − N, day)).
**Wind** for conditioning is ERA5 10 m wind (24 h mean before the image) read inside Earth Engine, because it
is needed for thousands of images server-side; this is wind only — the wave records of Module 0 come from the
Copernicus services directly.

**Temperature (Part D)** uses Landsat surface temperature, keeping pixels with ST uncertainty (ST_QA)
≤ `ST_MAX_UNC_K` and distance to cloud (ST_CDIST) ≥ `ST_MIN_CDIST_KM`. Anomalies are relative to the median
of a **fixed reference area** (your polygon, or all AOI water), used only when at least `ST_REF_MIN_COVER` of
that area is clear — so a changing cloud footprint does not create apparent contrasts.

**Run time.** Parts A, C and D process thousands of images; exports can take hours.
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

def add_weather(img, c=None):
    c = TR if c is None else c
    t0 = ee.Date(img.get('system:time_start'))
    day = ee.Date.fromYMD(t0.get('year'), t0.get('month'), t0.get('day'))      # midnight of the acquisition day
    wcol = era5_gee.filterDate(t0.advance(-24, 'hour'), t0)
    def wind_dict():
        w = wcol.mean().reduceRegion(reducer=ee.Reducer.first(), geometry=centre, scale=27830)
        u, v = ee.Number(w.get('u')), ee.Number(w.get('v'))
        frm = dir_to(u, v).add(180).mod(360)
        return ee.Dictionary({'wind_speed': u.hypot(v), 'wind_from': frm})
    wind = ee.Dictionary(ee.Algorithms.If(wcol.size().gt(0), wind_dict(), ee.Dictionary({})))
    rcol = chirps.filterDate(day.advance(-c['RAIN_DAYS'], 'day'), day)             # [day - N, day)
    rain = ee.Dictionary(ee.Algorithms.If(rcol.size().eq(c['RAIN_DAYS']),
        ee.Dictionary({'rain_mm': rcol.sum().reduceRegion(
            reducer=ee.Reducer.mean(), geometry=roi.bounds().buffer(c['RAIN_BUFFER']),
            scale=5566, bestEffort=True).get('precipitation')}), ee.Dictionary({})))
    return (img.set({'date': t0.format('YYYY-MM-dd'), 'month': t0.get('month'), 'year': t0.get('year'),
                     'rain_days': rcol.size()}).set(wind).set(rain))
def sector_filter(lo, hi):
    f = (ee.Filter.And if lo < hi else ee.Filter.Or)
    return f(ee.Filter.gte('wind_from', lo), ee.Filter.lt('wind_from', hi))
def tracer(rho, clear, swir, c=None):
    """Bands: X (index, valid obs only), sat (index saturated), swirrej (rejected by SWIR test),
    clearw (1 on every cloud-free water observation). Flags are 0/1 within clear water."""
    c = TR if c is None else c
    clearw = clear.And(water)
    swirrej = clearw.And(swir.gt(c['PIXEL_MAX_SWIR']))
    cand = clearw.And(swirrej.Not())
    sat = cand.And(rho.gte(c['TURB_C'] * 0.9))
    valid = cand.And(rho.gt(0)).And(sat.Not())
    x = rho.multiply(c['TURB_A']).divide(rho.divide(c['TURB_C']).multiply(-1).add(1)).updateMask(valid).rename('X')
    flags = ee.Image.cat([sat.rename('sat'), swirrej.rename('swirrej'), clearw.rename('clearw')]).updateMask(clearw)
    return x.toFloat().addBands(flags.toFloat())
def safe_stat(cc, band, name, c=None, reducer='median'):
    """Median (or mean) of `band` and its count; masked where count < MIN_SUPPORT; empty-collection safe."""
    c = TR if c is None else c
    has = cc.size().gt(0)
    red = cc.select(band).median() if reducer == 'median' else cc.select(band).mean()
    stat = ee.Image(ee.Algorithms.If(has, red, ee.Image.constant(0).updateMask(0))).rename(name)
    n = ee.Image(ee.Algorithms.If(has, cc.select(band).count(), ee.Image.constant(0))).rename('n_' + name).toFloat()
    return [stat.updateMask(n.gte(c['MIN_SUPPORT'])).toFloat(), n]
def conditions(col, c=None):
    c = TR if c is None else c
    out = [('all', col), ('dry', col.filter(in_months(c['DRY_MONTHS']))), ('wet', col.filter(in_months(c['WET_MONTHS'])))]
    out += [('wind_' + k, col.filter(sector_filter(*v))) for k, v in c['SECTORS'].items()]
    out += [('after_rain', col.filter(ee.Filter.gt('rain_mm', c['RAIN_WET_MM']))),
            ('no_rain', col.filter(ee.Filter.lt('rain_mm', c['RAIN_DRY_MM'])))]
    return out
def condition_stack(col, p, band, c=None, reducer='median'):
    c = TR if c is None else c
    bands = []
    for k, cc in conditions(col, c):
        bands += safe_stat(cc, band, f'{p}_{k}', c, reducer)
    return ee.Image.cat(bands)
def per_sensor_anomaly(col, sensors, p):
    """Anomaly A = X - p10 baseline of the same sensor; plume indicator per observation."""
    out, bases = None, []
    for s in sensors:
        cs = col.filter(ee.Filter.eq('sensor', s))
        base = ee.Image(ee.Algorithms.If(cs.size().gt(0), cs.select('X').reduce(ee.Reducer.percentile([10])),
                                         ee.Image.constant(0).updateMask(0))).rename('base')
        a = cs.map(lambda i: i.addBands(i.select('X').subtract(base).rename('A'))
                   .addBands(i.select('X').subtract(base).gt(TR['PLUME_DT']).unmask(0).Or(i.select('sat'))
                             .updateMask(i.select('clearw').And(i.select('swirrej').Not())).rename('plume').toFloat()))
        out = a if out is None else out.merge(a)
        bases.append(base.rename(f'{p}_baseline_p10_{s}').toFloat())
    return out, bases
def tracer_stack(col, sensors, p, c=None):
    c = TR if c is None else c
    anom, bases = per_sensor_anomaly(col, sensors, p)
    clear = col.select('clearw')
    stats = [col.select('X').median().rename(p + '_RTI_median_all').toFloat(),
             anom.select('plume').mean().rename(p + '_plume_freq').toFloat(),
             anom.select('plume').count().rename(p + '_n_plume_denominator').toFloat(),
             col.select('sat').mean().rename(p + '_saturated_frac').toFloat(),
             col.select('swirrej').mean().rename(p + '_swir_rejected_frac').toFloat(),
             clear.count().rename(p + '_n_clear_water').toFloat()]
    return ee.Image.cat(stats + bases + [condition_stack(anom, p + '_anom', 'A', c),
                                         condition_stack(anom, p + '_plumefreq', 'plume', c, reducer='mean')])
DATE_COLS = ['date', 'year', 'month', 'sensor', 'wind_speed', 'wind_from', 'rain_mm', 'rain_days', 'st_ref', 'st_ref_cover']
def export_dates(col, name):
    fc = col.map(lambda i: ee.Feature(None, i.toDictionary()))
    export_table(fc, 'transport', name, selectors=DATE_COLS)
    return name
S2_SENSORS = ['Sentinel-2A', 'Sentinel-2B', 'Sentinel-2C']
def s2_tracer(years, c=None):
    c = TR if c is None else c
    cs = ee.ImageCollection('GOOGLE/CLOUD_SCORE_PLUS/V1/S2_HARMONIZED')
    def f(img):
        return tracer(img.select('B4').divide(10000), img.select('cs_cdf').gte(c['CS_THRESHOLD']),
                      img.select('B11').divide(10000)).set(
            {'system:time_start': img.get('system:time_start'), 'sensor': img.get('SPACECRAFT_NAME')})
    return (ee.ImageCollection('COPERNICUS/S2_SR_HARMONIZED').filterBounds(roi).filter(years_filter(years))
            .filter(ee.Filter.lt('CLOUDY_PIXEL_PERCENTAGE', 80)).linkCollection(cs, ['cs_cdf']).map(f))
def hls_needs_scaling(coll, b='B4'):
    img = ee.Image(ee.ImageCollection(coll).filterBounds(roi).filter(ee.Filter.lt('CLOUD_COVERAGE', 30))
                   .sort('system:time_start', False).first())
    t = img.bandTypes().getInfo()[b]
    med = img.select(b).reduceRegion(reducer=ee.Reducer.median(), geometry=roi, scale=300,
                                     bestEffort=True).get(b).getInfo()
    scaled = t['precision'] == 'int' or (med is not None and med > 2)
    print(f'  {coll} {b}: type {t["precision"]}, AOI median {med} -> {"x0.0001" if scaled else "reflectance as is"}')
    return scaled
HLS_SENSORS = ['HLS_L30', 'HLS_S30']
def hls_tracer(years, c=None):
    c = TR if c is None else c
    def mk(coll, swir, sensor):
        scaled = hls_needs_scaling(coll)
        band = lambda img, b: img.select(b).toFloat().multiply(0.0001 if scaled else 1)
        def f(img):
            fm = img.select('Fmask')
            clear = (fm.bitwiseAnd(1 << 1).eq(0).And(fm.bitwiseAnd(1 << 2).eq(0)).And(fm.bitwiseAnd(1 << 3).eq(0))
                     .And(fm.rightShift(6).bitwiseAnd(3).lt(3)))
            return tracer(band(img, 'B4'), clear, band(img, swir)).set(
                {'system:time_start': img.get('system:time_start'), 'sensor': sensor})
        return (ee.ImageCollection(coll).filterBounds(roi).filter(years_filter(years))
                .filter(ee.Filter.lt('CLOUD_COVERAGE', 80)).map(f))
    return mk('NASA/HLS/HLSL30/v002', 'B6', 'HLS_L30').merge(mk('NASA/HLS/HLSS30/v002', 'B11', 'HLS_S30'))
LS = [dict(id='LANDSAT/LT05/C02/T1_L2', red='SR_B3', swir='SR_B5', st='ST_B6', name='L5'),
      dict(id='LANDSAT/LE07/C02/T1_L2', red='SR_B3', swir='SR_B5', st='ST_B6', name='L7'),
      dict(id='LANDSAT/LC08/C02/T1_L2', red='SR_B4', swir='SR_B6', st='ST_B10', name='L8'),
      dict(id='LANDSAT/LC09/C02/T1_L2', red='SR_B4', swir='SR_B6', st='ST_B10', name='L9')]
LS_SENSORS = [s['name'] for s in LS]
def ls_ok(img):   # QA_PIXEL bits 1 dilated cloud, 2 cirrus, 3 cloud, 4 shadow
    return img.select('QA_PIXEL').bitwiseAnd(0b11110).eq(0)
def ls_collection(s, years, c=None):
    c = TR if c is None else c
    col = (ee.ImageCollection(s['id']).filterBounds(roi).filter(years_filter(years))
           .filter(ee.Filter.lt('CLOUD_COVER', 80)))
    if s['name'] == 'L7' and not c['USE_L7_SLC_OFF']:
        col = col.filterDate('1999-01-01', '2003-05-31')
    return col
def landsat_tracer(years, c=None):
    c = TR if c is None else c
    out = None
    for s in LS:
        def f(img, s=s):
            sr = lambda b: img.select(b).multiply(0.0000275).add(-0.2)
            return tracer(sr(s['red']), ls_ok(img), sr(s['swir'])).set(
                {'system:time_start': img.get('system:time_start'), 'sensor': s['name']})
        col = ls_collection(s, years).map(f)
        out = col if out is None else out.merge(col)
    return out
def st_reference_geometry(c=None):
    c = TR if c is None else c
    if c['ST_REF_GEOJSON']:
        with open(c['ST_REF_GEOJSON']) as f: g = json.load(f)
        g = g['features'][0]['geometry'] if g.get('type') == 'FeatureCollection' else g.get('geometry', g)
        return ee.Geometry(g, None, False)
    return roi
def landsat_temperature(years, c=None):
    c = TR if c is None else c
    ref_geom = st_reference_geometry(c)
    n_ref = ee.Number(water.selfMask().rename('w').reduceRegion(
        reducer=ee.Reducer.count(), geometry=ref_geom, scale=200, maxPixels=1e9).get('w'))
    out = None
    for s in LS:
        def f(img, s=s):
            st_c = img.select(s['st']).multiply(0.00341802).add(149.0).subtract(273.15)
            unc = img.select('ST_QA').multiply(0.01); cdist = img.select('ST_CDIST').multiply(0.01)
            ok = (ls_ok(img).And(water).And(st_c.gte(c['ST_VALID_C'][0])).And(st_c.lte(c['ST_VALID_C'][1]))
                  .And(unc.lte(c['ST_MAX_UNC_K'])).And(cdist.gte(c['ST_MIN_CDIST_KM'])))
            st = st_c.updateMask(ok).rename('st')
            r = st.reduceRegion(reducer=ee.Reducer.median().combine(ee.Reducer.count(), None, True),
                                geometry=ref_geom, scale=200, maxPixels=1e9, tileScale=4)
            cover = ee.Number(r.get('st_count')).divide(n_ref.max(1))
            ref = r.get('st_median')
            return (st.subtract(ee.Image.constant(ee.Algorithms.If(ref, ref, 0))).rename('X').toFloat()
                    .set({'system:time_start': img.get('system:time_start'), 'sensor': s['name'],
                          'st_ref': ref, 'st_ref_cover': cover}))
        col = (ls_collection(s, years).map(f).filter(ee.Filter.notNull(['st_ref']))
               .filter(ee.Filter.gte('st_ref_cover', c['ST_REF_MIN_COVER'])))
        out = col if out is None else out.merge(col)
    return out
def support_summary(dates_df, c=None):
    """Images and distinct years per condition (from the exported date table)."""
    c = TR if c is None else c
    d = dates_df.copy(); rows = []
    sel = {'all': np.ones(len(d), bool), 'dry': d.month.between(*c['DRY_MONTHS']), 'wet': d.month.between(*c['WET_MONTHS']),
           'after_rain': d.rain_mm > c['RAIN_WET_MM'], 'no_rain': d.rain_mm < c['RAIN_DRY_MM']}
    for k, (lo, hi) in c['SECTORS'].items():
        sel['wind_' + k] = (d.wind_from >= lo) & (d.wind_from < hi) if lo < hi else (d.wind_from >= lo) | (d.wind_from < hi)
    for k, m in sel.items():
        m = np.asarray(m, bool)
        rows.append(dict(condition=k, images=int(m.sum()), dates=int(d.loc[m, 'date'].nunique()),
                         years=int(d.loc[m, 'year'].nunique()), sensors=','.join(sorted(d.loc[m, 'sensor'].dropna().unique()))))
    rows.append(dict(condition='missing_wind', images=int(d.wind_from.isna().sum())))
    rows.append(dict(condition='missing_rain', images=int(d.rain_mm.isna().sum())))
    return pd.DataFrame(rows)


def run(ctx=None, force=False):
    """Run this step. Same settings = same folder: finished exports and stages are re-used
    (force=True starts them again)."""
    global allstats, anomC, c, cc, colA, colC, colD, cur, cur_pts, cy, date_tables, e16, hy_all, hy_support, \
           hycom, n, nm, p, p0, p1, part, per, region, s_, supp_txt, t0, t1, tg, tr_names, vec, wind_pts, yrs
    ctx = bind(globals(), 'transport', ctx)
    ctx.force = force
    figure_style()
    c, P, tr_names, date_tables = TR, TR['PARTS'], [], {}
    hy_support = None
    if P['A']:
        print('Part A: recent tracer index (' + c['TURB_SOURCE'] + ')')
        colA = (s2_tracer(c['A_YEARS']) if c['TURB_SOURCE'] == 'S2' else hls_tracer(c['A_YEARS'])).map(add_weather)
        yrs = '_'.join(map(str, c['A_YEARS']))
        nm = f"{PREFIX}_{c['TURB_SOURCE']}_RTI_{yrs}"
        export_image(tracer_stack(colA, S2_SENSORS if c['TURB_SOURCE'] == 'S2' else HLS_SENSORS, c['TURB_SOURCE']),
                     'transport', nm, 20 if c['TURB_SOURCE'] == 'S2' else 30)
        tr_names.append(nm); date_tables['A'] = export_dates(colA, f"{PREFIX}_{c['TURB_SOURCE']}_RTI_dates_{yrs}")
    if P['C']:
        print('Part C: Landsat 5-9 tracer index')
        colC = landsat_tracer(c['C_YEARS']).map(add_weather)
        yrs = '_'.join(map(str, c['C_YEARS']))
        anomC, _ = per_sensor_anomaly(colC, LS_SENSORS, 'LS')
        per = []
        for p0, p1 in c['C_PERIODS']:
            cc, tg = anomC.filter(years_filter([p0, p1])), f'{p0}_{p1}'
            per += safe_stat(cc, 'X', 'RTI_median_' + tg) + safe_stat(cc.filter(in_months(c['WET_MONTHS'])), 'X', 'RTI_median_wet_' + tg)
            per += safe_stat(cc, 'plume', 'plume_freq_' + tg, reducer='mean')
        export_image(tracer_stack(colC, LS_SENSORS, 'LS'), 'transport', f'{PREFIX}_Landsat_RTI_{yrs}', 30)
        export_image(ee.Image.cat(per), 'transport', f'{PREFIX}_Landsat_RTI_by_period', 30)
        tr_names += [f'{PREFIX}_Landsat_RTI_{yrs}', f'{PREFIX}_Landsat_RTI_by_period']
        date_tables['C'] = export_dates(colC, f'{PREFIX}_Landsat_RTI_dates_{yrs}')
    if P['D']:
        print('Part D: Landsat water temperature')
        colD = landsat_temperature(c['D_YEARS']).map(add_weather)
        yrs = '_'.join(map(str, c['D_YEARS']))
        nm = f'{PREFIX}_Landsat_water_temperature_anomaly_{yrs}'
        export_image(condition_stack(colD, 'dT', 'X'), 'transport', nm, 30); tr_names.append(nm)
        date_tables['D'] = export_dates(colD, f'{PREFIX}_Landsat_temperature_dates_{yrs}')
    if P['B']:
        print('Part B: HYCOM currents + ERA5 wind')
        region = roi.bounds().buffer(c['CUR_BUFFER'])
        hy_all = ee.ImageCollection('HYCOM/sea_water_velocity')
        hy_support = ee.Dictionary({'first': ee.Image(hy_all.sort('system:time_start').first()).date().format('YYYY-MM-dd'),
                                    'last': ee.Image(hy_all.sort('system:time_start', False).first()).date().format('YYYY-MM-dd')}).getInfo()
        t0 = max(f"{c['CUR_YEARS'][0]}-01-01", hy_support['first'])
        t1 = min(f"{c['CUR_YEARS'][1] + 1}-01-01", (pd.Timestamp(hy_support['last']) + pd.Timedelta(days=1)).strftime('%Y-%m-%d'))
        hy_support.update(used_start=t0, used_end_exclusive=t1,
                          note='last requested year incomplete' if t1 < f"{c['CUR_YEARS'][1] + 1}-01-01" else '')
        print('  HYCOM support:', hy_support)
        hycom = (hy_all.filterDate(t0, t1).select(['velocity_u_0', 'velocity_v_0'], ['u', 'v'])
                 .map(lambda i: i.multiply(0.001).copyProperties(i, ['system:time_start'])))
        def vec(cc, tg):
            m = cc.mean(); u, v = m.select('u'), m.select('v')
            return ee.Image.cat([u.rename('u_' + tg), v.rename('v_' + tg), u.hypot(v).rename('spd_' + tg),
                                 dir_to(u, v).rename('dir_' + tg), cc.select('u').count().rename('n_' + tg)])
        allstats = lambda cc: ee.Image.cat([vec(cc, 'all'), vec(cc.filter(in_months(c['DRY_MONTHS'])), 'dry'),
                                            vec(cc.filter(in_months(c['WET_MONTHS'])), 'wet')])
        cur = allstats(hycom).addBands(hycom.map(lambda i: i.select('u').hypot(i.select('v')))
                                       .reduce(ee.Reducer.percentile([90])).rename('spd_p90'))
        cur_pts = cur.sample(region=region, projection=ee.Image(hy_all.first()).projection(),
                             scale=8905.6, geometries=True, dropNulls=True)
        e16 = era5_gee.filterDate(t0, t1).filter(ee.Filter.calendarRange(16, 16, 'hour'))
        wind_pts = allstats(e16).sample(region=region, projection=ee.Image(era5_gee.first()).projection(),
                                        scale=27830, geometries=True, dropNulls=True)
        cy = f'{t0[:10]}_{t1[:10]}'
        export_table(cur_pts, 'transport', f'{PREFIX}_HYCOM_surface_currents_{cy}', fmt='GeoJSON')
        export_table(wind_pts, 'transport', f'{PREFIX}_ERA5_wind_16UTC_{cy}', fmt='GeoJSON')
        tr_names += [f'{PREFIX}_HYCOM_surface_currents_{cy}', f'{PREFIX}_ERA5_wind_16UTC_{cy}']
        MANIFEST['coverage']['hycom'] = hy_support; save_manifest()

    supp_txt = ''
    if WAIT_FOR_EXPORTS:
        wait(tr_names + list(date_tables.values()), every=120)
        for n in tr_names: task_files(n)
        for part, n in date_tables.items():
            s_ = support_summary(read_task_csv(n)); s_.insert(0, 'part', part)
            p = drive_path('transport', f'{n}_condition_support.csv'); s_.to_csv(p, index=False); record_file(p)
            supp_txt += f'\n**Part {part}** (`{n}`):\n\n' + s_.to_markdown(index=False) + '\n'
        set_status('transport', 'complete')

    write_readme('transport', 'README_04_Transport_overview', f"""
    # Water-motion overview: observed tracer patterns and regional currents / wind

    ## Files
    - `{PREFIX}_{c['TURB_SOURCE']}_RTI_*` (Part A): relative tracer index from {'Sentinel-2 L2A (20 m)' if c['TURB_SOURCE'] == 'S2' else 'HLS v2.0, Landsat 8/9 + Sentinel-2 harmonised (30 m)'}, {c['A_YEARS']}.
    - `{PREFIX}_Landsat_RTI_*`, `{PREFIX}_Landsat_RTI_by_period` (Part C, 30 m): Landsat 5/7/8/9, {c['C_YEARS']}; per period {c['C_PERIODS']} (each statistic with its `n_` count band).
    - `{PREFIX}_Landsat_water_temperature_anomaly_*` (Part D, 30 m resampled from 60–120 m thermal).
    - `*_dates_*.csv`: per image date, sensor, wind speed / direction (from), rain (+ days available), thermal reference value and cover.
    - `*_condition_support.csv`: images, distinct dates, years and sensors per condition; missing wind / rain counts.
    - `{PREFIX}_HYCOM_surface_currents_*.geojson`, `{PREFIX}_ERA5_wind_16UTC_*.geojson` (Part B): points with u, v, speed, direction (TO) and counts for all / dry / wet months.

    ## Bands
    - `*_RTI_median_all`: median relative tracer index (unitless; **not FNU**).
    - `*_baseline_p10_<sensor>`: per-pixel 10th percentile per sensor (static bottom + sensor offset).
    - `*_plume_freq`: share of clear, SWIR-accepted water observations that are plumes (anomaly > {c['PLUME_DT']} **or saturated**); `*_n_plume_denominator` = its denominator.
    - `*_saturated_frac`, `*_swir_rejected_frac`: shares of cloud-free water observations saturated (ρ ≥ 0.9·C, counted as plumes) or rejected by the SWIR test (> {c['PIXEL_MAX_SWIR']}); `*_n_clear_water`: cloud-free water observations.
    - `*_anom_<cond>` median anomaly and `*_plumefreq_<cond>` plume frequency per condition (all, dry, wet, wind sectors {list(c['SECTORS'])}, after_rain, no_rain), each with `n_*`; masked where n < {c['MIN_SUPPORT']}.
    - Temperature `dT_<cond>`: surface temperature minus the median of the fixed reference area (°C), with `n_dT_<cond>`.

    ## Method
    - Index T = A·ρ/(1 − ρ/C) on red surface reflectance (A = {c['TURB_A']}, C = {c['TURB_C']}; Dogliotti et al. 2015 form, not locally calibrated).
    - Masks: clouds (Cloud Score+ / HLS Fmask / Landsat QA_PIXEL), water (Copernicus DEM water mask), glint (SWIR1 > {c['PIXEL_MAX_SWIR']}, recorded as rejection).
    - Per-sensor baselines; plume = anomaly > {c['PLUME_DT']} or saturation.
    - Conditions: wind = ERA5 10 m (GEE `ECMWF/ERA5/HOURLY`), mean of the 24 h before the image at the AOI centre, sectors by direction FROM {c['SECTORS']}; rain = CHIRPS sum over the {c['RAIN_DAYS']} whole days before the acquisition day ([day − {c['RAIN_DAYS']} d, day)), AOI + {c['RAIN_BUFFER']/1000:.0f} km (after rain > {c['RAIN_WET_MM']} mm, no rain < {c['RAIN_DRY_MM']} mm); dry months {c['DRY_MONTHS']}, wet months {c['WET_MONTHS']}.
    - Temperature: Landsat ST with ST_QA ≤ {c['ST_MAX_UNC_K']} K and ST_CDIST ≥ {c['ST_MIN_CDIST_KM']} km; reference = {'polygon ' + str(c['ST_REF_GEOJSON']) if c['ST_REF_GEOJSON'] else 'all AOI water'} (fixed), image used only if ≥ {c['ST_REF_MIN_COVER']:.0%} of it is clear.
    - Currents: HYCOM surface velocity (0.08°, daily); **actual support** {json.dumps(hy_support) if hy_support else 'n/a'}. Wind: ERA5 at 16 UTC.

    ## Support per condition
    {supp_txt or 'Run with WAIT_FOR_EXPORTS = True to tabulate.'}

    ## Limitations
    - **Tracer patterns, not measured currents; relative index, not calibrated turbidity.** Surface reflectance from land-oriented atmospheric corrections; changing atmosphere, glint, bottom signal and sensor response are only partly removed by per-sensor baselines. Do not interpret decadal differences as trends without cross-sensor calibration and comparable seasonal sampling.
    - Fixed overpass times → tidal phase not resolved. Landsat 7 after 2003 has gap stripes.
    - HYCOM (~9 km, no tides) and ERA5 (~28 km): regional context only.

    ## Sources
    NASA HLS v2.0 (Masek et al. 2021; doi:10.5067/HLS/HLSL30.002, 10.5067/HLS/HLSS30.002); Landsat Collection 2 L2 (USGS);
    Copernicus Sentinel-2 (ESA); Cloud Score+; CHIRPS (Funk et al. 2015); ERA5 (Hersbach et al. 2020); HYCOM (Cummings & Smedstad 2013);
    Dogliotti et al. (2015) RSE 156:157–168; Nechad et al. (2009).
    """)
    return ctx
