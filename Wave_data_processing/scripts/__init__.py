"""
scripts - pressure sensor calibration & cleaning pipeline.

This package is organised as:

  parsing.py     - read raw logger CSV exports into a DataFrame
  submersion.py  - auto-detect the submerged (in-water) part of a record
  calibration.py - fit & apply a 1/2/3(+)-point pressure calibration
  pipeline.py    - process_site(): runs the full pipeline for one sensor

The most commonly used functions are re-exported here for convenience, so
notebooks can just do:

    from scripts import process_site, print_report, plot_qc
    from scripts import fit_calibration, plot_calibration_fit
"""

from .parsing import load_raw, find_header_row, estimate_sampling_rate_hz
from .submersion import detect_submerged_window, trim_edges, manual_window
from .calibration import (
    G,
    PSI_TO_PA,
    resolve_calibration_points,
    fit_calibration,
    apply_calibration,
    mean_pressure_from_file,
    plot_calibration_fit,
)
from .pipeline import (
    process_site, process_calibration, process_deployment,
    print_report, print_calibration_report, plot_qc, trim_and_index,
)
from .staircase import (
    detect_plateaus, label_plateaus, plot_staircase,
    barometric_correct, detect_calibration_steps,
)

__all__ = [
    "load_raw", "find_header_row", "estimate_sampling_rate_hz",
    "detect_submerged_window", "trim_edges", "manual_window",
    "G", "PSI_TO_PA",
    "resolve_calibration_points", "fit_calibration", "apply_calibration",
    "mean_pressure_from_file", "plot_calibration_fit",
    "process_site", "process_calibration", "process_deployment",
    "print_report", "print_calibration_report", "plot_qc", "trim_and_index",
    "detect_plateaus", "label_plateaus", "plot_staircase",
    "barometric_correct", "detect_calibration_steps",
]
