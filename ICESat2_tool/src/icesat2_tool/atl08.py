"""ATL08 / PhoREAL land segments: ground elevation and canopy height (e.g. over mangroves).

SlideRule's ATL08 / PhoREAL processing gives, per ATL08_LEN-m segment, the ground height (WGS84 ellipsoid) and
canopy heights above ground. Only segments SlideRule considers valid are requested (`pass_invalid: False`).
Field names differ between SlideRule versions (`gnd_count` / `ground_photon_count`, ...): they are normalised and
segments with missing or non-finite values are flagged, never passed.

With MANGROVE_FILE (e.g. Global Mangrove Watch polygons cut to the AOI) only segments inside the polygons
(+ MANGROVE_BUFFER_M) are kept; without it, all land segments in the AOI.

**Geoid conversion is verified, not assumed.** Ellipsoid -> EGM2008 must be a real grid-based PROJ operation (not the
no-shift "ballpark" fallback used when the grid is missing); the grid is downloaded if needed. If the conversion
cannot be verified, `ground_h_egm08` stays empty, no segment is certified and DEM comparisons are skipped.
"""
import os, json
import numpy as np
import pandas as pd
import geopandas as gpd
import matplotlib.pyplot as plt
from .core import sliderule_years, read_polygons, figure_style, save_fig, empty_panel, write_gpkg, OKABE_ITO
from .options import check

ALIASES = {'n_ground_ph': ['gnd_count', 'ground_photon_count'], 'n_veg_ph': ['veg_count', 'vegetation_photon_count'],
           'ground_h_ellipsoid': ['h_te_median', 'h_te_best_fit', 'h_te_mean']}


def geoid_transformer(lon0, lat0):
    """Verified ellipsoid (EPSG:4979) -> EGM2008 (EPSG:4326+3855) transformer, or (None, report)."""
    from pyproj import network
    from pyproj.transformer import TransformerGroup
    network.set_network_enabled(True)
    rep = dict(status='failed')
    try:
        tg = TransformerGroup('EPSG:4979', 'EPSG:4326+3855', always_xy=True)
        if not tg.best_available:
            try:
                tg.download_grids(verbose=False); tg = TransformerGroup('EPSG:4979', 'EPSG:4326+3855', always_xy=True)
            except Exception as e:
                rep['download_error'] = str(e)[:200]
        rep['unavailable'] = [str(u)[:120] for u in tg.unavailable_operations][:3]
        for t in tg.transformers:
            if 'ballpark' in t.description.lower(): continue
            _, _, h0 = t.transform(lon0, lat0, 0.0, errcheck=True)
            if np.isfinite(h0) and abs(h0) > 0.1:                 # a real geoid gives a non-zero undulation
                rep.update(status='verified', description=t.description, undulation_m=float(-h0)); return t, rep
        rep['reason'] = 'only ballpark / zero-shift operations available'
    except Exception as e:
        rep['error'] = str(e)[:200]
    return None, rep


def dem_values(path, xs, ys, crs):
    import rasterio
    from pyproj import Transformer
    vals = np.full(len(xs), np.nan)
    with rasterio.open(path) as src:
        x_, y_ = (xs, ys) if str(src.crs) == str(crs) else Transformer.from_crs(crs, src.crs, always_xy=True).transform(xs, ys)
        x_, y_ = np.asarray(x_), np.asarray(y_)
        ins = (x_ >= src.bounds.left) & (x_ <= src.bounds.right) & (y_ >= src.bounds.bottom) & (y_ <= src.bounds.top)
        if ins.any():
            v = np.array([s[0] for s in src.sample(zip(x_[ins], y_[ins]))], float)
            nd = src.nodata if src.nodata is not None else -9999
            v[(v == nd) | (v <= -9000)] = np.nan
            vals[ins] = v
    return vals


def run(ctx, options=None):
    c = check('atl08', options); ctx.opts['atl08'] = c
    if not c['RUN']:
        print('ATL08 RUN = False: skipped'); return ctx
    from sliderule import icesat2
    figure_style()
    t1 = c['T1'] or ctx.today.isoformat()
    print('Downloading ATL08 / PhoREAL (SlideRule) ...')
    parms = {'srt': icesat2.SRT_LAND, 'len': c['ATL08_LEN'], 'res': c['ATL08_LEN'], 'pass_invalid': False,
             'atl08_class': ['atl08_ground', 'atl08_canopy', 'atl08_top_of_canopy'],
             'phoreal': {'binsize': 1.0, 'geoloc': 'center', 'use_abs_h': False, 'send_waveform': False}}
    v, cov = sliderule_years(ctx, 'atl08p', parms, c['T0'], t1, c['SR_RETRIES'], fn=icesat2.atl08p)
    cov.to_csv(ctx.path(f'{ctx.name}_ATL08_download_coverage.csv'), index=False)
    if v is None or v.empty:
        print('  no ATL08 segments returned'); return ctx
    v = v[v.intersects(ctx.aoi)].copy().reset_index(drop=True)
    found = {}
    for canon, al in ALIASES.items():
        hit = next((x for x in al if x in v), None); found[canon] = hit
        v[canon] = pd.to_numeric(v[hit], errors='coerce') if hit else np.nan
    print('  field mapping:', found)
    if c['MANGROVE_FILE']:
        m = read_polygons(c['MANGROVE_FILE'], 'MANGROVE_FILE').to_crs(ctx.crs)
        zone = m[m.geom_type.isin(['Polygon', 'MultiPolygon'])].buffer(c['MANGROVE_BUFFER_M'])
        zone = zone.union_all() if hasattr(zone, 'union_all') else zone.unary_union
        vu = v.to_crs(ctx.crs)
        v = v[vu.intersects(zone).values].copy().reset_index(drop=True)
        where = f"inside {os.path.basename(c['MANGROVE_FILE'])} (+{c['MANGROVE_BUFFER_M']} m)"
    else:
        where = 'all land segments in the AOI (no MANGROVE_FILE)'
    print(f'  {len(v):,} segments {where}')
    if not len(v): return ctx
    cen = ctx.aoi.centroid
    T, GEO = geoid_transformer(cen.x, cen.y)
    v['ground_h_egm08'] = np.nan
    if T is not None:
        _, _, hh = T.transform(v.geometry.x.values, v.geometry.y.values, v['ground_h_ellipsoid'].values)
        v['ground_h_egm08'] = np.where(np.isfinite(hh) & (np.abs(hh) < 1e4), hh, np.nan)
        print(f"  geoid conversion verified: {GEO['description']} (N = {GEO['undulation_m']:+.2f} m at the AOI centre)")
    else:
        print('  WARNING: EGM2008 conversion NOT verified', GEO, '-> ground_h_egm08 empty, nothing certified')
    v['geoid_status'] = GEO['status']
    v['f_missing'] = ~np.isfinite(v['n_ground_ph']) | ~np.isfinite(v['ground_h_ellipsoid'])
    v['f_few_ground'] = np.isfinite(v['n_ground_ph']) & (v['n_ground_ph'] < c['MIN_GROUND_PH'])
    hge = v['ground_h_egm08'].values
    v['f_ground_range'] = np.isfinite(hge) & ((hge < c['GROUND_RANGE'][0]) | (hge > c['GROUND_RANGE'][1]))
    v['qc_ok'] = ~(v.f_missing | v.f_few_ground | v.f_ground_range) & (T is not None)
    v['night'] = pd.to_numeric(v.get('solar_elevation', pd.Series(np.nan, index=v.index)), errors='coerce') < 0
    q = dict(total=len(v), missing=int(v.f_missing.sum()), few_ground=int(v.f_few_ground.sum()),
             out_of_range=int(v.f_ground_range.sum()), kept=int(v.qc_ok.sum()))
    print('  QC:', q)
    vu = v.to_crs(ctx.crs); xs, ys = vu.geometry.x.values, vu.geometry.y.values
    dem_cols = []
    for nm, p in (c['DEM_FILES'] or {}).items():
        col = f'dem_{nm}'; v[col] = dem_values(p, xs, ys, ctx.crs); dem_cols.append(col)
    keep = ['time', 'rgt', 'cycle', 'spot', 'ground_h_ellipsoid', 'ground_h_egm08', 'geoid_status', 'h_canopy', 'h_max_canopy',
            'h_mean_canopy', 'canopy_openness', 'n_ground_ph', 'n_veg_ph', 'solar_elevation', 'night', 'f_missing',
            'f_few_ground', 'f_ground_range', 'qc_ok', *dem_cols, 'geometry']
    p = write_gpkg(ctx, v, 'ATL08_ground_canopy', keep)
    print(f'  written: {os.path.basename(p)}')
    # figure
    qq = v[v.qc_ok] if T is not None else v[~v.f_missing & ~v.f_few_ground]
    fig, axs = plt.subplots(1, 3, figsize=(7.2, 2.7), constrained_layout=True)
    hcol = 'ground_h_egm08' if T is not None else 'ground_h_ellipsoid'
    if qq[hcol].notna().any():
        axs[0].hist(qq[hcol].dropna(), bins=40, color=OKABE_ITO[2], alpha=0.85, edgecolor='white', lw=0.3)
    axs[0].axvline(0, color='k', lw=0.6)
    axs[0].set_xlabel('ground elevation (m, ' + ('EGM2008)' if T is not None else 'ELLIPSOID - geoid not verified)')); axs[0].set_ylabel('segments')
    hc = next((k for k in ['h_canopy', 'h_max_canopy'] if k in qq), None)
    if hc and pd.to_numeric(qq[hc], errors='coerce').notna().any():
        axs[1].hist(pd.to_numeric(qq[hc], errors='coerce').dropna(), bins=40, color=OKABE_ITO[0], alpha=0.85, edgecolor='white', lw=0.3)
        axs[1].set_xlabel(f'canopy height above ground (m, {hc})')
    else:
        empty_panel(axs[1], 'no canopy field')
    diffs, labs = [], []
    if T is not None:
        for col in dem_cols:
            d = (qq[col] - qq.ground_h_egm08).dropna()
            if len(d) > 10: diffs.append(d.values); labs.append(col[4:])
    if diffs:
        axs[2].boxplot(diffs, showfliers=False, patch_artist=True, boxprops=dict(facecolor=OKABE_ITO[5], alpha=0.7), medianprops=dict(color='k'))
        axs[2].set_xticks(range(1, len(labs) + 1)); axs[2].set_xticklabels(labs); axs[2].axhline(0, color='k', lw=0.6)
        axs[2].set_ylabel('DEM − ICESat-2 ground (m)')
    else:
        empty_panel(axs[2], 'no DEM_FILES given' if T is not None else 'geoid not verified')
    fig.suptitle(f'ICESat-2 ATL08 (PhoREAL): {len(qq):,} segments, {where}', fontsize=9)
    save_fig(ctx, fig, 'Fig_ATL08_ground_canopy'); plt.show()
    dem_cmp = {l: dict(median=float(np.median(d)), n=len(d)) for l, d in zip(labs, diffs)}
    open(ctx.path(f'README_{ctx.name}_ATL08.md'), 'w').write(f"""# ICESat-2 ATL08 ground and canopy — {ctx.name}

`{ctx.name}_ATL08_ground_canopy.gpkg`: {c['ATL08_LEN']} m PhoREAL segments ({c['T0']} – {t1}), {where}.
Columns: `ground_h_ellipsoid` (WGS84 ellipsoid), `ground_h_egm08` (empty if the geoid conversion was not verified), `geoid_status`,
canopy heights above ground, `n_ground_ph`, `n_veg_ph`, `night`, QC flags (`f_missing`, `f_few_ground` < {c['MIN_GROUND_PH']} ground photons,
`f_ground_range` outside {c['GROUND_RANGE']} m EGM2008), `qc_ok`{', DEM values ' + ', '.join(dem_cols) if dem_cols else ''}.

Field mapping: `{json.dumps(found)}`. Geoid: `{json.dumps(GEO)}`. QC: `{json.dumps(q)}`. DEM − ICESat-2 ground: `{json.dumps(dem_cmp)}`.

Limitations: under dense mangrove canopy few photons reach the ground; daytime segments are noisier (`night`); EGM2008 is not local MSL.

Sources: ICESat-2 ATL03 / ATL08 (NSIDC) via SlideRule (Shean et al. 2023); PhoREAL (Neuenschwander et al.); PROJ / EGM2008 (NGA).
""")
    ctx.data.update(atl08=v, atl08_qc=q)
    ctx.note('atl08', dict(period=[c['T0'], t1], fields=found, geoid=GEO, qc=q, where=where))
    return ctx
