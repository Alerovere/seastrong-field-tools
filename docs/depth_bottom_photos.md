# Depth and Bottom Photos

## Overview

Depth points and bottom photos are collected **in the same operation**, by one snorkeller pushing a kickboard that carries an echosounder and a downward-looking camera. The method is low-cost and quick to deploy. It is not a high-resolution survey: its purpose is to collect many georeferenced depth points and bottom photos across the shallow habitats of a corridor, to calibrate and validate the satellite maps (see [Corridor mapping](corridor_mapping.md)).

**Video tutorial:** [Watch on YouTube](https://youtu.be/1o9oEFoXRG4?si=4JF5xB074aj_Nsrq)

The data are processed with two tools: [Echosounder bathymetry](echosounder_bathymetry.md) (depth points) and [Photo geotagging](photo_geotagging.md) (bottom photos).

---

## Equipment

- **Deeper Pro echosounder**: a consumer-grade sonar that records depth and GPS position, connected by Wi-Fi to a smartphone.
- **Smartphone** with the Deeper app, in a waterproof case.
- **Action camera** (e.g. GoPro) in a waterproof housing.
- **Swimming kickboard** used as a floating platform: the echosounder and the camera are mounted on the underside, facing down; the smartphone sits on top.
- Mask, snorkel and fins; a buoy and surface support for longer tracks.

---

## Set-up

1. Mount the echosounder under the kickboard, facing down, so that it is always under water when the board floats.
2. Mount the camera under the kickboard next to it, pointing **straight down** at the bottom.
3. Set the camera to **timelapse photo** mode with a short interval (e.g. 1 s), linear lens, and fixed white balance where possible (see the camera settings on the [Underwater photogrammetry](underwater_photogrammetry.md#camera-settings) page).
4. Connect the Deeper app to the echosounder and check that the GPS position is fixed before starting.

---

## Field procedure

1. **Survey ID:** note the survey ID (e.g. `BZ140327C1bathy`), the date, the operator and the time zone of the phone.
2. **Start recording:** start the scan in the Deeper app (with GPS on), then start the camera.
3. **Reference photo:** at the start, hold the **phone screen showing the GPS time** under the camera and let it take a photo. The camera and the phone have independent clocks: this photo is used in processing to compute the time offset between them. Take a second reference photo at the end of the survey as a check.
4. **Swim the tracks** planned for the corridor (see [Planning a corridor](corridor_mapping.md#planning-a-corridor)), pushing the board slowly and steadily, keeping it flat and the camera pointing down.
5. **Note the start and end time** of each track, and any interruption.
6. **At the end:** stop the camera and the scan, take the second reference photo, and check that the scan contains GPS positions.
7. **Export** the scan from the Deeper app (CSV) and the GPS track (GPX), and download the photos. Name all files with the survey ID (see [Field resources](field_resources.md#naming-rules)).

---

## Conditions

- **Depth points** can be collected at any tide stage: they are corrected for the tide in processing. Record the times.
- **Bottom photos** need clear water and calm conditions; avoid strong waves and very turbid water. Strong caustics make the photos harder to interpret.
- Work in a pair, with surface support for tracks far from shore, and follow the [safety rules](field_transects.md#safety-and-care-of-the-habitat).

---

## Field form and post-site report

The set-up checklist, the reference-photo times, the track sheet and the post-site report are in one form: {download}`Depth and bottom photos field form, v1.0 (PDF) <_static/forms/depth_photos_field_form_v1.0.pdf>`.

- **In the field:** print pages 1–2, or copy them onto the slate.
- **After the survey:** type the data and the post-site report (page 3) into the same PDF, the same day.
- **Fill it in with Adobe Acrobat Reader** (free, [download it here](https://get.adobe.com/reader/)): the **Survey ID** is then filled in automatically from study area, date and corridor, and the form fields are saved correctly.
- Save the filled form with the data, named `<surveyID>_field_form.pdf`, and put the data download link in section B of the report.
