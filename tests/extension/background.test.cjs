const vm=require('node:vm'),fs=require('node:fs'),assert=require('node:assert/strict');
async function run(tabs,requested=1){let listener,queries=0,captures=0;const chrome={sidePanel:{setPanelBehavior:()=>{}},runtime:{id:'test-extension',onMessage:{addListener:f=>listener=f}},tabs:{query:async()=>[tabs[Math.min(queries++,tabs.length-1)]],captureVisibleTab:async()=>{captures++;return 'data:image/png;base64,mock'}}};
vm.runInNewContext(fs.readFileSync('extension/background.js','utf8'),{chrome,URL});const result=await new Promise(resolve=>listener({type:'capture',tabId:requested},{id:'test-extension'},resolve));return {result,captures}}
(async()=>{
 const tab={id:1,windowId:1,url:'https://www.instagram.com/reel/fixture/'};
 let r=await run([tab]);assert(r.result.image&&r.captures===1);
 r=await run([{...tab,url:'https://example.com/'}]);assert(r.result.error&&r.captures===0);
 r=await run([tab],2);assert(r.result.error&&r.captures===0);
 r=await run([tab,{...tab,id:2,url:'https://example.com/'}]);assert(r.result.error&&!r.result.image);
 console.log(JSON.stringify({passed:true,cases:4,scope:'Mock Chrome capture authorization and tab-switch race tests'}));
})().catch(e=>{console.error(e);process.exitCode=1});
