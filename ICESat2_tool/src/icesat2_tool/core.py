"""Site context (AOI from a file, projected CRS, folders), SlideRule download with per-year cache, helpers."""
import os, json, time, hashlib, datetime as dt
import numpy as np
import pandas as pd
import geopandas as gpd
from .options import check

OKABE_ITO = ['#0072B2', '#E69F00', '#009E73', '#D55E00', '#56B4E9', '#CC79A7', '#F0E442', '#000000']


def read_polygons(path, label='file'):
    """Polygons (or lines) from GeoJSON, KML, shapefile, GeoPackage; returns a GeoDataFrame in WGS84."""
    if not path or not os.path.exists(path):
        raise FileNotFoundError(f'{label}: {path} not found (in Colab: Files panel -> right-click -> Copy path)')
    g = gpd.read_file(path)
    if g.crs is None:
        print(f'  {label}: no CRS in the file, WGS84 assumed'); g = g.set_crs('EPSG:4326')
    g = g[g.geometry.notna() & ~g.geometry.is_empty]
    if not len(g): raise ValueError(f'{label}: {path} has no geometries')
    return g.to_crs('EPSG:4326')


class Context:
    def __init__(self, site):
        self.site = check('site', site)
        if not self.site['OUTPUT_DIR']:
            raise ValueError("SITE['OUTPUT_DIR'] is not set (the notebook sets it to <toolkit folder>/outputs)")
        if not self.site['AOI_FILE']:
            raise ValueError("SITE['AOI_FILE'] is not set: a polygon file of the area of interest")
        g = read_polygons(self.site['AOI_FILE'], 'AOI_FILE')
        poly = g[g.geom_type.isin(['Polygon', 'MultiPolygon'])]
        if not len(poly): raise ValueError('AOI_FILE must contain a polygon')
        self.aoi = poly.union_all() if hasattr(poly, 'union_all') else poly.unary_union    # WGS84 shapely geometry
        self.crs = self.site['CRS'] or str(gpd.GeoSeries([self.aoi], crs='EPSG:4326').estimate_utm_crs())
        self.root = os.path.join(self.site['OUTPUT_DIR'], self.site['NAME'])
        self.cache = os.path.join(self.site['OUTPUT_DIR'], '_cache')
        for d in (self.root, self.cache): os.makedirs(d, exist_ok=True)
        self.opts, self.data, self.log = {}, {}, {}
        self.today = dt.datetime.now(dt.timezone.utc).date()
        a = gpd.GeoSeries([self.aoi], crs='EPSG:4326').to_crs(self.crs).area.iloc[0] / 1e6
        self.area_km2 = float(a)

    def path(self, *parts):
        p = os.path.join(self.root, *parts); os.makedirs(os.path.dirname(p), exist_ok=True); return p

    @property
    def name(self): return self.site['NAME']

    def note(self, key, value):
        self.log[key] = value
        p = self.path(f'{self.name}_sources.json')
        old = json.load(open(p)) if os.path.exists(p) else {}
        old[key] = value
        json.dump(old, open(p + '.tmp', 'w'), indent=1, default=str); os.replace(p + '.tmp', p)

    def __repr__(self):
        return f'Context({self.name}: AOI {self.area_km2:.0f} km2, {self.crs} -> {self.root})'


def setup(site):
    ctx = Context(site)
    x0, y0, x1, y1 = ctx.aoi.bounds
    print(f"Site {ctx.name}: AOI {ctx.area_km2:,.1f} km2 ({x0:.3f}..{x1:.3f} E, {y0:.3f}..{y1:.3f} N); map projection {ctx.crs}")
    print(f'Outputs: {ctx.root}   (downloads cached in {ctx.cache})')
    return ctx


def sliderule_versions():
    try:
        import sliderule
        from sliderule import sliderule as sr
        v = {'client': getattr(sliderule, '__version__', 'unknown')}
        try: v['server'] = sr.get_version()
        except Exception as e: v['server'] = f'unavailable ({str(e)[:80]})'
        return v
    except Exception as e:
        return {'error': str(e)[:120]}


def sliderule_years(ctx, api, parms_extra, t0, t1, retries, fn=None):
    """SlideRule request year by year over the AOI bounding box, with retries and a per-year cache.
    Returns (GeoDataFrame or None, coverage DataFrame)."""
    from sliderule import sliderule as sr
    sr.init(verbose=False)
    x0, y0, x1, y1 = ctx.aoi.bounds
    poly = [{'lon': x0, 'lat': y0}, {'lon': x1, 'lat': y0}, {'lon': x1, 'lat': y1}, {'lon': x0, 'lat': y1}, {'lon': x0, 'lat': y0}]
    cache_dir = os.path.join(ctx.cache, 'sliderule'); os.makedirs(cache_dir, exist_ok=True)
    out, cov = [], []
    for y in range(int(t0[:4]), int(t1[:4]) + 1):
        a = max(pd.Timestamp(t0), pd.Timestamp(f'{y}-01-01')); z = min(pd.Timestamp(t1), pd.Timestamp(f'{y}-12-31 23:59:59'))
        key = hashlib.sha256(json.dumps({'api': api, 'poly': poly, 'parms': parms_extra, 'a': str(a), 'z': str(z.date())},
                                        sort_keys=True, default=str).encode()).hexdigest()[:10]
        cache = os.path.join(cache_dir, f'{api}_{y}_{key}.parquet')
        current = z.date() >= ctx.today - dt.timedelta(days=1)           # the current year is never cached for good
        row = dict(api=api, year=y, requested_start=str(a.date()), requested_end=str(z.date()))
        if os.path.exists(cache) and not current:
            g = gpd.read_parquet(cache); row.update(status='ok (cache)', n=len(g), attempts=0)
        elif os.path.exists(cache + '.empty') and not current:
            g = None; row.update(status='empty (cache)', n=0, attempts=0)
        else:
            g = None
            for k in range(1, retries + 1):
                parms = {'poly': poly, 't0': a.strftime('%Y-%m-%dT%H:%M:%SZ'), 't1': z.strftime('%Y-%m-%dT%H:%M:%SZ'), **parms_extra}
                try:
                    g = fn(parms) if fn else sr.run(api, parms)
                    n = 0 if g is None else len(g)
                    row.update(status='ok' if n else 'empty', n=n, attempts=k)
                    if n:
                        g = gpd.GeoDataFrame(g, geometry='geometry', crs=g.crs or 'EPSG:4326')
                        if isinstance(g.index, pd.DatetimeIndex):
                            g = g.reset_index()
                            if 'time' not in g and 'index' in g: g = g.rename(columns={'index': 'time'})
                        g.to_parquet(cache)
                    else:
                        open(cache + '.empty', 'w').write('no data returned')   # not asked again (except the current year)
                    break
                except Exception as e:
                    row.update(status='failed', n=0, attempts=k, error=str(e)[:300])
                    print(f'  {api} {y}: attempt {k} failed ({str(e)[:120]})'); time.sleep(20 * k)
        print(f"  {api} {y}: {row['status']}, {row.get('n', 0):,} records")
        if g is not None and len(g):
            out.append(g)
            if 'time' in g: row.update(first=str(pd.to_datetime(g['time']).min()), last=str(pd.to_datetime(g['time']).max()))
        cov.append(row)
    cov = pd.DataFrame(cov)
    if not out: return None, cov
    g = gpd.GeoDataFrame(pd.concat(out, ignore_index=True), geometry='geometry', crs=out[0].crs or 'EPSG:4326')
    if 'time' not in g: g['time'] = pd.NaT
    g['time'] = pd.to_datetime(g['time'], utc=True, errors='coerce')
    return g, cov


def figure_style():
    import matplotlib.pyplot as plt
    plt.rcParams.update({'font.size': 8, 'axes.titlesize': 9, 'axes.labelsize': 8, 'legend.fontsize': 7,
                         'xtick.labelsize': 7, 'ytick.labelsize': 7, 'axes.spines.top': False, 'axes.spines.right': False,
                         'figure.dpi': 110})


def save_fig(ctx, fig, name):
    for ext in ('png', 'pdf'):
        fig.savefig(ctx.path('figures', f'{ctx.name}_{name}.{ext}'), dpi=200, bbox_inches='tight')


def empty_panel(ax, msg):
    ax.text(0.5, 0.5, msg, ha='center', va='center', transform=ax.transAxes, fontsize=8, color='0.4')
    ax.set_xticks([]); ax.set_yticks([])


def write_gpkg(ctx, df, name, cols):
    o = df[[c for c in cols if c in df]].copy()
    if 'time' in o: o['time'] = o['time'].astype(str)
    for k in ('rgt', 'cycle'):
        if k in o: o[k] = o[k].astype('float').astype('Int64')
    p = ctx.path(f'{ctx.name}_{name}.gpkg')
    if os.path.exists(p): os.remove(p)
    o.to_file(p, driver='GPKG')
    return p
