# SEASTRONG Field Processing Tools

This repository contains field data processing tools developed within the [SEASTRONG project](https://www.seastrong-project.eu) (HORIZON-CL6-2025-01-BIODIV-07), funded by the European Union under Horizon Europe.

SEASTRONG investigates the role of connectivity in safeguarding mangrove forests, seagrass beds, and coral reefs under global change, working across three study regions: Belize, Seychelles, and Fiji.

## About this repository

This repository is maintained by the [Ca' Foscari University of Venice (UNIVE)](https://www.unive.it), contributing to **Work Package 1** (coastal seascape mapping) and **Work Package 4** (functional connectivity and ecosystem services).

The tools hosted here support field data collection and processing workflows, including bathymetry mapping, tide correction, and photo geotagging. Each tool is self-contained in its own folder.

## Tools

| Tool | Description | WP |
|------|-------------|-----|
| [echosounder_bathymetry](./echosounder_bathymetry/) | Process depth data from a Deeper Pro echosounder and apply tide corrections | WP1, WP4 |
| [photo_geotagging](./photo_geotagging/) | Geotag time-lapse photos using a GPX track | WP1 |
| [underwater_photogrammetry](./underwater_photogrammetry/) | Two-camera GoPro rig for SfM photogrammetry surveys | WP1, WP2, WP5 |
| [Wave_climate](./Wave_climate/) | Wave, wind, tide and storm-surge climate at an offshore point, per month and season, with representative XBeach boundary conditions (Colab + ERA5 + Copernicus Marine + GTSM) | WP4 |
| [ICESat2_tool](./ICESat2_tool/) | ICESat-2 ATL24 bathymetry with per-rule quality flags and locked training / validation tracks for Bathymetrix-AI; ATL08 ground and canopy heights (Colab + SlideRule) | WP1 |
| [SDB_toolkit](./SDB_toolkit/) | Inputs for satellite-derived bathymetry (Bathymetrix-AI): Sentinel-2 composites, wave/wind/rain pre-screening of composite months, ICESat-2 training/validation depths, DEMs and habitat layers (Colab + Earth Engine + Copernicus) | WP1 |

## Documentation

Full documentation, including field procedures and step-by-step guides, is available at:

👉 **[seastrong-field-tools.readthedocs.io](https://seastrong-field-tools.readthedocs.io)**

## Funding

This project has received funding from the European Union's Horizon Europe research and innovation programme under grant agreement HORIZON-CL6-2025-01-BIODIV-07.
