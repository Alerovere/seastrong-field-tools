"""Shared building blocks for the SEASTRONG fillable field forms (reportlab + pypdf)."""
import os, re
from reportlab.lib.pagesizes import A4
from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
                                PageBreak, Flowable)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.units import mm
from pypdf import PdfReader, PdfWriter
from pypdf.generic import (NameObject, DictionaryObject, TextStringObject, ArrayObject,
                           BooleanObject)

INK = colors.HexColor("#1f2933"); ACC = colors.HexColor("#1f4e5f")
LIGHT = colors.HexColor("#e3eef2"); GRID = colors.HexColor("#9fb3bd"); FILL = colors.HexColor("#f4f9fb")
MUTE = "#5b6770"
_ss = getSampleStyleSheet()
H1 = ParagraphStyle("H1", parent=_ss["Title"], fontName="Helvetica-Bold", fontSize=16, textColor=ACC, alignment=0, spaceAfter=2)
SUB = ParagraphStyle("SUB", parent=_ss["Normal"], fontSize=8.5, textColor=colors.HexColor(MUTE), spaceAfter=6)
H2 = ParagraphStyle("H2", parent=_ss["Heading2"], fontName="Helvetica-Bold", fontSize=11.5, textColor=ACC, spaceBefore=8, spaceAfter=4)
N = ParagraphStyle("N", parent=_ss["Normal"], fontSize=9, leading=11.5, textColor=INK)
S = ParagraphStyle("S", parent=N, fontSize=8, leading=10)
W = A4[0] - 30 * mm

_names = set()
def uname(n):
    n = re.sub(r"[^A-Za-z0-9_]+", "_", n).strip("_").lower()[:40] or "f"
    b = n; i = 2
    while n in _names:
        n = f"{b}_{i}"; i += 1
    _names.add(n); return n

class Field(Flowable):
    """An AcroForm field placed inside the flow (text, choice or check box)."""
    def __init__(self, name, w, h, kind="text", options=None, multiline=False, tip=None):
        Flowable.__init__(self)
        self.name = uname(name); self.w = w; self.h = h; self.kind = kind
        self.options = options; self.multiline = multiline; self.tip = tip or name
    def wrap(self, aw, ah): return (self.w, self.h)
    def draw(self):
        f = self.canv.acroForm
        if self.kind == "check":
            f.checkbox(name=self.name, tooltip=self.tip, x=0, y=0, size=self.h, buttonStyle="check",
                       borderColor=INK, fillColor=colors.white, borderWidth=0.8, relative=True)
        elif self.kind == "choice":
            f.choice(name=self.name, tooltip=self.tip, value=" ", options=[" "] + self.options, x=0, y=0,
                     width=self.w, height=self.h, fontSize=8, borderWidth=0, fillColor=FILL, relative=True)
        else:
            f.textfield(name=self.name, tooltip=self.tip, x=0, y=0, width=self.w, height=self.h,
                        fontSize=9 if self.multiline else 8, borderWidth=0, fillColor=FILL,
                        fieldFlags="multiline" if self.multiline else "", relative=True)

class Form:
    def __init__(self, title, habitat_word, help=None, choices=None, id_label="Transect ID"):
        self.title = title; self.habitat = habitat_word
        self.id_label = id_label
        self.id_name = re.sub(r"[^A-Za-z0-9_]+", "_", id_label).strip("_").lower()
        self.help = help or {}; self.choices = choices or {}

    def label(self, f):
        h = self.help.get(f)
        return Paragraph(f"<b>{f}</b>" + (f"<br/><font size=6.5 color='{MUTE}'>{h}</font>" if h else ""), S)

    def fields(self, rows, cols=2, multiline=None):
        """Label/value table. rows: list of labels (None = empty cell)."""
        multiline = multiline or {}
        data = []; lw = W / cols
        for i in range(0, len(rows), cols):
            r = []
            for f in rows[i:i + cols]:
                if not f: r += ["", ""]; continue
                fw = lw * 0.62 - 6
                tip = f + (": " + self.help[f] if f in self.help else "")
                if f in self.choices: fld = Field(f, fw, 6 * mm, "choice", self.choices[f], tip=tip)
                elif "(Y / N)" in f: fld = Field(f, fw, 6 * mm, "choice", ["Y", "N"], tip=tip)
                elif f in multiline: fld = Field(f, fw, multiline[f], multiline=True, tip=tip)
                else: fld = Field(f, fw, 6 * mm, tip=tip)
                r += [self.label(f), fld]
            while len(r) < cols * 2: r += ["", ""]
            data.append(r)
        t = Table(data, colWidths=[lw * 0.38, lw * 0.62] * cols)
        st = [("VALIGN", (0, 0), (-1, -1), "MIDDLE"), ("GRID", (0, 0), (-1, -1), 0.5, GRID),
              ("TOPPADDING", (0, 0), (-1, -1), 3), ("BOTTOMPADDING", (0, 0), (-1, -1), 3)]
        for c in range(0, cols * 2, 2): st.append(("BACKGROUND", (c, 0), (c, -1), LIGHT))
        t.setStyle(TableStyle(st)); return t

    def checklist(self, items):
        data = [[Field("chk_" + re.sub("<[^>]+>", "", it)[:30], 4.2 * mm, 4.2 * mm, "check"), Paragraph(it, N)] for it in items]
        t = Table(data, colWidths=[8 * mm, W - 8 * mm])
        t.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "MIDDLE"), ("LINEBELOW", (0, 0), (-1, -1), 0.3, GRID),
                               ("TOPPADDING", (0, 0), (-1, -1), 3), ("BOTTOMPADDING", (0, 0), (-1, -1), 3)]))
        return t

    def grid(self, head, nrows, widths, prefix, prefill=None, rh=7 * mm, static_cols=(), example=None):
        """Table of fields. prefill: list of rows of fixed text (None = field).
        static_cols: column indexes that are never fields. example: one italic example row."""
        data = [[Paragraph(f"<b>{h}</b>", S) for h in head]]
        if example:
            data.append([Paragraph(f"<i>{v}</i>", S) for v in example])
        for i in range(nrows):
            row = []
            for k, h in enumerate(head):
                v = prefill[i][k] if prefill and i < len(prefill) else None
                if v is not None: row.append(Paragraph(v, S))
                elif k in static_cols: row.append("")
                else: row.append(Field(f"{prefix}_{i+1:02d}_{h}", widths[k] * W - 6, rh - 2.5 * mm))
            data.append(row)
        heights = [None] + ([None] if example else []) + [rh] * nrows
        t = Table(data, colWidths=[w * W for w in widths], rowHeights=heights, repeatRows=1)
        t.setStyle(TableStyle([("GRID", (0, 0), (-1, -1), 0.5, GRID), ("BACKGROUND", (0, 0), (-1, 0), LIGHT),
                               ("VALIGN", (0, 0), (-1, -1), "MIDDLE")]))
        return t

    def notes(self, name, h):
        t = Table([[Field(name, W - 8, h - 2 * mm, multiline=True)]], colWidths=[W], rowHeights=[h])
        t.setStyle(TableStyle([("BOX", (0, 0), (-1, -1), 0.5, GRID)])); return t

    def build(self, story, out, version, version_date):
        raw = os.path.join(os.path.dirname(os.path.abspath(__file__)), "_raw_form.pdf")
        os.makedirs(os.path.dirname(out), exist_ok=True)
        def footer(c, doc):
            c.saveState(); c.setFont("Helvetica", 7.5); c.setFillColor(colors.HexColor(MUTE))
            c.drawString(15 * mm, 10 * mm, f"SEASTRONG · {self.title} · v{version} ({version_date})")
            c.drawRightString(A4[0] - 15 * mm, 10 * mm, f"page {doc.page}")
            c.drawRightString(A4[0] - 15 * mm - 62 * mm, 10 * mm, f"{self.id_label}:")
            c.acroForm.textfield(name=f"footer_tid_{doc.page}", x=A4[0] - 15 * mm - 60 * mm, y=8.6 * mm,
                                 width=45 * mm, height=4.6 * mm, fontSize=7.5, borderWidth=0,
                                 fillColor=colors.white, textColor=INK)
            c.restoreState()
        doc = SimpleDocTemplate(raw, pagesize=A4, leftMargin=15 * mm, rightMargin=15 * mm,
                                topMargin=14 * mm, bottomMargin=16 * mm, title=self.title, author="SEASTRONG / UNIVE")
        doc.build(story, onFirstPage=footer, onLaterPages=footer)
        self._link_transect_id(raw, out, version)
        os.remove(raw)

    def _link_transect_id(self, raw, out, version):
        """Merge all Transect ID fields (header, report, footers) into one field,
        computed in Acrobat from study area + date (DDMMYY) + corridor + habitat."""
        w = PdfWriter(); w.append(PdfReader(raw))
        af = w._root_object["/AcroForm"]
        kids = ArrayObject(); keep = ArrayObject(); da = None
        for ref in af["/Fields"]:
            o = ref.get_object(); t = str(o.get("/T", ""))
            if t == self.id_name or t.startswith(self.id_name + "_") or t.startswith("footer_tid_"):
                kids.append(ref); da = da or o.get("/DA")
            else:
                keep.append(ref)
        calc = ('var a=this.getField("study_area_bz_sc_fj").valueAsString.replace(/\\s/g,"");'
                'var c=this.getField("corridor_c1_c6").valueAsString.replace(/\\s/g,"");'
                'var d=this.getField("date").valueAsString.replace(/\\s/g,"");var p=d.split("/");'
                'if(a&&c&&p.length==3){var mm=("0"+p[0]).slice(-2),dd=("0"+p[1]).slice(-2),yy=p[2].slice(-2);'
                f'event.value=a+dd+mm+yy+c+"{self.habitat}";}}else{{event.value="will autocompile";}}')
        parent = DictionaryObject()
        parent[NameObject("/FT")] = NameObject("/Tx"); parent[NameObject("/T")] = TextStringObject(self.id_name)
        parent[NameObject("/V")] = TextStringObject("will autocompile")
        if da: parent[NameObject("/DA")] = da
        parent[NameObject("/TU")] = TextStringObject(
            f"{self.id_label}: area + DDMMYY + corridor + {self.habitat} (automatic in Adobe Acrobat Reader)")
        js = DictionaryObject(); js[NameObject("/S")] = NameObject("/JavaScript"); js[NameObject("/JS")] = TextStringObject(calc)
        aa = DictionaryObject(); aa[NameObject("/C")] = js; parent[NameObject("/AA")] = aa
        pref = w._add_object(parent)
        for k in kids:
            o = k.get_object()
            for key in ("/T", "/FT", "/V", "/TU", "/Ff"):
                if key in o: del o[key]
            o[NameObject("/Parent")] = pref
        parent[NameObject("/Kids")] = kids
        keep.append(pref)
        af[NameObject("/Fields")] = keep
        af[NameObject("/CO")] = ArrayObject([pref])
        af[NameObject("/NeedAppearances")] = BooleanObject(True)
        w.add_metadata({"/Title": f"{self.title} v{version}", "/Author": "SEASTRONG / UNIVE"})
        os.makedirs(os.path.dirname(out), exist_ok=True)
        w.write(out)

COMMON_HELP = {
    "Study area (BZ / SC / FJ)": "Belize, Seychelles or Fiji",
    "Corridor (C1–C6)": "Corridor number in the study area",
    "Date": "Survey date, as mm/dd/yyyy",
    "Operators": "Names of the people in the field",
    "Sensor 1 ID (seaward)": "Serial number of the seaward pressure sensor",
    "Sensor 1 position on tape (m)": "Distance along the tape, e.g. 0",
    "Sensor 2 ID (landward)": "Serial number of the landward pressure sensor",
    "Sensor 2 position on tape (m)": "Distance along the tape, e.g. 30",
    "GPS point at 0 m end (lat, lon)": "One approximate point at the 0 m end",
    "Bearing 0 → 30 m (°)": "Compass bearing from 0 m towards 30 m",
    "Time zone of watch / phone": "Clock used for the times, e.g. UTC-6",
    "Filled in by": "Who fills in this report",
    "Data download link": "Link to the shared folder with all data, photos and this form",
}
COMMON_CHOICES = {
    "Study area (BZ / SC / FJ)": ["BZ", "SC", "FJ"],
    "Corridor (C1–C6)": ["C1", "C2", "C3", "C4", "C5", "C6"],
}
