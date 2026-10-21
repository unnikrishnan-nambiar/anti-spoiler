// Chromium UI tests use an explicitly mocked Chrome bridge and API, not Instagram.
const {chromium}=require('../../frontend/node_modules/playwright');
const fs=require('fs'),path=require('path'),http=require('http'),assert=require('node:assert/strict');
(async()=>{
 const server=http.createServer((req,res)=>{const name=req.url.slice(1)||'panel.html';if(!['panel.html','panel.css','panel.js','feed.js'].includes(name)){res.writeHead(404);res.end();return}res.setHeader('Content-Type',name.endsWith('.js')?'application/javascript':name.endsWith('.css')?'text/css':'text/html');res.end(fs.readFileSync(path.join('extension',name)))});await new Promise(r=>server.listen(0,'127.0.0.1',r));
 const browser=await chromium.launch({executablePath:'/usr/bin/chromium',headless:true,args:['--no-sandbox']});
 try{
  const context=await browser.newContext({viewport:{width:480,height:1100}});
  const page=await context.newPage();
  await page.addInitScript(()=>{
   window.mockState={active:true,captures:0,advances:0,checks:0};
   const canvas=document.createElement('canvas');canvas.width=640;canvas.height=360;canvas.getContext('2d').fillRect(0,0,640,360);const screenshot=canvas.toDataURL();
   window.chrome={storage:{session:{get:async()=>({}),set:async()=>{},clear:async()=>{}}},permissions:{request:async()=>true},
    tabs:{query:async()=>[{id:1,url:window.mockState.active?'https://www.instagram.com/reel/fixture/':'https://example.com/'}]},
    scripting:{executeScript:async({func})=>{
     if(func.name==='advanceFeed'){window.mockState.advances++;return [{result:null}]}
     return [{result:{status:'playing',url:'https://www.instagram.com/reel/fixture'+window.mockState.advances+'/',time:performance.now()/1000,rect:{x:0,y:0,w:640,h:360},viewport:{w:640,h:360}}}];
    }},runtime:{sendMessage:async()=>{window.mockState.captures++;return {image:screenshot}}}};
  });
  await page.route('http://localhost:8000/**',async route=>{
   const u=new URL(route.request().url());let data={};
   if(u.pathname==='/auth/login')data={access_token:'test-token',role:'analyst'};
   else if(u.pathname==='/movies')data=[{id:1,title:'Synthetic reference',active:true,media:[{id:1,kind:'reference',status:'ready'},{id:2,kind:'reference',status:'ready'}]}];
   else if(u.pathname.endsWith('/index-summary'))data={frames:121};
   else if(u.pathname==='/browser/match'){
    const body=route.request().postDataJSON();assert(body.frames[1].time-body.frames[0].time>=.5);
    assert(body.frames.every(f=>f.png.length>100));
    data={post_url:body.post_url,reference_id:body.reference_id,movie_title:body.reference_id===1?'=FORMULA()':'Negative fixture',verdict:body.reference_id===1?'visual_match':'no_match_in_sample',similarity:.9,reference_timestamp:30,evidence:{matched_frames:2},laya:{status:'used',choice:'confirmed',elapsed_seconds:.1,usage:{input_tokens:150}}};
   }
   await route.fulfill({status:200,contentType:'application/json',body:JSON.stringify(data)});
  });
  await page.goto('http://127.0.0.1:'+server.address().port+'/panel.html');
  await page.locator('#password').fill('fixture-password');await page.getByRole('button',{name:'Connect',exact:true}).click();
  await page.locator('#workspace').waitFor({state:'visible'});await page.locator('#authorized').check();await page.locator('#reference').selectOption(['1','2']);
  await page.locator('#start').click();await page.waitForFunction(()=>document.querySelector('#results').textContent.includes('Laya: used'));
  assert((await page.locator('#results').innerText()).includes('Laya: used'));
  await page.locator('#stop').click();const stopped=await page.evaluate(()=>({...window.mockState}));await page.waitForTimeout(2500);
  assert.equal((await page.evaluate(()=>window.mockState.captures)),stopped.captures,'Captures continued after Stop');
  await page.locator('#start').click();await page.waitForTimeout(500);await page.evaluate(()=>{window.mockState.active=false});await page.waitForTimeout(2300);
  assert((await page.locator('#status').innerText()).includes('selected Instagram tab'));
  await page.evaluate(()=>{window.mockState.active=true});await page.locator('#start').click();
  const started=Date.now();await page.waitForFunction(()=>document.querySelector('#timer').textContent==='60-second scan complete',null,{timeout:65000});
  const duration=Date.now()-started;assert(duration>=59000&&duration<=62000);
  const ended=await page.evaluate(()=>({...window.mockState}));await page.waitForTimeout(1000);
  assert.equal((await page.evaluate(()=>window.mockState.captures)),ended.captures);
  assert.equal(await page.locator('#stop').isDisabled(),true);
  const downloadPromise=page.waitForEvent('download');await page.locator('#csv').click();const download=await downloadPromise;await download.saveAs('.local/extension-tested-results.csv');
  const csv=fs.readFileSync('.local/extension-tested-results.csv','utf8');assert(csv.includes("'=FORMULA()"));assert(!csv.includes('Negative fixture'));
  await page.locator('#duration').fill('14');await page.locator('#start').click();assert((await page.locator('#status').innerText()).includes('15 and 600'));
  await page.screenshot({path:'.local/extension-ui-tested.png',fullPage:true});
  console.log(JSON.stringify({scope:'UI with mocked Chrome bridge and API',passed:true,duration_ms:duration,captures:ended.captures,checks:await page.locator('#results article').count()}));
 }finally{await browser.close();server.close()}
})().catch(e=>{console.error(e);process.exitCode=1});
