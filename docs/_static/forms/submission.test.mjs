import test from 'node:test';
import assert from 'node:assert/strict';
import {surveyId,newDraft,tableCSV,validateDetails,validateDraft,fileIdentity,metadata,VERSION,zipSuggestions,ZIP_SUGGEST_FILES} from './submission-core.js';
import {DriveClient} from './drive-client.js';
import {SURVEYS} from './survey-schema.js';
import {TABLES} from './survey-tables.js';
import {editAsRevision,recordProperties,groupRecords,isMyRecord,restoreRecord} from './submission-records.js';

test('survey IDs preserve project dates, region, type and duplicate suffix',()=>{
  const state={...newDraft(),date:'2027-03-14',area:'BZ',corridor:'C1'};
  assert.equal(surveyId(state),'BZ140327C1reef');
  assert.equal(surveyId({...state,suffix:'B'}),'BZ140327C1reefB');
  assert.equal(surveyId({...state,date:'2027-02-29'}),'');
  assert.equal(surveyId({...state,date:'2028-02-29'}),'BZ290228C1reef');
  assert(validateDetails(state,SURVEYS).some(x=>x.includes('operators')));
});
test('CSV retains multiline and quoted values, numeric negatives, and neutralises text formulas',()=>{
  const csv=tableCSV(['Depth','Notes'],[['-1.25','=HYPERLINK("https://example.org")'],['2','a,"b"\nnext']], 'BZ140327C1reef');
  assert(csv.includes('"-1.25"'));assert(csv.includes('"\'=HYPERLINK(""https://example.org"")"'));
  assert(csv.includes('"a,""b""\nnext"'));
});
test('draft validation rejects incompatible and malformed drafts without trusting filenames',()=>{
  const state=newDraft('waves');
  assert.equal(validateDraft(JSON.parse(JSON.stringify(state)),SURVEYS).type,'waves');
  assert.throws(()=>validateDraft({...state,operators:{}},SURVEYS));
  assert.throws(()=>fileIdentity('photos','../private.jpg',1,1));
  assert.throws(()=>validateDraft({...state,files:[{key:'file',path:'a',group:'photos',size:-1,lastModified:1}]},SURVEYS));
  assert.equal(TABLES.waves[0].seed.length,7);
  assert.equal(TABLES.seagrass.find(t=>t.id==='quadrats').seed.length,9);
  assert.equal(TABLES.seagrass.find(t=>t.id==='shoots').seed.length,45);
});
test('resumable upload uses confirmed ranges and verifies size and parent',async()=>{
  const original=globalThis.fetch;const size=8*1024*1024+11;const ranges=[];
  const client=new DriveClient({});client.token='test';client.expires=Date.now()+60000;
  globalThis.fetch=async(url,init={})=>{
    if(url.includes('uploadType=resumable'))return new Response('',{status:200,headers:{Location:'https://upload.test/session'}});
    if(url==='https://upload.test/session'){
      ranges.push(init.headers['Content-Range']);
      if(ranges.length===1)return new Response('',{status:308,headers:{Range:'bytes=0-8388607'}});
      return Response.json({id:'file',size:String(size)});
    }
    if(url.includes('/files/file?'))return Response.json({id:'file',size:String(size),parents:['parent']});
    throw new Error('Unexpected request');
  };
  try{const result=await client.upload(new Blob([new Uint8Array(size)]),{fileId:'file',name:'photos.bin',parent:'parent'});assert.equal(result.id,'file');assert.deepEqual(ranges,[`bytes 0-8388607/${size}`,`bytes 8388608-${size-1}/${size}`]);}
  finally{globalThis.fetch=original;}
});
test('expired sign-in and wrong destination never count as completed uploads',async()=>{
  const original=globalThis.fetch;const client=new DriveClient({});client.token='test';client.expires=Date.now()+60000;
  globalThis.fetch=async()=>new Response('',{status:401});
  try{await assert.rejects(client.getFile('file'),/session expired/);assert.equal(client.connected,false);}
  finally{globalThis.fetch=original;}
  const verify=new DriveClient({});verify.getFile=async()=>({id:'file',size:'3',parents:['other-folder']});
  await assert.rejects(verify.verify({id:'file'},new Blob(['abc']),'expected-folder'),/could not be verified/);
});

async function connectionFixture({status=0,selected='project-folder'}={}){
  const priorGoogle=globalThis.google,priorLocation=globalThis.location;
  const calls={picker:0,ids:[],features:[],scope:null};
  globalThis.location={protocol:'http:',origin:'http://localhost:8000'};
  globalThis.google={accounts:{oauth2:{initTokenClient:options=>({requestAccessToken(){calls.scope=options.scope;options.callback({access_token:'simulated',expires_in:3600});}})}},picker:{
    ViewId:{FOLDERS:'folders'},Action:{PICKED:'picked',CANCEL:'cancel'},Feature:{NAV_HIDDEN:'nav-hidden'},
    DocsView:class {setIncludeFolders(){return this;}setSelectFolderEnabled(){return this;}setFileIds(ids){calls.ids.push(ids);return this;}setEnableDrives(){throw new Error('Do not display all shared drives.');}},
    PickerBuilder:class {setAppId(){return this;}setDeveloperKey(){return this;}setOAuthToken(){return this;}setOrigin(){return this;}setTitle(){return this;}enableFeature(feature){calls.features.push(feature);return this;}addView(){return this;}setCallback(fn){this.callback=fn;return this;}build(){const callback=this.callback;return {setVisible(){calls.picker++;queueMicrotask(()=>callback({action:'picked',docs:[{id:selected}]}));},dispose(){}};}},
  }};
  const client=new DriveClient({googleClientId:'client',googleApiKey:'key',googleProjectNumber:'project',rootFolderId:'project-folder'});client.ready=true;
  let count=0;client.getFile=async()=>{if(++count===1&&status){const error=new Error('Unavailable');error.status=status;throw error;}return {id:'project-folder',name:'Survey submissions',mimeType:'application/vnd.google-apps.folder',driveId:'shared-drive',capabilities:{canAddChildren:true}};};
  client.json=async()=>({user:{emailAddress:'example@example.org'}});
  return {client,calls,restore(){if(priorGoogle===undefined)delete globalThis.google;else globalThis.google=priorGoogle;if(priorLocation===undefined)delete globalThis.location;else globalThis.location=priorLocation;}};
}
test('previously authorised project folder connects without opening a Drive browser',async()=>{
  const f=await connectionFixture();try{await f.client.connect();assert.equal(f.calls.picker,0);assert.equal(f.client.root.id,'project-folder');assert.equal(f.calls.scope,'https://www.googleapis.com/auth/drive.file');}finally{f.restore();}
});
test('first grant only offers the configured folder and hides navigation',async()=>{
  const f=await connectionFixture({status:404});try{await f.client.connect();assert.equal(f.calls.picker,1);assert.deepEqual(f.calls.ids,['project-folder']);assert.deepEqual(f.calls.features,['nav-hidden']);}finally{f.restore();}
});
test('a different folder or a forbidden API request cannot become an upload destination',async()=>{
  let f=await connectionFixture({status:404,selected:'unrelated-folder'});try{await assert.rejects(f.client.connect(),/configured Survey submissions/);assert.equal(f.client.root,null);assert.equal(f.client.token,null);}finally{f.restore();}
  f=await connectionFixture({status:403});try{await assert.rejects(f.client.connect(),/Unavailable/);assert.equal(f.calls.picker,0);}finally{f.restore();}
});

function savedRecord(){
  const user={permissionId:'user-A',emailAddress:'a@example.org',displayName:'Researcher A'};
  const state={...newDraft('reef'),date:'2027-03-14',operators:'Field team',filledBy:'Researcher A',surveyComplete:'Yes',qualityReviewed:true,
    submittedBy:user,values:{visibility_m:'6'},tables:{targets:[['T01','2.5','L','1.6','1.6','1.7','10:42']]},
    files:[{key:'original',group:'camA',path:'photo.jpg',size:3,lastModified:1,type:'image/jpeg',uploaded:true,driveFileId:'raw',parentId:'group',storedName:'BZ140327C1reef_photo.jpg'}],
    upload:{surveyFolderId:'survey',packageFolderId:'pack'}};
  const record=metadata(state,SURVEYS.reef,'complete');
  const file={id:'meta',name:record.surveyId+'_submission.json',mimeType:'application/json',size:'2000',parents:['pack'],driveId:'shared-drive',appProperties:recordProperties(state,user,'root','complete'),lastModifyingUser:{...user,me:true},modifiedTime:'2026-11-04T20:00:00Z'};
  return {user,state,record,file};
}
test('editing restores all measurements and links original files without mutating the earlier version',()=>{
  const f=savedRecord(),before=JSON.stringify(f.record);
  const revision=editAsRevision(f.record,f.file,f.user,'root',SURVEYS);
  assert.notEqual(revision.uid,f.record.submissionId);assert.equal(revision.recordId,f.record.submissionId);assert.equal(revision.revisionNumber,2);assert.equal(revision.revisionOf,f.record.submissionId);
  assert.equal(revision.files[0].inherited,true);assert.equal(revision.files[0].sourcePackageId,'pack');assert.equal(revision.files[0].driveFileId,'raw');assert.equal(revision.upload.packageFolderId,undefined);
  revision.values.visibility_m='10';revision.tables.targets[0][3]='2.0';
  assert.equal(JSON.stringify(f.record),before);
});
test('another account cannot reopen a saved record for editing, even if its last writer matches',()=>{
  const f=savedRecord(),other={permissionId:'user-B'};
  assert.equal(isMyRecord(f.file,other),false);
  assert.throws(()=>editAsRevision(f.record,f.file,other,'root',SURVEYS),/another Google account/);
  const partial={...f.record,status:'uploading'};assert.throws(()=>editAsRevision(partial,f.file,f.user,'root',SURVEYS),/incomplete/);
});
test('earlier drafts and sent records stay compatible and appear in their revision history',()=>{
  const f=savedRecord(),legacy=structuredClone(f.record);legacy.schemaVersion='1.0.0';delete legacy.submittedBy;delete legacy.recordId;delete legacy.revisionNumber;
  const file={...f.file,appProperties:{},legacyRecordId:legacy.submissionId};
  assert(isMyRecord(file,f.user));const revision=editAsRevision(legacy,file,f.user,'root',SURVEYS);
  assert.equal(revision.submittedBy.permissionId,f.user.permissionId);assert.equal(revision.recordId,legacy.submissionId);
  assert.equal(validateDraft({...f.state,version:'1.0.0'},SURVEYS).version,VERSION);
  const newer={...f.file,id:'new-meta',appProperties:recordProperties(revision,f.user,'root','complete'),modifiedTime:'2026-11-04T21:00:00Z'};
  const grouped=groupRecords([file,newer]);assert.equal(grouped.length,1);assert.equal(grouped[0][0].id,'new-meta');assert.equal(grouped[0].length,2);
  assert.equal(restoreRecord(f.record,f.file,SURVEYS).files[0].identity,fileIdentity('camA','photo.jpg',3,1));
});
test('record discovery excludes other accounts and files outside the configured root',async()=>{
  const f=savedRecord(),client=new DriveClient({rootFolderId:'root'});client.token='test';client.expires=Date.now()+60000;client.root={id:'root',driveId:'shared-drive'};client.user=f.user;
  const nodes={pack:{id:'pack',name:'survey_record_'+f.record.submissionId,parents:['survey'],driveId:'shared-drive',appProperties:{submissionId:f.record.submissionId}},survey:{id:'survey',parents:['root'],driveId:'shared-drive'},outside:{id:'outside',parents:['not-root'],driveId:'shared-drive'},'not-root':{id:'not-root',parents:[],driveId:'shared-drive'}};
  const own={...f.file},legacy={...f.file,id:'legacy',appProperties:{}},other={...f.file,id:'other',appProperties:{...f.file.appProperties,submittedBy:'user-B'}},outside={...f.file,id:'elsewhere',parents:['outside']};
  client.listRecordFiles=async q=>q.includes('appProperties')?[own,other,outside]:[own,legacy,other,outside];client.getFile=async id=>nodes[id];
  const results=await client.myRecords();assert.deepEqual(results.map(r=>r.id).sort(),['legacy','meta']);
});
test('earlier original reuse verifies size and survey ancestry',async()=>{
  const client=new DriveClient({});client.root={driveId:'shared-drive'};
  const nodes={pack:{id:'pack',parents:['survey'],driveId:'shared-drive'},group:{id:'group',parents:['pack'],driveId:'shared-drive'},raw:{id:'raw',size:'3',parents:['group'],driveId:'shared-drive'},outside:{id:'outside',parents:[],driveId:'shared-drive'}};
  client.getFile=async id=>nodes[id];
  const entry={sourcePackageId:'pack',driveFileId:'raw',size:3,parentId:'group',path:'photo.jpg'};
  assert.equal((await client.verifyInherited(entry,'survey')).id,'raw');
  await assert.rejects(client.verifyInherited({...entry,size:4},'survey'),/missing or changed/);
  await assert.rejects(client.verifyInherited({...entry,sourcePackageId:'outside'},'survey'),/outside this survey/);
});
test('opening a record checks the account and physical folder before downloading its data',async()=>{
  const f=savedRecord(),client=new DriveClient({rootFolderId:'root'});client.user=f.user;client.token='test';client.expires=Date.now()+60000;client.root={driveId:'shared-drive'};
  const nodes={meta:f.file,pack:{id:'pack',parents:['survey'],driveId:'shared-drive'},survey:{id:'survey',parents:['root'],driveId:'shared-drive'}};
  let reads=0;client.getFile=async id=>nodes[id];client.request=async()=>{reads++;return Response.json(f.record);};
  assert.equal((await client.readRecord('meta')).record.submissionId,f.record.submissionId);assert.equal(reads,1);
  nodes.meta={...f.file,appProperties:{...f.file.appProperties,submittedBy:'user-B'}};await assert.rejects(client.readRecord('meta'),/not an available record/);assert.equal(reads,1);
  nodes.meta={...f.file,parents:['outside']};nodes.outside={id:'outside',parents:[],driveId:'shared-drive'};await assert.rejects(client.readRecord('meta'),/outside the SEASTRONG/);assert.equal(reads,1);
});

test('corridor names survive JSON, CSV and revision editing without changing the survey ID',()=>{
  const f=savedRecord();f.state.corridorName='Mangrove Bay';
  const record=metadata(f.state,SURVEYS.reef,'complete');assert.equal(record.corridorName,'Mangrove Bay');assert.equal(record.surveyId,f.record.surveyId);
  const revision=editAsRevision(record,f.file,f.user,'root',SURVEYS);assert.equal(revision.corridorName,'Mangrove Bay');
  const csv=tableCSV(['Depth'],[['-1.25']],record.surveyId,{corridorName:revision.corridorName});
  assert(csv.includes('"survey_id","corridor_name","Depth"'));assert(csv.includes('"Mangrove Bay","-1.25"'));
  assert.equal(restoreRecord(f.record,f.file,SURVEYS).corridorName,'');
  const legacy={...f.state,version:'1.0.0'};delete legacy.corridorName;assert.equal(validateDraft(legacy,SURVEYS).corridorName,'');
  assert.throws(()=>validateDraft({...f.state,corridorName:{}},SURVEYS));
  const properties=recordProperties({...f.state,corridorName:'🌊'.repeat(100)},f.user,'root','complete');
  assert(Buffer.byteLength('corridorName'+properties.corridorName,'utf8')<=124);
});

test('more than 100 separate files in a category suggest ZIP archives; archives and earlier originals do not count',()=>{
  assert.equal(ZIP_SUGGEST_FILES,100);
  const groups=[['photos','Survey photos'],['targets','Ground target positions']];
  const many=n=>Array.from({length:n},(_,i)=>({group:'photos',path:`flight1/IMG_${i}.JPG`}));
  assert.deepEqual(zipSuggestions(many(100),groups),[]);
  assert.deepEqual(zipSuggestions(many(101),groups),[{key:'photos',label:'Survey photos',count:101}]);
  const zips=Array.from({length:150},(_,i)=>({group:'photos',path:`flight${i}.zip`}));
  assert.deepEqual(zipSuggestions(zips,groups),[]);
  assert.deepEqual(zipSuggestions(many(150).map(f=>({...f,inherited:true})),groups),[]);
});
