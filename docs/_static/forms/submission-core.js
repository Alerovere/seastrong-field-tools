export const VERSION = '1.1.0';
export const AREAS = { BZ: 'Belize', SC: 'Seychelles', FJ: 'Fiji' };
export const DATASET_TYPE = 'sat';
// Corridors 1-6 follow the field protocols; CX = data collected outside the corridors (always "additional data").
export const CORRIDORS = [...Array.from({length:6},(_,i)=>['C'+(i+1),'Corridor '+(i+1)]),['CX','Other · outside the corridors']];
export const OUTSIDE_FOLDER = 'Other (outside corridors)';
export function corridorFolder(s) { return s.corridor === 'CX' ? OUTSIDE_FOLDER : s.corridor; }
export const DATA_CATEGORIES = [['protocol','Corridor data according to protocols'],['additional','Additional data']];
const PRODUCT_CODE = /^[A-Za-z0-9]{2,20}$/;
export function surveyId(s) {
  const match = /^(\d{4})-(\d{2})-(\d{2})$/.exec(s.date || '');
  if (s.type === DATASET_TYPE) {
    // Satellite-derived dataset: explicit ID <area>-<AOI>-<product>-<YYYY-MM-DD><suffix>, e.g. BZ-South-S2composite-2026-11-06
    const product = s.values?.product || '', aoi = s.values?.aoi || '';
    if (!match || !AREAS[s.area] || !PRODUCT_CODE.test(product) || !PRODUCT_CODE.test(aoi) || !/^[A-Z]?$/.test(s.suffix)) return '';
    const d = new Date(`${s.date}T12:00:00Z`);
    if (Number.isNaN(+d) || d.toISOString().slice(0,10) !== s.date) return '';
    return `${s.area}-${aoi}-${product}-${s.date}${s.suffix}`;
  }
  if (!match || !AREAS[s.area] || !/^C[1-6X]$/.test(s.corridor) || !/^[A-Z]?$/.test(s.suffix)) return '';
  const date = new Date(`${s.date}T12:00:00Z`);
  if (Number.isNaN(+date) || date.toISOString().slice(0,10) !== s.date) return '';
  return `${s.area}${match[3]}${match[2]}${match[1].slice(2)}${s.corridor}${s.type}${s.suffix}`;
}
export function escapeHTML(value) { return String(value ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c])); }
export function validateDetails(s, surveys) {
  const issues=[];
  if (!surveys[s.type]) issues.push('Choose a survey type.');
  if (s.type === DATASET_TYPE) {
    if (!s.values?.product) issues.push('Choose the product.');
    if (!PRODUCT_CODE.test(s.values?.aoi || '')) issues.push('Enter the AOI name: 2-20 letters or digits, no spaces (e.g. South).');
    if (!surveyId(s)) issues.push('Choose a valid study area, product and processing date.');
    if (!s.operators?.trim()) issues.push('Enter who processed the dataset.');
    if (!s.filledBy?.trim()) issues.push('Enter the name of the person submitting this record.');
    return issues;
  }
  if (!surveyId(s)) issues.push('Choose a valid study area, corridor and survey date.');
  if (!DATA_CATEGORIES.some(([k]) => k === s.dataCategory)) issues.push('Choose the data category: corridor data according to protocols, or additional data.');
  if (s.corridor === 'CX' && s.dataCategory === 'protocol') issues.push('Data collected outside the corridors are additional data.');
  if (s.corridor === 'CX' && !s.corridorName?.trim()) issues.push('Enter the site name for data collected outside the corridors.');
  if (!s.operators?.trim()) issues.push('Enter the names of the operators.');
  if (!s.filledBy?.trim()) issues.push('Enter the name of the person submitting this record.');
  if (!/^UTC[+-](?:0\d|1[0-4]):[0-5]\d$/.test(s.timezone || '')) issues.push('Choose the UTC offset of the field clock.');
  return issues;
}
export function safePath(path) {
  const parts=String(path).replaceAll('\\','/').split('/');
  if(parts.some(p=>!p || p==='.' || p==='..' || /[\u0000-\u001f]/.test(p))) throw new Error('A selected filename contains an invalid path.');
  return parts;
}
export function fileIdentity(group,path,size,lastModified) { safePath(path); return JSON.stringify([group,path,size,lastModified]); }
export function formatBytes(n) { if(!n)return '0 B'; const units=['B','KB','MB','GB','TB'];const i=Math.min(4,Math.floor(Math.log(n)/Math.log(1024)));return `${(n/1024**i).toFixed(i>1?1:0)} ${units[i]}`; }
export function csvCell(value) {
  let text=String(value ?? '');
  // Keep measurement numbers numeric; neutralise spreadsheet formulas in text cells.
  if (/^[\s]*[=+@-]/.test(text) && !/^[+-]?\d+(?:\.\d+)?(?:[eE][+-]?\d+)?$/.test(text.trim())) text="'"+text;
  return '"'+text.replaceAll('"','""')+'"';
}
export function tableCSV(headers,rows,sid,context={}) { const withName=Object.hasOwn(context,'corridorName');return '\ufeff'+[['survey_id',...(withName?['corridor_name']:[]),...headers],...rows.filter(r=>r.some(v=>String(v).trim())).map(r=>[sid,...(withName?[context.corridorName||'']:[]),...r])].map(r=>r.map(csvCell).join(',')).join('\r\n')+'\r\n'; }
export function metadata(s,schema,status='draft') {
  return {schemaVersion:VERSION,sourcePDFVersion:schema.sourceVersion,submissionId:s.uid,surveyId:surveyId(s),status,
    studyArea:s.area,studyAreaName:AREAS[s.area],corridor:s.corridor,corridorName:s.corridorName||'',dataCategory:s.dataCategory||'',surveyType:s.type,surveyDate:s.date,
    clockUTCOffset:s.timezone,operators:s.operators,filledInBy:s.filledBy,recordStage:s.recordStage,
    surveyComplete:s.surveyComplete,notes:s.notes,missingFilesReason:s.missingFilesReason,qualityReviewed:!!s.qualityReviewed,
    submittedBy:s.submittedBy||null,recordId:s.recordId||s.uid,revisionNumber:s.revisionNumber||1,revisionOf:s.revisionOf||null,
    sourceMetadataFileId:s.sourceMetadataFileId||null,
    fields:s.values,tables:s.tables,checklists:s.checks,
    files:s.files.map(({identity,...file})=>file),savedAt:new Date().toISOString(),
    folderId:s.upload?.surveyFolderId||null,packageFolderId:s.upload?.packageFolderId||null};
}
export function newDraft(type='reef') {
  const now=new Date();const localDate=[now.getFullYear(),String(now.getMonth()+1).padStart(2,'0'),String(now.getDate()).padStart(2,'0')].join('-');
  return {version:VERSION,uid:crypto.randomUUID(),step:0,type,area:'BZ',corridor:'C1',corridorName:'',dataCategory:'',date:localDate,suffix:'',
    operators:'',filledBy:'',timezone:'UTC-06:00',recordStage:'Post-site report',surveyComplete:'',
    values:{},tables:{},checks:{},notes:'',files:[],missingFilesReason:'',confirmed:false,upload:{},done:false,
    submittedBy:null,recordId:null,revisionNumber:1,revisionOf:null,sourceMetadataFileId:null};
}
export function validateDraft(value,surveys) {
  if(!value || !['1.0.0',VERSION].includes(value.version) || !surveys[value.type] || typeof value.uid!=='string' || !/^[a-f0-9-]{36}$/.test(value.uid)) throw new Error('This is not a supported SEASTRONG draft.');
  for(const key of ['values','tables','checks','upload']) if(!value[key]||typeof value[key]!=='object'||Array.isArray(value[key])) throw new Error('The draft is missing '+key+'.');
  for(const key of ['area','corridor','date','suffix','operators','filledBy','timezone','recordStage','surveyComplete','notes','missingFilesReason']) if(typeof value[key]!=='string')throw new Error('The draft has an invalid '+key+' field.');
  if(value.corridorName!==undefined&&typeof value.corridorName!=='string')throw new Error('The draft has an invalid corridor name.');
  if(value.dataCategory!==undefined&&!['',...DATA_CATEGORIES.map(([k])=>k)].includes(value.dataCategory))throw new Error('The draft has an invalid data category.');
  if(Object.values(value.values).some(v=>typeof v!=='string'))throw new Error('The draft contains an invalid field value.');
  if(Object.values(value.checks).some(v=>typeof v!=='boolean'))throw new Error('The draft contains an invalid checklist.');
  if(value.submittedBy!=null&&(typeof value.submittedBy.permissionId!=='string'||!value.submittedBy.permissionId))throw new Error('The draft contains an invalid Google account.');
  for(const key of ['recordId','revisionOf'])if(value[key]!=null&&!/^[a-f0-9-]{36}$/.test(value[key]))throw new Error('The draft contains an invalid record lineage.');
  if(value.revisionNumber!==undefined&&(!Number.isSafeInteger(value.revisionNumber)||value.revisionNumber<1))throw new Error('The draft contains an invalid version number.');
  if(!Array.isArray(value.files) || value.files.length>100000)throw new Error('The draft file list is invalid.');
  if(Object.values(value.tables).some(rows=>!Array.isArray(rows)||rows.some(r=>!Array.isArray(r)||r.some(c=>typeof c!=='string'))))throw new Error('The draft contains an invalid measurement table.');
  for(const f of value.files) {if(typeof f.path!=='string'||!/^\w+$/.test(f.group)||!Number.isSafeInteger(f.size)||f.size<0||!Number.isSafeInteger(f.lastModified)||typeof f.key!=='string')throw new Error('Invalid file record.');safePath(f.path);f.identity=fileIdentity(f.group,f.path,f.size,f.lastModified);}
  return {...newDraft(value.type),...value,version:VERSION,confirmed:false};
}
export async function readDraft(storage,key,surveys) { try{const raw=storage.getItem(key);return raw?validateDraft(JSON.parse(raw),surveys):null;}catch{return null;} }

/* Large photo sets: suggest ZIP archives above this many individual (non-archive) files in one category. */
export const ZIP_SUGGEST_FILES = 100;
const ARCHIVE = /\.(zip|7z|tar|tgz|gz)$/i;
export function zipSuggestions(files, groups, limit = ZIP_SUGGEST_FILES) {
  return groups.map(([key, label]) => ({key, label,
    count: files.filter(f => f.group === key && !f.inherited && !ARCHIVE.test(f.path || '')).length}))
    .filter(g => g.count > limit);
}
