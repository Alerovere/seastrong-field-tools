# Underwater Photogrammetry

## Overview

This page describes the field setup and procedure for Structure-from-Motion (SfM) photogrammetric surveys of shallow coral reefs and seagrass beds using a pair of action cameras (e.g. GoPro) mounted on a simple rig. The survey covers the stretch of seabed between the two pressure sensors of a wave-attenuation transect, so that the 3D structure of the habitat can be linked to the wave-height decay measured between them. Photos are colour-corrected in **DaVinci Resolve** and processed in **Agisoft Metashape** to produce scaled 3D models, orthomosaics and structural complexity metrics.

**Source code:** [github.com/Alerovere/seastrong-field-tools](https://github.com/Alerovere/seastrong-field-tools/tree/main/underwater_photogrammetry)

---

## Site layout

- **Location:** the survey runs between the **two pressure sensors** placed at the two ends of the reef section (seaward and landward). See the [wave attenuation](wave_attenuation.md) page for the sensor deployment.
- **Orientation:** the transect is laid **cross-shore**, from one sensor to the other.
- **Depth and slope:** choose a broadly **planar** area at a maximum depth of **2–3 m**. This keeps the rig close enough to the bottom for sharp, well-lit photos while snorkelling.
- **Length:** a **30 m** tape is laid along the bottom between the sensors.

---

## Equipment

- **2× action cameras** (e.g. GoPro HERO10 Black with GoPro Labs firmware) in waterproof housings, with red/magenta dive filters
- **Camera rig:** any rigid bar, for example a plastic (PVC) tube, holding the two cameras pointing downward at a **fixed, known distance** (baseline; see the table below). Measure the distance between the two lens centres and record it.
- **30 m transect tape**
- **Scale-bar targets:** rigid bars with an **Agisoft coded target** printed at each end (see the photo below). The distance between the **centres** of the two targets must be measured precisely and recorded for each bar. Each target must have a unique code. Print targets from Metashape (*Tools → Markers → Print Markers…*) and laminate or seal them.
- **Depth gauge** (dive computer or depth gauge)
- **Underwater slate** and pencil
- **Colour reference tab** (optional), placed at the start of the transect for colour calibration in DaVinci Resolve
- Weights or pegs to keep the tape and targets in place in current or surge

```{figure} _static/photogrammetry_scalebar_targets.jpg
:width: 90%
:alt: Two scale-bar targets placed on either side of the transect tape over a coral reef

Two scale-bar targets placed on either side of the transect tape. Each bar carries an Agisoft coded target at each end, with the target centres at a known distance.
```

### Camera settings

Both cameras are configured identically using the following manual settings applied via the on-camera touchscreen menu. **Do not use QR codes to configure timelapse settings on the HERO10 Black.** This is a known incompatibility between the HERO10 firmware (GoPro Labs v1.62.70) and the QR timelapse command encoding: QR scans return a red checkmark with no effect. Configure each camera manually:

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
| White Balance | Fixed Kelvin, starting at 5500K and adjusted per test dive |
| Output format | Standard JPEG (not RAW) |

**Notes on shutter and white balance:** a fixed, short shutter speed freezes caustic light patterns common in shallow water. If test shots are too dark, step up one notch before adjusting ISO. For white balance, test-shoot at your survey depth: if images appear too blue/green, increase toward 6000–6500K; if too red/magenta, decrease toward 5000K. Set the same value on both cameras.

RAW is not needed here because exposure, white balance and shutter are all locked. JPEG keeps file sizes manageable and imports directly into Metashape.

### Baseline rig configuration

The distance between the two cameras (baseline) depends on how high above the bottom the rig is swum. Use the table below to select the baseline for your survey conditions. Values are calculated for 80% lateral overlap between the two cameras' fields of view, using the GoPro HERO10 Black in Linear FOV mode.

| Distance from reef (D) | Single camera footprint (W) | Recommended baseline (B) | Overlap |
|------------------------|----------------------------|--------------------------|---------|
| 0.5 m | 58 cm | 12–13 cm | 46 cm |
| 0.75 m | 87 cm | 17–18 cm | 69 cm |
| 1.0 m | 1.15 m | 23–25 cm | 92 cm |
| 1.25 m | 1.44 m | 29–30 cm | 1.15 m |
| 1.5 m | 1.73 m | 35–40 cm | 1.38 m |
| 1.75 m | 2.02 m | 40–45 cm | 1.62 m |
| 2.0 m | 2.31 m | 46–53 cm | 1.85 m |

Fix the cameras at the chosen spacing before entering the water and write the measured baseline on the slate.

---

## Field procedure

```{figure} _static/photogrammetry_field_layout.svg
:width: 100%
:alt: Schematic of the transect layout and the three camera passes

Data collection at a reef transect. (A) The 30 m tape is laid cross-shore between the two pressure sensors, with scale bars on both sides. (B) Forward pass with camera A over the tape. (C) Backward pass with camera A over the tape, so camera B covers the other side. (D) Zigzag pass across the tape. (E) Cross-section: targets placed at different elevations, with the depth measured at the centre of each target.
```

### 1. Lay out the transect

1. Lay the **30 m tape** along the bottom, **cross-shore**, between the two pressure sensors. Keep it as straight and taut as possible and secure both ends.
2. Note on the slate which end of the tape (0 m) is seaward and which is landward.

### 2. Place the scale-bar targets

1. Place the scale bars on **both sides of the tape**, spread along its whole length.
2. Where possible, place them at **different elevations**, for example some on top of coral colonies and others in sand patches or depressions. This constrains the vertical geometry of the model, not only its horizontal scale.
3. Make sure the targets are flat, stable, fully visible and not shaded by overhanging structures.
4. On the slate, record the **target codes** of each bar and its approximate position along the tape.

### 3. Measure target depths

1. At the **centre of each target** (each ground control point), take the **depth** with the depth gauge.
2. Write each depth on the slate next to its **target code**, together with the **time** of the reading. The time allows the depths to be corrected for the tide during processing.

### 4. Start the cameras

1. Check that both cameras are set as in the table above and that the baseline is correct.
2. Start the two cameras **as simultaneously as possible**. Exact synchronisation is not required: the two image sequences are aligned in post-processing.
3. If a colour reference tab is used, make sure it appears in the first photos.

### 5. Swim the three passes

The operator swims the rig at a steady height above the bottom (matching the chosen baseline) and at a slow, constant speed, keeping the cameras pointing straight down.

1. **Forward pass:** swim from one end of the tape to the other, with **one camera (camera A) directly above the tape**. Camera B covers one side of the corridor.
2. **Backward pass:** swim back to the start, again with **camera A directly above the tape**. Because the direction is reversed, camera B now covers the **other side** of the corridor.
3. **Zigzag pass:** swim the whole transect again in a **zigzag across the tape**, crossing it repeatedly so that the corridor is covered from different angles. This ties the two straight passes together and improves the 3D reconstruction.

At the end, stop both cameras and note the end time on the slate.

### 6. Recover and record

1. Recover the targets and the tape.
2. Check that the slate contains: site and transect ID, date, pressure sensor IDs, tape orientation (seaward/landward end), camera baseline, start and end times, and the code, position, depth and time for each target.
3. Download the photos from each camera into a **separate folder per camera**. Photograph the slate and store the photo with the images.

---

## Field checklist

Print this section, or copy it onto the slate, so that nothing is forgotten. Every item marked **data** must be written down: without it the model cannot be scaled, referenced or linked to the wave measurements.

### Before going in the water

| ☐ | Item |
|---|------|
| ☐ | Both cameras charged, memory cards empty, settings checked against the table above (same settings on both) |
| ☐ | Rig assembled, cameras fixed; **data:** measured camera spacing (cm) |
| ☐ | Scale bars ready; **data:** target codes and centre-to-centre distance of each bar (from the bar list) |
| ☐ | 30 m tape, depth gauge, slate and pencil, weights or pegs, colour reference tab (if used) |
| ☐ | **Data:** site name, transect ID, date, names of operators |
| ☐ | **Data:** IDs of the two pressure sensors at the ends of the transect |

### Layout (in the water)

| ☐ | Item |
|---|------|
| ☐ | Tape laid cross-shore between the two sensors, straight and secured at both ends |
| ☐ | **Data:** which end of the tape (0 m) is seaward |
| ☐ | Scale bars placed on **both sides** of the tape, along the whole length, at **different elevations** |
| ☐ | **Data:** for each bar, its target codes, position along the tape (m) and side (left or right, looking landward) |
| ☐ | **Data:** depth at the **centre of every target**, and the time of each reading |

### Photo survey

| ☐ | Item |
|---|------|
| ☐ | Both cameras started as close to simultaneously as possible; **data:** start time |
| ☐ | Colour reference tab in the first photos (if used) |
| ☐ | Pass 1: forward, camera A over the tape |
| ☐ | Pass 2: backward, camera A over the tape |
| ☐ | Pass 3: zigzag across the tape along the whole length |
| ☐ | Both cameras stopped; **data:** end time |

### After the dive

| ☐ | Item |
|---|------|
| ☐ | All targets and the tape recovered |
| ☐ | Slate photographed (before it is wiped) |
| ☐ | Photos downloaded into one folder per camera, named with site, transect ID, date and camera (A or B) |
| ☐ | Slate photo and notes saved in the same folder as the images |

### Slate template for target depths

| Target code | Position along tape (m) | Side (L/R) | Depth (m) | Time |
|-------------|-------------------------|------------|-----------|------|
| T01 | | | | |
| T02 | | | | |
| … | | | | |

---

## Processing

There is no automated processing tool for this dataset. Photos are processed using two external software packages:

1. **DaVinci Resolve:** colour correction is applied first, using the colour reference tab (if used) as a calibration reference. This corrects for the colour cast introduced by the water and ensures consistent colour across both cameras before SfM reconstruction.

2. **Agisoft Metashape:** colour-corrected images from both cameras are imported into a single chunk. Then:
   - detect the coded targets automatically (*Tools → Markers → Detect Markers*);
   - create a **scale bar** between the two targets of each bar and enter its measured centre-to-centre distance;
   - use the **depths** measured at each target (tide-corrected) as the vertical reference;
   - run the standard alignment, dense cloud, mesh and orthomosaic workflow to produce the 3D model and structural complexity metrics.

---

## Why we do this in SEASTRONG

In **WP1, Task 1.3** (baseline characterisation of biodiversity, condition and spatial connectivity within corridors), underwater photogrammetry is used to quantify the **structural complexity** of coral reef habitats along the cross-shelf corridors mapped in Task 1.2. Structural complexity, measured from 3D SfM models as rugosity and surface area ratio, is a key indicator of ecosystem condition and biodiversity on coral reefs.

In **WP1, Task 1.2 / WP4**, the photogrammetric models of the stretch between the two pressure sensors are used to describe the habitat structure that causes the measured wave attenuation, and to parameterise habitat roughness in the XBeach models.

In **WP2, Task 2.2** and **WP5, Task 5.1** (setting up and monitoring experimental restoration sites), repeated photogrammetric surveys at the same plots are used to track changes in structural complexity over time as a proxy for restoration progress, comparing sexually and asexually reproduced restoration plots.
