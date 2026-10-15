# Drone Survey

## Overview

The drone is used in two ways, which can be combined in the same survey:

| | 1. Mapping flight | 2. Spot photos |
| --- | --- | --- |
| What | **Continuous photos** along parallel flight lines, with large overlap | **Single geotagged photos** taken while hovering over chosen points |
| Product | **Orthomosaic**: one georeferenced image of the whole area | A set of photos, each showing **what is on the bottom (or the ground) at a known point** |
| Used for | Detailed habitat maps of reef flats, seagrass and mangrove fringe; link between the transects and the satellite maps | Ground truth for the habitat maps, at points that are hard to reach by swimming or where the satellite classes are uncertain |

Only the orthomosaic is produced from the mapping flight; no elevation model is made, so **no ground control points are needed**. Any consumer drone with a good camera can be used. Positions come from the **drone's own GNSS** (no RTK), accurate to a few metres, which is enough to compare the products with the satellite images and with the field data.

```{figure} _static/drone_survey_flight_v2.svg
:alt: Mapping flight lines and spot photo points over a corridor, photo overlap of the mapping flight in side view, and low versus high sun angle
:width: 100%

**A** 1) Mapping flight along parallel lines, for the orthomosaic; 2) spot photos taken while hovering over chosen points. **B** Altitude and overlap of consecutive photos in the mapping flight. **C** Low sun reflects away from the camera; at midday the sun glint falls in the photos.
```

---

## Before flying

- **Rules and permits:** follow the national drone regulations of the study area and the conditions of the research permit (protected areas, wildlife, distance from people and villages). The pilot must have the qualifications required locally.
- **Safety:** fly within visual line of sight, with an observer; check batteries, propellers and the home point before each flight; do not fly in strong wind or rain.
- **Area:** plan the flight area to cover the corridor section of interest, including the transects of the corridor.

---

## Flight planning

### 1. Mapping flight

| Parameter | Guidance |
| --- | --- |
| Altitude | Typically 60–100 m above take-off: a lower altitude gives finer detail but more photos and battery |
| Overlap | At least 75% along track and 70% across track; over water use **at least 80% / 80%**, because the image matching is harder on water |
| Camera | Pointing straight down (nadir); exposure and white balance fixed if the drone allows it |
| Flight lines | Parallel lines, planned with the drone's mission app |

### 2. Spot photos

| Parameter | Guidance |
| --- | --- |
| Points | Chosen before the flight on the satellite image: each habitat type of the corridor, the boundaries between habitats, and areas where the habitat is uncertain |
| Altitude | Low enough to see the bottom in detail, and the same for all points of a survey (e.g. 20–30 m); note it in the field form |
| Camera | Pointing straight down (nadir); one or two photos per point, with GPS position saved in the photo (check that geotagging is on) |
| Flight | Fly to each point, hover until the drone is stable, take the photo; note the point number and photo number |

---

## When to fly

- **Low tide**, so that reef flats, seagrass and the mangrove fringe are as shallow or as exposed as possible.
- **Low sun** (early morning, or late afternoon), to avoid **sun glint** on the water surface. Avoid flying around midday in clear sky.
- **Calm water and little wind**: ripples and waves blur the bottom and make the mosaic fail over water.
- **Uniform light**: a thin, even overcast is good; avoid scattered clouds that cast moving shadows.

---

## Field form and post-site report

One form per survey (one corridor, one day), with the survey ID (e.g. `BZ150327C1drone`), conditions, one row per flight (type, start and end time, altitude, overlap, number of photos), the list of spot photos and the post-site report: {download}`Drone field form, v1.1 (PDF) <_static/forms/drone_field_form_v1.1.pdf>`.

Fill it in with **Adobe Acrobat Reader** (free, [download it here](https://get.adobe.com/reader/)), so that the survey ID is filled in automatically and the form is saved correctly. Name the photo folders with the survey ID (see [Field resources](field_resources.md#naming-rules)).

---

## Why we do this in SEASTRONG

In **WP1, Task 1.2**, drone imagery is used together with the bottom photos and the bathymetry to map the extent and condition of the habitats within each corridor, and to link the field transects to the corridor-scale satellite maps.
