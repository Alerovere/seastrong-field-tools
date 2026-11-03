"""Step 3 — habitats: coral, seagrass, reef geomorphology, mangroves.

## Module 3 — Habitats: coral, seagrass, reef geomorphology, mangroves

**How to use the habitat layers.** They provide context for the corridors and allow the bathymetry errors
to be split by bottom type (dark seagrass tends to come out too deep, bright sand too shallow). The Allen
Coral Atlas maps only within its reef extent, so `0 = unmapped` is not the same as "no seagrass". The
mangrove extent (GMW 2020) is also used by Module 5e to select ICESat-2 vegetation segments.

**Areas** are computed at the layers' native resolution (Allen Coral Atlas 5 m, GMW 10 m) in an Earth
Engine *batch* task (no interactive memory limit, no `bestEffort` coarsening), then read back.
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
    global aca, area_fc, areas, benthic, geomorphic, gmw, gmw_vec, hab_names, hmax, img_, km2, n, nm, outs, \
           reef, sc
    ctx = bind(globals(), 'habitats', ctx)
    ctx.force = force
    figure_style()
    aca = ee.Image('ACA/reef_habitat/v2_0')
    benthic, geomorphic, reef = [aca.select(b).unmask(0) for b in ['benthic', 'geomorphic', 'reef_mask']]
    gmw = (ee.ImageCollection('projects/sat-io/open-datasets/GMW/annual-extent/GMW_MNG_2020')
           .filterBounds(roi).mosaic().select(['b1'], ['mangrove']).unmask(0))
    gmw_vec = ee.FeatureCollection('projects/sat-io/open-datasets/GMW/annual-extent/GMW_MNG_VEC_2020').filterBounds(roi)
    hmax = (ee.ImageCollection('projects/sat-io/open-datasets/global_mangrove_distribution/hmax95')
            .filterBounds(roi).mosaic().select([0], ['hmax95_m']))

    def km2(mask, scale):
        return ee.Image.pixelArea().divide(1e6).updateMask(mask).reduceRegion(
            reducer=ee.Reducer.sum(), geometry=roi, scale=scale, crs=CRS, maxPixels=1e13, tileScale=8).values().get(0)
    area_fc = ee.FeatureCollection([ee.Feature(None, {
        'seagrass_km2': km2(benthic.eq(14), HAB['AREA_SCALE_ACA']), 'coral_algae_km2': km2(benthic.eq(15), HAB['AREA_SCALE_ACA']),
        'aca_mapped_km2': km2(aca.select('benthic').mask(), HAB['AREA_SCALE_ACA']),
        'mangrove_km2': km2(gmw.eq(1), HAB['AREA_SCALE_GMW']),
        'scale_aca_m': HAB['AREA_SCALE_ACA'], 'scale_gmw_m': HAB['AREA_SCALE_GMW']})])
    hab_names = [f'{PREFIX}_habitat_areas_native_scale']
    export_table(area_fc, 'habitats', hab_names[0])
    outs = [(benthic.toUint8(), f'{PREFIX}_ACA_v2_benthic_5m', 5), (geomorphic.toUint8(), f'{PREFIX}_ACA_v2_geomorphic_5m', 5),
            (reef.toUint8(), f'{PREFIX}_ACA_v2_reef_mask_5m', 5), (gmw.toUint8(), f'{PREFIX}_GMW_v4_mangrove_2020_10m', 10)]
    for img_, nm, sc in outs:
        export_image(img_, 'habitats', nm, sc, nodata=None, to_float=False); hab_names.append(nm)
    export_table(gmw_vec, 'habitats', f'{PREFIX}_GMW_v4_mangrove_2020_polygons', fmt='GeoJSON')
    hab_names.append(f'{PREFIX}_GMW_v4_mangrove_2020_polygons')
    export_image(hmax, 'habitats', f'{PREFIX}_Mangrove_hmax95_Simard2019_30m', 30); hab_names.append(f'{PREFIX}_Mangrove_hmax95_Simard2019_30m')
    areas = {}
    if WAIT_FOR_EXPORTS:
        wait(hab_names)
        for n in hab_names: task_files(n)
        areas = read_task_csv(hab_names[0]).drop(columns=['system:index', '.geo'], errors='ignore').iloc[0].to_dict()
        print('Areas in AOI (native scale):', {k: round(float(v), 3) for k, v in areas.items()})
        set_status('habitats', 'complete')
    write_readme('habitats', 'README_03_Habitats', f"""
    # Coastal habitat layers: coral, seagrass, reef geomorphology, mangroves

    ## Files ({CRS}, aligned grid)
    | File | Content |
    |---|---|
    | `{PREFIX}_ACA_v2_benthic_5m` | Allen Coral Atlas v2.0 benthic, UInt8: 0 unmapped · 11 Sand · 12 Rubble · 13 Rock · **14 Seagrass** · **15 Coral/Algae** · 18 Microalgal Mats |
    | `{PREFIX}_ACA_v2_geomorphic_5m` | 0 unmapped · 11 Shallow Lagoon · 12 Deep Lagoon · 13 Inner Reef Flat · 14 Outer Reef Flat · 15 Reef Crest · 16 Terrestrial Reef Flat · 21 Sheltered Reef Slope · 22 Reef Slope · 23 Plateau · 24 Back Reef Slope · 25 Patch Reef |
    | `{PREFIX}_ACA_v2_reef_mask_5m` | 0 not reef · 1 reef |
    | `{PREFIX}_GMW_v4_mangrove_2020_10m` | 1 mangrove · 0 other (Global Mangrove Watch v4, 2020) |
    | `{PREFIX}_GMW_v4_mangrove_2020_polygons.geojson` | GMW polygons touching the AOI (not clipped) |
    | `{PREFIX}_Mangrove_hmax95_Simard2019_30m` | max mangrove canopy height (m), ~2000, NoData −9999 |
    | `{PREFIX}_habitat_areas_native_scale.csv` | areas inside the AOI at native scale (ACA {HAB['AREA_SCALE_ACA']} m, GMW {HAB['AREA_SCALE_GMW']} m) |

    Areas inside the AOI (km², native scale): {json.dumps({k: round(float(v), 3) for k, v in areas.items()}) if areas else 'see CSV (export not awaited)'}

    ## Method
    Catalogue layers mosaicked, clipped and exported on the run grid; no reclassification. Areas summed from pixel areas at native resolution in a batch task.

    ## Limitations
    - ACA maps only within its reef extent (shallow, clear water; PlanetScope 2018–2020): deeper or turbid seagrass is likely **unmapped (0), not absent** (`aca_mapped_km2` gives the mapped area).
    - Epochs differ (ACA 2018–2020, GMW 2020, canopy height ~2000). Local accuracy not assessed here.
    - UNEP-WCMC global seagrass polygons are not in Earth Engine.

    ## Sources / licences
    Allen Coral Atlas (2020) doi:10.5281/zenodo.3833242, CC BY 4.0 (© 2023 Allen Coral Atlas Partnership and Vulcan, Inc.).
    Global Mangrove Watch v4: Bunting et al. (2022), CC BY 4.0. Mangrove canopy height: Simard et al. (2019) Nat. Geosci. 12:40–45, CC0.
    """)
    return ctx
