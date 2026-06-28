"""
bathymetry_tide_processing.py

Utilities to merge sonar/bathymetry scan data with tide-gauge water-level data,
split the matched dataset into training/validation subsets, and export results
to CSV and GeoJSON.

Main features
-------------
- CSV import with automatic separator detection.
- Numeric parsing compatible with decimal comma and decimal point.
- Scan time conversion from UNIX time to pandas timestamp.
- Tide time parsing from either:
    1. separate DATE + TIME columns;
    2. one combined DATETIME column.
- Optional coordinate cleaning for scan data.
- Tide matching by interpolation or nearest timestamp.
- Training/validation split.
- CSV export.
- WGS84 GeoJSON export.
- UTM GeoJSON export with automatic UTM EPSG inference.
"""

from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any, Dict, Optional, Tuple, Union

import numpy as np
import pandas as pd


PathLike = Union[str, Path]


# =============================================================================
# Generic helpers
# =============================================================================


def _ensure_path(path: PathLike) -> Path:
    """
    Convert string or Path-like input to pathlib.Path.
    """
    return Path(path).expanduser().resolve()


def read_csv_auto(path: PathLike, **kwargs: Any) -> pd.DataFrame:
    """
    Read a CSV file using automatic separator detection.

    This handles comma-separated, semicolon-separated, tab-separated,
    and other common delimited files.

    Parameters
    ----------
    path : str or Path
        Path to the CSV file.
    **kwargs
        Additional keyword arguments passed to pandas.read_csv.

    Returns
    -------
    pd.DataFrame
        Imported dataframe.
    """
    path = _ensure_path(path)
    return pd.read_csv(path, sep=None, engine="python", **kwargs)


def _to_numeric(series: pd.Series) -> pd.Series:
    """
    Convert a pandas Series to numeric values.

    Accepts both decimal point and decimal comma.

    Examples
    --------
    "0.156" -> 0.156
    "0,156" -> 0.156
    """
    if series.dtype == object:
        series = (
            series.astype(str)
            .str.strip()
            .str.replace(",", ".", regex=False)
            .replace({"": np.nan, "nan": np.nan, "None": np.nan})
        )

    return pd.to_numeric(series, errors="coerce")


def _json_safe_value(value: Any) -> Any:
    """
    Convert pandas/numpy values to JSON-safe Python objects.
    """
    if pd.isna(value):
        return None

    if isinstance(value, pd.Timestamp):
        return value.isoformat()

    if isinstance(value, np.integer):
        return int(value)

    if isinstance(value, np.floating):
        return float(value)

    if isinstance(value, np.ndarray):
        return value.tolist()

    return value


def _validate_column(df: pd.DataFrame, column: Optional[str], label: str) -> None:
    """
    Validate that a column exists in a dataframe.
    """
    if column is None:
        raise ValueError(f"{label} column is required but was set to None.")

    if column not in df.columns:
        raise ValueError(
            f"{label} column '{column}' not found. "
            f"Available columns: {list(df.columns)}"
        )


# =============================================================================
# Time conversion
# =============================================================================


def infer_unix_unit(values: pd.Series) -> str:
    """
    Infer UNIX timestamp unit from the magnitude of numeric timestamp values.

    Typical magnitudes:
    - seconds:      ~1e9
    - milliseconds: ~1e12
    - microseconds: ~1e15
    - nanoseconds:  ~1e18

    Parameters
    ----------
    values : pd.Series
        Series containing UNIX timestamps.

    Returns
    -------
    str
        One of 's', 'ms', 'us', 'ns'.
    """
    numeric_values = _to_numeric(values).dropna()

    if numeric_values.empty:
        raise ValueError("Cannot infer UNIX unit from an empty time column.")

    median_abs = float(numeric_values.abs().median())

    if median_abs < 1e11:
        return "s"

    if median_abs < 1e14:
        return "ms"

    if median_abs < 1e17:
        return "us"

    return "ns"


def unix_to_timestamp(
    values: pd.Series,
    unit: str = "auto",
    timezone: Optional[str] = None,
) -> pd.Series:
    """
    Convert a UNIX time column to pandas datetime.

    Parameters
    ----------
    values : pd.Series
        UNIX time values.
    unit : str
        'auto', 's', 'ms', 'us', or 'ns'.
    timezone : str, optional
        Optional timezone name, for example 'Europe/Rome'.

    Returns
    -------
    pd.Series
        Datetime series.
    """
    numeric_values = _to_numeric(values)

    if unit == "auto":
        unit = infer_unix_unit(numeric_values)

    timestamps = pd.to_datetime(
        numeric_values,
        unit=unit,
        errors="coerce",
        utc=True,
    )

    if timezone is not None:
        timestamps = timestamps.dt.tz_convert(timezone)

    return timestamps


# =============================================================================
# Loading scan and tide data
# =============================================================================


def load_scan_data(
    scan_csv: PathLike,
    depth_column: str,
    time_column: str,
    latitude_column: Optional[str] = None,
    longitude_column: Optional[str] = None,
    unix_unit: str = "auto",
    timezone: Optional[str] = None,
    drop_missing_coordinates: bool = True,
) -> pd.DataFrame:
    """
    Load and standardize bathymetry/sonar scan data.

    The returned dataframe always contains:
    - depth
    - timestamp

    If coordinate columns are provided, it also contains:
    - latitude
    - longitude

    Parameters
    ----------
    scan_csv : str or Path
        Path to scan CSV.
    depth_column : str
        Name of depth column in the scan file.
    time_column : str
        Name of UNIX time column in the scan file.
    latitude_column : str, optional
        Name of latitude column in the scan file.
    longitude_column : str, optional
        Name of longitude column in the scan file.
    unix_unit : str
        UNIX unit: 'auto', 's', 'ms', 'us', or 'ns'.
    timezone : str, optional
        Optional timezone name.
    drop_missing_coordinates : bool
        If True, remove rows with missing latitude/longitude.

    Returns
    -------
    pd.DataFrame
        Standardized scan dataframe.
    """
    scan_df = read_csv_auto(scan_csv)

    _validate_column(scan_df, depth_column, "Scan depth")
    _validate_column(scan_df, time_column, "Scan time")

    scan_df = scan_df.copy()

    scan_df["depth"] = _to_numeric(scan_df[depth_column])
    scan_df["timestamp"] = unix_to_timestamp(
        scan_df[time_column],
        unit=unix_unit,
        timezone=timezone,
    )

    if latitude_column is not None:
        _validate_column(scan_df, latitude_column, "Scan latitude")
        scan_df["latitude"] = _to_numeric(scan_df[latitude_column])

    if longitude_column is not None:
        _validate_column(scan_df, longitude_column, "Scan longitude")
        scan_df["longitude"] = _to_numeric(scan_df[longitude_column])

    if (
        drop_missing_coordinates
        and latitude_column is not None
        and longitude_column is not None
    ):
        scan_df = scan_df.dropna(subset=["latitude", "longitude"]).copy()

    scan_df = scan_df.dropna(subset=["depth", "timestamp"]).copy()
    scan_df = scan_df.sort_values("timestamp").reset_index(drop=True)

    return scan_df


def load_tide_data(
    tide_csv: PathLike,
    water_level_column: str,
    date_column: Optional[str] = None,
    time_column: Optional[str] = None,
    datetime_column: Optional[str] = None,
    datetime_format: Optional[str] = None,
    dayfirst: Optional[bool] = None,
    timezone: Optional[str] = None,
) -> pd.DataFrame:
    """
    Load and standardize tide-gauge data.

    The returned dataframe always contains:
    - water_level
    - timestamp

    The timestamp can be built from:
    - one combined datetime column; or
    - separate date and time columns; or
    - one date column already containing date and time.

    Parameters
    ----------
    tide_csv : str or Path
        Path to tide-gauge CSV.
    water_level_column : str
        Name of water-level column.
    date_column : str, optional
        Name of date column, used if datetime_column is None.
    time_column : str, optional
        Name of time column, used together with date_column.
    datetime_column : str, optional
        Name of combined datetime column.
    datetime_format : str, optional
        Explicit pandas datetime format.
        Example: '%d/%m/%Y %H:%M:%S'
    dayfirst : bool, optional
        Use True for European day/month/year parsing.
        Use None to let pandas infer.
    timezone : str, optional
        Optional timezone name, for example 'Europe/Rome'.

    Returns
    -------
    pd.DataFrame
        Standardized tide dataframe.
    """
    tide_df = read_csv_auto(tide_csv)

    _validate_column(tide_df, water_level_column, "Tide water level")

    tide_df = tide_df.copy()
    tide_df["water_level"] = _to_numeric(tide_df[water_level_column])

    if datetime_column is not None:
        _validate_column(tide_df, datetime_column, "Tide datetime")
        datetime_values = tide_df[datetime_column].astype(str).str.strip()

    else:
        if date_column is None:
            raise ValueError(
                "You must provide either tide_datetime_column "
                "or tide_date_column."
            )

        _validate_column(tide_df, date_column, "Tide date")

        if time_column is None:
            datetime_values = tide_df[date_column].astype(str).str.strip()
        else:
            _validate_column(tide_df, time_column, "Tide time")
            datetime_values = (
                tide_df[date_column].astype(str).str.strip()
                + " "
                + tide_df[time_column].astype(str).str.strip()
            )

    to_datetime_kwargs: Dict[str, Any] = {
        "format": datetime_format,
        "errors": "coerce",
    }

    if dayfirst is not None:
        to_datetime_kwargs["dayfirst"] = dayfirst

    tide_df["timestamp"] = pd.to_datetime(
        datetime_values,
        **to_datetime_kwargs,
    )

    if timezone is not None:
        if tide_df["timestamp"].dt.tz is None:
            tide_df["timestamp"] = tide_df["timestamp"].dt.tz_localize(timezone)
        else:
            tide_df["timestamp"] = tide_df["timestamp"].dt.tz_convert(timezone)

    tide_df = tide_df.dropna(subset=["water_level", "timestamp"]).copy()
    tide_df = tide_df.sort_values("timestamp").reset_index(drop=True)

    return tide_df


# =============================================================================
# Matching scan and tide data
# =============================================================================


def _prepare_for_matching(
    scan_df: pd.DataFrame,
    tide_df: pd.DataFrame,
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    Prepare scan and tide dataframes for time matching.

    This removes timezone awareness for robust merge/interpolation operations
    if both datasets are already in equivalent local/UTC time references.
    """
    scan = scan_df.copy()
    tide = tide_df.copy()

    scan["timestamp"] = pd.to_datetime(scan["timestamp"])
    tide["timestamp"] = pd.to_datetime(tide["timestamp"])

    if getattr(scan["timestamp"].dt, "tz", None) is not None:
        scan["timestamp"] = scan["timestamp"].dt.tz_convert(None)

    if getattr(tide["timestamp"].dt, "tz", None) is not None:
        tide["timestamp"] = tide["timestamp"].dt.tz_convert(None)

    scan = scan.sort_values("timestamp").reset_index(drop=True)
    tide = tide.sort_values("timestamp").reset_index(drop=True)

    return scan, tide


def match_tide_to_scan(
    scan_df: pd.DataFrame,
    tide_df: pd.DataFrame,
    method: str = "interpolate",
    tolerance: Union[str, pd.Timedelta, None] = "15min",
) -> pd.DataFrame:
    """
    Match tide-gauge water level to scan points by timestamp.

    Parameters
    ----------
    scan_df : pd.DataFrame
        Scan dataframe with a timestamp column.
    tide_df : pd.DataFrame
        Tide dataframe with timestamp and water_level columns.
    method : str
        Matching method:
        - 'interpolate': interpolate tide level at scan timestamps.
        - 'nearest': use nearest tide timestamp within tolerance.
    tolerance : str, pd.Timedelta, or None
        Maximum allowed time distance for matching.

    Returns
    -------
    pd.DataFrame
        Scan dataframe with matched water_level and tide_correction.
    """
    if method not in {"interpolate", "nearest"}:
        raise ValueError("method must be either 'interpolate' or 'nearest'.")

    scan, tide = _prepare_for_matching(scan_df, tide_df)

    if tolerance is not None:
        tolerance = pd.Timedelta(tolerance)

    if method == "nearest":
        tide_for_merge = tide[["timestamp", "water_level"]].copy()

        merged = pd.merge_asof(
            scan.sort_values("timestamp"),
            tide_for_merge.sort_values("timestamp"),
            on="timestamp",
            direction="nearest",
            tolerance=tolerance,
        )

        merged["tide_correction"] = merged["depth"] + merged["water_level"]

        return merged

    scan = scan.copy()
    tide = tide.copy()

    scan["__source"] = "scan"
    tide["__source"] = "tide"

    scan_interp = scan[["timestamp", "__source"]].copy()
    tide_interp = tide[["timestamp", "water_level", "__source"]].copy()

    combined = pd.concat(
        [scan_interp, tide_interp],
        ignore_index=True,
        sort=False,
    )

    combined = combined.sort_values("timestamp").reset_index(drop=True)

    combined["water_level"] = combined["water_level"].interpolate(
        method="linear",
        limit_direction="both",
    )

    matched_tide = combined[combined["__source"] == "scan"][
        ["timestamp", "water_level"]
    ].copy()

    merged = pd.merge(
        scan.drop(columns=["__source"]),
        matched_tide,
        on="timestamp",
        how="left",
    )

    if tolerance is not None:
        nearest_tide_time = pd.merge_asof(
            scan[["timestamp"]].sort_values("timestamp"),
            tide[["timestamp"]]
            .rename(columns={"timestamp": "tide_timestamp"})
            .sort_values("tide_timestamp"),
            left_on="timestamp",
            right_on="tide_timestamp",
            direction="nearest",
            tolerance=tolerance,
        )

        merged["nearest_tide_timestamp"] = nearest_tide_time["tide_timestamp"].values
        missing_nearest = merged["nearest_tide_timestamp"].isna()
        merged.loc[missing_nearest, "water_level"] = np.nan

    merged["tide_correction"] = merged["depth"] + merged["water_level"]

    return merged


# =============================================================================
# Splitting
# =============================================================================


def split_training_validation(
    df: pd.DataFrame,
    train_fraction: float = 0.70,
    random_seed: int = 42,
    shuffle: bool = True,
    require_matched_tide: bool = True,
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    Split dataframe into training and validation subsets.

    By default, only rows with matched water_level are split.

    Parameters
    ----------
    df : pd.DataFrame
        Input dataframe.
    train_fraction : float
        Fraction assigned to training.
    random_seed : int
        Random seed.
    shuffle : bool
        If True, randomly shuffle before splitting.
    require_matched_tide : bool
        If True, remove rows where water_level is NaN before splitting.

    Returns
    -------
    tuple[pd.DataFrame, pd.DataFrame]
        Training dataframe, validation dataframe.
    """
    if not 0 < train_fraction < 1:
        raise ValueError("train_fraction must be between 0 and 1.")

    split_df = df.copy()

    if require_matched_tide and "water_level" in split_df.columns:
        split_df = split_df.dropna(subset=["water_level"]).copy()

    if shuffle:
        split_df = split_df.sample(
            frac=1.0,
            random_state=random_seed,
        ).reset_index(drop=True)
    else:
        split_df = split_df.reset_index(drop=True)

    n_train = int(len(split_df) * train_fraction)

    training_df = split_df.iloc[:n_train].copy()
    validation_df = split_df.iloc[n_train:].copy()

    training_df["dataset"] = "training"
    validation_df["dataset"] = "validation"

    return training_df, validation_df


# =============================================================================
# GeoJSON export
# =============================================================================


def dataframe_to_geojson(
    df: pd.DataFrame,
    output_path: PathLike,
    latitude_column: str = "latitude",
    longitude_column: str = "longitude",
) -> Path:
    """
    Export dataframe to WGS84 point GeoJSON.

    Geometry coordinates are [longitude, latitude].

    Parameters
    ----------
    df : pd.DataFrame
        Input dataframe.
    output_path : str or Path
        Output GeoJSON path.
    latitude_column : str
        Latitude column.
    longitude_column : str
        Longitude column.

    Returns
    -------
    Path
        Output path.
    """
    output_path = _ensure_path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    if latitude_column not in df.columns or longitude_column not in df.columns:
        raise ValueError(
            f"GeoJSON export requires '{latitude_column}' and "
            f"'{longitude_column}' columns. Available columns: {list(df.columns)}"
        )

    geo_df = df.copy()
    geo_df[latitude_column] = _to_numeric(geo_df[latitude_column])
    geo_df[longitude_column] = _to_numeric(geo_df[longitude_column])
    geo_df = geo_df.dropna(subset=[latitude_column, longitude_column])

    features = []

    for _, row in geo_df.iterrows():
        lat = float(row[latitude_column])
        lon = float(row[longitude_column])

        properties = {
            col: _json_safe_value(row[col])
            for col in geo_df.columns
            if col not in [latitude_column, longitude_column]
        }

        feature = {
            "type": "Feature",
            "geometry": {
                "type": "Point",
                "coordinates": [lon, lat],
            },
            "properties": properties,
        }

        features.append(feature)

    collection = {
        "type": "FeatureCollection",
        "name": output_path.stem,
        "crs": {
            "type": "name",
            "properties": {
                "name": "EPSG:4326",
            },
        },
        "features": features,
    }

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(collection, f, ensure_ascii=False, indent=2)

    return output_path


def infer_utm_epsg_from_lonlat(
    df: pd.DataFrame,
    latitude_column: str = "latitude",
    longitude_column: str = "longitude",
) -> int:
    """
    Infer the correct UTM EPSG code from median longitude/latitude.

    Northern hemisphere:
        EPSG:32601 to EPSG:32660

    Southern hemisphere:
        EPSG:32701 to EPSG:32760

    Parameters
    ----------
    df : pd.DataFrame
        Dataframe containing latitude/longitude columns.
    latitude_column : str
        Latitude column.
    longitude_column : str
        Longitude column.

    Returns
    -------
    int
        EPSG code.
    """
    if latitude_column not in df.columns or longitude_column not in df.columns:
        raise ValueError(
            f"Cannot infer UTM EPSG. Missing coordinate columns: "
            f"{latitude_column}, {longitude_column}"
        )

    coords = df[[latitude_column, longitude_column]].copy()
    coords[latitude_column] = _to_numeric(coords[latitude_column])
    coords[longitude_column] = _to_numeric(coords[longitude_column])
    coords = coords.dropna(subset=[latitude_column, longitude_column])

    if coords.empty:
        raise ValueError("Cannot infer UTM EPSG from empty coordinate dataframe.")

    median_lat = float(coords[latitude_column].median())
    median_lon = float(coords[longitude_column].median())

    utm_zone = int((median_lon + 180) // 6) + 1
    utm_zone = max(1, min(60, utm_zone))

    if median_lat >= 0:
        epsg = 32600 + utm_zone
    else:
        epsg = 32700 + utm_zone

    return epsg


def dataframe_to_utm_geojson(
    df: pd.DataFrame,
    output_path: PathLike,
    latitude_column: str = "latitude",
    longitude_column: str = "longitude",
    epsg: Optional[int] = None,
) -> Path:
    """
    Export dataframe to UTM point GeoJSON.

    UTM zone is inferred automatically from median lon/lat unless an EPSG
    code is explicitly provided.

    Requires pyproj.

    Parameters
    ----------
    df : pd.DataFrame
        Input dataframe.
    output_path : str or Path
        Output GeoJSON path.
    latitude_column : str
        Latitude column.
    longitude_column : str
        Longitude column.
    epsg : int, optional
        Manual UTM EPSG. If None, EPSG is inferred automatically.

    Returns
    -------
    Path
        Output path.
    """
    try:
        from pyproj import Transformer
    except ImportError as exc:
        raise ImportError(
            "UTM GeoJSON export requires pyproj. "
            "Install it in Colab with: !pip install -q pyproj"
        ) from exc

    output_path = _ensure_path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    if latitude_column not in df.columns or longitude_column not in df.columns:
        raise ValueError(
            f"UTM GeoJSON export requires '{latitude_column}' and "
            f"'{longitude_column}' columns. Available columns: {list(df.columns)}"
        )

    geo_df = df.copy()
    geo_df[latitude_column] = _to_numeric(geo_df[latitude_column])
    geo_df[longitude_column] = _to_numeric(geo_df[longitude_column])
    geo_df = geo_df.dropna(subset=[latitude_column, longitude_column])

    if geo_df.empty:
        raise ValueError("No valid coordinates available for UTM GeoJSON export.")

    if epsg is None:
        epsg = infer_utm_epsg_from_lonlat(
            geo_df,
            latitude_column=latitude_column,
            longitude_column=longitude_column,
        )

    transformer = Transformer.from_crs(
        "EPSG:4326",
        f"EPSG:{epsg}",
        always_xy=True,
    )

    features = []

    for _, row in geo_df.iterrows():
        lon = float(row[longitude_column])
        lat = float(row[latitude_column])

        easting, northing = transformer.transform(lon, lat)

        properties = {
            col: _json_safe_value(row[col])
            for col in geo_df.columns
            if col not in [latitude_column, longitude_column]
        }

        properties["utm_epsg"] = int(epsg)
        properties["utm_easting"] = float(easting)
        properties["utm_northing"] = float(northing)

        feature = {
            "type": "Feature",
            "geometry": {
                "type": "Point",
                "coordinates": [float(easting), float(northing)],
            },
            "properties": properties,
        }

        features.append(feature)

    collection = {
        "type": "FeatureCollection",
        "name": output_path.stem,
        "crs": {
            "type": "name",
            "properties": {
                "name": f"EPSG:{epsg}",
            },
        },
        "features": features,
    }

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(collection, f, ensure_ascii=False, indent=2)

    return output_path


# =============================================================================
# CSV and output export
# =============================================================================


def export_csv(
    df: pd.DataFrame,
    output_path: PathLike,
) -> Path:
    """
    Export dataframe to CSV.
    """
    output_path = _ensure_path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    df.to_csv(output_path, index=False)

    return output_path


def export_outputs(
    merged_df: pd.DataFrame,
    training_df: pd.DataFrame,
    validation_df: pd.DataFrame,
    output_dir: PathLike,
    export_geojson: bool = True,
    export_utm_geojson: bool = True,
    latitude_column: str = "latitude",
    longitude_column: str = "longitude",
    utm_epsg: Optional[int] = None,
) -> Dict[str, Path]:
    """
    Export merged, training, and validation datasets.

    Exports:
    - CSV always.
    - WGS84 GeoJSON if export_geojson=True.
    - UTM GeoJSON if export_utm_geojson=True.

    Parameters
    ----------
    merged_df : pd.DataFrame
        Merged dataset.
    training_df : pd.DataFrame
        Training subset.
    validation_df : pd.DataFrame
        Validation subset.
    output_dir : str or Path
        Output directory.
    export_geojson : bool
        Export WGS84 GeoJSON.
    export_utm_geojson : bool
        Export UTM GeoJSON.
    latitude_column : str
        Latitude column.
    longitude_column : str
        Longitude column.
    utm_epsg : int, optional
        Manual UTM EPSG. If None, inferred from merged_df.

    Returns
    -------
    dict
        Dictionary of output paths.
    """
    output_dir = _ensure_path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    output_paths: Dict[str, Path] = {}

    datasets = {
        "merged": merged_df,
        "training": training_df,
        "validation": validation_df,
    }

    for name, data in datasets.items():
        output_paths[f"{name}_csv"] = export_csv(
            data,
            output_dir / f"{name}.csv",
        )

    if export_geojson:
        for name, data in datasets.items():
            output_paths[f"{name}_geojson_wgs84"] = dataframe_to_geojson(
                data,
                output_dir / f"{name}_wgs84.geojson",
                latitude_column=latitude_column,
                longitude_column=longitude_column,
            )

    if export_utm_geojson:
        inferred_epsg = utm_epsg

        if inferred_epsg is None:
            inferred_epsg = infer_utm_epsg_from_lonlat(
                merged_df,
                latitude_column=latitude_column,
                longitude_column=longitude_column,
            )

        output_paths["utm_epsg"] = Path(str(inferred_epsg))

        for name, data in datasets.items():
            output_paths[f"{name}_geojson_utm"] = dataframe_to_utm_geojson(
                data,
                output_dir / f"{name}_utm_EPSG{inferred_epsg}.geojson",
                latitude_column=latitude_column,
                longitude_column=longitude_column,
                epsg=inferred_epsg,
            )

    return output_paths


# =============================================================================
# Summary
# =============================================================================


def summarize_processing_results(
    scan_df: pd.DataFrame,
    tide_df: pd.DataFrame,
    merged_df: pd.DataFrame,
    training_df: pd.DataFrame,
    validation_df: pd.DataFrame,
    water_level_column: str = "water_level",
) -> Dict[str, Any]:
    """
    Create a compact summary of processing results.

    Parameters
    ----------
    scan_df : pd.DataFrame
        Cleaned scan dataframe.
    tide_df : pd.DataFrame
        Cleaned tide dataframe.
    merged_df : pd.DataFrame
        Merged dataframe.
    training_df : pd.DataFrame
        Training subset.
    validation_df : pd.DataFrame
        Validation subset.
    water_level_column : str
        Water-level column name.

    Returns
    -------
    dict
        Summary dictionary.
    """
    total_scan = int(len(scan_df))
    total_tide = int(len(tide_df))
    total_merged = int(len(merged_df))

    if water_level_column in merged_df.columns:
        matched = int(merged_df[water_level_column].notna().sum())
        unmatched = int(merged_df[water_level_column].isna().sum())
    else:
        matched = 0
        unmatched = total_merged

    def pct(value: int, denominator: int) -> float:
        if denominator == 0:
            return 0.0
        return 100.0 * value / denominator

    if "timestamp" in scan_df.columns and len(scan_df) > 0:
        scan_time_min = scan_df["timestamp"].min()
        scan_time_max = scan_df["timestamp"].max()
    else:
        scan_time_min = None
        scan_time_max = None

    if "timestamp" in tide_df.columns and len(tide_df) > 0:
        tide_time_min = tide_df["timestamp"].min()
        tide_time_max = tide_df["timestamp"].max()
    else:
        tide_time_min = None
        tide_time_max = None

    summary = {
        "total_scan_points_after_cleaning": total_scan,
        "total_tide_points_after_cleaning": total_tide,
        "total_merged_points": total_merged,
        "matched_tide_points": matched,
        "unmatched_tide_points": unmatched,
        "matched_tide_percentage": pct(matched, total_merged),
        "unmatched_tide_percentage": pct(unmatched, total_merged),
        "training_points": int(len(training_df)),
        "validation_points": int(len(validation_df)),
        "training_percentage_of_matched": pct(len(training_df), matched),
        "validation_percentage_of_matched": pct(len(validation_df), matched),
        "scan_time_min": scan_time_min,
        "scan_time_max": scan_time_max,
        "tide_time_min": tide_time_min,
        "tide_time_max": tide_time_max,
    }

    return summary


def print_processing_summary(summary: Dict[str, Any]) -> None:
    """
    Print a readable processing summary in the notebook.
    """
    print("Processing summary")
    print("------------------")
    print(f"Scan points after cleaning:   {summary['total_scan_points_after_cleaning']}")
    print(f"Tide points after cleaning:   {summary['total_tide_points_after_cleaning']}")
    print(f"Total merged scan points:     {summary['total_merged_points']}")
    print(
        f"Matched tide points:          "
        f"{summary['matched_tide_points']} "
        f"({summary['matched_tide_percentage']:.2f}%)"
    )
    print(
        f"Unmatched scan points:        "
        f"{summary['unmatched_tide_points']} "
        f"({summary['unmatched_tide_percentage']:.2f}%)"
    )
    print()
    print(
        f"Training points:              "
        f"{summary['training_points']} "
        f"({summary['training_percentage_of_matched']:.2f}% of matched)"
    )
    print(
        f"Validation points:            "
        f"{summary['validation_points']} "
        f"({summary['validation_percentage_of_matched']:.2f}% of matched)"
    )
    print()
    print(
        f"Scan time range:              "
        f"{summary['scan_time_min']}  ->  {summary['scan_time_max']}"
    )
    print(
        f"Tide time range:              "
        f"{summary['tide_time_min']}  ->  {summary['tide_time_max']}"
    )


# =============================================================================
# Main processing function
# =============================================================================


def process_bathymetry_with_tide(
    scan_csv: PathLike,
    tide_csv: PathLike,
    output_dir: PathLike,
    scan_depth_column: str,
    scan_time_column: str,
    tide_water_level_column: str,
    tide_date_column: Optional[str] = None,
    tide_time_column: Optional[str] = None,
    tide_datetime_column: Optional[str] = None,
    scan_latitude_column: Optional[str] = None,
    scan_longitude_column: Optional[str] = None,
    scan_unix_unit: str = "auto",
    tide_datetime_format: Optional[str] = None,
    tide_dayfirst: Optional[bool] = None,
    timezone: Optional[str] = None,
    match_method: str = "interpolate",
    match_tolerance: Union[str, pd.Timedelta, None] = "15min",
    train_fraction: float = 0.70,
    random_seed: int = 42,
    shuffle_split: bool = True,
    export_geojson: bool = True,
    export_utm_geojson: bool = True,
    utm_epsg: Optional[int] = None,
    drop_missing_coordinates: bool = True,
) -> Dict[str, Any]:
    """
    Complete bathymetry + tide processing workflow.

    Parameters
    ----------
    scan_csv : str or Path
        Path to scan CSV.
    tide_csv : str or Path
        Path to tide-gauge CSV.
    output_dir : str or Path
        Output directory.
    scan_depth_column : str
        Depth column in scan file.
    scan_time_column : str
        UNIX time column in scan file.
    tide_water_level_column : str
        Water-level column in tide file.
    tide_date_column : str, optional
        Date column in tide file, used when tide_datetime_column is None.
    tide_time_column : str, optional
        Time column in tide file.
    tide_datetime_column : str, optional
        Combined date-time column in tide file.
    scan_latitude_column : str, optional
        Latitude column in scan file.
    scan_longitude_column : str, optional
        Longitude column in scan file.
    scan_unix_unit : str
        UNIX unit: 'auto', 's', 'ms', 'us', or 'ns'.
    tide_datetime_format : str, optional
        Explicit datetime format for tide data.
    tide_dayfirst : bool, optional
        True for European day/month/year parsing.
    timezone : str, optional
        Optional timezone name.
    match_method : str
        'interpolate' or 'nearest'.
    match_tolerance : str, pd.Timedelta, or None
        Matching tolerance.
    train_fraction : float
        Training fraction.
    random_seed : int
        Random seed.
    shuffle_split : bool
        Shuffle before split.
    export_geojson : bool
        Export WGS84 GeoJSON.
    export_utm_geojson : bool
        Export UTM GeoJSON.
    utm_epsg : int, optional
        Manual UTM EPSG. If None, inferred automatically.
    drop_missing_coordinates : bool
        Remove scan rows with missing coordinates.

    Returns
    -------
    dict
        Dictionary containing:
        - scan
        - tide
        - merged
        - training
        - validation
        - summary
        - output_files
    """
    output_dir = _ensure_path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    scan_df = load_scan_data(
        scan_csv=scan_csv,
        depth_column=scan_depth_column,
        time_column=scan_time_column,
        latitude_column=scan_latitude_column,
        longitude_column=scan_longitude_column,
        unix_unit=scan_unix_unit,
        timezone=timezone,
        drop_missing_coordinates=drop_missing_coordinates,
    )

    tide_df = load_tide_data(
        tide_csv=tide_csv,
        water_level_column=tide_water_level_column,
        date_column=tide_date_column,
        time_column=tide_time_column,
        datetime_column=tide_datetime_column,
        datetime_format=tide_datetime_format,
        dayfirst=tide_dayfirst,
        timezone=timezone,
    )

    merged_df = match_tide_to_scan(
        scan_df=scan_df,
        tide_df=tide_df,
        method=match_method,
        tolerance=match_tolerance,
    )

    training_df, validation_df = split_training_validation(
        merged_df,
        train_fraction=train_fraction,
        random_seed=random_seed,
        shuffle=shuffle_split,
        require_matched_tide=True,
    )

    output_paths = export_outputs(
        merged_df=merged_df,
        training_df=training_df,
        validation_df=validation_df,
        output_dir=output_dir,
        export_geojson=export_geojson,
        export_utm_geojson=export_utm_geojson,
        latitude_column="latitude",
        longitude_column="longitude",
        utm_epsg=utm_epsg,
    )

    summary = summarize_processing_results(
        scan_df=scan_df,
        tide_df=tide_df,
        merged_df=merged_df,
        training_df=training_df,
        validation_df=validation_df,
        water_level_column="water_level",
    )

    results = {
        "scan": scan_df,
        "tide": tide_df,
        "merged": merged_df,
        "training": training_df,
        "validation": validation_df,
        "summary": summary,
        "output_files": output_paths,
    }

    return results