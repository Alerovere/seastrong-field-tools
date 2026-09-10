"""
parsing.py

Functions to read raw pressure-logger exports (In-Situ PT2X-style CSV
files) into a plain pandas DataFrame.

These files start with several dozen lines of instrument metadata
(calibration coefficients, sensor serial number, etc.) before the actual
data table begins. We don't need that metadata for this pipeline, so we
just find where the real data starts and read from there.
"""

import pandas as pd


def find_header_row(path, encoding="latin1"):
    """
    Return the line index of the data header row ('Rec #, Date / Time, ...').

    The raw file has an instrument-metadata block above the actual data
    table; this scans line by line until it finds the header row.
    """
    with open(path, encoding=encoding) as f:
        for i, line in enumerate(f):
            if line.startswith("Rec #"):
                return i
    raise ValueError(f"Could not find data header row ('Rec #...') in {path}")


def load_raw(path, encoding="latin1"):
    """
    Load a raw PT2X-style logger export into a tidy DataFrame with columns:
    datetime, temp_C, pressure_psi.

    'pressure_psi' is whatever the logger itself reports (already passed
    through its internal factory + field calibration) - it is NOT yet
    corrected for the calibration issues this pipeline is designed to fix.
    """
    hdr_idx = find_header_row(path, encoding=encoding)
    df = pd.read_csv(path, skiprows=hdr_idx, encoding=encoding)
    df.columns = ["rec", "datetime", "temp_C", "pressure_psi"]
    df["datetime"] = pd.to_datetime(df["datetime"], format="mixed")
    df = df.drop(columns="rec").reset_index(drop=True)
    return df


def estimate_sampling_rate_hz(df):
    """Median time between samples -> sampling frequency in Hz."""
    dt = df["datetime"].diff().dt.total_seconds().median()
    return round(1.0 / dt, 6)
