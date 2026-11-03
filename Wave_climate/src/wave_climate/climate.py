"""Step 3 — wave and wind climate: statistics per month and per season, direction tables, joint tables, roses.

Directions are NAUTICAL and give where waves / wind COME FROM (0 = from north, 90 = from east), as in ERA5,
Copernicus Marine and XBeach. Means of directions are circular (vector) means; `dir_spread_deg` is the circular
standard deviation (how variable the direction is in that period, NOT the spectral spreading of the waves).
"""
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from .core import save_csv, save_fig, figure_style, OKABE_ITO
from .options import check

MON = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']


def circ_mean(deg):
    r = np.radians(np.asarray(deg, float)); r = r[np.isfinite(r)]
    if not len(r): return np.nan
    return float(np.degrees(np.arctan2(np.sin(r).mean(), np.cos(r).mean())) % 360)


def circ_std(deg):
    r = np.radians(np.asarray(deg, float)); r = r[np.isfinite(r)]
    if not len(r): return np.nan
    R = np.hypot(np.sin(r).mean(), np.cos(r).mean())
    return float(np.degrees(np.sqrt(-2 * np.log(max(R, 1e-12)))))


def periods(seasons):
    """[(name, months)]: all year, your seasons, then the twelve months."""
    return [('all year', list(range(1, 13)))] + [(k, list(v)) for k, v in seasons.items()] + \
           [(MON[m - 1], [m]) for m in range(1, 13)]


def sector_edges(n):
    w = 360 / n
    return w, [(i * w - w / 2) % 360 for i in range(n)]


def sector_of(deg, n):
    w = 360 / n
    return np.floor(((np.asarray(deg, float) + w / 2) % 360) / w)        # float; NaN where the direction is missing


def sector_names(n):
    names16 = ['N', 'NNE', 'NE', 'ENE', 'E', 'ESE', 'SE', 'SSE', 'S', 'SSW', 'SW', 'WSW', 'W', 'WNW', 'NW', 'NNW']
    if n == 16: return names16
    if n == 8: return names16[::2]
    return [f'{i * 360 / n:.0f}' for i in range(n)]


def wave_frame(ctx, o):
    """Waves of the chosen source with ERA5 wind at the same times (nearest hour)."""
    src = o['WAVE_SOURCE']
    if src not in ctx.data: raise RuntimeError(f"WAVE_SOURCE = '{src}' but no {src.upper()} data: run the download step with it")
    w = ctx.data[src].copy(); w['time'] = w['time'].dt.as_unit('ns')
    w = w[[c for c in w.columns if c not in ('dataset', 'cell_lon', 'cell_lat', 'u10', 'v10', 'wind_speed', 'wind_from')]]
    if 'era5' in ctx.data and src != 'era5':
        e = ctx.data['era5'][['time', 'wind_speed', 'wind_from']].sort_values('time')
        e = e.assign(time=e['time'].dt.as_unit('ns'))
        w = pd.merge_asof(w.sort_values('time'), e, on='time', direction='nearest', tolerance=pd.Timedelta('1h'))
    elif src == 'era5':
        w = ctx.data['era5'][['time', 'hs', 'tm', 'dir', 'wind_speed', 'wind_from']].copy()
    if o['YEARS']:
        y = w.time.dt.year; w = w[(y >= o['YEARS'][0]) & (y <= o['YEARS'][1])]
    w['month'] = w.time.dt.month
    return w.dropna(subset=['hs']).reset_index(drop=True)


def stats(df, cols, pers, pcts, dircols=()):
    rows = []
    for name, months in pers:
        x = df[df.month.isin(months)]
        r = dict(period=name, months=','.join(map(str, months)), n=len(x),
                 years=f"{x.time.dt.year.min()}-{x.time.dt.year.max()}" if len(x) else '')
        for c in cols:
            if c not in x: continue
            v = x[c].dropna()
            r[f'{c}_mean'] = v.mean(); r[f'{c}_std'] = v.std()
            for p in pcts: r[f'{c}_P{p}'] = v.quantile(p / 100) if len(v) else np.nan
            r[f'{c}_max'] = v.max()
        for c in dircols:
            if c in x:
                r[f'{c}_mean_deg'] = circ_mean(x[c]); r[f'{c}_spread_deg'] = circ_std(x[c])
        rows.append(r)
    return pd.DataFrame(rows)


def joint(df, var, bins, dircol, n, pers):
    """% of time in each (var bin, direction sector), per period; long format."""
    rows = []
    labs = [f'{a:g}-{b:g}' for a, b in zip(bins[:-1], bins[1:])]
    sec = sector_names(n)
    for name, months in pers:
        x = df[df.month.isin(months)].dropna(subset=[var, dircol])
        if not len(x): continue
        b = pd.cut(x[var], bins, labels=labs, right=False, include_lowest=True)
        s = sector_of(x[dircol].values, n).astype(int)
        t = pd.crosstab(b, pd.Categorical([sec[i] for i in s], categories=sec), dropna=False) / len(x) * 100
        t = t.reindex(index=labs, fill_value=0)
        long = t.stack().rename('percent').reset_index(); long.columns = [f'{var}_bin', 'from_sector', 'percent']
        long.insert(0, 'period', name); rows.append(long)
    return pd.concat(rows, ignore_index=True) if rows else pd.DataFrame()


def joint2(df, a, abins, b, bbins, pers):
    rows = []
    la = [f'{x:g}-{y:g}' for x, y in zip(abins[:-1], abins[1:])]; lb = [f'{x:g}-{y:g}' for x, y in zip(bbins[:-1], bbins[1:])]
    for name, months in pers:
        x = df[df.month.isin(months)].dropna(subset=[a, b])
        if not len(x): continue
        t = pd.crosstab(pd.cut(x[a], abins, labels=la, right=False), pd.cut(x[b], bbins, labels=lb, right=False), dropna=False) / len(x) * 100
        long = t.reindex(index=la, columns=lb, fill_value=0).stack().rename('percent').reset_index()
        long.columns = [f'{a}_bin', f'{b}_bin', 'percent']; long.insert(0, 'period', name); rows.append(long)
    return pd.concat(rows, ignore_index=True) if rows else pd.DataFrame()


def compare(ctx, pers):
    """ERA5 vs Copernicus Marine Hs at common times (model comparison, not validation)."""
    if not {'era5', 'cmems'} <= set(ctx.data): return pd.DataFrame()
    a = ctx.data['cmems'][['time', 'hs', 'dir']]; b = ctx.data['era5'][['time', 'hs', 'dir']]
    a = a.assign(time=a.time.dt.as_unit('ns')); b = b.assign(time=b.time.dt.as_unit('ns'))
    m = pd.merge(a, b, on='time', suffixes=('_cmems', '_era5')).dropna()
    m['month'] = m.time.dt.month
    rows = []
    for name, months in pers[:1 + len(pers) - 13]:
        x = m[m.month.isin(months)]
        if len(x) < 10: continue
        d = x.hs_era5 - x.hs_cmems
        dd = ((x.dir_era5 - x.dir_cmems + 180) % 360) - 180
        rows.append(dict(period=name, n=len(x), hs_cmems_mean=x.hs_cmems.mean(), hs_era5_mean=x.hs_era5.mean(), bias_era5_minus_cmems=d.mean(),
                         rmsd=np.sqrt((d ** 2).mean()), r=x.hs_era5.corr(x.hs_cmems), dir_diff_median_deg=dd.median()))
    return pd.DataFrame(rows)


# ------------------------------------------------------------------------------------------------ figures
def rose(ax, speed, deg, bins, n, title, unit, cmap='viridis'):
    w = 2 * np.pi / n
    s = sector_of(deg, n); ok = np.isfinite(s) & np.isfinite(np.asarray(speed, float))
    speed, s = np.asarray(speed)[ok], np.asarray(s[ok], int)
    base = np.zeros(n); cols = plt.get_cmap(cmap)(np.linspace(0.1, 0.95, len(bins) - 1))
    tot = max(len(speed), 1)
    for i, (a, b) in enumerate(zip(bins[:-1], bins[1:])):
        sel = (speed >= a) & (speed < b)
        if not sel.any(): continue
        h = np.bincount(s[sel], minlength=n) / tot * 100
        ax.bar(np.arange(n) * w, h, width=w * 0.95, bottom=base, color=cols[i], label=f'{a:g}–{b:g}', edgecolor='white', lw=0.3)
        base += h
    ax.set_theta_zero_location('N'); ax.set_theta_direction(-1); ax.set_title(title, fontsize=8, pad=10)
    from matplotlib.ticker import FuncFormatter
    ax.tick_params(labelsize=6); ax.yaxis.set_major_formatter(FuncFormatter(lambda v, _: f'{v:.0f}%'))
    ax.tick_params(axis='y', labelsize=5)
    return ax


def figures(ctx, w, o):
    figure_style()
    seasons = list(o['SEASONS'].items())
    # monthly boxplots
    vars_ = [('hs', '$H_s$ (m)'), ('tp', '$T_p$ (s)') if 'tp' in w else ('tm', '$T_m$ (s)'), ('wind_speed', 'wind (m s$^{-1}$)')]
    vars_ = [v for v in vars_ if v[0] in w and w[v[0]].notna().any()]
    fig, axs = plt.subplots(len(vars_), 1, figsize=(7.2, 1.9 * len(vars_)), sharex=True, constrained_layout=True)
    axs = np.atleast_1d(axs)
    for ax, (c, lab) in zip(axs, vars_):
        data = [w.loc[w.month == m, c].dropna().values for m in range(1, 13)]
        ax.boxplot(data, whis=(5, 95), showfliers=False, patch_artist=True,
                   boxprops=dict(facecolor=OKABE_ITO[4], alpha=0.6), medianprops=dict(color='k'))
        ax.set_ylabel(lab)
    axs[-1].set_xticks(range(1, 13)); axs[-1].set_xticklabels(MON)
    axs[0].set_title(f"{ctx.site['NAME']}: monthly distribution (box 25–75 %, whiskers 5–95 %, line median); waves {o['WAVE_SOURCE'].upper()}", loc='left')
    save_fig(ctx, fig, 'Fig_monthly_boxplots'); plt.show()
    # roses
    for kind, sp, dr, bins, unit in (('waves', 'hs', 'dir', o['HS_BINS'], 'm'), ('wind', 'wind_speed', 'wind_from', o['WIND_BINS'], 'm/s')):
        if dr not in w or w[dr].isna().all(): continue
        n = len(seasons) + 1; nc = min(n, 3); nr = int(np.ceil(n / nc))
        fig = plt.figure(figsize=(7.2, 3.0 * nr))
        for i, (name, months) in enumerate([('all year', list(range(1, 13)))] + seasons):
            x = w[w.month.isin(months)]
            ax = fig.add_subplot(nr, nc, i + 1, projection='polar')
            rose(ax, x[sp].values, x[dr].values, bins, o['DIR_SECTORS'], f'{name} (n = {len(x):,})', unit,
                 cmap='viridis' if kind == 'waves' else 'magma')
        h, l = ax.get_legend_handles_labels()
        fig.legend(h, l, title=f"{'$H_s$' if kind == 'waves' else 'wind speed'} ({unit})", loc='lower right', fontsize=6, title_fontsize=7, ncol=2)
        fig.suptitle(f"{kind.capitalize()} rose: direction they come FROM, % of time", fontsize=9)
        fig.tight_layout(rect=[0, 0.05, 1, 0.96], h_pad=2.5); save_fig(ctx, fig, f'Fig_rose_{kind}'); plt.show()
    # Hs-Tp scatter per season
    if 'tp' in w and w.tp.notna().any():
        fig, axs = plt.subplots(1, len(seasons), figsize=(7.2, 2.3), sharex=True, sharey=True, constrained_layout=True)
        for ax, (name, months) in zip(np.atleast_1d(axs), seasons):
            x = w[w.month.isin(months)].dropna(subset=['hs', 'tp'])
            ax.hexbin(x.tp, x.hs, gridsize=35, mincnt=1, bins='log', cmap='Blues')
            ax.set_title(name, loc='left'); ax.set_xlabel('$T_p$ (s)')
        np.atleast_1d(axs)[0].set_ylabel('$H_s$ (m)')
        save_fig(ctx, fig, 'Fig_Hs_Tp_by_season'); plt.show()


# ------------------------------------------------------------------------------------------------ run
def run(ctx, options=None):
    o = check('climate', options); ctx.opts['climate'] = o
    from .download import load
    load(ctx)
    w = wave_frame(ctx, o)
    pers = periods(o['SEASONS'])
    pcts = o['PERCENTILES']
    wcols = [c for c in ('hs', 'tp', 'tm10', 'tm02', 'tm', 'hs_windsea', 'tm_windsea', 'hs_swell', 'tm_swell') if c in w]
    T = {}
    T['wave_statistics'] = stats(w, wcols, pers, pcts, dircols=[c for c in ('dir', 'dir_swell', 'dir_windsea') if c in w])
    T['wind_statistics'] = stats(w.dropna(subset=['wind_speed']) if 'wind_speed' in w else w, ['wind_speed'], pers, pcts, dircols=['wind_from']) \
        if 'wind_speed' in w else pd.DataFrame()
    if 'era5' in ctx.data:                                # wind statistics from the full hourly ERA5 record
        e = ctx.data['era5'].copy(); e['month'] = e.time.dt.month
        if o['YEARS']: e = e[(e.time.dt.year >= o['YEARS'][0]) & (e.time.dt.year <= o['YEARS'][1])]
        T['wind_statistics'] = stats(e, ['wind_speed'], pers, pcts, dircols=['wind_from'])
        T['wind_speed_x_direction'] = joint(e, 'wind_speed', o['WIND_BINS'], 'wind_from', o['DIR_SECTORS'], pers[:len(o['SEASONS']) + 1])
    T['hs_x_direction'] = joint(w, 'hs', o['HS_BINS'], 'dir', o['DIR_SECTORS'], pers[:len(o['SEASONS']) + 1])
    if 'tp' in w:
        T['hs_x_tp'] = joint2(w, 'hs', o['HS_BINS'], 'tp', o['TP_BINS'], pers[:len(o['SEASONS']) + 1])
    T['era5_vs_cmems'] = compare(ctx, pers)
    for k, df in T.items():
        if len(df): save_csv(ctx, df, k)
    ctx.data['waves_for_climate'] = w; ctx.data['tables'] = T
    s = T['wave_statistics']
    show = ['period', 'n', 'hs_P50', 'hs_P90', 'hs_P99'] + (['tp_P50'] if 'tp_P50' in s else ['tm_P50'] if 'tm_P50' in s else []) + ['dir_mean_deg']
    print(f"Waves ({o['WAVE_SOURCE'].upper()}), per period:"); print(s[show].round(2).to_string(index=False))
    if len(T['wind_statistics']):
        print('\nWind (ERA5 10 m):'); print(T['wind_statistics'][['period', 'n', 'wind_speed_P50', 'wind_speed_P90', 'wind_from_mean_deg']].round(1).to_string(index=False))
    figures(ctx, w, o)
    return ctx
