"""Run the code cells of the Colab notebook (after the install cell) against fake services.
Run: python tests/test_notebook.py"""
import os, sys, json
sys.path.insert(0, os.path.dirname(__file__))
import mock_services as M
import matplotlib; matplotlib.use('Agg')

here = os.path.dirname(__file__)
nb = json.load(open(os.path.join(here, '..', 'notebooks', 'seastrong_toolkit_colab.ipynb')))
code = [''.join(c['source']) for c in nb['cells'] if c['cell_type'] == 'code']
code = [c for c in code if not c.lstrip().startswith('REPO =')]          # skip the install cell
src = '\n\n'.join(code)
for a, b in [("DRIVE_ROOT='/content/drive/MyDrive'", f"DRIVE_ROOT='{M.ROOT}'"), ('SDB_BOOT=200', 'SDB_BOOT=30'),
             ('XT_MIN_PASSES=3', 'XT_MIN_PASSES=2'), ("YEARS=[2000, 2026],        # years for sea-state", "YEARS=[2017, 2026],        # years for sea-state")]:
    assert a in src, a
    src = src.replace(a, b)
src = '\n'.join(l for l in src.splitlines() if not l.strip().startswith(('%', '!')))
ns = {}
exec(compile(src, 'notebook', 'exec'), ns)
print('NOTEBOOK RAN END TO END')
