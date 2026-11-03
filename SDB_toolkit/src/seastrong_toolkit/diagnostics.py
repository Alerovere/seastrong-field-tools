"""Plain-language reports after each step: what came out, what looks unusual, and which option to change.

Every report reads the step's saved outputs (manifest + files in its Drive folder), so it also works in a new Colab
session. Suggestions are only suggestions: the notebook never changes an option by itself.
"""
import os, json
import numpy as np
import pandas as pd
from . import core

MON3 = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']


class Report:
    def __init__(self, title):
        self.title, self.lines, self.sugg = title, [], []
    def say(self, *t): self.lines.append(' '.join(str(x) for x in t))
    def suggest(self, option, value, why): self.sugg.append((option, value, why))
    def show(self):
        print('=' * 100 + f'\n{self.title}\n' + '=' * 100)
        for l in self.lines: print(l)
        print('\nSUGGESTED CHANGES' + ('' if self.sugg else ': none, the results look consistent with the options used.'))
        for o, v, w in self.sugg:
            print(f'  - {o} = {v!r}\n      why: {w}')
        if self.sugg:
            print('  To apply one: edit the options cell of this step, run it, then run the step again.')
        return self

def _need(step, ctx):
    m = core.manifest(step, ctx)
    if not m['status']:
        raise RuntimeError(f"'{step}' has not been run with the current options: run it first.")
    return m

def _file(m, contains):
    for k, f in m['files'].items():
        if contains in k and os.path.exists(f['path']): return f['path']
    return None

def _km(lon1, lat1, lon2, lat2):
    r = 6371.0; p1, p2 = np.radians(lat1), np.radians(lat2)
    a = np.sin((p2 - p1) / 2) ** 2 + np.cos(p1) * np.cos(p2) * np.sin(np.radians(lon2 - lon1) / 2) ** 2
    return 2 * r * np.arcsin(np.sqrt(a))


# ------------------------------------------------------------------------------------------------ waves
def waves(ctx=None):
    ctx = core.use(ctx); m = _need('waves', ctx); W = ctx.cfg['waves']
    from .waves import load_series
    ser = load_series(); R = Report('WAVES, WIND AND RAIN — report')
    lon, lat = W['POINT']
    for k, d in ser.items():
        cl, ca = float(d.cell_lon.iloc[0]), float(d.cell_lat.iloc[0]); dist = _km(lon, lat, cl, ca)
        R.say(f"{k.upper():6s} {d.time.min():%Y-%m-%d} → {d.time.max():%Y-%m-%d}, {len(d):,} values; model cell {cl:.2f}, {ca:.2f} "
              f"({dist:.0f} km from your point)")
        if dist > (40 if k == 'era5' else 25):
            R.suggest("WAVES['POINT']", (round(cl, 2), round(ca, 2)),
                      f'the nearest {k.upper()} sea cell is {dist:.0f} km away: a point closer to open water gives a cell that represents your site better')
    cov = pd.DataFrame(m['coverage'].get('waves', []))
    if len(cov):
        bad = cov[cov.status != 'complete']
        R.say(f"\nCoverage: {int((cov.status == 'complete').sum())} of {len(cov)} source-years complete" +
              ('' if bad.empty else '; incomplete: ' + ', '.join(f"{r.source} {r.requested_start[:4]} ({r.status}, max gap {r.max_gap_h:.0f} h)" for r in bad.itertuples())))
    e, c = ser.get('era5'), ser.get('cmems')
    if e is not None and c is not None:
        mm = c[['time', 'hs', 'source']].merge(e[['time', 'hs']], on='time', suffixes=('_c', '_e'))
        R.say('\nERA5 vs Copernicus Marine (model comparison, not validation):')
        for src, g in mm.groupby('source'):
            d = g.hs_e - g.hs_c
            R.say(f"  {src}: N={len(g):,}, bias {d.mean():+.2f} m, r={g.hs_e.corr(g.hs_c):.2f}")
            if abs(d.mean()) > 0.25:
                R.say(f"    ! the two models differ by {d.mean():+.2f} m on average here: the 'max' screening source is the cautious choice")
    if e is not None:
        thr = W['PLOT_HS_THRESHOLD']
        e = e.copy(); e['month'] = e.time.dt.month
        t = e.groupby('month').agg(hs_median=('hs', 'median'), hs_p90=('hs', lambda x: x.quantile(0.9)),
                                   pct_above=('hs', lambda x: 100 * (x > thr).mean()))
        if 'wind_speed' in e: t['wind_median'] = e.groupby('month')['wind_speed'].median()
        if 'rain_mm' in e: t['rain_mm_per_day'] = e.groupby('month')['rain_mm'].sum() / e.groupby('month').time.apply(lambda x: x.dt.normalize().nunique())
        t.index = [MON3[i - 1] for i in t.index]
        R.say(f'\nERA5 monthly climate at the point (hs in m, % of hours with Hs > {thr} m, wind m/s, rain mm/day):')
        R.say(t.round(2).to_string())
        calm = t.pct_above.nsmallest(4).index.tolist()
        R.say(f"\nCalmest months (fewest hours above {thr} m): {', '.join(calm)}. The pre-screening combines this with rain, clouds and turbidity.")
    return R.show()


# ------------------------------------------------------------------------------------------------ prescreen
def prescreen(ctx=None):
    ctx = core.use(ctx); m = _need('prescreen', ctx); P = ctx.cfg['prescreen']
    R = Report('PRE-SCREENING: which months for the Sentinel-2 composite — report')
    o = m['outputs']; th = o.get('thresholds', {})
    R.say('Thresholds actually used (site percentile over all months, then capped):')
    for v, t in th.items():
        binding = 'cap' if t['cap'] is not None and t['cap'] < t['value'] else f"P{t['percentile']}"
        R.say(f"  {v:12s} ≤ {t['used']:.2f}   (P{t['percentile']} = {t['value']:.2f}, cap = {t['cap']}; limiting: {binding})")
    daily = pd.read_csv(_file(m, 'daily_conditions'), parse_dates=['date']) if _file(m, 'daily_conditions') else None
    if daily is not None:
        share = daily.good_day.mean()
        R.say(f"\nGood sea-state days: {share:.0%} of days with data.")
        fails = {v: (daily[v] > th[v]['used']).mean() for v in th if v in daily}
        R.say('Share of days failing each condition: ' + ', '.join(f"{k} {f:.0%}" for k, f in fails.items()))
        if share < 0.15:
            worst = max(fails, key=fails.get)
            R.suggest(f"PRESCREEN['PCTL']['{worst}']", min(95, P['PCTL'].get(worst, 75) + 10),
                      f'only {share:.0%} of days pass all conditions; {worst} removes the most ({fails[worst]:.0%}). A higher percentile accepts more days')
    win = pd.read_csv(_file(m, 'window_ranking')) if _file(m, 'window_ranking') else None
    if win is not None:
        R.say('\nBest windows by usable Sentinel-2 images per season (mean ± std, worst–best year, per month):')
        for L, g in win.groupby('length'):
            g = g.sort_values('usable_mean', ascending=False).head(3)
            R.say(f"  {L} months: " + ' | '.join(f"{r.label} {r.usable_mean:.1f}±{r.usable_std:.1f} ({r.usable_min:.0f}–{r.usable_max:.0f}), {r.usable_per_month:.1f}/mo" for r in g.itertuples()))
        cm = P['COMPARE_MONTHS']; L = (cm[1] - cm[0]) % 12 + 1
        cur = win[(win.length == L) & (win.start == cm[0])]
        best = win[win.length == L].sort_values(['usable_mean', 'usable_std'], ascending=[False, True]).iloc[0] if (win.length == L).any() else None
        if len(cur) and best is not None:
            c = cur.iloc[0]
            R.say(f"\nCOMPARE_MONTHS {MON3[cm[0] - 1]}–{MON3[cm[1] - 1]}: {c.usable_mean:.1f} ± {c.usable_std:.1f} usable images per season "
                  f"(rank {int(c.rank_in_length)} of 12 for {L}-month windows).")
            if best.start != cm[0] and best.usable_mean > c.usable_mean * 1.15:
                ms = json.loads(best.month_list) if isinstance(best.month_list, str) else best.month_list
                R.suggest("S2['MONTHS']", [int(ms[0]), int(ms[-1])],
                          f"{best.label} gives {best.usable_mean:.1f} usable images per season vs {c.usable_mean:.1f}; "
                          f"its worst year still had {best.usable_min:.0f}")
        lowyear = win[(win.length == L)].sort_values('usable_mean', ascending=False).iloc[0]
        if lowyear.usable_min < 3:
            R.say(f"\n! Even the best {L}-month window had a season with only {lowyear.usable_min:.0f} usable images: "
                  'a multi-year composite (several YEARS in the Sentinel-2 options) is needed to reach MIN_VALID observations per pixel.')
    mon = pd.read_csv(_file(m, 'monthly_summary')) if _file(m, 'monthly_summary') else None
    if mon is not None and 'p_clear_S2' in mon:
        R.say('\nClear-sky chance per Sentinel-2 scene: ' + ', '.join(f"{MON3[int(r.month) - 1]} {r.p_clear_S2:.0%}" for r in mon.itertuples() if pd.notna(r.p_clear_S2)))
    return R.show()


# ------------------------------------------------------------------------------------------------ s2
def s2(ctx=None):
    ctx = core.use(ctx); m = _need('s2', ctx); S2 = ctx.cfg['s2']
    R = Report('SENTINEL-2 COMPOSITE — report')
    st = m['stages'].get('s2_screening')
    if st and os.path.exists(st['decided_csv']):
        d = pd.read_csv(st['decided_csv'])
        R.say(f"Dates found: {len(d)}; kept: {int(d.kept.sum())}; dropped: {int((~d.kept).sum())}.")
        rc = st.get('rule_counts', {})
        rules = {'glint': ('water_nir', 'SCENE_MAX_NIR'), 'turbid': ('water_b5', 'SCENE_MAX_B5'), 'rain': ('rain_mm', 'RAIN_MAX_MM'),
                 'wind': ('wind_ms', 'WIND_MAX_MS'), 'waves': ('hs_m', 'WAVE_MAX_HS')}
        R.say('Per check (evaluated / failed / missing):')
        for k, v in rc.items():
            R.say(f"  {k:7s} {v['evaluated']:4d} / {v['failed']:4d} / {v['missing']:4d}")
            col, opt = rules[k]
            if v['evaluated'] and v['failed'] / v['evaluated'] > 0.4 and col in d:
                x = pd.to_numeric(d[col], errors='coerce').dropna()
                R.suggest(f"S2['{opt}']", round(float(x.quantile(0.7)), 3),
                          f"the {k} check drops {v['failed'] / v['evaluated']:.0%} of the dates it evaluates (threshold {S2[opt]}). "
                          f"This value keeps 70 % of them; check in the screening figure that the extra dates are acceptable")
            if v['missing'] and v['missing'] / max(len(d), 1) > 0.2:
                R.say(f"    ! {k}: {v['missing']} dates without data ({'dropped' if S2['MISSING_POLICY'].get('waves' if k == 'waves' else k if k in ('wind', 'rain') else 'water') == 'drop' else 'kept unchecked'})")
        kept = int(d.kept.sum())
        if kept < 3 * S2['MIN_VALID']:
            R.say(f"\n! Only {kept} dates kept for MIN_VALID = {S2['MIN_VALID']} clear observations per pixel: many pixels may be NoData.")
            R.suggest("S2['YEARS']", [S2['YEARS'][0] - 2, S2['YEARS'][1]], 'more years give more clear dates in the same months')
    off = _file(m, 'tile_offsets')
    if off:
        o = pd.read_csv(off)
        R.say('\nTile matching (offset of B2 blue, reflectance; overlap water pixels):')
        unsupported = []
        for r in o.itertuples():
            if r.role == 'reference': R.say(f'  {r.group}: reference'); continue
            R.say(f"  {r.group}: B2 {getattr(r, 'off_B2', 0):+.4f}, {r.n_water:.0f} px {('— ' + r.flag) if isinstance(r.flag, str) and r.flag else ''}")
            if isinstance(r.flag, str) and 'unsupported' in r.flag: unsupported.append(r.group)
            if isinstance(r.flag, str) and 'large' in r.flag:
                R.say('    ! large offset: check this seam in QGIS (bands 4-3-2) before trusting the matched values')
        if unsupported:
            R.suggest("S2['GROUPS']", 'same tiles, reordered so that each tile overlaps water of a tile listed before it',
                      f"tile(s) {', '.join(unsupported)} share too little water with the tiles before them; their offsets were set to 0, "
                      "so a seam may remain. Alternatively S2['NO_WATER_FALLBACK'] = 'all' matches them over all overlap pixels")
    qa_t = m['outputs'].get('qa_task')
    if qa_t and m['tasks'].get(qa_t, {}).get('state') == 'COMPLETED':
        import rasterio
        cnt, inv = [], []
        for f in core.task_files(qa_t):
            with rasterio.open(f) as src:
                for _, w in src.block_windows(1):
                    a = src.read(1, window=w); cnt.append(a[a >= 0].ravel()[::50])
                    if src.count >= 3:
                        b = src.read(3, window=w); inv.append(b[b >= 0].ravel()[::50])
        cnt = np.concatenate(cnt) if cnt else np.array([]); inv = np.concatenate(inv) if inv else np.array([])
        if cnt.size:
            q = np.percentile(cnt, [10, 50, 90])
            R.say(f"\nClear observations per pixel (where the composite has data): 10th/50th/90th percentile {q[0]:.0f} / {q[1]:.0f} / {q[2]:.0f}")
            if inv.size: R.say(f"Pixels with reflectance outside 0–1 after tile matching: {inv.mean():.2%}")
            if inv.size and inv.mean() > 0.01:
                R.say('  ! more than 1 % invalid reflectance: an offset pushes dark water below 0 (see the offsets table)')
    return R.show()


# ------------------------------------------------------------------------------------------------ dem / habitats / transport
def dem(ctx=None):
    ctx = core.use(ctx); m = _need('dem', ctx); R = Report('ELEVATION — report')
    for n, t in m['tasks'].items(): R.say(f"  {t.get('state', '?'):10s} {n}")
    R.say('\nCheck in QGIS: DSM − FABDEM should be ~0 on bare ground and positive under mangroves; the edit mask (EDM) '
          'shows where the 2024_1 DEM was edited, where DSM − FABDEM also contains release differences.')
    return R.show()

def habitats(ctx=None):
    ctx = core.use(ctx); m = _need('habitats', ctx); R = Report('HABITATS — report')
    f = _file(m, 'habitat_areas') or next((x['path'] for t in m['tasks'].values() for x in t.get('files', []) if 'habitat_areas' in x['path']), None)
    if f:
        a = pd.read_csv(f).drop(columns=['system:index', '.geo'], errors='ignore').iloc[0]
        R.say('Areas in the AOI (km²): ' + ', '.join(f"{k} {float(v):.2f}" for k, v in a.items() if k.endswith('km2')))
        if a.get('aca_mapped_km2', 1) and ctx.aoi_info['area_km2'] and a['aca_mapped_km2'] < 0.2 * ctx.aoi_info['area_km2']:
            R.say('  ! the Allen Coral Atlas maps less than 20 % of the AOI: seagrass and coral outside its reef extent are unmapped, not absent')
    return R.show()

def transport(ctx=None):
    ctx = core.use(ctx); m = _need('transport', ctx); TR = ctx.cfg['transport']; R = Report('WATER-MOTION OVERVIEW — report')
    for k, f in m['files'].items():
        if 'condition_support' in k and os.path.exists(f['path']):
            s = pd.read_csv(f['path']); R.say(f"\n{k}:"); R.say(s.to_string(index=False))
            low = s[(s.images < 10 * TR['MIN_SUPPORT']) & ~s.condition.str.startswith('missing')]
            for r in low.itertuples():
                R.say(f"  ! condition '{r.condition}' has only {r.images} images: its maps will be masked over much of the AOI")
    hy = m['coverage'].get('hycom')
    if hy: R.say(f"\nHYCOM support: {hy}")
    return R.show()


# ------------------------------------------------------------------------------------------------ icesat2
def icesat2(ctx=None):
    ctx = core.use(ctx); m = _need('icesat2', ctx); IS2 = ctx.cfg['icesat2']; o = m['outputs']
    R = Report('ICESat-2 — report')
    qs = o.get('qc_summary', {})
    if qs:
        tot = qs.get('total', 0)
        R.say(f"ATL24 photons in the AOI: {tot:,}; kept after quality control: {qs.get('kept', 0):,} ({qs.get('kept', 0) / max(tot, 1):.0%}).")
        hints = {'f_class': ("IS2['MIN_CONFIDENCE']", round(max(0.3, IS2['MIN_CONFIDENCE'] - 0.1), 2), 'lower confidence keeps more seabed photons (and more noise)'),
                 'f_shore': ("IS2['SHORE_BUFFER']", max(0.0, IS2['SHORE_BUFFER'] - 10), 'a smaller buffer keeps photons near the coast; check them in QGIS'),
                 'f_xtrack': ("IS2['XT_REL']", round(IS2['XT_REL'] + 0.1, 2), 'a looser cross-track tolerance keeps photons over real reef relief'),
                 'f_spike': ("IS2['SPIKE_MIN']", IS2['SPIKE_MIN'] + 0.5, 'a larger minimum keeps steep along-track changes'),
                 'f_atl24': ("IS2['MAX_SIGMA_TVU']", IS2['MAX_SIGMA_TVU'] + 0.5, 'accepts photons with a larger ATL24 vertical uncertainty')}
        for k, v in qs.items():
            if not isinstance(v, dict): continue
            share = v['flagged'] / max(v['evaluated'] or 1, 1)
            R.say(f"  {k:10s} flagged {v['flagged']:>8,} of {v['evaluated'] or 0:>8,} evaluated ({share:.0%})")
            if share > 0.3 and k in hints:
                R.suggest(*hints[k][:2], f"{k} removes {share:.0%} of the photons it evaluates; {hints[k][2]}")
    R.say(f"\nValidation tracks: {o.get('split_status')} — rule {o.get('split')}, {len(o.get('valid_rgts', []))} RGTs (lock file {o.get('lock_file')})")
    if o.get('split_status') == 'infeasible':
        R.suggest("IS2['T0']", '2018-10-13', 'not enough independent tracks for a hold-out: use the whole ICESat-2 period or a larger AOI')
    z = o.get('zsat', {})
    if z:
        R.say(f"\nDepth limit of SDB: status {z.get('status')}, z_sat = {z.get('z_sat')} m, track bootstrap 5–95 %: {z.get('z_p05')}–{z.get('z_p95')} m")
        if z.get('status') in ('insufficient_data', 'no_plateau', 'unstable', 'no_depth_signal'):
            R.suggest("IS2['SDB_MIN_PER_BIN']", max(10, IS2['SDB_MIN_PER_BIN'] // 2),
                      'the depth limit was not found; fewer photons per depth bin (or a larger SDB_FLAT_TOL) may resolve it — then check the figure')
        elif z.get('z_p05') is not None and z['z_p95'] - z['z_p05'] > 3:
            R.say('  ! the depth limit varies by more than 3 m between track resamples: treat depths near it with caution')
    mc = o.get('mask_counts', {})
    for k, c in mc.items():
        tot = sum(v for kk, v in c.items() if kk != 'not_assessed')
        if tot: R.say(f"Optical map {k}: shallow {c['shallow'] / tot:.0%}, deep {c['deep'] / tot:.0%}, unknown {c['unknown'] / tot:.0%} of assessed water")
    g = o.get('geoid', {})
    if g:
        R.say(f"\nATL08 geoid conversion: {g.get('status')}" + ('' if g.get('status') == 'verified' else ' — EGM2008 heights not produced; re-run when the PROJ grid can be downloaded'))
    q8 = o.get('atl08_qc')
    if q8:
        R.say(f"ATL08 segments in mangroves: {q8['total']}, kept {q8['kept']} (few ground photons: {q8['few_ground']})")
        if q8['total'] and q8['few_ground'] / q8['total'] > 0.5:
            R.suggest("IS2['MIN_GROUND_PH']", max(2, IS2['MIN_GROUND_PH'] - 2), 'more than half of the segments have too few ground photons under the canopy')
    return R.show()
