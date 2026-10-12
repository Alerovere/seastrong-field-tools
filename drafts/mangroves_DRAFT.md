# Mangrove Structure and Topography

<!-- DRAFT for review. Items marked [CHECK] are assumptions to confirm or correct. -->

## Overview

This page describes how to characterise the **structure** and **topography** of mangrove forest along the wave-attenuation transects. The structural data are used to parameterise the drag exerted by the mangrove on waves and currents in the XBeach models, and the topography provides the bed profile along which wave attenuation is measured.

Mangrove forests vary from open stands with pneumatophores to dense stands of prop-rooted trees, so no single method works everywhere. The method is chosen in the field according to how dense the forest is (see [Choosing the method](#choosing-the-method)). **Topography is always measured, whatever method is used for the structure.**

**Source code:** [github.com/Alerovere/seastrong-field-tools](https://github.com/Alerovere/seastrong-field-tools/tree/main/Mangroves_topography)

---

## Transect layout

- The transect is **cross-shore**, between the two pressure sensors of the wave-attenuation deployment: **sensor 1 at the front** (seaward edge of the forest) and **sensor 2 at the back**. See the [wave attenuation](wave_attenuation.md) page for the sensor deployment.
- A **30 m tape** is laid along the transect, from the 0 m mark (front) to the 30 m mark (back). [CHECK: is 0 m always at sensor 1 / forest edge?]
- Record on the field sheet: site, transect ID, date, operators, sensor IDs and their position along the tape, approximate GPS position of the 0 m end, and the compass bearing from 0 m to 30 m.
- Work at **low tide**, when the forest floor is exposed.

---

## Choosing the method

Three methods are used for the structure, in order of preference. Use the first one that is possible at the site.

| Forest condition | Method | What it gives |
|---|---|---|
| Open forest, or forest with **pneumatophores**, where the ground along the tape can be seen and photographed from several sides | **A. Photogrammetry** | 3D model of roots, pneumatophores and trunks along the whole transect |
| Denser forest with **prop roots** (e.g. *Rhizophora*), where a continuous 3D model is not possible but individual trees can be approached and photographed | **B. Tree-by-tree root parameterisation** (Mori et al., 2022) | Tree and root dimensions, and frontal area of the root system with height, for sample trees + tree density |
| Forest so dense that only manual measurements are possible | **C. Manual measurements** | Stem and root diameters and densities at the front, centre and back of the transect |

If the forest changes along the transect (e.g. open at the front and dense at the back), different methods can be used on different stretches. Note on the field sheet which method was used between which tape marks. [CHECK]

---

## A. Photogrammetry

Photogrammetry follows the same principle as the [underwater photogrammetry](underwater_photogrammetry.md) survey, adapted to an emerged forest floor.

```{figure} _static/mangrove_photogrammetry_targets.jpg
:width: 90%
:alt: Scale-bar targets placed along the transect tape in a mangrove stand with dense pneumatophores

Scale-bar targets placed along the transect tape among pneumatophores. Each bar carries an Agisoft coded target at each end, with the target centres at a known distance.
```

### Equipment

- **2× action cameras** (e.g. GoPro) on a short rig, with the cameras at a **short distance from each other** (e.g. 10–20 cm) [CHECK], labelled A and B. A short spacing gives two slightly different views of the same roots and improves the reconstruction of thin, vertical structures such as pneumatophores.
- **30 m tape**
- **Scale-bar targets (at least 8)** with an Agisoft coded target at each end and a known centre-to-centre distance, from the same bar list used for the underwater surveys
- Slate or field sheet, GPS (phone), compass

### Camera settings

Use the same settings as for the underwater survey (Timelapse, 0.5 s interval, Linear, Protune, flat colour, JPEG), with these differences for use in air under the canopy: [CHECK]

- **White balance:** fixed, around 5500K (daylight) or 6000–6500K under heavy shade. Do not use Auto, so that colour stays the same through the survey.
- **ISO and shutter:** light under the canopy is low. Allow ISO up to 800 and keep the shutter at 1/250 s or faster to avoid motion blur while walking.
- No red filter.

### Field procedure

1. Lay the tape along the transect and secure both ends.
2. Place **at least 8 scale bars** along the transect, on **both sides of the tape**, within ~2 m of it, with varied orientation and at **different elevations** (on the ground, on raised roots or hummocks, in depressions). Record the target codes, position along the tape and side (L/R, looking landward).
3. Record the **elevation of each target** by including it in the topography survey (see [Topography](#topography)): measure its distance along the tape and its height relative to the tape line. [CHECK: how do you want target elevations referenced? Same approach as the depth gauge underwater is not possible here.]
4. Start both cameras as simultaneously as possible. Synchronisation is done in post-processing.
5. Walk the transect holding the rig at about **1–1.5 m above the ground** [CHECK], in three passes:
   1. **forward**, with camera A over the tape, cameras pointing straight down;
   2. **backward**, with camera A over the tape, cameras pointing straight down;
   3. **zigzag** across the tape out to ~3 m each side, with the cameras **tilted about 45° forward**. Oblique views are needed to reconstruct the sides of pneumatophores, roots and trunks, which are almost invisible from directly above. [CHECK]
6. Walk slowly (about 0.3 m/s) and avoid stepping on pneumatophores or targets.
7. Before leaving, check on both cameras that photos were recorded for the whole survey and are sharp.

Processing in Agisoft Metashape is the same as for the underwater survey: detect targets, define scale bars, use the target elevations as vertical reference, then build the dense cloud and mesh. From the model, pneumatophore and root density, height and frontal area with height are extracted along the transect.

---

## B. Tree-by-tree root parameterisation (Mori et al., 2022)

When the forest is too dense for a continuous 3D model, the structure is described tree by tree following Mori et al. (2022), who parameterised the root system of *Rhizophora stylosa* for hydrodynamic models. The key quantity for the models is the **frontal (projected) area of the root system with height above the ground**, A(z), which is obtained from photos of individual trees, combined with tree density.

### Where to measure

- Three **plots** along the transect: at the **front** (sensor 1), the **centre** (~15 m) and the **back** (sensor 2). [CHECK: same three positions as method C?]
- In each plot, count all trees in a fixed area (e.g. 5 m × 5 m) [CHECK] to obtain **tree density** (trees per m²).
- In each plot, measure **at least 5 sample trees** [CHECK] covering the range of sizes present.

### Measurements on each sample tree

Following Mori et al. (2022, their Figure 1):

| Parameter | How to measure |
|---|---|
| Tree height **H** | From the ground to the top of the canopy (tape or measuring pole; clinometer for tall trees) |
| Diameter at breast height **DBH** | Trunk diameter at 1.30 m above the ground (caliper or diameter tape) |
| Trunk diameter **D1** | Trunk diameter just above the top of the root system |
| Root system height **Hroot** | From the ground to the highest point where prop roots leave the trunk |
| Spanning radius **W** | Distance from the trunk to the outermost root, measured in **six directions** (the two main axes of the root system and the four largest roots); the average is used |
| Number of prop roots **N** | Count of roots reaching the ground |
| Root diameter | Diameter of the prop roots at **20 cm above the ground** (caliper) |

### Photos of the root system

1. Place a **plain board** (e.g. white, ~1 m × 2 m, with a scale marked along its edges) [CHECK] behind the root system, so that the roots stand out against it.
2. Photograph the root system **perpendicular to the board**, with the camera level and far enough away to include the whole root system and the scale.
3. Take photos in **two directions**: along the main axis of the root system and perpendicular to it. Where possible, make one of them the **cross-shore** direction (the direction of wave approach). [CHECK]
4. Note the tree ID and direction for each photo.

In processing, the photos are binarised, the root system is extracted, and its pixels are counted and converted to area using the scale, giving the projected area of the root system and its distribution with height, A(z) (Mori et al., 2022).

---

## C. Manual measurements

Where the forest is so dense that neither photogrammetry nor photos of individual trees are possible, structure is measured by hand at **three positions**: the **front** (sensor 1), the **centre** (~15 m) and the **back** (sensor 2).

At each position: [CHECK: plot sizes and heights]

- **Trees:** in a plot of e.g. 5 m × 5 m, count all trees and measure the DBH of each with a caliper or diameter tape. Measure the height of a few representative trees.
- **Prop roots and pneumatophores:** in a smaller quadrat (e.g. 1 m × 1 m, or 0.5 m × 0.5 m for very dense pneumatophores), count all roots or pneumatophores, and measure with a caliper the diameter and height of a sample (e.g. 10–20).
- **Diameter with height:** for a few roots and stems, measure the diameter at several heights above the ground (e.g. 10, 20, 50 and 100 cm), so that the frontal area per unit volume can be computed at each height as number per m² × diameter.
- Take photos of each plot from the front and from above, with a scale.

---

## Topography

Topography is measured for **every** transect, whatever method was used for the structure. The profile runs from the **low-water mark** to the **30 m mark** of the tape.

- Identify the **low-water mark** on the ground (the water's edge at the time of low tide, or the visible low-water line) and record the time. [CHECK: is the low-water mark seaward of the 0 m mark? If so, the topography profile starts before the tape.]
- Measure the profile with tape distance and inclination readings, with an RTK GNSS fix at the starting point (and optionally at other points as ties), as described in the notebook `Mangroves_topography/mangrove_transect_topography.ipynb`.
- Take readings at every change in slope and at least every 2 m [CHECK], and include the positions of the two sensors and, for method A, the photogrammetry targets.
- The notebook reconstructs the X/Y/Z profile and exports a CSV, a plot and a GeoJSON file.

---

## Field checklist

### All methods

| ☐ | Item |
|---|------|
| ☐ | **Data:** site, transect ID, date, operators, tide time |
| ☐ | **Data:** sensor IDs and position along the tape |
| ☐ | **Data:** approximate GPS position of the 0 m end and compass bearing from 0 m to 30 m |
| ☐ | **Data:** method used (A, B or C), and between which tape marks if more than one |
| ☐ | **Data:** dominant species and general description of the forest (open/dense, pneumatophores/prop roots) |
| ☐ | Overview photos of the transect from both ends |
| ☐ | Topography from the low-water mark to the 30 m mark, with the RTK fix at the start |

### Method A: photogrammetry

| ☐ | Item |
|---|------|
| ☐ | **Data:** camera spacing (cm) |
| ☐ | At least 8 scale bars on both sides, varied orientation and elevation; **data:** codes, position, side |
| ☐ | Target positions included in the topography survey |
| ☐ | Passes: forward and backward (cameras down), zigzag (cameras tilted ~45°) |
| ☐ | Photos checked on both cameras |

### Method B: tree-by-tree (Mori et al., 2022)

| ☐ | Item |
|---|------|
| ☐ | Plots at front, centre and back; **data:** tree count per plot (density) |
| ☐ | **Data per sample tree:** H, DBH, D1, Hroot, W in six directions, N, root diameter at 20 cm |
| ☐ | Root system photos against the board in two directions, with scale; **data:** tree ID and direction per photo |

### Method C: manual

| ☐ | Item |
|---|------|
| ☐ | Plots at front, centre and back |
| ☐ | **Data:** tree count and DBH in each plot; heights of representative trees |
| ☐ | **Data:** root/pneumatophore count in each quadrat; diameter and height of a sample |
| ☐ | **Data:** diameters at several heights for a few roots and stems |
| ☐ | Plot photos with scale |

---

## References

Mori, N., Chang, C.-W., Inoue, T., Akaji, Y., Hinokidani, K., Baba, S., Takagi, M., Mori, S., Koike, H., Miyauchi, M., Suganuma, R., Sabunas, A., Miyashita, T. and Shimura, T. (2022). Parameterization of mangrove root structure of *Rhizophora stylosa* in coastal hydrodynamic model. *Frontiers in Built Environment*, 7, 782219. [doi:10.3389/fbuil.2021.782219](https://doi.org/10.3389/fbuil.2021.782219)

---

## Why we do this in SEASTRONG

In **WP1, Task 1.2 / WP4**, the structure of the mangrove between the two pressure sensors is used to explain the measured wave attenuation and to parameterise mangrove drag in the XBeach models. The topography gives the bed profile along which waves propagate and is needed both to interpret the sensor records and to build the model profile.
