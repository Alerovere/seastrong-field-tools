# Corridor Mapping: Overview

## Overview

In each corridor, SEASTRONG maps **bathymetry** and **habitats** at corridor scale, mainly from satellite imagery: satellite-derived bathymetry (SDB) and habitat classification. These products need **field data for calibration and validation**. This part of the documentation describes how the field data are collected and processed:

| Dataset | Field method | Processing | Used for |
| --- | --- | --- | --- |
| Depth points | [Depth and bottom photos](depth_bottom_photos.md) (echosounder) | [Processing, part 1](depth_photos_processing.md#1-depth-points-tide-correction) | Calibration and validation of satellite-derived bathymetry; bathymetry of the hydrodynamic models |
| Geotagged bottom photos | [Depth and bottom photos](depth_bottom_photos.md) (downward camera) | [Processing, part 2](depth_photos_processing.md#2-bottom-photos-geotagging) | Ground truth for habitat maps; record of habitat condition |
| Drone imagery | [Drone survey](drone_survey.md) | Orthomosaic and surface model | High-resolution habitat maps of reef flats, seagrass and mangroves; link between transects and satellite maps |

The transect surveys (habitat structure and wave attenuation, see [Field transects](field_transects.md)) are a separate operation at a much smaller scale. They are usually done in the same corridors and the same field campaign.

---

## Planning a corridor

- **Cover the whole corridor and the whole depth range.** Satellite-derived bathymetry is calibrated and validated with depth points, so the points must span all depths and all bottom types (sand, seagrass, coral, rubble) present in the corridor, not only the easiest areas.
- **Use several tracks, not one line.** Swim or fly parallel lines across the corridor, from the deepest accessible water to the shore, plus a few lines along the shore at different depths. Points are later split into a calibration and a validation set, so they need to be spread out.
- **Choose the timing for each dataset:**
  - depth points can be collected at any tide, because they are tide-corrected in processing; note the times;
  - bottom photos need clear water and are best in the middle of the day with low waves;
  - drone flights need low tide, calm water and a low sun (see [Drone survey](drone_survey.md)).

---

## Field forms, survey IDs and data

Each survey has its own **field form with a post-site report** (fillable PDF, see [Field resources](field_resources.md#field-forms)). The form is filled in during the survey and completed the same day; it is then **uploaded to the project's data repository together with the data** of that survey, so that every dataset comes with its record of how, when and where it was collected.

Each survey gets an ID made of **area + date (DDMMYY) + corridor + survey type**, with survey type `bathy` for the depth and bottom photos survey and `drone` for the drone survey. For example: `BZ140327C1bathy`, `BZ150327C1drone`. The ID is filled in automatically in the field form, and all files and folders start with it; see [Field resources](field_resources.md#naming-rules).
