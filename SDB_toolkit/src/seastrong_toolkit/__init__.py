"""SEASTRONG coastal toolkit: Earth Engine + Copernicus + ICESat-2 workflows for satellite-derived bathymetry
and coastal seascape products (SEASTRONG WP1).

Typical use in Colab::

    import seastrong_toolkit as st
    ctx = st.setup(PROJECT)          # PROJECT = dict(AOI_ASSET=..., PREFIX=..., ...)
    ctx.set('waves', WAVES); st.waves.run(ctx); st.waves.report(ctx)
    ctx.set('prescreen', PRESCREEN); st.prescreen.run(ctx); st.prescreen.report(ctx)
    ctx.set('s2', S2); st.s2.run(ctx); st.s2.report(ctx)
"""
__version__ = '0.7.1'

from .core import setup, defaults, summary, manifest, MissingSecret
from . import core, waves, prescreen, s2, dem, habitats, transport, icesat2, diagnostics

# st.<step>.report(ctx): plain-language summary of a step's results with suggested option changes
for _m in (waves, prescreen, s2, dem, habitats, transport, icesat2):
    _m.report = getattr(diagnostics, _m.__name__.rsplit('.', 1)[1])

__all__ = ['reload', 'setup', 'defaults', 'summary', 'manifest', 'MissingSecret', 'core', 'waves', 'prescreen', 's2', 'dem',
           'habitats', 'transport', 'icesat2']


def reload():
    """Re-import all modules after editing the package (alternative to IPython autoreload).
    Afterwards run the project cell and the options cells again (log-in is kept)."""
    import importlib, sys
    for name in ['core', 'waves', 'prescreen', 's2', 'dem', 'habitats', 'transport', 'icesat2', 'diagnostics']:
        importlib.reload(sys.modules[f'{__name__}.{name}'])
    importlib.reload(sys.modules[__name__])
    print('seastrong_toolkit reloaded: run st.setup(...) again')
