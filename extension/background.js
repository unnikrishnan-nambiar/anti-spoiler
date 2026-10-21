chrome.sidePanel.setPanelBehavior({openPanelOnActionClick:true});
chrome.runtime.onMessage.addListener((message,sender,respond)=>{
  if(sender.id!==chrome.runtime.id||message.type!=='capture')return;
  (async()=>{
    const [tab]=await chrome.tabs.query({active:true,currentWindow:true});
    if(!tab||tab.id!==message.tabId||new URL(tab.url).hostname!=='www.instagram.com')throw Error('Keep the selected Instagram tab active.');
    const image=await chrome.tabs.captureVisibleTab(tab.windowId,{format:'png'});
    const [after]=await chrome.tabs.query({active:true,currentWindow:true});
    if(after?.id!==tab.id||after.url!==tab.url)throw Error('Tab changed; capture discarded.');
    return {image};
  })().then(respond).catch(e=>respond({error:e.message}));return true;
});
