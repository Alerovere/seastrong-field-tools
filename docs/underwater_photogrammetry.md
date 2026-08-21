# Underwater Photogrammetry

## Overview

This page describes the field setup and procedures for collecting Structure-from-Motion (SfM) photogrammetric surveys on coral reefs and seagrass beds using a two-camera GoPro rig. The resulting photo datasets are first colour-corrected in **DaVinci Resolve** and then processed in **Agisoft Metashape** to produce 3D models, orthomosaics, and structural complexity metrics of the surveyed habitat.

**Source code:** [github.com/Alerovere/seastrong-field-tools](https://github.com/Alerovere/seastrong-field-tools/tree/main/underwater_photogrammetry)

---

## Field gear and procedures

Two operators work together to deploy a fixed transect on the seafloor and swim it carrying a stereo camera rig. The setup is designed to maximise photo overlap and geometric consistency for SfM reconstruction, while keeping the equipment affordable and field-deployable without specialist dive support.

### Equipment list

- **2× GoPro HERO10 Black** with GoPro Labs firmware, in waterproof housings
- **Stereo camera rig** — a rigid bar holding the two cameras at a fixed baseline distance (see table below), both facing downward
- **Transect tape** — deployed on the seafloor by the two operators before the survey begins
- **Photogrammetric targets** — placed on the seafloor along the transect to act as scale bars; targets must be of known size and spacing for metric reconstruction in Metashape
- **Colour reference tab** — placed on the seafloor at the start of the transect for post-processing colour calibration in DaVinci Resolve

### Camera settings

Both cameras are configured identically using the following manual settings applied via the on-camera touchscreen menu. **Do not use QR codes to configure timelapse settings on the HERO10 Black** — this is a known incompatibility between the HERO10 firmware (GoPro Labs v1.62.70) and the QR timelapse command encoding; QR scans return a red checkmark with no effect. Configure each camera manually:

| Setting | Value |
|---------|-------|
| Mode | Photo → Timelapse |
| Resolution | 5K |
| Lens/FOV | Linear |
| Interval | 0.5 s |
| Duration/Limit | Off |
| Protune | On |
| Color | Flat |
| ISO Min | 200 |
| ISO Max | 200 |
| Sharpness | Medium |
| Shutter | Shortest available (not Auto) |
| White Balance | Fixed Kelvin — start at 5500K, adjust per test dive |
| Output format | Standard JPEG (not RAW) |

**Notes on shutter and white balance:** a fixed, short shutter speed freezes caustic light patterns common in shallow water. If test shots are too dark, step up one notch before adjusting ISO. For white balance, test-shoot at your survey depth: if images appear too blue/green, increase toward 6000–6500K; if too red/magenta, decrease toward 5000K. Set the same value on both cameras.

RAW is not needed here because exposure, white balance, and shutter are all locked. JPEG keeps file sizes manageable and imports directly into Metashape.

### Baseline rig configuration

The distance between the two cameras (baseline) depends on the expected swimming depth above the reef. Use the table below to select the appropriate baseline for your survey conditions. Values are calculated for 80% lateral overlap between the two cameras' fields of view, using the GoPro HERO10 Black in Linear FOV mode.

| Distance from reef (D) | Single camera footprint (W) | Recommended baseline (B) | Overlap |
|------------------------|----------------------------|--------------------------|---------|
| 0.5 m | 58 cm | 12–13 cm | 46 cm |
| 0.75 m | 87 cm | 17–18 cm | 69 cm |
| 1.0 m | 1.15 m | 23–25 cm | 92 cm |
| 1.25 m | 1.44 m | 29–30 cm | 1.15 m |
| 1.5 m | 1.73 m | 35–40 cm | 1.38 m |
| 1.75 m | 2.02 m | 40–45 cm | 1.62 m |
| 2.0 m | 2.31 m | 46–53 cm | 1.85 m |

Adjust the baseline by loosening the rig mounts before the dive and locking them at the correct spacing.

### Field procedure

1. **Deploy the transect tape** on the seafloor between the two operators. The tape defines the survey corridor and ensures the rig is swum in a straight line.
2. **Place photogrammetric targets** along the transect at known intervals. These act as scale bars for metric reconstruction in Metashape — record their positions and spacing in your field notes.
3. **Place the colour reference tab** at the start of the transect, in a position where it will appear in the first few photos of the survey.
4. **Configure both cameras** per the settings table above. Verify that both are in timelapse mode at 0.5 s interval.
5. **Start both cameras simultaneously** — a hand-wave or light flash at the start of the transect provides a visual sync marker across both image sequences.
6. **Swim the transect slowly and steadily**, keeping the rig at a consistent height above the reef matched to your chosen baseline. Both operators swim in parallel, one on each side of the tape.
7. At the end of the transect, stop both cameras and note the time.
8. Download photos from both cameras and organise them into separate folders by camera before processing.

---

## Processing

There is no automated processing tool for this dataset. Photos are processed using two external software packages:

1. **DaVinci Resolve** — colour correction is applied first, using the colour reference tab visible in the opening frames as a calibration reference. This step corrects for the colour cast introduced by water depth and ensures consistent colour across both cameras before SfM reconstruction.

2. **Agisoft Metashape** — colour-corrected images from both cameras are imported as a single chunk. Photogrammetric targets are marked and used to define scale bars with known metric dimensions. Standard Metashape alignment, dense cloud, and mesh workflows are then used to produce the 3D model and orthomosaic.

---

## Why we do this in SEASTRONG

In **WP1 — Task 1.3** (Baseline characterisation of biodiversity, condition, and spatial connectivity within corridors), underwater photogrammetry is used to quantify the **structural complexity** of coral reef habitats along the cross-shelf corridors mapped in Task 1.2. Structural complexity — measured from 3D SfM models as rugosity and surface area ratio — is a key indicator of ecosystem condition and biodiversity on coral reefs.

In **WP2 — Task 2.2** and **WP5 — Task 5.1** (Setting up and monitoring experimental restoration sites), repeated photogrammetric surveys at the same plots are used to track changes in structural complexity over time as a proxy for restoration progress, comparing sexually and asexually reproduced restoration plots.
