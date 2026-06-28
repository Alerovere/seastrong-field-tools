"""
Photo-GPX geotagging utilities for Google Colab.

Purpose
-------
This module supports a workflow where GoPro photos are synchronized with one or
more GPX tracks using one reference photo that shows the GNSS date/time.

Main outputs
------------
1. Photos with GPS EXIF tags written either in-place or into copied files.
2. A GeoJSON file containing one point per successfully matched photo.
3. A CSV/TXT processing summary.

Required packages
-----------------
pip install gpxpy piexif pillow pandas matplotlib
"""

from __future__ import annotations

from pathlib import Path
from datetime import datetime, timedelta
import json
import shutil
from typing import Iterable, Optional, Sequence, Union

import gpxpy
import pandas as pd
import piexif
from PIL import Image, ExifTags
import matplotlib.pyplot as plt


PathLike = Union[str, Path]

PHOTO_EXTENSIONS = {".jpg", ".jpeg", ".JPG", ".JPEG"}
GPX_EXTENSIONS = {".gpx", ".GPX"}
EXIF_DATETIME_FORMAT = "%Y:%m:%d %H:%M:%S"
USER_DATETIME_FORMAT = "%Y-%m-%d %H:%M:%S"


# -----------------------------------------------------------------------------
# Generic path and input helpers
# -----------------------------------------------------------------------------


def clean_path(path_value: PathLike) -> Path:
    """
    Convert a path string copied from Colab/Drive into a clean Path object.

    Parameters
    ----------
    path_value : str or pathlib.Path
        Input path.

    Returns
    -------
    pathlib.Path
        Cleaned path.
    """

    if isinstance(path_value, Path):
        return path_value

    return Path(str(path_value).strip().strip('"').strip("'"))



def validate_existing_file(file_path: PathLike, label: str = "File") -> Path:
    """
    Validate that a path exists and is a file.
    """

    file_path = clean_path(file_path)

    if not file_path.exists():
        raise FileNotFoundError(f"{label} not found: {file_path}")

    if not file_path.is_file():
        raise FileNotFoundError(f"{label} is not a file: {file_path}")

    return file_path



def validate_existing_folder(folder_path: PathLike, label: str = "Folder") -> Path:
    """
    Validate that a path exists and is a folder.
    """

    folder_path = clean_path(folder_path)

    if not folder_path.exists():
        raise FileNotFoundError(f"{label} not found: {folder_path}")

    if not folder_path.is_dir():
        raise NotADirectoryError(f"{label} is not a folder: {folder_path}")

    return folder_path



def parse_path_list(path_text: Union[str, Sequence[PathLike]]) -> list[Path]:
    """
    Parse paths typed directly in a notebook cell.

    Accepts either:
    - a Python list of paths;
    - one multiline string with one path per line;
    - one comma-separated string.

    Examples
    --------
    GPX_FILES = parse_path_list('''
    /content/drive/MyDrive/site/track1.gpx
    /content/drive/MyDrive/site/track2.gpx
    ''')
    """

    if isinstance(path_text, (list, tuple)):
        raw_items = [str(item) for item in path_text]
    else:
        text = str(path_text).strip()
        if "\n" in text:
            raw_items = text.splitlines()
        else:
            raw_items = text.split(",")

    paths = []
    for item in raw_items:
        item = item.strip().strip('"').strip("'")
        if item:
            paths.append(Path(item))

    return paths



def find_photos(photo_folder: PathLike, recursive: bool = True) -> list[Path]:
    """
    Find JPG/JPEG photos inside a folder.
    """

    photo_folder = validate_existing_folder(photo_folder, label="Photo folder")
    pattern_iterator = photo_folder.rglob("*") if recursive else photo_folder.glob("*")

    photos = [
        path for path in pattern_iterator
        if path.is_file() and path.suffix in PHOTO_EXTENSIONS
    ]

    photos = sorted(photos)

    if len(photos) == 0:
        raise FileNotFoundError(f"No JPG/JPEG photos found in: {photo_folder}")

    print("Photo folder summary")
    print("--------------------")
    print(f"Photo folder: {photo_folder}")
    print(f"Photos found: {len(photos)}")

    return photos



def validate_gpx_files(gpx_files: Union[str, Sequence[PathLike]]) -> list[Path]:
    """
    Validate one or more GPX files typed in a notebook cell.
    """

    gpx_paths = parse_path_list(gpx_files)

    if len(gpx_paths) == 0:
        raise ValueError("No GPX files were provided.")

    validated = []
    for gpx_path in gpx_paths:
        gpx_path = validate_existing_file(gpx_path, label="GPX file")
        if gpx_path.suffix not in GPX_EXTENSIONS:
            raise ValueError(f"This file does not look like a GPX file: {gpx_path}")
        validated.append(gpx_path)

    print("GPX input summary")
    print("-----------------")
    print(f"GPX files provided: {len(validated)}")
    for path in validated:
        print(f"- {path}")

    return validated


# -----------------------------------------------------------------------------
# Reference photo and time synchronization
# -----------------------------------------------------------------------------


def display_photo(photo_path: PathLike, figsize: tuple[float, float] = (12, 8)) -> None:
    """
    Display a photo in the notebook.
    """

    photo_path = validate_existing_file(photo_path, label="Photo")

    image = Image.open(photo_path)

    plt.figure(figsize=figsize)
    plt.imshow(image)
    plt.axis("off")
    plt.title(photo_path.name)
    plt.show()



def parse_user_datetime(datetime_text: str) -> datetime:
    """
    Parse a manually typed datetime.

    Required format: YYYY-MM-DD HH:MM:SS
    """

    datetime_text = str(datetime_text).strip()

    try:
        return datetime.strptime(datetime_text, USER_DATETIME_FORMAT)
    except ValueError as error:
        raise ValueError(
            "Invalid datetime. Use format YYYY-MM-DD HH:MM:SS, "
            "for example 2026-06-21 13:43:16."
        ) from error



def get_exif_dict(photo_path: PathLike) -> dict:
    """
    Return EXIF metadata as a dictionary with readable tag names.
    """

    photo_path = validate_existing_file(photo_path, label="Photo")

    image = Image.open(photo_path)
    exif_data = image.getexif()

    if not exif_data:
        raise ValueError(f"No EXIF metadata found in: {photo_path}")

    return {
        ExifTags.TAGS.get(tag_id, tag_id): value
        for tag_id, value in exif_data.items()
    }



def extract_photo_datetime(photo_path: PathLike) -> datetime:
    """
    Extract the acquisition datetime from photo EXIF metadata.

    The function checks, in order:
    - DateTimeOriginal
    - DateTimeDigitized
    - DateTime
    """

    exif = get_exif_dict(photo_path)

    datetime_string = None
    for key in ["DateTimeOriginal", "DateTimeDigitized", "DateTime"]:
        if key in exif:
            datetime_string = exif[key]
            break

    if datetime_string is None:
        raise ValueError(f"No EXIF datetime field found in: {photo_path}")

    try:
        return datetime.strptime(str(datetime_string), EXIF_DATETIME_FORMAT)
    except ValueError as error:
        raise ValueError(f"Could not parse EXIF datetime: {datetime_string}") from error



def calculate_time_offset(
    reference_photo: PathLike,
    gnss_reference_time: Union[str, datetime],
) -> dict:
    """
    Calculate camera-GNSS time offset from a reference photo.

    The offset is defined as:

        offset = GNSS reference time - camera EXIF time

    Corrected photo time is then:

        corrected_time = photo_camera_time + offset
    """

    reference_photo = validate_existing_file(reference_photo, label="Reference photo")

    if isinstance(gnss_reference_time, str):
        gnss_reference_time = parse_user_datetime(gnss_reference_time)

    camera_reference_time = extract_photo_datetime(reference_photo)
    time_offset = gnss_reference_time - camera_reference_time

    print("Camera-GNSS time synchronization")
    print("--------------------------------")
    print(f"Reference photo:       {reference_photo.name}")
    print(f"Camera EXIF time:      {camera_reference_time}")
    print(f"GNSS reference time:   {gnss_reference_time}")
    print(f"Time offset:           {time_offset}")
    print(f"Time offset seconds:   {time_offset.total_seconds():.0f}")
    print(f"Time offset hours:     {time_offset.total_seconds() / 3600:.3f}")

    return {
        "reference_photo": reference_photo,
        "camera_reference_time": camera_reference_time,
        "gnss_reference_time": gnss_reference_time,
        "time_offset": time_offset,
    }


# -----------------------------------------------------------------------------
# GPX handling
# -----------------------------------------------------------------------------


def read_single_gpx(gpx_file: PathLike) -> pd.DataFrame:
    """
    Read one GPX file and extract timestamped track points.
    """

    gpx_file = validate_existing_file(gpx_file, label="GPX file")

    with open(gpx_file, "r", encoding="utf-8") as file:
        gpx = gpxpy.parse(file)

    records = []

    for track_index, track in enumerate(gpx.tracks):
        for segment_index, segment in enumerate(track.segments):
            for point_index, point in enumerate(segment.points):
                if point.time is None:
                    continue

                records.append(
                    {
                        "time": point.time,
                        "latitude": point.latitude,
                        "longitude": point.longitude,
                        "gpx_elevation": point.elevation,
                        "source_gpx": gpx_file.name,
                        "track_index": track_index,
                        "segment_index": segment_index,
                        "point_index": point_index,
                    }
                )

    if len(records) == 0:
        raise ValueError(f"No timestamped GPX track points found in: {gpx_file}")

    return pd.DataFrame(records)



def read_gpx_tracks(gpx_files: Union[str, Sequence[PathLike]]) -> pd.DataFrame:
    """
    Read and merge one or more GPX files.

    Returned times are timezone-aware UTC pandas timestamps.
    """

    gpx_files = validate_gpx_files(gpx_files)
    tables = [read_single_gpx(path) for path in gpx_files]

    gpx_track = pd.concat(tables, ignore_index=True)
    gpx_track["time"] = pd.to_datetime(gpx_track["time"], utc=True)
    gpx_track = gpx_track.sort_values("time").reset_index(drop=True)

    duplicate_count = int(gpx_track.duplicated(subset=["time"]).sum())
    if duplicate_count > 0:
        print(f"Warning: {duplicate_count} duplicate GPX timestamps found.")
        print("Keeping the first point for each duplicate timestamp.")
        gpx_track = gpx_track.drop_duplicates(subset=["time"], keep="first")
        gpx_track = gpx_track.reset_index(drop=True)

    print("GPX track summary")
    print("-----------------")
    print(f"GPX files read:  {len(gpx_files)}")
    print(f"GNSS points:     {len(gpx_track)}")
    print(f"Start time UTC:  {gpx_track['time'].min()}")
    print(f"End time UTC:    {gpx_track['time'].max()}")
    print(f"Latitude range:  {gpx_track['latitude'].min()} to {gpx_track['latitude'].max()}")
    print(f"Longitude range: {gpx_track['longitude'].min()} to {gpx_track['longitude'].max()}")

    return gpx_track


# -----------------------------------------------------------------------------
# Photo timestamp table and matching
# -----------------------------------------------------------------------------


def build_photo_time_table(
    photos: Sequence[PathLike],
    time_offset: timedelta,
) -> pd.DataFrame:
    """
    Extract EXIF timestamps from photos and apply the camera-GNSS offset.
    """

    if len(photos) == 0:
        raise ValueError("No photos were provided.")

    records = []

    for photo in photos:
        photo = clean_path(photo)

        try:
            camera_time = extract_photo_datetime(photo)
            corrected_time = camera_time + time_offset
            status = "ok"
            error_message = None
        except Exception as error:
            camera_time = None
            corrected_time = None
            status = "missing_or_invalid_exif_time"
            error_message = str(error)

        records.append(
            {
                "photo_path": photo,
                "photo_name": photo.name,
                "camera_time": camera_time,
                "corrected_gnss_time": corrected_time,
                "time_status": status,
                "time_error_message": error_message,
            }
        )

    photo_times = pd.DataFrame(records)
    photo_times["camera_time"] = pd.to_datetime(photo_times["camera_time"], errors="coerce")
    photo_times["corrected_gnss_time"] = pd.to_datetime(
        photo_times["corrected_gnss_time"],
        errors="coerce",
        utc=True,
    )

    photo_times = photo_times.sort_values(
        ["corrected_gnss_time", "photo_name"],
        na_position="last",
    ).reset_index(drop=True)

    valid_count = int(photo_times["time_status"].eq("ok").sum())
    invalid_count = len(photo_times) - valid_count

    print("Photo timestamp summary")
    print("-----------------------")
    print(f"Photos processed:      {len(photo_times)}")
    print(f"Valid EXIF times:      {valid_count}")
    print(f"Invalid EXIF times:    {invalid_count}")

    if valid_count > 0:
        print(f"First corrected time:  {photo_times['corrected_gnss_time'].min()}")
        print(f"Last corrected time:   {photo_times['corrected_gnss_time'].max()}")

    return photo_times



def match_photos_to_gpx(
    photo_times: pd.DataFrame,
    gpx_track: pd.DataFrame,
    max_delta_seconds: float = 1.0,
    output_altitude: float = 0.0,
) -> pd.DataFrame:
    """
    Match each corrected photo timestamp to the nearest GPX point.

    A photo is accepted only when the nearest GPX point is within
    max_delta_seconds. The default is 1 second.
    """

    if max_delta_seconds < 0:
        raise ValueError("max_delta_seconds must be >= 0.")

    required_photo_columns = [
        "photo_path",
        "photo_name",
        "camera_time",
        "corrected_gnss_time",
        "time_status",
    ]
    required_gpx_columns = ["time", "latitude", "longitude", "source_gpx"]

    missing_photo = [col for col in required_photo_columns if col not in photo_times.columns]
    missing_gpx = [col for col in required_gpx_columns if col not in gpx_track.columns]

    if missing_photo:
        raise KeyError(f"photo_times is missing columns: {missing_photo}")
    if missing_gpx:
        raise KeyError(f"gpx_track is missing columns: {missing_gpx}")

    photos = photo_times.copy()
    gpx = gpx_track.copy()

    photos["corrected_gnss_time"] = pd.to_datetime(
        photos["corrected_gnss_time"],
        errors="coerce",
        utc=True,
    )
    gpx["time"] = pd.to_datetime(gpx["time"], errors="coerce", utc=True)

    valid_photos = photos[
        photos["time_status"].eq("ok")
        & photos["corrected_gnss_time"].notna()
    ].copy()

    invalid_photos = photos.drop(valid_photos.index).copy()

    valid_photos = valid_photos.sort_values("corrected_gnss_time")
    gpx = gpx.dropna(subset=["time", "latitude", "longitude"]).sort_values("time")

    matched = pd.merge_asof(
        valid_photos,
        gpx,
        left_on="corrected_gnss_time",
        right_on="time",
        direction="nearest",
    )

    matched = matched.rename(columns={"time": "matched_gpx_time"})

    matched["time_delta_seconds"] = (
        matched["corrected_gnss_time"] - matched["matched_gpx_time"]
    ).dt.total_seconds()
    matched["absolute_time_delta_seconds"] = matched["time_delta_seconds"].abs()

    matched["altitude"] = float(output_altitude)
    matched["match_status"] = "ok"
    matched.loc[
        matched["absolute_time_delta_seconds"] > float(max_delta_seconds),
        "match_status",
    ] = "time_delta_too_large"

    if len(invalid_photos) > 0:
        invalid_photos["matched_gpx_time"] = pd.NaT
        invalid_photos["latitude"] = pd.NA
        invalid_photos["longitude"] = pd.NA
        invalid_photos["gpx_elevation"] = pd.NA
        invalid_photos["source_gpx"] = pd.NA
        invalid_photos["time_delta_seconds"] = pd.NA
        invalid_photos["absolute_time_delta_seconds"] = pd.NA
        invalid_photos["altitude"] = float(output_altitude)
        invalid_photos["match_status"] = invalid_photos["time_status"]

        matched = pd.concat([matched, invalid_photos], ignore_index=True, sort=False)

    matched = matched.sort_values(
        ["corrected_gnss_time", "photo_name"],
        na_position="last",
    ).reset_index(drop=True)

    total = len(matched)
    ok_count = int(matched["match_status"].eq("ok").sum())
    flagged_count = total - ok_count

    print("Photo-GPX matching summary")
    print("--------------------------")
    print(f"Photos processed:       {total}")
    print(f"Accepted matches:       {ok_count}")
    print(f"Flagged photos:         {flagged_count}")
    print(f"Max allowed delta:      {max_delta_seconds} s")

    if ok_count > 0:
        ok_rows = matched[matched["match_status"].eq("ok")]
        print(f"Largest accepted delta: {ok_rows['absolute_time_delta_seconds'].max():.3f} s")

    return matched


# -----------------------------------------------------------------------------
# EXIF GPS writing
# -----------------------------------------------------------------------------


def decimal_to_dms_rational(decimal_degree: float) -> tuple[tuple[int, int], tuple[int, int], tuple[int, int]]:
    """
    Convert decimal degrees to EXIF GPS rational DMS format.
    """

    decimal_degree = abs(float(decimal_degree))
    degrees = int(decimal_degree)
    minutes_float = (decimal_degree - degrees) * 60
    minutes = int(minutes_float)
    seconds = (minutes_float - minutes) * 60
    seconds_scaled = int(round(seconds * 1_000_000))

    return ((degrees, 1), (minutes, 1), (seconds_scaled, 1_000_000))



def build_gps_ifd(latitude: float, longitude: float, altitude: float = 0.0) -> dict:
    """
    Build the EXIF GPS IFD dictionary for piexif.
    """

    altitude = float(altitude)

    if altitude >= 0:
        altitude_ref = 0
        altitude_value = altitude
    else:
        altitude_ref = 1
        altitude_value = abs(altitude)

    return {
        piexif.GPSIFD.GPSLatitudeRef: "N" if float(latitude) >= 0 else "S",
        piexif.GPSIFD.GPSLatitude: decimal_to_dms_rational(latitude),
        piexif.GPSIFD.GPSLongitudeRef: "E" if float(longitude) >= 0 else "W",
        piexif.GPSIFD.GPSLongitude: decimal_to_dms_rational(longitude),
        piexif.GPSIFD.GPSAltitudeRef: altitude_ref,
        piexif.GPSIFD.GPSAltitude: (int(round(altitude_value * 1000)), 1000),
        piexif.GPSIFD.GPSMapDatum: "WGS-84",
    }



def write_gps_exif(
    input_photo: PathLike,
    latitude: float,
    longitude: float,
    altitude: float = 0.0,
    output_photo: Optional[PathLike] = None,
    overwrite: bool = True,
) -> Path:
    """
    Write GPS EXIF tags to one photo.

    If output_photo is None, the input photo is modified in-place.
    If output_photo is provided, the input photo is copied first and the copy is modified.
    """

    input_photo = validate_existing_file(input_photo, label="Input photo")

    if output_photo is None:
        target_photo = input_photo
    else:
        target_photo = clean_path(output_photo)
        target_photo.parent.mkdir(parents=True, exist_ok=True)

        if target_photo.exists() and not overwrite:
            return target_photo

        shutil.copy2(input_photo, target_photo)

    try:
        exif_dict = piexif.load(str(target_photo))
    except Exception:
        exif_dict = {"0th": {}, "Exif": {}, "GPS": {}, "1st": {}, "thumbnail": None}

    exif_dict["GPS"] = build_gps_ifd(
        latitude=latitude,
        longitude=longitude,
        altitude=altitude,
    )

    exif_bytes = piexif.dump(exif_dict)
    piexif.insert(exif_bytes, str(target_photo))

    return target_photo



def write_matched_photo_exif(
    photo_matches: pd.DataFrame,
    altitude: float = 0.0,
    output_folder: Optional[PathLike] = None,
    overwrite: bool = True,
    progress_every: int = 25,
) -> pd.DataFrame:
    """
    Write GPS EXIF coordinates for all accepted photo matches.

    Parameters
    ----------
    photo_matches : pandas.DataFrame
        Output of match_photos_to_gpx().
    altitude : float
        Constant Z value to write into EXIF.
    output_folder : str, Path, or None
        If None, photos are modified in-place.
        If provided, geotagged copies are written to this folder.
    overwrite : bool
        Whether existing output files can be overwritten when output_folder is used.
    progress_every : int
        Print progress every N written photos.

    Returns
    -------
    pandas.DataFrame
        Updated table with exif_output_path, exif_write_status, exif_write_error.
    """

    required_columns = ["photo_path", "photo_name", "latitude", "longitude", "match_status"]
    missing_columns = [col for col in required_columns if col not in photo_matches.columns]
    if missing_columns:
        raise KeyError(f"photo_matches is missing columns: {missing_columns}")

    results = photo_matches.copy()
    results["altitude"] = float(altitude)
    results["exif_output_path"] = None
    results["exif_write_status"] = None
    results["exif_write_error"] = None

    if output_folder is not None:
        output_folder = clean_path(output_folder)
        output_folder.mkdir(parents=True, exist_ok=True)

    ok_indices = results.index[results["match_status"].eq("ok")].tolist()
    total_to_write = len(ok_indices)
    written_counter = 0

    print("EXIF GPS writing")
    print("----------------")
    print(f"Accepted photos to write: {total_to_write}")
    print(f"Altitude/Z value:         {float(altitude)}")
    if output_folder is None:
        print("Mode:                     in-place modification")
    else:
        print(f"Mode:                     copies in {output_folder}")

    for index, row in results.iterrows():
        if row["match_status"] != "ok":
            results.at[index, "exif_write_status"] = "skipped"
            results.at[index, "exif_write_error"] = row["match_status"]
            continue

        input_photo = clean_path(row["photo_path"])
        output_photo = None if output_folder is None else output_folder / row["photo_name"]

        try:
            written_path = write_gps_exif(
                input_photo=input_photo,
                latitude=float(row["latitude"]),
                longitude=float(row["longitude"]),
                altitude=float(altitude),
                output_photo=output_photo,
                overwrite=overwrite,
            )
            results.at[index, "exif_output_path"] = written_path
            results.at[index, "exif_write_status"] = "written"
            results.at[index, "exif_write_error"] = None
        except Exception as error:
            results.at[index, "exif_output_path"] = output_photo if output_photo is not None else input_photo
            results.at[index, "exif_write_status"] = "failed"
            results.at[index, "exif_write_error"] = str(error)

        written_counter += 1
        if progress_every > 0 and (
            written_counter % progress_every == 0 or written_counter == total_to_write
        ):
            print(f"Processed {written_counter} / {total_to_write}")

    written_count = int(results["exif_write_status"].eq("written").sum())
    failed_count = int(results["exif_write_status"].eq("failed").sum())
    skipped_count = int(results["exif_write_status"].eq("skipped").sum())

    print("\nEXIF writing summary")
    print("--------------------")
    print(f"Written: {written_count}")
    print(f"Failed:  {failed_count}")
    print(f"Skipped: {skipped_count}")

    return results


# -----------------------------------------------------------------------------
# GeoJSON and summary export
# -----------------------------------------------------------------------------


def _json_safe_value(value):
    """
    Convert pandas/numpy/path/datetime values to JSON-safe values.
    """

    if pd.isna(value):
        return None

    if isinstance(value, Path):
        return str(value)

    if isinstance(value, pd.Timestamp):
        return value.isoformat()

    if isinstance(value, datetime):
        return value.isoformat()

    return value



def export_photo_points_geojson(
    photo_matches: pd.DataFrame,
    output_geojson: PathLike,
    only_ok: bool = True,
) -> Path:
    """
    Export matched photo positions as GeoJSON point features.

    Coordinates are written in standard GeoJSON order:

        [longitude, latitude, altitude]
    """

    output_geojson = clean_path(output_geojson)
    output_geojson.parent.mkdir(parents=True, exist_ok=True)

    required_columns = ["photo_name", "latitude", "longitude", "altitude", "match_status"]
    missing_columns = [col for col in required_columns if col not in photo_matches.columns]
    if missing_columns:
        raise KeyError(f"photo_matches is missing columns: {missing_columns}")

    rows = photo_matches.copy()
    if only_ok:
        rows = rows[rows["match_status"].eq("ok")].copy()

    rows = rows[rows["latitude"].notna() & rows["longitude"].notna()].copy()

    features = []
    for _, row in rows.iterrows():
        properties = {}
        for column in rows.columns:
            if column in ["latitude", "longitude", "altitude"]:
                continue
            properties[column] = _json_safe_value(row[column])

        altitude = row["altitude"] if pd.notna(row["altitude"]) else 0.0

        features.append(
            {
                "type": "Feature",
                "geometry": {
                    "type": "Point",
                    "coordinates": [
                        float(row["longitude"]),
                        float(row["latitude"]),
                        float(altitude),
                    ],
                },
                "properties": properties,
            }
        )

    feature_collection = {
        "type": "FeatureCollection",
        "name": output_geojson.stem,
        "crs": {
            "type": "name",
            "properties": {"name": "EPSG:4326"},
        },
        "features": features,
    }

    with open(output_geojson, "w", encoding="utf-8") as file:
        json.dump(feature_collection, file, indent=2)

    print("GeoJSON exported")
    print("----------------")
    print(f"Output file: {output_geojson}")
    print(f"Features:    {len(features)}")

    return output_geojson



def export_processing_summary(
    results: pd.DataFrame,
    output_csv: PathLike,
) -> Path:
    """
    Export processing table to CSV.
    """

    output_csv = clean_path(output_csv)
    output_csv.parent.mkdir(parents=True, exist_ok=True)

    table = results.copy()
    for column in table.columns:
        if table[column].dtype == "object":
            table[column] = table[column].apply(lambda value: str(value) if isinstance(value, Path) else value)

    table.to_csv(output_csv, index=False)

    print("Processing summary exported")
    print("---------------------------")
    print(f"Output file: {output_csv}")
    print(f"Rows:        {len(table)}")

    return output_csv


# -----------------------------------------------------------------------------
# Optional diagnostics
# -----------------------------------------------------------------------------


def plot_matches(
    photo_matches: pd.DataFrame,
    gpx_track: Optional[pd.DataFrame] = None,
    figsize: tuple[float, float] = (8, 8),
) -> None:
    """
    Plot GPX track and accepted/flagged photo positions.
    """

    plt.figure(figsize=figsize)

    if gpx_track is not None and len(gpx_track) > 0:
        plt.plot(
            gpx_track["longitude"],
            gpx_track["latitude"],
            linewidth=1,
            label="GPX track",
        )

    ok_rows = photo_matches[
        photo_matches["match_status"].eq("ok")
        & photo_matches["latitude"].notna()
        & photo_matches["longitude"].notna()
    ]
    flagged_rows = photo_matches[
        ~photo_matches["match_status"].eq("ok")
        & photo_matches["latitude"].notna()
        & photo_matches["longitude"].notna()
    ]

    if len(ok_rows) > 0:
        plt.scatter(ok_rows["longitude"], ok_rows["latitude"], s=25, label="Accepted photos")

    if len(flagged_rows) > 0:
        plt.scatter(
            flagged_rows["longitude"],
            flagged_rows["latitude"],
            s=40,
            marker="x",
            label="Flagged photos",
        )

    plt.xlabel("Longitude")
    plt.ylabel("Latitude")
    plt.title("Photo-GPX matches")
    plt.axis("equal")
    plt.grid(True)
    plt.legend()
    plt.show()



def print_match_report(photo_matches: pd.DataFrame) -> None:
    """
    Print a compact match report.
    """

    total = len(photo_matches)
    ok_count = int(photo_matches["match_status"].eq("ok").sum())
    flagged_count = total - ok_count

    print("Match report")
    print("------------")
    print(f"Total photos:     {total}")
    print(f"Accepted matches: {ok_count}")
    print(f"Flagged photos:   {flagged_count}")

    if ok_count > 0 and "absolute_time_delta_seconds" in photo_matches.columns:
        ok_rows = photo_matches[
            photo_matches["match_status"].eq("ok")
            & photo_matches["absolute_time_delta_seconds"].notna()
        ]
        print("\nAccepted time deltas")
        print("--------------------")
        print(f"Mean: {ok_rows['absolute_time_delta_seconds'].mean():.3f} s")
        print(f"Max:  {ok_rows['absolute_time_delta_seconds'].max():.3f} s")

    if flagged_count > 0:
        print("\nFlagged status counts")
        print("---------------------")
        print(photo_matches["match_status"].value_counts().to_string())
