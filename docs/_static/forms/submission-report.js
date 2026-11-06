/* Readable PDF report; original, unmodified text is always retained in JSON and CSV. */
export async function makeReport(record,schema,tables) {
  const {PDFDocument,StandardFonts,rgb}=globalThis.PDFLib;
  const pdf=await PDFDocument.create();
  const normal=await pdf.embedFont(StandardFonts.Helvetica);
  const bold=await pdf.embedFont(StandardFonts.HelveticaBold);
  const ink=rgb(.09,.21,.24),muted=rgb(.32,.42,.44),sea=rgb(.06,.43,.4);
  let page,y;const pages=[];
  const clean=value=>String(value??'').replace(/[–—−]/g,'-').replace(/→/g,'to').replace(/≥/g,'>=').replace(/≤/g,'<=').replace(/\u00a0/g,' ').split('').map(c=>{try{normal.encodeText(c);return c;}catch{return '?';}}).join('');
  function addPage(){page=pdf.addPage([595.28,841.89]);pages.push(page);y=776;page.drawText('SEASTRONG / FIELD SURVEY',{x:42,y:805,size:9,font:bold,color:sea});page.drawText(record.surveyId,{x:310,y:805,size:9,font:normal,color:muted});}
  function line(text,{size=10,font=normal,color=ink,indent=0}={}) {
    for(const paragraph of clean(text).split(/\r?\n/)){
      const words=paragraph.split(/\s+/);let current='';const lines=[];
      for(const word of words){const candidate=current?current+' '+word:word;if(font.widthOfTextAtSize(candidate,size)<=511-indent){current=candidate;continue}if(current)lines.push(current);current='';for(const char of word){if(font.widthOfTextAtSize(current+char,size)>511-indent){lines.push(current);current=''}current+=char;}}
      lines.push(current);
      for(const row of lines){if(y<58)addPage();page.drawText(row,{x:42+indent,y,size,font,color});y-=size+5;}
    }
  }
  function heading(text){if(y<100)addPage();y-=12;line(text,{size:12,font:bold,color:sea});y-=3;}
  addPage();line(schema.name+' - survey record',{size:20,font:bold});line('Submission '+record.submissionId,{size:8,color:muted});
  heading('Survey details');
  for(const [label,value] of [['Study area',record.studyAreaName],['Corridor',record.corridor==='CX'?'Other (outside the corridors)':record.corridor],['Corridor / site name',record.corridorName],['Data category',{protocol:'Corridor data according to protocols',additional:'Additional data'}[record.dataCategory]],['Survey date (YYYY-MM-DD)',record.surveyDate],['Clock UTC offset',record.clockUTCOffset],['Operators',record.operators],['Filled in by',record.filledInBy],['Record stage',record.recordStage],['Field survey complete',record.surveyComplete],['Package status',record.status]])line(label+': '+(value||'Not recorded'));
  if(record.submittedBy)line('Submitted with Google account: '+(record.submittedBy.emailAddress||record.submittedBy.displayName||record.submittedBy.permissionId));
  line('Record version: '+(record.revisionNumber||1));
  if(record.revisionOf)line('Previous submission: '+record.revisionOf,{size:9,color:muted});
  let section='';for(const field of schema.fields){if(!String(record.fields[field.id]||'').trim())continue;if(section!==field.section){section=field.section;heading(section)}line(field.label+': '+record.fields[field.id]);}
  for(const table of tables){const rows=record.tables[table.id]||[];heading(table.name);if(table.help)line(table.help,{size:9,color:muted});let filled=0;rows.forEach((row,index)=>{if(!row.some(v=>String(v).trim()))return;filled++;if(y<90)addPage();line('Row '+(index+1),{font:bold,size:9});line(table.columns.map((label,i)=>label+': '+(row[i]||'Not recorded')).join(' | '),{size:9,indent:8});y-=3});if(!filled)line('No rows recorded.',{color:muted});}
  for(const [index,list] of schema.checklists.entries()){heading(list.title);list.items.forEach((text,i)=>line((record.checklists[index+'-'+i]?'[X] ':'[ ] ')+text,{size:9}));}
  heading('Deviations and notes');line(record.notes||'None recorded.');
  heading('Missing files / incomplete data');line(record.missingFilesReason||'None reported.');
  heading('File manifest');line(record.files.length+' file(s). Original names and Drive file IDs are retained in the JSON manifest.',{size:9,color:muted});
  for(const file of record.files)line(file.group+'/'+file.path+' ('+file.size+' bytes)',{size:9});
  if(record.packageFolderId){heading('Shared Drive location');line('https://drive.google.com/drive/folders/'+record.packageFolderId,{size:9});}
  y-=10;line('Blank values mean not recorded. Unsupported characters in this PDF are replaced with ?. Refer to JSON and CSV for original text.',{size:8,color:muted});
  pages.forEach((p,i)=>{p.drawLine({start:{x:42,y:42},end:{x:553,y:42},thickness:.5,color:rgb(.82,.87,.87)});p.drawText('SEASTRONG - '+record.surveyId,{x:42,y:27,size:8,font:normal,color:muted});p.drawText(`${i+1} / ${pages.length}`,{x:520,y:27,size:8,font:normal,color:muted});});
  pdf.setTitle(record.surveyId+' field survey');pdf.setAuthor('SEASTRONG');pdf.setSubject(schema.name+' submission record');
  return new Blob([await pdf.save()],{type:'application/pdf'});
}
