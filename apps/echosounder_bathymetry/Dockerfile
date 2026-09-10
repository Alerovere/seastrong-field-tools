# Build from the repo root's apps/ folder (not from this folder alone),
# since this image also needs the shared branding/theme in apps/_shared:
#
#   docker build -f apps/echosounder_bathymetry/Dockerfile -t seastrong-echosounder apps/
#   docker run --rm -p 8501:8501 seastrong-echosounder
#
# To use the FES2022 tide option, mount your local FES2022 data as a volume
# instead of copying it into the image, e.g.:
#
#   docker run --rm -p 8501:8501 -v /path/to/fes2022:/data/fes2022:ro seastrong-echosounder
#
# ...then enter /data/fes2022 as the "FES2022 model folder" in the app.

FROM python:3.11-slim

WORKDIR /app

# build-essential covers the rare case a dependency needs to compile from
# source; most of this stack (pandas/numpy/pyproj/h5netcdf) ships prebuilt
# manylinux wheels so this is mostly a safety net, not a hard requirement.
RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY echosounder_bathymetry/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY _shared ./_shared
COPY echosounder_bathymetry ./echosounder_bathymetry

RUN mkdir -p /app/echosounder_bathymetry/.streamlit \
    && cp /app/_shared/streamlit_theme.toml /app/echosounder_bathymetry/.streamlit/config.toml

WORKDIR /app/echosounder_bathymetry

EXPOSE 8501

HEALTHCHECK CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8501/_stcore/health')" || exit 1

ENTRYPOINT ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0"]
