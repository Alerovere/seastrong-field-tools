# SEASTRONG Field Processing Tools

```{image} _static/Seastrong_logo_Trans.png
:alt: SEASTRONG logo
:width: 200px
:align: center
```

## About the project

**SEASTRONG** (*Stronger Together: The Role of Connectivity in Safeguarding Functioning Coastal Ecosystems under Global Change*) is a research project funded by the European Union under the Horizon Europe programme (grant agreement HORIZON-CL6-2025-01-BIODIV-07).

Tropical coastal ecosystems — mangrove forests, seagrass beds, and coral reefs — are caught at the intersection of climate change and human coastal development. Together they underpin local fisheries, protect coastlines from storm surges, and regulate global climate through carbon sequestration. Yet by 2100, large fractions of these ecosystems face severe degradation or loss due to warming, sea level rise, and intensified tropical cyclones.

SEASTRONG addresses this urgent challenge by investigating the role of **connectivity** among these three ecosystems as a key factor in their resilience and functioning. The project works across three study regions — **Belize**, the **Seychelles**, and **Fiji** — spanning the Atlantic, Indian, and Pacific Oceans.

## Scientific objectives

SEASTRONG pursues six specific objectives:

- **O1** — Map coastal seascapes and spatial connectivity across cross-shelf corridors encompassing mangrove forests, seagrass beds, and coral reefs
- **O2** — Unlock local and traditional knowledge to foster climate-smart conservation and restoration practices
- **O3** — Assess the current and future role of spatial connectivity in ecosystem functioning and service provision
- **O4** — Assess the current and future potential of mangrove, seagrass, and coral restoration efforts
- **O5** — Integrate social and ecological knowledge to place tropical seascapes on a path to recovery
- **O6** — Share knowledge inclusively and catalyse science-policy impact

## About this repository

This repository is maintained by the **Ca' Foscari University of Venice (UNIVE)**, contributing to:

- **Work Package 1** — Mapping and characterisation of coastal seascapes for spatial connectivity
- **Work Package 4** — The role of spatial connectivity in functional connectivity and ecosystem services

It hosts field data processing tools developed to support SEASTRONG fieldwork. Each tool is self-contained and designed to be accessible to users with varying levels of coding experience, running primarily in Google Colab.

## Contents

The documentation has three parts:

**Bathymetry and habitat mapping** (corridor scale)

| Page | Description | Relevant WP tasks |
|------|-------------|-------------------|
| [Corridor mapping](corridor_mapping.md) | Overview: which field data calibrate and validate the satellite bathymetry and habitat maps, and how to plan a corridor | T1.2 |
| [Depth and bottom photos](depth_bottom_photos.md) | Field method: depth points and bottom photos with an echosounder and a camera on a kickboard | T1.2, T1.3, T4.5 |
| [Drone survey](drone_survey.md) | Field method: drone imagery of reef flats, seagrass and mangroves | T1.2 |
| [Depth and bottom photos: processing](depth_photos_processing.md) | Processing: tide correction of the depth points (calibration and validation sets) and geotagging of the bottom photos | T1.2, T1.3, T4.5 |

**Habitat structure and wave attenuation** (transect scale)

| Page | Description | Relevant WP tasks |
|------|-------------|-------------------|
| [Field transects](field_transects.md) | Common layout, header, effort and safety for the reef, seagrass and mangrove transects | T1.2, T4.5 |
| [Underwater photogrammetry](underwater_photogrammetry.md) | Reef structure with a two-camera rig | T1.2, T1.3, T2.2, T5.1 |
| [Mangroves](mangroves.md) | Mangrove structure and topographic profile | T1.2, T4.5 |
| [Seagrass](seagrass.md) | Seagrass structure from quadrats, and depth profile | T1.2, T4.5 |
| [Wave attenuation](wave_attenuation.md) | Pressure-sensor deployment, calibration and field validation | T1.2, T4.5 |

**Field resources:** [field forms, naming rules and equipment list](field_resources.md).

## Consortium

SEASTRONG brings together 15 partner institutions across 10 countries:

| # | Institution | Country |
|---|-------------|---------|
| 1 (Coordinator) | University of Bremen (UBRE) | Germany |
| 2 | Leibniz Centre for Tropical Marine Research (ZMT) | Germany |
| 3 | Ca' Foscari University of Venice (UNIVE) | Italy |
| 4 | Ecole Pratique des Hautes Etudes (EPHE) | France |
| 5 | Edinburgh Napier University (ENU) | UK |
| 6 | Institute for Water Education Delft (IHE) | Netherlands |
| 7 | Lancaster University (ULANC) | UK |
| 8 | Stazione Zoologica Anton Dohrn (SZN) | Italy |
| 9 | University of Almería (UAL) | Spain |
| 10 | Healthy Reefs for Healthy People (HRHP) | Belize |
| 11 | Toledo Institute for Development and Environment (TIDE) | Belize |
| 12 | Talanoa Consulting (TAL) | Fiji |
| 13 | University of the South Pacific (USP) | Fiji |
| 14 | Seychelles Islands Foundation (SIF) | Seychelles |
| 15 | Seychelles Parks and Gardens Authority (SPGA) | Seychelles |

## Funding acknowledgement

This project has received funding from the European Union's Horizon Europe research and innovation programme under grant agreement HORIZON-CL6-2025-01-BIODIV-07. Views and opinions expressed are those of the authors only and do not necessarily reflect those of the European Union or the European Research Executive Agency. Neither the European Union nor the granting authority can be held responsible for them.

![EU Flag](_static/EU_flag.png)