import {CONFIG} from './submission-config.js';
import {SURVEYS} from './survey-schema.js';
import {TABLES,FILE_GROUPS,visibleTables} from './survey-tables.js';
import {DriveClient} from './drive-client.js';
import {makeReport} from './submission-report.js';
import {accountIdentity,recordProperties,groupRecords,restoreRecord,editAsRevision} from './submission-records.js';
import {AREAS,VERSION,escapeHTML as esc,surveyId,newDraft,validateDetails,validateDraft,metadata,tableCSV,fileIdentity,safePath,formatBytes,readDraft} from './submission-core.js';

const root=document.getElementById('seastrong-submission');
const $=s=>root.querySelector(s);
const storageKey='seastrong.field-submission.v1';
const drive=new DriveClient(CONFIG);
const selectedFiles=new Map();
let storage;try{storage=localStorage;}catch{storage=null;}
let state=storage?await readDraft(storage,storageKey,SURVEYS):null;
state=state||newDraft();
let tableChoice='',fileGroup='',busy=false,controller=null,saveTimer,sessionProgress='';
let view='form',recordFiles=[],recordDetail=null,recordsLoading=false,recordsError='',recordsEpoch=0;
const openHistory=new Set();
const steps=['Survey details','Measurements','Files','Review'];
const glyph={reef:'◉',mangrove:'♧',seagrass:'♧',bathy:'≋',drone:'↗',waves:'≋'};
function schema(){return SURVEYS[state.type];}
function getTables(){return visibleTables(state.type,state.values);}
function seedTables(){for(const t of TABLES[state.type])if(!state.tables[t.id])state.tables[t.id]=t.seed.map(r=>r.slice());}
function status(text,error=false){$('.ss-status').textContent=text;$('.ss-status').classList.toggle('ss-error',error);}
function saveDraft(quiet=true){
  try{if(!storage)throw new Error();storage.setItem(storageKey,JSON.stringify(state));if(!quiet)status('Draft saved on this browser.');}
  catch{status('Browser storage is unavailable or full. Download your draft to keep a copy.',true);}
}
function scheduleSave(){clearTimeout(saveTimer);saveTimer=setTimeout(()=>saveDraft(),400);}
function link(id){return 'https://drive.google.com/drive/folders/'+encodeURIComponent(id);}
function options(items,value){return '<option value="">Choose…</option>'+items.map(v=>`<option value="${esc(Array.isArray(v)?v[0]:v)}"${(Array.isArray(v)?v[0]:v)===value?' selected':''}>${esc(Array.isArray(v)?v[1]:v)}</option>`).join('');}
function input(label,key,value,{type='text',choices,full=false,help='',scope='base',required=false}={}){
  const attrs=`data-scope="${scope}" data-field="${esc(key)}" ${required?'required':''}`;
  return `<label class="ss-field${full?' ss-full':''}"><span>${esc(label)}${required?' *':''}</span>${choices?`<select ${attrs}>${options(choices,value)}</select>`:type==='textarea'?`<textarea ${attrs}>${esc(value)}</textarea>`:`<input type="${type}" ${attrs} value="${esc(value)}"${type==='date'?' min="2000-01-01" max="2099-12-31"':''}>`}${help?`<span class="ss-muted ss-help">${esc(help)}</span>`:''}</label>`;
}
function details(){
  const offsets=Array.from({length:105},(_,i)=>{const mins=-12*60+i*15;const value='UTC'+(mins>=0?'+':'-')+String(Math.floor(Math.abs(mins)/60)).padStart(2,'0')+':'+String(Math.abs(mins)%60).padStart(2,'0');return value;});
  return `<section class="ss-panel"><div class="ss-panel-head"><h2>Where and what did you survey?</h2><p>Choose a survey type to see its measurements and file requirements.</p></div><div class="ss-field">Survey type</div><div class="ss-types">${Object.entries(SURVEYS).map(([k,s])=>`<button type="button" class="ss-type" data-type="${k}" aria-pressed="${state.type===k}"${state.upload.packageFolderId?' disabled':''}><span class="ss-glyph" aria-hidden="true">${glyph[k]}</span><span>${s.name}</span></button>`).join('')}</div><div class="ss-fields">${input('Study area','area',state.area,{choices:Object.entries(AREAS),required:true})}${input('Corridor','corridor',state.corridor,{choices:Array.from({length:6},(_,i)=>['C'+(i+1),'Corridor '+(i+1)]),required:true})}${input(state.type==='waves'?'Deployment date':'Survey date','date',state.date,{type:'date',required:true,help:'Stored as YYYY-MM-DD. Survey ID uses DDMMYY.'})}${input('Time zone of field clock','timezone',state.timezone,{choices:offsets,required:true,help:'The UTC offset actually used by the watch, camera or phone.'})}${input('Operators','operators',state.operators,{full:true,required:true})}${input('Filled in by','filledBy',state.filledBy,{required:true})}${input('Survey occurrence','suffix',state.suffix,{choices:[['','First survey of this type today'],['B','Second survey · suffix B'],['C','Third survey · suffix C'],['D','Fourth survey · suffix D']]})}${state.type==='waves'?input('Record stage','recordStage',state.recordStage,{choices:['Deployment','Retrieval','Post-site report']}):''}</div><div class="ss-id-box"><span>Automatic survey ID</span><span class="ss-code" data-id>${surveyId(state)||'Complete the survey details'}</span></div><p class="ss-muted" style="margin-top:14px"><a href="./${schema().pdf}" target="_blank" rel="noopener">Open the printable ${schema().name.toLowerCase()} field sheet ↗</a></p></section>`;
}
function measurementFields(){
  const sections=new Map();
  for(const f of schema().fields){
    if(f.id==='survey_complete_y_n')continue;
    if(state.type==='mangrove'&&/^[456]\. Method/.test(f.section)&&state.values.structure_method&&!state.values.structure_method.includes(f.section.match(/Method ([ABC])/)?.[1]))continue;
    if(!sections.has(f.section))sections.set(f.section,[]);sections.get(f.section).push(f);
  }
  return [...sections.entries()].map(([title,fields],i)=>`<details class="ss-details"${i===0?' open':''}><summary>${esc(title)}</summary><div class="ss-fields">${fields.map(f=>input(f.label,f.id,state.values[f.id]||'',{scope:'value',choices:f.options.length?f.options:undefined,help:f.help,type:/description|changes|methods along|repeated|notes/i.test(f.label)?'textarea':'text',full:/description|changes|methods along/i.test(f.label)})).join('')}</div></details>`).join('');
}
function tableMarkup(){
  const tables=getTables();if(!tables.length)return '';
  if(!tables.some(t=>t.id===tableChoice))tableChoice=tables[0].id;
  const table=tables.find(t=>t.id===tableChoice);const rows=state.tables[table.id];
  return `<hr class="ss-line"><label class="ss-field">Measurement table<select data-table-choice>${options(tables.map(t=>[t.id,t.name]),tableChoice)}</select></label>${table.help?`<p class="ss-muted" style="margin-top:10px">${esc(table.help)}</p>`:''}<div class="ss-tablewrap"><table><thead><tr>${table.columns.map(c=>`<th scope="col">${esc(c)}</th>`).join('')}<th scope="col">Remove</th></tr></thead><tbody>${rows.map((r,ri)=>`<tr>${table.columns.map((c,ci)=>`<td><input aria-label="${esc(c)}, row ${ri+1}" data-table="${table.id}" data-row="${ri}" data-col="${ci}" value="${esc(r[ci]||'')}"></td>`).join('')}<td><button type="button" class="ss-icon-btn" data-remove-row="${ri}" aria-label="Remove row ${ri+1}">×</button></td></tr>`).join('')}</tbody></table></div><div class="ss-table-actions"><button type="button" class="ss-small-btn" data-action="add-row">＋ Add a reading</button><label class="ss-small-btn ss-file-button">Import CSV<input type="file" data-import-csv accept=".csv,text/csv"></label><button type="button" class="ss-small-btn" data-action="template">CSV template ↓</button></div>`;
}
function measurements(){return `<section class="ss-panel"><div class="ss-panel-head"><h2>${schema().name} measurements</h2><p>Enter the observations from the field sheet. Leave unavailable values blank and explain gaps below.</p></div>${input('Was the planned field survey completed?','surveyComplete',state.surveyComplete,{choices:[['Yes','Yes'],['No','No / partly complete'],['Ongoing','Ongoing · deployment not yet retrieved']],required:true})}<div style="margin-top:20px">${measurementFields()}</div>${tableMarkup()}<hr class="ss-line">${schema().checklists.map((list,li)=>`<details class="ss-details"><summary>${esc(list.title)}</summary><p class="ss-muted">Tick recorded checks or observed problems. Unticked items alone do not establish protocol compliance.</p>${list.items.map((text,i)=>`<label class="ss-check"><input type="checkbox" data-check="${li}-${i}"${state.checks[li+'-'+i]?' checked':''}><span>${esc(text)}</span></label>`).join('')}</details>`).join('')}<label class="ss-check"><input type="checkbox" data-field="qualityReviewed" data-scope="base"${state.qualityReviewed?' checked':''}><span>I have reviewed the field checks and quality flags above.</span></label>${input('Deviations, problems and notes','notes',state.notes,{type:'textarea',full:true})}</section>`;}
function groups(){return [...FILE_GROUPS[state.type],['other','Other survey files']];}
function filePanel(){
  if(!groups().some(([key])=>key===fileGroup))fileGroup=groups()[0][0];
  const missing=FILE_GROUPS[state.type].filter(([k])=>!state.files.some(f=>f.group===k));
  return `<section class="ss-panel"><div class="ss-panel-head"><h2>Add the survey files</h2><p>Select a category, then add its files or a whole folder. File contents are sent only when you submit.</p></div>${input('File category','group',fileGroup,{choices:groups(),scope:'file'})}<div class="ss-drop"><strong>Add ${esc(groups().find(([k])=>k===fileGroup)?.[1].toLowerCase())}</strong><span class="ss-muted">Folder structure is preserved; stored filenames receive the survey ID prefix.</span><label class="ss-btn ss-primary ss-file-button">Choose files<input type="file" data-add-files multiple></label><label class="ss-small-btn ss-file-button">Choose a folder<input type="file" data-add-folder webkitdirectory multiple></label></div><div class="ss-group-list">${groups().map(([key,label])=>{const files=state.files.filter(f=>f.group===key);if(!files.length)return '';const selected=files.filter(f=>selectedFiles.has(f.identity)).length;const uploaded=files.filter(f=>f.uploaded).length;return `<details class="ss-details"><summary>${esc(label)} · ${files.length} files · ${formatBytes(files.reduce((n,f)=>n+f.size,0))}</summary><p class="ss-muted">${uploaded} uploaded · ${selected} selected on this computer${files.length>10?' · showing the first 10':''}</p>${files.slice(0,10).map(f=>`<div class="ss-file-row"><div class="ss-file-info"><div>${esc(f.path)}</div><span class="ss-muted">${formatBytes(f.size)}</span></div><span class="ss-tag">${f.inherited?'Earlier original':f.uploaded?'Uploaded':selectedFiles.has(f.identity)?'Ready':'Select again'}</span></div>`).join('')}<button type="button" class="ss-small-btn" data-clear-group="${key}">Remove this category from the draft</button></details>`;}).join('')}</div>${missing.length?`<div class="ss-notice">No files selected in: ${missing.map(([,label])=>esc(label)).join(', ')}. Explain anything not collected, not yet available or included in another category.</div>`:''}${input('Missing or pending files','missingFilesReason',state.missingFilesReason,{type:'textarea',full:true,required:!!missing.length})}<p class="ss-muted" style="margin-top:14px">Earlier originals stay on Drive and are linked in the new record. Keep this page open while uploading new files; after a reload, reselect any new files that have not finished.</p></section>`;
}
function reviewIssues(){
  const issues=validateDetails(state,SURVEYS);
  if(!state.surveyComplete)issues.push('Record whether the field survey was completed.');
  if(!state.qualityReviewed)issues.push('Confirm that you reviewed the field checks and quality flags.');
  const missing=FILE_GROUPS[state.type].filter(([key])=>!state.files.some(f=>f.group===key));
  if(missing.length&&!state.missingFilesReason.trim())issues.push('Explain missing or pending file categories.');
  if(state.files.some(f=>!f.uploaded&&!selectedFiles.has(f.identity)))issues.push('Reselect the files listed as “Select again” before uploading.');
  if(!state.confirmed)issues.push('Confirm the final review below.');
  return issues;
}
function review(){
  if(state.done)return `<section class="ss-panel"><div class="ss-success"><div class="ss-success-mark">✓</div><h2>Your survey package is saved</h2><span class="ss-code">${surveyId(state)}</span><p>${state.files.length} original files verified on Google Drive.</p><a class="ss-btn ss-primary" href="${link(state.upload.packageFolderId)}" target="_blank" rel="noopener">Open submission folder ↗</a><button type="button" class="ss-btn" data-action="revision">Edit this record</button><button type="button" class="ss-btn" data-view="records">View my records</button><button type="button" class="ss-small-btn" data-action="new">Start another survey</button></div></section>`;
  const rows=getTables().reduce((n,t)=>n+(state.tables[t.id]||[]).filter(r=>r.some(v=>String(v).trim())).length,0);
  return `<section class="ss-panel"><div class="ss-panel-head"><h2>Review the survey package</h2><p>Uploads go to the fixed institutional destination shown on the right.</p></div>${[['Survey ID',surveyId(state)||'Incomplete'],['Survey',schema().name],['Location',AREAS[state.area]+' · '+state.corridor],['Survey date',state.date],['Operators',state.operators||'Missing'],['Filled in by',state.filledBy||'Missing'],['Record stage',state.recordStage],['Field survey complete',state.surveyComplete||'Not recorded'],['Table rows (including position labels)',rows],['Original files',state.files.length],['Total original file size',formatBytes(state.files.reduce((n,f)=>n+f.size,0))]].map(([k,v])=>`<div class="ss-review-row"><span>${k}</span><span>${esc(v)}</span></div>`).join('')}<label class="ss-check"><input type="checkbox" data-field="confirmed" data-scope="base"${state.confirmed?' checked':''}><span>I have checked the survey details and selected the intended files.</span></label><div class="ss-notice">Submitting saves the originals, JSON metadata, CSV tables, PDF report and a file manifest. “Complete” means the upload package is verified, not that the field survey met every protocol requirement.</div><div class="ss-review-errors" role="alert"></div><div class="ss-upload-progress"${busy?'':' hidden'}><div class="ss-progress" role="progressbar" aria-label="Upload progress" aria-valuemin="0" aria-valuemax="100" aria-valuenow="0"><div class="ss-progress-fill"></div></div><p class="ss-muted" data-upload-message aria-live="polite">${esc(sessionProgress)}</p></div><button type="button" class="ss-small-btn" data-action="report">Download report preview ↓</button></section>`;
}
function summary(){
  const sid=surveyId(state)||'Survey ID pending';
  $('.ss-tree').innerHTML=`<div>Survey submissions</div><div>${esc(AREAS[state.area]||'Study area')}</div><div>${esc(state.corridor)}</div><div><span class="ss-code">${esc(sid)}</span></div>`;
  root.querySelectorAll('[data-id]').forEach(el=>el.textContent=sid);
  const connected=drive.connected;$('.ss-connection').textContent=connected?'Connected to '+(drive.user?.emailAddress||'Google Drive')+' · '+drive.root.name:drive.configured?'Draft mode · connect Google Drive when you are ready to upload.':'Google setup is not finished. You can complete and download a local draft.';
  $('[data-action="connect"]').textContent=connected?'Reconnect Google Drive':'Connect Google Drive';
}
function render(){
  root.querySelectorAll('input,textarea,select,button').forEach(el=>{el.disabled=false;});
  seedTables();state.step=Math.min(3,Math.max(0,Number(state.step)||0));
  $('.ss-steps').innerHTML=steps.map((name,i)=>`<button type="button" class="ss-step" data-step="${i}"${i===state.step?' aria-current="step"':''}><span class="ss-step-num">${i+1}</span><span>${name}</span></button>`).join('');
  $('.ss-panels').innerHTML=(state.revisionOf?`<div class="ss-notice">Editing version ${state.revisionNumber}. Saving creates a new version. Earlier originals remain available without uploading them again.</div>`:'')+[details,measurements,filePanel,review][state.step]();
  $('[data-action="back"]').hidden=state.step===0||state.done;
  const next=$('[data-action="next"]');next.hidden=state.done;next.textContent=busy?'Pause upload':state.step===3?(state.upload.packageFolderId?'Resume submission ↑':'Submit to Shared Drive ↑'):'Continue →';
  summary();
  $('.ss-heading h1').textContent=view==='records'?'Your field records':'Submit a field survey';
  $('.ss-heading .ss-lead').textContent=view==='records'?'Review your submissions and keep a history of corrections.':'The measurements, the context and the files. Together.';
  $('.ss-steps').hidden=view==='records';$('.ss-layout').hidden=view==='records';
  $('[data-action="save"]').hidden=view==='records'||state.done;
  $('.ss-records-view').hidden=view!=='records';
  root.querySelectorAll('[data-view]').forEach(el=>el.setAttribute('aria-pressed',String(el.dataset.view===view)));
  if(view==='records')renderRecords();
  if(state.upload.surveyFolderId)root.querySelectorAll('[data-field="area"],[data-field="corridor"],[data-field="date"],[data-field="suffix"]').forEach(el=>el.disabled=true);
  if(busy)root.querySelectorAll('input,textarea,select,button').forEach(el=>{if(el!==next)el.disabled=true;});
}
function savedTime(value){try{return new Intl.DateTimeFormat(undefined,{dateStyle:'medium',timeStyle:'short'}).format(new Date(value));}catch{return 'Date unavailable';}}
function recordRow(file,history=false){
  const props=file.appProperties||{},legacy=props.seastrongRecord!=='1';
  const sid=props.surveyId||file.name.replace(/_submission\.json$/,'');
  const statusText=legacy?'Earlier format':props.recordStatus==='complete'?'Saved':'Upload incomplete';
  const version=Number(props.revisionNumber)||1;
  return `<div class="ss-record-row${history?' ss-record-older':''}"><div class="ss-record-name"><span class="ss-code">${esc(sid)}</span><span class="ss-muted">${esc(SURVEYS[props.surveyType]?.name||'Earlier record')} · Version ${version}</span></div><div class="ss-muted">${esc(savedTime(file.modifiedTime))}<br>${esc(props.recordStage||'')}</div><div><span class="ss-tag">${statusText}</span></div><div class="ss-record-actions"><button type="button" class="ss-btn" data-open-record="${esc(file.id)}">View</button><button type="button" class="ss-btn" data-edit-record="${esc(file.id)}"${!legacy&&props.recordStatus!=='complete'?' disabled':''}>Edit</button></div></div>`;
}
function recordDetailMarkup(){
  const {file,record,draft}=recordDetail,legacy=!record.submittedBy?.permissionId;
  const fields=schemaForRecord(record).fields.filter(f=>String(draft.values[f.id]||'').trim());
  const tables=visibleTables(draft.type,draft.values);
  return `<article class="ss-panel"><div class="ss-record-heading"><div><div class="ss-eyebrow">SAVED RECORD · VERSION ${esc(record.revisionNumber||1)}</div><h2>${esc(record.surveyId)}</h2><p class="ss-muted">${esc(SURVEYS[draft.type].name)} · ${esc(savedTime(record.savedAt||file.modifiedTime))}</p></div><button type="button" class="ss-btn" data-action="records-back">← My records</button></div>${legacy?'<div class="ss-notice">Earlier record: the form did not yet save an account ID. This record was matched using the Google account that last saved its metadata.</div>':''}<dl class="ss-record-meta">${[['Study area',AREAS[draft.area]],['Corridor',draft.corridor],['Survey date',draft.date],['Operators',draft.operators],['Filled in by',draft.filledBy],['Google account',record.submittedBy?.emailAddress||file.lastModifyingUser?.emailAddress||'Matched current account'],['Record stage',draft.recordStage],['Field survey complete',draft.surveyComplete],['Upload package',record.status],...fields.map(f=>[f.label,draft.values[f.id]])].map(([label,value])=>`<div><dt>${esc(label)}</dt><dd>${esc(value||'Not recorded')}</dd></div>`).join('')}</dl>${tables.map(table=>`<details class="ss-details"><summary>${esc(table.name)} · ${(draft.tables[table.id]||[]).length} row${(draft.tables[table.id]||[]).length===1?'':'s'}</summary><div class="ss-tablewrap"><table><thead><tr>${table.columns.map(c=>`<th scope="col">${esc(c)}</th>`).join('')}</tr></thead><tbody>${(draft.tables[table.id]||[]).map(row=>`<tr>${row.map(cell=>`<td>${esc(cell||'—')}</td>`).join('')}</tr>`).join('')}</tbody></table></div></details>`).join('')}<details class="ss-details"><summary>Field checks and quality flags</summary>${schemaForRecord(record).checklists.map((list,li)=>`<h3>${esc(list.title)}</h3>${list.items.map((text,i)=>`<p class="ss-muted">${draft.checks[li+'-'+i]?'✓':'—'} ${esc(text)}</p>`).join('')}`).join('')}</details><h3 style="margin-top:20px">Notes</h3><p class="ss-record-text">${esc(draft.notes||'None recorded.')}</p><h3 style="margin-top:18px">Missing or pending files</h3><p class="ss-record-text">${esc(draft.missingFilesReason||'None reported.')}</p><details class="ss-details"><summary>Original files · ${draft.files.length}</summary>${draft.files.slice(0,50).map(f=>`<div class="ss-file-row"><div class="ss-file-info"><a href="https://drive.google.com/file/d/${encodeURIComponent(f.driveFileId)}/view" target="_blank" rel="noopener">${esc(f.group+'/'+f.path)}</a><div class="ss-muted">${formatBytes(f.size)}${f.inherited?' · earlier original':''}</div></div></div>`).join('')}${draft.files.length>50?'<p class="ss-muted">Showing the first 50 files. Download the record data for the complete manifest.</p>':''}</details><div class="ss-record-footer"><button type="button" class="ss-btn ss-primary" data-edit-record="${esc(file.id)}"${record.status!=='complete'?' disabled':''}>Edit as a new version</button><a class="ss-btn" href="${link(record.packageFolderId)}" target="_blank" rel="noopener">Open folder ↗</a><button type="button" class="ss-small-btn" data-action="download-record">Download record data ↓</button></div>${record.status!=='complete'?'<p class="ss-muted">This upload is incomplete. Resume the draft in its original browser, or import its downloaded draft.</p>':''}</article>`;
}
function schemaForRecord(record){return SURVEYS[record.surveyType];}
function renderRecords(){
  const panel=$('.ss-records-view');
  if(!drive.connected){panel.innerHTML=`<section class="ss-panel"><h2>My records</h2><p class="ss-lead">Connect Google Drive above to find records saved by your Google account.</p>${recordsError?`<p class="ss-record-error" role="alert">${esc(recordsError)}</p>`:''}</section>`;return;}
  const title=`<div class="ss-record-heading"><div><h2>My records</h2><p class="ss-muted">${esc(drive.user?.emailAddress||drive.user?.displayName||'Your Google account')} · SEASTRONG submissions</p></div><button type="button" class="ss-btn" data-action="refresh-records"${recordsLoading?' disabled':''}>Refresh</button></div>`;
  if(recordsLoading){panel.innerHTML=`<section class="ss-panel">${title}<p class="ss-lead" role="status">Loading your records from Drive…</p></section>`;return;}
  const error=recordsError?`<p class="ss-record-error" role="alert">${esc(recordsError)}</p>`:'';
  if(recordDetail){panel.innerHTML=error+recordDetailMarkup();return;}
  const groups=groupRecords(recordFiles);
  panel.innerHTML=`<section class="ss-panel">${title}${error}${groups.length?groups.map(versions=>{const key=versions[0].appProperties?.recordId||versions[0].appProperties?.submissionId||versions[0].legacyRecordId||versions[0].id;return `<div class="ss-record-group">${recordRow(versions[0])}${versions.length>1?`<button type="button" class="ss-small-btn" data-history="${esc(key)}" aria-expanded="${openHistory.has(key)}">${openHistory.has(key)?'Hide':'Show'} ${versions.length-1} earlier version${versions.length>2?'s':''}</button>${openHistory.has(key)?versions.slice(1).map(f=>recordRow(f,true)).join(''):''}`:''}</div>`;}).join(''):'<p class="ss-lead">No saved records found for this account.</p>'}<p class="ss-muted" style="margin-top:18px">This list is filtered by the signed-in account. Editing saves a new version and keeps the earlier record and original files.</p></section>`;
}
async function loadRecords(){
  if(!drive.connected){recordsError='';renderRecords();return;}
  const epoch=++recordsEpoch;recordsLoading=true;recordsError='';renderRecords();
  try{const files=await drive.myRecords();if(epoch===recordsEpoch)recordFiles=files;}
  catch(error){if(epoch===recordsEpoch)recordsError=error.message||String(error);}
  finally{if(epoch===recordsEpoch){recordsLoading=false;if(view==='records')renderRecords();}}
}
async function openRecord(id){
  const epoch=++recordsEpoch;recordsLoading=true;recordsError='';renderRecords();
  try{const result=await drive.readRecord(id);const draft=restoreRecord(result.record,result.file,SURVEYS);if(epoch===recordsEpoch)recordDetail={...result,draft};}
  catch(error){if(epoch===recordsEpoch)recordsError=error.message||String(error);}
  finally{if(epoch===recordsEpoch){recordsLoading=false;renderRecords();}}
}
async function editRecord(id){
  if(!drive.connected)throw new Error('Reconnect Google Drive to edit a saved record.');
  const {file,record}=await drive.readRecord(id);
  const draft=editAsRevision(record,file,drive.user,CONFIG.rootFolderId,SURVEYS);
  const unfinished=!state.done&&(state.operators.trim()||Object.keys(state.values).length||state.files.length);
  if(unfinished&&!confirm('Replace the current browser draft with a new version of this saved record? Download your current draft first if you want to keep it.'))return;
  state=draft;selectedFiles.clear();tableChoice='';fileGroup='';view='form';recordDetail=null;recordsError='';saveDraft();render();
  status('Editing a new version. Earlier originals stay linked; add only new or replacement files.');
}
function download(blob,name){const url=URL.createObjectURL(blob);const a=document.createElement('a');a.href=url;a.download=name;a.click();setTimeout(()=>URL.revokeObjectURL(url),60000);}
function errorMessage(error){status(error.message||String(error),true);}
function parseCSV(text){
  const rows=[];let row=[],cell='',quoted=false;
  text=text.replace(/^\ufeff/,'');
  for(let i=0;i<text.length;i++){const c=text[i];if(quoted){if(c==='"'&&text[i+1]==='"'){cell+='"';i++;}else if(c==='"')quoted=false;else cell+=c;}
    else if(c==='"'&&!cell)quoted=true;else if(c===','){row.push(cell);cell='';}else if(c==='\n'||c==='\r'){if(c==='\r'&&text[i+1]==='\n')i++;row.push(cell);if(row.some(v=>v!==''))rows.push(row);row=[];cell='';}else cell+=c;}
  if(quoted)throw new Error('The CSV ends inside a quoted value.');row.push(cell);if(row.some(v=>v!==''))rows.push(row);return rows;
}
async function importCSV(file){
  if(file.size>10*1024*1024)throw new Error('This measurement CSV is larger than 10 MB. Split it into smaller tables.');
  const table=getTables().find(t=>t.id===tableChoice);const rows=parseCSV(await file.text());const head=rows.shift();if(!head)throw new Error('The CSV is empty.');
  let offset=head[0]==='survey_id'?1:0;
  if(JSON.stringify(head.slice(offset))!==JSON.stringify(table.columns))throw new Error('CSV headings do not match this table. Download its CSV template first.');
  if(rows.some(r=>r.length!==head.length))throw new Error('Some CSV rows have a different number of columns.');
  if(offset&&rows.some(r=>r[0]&&r[0]!==surveyId(state)))throw new Error('The CSV contains another survey ID.');
  if(!confirm('Replace the current '+table.name+' table with '+rows.length+' imported rows?'))return;
  state.tables[table.id]=rows.map(r=>r.slice(offset));state.confirmed=false;saveDraft();render();status('CSV imported.');
}
function addFiles(files){
  let added=0;
  for(const file of files){const path=file.webkitRelativePath||file.name;const identity=fileIdentity(fileGroup,path,file.size,file.lastModified);selectedFiles.set(identity,file);if(!state.files.some(f=>f.identity===identity)){state.files.push({key:crypto.randomUUID(),identity,group:fileGroup,path,size:file.size,lastModified:file.lastModified,type:file.type||'application/octet-stream',uploaded:false});added++;}}
  state.confirmed=false;saveDraft();render();status(added+' files added. Nothing uploaded yet.');
}
async function prepareFolders(){
  if(state.upload.rootFolderId&&state.upload.rootFolderId!==CONFIG.rootFolderId)throw new Error('This draft belongs to a different Drive destination. Start a new survey.');
  const sid=surveyId(state);
  if(state.upload.surveyId&&state.upload.surveyId!==sid)throw new Error('The survey ID changed after uploading. Restore the original ID or start another survey.');
  const area=await drive.folder(CONFIG.rootFolderId,AREAS[state.area]);const corridor=await drive.folder(area.id,state.corridor);
  let survey;
  if(state.upload.surveyFolderId){survey=await drive.getFile(state.upload.surveyFolderId,'id,name,parents,trashed');if(survey.trashed||survey.name!==sid||!survey.parents.includes(corridor.id))throw new Error('The existing survey folder does not match this record.');}
  else survey=await drive.folder(corridor.id,sid);
  if(state.upload.packageFolderId){const folder=await drive.getFile(state.upload.packageFolderId,'id,mimeType,trashed,driveId,parents');if(folder.trashed||folder.driveId!==drive.root.driveId||!folder.parents?.includes(survey.id))throw new Error('The saved upload folder is no longer inside this survey.');return;}
  const packageName=sid+'_record_'+state.uid;
  const pack=await drive.folder(survey.id,packageName,{submissionId:state.uid,surveyId:sid});
  state.upload={...state.upload,surveyId:sid,rootFolderId:CONFIG.rootFolderId,surveyFolderId:survey.id,packageFolderId:pack.id,artifacts:state.upload.artifacts||{}};saveDraft();
}
async function putArtifact(name,blob){
  const previous=state.upload.artifacts[name];
  const result=await drive.upload(blob,{name,parent:state.upload.packageFolderId,fileId:previous,signal:controller.signal,onReserved:async id=>{state.upload.artifacts[name]=id;saveDraft();}});
  state.upload.artifacts[name]=result.id;saveDraft();return result;
}
function progress(message,done,total){
  sessionProgress=message;const display=$('[data-upload-message]');if(display)display.textContent=message;
  const percent=total?Math.min(100,Math.round(done/total*100)):0;const bar=$('[role="progressbar"]');if(bar){bar.setAttribute('aria-valuenow',percent);bar.querySelector('.ss-progress-fill').style.width=percent+'%';}
}
async function submit(){
  const issues=reviewIssues();if(issues.length){$('.ss-review-errors').textContent=issues.join(' ');return;}
  if(!drive.connected){status('Connect Google Drive first, then submit.',true);return;}
  const actor=accountIdentity(drive.user);
  if(state.submittedBy?.permissionId&&state.submittedBy.permissionId!==actor.permissionId){status('This draft belongs to another Google account. Reconnect with its submitting account.',true);return;}
  state.submittedBy=actor;state.recordId=state.recordId||state.uid;saveDraft();
  busy=true;controller=new AbortController();render();
  try {
    await prepareFolders();const sid=surveyId(state),parent=state.upload.packageFolderId;
    progress('Saving the initial survey record…',0,1);
    await putArtifact(sid+'_submission.json',new Blob([JSON.stringify(metadata(state,schema(),'uploading'),null,2)],{type:'application/json'}));
    const metadataId=state.upload.artifacts[sid+'_submission.json'];
    await drive.updateProperties(metadataId,recordProperties(state,drive.user,CONFIG.rootFolderId,'uploading'));
    const folderCache=new Map(),referenceCache=new Map();let completedBytes=0;const totalBytes=state.files.reduce((n,f)=>n+f.size,0);
    for(let i=0;i<state.files.length;i++){
      const entry=state.files[i];if(controller.signal.aborted)throw new Error('Upload paused. Keep the page open to resume.');
      if(entry.inherited){await drive.verifyInherited(entry,state.upload.surveyFolderId,referenceCache);completedBytes+=entry.size;progress('Verified earlier original '+(i+1)+' / '+state.files.length,completedBytes,totalBytes);continue;}
      const parts=safePath(entry.path);const leaf=parts.pop();let target=parent;
      for(const part of [entry.group,...parts]){const key=target+'/'+part;if(!folderCache.has(key))folderCache.set(key,(await drive.folder(target,sid+'_'+part)).id);target=folderCache.get(key);}
      if(entry.uploaded&&entry.driveFileId){const remote=await drive.getFile(entry.driveFileId);if(remote.trashed||Number(remote.size)!==entry.size||!remote.parents?.includes(target))throw new Error('A previously uploaded file is missing or changed: '+entry.path);completedBytes+=entry.size;progress('Verified '+(i+1)+' / '+state.files.length+' files',completedBytes,totalBytes);continue;}
      const file=selectedFiles.get(entry.identity);if(!file)throw new Error('Reselect '+entry.path+' before resuming.');
      entry.parentId=target;entry.storedName=leaf.startsWith(sid+'_')?leaf:sid+'_'+leaf;
      if(entry.driveFileId){const existing=await drive.getFile(entry.driveFileId);if(existing.trashed||!existing.parents?.includes(target))throw new Error('The reserved file moved outside this submission: '+entry.path);}
      const remote=await drive.upload(file,{name:entry.storedName,parent:target,fileId:entry.driveFileId,signal:controller.signal,onReserved:async id=>{entry.driveFileId=id;saveDraft();},onProgress:bytes=>progress('Uploading '+(i+1)+' / '+state.files.length+' · '+entry.path,completedBytes+bytes,totalBytes)});
      entry.driveFileId=remote.id;entry.uploaded=true;completedBytes+=entry.size;saveDraft();
    }
    progress('Saving measurement tables and the report…',1,1);
    for(const table of getTables())await putArtifact(sid+'_'+table.id+'.csv',new Blob([tableCSV(table.columns,state.tables[table.id]||[],sid)],{type:'text/csv;charset=utf-8'}));
    const record=metadata(state,schema(),'complete');record.qualityReviewed=!!state.qualityReviewed;
    await putArtifact(sid+'_field_report.pdf',await makeReport(record,schema(),getTables()));
    await putArtifact(sid+'_file_manifest.json',new Blob([JSON.stringify({submissionId:state.uid,surveyId:sid,files:record.files,verification:'Drive file ID, parent and byte size checked after upload'},null,2)],{type:'application/json'}));
    await putArtifact(sid+'_file_links.csv',new Blob([tableCSV(['Category','Original path','Size (bytes)','Drive link','Earlier original'],state.files.map(f=>[f.group,f.path,String(f.size),'https://drive.google.com/file/d/'+f.driveFileId+'/view',f.inherited?'Yes':'No']),sid)],{type:'text/csv;charset=utf-8'}));
    // This final write is the completion marker. Failures above leave status=uploading.
    await putArtifact(sid+'_submission.json',new Blob([JSON.stringify(record,null,2)],{type:'application/json'}));
    await drive.updateProperties(metadataId,recordProperties(state,drive.user,CONFIG.rootFolderId,'complete'));
    recordFiles=[];recordDetail=null;
    state.done=true;state.step=3;saveDraft();status('Submission saved and verified.');
  }catch(error){errorMessage(error);}
  finally{busy=false;controller=null;render();}
}
function dirty(){state.confirmed=false;scheduleSave();}
root.addEventListener('input',e=>{const t=e.target;
  if(t.dataset.table){state.tables[t.dataset.table][+t.dataset.row][+t.dataset.col]=t.value;dirty();return;}
  if(t.dataset.field&&t.type!=='checkbox'&&t.tagName!=='SELECT'){
    if(t.dataset.scope==='value')state.values[t.dataset.field]=t.value;else if(t.dataset.scope==='base')state[t.dataset.field]=t.value;
    dirty();if(t.dataset.field==='date')summary();
  }
});
root.addEventListener('change',async e=>{const t=e.target;try{
  if(t.dataset.field){
    if(t.dataset.scope==='file'){fileGroup=t.value;render();return;}
    if(t.dataset.scope==='value')state.values[t.dataset.field]=t.value;else state[t.dataset.field]=t.type==='checkbox'?t.checked:t.value;
    if(t.dataset.field==='area')state.timezone={BZ:'UTC-06:00',SC:'UTC+04:00',FJ:'UTC+12:00'}[state.area]||state.timezone;
    if(t.dataset.field!=='confirmed')state.confirmed=false;
    saveDraft();if(['area','structure_method'].includes(t.dataset.field))render();else summary();
  }
  if(t.dataset.check!==undefined){state.checks[t.dataset.check]=t.checked;dirty();}
  if(t.hasAttribute('data-table-choice')){tableChoice=t.value;render();}
  if(t.hasAttribute('data-add-files')||t.hasAttribute('data-add-folder'))addFiles(Array.from(t.files));
  if(t.hasAttribute('data-import-csv')&&t.files[0])await importCSV(t.files[0]);
  if(t.hasAttribute('data-import-draft')&&t.files[0]){
    if(t.files[0].size>20*1024*1024)throw new Error('This draft is larger than 20 MB.');
    const imported=validateDraft(JSON.parse(await t.files[0].text()),SURVEYS);
    if(confirm('Replace the draft on this browser with the imported survey?')){state=imported;selectedFiles.clear();tableChoice='';fileGroup='';saveDraft();render();status('Draft imported. Reselect original files before resuming.');}
  }
}catch(error){errorMessage(error);}});
root.addEventListener('click',async e=>{const button=e.target.closest('button');if(!button)return;
  try {
    if(busy){if(button.dataset.action==='next'){controller?.abort();status('Pausing after the current request…');}return;}
    if(button.dataset.view){view=button.dataset.view;recordDetail=null;render();if(view==='records')await loadRecords();return;}
    if(button.dataset.openRecord){await openRecord(button.dataset.openRecord);return;}
    if(button.dataset.editRecord){await editRecord(button.dataset.editRecord);return;}
    if(button.dataset.history){if(openHistory.has(button.dataset.history))openHistory.delete(button.dataset.history);else openHistory.add(button.dataset.history);renderRecords();return;}
    if(button.dataset.type){
      const type=button.dataset.type;if(type===state.type)return;
      if((Object.keys(state.values).length||state.files.length)&&!confirm('Changing survey type starts a fresh set of measurements and files. Download the current draft first if you want to keep it. Continue?'))return;
      state={...newDraft(type),area:state.area,corridor:state.corridor,date:state.date,operators:state.operators,filledBy:state.filledBy,timezone:state.timezone};selectedFiles.clear();tableChoice='';fileGroup='';saveDraft();render();return;
    }
    if(button.dataset.step!==undefined){state.step=+button.dataset.step;saveDraft();render();return;}
    if(button.dataset.removeRow!==undefined){state.tables[tableChoice].splice(+button.dataset.removeRow,1);dirty();render();return;}
    if(button.dataset.clearGroup){if(!confirm('Remove these files from the draft? Already uploaded files on Drive will remain.'))return;state.files=state.files.filter(f=>f.group!==button.dataset.clearGroup);dirty();render();return;}
    switch(button.dataset.action){
      case 'connect':button.disabled=true;recordsEpoch++;recordFiles=[];recordDetail=null;status('Connecting to the SEASTRONG submission folder…');try{await drive.connect();status('Connected. Uploads will be saved inside the SEASTRONG submission folder.');if(view==='records')await loadRecords();}finally{button.disabled=false;summary();if(view==='records')renderRecords();}break;
      case 'save':saveDraft(false);break;
      case 'export':download(new Blob([JSON.stringify(state,null,2)],{type:'application/json'}),(surveyId(state)||'SEASTRONG')+'_draft.json');break;
      case 'back':state.step--;saveDraft();render();break;
      case 'next':if(state.step===3){await submit();break;}if(state.step===0){const issues=validateDetails(state,SURVEYS);if(issues.length){status(issues.join(' '),true);return;}}state.step++;saveDraft();status('');render();break;
      case 'add-row':{const table=getTables().find(t=>t.id===tableChoice);state.tables[table.id].push(table.columns.map(()=>''));dirty();render();break;}
      case 'template':{const table=getTables().find(t=>t.id===tableChoice);download(new Blob([tableCSV(table.columns,[],surveyId(state))],{type:'text/csv;charset=utf-8'}),table.id+'_template.csv');break;}
      case 'report':{const record=metadata(state,schema(),'draft');download(await makeReport(record,schema(),getTables()),(surveyId(state)||'SEASTRONG')+'_report_preview.pdf');break;}
      case 'revision':{const id=state.upload.artifacts?.[surveyId(state)+'_submission.json'];if(!id)throw new Error('Open the record from My records to edit it.');await editRecord(id);break;}
      case 'refresh-records':recordDetail=null;await loadRecords();break;
      case 'records-back':recordDetail=null;renderRecords();break;
      case 'download-record':if(recordDetail)download(new Blob([JSON.stringify(recordDetail.record,null,2)],{type:'application/json'}),recordDetail.record.surveyId+'_record.json');break;
      case 'new':if(confirm('Start a fresh survey? Download the current draft first if it has not been submitted.')){state=newDraft();selectedFiles.clear();tableChoice='';fileGroup='';saveDraft();render();status('New survey started.');}break;
    }
  }catch(error){if(view==='records'){recordsError=error.message||String(error);renderRecords();}else errorMessage(error);}
});
window.addEventListener('beforeunload',e=>{if(busy){e.preventDefault();e.returnValue='';}saveDraft();});
seedTables();render();
// Load Google's libraries before the user clicks, so Safari retains the click's
// popup permission when the token chooser opens. This does not sign in a user.
if(drive.configured&&/^https?:$/.test(location.protocol))drive.prepare().catch(()=>{status('Google could not load. Check your connection, then use Connect Google Drive to retry.',true);});
