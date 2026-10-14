"""Generate the SEASTRONG drone survey field form (fillable PDF).

Usage:  python drone_field_form.py
Output: ../docs/_static/forms/drone_field_form_v<VERSION>.pdf

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
OUT = os.path.join(HERE, "..", "docs", "_static", "forms", f"drone_field_form_v{VERSION}.pdf")

HELP = dict(COMMON_HELP)
HELP.update({
    "Survey ID": "e.g. BZ150327C1drone (automatic in Acrobat)",
    "Operators": "Pilot and observer",
    "Time zone of watch / phone": "Clock used for the times, e.g. UTC-6",
    "Drone model": "Make and model of the drone",
    "Take-off point (lat, lon)": "Approximate position of the take-off point",
    "Tide": "Rising, falling, high or low",
    "Weather": "Clear, thin overcast, scattered clouds, overcast",
    "Wind": "Calm, light, moderate or strong",
    "Sea surface": "Calm, ripples or waves",
    "Sun glint": "None, some or strong",
    "Survey complete (Y / N)": "Whole planned area flown",
    "Flights (n)": "Number of flights (batteries)",
    "Photos (n)": "Total number of photos downloaded",
    "Photo folder name": "Survey ID + _photos",
    "Target positions saved (Y / N)": "Handheld GNSS points or table on page 1",
})
CHOICES = dict(COMMON_CHOICES)
CHOICES.update({"Tide": ["Rising", "Falling", "High", "Low"],
                "Weather": ["Clear", "Thin overcast", "Scattered clouds", "Overcast"],
                "Wind": ["Calm", "Light", "Moderate", "Strong"],
                "Sea surface": ["Calm", "Ripples", "Waves"],
                "Sun glint": ["None", "Some", "Strong"]})
f = Form("Drone field form", "drone", HELP, CHOICES, id_label="Survey ID")
story = []

# ---------- page 1 ----------
story += [Paragraph("Drone survey: field form", H1),
          Paragraph("One form per survey (one corridor, one day). Page 1 is used in the field; page 2 is the post-site report, "
                    "filled in the same day. Fill it in with Adobe Acrobat Reader (free): the Survey ID is then filled in "
                    "automatically and the form is saved correctly. Method: Drone survey page of the SEASTRONG Field Processing "
                    "Tools documentation.", SUB)]
story.append(Paragraph("1. Survey header", H2))
story.append(f.fields(["Study area (BZ / SC / FJ)", "Corridor (C1–C6)", "Survey ID", "Date", "Operators",
                       "Time zone of watch / phone", "Drone model", "Take-off point (lat, lon)",
                       "Tide", "Weather", "Wind", "Sea surface"]))
story.append(Paragraph("2. Flights", H2))
story.append(Paragraph("One row per flight (battery). <b>Altitude</b>: above take-off. <b>Overlap</b>: along / across track, in %.", S))
story.append(Spacer(1, 3))
story.append(f.grid(["Flight", "Start", "End", "Altitude (m)", "Overlap (%)", "Photos (n)", "Notes"], 6,
                    [0.08, 0.1, 0.1, 0.12, 0.13, 0.11, 0.36], "flight",
                    prefill=[[str(i + 1)] + [None] * 6 for i in range(6)], rh=7.5 * mm,
                    example=["e.g.", "07:40", "07:58", "80", "80 / 80", "412", "glint on last lines"]))
story.append(Paragraph("3. Ground targets", H2))
story.append(Paragraph("4–5 targets on land or emergent reef, spread across the area. Position with handheld GNSS, averaged for about a minute.", S))
story.append(Spacer(1, 3))
story.append(f.grid(["Target", "Latitude", "Longitude", "Notes"], 5, [0.1, 0.25, 0.25, 0.4], "target",
                    prefill=[[f"T{i + 1}"] + [None] * 3 for i in range(5)], rh=7 * mm))
story.append(PageBreak())

# ---------- page 2: post-site report ----------
story.append(Paragraph("Post-site report", H1))
story.append(Paragraph("Filled in the same day, after downloading the data. Send it with the data to the data manager.", SUB))
story.append(Paragraph("A. Survey", H2))
story.append(f.fields(["Survey ID", "Date", "Filled in by", "Survey complete (Y / N)", "Flights (n)", "Sun glint"]))
story.append(Paragraph("B. Data", H2))
story.append(f.fields(["Photos (n)", "Photo folder name", "Target positions saved (Y / N)", None]))
story.append(Spacer(1, 4))
story.append(f.fields(["Data download link"], cols=1))
story.append(Paragraph("C. Quality check (tick if a problem)", H2))
story.append(f.checklist(["Sun glint on part of the photos", "Waves or ripples blur the bottom",
                          "Cloud shadows on part of the area", "Gaps in the coverage (missed lines, aborted flight)",
                          "Fewer than 4 ground targets, or targets not visible", "Photos blurred or over- / under-exposed"]))
story.append(Paragraph("D. Deviations from the protocol, problems and notes", H2))
story.append(f.notes("notes_deviations", 45 * mm))

f.build(story, OUT, VERSION, VERSION_DATE)
print("written", os.path.normpath(OUT))
