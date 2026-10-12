# Mangrove Structure and Topography

## Overview

This page describes how to measure the **structure** and **topography** of the mangrove forest along the wave-attenuation transects. The structure is used to parameterise mangrove drag in the XBeach models; the topography gives the bed profile along which wave attenuation is measured.

Mangrove forests range from open stands with pneumatophores to dense stands of prop-rooted trees, so the method for the structure is chosen in the field according to forest density. **Topography is always measured, whatever method is used for the structure.**

**Source code:** [github.com/Alerovere/seastrong-field-tools](https://github.com/Alerovere/seastrong-field-tools/tree/main/Mangroves_topography)

---

## Transect layout

- The transect is **cross-shore**, between the two pressure sensors of the wave-attenuation deployment: **sensor 1 at the front** (seaward edge of the forest) and **sensor 2 at the back**. See the [wave attenuation](wave_attenuation.md) page for the sensor deployment.
- A **30 m tape** is laid along the transect, from the 0 m mark (front) to the 30 m mark (back). The 0 m mark is always at sensor 1, at the forest edge.
- Record on the field sheet: site, transect ID, date, operators, sensor IDs and their position along the tape, approximate GPS position of the 0 m end, and the compass bearing from 0 m to 30 m.
- Work at **low tide**, when the forest floor is exposed.

---

## Topography

Topography is measured for **every** transect, whatever method is used for the structure. The profile runs from the **low-water mark** to the **30 m mark** of the tape.

```{figure} _static/mangrove_topography_transect.svg
:width: 100%
:alt: Schematic of the topographic transect: side view with stations, one segment measured with two poles and a clinometer, plan view with bearing, and the resulting CSV

How to measure the topographic profile. (A) Stations along the tape from the low-water mark to the 30 m mark, with the GNSS fix at the start. (B) One segment: inclination measured with a clinometer between two poles of equal height, and slope distance read on the tape. (C) The profile is a straight line with one compass bearing. (D) One CSV row per station, in the format read by the processing notebook.
```

- Identify the **low-water mark** on the ground (the water's edge at low tide, or the visible low-water line) and record the time.
- Measure the profile with tape distance and inclination readings, with a GNSS fix at the starting point: RTK GNSS if available (optionally also at other points as ties), otherwise a simple handheld GNSS.
- The readings are processed with the notebook `Mangroves_topography/mangrove_transect_topography.ipynb`, which reconstructs the X/Y/Z profile and exports a CSV, a plot and a GeoJSON file.

### How to measure the profile

1. **Start point:** the low-water mark. Take a GNSS fix there: RTK GNSS (latitude, longitude and elevation) if available, otherwise a handheld GNSS (latitude and longitude; the elevation is then only approximate and the profile is relative).
2. **Bearing:** take the compass bearing of the profile, pointing landward. The profile is straight and follows the transect.
3. **Stations:** run the tape from the start point landward to the 30 m mark of the transect tape. Place a station at every change in slope and at most 2 m apart, and always at the transect 0 m mark, sensor 1, sensor 2 and the 30 m mark.
4. **Distance:** at each station, read the cumulative distance along the taut, straight tape from the start point (slope distance).
5. **Inclination:** for each segment between two consecutive stations, measure the slope with a clinometer (or phone app), sighting between two poles of equal height held vertically on the two stations. Sign: **+ = uphill landward**, **− = downhill landward**.
6. **Optional ties:** if RTK GNSS is available, also take fixes at other stations (e.g. at the sensors and the 30 m mark); the notebook uses them to correct the profile.
7. **Labels:** name the key stations (low water, 0 m, sensor 1, sensor 2, 30 m).

Enter the readings in a CSV, one row per station, in the format read by the notebook:

| Column | Content |
| --- | --- |
| `tape_distance_m` | Cumulative distance from the start point (m) |
| `inclination_deg` | Slope of the segment leading to this station (°, + uphill landward); empty on the first row |
| `lat`, `lon`, `z` | GNSS fix: required on the first row, optional on others |
| `label` | Station name (optional) |

---

## Choosing the method

Three methods are used for the structure, in order of preference. Use the first one that is possible at the site.

| Forest condition | Method | What it gives |
| --- | --- | --- |
| Open forest, or forest with **pneumatophores**, where the ground along the tape can be photographed from several sides | **A. Photogrammetry** | 3D model of roots, pneumatophores and trunks along the whole transect |
| Denser forest with **prop roots** (e.g. *Rhizophora*), where a continuous 3D model is not possible but individual trees can be approached and photographed | **B. Tree-by-tree root parameterisation** (Mori et al., 2022) | Tree and root dimensions, frontal area of the root system with height for sample trees, plus tree density |
| Forest so dense that only manual measurements are possible | **C. Manual measurements** | Stem and root diameters and densities at front, centre and back |

If the forest changes along the transect (e.g. open at the front and dense at the back), different methods can be used on different stretches. Note on the field sheet which method was used between which tape marks.

---

## A. Photogrammetry

Same principle as the [underwater photogrammetry](underwater_photogrammetry.md) survey, adapted to an emerged forest floor.

```{figure} _static/mangrove_photogrammetry_targets.jpg
:width: 90%
:alt: Scale-bar targets placed along the transect tape in a mangrove stand with dense pneumatophores

Scale-bar targets placed along the transect tape among pneumatophores. Each bar carries an Agisoft coded target at each end, with the target centres at a known distance.
```

### Equipment

- **2× action cameras** (e.g. GoPro) on a short rig, at a **short distance from each other** (e.g. 10–20 cm), labelled A and B. A short spacing improves the reconstruction of thin, vertical structures such as pneumatophores.
- **30 m tape**
- **Scale-bar targets (at least 6)** with an Agisoft coded target at each end and a known centre-to-centre distance, from the same bar list used underwater
- Field sheet, GPS (phone), compass

### Camera settings

Same as for the [underwater survey](underwater_photogrammetry.md) (Timelapse, 0.5 s interval, Linear, Protune, flat colour, JPEG), with these changes for use in air under the canopy:

- White balance fixed at about 5500K (6000–6500K under heavy shade), not Auto.
- Light under the canopy is low: allow ISO up to 800 and keep the shutter at 1/250 s or faster.
- No red filter.

### Field procedure

1. Lay the tape along the transect and secure both ends.
2. Place **at least 6 scale bars** on **both sides of the tape**, within ~2 m of it, with varied orientation and at **different elevations** (ground, raised roots or hummocks, depressions). Record target codes, position along the tape and side (L/R, looking landward).
3. The targets are used **only to scale** the model: their elevation is not measured.
4. Start both cameras as simultaneously as possible; synchronisation is done in post-processing.
5. Walk the transect holding the rig about **1–1.5 m above the ground**, in three passes:
   1. **forward**, camera A over the tape, cameras pointing straight down;
   2. **backward**, camera A over the tape, cameras pointing straight down;
   3. **zigzag** across the tape out to ~3 m each side, cameras **tilted about 45° forward**. Oblique views are needed to reconstruct the sides of pneumatophores, roots and trunks.
6. Walk slowly (about 0.3 m/s) and avoid stepping on pneumatophores or targets.
7. Before leaving, check that both cameras recorded the whole survey and that photos are sharp.

Processing in Agisoft Metashape follows the underwater workflow: detect targets, define scale bars, then build dense cloud and mesh. Pneumatophore and root density, height and frontal area with height are extracted from the model.

---

## B. Tree-by-tree root parameterisation (Mori et al., 2022)

When the forest is too dense for a continuous 3D model, structure is described tree by tree following Mori et al. (2022), who parameterised the root system of *Rhizophora stylosa* for hydrodynamic models. The key quantity is the **frontal (projected) area of the root system with height above the ground**, A(z), obtained from photos of individual trees and combined with tree density.

### Where to measure

- Three **plots** along the transect: **front** (sensor 1), **centre** (~15 m) and **back** (sensor 2). These are the same three positions used in method C.
- In each plot, count all trees in a 5 m × 5 m area to obtain **tree density** (trees per m²).
- In each plot, measure **at least 5 sample trees** covering the range of sizes present.

### Measurements on each sample tree

Following Mori et al. (2022, their Figure 1):

| Parameter | How to measure |
| --- | --- |
| Tree height **H** | Ground to top of canopy (tape or pole; clinometer for tall trees) |
| Diameter at breast height **DBH** | Trunk diameter at 1.30 m above the ground (caliper or diameter tape) |
| Trunk diameter **D1** | Trunk diameter just above the top of the root system |
| Root system height **Hroot** | Ground to the highest point where prop roots leave the trunk |
| Spanning radius **W** | Trunk to outermost root, in **six directions** (two main axes of the root system + four largest roots); averaged |
| Number of prop roots **N** | Count of roots reaching the ground |
| Root diameter | Diameter of prop roots at **20 cm above the ground** (caliper) |

### Photos of the root system

1. Place a **plain board** (e.g. white, ~1 m × 2 m, with a scale marked along its edges) behind the root system so the roots stand out against it.
2. Photograph **perpendicular to the board**, camera level, far enough to include the whole root system and the scale.
3. Take photos in **two directions**: along the main axis of the root system and perpendicular to it. Where possible, make one of them the **cross-shore** direction (direction of wave approach).
4. Note tree ID and direction for each photo.

In processing, each photo is binarised, the root system is extracted, and its pixels are counted and converted to area using the scale, giving the projected area and its distribution with height, A(z).

---

## C. Manual measurements

Where the forest is so dense that neither photogrammetry nor photos of individual trees are possible, structure is measured by hand at **three positions**: **front** (sensor 1), **centre** (~15 m) and **back** (sensor 2). At each position:

- **Trees:** in a plot of 5 m × 5 m, count all trees and measure each DBH with a caliper or diameter tape. Measure the height of a few representative trees.
- **Prop roots and pneumatophores:** in a smaller quadrat (e.g. 1 m × 1 m, or 0.5 m × 0.5 m for very dense pneumatophores), count all roots or pneumatophores and measure with a caliper the diameter and height of a sample (e.g. 10–20).
- **Diameter with height:** for a few roots and stems, measure the diameter at several heights above the ground (e.g. 10, 20, 50 and 100 cm), so the frontal area per unit volume can be computed at each height as number per m² × diameter.
- Take photos of each plot from the front and from above, with a scale.

---

## Field checklist

Print this section so that nothing is forgotten.

### All methods

| ☐ | Item |
|---|------|
| ☐ | **Data:** site, transect ID, date, operators, tide time |
| ☐ | **Data:** sensor IDs and position along the tape |
| ☐ | **Data:** approximate GPS position of the 0 m end and compass bearing from 0 m to 30 m |
| ☐ | **Data:** method used (A, B or C), and between which tape marks if more than one |
| ☐ | **Data:** dominant species and general description of the forest (open/dense, pneumatophores/prop roots) |
| ☐ | Overview photos of the transect from both ends |
| ☐ | Topography from the low-water mark to the 30 m mark, with a GNSS fix at the start (RTK if available, otherwise handheld) |

### Method A: photogrammetry

| ☐ | Item |
|---|------|
| ☐ | **Data:** camera spacing (cm) |
| ☐ | At least 6 scale bars on both sides, varied orientation and elevation; **data:** codes, position, side |
| ☐ | Passes: forward and backward (cameras down), zigzag (cameras tilted ~45°) |
| ☐ | Photos checked on both cameras |

### Method B: tree-by-tree (Mori et al., 2022)

| ☐ | Item |
|---|------|
| ☐ | Plots at front, centre and back; **data:** tree count per 5 m × 5 m plot (density) |
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

## Why we do this in SEASTRONG

In **WP1, Task 1.2 / WP4**, the structure of the mangrove between the two pressure sensors is used to explain the measured wave attenuation and to parameterise mangrove drag in the XBeach models. The topography gives the bed profile along which waves propagate, needed both to interpret the sensor records and to build the model profile.

---

## References

Mori, N., Chang, C.-W., Inoue, T., Akaji, Y., Hinokidani, K., Baba, S., Takagi, M., Mori, S., Koike, H., Miyauchi, M., Suganuma, R., Sabunas, A., Miyashita, T. and Shimura, T. (2022). Parameterization of mangrove root structure of *Rhizophora stylosa* in coastal hydrodynamic model. *Frontiers in Built Environment*, 7, 782219. [doi:10.3389/fbuil.2021.782219](https://doi.org/10.3389/fbuil.2021.782219)
