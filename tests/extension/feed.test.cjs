const {chromium}=require('../../frontend/node_modules/playwright');const fs=require('fs'),assert=require('node:assert/strict');
(async()=>{const b=await chromium.launch({executablePath:'/usr/bin/chromium',args:['--no-sandbox']});try{
 const p=await b.newPage({viewport:{width:800,height:800}});
 await p.route('http://localhost:31998/**',route=>route.fulfill({contentType:'text/html',body:'<article><a href="https://www.instagram.com/reel/controlled_fixture/">Reel</a><video style="display:block;width:400px;height:400px;object-fit:contain"></video></article>'}));
 await p.goto('http://localhost:31998/');await p.addScriptTag({content:fs.readFileSync('extension/feed.js','utf8')});
 assert.equal(await p.evaluate(()=>inspectFeed().status),'video_not_playing');
 await p.evaluate(()=>{const v=document.querySelector('video');for(const [k,val] of Object.entries({paused:false,ended:false,readyState:4,videoWidth:640,videoHeight:360,currentTime:8}))Object.defineProperty(v,k,{get:()=>val,configurable:true})});
 const frame=await p.evaluate(()=>inspectFeed());assert.equal(frame.status,'playing');assert.equal(frame.rect.h,225);assert.equal(frame.url,'https://www.instagram.com/reel/controlled_fixture/');
 await p.evaluate(()=>document.querySelector('a').remove());assert.equal(await p.evaluate(()=>inspectFeed().status),'missing_post_link');
 await p.evaluate(()=>{document.querySelector('video').style.marginTop='700px'});assert.equal(await p.evaluate(()=>inspectFeed().status),'no_fully_visible_video');
 console.log(JSON.stringify({passed:true,cases:4,scope:'DOM fixtures, no Instagram access'}));
 }finally{await b.close()}})().catch(e=>{console.error(e);process.exitCode=1});
