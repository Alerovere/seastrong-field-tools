"""
pipeline.py

Ties parsing.py, submersion.py, and calibration.py together into one
function, process_site(), that goes from "raw logger CSV" to "calibrated,
trimmed, OCEANLYZ-ready files" for a single sensor deployment.
"""

import os

import matplotlib.pyplot as plt

from .parsing import load_raw, estimate_sampling_rate_hz
from .submersion import detect_submerged_window, trim_edges, manual_window
from .calibration import (
    G,
    resolve_calibration_points,
    fit_calibration,
    apply_calibration,
)
from .staircase import detect_calibration_steps, label_plateaus


def trim_and_index(df, start_idx, end_idx):
    """Trim to [start_idx, end_idx] and add an elapsed_s column starting at 0."""
    trimmed = df.iloc[start_idx:end_idx + 1].reset_index(drop=True)
    t0 = trimmed["datetime"].iloc[0]
    trimmed["elapsed_s"] = (trimmed["datetime"] - t0).dt.total_seconds()
    return trimmed


def plot_qc(raw_df, clean_df, site_name, out_path=None):
    """Quick before/after QC plot (1-min mean): raw vs. calibrated pressure."""
    fig, axes = plt.subplots(2, 1, figsize=(11, 7))

    raw_1m = raw_df.set_index("datetime")["pressure_psi"].resample("1min").mean()
    axes[0].plot(raw_1m.index, raw_1m.values, color="tab:gray")
    axes[0].axhline(0, color="k", lw=0.6, ls="--")
    axes[0].set_title(f"{site_name}: raw pressure (psi), full record")
    axes[0].set_ylabel("psi")

    clean_1m = clean_df.set_index("datetime")["pressure_pa"].resample("1min").mean()
    elapsed_hours = (clean_1m.index - clean_1m.index[0]).total_seconds() / 3600
    axes[1].plot(elapsed_hours, clean_1m.values, color="tab:blue")
    axes[1].set_title(f"{site_name}: calibrated water pressure (Pa), submerged window only")
    axes[1].set_xlabel("Elapsed hours since deployment start")
    axes[1].set_ylabel("Pa")

    fig.tight_layout()
    if out_path:
        fig.savefig(out_path, dpi=130)
    return fig


def process_site(site, input_dir=".", output_dir=".", raw_df=None):
    """
    Run the full pipeline for one site config:
      1. Load the raw logger file (or reuse `raw_df` if you already loaded
         it - handy if you also want it for plotting afterwards, since
         parsing these files is the slowest step and there's no reason to
         do it twice).
      2. Auto-detect the submerged window (and trim a safety buffer off its edges).
      3. Resolve and fit the calibration (1, 2, or 3+ points - see calibration.py).
      4. Apply the calibration to the whole record, convert units, and trim
         to the submerged window.
      5. Write "<output_dir>/clean.csv" (full detail) and
         "<output_dir>/oceanlyz.csv" (single-column Pa, ready for OCEANLYZ).

    `output_dir` is used exactly as given - it is NOT joined with the site
    name here. Callers that want a folder named after the site (e.g. the
    notebook does) should build that path themselves, once, before calling
    this function, e.g.:

        site_dir = os.path.join("results", site["name"])
        os.makedirs(site_dir, exist_ok=True)
        process_site(site, input_dir=..., output_dir=site_dir)

    That way there's a single, explicit place the folder gets named and
    created, instead of this function and its caller each guessing the
    same path independently (and risking drifting out of sync).

    `site` is a dict with:
      name, raw_csv, height_above_bed_m, rho,
      calibration_points: [{"depth_m": ..., "pressure_psi": ...-or-omit}, ...]

    Returns (clean_df, report_dict, fit_result_dict, raw_df).
    """
    name = site["name"]
    path = os.path.join(input_dir, site["raw_csv"])
    rho = site["rho"]
    os.makedirs(output_dir, exist_ok=True)

    if raw_df is None:
        raw_df = load_raw(path)
    fs_hz = estimate_sampling_rate_hz(raw_df)

    raw_start_idx, raw_end_idx = detect_submerged_window(raw_df)
    start_idx, end_idx = trim_edges(raw_start_idx, raw_end_idx, fs_hz)

    depths_m, measured_psi = resolve_calibration_points(
        site["calibration_points"], raw_df, start_idx, end_idx
    )
    fit_result = fit_calibration(depths_m, measured_psi, rho)

    df = raw_df.copy()
    df["pressure_pa"] = apply_calibration(
        df["pressure_psi"], fit_result["slope"], fit_result["intercept"]
    )
    df["pressure_dbar"] = df["pressure_pa"] / 1e4
    df["water_depth_m"] = df["pressure_pa"] / (rho * G)

    clean_df = trim_and_index(df, start_idx, end_idx)

    full_out = clean_df[[
        "datetime", "elapsed_s", "temp_C",
        "pressure_psi", "pressure_pa", "pressure_dbar", "water_depth_m",
    ]].rename(columns={"pressure_psi": "pressure_psi_raw"})

    clean_path = os.path.join(output_dir, "clean.csv")
    full_out.to_csv(clean_path, index=False)

    oceanlyz_path = os.path.join(output_dir, "oceanlyz.csv")
    clean_df["pressure_pa"].to_csv(oceanlyz_path, index=False, header=False)

    report = {
        "site": name,
        "raw_file": path,
        "n_calibration_points": fit_result["n_points"],
        "slope": fit_result["slope"],
        "intercept_pa": fit_result["intercept"],
        "r2": fit_result["r2"],
        "sampling_rate_hz": fs_hz,
        "submerged_start": clean_df["datetime"].iloc[0],
        "submerged_end": clean_df["datetime"].iloc[-1],
        "n_samples": len(clean_df),
        "duration_hours": clean_df["elapsed_s"].iloc[-1] / 3600,
        "height_above_bed_m": site["height_above_bed_m"],
        "rho": rho,
        "site_dir": output_dir,
        "clean_csv": clean_path,
        "oceanlyz_csv": oceanlyz_path,
    }
    return clean_df, report, fit_result, raw_df


def process_calibration(
    calib_csv,
    start_time,
    end_time,
    nominal_depths,
    rho,
    input_dir=".",
    rope_offset_m=0.0,
    expected_steps=None,
    encoding="latin1",
    **detect_kwargs,
):
    """
    Turn a rope-drop calibration file into a fitted slope/intercept.

    Runs the whole staircase workflow: load the raw file, trim to
    [start_time, end_time], barometric-correct using the flat stretches at
    each end, detect the depth-hold plateaus in between, label them with
    known depths (nominal_depths + rope_offset_m), and fit the calibration.

    Parameters
    ----------
    calib_csv : filename, resolved as os.path.join(input_dir, calib_csv)
    start_time, end_time : bracket the whole test, including a bit of flat
        in-air record on both ends (see staircase.barometric_correct)
    nominal_depths : list of rope depths (m), one per expected plateau, in
        chronological order, e.g. [0.5, 1.0, 1.5, 2.0, 1.5, 1.0, 0.5]. If
        this doesn't match the number of plateaus actually detected, this
        raises with a clear message - check plot_staircase() and either fix
        detect_kwargs or the list.
    rho : water density (kg/m^3) used to convert depths to target pressure
        for this test (fresh ~1000, seawater ~1025 - use whatever the dip
        test was actually done in)
    rope_offset_m : added to every nominal depth - the distance from the
        rope's depth markings to the sensor's own pressure port
    expected_steps : optional int, just for the "found N, not the expected
        M" sanity message
    **detect_kwargs : passed through to detect_calibration_steps() (e.g.
        std_threshold, std_window_s, min_duration_s to retune step detection)

    Returns
    -------
    dict with:
        fit_result   - from calibration.fit_calibration() (slope, intercept, r2, ...)
        steps        - labeled plateau table (nominal_depth_m, depth_m, mean_psi, ...)
        window_df    - trimmed + barometric-corrected raw calibration data (for plotting)
        pre_baseline, post_baseline - the air readings used for the correction
        fs_hz        - sampling rate of the calibration file
    """
    path = os.path.join(input_dir, calib_csv)
    raw_df = load_raw(path, encoding=encoding)
    fs_hz = estimate_sampling_rate_hz(raw_df)

    steps, window_df, pre_baseline, post_baseline = detect_calibration_steps(
        raw_df, fs_hz, start_time, end_time, expected_steps=expected_steps, **detect_kwargs
    )
    labeled = label_plateaus(steps, nominal_depths, offset_m=rope_offset_m)
    fit_result = fit_calibration(labeled["depth_m"].tolist(), labeled["mean_psi"].tolist(), rho)

    return {
        "fit_result": fit_result,
        "steps": labeled,
        "window_df": window_df,
        "pre_baseline": pre_baseline,
        "post_baseline": post_baseline,
        "fs_hz": fs_hz,
        "calib_file": path,
    }


def process_deployment(
    site,
    calibration,
    input_dir=".",
    output_dir=".",
    raw_df=None,
    encoding="latin1",
    edge_trim_seconds=0,
    recovery_tail_seconds=30,
):
    """
    Apply a calibration already fitted by process_calibration() to a
    deployment/wave file, trimmed to a manually-specified survey window
    (rather than detect_submerged_window()'s auto-detection) - use this
    when you know the survey start/end date-time from field notes and
    trust that more than an automatic threshold-based guess.

    Parameters
    ----------
    site : dict with:
        name, raw_csv, height_above_bed_m, rho,
        survey_start, survey_end   - manual window, anything pandas.Timestamp can parse
        recovery_depth_m           - optional, a rough depth measured right
                                      at recovery; used only as a sanity
                                      cross-check against the modeled depth
                                      at the end of the record, NOT as a
                                      calibration input
    calibration : the dict returned by process_calibration() - only
        calibration["fit_result"]["slope"]/["intercept"] are used, so you
        can also pass a bare {"fit_result": {...}} or reuse a fit_result
        dict directly (see the `_slope_intercept` fallback below)
    edge_trim_seconds : optional safety margin trimmed off both ends of the
        manual window (0 by default - a manual window is assumed already
        accurate; set this if you still want a buffer)
    recovery_tail_seconds : how much of the end of the trimmed record to
        average for the recovery-depth cross-check

    Returns
    -------
    (clean_df, report, raw_df) - report includes a "recovery_check" dict
    (or None if site["recovery_depth_m"] wasn't given).
    """
    name = site["name"]
    path = os.path.join(input_dir, site["raw_csv"])
    rho = site["rho"]
    os.makedirs(output_dir, exist_ok=True)

    if raw_df is None:
        raw_df = load_raw(path, encoding=encoding)
    fs_hz = estimate_sampling_rate_hz(raw_df)

    start_idx, end_idx = manual_window(raw_df, site["survey_start"], site["survey_end"])
    if edge_trim_seconds:
        start_idx, end_idx = trim_edges(start_idx, end_idx, fs_hz, edge_trim_seconds)

    fit_result = calibration["fit_result"] if "fit_result" in calibration else calibration
    slope, intercept = fit_result["slope"], fit_result["intercept"]

    df = raw_df.copy()
    df["pressure_pa"] = apply_calibration(df["pressure_psi"], slope, intercept)
    df["pressure_dbar"] = df["pressure_pa"] / 1e4
    df["water_depth_m"] = df["pressure_pa"] / (rho * G)

    clean_df = trim_and_index(df, start_idx, end_idx)

    full_out = clean_df[[
        "datetime", "elapsed_s", "temp_C",
        "pressure_psi", "pressure_pa", "pressure_dbar", "water_depth_m",
    ]].rename(columns={"pressure_psi": "pressure_psi_raw"})

    clean_path = os.path.join(output_dir, "clean.csv")
    full_out.to_csv(clean_path, index=False)

    oceanlyz_path = os.path.join(output_dir, "oceanlyz.csv")
    clean_df["pressure_pa"].to_csv(oceanlyz_path, index=False, header=False)

    recovery_check = None
    if site.get("recovery_depth_m") is not None:
        tail_n = max(1, int(round(recovery_tail_seconds * fs_hz)))
        modeled_depth_m = clean_df["water_depth_m"].iloc[-tail_n:].mean()
        recovery_check = {
            "measured_recovery_depth_m": site["recovery_depth_m"],
            "modeled_depth_at_end_m": modeled_depth_m,
            "diff_m": modeled_depth_m - site["recovery_depth_m"],
        }

    report = {
        "site": name,
        "raw_file": path,
        "n_calibration_points": fit_result.get("n_points"),
        "slope": slope,
        "intercept_pa": intercept,
        "r2": fit_result.get("r2"),
        "sampling_rate_hz": fs_hz,
        "survey_start": clean_df["datetime"].iloc[0],
        "survey_end": clean_df["datetime"].iloc[-1],
        "n_samples": len(clean_df),
        "duration_hours": clean_df["elapsed_s"].iloc[-1] / 3600,
        "height_above_bed_m": site["height_above_bed_m"],
        "rho": rho,
        "site_dir": output_dir,
        "clean_csv": clean_path,
        "oceanlyz_csv": oceanlyz_path,
        "recovery_check": recovery_check,
    }
    return clean_df, report, raw_df


def print_calibration_report(calibration):
    """Human-readable summary of a process_calibration() result."""
    fit = calibration["fit_result"]
    print(f"\n=== CALIBRATION: {calibration['calib_file']} ===")
    print(f"Sampling rate: {calibration['fs_hz']} Hz")
    print(f"Pre-test air baseline:  {calibration['pre_baseline']['mean_psi']:.4f} psi "
          f"({calibration['pre_baseline']['start']} -> {calibration['pre_baseline']['end']})")
    print(f"Post-test air baseline: {calibration['post_baseline']['mean_psi']:.4f} psi "
          f"({calibration['post_baseline']['start']} -> {calibration['post_baseline']['end']})")
    print(f"\n{len(calibration['steps'])} depth-hold(s) used:")
    cols = ["nominal_depth_m", "depth_m", "mean_psi", "std_psi", "duration_s"]
    print(calibration["steps"][cols].to_string(index=False))
    print(f"\nFit: slope={fit['slope']:.5f}, intercept={fit['intercept']:.1f} Pa"
          + (f", R²={fit['r2']:.4f}" if fit["r2"] == fit["r2"] else " (R² needs 3+ points)"))


def print_report(report):
    """Human-readable summary of a process_site() / process_deployment() report."""
    window_start = report.get("survey_start", report.get("submerged_start"))
    window_end = report.get("survey_end", report.get("submerged_end"))

    print(f"\n=== {report['site'].upper()} ===")
    print(f"Calibration: {report['n_calibration_points']} point(s) "
          f"-> slope={report['slope']:.5f}, intercept={report['intercept_pa']:.1f} Pa"
          + (f", R²={report['r2']:.4f}" if report["r2"] == report["r2"] else ""))
    print(f"Sampling rate: {report['sampling_rate_hz']} Hz")
    print(f"Survey window: {window_start} -> {window_end} "
          f"({report['duration_hours']:.2f} h, {report['n_samples']} samples)")
    if report.get("recovery_check") is not None:
        rc = report["recovery_check"]
        print(f"Recovery check: modeled depth at end of record = {rc['modeled_depth_at_end_m']:.3f} m, "
              f"measured at recovery = {rc['measured_recovery_depth_m']:.3f} m "
              f"(diff = {rc['diff_m']:+.3f} m)")
    print(f"Wrote: {report['clean_csv']}")
    print(f"Wrote: {report['oceanlyz_csv']}  (OCEANLYZ InputType='pressure', units: Pa)")
    print("Suggested OCEANLYZ properties:")
    print(f"  ocn.InputType = 'pressure'")
    print(f"  ocn.fs = {report['sampling_rate_hz']}")
    print(f"  ocn.heightfrombed = {report['height_above_bed_m']}")
    print(f"  ocn.Rho = {report['rho']}")
