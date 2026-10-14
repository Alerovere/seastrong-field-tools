# Wave Attenuation: Sensor Deployment

## Overview

Wave attenuation is measured with **seven pressure sensors per corridor**, on the same transects used for the habitat structure surveys (see [Field transects](field_transects.md)):

| Habitat | Sensors | Position |
| --- | --- | --- |
| Outer reef | 2 (PT2X) | Ends of the reef transect: 0 m (seaward) and 30 m |
| Back reef | 1 (PT2X) | Behind the reef crest (post-crest) |
| Seagrass | 2 (Driesen + Kern) | Ends of the seagrass transect: 0 m and 30 m |
| Mangrove | 2 (Driesen + Kern) | Ends of the mangrove transect: 0 m and 30 m |

The difference in wave height between the two sensors of a transect gives the attenuation across that habitat; the post-crest sensor adds the wave height after breaking on the reef crest.

```{figure} _static/wave_sensor_placement.svg
:alt: Cross-section of a corridor with seven pressure sensors on outer reef, back reef, seagrass and mangrove, and how they are fixed in each habitat
:width: 100%

**A** Position of the seven sensors across the corridor: two on an almost planar part of the outer reef (reef transect), one on the back reef behind the crest, two at the ends of the seagrass transect and two at the ends of the mangrove transect. **B** How the sensors are fixed in each habitat.
```

This page explains **where to place the sensors, how to fix them to the bottom, and when to download them**. Calibration and the barometric reference are on the [Pressure sensor calibration](pressure_sensor_calibration.md) page.

---

## Sensors

| | Seametrics PT2X | Driesen + Kern P-Log3020 |
| --- | --- | --- |
| Used on | **Outer reef** and **back reef** (3 per corridor) | **Seagrass** and **mangrove** (4 per corridor) |
| Maximum depth | ~10 m | ~5 m |
| Download every | **2 days** | **4 days** |
| Sampling | Continuous, 4 Hz | Continuous, 4 Hz |

The sensors of a transect are always **the same model**. The PT2X records deeper and goes on the reef, offshore; the Driesen + Kern sensors go in the shallower seagrass and mangrove transects.

---

## Where to place the sensors

- **Transect sensors:** sensor 1 at the **0 m** mark (seaward) and sensor 2 at the **30 m** mark (landward) of the transect tape, on the outer reef, seagrass and mangrove transects. On the outer reef, choose an **almost planar** stretch of reef where possible (not a steep slope or the face of the crest), so that the change in wave height comes from the reef roughness and not from shoaling.
- **Post-crest sensor:** on the back reef, a short distance behind the reef crest, where the waves have broken; note its distance from the crest and a GPS point.
- Check that the **depth at low tide** is within the range of the sensor (10 m for PT2X, 5 m for Driesen + Kern), and that it stays **submerged for as much of the tide as possible**. In mangroves the sensors dry out at low tide: they record only when covered, which is expected.
- Choose a spot that is **representative of the habitat** at that end of the transect, not a hole, a channel or the top of a coral head.
- Keep the **pressure port free**: not buried in sand or mud, not covered by leaves or seagrass blades.
- Put both sensors at about the **same height above the bottom**, as low as possible (a few cm), and measure it.

---

## How to fix the sensors

The sensor must not move during the whole deployment: any movement shows up as a change of depth in the record.

| Habitat | Fixing | Notes |
| --- | --- | --- |
| Coral reef | **Concrete block**, or attached **directly to the substrate** (dead coral, rock) with cable ties | Never tie to live coral. Place the block on sand or rubble |
| Seagrass | **Stake** driven into the sediment, or a **rounded weight** on the bottom | Stake where currents or waves are strong; weight in sheltered sites. Do not crush the shoots more than needed |
| Mangrove | **Cable ties on roots** (prop roots or a firm stem) | Choose a root that does not move with waves; keep the sensor close to the ground |

In all cases:

- Use at least **two cable ties** (or a hose clamp), tight, so that the sensor cannot rotate or slide.
- Do not cover the pressure port with the ties.
- Take a **photo of the mounted sensor** with a scale (e.g. the tape), and note the **height of the pressure port above the bottom**.
- Mark the position (GPS point and distance on the tape) so the sensor can be found again, but avoid large buoys that attract attention.

---

## Deployment and download schedule

| Step | What to do |
| --- | --- |
| Before the trip | Set the clocks of all sensors to **UTC**, set continuous logging at 4 Hz, and do the checks on the [calibration page](pressure_sensor_calibration.md) |
| Barometric reference | Start the barometric logger in air at the base, before the first deployment, and leave it running for the whole field trip |
| Deploy | Start logging, fix the sensors, note the time and the depth at each sensor |
| Download | **PT2X after 2 days, Driesen + Kern after 4 days**: retrieve, download the data, check the record, recharge or change batteries if needed |
| Redeploy | On the same transect (to sample another weather window) or on the next one |

Each corridor should get **2–3 deployments** during the field trip, so that different wave conditions are recorded. With 10 sensors, one corridor (7 sensors) can be instrumented at a time, with 3 spares.

---

## Field form and post-site report

One form per **corridor and deployment** (all 7 sensors), with survey ID made of area + deployment date + corridor + `waves` (e.g. `BZ140327C1waves`, see [Field resources](field_resources.md#naming-rules)): {download}`Wave sensor field form, v1.0 (PDF) <_static/forms/wave_sensor_field_form_v1.0.pdf>`.

- **Page 1, deployment:** for each sensor, the serial number, start time (UTC), depth at the sensor and the time it was measured, height of the pressure port above the bottom, fixing method, photo number of the mounted sensor, and water temperature (and salinity where possible).
- **Page 2, retrieval:** for each sensor, the retrieval date and end time, depth and time, data file name, and whether the sensor was found in place.
- **Page 3, post-site report:** data downloaded, barometric record, data link, quality checks and notes.

Data files are named with the survey ID, the habitat and the position (`S1`, `S2` or `PC` for post-crest), e.g. `BZ140327C1waves_reef_S1`.

Fill it in with **Adobe Acrobat Reader** (free, [download it here](https://get.adobe.com/reader/)), so that the survey ID is filled in automatically and the form is saved correctly.

---

## Why we do this in SEASTRONG

In **WP1, Task 1.2**, wave attenuation is measured across each corridor (mangrove, seagrass, coral reef) as one of the physical-environment datasets. In **WP4, Task 4.5**, the same data are used to calibrate the XBeach model: for each transect, a drag coefficient for the habitat is fitted to the observed decrease in wave height, together with the habitat structure measured on the same transect.
