"""Run the notebook's code cells (after the install cell) against a fake SlideRule. Run: python tests/test_notebook.py"""
import os, sys, json
here = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, here); sys.path.insert(0, os.path.join(here, '..', 'src'))
import mock_services as M
nb = json.load(open(os.path.join(here, '..', 'notebooks', 'icesat2_colab.ipynb')))
code = [''.join(c['source']) for c in nb['cells'] if c['cell_type'] == 'code']
code = [c for c in code if not c.lstrip().startswith('TOOLKIT_DIR =')]
code.insert(0, f"import os\nTOOLKIT_DIR = {os.path.abspath(os.path.join(here, '..'))!r}\nOUTPUTS = {M.ROOT!r}")
src = '\n\n'.join(code)
for a, b in [("AOI_FILE='/content/drive/MyDrive/SEASTRONG/aoi_belize_south.geojson'", f"AOI_FILE={M.AOI_FILE!r}"),
             ("T1=None,                      # last day (None = today)", "T1='2026-10-31',")]:
    assert a in src, a; src = src.replace(a, b)
exec(compile(src, 'notebook', 'exec'), {})
print('NOTEBOOK RAN END TO END')
