"""Generate the SEASTRONG wave sensor deployment field form (fillable PDF).

Usage:  python wave_sensor_field_form.py
Output: ../docs/_static/forms/wave_sensor_field_form_v<VERSION>.pdf

Bump VERSION (and VERSION_DATE) for every change; see README.md.
Requires: reportlab, pypdf.
"""
import os
from reportlab.platypus import Paragraph, Spacer, PageBreak
from reportlab.lib.units import mm
from formlib import Form, H1, H2, SUB, S, W, COMMON_HELP, COMMON_CHOICES

VERSION = "1.0"
VERSION_DATE = "2026-10-14"
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "..", "docs", "_static", "forms", f"wave_sensor_field_form_v{VERSION}.pdf")

HELP = dict(COMMON_HELP)
HELP.update({
    "Survey ID": "e.g. BZ140327C1waves (automatic in Acrobat)",
    "Date": "Deployment date, as mm/dd/yyyy",
    "Deployment (D1 / D2 / D3)": "First, second or third deployment in this corridor",
    "Operators": "Names of the people deploying",
    "Sensor clocks set to UTC (Y / N)": "All sensor clocks set to UTC before deployment",
    "Barometric logger running (Y / N)": "Barometric reference logging in air at the base",
    "Barometric logger ID": "Serial number or label",
    "Tide at deployment": "Rising, falling, high or low",
    "Sea state": "Calm, moderate or rough",
    "Filled in by": "Who fills in this report",
    "All sensors recovered (Y / N)": "All 7 sensors retrieved",
    "Data downloaded (Y / N)": "All records downloaded and checked",
    "Barometric data downloaded (Y / N)": "Barometric record covering the deployment",
    "Data folder name": "Survey ID, e.g. BZ140327C1waves",
    "Retrieval date": "As mm/dd/yyyy",
    "Retrieved by": "Names of the people retrieving",
})
CHOICES = dict(COMMON_CHOICES)
CHOICES.update({"Deployment (D1 / D2 / D3)": ["D1", "D2", "D3"],
                "Tide at deployment": ["Rising", "Falling", "High", "Low"],
                "Sea state": ["Calm", "Moderate", "Rough"]})
f = Form("Wave sensor field form", "waves", HELP, CHOICES, id_label="Survey ID")
POS = ["Reef S1 (0 m)", "Reef S2 (30 m)", "Reef PC (post-crest)", "Seagrass S1 (0 m)", "Seagrass S2 (30 m)",
       "Mangrove S1 (0 m)", "Mangrove S2 (30 m)"]
story = []

# ---------- page 1 ----------
story += [Paragraph("Wave sensors: field form", H1),
          Paragraph("One form per corridor and deployment (7 sensors). Page 1 is filled in at deployment, page 2 at "
                    "retrieval, and page 3 is the post-site report, filled in after downloading the data. Fill it in with Adobe Acrobat "
                    "Reader (free): the Survey ID is then filled in automatically and the form is saved correctly. "
                    "Method: Wave attenuation page of the SEASTRONG Field Processing Tools documentation.", SUB)]
story.append(Paragraph("1. Header", H2))
story.append(f.fields(["Study area (BZ / SC / FJ)", "Corridor (C1–C6)", "Survey ID", "Date",
                       "Deployment (D1 / D2 / D3)", "Operators", "Sensor clocks set to UTC (Y / N)",
                       "Barometric logger running (Y / N)", "Barometric logger ID", "Tide at deployment",
                       "Sea state", None]))
story.append(Paragraph("2. Deployment", H2))
story.append(Paragraph("<b>Start</b>: time logging started (UTC). <b>Depth</b>: water depth at the sensor and the time it was "
                       "measured. <b>Port</b>: height of the pressure port above the bottom. <b>Fixing</b>: block, substrate, "
                       "stake, weight or root. <b>Photo</b>: photo number of the mounted sensor. <b>T / S</b>: water "
                       "temperature (°C) and salinity, if measured.", S))
story.append(Spacer(1, 3))
head = ["Position", "Sensor ID", "Start (UTC)", "Depth (m)", "at (UTC)", "Port (cm)", "Fixing", "Photo", "T / S"]
wd = [0.17, 0.12, 0.1, 0.08, 0.1, 0.08, 0.13, 0.08, 0.14]
story.append(f.grid(head, 7, wd, "dep", prefill=[[p] + [None] * 8 for p in POS], rh=8 * mm,
                    example=["e.g.", "PT2X-0412", "09:40", "1.8", "09:52", "5", "block", "0123", "28.5 / 35"]))
story.append(PageBreak())
story.append(Paragraph("3. Retrieval", H2))
story.append(f.fields(["Retrieved by", None]))
story.append(Spacer(1, 4))
story.append(Paragraph("PT2X are retrieved after 2 days, Driesen + Kern after 4 days. <b>Date</b>: retrieval date (mm/dd). <b>End</b>: time logging stopped (UTC). <b>Data file</b>: survey ID + habitat + position, "
                       "e.g. BZ140327C1waves_reef_S1. <b>OK</b>: sensor in place, not moved or buried (Y / N).", S))
story.append(Spacer(1, 3))
head = ["Position", "Date", "End (UTC)", "Depth (m)", "at (UTC)", "Data file", "OK", "Notes"]
wd = [0.17, 0.09, 0.09, 0.07, 0.09, 0.25, 0.05, 0.19]
story.append(f.grid(head, 7, wd, "ret", prefill=[[p] + [None] * 7 for p in POS], rh=8 * mm))
story.append(PageBreak())

# ---------- page 2: post-site report ----------
story.append(Paragraph("Post-site report", H1))
story.append(Paragraph("Filled in after the retrieval and download. Send it with the data to the data manager.", SUB))
story.append(Paragraph("A. Deployment", H2))
story.append(f.fields(["Survey ID", "Date", "Filled in by", "All sensors recovered (Y / N)",
                       "Data downloaded (Y / N)", "Barometric data downloaded (Y / N)", "Data folder name", None]))
story.append(Spacer(1, 4))
story.append(f.fields(["Data download link"], cols=1))
story.append(Paragraph("B. Quality check (tick if a problem)", H2))
story.append(f.checklist(["A sensor moved, tilted or was found loose", "Pressure port buried, fouled or covered",
                          "Battery or memory ran out before retrieval", "Sensor clock not on UTC or time unclear",
                          "Barometric record missing or with gaps", "Depth at deployment or retrieval not measured"]))
story.append(Paragraph("C. Deviations from the protocol, problems and notes", H2))
story.append(f.notes("notes_deviations", 55 * mm))

f.build(story, OUT, VERSION, VERSION_DATE)
print("written", os.path.normpath(OUT))
