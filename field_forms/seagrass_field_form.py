"""Generate the SEASTRONG seagrass structure and bathymetry field form (fillable PDF).

Usage:  python seagrass_field_form.py
Output: ../docs/_static/forms/seagrass_field_form_v<VERSION>.pdf

Bump VERSION (and VERSION_DATE) for every change; see README.md.
Requires: reportlab, pypdf.
"""
import os
from reportlab.platypus import Paragraph, Spacer, PageBreak, Table, TableStyle, KeepTogether
from reportlab.lib.units import mm
from formlib import Form, Field, H1, H2, SUB, S, N, W, GRID, LIGHT, COMMON_HELP, COMMON_CHOICES

VERSION = "1.0"
VERSION_DATE = "2026-10-14"
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "..", "docs", "_static", "forms", f"seagrass_field_form_v{VERSION}.pdf")

HELP = dict(COMMON_HELP)
HELP.update({
    "Transect ID": "e.g. BZ150327C1seagrass (automatic in Acrobat)",
    "Operators": "Recorder (A) and photographer (B)",
    "GPS point at 0 m end (lat, lon)": "One approximate point at the surface above 0 m",
    "Slack water time": "Expected slack water on the survey day",
    "Dominant species": "Species measured in the quadrats, e.g. Thalassia testudinum",
    "Other species": "Other seagrass species present on the transect",
    "Meadow changes along tape (m: description)": "e.g. 0–6 m continuous; 6–10 m bare sand; 10–30 m patchy",
    "Survey complete (Y / N)": "Depth stops and all 9 quadrats done",
    "Time in the water (h)": "From entering to leaving the water",
    "Visibility (m)": "Estimated horizontal visibility",
    "Current": "None, weak or strong",
    "Cover photos (n)": "Vertical photos taken at the 2 m stops",
    "Quadrat photos (n)": "Photo 1 + Photo 2 of the 9 quadrats (18 expected)",
    "Photo folder name": "Transect ID + _photos",
    "Slate photographed (Y / N)": "Photo of the slate saved with the data",
})
f = Form("Seagrass field form", "seagrass", HELP, dict(COMMON_CHOICES))
story = []

# ---------- page 1 ----------
story += [Paragraph("Seagrass structure and bathymetry: field form", H1),
          Paragraph("One form per transect. Pages 1–5 are used in the water (print on waterproof paper or copy onto the slate); "
                    "page 6 is the post-site report, filled in the same day. Fill it in with Adobe Acrobat Reader (free): the "
                    "Transect ID is then filled in automatically and the form is saved correctly. Nothing is collected. Method: "
                    "Seagrass and Field transects pages of the SEASTRONG Field Processing Tools documentation.", SUB)]
story.append(Paragraph("1. Transect header", H2))
story.append(f.fields(["Study area (BZ / SC / FJ)", "Corridor (C1–C6)", "Transect ID", "Date", "Operators", "Time zone of watch / phone",
                       "Sensor 1 ID (seaward)", "Sensor 1 position on tape (m)", "Sensor 2 ID (landward)", "Sensor 2 position on tape (m)",
                       "GPS point at 0 m end (lat, lon)", "Bearing 0 → 30 m (°)", "Slack water time", None,
                       "Dominant species", "Other species"]))
story.append(Spacer(1, 3))
story.append(f.fields(["Meadow changes along tape (m: description)"], cols=1,
                      multiline={"Meadow changes along tape (m: description)": 12 * mm}))
story.append(Paragraph("2. Before going in the water", H2))
story.append(f.checklist([
    "Around slack water; visibility and current OK for snorkelling",
    "30 m tape laid on the bottom from sensor 1 (0 m, seaward) to sensor 2 (30 m), and on for 5–10 m",
    "Two 25 cm × 25 cm frames with marked points; graduated stick or depth gauge; camera",
    "Slate with mm ruler; plastic caliper; pencils",
    "Roles agreed: A recorder (depths, shoots, slate), B photographer (frames, photos, canopy height, thickness)",
]))
story.append(PageBreak())

# ---------- page 2: depth and cover ----------
story.append(Paragraph("3. Depth and cover: every 2 m, at each sensor, and 5–10 m beyond the 30 m mark", H2))
story.append(Paragraph("<b>Depth</b>: graduated stick or gauge on the bottom next to the tape (m). <b>Time</b>: of the reading, for the "
                       "tide correction. <b>Photo</b>: one vertical photo of the bottom from ~1 m above, tape in view (tick when taken). "
                       "<b>Cover</b>: bare, patchy or continuous (optional, can be done later from the photo).", S))
story.append(Spacer(1, 3))
head = ["Tape (m)", "Depth (m)", "Time", "Photo", "Cover"]
wd = [0.09, 0.1, 0.1, 0.07, 0.13]
st = [str(d) for d in range(0, 42, 2)]
left = [[s, None, None, None, None] for s in st[:12]]
right = [[s, None, None, None, None] for s in st[12:]] + [["sensor 1", None, None, None, None], ["sensor 2", None, None, None, None]]
t1 = f.grid(head, 12, wd, "depth_a", prefill=left, rh=7.2 * mm)
t2 = f.grid(head, 11, wd, "depth_b", prefill=right, rh=7.2 * mm)
two = Table([[t1, t2]], colWidths=[W * 0.5, W * 0.5])
two.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"), ("LEFTPADDING", (0, 0), (-1, -1), 0)]))
story.append(two)
story.append(PageBreak())

# ---------- pages 3–5: quadrats ----------
def quadrat(code, pos_label, default_pos):
    """One quadrat block: position, canopy height, photos, 5 shoots, one thickness stack."""
    p = code.replace("-", "").lower()
    def fl(name, w, h=5.5 * mm, kind="text", opts=None, tip=None):
        return Field(f"q{p}_{name}", w, h, kind, opts, tip=tip or name)
    lab = lambda t: Paragraph(f"<b>{t}</b>", S)
    top = [
        [Paragraph(f"<b>Quadrat {code}</b><br/><font size=6.5 color='#5b6770'>{pos_label}</font>", S),
         lab("Position on tape (m)"), fl("position", 0.12 * W - 6, tip="Distance along the tape (planned: " + default_pos + " m)"),
         lab("Moved to reach seagrass (m)"), fl("moved", 0.1 * W - 6, tip="0 if not moved"),
         lab("Photo 1 / Photo 2"), Table([[fl("photo1", 4.2 * mm, 4.2 * mm, "check"), fl("photo2", 4.2 * mm, 4.2 * mm, "check")]],
                                         colWidths=[8 * mm, 8 * mm])],
        ["", lab("Canopy height (cm) 1 / 2 / 3"),
         Table([[fl("canopy1", 0.029 * W), fl("canopy2", 0.029 * W), fl("canopy3", 0.029 * W)]], colWidths=[0.032 * W] * 3, style=[("LEFTPADDING", (0, 0), (-1, -1), 0), ("RIGHTPADDING", (0, 0), (-1, -1), 0)]),
         lab("Other species"), fl("other_species", 0.1 * W - 6),
         lab("Thickness: stack (mm) / blades (n)"),
         Table([[fl("stack_mm", 0.06 * W), fl("stack_n", 0.05 * W)]], colWidths=[0.066 * W, 0.055 * W], style=[("LEFTPADDING", (0, 0), (-1, -1), 0), ("RIGHTPADDING", (0, 0), (-1, -1), 0)])],
    ]
    t = Table(top, colWidths=[0.14 * W, 0.15 * W, 0.12 * W, 0.15 * W, 0.1 * W, 0.18 * W, 0.16 * W])
    t.setStyle(TableStyle([("GRID", (0, 0), (-1, -1), 0.5, GRID), ("BACKGROUND", (0, 0), (0, -1), LIGHT),
                           ("VALIGN", (0, 0), (-1, -1), "MIDDLE"), ("SPAN", (0, 0), (0, 1))]))
    rows = [[lab("Shoot"), lab("Blades (n)"), lab("Longest blade: length (cm)"), lab("Longest blade: width at mid-length (mm)")]]
    for i in range(5):
        rows.append([Paragraph(str(i + 1), S), fl(f"shoot{i+1}_blades", 0.2 * W - 6), fl(f"shoot{i+1}_length_cm", 0.3 * W - 6),
                     fl(f"shoot{i+1}_width_mm", 0.36 * W - 6)])
    s = Table(rows, colWidths=[0.14 * W, 0.2 * W, 0.3 * W, 0.36 * W], rowHeights=[None] + [6.4 * mm] * 5)
    s.setStyle(TableStyle([("GRID", (0, 0), (-1, -1), 0.5, GRID), ("BACKGROUND", (0, 0), (-1, 0), LIGHT),
                           ("VALIGN", (0, 0), (-1, -1), "MIDDLE")]))
    return KeepTogether([t, s, Spacer(1, 7)])

positions = [("FRONT", "2.5"), ("CENTRE", "15"), ("BACK", "27.5")]
first = True
for name, pos in positions:
    if not first: story.append(PageBreak())
    first = False
    story.append(Paragraph(f"4. Quadrats at the {name.lower()} ({pos} m): left (2 m), centre (at the tape), right (2 m)", H2))
    story.append(Paragraph("Always on seagrass: if the planned spot is bare, move along the same line to the nearest seagrass and write "
                           "the distance moved. <b>Canopy height</b>: undisturbed canopy at 3 points around the frame. <b>Photo 1</b>: "
                           "canopy, straight down. <b>Photo 2</b>: shoot bases with leaves pushed aside. <b>Shoots</b>: 5 shoots of the "
                           "dominant species nearest to the marked points, measured in place, longest blade held straight along the "
                           "ruler. <b>Thickness</b>: all blades of one shoot held together at mid-length, plastic caliper.", S))
    story.append(Spacer(1, 4))
    for side, lbl in (("L", "left, 2 m"), ("C", "centre, at the tape"), ("R", "right, 2 m")):
        story.append(quadrat(f"{name[0]}-{side}", f"{name.lower()}, {lbl}", pos))
story.append(PageBreak())

# ---------- page 6: post-site report ----------
story.append(Paragraph("Post-site report", H1))
story.append(Paragraph("Filled in the same day, after downloading the data. Send it with the data to the data manager.", SUB))
story.append(Paragraph("A. Survey", H2))
story.append(f.fields(["Transect ID", "Date", "Filled in by", "Survey complete (Y / N)", "Time in the water (h)", "Visibility (m)",
                       "Current", None]))
story.append(Paragraph("B. Data", H2))
story.append(f.fields(["Cover photos (n)", "Quadrat photos (n)", "Photo folder name", "Slate photographed (Y / N)"]))
story.append(Spacer(1, 4))
story.append(f.fields(["Data download link"], cols=1))
story.append(Paragraph("C. Quality check (tick if a problem)", H2))
story.append(f.checklist(["Shoot bases not visible in some Photo 2", "Quadrats moved far from the planned position",
                          "Depth stops missing", "Shoots or thickness missing in some quadrats",
                          "Strong current or poor visibility during the survey", "Tide changed a lot during the survey"]))
story.append(Paragraph("D. Deviations from the protocol, problems and notes", H2))
story.append(f.notes("notes_deviations", 34 * mm))

f.build(story, OUT, VERSION, VERSION_DATE)
print("written", os.path.normpath(OUT))
