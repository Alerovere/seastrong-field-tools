"""SEASTRONG coastal toolkit: Earth Engine + Copernicus + ICESat-2 workflows for satellite-derived bathymetry
and coastal seascape products (SEASTRONG WP1).

Typical use in Colab::

    import seastrong_toolkit as st
    ctx = st.setup('config.yaml')
    st.waves.run(ctx)
    st.prescreen.run(ctx)   # suggests Sentinel-2 composite months
    st.s2.run(ctx)
"""
__version__ = '0.6.0'

from .core import setup, load_config, summary, manifest, write_example_config, MissingSecret
from . import core, waves, prescreen, s2, dem, habitats, transport, icesat2

__all__ = ['setup', 'write_example_config', 'load_config', 'summary', 'manifest', 'MissingSecret', 'core', 'waves', 'prescreen', 's2', 'dem',
           'habitats', 'transport', 'icesat2']
