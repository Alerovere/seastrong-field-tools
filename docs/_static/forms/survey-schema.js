/* Survey fields transcribed from the existing Python PDF generators. */
import {DATASET} from './dataset-schema.js';
export const SURVEYS = {
  "reef": {
    "name": "Reef photogrammetry",
    "pdf": "reef_photogrammetry_field_form_v1.0.pdf",
    "sourceVersion": "1.0",
    "fields": [
      {
        "id": "snorkel_scuba",
        "label": "Snorkel / scuba",
        "section": "1. Transect header",
        "help": "How the photo passes were swum",
        "options": [
          "Snorkel",
          "Scuba"
        ],
        "kind": "text"
      },
      {
        "id": "sensor_1_id_seaward",
        "label": "Sensor 1 ID (seaward)",
        "section": "1. Transect header",
        "help": "Serial number of the seaward pressure sensor",
        "options": [],
        "kind": "text"
      },
      {
        "id": "sensor_1_position_on_tape_m",
        "label": "Sensor 1 position on tape (m)",
        "section": "1. Transect header",
        "help": "Distance along the tape, e.g. -1",
        "options": [],
        "kind": "text"
      },
      {
        "id": "sensor_2_id_landward",
        "label": "Sensor 2 ID (landward)",
        "section": "1. Transect header",
        "help": "Serial number of the landward pressure sensor",
        "options": [],
        "kind": "text"
      },
      {
        "id": "sensor_2_position_on_tape_m",
        "label": "Sensor 2 position on tape (m)",
        "section": "1. Transect header",
        "help": "Distance along the tape, e.g. 31",
        "options": [],
        "kind": "text"
      },
      {
        "id": "gps_point_above_0_m_end_lat_lon",
        "label": "GPS point above 0 m end (lat, lon)",
        "section": "1. Transect header",
        "help": "One approximate point at the surface above 0 m",
        "options": [],
        "kind": "text"
      },
      {
        "id": "bearing_0_30_m",
        "label": "Bearing 0 → 30 m (°)",
        "section": "1. Transect header",
        "help": "Compass bearing from 0 m towards 30 m",
        "options": [],
        "kind": "text"
      },
      {
        "id": "camera_spacing_cm",
        "label": "Camera spacing (cm)",
        "section": "1. Transect header",
        "help": "Measured distance between the two lens centres",
        "options": [],
        "kind": "text"
      },
      {
        "id": "swimming_height_m",
        "label": "Swimming height (m)",
        "section": "1. Transect header",
        "help": "Height of the rig above the bottom, ~1.5–2 m",
        "options": [],
        "kind": "text"
      },
      {
        "id": "tide_rising_falling_slack",
        "label": "Tide (rising / falling / slack)",
        "section": "1. Transect header",
        "help": "Tide stage during the survey",
        "options": [
          "Rising",
          "Falling",
          "Slack"
        ],
        "kind": "text"
      },
      {
        "id": "habitat_changes_along_tape_m_description",
        "label": "Habitat changes along tape (m: description)",
        "section": "3. Layout (in the water)",
        "help": "e.g. 0–8 m coral; 8–14 m sand; 14–30 m coral",
        "options": [],
        "kind": "text"
      },
      {
        "id": "cameras_start_time",
        "label": "Cameras start time",
        "section": "6. Photo survey",
        "help": "Time both cameras were started",
        "options": [],
        "kind": "text"
      },
      {
        "id": "cameras_end_time",
        "label": "Cameras end time",
        "section": "6. Photo survey",
        "help": "Time both cameras were stopped",
        "options": [],
        "kind": "text"
      },
      {
        "id": "passes_repeated_which_why",
        "label": "Passes repeated? (which, why)",
        "section": "6. Photo survey",
        "help": "e.g. pass 1 repeated, housing fogged",
        "options": [],
        "kind": "text"
      },
      {
        "id": "survey_complete_y_n",
        "label": "Survey complete (Y / N)",
        "section": "A. Survey",
        "help": "All passes, targets and depths done",
        "options": [
          "Y",
          "N"
        ],
        "kind": "text"
      },
      {
        "id": "time_in_the_water_h",
        "label": "Time in the water (h)",
        "section": "A. Survey",
        "help": "From entering to leaving the water",
        "options": [],
        "kind": "text"
      },
      {
        "id": "visibility_m",
        "label": "Visibility (m)",
        "section": "A. Survey",
        "help": "Estimated horizontal visibility",
        "options": [],
        "kind": "text"
      },
      {
        "id": "waves_surge",
        "label": "Waves / surge",
        "section": "A. Survey",
        "help": "Calm, moderate or strong",
        "options": [],
        "kind": "text"
      },
      {
        "id": "cloud_caustics",
        "label": "Cloud / caustics",
        "section": "A. Survey",
        "help": "Overcast or sunny; caustics yes or no",
        "options": [],
        "kind": "text"
      },
      {
        "id": "current",
        "label": "Current",
        "section": "A. Survey",
        "help": "None, weak or strong",
        "options": [],
        "kind": "text"
      },
      {
        "id": "photos_camera_a_n",
        "label": "Photos camera A (n)",
        "section": "B. Data",
        "help": "Number of photos downloaded from camera A",
        "options": [],
        "kind": "text"
      },
      {
        "id": "photos_camera_b_n",
        "label": "Photos camera B (n)",
        "section": "B. Data",
        "help": "Number of photos downloaded from camera B",
        "options": [],
        "kind": "text"
      },
      {
        "id": "target_depths_complete_y_n",
        "label": "Target depths complete (Y / N)",
        "section": "B. Data",
        "help": "Three readings and time for every target",
        "options": [
          "Y",
          "N"
        ],
        "kind": "text"
      },
      {
        "id": "depth_profile_complete_y_n",
        "label": "Depth profile complete (Y / N)",
        "section": "B. Data",
        "help": "Every 2 m, both sensors and beyond 30 m",
        "options": [
          "Y",
          "N"
        ],
        "kind": "text"
      },
      {
        "id": "slate_photo_saved_y_n",
        "label": "Slate photo saved (Y / N)",
        "section": "B. Data",
        "help": "Photo of the slate saved with the data",
        "options": [
          "Y",
          "N"
        ],
        "kind": "text"
      },
      {
        "id": "field_sheet_copied_y_n",
        "label": "Field sheet copied (Y / N)",
        "section": "B. Data",
        "help": "Slate data typed into this form",
        "options": [
          "Y",
          "N"
        ],
        "kind": "text"
      }
    ],
    "checklists": [
      {
        "title": "2. Before going in the water",
        "items": [
          "Two cameras set to the same time (GoPro app); labelled A and B",
          "Cameras charged, memory cards empty, identical settings (Timelapse, 0.5 s, 5K, Linear, Protune, Flat, ISO 200, shortest shutter, fixed white balance, JPEG)",
          "Rig assembled; camera spacing measured and written above",
          "At least 6 scale bars (bar list with you), 30 m tape, depth gauge, compass, GPS/phone, slate, weights or pegs, colour tab (optional)",
          "Conditions OK: visibility > ~4 m, little surge, tide not changing fast",
          "No strong caustics on the bottom (otherwise wait for clouds or a lower sun)"
        ]
      },
      {
        "title": "3. Layout (in the water)",
        "items": [
          "Tape laid cross-shore, straight and secured: 0 m at sensor 1 (seaward), 30 m at sensor 2",
          "At least 6 scale bars on both sides, within ~2 m of the tape, varied orientation and elevation; no damage to live coral",
          "Tape positions where the habitat changes noted below"
        ]
      },
      {
        "title": "6. Photo survey",
        "items": [
          "Both cameras started as close to simultaneously as possible; colour tab in the first photos (if used)",
          "Pass 1: forward, camera A over the tape, ~1.5–2 m above the bottom, ~0.3 m/s",
          "Pass 2: backward, camera A over the tape",
          "Pass 3: zigzag, ~3 m each side, ~5 crossings each way",
          "Photos checked on both cameras: complete, sharp, not fogged; passes repeated if needed",
          "All scale bars (checked against the bar list) and the tape recovered; slate photographed"
        ]
      },
      {
        "title": "C. Quality check (tick if a problem)",
        "items": [
          "Blurred or dark photos",
          "Fogged housing",
          "Caustics in part of the survey",
          "A camera stopped during a pass",
          "Targets moved or not visible",
          "Tape not straight or moved",
          "Missing depth readings"
        ]
      }
    ],
    "tables": []
  },
  "mangrove": {
    "name": "Mangrove",
    "pdf": "mangrove_field_form_v1.0.pdf",
    "sourceVersion": "1.0",
    "fields": [
      {
        "id": "structure_method",
        "label": "Structure method",
        "section": "1. Transect header",
        "help": "A photogrammetry, B tree-by-tree, C manual",
        "options": [
          "A",
          "B",
          "C",
          "A + C",
          "B + C",
          "A + B"
        ],
        "kind": "text"
      },
      {
        "id": "sensor_1_id_seaward",
        "label": "Sensor 1 ID (seaward)",
        "section": "1. Transect header",
        "help": "Serial number of the seaward pressure sensor",
        "options": [],
        "kind": "text"
      },
      {
        "id": "sensor_1_position_on_tape_m",
        "label": "Sensor 1 position on tape (m)",
        "section": "1. Transect header",
        "help": "Distance along the tape, e.g. 0",
        "options": [],
        "kind": "text"
      },
      {
        "id": "sensor_2_id_landward",
        "label": "Sensor 2 ID (landward)",
        "section": "1. Transect header",
        "help": "Serial number of the landward pressure sensor",
        "options": [],
        "kind": "text"
      },
      {
        "id": "sensor_2_position_on_tape_m",
        "label": "Sensor 2 position on tape (m)",
        "section": "1. Transect header",
        "help": "Distance along the tape, e.g. 30",
        "options": [],
        "kind": "text"
      },
      {
        "id": "gps_point_at_0_m_end_lat_lon",
        "label": "GPS point at 0 m end (lat, lon)",
        "section": "1. Transect header",
        "help": "One approximate point at the 0 m end",
        "options": [],
        "kind": "text"
      },
      {
        "id": "bearing_0_30_m",
        "label": "Bearing 0 → 30 m (°)",
        "section": "1. Transect header",
        "help": "Compass bearing from 0 m towards 30 m",
        "options": [],
        "kind": "text"
      },
      {
        "id": "low_tide_time",
        "label": "Low tide time",
        "section": "1. Transect header",
        "help": "Time of low water on the survey day",
        "options": [],
        "kind": "text"
      },
      {
        "id": "dominant_species",
        "label": "Dominant species",
        "section": "1. Transect header",
        "help": "e.g. Rhizophora mangle",
        "options": [],
        "kind": "text"
      },
      {
        "id": "forest_description",
        "label": "Forest description",
        "section": "1. Transect header",
        "help": "Open or dense; pneumatophores or prop roots",
        "options": [],
        "kind": "text"
      },
      {
        "id": "methods_along_the_tape",
        "label": "Methods along the tape",
        "section": "1. Transect header",
        "help": "If more than one, e.g. A 0–12 m, C 12–30 m",
        "options": [],
        "kind": "text"
      },
      {
        "id": "vegetation_changes_along_tape_m_description",
        "label": "Vegetation changes along tape (m: description)",
        "section": "1. Transect header",
        "help": "e.g. 0–6 m pneumatophores only; 6–30 m dense prop roots",
        "options": [],
        "kind": "text"
      },
      {
        "id": "vegetation_beyond_the_30_m_mark",
        "label": "Vegetation beyond the 30 m mark",
        "section": "1. Transect header",
        "help": "Short description of the 5–10 m beyond the tape",
        "options": [],
        "kind": "text"
      },
      {
        "id": "low_water_mark_time",
        "label": "Low-water mark: time",
        "section": "3. Topography: from the low-water mark to 5–10 m beyond the 30 m mark",
        "help": "Time when the low-water mark was identified",
        "options": [],
        "kind": "text"
      },
      {
        "id": "low_water_mark_position",
        "label": "Low-water mark: position",
        "section": "3. Topography: from the low-water mark to 5–10 m beyond the 30 m mark",
        "help": "Distance seaward of the 0 m mark (m)",
        "options": [],
        "kind": "text"
      },
      {
        "id": "gnss_at_start_lat_lon",
        "label": "GNSS at start: lat, lon",
        "section": "3. Topography: from the low-water mark to 5–10 m beyond the 30 m mark",
        "help": "At the low-water mark",
        "options": [],
        "kind": "text"
      },
      {
        "id": "gnss_at_start_elevation_m",
        "label": "GNSS at start: elevation (m)",
        "section": "3. Topography: from the low-water mark to 5–10 m beyond the 30 m mark",
        "help": "RTK only; leave empty with handheld GNSS",
        "options": [],
        "kind": "text"
      },
      {
        "id": "gnss_type",
        "label": "GNSS type",
        "section": "3. Topography: from the low-water mark to 5–10 m beyond the 30 m mark",
        "help": "RTK or handheld",
        "options": [
          "RTK",
          "Handheld"
        ],
        "kind": "text"
      },
      {
        "id": "datum_tie_at_this_site",
        "label": "Datum tie at this site",
        "section": "3. Topography: from the low-water mark to 5–10 m beyond the 30 m mark",
        "help": "RTK fix or benchmark, at least once per site",
        "options": [
          "RTK fix",
          "Benchmark",
          "Done at another transect",
          "Not done"
        ],
        "kind": "text"
      },
      {
        "id": "camera_spacing_cm",
        "label": "Camera spacing (cm)",
        "section": "4. Method A: photogrammetry",
        "help": "Measured distance between the two lens centres",
        "options": [],
        "kind": "text"
      },
      {
        "id": "rig_height_above_ground_m",
        "label": "Rig height above ground (m)",
        "section": "4. Method A: photogrammetry",
        "help": "About 1–1.5 m",
        "options": [],
        "kind": "text"
      },
      {
        "id": "cameras_start_time",
        "label": "Cameras start time",
        "section": "4. Method A: photogrammetry",
        "help": "Time both cameras were started",
        "options": [],
        "kind": "text"
      },
      {
        "id": "cameras_end_time",
        "label": "Cameras end time",
        "section": "4. Method A: photogrammetry",
        "help": "Time both cameras were stopped",
        "options": [],
        "kind": "text"
      },
      {
        "id": "passes_repeated_which_why",
        "label": "Passes repeated? (which, why)",
        "section": "4. Method A: photogrammetry",
        "help": "",
        "options": [],
        "kind": "text"
      },
      {
        "id": "trees_in_front_plot_n",
        "label": "Trees in front plot (n)",
        "section": "5. Method B: tree-by-tree (Mori et al., 2022)",
        "help": "All trees rooted in the 5 m × 5 m plot",
        "options": [],
        "kind": "text"
      },
      {
        "id": "trees_in_centre_plot_n",
        "label": "Trees in centre plot (n)",
        "section": "5. Method B: tree-by-tree (Mori et al., 2022)",
        "help": "All trees rooted in the 5 m × 5 m plot",
        "options": [],
        "kind": "text"
      },
      {
        "id": "trees_in_back_plot_n",
        "label": "Trees in back plot (n)",
        "section": "5. Method B: tree-by-tree (Mori et al., 2022)",
        "help": "All trees rooted in the 5 m × 5 m plot",
        "options": [],
        "kind": "text"
      },
      {
        "id": "survey_complete_y_n",
        "label": "Survey complete (Y / N)",
        "section": "A. Survey",
        "help": "Topography and the structure method completed",
        "options": [
          "Y",
          "N"
        ],
        "kind": "text"
      },
      {
        "id": "time_on_site_h",
        "label": "Time on site (h)",
        "section": "A. Survey",
        "help": "From arrival to departure",
        "options": [],
        "kind": "text"
      },
      {
        "id": "weather",
        "label": "Weather",
        "section": "A. Survey",
        "help": "Sun, cloud, rain",
        "options": [],
        "kind": "text"
      },
      {
        "id": "ground_conditions",
        "label": "Ground conditions",
        "section": "A. Survey",
        "help": "e.g. soft mud, firm sand, standing water",
        "options": [],
        "kind": "text"
      },
      {
        "id": "topography_csv_prepared_y_n",
        "label": "Topography CSV prepared (Y / N)",
        "section": "B. Data",
        "help": "Stations typed into the CSV for the notebook",
        "options": [
          "Y",
          "N"
        ],
        "kind": "text"
      },
      {
        "id": "photos_n",
        "label": "Photos (n)",
        "section": "B. Data",
        "help": "Total number of photos from the survey",
        "options": [],
        "kind": "text"
      },
      {
        "id": "slate_sheets_photographed_y_n",
        "label": "Slate / sheets photographed (Y / N)",
        "section": "B. Data",
        "help": "Photos of all paper sheets saved with the data",
        "options": [
          "Y",
          "N"
        ],
        "kind": "text"
      }
    ],
    "checklists": [
      {
        "title": "2. Before starting",
        "items": [
          "Working at low tide, forest floor exposed",
          "30 m tape laid from sensor 1 (0 m, forest edge) to sensor 2 (30 m), straight and secured",
          "Overview photos of the transect taken from both ends",
          "Equipment for the topography: 50 m tape, clinometer, plastic board, station pegs, GNSS",
          "Equipment for the structure method (see the page of the method used)"
        ]
      },
      {
        "title": "4. Method A: photogrammetry",
        "items": [
          "Two cameras set to the same time (GoPro app); identical settings; white balance fixed; no red filter",
          "At least 6 scale bars on both sides of the tape, within ~2 m, varied orientation and elevation (used only for scaling)",
          "Pass 1: forward, camera A over the tape, cameras pointing down, ~0.3 m/s",
          "Pass 2: backward, camera A over the tape, cameras pointing down",
          "Pass 3: zigzag across the tape to ~3 m each side, cameras tilted ~45° forward",
          "Photos checked on both cameras: complete and sharp"
        ]
      },
      {
        "title": "C. Quality check (tick if a problem)",
        "items": [
          "Tide came in before the survey was finished",
          "Topography incomplete or stations missing",
          "No GNSS fix at the start",
          "Plots or sample trees fewer than planned",
          "Photos blurred or incomplete (method A or B)",
          "Measurements missing at some heights (method C)"
        ]
      }
    ],
    "tables": []
  },
  "seagrass": {
    "name": "Seagrass",
    "pdf": "seagrass_field_form_v1.0.pdf",
    "sourceVersion": "1.0",
    "fields": [
      {
        "id": "sensor_1_id_seaward",
        "label": "Sensor 1 ID (seaward)",
        "section": "1. Transect header",
        "help": "Serial number of the seaward pressure sensor",
        "options": [],
        "kind": "text"
      },
      {
        "id": "sensor_1_position_on_tape_m",
        "label": "Sensor 1 position on tape (m)",
        "section": "1. Transect header",
        "help": "Distance along the tape, e.g. 0",
        "options": [],
        "kind": "text"
      },
      {
        "id": "sensor_2_id_landward",
        "label": "Sensor 2 ID (landward)",
        "section": "1. Transect header",
        "help": "Serial number of the landward pressure sensor",
        "options": [],
        "kind": "text"
      },
      {
        "id": "sensor_2_position_on_tape_m",
        "label": "Sensor 2 position on tape (m)",
        "section": "1. Transect header",
        "help": "Distance along the tape, e.g. 30",
        "options": [],
        "kind": "text"
      },
      {
        "id": "gps_point_at_0_m_end_lat_lon",
        "label": "GPS point at 0 m end (lat, lon)",
        "section": "1. Transect header",
        "help": "One approximate point at the surface above 0 m",
        "options": [],
        "kind": "text"
      },
      {
        "id": "bearing_0_30_m",
        "label": "Bearing 0 → 30 m (°)",
        "section": "1. Transect header",
        "help": "Compass bearing from 0 m towards 30 m",
        "options": [],
        "kind": "text"
      },
      {
        "id": "slack_water_time",
        "label": "Slack water time",
        "section": "1. Transect header",
        "help": "Expected slack water on the survey day",
        "options": [],
        "kind": "text"
      },
      {
        "id": "dominant_species",
        "label": "Dominant species",
        "section": "1. Transect header",
        "help": "Species measured in the quadrats, e.g. Thalassia testudinum",
        "options": [],
        "kind": "text"
      },
      {
        "id": "other_species",
        "label": "Other species",
        "section": "1. Transect header",
        "help": "Other seagrass species present on the transect",
        "options": [],
        "kind": "text"
      },
      {
        "id": "meadow_changes_along_tape_m_description",
        "label": "Meadow changes along tape (m: description)",
        "section": "1. Transect header",
        "help": "e.g. 0–6 m continuous; 6–10 m bare sand; 10–30 m patchy",
        "options": [],
        "kind": "text"
      },
      {
        "id": "survey_complete_y_n",
        "label": "Survey complete (Y / N)",
        "section": "A. Survey",
        "help": "Depth stops and all 9 quadrats done",
        "options": [
          "Y",
          "N"
        ],
        "kind": "text"
      },
      {
        "id": "time_in_the_water_h",
        "label": "Time in the water (h)",
        "section": "A. Survey",
        "help": "From entering to leaving the water",
        "options": [],
        "kind": "text"
      },
      {
        "id": "visibility_m",
        "label": "Visibility (m)",
        "section": "A. Survey",
        "help": "Estimated horizontal visibility",
        "options": [],
        "kind": "text"
      },
      {
        "id": "current",
        "label": "Current",
        "section": "A. Survey",
        "help": "None, weak or strong",
        "options": [],
        "kind": "text"
      },
      {
        "id": "cover_photos_n",
        "label": "Cover photos (n)",
        "section": "B. Data",
        "help": "Vertical photos taken at the 2 m stops",
        "options": [],
        "kind": "text"
      },
      {
        "id": "quadrat_photos_n",
        "label": "Quadrat photos (n)",
        "section": "B. Data",
        "help": "Photo 1 + Photo 2 of the 9 quadrats (18 expected)",
        "options": [],
        "kind": "text"
      },
      {
        "id": "slate_photographed_y_n",
        "label": "Slate photographed (Y / N)",
        "section": "B. Data",
        "help": "Photo of the slate saved with the data",
        "options": [
          "Y",
          "N"
        ],
        "kind": "text"
      }
    ],
    "checklists": [
      {
        "title": "2. Before going in the water",
        "items": [
          "Around slack water; visibility and current OK for snorkelling",
          "30 m tape laid on the bottom from sensor 1 (0 m, seaward) to sensor 2 (30 m), and on for 5–10 m",
          "Two 25 cm × 25 cm frames with marked points; graduated stick or depth gauge; camera",
          "Slate with mm ruler; plastic caliper; pencils",
          "Roles agreed: A recorder (depths, shoots, slate), B photographer (frames, photos, canopy height, thickness)"
        ]
      },
      {
        "title": "C. Quality check (tick if a problem)",
        "items": [
          "Shoot bases not visible in some Photo 2",
          "Quadrats moved far from the planned position",
          "Depth stops missing",
          "Shoots or thickness missing in some quadrats",
          "Strong current or poor visibility during the survey",
          "Tide changed a lot during the survey"
        ]
      }
    ],
    "tables": []
  },
  "bathy": {
    "name": "Depth & bottom photos",
    "pdf": "depth_photos_field_form_v1.2.pdf",
    "sourceVersion": "1.2",
    "fields": [
      {
        "id": "data_collected",
        "label": "Data collected",
        "section": "1. Survey header",
        "help": "Depth and photos, depth only, or photos only",
        "options": [
          "Depth + photos",
          "Depth only",
          "Photos only"
        ],
        "kind": "text"
      },
      {
        "id": "echosounder_id",
        "label": "Echosounder ID",
        "section": "1. Survey header",
        "help": "Serial number or label of the Deeper Pro",
        "options": [],
        "kind": "text"
      },
      {
        "id": "camera_id",
        "label": "Camera ID",
        "section": "1. Survey header",
        "help": "Label of the camera used",
        "options": [],
        "kind": "text"
      },
      {
        "id": "gnss_id",
        "label": "GNSS ID",
        "section": "1. Survey header",
        "help": "Label or serial number of the handheld GNSS",
        "options": [],
        "kind": "text"
      },
      {
        "id": "photo_interval_s",
        "label": "Photo interval (s)",
        "section": "1. Survey header",
        "help": "Timelapse interval set on the camera, e.g. 1",
        "options": [],
        "kind": "text"
      },
      {
        "id": "tide_during_the_survey",
        "label": "Tide during the survey",
        "section": "1. Survey header",
        "help": "Rising, falling, high or low",
        "options": [
          "Rising",
          "Falling",
          "High",
          "Low"
        ],
        "kind": "text"
      },
      {
        "id": "water_clarity",
        "label": "Water clarity",
        "section": "1. Survey header",
        "help": "Clear, moderate or turbid",
        "options": [
          "Clear",
          "Moderate",
          "Turbid"
        ],
        "kind": "text"
      },
      {
        "id": "start_reference_photo_gps_time_shown",
        "label": "Start reference photo: GPS time shown",
        "section": "3. Reference photos (clock synchronisation)",
        "help": "Time on the GNSS screen in the photo (hh:mm:ss)",
        "options": [],
        "kind": "text"
      },
      {
        "id": "end_reference_photo_gps_time_shown",
        "label": "End reference photo: GPS time shown",
        "section": "3. Reference photos (clock synchronisation)",
        "help": "Time on the GNSS screen in the photo (hh:mm:ss)",
        "options": [],
        "kind": "text"
      },
      {
        "id": "survey_start_time",
        "label": "Survey start time",
        "section": "4. Survey times and notes",
        "help": "Time when recording was started",
        "options": [],
        "kind": "text"
      },
      {
        "id": "survey_end_time",
        "label": "Survey end time",
        "section": "4. Survey times and notes",
        "help": "Time when recording was stopped",
        "options": [],
        "kind": "text"
      },
      {
        "id": "survey_complete_y_n",
        "label": "Survey complete (Y / N)",
        "section": "A. Survey",
        "help": "Whole corridor covered as planned",
        "options": [
          "Y",
          "N"
        ],
        "kind": "text"
      },
      {
        "id": "time_in_the_water_h",
        "label": "Time in the water (h)",
        "section": "A. Survey",
        "help": "From entering to leaving the water",
        "options": [],
        "kind": "text"
      },
      {
        "id": "waves",
        "label": "Waves",
        "section": "A. Survey",
        "help": "Calm, moderate or strong",
        "options": [],
        "kind": "text"
      },
      {
        "id": "current",
        "label": "Current",
        "section": "A. Survey",
        "help": "None, weak or strong",
        "options": [],
        "kind": "text"
      },
      {
        "id": "scan_exported_csv_y_n",
        "label": "Scan exported (CSV) (Y / N)",
        "section": "B. Data",
        "help": "Scan exported from the Deeper app",
        "options": [
          "Y",
          "N"
        ],
        "kind": "text"
      },
      {
        "id": "gps_track_exported_gpx_y_n",
        "label": "GPS track exported (GPX) (Y / N)",
        "section": "B. Data",
        "help": "Track exported from the handheld GNSS",
        "options": [
          "Y",
          "N"
        ],
        "kind": "text"
      },
      {
        "id": "photos_n",
        "label": "Photos (n)",
        "section": "B. Data",
        "help": "Number of photos downloaded from the camera",
        "options": [],
        "kind": "text"
      }
    ],
    "checklists": [
      {
        "title": "2. Set-up",
        "items": [
          "Echosounder mounted under the kickboard, always under water",
          "Camera mounted under the kickboard, pointing straight down; timelapse mode; memory card empty",
          "Depth: phone charged, in a waterproof case; Deeper app connected; phone GPS fixed",
          "Photos: handheld GNSS recording a track (1 s), fix OK, on top of the board in a waterproof bag",
          "Scan started in the Deeper app, GNSS track started, camera started"
        ]
      },
      {
        "title": "C. Quality check (tick if a problem)",
        "items": [
          "No GPS fix for part of the survey",
          "Reference photo missing or GPS time not readable",
          "Camera stopped or memory card full",
          "Photos blurred, dark or turbid",
          "Echosounder out of the water for part of a track (waves)",
          "Planned tracks not completed"
        ]
      }
    ],
    "tables": []
  },
  "drone": {
    "name": "Drone survey",
    "pdf": "drone_field_form_v1.0.pdf",
    "sourceVersion": "1.0",
    "fields": [
      {
        "id": "drone_model",
        "label": "Drone model",
        "section": "1. Survey header",
        "help": "Make and model of the drone",
        "options": [],
        "kind": "text"
      },
      {
        "id": "take_off_point_lat_lon",
        "label": "Take-off point (lat, lon)",
        "section": "1. Survey header",
        "help": "Approximate position of the take-off point",
        "options": [],
        "kind": "text"
      },
      {
        "id": "tide",
        "label": "Tide",
        "section": "1. Survey header",
        "help": "Rising, falling, high or low",
        "options": [
          "Rising",
          "Falling",
          "High",
          "Low"
        ],
        "kind": "text"
      },
      {
        "id": "weather",
        "label": "Weather",
        "section": "1. Survey header",
        "help": "Clear, thin overcast, scattered clouds, overcast",
        "options": [
          "Clear",
          "Thin overcast",
          "Scattered clouds",
          "Overcast"
        ],
        "kind": "text"
      },
      {
        "id": "wind",
        "label": "Wind",
        "section": "1. Survey header",
        "help": "Calm, light, moderate or strong",
        "options": [
          "Calm",
          "Light",
          "Moderate",
          "Strong"
        ],
        "kind": "text"
      },
      {
        "id": "sea_surface",
        "label": "Sea surface",
        "section": "1. Survey header",
        "help": "Calm, ripples or waves",
        "options": [
          "Calm",
          "Ripples",
          "Waves"
        ],
        "kind": "text"
      },
      {
        "id": "survey_complete_y_n",
        "label": "Survey complete (Y / N)",
        "section": "A. Survey",
        "help": "Whole planned area flown",
        "options": [
          "Y",
          "N"
        ],
        "kind": "text"
      },
      {
        "id": "flights_n",
        "label": "Flights (n)",
        "section": "A. Survey",
        "help": "Number of flights (batteries)",
        "options": [],
        "kind": "text"
      },
      {
        "id": "sun_glint",
        "label": "Sun glint",
        "section": "A. Survey",
        "help": "None, some or strong",
        "options": [
          "None",
          "Some",
          "Strong"
        ],
        "kind": "text"
      },
      {
        "id": "photos_n",
        "label": "Photos (n)",
        "section": "B. Data",
        "help": "Total number of photos downloaded",
        "options": [],
        "kind": "text"
      },
      {
        "id": "target_positions_saved_y_n",
        "label": "Target positions saved (Y / N)",
        "section": "B. Data",
        "help": "Handheld GNSS points or table on page 1",
        "options": [
          "Y",
          "N"
        ],
        "kind": "text"
      }
    ],
    "checklists": [
      {
        "title": "C. Quality check (tick if a problem)",
        "items": [
          "Sun glint on part of the photos",
          "Waves or ripples blur the bottom",
          "Cloud shadows on part of the area",
          "Gaps in the coverage (missed lines, aborted flight)",
          "Fewer than 4 ground targets, or targets not visible",
          "Photos blurred or over- / under-exposed"
        ]
      }
    ],
    "tables": []
  },
  "waves": {
    "name": "Wave sensors",
    "pdf": "wave_sensor_field_form_v1.0.pdf",
    "sourceVersion": "1.0",
    "fields": [
      {
        "id": "deployment_d1_d2_d3",
        "label": "Deployment (D1 / D2 / D3)",
        "section": "1. Header",
        "help": "First, second or third deployment in this corridor",
        "options": [
          "D1",
          "D2",
          "D3"
        ],
        "kind": "text"
      },
      {
        "id": "sensor_clocks_set_to_utc_y_n",
        "label": "Sensor clocks set to UTC (Y / N)",
        "section": "1. Header",
        "help": "All sensor clocks set to UTC before deployment",
        "options": [
          "Y",
          "N"
        ],
        "kind": "text"
      },
      {
        "id": "barometric_logger_running_y_n",
        "label": "Barometric logger running (Y / N)",
        "section": "1. Header",
        "help": "Barometric reference logging in air at the base",
        "options": [
          "Y",
          "N"
        ],
        "kind": "text"
      },
      {
        "id": "barometric_logger_id",
        "label": "Barometric logger ID",
        "section": "1. Header",
        "help": "Serial number or label",
        "options": [],
        "kind": "text"
      },
      {
        "id": "tide_at_deployment",
        "label": "Tide at deployment",
        "section": "1. Header",
        "help": "Rising, falling, high or low",
        "options": [
          "Rising",
          "Falling",
          "High",
          "Low"
        ],
        "kind": "text"
      },
      {
        "id": "sea_state",
        "label": "Sea state",
        "section": "1. Header",
        "help": "Calm, moderate or rough",
        "options": [
          "Calm",
          "Moderate",
          "Rough"
        ],
        "kind": "text"
      },
      {
        "id": "retrieved_by",
        "label": "Retrieved by",
        "section": "3. Retrieval",
        "help": "Names of the people retrieving",
        "options": [],
        "kind": "text"
      },
      {
        "id": "all_sensors_recovered_y_n",
        "label": "All sensors recovered (Y / N)",
        "section": "A. Deployment",
        "help": "All 7 sensors retrieved",
        "options": [
          "Y",
          "N"
        ],
        "kind": "text"
      },
      {
        "id": "data_downloaded_y_n",
        "label": "Data downloaded (Y / N)",
        "section": "A. Deployment",
        "help": "All records downloaded and checked",
        "options": [
          "Y",
          "N"
        ],
        "kind": "text"
      },
      {
        "id": "barometric_data_downloaded_y_n",
        "label": "Barometric data downloaded (Y / N)",
        "section": "A. Deployment",
        "help": "Barometric record covering the deployment",
        "options": [
          "Y",
          "N"
        ],
        "kind": "text"
      }
    ],
    "checklists": [
      {
        "title": "B. Quality check (tick if a problem)",
        "items": [
          "A sensor moved, tilted or was found loose",
          "Pressure port buried, fouled or covered",
          "Battery or memory ran out before retrieval",
          "Sensor clock not on UTC or time unclear",
          "Barometric record missing or with gaps",
          "Depth at deployment or retrieval not measured"
        ]
      }
    ],
    "tables": []
  }
};

// Derived datasets (processed products, not field surveys): see dataset-schema.js
SURVEYS.sat = DATASET;
