'use strict';
const $=id=>document.getElementById(id);
let config,schema,state,values,dirty=false,section,busy=false;
const status=(message,error=false)=>{$('status').textContent=message;$('status').classList.toggle('error',error);};
const token=()=>{try{return JSON.parse(sessionStorage.getItem('wolves-session')||'null');}catch{return null;}};
const b64=bytes=>btoa(String.fromCharCode(...bytes)).replace(/\+/g,'-').replace(/\//g,'_').replace(/=+$/,'');
function markDirty(){dirty=true;$('saved-state').textContent='Unsaved changes';}
async function run(action){if(busy)return;busy=true;document.querySelectorAll('#workspace button,#workspace input,#workspace textarea,#workspace select,#confirm-publish,#signin').forEach(b=>b.disabled=true);try{await action();}catch(e){status(e.message||'Something went wrong. Please try again.',true);}finally{busy=false;document.querySelectorAll('#workspace button,#workspace input,#workspace textarea,#workspace select,#confirm-publish,#signin').forEach(b=>b.disabled=false);}}
async function api(path,body){
  const session=token();if(!session||session.expires<Date.now()){throw Error('Your session has ended. Save a copy of any unsaved words, then sign in again.');}
  const r=await fetch(config.api+path,{method:body?'POST':'GET',headers:{Authorization:'Bearer '+session.access,'Content-Type':'application/json'},body:body?JSON.stringify(body):undefined,cache:'no-store'});
  const data=await r.json();if(!r.ok)throw Error(data.error||(r.status===401?'Please sign in again.':'The request could not be completed.'));return data;
}
async function signin(){
  const verifier=b64(crypto.getRandomValues(new Uint8Array(32))),stateCode=b64(crypto.getRandomValues(new Uint8Array(24)));
  sessionStorage.setItem('wolves-oauth',JSON.stringify({verifier,state:stateCode}));
  const challenge=b64(new Uint8Array(await crypto.subtle.digest('SHA-256',new TextEncoder().encode(verifier))));
  const query=new URLSearchParams({client_id:config.clientId,response_type:'code',scope:'openid email aws.cognito.signin.user.admin',redirect_uri:config.redirectUri,state:stateCode,code_challenge:challenge,code_challenge_method:'S256'});
  location.assign(config.authDomain+'/oauth2/authorize?'+query);
}
async function callback(){
  const query=new URLSearchParams(location.search);if(query.has('error'))throw Error('Sign-in was not completed. Please try again.');
  if(!query.has('code'))return;
  const pending=JSON.parse(sessionStorage.getItem('wolves-oauth')||'null');
  if(!pending||query.get('state')!==pending.state)throw Error('This sign-in link expired. Please sign in again.');
  history.replaceState(null,'',location.pathname);
  const r=await fetch(config.authDomain+'/oauth2/token',{method:'POST',headers:{'Content-Type':'application/x-www-form-urlencoded'},body:new URLSearchParams({grant_type:'authorization_code',client_id:config.clientId,code:query.get('code'),redirect_uri:config.redirectUri,code_verifier:pending.verifier})});
  const t=await r.json();sessionStorage.removeItem('wolves-oauth');if(!r.ok||!t.access_token)throw Error('Sign-in could not be completed. Please try again.');
  sessionStorage.setItem('wolves-session',JSON.stringify({access:t.access_token,expires:Date.now()+t.expires_in*1000}));
}
function fieldElement(f){
  const box=document.createElement('div'),label=document.createElement('label');label.htmlFor=f.id;label.textContent=f.label;box.append(label);
  if(f.kind==='image'){
    const img=document.createElement('img');img.className='photo-preview';img.alt=f.label;img.src=new URL(values[f.id],location.origin+'/').href;box.append(img);
    const row=document.createElement('div');row.className='photo-tools';
    const select=document.createElement('select');select.id=f.id;select.setAttribute('aria-label',f.label+' — choose an existing photo');
    const choices=[...schema.assets];if(!choices.some(a=>a.src===values[f.id]))choices.unshift({src:values[f.id],label:'Uploaded photo'});
    for(const a of choices){const option=document.createElement('option');option.value=a.src;option.textContent=a.label;select.append(option);}select.value=values[f.id];
    select.addEventListener('change',()=>{values[f.id]=select.value;img.src=new URL(select.value,location.origin+'/').href;markDirty();});row.append(select);
    const file=document.createElement('input');file.type='file';file.accept='image/jpeg,image/png,image/webp';file.setAttribute('aria-label','Upload '+f.label.toLowerCase());
    file.addEventListener('change',()=>run(async()=>{
      if(!file.files[0])return;const upload=file.files[0];if(upload.size>3*1024*1024)throw Error('Please choose a JPG, PNG or WebP image smaller than 3 MB.');
      status('Uploading photo…');const encoded=await new Promise((resolve,reject)=>{const reader=new FileReader();reader.onload=()=>resolve(String(reader.result).split(',')[1]);reader.onerror=()=>reject(Error('Could not read that photo.'));reader.readAsDataURL(upload);});
      const result=await api('/images',{base64:encoded});values[f.id]=result.src;markDirty();renderFields();status('Photo added to your draft. Preview it before publishing.');
    }));row.append(file);box.append(row);
    const help=document.createElement('p');help.className='field-help';help.textContent='Choose a club image or upload JPG, PNG or WebP (up to 3 MB).';box.append(help);
  }else{
    const input=document.createElement(f.max<=200?'input':'textarea');input.id=f.id;input.value=values[f.id];input.maxLength=f.max;input.required=true;
    if(input.tagName==='TEXTAREA')input.rows=Math.min(9,Math.max(3,Math.ceil(input.value.length/75)));
    input.addEventListener('input',()=>{values[f.id]=input.value;markDirty();});box.append(input);
  }return box;
}
function renderFields(){
  $('section-title').textContent=section;$('fields').replaceChildren(...schema.fields.filter(f=>f.group===section).map(fieldElement));
  for(const button of $('sections').children)button.setAttribute('aria-current',String(button.textContent===section));
}
function render(){
  $('login').hidden=true;$('workspace').hidden=false;$('logout').hidden=false;
  const groups=[...new Set(schema.fields.map(f=>f.group))];section=section||groups[0];$('sections').replaceChildren();
  for(const group of groups){const button=document.createElement('button');button.textContent=group;button.onclick=()=>{section=group;renderFields();};$('sections').append(button);}renderFields();
  $('saved-state').textContent=JSON.stringify(values)===JSON.stringify(state.published.values)?'Matches published site':'Saved draft';
}
function validate(){for(const f of schema.fields){if(typeof values[f.id]!=='string'||!values[f.id].trim()||values[f.id].length>f.max){section=f.group;renderFields();$(f.id)?.focus();throw Error('Check “'+f.label+'” before saving.');}}}
async function save(){validate();const r=await api('/draft',{content:{values},etag:state.etag});state.draft=r.draft;state.etag=r.etag;dirty=false;$('saved-state').textContent='Draft saved';status('Draft saved. The public website has not changed.');}
function sendPreview(){const frame=$('preview-frame');frame.contentWindow?.postMessage({type:'wolves-preview',content:{values}},location.origin);}
$('signin').onclick=()=>run(signin);
$('logout').onclick=()=>{if(dirty&&!confirm('Leave without saving your latest edits?'))return;sessionStorage.removeItem('wolves-session');dirty=false;location.assign(config.authDomain+'/logout?'+new URLSearchParams({client_id:config.clientId,logout_uri:config.redirectUri}));};
$('save').onclick=()=>run(save);
$('preview').onclick=()=>run(async()=>{validate();$('preview-dialog').showModal();$('preview-frame').src='/?editor-preview=1';});
window.addEventListener('message',e=>{if(e.origin===location.origin&&e.source===$('preview-frame').contentWindow&&e.data?.type==='wolves-preview-ready')sendPreview();});
$('phone').onclick=()=>{$('preview-frame').style.width='390px';};$('desktop').onclick=()=>{$('preview-frame').style.width='1200px';};
$('publish').onclick=()=>run(async()=>{if(dirty)await save();$('publish-dialog').showModal();});
$('confirm-publish').onclick=()=>run(async()=>{const r=await api('/publish',{etag:state.etag,publishedEtag:state.publishedEtag});state.published=r.published;state.publishedEtag=r.publishedEtag;$('publish-dialog').close();$('saved-state').textContent='Published';status('Published. Your updated words and photos are now on the website.');});
$('history').onclick=()=>run(async()=>{
  const data=await api('/history');$('versions').replaceChildren();
  for(const version of data.versions){const row=document.createElement('div');row.className='version-row';const label=document.createElement('span');label.textContent=version.baseline?'Approved design — original content':new Date(version.savedAt).toLocaleString('en-IE');const button=document.createElement('button');button.textContent='Load as draft';button.onclick=()=>run(async()=>{if(dirty&&!confirm('Replace your unsaved edits with this earlier version?'))return;const r=await api('/history/'+encodeURIComponent(version.id));values=structuredClone(r.content.values);markDirty();renderFields();$('history-dialog').close();status('Earlier content loaded into your draft. Preview and publish when ready.');});row.append(label,button);$('versions').append(row);}
  if(!data.versions.length)$('versions').textContent='Your first published update will appear here.';$('history-dialog').showModal();
});
document.querySelectorAll('[data-close]').forEach(b=>b.onclick=()=>$(b.dataset.close).close());
$('fields').onsubmit=e=>e.preventDefault();window.addEventListener('beforeunload',e=>{if(dirty){e.preventDefault();e.returnValue='';}});
(async()=>{try{const results=await Promise.all([fetch('./config.json',{cache:'no-store'}),fetch('/editor-schema.json')]);if(results.some(r=>!r.ok))throw Error('The editor is being configured. Please return shortly.');[config,schema]=await Promise.all(results.map(r=>r.json()));await callback();if(token()?.expires>Date.now()){state=await api('/editor');values=structuredClone(state.draft.values);render();}}catch(e){status(e.message,true);}})();
