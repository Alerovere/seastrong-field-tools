# Underwater Photogrammetry

## Overview

This page describes the field setup and procedure for Structure-from-Motion (SfM) photogrammetric surveys of shallow coral reefs using a pair of action cameras (e.g. GoPro) mounted on a simple rig. The layout, header, file names, safety and effort common to all habitats are on the [Field transects](field_transects.md) page. The survey covers the stretch of seabed between the two pressure sensors of a wave-attenuation transect, so that the 3D structure of the habitat can be linked to the wave-height decay measured between them. Photos are colour-corrected in **DaVinci Resolve** and processed in **Agisoft Metashape** to produce scaled 3D models, orthomosaics and structural complexity metrics.

**Source code:** [github.com/Alerovere/seastrong-field-tools](https://github.com/Alerovere/seastrong-field-tools/tree/main/underwater_photogrammetry)

---

## Transect layout

The transect follows the [common layout](field_transects.md#transect-layout-all-habitats): a **30 m** tape laid cross-shore from **sensor 1 (0 m, seaward)** to **sensor 2 (30 m, landward)**. On reefs:

- choose a broadly **planar** area with a maximum depth of **3 m**;
- the surveyed corridor extends **about 3 m on each side** of the tape.

### Survey conditions

Survey only when:

- underwater visibility is clearly greater than the swimming height (at least ~4 m), so that both cameras see the bottom sharply;
- waves and surge are small enough to keep the rig steady at a constant height;
- the tide is not changing fast; around slack water is best, because the target depths are compared with each other;
- the sun is not producing strong caustic patterns on the bottom. Overcast conditions, or early morning and late afternoon, give the most uniform light.

If conditions are marginal, do a short test pass and check the photos on the camera before surveying the whole transect.

### Snorkel or scuba

The survey is normally done **snorkelling**, holding the rig at arm's length below the surface with the cameras pointing straight down. The rig should be **about 1.5–2 m above the bottom**:

- in water up to ~2.5 m deep, snorkel at the surface;
- where the rig cannot be kept within ~2 m of the bottom from the surface, or where surface conditions make the rig unstable, use **scuba** and swim at ~1.5 m above the bottom.

Keep the same height for the whole survey, and choose the camera spacing for that height (see the table below). Poles are not used.

---

## Equipment

- **2× action cameras** (e.g. GoPro HERO10 Black with GoPro Labs firmware) in waterproof housings, with red/magenta dive filters. Label them clearly as **A** and **B**, on both the camera and the housing.
- **Camera rig:** any rigid bar, for example a plastic (PVC) tube, holding the two cameras pointing downward at a **fixed, known distance** (camera spacing; see the table below). Measure the distance between the two lens centres and record it.
- **30 m transect tape**
- **Scale-bar targets (at least 6):** rigid bars (e.g. ~50 cm long) with an **Agisoft coded target** printed at each end (see the photo below). The distance between the **centres** of the two targets is measured precisely once, at the lab, and listed with the target codes in a **bar list** that travels with the kit. Each target must have a unique code, and all bars must use the same coded-target type. Print targets from Metashape (*Tools → Markers → Print Markers…*) and laminate or seal them.
- **Depth gauge or dive computer** (preferably with 0.1 m resolution or better; always use the same instrument for all targets of a transect)
- **Phone or handheld GPS** for the location of the transect, and a **compass** for its bearing
- **Underwater slate** and pencil, prepared with the field sheet (see the checklist below)
- **Watch** set to UTC, like the cameras and sensors (see [Before the trip](field_transects.md#before-the-trip))
- **Colour reference tab** (optional), placed at the start of the transect for colour calibration in DaVinci Resolve
- Weights or pegs to keep the tape and targets in place in current or surge

```{figure} _static/photogrammetry_scalebar_targets.jpg
:width: 90%
:alt: Two scale-bar targets placed on either side of the transect tape over a coral reef

Two scale-bar targets placed on either side of the transect tape. Each bar carries an Agisoft coded target at each end, with the target centres at a known distance.
```

### Clocks

All clocks are set to the same time (UTC) before the trip, as described on the [Field transects](field_transects.md#before-the-trip) page.

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

### Camera spacing

The distance between the two cameras depends on how high above the bottom the rig is swum. Values are calculated for 80% overlap between the two cameras' fields of view, using the GoPro HERO10 Black in Linear FOV mode. For the snorkel survey described here, the usual range is **1.5–2 m**.

| Height above bottom (D) | Single camera footprint (W) | Recommended spacing (B) | Overlap |
|------------------------|----------------------------|--------------------------|---------|
| 0.5 m | 58 cm | 12–13 cm | 46 cm |
| 0.75 m | 87 cm | 17–18 cm | 69 cm |
| 1.0 m | 1.15 m | 23–25 cm | 92 cm |
| 1.25 m | 1.44 m | 29–30 cm | 1.15 m |
| **1.5 m** | **1.73 m** | **35–40 cm** | **1.38 m** |
| **1.75 m** | **2.02 m** | **40–45 cm** | **1.62 m** |
| **2.0 m** | **2.31 m** | **46–53 cm** | **1.85 m** |
| 2.5 m | 2.89 m | 58–65 cm | 2.31 m |

Fix the cameras at the chosen spacing before entering the water and write the measured spacing on the slate.

---

## Roles and timing

A team of **two people** is enough; three makes the layout faster:

- **Operator 1:** lays the tape, places the scale bars, takes target depths and the depth profile, and fills in the slate.
- **Operator 2:** prepares and starts the cameras, swims the three passes, and checks the photos afterwards.

Allow roughly **1–1.25 hours in the water per transect**: about 20 minutes for layout and target depths, 10–15 minutes for the depth profile, 10–15 minutes for the three passes, and 10 minutes for checks and recovery. The surface support person (boat or shore) keeps track of time and of the swimmers.

---

## Field procedure

```{figure} _static/photogrammetry_field_layout.svg
:width: 100%
:alt: Schematic of the transect layout and the three camera passes

Data collection at a reef transect. (A) The 30 m tape is laid cross-shore between the two pressure sensors, with scale bars on both sides within ~2 m of the tape. (B) Forward pass with camera A over the tape. (C) Backward pass with camera A over the tape, so camera B is shifted to the other side. (D) Zigzag pass out to ~3 m on each side. (E) Cross-section of a snorkel survey: targets at different elevations, with the depth measured at the centre of each target.
```

### 1. Lay out the transect

1. Lay the **30 m tape** along the bottom, **cross-shore**, between the two pressure sensors. Keep it as straight and taut as possible and secure both ends.
2. The **0 m end is at sensor 1, seaward**. Note on the slate the **position of each pressure sensor along the tape** (e.g. "sensor 1 at −1 m, sensor 2 at 31 m").
3. **Location and bearing:** at the surface above the 0 m end, take the GPS position with a phone or handheld GPS (approximate is enough), and take the **compass bearing** of the tape from the 0 m end towards the 30 m end.
4. Fill in the [slate header](field_transects.md#on-every-transect), common to all habitats.

### 2. Place the scale-bar targets

1. Place **at least 6 scale bars** along the whole length of the tape, on **both sides**, within **~2 m of the tape** (so they are seen by the straight passes as well as the zigzag).
2. Vary their **orientation**: some parallel to the tape, some across it, some diagonal.
3. Place them at **different elevations**, for example some on top of coral colonies and others in sand patches or depressions. This constrains the vertical geometry of the model, not only its horizontal scale.
4. Make sure the targets are flat, stable, fully visible and not shaded by overhanging structures. **Do not break, scrape or press on live coral** to place them; use sand, rubble or dead substrate where possible.
5. On the slate, record the **target codes** of each bar, its position along the tape (m) and its side (left or right, looking landward).

### 3. Measure depths

1. At the **centre of each target** (each ground control point), hold the depth gauge sensor at the target centre and read the **depth**. Take **three readings** a few seconds apart and write them all down (they are averaged in post-processing to smooth out the effect of waves).
2. Write each set of readings on the slate next to its **target code**, together with the **time**. The time allows the depths to be corrected for the tide using the pressure-sensor record.
3. **Depth profile:** read the depth and time **every 2 m** along the tape, at each sensor, and on for **5–10 m beyond the 30 m mark** (see [Bed profile](field_transects.md#bed-profile-and-vertical-datum)). Inside the 30 m the 3D model gives the detailed bed; these readings reference it and extend it to the model boundary.

### 4. Start the cameras

1. Check that both cameras are set as in the table above, that the spacing is correct, and that the housings are not fogged.
2. Start the two cameras **as simultaneously as possible**. Exact synchronisation is not required: the two image sequences are aligned in post-processing.
3. If a colour reference tab is used, make sure it appears in the first photos.

### 5. Swim the three passes

Swim the rig at a **constant height of about 1.5–2 m above the bottom**, keeping the cameras pointing straight down and the rig level. Swim slowly and evenly at **about 0.3 m/s**, which means each straight pass of 30 m takes about **1.5–2 minutes**. At this speed and a 0.5 s interval, consecutive photos overlap by about 90%.

1. **Forward pass:** swim from the 0 m end to the 30 m end with **camera A directly above the tape**. Camera B covers a strip shifted to one side.
2. **Backward pass:** swim back to the 0 m end, again with **camera A directly above the tape**. Because the direction is reversed, camera B now covers the **other side**. Together, the two straight passes cover about 1.5 m on each side of the tape.
3. **Zigzag pass:** swim the whole transect again in a **zigzag across the tape**, reaching **about 3 m on each side**, with about **5 crossings each way** over the 30 m. This widens the model and ties the two straight passes together.

At the end, stop both cameras and note the end time on the slate.

### 6. Check before leaving the site

1. On each camera, check that photos were recorded for the whole survey (photo count roughly matches the survey time: ~2 photos per second).
2. Look at a few photos from the start, middle and end of each camera: the bottom must be sharp, not too dark, and the housing not fogged.
3. If a camera stopped, fogged up, or the photos are blurred, **repeat the passes** while the tape and targets are still in place.

### 7. Recover and record

1. Recover the targets and the tape. Check that no target is left behind (count them against the bar list).
2. Photograph the slate before it is wiped.
3. In the evening, copy the slate into the digital field sheet and download the photos, named as on the [Field transects](field_transects.md#file-names) page.

---

## Safety and reef care

See [Safety and care of the habitat](field_transects.md#safety-and-care-of-the-habitat). On reefs in particular: avoid touching, kneeling on or finning against coral, and keep the rig and tape away from fragile colonies.

---

## Field checklist

Print this section, or copy it onto the slate, so that nothing is forgotten. Every item marked **data** must be written down: without it the model cannot be scaled, referenced or linked to the wave measurements.

### Before the trip

See the [common checklist](field_transects.md#before-the-trip) (clocks in UTC, cameras labelled, bar list).

### Before going in the water

| ☐ | Item |
|---|------|
| ☐ | Both cameras charged, memory cards empty, settings checked against the table above (same settings on both) |
| ☐ | Rig assembled for the planned swimming height; **data:** measured camera spacing (cm) |
| ☐ | At least 6 scale bars, 30 m tape, depth gauge, GPS (phone), compass, slate and pencil, weights or pegs, colour reference tab (if used) |
| ☐ | Conditions OK: visibility, waves and surge, tide, light |
| ☐ | **Data:** [slate header](field_transects.md#on-every-transect); snorkel or scuba |
| ☐ | **Data:** IDs of the two pressure sensors at the ends of the transect |

### Layout (in the water)

| ☐ | Item |
|---|------|
| ☐ | Tape laid cross-shore between the two sensors, straight and secured at both ends |
| ☐ | **Data:** position of each sensor along the tape (0 m at sensor 1, seaward) |
| ☐ | **Data:** approximate GPS position of the 0 m end and compass bearing from 0 m to 30 m |
| ☐ | At least 6 scale bars on **both sides**, within ~2 m of the tape, varied orientation, **different elevations** |
| ☐ | **Data:** for each bar, its target codes, position along the tape (m) and side (L/R, looking landward) |
| ☐ | **Data:** three depth readings at the **centre of every target**, and the time |
| ☐ | **Data:** depth + time every 2 m, at each sensor and 5–10 m beyond the 30 m mark |

### Photo survey

| ☐ | Item |
|---|------|
| ☐ | Both cameras started as close to simultaneously as possible; **data:** start time |
| ☐ | Colour reference tab in the first photos (if used) |
| ☐ | Pass 1: forward, camera A over the tape, ~1.5–2 m above the bottom, ~0.3 m/s |
| ☐ | Pass 2: backward, camera A over the tape |
| ☐ | Pass 3: zigzag, ~3 m each side, ~5 crossings each way |
| ☐ | Both cameras stopped; **data:** end time |
| ☐ | Photos checked on both cameras (complete, sharp, not fogged); passes repeated if needed |

### After the dive

| ☐ | Item |
|---|------|
| ☐ | All targets (checked against the bar list) and the tape recovered |
| ☐ | Slate photographed before it is wiped |
| ☐ | Photos downloaded into one folder per camera, e.g. `FJ_C1_RF_20270602_camA` and `..._camB` |
| ☐ | Slate copied into the digital field sheet; slate photo and field sheet saved next to the photo folders |

### Slate template

**Header:** the [common header](field_transects.md#on-every-transect), plus snorkel/scuba · camera spacing · camera start/end time

**Depth profile:** distance along tape (m) · depth (m) · time, every 2 m to 5–10 m beyond the 30 m mark

**Target depths:**

| Target code | Position along tape (m) | Side (L/R) | Depth 1 (m) | Depth 2 (m) | Depth 3 (m) | Time |
|-------------|-------------------------|------------|-------------|-------------|-------------|------|
| T01 | | | | | | |
| T02 | | | | | | |
| … | | | | | | |

---

## Processing

There is no automated processing tool for this dataset. Photos are processed using two external software packages:

1. **DaVinci Resolve:** colour correction is applied first, using the colour reference tab (if used) as a calibration reference. This corrects for the colour cast introduced by the water and ensures consistent colour across both cameras before SfM reconstruction.

2. **Agisoft Metashape:** colour-corrected images from both cameras are imported into a single chunk. Then:
   - detect the coded targets automatically (*Tools → Markers → Detect Markers*, with the same target type used for printing);
   - create a **scale bar** between the two targets of each bar and enter its centre-to-centre distance from the bar list;
   - use the **depths** measured at each target as the vertical reference, after averaging the three readings and correcting them for the tide with the pressure-sensor water-level record at the time of each reading;
   - run the standard alignment, dense cloud, mesh and orthomosaic workflow to produce the 3D model and structural complexity metrics;
   - orient the model using the compass bearing of the tape if a map-aligned product is needed.

---

## Why we do this in SEASTRONG

In **WP1, Task 1.3** (baseline characterisation of biodiversity, condition and spatial connectivity within corridors), underwater photogrammetry is used to quantify the **structural complexity** of coral reef habitats along the cross-shelf corridors mapped in Task 1.2. Structural complexity, measured from 3D SfM models as rugosity and surface area ratio, is a key indicator of ecosystem condition and biodiversity on coral reefs.

In **WP1, Task 1.2 / WP4**, the photogrammetric models of the stretch between the two pressure sensors are used to describe the habitat structure that causes the measured wave attenuation, and to parameterise habitat roughness in the XBeach models.

In **WP2, Task 2.2** and **WP5, Task 5.1** (setting up and monitoring experimental restoration sites), repeated photogrammetric surveys at the same plots are used to track changes in structural complexity over time as a proxy for restoration progress, comparing sexually and asexually reproduced restoration plots.
