"""
calibration.py

Turns a raw pressure-sensor reading (in psi) into a true water pressure (in
Pa), by correcting the sensor's OFFSET (zero-error) and, if you have enough
reference points, its GAIN (scale-error) too.

------------------------------------------------------------------------
THE PHYSICS: why we can calibrate against a "known depth" at all
------------------------------------------------------------------------
A pressure sensor sitting under a column of still water of depth h (in
metres) experiences a hydrostatic pressure:

    P = rho * g * h

where rho is the water density (kg/m^3, ~1025 for seawater) and g is
gravitational acceleration (9.81 m/s^2). This is just weight-of-water-above
-the-sensor. If we know h exactly (because we measured it directly, e.g.
with a ruler in a bucket, or because we know how deep the sensor was
deployed), we know exactly what pressure the sensor SHOULD read. Comparing
that to what it ACTUALLY reads tells us how to fix its readings.

------------------------------------------------------------------------
WHY A SENSOR NEEDS CALIBRATING AT ALL
------------------------------------------------------------------------
Manufacturers calibrate sensors at the factory, but that calibration can
drift over time (ageing electronics, a bump during shipping, corrosion,
temperature effects, or simply time passing since the last field
calibration). This shows up as an error that has two possible parts:

- OFFSET (zero) error: every reading is shifted up or down by a constant
  amount, regardless of the true pressure. E.g. a sensor reads +2 psi even
  with zero real pressure on it.
- GAIN (scale) error: the reading is stretched or compressed relative to
  the truth - e.g. it reads 10% too high at every depth, so the error GROWS
  with depth rather than staying constant.

A single reference point can only ever tell you about a combination of the
two - it can't tell them apart. Multiple reference points at different,
known depths let you separate offset from gain (and, with 3+ points, check
whether "offset + gain" (a straight line) is even an adequate description
of the sensor's behaviour, or if it's doing something more complicated).

------------------------------------------------------------------------
1, 2, AND 3-POINT CALIBRATION
------------------------------------------------------------------------
This module fits a straight line:

    corrected_pressure_pa = slope * raw_pressure_pa + intercept

from however many (known_depth, raw_reading) points you give it.

- 1 POINT ("sensor/deployment depth calibration"):
    You only know ONE true depth - typically the water depth you measured
    (or knew in advance) at the field deployment site. With only one point,
    the fit CANNOT separate offset from gain, so we make the simplifying
    assumption that the gain is correct (slope = 1.0) and solve only for
    the offset (intercept). This is the fastest option and needs no extra
    fieldwork, but it silently assumes there's no gain error - if there
    is one, it will still be wrong away from that one reference depth.

- 2 POINTS ("two-point bucket calibration"):
    The classic, standard calibration approach: submerge the sensor in a
    bucket/tank at two different KNOWN depths (ideally spanning close to
    the range of depths you expect in the field) and note the reading at
    each. Two points exactly determine a straight line, so both slope and
    intercept are solved for. This is the minimum needed to catch a gain
    error, and is usually enough for a well-behaved sensor.

- 3+ POINTS ("three-point calibration / linearity check"):
    Add a third depth (ideally somewhere between the other two) and you
    now have more points than the 2 needed to define a line. The best-fit
    line is found by least squares, and - crucially - you can now measure
    how far each point falls from that line (the "residuals"). If the
    residuals are tiny, a straight-line (offset + gain) model is a good
    description of your sensor. If the middle point (or any point) is
    noticeably off the line, that's a sign the sensor's response isn't
    perfectly linear, and you may want to treat it with more caution (or
    add even more calibration points).

This module treats all of the above as the same underlying operation - fit
a line through 1 or more (depth, reading) points - the difference is just
how many points you supply and what you can conclude from the fit.
"""

import numpy as np
import pandas as pd

from .parsing import load_raw

G = 9.81                     # gravitational acceleration (m/s^2)
PSI_TO_PA = 6894.757293168   # 1 psi in Pa


def resolve_calibration_points(points, raw_df=None, start_idx=None, end_idx=None):
    """
    Turn a list of calibration point specs into plain (depths_m, psi) arrays.

    Each point is a dict with:
      - "depth_m": the known water depth (required)
      - "pressure_psi": the sensor's raw reading at that depth (optional)

    If "pressure_psi" is left out, it is filled in automatically as the
    mean raw reading over [start_idx, end_idx] in raw_df - this is exactly
    the "sensor/deployment depth calibration" case, where the "reading" is
    just what the sensor recorded, on average, while it sat at the known
    field deployment depth.
    """
    depths_m, measured_psi = [], []
    for p in points:
        depths_m.append(p["depth_m"])
        if "pressure_psi" in p and p["pressure_psi"] is not None:
            measured_psi.append(p["pressure_psi"])
        else:
            if raw_df is None or start_idx is None or end_idx is None:
                raise ValueError(
                    "A calibration point is missing 'pressure_psi' and no "
                    "raw_df/window was given to compute it from."
                )
            reference_psi = raw_df["pressure_psi"].iloc[start_idx:end_idx + 1].mean()
            measured_psi.append(reference_psi)
    return depths_m, measured_psi


def fit_calibration(known_depths_m, measured_pressure_psi, rho, g=G):
    """
    Fit corrected_pa = slope * raw_pa + intercept from 1 or more
    (known_depth_m, measured_pressure_psi) calibration points.

    Returns a dict with:
      slope, intercept       - the fitted calibration coefficients
      n_points                - how many calibration points were used
      target_pa, raw_pa       - the calibration points themselves, in Pa
      residuals_pa            - how far each point's raw reading (after
                                 calibration) ends up from its true value;
                                 all zero for 1 or 2 points (a line always
                                 passes exactly through 1 or 2 points), and
                                 informative for 3+ points
      r2                       - goodness-of-fit (1.0 = perfect); only
                                 meaningful with 3+ points, NaN otherwise
    """
    depths = np.atleast_1d(np.asarray(known_depths_m, dtype=float))
    raw_psi = np.atleast_1d(np.asarray(measured_pressure_psi, dtype=float))
    if len(depths) != len(raw_psi):
        raise ValueError("known_depths_m and measured_pressure_psi must be the same length")

    raw_pa = raw_psi * PSI_TO_PA
    target_pa = rho * g * depths
    n = len(depths)

    if n == 1:
        slope = 1.0
        intercept = target_pa[0] - slope * raw_pa[0]
    else:
        slope, intercept = np.polyfit(raw_pa, target_pa, 1)

    predicted_pa = slope * raw_pa + intercept
    residuals_pa = target_pa - predicted_pa

    if n >= 3:
        ss_res = np.sum(residuals_pa ** 2)
        ss_tot = np.sum((target_pa - target_pa.mean()) ** 2)
        r2 = 1 - ss_res / ss_tot if ss_tot > 0 else np.nan
    else:
        r2 = np.nan

    return {
        "slope": float(slope),
        "intercept": float(intercept),
        "n_points": n,
        "target_pa": target_pa,
        "raw_pa": raw_pa,
        "residuals_pa": residuals_pa,
        "r2": r2,
    }


def apply_calibration(pressure_psi, slope, intercept):
    """Apply a fitted calibration to a raw pressure (psi) series -> Pa."""
    raw_pa = np.asarray(pressure_psi) * PSI_TO_PA
    return slope * raw_pa + intercept


def mean_pressure_from_file(path, start_time=None, end_time=None, encoding="latin1"):
    """
    Optional helper for bucket tests: if you logged each bucket dip with the
    instrument itself (rather than just writing the reading down by hand),
    load that raw file and return the mean pressure (psi) over an optional
    [start_time, end_time] window (strings pandas can parse, e.g.
    "2026-07-20 09:15:00"), or the whole file if left as None.
    """
    df = load_raw(path, encoding=encoding)
    if start_time is not None:
        df = df[df["datetime"] >= pd.Timestamp(start_time)]
    if end_time is not None:
        df = df[df["datetime"] <= pd.Timestamp(end_time)]
    return df["pressure_psi"].mean()


def plot_calibration_fit(fit_result, out_path=None):
    """
    Diagnostic plot for a fitted calibration: known target pressure vs. raw
    reading, the fitted line, and (for 3+ points) the residual of each point.
    Most useful for 2 and 3+ point calibrations - for a single point there's
    only one dot and nothing to visually check.
    """
    import matplotlib.pyplot as plt

    raw_pa = fit_result["raw_pa"]
    target_pa = fit_result["target_pa"]
    slope, intercept = fit_result["slope"], fit_result["intercept"]

    x_line = np.linspace(raw_pa.min() * 0.95 if raw_pa.min() != 0 else -100,
                          raw_pa.max() * 1.05 if raw_pa.max() != 0 else 100, 50)
    y_line = slope * x_line + intercept

    fig, ax = plt.subplots(figsize=(5.5, 5))
    ax.plot(x_line, y_line, "-", color="tab:blue", label=f"fit: y={slope:.4f}x+{intercept:.1f}")
    ax.scatter(raw_pa, target_pa, color="tab:red", zorder=3, label="calibration points")
    ax.set_xlabel("Raw sensor reading (Pa)")
    ax.set_ylabel("True hydrostatic pressure at known depth (Pa)")
    title = f"Calibration fit ({fit_result['n_points']} point(s))"
    if not np.isnan(fit_result["r2"]):
        title += f", R²={fit_result['r2']:.4f}"
    ax.set_title(title)
    ax.legend(fontsize=8)
    fig.tight_layout()
    if out_path:
        fig.savefig(out_path, dpi=130)
    return fig
