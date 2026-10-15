# Depth and Bottom Photos

## Overview

The survey collects two datasets with simple equipment pushed on a kickboard by one snorkeller:

- **depth points**, with an echosounder (Deeper Pro) connected to a smartphone;
- **bottom photos**, with a downward-looking action camera, positioned with the track of a handheld GNSS.

The two can be collected **in the same swim**, with all the equipment on the same kickboard, or **separately**, each with its own equipment. The method is low-cost and quick to deploy. It is not a high-resolution survey: its purpose is to collect many georeferenced depth points and bottom photos across the shallow habitats of a corridor, to calibrate and validate the satellite maps (see [Corridor mapping](corridor_mapping.md)).

The processing of the depth points and the photos is described in [Depth and bottom photos: processing](depth_photos_processing.md).

```{figure} _static/depth_bottom_photos_v2.svg
:alt: Kickboard with echosounder, phone, handheld GNSS and downward camera, survey tracks across a corridor, and the reference photo of the GNSS time
:width: 100%

**A** Side view: the snorkeller pushes the kickboard; the echosounder records depth (with the position from the phone), the camera takes bottom photos (positioned with the GNSS track). **B** Plan view: cross-shore tracks from deep water to the shore, plus a few alongshore tracks at different depths, covering all bottom types. **C** Reference photo of the GNSS time, taken at the start and at the end, to compute the offset between the camera clock and the GNSS.
```

---

## Video tutorial

The whole set-up and procedure are shown step by step in this video:

```{raw} html
<div style="position: relative; padding-bottom: 56.25%; height: 0; overflow: hidden; margin-bottom: 1em;">
  <iframe src="https://www.youtube.com/embed/1o9oEFoXRG4" title="Depth and bottom photos: video tutorial"
          style="position: absolute; top: 0; left: 0; width: 100%; height: 100%; border: 0;"
          allow="accelerometer; clipboard-write; encrypted-media; gyroscope; picture-in-picture" allowfullscreen></iframe>
</div>
```

If the video does not show, [watch it on YouTube](https://youtu.be/1o9oEFoXRG4?si=4JF5xB074aj_Nsrq).

---

## Equipment

| For | Equipment | Notes |
| --- | --- | --- |
| Depth points | **Deeper Pro** echosounder | Consumer-grade sonar, mounted under the kickboard |
| | **Smartphone** with the **Deeper app** installed, in a waterproof case | Connected to the Deeper by Wi-Fi; records the depths with the **phone's GPS position** |
| Bottom photos | **Action camera** (e.g. GoPro) in a waterproof housing | Mounted under the kickboard, pointing down, in timelapse mode |
| | **Handheld GNSS** recording a track, in a waterproof bag | On top of the kickboard, antenna out of the water; its track gives the **position of the photos** |
| Both | **Swimming kickboard** | Floating platform for all the equipment |
| | Mask, snorkel, fins; buoy | Surface support for longer tracks |

The phone and the GNSS do different jobs: the phone gives the positions of the **depths** (through the Deeper app), the GNSS track gives the positions of the **photos**.

---

## Set-up

**Depth points**

1. Install the Deeper app on the phone before the trip.
2. Mount the echosounder under the kickboard, facing down, so that it is always under water when the board floats.
3. Put the phone in its waterproof case on top of the board, connect the Deeper app to the echosounder by Wi-Fi, and check that the phone GPS has a fix.

**Bottom photos**

4. Mount the camera under the kickboard, pointing **straight down** at the bottom.
5. Set the camera to **timelapse photo** mode with a short interval (e.g. 1 s), linear lens, and fixed white balance where possible (see the camera settings on the [Underwater photogrammetry](underwater_photogrammetry.md#camera-settings) page).
6. Set the handheld GNSS to record a **track** with the shortest logging interval (e.g. every 1 s), check that it has a fix, and fix it on top of the board in a waterproof bag, antenna up.

If only one dataset is collected, set up only that part.

---

## Field procedure

1. **Survey ID:** note the survey ID (e.g. `BZ140327C1bathy`), the date, the operator, which datasets are collected, and the time zone of the GNSS and the phone.
2. **Start recording:** start the scan in the Deeper app; start the track on the GNSS; start the camera.
3. **Reference photo:** hold the **GNSS screen showing the time** under the camera and let it take a photo. The camera and the GNSS have independent clocks: this photo is used in processing to compute the offset between them.
4. **Swim the tracks** planned for the corridor (see [Planning a corridor](corridor_mapping.md#planning-a-corridor)), pushing the board slowly and steadily, keeping it flat and the camera pointing down.
5. **Note the start and end time** of the survey, and any interruption.
6. **At the end:** take a second reference photo of the GNSS time, then stop the camera, the GNSS track and the Deeper scan. Check that the scan contains positions.
7. **Export** the scan from the Deeper app (CSV) and the track from the GNSS (GPX), and download the photos. Name all files with the survey ID (see [Field resources](field_resources.md#naming-rules)).

If only one dataset is collected, skip the steps of the other one (no reference photo is needed for depth only).

---

## Conditions

- **Depth points** can be collected at any tide stage: they are corrected for the tide in processing. Record the times.
- **Bottom photos** need clear water and calm conditions; avoid strong waves and very turbid water. Strong caustics make the photos harder to interpret.
- Work in a pair, with surface support for tracks far from shore, and follow the [safety rules](field_transects.md#safety-and-care-of-the-habitat).

---

## Field form and post-site report

The set-up checklist, the reference-photo times, the survey times and the post-site report are in one form: {download}`Depth and bottom photos field form, v1.2 (PDF) <_static/forms/depth_photos_field_form_v1.2.pdf>`.

- **In the field:** print page 1, or copy it onto the slate.
- **After the survey:** type the data and the post-site report (page 2) into the same PDF, the same day.
- **Fill it in with Adobe Acrobat Reader** (free, [download it here](https://get.adobe.com/reader/)): the **Survey ID** is then filled in automatically from study area, date and corridor, and the form fields are saved correctly.
- Save the filled form with the data, named `<surveyID>_field_form.pdf`, and put the data download link in section B of the report.
