# Wave Attenuation Monitoring

## Overview

This page covers the field method used in SEASTRONG to measure **wave attenuation** across mangrove, seagrass, and coral reef transects: what's deployed, why, and how the sensors are calibrated and validated in the field. The data-processing notebooks (pressure calibration, OCEANLYZ wave-parameter extraction) live in `Wave_data_processing/` and will get their own docs page next.

**Sensors used in this project:** Seametrics **PT2X** and Driesen + Kern **P-Log3020-PA-INT-150** submersible pressure loggers.

---

## Why we measure wave attenuation in SEASTRONG

In **WP1 — Task 1.2**, wave attenuation is measured across each cross-shelf corridor (mangrove → seagrass → coral, six corridors minimum per region) as one of the physical-environment datasets characterizing the corridor, alongside bathymetry and water movement.

In **WP4 — Task 4.5 (D4.5)**, the same data is used to calibrate the hydrodynamic model: a 1D XBeach model is inverted per transect against the observed wave-height decay (combined with structural/photogrammetry metrics) to fit a per-habitat drag/roughness coefficient. Those coefficients then feed the 2D production runs used to map wave dissipation and water movement across each corridor under different tide and storm scenarios. In short — this field data is what turns a generic hydrodynamic model into one that reflects the specific mangrove, seagrass, and coral structure being measured.

---

## Field design

| Parameter | Value |
|---|---|
| Transect length | 30 m per ecosystem, per corridor, cross-shore, 0 m at the seaward sensor (see [Field transects](field_transects.md)) |
| Sensors per transect | 2 (seaward end + landward end) |
| What that gives you | Bulk incoming vs. outgoing significant wave height (Hs-in vs. Hs-out) across the segment — enough to fit one lumped roughness/drag coefficient per habitat, not to resolve the full decay curve along the transect |
| Deployments per ecosystem, per corridor | 2–3, roughly 2 days each |
| Why 2-day deployments | Long enough to span multiple full tidal cycles (flood/ebb/slack) within a single deployment — the repeat deployments are mainly there to sample different weather/swell windows during the field trip, not to add tidal coverage |
| Sensor inventory | 10 pressure sensors → up to 5 transects can run in parallel |
| Paired data | Habitat structure and bed profile at each transect, to parameterize habitat-specific drag alongside the wave data: photogrammetry on reefs, quadrats on seagrass, photogrammetry or tree measurements in mangroves (see [Field transects](field_transects.md)) |

Corridors are chosen to be as structurally homogeneous as possible, to reduce confounding in the per-corridor roughness estimate. If the full deployment count can't be reached everywhere, a smaller set of corridors (spanning the structural/exposure gradient) gets the complete protocol as a calibration set, and the rest are predicted from the fitted structure-to-roughness relationship plus literature values — see the project's Task 1.2 decision log for the full fallback design.

---

## Instruments

Both sensors are **submersible absolute-pressure loggers**: they record total pressure (water column + atmosphere), not water depth directly, which is why barometric compensation (below) is essential for both.

| | Seametrics PT2X | Driesen + Kern P-Log3020-PA-INT-150 |
|---|---|---|
| Measurement principle | Absolute pressure + temperature, integrated logger | Absolute pressure (PA / no vent tube) + temperature, integrated logger |
| Range (this deployment) | 30 psia (≈ 21 m water column) | ~150 mbar (≈ 1.5 m water column) — a low-range variant suited to shallow, near-surface wave measurement; confirm against the unit's own calibration certificate rather than a generic datasheet, since D+K offers this sensor across several range options |
| Stated accuracy | ±0.05% FSO typical, ±0.1% FSO maximum (static) | Better than 0.05% FSO |
| Resolution | 0.0034% FS | < 1 mm (better than 0.01%) |
| Sampling rate | Up to 8 Hz | 1 s–24 h adjustable; FastMode 2–32 Hz |
| Memory | 520,000 records | ~4,000,000 readings |
| Battery life | ~18 months at 15-min polling | ~4 years at 1-min intervals |
| Temperature sensor | ±0.5 °C (0–55 °C) | ±0.2 °C, −20 to 60 °C |
| Interface | Modbus RTU (RS485) / SDI-12 | USB |
| Housing | Acetal/Viton, 316SS, or titanium body; IP68 | Stainless steel, seawater-resistant |

Because the two ranges differ by more than an order of magnitude, the PT2X (wider range) is better suited to deeper/tidal-range deployments and the P-Log3020 (narrow, high-resolution range) to shallow, near-surface wave capture — plan sensor placement per transect accordingly rather than treating the two models as interchangeable.

**A caution when mixing brands on the same transect:** a *gain* (slope) mismatch between the two sensor models would scale the oscillatory wave signal itself and bias the Hs-out/Hs-in ratio — unlike a constant offset, which mostly cancels out of a variance-based wave calculation. A single-point bucket comparison can really only catch offset-type errors, not confirm the two brands' gains agree. Before trusting attenuation ratios from a mixed-brand transect, run a short side-by-side burst in *real* moving water (not a static bucket) and compare the derived Hs from both sensors.

---

## Calibration and field validation

Pressure loggers drift for two largely independent reasons — a slowly-drifting **barometric zero** (weather-driven, re-occurs on a timescale of weeks) and the underlying **sensor gain/calibration** (stable over a campaign, but degrades over years without a real multi-point calibration). A bucket comparison of a long-unrecalibrated PT2X against a freshly factory-calibrated unit found a ~3–4 cm bias, of which the barometric zero drift alone accounted for essentially all of it (the onboard field-cal zero was three weeks stale against the true atmospheric pressure on test day). That's a structural problem, not something you can fix by re-zeroing before every deployment — so the workflow below treats each error source separately.

### 1. Pre-trip: traceable calibration + pool verification

Obtain a multi-point, traceable calibration (a real certificate with measured points, not just a certificate of conformance) for each sensor before the trip, spanning its field working range. Then, for **all** sensors regardless of brand, run an in-house pool *verification* against that certificate: 3–4 known depths across the working range, a couple of minutes of stationary dwell at each, with water temperature logged so the reference pressure can be computed precisely. This step confirms the calibration still holds close to deployment time — it doesn't replace the certificate.

Keep a per-sensor (per serial number) record of both the calibration certificate and the verification results, dated.

### 2. Per field leg: a continuous barometric reference

Deploy one sensor permanently in air (shaded, above the high-tide line, same site) logging continuously for the whole field leg, so every submerged sensor's record can be barometrically compensated in post-processing against the *actual* concurrent atmospheric pressure — not a weeks-old onboard zero. This is the single highest-leverage step, since it directly removes the dominant error source found above, and it means individual sensors never need re-zeroing between deployments.

Atmospheric pressure is a slow signal: 1 sample/hour (as a short averaged burst, not one instantaneous reading) is standard practice for barometric loggers and resolves normal weather passages comfortably. Tighten the interval (every 15–30 min) around a forecast storm. One barometric reference per corridor/region is enough — atmospheric pressure is coherent over tens of km within a single weather system.

### 3. Bracket each field leg with a short side-by-side dip test

Before splitting sensors out across transects, and again after retrieval, put all of them in a bucket together for 15–20 minutes. This is QA, not full recalibration: with barometric compensation already handling the dominant drift, this check should catch genuine sensor failures or measure a small, consistent sensor-to-sensor offset — not chase weather.

### 4. Per deployment: log site water properties

Record water temperature (and salinity/conductivity where feasible) per transect, per deployment, so the pressure-to-depth conversion uses the correct density for that ecosystem (mangrove/estuarine brackish water vs. open reef seawater) instead of one fixed constant — a freshwater-vs-seawater density mismatch alone is on the order of ~2.7%, comparable in size to the barometric error above.

### 5. Discard the thermal settling period

Trim the first ~10 minutes of each deployment record — sensors take roughly 7–8 minutes to thermally settle after handling, which is short relative to a 2-day deployment but long enough to bias the start of a burst if left in.

---

## From pressure to wave height, briefly

Wave attenuation (Hs-in vs. Hs-out) is computed from the *oscillatory* part of the pressure signal (its variance/spectral energy), using linear wave theory to correct for the exponential decay of pressure with depth (the pressure-to-surface-elevation transfer function) and recover surface wave height from a sensor sitting on or near the bed. A few things follow directly from that:

- A slowly-varying or constant **offset** (like residual barometric drift) mostly cancels out of the variance calculation — attenuation results are fairly forgiving of small calibration offsets.
- The **burst-mean water depth**, however, is not forgiving: it directly drives the depth-attenuation correction, so it needs the barometrically-compensated, site-density-corrected depth per burst, per sensor — not a shared constant. This is exactly the number that can be off by several centimeters if the barometric compensation above isn't applied.
- The pressure-attenuation correction amplifies noise at high frequencies (large *kh*), so the processing cutoff should be set conservatively rather than trusting the correction all the way to the sensor's noise floor.
- Sensor height above the bed is per-deployment field metadata, logged at each transect rather than assumed fixed.

Full processing detail (OCEANLYZ setup, the calibration pipeline implementation) lives in the `Wave_data_processing/` notebooks and will be documented on its own page.

---

## References

- Seametrics PT2X Smart Sensor specification sheet — [seametrics.com/product/pt2x](https://www.seametrics.com/product/pt2x/)
- Driesen + Kern P-Log3020-PA absolute-pressure water level logger — [driesen-kern.com](https://www.driesen-kern.com/products/water-analysis/water-level/water-level-logger-plog3020.php) / [driesen-kern.de](https://www.driesen-kern.de/produkte/wasserseiten/pegel/p-log3020-pa-absolutdrucklogger.php)
