# Field Resources

Survey submission, naming rules and field preparation shared by all SEASTRONG surveys.

---

## Field forms

Complete survey records and post-site reports in the [SEASTRONG Field Data Portal](https://alerovere.github.io/seastrong-field-tools/). Sign in with your authorised Google account, choose the survey type, enter the observations and attach the original files. The portal saves the record, measurement tables and generated report with the files in the project Shared Drive.

Read the [portal guide](field_portal.md) for access, the four submission steps, drafts and **My records**. All six survey types use the same portal: depth and bottom photos, drone surveys, wave sensors, reef photogrammetry, mangroves and seagrass.

In the field, use slates or waterproof notes and photograph them before wiping them. Transcribe the observations and submit once you are back online, preferably the same day. Prepare the required fields from the relevant survey protocol before leaving.

---

## Naming rules

### Survey IDs

Every survey has an ID made of **area + date (DDMMYY) + corridor + survey type**:

| Part | Values |
| --- | --- |
| Area | `BZ` (Belize), `SC` (Seychelles), `FJ` (Fiji) |
| Date | Day, month, year of the survey: `140327` = 14 March 2027 |
| Corridor | `C1` to `C6` |
| Survey type | Transects: `reef`, `seagrass`, `mangrove`. Corridor mapping: `bathy` (depth and bottom photos), `drone`. Wave sensors: `waves` |

Examples: `BZ140327C1reef`, `BZ150327C1seagrass`, `BZ160327C1mangrove`, `BZ140327C1bathy`, `BZ150327C1drone`, `BZ140327C1waves`. If two surveys of the same type are done in the same corridor on the same day, add a letter: `BZ140327C1bathyB`.

The optional **Corridor name** records a local name such as Mangrove Bay. It is saved with the record without changing the `C1`–`C6` code or the automatic survey ID.

### Files and folders

Start every file and folder name with the survey ID, then the item: `<surveyID>_<item>`. For example: `FJ020627C1reef_camA/`, `BZ150327C3seagrass_Q05_photo2.jpg`, `BZ140327C1bathy_scan.csv`, `BZ140327C1bathy.gpx`, `BZ140327C1reef_field_report.pdf`.

### Dates and times

- Write field dates unambiguously, for example **14 March 2027**. The portal date picker follows the browser locale and saves dates as **YYYY-MM-DD**; the survey ID uses **DDMMYY**.
- Note the **time zone** of the watch or phone used for the times written in the field.
