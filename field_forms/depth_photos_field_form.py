"""Generate the SEASTRONG depth and bottom photos field form (fillable PDF).

Usage:  python depth_photos_field_form.py
Output: ../docs/_static/forms/depth_photos_field_form_v<VERSION>.pdf

Bump VERSION (and VERSION_DATE) for every change; see README.md.
Requires: reportlab, pypdf.
"""
import os
from reportlab.platypus import Paragraph, Spacer, PageBreak
from reportlab.lib.units import mm
from formlib import Form, H1, H2, SUB, S, W, COMMON_HELP, COMMON_CHOICES

VERSION = "1.2"
VERSION_DATE = "2026-10-15"
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "..", "docs", "_static", "forms", f"depth_photos_field_form_v{VERSION}.pdf")

HELP = dict(COMMON_HELP)
HELP.update({
    "Survey ID": "e.g. BZ140327C1bathy (automatic in Acrobat)",
    "Operators": "Swimmer and surface support",
    "Time zone of watch / phone": "Time zone of the GNSS and the phone, e.g. UTC-6",
    "Data collected": "Depth and photos, depth only, or photos only",
    "GNSS ID": "Label or serial number of the handheld GNSS",
    "Echosounder ID": "Serial number or label of the Deeper Pro",
    "Camera ID": "Label of the camera used",
    "Photo interval (s)": "Timelapse interval set on the camera, e.g. 1",
    "Tide during the survey": "Rising, falling, high or low",
    "Water clarity": "Clear, moderate or turbid",
    "Start reference photo: GPS time shown": "Time on the GNSS screen in the photo (hh:mm:ss)",
    "Survey start time": "Time when recording was started",
    "Survey end time": "Time when recording was stopped",
    "End reference photo: GPS time shown": "Time on the GNSS screen in the photo (hh:mm:ss)",
    "Survey complete (Y / N)": "Whole corridor covered as planned",
    "Time in the water (h)": "From entering to leaving the water",
    "Waves": "Calm, moderate or strong",
    "Current": "None, weak or strong",
    "Scan exported (CSV) (Y / N)": "Scan exported from the Deeper app",
    "GPS track exported (GPX) (Y / N)": "Track exported from the handheld GNSS",
    "Photos (n)": "Number of photos downloaded from the camera",
    "Photo folder name": "Survey ID + _photos",
})
CHOICES = dict(COMMON_CHOICES)
CHOICES.update({"Data collected": ["Depth + photos", "Depth only", "Photos only"],
                "Tide during the survey": ["Rising", "Falling", "High", "Low"],
                "Water clarity": ["Clear", "Moderate", "Turbid"]})
f = Form("Depth and bottom photos field form", "bathy", HELP, CHOICES, id_label="Survey ID")
story = []

# ---------- page 1 ----------
story += [Paragraph("Depth and bottom photos: field form", H1),
          Paragraph("One form per survey. Page 1 is used in the field; page 2 is the post-site report, filled in the same day. "
                    "Fill it in with Adobe Acrobat Reader (free): the Survey ID is then filled in automatically and the form is "
                    "saved correctly. Method: Depth and bottom photos page of the SEASTRONG Field Processing Tools documentation.", SUB)]
story.append(Paragraph("1. Survey header", H2))
story.append(f.fields(["Study area (BZ / SC / FJ)", "Corridor (C1–C6)", "Survey ID", "Date", "Operators", "Time zone of watch / phone",
                       "Data collected", "Echosounder ID", "Camera ID", "GNSS ID", "Photo interval (s)", "Tide during the survey", "Water clarity"]))
story.append(Paragraph("2. Set-up", H2))
story.append(f.checklist([
    "Echosounder mounted under the kickboard, always under water",
    "Camera mounted under the kickboard, pointing straight down; timelapse mode; memory card empty",
    "Depth: phone charged, in a waterproof case; Deeper app connected; phone GPS fixed",
    "Photos: handheld GNSS recording a track (1 s), fix OK, on top of the board in a waterproof bag",
    "Scan started in the Deeper app, GNSS track started, camera started",
]))
story.append(Paragraph("3. Reference photos (clock synchronisation)", H2))
story.append(Paragraph("Hold the handheld GNSS screen showing the time under the camera and let it take a photo, at the start and at the end "
                       "of the survey. Write the time shown on the screen.", S))
story.append(Spacer(1, 3))
story.append(f.fields(["Start reference photo: GPS time shown", "End reference photo: GPS time shown"]))
story.append(Paragraph("4. Survey times and notes", H2))
story.append(f.fields(["Survey start time", "Survey end time"]))
story.append(Spacer(1, 4))
story.append(Paragraph("Notes: interruptions, problems, anything unusual.", S))
story.append(f.notes("notes_field", 35 * mm))
story.append(PageBreak())

# ---------- page 2: post-site report ----------
story.append(Paragraph("Post-site report", H1))
story.append(Paragraph("Filled in the same day, after downloading the data. Send it with the data to the data manager.", SUB))
story.append(Paragraph("A. Survey", H2))
story.append(f.fields(["Survey ID", "Date", "Filled in by", "Survey complete (Y / N)", "Time in the water (h)", "Waves",
                       "Current", None]))
story.append(Paragraph("B. Data", H2))
story.append(f.fields(["Scan exported (CSV) (Y / N)", "GPS track exported (GPX) (Y / N)", "Photos (n)", "Photo folder name"]))
story.append(Spacer(1, 4))
story.append(f.fields(["Data download link"], cols=1))
story.append(Paragraph("C. Quality check (tick if a problem)", H2))
story.append(f.checklist(["No GPS fix for part of the survey", "Reference photo missing or GPS time not readable",
                          "Camera stopped or memory card full", "Photos blurred, dark or turbid",
                          "Echosounder out of the water for part of a track (waves)", "Planned tracks not completed"]))
story.append(Paragraph("D. Deviations from the protocol, problems and notes", H2))
story.append(f.notes("notes_deviations", 40 * mm))

f.build(story, OUT, VERSION, VERSION_DATE)
print("written", os.path.normpath(OUT))
