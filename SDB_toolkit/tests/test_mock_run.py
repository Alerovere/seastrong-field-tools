"""End-to-end run of every step against fake services (no network). Run: python tests/test_mock_run.py"""
import os, sys, json
sys.path.insert(0, os.path.dirname(__file__))
import mock_services as M                     # must come before seastrong_toolkit
import seastrong_toolkit as st

PROJECT = dict(DRIVE_ROOT=M.ROOT, WAVE_REGION=os.environ.get('REGION', 'global'))
OPTIONS = {'waves': {}, 'prescreen': dict(SENSORS=['S2', 'LANDSAT'], YEARS=[2017, 2026]), 's2': dict(YEARS=[2023, 2026]),
           'dem': {}, 'habitats': {}, 'transport': {}, 'icesat2': dict(SDB_BOOT=30, XT_MIN_PASSES=2)}

def run_all(options=OPTIONS, steps=('waves', 'prescreen', 's2', 'dem', 'habitats', 'transport', 'icesat2')):
    ctx = st.setup(PROJECT)
    for step in steps:
        ctx.set(step, options[step])
        getattr(st, step).run(ctx)
        getattr(st, step).report(ctx)
    st.summary(ctx)
    return ctx

def test_pipeline():
    ctx = run_all()
    m = {s: st.manifest(s, ctx) for s in st.core.STEPS}
    assert 'rain_mm' in st.waves.load_series()['era5']
    w = st.prescreen.WINDOWS
    assert set(w.length) == {2, 3, 4} and w.usable_mean.notna().all()
    best3 = w[(w.length == 3)].iloc[0]
    assert all(mo not in [6, 7, 8, 9, 10, 11] for mo in best3.month_list), best3.label   # synthetic wet season avoided
    assert m['s2']['outputs']['composite_task']
    assert m['icesat2']['status']['icesat2_depth_limit']['status'] == 'resolved'
    assert m['icesat2']['outputs']['qc_summary']['kept'] > 0
    txt = json.dumps(m, default=str)
    assert 'xxxx-key' not in txt and '"pw"' not in txt

def test_rerun_reuses_everything():
    n_tasks, n_cds = M.Task.n, len(M.LOG['cds'])
    run_all(steps=('waves', 'prescreen', 's2', 'dem', 'habitats'))
    assert M.Task.n == n_tasks and len(M.LOG['cds']) == n_cds

def test_changed_s2_options_only_change_s2_and_downstream():
    ctx = st.setup(PROJECT, login=False, mount_drive=False)
    for s, o in OPTIONS.items(): ctx.set(s, o, quiet=True)
    h0 = ctx.hashes
    ctx.set('s2', dict(OPTIONS['s2'], MONTHS=[3, 5]))
    h1 = ctx.hashes
    assert h1['waves'] == h0['waves'] and h1['prescreen'] == h0['prescreen'] and h1['dem'] == h0['dem']
    assert h1['s2'] != h0['s2'] and h1['icesat2'] != h0['icesat2']

def test_screening_modes():
    """'metadata' never touches Earth Engine pixels; 'aoi' checks every date; metadata+aoi only the survivors."""
    ctx = st.setup(PROJECT, login=False, mount_drive=False)
    for s, o in OPTIONS.items(): ctx.set(s, o, quiet=True)
    n = {}
    for mode in ('metadata', 'metadata+aoi', 'aoi'):
        ctx.set('s2', dict(OPTIONS['s2'], SCREENING=mode), quiet=True)
        a0 = len(M.LOG.get('aoi_exports', []))
        st.s2.run(ctx); st.s2.report(ctx)
        n[mode] = (int(st.s2.scr.aoi_evaluated.sum()), len(M.LOG.get('aoi_exports', [])) - a0, len(st.s2.scr))
    assert n['metadata'][:2] == (0, 0)
    assert 0 < n['metadata+aoi'][0] < n['aoi'][0] == n['aoi'][2]
    assert n['aoi'][1] == 1          # only the dates not yet in the cache
    pc = st.s2.proxy_check(st.s2.scr, ctx.cfg['s2'])
    assert set(pc.check) >= {'rain', 'wind', 'waves', 'tile cloud', 'glint angle'}

def test_prescreen_aoi_mode():
    ctx = st.setup(PROJECT, login=False, mount_drive=False)
    for s, o in OPTIONS.items(): ctx.set(s, o, quiet=True)
    ctx.set('prescreen', dict(OPTIONS['prescreen'], SCENES='aoi', CHIRPS=True), quiet=True)
    st.prescreen.run(ctx); st.prescreen.report(ctx)
    assert set(st.prescreen.SCENES.family) == {'S2', 'LANDSAT'} and st.prescreen.DAILY.rain_chirps.notna().any()

def test_misspelt_option_stops():
    ctx = st.setup(PROJECT, login=False, mount_drive=False)
    try:
        ctx.set('s2', {'MONTH': [2, 4]}); raise AssertionError('no error')
    except KeyError as e:
        assert 'MONTHS' in str(e)

def test_checker_decisions_reach_the_composite():
    import ipywidgets as wg
    ctx = st.setup(PROJECT, login=False, mount_drive=False)
    for s, o in OPTIONS.items(): ctx.set(s, o, quiet=True)
    h0 = ctx.hashes['s2']
    df = st.s2.checker(ctx)
    assert df.date.min() >= '2023' and len(df) > df.aoi_evaluated.sum() > 0
    dropped = df[~df.auto_kept & df.aoi_evaluated].date.iloc[0]; kept = df[df.auto_kept].date.iloc[0]
    st.s2.save_decision(dropped, 'accept'); st.s2.save_decision(kept, 'reject')
    assert ctx.hashes['s2'] != h0                       # decisions give a new composite folder
    n_tasks = M.Task.n
    st.s2.run(ctx)
    d = st.s2.scr.set_index('date')
    assert d.loc[dropped, 'kept'] and not d.loc[kept, 'kept'] and d.loc[kept, 'manual'] == 'reject'
    exported = [M.LOG['tasks'][f'T{i:04d}'][0] for i in range(n_tasks + 1, M.Task.n + 1)]
    assert not any('AOI_stats' in e for e in exported), exported      # image statistics re-used from the cache
    # accepting a date that never had the image check sends only that date to Earth Engine
    never = df[~df.aoi_evaluated].date.iloc[0]
    st.s2.save_decision(never, 'accept'); n_tasks = M.Task.n
    st.s2.run(ctx)
    exported = [M.LOG['tasks'][f'T{i:04d}'][0] for i in range(n_tasks + 1, M.Task.n + 1)]
    assert sum('AOI_stats' in e for e in exported) == 1, exported
    assert st.s2.scr.set_index('date').loc[never, 'aoi_evaluated']
    st.s2.save_decision(never, 'auto')
    st.s2.save_decision(dropped, 'auto'); st.s2.save_decision(kept, 'auto')
    assert ctx.hashes['s2'] == h0

if __name__ == '__main__':
    test_pipeline(); test_rerun_reuses_everything(); test_changed_s2_options_only_change_s2_and_downstream(); test_misspelt_option_stops()
    test_checker_decisions_reach_the_composite(); test_screening_modes(); test_prescreen_aoi_mode()
    print('ALL MOCK TESTS PASSED')

