import {newDraft,validateDraft,surveyId} from './submission-core.js';

export function accountIdentity(user) {
  if(!user?.permissionId)throw new Error('Google did not identify your account. Reconnect Google Drive and try again.');
  return {permissionId:user.permissionId,emailAddress:user.emailAddress||'',displayName:user.displayName||''};
}

export function isMyRecord(file,user) {
  if(!user?.permissionId)return false;
  if(file.appProperties?.seastrongRecord==='1')return file.appProperties.submittedBy===user.permissionId;
  // The first version did not retain authorship. Match these earlier files only
  // to Google's last modifying user and make that limitation explicit in the UI.
  return !!file.lastModifyingUser&&(file.lastModifyingUser.permissionId===user.permissionId||file.lastModifyingUser.me===true);
}

export function recordProperties(state,user,rootFolderId,status) {
  const actor=accountIdentity(user);
  return {seastrongRecord:'1',submittedBy:actor.permissionId,rootFolderId,surveyId:surveyId(state),
    surveyType:state.type,surveyDate:state.date,recordId:state.recordId||state.uid,
    submissionId:state.uid,revisionNumber:String(state.revisionNumber||1),
    recordStatus:status,recordStage:state.recordStage,corridorName:Array.from(state.corridorName||'').slice(0,24).join(''),
    ...(state.type==='sat'?{datasetProduct:state.values?.product||'',reviewStatus:'draft'}:{})};
}

export function groupRecords(files) {
  const groups=new Map();
  for(const file of files){const key=file.appProperties?.recordId||file.appProperties?.submissionId||file.legacyRecordId||file.id;
    if(!groups.has(key))groups.set(key,[]);groups.get(key).push(file);}
  for(const rows of groups.values())rows.sort((a,b)=>(Number(b.appProperties?.revisionNumber)||1)-(Number(a.appProperties?.revisionNumber)||1)||String(b.modifiedTime||'').localeCompare(a.modifiedTime||''));
  return [...groups.values()].sort((a,b)=>String(b[0].modifiedTime||'').localeCompare(a[0].modifiedTime||''));
}

export function restoreRecord(record,file,surveys) {
  if(!record||!surveys[record.surveyType]||!['1.0.0','1.1.0'].includes(record.schemaVersion))throw new Error('This record format is not supported.');
  const draft={...newDraft(record.surveyType),uid:record.submissionId,area:record.studyArea,corridor:record.corridor,corridorName:record.corridorName||'',date:record.surveyDate,
    operators:record.operators,filledBy:record.filledInBy,timezone:record.clockUTCOffset,recordStage:record.recordStage,
    surveyComplete:record.surveyComplete,notes:record.notes||'',missingFilesReason:record.missingFilesReason||'',
    qualityReviewed:!!record.qualityReviewed,values:structuredClone(record.fields),tables:structuredClone(record.tables),checks:structuredClone(record.checklists),
    files:structuredClone(record.files),submittedBy:record.submittedBy||null,recordId:record.recordId||record.submissionId,
    revisionNumber:record.revisionNumber||1,revisionOf:record.revisionOf||null,done:record.status==='complete',
    upload:{surveyFolderId:record.folderId,packageFolderId:record.packageFolderId,
      surveyId:record.surveyId,artifacts:{[record.surveyId+'_submission.json']:file.id}}};
  const base=surveyId(draft);
  if(!base||!record.surveyId?.startsWith(base))throw new Error('The saved survey ID does not match its survey details.');
  draft.suffix=record.surveyId.slice(base.length);
  if(surveyId(draft)!==record.surveyId)throw new Error('The saved survey ID has an invalid suffix.');
  const validated=validateDraft(draft,surveys);
  if(validated.files.some(f=>!f.uploaded||!f.driveFileId||!f.parentId)){
    if(record.status==='complete')throw new Error('The completed record has an incomplete file manifest.');
  }
  return validated;
}

export function editAsRevision(record,file,user,rootFolderId,surveys) {
  if(!isMyRecord(file,user))throw new Error('This record belongs to another Google account.');
  if(record.status!=='complete')throw new Error('This upload is incomplete. Resume its original browser draft or import a downloaded draft.');
  if(record.submittedBy?.permissionId&&record.submittedBy.permissionId!==user.permissionId)throw new Error('The saved author does not match your Google account.');
  const actor=accountIdentity(user),previous=restoreRecord(record,file,surveys);
  if(!previous.upload.packageFolderId||!previous.upload.surveyFolderId)throw new Error('This record is missing its Drive location.');
  return {...previous,uid:crypto.randomUUID(),step:0,done:false,confirmed:false,submittedBy:actor,
    revisionOf:previous.uid,revisionNumber:previous.revisionNumber+1,sourceMetadataFileId:file.id,
    files:previous.files.map(f=>({...f,inherited:true,sourcePackageId:f.sourcePackageId||previous.upload.packageFolderId,uploaded:true})),
    upload:{surveyFolderId:previous.upload.surveyFolderId,rootFolderId,surveyId:record.surveyId}};
}
