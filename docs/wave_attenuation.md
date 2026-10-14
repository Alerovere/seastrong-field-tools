# Wave Attenuation: Sensor Deployment

## Overview

Wave attenuation is measured with **two pressure sensors per transect**: one at the seaward end (0 m, sensor 1) and one at the landward end (30 m, sensor 2), on the same transects used for the habitat structure surveys (see [Field transects](field_transects.md)). The difference in wave height between the two sensors gives the attenuation across the habitat.

This page explains **where to place the sensors, how to fix them to the bottom, and when to download them**. Calibration and the barometric reference are on the [Pressure sensor calibration](pressure_sensor_calibration.md) page.

---

## Sensors

| | Seametrics PT2X | Driesen + Kern P-Log3020 |
| --- | --- | --- |
| Used on | **Reef** transects | **Seagrass** and **mangrove** transects |
| Maximum depth | ~10 m | ~5 m |
| Download every | **2 days** | **4 days** |
| Sampling | Continuous, 4 Hz | Continuous, 4 Hz |

The two sensors of a transect are always **the same model**. The PT2X records deeper and goes on the reefs, offshore; the Driesen + Kern sensors go in the shallower seagrass and mangrove transects.

---

## Where to place the sensors

- **Sensor 1** at the **0 m** mark (seaward) and **sensor 2** at the **30 m** mark (landward) of the transect tape.
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

Each transect should get **2–3 deployments** during the field trip, so that different wave conditions are recorded. Ten sensors allow up to 5 transects to run at the same time.

---

## Field record

For each sensor and each deployment, note:

- transect ID, sensor ID (serial number), position (sensor 1 at 0 m, sensor 2 at 30 m);
- start and end time of the deployment (UTC);
- **depth at the sensor** and the time it was measured, at deployment and at retrieval;
- **height of the pressure port above the bottom**;
- fixing method and photo number of the mounted sensor;
- **water temperature** (and salinity where possible);
- data file name: `<transectID>_S1_<deployment>` (e.g. `BZ140327C1reef_S1_D2`).

---

## Why we do this in SEASTRONG

In **WP1, Task 1.2**, wave attenuation is measured across each corridor (mangrove, seagrass, coral reef) as one of the physical-environment datasets. In **WP4, Task 4.5**, the same data are used to calibrate the XBeach model: for each transect, a drag coefficient for the habitat is fitted to the observed decrease in wave height, together with the habitat structure measured on the same transect.
