# Earth Engine scripts

| Script | What it does |
| --- | --- |
| `seastrong_sdb_inputs.js` | Sentinel-2 composite for satellite-derived bathymetry (Bathymetrix-AI), Copernicus DEM / FABDEM / DeltaDTM, habitat layers (Allen Coral Atlas, Global Mangrove Watch), land and mangrove polygons for the ICESat-2 tool. One script; products switched on in `RUN`. |

Open the [Earth Engine Code Editor](https://code.earthengine.google.com), create a new script, paste the file and
follow the instructions in its header. The whole workflow (with the Colab tools) is described in the documentation:
[Satellite-derived bathymetry workflow](https://seastrong-field-tools.readthedocs.io/en/latest/sdb_workflow.html).

`previous_versions/` keeps the three separate scripts (`composite.js`, `EarthDEM.js`, `Habitats.js`) that this
script replaces (2026-11-05).
