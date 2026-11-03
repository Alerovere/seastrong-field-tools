"""Shared machinery: settings, Colab Secrets, Earth Engine log-in, per-step folders and manifests,
Earth Engine exports, figures and shared Earth Engine data.

Every step (waves, prescreen, s2, dem, habitats, transport, icesat2) has its own settings hash. Its outputs go to
the Drive folder ``<FOLDER_ROOT>__<NN>_<Name>__<hash8>`` with a ``manifest.json`` (settings, versions, Earth
Engine task IDs, files with SHA-256 and raster metadata, coverage, status). A step whose settings did not change
re-uses its folder: finished exports and stages are skipped. A step that uses another step's outputs includes that
step's hash in its own, so changed inputs always give a new folder.
"""
import os, re, json, time, copy, hashlib, datetime as dt
from importlib import resources
import numpy as np
import pandas as pd

CTX = None          # the active Context (set by setup())

STEPS = {   # key: (folder number/name, upstream steps)
    'waves': ('00_Waves', []),
    'prescreen': ('00b_Prescreen_S2_months', ['waves']),
    's2': ('01_S2_composite_SDB', ['waves']),
    'dem': ('02_DEM_DSM', []),
    'habitats': ('03_Habitats', []),
    'transport': ('04_Transport_overview', []),
    'icesat2': ('05_ICESat2', ['s2', 'dem']),
}
CMEMS_REGIONS = {
    'global': dict(datasets=['cmems_mod_glo_wav_my_0.2deg_PT3H-i', 'cmems_mod_glo_wav_anfc_0.083deg_PT3H-i'],
                   step_h=3, search_deg=0.3, start='1980-01-01',
                   products='GLOBAL_MULTIYEAR_WAV_001_032 (WAVERYS), GLOBAL_ANALYSISFORECAST_WAV_001_027'),
    'med': dict(datasets=['cmems_mod_med_wav_my_4.2km_PT1H-i', 'cmems_mod_med_wav_anfc_4.2km_PT1H-i'],
                step_h=1, search_deg=0.1, start='1985-01-01',
                products='MEDSEA_MULTIYEAR_WAV_006_012, MEDSEA_ANALYSISFORECAST_WAV_006_017'),
}


# =============================================================================================== settings
def _merge(a, b):
    out = copy.deepcopy(a)
    for k, v in (b or {}).items():
        out[k] = _merge(out[k], v) if isinstance(v, dict) and isinstance(out.get(k), dict) else copy.deepcopy(v)
    return out

def _jsonable(o):
    if isinstance(o, dict): return {str(k): _jsonable(v) for k, v in sorted(o.items(), key=lambda kv: str(kv[0]))}
    if isinstance(o, (list, tuple)): return [_jsonable(v) for v in o]
    if isinstance(o, np.integer): return int(o)
    if isinstance(o, np.floating): return float(o)
    if isinstance(o, (dt.date, pd.Timestamp)): return str(o)
    return o

def _hash(o):
    return hashlib.sha256(json.dumps(_jsonable(o), sort_keys=True).encode()).hexdigest()

def defaults():
    """The package's default settings for every step (a fresh copy)."""
    import yaml
    return yaml.safe_load(resources.files('seastrong_toolkit').joinpath('defaults.yaml').read_text())

def check_keys(section, settings, ref):
    """Stop on misspelt option names (they would otherwise be ignored silently)."""
    unknown = sorted(set(settings) - set(ref))
    if unknown:
        import difflib
        hints = {k: difflib.get_close_matches(k, list(ref), n=1) for k in unknown}
        raise KeyError(f"Unknown option(s) for '{section}': " +
                       ', '.join(f"{k} (did you mean {h[0]}?)" if h else k for k, h in hints.items()))

def derive(cfg):
    """Settings computed from others (Copernicus Marine datasets of the chosen region)."""
    reg = cfg['project']['WAVE_REGION']
    if reg not in CMEMS_REGIONS: raise ValueError(f"WAVE_REGION must be one of {list(CMEMS_REGIONS)}")
    r = CMEMS_REGIONS[reg]
    cfg['waves'].update(REGION=reg, CMEMS_DATASETS=r['datasets'], CMEMS_STEP_H=r['step_h'], CMEMS_SEARCH_DEG=r['search_deg'])
    return cfg

DERIVED = {'waves': ['REGION', 'CMEMS_DATASETS', 'CMEMS_STEP_H', 'CMEMS_SEARCH_DEG']}

def step_hash(cfg, step, _memo=None):
    """Hash of a step's settings + project settings + upstream step hashes."""
    _memo = {} if _memo is None else _memo
    if step in _memo: return _memo[step]
    proj = {k: v for k, v in cfg['project'].items() if k != 'DRIVE_ROOT'}
    h = _hash(dict(project=proj, step=step, settings=cfg[step],
                   upstream={u: step_hash(cfg, u, _memo) for u in STEPS[step][1]}))
    _memo[step] = h
    return h


# =============================================================================================== secrets
class MissingSecret(RuntimeError):
    pass

def secret(name, required=True, purpose=''):
    """Value of a Colab Secret (key icon, left sidebar), else of an environment variable of the same name.
    Never printed. Raises MissingSecret with instructions if required and absent."""
    v = None
    try:
        from google.colab import userdata
        try:
            v = userdata.get(name)
        except Exception:
            v = None
    except ImportError:
        pass
    v = v or os.environ.get(name)
    if required and not v:
        raise MissingSecret(
            f"Colab Secret '{name}' is missing{(' (needed for ' + purpose + ')') if purpose else ''}. "
            f"Open the key icon in the left sidebar, add a secret called {name}, switch on 'Notebook access', "
            f"then re-run this cell.")
    return v

def ee_login():
    import ee
    project = secret('EE_PROJECT', purpose='Earth Engine')
    sa_json = secret('EE_SERVICE_ACCOUNT_JSON', required=False)
    if sa_json:
        key = json.loads(sa_json)
        ee.Initialize(ee.ServiceAccountCredentials(key['client_email'], key_data=sa_json), project=project)
        how = 'service account from Colab Secret'
    else:
        ee.Authenticate()
        ee.Initialize(project=project)
        how = 'Colab Google sign-in'
    print(f'Earth Engine initialised ({how}); project from Colab Secret EE_PROJECT')
    return project

def package_versions():
    out = {}
    for m in ['seastrong_toolkit', 'ee', 'geemap', 'copernicusmarine', 'cdsapi', 'sliderule', 'rasterio', 'geopandas',
              'pyproj', 'shapely', 'xarray', 'numpy', 'pandas', 'scipy', 'matplotlib', 'google.auth']:
        try:
            mod = __import__(m, fromlist=['_']); out[m] = getattr(mod, '__version__', 'unknown')
        except Exception:
            out[m] = 'not installed'
    return out


# =============================================================================================== context
class Context:
    """Everything a step needs: settings, Earth Engine objects, folders, manifests.

    Settings come from the notebook: ``ctx.set('s2', S2)`` replaces the options of one step (missing options take
    the package default). The step's settings hash, and therefore its Drive folder, follow the current settings.
    """
    def __init__(self, cfg):
        self.cfg = derive(cfg)
        self.drive_root = cfg['project']['DRIVE_ROOT']
        self.manifests = {}
        self.current = None
        self.data = {}            # in-memory results shared between steps in one session
        self.today = dt.datetime.now(dt.timezone.utc).date()
        self.user_set = set()     # steps whose options were given in the notebook

    @property
    def hashes(self):
        memo = {}
        return {s: step_hash(self.cfg, s, memo) for s in STEPS}

    @property
    def folders(self):
        p, h = self.cfg['project'], self.hashes
        f = {s: f"{p['FOLDER_ROOT']}__{STEPS[s][0]}__{h[s][:8]}" for s in STEPS}
        f['cache'] = f"{p['FOLDER_ROOT']}__cache"
        return f

    def set(self, step, settings=None, quiet=False):
        """Use these options for a step (options not given take the package default; misspelt names stop)."""
        if step not in STEPS and step != 'run': raise KeyError(f'unknown step {step}; steps: {list(STEPS)}')
        ref = defaults()[step]
        settings = dict(settings or {})
        check_keys(step, settings, ref)
        self.cfg[step] = _merge(ref, settings)
        derive(self.cfg)
        self.user_set.add(step)
        if not quiet and step in STEPS:
            folder = self.folders[step]
            done = os.path.exists(os.path.join(self.drive_root, folder, 'manifest.json'))
            changed = {k: v for k, v in settings.items() if ref.get(k) != v}
            print(f"[{step}] {len(settings)} options set ({len(changed)} differ from the defaults: {', '.join(changed) or 'none'})")
            print(f"  output folder: {folder}  ->  " + ('exists: finished parts will be re-used' if done else 'new (these settings were not run before)'))
            down = [s for s, (_, up) in STEPS.items() if step in up]
            if down: print(f"  steps that use these results: {', '.join(down)}")
        return self

    def show(self, step):
        """Print the options a step will use, marking those that differ from the default."""
        ref = defaults()[step]
        for k, v in self.cfg[step].items():
            if k in DERIVED.get(step, []): continue
            print(f"  {'*' if ref.get(k) != v else ' '} {k:22s} = {v!r}")

    def __repr__(self):
        h = self.hashes
        return 'Context(' + ', '.join(f'{s}={h[s][:8]}' for s in STEPS) + ')'

def setup(project=None, run=None, mount_drive=True, login=True):
    """Project options (dict), Earth Engine log-in (Colab Secrets), Drive, AOI, export grid.
    Returns the Context used by every step. Step options are given later with ctx.set(step, {...})."""
    global CTX
    cfg = defaults()
    check_keys('project', project or {}, cfg['project'])
    check_keys('run', run or {}, cfg['run'])
    cfg['project'] = _merge(cfg['project'], project or {})
    cfg['run'] = _merge(cfg['run'], run or {})
    ctx = Context(cfg)
    CTX = ctx
    if login:
        ctx.ee_project = ee_login()
    else:                                   # Earth Engine already initialised in this session
        ctx.ee_project = secret('EE_PROJECT', purpose='Earth Engine')
    if mount_drive:
        try:
            from google.colab import drive
            drive.mount('/content/drive')
        except ImportError:
            pass
    os.makedirs(os.path.join(ctx.drive_root, ctx.folders['cache']), exist_ok=True)
    _init_ee_objects(ctx)
    return ctx

def use(ctx=None):
    global CTX
    if ctx is not None: CTX = ctx
    if CTX is None: raise RuntimeError('Run the project cell (st.setup(...)) first')
    return CTX

def _init_ee_objects(ctx):
    import ee
    p = ctx.cfg['project']
    if p['AOI_GEOJSON']:
        with open(p['AOI_GEOJSON']) as f:
            gj = json.load(f)
        feats = gj['features'] if gj.get('type') == 'FeatureCollection' else [gj]
        ctx.aoi_fc = ee.FeatureCollection([ee.Feature(ee.Geometry(ft['geometry'], None, False)) for ft in feats])
        ctx.aoi_label = p['AOI_GEOJSON']
    else:
        ctx.aoi_fc = ee.FeatureCollection(p['AOI_ASSET']); ctx.aoi_label = p['AOI_ASSET']
    ctx.roi = ctx.aoi_fc.geometry()
    ctx.centre = ctx.roi.centroid(100)
    info = ee.Dictionary({'area_km2': ctx.roi.area(1).divide(1e6),
                          'bounds_crs': ctx.roi.bounds(1, p['CRS']).coordinates(),
                          'bounds_wgs84': ctx.roi.bounds(1).coordinates(),
                          'geojson': ctx.roi.simplify(50),
                          'centre': ctx.centre.coordinates()}).getInfo()
    ctx.aoi_info = info
    print('AOI area (km2):', round(info['area_km2'], 1))
    b, s = info['bounds_crs'][0], p['GRID_SNAP']
    ctx.grid = dict(crs=p['CRS'], snap=s,
                    x0=float(np.floor(min(q[0] for q in b) / s) * s), y1=float(np.ceil(max(q[1] for q in b) / s) * s),
                    x1=float(np.ceil(max(q[0] for q in b) / s) * s), y0=float(np.floor(min(q[1] for q in b) / s) * s))
    ctx.water = (ee.ImageCollection(p['COPDEM_COLLECTION']).filterBounds(ctx.roi.buffer(5000))
                 .select('WBM').mosaic().gt(0))
    ctx.era5_gee = (ee.ImageCollection('ECMWF/ERA5/HOURLY')
                    .select(['u_component_of_wind_10m', 'v_component_of_wind_10m'], ['u', 'v']))
    ctx.chirps = ee.ImageCollection('UCSB-CHG/CHIRPS/DAILY').select('precipitation')

def bind(module_globals, step, ctx=None):
    """Make the settings and shared objects available to a step module under the names its code uses."""
    ctx = use(ctx)
    ctx.current = step
    c, p, g = ctx.cfg, ctx.cfg['project'], ctx.grid
    module_globals.update(
        CTX=ctx, CFG=c, W=c['waves'], P=c['prescreen'], S2=c['s2'], DEM=c['dem'], HAB=c['habitats'], TR=c['transport'],
        IS2=c['icesat2'], CRS=p['CRS'], PREFIX=p['PREFIX'], FOLDER_ROOT=p['FOLDER_ROOT'], DRIVE_ROOT=ctx.drive_root,
        COPDEM_COLLECTION=p['COPDEM_COLLECTION'], WAIT_FOR_EXPORTS=c['run']['WAIT_FOR_EXPORTS'],
        roi=ctx.roi, centre=ctx.centre, aoi_fc=ctx.aoi_fc, AOI_LABEL=ctx.aoi_label, TODAY=ctx.today,
        GRID_X0=g['x0'], GRID_Y1=g['y1'], GRID_X1=g['x1'], GRID_Y0=g['y0'],
        water=ctx.water, era5_gee=ctx.era5_gee, chirps=ctx.chirps, MANIFEST=manifest(step, ctx),
        RUN_ID=ctx.hashes[step][:12])
    return ctx


# =============================================================================================== manifests
def drive_path(folder_key, filename):
    return os.path.join(CTX.drive_root, CTX.folders[folder_key], filename)

def manifest(step, ctx=None):
    """The manifest of a step for its CURRENT settings (loaded from its folder if it exists)."""
    ctx = use(ctx)
    h = ctx.hashes[step]
    m = ctx.manifests.get(step)
    if m is None or m.get('settings_hash') != h:
        folder = ctx.folders[step]
        os.makedirs(os.path.join(ctx.drive_root, folder), exist_ok=True)
        p = os.path.join(ctx.drive_root, folder, 'manifest.json')
        if os.path.exists(p):
            with open(p) as f: m = json.load(f)
        else:
            m = dict(step=step, settings_hash=h, created_utc=dt.datetime.now(dt.timezone.utc).isoformat(),
                     project=ctx.cfg['project'], settings=ctx.cfg[step],
                     upstream={u: ctx.hashes[u] for u in STEPS[step][1]}, versions=package_versions(),
                     stages={}, tasks={}, files={}, coverage={}, status={}, outputs={})
        m['folder'] = folder
        ctx.manifests[step] = m
    return ctx.manifests[step]

def save_manifest(step=None):
    """Atomic write (temp file + rename) into the manifest's own folder. Without a step: the current step."""
    step = step or CTX.current
    m = CTX.manifests[step]
    p = os.path.join(CTX.drive_root, m['folder'], 'manifest.json'); tmp = p + '.tmp'
    with open(tmp, 'w') as f:
        json.dump(_jsonable(m), f, indent=1, default=str)
    os.replace(tmp, p)

def stage_done(name, **info):
    manifest(CTX.current)['stages'][name] = dict(done_utc=dt.datetime.now(dt.timezone.utc).isoformat(), **_jsonable(info))
    save_manifest()

def stage_get(name, step=None):
    """A finished stage of this step (None when the step runs with force=True)."""
    if getattr(CTX, 'force', False) and step is None: return None
    return manifest(step or CTX.current)['stages'].get(name)

def set_status(key, value, **details):
    """'complete', 'partial', 'unresolved', 'failed', 'skipped' (+ details), in the current step's manifest."""
    manifest(CTX.current)['status'][key] = dict(status=value, **_jsonable(details)); save_manifest()

def step_done(step):
    """True if a step finished with these settings (its manifest says so)."""
    m = manifest(step)
    return bool(m['status'])

def require(step):
    """Stop with a clear message if an upstream step has not finished with the current settings."""
    if step not in CTX.user_set:
        print(f"  NOTE: options of '{step}' were not set in this session: using the package defaults to find its results. "
              f"Run the '{step}' options cell first if you changed them.")
    if not step_done(step):
        raise RuntimeError(f"Step '{step}' has not been run with the current options (folder {CTX.folders[step]}). "
                           f"Run its options cell and st.{step}.run(ctx) first.")
    return manifest(step)


# =============================================================================================== exports
_OP_STATE = {'PENDING': 'READY', 'RUNNING': 'RUNNING', 'SUCCEEDED': 'COMPLETED', 'FAILED': 'FAILED',
             'CANCELLING': 'CANCEL_REQUESTED', 'CANCELLED': 'CANCELLED'}
TERMINAL_BAD = ('FAILED', 'CANCELLED', 'CANCEL_REQUESTED')

def crs_transform(scale):
    return [scale, 0, CTX.grid['x0'], 0, -scale, CTX.grid['y1']]

def task_status(tid):
    import ee
    try:
        return ee.data.getTaskStatus(tid)[0]
    except AttributeError:
        op = ee.data.getOperation(f'projects/{CTX.ee_project}/operations/{tid}')
        md = op.get('metadata', {})
        s = {'id': tid, 'state': _OP_STATE.get(md.get('state'), md.get('state', 'UNKNOWN'))}
        if 'error' in op: s['error_message'] = op['error'].get('message')
        if md.get('createTime'): s['creation_timestamp_ms'] = pd.Timestamp(md['createTime']).value // 1_000_000
        return s

def find_task(name):
    """(step, task record) of a task name in any loaded manifest."""
    for s, m in CTX.manifests.items():
        if name in m['tasks']: return s, m['tasks'][name]
    raise KeyError(f'task {name} not found in the manifests of this session')

def _register(name, task, folder_key, kind, ext):
    m = manifest(folder_key)
    m['tasks'][name] = dict(id=task.id, kind=kind, ext=ext, folder=CTX.folders[folder_key],
                            started_utc=dt.datetime.now(dt.timezone.utc).isoformat(), state='SUBMITTED')
    save_manifest(folder_key)
    print('  started', name, f'(task {task.id})')
    return task.id

def _reuse(name, folder_key):
    t = manifest(folder_key)['tasks'].get(name)
    if not t or getattr(CTX, 'force', False): return None
    st = task_status(t['id'])['state']
    if st in ('COMPLETED', 'READY', 'RUNNING'):
        print(f'  {name}: re-using task {t["id"]} ({st})'); return t['id']
    print(f'  {name}: earlier task {t["id"]} is {st} -> starting again'); return None

def export_image(img, folder_key, name, scale, nodata=-9999, to_float=True):
    """Export on the aligned grid. Float: masked -> nodata. Integer (to_float=False): masked -> nodata if given."""
    import ee
    tid = _reuse(name, folder_key)
    if tid: return tid
    img = img.clip(CTX.roi)
    if to_float: img = img.unmask(nodata).toFloat()
    elif nodata is not None: img = img.unmask(nodata)
    t = ee.batch.Export.image.toDrive(
        image=img, description=name[:100], fileNamePrefix=name, folder=CTX.folders[folder_key],
        region=CTX.roi, crs=CTX.cfg['project']['CRS'], crsTransform=crs_transform(scale), maxPixels=1e13,
        formatOptions={'cloudOptimized': True, **({'noData': nodata} if nodata is not None else {})})
    t.start()
    return _register(name, t, folder_key, 'image', 'tif')

def export_table(fc, folder_key, name, fmt='CSV', selectors=None):
    import ee
    tid = _reuse(name, folder_key)
    if tid: return tid
    kw = dict(collection=fc, description=name[:100], fileNamePrefix=name, folder=CTX.folders[folder_key], fileFormat=fmt)
    if selectors: kw['selectors'] = selectors
    t = ee.batch.Export.table.toDrive(**kw)
    t.start()
    return _register(name, t, folder_key, 'table', fmt.lower())

def wait(names, every=30, timeout_h=None):
    """Block until every task is COMPLETED. FAILED / CANCELLED / timeout -> error with task IDs."""
    names = [n for n in names if n]
    timeout_h = timeout_h or CTX.cfg['run']['WAIT_TIMEOUT_H']
    timeout = time.time() + 3600 * timeout_h
    while True:
        st = {}
        for n in names:
            step, t = find_task(n)
            s = task_status(t['id']); st[n] = s
            t['state'] = s['state']
            if s.get('error_message'): t['error'] = s['error_message']
            for k in ('creation_timestamp_ms', 'start_timestamp_ms', 'update_timestamp_ms'):
                if k in s: t[k] = s[k]
        for step in {find_task(n)[0] for n in names}: save_manifest(step)
        bad = {n: (s['state'], s.get('error_message')) for n, s in st.items() if s['state'] in TERMINAL_BAD}
        if bad:
            raise RuntimeError(f'Export(s) did not complete: {bad}. Task IDs are in the manifest.')
        pending = [n for n, s in st.items() if s['state'] != 'COMPLETED']
        if not pending:
            print(f'  all {len(names)} exports COMPLETED'); return
        if time.time() > timeout:
            raise TimeoutError(f'{len(pending)} export(s) still running after {timeout_h} h: {pending[:5]}. '
                               f'Run the same step again later: finished and running tasks are re-used.')
        print(f'  {time.strftime("%H:%M:%S")} waiting for {len(pending)}: {pending[:3]}...'); time.sleep(every)

def sha256_file(p, chunk=8 << 20):
    h = hashlib.sha256()
    with open(p, 'rb') as f:
        for b in iter(lambda: f.read(chunk), b''): h.update(b)
    return h.hexdigest()

def raster_meta(p):
    import rasterio
    with rasterio.open(p) as src:
        return dict(crs=str(src.crs), transform=list(src.transform)[:6], width=src.width, height=src.height,
                    count=src.count, dtype=src.dtypes[0], nodata=src.nodata, descriptions=list(src.descriptions))

def task_files(name):
    """Files written by the COMPLETED task `name` (sharded GeoTIFFs included), validated and recorded."""
    step, t = find_task(name)
    if t.get('state') != 'COMPLETED':
        raise RuntimeError(f'{name} is {t.get("state")}, not COMPLETED')
    if t.get('files') and all(os.path.exists(f['path']) for f in t['files']):
        return [f['path'] for f in t['files']]
    folder = os.path.join(CTX.drive_root, t['folder'])
    pat = re.compile(rf'^{re.escape(name)}(-\d{{10}}-\d{{10}})?\.{t["ext"]}$')
    t_min = (t.get('creation_timestamp_ms', 0) / 1000) - 120
    deadline = time.time() + CTX.cfg['run']['DRIVE_SYNC_TIMEOUT_S']
    while True:
        hits = sorted(os.path.join(folder, f) for f in os.listdir(folder) if pat.match(f))
        fresh = [p for p in hits if os.path.getmtime(p) >= t_min]
        if fresh:
            sizes = [os.path.getsize(p) for p in fresh]; time.sleep(5)
            if sizes == [os.path.getsize(p) for p in fresh] and all(sizes): break
        if time.time() > deadline:
            raise FileNotFoundError(f'{name}: no fresh file in {folder}. Check Drive for a duplicate folder named '
                                    f'{t["folder"]}, or remount Drive and re-run.')
        time.sleep(15)
    rec = []
    for p in fresh:
        r = dict(path=p, size=os.path.getsize(p), sha256=sha256_file(p),
                 mtime_utc=dt.datetime.fromtimestamp(os.path.getmtime(p), dt.timezone.utc).isoformat())
        if p.endswith('.tif'): r['raster'] = raster_meta(p)
        rec.append(r)
    t['files'] = rec; save_manifest(step)
    return [r['path'] for r in rec]

def read_task_csv(name):
    return pd.read_csv(task_files(name)[0])

def record_file(p, kind='local'):
    """Register a file written by this toolkit (not by Earth Engine) in the current step's manifest."""
    r = dict(path=p, kind=kind, size=os.path.getsize(p), sha256=sha256_file(p),
             written_utc=dt.datetime.now(dt.timezone.utc).isoformat())
    if p.endswith('.tif'): r['raster'] = raster_meta(p)
    manifest(CTX.current)['files'][os.path.basename(p)] = r; save_manifest()

def write_readme(folder_key, name, body_md):
    ctx = CTX
    g = ctx.grid
    head = (f'_Generated {dt.datetime.now(dt.timezone.utc):%Y-%m-%d %H:%M} UTC with seastrong_toolkit '
            f'{package_versions()["seastrong_toolkit"]}._  \n'
            f'_Step `{folder_key}`, settings hash `{ctx.hashes.get(folder_key, "")[:12]}` (all settings, task IDs and file '
            f'checksums in `manifest.json` in this folder)._  \n'
            f'_AOI: `{ctx.aoi_label}` · CRS: `{g["crs"]}`, grid origin ({g["x0"]:.0f}, {g["y1"]:.0f})_\n\n')
    # README templates live inside run() and are indented by 4 spaces in the source: remove exactly that
    body = '\n'.join(l[4:] if l.startswith('    ') else l for l in body_md.splitlines())
    p = drive_path(folder_key, name + '.md')
    with open(p, 'w') as f:
        f.write(head + body.strip() + '\n')
    print('  README written:', p)

def summary(ctx=None):
    """Task states and step status of every step run in this session."""
    ctx = use(ctx)
    for step, m in ctx.manifests.items():
        print(f"\n[{step}] {ctx.folders[step]}")
        for n, t in m['tasks'].items():
            s = task_status(t['id']); t['state'] = s['state']
            print(f"  {s['state']:10s} {n}" + (f"  ERROR: {s.get('error_message')}" if s['state'] in TERMINAL_BAD else ''))
        for k, v in m['status'].items(): print(f"  status {k}: {v['status']}")
        ctx.current = step; save_manifest(step)


# =============================================================================================== figures
def figure_style():
    import matplotlib as mpl
    mpl.rcParams.update({
        'figure.dpi': 110, 'savefig.dpi': 300, 'savefig.bbox': 'tight',
        'font.family': 'DejaVu Sans', 'font.size': 9, 'axes.titlesize': 10, 'axes.labelsize': 9,
        'xtick.labelsize': 8, 'ytick.labelsize': 8, 'legend.fontsize': 8, 'legend.frameon': False,
        'axes.spines.top': False, 'axes.spines.right': False, 'axes.grid': True, 'grid.alpha': 0.25,
        'grid.linewidth': 0.5, 'lines.linewidth': 1.0, 'axes.prop_cycle': mpl.cycler(color=OKABE_ITO),
        'pdf.fonttype': 42, 'ps.fonttype': 42})

OKABE_ITO = ['#0072B2', '#E69F00', '#009E73', '#D55E00', '#CC79A7', '#56B4E9', '#F0E442', '#000000']

def panel_labels(axes, x=-0.12, y=1.04):
    for i, ax in enumerate(np.ravel(axes)):
        lab = r'$\bf{(' + chr(97 + i) + r')}$'
        t = ax.get_title(loc='left')
        if t: ax.set_title(f'{lab} {t}', loc='left')
        else: ax.text(x, y, lab, transform=ax.transAxes, va='bottom', ha='left')

def save_fig(fig, folder_key, name):
    for ext in ('png', 'pdf'):
        fig.savefig(drive_path(folder_key, f'{name}.{ext}'))
    print('  figure saved:', drive_path(folder_key, name + '.png/.pdf'))

def empty_panel(ax, msg):
    ax.text(0.5, 0.5, msg, ha='center', va='center', transform=ax.transAxes, fontsize=8, color='0.4')
    ax.set_xticks([]); ax.set_yticks([])


# =============================================================================================== Earth Engine helpers
def dir_to(u, v):   # direction the vector points TO, degrees from north
    return u.atan2(v).multiply(180 / np.pi).add(360).mod(360)

def in_months(m):
    import ee
    return ee.Filter.calendarRange(m[0], m[1], 'month')

def years_filter(y):
    import ee
    return ee.Filter.date(f'{y[0]}-01-01', f'{y[1] + 1}-01-01')

def aoi_shapely():
    """AOI polygon (WGS84), simplified to ~50 m."""
    from shapely.geometry import shape
    return shape(CTX.aoi_info['geojson'])

def aoi_bbox_wgs84():
    b = CTX.aoi_info['bounds_wgs84'][0]
    return min(q[0] for q in b), min(q[1] for q in b), max(q[0] for q in b), max(q[1] for q in b)
