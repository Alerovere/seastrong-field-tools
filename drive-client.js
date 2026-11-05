/* Direct Google Drive integration. Tokens and resumable-session URLs stay in memory. */
import {accountIdentity,isMyRecord} from './submission-records.js';
const API='https://www.googleapis.com/drive/v3';
const UPLOAD='https://www.googleapis.com/upload/drive/v3/files';
const FOLDER='application/vnd.google-apps.folder';
const CHUNK=8*1024*1024; // Multiple of Google's required 256 KiB chunk size.
const pause=ms=>new Promise(resolve=>setTimeout(resolve,ms));
const quote=s=>String(s).replaceAll('\\','\\\\').replaceAll("'","\\'");
const scripts=new Map();
function loadScript(url){
  if(!scripts.has(url))scripts.set(url,new Promise((resolve,reject)=>{
    const script=document.createElement('script');script.src=url;script.async=true;
    script.onload=resolve;script.onerror=()=>{scripts.delete(url);script.remove();reject(new Error('Google could not load. Check your connection and try again.'))};document.head.append(script);
  }));return scripts.get(url);
}
export class DriveClient {
  constructor(config){this.config=config;this.token=null;this.expires=0;this.sessions=new Map();this.root=null;this.user=null;this.ready=false;this.preparing=null;}
  get configured(){return ['googleClientId','googleApiKey','googleProjectNumber','rootFolderId'].every(k=>!!this.config[k]);}
  get connected(){return !!this.root&&!!this.token&&Date.now()<this.expires;}
  disconnect(){this.token=null;this.expires=0;this.root=null;this.user=null;this.sessions.clear();}
  async prepare(){
    if(this.ready)return;
    if(!this.preparing)this.preparing=(async()=>{
      await Promise.all([loadScript('https://accounts.google.com/gsi/client'),loadScript('https://apis.google.com/js/api.js')]);
      await new Promise((resolve,reject)=>gapi.load('picker',{callback:resolve,onerror:()=>reject(new Error('Google folder picker could not load.')),timeout:15000,ontimeout:()=>reject(new Error('Google folder picker timed out.'))}));
      this.ready=true;
    })().catch(error=>{this.preparing=null;throw error;});
    return this.preparing;
  }
  async connect(){
    if(!this.configured)throw new Error('Google setup is not finished. Follow SUBMISSION_SETUP.md in this folder.');
    if(!/^https?:$/.test(location.protocol))throw new Error('Open this site over HTTPS or localhost to connect Google.');
    await this.prepare();
    const response=await new Promise((resolve,reject)=>{
      const client=google.accounts.oauth2.initTokenClient({client_id:this.config.googleClientId,scope:'https://www.googleapis.com/auth/drive.file',callback:r=>r.error?reject(new Error(r.error_description||r.error)):resolve(r),error_callback:()=>reject(new Error('Sign-in was cancelled or blocked. Allow the Google sign-in popup and try again.'))});
      client.requestAccessToken({prompt:'consent'});
    });
    this.token=response.access_token;this.expires=Date.now()+(Number(response.expires_in||3600)-60)*1000;
    try {
      // Reuse a previous drive.file grant before showing any folder chooser.
      // A folder ID alone does not grant access: on the first use, Google may
      // require the user to select that exact folder in its own Picker.
      const fields='id,name,mimeType,driveId,capabilities(canAddChildren),trashed';
      let root;
      try{root=await this.getFile(this.config.rootFolderId,fields);}
      catch(error){if(error.status!==404)throw error;await this.pickRoot();root=await this.getFile(this.config.rootFolderId,fields);}
      if(root.mimeType!==FOLDER||root.trashed)throw new Error('The configured destination is not an available folder.');
      if(!root.driveId)throw new Error('The destination belongs to My Drive. Choose the project folder inside the institutional Shared Drive.');
      if(!root.capabilities?.canAddChildren)throw new Error('Your account cannot upload to this folder. Ask the Shared Drive manager for Contributor access or higher.');
      this.root=root;
      try {this.user=(await this.json('/about?fields=user(displayName,emailAddress,permissionId)')).user;}catch{this.user=null;}
      return root;
    }catch(error){this.disconnect();throw error;}
  }
  pickRoot(){return new Promise((resolve,reject)=>{
    // setFileIds restricts this view to the configured folder. Do not combine
    // it with setEnableDrives or setParent: Google documents them as overrides.
    const view=new google.picker.DocsView(google.picker.ViewId.FOLDERS).setIncludeFolders(true).setSelectFolderEnabled(true).setFileIds(this.config.rootFolderId);
    const picker=new google.picker.PickerBuilder().setAppId(this.config.googleProjectNumber).setDeveloperKey(this.config.googleApiKey).setOAuthToken(this.token).setOrigin(location.origin).setTitle('Confirm SEASTRONG · Survey submissions').enableFeature(google.picker.Feature.NAV_HIDDEN).addView(view).setCallback(data=>{
      if(data.action===google.picker.Action.CANCEL){picker.dispose();reject(new Error('SEASTRONG folder confirmation cancelled. If no folder appears, ask the project manager to check your access.'));}
      if(data.action===google.picker.Action.PICKED){const selected=data.docs?.[0];picker.dispose();if(selected?.id!==this.config.rootFolderId)reject(new Error('Please connect the configured Survey submissions folder, rather than another Drive folder.'));else resolve();}
    }).build();picker.setVisible(true);
  });}
  async updateProperties(fileId,appProperties){return this.json('/files/'+encodeURIComponent(fileId)+'?supportsAllDrives=true&fields=id,appProperties',{method:'PATCH',headers:{'Content-Type':'application/json'},body:JSON.stringify({appProperties})});}
  async listRecordFiles(q){
    if(!this.connected)throw new Error('Connect Google Drive to view your records.');
    const files=[];let pageToken='';
    do{
      // Search the user's accessible files so folder-only contributors do not
      // need permission to enumerate the entire institutional shared drive.
      const params=new URLSearchParams({q,corpora:'user',supportsAllDrives:'true',includeItemsFromAllDrives:'true',orderBy:'modifiedTime desc',pageSize:'100',
        fields:'nextPageToken,files(id,name,parents,size,mimeType,modifiedTime,createdTime,appProperties,lastModifyingUser(permissionId,emailAddress,displayName,me),trashed,driveId)'});
      if(pageToken)params.set('pageToken',pageToken);
      const result=await this.json('/files?'+params);files.push(...result.files);pageToken=result.nextPageToken||'';
    }while(pageToken);
    return files;
  }
  async cachedFile(id,cache){
    if(!cache.has(id))cache.set(id,await this.getFile(id,'id,name,parents,mimeType,trashed,driveId,appProperties'));
    return cache.get(id);
  }
  async isUnder(id,ancestorId,cache=new Map()){
    const seen=new Set();let current=id;
    for(let depth=0;depth<128;depth++){
      if(current===ancestorId)return true;
      if(!current||seen.has(current))return false;seen.add(current);
      let file;try{file=await this.cachedFile(current,cache);}catch(error){if(error.status===404)return false;throw error;}
      if(file.trashed||file.driveId!==this.root.driveId)return false;
      current=file.parents?.[0];
    }
    return false;
  }
  async myRecords(){
    const user=accountIdentity(this.user);
    const base="trashed = false and mimeType = 'application/json'";
    const indexedQuery=base+` and appProperties has {key='seastrongRecord' and value='1'} and appProperties has {key='rootFolderId' and value='${quote(this.config.rootFolderId)}'} and appProperties has {key='submittedBy' and value='${quote(user.permissionId)}'}`;
    // Earlier records have no per-user index. Check the last writer, shared drive
    // and actual root ancestry before including any result from this fallback.
    const [indexed,earlier]=await Promise.all([this.listRecordFiles(indexedQuery),this.listRecordFiles(base)]);
    const found=new Map(indexed.map(f=>[f.id,f]));
    for(const file of earlier)if(file.name.endsWith('_submission.json')&&isMyRecord(file,this.user))found.set(file.id,file);
    const records=[],cache=new Map();
    for(const file of found.values()){
      if(!file.name.endsWith('_submission.json')||!isMyRecord(file,this.user)||!await this.isUnder(file.parents?.[0],this.config.rootFolderId,cache))continue;
      if(file.appProperties?.seastrongRecord!=='1'){
        const folder=await this.cachedFile(file.parents[0],cache);
        file.legacyRecordId=folder.appProperties?.submissionId||/_record_([a-f0-9-]{36})$/.exec(folder.name)?.[1]||file.id;
      }
      records.push(file);
    }
    return records;
  }
  async readRecord(fileId){
    if(!this.connected)throw new Error('Connect Google Drive to open your records.');
    const file=await this.getFile(fileId,'id,name,parents,size,mimeType,modifiedTime,createdTime,appProperties,lastModifyingUser(permissionId,emailAddress,displayName,me),trashed,driveId');
    if(file.trashed||file.mimeType!=='application/json'||!file.name.endsWith('_submission.json')||!isMyRecord(file,this.user))throw new Error('This is not an available record for your Google account.');
    const cache=new Map();
    if(!await this.isUnder(file.parents?.[0],this.config.rootFolderId,cache))throw new Error('The record is outside the SEASTRONG submission folder.');
    if(!Number.isFinite(Number(file.size))||Number(file.size)>20*1024*1024)throw new Error('The saved record is too large to open in this form.');
    const response=await this.request(API+'/files/'+encodeURIComponent(fileId)+'?alt=media&supportsAllDrives=true');
    if(!response.ok)throw await this.error(response);
    const record=await response.json();
    const pack=await this.cachedFile(file.parents[0],cache);
    if(record.packageFolderId!==pack.id||!pack.parents?.includes(record.folderId))throw new Error('The saved record does not match its Drive folder.');
    if(record.submittedBy?.permissionId&&record.submittedBy.permissionId!==this.user.permissionId)throw new Error('The saved author belongs to another Google account.');
    return {file,record};
  }
  async verifyInherited(entry,surveyFolderId,cache=new Map()){
    if(!entry.sourcePackageId||!entry.driveFileId||!await this.isUnder(entry.sourcePackageId,surveyFolderId,cache))throw new Error('An earlier original is outside this survey: '+entry.path);
    const file=await this.getFile(entry.driveFileId,'id,name,size,parents,trashed,driveId');cache.set(file.id,file);
    if(file.trashed||Number(file.size)!==entry.size||!file.parents?.includes(entry.parentId)||!await this.isUnder(file.id,entry.sourcePackageId,cache))throw new Error('An earlier original is missing or changed: '+entry.path);
    return file;
  }
  auth(){if(!this.token||Date.now()>=this.expires)throw new Error('Your Google session expired. Connect Google again, then resume the upload.');return {Authorization:'Bearer '+this.token};}
  async request(url,init={},attempt=0){
    let response;
    try {response=await fetch(url,{...init,headers:{...this.auth(),...init.headers}});}
    catch(error){if(init.signal?.aborted)throw new Error('Upload paused. Connect again if needed, then resume.');if(attempt<3){await pause(500*2**attempt);return this.request(url,init,attempt+1)}throw new Error('The connection was interrupted. Keep this page open and resume when you are online.');}
    if(response.status===401){this.expires=0;throw new Error('Your Google session expired. Connect Google again, then resume.');}
    if((response.status===429||response.status>=500)&&attempt<3){await pause(500*2**attempt);return this.request(url,init,attempt+1)}
    return response;
  }
  async error(response){let message='Google Drive request failed ('+response.status+').';try{const data=await response.json();message=data.error?.message||message;}catch{}const error=new Error(message);error.status=response.status;return error;}
  async json(path,init={}){const r=await this.request(API+path,init);if(!r.ok)throw await this.error(r);return r.status===204?null:r.json();}
  async getFile(id,fields='id,name,size,parents,trashed'){return this.json('/files/'+encodeURIComponent(id)+'?supportsAllDrives=true&fields='+encodeURIComponent(fields));}
  async reserveId(){return (await this.json('/files/generateIds?count=1&space=drive&type=files')).ids[0];}
  async createMetadata(meta){
    const id=meta.id||await this.reserveId();
    const r=await this.request(API+'/files?supportsAllDrives=true&fields=id,name,size',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({...meta,id})});
    if(r.status===409)return this.getFile(id);
    if(!r.ok)throw await this.error(r);return r.json();
  }
  async folders(parent,name){
    const found=[];let pageToken='';
    do {const params=new URLSearchParams({q:`'${quote(parent)}' in parents and name = '${quote(name)}' and mimeType = '${FOLDER}' and trashed = false`,supportsAllDrives:'true',includeItemsFromAllDrives:'true',fields:'nextPageToken,files(id,name,appProperties)',pageSize:'100'});if(pageToken)params.set('pageToken',pageToken);const data=await this.json('/files?'+params);found.push(...data.files);pageToken=data.nextPageToken||'';}while(pageToken);
    return found;
  }
  async folder(parent,name,properties={}){
    const found=await this.folders(parent,name);
    if(found.length>1)throw new Error('More than one folder is named '+name+'. Ask the data manager to resolve the duplicate before uploading.');
    return found[0]||this.createMetadata({name,mimeType:FOLDER,parents:[parent],appProperties:properties});
  }
  async startSession(fileId,blob,signal){
    const r=await this.request(UPLOAD+'/'+encodeURIComponent(fileId)+'?uploadType=resumable&supportsAllDrives=true&fields=id,size,name',{method:'PATCH',headers:{'Content-Type':'application/json','X-Upload-Content-Type':blob.type||'application/octet-stream'},body:'{}',signal});
    if(!r.ok)throw await this.error(r);const url=r.headers.get('Location');
    if(!url)throw new Error('Google did not provide an upload session. Try again.');
    this.sessions.set(fileId,url);return url;
  }
  async upload(blob,{fileId,name,parent,signal,onProgress=()=>{},onReserved=()=>{}}){
    if(!fileId){fileId=(await this.createMetadata({name,mimeType:blob.type||'application/octet-stream',parents:[parent]})).id;await onReserved(fileId);}
    if(!blob.size){const f=await this.getFile(fileId);if(Number(f.size)!==0)throw new Error('Empty-file verification failed for '+name);onProgress(0,0);return f;}
    let session=this.sessions.get(fileId),offset=0,restarts=0;
    const probe=async()=>{
      const r=await this.request(session,{method:'PUT',headers:{'Content-Range':'bytes */'+blob.size},signal});
      if(r.status===200||r.status===201)return {done:await r.json()};
      if(r.status===308){const range=/bytes=0-(\d+)/.exec(r.headers.get('Range')||'');return {offset:range?Number(range[1])+1:0};}
      if(r.status===404||r.status===410)return {expired:true};
      throw await this.error(r);
    };
    if(session){const resume=await probe();if(resume.done)return this.verify(resume.done,blob,parent);if(resume.expired)session=null;else offset=resume.offset;}
    if(!session)session=await this.startSession(fileId,blob,signal);
    while(offset<blob.size){
      if(signal?.aborted)throw new Error('Upload paused. Keep the page open to resume.');
      const end=Math.min(offset+CHUNK,blob.size);
      try {
        const r=await this.request(session,{method:'PUT',headers:{'Content-Type':blob.type||'application/octet-stream','Content-Range':`bytes ${offset}-${end-1}/${blob.size}`},body:blob.slice(offset,end),signal});
        if(r.status===200||r.status===201){const verified=await this.verify(await r.json(),blob,parent);this.sessions.delete(fileId);onProgress(blob.size,blob.size);return verified;}
        if(r.status===308){const range=/bytes=0-(\d+)/.exec(r.headers.get('Range')||'');const received=range?Number(range[1])+1:0;if(received<=offset)throw new Error('Google did not confirm the upload chunk.');offset=received;onProgress(offset,blob.size);continue;}
        if(r.status===404||r.status===410){if(++restarts>2)throw new Error('The upload session expired repeatedly. Reconnect and try again.');session=await this.startSession(fileId,blob,signal);offset=0;continue;}
        throw await this.error(r);
      }catch(error){
        if(signal?.aborted||Date.now()>=this.expires)throw error;
        // Determine the committed byte range before retrying an uncertain chunk.
        try{const probeResult=await probe();if(probeResult.done)return this.verify(probeResult.done,blob,parent);if(probeResult.expired)throw error;if(probeResult.offset>offset){offset=probeResult.offset;onProgress(offset,blob.size);continue;}}catch{throw error;}
        throw error;
      }
    }
    const final=await probe();if(final.done)return this.verify(final.done,blob,parent);throw new Error('Google has not confirmed the completed upload. Resume to check it.');
  }
  async verify(result,blob,parent){
    const remote=await this.getFile(result.id);
    if(remote.trashed||Number(remote.size)!==blob.size||(parent&&!remote.parents?.includes(parent)))throw new Error('The uploaded file could not be verified. Resume before marking this submission complete.');
    return remote;
  }
}
