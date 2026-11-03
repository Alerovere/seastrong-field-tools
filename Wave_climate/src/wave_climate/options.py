"""Default options of every step. The notebook passes its own dictionaries; a misspelt name stops with a hint."""
import copy, difflib

DEFAULTS = {
    'site': dict(
        NAME='Belize_south',          # start of every file name and of the output subfolder
        POINT=(-88.30, 16.10),        # lon, lat of the offshore point (deep water, seaward of reefs and islands)
        REGION='global',              # Copernicus Marine wave model: 'global' or 'med'
        OUTPUT_DIR=None,              # where results go (the notebook sets <toolkit folder>/outputs)
    ),
    'download': dict(
        START='1980-01-01',           # first day (Copernicus Marine global waves start 1980, Med 1985)
        END=None,                     # last day (None = latest available)
        ERA5=True,                    # ERA5 waves + wind (CDS point time-series service)
        CMEMS=True,                   # Copernicus Marine waves (peak period, swell / wind-sea partitions)
        CMEMS_VARIABLES={'VHM0': 'hs', 'VTPK': 'tp', 'VTM10': 'tm10', 'VTM02': 'tm02', 'VMDR': 'dir',
                         'VHM0_WW': 'hs_windsea', 'VTM01_WW': 'tm_windsea', 'VMDR_WW': 'dir_windsea',
                         'VHM0_SW1': 'hs_swell', 'VTM01_SW1': 'tm_swell', 'VMDR_SW1': 'dir_swell'},
        CMEMS_SEARCH_DEG=None,        # box searched for the nearest sea cell (None = region default)
        ERA5_SEARCH_DEG=0.75,         # box searched for the nearest ERA5 wave (sea) cell, <= 1
        ERA5_LAG_DAYS=6,              # ERA5 ends about 5 days before today
        ERA5_TS_CHUNK_YEARS=20,       # years per ERA5 request (halved automatically if refused)
        CDS_RETRIES=3,
    ),
    'tides': dict(
        TIDES=True,                   # GTSM tide + surge from the Climate Data Store
        TIDE_YEARS=[2023, 2023],      # years of hourly tidal elevation for the harmonic analysis (1 year is enough)
        TIDE_AGGREGATION='hourly',    # 'hourly' or '10_min'
        SURGE_YEARS=[1995, 2024],     # years of daily-maximum storm surge (GTSM reanalysis ends 2024)
        GTSM_VERSION='v3',
        MAX_STATION_KM=30,            # GTSM output point must be within this distance of POINT
        PREDICT_YEARS=19,             # tide predicted over this many years for HAT / LAT (nodal cycle 18.6 y)
        KEEP_GLOBAL_FILES=False,      # GTSM files are global (no area option): delete them after extracting the point
    ),
    'climate': dict(
        SEASONS={'DJF': [12, 1, 2], 'MAM': [3, 4, 5], 'JJA': [6, 7, 8], 'SON': [9, 10, 11]},
        WAVE_SOURCE='cmems',          # waves for the tables and cases: 'cmems' (has Tp) or 'era5' (no Tp)
        YEARS=None,                   # [first, last] year used for the statistics (None = all downloaded)
        PERCENTILES=[10, 25, 50, 75, 90, 95, 99],
        DIR_SECTORS=16,               # direction sectors of the roses and joint tables
        HS_BINS=[0, 0.25, 0.5, 0.75, 1.0, 1.5, 2.0, 2.5, 3.0, 4.0, 6.0, 20.0],
        TP_BINS=[0, 4, 6, 8, 10, 12, 14, 16, 18, 22, 30],
        WIND_BINS=[0, 2, 4, 6, 8, 10, 12, 15, 20, 40],
    ),
    'cases': dict(
        LEVELS={'typical': 50, 'energetic': 90, 'storm': 99},   # Hs percentile of each case, per season
        BAND=0.10,                    # records with Hs within +-10 % of the case Hs give its Tp, direction, wind
        MIN_RECORDS=30,               # widen the band until at least this many records are used
        SURGE_PERCENTILE='same',      # surge of each case: 'same' percentile as Hs, or a number, or 0
        TIDE_CYCLE='spring',          # tide of each case: 'spring', 'mean' or 'neap' cycle; or 'none' (zs0 = surge only)
        DURATION_H=25,                # length of each XBeach case (one tidal day + 1 h)
        GAMMA=3.3,                    # JONSWAP peak enhancement
        SPREADING_S=10,               # XBeach directional spreading s (cosine power): ~10 wind sea, 20-30+ swell
        DTBC=1.0,                     # XBeach boundary time step (s)
        TIDE_DT_S=600,                # time step of the zs0 tide file (s)
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
