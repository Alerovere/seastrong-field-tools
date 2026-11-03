"""Run the code cells of the Colab notebook (after the install cell) against fake services.
Run: python tests/test_notebook.py"""
import os, sys, json
sys.path.insert(0, os.path.dirname(__file__))
import mock_services as M
import matplotlib; matplotlib.use('Agg')

here = os.path.dirname(__file__)
nb = json.load(open(os.path.join(here, '..', 'notebooks', 'seastrong_toolkit_colab.ipynb')))
code = [''.join(c['source']) for c in nb['cells'] if c['cell_type'] == 'code']
code = [c for c in code if not c.lstrip().startswith('TOOLKIT_DIR =')]   # skip the install cell (Drive, pip)
# what the install cell defines: the toolkit folder (here: this checkout) and its outputs folder (the fake Drive)
code.insert(0, f"import os\nTOOLKIT_DIR = {os.path.abspath(os.path.join(here, '..'))!r}\nOUTPUTS = {M.ROOT!r}")
src = '\n\n'.join(code)
for a, b in [('SDB_BOOT=200', 'SDB_BOOT=30'),
             ('XT_MIN_PASSES=3', 'XT_MIN_PASSES=2'), ("YEARS=[2000, 2026],        # years for sea-state", "YEARS=[2017, 2026],        # years for sea-state")]:
    assert a in src, a
    src = src.replace(a, b)
src = '\n'.join(l for l in src.splitlines() if not l.strip().startswith(('%', '!')))
ns = {}
exec(compile(src, 'notebook', 'exec'), ns)
print('NOTEBOOK RAN END TO END')
