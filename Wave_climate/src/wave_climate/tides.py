"""Step 2 — tide and storm surge from GTSM (Global Tide and Surge Model, Deltares) in the Climate Data Store.

Dataset `sis-water-level-change-timeseries-cmip6`:
- tide (TIDE_SOURCE='twl_minus_surge', default): reanalysis (GTSM forced by ERA5, 1950–2024) `total_water_level`
  minus `storm_surge_residual`, hourly, for TIDE_YEARS. By definition this is the astronomical tide plus the annual
  mean sea level, which is removed. The pure `tidal_elevation` exists only in the 'historical' experiment, as 10-min
  files up to 2014 (TIDE_SOURCE='tidal_elevation'; 6 times larger downloads);
- `storm_surge_residual`: reanalysis, `daily_maximum` values for SURGE_YEARS.

The files are GLOBAL (the service has no area option): each month is downloaded, the output point nearest to the
site is extracted, and the global file is deleted (KEEP_GLOBAL_FILES=False). Point series are cached.

From the tide, a harmonic analysis (UTide) gives the constituents; the tide is then predicted over PREDICT_YEARS
years (nodal cycle) to get the tidal levels: HAT, MHWS, MHHW, MHW, MSL, MLW, MLLW, MLWS, LAT, spring / neap ranges,
and representative spring, mean and neap tidal days for XBeach.

Vertical reference: GTSM mean sea level (1986–2005). Not chart datum and not the local land survey datum: shift by
the local offset before using the levels with a DEM or a survey.
"""
import os, io, zipfile, datetime as dt
import numpy as np
import pandas as pd
from .core import req_hash, km, save_csv, save_fig, figure_style, OKABE_ITO
from .options import check
from .download import cds_client

GTSM = 'sis-water-level-change-timeseries-cmip6'
TIDAL_DAY_H = 24.8412
SPRING_NEAP_D = 14.765


# ------------------------------------------------------------------------------------------------ GTSM download
def _coords(ds):
    """(station dim, lon array, lat array) of a GTSM file."""
    xn = next((v for v in list(ds.variables) if 'x_coord' in v or v in ('lon', 'longitude')), None)
    yn = next((v for v in list(ds.variables) if 'y_coord' in v or v in ('lat', 'latitude')), None)
    if xn is None or yn is None: raise ValueError(f'GTSM file: no station coordinates among {list(ds.variables)}')
    dim = ds[xn].dims[0]
    return dim, np.asarray(ds[xn].values, float), np.asarray(ds[yn].values, float)


def _point_from_file(path, lon, lat, max_km):
    import xarray as xr
    with xr.open_dataset(path) as ds:
        dim, x, y = _coords(ds)
        d = km(lon, lat, x, y)
        i = int(np.nanargmin(d))
        if d[i] > max_km:
            raise RuntimeError(f'Nearest GTSM output point is {d[i]:.0f} km from the site (> MAX_STATION_KM = {max_km})')
        tn = 'time' if 'time' in ds.dims else next(d_ for d_ in ds.dims if 'time' in d_)
        var = next(v for v in ds.data_vars if set(ds[v].dims) == {tn, dim})
        s = ds[var].isel({dim: i}).load().to_series()
    s.index = pd.to_datetime(s.index, utc=True)
    return s.astype(float), dict(station_index=i, station_lon=float(x[i]), station_lat=float(y[i]), distance_km=float(d[i]),
                                 variable_in_file=var)


def _retrieve(client, req, target, retries=3):
    import time
    for attempt in range(1, retries + 1):
        try:
            client.retrieve(GTSM, req, target); return
        except Exception as e:
            msg = str(e).lower()
            if 'cost' in msg or 'too large' in msg or 'limit' in msg: raise
            if attempt == retries: raise
            print(f'    attempt {attempt} failed ({str(e)[:120]}); retrying in {30 * attempt} s'); time.sleep(30 * attempt)


# What the CDS actually offers (constraints file, checked 2026-11-04):
#   reanalysis (ERA5-forced): storm_surge_residual, total_water_level; 10_min / hourly / daily_maximum; v2, v3; 1950-2024
#   historical: tidal_elevation only as 10_min, version v1, 1950-2014 (future: 2015-2050, same)
# so tidal_elevation is NOT in the reanalysis.
def check_request(experiment, variable, aggregation, version, years):
    ok = {('reanalysis', 'storm_surge_residual'), ('reanalysis', 'total_water_level'), ('historical', 'tidal_elevation')}
    if (experiment, variable) not in ok:
        raise ValueError(f'GTSM: {variable} is not offered for experiment {experiment!r}')
    if experiment == 'reanalysis' and (aggregation not in ('10_min', 'hourly', 'daily_maximum') or version not in ('v2', 'v3')
                                       or years[0] < 1950 or years[1] > 2024):
        raise ValueError(f'GTSM reanalysis: aggregation 10_min / hourly / daily_maximum, version v2 / v3, years 1950-2024 '
                         f'(asked: {aggregation}, {version}, {years})')
    if experiment == 'historical' and (aggregation != '10_min' or version != 'v1' or years[0] < 1950 or years[1] > 2014):
        raise ValueError(f'GTSM tidal_elevation: only 10_min, version v1, years 1950-2014 (asked: {aggregation}, {version}, {years})')


def gtsm_point(ctx, o, variable, aggregation, years, experiment='reanalysis', version=None):
    """Point series of one GTSM variable for whole years (cached per year), nearest output point."""
    version = version or o['GTSM_VERSION']
    check_request(experiment, variable, aggregation, version, years)
    cache = os.path.join(ctx.cache, 'gtsm'); os.makedirs(cache, exist_ok=True)
    client, parts, info = None, [], {}
    for y in range(years[0], years[1] + 1):
        req = {'variable': [variable], 'experiment': experiment, 'temporal_aggregation': [aggregation],
               'year': [str(y)], 'month': [f'{m:02d}' for m in range(1, 13)], 'version': [version]}
        key = req_hash(dict(r=req, lon=ctx.lon, lat=ctx.lat, k=o['MAX_STATION_KM']))
        f = os.path.join(cache, f'gtsm_{variable}_{aggregation}_{y}_{key}.csv')
        if os.path.exists(f):
            s = pd.read_csv(f, index_col=0, parse_dates=True).iloc[:, 0]; s.index = pd.to_datetime(s.index, utc=True)
            parts.append(s); continue
        client = client or cds_client()
        print(f'  GTSM {variable} ({aggregation}) {y}: requesting the global files ...')
        targets = []
        try:
            t = os.path.join(cache, f'_global_{key}.zip'); _retrieve(client, req, t); targets = [t]
        except Exception as e:                            # too large for one request: one month at a time
            print(f'    one request per month instead ({str(e)[:100]})')
            for m in range(1, 13):
                t = os.path.join(cache, f'_global_{key}_{m:02d}.zip'); _retrieve(client, dict(req, month=[f'{m:02d}']), t)
                targets.append(t)
        series = []
        for t in targets:
            files, tmp = [t], None
            if zipfile.is_zipfile(t):                 # extract to disk one file at a time (global files are large)
                tmp = t + '_x'; os.makedirs(tmp, exist_ok=True)
                with zipfile.ZipFile(t) as z:
                    files = []
                    for n in sorted(x for x in z.namelist() if x.endswith('.nc')):
                        files.append(z.extract(n, tmp))
            for fn in files:
                s, info = _point_from_file(fn, ctx.lon, ctx.lat, o['MAX_STATION_KM'])
                series.append(s)
                if tmp and not o['KEEP_GLOBAL_FILES']: os.remove(fn)
            if not o['KEEP_GLOBAL_FILES']:
                os.remove(t)
                if tmp: import shutil; shutil.rmtree(tmp, ignore_errors=True)
        s = pd.concat(series).sort_index(); s = s[~s.index.duplicated()]
        s.name = variable
        s.to_csv(f + '.tmp'); os.replace(f + '.tmp', f)
        ctx.note(f'gtsm_{variable}_{aggregation}', dict(dataset=GTSM, experiment=experiment, aggregation=aggregation,
                                                        version=version, **info))
        print(f"    {len(s):,} values at the GTSM point {info['station_lon']:.3f}, {info['station_lat']:.3f} ({info['distance_km']:.1f} km)")
        parts.append(s)
    s = pd.concat(parts).sort_index()
    return s[~s.index.duplicated()]


# ------------------------------------------------------------------------------------------------ harmonic analysis
def harmonic(tide, lat):
    """UTide harmonic analysis of the GTSM tide. Returns (coef, constituent table)."""
    import utide
    s = tide.dropna()
    t = s.index.tz_convert(None).values.astype('datetime64[ns]')
    coef = utide.solve(t, s.values, lat=lat, method='ols', conf_int='none', trend=False, verbose=False)
    tab = pd.DataFrame({'constituent': coef['name'], 'amplitude_m': coef['A'], 'phase_deg_UTC': coef['g']})
    tab = tab.sort_values('amplitude_m', ascending=False).reset_index(drop=True)
    return coef, tab


def predict(coef, start, hours, step_min=10):
    import utide
    start = pd.Timestamp(start); start = start.tz_localize('UTC') if start.tzinfo is None else start
    t = pd.date_range(start, periods=int(hours * 60 / step_min) + 1, freq=f'{int(round(step_min * 60))}s')
    tt = t.tz_convert(None).values.astype('datetime64[ns]')
    h = np.concatenate([utide.reconstruct(tt[i:i + 20000], coef, verbose=False)['h']       # in pieces: limits memory
                        for i in range(0, len(tt), 20000)])
    return pd.Series(h - coef.get('mean', 0.0), index=t)


def extremes(s, min_sep_h=2.0, prominence=0.005):
    """High and low waters of a tide series."""
    from scipy.signal import find_peaks
    step_h = (s.index[1] - s.index[0]) / pd.Timedelta(hours=1)
    dist = max(1, int(min_sep_h / step_h))
    hi, _ = find_peaks(s.values, distance=dist, prominence=prominence)
    lo, _ = find_peaks(-s.values, distance=dist, prominence=prominence)
    return s.iloc[hi], s.iloc[lo]


def datums(pred, tab):
    """Tidal levels (m relative to model MSL) from a multi-year prediction and the constituents."""
    hw, lw = extremes(pred)
    t0 = pred.index[0]
    day = ((pred.index - t0) / pd.Timedelta(hours=TIDAL_DAY_H)).astype(int)
    daily = pd.DataFrame({'h': pred.values, 'day': day}).groupby('day')['h'].agg(['max', 'min'])
    rng = daily['max'] - daily['min']
    fort = (np.arange(len(rng)) * TIDAL_DAY_H / 24 / SPRING_NEAP_D).astype(int)
    fr = pd.DataFrame({'rng': rng.values, 'hi': daily['max'].values, 'lo': daily['min'].values, 'f': fort})
    g = fr.groupby('f')
    spr = g.apply(lambda x: x.loc[x.rng.idxmax()]); nep = g.apply(lambda x: x.loc[x.rng.idxmin()])
    A = dict(zip(tab.constituent, tab.amplitude_m))
    m2, s2, k1, o1 = (A.get(k, 0.0) for k in ('M2', 'S2', 'K1', 'O1'))
    F = (k1 + o1) / (m2 + s2) if (m2 + s2) > 0 else np.inf
    kind = ('semidiurnal' if F < 0.25 else 'mixed, mainly semidiurnal' if F < 1.5 else
            'mixed, mainly diurnal' if F < 3 else 'diurnal')
    rows = [('HAT', 'highest astronomical tide (max of the prediction)', pred.max()),
            ('MHWS', 'mean high water springs (mean of the highest daily high of each spring-neap cycle)', spr.hi.mean()),
            ('MHHW', 'mean higher high water (highest high of each tidal day)', daily['max'].mean()),
            ('MHW', 'mean high water (all high waters)', hw.mean()),
            ('MHWN', 'mean high water neaps', nep.hi.mean()),
            ('MSL', 'mean sea level of the model (reference)', 0.0),
            ('MLWN', 'mean low water neaps', nep.lo.mean()),
            ('MLW', 'mean low water (all low waters)', lw.mean()),
            ('MLLW', 'mean lower low water (lowest low of each tidal day)', daily['min'].mean()),
            ('MLWS', 'mean low water springs', spr.lo.mean()),
            ('LAT', 'lowest astronomical tide (min of the prediction)', pred.min())]
    lev = pd.DataFrame(rows, columns=['level', 'definition', 'm_above_model_MSL'])
    ranges = pd.DataFrame([('mean spring range', spr.rng.mean()), ('mean neap range', nep.rng.mean()),
                           ('mean daily range (MHHW-MLLW)', daily['max'].mean() - daily['min'].mean()),
                           ('mean range (MHW-MLW)', hw.mean() - lw.mean()), ('maximum range (HAT-LAT)', pred.max() - pred.min()),
                           ('M2 + S2 amplitude', m2 + s2), ('K1 + O1 amplitude', k1 + o1),
                           ('form factor F = (K1+O1)/(M2+S2)', F)], columns=['quantity', 'value'])
    ranges.loc[len(ranges)] = ['tide type', kind]
    return lev, ranges, dict(spring=float(spr.rng.mean()), neap=float(nep.rng.mean()), mean=float(rng.mean()), kind=kind, F=F)


def tidal_day(pred, target_range, hours):
    """Window of `hours` starting at a rising crossing of MSL whose tidal range is closest to target_range."""
    v = pred.values; idx = pred.index
    up = np.where((v[:-1] < 0) & (v[1:] >= 0))[0]
    step = idx[1] - idx[0]; n = int(pd.Timedelta(hours=hours) / step) + 1
    best, best_d = None, np.inf
    for i in up:
        if i + n >= len(v): break
        w = v[i:i + n]; d = abs((w.max() - w.min()) - target_range)
        if d < best_d: best, best_d = i, d
    w = pred.iloc[best:best + n]
    return pd.Series(w.values, index=(w.index - w.index[0]) / pd.Timedelta(seconds=1)), w.index[0]


def surge_tables(surge, seasons, pcts):
    s = surge.dropna(); m = s.index.month
    rows = []
    for name, months in [('all year', list(range(1, 13)))] + [(k, v) for k, v in seasons.items()] + \
                        [(f'{mm:02d}', [mm]) for mm in range(1, 13)]:
        x = s[np.isin(m, months)]
        if not len(x): continue
        r = dict(period=name, months=','.join(map(str, months)), n_days=len(x), mean=x.mean(), max=x.max(), min=x.min())
        r.update({f'P{p}': x.quantile(p / 100) for p in pcts})
        rows.append(r)
    am = s.groupby(s.index.year).max()
    return pd.DataFrame(rows), pd.DataFrame({'year': am.index, 'annual_max_surge_m': am.values})


def figure(ctx, tide, pred, lev, surge, seasons, rinfo):
    import matplotlib.pyplot as plt
    figure_style()
    fig, axs = plt.subplots(1, 2, figsize=(7.2, 2.6), constrained_layout=True, gridspec_kw=dict(width_ratios=[1.7, 1]))
    t0 = tide.index[0]; m = tide[(tide.index >= t0) & (tide.index < t0 + pd.Timedelta(days=30))]
    axs[0].plot(m.index, m.values, color=OKABE_ITO[0], lw=0.8, label='GTSM tide')
    for k, ls in (('HAT', ':'), ('MHWS', '--'), ('MLWS', '--'), ('LAT', ':')):
        v = float(lev.loc[lev.level == k, 'm_above_model_MSL'].iloc[0]); axs[0].axhline(v, color='0.4', ls=ls, lw=0.7)
        axs[0].text(m.index[-1], v, f' {k}', va='center', fontsize=6)
    axs[0].set_ylabel('m (model MSL)'); axs[0].set_title(f"Tide, first 30 days ({rinfo['kind']})", loc='left')
    axs[0].tick_params(axis='x', rotation=30)
    data = [surge[np.isin(surge.index.month, v)].dropna().values for v in seasons.values()]
    axs[1].boxplot(data, whis=(1, 99), showfliers=False, patch_artist=True, boxprops=dict(facecolor=OKABE_ITO[1], alpha=0.6),
                   medianprops=dict(color='k'))
    axs[1].set_xticks(range(1, len(seasons) + 1)); axs[1].set_xticklabels([k.replace(' ', '\n', 1) for k in seasons], fontsize=7)
    axs[1].set_ylabel('daily max surge (m)'); axs[1].set_title('Storm surge by season (whiskers 1-99 %)', loc='left')
    save_fig(ctx, fig, 'Fig_tide_surge'); plt.show()


# ------------------------------------------------------------------------------------------------ run
def run(ctx, options=None, seasons=None, percentiles=None):
    o = check('tides', options); ctx.opts['tides'] = o
    if not o['TIDES']:
        print('TIDES = False: no tide / surge'); return ctx
    from .options import DEFAULTS
    seasons = seasons or ctx.opts.get('climate', {}).get('SEASONS') or DEFAULTS['climate']['SEASONS']
    pcts = percentiles or DEFAULTS['climate']['PERCENTILES']
    name = ctx.site['NAME']
    if o['TIDE_SOURCE'] == 'twl_minus_surge':        # reanalysis: tide = total water level - surge (+ constant MSL)
        twl = gtsm_point(ctx, o, 'total_water_level', o['TIDE_AGGREGATION'], o['TIDE_YEARS'])
        sur = gtsm_point(ctx, o, 'storm_surge_residual', o['TIDE_AGGREGATION'], o['TIDE_YEARS'])
        tide = (twl - sur).dropna(); tide = tide - tide.mean(); tide.name = 'tide'
    elif o['TIDE_SOURCE'] == 'tidal_elevation':      # pure astronomical tide: 'historical', 10-min, v1, up to 2014
        tide = gtsm_point(ctx, o, 'tidal_elevation', '10_min', o['TIDE_YEARS'], experiment='historical', version='v1')
    else:
        raise ValueError("TIDES['TIDE_SOURCE'] must be 'twl_minus_surge' or 'tidal_elevation'")
    surge = gtsm_point(ctx, o, 'storm_surge_residual', 'daily_maximum', o['SURGE_YEARS'])
    tide.to_csv(ctx.path('data', f'{name}_GTSM_tide.csv')); surge.to_csv(ctx.path('data', f'{name}_GTSM_surge_daily_max.csv'))
    coef, tab = harmonic(tide, ctx.lat)
    pred = predict(coef, pd.Timestamp(f"{o['TIDE_YEARS'][0]}-01-01", tz='UTC'), o['PREDICT_YEARS'] * 365.25 * 24, step_min=15)
    lev, ranges, rinfo = datums(pred, tab)
    stab, amax = surge_tables(surge, seasons, pcts)
    figure(ctx, tide, pred, lev, surge, seasons, rinfo)
    for df, nm in ((tab, 'tide_constituents'), (lev, 'tide_levels'), (ranges, 'tide_ranges'), (stab, 'surge_statistics'),
                   (amax, 'surge_annual_maxima')):
        save_csv(ctx, df, nm)
    ctx.data.update(tide=tide, surge=surge, tide_coef=coef, tide_constituents=tab, tide_levels=lev, tide_ranges=ranges,
                    tide_range_info=rinfo, surge_stats=stab, surge_annual_max=amax, tide_pred=pred)
    print(f"Tide: {rinfo['kind']} (F = {rinfo['F']:.2f}); mean spring range {rinfo['spring']:.2f} m, neap {rinfo['neap']:.2f} m; "
          f"HAT {pred.max():+.2f} m, LAT {pred.min():+.2f} m (model MSL)")
    print(lev[['level', 'm_above_model_MSL']].round(3).to_string(index=False))
    print(f"Storm surge (daily maxima {o['SURGE_YEARS'][0]}–{o['SURGE_YEARS'][1]}): P50 {surge.median():.2f} m, P99 "
          f"{surge.quantile(0.99):.2f} m, max {surge.max():.2f} m ({surge.idxmax():%Y-%m-%d})")
    return ctx

