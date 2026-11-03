"""Pre-screening — which months suit a Sentinel-2 composite for bathymetry?

Before choosing the composite months, this step looks at several years of the conditions that spoil seabed
colour, day by day:

| Variable | Source | Value used for day *d* (overpass time `OVERPASS_UTC`) |
|---|---|---|
| waves | ERA5 + Copernicus Marine (waves step; `SCREEN_SOURCE`) | max Hs over the `WAVE_WINDOW_H` hours before the overpass |
| wind | ERA5 10 m wind (waves step) | mean speed over the `WIND_WINDOW_H` hours before |
| rain (ERA5) | ERA5 total precipitation at the point (waves step) | sum over the `RAIN_DAYS` whole days before *d* |
| rain (CHIRPS) | CHIRPS daily, mean over AOI + `RAIN_BUFFER` (Earth Engine) | same window |
| clear sky, glint, turbidity | Sentinel-2 (Cloud Score+) and Landsat 5–9 (QA) scenes over AOI water (Earth Engine) | per scene: share of clear water, share with SWIR glint, median red reflectance of clear water |
| ocean-colour transparency | Copernicus Marine OLCI transparency (SPM, ZSD, KD490) | daily median over the AOI |

**Good day.** A day is *good* for the sea state when waves, wind and rain are all at or below their own
**site percentile** `PCTL` (computed over all months of all years), and never above the absolute `ABS_CAPS`.
A Sentinel-2 scene is **usable** when the day is good, at least `CLEAR_MIN` of AOI water is cloud-free, and
its turbidity (red reflectance of clear water) is at or below the Sentinel-2 percentile.

**Suggestion.** For every window of `WINDOW_LENGTHS` consecutive months, the step counts the usable Sentinel-2
images per season (one season = one year) and ranks windows by the mean count (then by a smaller year-to-year
spread). You choose the months yourself and write them into `s2.MONTHS`; Module 1 then removes the bad dates
inside the window.

**Caveats.** Percentile thresholds are relative to this site: "calm" means calm for here. Turbidity from red
surface reflectance is a relative index, compared within one sensor family only. Copernicus Marine ocean colour is
4 km (global) / 300 m (Med): it describes offshore plumes, not the lagoon. Scene counts depend on the relative orbit
(`ORBIT`): use the same orbit as the Sentinel-2 composite.
"""
import os, json, datetime as dt
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from .core import (bind, manifest, save_manifest, stage_done, stage_get, set_status, require, drive_path, export_table,
                   wait, read_task_csv, record_file, write_readme, OKABE_ITO, panel_labels, save_fig, empty_panel,
                   figure_style, aoi_bbox_wgs84, secret)
from .waves import load_series
try:
    import ee
except ImportError:
    ee = None

# set by bind()
CTX = P = S2 = W = CRS = PREFIX = roi = water = chirps = WAIT_FOR_EXPORTS = MANIFEST = None
MONTHS = list('JFMAMJJASOND')
MON3 = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
VARS = ['hs', 'wind', 'rain_era5', 'rain_chirps']
LABELS = {'hs': 'waves $H_s$', 'wind': 'wind', 'rain_era5': 'rain ERA5', 'rain_chirps': 'rain CHIRPS',
          'turb_S2': 'turbidity S2', 'turb_LANDSAT': 'turbidity Landsat', 'cloud_S2': 'cloud S2',
          'cloud_LANDSAT': 'cloud Landsat'}


# ------------------------------------------------------------------ Earth Engine scene statistics
def _scene_feature(img, red, nir, swir, clear, sensor):
    w = water.rename('w')
    cw = w.And(clear)
    glint = cw.And(swir.gt(P['PIXEL_MAX_SWIR']))
    good = cw.And(glint.Not())
    counts = ee.Image.cat([w, cw.rename('c'), glint.rename('g')]).unmask(0).reduceRegion(
        reducer=ee.Reducer.sum(), geometry=roi, scale=P['STAT_SCALE'], maxPixels=1e10, tileScale=4)
    med = ee.Image.cat([red.rename('red'), nir.rename('nir')]).updateMask(good).reduceRegion(
        reducer=ee.Reducer.median(), geometry=roi, scale=P['STAT_SCALE'], maxPixels=1e10, tileScale=4)
    return ee.Feature(None, {'time_ms': img.get('system:time_start'), 'sensor': sensor, 'n_water': counts.get('w'),
                             'n_clear': counts.get('c'), 'n_glint': counts.get('g'), 'red': med.get('red'),
                             'nir': med.get('nir')})

SCENE_COLS = ['time_ms', 'sensor', 'n_water', 'n_clear', 'n_glint', 'red', 'nir']

def s2_scenes():
    y = P['YEARS']
    col = (ee.ImageCollection('COPERNICUS/S2_SR_HARMONIZED').filterBounds(roi)
           .filterDate(f'{y[0]}-01-01', f'{y[1] + 1}-01-01'))          # no cloud pre-filter: clear-sky statistics
    if P['ORBIT'] is not None:
        col = col.filter(ee.Filter.eq('SENSING_ORBIT_NUMBER', P['ORBIT']))
    col = col.linkCollection(ee.ImageCollection('GOOGLE/CLOUD_SCORE_PLUS/V1/S2_HARMONIZED'), ['cs_cdf'])
    def f(img):
        b = lambda n: img.select(n).divide(10000)
        return _scene_feature(img, b('B4'), b('B8'), b('B11'), img.select('cs_cdf').gte(P['CS_THRESHOLD']), 'S2')
    return ee.FeatureCollection(col.map(f))

LS = [('LANDSAT/LT05/C02/T1_L2', 'SR_B3', 'SR_B4', 'SR_B5', 'L5'), ('LANDSAT/LE07/C02/T1_L2', 'SR_B3', 'SR_B4', 'SR_B5', 'L7'),
      ('LANDSAT/LC08/C02/T1_L2', 'SR_B4', 'SR_B5', 'SR_B6', 'L8'), ('LANDSAT/LC09/C02/T1_L2', 'SR_B4', 'SR_B5', 'SR_B6', 'L9')]

def landsat_scenes():
    y = P['LANDSAT_YEARS']; out = None
    for cid, r, n, s, name in LS:
        def f(img, r=r, n=n, s=s, name=name):
            sr = lambda b: img.select(b).multiply(0.0000275).add(-0.2)
            clear = img.select('QA_PIXEL').bitwiseAnd(0b11110).eq(0)
            return _scene_feature(img, sr(r), sr(n), sr(s), clear, name)
        c = (ee.ImageCollection(cid).filterBounds(roi).filterDate(f'{y[0]}-01-01', f'{y[1] + 1}-01-01').map(f))
        out = c if out is None else out.merge(c)
    return ee.FeatureCollection(out)

def hls_scenes():
    y = P['YEARS']; out = None
    for cid, swir, name in (('NASA/HLS/HLSL30/v002', 'B6', 'HLS_L30'), ('NASA/HLS/HLSS30/v002', 'B11', 'HLS_S30')):
        def f(img, swir=swir, name=name):
            fm = img.select('Fmask')
            clear = fm.bitwiseAnd(0b1110).eq(0)
            return _scene_feature(img, img.select('B4'), img.select('B5' if name == 'HLS_L30' else 'B8A'), img.select(swir), clear, name)
        c = ee.ImageCollection(cid).filterBounds(roi).filterDate(f'{y[0]}-01-01', f'{y[1] + 1}-01-01').map(f)
        out = c if out is None else out.merge(c)
    return ee.FeatureCollection(out)

def chirps_daily():
    y = P['YEARS']; region = roi.bounds().buffer(P['RAIN_BUFFER'])
    col = chirps.filterDate(f'{y[0]}-01-01', f'{y[1] + 1}-01-01')
    return ee.FeatureCollection(col.map(lambda i: ee.Feature(None, {
        'time_ms': i.get('system:time_start'),
        'rain': i.reduceRegion(reducer=ee.Reducer.mean(), geometry=region, scale=5566, maxPixels=1e9).get('precipitation')})))


# ------------------------------------------------------------------ Copernicus Marine ocean colour
def ocean_colour_daily():
    """Daily AOI median (and valid share) of each transparency variable; None if unavailable."""
    import copernicusmarine as cm
    spec = P['OC_DATASETS'][W['REGION']]
    x0, y0, x1, y1 = aoi_bbox_wgs84(); b = P['OC_BUFFER_DEG']
    y = P['YEARS']; frames = []
    for v in spec['variables']:
        try:
            ds = cm.open_dataset(dataset_id=spec['id'], variables=[v], minimum_longitude=x0 - b, maximum_longitude=x1 + b,
                                 minimum_latitude=y0 - b, maximum_latitude=y1 + b, start_datetime=f'{y[0]}-01-01',
                                 end_datetime=f'{y[1]}-12-31', username=secret('CMEMS_USERNAME', purpose='Copernicus Marine'),
                                 password=secret('CMEMS_PASSWORD', purpose='Copernicus Marine'))
        except Exception as e:
            print(f'  ocean colour {spec["id"]} {v}: not available ({str(e)[:120]})'); continue
        da = ds[v]; sp = [d for d in da.dims if d != 'time']
        med = da.median(sp, skipna=True).load().to_series()
        frac = da.notnull().mean(sp).load().to_series()
        frames.append(pd.DataFrame({f'oc_{v}': med, f'oc_{v}_valid': frac}))
        print(f'  ocean colour {v}: {int(med.notna().sum()):,} days with data')
    if not frames: return None
    out = pd.concat(frames, axis=1)
    out.index = pd.to_datetime(out.index).tz_localize(None).normalize(); out.index.name = 'date'
    return out


# ------------------------------------------------------------------ daily table
def _hourly(df, col):
    s = df.set_index('time')[col].dropna().sort_index()
    return s[~s.index.duplicated()]

def daily_metocean(series, chirps_df, days):
    """One row per day: hs, wind, rain_era5, rain_chirps at the typical overpass time."""
    t = days + pd.to_timedelta(P['OVERPASS_UTC'], unit='h')
    t = t.tz_localize('UTC')
    out = pd.DataFrame(index=days)
    srcs = {'cmems': ['cmems'], 'era5': ['era5'], 'max': ['era5', 'cmems']}[W['SCREEN_SOURCE']]
    hs = []
    for s in srcs:
        if s in series:
            r = _hourly(series[s], 'hs').rolling(f"{P['WAVE_WINDOW_H']}h").max()
            hs.append(r.reindex(t, method='ffill', tolerance=pd.Timedelta(hours=3)).values)
    out['hs'] = np.nanmax(np.vstack(hs), axis=0) if hs else np.nan
    e = series.get('era5')
    if e is not None and 'wind_speed' in e:
        r = _hourly(e, 'wind_speed').rolling(f"{P['WIND_WINDOW_H']}h").mean()
        out['wind'] = r.reindex(t, method='ffill', tolerance=pd.Timedelta(hours=2)).values
    else:
        out['wind'] = np.nan
    n = P['RAIN_DAYS']
    if e is not None and 'rain_mm' in e:
        d = _hourly(e, 'rain_mm').resample('1D').sum(min_count=20)
        d.index = d.index.tz_localize(None)
        out['rain_era5'] = d.rolling(n, min_periods=n).sum().shift(1).reindex(days).values    # [d-N, d)
    else:
        out['rain_era5'] = np.nan
    if chirps_df is not None and len(chirps_df):
        c = chirps_df.set_index('date')['rain'].sort_index()
        c = c.reindex(pd.date_range(c.index.min(), c.index.max(), freq='D'))
        out['rain_chirps'] = c.rolling(n, min_periods=n).sum().shift(1).reindex(days).values
    else:
        out['rain_chirps'] = np.nan
    return out

def thresholds(daily):
    th = {}
    for v in VARS:
        x = daily[v].dropna()
        if not len(x): continue
        q = float(np.percentile(x, P['PCTL'].get(v, 50)))
        cap = (P['ABS_CAPS'] or {}).get(v)
        th[v] = dict(percentile=P['PCTL'].get(v, 50), value=q, cap=cap, used=min(q, cap) if cap is not None else q)
    return th

def good_days(daily, th):
    need = [v for v in ('hs', 'wind', 'rain_era5') if v in th]
    ok = pd.Series(True, index=daily.index); avail = pd.Series(True, index=daily.index)
    for v in VARS:
        if v not in th: continue
        x = daily[v]
        if v in need: avail &= x.notna()
        ok &= ~(x > th[v]['used'])           # NaN never fails, but required variables must exist (avail)
    return (ok & avail).astype(float).where(avail)     # 1 good, 0 not, NaN where a required variable is missing

def scenes_by_date(sc):
    """Combine tiles of the same date and sensor family."""
    sc = sc.copy()
    sc['family'] = np.where(sc.sensor.str.startswith('L'), 'LANDSAT', np.where(sc.sensor.str.startswith('HLS'), 'HLS', 'S2'))
    sc['date'] = pd.to_datetime(sc.time_ms, unit='ms').dt.normalize()
    for k in ('n_water', 'n_clear', 'n_glint', 'red', 'nir'): sc[k] = pd.to_numeric(sc[k], errors='coerce')
    sc['w_red'] = sc.red * sc.n_clear
    g = sc.groupby(['family', 'date']).agg(n_water=('n_water', 'sum'), n_clear=('n_clear', 'sum'), n_glint=('n_glint', 'sum'),
                                           w_red=('w_red', 'sum'), sensors=('sensor', lambda s: ','.join(sorted(set(s))))).reset_index()
    g['clear_frac'] = g.n_clear / g.n_water.replace(0, np.nan)
    g['glint_frac'] = g.n_glint / g.n_clear.replace(0, np.nan)
    g['turb'] = g.w_red / g.n_clear.replace(0, np.nan)
    return g.drop(columns='w_red')


# ------------------------------------------------------------------ months and windows
def window_months(start, length):
    return [((start - 1 + i) % 12) + 1 for i in range(length)]

def season_year(d, start):
    """Season label = calendar year in which the window starts (Dec-Feb of 2024/25 -> 2024)."""
    return d.year - (d.month < start).astype(int)

def rank_windows(usable, daily_good, years):
    """usable: DataFrame of usable S2 dates. Returns all windows with per-season statistics."""
    rows = []
    for L in P['WINDOW_LENGTHS']:
        for start in range(1, 13):
            ms = window_months(start, L)
            u = usable[usable.date.dt.month.isin(ms)]
            sy = season_year(u.date.dt, start) if len(u) else pd.Series(dtype=int)
            seasons = []
            for yy in range(years[0], years[1] + 1):          # complete seasons only
                end_m = start + L - 1; ey, em = yy + (end_m - 1) // 12, (end_m - 1) % 12 + 1
                if pd.Timestamp(ey, em, 1) + pd.offsets.MonthEnd(0) <= pd.Timestamp(CTX.today): seasons.append(yy)
            counts = pd.Series(0, index=seasons, dtype=float)
            if len(u):
                vc = sy.value_counts(); counts = counts.add(vc.reindex(seasons).fillna(0), fill_value=0)
            dg = daily_good[daily_good.index.month.isin(ms)]
            rows.append(dict(length=L, start=start, label=f'{MON3[ms[0] - 1]}–{MON3[ms[-1] - 1]}',
                             month_list=ms, seasons=len(counts), usable_mean=float(counts.mean()) if len(counts) else np.nan,
                             usable_std=float(counts.std()) if len(counts) > 1 else np.nan,
                             usable_min=float(counts.min()) if len(counts) else np.nan,
                             usable_max=float(counts.max()) if len(counts) else np.nan,
                             p_good_day=float(dg.mean()) if dg.notna().any() else np.nan))
    w = pd.DataFrame(rows)
    w['usable_per_month'] = w.usable_mean / w.length          # compares windows of different length
    w['rank_in_length'] = w.groupby('length')['usable_mean'].rank(ascending=False, method='first')
    return w.sort_values(['length', 'usable_mean', 'usable_std'], ascending=[True, False, True]).reset_index(drop=True)


# ------------------------------------------------------------------ run
def run(ctx=None, force=False):
    """Run the pre-screening. Needs the waves step (with ERA5 wind + rain) for the same settings."""
    global DAILY, SCENES, MONTHLY, WINDOWS, THRESHOLDS
    ctx = bind(globals(), 'prescreen', ctx)
    ctx.force = force
    figure_style()
    series = load_series(required=True)
    if 'era5' in series and 'rain_mm' not in series['era5']:
        print('  NOTE: the ERA5 series has no rain (waves.ERA5_WIND false?): ERA5 rain not used')
    y = P['YEARS']

    # ---- Earth Engine tables (scene statistics, CHIRPS), exported once per settings
    tables = {'CHIRPS': (chirps_daily, ['time_ms', 'rain'])}
    builders = {'S2': s2_scenes, 'LANDSAT': landsat_scenes, 'HLS': hls_scenes}
    for s in P['SENSORS']:
        tables[s] = (builders[s], SCENE_COLS)
    names = {}
    for k, (fn, cols) in tables.items():
        nm = f'{PREFIX}_prescreen_{k}_{y[0]}_{y[1] if k != "LANDSAT" else P["LANDSAT_YEARS"][1]}'
        export_table(fn(), 'prescreen', nm, selectors=cols); names[k] = nm
    if not WAIT_FOR_EXPORTS:
        print('WAIT_FOR_EXPORTS is false: run this step again when the exports are COMPLETED'); return ctx
    wait(list(names.values()), every=60)
    ch = read_task_csv(names['CHIRPS']); ch['date'] = pd.to_datetime(ch.time_ms, unit='ms').dt.normalize()
    SCENES = scenes_by_date(pd.concat([read_task_csv(names[s]) for s in P['SENSORS']], ignore_index=True))

    # ---- daily table
    days = pd.date_range(f'{y[0]}-01-01', min(pd.Timestamp(f'{y[1]}-12-31'), pd.Timestamp(ctx.today) - pd.Timedelta(days=1)), freq='D')
    DAILY = daily_metocean(series, ch[['date', 'rain']], days)
    if P['OCEAN_COLOUR']:
        oc = ocean_colour_daily()
        if oc is not None: DAILY = DAILY.join(oc, how='left')
    DAILY.index.name = 'date'
    THRESHOLDS = th = thresholds(DAILY)
    DAILY['good_day'] = good_days(DAILY, th)
    print('  thresholds (site percentile, cap, used):', {k: (round(v['value'], 2), v['cap'], round(v['used'], 2)) for k, v in th.items()})
    print(f"  good days: {DAILY.good_day.mean():.0%} of {int(DAILY.good_day.notna().sum()):,} days with data")

    # ---- scenes: turbidity percentile per sensor family (all months), usable S2 images
    SCENES['turb_rank'] = SCENES.groupby('family')['turb'].rank(pct=True) * 100
    turb_q = SCENES.groupby('family')['turb'].quantile(P['PCTL'].get('turbidity', 50) / 100).to_dict()
    SCENES['turb_ok'] = SCENES.apply(lambda r: (r.turb <= turb_q.get(r.family, np.inf)) if pd.notna(r.turb) else False, axis=1)
    SCENES['clear_ok'] = SCENES.clear_frac >= P['CLEAR_MIN']
    SCENES = SCENES.merge(DAILY[['good_day']], left_on='date', right_index=True, how='left')
    SCENES['usable'] = SCENES.clear_ok & SCENES.turb_ok & (SCENES.good_day == 1)
    s2 = SCENES[SCENES.family == 'S2']

    # ---- monthly table
    D = DAILY.copy(); D['month'] = D.index.month; D['year'] = D.index.year
    M = pd.DataFrame(index=pd.Index(range(1, 13), name='month'))
    for v in VARS:
        if D[v].notna().any():
            rk = D[v].rank(pct=True) * 100
            M[f'{v}_median'] = D.groupby('month')[v].median(); M[f'{v}_rank'] = rk.groupby(D.month).median()
    M['p_good_day'] = D.groupby('month')['good_day'].mean()
    M['p_good_day_std'] = D.groupby(['year', 'month'])['good_day'].mean().groupby('month').std()
    for fam in SCENES.family.unique():
        S = SCENES[SCENES.family == fam]
        M[f'p_clear_{fam}'] = S.groupby(S.date.dt.month)['clear_ok'].mean()
        M[f'turb_rank_{fam}'] = S.groupby(S.date.dt.month)['turb_rank'].median()
        M[f'scenes_per_year_{fam}'] = S.groupby([S.date.dt.year, S.date.dt.month]).size().groupby(level=1).mean()
    if len(s2):
        u = s2[s2.usable].groupby([s2.date.dt.year, s2.date.dt.month]).size().unstack(fill_value=0)
        u = u.reindex(columns=range(1, 13), fill_value=0)
        M['usable_S2_per_year'] = u.mean(); M['usable_S2_std'] = u.std()
        M['usable_S2_min'] = u.min(); M['usable_S2_max'] = u.max()
    for c in [c for c in DAILY.columns if c.startswith('oc_') and not c.endswith('_valid')]:
        M[f'{c}_median'] = D.groupby('month')[c].median()
    MONTHLY = M
    WINDOWS = rank_windows(s2[s2.usable][['date']], DAILY['good_day'], (max(y[0], 2017), y[1]))
    cur = WINDOWS[(WINDOWS.length == (P['COMPARE_MONTHS'][1] - P['COMPARE_MONTHS'][0]) % 12 + 1) & (WINDOWS.start == P['COMPARE_MONTHS'][0])]

    # ---- files
    for df, nm, idx in ((DAILY, 'daily_conditions', True), (SCENES, 'scenes_by_date', False), (MONTHLY, 'monthly_summary', True),
                        (WINDOWS, 'window_ranking', False)):
        p = drive_path('prescreen', f'{PREFIX}_prescreen_{nm}.csv'); df.to_csv(p, index=idx); record_file(p)
    top = WINDOWS[WINDOWS.rank_in_length <= P['TOP_N']]
    print('\nBest windows (usable Sentinel-2 images per season: mean ± std (min–max); per month):')
    for L, g in top.groupby('length'):
        print(f'  {L} months: ' + ' | '.join(f"{r.label}: {r.usable_mean:.1f} ± {r.usable_std:.1f} ({r.usable_min:.0f}–{r.usable_max:.0f}); {r.usable_per_month:.1f}/mo"
                                             for r in g.itertuples()))
    if len(cur):
        r = cur.iloc[0]; print(f"  months to compare (COMPARE_MONTHS) {P['COMPARE_MONTHS']}: {r.usable_mean:.1f} ± {r.usable_std:.1f}")

    # ---- figure 1: calendar of good days, month x variable ranks
    fig = plt.figure(figsize=(7.2, 7.0))
    gs = fig.add_gridspec(2, 1, height_ratios=[1.1, 1], hspace=0.35)
    ax = fig.add_subplot(gs[0])
    G = D.pivot_table(index='year', columns=D.index.dayofyear, values='good_day', aggfunc='first')
    from matplotlib.colors import ListedColormap
    im = ax.imshow(G.values, aspect='auto', cmap=ListedColormap([OKABE_ITO[3], OKABE_ITO[2]]), vmin=0, vmax=1,
                   interpolation='nearest', extent=[0.5, G.shape[1] + 0.5, G.index.max() + 0.5, G.index.min() - 0.5])
    ax.set_facecolor('0.85')
    starts = pd.date_range('2001-01-01', periods=12, freq='MS').dayofyear
    ax.set_xticks(starts + 14); ax.set_xticklabels(MONTHS); ax.grid(False)
    ax.set_ylabel('year'); ax.set_title(f'Good sea-state days (green; red = not; grey = no data), overpass {P["OVERPASS_UTC"]:g} UTC', loc='left')
    ax2 = fig.add_subplot(gs[1])
    rows, labs = [], []
    for v in VARS:
        if f'{v}_rank' in M: rows.append(M[f'{v}_rank'].values); labs.append(LABELS[v])
    for fam in sorted(SCENES.family.unique()):
        if f'turb_rank_{fam}' in M: rows.append(M[f'turb_rank_{fam}'].values); labs.append(f'turbidity {fam}')
        if f'p_clear_{fam}' in M: rows.append(100 - 100 * M[f'p_clear_{fam}'].values); labs.append(f'cloudy scenes {fam} (%)')
    for c in [c for c in M.columns if c.startswith('oc_') and c.endswith('_median')]:
        rows.append(M[c].rank(pct=True).values * 100); labs.append(c[3:-7] + ' (ocean colour, rank)')
    if rows:
        hm = ax2.imshow(np.vstack(rows), aspect='auto', cmap='cividis', vmin=0, vmax=100)
        ax2.set_yticks(range(len(labs))); ax2.set_yticklabels(labs, fontsize=7); ax2.set_xticks(range(12)); ax2.set_xticklabels(MONTHS)
        ax2.grid(False); fig.colorbar(hm, ax=ax2, label='monthly median rank / % (low = favourable)', shrink=0.9)
        ms = P['COMPARE_MONTHS']
        if ms[1] >= ms[0]: ax2.axvspan(ms[0] - 1.5, ms[1] - 0.5, fill=False, ec=OKABE_ITO[1], lw=1.5)
    ax2.set_title('Conditions by month (all years; box = months to compare (COMPARE_MONTHS))', loc='left')
    panel_labels([ax, ax2]); save_fig(fig, 'prescreen', f'{PREFIX}_Fig_prescreen_calendar_conditions'); plt.show()

    # ---- figure 2: usable images per month, probabilities, ranked windows
    fig, axs = plt.subplots(1, 3, figsize=(7.2, 2.9), constrained_layout=True, gridspec_kw=dict(width_ratios=[1, 1, 1.25]))
    x = np.arange(1, 13)
    if 'usable_S2_per_year' in M:
        axs[0].bar(x, M.usable_S2_per_year, color=OKABE_ITO[0], alpha=0.85)
        axs[0].errorbar(x, M.usable_S2_per_year, yerr=[M.usable_S2_per_year - M.usable_S2_min, M.usable_S2_max - M.usable_S2_per_year],
                        fmt='none', ecolor='k', lw=0.6, capsize=1.5)
    axs[0].set_xticks(x); axs[0].set_xticklabels(MONTHS); axs[0].set_ylabel('usable S2 images per year')
    axs[0].set_title('Usable Sentinel-2 images', loc='left')
    axs[1].plot(x, M.p_good_day * 100, '-o', ms=3, color=OKABE_ITO[2], label='good sea-state day')
    for i, fam in enumerate(sorted(SCENES.family.unique())):
        if f'p_clear_{fam}' in M: axs[1].plot(x, M[f'p_clear_{fam}'] * 100, '-s', ms=2.5, color=OKABE_ITO[4 + i], label=f'clear scene {fam}')
    axs[1].set_xticks(x); axs[1].set_xticklabels(MONTHS); axs[1].set_ylabel('%'); axs[1].set_ylim(0, 100)
    axs[1].legend(loc='lower left', fontsize=6.5); axs[1].set_title('Probabilities', loc='left')
    t3 = WINDOWS[WINDOWS.rank_in_length <= min(P['TOP_N'], 4)].copy()
    t3['lab'] = t3.label + ' (' + t3.length.astype(str) + ' mo)'
    cols = [OKABE_ITO[k % 8] for k in t3.length]
    axs[2].barh(range(len(t3)), t3.usable_mean, xerr=t3.usable_std.fillna(0), color=cols, alpha=0.85, error_kw=dict(lw=0.6))
    axs[2].set_yticks(range(len(t3))); axs[2].set_yticklabels(t3.lab, fontsize=6.5); axs[2].invert_yaxis()
    axs[2].set_xlabel('usable images per season'); axs[2].set_title('Best windows', loc='left')
    if len(cur):
        axs[2].axvline(cur.iloc[0].usable_mean, color='k', ls='--', lw=0.8, label=f"months to compare (COMPARE_MONTHS) ({cur.iloc[0].label})")
        axs[2].legend(fontsize=6.5, loc='lower right')
    panel_labels(axs, x=-0.18); save_fig(fig, 'prescreen', f'{PREFIX}_Fig_prescreen_usable_images_windows'); plt.show()

    best = {int(L): g.iloc[0].label for L, g in WINDOWS.groupby('length')}
    MANIFEST['outputs'] = dict(best_windows=best, thresholds=th, current_months=P['COMPARE_MONTHS'],
                               top=top[['length', 'label', 'month_list', 'usable_mean', 'usable_std', 'usable_min', 'usable_max', 'usable_per_month', 'p_good_day']].to_dict('records'))
    save_manifest()
    tbl = top[['length', 'label', 'usable_mean', 'usable_std', 'usable_min', 'usable_max', 'usable_per_month', 'p_good_day', 'seasons']].round(2).to_markdown(index=False)
    thr = pd.DataFrame(th).T.round(2).to_markdown()
    write_readme('prescreen', 'README_00b_Prescreen', f"""
    # Pre-screening: which months suit a Sentinel-2 composite?

    ## Suggestion (you decide; write your choice into the Sentinel-2 options, `MONTHS`)
    {tbl}

    Months compared (`COMPARE_MONTHS`) {P['COMPARE_MONTHS']}: {f"{cur.iloc[0].usable_mean:.1f} ± {cur.iloc[0].usable_std:.1f} usable images per season" if len(cur) else 'not a contiguous window'}.
    Usable = good sea-state day + ≥ {P['CLEAR_MIN']:.0%} of AOI water cloud-free + turbidity at or below the Sentinel-2 P{P['PCTL'].get('turbidity', 50)}.
    Sentinel-2 years {max(y[0], 2017)}–{y[1]}, relative orbit {P['ORBIT'] if P['ORBIT'] is not None else 'all'}.

    ## Thresholds (site percentiles over all months, capped)
    {thr}

    ## Files
    | File | Content |
    |---|---|
    | `{PREFIX}_prescreen_daily_conditions.csv` | per day: hs (max over {P['WAVE_WINDOW_H']} h), wind (mean over {P['WIND_WINDOW_H']} h), rain_era5 / rain_chirps ({P['RAIN_DAYS']} whole days before), ocean colour, good_day |
    | `{PREFIX}_prescreen_scenes_by_date.csv` | per sensor family and date: clear-water share, glint share, turbidity (median red of clear water), ranks, usable |
    | `{PREFIX}_prescreen_monthly_summary.csv` | per month: medians and ranks, probability of a good day, clear-scene probability, usable S2 images per year (mean, std, min, max) |
    | `{PREFIX}_prescreen_window_ranking.csv` | every window of {P['WINDOW_LENGTHS']} months: usable images per season (mean, std, min, max), good-day probability |
    | `{PREFIX}_Fig_prescreen_*.png/.pdf` | calendar of good days and month × variable heatmap; usable images per month, probabilities, best windows |

    ## Method
    - Waves: {W['SCREEN_SOURCE']} of ERA5 / Copernicus Marine ({W['REGION']}) at {W['POINT']}; wind and rain: ERA5 at the nearest cell; CHIRPS: mean over AOI + {P['RAIN_BUFFER'] / 1000:.0f} km.
    - Scenes: Sentinel-2 L2A (Cloud Score+ ≥ {P['CS_THRESHOLD']}), {', '.join(P['SENSORS'])}; glint = clear water with SWIR > {P['PIXEL_MAX_SWIR']}; statistics at {P['STAT_SCALE']} m over the Copernicus DEM water mask.
    - Ocean colour: {P['OC_DATASETS'][W['REGION']]['id'] if P['OCEAN_COLOUR'] else 'not used'} (daily AOI median, shown in the heatmap; not part of the usable count).

    ## Limitations
    - Percentiles are relative to the site; caps keep "calm" within Module 1's physical limits.
    - Turbidity from red surface reflectance is relative and compared only within a sensor family.
    - Past seasons are not a forecast; year-to-year spread (std, min–max) shows how reliable a window is.
    """)
    stage_done('prescreen', best=best)
    set_status('prescreen', 'complete', best_windows=best)
    return ctx
