"""Sentinel-2 sea-state dates — days to leave out of an Earth Engine composite because of rough seas or wind.

For every day of MONTHS in YEARS, at the Sentinel-2 overpass time (OVERPASS_UTC):
- waves: the largest offshore Hs in the WAVE_WINDOW_H hours before the overpass (Copernicus Marine, ERA5, or the
  larger of the two), compared with WAVE_MAX_HS;
- wind: the mean ERA5 10 m wind speed over the WIND_WINDOW_H hours before, compared with WIND_MAX_MS.

Days above either limit are written as a JavaScript line, `var SEA_STATE_EXCLUDE = [...]`, to paste into the
Earth Engine script (seastrong_sdb_inputs.js). Every day of the months is listed, whether or not Sentinel-2 took an
image that day: Earth Engine simply ignores dates without images. The per-day table with the values is saved too.
"""
import numpy as np
import pandas as pd
from .core import save_csv
from .options import check


def window(series, times, hours, how):
    """max or mean of `series` (time-indexed) in (t - hours, t] for each t; NaN if no value."""
    s = series.dropna().sort_index()
    s = s[~s.index.duplicated()]
    out = np.full(len(times), np.nan)
    if not len(s): return out
    idx = s.index.values; val = s.values
    lo = np.searchsorted(idx, (times - pd.Timedelta(hours=hours)).values, side='right')
    hi = np.searchsorted(idx, times.values, side='right')
    for i, (a, b) in enumerate(zip(lo, hi)):
        if b > a: out[i] = val[a:b].max() if how == 'max' else val[a:b].mean()
    return out


def run(ctx, options=None):
    o = check('seastate', options); ctx.opts['seastate'] = o
    from .download import load
    load(ctx)
    m0, m1 = o['MONTHS']
    days = pd.date_range(f"{o['YEARS'][0]}-01-01", f"{o['YEARS'][1]}-12-31", freq='D')
    mon = days.month
    days = days[((mon >= m0) & (mon <= m1)) if m0 <= m1 else ((mon >= m0) | (mon <= m1))]
    days = days[days <= pd.Timestamp(ctx.today)]
    t = (days + pd.to_timedelta(o['OVERPASS_UTC'], unit='h')).tz_localize('UTC')
    df = pd.DataFrame({'date': days.strftime('%Y-%m-%d'), 'overpass_utc': t})
    srcs = {'cmems': ['cmems'], 'era5': ['era5'], 'max': ['cmems', 'era5']}[o['WAVE_SOURCE']]
    hs = []
    for s in srcs:
        if s in ctx.data:
            d = ctx.data[s]; v = window(d.set_index(pd.to_datetime(d['time'], utc=True))['hs'], t, o['WAVE_WINDOW_H'], 'max')
            df[f'hs_{s}'] = v; hs.append(v)
    if not hs: raise RuntimeError('No wave data: run the download step first')
    df['hs_m'] = np.nanmax(np.vstack(hs), axis=0) if len(hs) > 1 else hs[0]
    if 'era5' in ctx.data:
        e = ctx.data['era5']
        df['wind_ms'] = window(e.set_index(pd.to_datetime(e['time'], utc=True))['wind_speed'], t, o['WIND_WINDOW_H'], 'mean')
    else:
        df['wind_ms'] = np.nan
    reasons = []
    for h, w in zip(df.hs_m, df.wind_ms):
        r = []
        if np.isfinite(h) and h > o['WAVE_MAX_HS']: r.append('waves')
        if np.isfinite(w) and w > o['WIND_MAX_MS']: r.append('wind')
        if o['MISSING'] == 'list' and (not np.isfinite(h) or not np.isfinite(w)): r.append('no_data')
        reasons.append(','.join(r))
    df['reason'] = reasons
    df['listed'] = df.reason != ''
    df['overpass_utc'] = df.overpass_utc.dt.strftime('%Y-%m-%d %H:%M')
    save_csv(ctx, df, 'S2_sea_state_by_day')
    bad = df.loc[df.listed, 'date'].tolist()
    line = 'var SEA_STATE_EXCLUDE = [' + ', '.join(f"'{d}'" for d in bad) + '];'
    p = ctx.path('tables', f"{ctx.site['NAME']}_S2_SEA_STATE_EXCLUDE.js.txt")
    open(p, 'w').write(f"// {ctx.site['NAME']}: {len(bad)} of {len(df)} days of months {m0}-{m1}, {o['YEARS'][0]}-{o['YEARS'][1]}, "
                       f"with Hs > {o['WAVE_MAX_HS']} m (max over {o['WAVE_WINDOW_H']} h, {o['WAVE_SOURCE']}) or wind > "
                       f"{o['WIND_MAX_MS']} m/s (mean over {o['WIND_WINDOW_H']} h) before {o['OVERPASS_UTC']:g} h UTC\n{line}\n")
    n = df.reason.str.split(',').explode().value_counts().to_dict()
    print(f"{len(bad)} of {len(df)} days listed ({', '.join(f'{k}: {v}' for k, v in n.items() if k)}).")
    by_month = df.groupby(pd.to_datetime(df.date).dt.month)['listed'].mean().mul(100).round(0)
    print('Share of days listed, by month (%):', by_month.to_dict())
    print(f'Saved: {p}\nCopy the line below into the Earth Engine script (SEA_STATE_EXCLUDE):\n')
    print(line)
    ctx.data['seastate'] = df
    return ctx
