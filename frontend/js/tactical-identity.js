(function(){
  const I=window.MatchIQIdentity,$=id=>document.getElementById(id);
  I.els={notice:$("identityNotice"),run:$("identityRun"),meta:$("identityMeta"),empty:$("identityEmpty"),summary:$("identitySummary"),comparison:$("identityComparison"),dimensions:$("identityDimensions"),timeline:$("identityTimeline"),ask:$("identityAsk"),dialog:$("identityDialog"),dialogTitle:$("identityDialogTitle"),detail:$("identityDetail")};
  I.notice=(message,error=false)=>{I.els.notice.textContent=message;I.els.notice.classList.toggle("error",error)};
  const values=()=>({season:$("filterSeason").value,period_start:$("filterFrom").value,period_end:$("filterTo").value,competition:$("filterCompetition").value.trim(),formation:$("filterFormation").value.trim(),source_type:$("filterSource").value,dimension_group:$("filterGroup").value,confidence_level:$("filterConfidence").value,validation_state:$("filterValidation").value});
  const params=()=>{const p=new URLSearchParams();Object.entries(values()).forEach(([key,value])=>value&&p.set(key,value));return p};
  I.load=async()=>{
    if(!I.token()){location.href="/login.html?next=/tactical-identity.html";return}
    if(!navigator.onLine){const cached=I.cached();if(cached?.data){I.render(cached.data);I.notice(`Offline: mostro l'identita salvata il ${new Date(cached.savedAt).toLocaleString("it-IT")}. I dati potrebbero non essere aggiornati.`);I.els.run.disabled=true}else I.notice("Offline: nessuna identita salvata disponibile.",true);return}
    try{const data=await I.api.current(params().toString());I.render(data);I.notice(data.status==="empty"?data.message:`Identita aggiornata al ${new Date(data.updated_at).toLocaleString("it-IT")}.`)}catch(error){I.notice(error.message,true)}
  };
  I.run=async()=>{
    if(!navigator.onLine)return; I.els.run.disabled=true; I.notice("Raccolgo le fonti Knowledge e aggiorno l'identita senza duplicare dati...");
    try{const filter=values(),payload={season:filter.season||null,period_start:filter.period_start||null,period_end:filter.period_end||null,competition:filter.competition||null,formation:filter.formation||null,source_type:filter.source_type||null};const result=await I.api.run(payload);if(result.status==="processing"){I.notice(result.message||"Aggiornamento identita gia in corso.");return}if(result.data)I.render(result.data);I.notice(result.unchanged?(result.evidence_refreshed?"Evidenze aggiornate: l'identita non e cambiata, quindi non e stata creata una versione inutile.":"Le fonti non sono cambiate: nessuna nuova versione creata."):"Identita aggiornata e nuova versione significativa salvata.")}catch(error){I.notice(error.message,true)}finally{I.els.run.disabled=false}
  };
  I.els.run.addEventListener("click",I.run); $("filterApply").addEventListener("click",I.load);
  I.els.dimensions.addEventListener("click",event=>{const detail=event.target.closest("[data-detail]"),validation=event.target.closest("[data-validation]");if(detail)I.openDetail(detail.dataset.detail);if(validation)I.openValidation(validation.dataset.validation)});
  I.els.detail.addEventListener("click",event=>{const save=event.target.closest("[data-save-validation]");if(save)I.saveValidation(save.dataset.saveValidation)});
  $("identityClose").addEventListener("click",I.closeDetail); I.els.dialog.addEventListener("click",event=>{if(event.target===I.els.dialog)I.closeDetail()});
  window.addEventListener("offline",()=>I.load()); window.addEventListener("online",()=>{I.els.run.disabled=false;I.load()}); document.addEventListener("keydown",event=>{if(event.key==="Escape"&&I.els.dialog.open)I.closeDetail()});
  const today=new Date(),from=new Date(today);from.setDate(from.getDate()-120);$("filterTo").value=today.toISOString().slice(0,10);$("filterFrom").value=from.toISOString().slice(0,10);I.load();
})();
