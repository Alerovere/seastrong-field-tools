"""
staircase.py

For a "rope-drop" calibration: one continuous file where the sensor is held
at several known depths in turn (descending, then ascending), rather than
one file per depth. This module finds each depth-hold ("plateau") in that
file automatically, so you don't have to eyeball timestamps by hand.

Detection is two passes:
  1. Classify each sample as "stable" (rolling std below std_threshold) or
     not, then merge stable runs across brief unstable gaps (sensor noise
     mid-hold), and drop anything shorter than min_duration_s.
  2. Consolidate adjacent plateaus that are really the same hold split by a
     short pause (e.g. "reached the deepest point and held it a bit
     longer") - merged only if BOTH the value is close (within
     fragment_merge_tol) AND the gap between them is short
     (fragment_merge_gap_s). The value check is what keeps this from
     bridging genuinely different depths, which differ by far more than
     fragment_merge_tol.

Defaults were tuned against a real 4-depth (0.5/1/1.5/2 m) rope-drop test
and should be a reasonable starting point, but every deployment's hold
durations differ - inspect the output table/plot before trusting it.
"""

import pandas as pd


def detect_plateaus(
    df,
    fs,
    min_duration_s=6,
    std_window_s=1.5,
    std_threshold=0.03,
    merge_gap_s=1.0,
    fragment_merge_gap_s=8.0,
    fragment_merge_tol=0.1,
    min_pressure_psi=0.5,
    pressure_col="pressure_psi",
):
    """
    Find candidate depth-holds in a raw pressure record.

    Parameters
    ----------
    df : DataFrame with "datetime" and a pressure column (from load_raw)
    fs : sampling rate in Hz (from estimate_sampling_rate_hz)
    min_duration_s : shortest hold worth keeping
    std_window_s : rolling-std window used to judge "is this sample stable"
    std_threshold : rolling std (psi) below which a sample counts as stable
    merge_gap_s : bridges brief unstable blips (noise) inside a real hold
    fragment_merge_gap_s : max gap between two stable runs to still treat
        them as one hold split by a short pause
    fragment_merge_tol : max mean-pressure difference (psi) for two runs to
        be considered "the same hold" during that merge
    min_pressure_psi : plateaus with |mean pressure| below this are dropped
        as being in air (pre-test/post-test baseline), not an actual depth.
        Set to None/0 to keep everything, e.g. when you want the baseline
        plateaus too (barometric_correct() does this internally).
    pressure_col : which column to run detection on - "pressure_psi" (raw)
        by default, or "pressure_psi_barocorr" after barometric_correct().

    Returns
    -------
    DataFrame, one row per detected plateau, columns:
        start, end, start_idx, end_idx, duration_s, mean_psi, std_psi
    Sorted chronologically. Inspect this (and plot_staircase()) before
    assigning known depths with label_plateaus().
    """
    n_std = max(3, int(round(std_window_s * fs)))
    roll_std = df[pressure_col].rolling(n_std, center=True, min_periods=1).std()
    stable = (roll_std < std_threshold).values

    n_gap = max(1, int(round(merge_gap_s * fs)))
    s = pd.Series(stable)
    unstable_run = (~s).astype(int).groupby((s != s.shift()).cumsum()).transform("sum")
    stable_merged = stable | ((~s) & (unstable_run <= n_gap)).values

    run_id = (pd.Series(stable_merged) != pd.Series(stable_merged).shift()).cumsum()
    tmp = df.copy()
    tmp["stable"] = stable_merged
    tmp["run_id"] = run_id.values

    runs = tmp.groupby("run_id").agg(
        start=("datetime", "first"),
        end=("datetime", "last"),
        start_idx=("datetime", lambda x: x.index[0]),
        end_idx=("datetime", lambda x: x.index[-1]),
        stable=("stable", "first"),
    )
    runs = runs[runs["stable"]].copy()
    runs["duration_s"] = (runs["end"] - runs["start"]).dt.total_seconds()
    runs = runs[runs["duration_s"] >= min_duration_s].copy()

    means, stds = [], []
    for _, r in runs.iterrows():
        seg = df[pressure_col].iloc[int(r["start_idx"]):int(r["end_idx"]) + 1]
        means.append(seg.mean())
        stds.append(seg.std())
    runs["mean_psi"] = means
    runs["std_psi"] = stds
    runs = runs.reset_index(drop=True)

    # Consolidate a hold that was briefly interrupted (same value, short gap).
    merged_rows = []
    for _, r in runs.iterrows():
        r = r.to_dict()
        if merged_rows:
            prev = merged_rows[-1]
            gap_s = (r["start"] - prev["end"]).total_seconds()
            if gap_s <= fragment_merge_gap_s and abs(r["mean_psi"] - prev["mean_psi"]) <= fragment_merge_tol:
                prev["end"] = r["end"]
                prev["end_idx"] = r["end_idx"]
                prev["duration_s"] = (prev["end"] - prev["start"]).total_seconds()
                seg = df[pressure_col].iloc[int(prev["start_idx"]):int(prev["end_idx"]) + 1]
                prev["mean_psi"] = seg.mean()
                prev["std_psi"] = seg.std()
                continue
        merged_rows.append(r)

    out = pd.DataFrame(merged_rows)
    if min_pressure_psi:
        out = out[out["mean_psi"].abs() >= min_pressure_psi]
    return out.reset_index(drop=True)


def barometric_correct(df, fs, start_time, end_time, **detect_kwargs):
    """
    Trim a calibration file to [start_time, end_time] and remove barometric
    drift (or sensor zero-drift) using the flat "in air" stretches right
    before and after the dip test.

    Assumes start_time/end_time bracket the whole test *including* a bit of
    flat, in-air record on both ends (a few seconds is enough) - not just
    the depth steps themselves. The first and last detected plateaus in
    that window are taken as the pre- and post-test air readings; a
    straight line between their mean pressure and mean time is subtracted
    from the whole window, so both ends read ~0 afterwards and any drift
    in between is corrected proportionally by elapsed time.

    Parameters
    ----------
    df : DataFrame from load_raw() (full file - this function does the slicing)
    fs : sampling rate in Hz
    start_time, end_time : anything pandas.Timestamp can parse, e.g.
        "2026-08-18 13:20:30"
    **detect_kwargs : passed through to detect_plateaus() for finding the
        pre/post baseline plateaus (e.g. min_duration_s if your flat
        stretches are shorter than the 6 s default)

    Returns
    -------
    (window_df, pre_baseline, post_baseline)
      window_df   - df sliced to [start_time, end_time], with an added
                    "pressure_psi_barocorr" column
      pre_baseline, post_baseline - dicts with the detected plateau's
                    start/end/mean_psi, for reporting/sanity-checking
    """
    window = df[(df["datetime"] >= pd.Timestamp(start_time)) & (df["datetime"] <= pd.Timestamp(end_time))].copy()
    window = window.reset_index(drop=True)
    if len(window) < 3:
        raise ValueError("start_time/end_time select fewer than 3 samples - check the timestamps.")

    kwargs = dict(min_pressure_psi=None)
    kwargs.update(detect_kwargs)
    all_plateaus = detect_plateaus(window, fs, **kwargs)
    if len(all_plateaus) < 3:
        raise ValueError(
            f"Only found {len(all_plateaus)} stable stretch(es) in [{start_time}, {end_time}] - "
            "need at least a pre-test baseline, the depth steps, and a post-test baseline. "
            "Widen the window or check detect_plateaus() parameters."
        )

    pre = all_plateaus.iloc[0]
    post = all_plateaus.iloc[-1]

    t0 = window["datetime"].iloc[0]
    pre_t = (pre["start"] + (pre["end"] - pre["start"]) / 2 - t0).total_seconds()
    post_t = (post["start"] + (post["end"] - post["start"]) / 2 - t0).total_seconds()
    elapsed = (window["datetime"] - t0).dt.total_seconds()

    if post_t <= pre_t:
        raise ValueError("Pre- and post-test baseline plateaus overlap in time - check start_time/end_time.")

    frac = (elapsed - pre_t) / (post_t - pre_t)
    baro_line = pre["mean_psi"] + frac * (post["mean_psi"] - pre["mean_psi"])
    window["pressure_psi_barocorr"] = window["pressure_psi"] - baro_line

    pre_baseline = {"start": pre["start"], "end": pre["end"], "mean_psi": pre["mean_psi"]}
    post_baseline = {"start": post["start"], "end": post["end"], "mean_psi": post["mean_psi"]}
    return window, pre_baseline, post_baseline


def detect_calibration_steps(df, fs, start_time, end_time, expected_steps=None, **detect_kwargs):
    """
    End-to-end: trim to [start_time, end_time], barometric-correct using the
    flat stretches at each end, then detect the depth-hold plateaus in
    between (the pre-/post-test baselines themselves are excluded from the
    returned steps - they're ~0 after correction and not a depth reading).

    This is the function to call when you have a start/end time for the
    test: it replaces a plain detect_plateaus(df, fs) call on the whole
    file, which otherwise also has to deal with everything else in the
    record (long baselines before/after, unrelated spikes, etc.).

    Returns
    -------
    (steps, window_df, pre_baseline, post_baseline)
      steps      - DataFrame of detected depth-hold plateaus (barometric-
                   corrected mean_psi), chronological, ready for
                   label_plateaus()
      window_df  - the trimmed, barometric-corrected DataFrame (for plotting)
      pre_baseline, post_baseline - the air readings used for the correction

    Pass expected_steps (e.g. 7 or 8) to print a mismatch warning if the
    count found doesn't match what you know the test should contain.
    """
    window, pre_baseline, post_baseline = barometric_correct(df, fs, start_time, end_time, **detect_kwargs)

    kwargs = dict(detect_kwargs)
    kwargs.setdefault("min_pressure_psi", 0.3)
    # Shallow holds near the surface tend to be noisier (hand/wave motion),
    # so the step-detection pass uses a looser stability threshold and a
    # wider smoothing window than the module defaults - tuned against a
    # real rope-drop test where the final, shallowest hold was otherwise
    # missed entirely at the tighter defaults.
    kwargs.setdefault("std_threshold", 0.06)
    kwargs.setdefault("std_window_s", 2.0)
    kwargs.setdefault("min_duration_s", 5)
    steps = detect_plateaus(window, fs, pressure_col="pressure_psi_barocorr", **kwargs)
    # Drop the pre/post baseline themselves if detect_plateaus still picked
    # them up as separate low-but-above-threshold plateaus at the very ends.
    if len(steps) and steps.iloc[0]["end"] <= pre_baseline["end"]:
        steps = steps.iloc[1:].reset_index(drop=True)
    if len(steps) and steps.iloc[-1]["start"] >= post_baseline["start"]:
        steps = steps.iloc[:-1].reset_index(drop=True)

    n = len(steps)
    if expected_steps is not None and n != expected_steps:
        print(f"Note: found {n} step(s) in this window, not the expected {expected_steps} - "
              "check plot_staircase(window_df, steps) before labeling. A very "
              "fast final step (e.g. the last shallow stop on the way up) can "
              "be too brief to register as its own plateau.")
    return steps, window, pre_baseline, post_baseline


def label_plateaus(plateaus, depth_sequence, offset_m=0.0):
    """
    Attach a known depth to each detected plateau, in order.

    depth_sequence : list of NOMINAL depth_m values, one per row of
        `plateaus` (in chronological order) - e.g.
        [0.5, 1.0, 1.5, 2.0, 1.5, 1.0, 0.5] for a 4-depth rope-drop, down
        and back up. Length must match len(plateaus) exactly - if it
        doesn't, you're missing/have an extra detected plateau and should
        check the plot before proceeding.
    offset_m : added to every value in depth_sequence before use - e.g. the
        distance from the rope's depth markings down to the sensor's actual
        pressure port, if the rope depth was measured to a different point
        on the sensor than where it senses. 0.0 (default) if the rope
        depths already refer to the sensor's own depth.
    """
    if len(depth_sequence) != len(plateaus):
        raise ValueError(
            f"depth_sequence has {len(depth_sequence)} entries but "
            f"{len(plateaus)} plateaus were detected - check plot_staircase() "
            f"and adjust detect_plateaus() parameters or depth_sequence."
        )
    labeled = plateaus.copy()
    labeled["nominal_depth_m"] = depth_sequence
    labeled["depth_m"] = [d + offset_m for d in depth_sequence]
    return labeled


def plot_staircase(df, plateaus, out_path=None, pressure_col="pressure_psi"):
    """Raw (or barometric-corrected) trace with detected plateaus shaded."""
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=(11, 4.5))
    ax.plot(df["datetime"], df[pressure_col], color="tab:gray", lw=0.6)
    for i, r in plateaus.iterrows():
        ax.axvspan(r["start"], r["end"], color="tab:orange", alpha=0.35)
        ax.annotate(
            f"{i}", xy=(r["start"] + (r["end"] - r["start"]) / 2, r["mean_psi"]),
            ha="center", va="bottom", fontsize=9, color="tab:red",
        )
    ax.set_ylabel("psi")
    ax.set_title("Detected plateaus (orange), numbered in chronological order")
    fig.autofmt_xdate()
    fig.tight_layout()
    if out_path:
        fig.savefig(out_path, dpi=130)
    return fig
