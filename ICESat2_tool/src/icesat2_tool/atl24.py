"""ATL24 bathymetry: download, quality control, locked training / validation tracks, cross-track consistency.

ICESat-2 is downloaded with [SlideRule](https://slideruleearth.io) (no login needed); cleaning is done here.

**Order of operations (why it matters).** Validation must not help decide how the data are cleaned, otherwise
validation errors look better than they are. So:

1. **download** ATL24 year by year (retries, per-year cache, coverage table), full schema (`compact: False`);
   required fields are checked and missing or non-finite values are flagged, never passed;
2. **independent QC**, using no information from other tracks: ATL24 class / confidence and product flags, depth
   bounds, land and distance to the shore (only with SHORELINE_FILE), along-track spikes;
3. **reserve validation tracks**: whole reference ground tracks (RGTs) go to validation by a rule
   `rgt % m == k`, chosen once and **locked** in a JSON file; later runs re-use it (new RGTs follow the same rule);
   if no feasible split exists, no training / validation files are written (never a random point split);
4. **cross-track consistency** of each photon against **training passes only**; validation photons get the flag
   for information but are not removed (`XT_APPLY_TO_VALID = False`);
5. **exports** (GeoPackages for QGIS and Bathymetrix-AI), coverage tables, figures, README.

| Flag | Test |
|---|---|
| `f_missing` | a required value (`ortho_h`, `surface_h`, `class_ph`, `confidence`, ATL24 QC fields) is missing or not finite |
| `f_class` | `class_ph` != 40 (seabed) or `confidence` < MIN_CONFIDENCE |
| `f_atl24` | `low_confidence_flag`, `invalid_kd`, `sensor_depth_exceeded` set, or `sigma_tvu` > MAX_SIGMA_TVU |
| `f_depth` | depth < DEPTH_MIN or > DEPTH_MAX |
| `f_land` / `f_shore` | on land, or closer than SHORE_BUFFER to it (only with SHORELINE_FILE) |
| `f_spike` | > max(SPIKE_MIN, 3 x running MAD) from the along-track running median |
| `f_xtrack` | > max(XT_MIN, XT_REL x depth) from the median of >= XT_MIN_PASSES other training passes within XT_RADIUS |

**Depth and datum.** `ortho_h` is the seabed elevation relative to EGM2008 (negative below the geoid): the
Bathymetrix-AI training field. `depth = surface_h - ortho_h` is the instantaneous water depth. EGM2008 is neither
local mean sea level nor chart datum, and the tide at each pass is not removed.
"""
import os, json, datetime as dt
import numpy as np
import pandas as pd
import geopandas as gpd
import matplotlib.pyplot as plt
from scipy import stats
from scipy.spatial import cKDTree
from .core import (sliderule_years, sliderule_versions, read_polygons, figure_style, save_fig, empty_panel, write_gpkg,
                   OKABE_ITO)
from .options import check

REQUIRED = ['ortho_h', 'surface_h', 'class_ph', 'confidence', 'rgt', 'cycle']
QC_ALIASES = {'sigma_tvu': ['sigma_tvu'], 'invalid_kd': ['invalid_kd'], 'sensor_depth_exceeded': ['sensor_depth_exceeded'],
              'low_confidence_flag': ['low_confidence_flag', 'low_conf_flag']}
INDEP = ['f_missing', 'f_class', 'f_atl24', 'f_depth', 'f_land', 'f_shore', 'f_spike']
FLAGS = INDEP + ['f_xtrack']


def normalise(g):
    rep = dict(columns=list(map(str, g.columns)), missing_required=[], missing_qc=[], aliases_used={})
    for canon, al in QC_ALIASES.items():
        hit = next((a for a in al if a in g.columns), None)
        if hit is None: rep['missing_qc'].append(canon)
        elif hit != canon: g = g.rename(columns={hit: canon}); rep['aliases_used'][hit] = canon
    rep['missing_required'] = [k for k in REQUIRED if k not in g.columns]
    for k in REQUIRED + list(QC_ALIASES):
        if k in g: g[k] = pd.to_numeric(g[k], errors='coerce')
    return g, rep


def shore_distance(ctx, x, y, path):
    """(distance to land in m, on-land 1/0 or NaN, description). Land polygons: exact; lines: distance only."""
    import shapely
    if not path:
        n = len(x); return np.full(n, np.nan), np.full(n, np.nan), 'not applied (no SHORELINE_FILE)'
    g = read_polygons(path, 'SHORELINE_FILE').to_crs(ctx.crs).explode(index_parts=False)
    pts = shapely.points(x, y)
    is_poly = g.geom_type.isin(['Polygon', 'MultiPolygon'])
    geoms = g.geometry.values
    tree = shapely.STRtree(geoms)
    _, dist = tree.query_nearest(pts, return_distance=True, all_matches=False)
    if is_poly.all():
        return dist, (dist == 0).astype(float), f'land polygons {os.path.basename(path)} (exact distance)'
    if (~is_poly).all():
        return dist, np.full(len(x), np.nan), f'coastline lines {os.path.basename(path)} (distance only; on-land not tested)'
    poly_tree = shapely.STRtree(geoms[is_poly.values])
    _, dpoly = poly_tree.query_nearest(pts, return_distance=True, all_matches=False)
    return dist, (dpoly == 0).astype(float), f'shoreline file {os.path.basename(path)} (polygons + lines)'


def choose_holdout(df, c):
    rg = df['rgt'].astype(int)
    n_rgt = rg.nunique()
    diag = dict(n_rgt=int(n_rgt), photons_per_rgt=rg.value_counts().sort_index().to_dict())
    if n_rgt < c['MIN_RGT_TOTAL']:
        return None, dict(diag, reason=f"only {n_rgt} RGTs (< MIN_RGT_TOTAL {c['MIN_RGT_TOTAL']})")
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


def xtrack(df, c):
    d = df[df.qc_indep_ok].drop(columns=['xt_ref_depth', 'xt_n_passes', 'xt_ref_dist_m', 'f_xtrack'], errors='ignore').copy()
    d['bx'] = np.floor(d.geometry.x / c['XT_BIN']).astype(np.int64); d['by'] = np.floor(d.geometry.y / c['XT_BIN']).astype(np.int64)
    d['ex'], d['ey'] = d.geometry.x, d.geometry.y
    B = d.groupby(['track_id', 'bx', 'by']).agg(depth=('depth', 'median'), x=('ex', 'mean'), y=('ey', 'mean'),
                                                  pass_id=('pass_id', 'first'), set=('set', 'first')).reset_index()
    ref = B[B.set != 'valid'].reset_index(drop=True)
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
    keep_idx = d.index
    d = d.merge(B[['track_id', 'bx', 'by', 'xt_ref_depth', 'xt_n_passes', 'xt_ref_dist_m']], on=['track_id', 'bx', 'by'], how='left')
    d.index = keep_idx
    r_ = d['xt_ref_depth'].values.astype(float)
    d['f_xtrack'] = np.isfinite(r_) & (np.abs(d['depth'].values - r_) > np.maximum(c['XT_MIN'], c['XT_REL'] * r_))
    return d[['xt_ref_depth', 'xt_n_passes', 'xt_ref_dist_m', 'f_xtrack']], int(np.isfinite(r_).sum())


KEEP = ['time', 'rgt', 'cycle', 'spot', 'gt', 'pass_id', 'track_id', 'set', 'ortho_h', 'surface_h', 'depth', 'confidence',
        'sigma_tvu', 'sigma_thu', 'class_ph', 'low_confidence_flag', 'invalid_kd', 'sensor_depth_exceeded', 'dist_shore_m',
        'qc_indep_ok', 'qc_ok', *FLAGS, 'xt_ref_depth', 'xt_n_passes', 'xt_ref_dist_m', 'geometry']


def run(ctx, options=None):
    c = check('atl24', options); ctx.opts['atl24'] = c
    figure_style()
    t1 = c['T1'] or ctx.today.isoformat()
    lock_path = c['HOLDOUT_LOCK'] or ctx.path(f'{ctx.name}_ICESat2_holdout_lock.json')
    out = dict(sliderule=sliderule_versions(), period=[c['T0'], t1])
    print('1. Downloading ATL24 (SlideRule, full schema) ...')
    a, cov = sliderule_years(ctx, 'atl24x', {'atl24': {'compact': False}}, c['T0'], t1, c['SR_RETRIES'])
    cov.to_csv(ctx.path(f'{ctx.name}_ATL24_download_coverage.csv'), index=False)
    failed = cov.loc[cov.status == 'failed', 'year'].tolist()
    if failed: print(f'  WARNING: years without data because the request failed: {failed} (run again later: the other years are cached)')
    if a is None or a.empty:
        raise RuntimeError('No ATL24 data returned for the AOI (see the coverage table)')
    a, schema = normalise(a); out['schema'] = schema
    if schema['missing_required']:
        raise RuntimeError(f"ATL24 response lacks required fields {schema['missing_required']}; got {schema['columns']}")
    if schema['missing_qc'] and c['ON_MISSING_QC_FIELD'] == 'fail':
        raise RuntimeError(f"ATL24 response lacks QC fields {schema['missing_qc']}. Columns: {schema['columns']}. "
                           "Set ATL24['ON_MISSING_QC_FIELD'] = 'quarantine' to continue with every photon flagged.")
    a = a[a.intersects(ctx.aoi)].copy().reset_index(drop=True)
    print(f"  {len(a):,} ATL24 photons inside the AOI; {len(schema['columns'])} fields; aliases: {schema['aliases_used'] or 'none'}")
    if not len(a): raise RuntimeError('No ATL24 photons inside the AOI polygon')
    a['depth'] = a['surface_h'] - a['ortho_h']
    a['spot'] = a['spot'] if 'spot' in a else a.get('gt', 0)
    a['rgt'] = a['rgt'].astype('Int64'); a['cycle'] = a['cycle'].astype('Int64')
    a['pass_id'] = a['rgt'].astype(str) + '_' + a['cycle'].astype(str)
    a['track_id'] = a['pass_id'] + '_' + a['spot'].astype(str)
    a = a.to_crs(ctx.crs)
    x, y = a.geometry.x.values, a.geometry.y.values

    print('2. Independent quality control ...')
    F = pd.DataFrame(index=a.index); EVAL = {}
    num = lambda k: a[k].values.astype(float) if k in a else np.full(len(a), np.nan)
    req = ['ortho_h', 'surface_h', 'class_ph', 'confidence'] + [k for k in QC_ALIASES if k in a]
    fin = np.column_stack([np.isfinite(num(k)) for k in req])
    F['f_missing'] = ~fin.all(axis=1) | bool(schema['missing_qc']); EVAL['f_missing'] = len(a)
    cls, conf = num('class_ph'), num('confidence')
    ok = np.isfinite(cls) & np.isfinite(conf)
    F['f_class'] = ok & ((cls != 40) | (conf < c['MIN_CONFIDENCE'])); EVAL['f_class'] = int(ok.sum())
    f = np.zeros(len(a), bool); ev = np.zeros(len(a), bool)
    for flag in ['low_confidence_flag', 'invalid_kd', 'sensor_depth_exceeded']:
        v = num(flag); f |= np.isfinite(v) & (v != 0); ev |= np.isfinite(v)
    sig = num('sigma_tvu'); f |= np.isfinite(sig) & (sig > c['MAX_SIGMA_TVU']); ev |= np.isfinite(sig)
    F['f_atl24'] = f; EVAL['f_atl24'] = int(ev.sum())
    dep = a['depth'].values.astype(float)
    F['f_depth'] = np.isfinite(dep) & ((dep < c['DEPTH_MIN']) | (dep > c['DEPTH_MAX'])); EVAL['f_depth'] = int(np.isfinite(dep).sum())
    dist, in_land, shore_src = shore_distance(ctx, x, y, c['SHORELINE_FILE'])
    a['dist_shore_m'] = dist
    F['f_land'] = np.isfinite(in_land) & (in_land == 1)
    F['f_shore'] = ~F['f_land'] & np.isfinite(dist) & (dist < c['SHORE_BUFFER'])
    EVAL['f_land'] = int(np.isfinite(in_land).sum()); EVAL['f_shore'] = int(np.isfinite(dist).sum())
    out['shoreline'] = shore_src
    if not c['SHORELINE_FILE']:
        print('  no SHORELINE_FILE: land / shore rules not applied (ATL24 classification, depth and spike rules still apply)')
    order = 'x_atc' if 'x_atc' in a else 'time'
    spike = pd.Series(False, index=a.index)
    base = ~(F[['f_missing', 'f_class', 'f_atl24', 'f_depth', 'f_land']].any(axis=1))
    for _, g in a[base].sort_values(order).groupby('track_id'):
        med = g['depth'].rolling(c['SPIKE_WINDOW'], center=True, min_periods=5).median()
        mad = (g['depth'] - med).abs().rolling(c['SPIKE_WINDOW'], center=True, min_periods=5).median()
        spike.loc[g.index] = ((g['depth'] - med).abs() > np.maximum(c['SPIKE_MIN'], 3 * 1.4826 * mad)).fillna(False)
    F['f_spike'] = spike; EVAL['f_spike'] = int(base.sum())
    a = a.join(F)
    a['qc_indep_ok'] = ~F[INDEP].any(axis=1)
    print('  photons evaluated / flagged per rule:', {k: (EVAL[k], int(F[k].sum())) for k in INDEP})
    print(f"  passing independent QC: {int(a.qc_indep_ok.sum()):,} of {len(a):,}")

    pre = a[a.qc_indep_ok]
    rgts_now = sorted(pre['rgt'].astype(int).unique().tolist())
    if os.path.exists(lock_path):
        lock = json.load(open(lock_path))
        new = [r for r in rgts_now if r not in lock['all_rgts']]
        if new:
            lock['valid_rgts'] = sorted(set(lock['valid_rgts']) | {r for r in new if r % lock['mod'] == lock['off']})
            lock['all_rgts'] = sorted(set(lock['all_rgts']) | set(new))
            lock.setdefault('history', []).append(dict(added_rgts=new, utc=dt.datetime.now(dt.timezone.utc).isoformat()))
            json.dump(lock, open(lock_path, 'w'), indent=1)
        print(f"3. Validation tracks: lock re-used ({lock_path}): rgt % {lock['mod']} == {lock['off']}; {len(new)} new RGTs assigned by the rule")
        split_status = 'locked'
    else:
        rule, diag = choose_holdout(pre, c)
        if rule is None:
            lock, split_status = None, 'infeasible'
            print('3. NO FEASIBLE TRACK SPLIT:', diag['reason']); print('   photons per RGT:', diag['photons_per_rgt'])
            print('   -> training / validation files are NOT written. Extend the period, enlarge the AOI, or validate with echosounder data.')
            out['split_diag'] = diag
        else:
            lock = dict(created_utc=dt.datetime.now(dt.timezone.utc).isoformat(), **rule,
                        valid_rgts=[r for r in rgts_now if r % rule['mod'] == rule['off']], all_rgts=rgts_now,
                        note='Chosen once before cross-track QC; do not retune after seeing results.')
            json.dump(lock, open(lock_path, 'w'), indent=1)
            split_status = 'new_lock'
            print(f"3. Validation tracks chosen and LOCKED: rgt % {rule['mod']} == {rule['off']} "
                  f"({rule['share']:.0%} of photons, depth KS {rule['ks']:.2f}) -> {lock_path}")
    a['set'] = 'unsplit'
    if lock:
        a['set'] = 'train'; a.loc[a['rgt'].astype(int).isin(lock['valid_rgts']), 'set'] = 'valid'
    out.update(split_status=split_status, split=(f"rgt % {lock['mod']} == {lock['off']}" if lock else None),
               lock_file=lock_path, valid_rgts=lock['valid_rgts'] if lock else [])

    print('4. Cross-track consistency (training passes as reference) ...')
    for k in ('xt_ref_depth', 'xt_n_passes', 'xt_ref_dist_m'): a[k] = np.nan
    a['f_xtrack'] = False
    if a.qc_indep_ok.any():
        xt, n_eval = xtrack(a, c)
        a.loc[xt.index, ['xt_ref_depth', 'xt_n_passes', 'xt_ref_dist_m']] = xt[['xt_ref_depth', 'xt_n_passes', 'xt_ref_dist_m']].values
        a.loc[xt.index, 'f_xtrack'] = xt['f_xtrack'].values.astype(bool)
    else:
        n_eval = 0
    a['f_xtrack'] = a['f_xtrack'].astype(bool); EVAL['f_xtrack'] = n_eval
    apply_xt = a['f_xtrack'] & ((a['set'] != 'valid') | c['XT_APPLY_TO_VALID'])
    a['qc_ok'] = a['qc_indep_ok'] & ~apply_xt
    print(f"  evaluated {n_eval:,} photons (with enough reference passes); flagged {int(a.f_xtrack.sum()):,} "
          f"(train {int((a.f_xtrack & (a.set != 'valid')).sum()):,}, valid {int((a.f_xtrack & (a.set == 'valid')).sum()):,}"
          f"{' - for information only on validation tracks' if not c['XT_APPLY_TO_VALID'] else ''})")
    summary = {k: dict(evaluated=EVAL.get(k), flagged=int(a[k].sum())) for k in FLAGS}
    summary['kept'] = int(a.qc_ok.sum()); summary['total'] = len(a)
    out['qc_summary'] = summary

    print('5. Files ...')
    write_gpkg(ctx, a, 'ATL24_all_with_QC_flags', KEEP)
    use = a[a.qc_ok]
    report = pd.DataFrame()
    if lock:
        rows = []
        for s in ('train', 'valid'):
            sub = use[use.set == s]
            write_gpkg(ctx, sub, f'ATL24_{s}', KEEP)
            alls = a[a.set == s]
            rows.append(dict(set=s, photons=len(sub), rgts=int(sub.rgt.nunique()), passes=int(sub.pass_id.nunique()),
                             depth_min=float(sub.depth.min()) if len(sub) else None, depth_max=float(sub.depth.max()) if len(sub) else None,
                             depth_median=float(sub.depth.median()) if len(sub) else None,
                             **{f'excluded_{k}': int(alls[k].sum()) for k in FLAGS}))
        report = pd.DataFrame(rows)
        report.to_csv(ctx.path(f'{ctx.name}_ATL24_train_valid_coverage.csv'), index=False)
        assert not set(use[use.set == 'train'].rgt.astype(int)) & set(use[use.set == 'valid'].rgt.astype(int)), 'RGT in both sets'
        print(report[['set', 'photons', 'rgts', 'passes', 'depth_min', 'depth_median', 'depth_max']].to_string(index=False))
        print(f'  written: {ctx.name}_ATL24_all_with_QC_flags.gpkg, _ATL24_train.gpkg, _ATL24_valid.gpkg (+ coverage CSV)')
    else:
        print(f'  written: {ctx.name}_ATL24_all_with_QC_flags.gpkg only (no feasible track split)')
    figure(ctx, a, use, summary, out, c, t1)
    readme(ctx, c, t1, out, report, failed)
    ctx.data.update(atl24=a, atl24_summary=out, atl24_report=report)
    ctx.note('atl24', dict(period=[c['T0'], t1], sliderule=out['sliderule'], schema_missing_qc=schema['missing_qc'],
                           shoreline=shore_src, split=out['split'], failed_years=failed))
    return ctx


def figure(ctx, a, use, summary, out, c, t1):
    aoi = gpd.GeoSeries([ctx.aoi], crs='EPSG:4326').to_crs(ctx.crs)
    fig = plt.figure(figsize=(7.2, 5.6), constrained_layout=True)
    gs = fig.add_gridspec(2, 2, width_ratios=[1.4, 1])
    ax = fig.add_subplot(gs[:, 0])
    aoi.boundary.plot(ax=ax, color='k', lw=0.6)
    bad = a[~a.qc_ok]
    ax.scatter(bad.geometry.x, bad.geometry.y, s=0.3, color='0.75', label='rejected (QC)', rasterized=True)
    if len(use):
        sc = ax.scatter(use.geometry.x, use.geometry.y, c=use.depth, s=0.4, cmap='viridis_r', vmin=0,
                        vmax=np.nanpercentile(use.depth, 98), rasterized=True)
        fig.colorbar(sc, ax=ax, shrink=0.6, label='depth (m)')
        vv = use[use.set == 'valid']
        ax.scatter(vv.geometry.x, vv.geometry.y, s=0.2, facecolors='none', edgecolors=OKABE_ITO[1], lw=0.2,
                   label='validation tracks', rasterized=True)
    ax.set_aspect('equal'); ax.set_xlabel('Easting (m)'); ax.set_ylabel('Northing (m)')
    ax.ticklabel_format(style='plain'); ax.tick_params(axis='x', rotation=30)
    ax.legend(loc='upper center', bbox_to_anchor=(0.5, -0.2), ncol=3, markerscale=5)
    ax.set_title(f"ICESat-2 ATL24, {c['T0'][:4]}–{t1[:4]}", loc='left')
    axb = fig.add_subplot(gs[0, 1])
    cnt = [summary[f]['flagged'] for f in FLAGS]; ev_ = [summary[f]['evaluated'] or 0 for f in FLAGS]
    axb.barh(range(len(FLAGS)), cnt, color=OKABE_ITO[3], alpha=0.8); axb.set_yticks(range(len(FLAGS)))
    axb.set_yticklabels([f'{f[2:]} (of {e:,})' for f, e in zip(FLAGS, ev_)], fontsize=6.5); axb.invert_yaxis()
    axb.set_xlabel('photons flagged'); axb.set_title(f"kept {summary['kept']:,} of {summary['total']:,}", loc='left')
    axc = fig.add_subplot(gs[1, 1])
    if out['split'] and len(use):
        bins = np.arange(0, use.depth.max() + 1, 1)
        for s, col_ in (('train', OKABE_ITO[0]), ('valid', OKABE_ITO[1])):
            axc.hist(use.depth[use.set == s], bins=bins, density=True, histtype='step', lw=1.2, color=col_,
                     label=f"{s} ({(use.set == s).sum():,}; {use[use.set == s].rgt.nunique()} RGTs)")
        axc.set_xlabel('depth (m)'); axc.set_ylabel('density'); axc.legend(); axc.set_title(f"locked: {out['split']}", loc='left')
    else:
        empty_panel(axc, 'no feasible track split')
    save_fig(ctx, fig, 'Fig_ATL24_QC_split'); plt.show()


def readme(ctx, c, t1, out, report, failed):
    qs = out['qc_summary']
    vr = report.to_markdown(index=False) if len(report) else 'no feasible split'
    txt = f"""# ICESat-2 ATL24 bathymetry — {ctx.name}

## Files
| File | Content |
|---|---|
| `{ctx.name}_ATL24_all_with_QC_flags.gpkg` | all ATL24 photons in the AOI: `set` (train / valid / unsplit), flags `f_*`, `qc_indep_ok`, `qc_ok`, cross-track reference (`xt_*`), `dist_shore_m` |
| `{ctx.name}_ATL24_train.gpkg`, `{ctx.name}_ATL24_valid.gpkg` | {'clean photons, split by locked RGTs' if out['split'] else '**not written: no feasible track split**'}. **Depth field for Bathymetrix-AI: `ortho_h`** (m, EGM2008, negative = below); `depth` = instantaneous water depth (positive) |
| `{ctx.name}_ATL24_train_valid_coverage.csv` | per set: photons, RGTs, passes, depth range, exclusions per rule |
| `{ctx.name}_ATL24_download_coverage.csv` | requested vs returned per year (ok / empty / failed, attempts) |
| `{ctx.name}_ICESat2_holdout_lock.json` | the locked validation rule and RGTs |
| `figures/{ctx.name}_Fig_ATL24_QC_split.png/.pdf` | map, flags, depth distributions |

## Data ({c['T0']} – {t1})
SlideRule {json.dumps(out['sliderule'])}; ATL24 via `atl24x`, `compact: False`. Missing QC fields: {out['schema']['missing_qc'] or 'none'}.
Years that failed after {c['SR_RETRIES']} attempts: {failed or 'none'}.

## Quality control
f_missing; f_class (class_ph ≠ 40 or confidence < {c['MIN_CONFIDENCE']}); f_atl24 (low_confidence_flag / invalid_kd / sensor_depth_exceeded, or sigma_tvu > {c['MAX_SIGMA_TVU']} m);
f_depth (< {c['DEPTH_MIN']} or > {c['DEPTH_MAX']} m); f_land / f_shore (< {c['SHORE_BUFFER']} m; {out['shoreline']}); f_spike (> max({c['SPIKE_MIN']} m, 3·MAD), {c['SPIKE_WINDOW']}-point running median);
f_xtrack (> max({c['XT_MIN']} m, {c['XT_REL']:.0%}) from the median of ≥ {c['XT_MIN_PASSES']} other training passes within {c['XT_RADIUS']} m; {'applied to validation too' if c['XT_APPLY_TO_VALID'] else 'information only on validation tracks'}).
Evaluated / flagged: `{json.dumps(qs)}`

## Validation tracks
Status **{out['split_status']}**; rule `{out['split']}`; lock `{out['lock_file']}` (chosen once, before cross-track QC; re-used by later runs).

{vr}

Keep datum-aligned echosounder data as the final external check; never use validation tracks for Bathymetrix-AI residual correction (Phase 4).

## Limitations
- `ortho_h` is EGM2008, not local MSL or chart datum; the tide at each pass is not removed (decimetres in a microtidal setting).
- Without a shoreline file, land and shore photons are only removed by ATL24's own classification and the depth / spike rules.
- Thresholds are starting values: inspect the `f_*` columns in QGIS. Cross-track agreement can remove real relief or seabed change.

## Sources
ICESat-2 ATL24 (NSIDC, doi:10.5067/ATLAS/ATL24.001) via SlideRule (Shean et al. 2023, JOSS 8(81):4982).
"""
    open(ctx.path(f'README_{ctx.name}_ATL24.md'), 'w').write(txt)
