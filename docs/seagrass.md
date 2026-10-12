# Seagrass Structure and Bathymetry

## Overview

This page describes how to measure the **structure** of seagrass meadows and the **depth profile** along the wave-attenuation transects. The structure is used to parameterise seagrass drag in the XBeach models; the depth profile gives the bed along which wave attenuation is measured.

The method is **non-destructive** (nothing is collected) and designed to be quick in the water: shoots are counted afterwards from photos, and blade measurements are taken in place.

**Source code:** [github.com/Alerovere/seastrong-field-tools](https://github.com/Alerovere/seastrong-field-tools)

---

## Transect layout

- The transect is **cross-shore**, between the two pressure sensors of the wave-attenuation deployment: **sensor 1 at the seaward end** and **sensor 2 at the landward end**. See the [wave attenuation](wave_attenuation.md) page for the sensor deployment.
- A **30 m tape** is laid on the bottom from the 0 m mark (sensor 1) to the 30 m mark (sensor 2).
- Record on the field sheet: site, transect ID, date, operators, sensor IDs and their position along the tape, approximate GPS position of the 0 m end, and the compass bearing from 0 m to 30 m.
- Note the tape positions where the meadow visibly changes (e.g. bare sand, patchy, continuous; change of dominant species).
- Work by snorkelling, preferably around **slack water**, when the leaves stand more upright and the depth changes slowly. Do the survey in the same field campaign as the sensor deployments.

```{figure} _static/seagrass_transect.svg
:width: 100%
:alt: Schematic of the seagrass transect: depth and photo stations every 2 m along the tape, three quadrats, the two photos and canopy height at each quadrat, and the measurements taken in place on each shoot

Seagrass data collection. (A) Depth and a vertical photo every 2 m along the tape, and three 25 cm × 25 cm quadrats at the front, centre and back. (B) At each quadrat: canopy height, a canopy photo, and a photo of the shoot bases with the leaves pushed aside. (C) On 10–15 shoots, measured in place: number of blades, and length and width of the longest blade; thickness of a stack of blades on 3–5 shoots per quadrat.
```

---

## Depth profile and cover (every 2 m)

Swim along the tape and stop **every 2 m**, from 0 m to the 30 m mark and then **5–10 m beyond it** (so that the landward boundary of the model is not at sensor 2). Always include a stop at each sensor. At each stop:

1. Read the **water depth** with a depth gauge or a metered stick held vertically on the bottom, next to the tape.
2. Note the **time** of the reading. The depths are later corrected for the tide using the pressure-sensor record.
3. Take **one vertical photo** of the bottom, straight down, from about 1 m above it, with the tape in the frame. These photos give the seagrass **cover** along the transect (bare, patchy, continuous) and the zone boundaries for the model.

---

## Quadrats

Place three **25 cm × 25 cm quadrats** (a rigid frame of known size): at the **front** (2.5 m), **centre** (15 m) and **back** (27.5 m) of the transect, about 1 m to the side of the tape, in a spot representative of the surrounding meadow. These are the same front, centre and back positions used on the mangrove transects.

At each quadrat, in this order:

1. **Canopy height:** with the metered stick, read the height of the undisturbed canopy at **5 points** around the frame.
2. **Photo 1, canopy:** a vertical photo of the whole frame, straight down, before touching the leaves. It gives cover, species composition and a record of the quadrat.
3. **Photo 2, shoot bases:** push the leaves aside with one hand and take a vertical photo close to the bottom, so that the **shoot bases** inside the frame are visible. The shoots are counted later on this photo to obtain **shoot density**. If one photo cannot show the whole frame, take two (one per half) and note it.
4. **Measure 10–15 shoots** of the **dominant species in place**, without cutting or pulling them: take the shoots nearest to marked points on the frame (so the sample is not biased towards long leaves). Note the other species present.

### On each shoot (in place)

Use a ruler fixed to the slate (mm scale) and a simple plastic caliper, and write the readings directly on the slate.

| Measurement | How |
| --- | --- |
| Number of blades | Count the blades on the shoot |
| Blade length | Length of the **longest blade**, from the base to the tip, held straight along the ruler |
| Blade width | Width of the same blade at mid-length, against the ruler |
| Blade thickness | On **3–5 shoots per quadrat**: hold all the blades of the shoot together at mid-length, measure the thickness of the stack with the plastic caliper (jaws closed gently, without squashing), and divide by the number of blades |

Thickness is measured because published values of blade thickness are not available for all seagrass species; together with length and width, it allows a correction for blade flexibility in the models (see [Notes for modelling](#notes-for-modelling)).

### In the lab

- Count the shoots inside the frame on each Photo 2 → shoots per 25 cm × 25 cm → **shoots per m²** (× 16).
- Estimate **percent cover** from the photos taken every 2 m along the tape.

---

## Notes for modelling

### From the field data to XBeach vegetation input

Seagrass is usually represented as a single vegetation section in XBeach, with:

| XBeach input | From the field data |
| --- | --- |
| Vegetation height (ah) | Canopy height (mean of the 5 readings), or an effective blade length that accounts for flexibility (see below) |
| Stem width (bv) | Mean blade width |
| Density (N, per m²) | Shoots per m² (from Photo 2) × mean number of blades per shoot |

Within each zone along the transect, the density is scaled by the **cover** from the photos every 2 m, so that bare and patchy stretches are not given the density of the quadrats. The front, centre and back quadrats give the values for the corresponding parts of the transect.

### Flexibility

XBeach's vegetation module treats stems as rigid, whereas seagrass blades bend under waves. Flexibility is either absorbed into the calibrated drag coefficient, or accounted for with an **effective blade length** (Luhar and Nepf, 2011), which needs blade length, width, thickness and stiffness. Thickness is measured in the field; stiffness is taken from the literature where available. Where stiffness is not available for a species, flexibility is absorbed into the calibrated drag coefficient. Use the same choice for all transects of the same species, so that calibrated drag coefficients can be compared.

### Depth relative to canopy

Wave attenuation by seagrass depends strongly on the ratio between canopy height and water depth. Depths along the transect must be corrected for the tide (with the time of each reading and the pressure-sensor record) and referred to the same vertical datum as the sensors and the tide used at the model boundary.

### Consistency

Shoot density from photos can differ from density counted by hand. Use the same photo method at all sites, so that any bias is consistent and is absorbed in the same way by the calibrated drag coefficient.

---

## Field checklist

### Transect

| ☐ | Item |
|---|------|
| ☐ | **Data:** site, transect ID, date, operators, time |
| ☐ | **Data:** sensor IDs and position along the tape |
| ☐ | **Data:** approximate GPS position of the 0 m end and compass bearing from 0 m to 30 m |
| ☐ | **Data:** tape positions where the meadow changes (cover, dominant species) |
| ☐ | Depth + time + vertical photo every 2 m, from 0 m to 5–10 m beyond the 30 m mark, and at each sensor |

### Each quadrat (front 2.5 m, centre 15 m, back 27.5 m)

| ☐ | Item |
|---|------|
| ☐ | **Data:** canopy height at 5 points |
| ☐ | Photo 1: canopy, straight down, frame in view |
| ☐ | Photo 2: shoot bases with leaves pushed aside, whole frame visible |
| ☐ | **Data:** on 10–15 shoots of the dominant species, measured in place: number of blades, length and width of the longest blade |
| ☐ | **Data:** on 3–5 shoots, thickness of the stack of blades at mid-length and number of blades in the stack |
| ☐ | **Data:** other species present |

### After the survey

| ☐ | Item |
|---|------|
| ☐ | Slate photographed and copied into the field sheet |
| ☐ | Photos downloaded and named with site, transect, station or quadrat |

---

## Why we do this in SEASTRONG

In **WP1, Task 1.2 / WP4**, the structure of the seagrass meadow between the two pressure sensors is used to explain the measured wave attenuation and to parameterise seagrass drag in the XBeach models. The depth profile gives the bed along which waves propagate, needed both to interpret the sensor records and to build the model profile.

---

## References

Luhar, M. and Nepf, H. M. (2011). Flow-induced reconfiguration of buoyant and flexible aquatic vegetation. *Limnology and Oceanography*, 56(6), 2003–2017. [doi:10.4319/lo.2011.56.6.2003](https://doi.org/10.4319/lo.2011.56.6.2003)
