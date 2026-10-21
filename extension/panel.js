const $=id=>document.getElementById(id),delay=ms=>new Promise(r=>setTimeout(r,ms));
let server='',token='',running=false,preparing=false,deadline=0,tabId=null,records=[],abort=null,clock=null,scanId=0,scanReference=null,scanSeconds=60;
const status=message=>{$('status').textContent=message};
function endpoint(value){const u=new URL(value);if(u.username||u.password||u.search||u.hash||u.pathname!=='/')throw Error('Enter the API origin without a path or embedded credentials.');if(u.protocol!=='https:'&&!(u.protocol==='http:'&&['localhost','127.0.0.1'].includes(u.hostname)))throw Error('Remote APIs require HTTPS.');return u.origin}
async function api(path,options={},timeout=15000){
 const controller=new AbortController(),signal=running?abort.signal:null,stop=()=>controller.abort();
 const timer=setTimeout(stop,Math.max(1,timeout));signal?.addEventListener('abort',stop,{once:true});
 try{
  const r=await fetch(server+path,{...options,credentials:'omit',headers:{...(token?{Authorization:'Bearer '+token}:{}),...(options.body instanceof FormData?{}:{'Content-Type':'application/json'}),...options.headers},signal:controller.signal});
  const data=await r.json();if(!r.ok)throw Error(typeof data.detail==='string'?data.detail:'Request rejected ('+r.status+')');return data;
 }finally{clearTimeout(timer);signal?.removeEventListener('abort',stop)}
}
async function references(preferred=[]){
 const selected=new Set(preferred.length?preferred.map(String):[...$('reference').selectedOptions].map(o=>o.value));
 const movies=await api('/movies');$('reference').replaceChildren();
 for(const m of movies.filter(m=>m.active))for(const f of m.media.filter(f=>f.kind==='reference'&&f.status==='ready')){
  const o=document.createElement('option');o.value=f.id;o.textContent=m.title+' · #'+f.id;o.selected=selected.has(String(f.id));$('reference').append(o);
 }
 if(!$('reference').selectedOptions.length&&$('reference').options.length)$('reference').options[0].selected=true;
}
$('login').onsubmit=async e=>{e.preventDefault();try{
 server=endpoint($('server').value);token='';
 if(new URL(server).protocol==='https:'&&!await chrome.permissions.request({origins:[server+'/*']}))throw Error('API host permission is required.');
 const result=await api('/auth/login',{method:'POST',body:JSON.stringify({username:$('username').value,password:$('password').value})});
 if(!['admin','analyst'].includes(result.role))throw Error('An analyst or admin account is required.');
 token=result.access_token;$('password').value='';await chrome.storage.session.set({server,token});
 $('login').hidden=true;$('workspace').hidden=false;await references();status('Connected. Laya reviews compact evidence on your SceneGuard server.');
 }catch(e){status(e.message)}};
$('logout').onclick=async()=>{stop();token='';await chrome.storage.session.clear();$('workspace').hidden=true;$('login').hidden=false;status('Disconnected.')};
$('refresh').onclick=()=>references().catch(e=>status(e.message));
$('upload').onclick=async()=>{if(preparing||running)return;try{
 if(!$('authorized').checked)throw Error('Confirm that you are authorized to process the footage.');
 const files=[...$('file').files];if(!files.length||files.length>5)throw Error('Choose between one and five reference videos.');
 if(files.some(f=>f.size>500*1024*1024))throw Error('Maximum file size is 500 MiB per video.');
 preparing=true;$('upload').disabled=true;$('start').disabled=true;$('logout').disabled=true;
 const indexed=[];
 for(const file of files){
  status('Uploading '+file.name+'…');
  const movie=await api('/movies',{method:'POST',body:JSON.stringify({title:file.name.slice(0,200),spoiler_start:0})});
  const form=new FormData();form.append('file',file);form.append('kind','reference');form.append('movie_id',movie.id);form.append('authorized','true');form.append('platform','mock');form.append('post_url','https://example.invalid/browser-reference');
  const media=await api('/media',{method:'POST',body:form},120000);status('Indexing '+file.name+'. The scan timer has not started.');
  let ready=false;
  for(let i=0;i<450;i++){
   const rows=await api('/media?limit=500'),row=rows.find(r=>r.id===media.id);
   if(row?.status==='ready'){indexed.push(media.id);ready=true;break}
   if(row?.status==='failed')throw Error('Indexing failed for '+file.name+': '+row.error);
   await delay(2000);
  }
  if(!ready)throw Error('Indexing remains pending. Refresh references when it completes.');
 }
 await references(indexed);status(indexed.length+' references ready. Set your scan duration and open your feed.');
 }catch(e){status(e.message)}finally{preparing=false;$('upload').disabled=false;$('start').disabled=false;$('logout').disabled=false}};
async function inspect(){
 const [tab]=await chrome.tabs.query({active:true,currentWindow:true});
 if(!tab||tab.id!==tabId||new URL(tab.url).hostname!=='www.instagram.com')throw Error('Scan stopped: keep the selected Instagram tab active.');
 const [result]=await chrome.scripting.executeScript({target:{tabId},func:inspectFeed});return result.result;
}
async function capture(info){
 const response=await chrome.runtime.sendMessage({type:'capture',tabId});if(response.error)throw Error(response.error);
 const after=await inspect();if(after.status!=='playing'||after.url!==info.url||Math.abs(after.time-info.time)>.7)throw Error('Playback changed during capture; sample skipped.');
 const image=await createImageBitmap(await (await fetch(response.image)).blob());
 try{
  const {x,y,w,h}=info.rect,sx=image.width/info.viewport.w,sy=image.height/info.viewport.h;
  const ratio=Math.min(1,640/w,640/h),canvas=document.createElement('canvas');canvas.width=Math.round(w*ratio);canvas.height=Math.round(h*ratio);
  canvas.getContext('2d').drawImage(image,x*sx,y*sy,w*sx,h*sy,0,0,canvas.width,canvas.height);
  const png=canvas.toDataURL('image/png').split(',')[1];if(png.length>1400000)throw Error('Frame too large; sample skipped.');return {png,time:info.time};
 }finally{image.close()}
}
function verdict(record){
 const comparisons=record.comparisons||[];
 if(comparisons.some(r=>r.verdict==='visual_match'))return 'visual_match';
 if(comparisons.some(r=>r.verdict==='review'))return 'review';
 if(record.unprocessed_reference_ids?.length||comparisons.some(r=>r.verdict==='not_checked'))return 'partially_checked';
 if(comparisons.some(r=>r.verdict==='excluded_promotional'))return 'excluded_promotional';
 return comparisons.length?'no_match_in_sample':record.verdict;
}
function render(){
 $('results').replaceChildren();
 for(const record of [...records].reverse()){
  record.verdict=verdict(record);const card=document.createElement('article'),text=document.createElement('strong');text.textContent=record.verdict.replaceAll('_',' ');card.append(text);
  if(record.post_url){const p=document.createElement('p'),a=document.createElement('a');a.href=record.post_url;a.target='_blank';a.rel='noreferrer';a.textContent=record.post_url;p.append(a);card.append(p)}
  for(const r of record.comparisons||[]){
   const detail=document.createElement('p');detail.textContent=(r.movie_title||'Reference #'+r.reference_id)+' — '+r.verdict.replaceAll('_',' ')+(r.similarity!==undefined?` · similarity ${r.similarity.toFixed(3)} · reference ${r.reference_timestamp.toFixed(1)}s`:': '+r.reason);card.append(detail);
   if(r.laya){const model=document.createElement('p');model.className='small';model.textContent=`Laya: ${r.laya.status}${r.laya.choice?' / '+r.laya.choice:''} · ${r.laya.elapsed_seconds}s${r.laya.usage?.input_tokens!==undefined?' · '+r.laya.usage.input_tokens+' input tokens':''}`;card.append(model)}
  }
  if(record.reason){const p=document.createElement('p');p.textContent=record.reason;card.append(p)}
  if(record.unprocessed_reference_ids?.length){const p=document.createElement('p');p.textContent=record.unprocessed_reference_ids.length+' reference comparisons pending or outside the time limit.';card.append(p)}
  $('results').append(card);
 }
 $('matches').replaceChildren();
 const related=records.filter(r=>r.comparisons?.some(c=>['visual_match','review'].includes(c.verdict)));
 for(const r of related){
  const card=document.createElement('article'),link=document.createElement('a');link.href=r.post_url;link.textContent=r.post_url;link.target='_blank';link.rel='noreferrer';card.append(link);
  for(const c of r.comparisons.filter(c=>['visual_match','review'].includes(c.verdict))){const p=document.createElement('p');p.textContent=(c.movie_title||'Reference #'+c.reference_id)+' · '+c.verdict.replaceAll('_',' ')+` · ${c.reference_timestamp.toFixed(1)}s · similarity ${c.similarity.toFixed(3)}`;card.append(p)}
  $('matches').append(card);
 }
 if(!related.length){const p=document.createElement('p');p.textContent='No related reel leads in completed comparisons yet.';$('matches').append(p)}
 $('coverage').textContent=`${records.filter(r=>r.comparisons?.some(c=>c.similarity!==undefined)).length} reels checked · ${records.filter(r=>r.verdict==='visual_match').length} matched reels · ${records.filter(r=>r.verdict==='review').length} need review · ${records.filter(r=>r.verdict==='skipped').length} skipped samples`;
 $('export').disabled=!records.length;$('csv').disabled=!records.some(r=>r.comparisons?.some(c=>['visual_match','review'].includes(c.verdict)));
}
function add(record){records.push(record);render()}
function stop(){running=false;scanId++;abort?.abort();clearInterval(clock);$('start').disabled=preparing;$('stop').disabled=true;$('upload').disabled=preparing;$('reference').disabled=false;$('refresh').disabled=false;$('duration').disabled=false;$('timer').textContent='Stopped';render();}
$('stop').onclick=()=>{stop();status('Stopped. Only completed comparisons are listed.')};
$('start').onclick=async()=>{
 if(running||preparing)return;const id=++scanId;$('start').disabled=true;
 try{
  if(!$('authorized').checked)throw Error('Confirm that you are authorized to process the footage.');
  const selected=[...$('reference').selectedOptions].map(o=>Number(o.value));if(!selected.length||selected.length>5)throw Error('Select between one and five indexed references.');
  scanSeconds=Number($('duration').value);if(!Number.isInteger(scanSeconds)||scanSeconds<15||scanSeconds>600)throw Error('Choose a duration between 15 and 600 seconds.');
  for(const reference of selected){const summary=await api('/media/'+reference+'/index-summary');if(summary.frames>450)throw Error('Each reference must be an excerpt up to 15 minutes.');}
  const [tab]=await chrome.tabs.query({active:true,currentWindow:true});if(!tab||new URL(tab.url).hostname!=='www.instagram.com')throw Error('Open Instagram and click the extension toolbar icon on that tab.');
  tabId=tab.id;await inspect();if(scanId!==id)return;
  records=[];scanReference=selected;render();$('results').replaceChildren();$('coverage').textContent='';$('export').disabled=true;
  running=true;abort=new AbortController();deadline=performance.now()+scanSeconds*1000;const seen=new Set();let lastSkip='';
  $('stop').disabled=false;$('upload').disabled=true;$('reference').disabled=true;$('refresh').disabled=true;$('duration').disabled=true;
  clock=setInterval(()=>{const left=Math.max(0,Math.ceil((deadline-performance.now())/1000));$('timer').textContent=left+'s remaining';if(!left){stop();$('timer').textContent=scanSeconds+'-second scan complete';status('Complete. Reels not loaded or checked are outside this result.');$('matches').scrollIntoView({behavior:'smooth',block:'start'})}},100);
  status('Scanning visible playing reels. Keep this Instagram tab active.');
  const active=()=>running&&scanId===id&&performance.now()<deadline;
  while(active()){
   const first=await inspect();if(!active())break;
   if(first.status!=='playing'){
    if(lastSkip!==first.status){add({verdict:'skipped',reason:first.status.replaceAll('_',' ')});lastSkip=first.status}
    // Do not automatically scroll past a login, obscured video, or missing media.
    await delay(800);continue;
   }
   lastSkip='';
   if(!seen.has(first.url)&&deadline-performance.now()>4000){
    try{
     const a=await capture(first);await delay(2000);if(!active())break;
     const second=await inspect();if(second.status!=='playing'||second.url!==first.url||second.time-first.time<.5||second.time-first.time>4)throw Error('Reel changed, looped, or stopped before a second frame.');
     const b=await capture(second);if(!active())break;
     const group={post_url:first.url,verdict:'partially_checked',comparisons:[],unprocessed_reference_ids:[...selected]};seen.add(first.url);add(group);
     for(const reference of selected){
      if(!active()||deadline-performance.now()<300)break;
      try{
       const result=await api('/browser/match',{method:'POST',body:JSON.stringify({reference_id:reference,post_url:first.url,frames:[a,b]})},Math.min(6500,deadline-performance.now()));
       if(active()){group.comparisons.push(result);group.unprocessed_reference_ids=group.unprocessed_reference_ids.filter(id=>id!==reference);render()}
      }catch(e){if(active()){group.comparisons.push({reference_id:reference,verdict:'not_checked',reason:e.name==='AbortError'?'Comparison timeout':e.message});group.unprocessed_reference_ids=group.unprocessed_reference_ids.filter(id=>id!==reference);render()}}
     }
    }catch(e){if(active()){seen.add(first.url);add({post_url:first.url,verdict:'skipped',reason:e.name==='AbortError'?'Comparison exceeded remaining time.':e.message})}}
   }
   if(!active())break;
   if($('advance').checked){await inspect();if(active())await chrome.scripting.executeScript({target:{tabId},func:advanceFeed})}
   await delay(800);
  }
 }catch(e){if(scanId===id){stop();status(e.message)}}finally{if(!running)$('start').disabled=preparing}
};
$('export').onclick=()=>{
 const blob=new Blob([JSON.stringify({exported_at:new Date().toISOString(),scope:'Visible sampled frames only; no completeness guarantee',reference_ids:scanReference,duration_seconds:scanSeconds,results:records},null,2)],{type:'application/json'});
 const url=URL.createObjectURL(blob),a=document.createElement('a');a.href=url;a.download='sceneguard-feed-results.json';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);
};
$('csv').onclick=()=>{
 const rows=[['Reel URL','Reference','Reference ID','Decision','Reference seconds','Similarity','Laya status','Laya choice']];
 for(const r of records)for(const c of r.comparisons||[])if(['visual_match','review'].includes(c.verdict))rows.push([r.post_url,c.movie_title,c.reference_id,c.verdict,c.reference_timestamp,c.similarity,c.laya?.status,c.laya?.choice]);
 const quote=v=>{let s=String(v??'');if(/^[\s]*[=+@-]/.test(s))s="'"+s;return '"'+s.replaceAll('"','""')+'"'};
 const blob=new Blob([rows.map(r=>r.map(quote).join(',')).join('\r\n')],{type:'text/csv'}),url=URL.createObjectURL(blob),a=document.createElement('a');a.href=url;a.download='sceneguard-matching-reels.csv';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);
};
window.addEventListener('pagehide',stop);
(async()=>{const saved=await chrome.storage.session.get(['server','token']);if(saved.token){server=saved.server;token=saved.token;$('server').value=server;try{await references();$('login').hidden=true;$('workspace').hidden=false;status('Connected.')}catch{token='';await chrome.storage.session.clear();status('Sign in to SceneGuard again.')}}})();
