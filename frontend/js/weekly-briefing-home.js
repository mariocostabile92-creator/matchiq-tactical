(async function showWeeklyBriefingOnHome(){
  const W=window.MatchIQWeekly;if(!W?.authToken?.())return;
  try{
    const data=await W.generate();const briefing=data.briefing;if(!briefing||briefing.is_read)return;
    const grid=document.getElementById("homeIntelligenceGrid");if(!grid||document.getElementById("weeklyHomeBanner"))return;
    const banner=document.createElement("section");banner.id="weeklyHomeBanner";banner.className="weekly-home-banner";banner.setAttribute("aria-label","Weekly AI Briefing disponibile");
    const copy=document.createElement("div");const label=document.createElement("span");label.textContent="WEEKLY AI BRIEFING";const title=document.createElement("strong");title.textContent="È disponibile il Weekly AI Briefing.";copy.append(label,title);
    const action=document.createElement("a");action.href="/weekly-briefing.html";action.textContent="Apri";banner.append(copy,action);grid.appendChild(banner);
  }catch(error){console.warn("[Weekly Briefing] Avviso Home non disponibile",error);}
})();
