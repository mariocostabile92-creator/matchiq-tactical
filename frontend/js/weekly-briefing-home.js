(async function showWeeklyBriefingOnHome(){
  const W=window.MatchIQWeekly;if(!W?.authToken?.())return;
  try{
    const data=await W.generate();const briefing=data.briefing;if(!briefing||briefing.is_read)return;
    const grid=document.getElementById("homeIntelligenceGrid");if(!grid||document.getElementById("weeklyHomeBanner"))return;
    const banner=document.createElement("section");banner.id="weeklyHomeBanner";banner.className="weekly-home-banner";banner.setAttribute("aria-label","La tua settimana disponibile");
    const copy=document.createElement("div");const label=document.createElement("span");label.textContent="LA TUA SETTIMANA";const title=document.createElement("strong");title.textContent="La sintesi della settimana è pronta.";copy.append(label,title);
    const action=document.createElement("a");action.href="/weekly-briefing.html";action.textContent="Apri";banner.append(copy,action);grid.appendChild(banner);
  }catch(error){console.warn("[Weekly Briefing] Avviso Home non disponibile",error);}
})();
