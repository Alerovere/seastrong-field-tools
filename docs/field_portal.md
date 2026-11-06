# Field Data Portal

Use the [SEASTRONG Field Data Portal](https://alerovere.github.io/seastrong-field-tools/) to submit survey observations, post-site reports and original files to the project Shared Drive. The same website handles all six survey types and lets you view and revise your submitted records.

**[Open the SEASTRONG Field Data Portal](https://alerovere.github.io/seastrong-field-tools/)**

## Before you start

You need an internet connection, a Google account authorised to add files to the SEASTRONG submission folder, and the observations and files from your survey. Ask the project coordinator to arrange access before your first submission. An institutional email address can be used if it is associated with a Google account.

Record observations on slates or waterproof field notes while away from a connection. Photograph the notes before wiping them, and complete the online submission when you return, preferably the same day. The portal requires a connection for sign-in and uploads.

## Sign in

Open the portal and choose **Sign in with Google**. Use the account authorised for the project. The form opens after the portal checks that the account can add files to the submission folder. If Google asks you to confirm the **Survey submissions** folder, select that folder.

If access is refused, ask the project coordinator to check your account and folder permissions. **Lock portal** returns to the sign-in screen. You will also be asked to sign in again when the Google session expires.

## Submit a survey

### 1. Survey details

Choose the survey type and complete the study area, corridor code, date, clock UTC offset, operators and **Filled in by** fields. Add the optional **Corridor name** when the area has a local name, such as Mangrove Bay.

| Survey protocol | Survey type in the portal |
| --- | --- |
| [Depth and bottom photos](depth_bottom_photos.md) | Depth & bottom photos |
| [Drone survey](drone_survey.md) | Drone survey |
| [Wave attenuation](wave_attenuation.md) | Wave sensors |
| [Underwater photogrammetry](underwater_photogrammetry.md) | Reef photogrammetry |
| [Mangroves](mangroves.md) | Mangrove |
| [Seagrass](seagrass.md) | Seagrass |

The survey ID is generated automatically from the study area, date, corridor code and survey type. For another survey of the same type in the same corridor on the same day, choose the appropriate **Survey occurrence**. The corridor name is saved with the record without changing its ID. See the [naming rules](field_resources.md#naming-rules).

For wave sensors, use the **deployment date** and choose **Deployment**, **Retrieval** or **Post-site report** under **Record stage**. Later retrieval information can be added as a new version of the deployment record through **My records**.

### 2. Measurements

Enter the observations from the field notes, complete the measurement tables and review the field checks and quality flags. For mangroves, choose the structure method to display the appropriate tables. The seagrass form has separate tables for depth and cover, quadrats and shoots.

Leave unavailable measurements blank and explain gaps or deviations in the notes. Record whether the planned field survey was completed. Review the checks and confirm that review before submitting.

For a measurement table, you can download its CSV template and import a completed copy. Import replaces that table after confirmation, so check the headings and survey ID before proceeding.

### 3. Files

Choose a file category, then add files or a folder. Repeat for the other categories. For example, reef camera photos have separate **Camera A photos** and **Camera B photos** categories. Preserve the organisation of camera, quadrat and sensor files when preparing the submission.

Explain any missing or pending file categories. Selecting files does not upload their contents yet.

**Large photo sets: upload ZIP archives.** When a category holds more than 100 separate files, the form suggests
using ZIP archives instead. Photos that are processed as a whole (drone flights, photogrammetry series, long
bottom-photo sequences) are best uploaded as one ZIP per flight, transect or camera:

- name each archive with the survey ID, e.g. `BZ150327C1drone_flight2.zip`;
- create it on a laptop **without compression** ("store"): photos are already compressed, so this is fast and the
  file is barely larger;
- keep each archive under about 20 GB, so an interrupted or damaged upload is quick to repeat.

ZIP archives keep the folder structure and the photo metadata (time, GPS), make interrupted uploads easier to resume
and keep the shared drive manageable (a shared drive holds at most 400,000 items). Keep as individual files the
photos people look at one by one, such as field-sheet and spot photos, which Drive can preview.

Each Google account can upload about 750 GB per day; for very large surveys, upload over two days or from two
accounts, preferably from the institute's network rather than a field connection.

### 4. Review

Check the survey ID, location, measurements, file list and explanations. Confirm the final review, then choose **Submit to Shared Drive**. Keep the page open until **Your survey package is saved** appears.

Use **Open submission folder** to check the result. The package contains:

- the survey record and file manifest;
- CSV measurement tables and links to the original files;
- a generated PDF survey report;
- the original survey files.

The portal organises submissions by study area, corridor and survey ID, with a separate folder for each record version. The saved confirmation means that the upload package was verified; missing field observations remain recorded as missing.

## Satellite-derived datasets

Processed products of the project are submitted with the same form: choose **Satellite-derived dataset** as the
type. They are stored under **<Study area> / Satellite datasets / <dataset ID>** on the shared drive.

| Product | Typical files |
| --- | --- |
| Sentinel-2 composite | 12-band GeoTIFF, QA raster and blue temporal std, date-screening tables, README |
| ICESat-2 depths | ATL24 training / validation / all-flags GeoPackages, hold-out lock file, ATL08, coverage tables |
| SDB bathymetry map | depth map, error rasters, validation tables, Bathymetrix-AI settings |
| Elevation, habitats, wave climate | rasters, polygons, tables and XBeach cases from the Earth Engine script and the Colab tools |

- **Dataset ID**: `<area>-<product>-<processing date>`, e.g. `BZ-S2composite-2026-11-06` (a letter is added for a
  second dataset of the same product on the same day: `BZ-S2composite-2026-11-06B`).
- **Description**: what the dataset covers (area, period, months, projection, resolution, vertical reference), how it
  was made (tool and version, key settings, the inputs used, e.g. other dataset IDs) and its quality (checks, known
  issues). Attach the README written by the tool.
- **Review**: every new dataset, and every new version, starts as **Draft**. In **Satellite datasets** (tab at the
  top) anyone can open a dataset; someone **other than its producer** can mark it **Checked**, and only the dataset
  approver (Alessio Rovere) can mark it **Approved** or set it back to Draft. Each review is saved on the record and as
  a small `_review_…json` file in its folder. Use the approved version for analyses and reports.

```{note}
The review rules are applied by the form. The files themselves are protected by the shared-drive permissions, so
keep editing rights on the shared drive limited to the project team.
```

## View and correct records

Open **My records** after signing in. **View** shows a saved record and its file links. **Edit** loads it into the form; make the corrections and submit to save a new version. The earlier record and original files remain available, and earlier originals are linked without uploading them again. Add only new or replacement files as needed.

Use **Show earlier versions** to inspect the history. The list is associated with the signed-in Google account. Access to files directly in Google Drive continues to follow the project's folder permissions.

For sensor retrieval, edit the saved deployment record, retain its deployment date and survey ID, and update **Record stage** and the retrieval data. For a different location, corridor or survey date, start another survey.

## Drafts and interrupted uploads

**Save draft** keeps the observations and file list in this browser, separately for each Google account. **Download draft** saves a copy that can be imported on another computer. Original file contents are not included in a draft: retain them on your computer until the upload is complete.

If a connection or session ends, sign in again and resume the draft. After reopening the page or moving to another computer, reselect any original files whose uploads have not finished, using the same categories and folder paths. Previously confirmed originals are checked on Drive and do not need uploading again.

An incomplete upload shown in **My records** must be resumed from its original browser draft or an exported draft; it cannot be edited as a completed record.
