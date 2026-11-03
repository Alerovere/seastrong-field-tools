"""SEASTRONG coastal toolkit: Earth Engine + Copernicus + ICESat-2 workflows for satellite-derived bathymetry
and coastal seascape products (SEASTRONG WP1).

Typical use in Colab::

    import seastrong_toolkit as st
    ctx = st.setup('config.yaml')
    st.waves.run(ctx)
    st.prescreen.run(ctx)   # suggests Sentinel-2 composite months
    st.s2.run(ctx)
"""
__version__ = '0.6.1'

from .core import setup, load_config, summary, manifest, write_example_config, MissingSecret
from . import core, waves, prescreen, s2, dem, habitats, transport, icesat2

__all__ = ['reload', 'setup', 'write_example_config', 'load_config', 'summary', 'manifest', 'MissingSecret', 'core', 'waves', 'prescreen', 's2', 'dem',
           'habitats', 'transport', 'icesat2']


def reload():
    """Re-import all modules after editing the package (alternative to IPython autoreload).
    Afterwards create the context again: ctx = st.setup(CONFIG, login=False, mount_drive=False)."""
    import importlib, sys
    for name in ['core', 'waves', 'prescreen', 's2', 'dem', 'habitats', 'transport', 'icesat2']:
        importlib.reload(sys.modules[f'{__name__}.{name}'])
    importlib.reload(sys.modules[__name__])
    print('seastrong_toolkit reloaded: run st.setup(...) again')
