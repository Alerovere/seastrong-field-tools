"""icesat2_tool: ICESat-2 ATL24 bathymetry (quality control, locked training / validation tracks for Bathymetrix-AI)
and ATL08 ground / canopy heights, downloaded with SlideRule. No Earth Engine.

Typical use (Colab)::

    import icesat2_tool as it
    ctx = it.setup(SITE)            # SITE = dict(NAME=..., AOI_FILE=..., OUTPUT_DIR=...)
    it.atl24.run(ctx, ATL24)
    it.atl08.run(ctx, ATL08)
"""
__version__ = '0.1.0'

from .core import setup
from .options import DEFAULTS
from . import core, options, atl24, atl08


def reload():
    import importlib, sys
    for n in ['options', 'core', 'atl24', 'atl08']:
        importlib.reload(sys.modules[f'{__name__}.{n}'])
    importlib.reload(sys.modules[__name__])
    print('icesat2_tool reloaded')
