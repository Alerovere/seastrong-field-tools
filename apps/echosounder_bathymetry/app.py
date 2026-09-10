"""
Echosounder Bathymetry -- SEASTRONG field tool.

Processes Deeper Pro echosounder depth data, applies a tide correction, and
exports calibration/validation CSV + GeoJSON for satellite-derived
bathymetry work. Tide can come from either an uploaded tide-gauge CSV, or be
predicted from the FES2022 global ocean tide model given a local copy of the
model data and the survey coordinates.

This is a thin UI layer -- all the actual processing logic lives in core/
(bathymetry_tide_processing.py, fes_tide.py) and has no Streamlit dependency,
so it stays testable and reusable outside this app.
"""
from __future__ import annotations

import io
import re
import sys
import tempfile
import zipfile
from datetime import datetime
from pathlib import Path

import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import pandas as pd
import streamlit as st

APP_DIR = Path(__file__).parent
sys.path.insert(0, str(APP_DIR))
sys.path.insert(0, str(APP_DIR.parent))

from core.bathymetry_tide_processing import (  # noqa: E402
    load_tide_data,
    process_bathymetry_with_tide_df,
)
from core.fes_tide import describe_expected_layout, predict_fes2022_tide  # noqa: E402

from _shared.branding import (  # noqa: E402
    apply_page_config,
    render_footer,
    render_header,
)

apply_page_config("Echosounder Bathymetry", icon="\U0001F41F")
render_header(
    "Echosounder Bathymetry",
    "Deeper Pro depth processing with tide correction -- tide-gauge file or FES2022 model",
)


def _read_preview(uploaded_file) -> pd.DataFrame:
    uploaded_file.seek(0)
    preview = pd.read_csv(uploaded_file, sep=None, engine="python", nrows=5)
    uploaded_file.seek(0)
    return preview


def _save_upload_to_tempdir(uploaded_file, tmpdir: Path) -> Path:
    dest = tmpdir / uploaded_file.name
    uploaded_file.seek(0)
    dest.write_bytes(uploaded_file.read())
    return dest


def _column_index(columns: list[str], preferred: list[str], fallback: int = 0) -> int:
    for name in preferred:
        if name in columns:
            return columns.index(name)
    return fallback


def _zip_output_dir(output_dir: Path) -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        for path in sorted(output_dir.rglob("*")):
            if path.is_file():
                zf.write(path, arcname=path.relative_to(output_dir))
    return buffer.getvalue()


def _slugify(name: str) -> str:
    """Turn a site name into a safe folder name; fall back to a timestamp."""
    slug = re.sub(r"[^A-Za-z0-9_-]+", "_", name.strip()).strip("_")
    return slug or datetime.now().strftime("%Y%m%dT%H%M%S")


# -----------------------------------------------------------------------
# 1. Scan data
# -----------------------------------------------------------------------
st.header("1. Scan data")
scan_upload = st.file_uploader("Deeper Pro scan CSV", type=["csv"], key="scan_upload")

scan_depth_col = scan_time_col = scan_lat_col = scan_lon_col = None
scan_preview = None

if scan_upload is not None:
    scan_preview = _read_preview(scan_upload)
    st.dataframe(scan_preview, use_container_width=True)
    cols = list(scan_preview.columns)

    c1, c2, c3, c4 = st.columns(4)
    scan_depth_col = c1.selectbox(
        "Depth column", cols, index=_column_index(cols, ["depth"])
    )
    scan_time_col = c2.selectbox(
        "Time column (UNIX)", cols, index=_column_index(cols, ["time"])
    )
    scan_lat_col = c3.selectbox(
        "Latitude column", cols, index=_column_index(cols, ["latitude", "lat"])
    )
    scan_lon_col = c4.selectbox(
        "Longitude column",
        cols,
        index=_column_index(cols, ["longtitude", "longitude", "lon"]),
    )
else:
    st.info("Upload a scan CSV to continue.")

# -----------------------------------------------------------------------
# 2. Tide data
# -----------------------------------------------------------------------
st.header("2. Tide data")
tide_source = st.radio(
    "Tide source",
    ["Tide-gauge file", "FES2022 model"],
    horizontal=True,
)

tide_upload = None
tide_water_level_col = tide_date_col = tide_time_col = tide_datetime_col = None
fes_directory = fes_lat = fes_lon = None

if tide_source == "Tide-gauge file":
    tide_upload = st.file_uploader("Tide-gauge CSV", type=["csv"], key="tide_upload")

    if tide_upload is not None:
        tide_preview = _read_preview(tide_upload)
        st.dataframe(tide_preview, use_container_width=True)
        tcols = list(tide_preview.columns)

        tide_water_level_col = st.selectbox(
            "Water level column",
            tcols,
            index=_column_index(tcols, ["HYDROMETRIC LEVEL", "water_level"]),
        )

        datetime_mode = st.radio(
            "Date/time format",
            ["Separate date + time columns", "Single combined datetime column"],
            horizontal=True,
        )

        if datetime_mode == "Separate date + time columns":
            d1, d2 = st.columns(2)
            tide_date_col = d1.selectbox(
                "Date column", tcols, index=_column_index(tcols, ["DATE", "date"])
            )
            tide_time_col = d2.selectbox(
                "Time column", tcols, index=_column_index(tcols, ["TIME", "time"])
            )
        else:
            tide_datetime_col = st.selectbox(
                "Datetime column",
                tcols,
                index=_column_index(tcols, ["DATETIME", "datetime"]),
            )
else:
    st.caption(
        "The FES2022 model data (tens of GB) must already be available on the "
        "machine/container running this tool -- e.g. mounted as a Docker volume. "
        "Point this at the folder that contains `fes2022b/` (don't reorganize the "
        "files inside it)."
    )
    fes_directory = st.text_input(
        "FES2022 model folder", placeholder="/data/fes2022"
    )
    f1, f2 = st.columns(2)
    fes_lat = f1.number_input(
        "Latitude (decimal degrees)", min_value=-90.0, max_value=90.0, value=0.0, format="%.6f"
    )
    fes_lon = f2.number_input(
        "Longitude (decimal degrees)", min_value=-180.0, max_value=180.0, value=0.0, format="%.6f"
    )

    with st.expander("What files does this look for?"):
        try:
            expected = describe_expected_layout()
            n = len(expected)
            st.write(
                f"Looks for all {n} FES2022 ocean-tide constituent files, named "
                f"`<constituent>_fes2022.nc` (plain or gzip-compressed `.nc.gz` -- "
                f"either is fine), under the folder above. Several common layouts "
                f"are accepted automatically, checked in this order:"
            )
            st.markdown(
                "- `<folder>/fes2022b/ocean_tide_<date>/<constituent>_fes2022.nc` "
                "(pyTMD's own default, e.g. the first path below)\n"
                "- `<folder>/fes2022b/<constituent>_fes2022.nc`\n"
                "- `<folder>/ocean_tide_<date>/<constituent>_fes2022.nc`\n"
                "- `<folder>/<constituent>_fes2022.nc` (flat, no subfolders)"
            )
            st.code("\n".join(expected[:3]) + f"\n... ({n} total)")
            st.caption(
                "If none of these match, the error message after running will "
                "list exactly what was tried and how many files it found in "
                "each place."
            )
        except Exception as exc:  # noqa: BLE001
            st.warning(f"Could not read the expected file list: {exc}")

# -----------------------------------------------------------------------
# 3. Output location
# -----------------------------------------------------------------------
st.header("3. Output location")
oc1, oc2 = st.columns([1, 2])
site_name = oc1.text_input(
    "Site name",
    value="",
    placeholder="corridor3_mangrove",
    help="Names the output subfolder. Leave blank to use a timestamp instead.",
)
output_folder = oc2.text_input(
    "Save results to a folder on this machine (optional)",
    value="",
    placeholder="/data/outputs",
    help=(
        "A folder inside this container, mounted from your Mac with "
        "`-v host_folder:/data/outputs` when you started the container -- "
        "see the tool's README. A subfolder named after the site above is "
        "created inside it. Leave blank to just use the download button "
        "after processing instead."
    ),
)

# -----------------------------------------------------------------------
# 4. Processing options
# -----------------------------------------------------------------------
with st.expander("4. Processing options", expanded=False):
    o1, o2 = st.columns(2)
    match_method = o1.selectbox("Tide matching method", ["interpolate", "nearest"])
    match_tolerance = o2.text_input("Matching tolerance", value="15min")

    o3, o4 = st.columns(2)
    train_fraction = o3.slider("Training fraction", 0.05, 0.95, 0.70, step=0.05)
    random_seed = o4.number_input("Random seed", value=42, step=1)

    o5, o6 = st.columns(2)
    shuffle_split = o5.checkbox("Shuffle before split", value=True)
    scan_unix_unit = o6.selectbox("Scan UNIX time unit", ["auto", "s", "ms", "us", "ns"])

    o7, o8 = st.columns(2)
    export_geojson = o7.checkbox("Export WGS84 GeoJSON", value=True)
    export_utm_geojson = o8.checkbox("Export UTM GeoJSON", value=True)

    timezone = st.text_input(
        "Timezone override (optional)",
        value="",
        help="e.g. Europe/Rome. Leave blank to keep timestamps as-is (UTC/naive).",
    )

# -----------------------------------------------------------------------
# Run
# -----------------------------------------------------------------------
st.header("5. Run")
run_disabled = scan_upload is None or (
    tide_source == "Tide-gauge file" and tide_upload is None
) or (tide_source == "FES2022 model" and not fes_directory)

if st.button("Run processing", type="primary", disabled=run_disabled):
    try:
        with st.spinner("Processing..."):
            tmpdir = Path(tempfile.mkdtemp(prefix="echosounder_"))
            scan_path = _save_upload_to_tempdir(scan_upload, tmpdir)

            site_slug = _slugify(site_name)
            persisted_path: Path | None = None
            output_dir_ok = True

            if output_folder.strip():
                output_dir = Path(output_folder.strip()).expanduser() / site_slug
                try:
                    output_dir.mkdir(parents=True, exist_ok=True)
                    persisted_path = output_dir
                except OSError as exc:
                    output_dir_ok = False
                    st.error(
                        f"Can't write to '{output_dir}': {exc}. Check that "
                        f"'{output_folder}' was mounted as a volume when you "
                        "started the container (see the tool's README), and "
                        "that the folder is writable."
                    )
            else:
                output_dir = tmpdir / site_slug

            tz = timezone.strip() or None

            if output_dir_ok:
                if tide_source == "Tide-gauge file":
                    tide_path = _save_upload_to_tempdir(tide_upload, tmpdir)
                    tide_df = load_tide_data(
                        tide_csv=tide_path,
                        water_level_column=tide_water_level_col,
                        date_column=tide_date_col,
                        time_column=tide_time_col,
                        datetime_column=tide_datetime_col,
                        timezone=tz,
                    )
                else:
                    # Need the scan timestamps first, to know what times to predict.
                    from core.bathymetry_tide_processing import load_scan_data

                    scan_for_times = load_scan_data(
                        scan_csv=scan_path,
                        depth_column=scan_depth_col,
                        time_column=scan_time_col,
                        latitude_column=scan_lat_col,
                        longitude_column=scan_lon_col,
                        unix_unit=scan_unix_unit,
                        timezone=tz,
                    )
                    tide_df = predict_fes2022_tide(
                        model_directory=fes_directory,
                        longitude=fes_lon,
                        latitude=fes_lat,
                        timestamps=scan_for_times["timestamp"],
                    )

                results = process_bathymetry_with_tide_df(
                    scan_csv=scan_path,
                    tide_df=tide_df,
                    output_dir=output_dir,
                    scan_depth_column=scan_depth_col,
                    scan_time_column=scan_time_col,
                    scan_latitude_column=scan_lat_col,
                    scan_longitude_column=scan_lon_col,
                    scan_unix_unit=scan_unix_unit,
                    timezone=tz,
                    match_method=match_method,
                    match_tolerance=match_tolerance or None,
                    train_fraction=train_fraction,
                    random_seed=int(random_seed),
                    shuffle_split=shuffle_split,
                    export_geojson=export_geojson,
                    export_utm_geojson=export_utm_geojson,
                )

                st.session_state["results"] = results
                st.session_state["output_zip"] = _zip_output_dir(output_dir)
                st.session_state["persisted_path"] = (
                    str(persisted_path) if persisted_path else None
                )

        if output_dir_ok:
            st.success("Processing complete.")
    except Exception as exc:  # noqa: BLE001
        st.error(f"Processing failed: {exc}")

# -----------------------------------------------------------------------
# Results
# -----------------------------------------------------------------------
if "results" in st.session_state:
    results = st.session_state["results"]
    summary = results["summary"]
    merged = results["merged"]
    tide_df = results["tide"]

    st.header("6. Results")

    persisted_path = st.session_state.get("persisted_path")
    if persisted_path:
        st.info(
            f"Results saved to `{persisted_path}` inside the container -- "
            "on your Mac at whatever host folder you mounted there with `-v`."
        )

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Scan points", f"{summary['total_scan_points_after_cleaning']:,}")
    m2.metric(
        "Matched to tide",
        f"{summary['matched_tide_points']:,}",
        f"{summary['matched_tide_percentage']:.1f}%",
    )
    m3.metric("Training points", f"{summary['training_points']:,}")
    m4.metric("Validation points", f"{summary['validation_points']:,}")

    tab_plots, tab_map, tab_download = st.tabs(["Plots", "Map", "Download"])

    with tab_plots:
        fig, axes = plt.subplots(3, 1, figsize=(10, 9))

        ax = axes[0]
        ax.scatter(merged["timestamp"], merged["depth"], s=2, color="#2196F3", alpha=0.6)
        ax.set_ylabel("Depth (m)")
        ax.set_title("Echosounder depth over time")
        ax.invert_yaxis()
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%H:%M"))
        ax.grid(True, alpha=0.3)

        ax = axes[1]
        ax.plot(tide_df["timestamp"], tide_df["water_level"], color="#4CAF50", linewidth=1.2)
        ax.set_ylabel("Water level (m)")
        ax.set_title("Tide water level used for correction")
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%d/%m %H:%M"))
        ax.grid(True, alpha=0.3)

        ax = axes[2]
        valid = merged["tide_correction"].dropna()
        if len(valid) > 0:
            ax.hist(valid, bins=40, color="#FF9800", edgecolor="white", linewidth=0.5)
        ax.set_xlabel("Tide-corrected depth (m)")
        ax.set_ylabel("Scan points")
        ax.set_title("Distribution of tide-corrected depth")
        ax.grid(True, alpha=0.3)

        fig.tight_layout()
        st.pyplot(fig)

    with tab_map:
        map_data = merged.dropna(subset=["latitude", "longitude"]).copy()
        if map_data.empty:
            st.info("No georeferenced scan points to display.")
        else:
            try:
                import folium
                from streamlit_folium import st_folium

                center = [map_data["latitude"].mean(), map_data["longitude"].mean()]
                fmap = folium.Map(location=center, zoom_start=16, tiles="OpenStreetMap")
                for _, row in map_data.iterrows():
                    folium.CircleMarker(
                        location=[row["latitude"], row["longitude"]],
                        radius=3,
                        color="#2196F3",
                        fill=True,
                        fill_opacity=0.7,
                        popup=(
                            f"Depth: {row.get('depth', 'n/a'):.2f} m<br>"
                            f"Water level: {row.get('water_level', 'n/a')}<br>"
                            f"Time: {row.get('timestamp', 'n/a')}"
                        ),
                    ).add_to(fmap)
                st_folium(fmap, width=None, height=500)
            except ImportError:
                st.map(map_data.rename(columns={"latitude": "lat", "longitude": "lon"}))

    with tab_download:
        st.download_button(
            "Download all outputs (.zip)",
            data=st.session_state["output_zip"],
            file_name="echosounder_bathymetry_outputs.zip",
            mime="application/zip",
        )
        st.caption(
            "Contains merged/training/validation CSV, plus WGS84 and UTM GeoJSON "
            "if enabled above."
        )

render_footer(
    "Field procedure and tide-source background: see the readthedocs "
    '<a href="https://seastrong-field-tools.readthedocs.io/en/latest/echosounder_bathymetry.html" target="_blank">Echosounder Bathymetry</a> page.'
)
