"""wave_climate: wave, wind, tide and storm-surge climate at an offshore point, with seasonal tables and
representative XBeach boundary conditions. Data: ERA5 (CDS point time series), Copernicus Marine waves,
GTSM tide and surge (CDS). No Earth Engine.

Typical use (Colab)::

    import wave_climate as wc
    ctx = wc.setup(SITE)
    wc.download.run(ctx, DOWNLOAD)
    wc.climate.run(ctx, CLIMATE)
    wc.tides.run(ctx, TIDES)
    wc.cases.run(ctx, CASES)
    wc.seastate.run(ctx, SEASTATE)   # days to leave out of the Earth Engine Sentinel-2 composite
"""
__version__ = '0.2.0'

from .core import setup, MissingSecret
from .options import DEFAULTS
from . import core, options, download, climate, tides, cases, seastate


def reload():
    """Re-import the modules after editing the code; then run the cells from the site cell down."""
    import importlib, sys
    for n in ['options', 'core', 'download', 'climate', 'tides', 'cases', 'seastate']:
        importlib.reload(sys.modules[f'{__name__}.{n}'])
    importlib.reload(sys.modules[__name__])
    print('wave_climate reloaded')
