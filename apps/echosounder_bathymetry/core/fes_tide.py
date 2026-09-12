"""
fes_tide.py

Predict a synthetic tide water-level time series from the FES2022 global
ocean tide model, as an alternative to importing a tide-gauge CSV.

Uses pyTMD (https://pytmd.readthedocs.io/) to read the FES2022 constituent
grids and predict tide elevation at one point for an arbitrary series of
timestamps. The output has the same shape (timestamp, water_level columns)
as bathymetry_tide_processing.load_tide_data(), so it plugs directly into
process_bathymetry_with_tide_df() in that module.

Getting the FES2022 model data
-------------------------------
FES2022 is not bundled with this tool (the full distribution is tens of GB).
Request it from AVISO:
https://www.aviso.altimetry.fr/en/data/products/auxiliary-products/global-tide-fes.html

Real-world FES2022 downloads don't all come laid out the same way -- some
are the nested `fes2022b/ocean_tide_<date>/<constituent>_fes2022.nc` layout
pyTMD expects by default, some are a flat folder of `<constituent>_fes2022.nc`
files with no subfolders at all, and constituent files can be plain `.nc` or
gzip-compressed `.nc.gz`. Rather than requiring one specific layout,
predict_fes2022_tide() below searches model_directory for a handful of
common layouts and accepts whichever one actually has all 34 constituent
files, in either compression -- see _resolve_fes2022_layout().

Notes on the output
--------------------
- The predicted water level is relative to FES2022's mean sea level
  reference, not a local chart datum -- treat it the same way you would a
  tide-gauge series referenced to an arbitrary local zero: it corrects
  *relative* depth changes over the survey consistently, but isn't
  automatically tied to your chart datum.
- FES2022 predicts the astronomical ocean tide only. It does not include
  meteorological effects (storm surge, wind setup) the way a real tide
  gauge measurement would -- keep that in mind for validation/QA, same as
  you would for the barometric-compensation caveats documented for the
  pressure-sensor workflow elsewhere in this repo.
"""
from __future__ import annotations

import json
import tempfile
from pathlib import Path
from typing import Dict, List, Tuple, Union

import numpy as np
import pandas as pd

PathLike = Union[str, Path]

MODEL_NAME = "FES2022"


def _load_fes2022_database_entry() -> dict:
    """
    Read pyTMD's own FES2022 entry from its data/database.json. Used both
    to know the 34 expected constituent names, and as a template for the
    dynamically-built definition file in _resolve_fes2022_layout() --
    reading it directly rather than guessing at an internal API means this
    can never drift out of sync with whatever pyTMD version is installed.
    """
    import pyTMD

    db_path = Path(pyTMD.__file__).parent / "data" / "database.json"
    with open(db_path, encoding="utf-8") as f:
        db = json.load(f)

    entry = db.get(MODEL_NAME)
    if entry is None:
        raise RuntimeError(
            f"The installed pyTMD version has no '{MODEL_NAME}' entry in its "
            "model database -- this shouldn't happen with a supported pyTMD "
            "version. Check the pinned pyTMD version in requirements.txt."
        )
    return entry


def describe_expected_layout() -> List[str]:
    """
    Return the relative file paths pyTMD's *default* lookup expects for the
    FES2022 model, as currently defined by the installed pyTMD version.
    Shown to the user as a reference -- predict_fes2022_tide() itself is
    not limited to this exact layout, see _resolve_fes2022_layout().
    """
    entry = _load_fes2022_database_entry()
    return list(entry.get("z", {}).get("model_file", []))


def _constituent_names() -> List[str]:
    """['2n2', 'eps2', 'j1', ...] -- derived from describe_expected_layout()
    so it always matches whatever constituents the installed pyTMD actually
    ships for FES2022."""
    names = []
    for rel_path in describe_expected_layout():
        filename = Path(rel_path).name  # e.g. "2n2_fes2022.nc"
        suffix = f"_{MODEL_NAME.lower()}.nc"
        names.append(
            filename[: -len(suffix)] if filename.lower().endswith(suffix) else filename
        )
    return names


def _candidate_base_dirs(model_directory: Path) -> List[Path]:
    """
    Base directories to check for the constituent files, most-specific
    (pyTMD's own default expectation) first, flattest last.
    """
    candidates: List[Path] = []

    fes2022b = model_directory / "fes2022b"
    if fes2022b.is_dir():
        candidates.extend(sorted(fes2022b.glob("ocean_tide_*")))
        candidates.append(fes2022b)

    candidates.extend(sorted(model_directory.glob("ocean_tide_*")))
    candidates.append(model_directory)  # flat layout -- files directly here

    # de-duplicate while preserving order
    seen = set()
    unique: List[Path] = []
    for c in candidates:
        resolved = c.resolve()
        if resolved not in seen:
            seen.add(resolved)
            unique.append(c)
    return unique


def _resolve_fes2022_layout(model_directory: Path) -> Tuple[Path, Dict[str, str]]:
    """
    Find a base directory under model_directory that contains all of the
    FES2022 ocean-tide constituent files, trying several common layouts and
    accepting either plain .nc or gzip .nc.gz for each file.

    Returns
    -------
    (base_dir, {constituent_name: actual_filename_found})

    Raises
    ------
    FileNotFoundError
        Listing every layout that was tried and how many of the 34
        constituents it found there, plus the closest partial match --
        enough to tell a user *which* files are missing/misnamed rather
        than just "not found".
    """
    constituents = _constituent_names()
    tried: List[Tuple[Path, int, bool]] = []  # (dir, n_found, existed)
    best_dir = None
    best_found: Dict[str, str] = {}

    for base in _candidate_base_dirs(model_directory):
        if not base.is_dir():
            tried.append((base, 0, False))
            continue

        found: Dict[str, str] = {}
        for name in constituents:
            plain = base / f"{name}_fes2022.nc"
            gz = base / f"{name}_fes2022.nc.gz"
            if plain.exists():
                found[name] = plain.name
            elif gz.exists():
                found[name] = gz.name

        tried.append((base, len(found), True))

        if len(found) == len(constituents):
            return base, found

        if len(found) > len(best_found):
            best_found = found
            best_dir = base

    lines = []
    for base, n_found, existed in tried:
        status = f"{n_found}/{len(constituents)} constituent files found" if existed else "folder does not exist"
        lines.append(f"  {base} -- {status}")
    tried_desc = "\n".join(lines)

    closest = (
        f"\nClosest match: {best_dir} ({len(best_found)}/{len(constituents)} found)."
        if best_dir is not None
        else ""
    )

    raise FileNotFoundError(
        f"Could not find all {len(constituents)} FES2022 ocean-tide constituent "
        f"files under {model_directory}. Layouts tried:\n{tried_desc}{closest}\n"
        "Expected files are named '<constituent>_fes2022.nc' (or '.nc.gz'), "
        "e.g. 'm2_fes2022.nc' -- either directly inside the folder above, or "
        "inside a 'fes2022b/' or 'fes2022b/ocean_tide_<date>/' subfolder."
    )


def predict_fes2022_tide(
    model_directory: PathLike,
    longitude: float,
    latitude: float,
    timestamps: "pd.Series[pd.Timestamp]",
    extrapolate: bool = True,
    cutoff_km: float = 25.0,
) -> pd.DataFrame:
    """
    Predict ocean tide elevation at one point for a series of timestamps,
    using the FES2022 global tide model.

    Parameters
    ----------
    model_directory : str or Path
        Local folder containing your FES2022 download. Several common
        layouts are accepted -- see module docstring and
        _resolve_fes2022_layout() -- including a flat folder of
        '<constituent>_fes2022.nc' files with no subfolders.
    longitude : float
        Longitude in decimal degrees (WGS84).
    latitude : float
        Latitude in decimal degrees (WGS84).
    timestamps : pd.Series
        Timestamps (naive or tz-aware, treated as UTC) to predict tide at --
        typically the scan data's timestamp column.
    extrapolate : bool
        FES2022's native grid (~1/16 degree, ~7 km) masks cells it treats
        as land, which routinely includes narrow lagoons, reef flats, and
        mangrove creeks -- exactly the kind of site this tool is built for.
        With pyTMD's own default (extrapolate=False), a survey point that
        lands on one of those masked cells silently predicts NaN for
        *every* requested timestamp (it's the same x/y each time, so it's
        all-or-nothing, not a partial gap) -- no error, just an empty tide
        table downstream. Defaulting this to True instead extrapolates
        from the nearest valid open-water cells within `cutoff_km`, which
        is what you want for a nearshore point like this.
    cutoff_km : float
        Maximum distance (kilometers) from the requested point to a valid
        FES2022 cell for extrapolation to be used. 25 km comfortably
        covers being a few grid cells inside a masked lagoon/reef area at
        FES2022's resolution, without extrapolating from a cell so far
        away the result stops being meaningful.

    Returns
    -------
    pd.DataFrame
        Columns: timestamp, water_level (meters, relative to FES2022's mean
        sea level reference -- see module docstring).

    Raises
    ------
    ImportError
        If pyTMD is not installed.
    FileNotFoundError
        If model_directory, or a recognizable FES2022 layout inside it,
        can't be found -- the error lists every layout that was tried.
    RuntimeError
        If FES2022 has no valid tide value at (longitude, latitude) even
        after extrapolation -- the point is likely too far from any
        FES2022 ocean cell (or the coordinates are swapped/wrong).
    """
    try:
        import pyTMD.compute as compute
    except ImportError as exc:
        raise ImportError(
            "FES2022 tide prediction requires pyTMD. Install it with: "
            "pip install pyTMD"
        ) from exc

    model_directory = Path(model_directory).expanduser().resolve()
    if not model_directory.exists():
        raise FileNotFoundError(
            f"FES2022 model directory not found: {model_directory}"
        )

    base_dir, found_files = _resolve_fes2022_layout(model_directory)

    entry = _load_fes2022_database_entry()
    definition = dict(entry)
    definition["z"] = dict(entry["z"])
    # Order doesn't matter functionally, but keep it deterministic.
    definition["z"]["model_file"] = [
        found_files[name] for name in _constituent_names()
    ]

    ts = pd.to_datetime(pd.Series(timestamps).rename("timestamp"))
    if ts.dt.tz is not None:
        ts = ts.dt.tz_convert("UTC").dt.tz_localize(None)
    ts = ts.dropna().sort_values().reset_index(drop=True)

    if ts.empty:
        raise ValueError("No valid timestamps to predict tide for.")

    delta_time = ts.to_numpy().astype("datetime64[s]")
    # A single fixed point ("time series" type), NOT one x/y per timestamp --
    # pyTMD treats every x/y entry as its own separate "station" and predicts
    # the full time series at *each* one, so repeating the point per
    # timestamp (as an earlier version of this function did) turns an O(N)
    # prediction into an O(N^2) one -- fine for a handful of points, but for
    # thousands of scan timestamps it can run for a very long time (or
    # effectively never finish). One station, many times, is the correct
    # (and fast) shape.
    x = np.array([float(longitude)])
    y = np.array([float(latitude)])

    definition_fp = tempfile.NamedTemporaryFile(
        mode="w", suffix=".json", delete=False
    )
    try:
        json.dump(definition, definition_fp)
        definition_fp.close()

        tide = compute.tide_elevations(
            x=x,
            y=y,
            delta_time=delta_time,
            directory=str(base_dir),
            definition_file=definition_fp.name,
            crs=4326,
            type="time series",
            standard="datetime",
            extrapolate=extrapolate,
            cutoff=cutoff_km,
        )
    finally:
        Path(definition_fp.name).unlink(missing_ok=True)

    water_level = np.asarray(tide).reshape(-1).astype(float)

    if water_level.shape[0] != ts.shape[0]:
        raise RuntimeError(
            "pyTMD returned an unexpected number of tide values "
            f"({water_level.shape[0]} for {ts.shape[0]} timestamps)."
        )

    # x/y is the same single point for every timestamp (see the "one
    # station, many times" note above), so validity here isn't
    # time-dependent -- either the point resolves to a real FES2022 cell
    # (directly or via extrapolation) and every value is finite, or it
    # doesn't and *every* value is NaN. Catch the all-NaN case explicitly
    # rather than letting it silently reach the caller as an
    # empty-after-dropna tide table with no explanation.
    if not np.isfinite(water_level).any():
        extra_hint = (
            f"Extrapolation from the nearest valid cell within {cutoff_km:.0f} km "
            "was already tried and still found nothing."
            if extrapolate
            else "Extrapolation was not attempted."
        )
        raise RuntimeError(
            f"FES2022 has no valid tide data at ({latitude}, {longitude}) -- "
            "the point falls on a cell FES2022 treats as land (common for "
            "narrow lagoons, reef flats, and mangrove creeks, since "
            "FES2022's native grid is only about 1/16 degree, ~7 km). "
            f"{extra_hint} Double-check the coordinates aren't swapped, try "
            "a point a bit further into open water, increase cutoff_km, or "
            "use a tide-gauge CSV for this site instead."
        )

    return pd.DataFrame({"timestamp": ts.values, "water_level": water_level})
