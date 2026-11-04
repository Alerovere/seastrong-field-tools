"""Default options of every step. The notebook passes its own dictionaries; a misspelt name stops with a hint."""
import copy, difflib

DEFAULTS = {
    'site': dict(
        NAME='Belize_south',          # start of every file name and of the output subfolder
        AOI_FILE=None,                # polygon of the area of interest: GeoJSON, KML, shapefile or GeoPackage (any CRS)
        CRS=None,                     # projected CRS for distances and maps (None = UTM zone of the AOI)
        OUTPUT_DIR=None,              # where results go (the notebook sets <toolkit folder>/outputs)
    ),
    'atl24': dict(
        T0='2018-10-13',              # first day (ICESat-2 science data start 2018-10-13)
        T1=None,                      # last day (None = today)
        SR_RETRIES=3,                 # attempts per year if SlideRule fails
        ON_MISSING_QC_FIELD='fail',   # 'fail' or 'quarantine' (keep, but flag every photon) if ATL24 QC fields are absent
        MIN_CONFIDENCE=0.6,           # ATL24 seabed confidence below this -> f_class
        MAX_SIGMA_TVU=1.0,            # total vertical uncertainty (m) above this -> f_atl24
        DEPTH_MIN=0.3,                # depth (m) below this -> f_depth (surface / foam confusion)
        DEPTH_MAX=40.0,               # depth (m) above this -> f_depth (beyond any plausible lidar return here)
        SHORELINE_FILE=None,          # land polygons (or coastline lines) for f_land / f_shore; None = those rules are not applied
        SHORE_BUFFER=20.0,            # photons closer than this (m) to land -> f_shore
        SPIKE_WINDOW=15,              # photons in the along-track running median
        SPIKE_MIN=0.5,                # m; spike if > max(SPIKE_MIN, 3 x running MAD) from the running median
        VALID_SHARE=0.25,             # target share of photons on validation tracks
        MIN_RGT_TOTAL=4,              # fewer reference ground tracks than this -> no split
        MIN_RGT_VALID=1,              # validation tracks needed at least
        MIN_PHOTONS_SIDE=50,          # photons needed on each side of the split
        HOLDOUT_LOCK=None,            # lock file of the validation tracks (None = <outputs>/<NAME>/<NAME>_ICESat2_holdout_lock.json)
        XT_RADIUS=30.0,               # m; training passes within this distance are compared
        XT_MIN=1.0,                   # m; flag if deviation > max(XT_MIN, XT_REL x reference depth)
        XT_REL=0.20,
        XT_MIN_PASSES=3,              # independent training passes needed for a reference
        XT_BIN=10.0,                  # m; along-track bins summarised before the comparison
        XT_APPLY_TO_VALID=False,      # remove cross-track outliers from the validation set too (False = flag only)
    ),
    'atl08': dict(
        RUN=True,                     # download and clean ATL08 / PhoREAL land segments
        T0='2018-10-13',
        T1=None,
        SR_RETRIES=3,
        ATL08_LEN=100,                # m; segment length (and step)
        MANGROVE_FILE=None,           # mangrove polygons (e.g. Global Mangrove Watch for the AOI); None = all land segments in the AOI
        MANGROVE_BUFFER_M=30,         # m; buffer around the mangrove polygons
        MIN_GROUND_PH=5,              # ground photons needed in a segment
        GROUND_RANGE=[-3.0, 6.0],     # m EGM2008; plausible ground elevations (mangroves: around sea level)
        DEM_FILES={},                 # optional {'name': '/content/drive/.../dem.tif'} in EGM2008 heights, compared with ICESat-2 ground
    ),
}


def check(section, given):
    ref = DEFAULTS[section]
    for k in given or {}:
        if k not in ref:
            hint = difflib.get_close_matches(k, ref, n=1)
            raise KeyError(f"[{section}] unknown option {k!r}" + (f" — did you mean {hint[0]!r}?" if hint else '') +
                           f". Options: {', '.join(ref)}")
    out = copy.deepcopy(ref)
    out.update(copy.deepcopy(given or {}))
    return out
