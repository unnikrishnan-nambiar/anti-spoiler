// Self-contained functions injected only after the user clicks the extension on Instagram.
function inspectFeed(){
  if(document.visibilityState!=='visible')return {status:'tab_not_visible'};
  const entries=[...document.querySelectorAll('video')].map(v=>({v,r:v.getBoundingClientRect()}))
    .filter(({r})=>r.width>120&&r.height>120&&r.top>=0&&r.left>=0&&r.bottom<=innerHeight&&r.right<=innerWidth)
    .sort((a,b)=>b.r.width*b.r.height-a.r.width*a.r.height);
  if(!entries.length)return {status:'no_fully_visible_video'};
  const {v,r}=entries[0];
  if(v.paused||v.ended||v.readyState<2||!v.videoWidth)return {status:'video_not_playing'};
  // Reject modal overlays covering the video's centre. Captions/buttons inside its container are allowed.
  const top=document.elementFromPoint(r.x+r.width/2,r.y+r.height/2);
  if(top&&top!==v&&!v.parentElement?.contains(top))return {status:'video_obscured'};
  const article=v.closest('article');
  const links=article?[...article.querySelectorAll('a[href]')].map(a=>a.href):[];
  const url=[...links,location.href].map(x=>{try{
    const u=new URL(x),m=u.pathname.match(/^\/(reel|reels|p)\/([\w-]+)\/?$/);
    return u.hostname==='www.instagram.com'&&m?'https://www.instagram.com/'+(m[1]==='reels'?'reel':m[1])+'/'+m[2]+'/':null;
  }catch{return null}}).find(Boolean);
  if(!url)return {status:'missing_post_link'};
  let x=r.x,y=r.y,w=r.width,h=r.height;const fit=getComputedStyle(v).objectFit;
  if(fit==='contain'||fit==='scale-down'){
    const ratio=Math.min(w/v.videoWidth,h/v.videoHeight),nw=v.videoWidth*ratio,nh=v.videoHeight*ratio;
    x+=(w-nw)/2;y+=(h-nh)/2;w=nw;h=nh;
  }
  return {status:'playing',url,time:v.currentTime,rect:{x,y,w,h},viewport:{w:innerWidth,h:innerHeight}};
}
function advanceFeed(){
  const video=[...document.querySelectorAll('video')].find(v=>{const r=v.getBoundingClientRect();return r.top>=0&&r.top<innerHeight&&r.width>120});
  let parent=video?.parentElement;
  while(parent&&parent!==document.body){
    if(/auto|scroll/.test(getComputedStyle(parent).overflowY)&&parent.scrollHeight>parent.clientHeight+100){parent.scrollBy({top:parent.clientHeight,behavior:'instant'});return}
    parent=parent.parentElement;
  }
  window.scrollBy({top:innerHeight*.85,behavior:'instant'});
}
