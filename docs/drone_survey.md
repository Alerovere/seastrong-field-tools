# Drone Survey

## Overview

Drone imagery gives high-resolution maps of reef flats, seagrass beds and mangrove canopy, between the scale of the transects and that of the satellite images. From the photos, an **orthomosaic** (a georeferenced image of the whole area) and a **surface model** are produced. They are used to map habitats in detail, to link the transects to the satellite maps, and, in mangroves, to describe the canopy and the exposed intertidal areas.

Any consumer drone with a good camera can be used. Positions come from the **drone's own GNSS** (no RTK): the absolute position of the maps is accurate to a few metres, which is enough to compare them with satellite images and with the field data collected with handheld GNSS.

```{figure} _static/drone_survey_flight.svg
:alt: Parallel drone flight lines over a corridor with ground targets, photo overlap in side view, and low versus high sun angle
:width: 100%

**A** Parallel flight lines over the corridor, with take-off point and ground targets. **B** Altitude and overlap of consecutive photos. **C** Low sun reflects away from the camera; at midday the sun glint falls in the photos.
```

---

## Before flying

- **Rules and permits:** follow the national drone regulations of the study area and the conditions of the research permit (protected areas, wildlife, distance from people and villages). The pilot must have the qualifications required locally.
- **Safety:** fly within visual line of sight, with an observer; check batteries, propellers and the home point before each flight; do not fly in strong wind or rain.
- **Area:** plan the flight area to cover the corridor section of interest, including the transects of the corridor.

---

## Flight planning

| Parameter | Guidance |
| --- | --- |
| Altitude | Typically 60–100 m above take-off: a lower altitude gives finer detail but more photos and battery |
| Overlap | At least 75% along track and 70% across track; over water use **at least 80% / 80%**, because the image matching is harder on water |
| Camera | Pointing straight down (nadir); exposure and white balance fixed if the drone allows it |
| Flight lines | Parallel lines, planned with the drone's mission app |

---

## When to fly

- **Low tide**, so that reef flats, seagrass and the mangrove fringe are as shallow or as exposed as possible.
- **Low sun** (early morning, or late afternoon), to avoid **sun glint** on the water surface. Avoid flying around midday in clear sky.
- **Calm water and little wind**: ripples and waves blur the bottom and make the mosaic fail over water.
- **Uniform light**: a thin, even overcast is good; avoid scattered clouds that cast moving shadows.

---

## Ground control (without RTK)

Without RTK, the maps are positioned by the drone's GNSS. To check and improve the alignment with the other datasets:

- where there is dry land or emergent reef, place **4–5 visible targets** (e.g. large printed boards) spread across the area, and record their position with a handheld GNSS (averaging the position for a minute);
- otherwise, the orthomosaic can be aligned in processing to recognisable features in the satellite images.

---

## Field record

For each flight, note: survey ID (e.g. `BZ150327C1drone`), date, start and end time, tide, weather and wind, altitude, overlap, number of photos, and positions of the ground targets. Name the photo folders with the survey ID (see [Field resources](field_resources.md#naming-rules)).

---

## Why we do this in SEASTRONG

In **WP1, Task 1.2**, drone imagery is used together with the bottom photos and the bathymetry to map the extent and condition of the habitats within each corridor, and to link the field transects to the corridor-scale satellite maps.
