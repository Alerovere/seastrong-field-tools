# Field forms

Scripts that generate the printable and fillable PDF field forms published in the docs
(`docs/_static/forms/`).

| Form | Script | Current version |
| --- | --- | --- |
| Reef photogrammetry | `reef_photogrammetry_field_form.py` | v1.0 |
| Mangrove structure and topography | `mangrove_field_form.py` | v1.0 |
| Seagrass structure and bathymetry | `seagrass_field_form.py` | v1.0 |
| Depth and bottom photos | `depth_photos_field_form.py` | v1.1 |

## Updating a form

1. Edit the script and increase `VERSION` (e.g. 1.0 → 1.1) and `VERSION_DATE`.
2. Run it, e.g. `python mangrove_field_form.py` (requires `reportlab` and `pypdf`).
   The new PDF is written to `docs/_static/forms/` with the version in its name.
3. Delete the previous version of the PDF and update the download links in the docs pages
   (the habitat page and `field_transects.md`).

The version is in the file name so that browsers and the docs site never show a cached
older copy. It is also printed in the footer of every page.

`formlib.py` holds the building blocks shared by the forms (fields, tables, footer, and the
automatic Transect ID). The reef form script predates it and is self-contained; the other forms
use `formlib.py`.
