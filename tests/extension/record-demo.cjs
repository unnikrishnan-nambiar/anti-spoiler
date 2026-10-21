// A clearly labeled controlled demonstration: real backend/Laya, simulated Chrome bridge/feed.
const {chromium,request}=require('../../frontend/node_modules/playwright');
const fs=require('fs'),http=require('http'),path=require('path'),assert=require('node:assert/strict');
(async()=>{
 const env=Object.fromEntries(fs.readFileSync('.env','utf8').split('\n').filter(l=>l.includes('=')&&!l.startsWith('#')).map(l=>[l.slice(0,l.indexOf('=')),l.slice(l.indexOf('=')+1)]));
 const client=await request.newContext({baseURL:'http://127.0.0.1:8000'});
 const auth=await client.post('/auth/login',{data:{username:env.ADMIN_USERNAME||'admin',password:env.ADMIN_PASSWORD}});assert(auth.ok(),'Backend login failed');const token=(await auth.json()).access_token;
 const frames=[30,60].map(offset=>[0,1].map(i=>'data:image/png;base64,'+fs.readFileSync(`.local/extension-demo-frames/${offset}-${i}.png`).toString('base64')));
 const server=http.createServer((req,res)=>{const name=req.url.slice(1)||'panel.html';if(!['panel.html','panel.css','panel.js','feed.js'].includes(name)){res.writeHead(404);res.end();return}res.setHeader('Content-Type',name.endsWith('.js')?'application/javascript':name.endsWith('.css')?'text/css':'text/html');res.end(fs.readFileSync(path.join('extension',name)))});await new Promise(r=>server.listen(0,'127.0.0.1',r));
 const b=await chromium.launch({executablePath:'/usr/bin/chromium',headless:true,args:['--no-sandbox']});
 const context=await b.newContext({viewport:{width:1400,height:1000},recordVideo:{dir:'.local/extension-demo-video',size:{width:1400,height:1000}}});
 let page,video;
 try{
  page=await context.newPage();video=page.video();
  await page.addInitScript(({token,frames})=>{
   const state={advance:0,capture:0,started:performance.now()};
   window.chrome={storage:{session:{get:async()=>({server:'http://127.0.0.1:8000',token}),set:async()=>{},clear:async()=>{}}},permissions:{request:async()=>true},tabs:{query:async()=>[{id:1,url:'https://www.instagram.com/reel/CONTROLLED_DEMO/'}]},scripting:{executeScript:async({func})=>{
    if(func.name==='advanceFeed'){state.advance++;state.capture=0;state.started=performance.now();return [{result:null}]}
    return [{result:{status:'playing',url:'https://www.instagram.com/reel/DEMO_'+(state.advance%2===0?'A':'B')+'/',time:1+(performance.now()-state.started)/1000,rect:{x:0,y:0,w:426,h:238},viewport:{w:426,h:238}}}];
   }},runtime:{sendMessage:async()=>{const image=frames[state.advance%2][state.capture%2];state.capture++;const img=document.querySelector('#demo-image');if(img)img.src=image;return {image}}}};
  },{token,frames});
  await page.route('http://127.0.0.1:8000/**',async route=>{
   if(route.request().method()==='OPTIONS'){await route.fulfill({status:204,headers:{'Access-Control-Allow-Origin':'*','Access-Control-Allow-Headers':'authorization,content-type','Access-Control-Allow-Methods':'GET,POST'}});return}
   const response=await route.fetch();if(response.status()>=400&&new URL(route.request().url()).pathname==='/media')console.log('Upload diagnostic:',await response.text());await route.fulfill({response,headers:{...response.headers(),'Access-Control-Allow-Origin':'*'}});
  });
  await page.goto('http://127.0.0.1:'+server.address().port+'/panel.html');await page.locator('#workspace').waitFor({state:'visible'});
  await page.evaluate(first=>{
   document.body.style.maxWidth='620px';document.body.style.paddingTop='70px';
   const banner=document.createElement('div');banner.textContent='CONTROLLED DEMO — SIMULATED FEED / REAL MATCHER + LAYA';banner.style='position:fixed;top:0;left:0;right:0;background:#111;color:white;padding:20px;font:700 18px system-ui;z-index:1000';document.body.prepend(banner);
   const feed=document.createElement('aside');feed.style='position:fixed;left:720px;top:120px;width:580px;padding:20px;border:1px solid #aaa;font:16px system-ui';const h=document.createElement('h2');h.textContent='Controlled reference-derived reel sample';const img=document.createElement('img');img.id='demo-image';img.src=first;img.style='width:100%';const p=document.createElement('p');p.textContent='These clips were derived from the uploaded authorized video. This recording does not show a live Instagram discovery.';feed.append(h,img,p);document.body.append(feed);
  },frames[0][0]);
  await page.waitForTimeout(1500);await page.locator('#authorized').check();
  await page.locator('#file').setInputFiles([30,60].map(offset=>({name:'controlled-reference-'+offset+'.mp4',mimeType:'video/mp4',buffer:fs.readFileSync('.local/real-reference-evaluation/controlled-offset-'+offset+'.mp4')}))); 
  await page.locator('#upload').click();await page.waitForFunction(()=>document.querySelector('#status').textContent.includes('2 references ready')||(!document.querySelector('#upload').disabled&&!document.querySelector('#status').textContent.includes('Uploading')),null,{timeout:120000});assert((await page.locator('#status').innerText()).includes('2 references ready'),await page.locator('#status').innerText());
  await page.locator('#duration').fill('25');await page.locator('#start').scrollIntoViewIfNeeded();await page.waitForTimeout(1500);await page.locator('#start').click();
  await page.waitForFunction(()=>document.querySelector('#timer').textContent==='25-second scan complete',null,{timeout:35000});
  await page.locator('#matches').scrollIntoViewIfNeeded();await page.waitForTimeout(1500);
  const jsonDownload=page.waitForEvent('download');await page.locator('#export').click();await (await jsonDownload).saveAs('.local/extension-demo-results.json');
  const data=JSON.parse(fs.readFileSync('.local/extension-demo-results.json','utf8'));assert(data.reference_ids.length===2);assert(data.results.some(r=>r.comparisons?.some(c=>c.laya?.status==='used')),'No live Laya decision recorded');
  if(!await page.locator('#csv').isDisabled()){const csvDownload=page.waitForEvent('download');await page.locator('#csv').click();await (await csvDownload).saveAs('.local/extension-demo-reels.csv')}
  await page.waitForTimeout(2500);console.log(JSON.stringify({scope:'Controlled demo: simulated feed/Chrome bridge, actual uploads, API, matching and Laya',reference_ids:data.reference_ids,reels:data.results.length,matched_reels:data.results.filter(r=>r.verdict==='visual_match').length,review_reels:data.results.filter(r=>r.verdict==='review').length}));
 }finally{await context.close();if(video)await video.saveAs('.local/sceneguard-demo-latest.webm');await b.close();server.close();await client.dispose()}
})().catch(e=>{console.error(e.message);process.exitCode=1});
