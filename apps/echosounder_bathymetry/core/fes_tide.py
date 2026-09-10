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

pyTMD expects the folder you point it at to contain the model exactly as
AVISO distributes it -- i.e. `<your_folder>/fes2022b/ocean_tide_<date>/
<constituent>_fes2022.nc[.gz]` for each tidal constituent (m2, s2, k1, o1,
...). Point `model_directory` at the parent of `fes2022b/`, not at
`fes2022b/` itself, and don't reorganize the files pyTMD is looking for --
see `describe_expected_layout()` below to print the exact relative paths
pyTMD (as currently pinned in requirements.txt) will look for.

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

from pathlib import Path
from typing import Union

import numpy as np
import pandas as pd

PathLike = Union[str, Path]

MODEL_NAME = "FES2022"


def describe_expected_layout() -> list[str]:
    """
    Return the relative file paths pyTMD expects to find under the FES2022
    model directory, as currently defined by the installed pyTMD version's
    model database. Useful for showing the user exactly what to check if
    prediction fails with a FileNotFoundError -- read directly from
    pyTMD's own data/database.json rather than guessing at an internal API,
    so it can never drift out of sync with the pinned pyTMD version.
    """
    import json as _json

    import pyTMD

    db_path = Path(pyTMD.__file__).parent / "data" / "database.json"
    with open(db_path, encoding="utf-8") as f:
        db = _json.load(f)

    entry = db.get(MODEL_NAME, {})
    return list(entry.get("z", {}).get("model_file", []))


def predict_fes2022_tide(
    model_directory: PathLike,
    longitude: float,
    latitude: float,
    timestamps: "pd.Series[pd.Timestamp]",
) -> pd.DataFrame:
    """
    Predict ocean tide elevation at one point for a series of timestamps,
    using the FES2022 global tide model.

    Parameters
    ----------
    model_directory : str or Path
        Local folder containing the FES2022 model distribution -- the
        folder that has `fes2022b/` inside it (see module docstring).
    longitude : float
        Longitude in decimal degrees (WGS84).
    latitude : float
        Latitude in decimal degrees (WGS84).
    timestamps : pd.Series
        Timestamps (naive or tz-aware, treated as UTC) to predict tide at --
        typically the scan data's timestamp column.

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
        If model_directory (or the expected files inside it) don't exist --
        the original pyTMD error message names the specific missing file.
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

    ts = pd.to_datetime(pd.Series(timestamps).rename("timestamp"))
    if ts.dt.tz is not None:
        ts = ts.dt.tz_convert("UTC").dt.tz_localize(None)
    ts = ts.dropna().sort_values().reset_index(drop=True)

    if ts.empty:
        raise ValueError("No valid timestamps to predict tide for.")

    delta_time = ts.to_numpy().astype("datetime64[s]")
    x = np.full(delta_time.shape, float(longitude))
    y = np.full(delta_time.shape, float(latitude))

    tide = compute.tide_elevations(
        x=x,
        y=y,
        delta_time=delta_time,
        directory=str(model_directory),
        model=MODEL_NAME,
        crs=4326,
        type="time series",
        standard="datetime",
    )

    water_level = np.asarray(tide).reshape(-1).astype(float)

    if water_level.shape[0] != ts.shape[0]:
        raise RuntimeError(
            "pyTMD returned an unexpected number of tide values "
            f"({water_level.shape[0]} for {ts.shape[0]} timestamps)."
        )

    return pd.DataFrame({"timestamp": ts.values, "water_level": water_level})
