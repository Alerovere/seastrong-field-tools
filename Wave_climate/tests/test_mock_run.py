"""End-to-end run against fake services. Run: python tests/test_mock_run.py"""
import os, sys, json
sys.path.insert(0, os.path.dirname(__file__)); sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
import mock_services as M
import wave_climate as wc
import pandas as pd

SITE = dict(NAME='Test_site', POINT=(M.LON0, M.LAT0), OUTPUT_DIR=M.ROOT)

def run_all(tides=None):
    ctx = wc.setup(SITE)
    wc.download.run(ctx, dict(START='2015-01-01'))
    wc.climate.run(ctx, dict(SEASONS={'Northers Nov-Feb': [11, 12, 1, 2], 'Dry Mar-May': [3, 4, 5], 'Wet Jun-Oct': [6, 7, 8, 9, 10]}))
    wc.tides.run(ctx, tides or dict(SURGE_YEARS=[2015, 2024]))
    wc.cases.run(ctx, {})
    return ctx

def test_pipeline():
    ctx = run_all()
    c = ctx.data['cases']
    assert len(c) == 9 and c.Hm0.is_monotonic_increasing is False
    for s, g in c.groupby('season'): assert g.set_index('level').Hm0['typical'] < g.set_index('level').Hm0['storm']
    nort = c[c.season.str.startswith('Northers')].set_index('level'); dry = c[c.season.str.startswith('Dry')].set_index('level')
    assert nort.Hm0['typical'] > dry.Hm0['typical']                      # synthetic winter waves are larger
    lev = ctx.data['tide_levels'].set_index('level').m_above_model_MSL
    assert lev['HAT'] > lev['MHWS'] > lev['MHW'] > 0 > lev['MLW'] > lev['MLWS'] > lev['LAT']
    tab = ctx.data['tide_constituents'].set_index('constituent').amplitude_m
    assert abs(tab['M2'] - 0.08) < 0.01 and abs(tab['K1'] - 0.06) < 0.015, tab.head()
    d = os.path.join(ctx.root, 'xbeach', c.case.iloc[0])
    j = open(os.path.join(d, 'jonswap.txt')).read().split(); assert len(j) == 7
    tide = pd.read_csv(os.path.join(d, 'tide.txt'), sep=' ', header=None)
    assert tide[0].iloc[-1] == 25 * 3600 and abs(tide[1].iloc[0] - c.surge_m.iloc[0]) < 0.02   # starts at MSL rising
    x = pd.ExcelFile(os.path.join(ctx.root, 'Test_site_wave_wind_tide_climate.xlsx'))
    assert {'README', 'wave_statistics', 'wind_statistics', 'hs_x_direction', 'hs_x_tp', 'tide_levels', 'cases'} <= set(x.sheet_names)
    txt = json.dumps(ctx.log) + open(os.path.join(ctx.root, 'xbeach', c.case.iloc[0], 'params_boundary.txt')).read()
    assert 'xxxx-key' not in txt and '"pw"' not in txt
    js = ctx.data['tables']['hs_x_direction']
    assert abs(js.groupby('period').percent.sum() - 100).max() < 1e-6

def test_rerun_uses_cache():
    n = len(M.LOG['cds']), len(M.LOG['cmems'])
    run_all()
    assert len(M.LOG['cds']) == n[0] and len(M.LOG['cmems']) == n[1]

def test_misspelt_option():
    ctx = wc.setup(SITE)
    try:
        wc.climate.run(ctx, dict(SEASON={'a': [1]})); raise AssertionError('no error')
    except KeyError as e:
        assert 'SEASONS' in str(e)

if __name__ == '__main__':
    test_pipeline(); test_rerun_uses_cache(); test_misspelt_option()
    print('ALL MOCK TESTS PASSED')
