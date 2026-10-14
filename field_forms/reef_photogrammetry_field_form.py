"""Generate the SEASTRONG reef photogrammetry field form (fillable PDF).

Usage:  python reef_photogrammetry_field_form.py
Output: ../docs/_static/forms/reef_photogrammetry_field_form_v<VERSION>.pdf

Bump VERSION (and VERSION_DATE) for every change, so that the new file gets a new
name and browsers do not show a cached copy. Update the links in the docs pages.
Requires: reportlab, pypdf.
"""
import os, sys
VERSION="1.0"
VERSION_DATE="2026-10-14"
HERE=os.path.dirname(os.path.abspath(__file__))
OUT=os.path.join(HERE,"..","docs","_static","forms",f"reef_photogrammetry_field_form_v{VERSION}.pdf")
RAW=os.path.join(HERE,"_raw_form.pdf")
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, KeepTogether
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.units import mm

INK=colors.HexColor("#1f2933"); ACC=colors.HexColor("#1f4e5f"); LIGHT=colors.HexColor("#e3eef2"); GRID=colors.HexColor("#9fb3bd")
ss=getSampleStyleSheet()
H1=ParagraphStyle("H1",parent=ss["Title"],fontName="Helvetica-Bold",fontSize=16,textColor=ACC,alignment=0,spaceAfter=2)
SUB=ParagraphStyle("SUB",parent=ss["Normal"],fontSize=8.5,textColor=colors.HexColor("#5b6770"),spaceAfter=6)
H2=ParagraphStyle("H2",parent=ss["Heading2"],fontName="Helvetica-Bold",fontSize=11.5,textColor=ACC,spaceBefore=8,spaceAfter=4)
N=ParagraphStyle("N",parent=ss["Normal"],fontSize=9,leading=11.5,textColor=INK)
S=ParagraphStyle("S",parent=N,fontSize=8,leading=10)
W=A4[0]-30*mm
from reportlab.platypus import Flowable
import re
_names=set()
def uname(n):
    n=re.sub(r'[^A-Za-z0-9_]+','_',n).strip('_').lower()[:40] or 'f'
    b=n;i=2
    while n in _names: n=f"{b}_{i}"; i+=1
    _names.add(n); return n
FILL=colors.HexColor("#f4f9fb")
class Field(Flowable):
    def __init__(self,name,w,h,kind="text",options=None,multiline=False,tip=None):
        Flowable.__init__(self); self.name=uname(name); self.w=w; self.h=h; self.kind=kind; self.options=options; self.multiline=multiline; self.tip=tip or name
    def wrap(self,aw,ah): return (self.w,self.h)
    def draw(self):
        f=self.canv.acroForm
        if self.kind=="check":
            f.checkbox(name=self.name,tooltip=self.tip,x=0,y=0,size=self.h,buttonStyle="check",borderColor=INK,fillColor=colors.white,borderWidth=0.8,relative=True)
        elif self.kind=="choice":
            f.choice(name=self.name,tooltip=self.tip,value=" ",options=[" "]+self.options,x=0,y=0,width=self.w,height=self.h,fontSize=8,borderWidth=0,fillColor=FILL,relative=True)
        else:
            f.textfield(name=self.name,tooltip=self.tip,x=0,y=0,width=self.w,height=self.h,fontSize=8 if not self.multiline else 9,borderWidth=0,fillColor=FILL,
                        fieldFlags="multiline" if self.multiline else "",relative=True)
CHOICES={"Study area (BZ / SC / FJ)":["BZ","SC","FJ"],"Corridor (C1–C6)":["C1","C2","C3","C4","C5","C6"],"Snorkel / scuba":["Snorkel","Scuba"],
 "Tide (rising / falling / slack)":["Rising","Falling","Slack"]}
def yn(label): return "(Y / N)" in label



HELP={
"Study area (BZ / SC / FJ)":"Belize, Seychelles or Fiji",
"Corridor (C1–C6)":"Corridor number in the study area",
"Transect ID":"e.g. BZ140327C1reef (automatic in Acrobat)",
"Date":"Survey date, as mm/dd/yyyy",
"Operators":"Names of the people in the water",
"Snorkel / scuba":"How the photo passes were swum",
"Sensor 1 ID (seaward)":"Serial number of the seaward pressure sensor",
"Sensor 1 position on tape (m)":"Distance along the tape, e.g. -1",
"Sensor 2 ID (landward)":"Serial number of the landward pressure sensor",
"Sensor 2 position on tape (m)":"Distance along the tape, e.g. 31",
"GPS point above 0 m end (lat, lon)":"One approximate point at the surface above 0 m",
"Bearing 0 → 30 m (°)":"Compass bearing from 0 m towards 30 m",
"Camera spacing (cm)":"Measured distance between the two lens centres",
"Swimming height (m)":"Height of the rig above the bottom, ~1.5–2 m",
"Time zone of watch / phone":"Clock used for depth times, e.g. UTC+12",
"Tide (rising / falling / slack)":"Tide stage during the survey",
"Habitat changes along tape (m: description)":"e.g. 0–8 m coral; 8–14 m sand; 14–30 m coral",
"Cameras start time":"Time both cameras were started",
"Cameras end time":"Time both cameras were stopped",
"Passes repeated? (which, why)":"e.g. pass 1 repeated, housing fogged",
"Survey complete (Y / N)":"All passes, targets and depths done",
"Time in the water (h)":"From entering to leaving the water",
"Visibility (m)":"Estimated horizontal visibility",
"Waves / surge":"Calm, moderate or strong",
"Cloud / caustics":"Overcast or sunny; caustics yes or no",
"Current":"None, weak or strong",
"Photos camera A (n)":"Number of photos downloaded from camera A",
"Photos camera B (n)":"Number of photos downloaded from camera B",
"Folder name camera A":"Transect ID + _camA",
"Folder name camera B":"Transect ID + _camB",
"Target depths complete (Y / N)":"Three readings and time for every target",
"Depth profile complete (Y / N)":"Every 2 m, both sensors and beyond 30 m",
"Slate photo saved (Y / N)":"Photo of the slate saved with the data",
"Field sheet copied (Y / N)":"Slate data typed into this form",
"Data download link":"Link to the shared folder with photos, slate photo and this form",
"Filled in by":"Who fills in this report",
}
HS=ParagraphStyle("HS",parent=S,fontSize=6.5,leading=8,textColor=colors.HexColor("#5b6770"))
def label(f):
    h=HELP.get(f)
    return Paragraph(f"<b>{f}</b>"+(f"<br/><font size=6.5 color='#5b6770'>{h}</font>" if h else ""),S)

def header_fields(rows, cols=2):
    data=[]; 
    for i in range(0,len(rows),cols):
        r=[]
        lw0=W/cols
        for f in rows[i:i+cols]:
            if not f: r+=["",""]; continue
            fw=lw0*0.62-6
            tip=f+(": "+HELP[f] if f in HELP else "")
            if f in CHOICES: fld=Field(f,fw,6*mm,"choice",CHOICES[f],tip=tip)
            elif yn(f): fld=Field(f,fw,6*mm,"choice",["Y","N"],tip=tip)
            else: fld=Field(f,fw,6*mm,tip=tip)
            r+= [label(f),fld]
        while len(r)<cols*2: r+=["",""]
        data.append(r)
    lw=W/cols
    t=Table(data,colWidths=[lw*0.38,lw*0.62]*cols)
    st=[("VALIGN",(0,0),(-1,-1),"MIDDLE"),("GRID",(0,0),(-1,-1),0.5,GRID),("TOPPADDING",(0,0),(-1,-1),3),("BOTTOMPADDING",(0,0),(-1,-1),3)]
    for c in range(0,cols*2,2): st.append(("BACKGROUND",(c,0),(c,-1),LIGHT))
    t.setStyle(TableStyle(st)); return t

def checklist(items):
    data=[["",Paragraph(i,N)] for i in items]
    t=Table(data,colWidths=[8*mm,W-8*mm])
    st=[("VALIGN",(0,0),(-1,-1),"MIDDLE"),("LINEBELOW",(0,0),(-1,-1),0.3,GRID),("TOPPADDING",(0,0),(-1,-1),3),("BOTTOMPADDING",(0,0),(-1,-1),3)]
    t.setStyle(TableStyle(st))
    # draw boxes in first column
    class Box(Table): pass
    for r in range(len(items)):
        data[r][0]=Field("chk_"+re.sub('<[^>]+>','',items[r])[:30],4.2*mm,4.2*mm,"check")
    t=Table(data,colWidths=[8*mm,W-8*mm]); t.setStyle(TableStyle(st)); return t

def grid(head, nrows, widths, prefill=None, rh=7.5*mm, prefix="row", fill_from=0):
    data=[[Paragraph(f"<b>{h}</b>",S) for h in head]]
    for i in range(nrows):
        row=[Field(f"{prefix}_{i+1:02d}_{h}",widths[k]*W-6,rh-2.5*mm) if i>=fill_from else "" for k,h in enumerate(head)]
        if prefill and i<len(prefill):
            for k,v in enumerate(prefill[i]):
                if v is not None: row[k]=Paragraph(v,S)
        data.append(row)
    t=Table(data,colWidths=[w*W for w in widths],rowHeights=[None]+[rh]*nrows,repeatRows=1)
    t.setStyle(TableStyle([("GRID",(0,0),(-1,-1),0.5,GRID),("BACKGROUND",(0,0),(-1,0),LIGHT),("VALIGN",(0,0),(-1,-1),"MIDDLE")]))
    return t

def footer(c,doc):
    c.saveState(); c.setFont("Helvetica",7.5); c.setFillColor(colors.HexColor("#5b6770"))
    c.drawString(15*mm,10*mm,f"SEASTRONG · Reef photogrammetry field form · v{VERSION} ({VERSION_DATE})")
    c.drawRightString(A4[0]-15*mm,10*mm,f"page {doc.page}")
    c.drawRightString(A4[0]-15*mm-62*mm,10*mm,"Transect ID:")
    c.acroForm.textfield(name=f"footer_tid_{doc.page}",x=A4[0]-15*mm-60*mm,y=8.6*mm,width=45*mm,height=4.6*mm,fontSize=7.5,borderWidth=0,fillColor=colors.white,textColor=INK)
    c.restoreState()

story=[]
story+= [Paragraph("Reef photogrammetry: field form",H1),
 Paragraph("One form per transect. Pages 1–3 are filled in the field (print on waterproof paper or copy onto the slate); page 4 is the post-site report, filled in the same day. Method: Underwater Photogrammetry and Field transects pages of the SEASTRONG Field Processing Tools documentation.",SUB)]
story.append(Paragraph("1. Transect header",H2))
story.append(header_fields(["Study area (BZ / SC / FJ)","Corridor (C1–C6)","Transect ID","Date","Operators","Snorkel / scuba",
 "Sensor 1 ID (seaward)","Sensor 1 position on tape (m)","Sensor 2 ID (landward)","Sensor 2 position on tape (m)",
 "GPS point above 0 m end (lat, lon)","Bearing 0 → 30 m (°)","Camera spacing (cm)","Swimming height (m)",
 "Time zone of watch / phone","Tide (rising / falling / slack)"]))
story.append(Paragraph("2. Before going in the water",H2))
story.append(checklist([
 "Two cameras set to the same time (GoPro app); labelled A and B",
 "Cameras charged, memory cards empty, identical settings (Timelapse, 0.5 s, 5K, Linear, Protune, Flat, ISO 200, shortest shutter, fixed white balance, JPEG)",
 "Rig assembled; camera spacing measured and written above",
 "At least 6 scale bars (bar list with you), 30 m tape, depth gauge, compass, GPS/phone, slate, weights or pegs, colour tab (optional)",
 "Conditions OK: visibility > ~4 m, little surge, tide not changing fast",
 "<b>No strong caustics on the bottom</b> (otherwise wait for clouds or a lower sun)",
]))
story.append(Paragraph("3. Layout (in the water)",H2))
story.append(checklist([
 "Tape laid cross-shore, straight and secured: 0 m at sensor 1 (seaward), 30 m at sensor 2",
 "At least 6 scale bars on both sides, within ~2 m of the tape, varied orientation and elevation; no damage to live coral",
 "Tape positions where the habitat changes noted below",
]))
story.append(Spacer(1,4))
story.append(header_fields(["Habitat changes along tape (m: description)"],cols=1))
story.append(PageBreak())

story.append(Paragraph("4. Scale-bar targets: three depth readings at the centre of each target",H2))
story.append(Paragraph("<b>Target code</b>: printed on the target. <b>Position</b>: distance along the tape (m). <b>Side</b>: L or R looking landward. <b>Depth 1–3</b>: three readings a few seconds apart, gauge held at the target centre. <b>Time</b>: of the readings, for the tide correction.",S))
story.append(Spacer(1,3))
story.append(grid(["Target code","Position on tape (m)","Side (L/R)","Depth 1 (m)","Depth 2 (m)","Depth 3 (m)","Time"],26,
 [0.14,0.17,0.11,0.14,0.14,0.14,0.16],prefix="target",fill_from=1,prefill=[["<i>e.g. T01</i>","<i>2.5</i>","<i>L</i>","<i>1.62</i>","<i>1.60</i>","<i>1.63</i>","<i>10:42</i>"]]))
story.append(PageBreak())

story.append(Paragraph("5. Depth profile: depth and time every 2 m, at each sensor, and 5–10 m beyond the 30 m mark",H2))
story.append(Paragraph("Depth from the gauge or a graduated stick held on the bottom next to the tape; time of each reading, for the tide correction. Write the position of the sensors in the last two rows.",S))
story.append(Spacer(1,3))
stations=[f"{d}" for d in range(0,42,2)]
left=[[s,None,None] for s in stations[:11]]; right=[[s,None,None] for s in stations[11:]]+[["sensor 1",None,None],["sensor 2",None,None]]
t1=grid(["Tape (m)","Depth (m)","Time"],11,[0.15,0.17,0.15],prefill=left,rh=7*mm,prefix="profile_a")
t2=grid(["Tape (m)","Depth (m)","Time"],12,[0.15,0.17,0.15],prefill=right,rh=7*mm,prefix="profile_b")
two=Table([[t1,t2]],colWidths=[W*0.5,W*0.5]); two.setStyle(TableStyle([("VALIGN",(0,0),(-1,-1),"TOP"),("LEFTPADDING",(0,0),(-1,-1),0)]))
story.append(two)
story.append(Paragraph("6. Photo survey",H2))
story.append(checklist([
 "Both cameras started as close to simultaneously as possible; colour tab in the first photos (if used)",
 "Pass 1: forward, camera A over the tape, ~1.5–2 m above the bottom, ~0.3 m/s",
 "Pass 2: backward, camera A over the tape",
 "Pass 3: zigzag, ~3 m each side, ~5 crossings each way",
 "Photos checked on both cameras: complete, sharp, not fogged; passes repeated if needed",
 "All scale bars (checked against the bar list) and the tape recovered; slate photographed",
]))
story.append(Spacer(1,4))
story.append(header_fields(["Cameras start time","Cameras end time","Passes repeated? (which, why)",None],cols=2))
story.append(PageBreak())

story.append(Paragraph("Post-site report",H1))
story.append(Paragraph("Filled in the same day, after downloading the data. Send it with the data to the data manager.",SUB))
story.append(Paragraph("A. Survey",H2))
story.append(header_fields(["Transect ID","Date","Filled in by","Survey complete (Y / N)","Time in the water (h)","Visibility (m)","Waves / surge","Cloud / caustics","Current",None]))
story.append(Paragraph("B. Data",H2))
story.append(header_fields(["Photos camera A (n)","Photos camera B (n)","Folder name camera A","Folder name camera B",
 "Target depths complete (Y / N)","Depth profile complete (Y / N)","Slate photo saved (Y / N)","Field sheet copied (Y / N)"]))
story.append(Spacer(1,4))
story.append(header_fields(["Data download link"],cols=1))
story.append(Paragraph("C. Quality check (tick if a problem)",H2))
story.append(checklist(["Blurred or dark photos","Fogged housing","Caustics in part of the survey","A camera stopped during a pass","Targets moved or not visible","Tape not straight or moved","Missing depth readings"]))
story.append(Paragraph("D. Deviations from the protocol, problems and notes",H2))
nb=Table([[Field("notes_deviations",W-8,24*mm,multiline=True)]],colWidths=[W],rowHeights=[26*mm]); nb.setStyle(TableStyle([("BOX",(0,0),(-1,-1),0.5,GRID)]))
story.append(nb)

doc=SimpleDocTemplate(RAW,pagesize=A4,leftMargin=15*mm,rightMargin=15*mm,topMargin=14*mm,bottomMargin=16*mm,
  title="Reef photogrammetry field form",author="SEASTRONG / UNIVE")
doc.build(story,onFirstPage=footer,onLaterPages=footer)


# ---- post-processing: one shared Transect ID field, auto-filled in Acrobat ----
from pypdf import PdfReader, PdfWriter
from pypdf.generic import NameObject, DictionaryObject, TextStringObject, ArrayObject, NumberObject
r=PdfReader(RAW); w=PdfWriter(); w.append(r)
af=w._root_object["/AcroForm"]
fields=af["/Fields"]
targets={"transect_id","transect_id_2","footer_tid_1","footer_tid_2","footer_tid_3","footer_tid_4"}
kids=ArrayObject(); keep=ArrayObject(); da=None
for ref in fields:
    o=ref.get_object(); t=str(o.get("/T",""))
    if t in targets or t.startswith("footer_tid_"):
        kids.append(ref); da=da or o.get("/DA")
    else: keep.append(ref)
calc=('var a=this.getField("study_area_bz_sc_fj").valueAsString.replace(/\\s/g,"");'
 'var c=this.getField("corridor_c1_c6").valueAsString.replace(/\\s/g,"");'
 'var d=this.getField("date").valueAsString.replace(/\\s/g,"");'
 'var p=d.split("/");'
 'if(a&&c&&p.length==3){var mm=("0"+p[0]).slice(-2),dd=("0"+p[1]).slice(-2),yy=p[2].slice(-2);event.value=a+dd+mm+yy+c+"reef";}else{event.value="will autocompile";}')
parent=DictionaryObject()
parent[NameObject("/FT")]=NameObject("/Tx"); parent[NameObject("/T")]=TextStringObject("transect_id")
parent[NameObject("/V")]=TextStringObject("will autocompile"); 
if da: parent[NameObject("/DA")]=da
parent[NameObject("/TU")]=TextStringObject("Transect ID: area + DDMMYY + corridor + reef, e.g. BZ140327C1reef (filled in automatically in Adobe Acrobat Reader; type it in other viewers)")
js=DictionaryObject(); js[NameObject("/S")]=NameObject("/JavaScript"); js[NameObject("/JS")]=TextStringObject(calc)
aa=DictionaryObject(); aa[NameObject("/C")]=js; parent[NameObject("/AA")]=aa
pref=w._add_object(parent)
for k in kids:
    o=k.get_object()
    for key in ("/T","/FT","/V","/TU","/Ff"):
        if key in o: del o[key]
    o[NameObject("/Parent")]=pref
parent[NameObject("/Kids")]=kids
keep.append(pref)
af[NameObject("/Fields")]=keep
af[NameObject("/CO")]=ArrayObject([pref])
af[NameObject("/NeedAppearances")]=__import__("pypdf").generic.BooleanObject(True)
w.add_metadata({"/Title":f"Reef photogrammetry field form v{VERSION}","/Author":"SEASTRONG / UNIVE"})
os.makedirs(os.path.dirname(OUT),exist_ok=True)
w.write(OUT)
os.remove(RAW)
print('written',os.path.normpath(OUT))
