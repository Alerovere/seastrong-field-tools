# Pressure Sensor Calibration

## Overview

This page describes how the pressure sensors used for [wave attenuation](wave_attenuation.md) are calibrated and checked, before and during the field trip. Deployment in the field (where, how and when) is on the [wave attenuation](wave_attenuation.md) page.

Both sensor models are **absolute-pressure loggers**: they record total pressure (water + atmosphere), not water depth. The atmospheric pressure must therefore be subtracted using a **barometric reference** logged during the whole field trip.

---

## Instruments

| | Seametrics PT2X | Driesen + Kern P-Log3020-PA |
| --- | --- | --- |
| Measurement | Absolute pressure + temperature | Absolute pressure + temperature |
| Stated accuracy | ±0.05% FSO typical, ±0.1% FSO maximum (static) | Better than 0.05% FSO |
| Resolution | 0.0034% FS | < 1 mm (better than 0.01%) |
| Sampling rate | Up to 8 Hz | 1 s–24 h; FastMode 2–32 Hz |
| Memory | 520,000 records | ~4,000,000 readings |
| Temperature sensor | ±0.5 °C (0–55 °C) | ±0.2 °C (−20 to 60 °C) |
| Interface | Modbus RTU (RS485) / SDI-12 | USB |

Check the range of each unit on its own calibration certificate.

---

## Why calibration matters

Pressure loggers drift for two mostly independent reasons:

- the **barometric zero**, which changes with the weather over days to weeks;
- the **sensor gain** (calibration slope), which is stable over a campaign but degrades over years.

A bucket comparison of a PT2X not recalibrated for a long time against a freshly calibrated unit found a bias of ~3–4 cm, almost all due to a barometric zero that was three weeks old. This cannot be fixed by re-zeroing before every deployment, so the steps below treat each error source separately.

---

## 1. Before the trip: calibration and pool check

- Obtain a **multi-point, traceable calibration** (a certificate with measured points, not only a certificate of conformance) for each sensor, covering its field working range.
- For **all** sensors, run a **pool check** against that certificate: 3–4 known depths across the working range, a couple of minutes at each, with water temperature logged.
- Keep a record per sensor (serial number) of the certificate and the pool check results, with dates.

---

## 2. During the trip: barometric reference

Keep **one barometric logger in air** (shaded, above high tide, at the base or near the sites) logging **continuously for the whole field trip**. Every sensor record is then corrected in processing with the atmospheric pressure measured at the same time, and the sensors never need re-zeroing between deployments.

- **Sampling:** atmospheric pressure changes slowly; one averaged reading per hour is enough, every 15–30 min around a forecast storm.
- **One reference per study area** is enough: atmospheric pressure is uniform over tens of km in the same weather system.

---

## 3. At the start and end of the trip: side-by-side check

Before the sensors are split among the transects, and again after the last retrieval, put **all sensors together in a bucket for 15–20 minutes**. This is a check, not a calibration: it finds failed sensors and measures any small, constant offset between sensors.

---

## 4. At every deployment: water properties

Record **water temperature** (and salinity where possible) at each transect, at each deployment. The conversion from pressure to depth uses the water density, which differs between brackish mangrove water and open seawater: using fresh-water density in seawater alone gives an error of ~2.7%.

---

## 5. In processing: settling time

Remove the first **~10 minutes** of each record: sensors take 7–8 minutes to reach the water temperature after handling.

---

## Notes for wave processing

Wave height is computed from the **oscillating part** of the pressure signal, corrected with linear wave theory for the decrease of the pressure signal with depth.

- A constant or slowly changing **offset** (such as residual barometric drift) mostly cancels out of the wave height.
- The **mean water depth** of each burst does not cancel: it drives the depth correction, so it must be computed per burst and per sensor, with barometric compensation and site water density.
- The depth correction amplifies noise at high frequencies: set the frequency cutoff conservatively.
- The **height of the sensor above the bottom** is recorded at each deployment, not assumed.
- The two sensors of a transect are the same model. If two different models are ever used on one transect, a difference in **gain** would bias the wave-height ratio: compare them first side by side in moving water, not in a static bucket.

The processing notebooks are in `Wave_data_processing/` and will be documented on a separate page.

---

## References

- Seametrics PT2X Smart Sensor specification sheet: [seametrics.com/product/pt2x](https://www.seametrics.com/product/pt2x/)
- Driesen + Kern P-Log3020-PA absolute-pressure water level logger: [driesen-kern.com](https://www.driesen-kern.com/products/water-analysis/water-level/water-level-logger-plog3020.php)
