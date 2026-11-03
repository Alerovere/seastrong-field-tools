"""Run the notebook's code cells (after the install cell) against fake services. Run: python tests/test_notebook.py"""
import os, sys, json
here = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, here); sys.path.insert(0, os.path.join(here, '..', 'src'))
import mock_services as M
nb = json.load(open(os.path.join(here, '..', 'notebooks', 'wave_climate_colab.ipynb')))
code = [''.join(c['source']) for c in nb['cells'] if c['cell_type'] == 'code']
code = [c for c in code if not c.lstrip().startswith('TOOLKIT_DIR =')]          # install cell (Drive, pip)
code.insert(0, f"import os\nTOOLKIT_DIR = {os.path.abspath(os.path.join(here, '..'))!r}\nOUTPUTS = {M.ROOT!r}")
src = '\n\n'.join(code)
for a, b in [("START='1980-01-01'", "START='2015-01-01'"), ("SURGE_YEARS=[1995, 2024]", "SURGE_YEARS=[2020, 2024]")]:
    assert a in src, a; src = src.replace(a, b)
exec(compile(src, 'notebook', 'exec'), {})
print('NOTEBOOK RAN END TO END')
