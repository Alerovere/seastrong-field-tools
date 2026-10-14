# Field forms

Scripts that generate the printable and fillable PDF field forms published in the docs
(`docs/_static/forms/`).

| Form | Script | Current version |
| --- | --- | --- |
| Reef photogrammetry | `reef_photogrammetry_field_form.py` | v1.0 |

## Updating a form

1. Edit the script and increase `VERSION` (e.g. 1.0 → 1.1) and `VERSION_DATE`.
2. Run it: `python reef_photogrammetry_field_form.py` (requires `reportlab` and `pypdf`).
   The new PDF is written to `docs/_static/forms/` with the version in its name.
3. Delete the previous version of the PDF and update the download links in the docs pages
   (`underwater_photogrammetry.md`, `field_transects.md`).

The version is in the file name so that browsers and the docs site never show a cached
older copy. It is also printed in the footer of every page.
