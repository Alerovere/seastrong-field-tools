"""
submersion.py

Detect which part of a raw pressure record was actually recorded while the
sensor was submerged, as opposed to sitting in air before deployment or
after recovery.

Why this matters: a logger usually keeps recording during the boat ride out,
while it's being lowered into the water, and again after it's pulled back
out and is on its way back to the lab. None of that is real "wave data" -
it needs to be trimmed off before doing anything else (including
calibration, since we don't want a calibration reference to be computed
using in-air samples).
"""

import numpy as np
import pandas as pd


def manual_window(df, start_time, end_time):
    """
    Like detect_submerged_window(), but for when you already know the
    survey start/end date-time (e.g. from field notes) and would rather
    use that directly than trust auto-detection - useful when the
    in-air/in-water pressure contrast isn't clean enough for
    detect_submerged_window() to find reliably, or you simply have the
    times and prefer to be explicit.

    Parameters
    ----------
    df : DataFrame with a "datetime" column
    start_time, end_time : anything pandas.Timestamp can parse

    Returns
    -------
    (start_idx, end_idx) : row indices (inclusive) of the first/last sample
    within [start_time, end_time]. Feed these into trim_edges() first if you
    still want a safety margin trimmed off both ends.
    """
    start_time = pd.Timestamp(start_time)
    end_time = pd.Timestamp(end_time)
    in_window = df.index[(df["datetime"] >= start_time) & (df["datetime"] <= end_time)]
    if len(in_window) == 0:
        raise ValueError(f"No samples found between {start_time} and {end_time} - check the record's time range.")
    return int(in_window[0]), int(in_window[-1])


def detect_submerged_window(df, air_threshold_psi=0.5, smooth_window=5):
    """
    Find the longest contiguous stretch of the record where the (smoothed)
    pressure magnitude exceeds air_threshold_psi.

    Why "longest contiguous stretch" rather than "first time it crosses the
    threshold": deployment often involves some splashing/handling noise
    right as the sensor goes in or comes out of the water, which can
    briefly cross the threshold in both directions. Taking the single
    longest stretch above threshold is robust to that - it reliably finds
    the real, sustained deployment window rather than a transient blip.

    Parameters
    ----------
    air_threshold_psi : float
        Pressure magnitude (psi) below which a reading counts as
        "sensor in air" (i.e. close to zero gauge pressure). If your sensor's
        in-air baseline isn't close to 0 psi, or its submerged readings are
        small, you may need to adjust this.
    smooth_window : int
        Rolling-median window (in samples) used only to make the
        submerged/in-air decision more robust to single-sample noise. This
        does NOT affect the actual pressure values that get exported later.

    Returns
    -------
    (start_idx, end_idx) : the row indices (inclusive) of the detected
    submerged window in the input DataFrame.
    """
    p_smooth = df["pressure_psi"].rolling(
        smooth_window, center=True, min_periods=1
    ).median()
    submerged = p_smooth.abs() > air_threshold_psi

    run_id = (submerged != submerged.shift()).cumsum()
    runs = df.groupby(run_id).agg(
        start_idx=("datetime", lambda s: s.index[0]),
        end_idx=("datetime", lambda s: s.index[-1]),
        n=("datetime", "size"),
    )
    runs["submerged"] = submerged.groupby(run_id).first().values

    submerged_runs = runs[runs["submerged"]]
    if submerged_runs.empty:
        raise ValueError(
            "No submerged interval detected - try lowering air_threshold_psi, "
            "or check that this file actually contains a deployment."
        )

    longest = submerged_runs.loc[submerged_runs["n"].idxmax()]
    return int(longest["start_idx"]), int(longest["end_idx"])


def trim_edges(start_idx, end_idx, fs_hz, edge_trim_seconds=30):
    """
    Shrink a [start_idx, end_idx] window by edge_trim_seconds on each side.

    Even after finding the main submerged run, the first and last few
    seconds of it can still be contaminated by handling/splashing as the
    sensor was being positioned or picked back up. This trims a small,
    configurable safety margin off both ends.
    """
    n_trim = int(round(edge_trim_seconds * fs_hz))
    new_start = start_idx + n_trim
    new_end = end_idx - n_trim
    if new_start >= new_end:
        # Window too short for the requested trim - better to keep the
        # untrimmed window than to raise an error or return something empty.
        return start_idx, end_idx
    return new_start, new_end
