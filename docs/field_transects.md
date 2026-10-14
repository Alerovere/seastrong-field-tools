# Field Transects: Common Protocol

## Overview

In each study area (Belize, Seychelles, Fiji), wave attenuation and habitat structure are measured along **one transect per habitat per corridor**, in **6 corridors**: 6 reef, 6 seagrass and 6 mangrove transects per study area. All transects follow the same layout and the same basic rules, described on this page. What changes between habitats is how the structure is measured:

| Habitat | Structure survey | Bed profile | Page |
| --- | --- | --- | --- |
| Coral reef | Two-camera photogrammetry | Depth every 2 m + target depths | [Underwater photogrammetry](underwater_photogrammetry.md) |
| Seagrass | Quadrats (photos + shoot measurements) | Depth every 2 m | [Seagrass](seagrass.md) |
| Mangrove | Photogrammetry, tree-by-tree, or manual (by forest density) | Topographic profile | [Mangroves](mangroves.md) |

The sensor deployment is described on the [wave attenuation](wave_attenuation.md) page. Each structure survey is done **once per transect**, not at every sensor deployment, but in the **same field campaign** as the deployments.

---

## Transect layout (all habitats)

- The transect is **cross-shore**, between the two pressure sensors: **sensor 1 at the seaward end** and **sensor 2 at the landward end**.
- A **30 m tape** is laid on the bottom (or the ground) from the **0 m mark at sensor 1** to the **30 m mark at sensor 2**. The 0 m mark is always the seaward end.
- The **bed profile** (depth or topography) extends **5–10 m beyond the 30 m mark**, so that the landward boundary of the model is not at sensor 2. On mangrove transects it also starts at the low-water mark, seaward of 0 m.
- Positions along the transect are always given as **distance along the tape from 0 m**, and sides as **left/right looking landward**.

---

## Before the trip

| ☐ | Item |
|---|------|
| ☐ | The two cameras of each rig set to the **same time** (from the GoPro app) |
| ☐ | Cameras labelled A and B (camera and housing) |
| ☐ | Bar list prepared: target codes and measured centre-to-centre distance of each scale bar |
| ☐ | Slates prepared with the field sheet of each habitat |
| ☐ | Equipment checked against the purchase list |
| ☐ | Field forms printed: {download}`reef <_static/forms/reef_photogrammetry_field_form_v1.0.pdf>`, {download}`mangrove <_static/forms/mangrove_field_form_v1.0.pdf>` |

Times of depth readings are written from a watch or phone; note the time zone on the slate, so that depths can be corrected for the tide with the pressure-sensor record.

---

## On every transect

Record on the slate or field sheet (the **header**, the same for all habitats):

- study area, corridor, habitat, date, operators, and the **transect ID**: area + date (DDMMYY) + corridor + habitat, e.g. `BZ140327C1reef`, `BZ150327C1seagrass`, `BZ160327C1mangrove`;
- sensor IDs and their **position along the tape**;
- **approximate GPS position** of the 0 m end (phone or handheld GPS) and **compass bearing** from 0 m to 30 m;
- tape positions where the habitat visibly changes (e.g. bare sand, patchy or continuous seagrass; open or dense mangrove; change of dominant species);
- conditions (tide, visibility, waves, cloud).

At the end, **photograph the slate** before wiping it, and copy it into the digital field sheet the same evening.

### File names

Start every file and folder name with the transect ID, then the item: `<transectID>_<item>`, with area `BZ`, `SC` or `FJ`, corridor `C1`–`C6` and habitat `reef`, `seagrass` or `mangrove`. For example: `BZ150327C3seagrass_Q05_photo2.jpg`, `FJ020627C1reef_camA/`. Dates in forms are written as mm/dd/yyyy; in the transect ID the date is DDMMYY.

---

## Bed profile and vertical datum

- **Reef and seagrass:** depth (gauge or graduated stick) and **time** every 2 m along the tape, and on for 5–10 m beyond the 30 m mark, plus a reading at each sensor. Depths are corrected for the tide with the pressure-sensor record.
- **Mangrove:** topographic profile from the low-water mark to 5–10 m beyond the 30 m mark (see the [mangrove page](mangroves.md#topography)).
- **Vertical datum:** the bed, the sensor water levels and the tide used at the model boundary must be on the same datum. The sensors tie each profile to the measured water levels; an **RTK GNSS fix or a local benchmark, at least once per site**, links it to an absolute datum.

---

## Effort per study area

Rough times for a team of two, in good conditions. They are first estimates and should be checked in the first days of fieldwork.

| Habitat | Time per transect | 6 transects (one study area) |
| --- | --- | --- |
| Coral reef | ~1–1.25 h in the water | ~6–8 h, 2–3 field days |
| Seagrass | ~1.5 h in the water | ~9 h, 3–4 field days |
| Mangrove | ~4–5 h (topography + method C); less with method A | ~25–30 h, 6 field days |

Add travel between corridors, weather days and sensor deployments when planning a ~20-day stay. Reef and seagrass transects of the same corridor can often be done on the same day.

---

## Safety and care of the habitat

- Never work alone: always in a pair, with surface support (boat or shore) in the water, and with agreed signals.
- Check weather, tide and current before going out, and stop if conditions get worse.
- Sun protection, rash vest or wetsuit, water; boots and gloves in the mangrove.
- Do not touch, kneel on or fin against coral; do not step on pneumatophores where it can be avoided; nothing is collected.
- Follow the conditions of the research permit for each site.

---

## Notes for modelling (all habitats)

- **Same campaign:** structure, bed profile and wave data must describe the same state of the habitat.
- **Same method within a habitat:** calibrated drag coefficients can only be compared and pooled if structure is measured and converted to model inputs in the same way at every transect. Always record which method was used.
- **Model domain:** the profile beyond the 30 m mark keeps the landward boundary away from sensor 2.
- **Zones:** habitat zones in the 1D model follow the boundaries noted along the tape.
