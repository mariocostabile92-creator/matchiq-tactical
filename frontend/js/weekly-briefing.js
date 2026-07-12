(async function bootWeeklyBriefing(){
  const W=window.MatchIQWeekly;if(!W.authToken()){document.getElementById("weeklyLoading").textContent="Accedi per creare il tuo Weekly AI Briefing.";document.getElementById("weeklyLogin").hidden=false;return;}
  try{const data=await W.generate();W.render(data.briefing);if(data.briefing?.id)await W.markRead(data.briefing.id);}catch(error){document.getElementById("weeklyLoading").textContent=`Briefing non disponibile: ${error.message}`;}
  if("serviceWorker" in navigator)navigator.serviceWorker.register("/service-worker.js").catch(()=>{});
})();
