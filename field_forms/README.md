# Field forms

Scripts that generate the retained printable and fillable field sheets in
`docs/_static/forms/`. Survey records and files are submitted through the
[SEASTRONG Field Data Portal](https://alerovere.github.io/seastrong-field-tools/);
Read the Docs links to the portal rather than to these PDF templates.

| Form | Script | Current version |
| --- | --- | --- |
| Reef photogrammetry | `reef_photogrammetry_field_form.py` | v1.0 |
| Mangrove structure and topography | `mangrove_field_form.py` | v1.0 |
| Seagrass structure and bathymetry | `seagrass_field_form.py` | v1.0 |
| Depth and bottom photos | `depth_photos_field_form.py` | v1.2 |
| Drone survey | `drone_field_form.py` | v1.0 |
| Wave sensors | `wave_sensor_field_form.py` | v1.0 |

## Updating a form

1. Edit the script and increase `VERSION` (e.g. 1.0 → 1.1) and `VERSION_DATE`.
2. Run it, e.g. `python mangrove_field_form.py` (requires `reportlab` and `pypdf`).
   The new PDF is written to `docs/_static/forms/` with the version in its name.
3. Keep existing PDFs until the replacement has been reviewed. If the portal
   should offer the revised printable sheet, update its filename and source version
   in `docs/_static/forms/survey-schema.js`. The protocol pages link to the portal.

The version is in the file name so that browsers and the docs site never show a cached
older copy. It is also printed in the footer of every page.

`formlib.py` holds the building blocks shared by the forms (fields, tables, footer, and the
automatic Transect ID). The reef form script predates it and is self-contained; the other forms
use `formlib.py`.
