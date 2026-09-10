# SEASTRONG field tools -- GUI apps

This folder holds standalone, Dockerized GUI tools that replace the older
Colab-notebook workflow for individual pieces of field-data processing. It's
meant to grow: each tool lives in its own subfolder here, is independently
buildable/runnable, and shares a common look via `_shared/`.

## Layout

```
apps/
  _shared/                 # imported by every tool -- branding, theme
    branding.py
    streamlit_theme.toml
  echosounder_bathymetry/  # first tool -- see its own README.md
    app.py
    core/
    Dockerfile
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
   matches the others without re-implementing any of it.
3. Write a `Dockerfile` that copies both `_shared/` and the tool's own folder
   into the image (build context is `apps/`, not the tool's own folder --
   see the echosounder_bathymetry Dockerfile for the exact pattern) and runs
   `streamlit run app.py`.
4. Add a short `README.md` in the tool's folder: what it does, how to build
   and run it, what inputs it expects.

## Running a tool

Each tool is self-contained. From the repo root:

```
docker build -f apps/echosounder_bathymetry/Dockerfile -t seastrong-echosounder apps/
docker run --rm -p 8501:8501 seastrong-echosounder
```

Then open http://localhost:8501 in a browser. See each tool's own README for
tool-specific run instructions (e.g. mounting a large local dataset as a
volume rather than uploading it through the browser).

## Design principles carried across every tool

- **Point at large data, don't upload it through the browser.** Small
  inputs (a scan CSV, a tide-gauge CSV) use a normal file-upload widget.
  Anything large (a folder of raw sensor data, a global tide model) is
  referenced by a local path and mounted into the container as a volume
  instead.
- **`core/` has no UI dependency.** The processing functions take plain
  Python/pandas objects in and out, so they're unit-testable and reusable
  from a notebook, independent of Streamlit.
- **One Docker image per tool**, not one monolith app. This keeps adding
  tool #6 as simple as adding tool #2 was, and means one tool's dependencies
  (e.g. this tool's `pyTMD` for FES2022 tide prediction) never bloat another
  tool's image.
