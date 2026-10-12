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
:alt: Schematic of the topographic transect: side view with stations, one segment measured on the ground with a clinometer on a plastic board, plan view with bearing, and the resulting CSV

How to measure the topographic profile. (A) Stations along the tape from the low-water mark to the 30 m mark, with the GNSS fix at the start. (B) One segment: inclination measured on the ground with a clinometer placed on a plastic board, and slope distance read on the tape. (C) The profile is a straight line with one compass bearing. (D) One CSV row per station, in the format read by the processing notebook.
```

- Identify the **low-water mark** on the ground (the water's edge at low tide, or the visible low-water line) and record the time.
- Measure the profile with tape distance and inclination readings, with a GNSS fix at the starting point: RTK GNSS if available (optionally also at other points as ties), otherwise a simple handheld GNSS.
- The readings are processed with the notebook `Mangroves_topography/mangrove_transect_topography.ipynb`, which reconstructs the X/Y/Z profile and exports a CSV, a plot and a GeoJSON file.

### How to measure the profile

1. **Start point:** the low-water mark. Take a GNSS fix there: RTK GNSS (latitude, longitude and elevation) if available, otherwise a handheld GNSS (latitude and longitude; the elevation is then only approximate and the profile is relative).
2. **Bearing:** take the compass bearing of the profile, pointing landward. The profile is straight and follows the transect.
3. **Stations:** run the tape from the start point landward to the 30 m mark of the transect tape. Place a station at every change in slope and at most 2 m apart, and always at the transect 0 m mark, sensor 1, sensor 2 and the 30 m mark.
4. **Distance:** at each station, read the cumulative distance along the taut, straight tape from the start point (slope distance).
5. **Inclination:** for each segment between two consecutive stations, lay a rigid plastic board (e.g. a small plastic whiteboard) flat on the ground along the tape, put the clinometer (or phone app) on it, aligned with the tape, and read the slope. The board keeps the clinometer out of mud and water and smooths small bumps. Sign: **+ = uphill landward**, **− = downhill landward**.
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

```{figure} _static/mangrove_root_board.svg
:width: 100%
:alt: Example of root-system photos against a plain board: what the photo should look like, the set-up seen from above, and the processing to A(z)

Example set-up for root-system photos (illustrative). (A) The board stands behind the root system, with a scale on its edges and a card with tree ID, plot and direction. (B) Two photos per tree, one cross-shore and one along-shore, each with the board behind the tree and the camera opposite. (C) Processing: the binarised photo is divided into 10 cm height bands and the root pixels in each band give A(z).
```

1. Place a **plain board** (e.g. white, ~1 m × 2 m, with a scale marked along its edges) behind the root system so the roots stand out against it. Include a card in the frame with tree ID, plot and photo direction.
2. Photograph **perpendicular to the board**, camera level, far enough to include the whole root system and the scale.
3. Take photos in **two directions**: along the main axis of the root system and perpendicular to it. Where possible, make one of them the **cross-shore** direction (direction of wave approach).
4. Note tree ID and direction for each photo.

In processing, each photo is binarised, the root system is extracted, and its pixels are counted and converted to area using the scale, giving the projected area and its distribution with height, A(z).

---

## C. Manual measurements

Use this method where the forest is so dense that neither photogrammetry nor photos of single trees are possible. The hydrodynamic models describe the vegetation as layers at different heights above the ground, so what is needed is a **vertical profile** of the vegetation: at each height z, the **frontal area per unit volume**, a(z), i.e. how much stem and root surface the water meets per m³. The method keeps the counting simple (density) and puts the effort on measuring the vertical structure of a few sample trees.

```{figure} _static/mangrove_manual_measurements.svg
:width: 100%
:alt: Plan view of the three 5 m by 5 m plots with sample trees and a pneumatophore quadrat, and side view of a sample tree with measuring heights at 25, 50, 75, 100 and 150 cm

Manual measurements. (A) Three 5 m × 5 m plots along the tape (front, centre, back): count all trees, measure 3–5 sample trees in detail, and count pneumatophores in one quadrat. (B) On each sample tree, prop roots and trunk are counted and measured at 25, 50, 75, 100 and 150 cm along a measuring pole.
```

### Where to measure

- Three **5 m × 5 m plots**, along the tape and centred on it (2.5 m on each side): **front** from 0 to 5 m (at sensor 1), **centre** from 12.5 to 17.5 m, **back** from 25 to 30 m (at sensor 2). These are the same positions as in method B.
- Mark the plot corners with stakes.

### 1. Density (quick)

1. Count all trees rooted inside the plot, and note the species.
2. Measure the **DBH** of each tree with a caliper or diameter tape at 1.3 m above the ground. Where prop roots reach above 1.3 m, measure 30 cm above the highest prop root and record that height.
3. **Pneumatophores:** in one 1 m × 1 m quadrat per plot (0.5 m × 0.5 m if they are too many to count), count all pneumatophores, and measure the height and the diameter (at the base and at mid-height) of up to 20 of them.

### 2. Vertical profile of sample trees (detailed)

Choose **3–5 sample trees** per plot that cover the range of sizes present. For each tree:

1. Place a **measuring pole** (marked every 10 cm) vertically next to the trunk.
2. Measuring heights: **every 25 cm up to 1 m** (25, 50, 75 and 100 cm), then at **150 cm**. This gives five heights, up to 1.5 m above the ground.
3. At each height:
   - **count** the prop roots of this tree that cross that height;
   - **measure** their diameters with a caliper (all of them, or up to 10 if there are more);
   - **measure** the trunk diameter (where the trunk is present at that height).
4. Record the height of the root system (**Hroot**) and the tree height.

A horizontal stick held at each height against the pole makes it easy to see which roots cross it. If the roots of neighbouring trees are too intertwined to tell which tree they belong to, use the **quadrat frame instead**: raise a 1 m × 1 m frame to each height and count and measure all roots and stems passing through it; this gives the number per m² directly.

### From the measurements to a(z)

For each plot and height z:

a(z) = tree density × mean (sum of diameters per tree at z) + pneumatophore density × pneumatophore diameter (only below the pneumatophore height)

with the density in trees (or pneumatophores) per m² and diameters in m, so that a(z) is in m²/m³ (m⁻¹). Example for one plot with 20 trees in 25 m² (0.8 trees/m²) and 60 pneumatophores/m², about 30 cm high and 1.2 cm wide (illustrative numbers):

| Height | Per tree: roots × diameter (+ trunk) | Sum of diameters per tree | Trees: 0.8 × sum | Pneumatophores: 60 × 0.012 | a(z) |
| --- | --- | --- | --- | --- | --- |
| 25 cm | 12 × 2.5 cm | 0.30 m | 0.24 | 0.72 | 0.96 m⁻¹ |
| 50 cm | 9 × 3.0 cm | 0.27 m | 0.22 | – | 0.22 m⁻¹ |
| 75 cm | 2 × 3.5 cm + trunk 12 cm | 0.19 m | 0.15 | – | 0.15 m⁻¹ |
| 100 cm | trunk 12 cm | 0.12 m | 0.10 | – | 0.10 m⁻¹ |
| 150 cm | trunk 11 cm | 0.11 m | 0.09 | – | 0.09 m⁻¹ |

The profiles of the front, centre and back plots are then grouped into the vertical layers used by the model.

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
| ☐ | Three 5 m × 5 m plots centred on the tape: front (0–5 m), centre (12.5–17.5 m), back (25–30 m) |
| ☐ | **Data:** tree count and species in each plot; DBH of each tree (and measurement height if not 1.3 m) |
| ☐ | **Data:** pneumatophore count in one quadrat per plot (and quadrat size); height and diameter (base, mid-height) of up to 20 |
| ☐ | 3–5 sample trees per plot, covering the range of sizes |
| ☐ | **Data per sample tree, at 25, 50, 75, 100 and 150 cm:** number of roots crossing, their diameters, trunk diameter |
| ☐ | **Data per sample tree:** Hroot and tree height |
| ☐ | Photos of each plot and sample tree, with scale |

---

## Why we do this in SEASTRONG

In **WP1, Task 1.2 / WP4**, the structure of the mangrove between the two pressure sensors is used to explain the measured wave attenuation and to parameterise mangrove drag in the XBeach models. The topography gives the bed profile along which waves propagate, needed both to interpret the sensor records and to build the model profile.

---

## References

Mori, N., Chang, C.-W., Inoue, T., Akaji, Y., Hinokidani, K., Baba, S., Takagi, M., Mori, S., Koike, H., Miyauchi, M., Suganuma, R., Sabunas, A., Miyashita, T. and Shimura, T. (2022). Parameterization of mangrove root structure of *Rhizophora stylosa* in coastal hydrodynamic model. *Frontiers in Built Environment*, 7, 782219. [doi:10.3389/fbuil.2021.782219](https://doi.org/10.3389/fbuil.2021.782219)
