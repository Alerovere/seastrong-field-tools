# Repo context for Claude / coding assistants

This file exists so that any Claude session opened directly on this repo — not just
one with the "SEASTRONG CODE AND TUTORIALS" Claude Project attached — has the working
context needed to write or edit code, notebooks, and readthedocs pages here without
re-deriving it from scratch. It's a condensed index, not the full record: the source
project docs (richer, with dated reasoning and open questions) live in that Claude
Project and should be treated as the primary reference when they're available.

## What this repo is

**SEASTRONG Field Processing Tools** — field data processing tools for the SEASTRONG
project (Horizon Europe, grant HORIZON-CL6-2025-01-BIODIV-07), maintained by Ca'
Foscari University of Venice (UNIVE) for **Work Package 1** (coastal seascape mapping)
and **Work Package 4** (functional connectivity & ecosystem services). SEASTRONG studies
connectivity between mangrove, seagrass, and coral reef ecosystems across three regions:
Belize, Seychelles, Fiji.

Tools are meant to be self-contained and usable by people with varying coding
experience — most run in Google Colab. Docs are built with Sphinx/MyST and published to
Read the Docs (`docs/`, `.readthedocs.yaml`, published at
seastrong-field-tools.readthedocs.io).

## Repo layout

| Path | What it is | Docs page |
|---|---|---|
| `echosounder_bathymetry/` | Deeper Pro echosounder depth processing + tide correction | `docs/echosounder_bathymetry.md` |
| `photo_geotagging/` | Geotag time-lapse photos from a GPX track | `docs/photo_geotagging.md` |
| `underwater_photogrammetry/` | Two-camera GoPro SfM photogrammetry rig | `docs/underwater_photogrammetry.md` |
| `Mangroves_topography/` | Transect topography reconstruction (`mangrove_transect_topography.ipynb`, `transect_demo.csv`) | **none yet** — see below |
| `Wave_data_processing/` | Pressure-sensor calibration + OCEANLYZ wave processing (`pressure_calibrate_and_prepare.ipynb`, `run_oceanlyz.ipynb`) | **none yet** — see below |

**Known gap:** `Mangroves_topography/` and `Wave_data_processing/` aren't yet listed in
`README.md`'s tools table or `docs/index.rst`'s toctree, and have no readthedocs page.
The source material to write those pages already exists (summarized below / in the
Claude Project). This is a natural next task.

## Task 1.2 / WP4 field methodology (wave attenuation & water movement)

Design settled 2026-09-01. Per corridor (of 6 min per region), per ecosystem
(mangrove/seagrass/coral): one 20 m transect, 2 pressure sensors per transect
(seaward + landward, for bulk Hs-in vs Hs-out), 2-3 deployments of ~2 days each,
plus structural photogrammetry at each transect to parameterize habitat drag.
10 sensors total → up to 5 transects in parallel; ~90 deployment-days/region fits an
~20-day stay at 5 parallel transects (thin buffer — partners can continue deployments
after departure).

Roughness calibration: invert 1D XBeach per transect against observed wave-height decay
+ structural metrics, hierarchical/partial-pooling across corridors of the same habitat
type. Fallback (if full deployment count isn't achievable everywhere): full protocol on
~2 calibration corridors per region spanning the structural/exposure gradient; remaining
corridors get photogrammetry/habitat classification only, roughness predicted from the
fitted relationship. D4.5 modelling stays entirely in XBeach (1D calibration + 2D
production runs); scenario axes are tide state (flood/ebb/slack) × wave state
(seasonal-average, 10-yr-return-period storm).

Full decision log with sensor logistics, fallback triggers, and DoA framing:
`task1.2_water_movement_wave_attenuation_methodology.md` in the Claude Project.

## Pressure sensor calibration & QA (feeds `Wave_data_processing/`)

Found via a bucket test (2026-09-09, PT2X vs a freshly lab-calibrated unit): the
dominant error source is **barometric zero drift**, not sensor gain — PT2X's onboard
zero is a stale single-point in-air reading that drifts with weather over weeks. Fix is
structural, not per-deployment recalibration:

1. **Pre-trip:** traceable multi-point calibration for PT2X (via Seametrics/Observator,
   not the onboard zero), plus an in-house pool verification for all sensors before the
   trip (3-4 known depths, logged temperature).
2. **Per field leg:** deploy one continuous barometric reference (candidates evaluated:
   SensorPush HTP.xw ~$90, DIY BME280 logger, Solinst Barologger, Seametrics PT2X-BV) so
   every submerged sensor's record is compensated against actual concurrent atmospheric
   pressure in post-processing, not a stored offset. ~1 sample/hour is enough (tighten
   around forecast storms). One reference per corridor/region is sufficient (coherent
   over tens of km).
3. **Per field leg:** bracket with a short side-by-side bucket dip test (before/after) —
   QA, not full recalibration.
4. **Per deployment:** log site water temperature/salinity so the pipeline picks the
   correct density instead of a hardcoded constant; discard the first ~10 min of each
   record for thermal settling.
5. **Pipeline:** barometric compensation and density selection should be automatic in
   the processing scripts, keyed by sensor serial number / campaign date / site
   metadata — not a manual per-deployment step.

For OCEANLYZ processing specifically: burst-mean depth (`h`) must be the
barometrically-compensated, site-density-corrected value per burst — an offset error
here biases the pressure-attenuation correction directly, unlike raw pressure variance
(which mostly cancels a DC offset). Set `fmaxpcorr` conservatively. Log sensor height
above bed per deployment. A gain/slope mismatch between sensor brands would bias the
Hs-out/Hs-in ratio and isn't something the single-point bucket test can rule out — needs
a real side-by-side burst in moving water.

Full workflow with a stable-vs-drifting property table and purchase comparison:
`pressure_sensor_calibration_workflow.md` in the Claude Project.

## GoPro underwater photogrammetry rig (feeds `underwater_photogrammetry/`)

2x GoPro HERO10 Black, GoPro Labs firmware v1.62.70, Timelapse Photo mode, 1-2 m depth,
red/magenta dive filter.

**Known issue:** QR-code control does not work for Timelapse-mode settings on this
camera/firmware (red checkmark, no beep, setting doesn't change) — tested extensively
2026-08-19, reproducible across tools and after a full reformat/firmware reinstall.
Video-mode QR settings do work on the same camera. Likely a genuine QR-tooling /
HERO10 Labs-firmware incompatibility (HERO10 is an older, no-longer-updated model on
the Labs side). **Workaround: configure Timelapse settings manually via the on-camera
touchscreen menu**, identically on both cameras: Timelapse sub-mode, 5K, Linear lens,
0.5s interval, Protune on, Flat color, ISO locked at 200/200, shortest available shutter
(not Auto — freezes caustic flicker), fixed white balance starting at 5500K (adjust
toward 6000-6500K if too blue/green, 5000K if too red/magenta with the filter on),
**JPEG output, not RAW** (RAW can restrict the 0.5s interval and isn't needed since
exposure/WB are already locked). Frame-exact two-camera sync isn't required for SfM as
long as there's image overlap.

Full checklist and camera-sync options: `gopro_underwater_photogrammetry_settings.md`
in the Claude Project.

## Mangrove transect topography (feeds `Mangroves_topography/`)

`mangrove_transect_topography.ipynb` reconstructs X/Y/Z along a mangrove transect from a
CSV of tape-distance + inclination readings, with an RTK GNSS fix mandatory only on the
first row and optional as a "tie" on any other row. Method: raw dead-reckoning traverse
from slope distance + inclination, corrected by linearly interpolating the misclosure
between consecutive GNSS ties (translation-only, no rotation/rescale); with only the
mandatory start tie it collapses to plain dead-reckoning. Points after the last tie
carry that tie's correction forward as a constant offset.

Output: `<input>_topography.csv` + `_profile_plan.png` + `_topography.geojson` (GeoJSON
deliberately in **UTM meters**, not WGS84 lon/lat, with the CRS named in the
FeatureCollection — a documented deviation from strict RFC 7946, chosen because UTM
suits on-the-ground/desktop-GIS use better; `lon`/`lat` columns are still in the CSV if a
web-safe file is needed). `transect_demo.csv` is the schema-matching demo/test file.

Possible follow-ups not yet built: batch mode for multiple transects, curved
(non-straight) transect support, optional full 2D affine adjustment.

Full notebook design notes and CSV schema: `mangrove_transect_topography_notebook.md`
in the Claude Project (note: that doc references a Drive-integrated variant,
`mangrove_transect_topography_drive.ipynb`, for Colab use — check whether the copy in
this repo's `Mangroves_topography/` is that version or the earlier two-point-only one).

## Project background

Proposal text (objectives, work packages, full DoA) is in the Claude Project as
`PROPOSAL_101286483-SeaStrong-HORIZON-CL6-2025-01-PART_B_Section_1.pdf` and `..._Section_2.pdf`.
