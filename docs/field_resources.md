# Field Resources

Forms, naming rules and equipment lists shared by all SEASTRONG field surveys.

---

## Field forms

One fillable form per survey, with the field data sheets and the post-site report. Print the field pages on waterproof paper (or copy them onto the slate), then type the data and the report into the same PDF the same day.

| Survey | Form |
| --- | --- |
| Depth and bottom photos | {download}`Depth and bottom photos field form, v1.1 <_static/forms/depth_photos_field_form_v1.1.pdf>` |
| Drone survey | {download}`Drone field form, v1.0 <_static/forms/drone_field_form_v1.0.pdf>` |
| Reef photogrammetry | {download}`Reef photogrammetry field form, v1.0 <_static/forms/reef_photogrammetry_field_form_v1.0.pdf>` |
| Mangrove structure and topography | {download}`Mangrove field form, v1.0 <_static/forms/mangrove_field_form_v1.0.pdf>` |
| Seagrass structure and bathymetry | {download}`Seagrass field form, v1.0 <_static/forms/seagrass_field_form_v1.0.pdf>` |

**Fill the forms in with Adobe Acrobat Reader** (free, [download it here](https://get.adobe.com/reader/)). In Acrobat Reader the survey ID is filled in automatically from study area, date and corridor, and appears on every page, and the form fields are saved correctly. Other viewers (Mac Preview, browsers, phone apps) may not fill in the ID or may not save the fields.

Save each filled form with the data, named `<surveyID>_field_form.pdf`.

---

## Naming rules

### Survey IDs

Every survey has an ID made of **area + date (DDMMYY) + corridor + survey type**:

| Part | Values |
| --- | --- |
| Area | `BZ` (Belize), `SC` (Seychelles), `FJ` (Fiji) |
| Date | Day, month, year of the survey: `140327` = 14 March 2027 |
| Corridor | `C1` to `C6` |
| Survey type | Transects: `reef`, `seagrass`, `mangrove`. Corridor mapping: `bathy` (depth and bottom photos), `drone` |

Examples: `BZ140327C1reef`, `BZ150327C1seagrass`, `BZ160327C1mangrove`, `BZ140327C1bathy`, `BZ150327C1drone`. If two surveys of the same type are done in the same corridor on the same day, add a letter: `BZ140327C1bathyB`.

### Files and folders

Start every file and folder name with the survey ID, then the item: `<surveyID>_<item>`. For example: `FJ020627C1reef_camA/`, `BZ150327C3seagrass_Q05_photo2.jpg`, `BZ140327C1bathy_scan.csv`, `BZ140327C1bathy.gpx`, `BZ140327C1reef_field_form.pdf`.

### Dates and times

- In forms and field sheets, dates are written as **mm/dd/yyyy**; in the survey ID the date is **DDMMYY**.
- Note the **time zone** of the watch or phone used for the times written in the field.
