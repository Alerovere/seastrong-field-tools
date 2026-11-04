"""End-to-end run against a fake SlideRule. Run: python tests/test_mock_run.py"""
import os, sys, json
sys.path.insert(0, os.path.dirname(__file__)); sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
import mock_services as M
import icesat2_tool as it
import geopandas as gpd

SITE = dict(NAME='Test_site', AOI_FILE=M.AOI_FILE, OUTPUT_DIR=M.ROOT)
ATL24 = dict(T1='2026-10-31', SHORELINE_FILE=M.SHORE_FILE, XT_MIN_PASSES=2)

def test_pipeline():
    ctx = it.setup(SITE)
    assert ctx.crs == 'EPSG:32616'
    it.atl24.run(ctx, ATL24)
    a = ctx.data['atl24']
    assert a.f_land.sum() > 0 and a.f_shore.sum() >= 0 and a.dist_shore_m.notna().all()
    assert a.xt_ref_depth.notna().sum() > 1000                                               # cross-track check ran
    assert not (a.f_xtrack & (a.set == 'valid') & ~a.qc_ok & a.qc_indep_ok).any()           # validation not removed
    tr = gpd.read_file(ctx.path('Test_site_ATL24_train.gpkg')); va = gpd.read_file(ctx.path('Test_site_ATL24_valid.gpkg'))
    assert len(tr) and len(va) and not set(tr.rgt) & set(va.rgt)
    assert tr.qc_ok.all() and (tr.ortho_h < 0).all()
    lock = json.load(open(ctx.path('Test_site_ICESat2_holdout_lock.json')))
    it.atl08.run(ctx, dict(T1='2026-10-31', MANGROVE_FILE=M.MANG_FILE))
    v = ctx.data['atl08']; assert 0 < len(v) < 300 * 9
    # second run: cached years, lock re-used and unchanged
    n = len(M.CALLS)
    ctx2 = it.setup(SITE); it.atl24.run(ctx2, ATL24)
    assert json.load(open(ctx.path('Test_site_ICESat2_holdout_lock.json')))['valid_rgts'] == lock['valid_rgts']
    assert len(M.CALLS) == n, 'cached years were downloaded again'

def test_without_shoreline():
    ctx = it.setup(dict(SITE, NAME='No_shore'))
    it.atl24.run(ctx, dict(T1='2026-10-31'))
    a = ctx.data['atl24']
    assert not a.f_land.any() and not a.f_shore.any() and not a.f_missing.all()

def test_misspelt_option():
    ctx = it.setup(SITE)
    try:
        it.atl24.run(ctx, dict(DEPTH_MAXX=30)); raise AssertionError('no error')
    except KeyError as e:
        assert 'DEPTH_MAX' in str(e)

if __name__ == '__main__':
    test_pipeline(); test_without_shoreline(); test_misspelt_option()
    print('ALL MOCK TESTS PASSED')
