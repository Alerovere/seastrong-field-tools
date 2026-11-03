"""Step 2 — elevation: DSM, bare-earth DEMs, water mask.

## Module 2 — Elevation: DSM, bare-earth DEMs, water mask

**Why three elevation models?** The Copernicus DEM is a *surface* model: over mangroves it gives the
canopy top. FABDEM removes forests and buildings from it with machine learning; DeltaDTM is a coastal
bare-earth model corrected with ICESat-2 and GEDI lidar. Comparing them (and ICESat-2 ground in Module 5e)
shows how uncertain the ground under mangroves is.

**Vertical datum.** All three are heights above **EGM2008** (DeltaDTM: Pronk et al. 2024), the same
reference as ICESat-2 ATL24 `ortho_h`. EGM2008 is *not* local mean sea level or chart datum: relating
them needs a separate, documented local offset (e.g. from a tide gauge).

**Release.** The Copernicus DEM is read from `COPDEM_COLLECTION` (default `COPERNICUS/DEM/GLO30_2024_1`, the
2024_1 release; the older `COPERNICUS/DEM/GLO30` is deprecated in the catalogue). FABDEM was derived from an
earlier GLO-30 release, so **DSM − FABDEM mixes two releases**: where the 2024_1 release re-edited terrain or
water, the difference is not only canopy/buildings. The `EDM` (edit mask) band of 2024_1 is exported so such
pixels can be identified.
"""
import os, re, io, json, time, hashlib, calendar, datetime as dt
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from .core import (bind, manifest, save_manifest, stage_done, stage_get, set_status, require, drive_path,
                   export_image, export_table, wait, task_files, task_status, read_task_csv, record_file,
                   write_readme, find_task, TERMINAL_BAD, OKABE_ITO, panel_labels, save_fig, empty_panel,
                   figure_style, dir_to, in_months, years_filter, aoi_shapely, aoi_bbox_wgs84, _jsonable,
                   secret, CMEMS_REGIONS)
try:
    import ee
except ImportError:  # documentation builds
    ee = None

# Settings and shared objects, set by bind() when run() is called (see core.bind)
AOI_LABEL = CFG = COPDEM_COLLECTION = CRS = CTX = DEM = DRIVE_ROOT = FOLDER_ROOT = GRID_X0 = GRID_X1 = GRID_Y0 \
    = GRID_Y1 = HAB = IS2 = MANIFEST = P = PREFIX = RUN_ID = S2 = TODAY = TR = W = WAIT_FOR_EXPORTS = aoi_fc = \
    centre = chirps = era5_gee = roi = water = None



def run(ctx=None, force=False):
    """Run this step. Same settings = same folder: finished exports and stages are re-used
    (force=True starts them again)."""
    global ddtm, dem, dem_names, dsm, edm, fab, glo30, img_, kw, n, nm, outs, s, wbm
    ctx = bind(globals(), 'dem', ctx)
    ctx.force = force
    figure_style()
    glo30 = ee.ImageCollection(COPDEM_COLLECTION).filterBounds(roi)
    dsm = glo30.select('DEM').map(lambda i: i.resample('bilinear')).mosaic().rename('DSM')
    wbm = glo30.select('WBM').mosaic().rename('WBM')
    edm = glo30.select('EDM').mosaic().rename('EDM')
    fab = ee.ImageCollection('projects/sat-io/open-datasets/FABDEM').filterBounds(roi)
    dem = fab.select('b1').map(lambda i: i.resample('bilinear')).mosaic().rename('DEM')
    ddtm = ee.Image('projects/sat-io/open-datasets/DELTARES/deltadtm_v1-1').select(0).rename('DeltaDTM').resample('bilinear')
    ddtm = ddtm.updateMask(ddtm.neq(30))
    s = DEM['SCALE']
    outs = [(dsm, f'{PREFIX}_CopDEM_GLO30_DSM_EGM08', {}), (dem, f'{PREFIX}_FABDEM_DEM_EGM08', {}),
            (dsm.subtract(dem).rename('DSM_minus_DEM'), f'{PREFIX}_DSM_minus_DEM', {}),
            (ddtm, f'{PREFIX}_DeltaDTM_v1-1_EGM08', {}),
            (wbm.toUint8(), f'{PREFIX}_CopDEM_WaterBodyMask', dict(nodata=255, to_float=False)),
            (edm.toUint8(), f'{PREFIX}_CopDEM_EditDataMask', dict(nodata=255, to_float=False))]
    dem_names = []
    for img_, nm, kw in outs:
        export_image(img_, 'dem', nm, s, **kw); dem_names.append(nm)
    MANIFEST['outputs'] = dict(fabdem=dem_names[1], deltadtm=dem_names[3], copdem_dsm=dem_names[0]); save_manifest()
    write_readme('dem', 'README_02_DEM_DSM', f"""
    # Elevation products: surface model, bare-earth models, water mask

    ## Files ({s} m, {CRS}, aligned grid, Float32, NoData −9999 unless stated)
    | File | Content |
    |---|---|
    | `{PREFIX}_CopDEM_GLO30_DSM_EGM08` | Copernicus DEM GLO-30 (`{COPDEM_COLLECTION}`) **surface** model (canopy tops, buildings), m above EGM2008 |
    | `{PREFIX}_FABDEM_DEM_EGM08` | FABDEM bare-earth (forests/buildings removed from GLO-30 by machine learning), m above EGM2008 |
    | `{PREFIX}_DSM_minus_DEM` | GLO-30 − FABDEM ≈ canopy / object height (m); **releases differ** (see Limitations) |
    | `{PREFIX}_DeltaDTM_v1-1_EGM08` | DeltaDTM coastal bare-earth DTM (GLO-30 corrected with ICESat-2 + GEDI), m above EGM2008, land < 30 m only |
    | `{PREFIX}_CopDEM_WaterBodyMask` | 0 land · 1 ocean · 2 lake · 3 river · 255 NoData (UInt8) |
    | `{PREFIX}_CopDEM_EditDataMask` | GLO-30 edit data mask (EDM, 0–13: pixels modified by terrain / hydro editing), 255 NoData |

    ## Method
    Tiles mosaicked, heights resampled bilinearly (mask: nearest), clipped to the AOI, exported on the run grid. DeltaDTM cells = 30 (clip value) masked.

    ## Vertical datum
    GLO-30, FABDEM and DeltaDTM (Pronk et al. 2024) refer to EGM2008, as ICESat-2 ATL24 `ortho_h`. EGM2008 ≠ local MSL ≠ chart datum.

    ## Limitations
    - DSM = canopy top in mangroves; bare-earth heights under dense canopy carry ~metre-level errors.
    - No bathymetry; sea surfaces flattened. Epochs differ (GLO-30 radar 2011–2015; DeltaDTM lidar era 2018–2022).
    - DSM − DEM is a rough proxy, not a validated canopy height.
    - DSM from `{COPDEM_COLLECTION}`, FABDEM from an earlier GLO-30 release: DSM − FABDEM also contains release differences, especially where EDM shows edits.

    ## Sources / licences
    Copernicus DEM GLO-30 © DLR e.V. 2010–2014 and © Airbus Defence and Space GmbH 2014–2018 (Copernicus, EU/ESA).
    FABDEM: Hawker et al. (2022) ERL 17 024016, CC BY-NC-SA 4.0. DeltaDTM: Pronk et al. (2024) Sci. Data 11:273, CC BY 4.0.
    FABDEM and DeltaDTM via the GEE community catalogue (asset IDs as above).
    """)
    if WAIT_FOR_EXPORTS:
        wait(dem_names)
        for n in dem_names: task_files(n)
        set_status('dem', 'complete')

    return ctx
