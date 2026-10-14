"""Generate the SEASTRONG mangrove structure and topography field form (fillable PDF).

Usage:  python mangrove_field_form.py
Output: ../docs/_static/forms/mangrove_field_form_v<VERSION>.pdf

Bump VERSION (and VERSION_DATE) for every change; see README.md.
Requires: reportlab, pypdf.
"""
import os
from reportlab.platypus import Paragraph, Spacer, PageBreak, Table, TableStyle
from reportlab.lib.units import mm
from formlib import Form, H1, H2, SUB, S, N, W, COMMON_HELP, COMMON_CHOICES

VERSION = "1.0"
VERSION_DATE = "2026-10-14"
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "..", "docs", "_static", "forms", f"mangrove_field_form_v{VERSION}.pdf")

HELP = dict(COMMON_HELP)
HELP.update({
    "Transect ID": "e.g. BZ160327C1mangrove (automatic in Acrobat)",
    "Structure method": "A photogrammetry, B tree-by-tree, C manual",
    "Methods along the tape": "If more than one, e.g. A 0–12 m, C 12–30 m",
    "Low tide time": "Time of low water on the survey day",
    "Dominant species": "e.g. Rhizophora mangle",
    "Forest description": "Open or dense; pneumatophores or prop roots",
    "Vegetation changes along tape (m: description)": "e.g. 0–6 m pneumatophores only; 6–30 m dense prop roots",
    "Vegetation beyond the 30 m mark": "Short description of the 5–10 m beyond the tape",
    "Low-water mark: time": "Time when the low-water mark was identified",
    "Low-water mark: position": "Distance seaward of the 0 m mark (m)",
    "GNSS at start: lat, lon": "At the low-water mark",
    "GNSS at start: elevation (m)": "RTK only; leave empty with handheld GNSS",
    "GNSS type": "RTK or handheld",
    "Datum tie at this site": "RTK fix or benchmark, at least once per site",
    "Camera spacing (cm)": "Measured distance between the two lens centres",
    "Rig height above ground (m)": "About 1–1.5 m",
    "Cameras start time": "Time both cameras were started",
    "Cameras end time": "Time both cameras were stopped",
    "Trees in front plot (n)": "All trees rooted in the 5 m × 5 m plot",
    "Trees in centre plot (n)": "All trees rooted in the 5 m × 5 m plot",
    "Trees in back plot (n)": "All trees rooted in the 5 m × 5 m plot",
    "Survey complete (Y / N)": "Topography and the structure method completed",
    "Time on site (h)": "From arrival to departure",
    "Weather": "Sun, cloud, rain",
    "Ground conditions": "e.g. soft mud, firm sand, standing water",
    "Topography CSV prepared (Y / N)": "Stations typed into the CSV for the notebook",
    "Photos (n)": "Total number of photos from the survey",
    "Photo folder name": "Transect ID + _photos",
    "Slate / sheets photographed (Y / N)": "Photos of all paper sheets saved with the data",
})
CHOICES = dict(COMMON_CHOICES)
CHOICES.update({
    "Structure method": ["A", "B", "C", "A + C", "B + C", "A + B"],
    "GNSS type": ["RTK", "Handheld"],
    "Datum tie at this site": ["RTK fix", "Benchmark", "Done at another transect", "Not done"],
})
f = Form("Mangrove field form", "mangrove", HELP, CHOICES)
story = []

# ---------- page 1: header ----------
story += [Paragraph("Mangrove structure and topography: field form", H1),
          Paragraph("One form per transect. Print pages 1–2 (header and topography) for every transect, plus the pages of the "
                    "structure method used: A (page 3), B (page 4) or C (pages 5–6); page 7 is the post-site report, filled "
                    "in the same day. Fill it in with Adobe Acrobat Reader (free): the Transect ID is then filled in "
                    "automatically and the form is saved correctly. Method: Mangroves and Field transects pages of the "
                    "SEASTRONG Field Processing Tools documentation.", SUB)]
story.append(Paragraph("1. Transect header", H2))
story.append(f.fields(["Study area (BZ / SC / FJ)", "Corridor (C1–C6)", "Transect ID", "Date", "Operators", "Structure method",
                       "Sensor 1 ID (seaward)", "Sensor 1 position on tape (m)", "Sensor 2 ID (landward)", "Sensor 2 position on tape (m)",
                       "GPS point at 0 m end (lat, lon)", "Bearing 0 → 30 m (°)", "Time zone of watch / phone", "Low tide time",
                       "Dominant species", "Forest description"]))
story.append(Spacer(1, 3))
story.append(f.fields(["Methods along the tape", "Vegetation changes along tape (m: description)", "Vegetation beyond the 30 m mark"],
                      cols=1, multiline={"Vegetation changes along tape (m: description)": 12 * mm}))
story.append(Paragraph("2. Before starting", H2))
story.append(f.checklist([
    "Working at low tide, forest floor exposed",
    "30 m tape laid from sensor 1 (0 m, forest edge) to sensor 2 (30 m), straight and secured",
    "Overview photos of the transect taken from both ends",
    "Equipment for the topography: 50 m tape, clinometer, plastic board, station pegs, GNSS",
    "Equipment for the structure method (see the page of the method used)",
]))
story.append(PageBreak())

# ---------- page 2: topography ----------
story.append(Paragraph("3. Topography: from the low-water mark to 5–10 m beyond the 30 m mark", H2))
story.append(f.fields(["Low-water mark: time", "Low-water mark: position", "GNSS at start: lat, lon", "GNSS at start: elevation (m)",
                       "GNSS type", "Datum tie at this site"]))
story.append(Spacer(1, 3))
story.append(Paragraph("<b>Distance</b>: cumulative distance along the taut tape from the low-water mark (slope distance, m). "
                       "<b>Inclination</b>: slope of the segment leading to this station, clinometer on the plastic board "
                       "(°; <b>+ uphill landward</b>, − downhill landward; empty on the first row). <b>Label</b>: low water, 0 m, "
                       "sensor 1, sensor 2, 30 m, end. Stations at every change in slope and at most 2 m apart.", S))
story.append(Spacer(1, 3))
head = ["Station", "Distance (m)", "Inclination (°)", "Label"]
left = [[str(i + 1), None, None, None] for i in range(20)]
right = [[str(i + 21), None, None, None] for i in range(20)]
ex = ["", "", "", ""]
t1 = f.grid(head, 20, [0.08, 0.13, 0.13, 0.16], "topo_a", prefill=left, rh=6.6 * mm)
t2 = f.grid(head, 20, [0.08, 0.13, 0.13, 0.16], "topo_b", prefill=right, rh=6.6 * mm)
two = Table([[t1, t2]], colWidths=[W * 0.5, W * 0.5])
two.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"), ("LEFTPADDING", (0, 0), (-1, -1), 0)]))
story.append(two)
story.append(PageBreak())

# ---------- page 3: method A ----------
story.append(Paragraph("4. Method A: photogrammetry", H2))
story.append(f.fields(["Camera spacing (cm)", "Rig height above ground (m)", "Cameras start time", "Cameras end time"]))
story.append(Spacer(1, 4))
story.append(f.checklist([
    "Two cameras set to the same time (GoPro app); identical settings; white balance fixed; no red filter",
    "At least 6 scale bars on both sides of the tape, within ~2 m, varied orientation and elevation (used only for scaling)",
    "Pass 1: forward, camera A over the tape, cameras pointing down, ~0.3 m/s",
    "Pass 2: backward, camera A over the tape, cameras pointing down",
    "Pass 3: zigzag across the tape to ~3 m each side, cameras tilted ~45° forward",
    "Photos checked on both cameras: complete and sharp",
]))
story.append(Spacer(1, 4))
story.append(Paragraph("<b>Scale bars</b>: target codes of the bar, distance along the tape (m), side (L or R looking landward).", S))
story.append(Spacer(1, 3))
story.append(f.grid(["Bar", "Target codes", "Position on tape (m)", "Side (L/R)"], 10, [0.1, 0.35, 0.3, 0.25], "bar",
                    prefill=[[str(i + 1), None, None, None] for i in range(10)], example=["e.g.", "T01 / T02", "2.5", "L"]))
story.append(Spacer(1, 4))
story.append(f.fields(["Passes repeated? (which, why)"], cols=1))
story.append(PageBreak())

# ---------- page 4: method B ----------
story.append(Paragraph("5. Method B: tree-by-tree (Mori et al., 2022)", H2))
story.append(f.fields(["Trees in front plot (n)", "Trees in centre plot (n)", "Trees in back plot (n)", None]))
story.append(Spacer(1, 3))
story.append(Paragraph("At least 5 sample trees per plot, covering the range of sizes. Heights and lengths in cm, diameters in cm. "
                       "<b>H</b>: tree height · <b>CB</b>: crown-base height (lowest major branch) · <b>DBH</b>: at 1.3 m · "
                       "<b>D1</b>: trunk just above the roots · <b>Hroot</b>: top of the root system · <b>W1–W6</b>: trunk to outermost root "
                       "in six directions · <b>N</b>: prop roots reaching the ground · <b>d20</b>: mean root diameter at 20 cm · "
                       "<b>Ph</b>: root photos taken in two directions (Y/N).", S))
story.append(Spacer(1, 3))
headB = ["Plot", "Tree", "H", "CB", "DBH", "D1", "Hroot", "W1", "W2", "W3", "W4", "W5", "W6", "N", "d20", "Ph"]
wB = [0.07, 0.06] + [0.06] * 13 + [0.05]
wB = [x / sum(wB) for x in wB]
preB = [[p, str(t + 1)] + [None] * 14 for p in ("front", "centre", "back") for t in range(5)]
story.append(f.grid(headB, 15, wB, "treeB", prefill=preB, rh=7.5 * mm))
story.append(PageBreak())

# ---------- pages 5–6: method C ----------
story.append(Paragraph("6. Method C: manual measurements", H2))
story.append(Paragraph("<b>Density</b>: in each 5 m × 5 m plot, count all trees and measure the DBH of each (at 1.3 m, or 30 cm above "
                       "the highest prop root: write that height). <b>Pneumatophores</b>: one 1 m × 1 m quadrat per plot "
                       "(0.5 m × 0.5 m if too dense: write the size); count all, and measure height and diameter of up to 20.", S))
story.append(Spacer(1, 3))
headP = ["Plot", "Trees (n)", "Species", "DBH of each tree (cm)", "Quadrat size", "Pneumat. (n)", "Pneumat. heights / diameters (cm)"]
wP = [0.08, 0.08, 0.13, 0.27, 0.09, 0.09, 0.26]
story.append(f.grid(headP, 3, wP, "plotC", prefill=[["front"] + [None] * 6, ["centre"] + [None] * 6, ["back"] + [None] * 6], rh=30 * mm))
story.append(Spacer(1, 4))
story.append(Paragraph("<b>Sample trees</b> (3–5 per plot): at each height, the number of prop roots of this tree crossing that height, "
                       "their diameters (all, or up to 10), and the trunk diameter. Also record root-system height (Hroot), "
                       "crown-base height and tree height. Print this page twice for more than 3 trees per plot.", S))
story.append(PageBreak())
headC = ["Plot / tree", "Hroot / CB / H (cm)", "Height (cm)", "Roots crossing (n)", "Root diameters (cm)", "Trunk diam. (cm)"]
wC = [0.12, 0.17, 0.1, 0.12, 0.37, 0.12]
preC = []
for p in ("front", "centre", "back"):
    for t in range(1, 4):
        for k, h in enumerate(("25", "50", "75", "100", "150")):
            preC.append([f"{p} {t}" if k == 0 else "", None if k == 0 else "", h, None, None, None])
story.append(f.grid(headC, 45, wC, "treeC", prefill=preC, rh=5.6 * mm))
story.append(PageBreak())

# ---------- page 7: post-site report ----------
story.append(Paragraph("Post-site report", H1))
story.append(Paragraph("Filled in the same day, after downloading the data. Send it with the data to the data manager.", SUB))
story.append(Paragraph("A. Survey", H2))
story.append(f.fields(["Transect ID", "Date", "Filled in by", "Survey complete (Y / N)", "Time on site (h)", "Weather",
                       "Ground conditions", None]))
story.append(Paragraph("B. Data", H2))
story.append(f.fields(["Topography CSV prepared (Y / N)", "Photos (n)", "Photo folder name", "Slate / sheets photographed (Y / N)"]))
story.append(Spacer(1, 4))
story.append(f.fields(["Data download link"], cols=1))
story.append(Paragraph("C. Quality check (tick if a problem)", H2))
story.append(f.checklist(["Tide came in before the survey was finished", "Topography incomplete or stations missing",
                          "No GNSS fix at the start", "Plots or sample trees fewer than planned",
                          "Photos blurred or incomplete (method A or B)", "Measurements missing at some heights (method C)"]))
story.append(Paragraph("D. Deviations from the protocol, problems and notes", H2))
story.append(f.notes("notes_deviations", 32 * mm))

f.build(story, OUT, VERSION, VERSION_DATE)
print("written", os.path.normpath(OUT))
