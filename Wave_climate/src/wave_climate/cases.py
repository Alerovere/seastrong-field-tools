"""Step 4 — representative seasonal cases and XBeach boundary files; Excel workbook with every table.

For each season and level (e.g. typical P50, energetic P90, storm P99):
- `Hs` = that percentile of the season's Hs;
- `Tp`, wave direction and wind = median Tp, circular-mean direction and median wind (with its mean direction) of the
  records whose Hs is within +-BAND of the case Hs (the band widens until MIN_RECORDS are found), so the
  combination is one that actually occurs together;
- water level = a representative tidal day (spring / mean / neap, from the GTSM harmonic prediction) + the season's
  daily-maximum storm surge at the same percentile (SURGE_PERCENTILE='same').

XBeach files per case (folder xbeach/<season>_<level>/):
- `jonswap.txt` (wbctype = jonstable): one line `Hm0 Tp mainang gammajsp s duration dtbc`;
- `wind.txt`: `time windv windth` (constant wind, nautical direction it comes FROM);
- `tide.txt`: `time zs0` (tide + surge, m relative to model MSL);
- `params_boundary.txt`: the matching params.txt keywords to paste into your model setup.
Check in XBeach: the nautical convention of mainang / windth with your grid orientation (alfa), and the vertical
datum of your bathymetry (GTSM levels are relative to model MSL).
"""
import os, re
import numpy as np
import pandas as pd
from .core import save_csv
from .options import check
from .climate import circ_mean, wave_frame
from .tides import tidal_day, predict


def conditional(x, hs, band, nmin):
    b = band
    while True:
        sel = x[(x.hs >= hs * (1 - b)) & (x.hs <= hs * (1 + b))]
        if len(sel) >= nmin or b > 1.0: return sel, b
        b *= 1.5


def make_cases(ctx, o, co):
    w = ctx.data.get('waves_for_climate')
    if w is None: w = wave_frame(ctx, co)
    if 'tp' not in w or w.tp.isna().all():
        raise RuntimeError("XBeach needs a peak period: use climate WAVE_SOURCE = 'cmems' (ERA5's point service has no Tp)")
    surge = ctx.data.get('surge')
    rows = []
    for season, months in co['SEASONS'].items():
        x = w[w.month.isin(months)].dropna(subset=['hs', 'tp', 'dir'])
        sx = surge[np.isin(surge.index.month, months)] if surge is not None else None
        for level, p in o['LEVELS'].items():
            hs = float(x.hs.quantile(p / 100))
            sel, b = conditional(x, hs, o['BAND'], o['MIN_RECORDS'])
            sp = p if o['SURGE_PERCENTILE'] == 'same' else o['SURGE_PERCENTILE']
            r = dict(case=re.sub(r'[^A-Za-z0-9]+', '_', f'{season}_{level}').strip('_'), season=season, months=','.join(map(str, months)), level=level, hs_percentile=p,
                     Hm0=round(hs, 2), Tp=round(float(sel.tp.median()), 1), mainang=round(circ_mean(sel.dir), 0),
                     tp_P10=round(float(sel.tp.quantile(0.1)), 1), tp_P90=round(float(sel.tp.quantile(0.9)), 1),
                     n_records=len(sel), band_used=round(b, 2))
            if 'wind_speed' in sel and sel.wind_speed.notna().any():
                r.update(windv=round(float(sel.wind_speed.median()), 1), windth=round(circ_mean(sel.wind_from.dropna()), 0))
            else:
                r.update(windv=np.nan, windth=np.nan)
            if 'hs_swell' in sel:
                r['swell_share_of_energy'] = round(float(((sel.hs_swell ** 2) / (sel.hs ** 2)).median()), 2)
            r['surge_m'] = round(float(sx.quantile(sp / 100)), 3) if (sx is not None and len(sx) and sp) else 0.0
            r.update(gammajsp=o['GAMMA'], s=o['SPREADING_S'], tide_cycle=o['TIDE_CYCLE'], duration_h=o['DURATION_H'])
            rows.append(r)
    return pd.DataFrame(rows)


def write_xbeach(ctx, cases, o):
    pred, info = ctx.data.get('tide_pred'), ctx.data.get('tide_range_info')
    dur = o['DURATION_H'] * 3600
    tide_txt, t0 = None, None
    if o['TIDE_CYCLE'] != 'none':
        if pred is None: raise RuntimeError("TIDE_CYCLE needs the tide step (run st.tides.run first) or TIDE_CYCLE = 'none'")
        target = info[o['TIDE_CYCLE']]
        _, t0 = tidal_day(pred[pred.index < pred.index[0] + pd.Timedelta(days=366)], target, o['DURATION_H'])                       # find the day on the 15-min prediction
        fine = predict(ctx.data['tide_coef'], t0, o['DURATION_H'], step_min=o['TIDE_DT_S'] / 60)   # then at the file step
        tide_txt = pd.Series(fine.values, index=(fine.index - fine.index[0]) / pd.Timedelta(seconds=1))
    out = []
    for r in cases.itertuples():
        d = ctx.path('xbeach', r.case, 'x'); d = os.path.dirname(d)
        with open(os.path.join(d, 'jonswap.txt'), 'w') as f:
            f.write(f'{r.Hm0:.3f} {r.Tp:.2f} {r.mainang:.1f} {r.gammajsp:.2f} {r.s:.1f} {dur:.0f} {o["DTBC"]:.2f}\n')
        wv = 0.0 if pd.isna(r.windv) else r.windv; wth = 0.0 if pd.isna(r.windth) else r.windth
        with open(os.path.join(d, 'wind.txt'), 'w') as f:
            f.write(f'0 {wv:.2f} {wth:.1f}\n{dur:.0f} {wv:.2f} {wth:.1f}\n')
        if tide_txt is not None:
            zs = tide_txt + r.surge_m
        else:
            zs = pd.Series([r.surge_m, r.surge_m], index=[0.0, float(dur)])
        with open(os.path.join(d, 'tide.txt'), 'w') as f:
            for t, z in zs.items(): f.write(f'{t:.0f} {z:.4f}\n')
        with open(os.path.join(d, 'params_boundary.txt'), 'w') as f:
            f.write(f"""% {ctx.site['NAME']} case {r.case}: season {r.season} (months {r.months}), Hs P{r.hs_percentile}
% Generated by wave_climate. Waves: Copernicus Marine at the offshore point; wind: ERA5; tide + surge: GTSM (m, model MSL).
% Tide: representative {o['TIDE_CYCLE']} tidal day{f' starting {t0:%Y-%m-%d %H:%M} UTC (prediction)' if t0 is not None else ''}; surge {r.surge_m:+.3f} m added.
% Paste into params.txt; check thetanaut / alfa (directions are nautical, coming FROM) and the datum of your bathymetry.
wbctype  = jonstable
bcfile   = jonswap.txt
windfile = wind.txt
zs0file  = tide.txt
tideloc  = 1
zs0      = {zs.iloc[0]:.4f}
tstop    = {dur:.0f}
""")
        out.append(d)
    return out


def workbook(ctx):
    """Every table in one Excel file (one sheet per table, a README sheet first)."""
    T = dict(ctx.data.get('tables', {}))
    for k in ('tide_levels', 'tide_ranges', 'tide_constituents', 'surge_stats', 'surge_annual_max', 'cases'):
        if k in ctx.data and isinstance(ctx.data[k], pd.DataFrame): T[k] = ctx.data[k]
    readme = pd.DataFrame({'item': [
        'site', 'point', 'units', 'directions', 'periods', 'waves', 'wind', 'tide and surge', 'vertical reference', 'sources'],
        'description': [
        ctx.site['NAME'], f'{ctx.lon:.4f} E, {ctx.lat:.4f} N (offshore point; model cells in sources.json)',
        'Hs, surge, levels m; periods s; wind m/s; percent = % of time in the period',
        'nautical, direction waves / wind come FROM (0 = N, 90 = E); circular means',
        'all year, your seasons (SEASONS), then each month', 'Copernicus Marine (hs, tp, tm10, tm02, dir, partitions) and/or ERA5 (hs, tm, dir)',
        'ERA5 10 m wind, hourly', 'GTSM reanalysis (Deltares, CDS): harmonic analysis of tidal_elevation; daily-maximum storm_surge_residual',
        'GTSM model mean sea level (1986-2005); NOT chart datum or local survey datum',
        'ERA5 (Hersbach et al. 2020), Copernicus Marine wave products, GTSM v3 (Muis et al. 2020, CDS doi:10.24381/cds.a6d42d60)']})
    p = ctx.path(f"{ctx.site['NAME']}_wave_wind_tide_climate.xlsx")
    with pd.ExcelWriter(p + '.tmp.xlsx', engine='openpyxl') as xw:
        readme.to_excel(xw, sheet_name='README', index=False)
        for k, df in T.items():
            if isinstance(df, pd.DataFrame) and len(df):
                df.to_excel(xw, sheet_name=k[:31], index=False)
    os.replace(p + '.tmp.xlsx', p)
    return p


def run(ctx, options=None):
    o = check('cases', options); ctx.opts['cases'] = o
    co = ctx.opts.get('climate') or check('climate', {})
    cases = make_cases(ctx, o, co)
    save_csv(ctx, cases, 'xbeach_cases'); ctx.data['cases'] = cases
    dirs = write_xbeach(ctx, cases, o)
    print(cases[['case', 'Hm0', 'Tp', 'mainang', 'windv', 'windth', 'surge_m', 'n_records']].to_string(index=False))
    print(f"\nXBeach boundary files for {len(dirs)} cases in {os.path.dirname(dirs[0]) if dirs else '-'}")
    p = workbook(ctx); print(f'All tables in one workbook: {p}')
    return ctx
