(function initWeeklyBriefingState(){
  const W = window.MatchIQWeekly = window.MatchIQWeekly || {};
  W.authToken = () => localStorage.getItem("matchiq_auth_token") || sessionStorage.getItem("matchiq_auth_token") || "";
  W.authHeaders = () => ({"Accept":"application/json","Content-Type":"application/json",...(W.authToken()?{"Authorization":`Bearer ${W.authToken()}`}:{})});
  W.readJson = (key, fallback) => { try{ const raw=localStorage.getItem(key)||sessionStorage.getItem(key); return raw?JSON.parse(raw):fallback; }catch{return fallback;} };
  W.weekStart = () => { const d=new Date(); const day=(d.getDay()+6)%7; d.setHours(0,0,0,0); d.setDate(d.getDate()-day); return d; };
  W.buildLocalSources = function(){
    const current=W.readJson("matchiq_coach_v13",null);
    const history=W.readJson("matchiq_coach_history_v14",[]);
    const start=W.weekStart().getTime();
    const recent=(Array.isArray(history)?history:[]).filter(item=>{
      const when=new Date(item.savedAt||item.match?.date||0).getTime(); return Number.isFinite(when)&&when>=start;
    });
    const currentDate=new Date(current?.match?.date||0).getTime();
    const currentIsRecent=Boolean(current?.match)&&(current?.live?.running||currentDate>=start);
    const candidates=[...(currentIsRecent?[{...current,savedAt:current.match?.date||new Date().toISOString()}]:[]),...recent]
      .sort((a,b)=>new Date(b.savedAt||b.match?.date||0)-new Date(a.savedAt||a.match?.date||0));
    const latestRaw=candidates[0]||null;
    const latest=latestRaw?{
      ...latestRaw,
      homeGoals:latestRaw.homeGoals??(latestRaw.events||[]).filter(event=>event.type==="gol"&&event.side==="home").length,
      awayGoals:latestRaw.awayGoals??(latestRaw.events||[]).filter(event=>event.type==="gol"&&event.side==="away").length
    }:null;
    const tagCounts=new Map();
    (latest?.events||[]).forEach(event=>(event.tags||[]).forEach(tag=>tagCounts.set(String(tag),(tagCounts.get(String(tag))||0)+1)));
    const memoryTags=latest?.metadata?.memory?.tags||latest?.memory?.tags||latest?.memory?.voiceCoach?.themes||{};
    if(Array.isArray(memoryTags)) memoryTags.forEach(item=>{
      const label=String(item.label||item.tag||item||"").trim(); const count=Number(item.count||1); if(label) tagCounts.set(label,Math.max(tagCounts.get(label)||0,count));
    });
    else if(memoryTags&&typeof memoryTags==="object") Object.values(memoryTags).forEach(item=>{
      const label=String(item?.label||"").trim(); const count=Number(item?.count||0); if(label&&count) tagCounts.set(label,Math.max(tagCounts.get(label)||0,count));
    });
    return {
      latest_match:latest,
      history_count:recent.length,
      patterns:[...tagCounts.entries()].filter(([,count])=>count>=2).map(([label,count])=>({label,count,source:"Coach"})).slice(0,8),
      clips_count:0,
      captured_at:new Date().toISOString()
    };
  };
})();
