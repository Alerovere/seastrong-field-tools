# Underwater Photogrammetry

## Overview

This page describes the field setup and procedure for Structure-from-Motion (SfM) photogrammetric surveys of shallow coral reefs using a pair of action cameras (e.g. GoPro) mounted on a simple rig. The layout, header, file names, safety and effort common to all habitats are on the [Field transects](field_transects.md) page. The survey covers the stretch of seabed between the two pressure sensors of a wave-attenuation transect, so that the 3D structure of the habitat can be linked to the wave-height decay measured between them. The photos are used to build scaled 3D models and orthomosaics of the reef.

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

**Do NOT survey when strong caustics are visible on the bottom** (bright, moving networks of light, as in the photo below). They change from one photo to the next and prevent a reliable 3D reconstruction. Wait for clouds or a lower sun.

```{figure} _static/reef_caustics_example.jpg
:width: 80%
:alt: Bottom photo with strong caustic light patterns over sand and coral

Strong caustics on the bottom: **conditions in which the survey must not be done**.
```

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
- **Scale-bar targets (at least 6):** rigid bars (e.g. ~50 cm long) with an **Agisoft coded target** printed at each end (see the photo below). The distance between the **centres** of the two targets is measured precisely once, at the lab, and listed with the target codes in a **bar list** that travels with the kit. Each target must have a unique code, and all bars must use the same coded-target type. Print the targets and laminate or seal them.
- **Depth gauge or dive computer** (preferably with 0.1 m resolution or better; always use the same instrument for all targets of a transect)
- **Phone or handheld GPS** to take **one approximate point** at the surface above the 0 m end of the transect (a general location, not precise positioning), and a **compass** for the bearing of the tape
- **Underwater slate** and pencil, prepared with the field sheet (see the checklist below)
- **Watch**, for the time of the depth readings
- **Colour reference tab** (optional), placed at the start of the transect for colour calibration of the photos
- Weights or pegs to keep the tape and targets in place in current or surge

```{figure} _static/photogrammetry_scalebar_targets.jpg
:width: 90%
:alt: Two scale-bar targets placed on either side of the transect tape over a coral reef

Two scale-bar targets placed on either side of the transect tape. Each bar carries an Agisoft coded target at each end, with the target centres at a known distance.
```

### Clocks

Set the **two cameras to the same time** before the survey (this is done easily from the GoPro app). Exact synchronisation is done afterwards.

### Camera settings

Both cameras are configured identically, using the on-camera menu:

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

RAW is not needed here because exposure, white balance and shutter are all locked. JPEG keeps file sizes manageable.

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

```{figure} _static/reef_photogrammetry_layout_v2.svg
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

## Field form and post-site report

The checklist, the slate data sheets and the post-site report are in one form: {download}`Reef photogrammetry field form, v1.0 (PDF) <_static/forms/reef_photogrammetry_field_form_v1.0.pdf>`.

- **In the field:** print pages 1–3 on waterproof paper, or copy them onto the slate.
- **After the survey:** type the slate data and the post-site report (page 4) into the same PDF, the same day.
- **Fill it in with Adobe Acrobat Reader** (free, [download it here](https://get.adobe.com/reader/)). In Acrobat Reader the **Transect ID** is filled in automatically from study area, date and corridor, and appears on every page, and the form fields are saved correctly. Other viewers (Mac Preview, browsers, phone apps) may not fill in the Transect ID or may not save the fields.
- Save the filled form with the data, named `<transectID>_field_form.pdf`, and put the data download link in section B of the report.

---

## Why we do this in SEASTRONG

In **WP1, Task 1.3** (baseline characterisation of biodiversity, condition and spatial connectivity within corridors), underwater photogrammetry is used to quantify the **structural complexity** of coral reef habitats along the cross-shelf corridors mapped in Task 1.2. Structural complexity, measured from 3D SfM models as rugosity and surface area ratio, is a key indicator of ecosystem condition and biodiversity on coral reefs.

In **WP1, Task 1.2 / WP4**, the photogrammetric models of the stretch between the two pressure sensors are used to describe the habitat structure that causes the measured wave attenuation, and to parameterise habitat roughness in the XBeach models.

In **WP2, Task 2.2** and **WP5, Task 5.1** (setting up and monitoring experimental restoration sites), repeated photogrammetric surveys at the same plots are used to track changes in structural complexity over time as a proxy for restoration progress, comparing sexually and asexually reproduced restoration plots.
