"""End-to-end run of every step against fake services (no network). Run: pytest -q tests/test_mock_run.py"""
import os, sys, json, importlib
sys.path.insert(0, os.path.dirname(__file__))
import mock_services as M                     # must come before seastrong_toolkit
import numpy as np, pandas as pd
import seastrong_toolkit as st

OVR = {'project': {'DRIVE_ROOT': M.ROOT, 'WAVE_REGION': os.environ.get('REGION', 'global')},
       's2': {'YEARS': [2023, 2026]}, 'icesat2': {'SDB_BOOT': 30, 'XT_MIN_PASSES': 2},
       'prescreen': {'SENSORS': ['S2', 'LANDSAT']}}

def run_all():
    ctx = st.setup(None, overrides=OVR)
    for step in ['waves', 'prescreen', 's2', 'dem', 'habitats', 'transport', 'icesat2']:
        getattr(st, step).run(ctx)
    st.summary(ctx)
    return ctx

def test_pipeline():
    ctx = run_all()
    m = {s: st.manifest(s, ctx) for s in st.core.STEPS}
    assert m['waves']['status']['waves']['status'] in ('complete', 'partial')
    assert 'rain_mm' in st.waves.load_series()['era5']
    w = st.prescreen.WINDOWS
    assert set(w.length) == {2, 3, 4} and w.usable_mean.notna().all()
    best3 = w[(w.length == 3)].iloc[0]
    assert all(mo not in [6, 7, 8, 9, 10, 11] for mo in best3.month_list), best3.label   # synthetic wet season avoided
    assert m['s2']['outputs']['composite_task']
    assert m['icesat2']['status']['icesat2_depth_limit']['status'] == 'resolved'
    txt = json.dumps(m, default=str)
    assert 'xxxx-key' not in txt and '"pw"' not in txt

def test_rerun_reuses_everything():
    ctx = st.setup(None, overrides=OVR)
    n_tasks, n_cds = M.Task.n, len(M.LOG['cds'])
    for step in ['waves', 'prescreen', 's2', 'dem', 'habitats']:
        getattr(st, step).run(ctx)
    assert M.Task.n == n_tasks and len(M.LOG['cds']) == n_cds

def test_changed_s2_settings_only_rerun_s2():
    ctx0 = st.setup(None, overrides=OVR)
    ovr = json.loads(json.dumps(OVR)); ovr['s2']['MONTHS'] = [3, 5]
    ctx1 = st.setup(None, overrides=ovr)
    assert ctx1.hashes['waves'] == ctx0.hashes['waves'] and ctx1.hashes['prescreen'] == ctx0.hashes['prescreen']
    assert ctx1.hashes['s2'] != ctx0.hashes['s2'] and ctx1.hashes['icesat2'] != ctx0.hashes['icesat2']
    assert ctx1.hashes['dem'] == ctx0.hashes['dem']

if __name__ == '__main__':
    test_pipeline(); test_rerun_reuses_everything(); test_changed_s2_settings_only_rerun_s2(); print('ALL MOCK TESTS PASSED')
