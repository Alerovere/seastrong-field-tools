# SEASTRONG field tools -- GUI apps

This folder holds standalone GUI tools that replace the older
Colab-notebook workflow for individual pieces of field-data processing.
It's meant to grow: each tool lives in its own subfolder here, is
independently runnable, and shares a common look via `_shared/`.

Each tool runs natively on the user's machine via a dedicated conda
environment and a double-click launcher -- see `echosounder_bathymetry/`
for the reference implementation. An earlier version of this pattern used
Docker for each tool; that turned out to add more friction than it was
worth for field laptops (volume-mount path confusion, Docker Desktop's
macOS file-sharing/TCC permission quirks, and slower file I/O for
large local datasets like FES2022). Docker isn't ruled out for a future
tool that specifically needs strict environment isolation, but conda + a
launcher script is the default now.

## Layout

```
apps/
  _shared/                 # imported by every tool -- branding, theme, folder_picker
    branding.py
    streamlit_theme.toml
    folder_picker.py
  echosounder_bathymetry/  # first tool -- see its own README.md
    app.py
    core/
    "Launch Echosounder Bathymetry.command"
    requirements.txt
    README.md
  <next_tool>/              # same shape as above
```

## The pattern (for adding a new tool)

1. Create `apps/<tool_name>/` with a `core/` subfolder for the actual
   processing logic (plain Python, no Streamlit imports -- so it stays
   testable and importable from notebooks too) and an `app.py` that's a thin
   Streamlit UI wired to `core/`.
2. Import `_shared.branding` for the page config/header/footer so the tool
   matches the others without re-implementing any of it. Use
   `_shared.folder_picker.pick_folder()` wherever the tool needs the user to
   point at a local folder (a raw dataset, a model directory) instead of
   uploading it through the browser.
3. Add a `requirements.txt` and a double-click `.command` launcher (see
   `echosounder_bathymetry/Launch Echosounder Bathymetry.command`) that
   creates/activates a dedicated conda environment, `pip install`s
   `requirements.txt`, and runs `streamlit run app.py`.
4. Write a short `README.md` in the tool's folder: what it does, how to run
   it, what inputs it expects.

## Running a tool

Each tool is self-contained. From Finder, double-click that tool's
`.command` launcher (macOS will ask for a one-time security approval the
first time -- see the tool's README). From Terminal, the equivalent is:

```
conda create -n <tool-env-name> python=3.11   # first time only
conda activate <tool-env-name>
cd apps/<tool_name>
pip install -r requirements.txt
streamlit run app.py
```

See each tool's own README for tool-specific details (e.g. where to point
it at a large local dataset).

## Design principles carried across every tool

- **Point at large data, don't upload it through the browser.** Small
  inputs (a scan CSV, a tide-gauge CSV) use a normal file-upload widget.
  Anything large (a folder of raw sensor data, a global tide model) is
  referenced by a local path via `_shared.folder_picker.pick_folder()`
  instead of being uploaded.
- **`core/` has no UI dependency.** The processing functions take plain
  Python/pandas objects in and out, so they're unit-testable and reusable
  from a notebook, independent of Streamlit.
- **One conda environment per tool**, not one shared environment. This
  keeps adding tool #6 as simple as adding tool #2 was, and means one
  tool's dependencies (e.g. this tool's `pyTMD` for FES2022 tide
  prediction) never conflict with another tool's.
