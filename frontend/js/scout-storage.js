/* MatchIQ Scout - Storage Module V8.0.3 Hotfix 3 */
function toggleWatchlistById(id){ if(!canUseWatchlist()){toast("Watchlist PRO","La watchlist Scout è disponibile solo per Pro/Owner.");return;} const p=state.players.find(x=>String(x.id)===String(id)); if(!p)return; if(isWatched(id)){removeWatchlist(id);toast("Rimosso dalla watchlist",p.name);}else{addWatchlist(p);toast("Aggiunto alla watchlist",p.name);} renderAll(); }
function addOpenPlayerToWatchlist(){ if(!canUseWatchlist()){toast("Watchlist PRO","Disponibile solo per Pro/Owner.");return;} const p=state.players.find(x=>String(x.id)===String(state.openPlayerId)); if(!p)return; addWatchlist(p); renderAll(); renderModal(); toast("Aggiunto alla watchlist",p.name); }
function removeOpenPlayerFromWatchlist(){ if(!canUseWatchlist())return; if(!state.openPlayerId)return; removeWatchlist(state.openPlayerId); renderAll(); renderModal(); }
function addWatchlist(p){ if(!p||!p.id||isWatched(p.id))return; const verdict=typeof scoutVerdict==="function"?scoutVerdict(p):null; state.watchlist.push({id:p.id,name:p.name,team:p.team,role:p.role,scout_score:p.scout_score,threat:p.threat,creativity:p.creativity,pressure:p.pressure,momentum:p.momentum,signal:p.signal,data_source:p.data_source,verdict_label:verdict?.label||"",verdict_reason:verdict?.reason||"",saved_at:new Date().toISOString()}); saveWatchlist(); }
function removeWatchlist(id){ state.watchlist=state.watchlist.filter(p=>String(p.id)!==String(id)); saveWatchlist(); }
function clearWatchlist(){ if(!canUseWatchlist()){toast("Watchlist PRO","Disponibile solo per Pro/Owner.");return;} state.watchlist=[]; saveWatchlist(); renderAll(); toast("Watchlist svuotata","Tutti i giocatori salvati sono stati rimossi."); }
function isWatched(id){ return state.watchlist.some(p=>String(p.id)===String(id)); }
function loadWatchlist(){ try{ const raw=localStorage.getItem(STORAGE_KEY); const parsed=JSON.parse(raw||"[]"); return Array.isArray(parsed)?parsed.filter(p=>p&&p.id):[];}catch{return [];} }
function saveWatchlist(){ try{localStorage.setItem(STORAGE_KEY,JSON.stringify(state.watchlist||[]));}catch{toast("Errore salvataggio","Non riesco a salvare la watchlist nel browser.");} }
function exportWatchlist(){
  if(!canExportScout()){toast("Export PRO","Export disponibile solo per Pro/Owner.");return;}
  if(!state.watchlist.length){toast("Watchlist vuota","Non ci sono player da esportare.");return;}
  const rows=[
    "Nome;Squadra;Ruolo;Score;Threat;Creativity;Pressure;Momentum;Verdetto;Motivo;Signal;Source;SavedAt",
    ...state.watchlist.map(p=>[
      csv(p.name),
      csv(p.team),
      csv(p.role),
      Math.round(num(p.scout_score,0)),
      Math.round(num(p.threat,0)),
      Math.round(num(p.creativity,0)),
      Math.round(num(p.pressure,0)),
      Math.round(num(p.momentum,0)),
      csv(p.verdict_label||"Da monitorare"),
      csv(p.verdict_reason||"profilo salvato"),
      csv(p.signal),
      csv(p.data_source),
      csv(p.saved_at||"")
    ].join(";"))
  ];
  downloadText("matchiq_watchlist_staff.csv",rows.join("\n"));
}
function scoutReportRecommendation(players, watchlist){
  const top=[...players].sort((a,b)=>num(b.scout_score,0)-num(a.scout_score,0))[0];
  const high=players.filter(p=>num(p.scout_score,0)>=82||num(p.threat,0)>=75).length;
  const creative=players.filter(p=>num(p.creativity,0)>=70).length;
  const watch=watchlist.length;
  if(!top){return "Nessun profilo reale disponibile: attendere dati live o cambiare partita.";}
  if(watch>0){return `Priorità staff: rivedere subito ${watch} profili salvati in watchlist, partendo da ${watchlist[0].name}.`;}
  if(high>=3){return `Partita con molti segnali scout: monitorare ${top.name} e preparare shortlist live.`;}
  if(creative>=2){return `Focus creativo: osservare i player che generano passaggi chiave e rifinitura.`;}
  return `Profilo principale da seguire: ${top.name}, score ${Math.round(num(top.scout_score,0))}.`;
}
function exportScoutReport(){
  if(!canExportScout()){toast("Export PRO","Report Scout disponibile solo per Pro/Owner.");return;}
  if(!state.players.length){toast("Nessun dato","Non ci sono player reali da esportare.");return;}
  const m=getMatch();
  const topPlayers=[...state.players].sort((a,b)=>num(b.scout_score,0)-num(a.scout_score,0)).slice(0,12);
  const urgent=state.players.filter(p=>num(p.scout_score,0)>=82||num(p.threat,0)>=75);
  const recommendation=scoutReportRecommendation(state.players,state.watchlist);
  const report=[
    "MATCHIQ SCOUT STAFF REPORT",
    "==========================",
    "",
    `Match: ${m?`${m.home} - ${m.away}`:"--"}`,
    `Score: ${m?`${m.scoreHome}-${m.scoreAway}`:"--"}`,
    `Minuto: ${m?m.minute+"'":"--"}`,
    `Status: ${m?m.status:"--"}`,
    `Generato: ${new Date().toLocaleString("it-IT")}`,
    "",
    "SINTESI STAFF",
    "------------",
    recommendation,
    "",
    "NUMERI CHIAVE",
    "------------",
    `Player analizzati: ${state.players.length}`,
    `Segnali forti: ${urgent.length}`,
    `Eventi timeline: ${state.events.length}`,
    `Watchlist: ${state.watchlist.length}`,
    "",
    "TOP PLAYER",
    "----------",
    ...topPlayers.map((p,i)=>{
      const verdict=typeof scoutVerdict==="function"?scoutVerdict(p):{label:"Da monitorare",reason:p.signal||""};
      return `${i+1}. ${p.name} | ${p.team} | ${p.role} | Score ${Math.round(num(p.scout_score,0))} | ${verdict.label}: ${verdict.reason}`;
    }),
    "",
    "WATCHLIST STAFF",
    "---------------",
    ...(state.watchlist.length?state.watchlist.map((p,i)=>`${i+1}. ${p.name} | ${p.team} | ${p.role} | Score ${Math.round(num(p.scout_score,0))} | ${p.verdict_label||"Da monitorare"}: ${p.verdict_reason||p.signal||"profilo salvato"}`):["Nessun player salvato in watchlist."]),
    "",
    "ULTIMI EVENTI LIVE",
    "-----------------",
    ...([...state.events].sort((a,b)=>num(b.minute,0)-num(a.minute,0)).slice(0,8).map(e=>`${e.minute}' ${e.label} - ${e.title}: ${e.desc}`))
  ].join("\n");
  downloadText(`matchiq_scout_${safeFilename(m?`${m.home}_${m.away}`:"report")}_staff.txt`,report);
}
function exportOpenPlayerReport(){
  if(!canExportScout()){toast("Export PRO","Player report disponibile solo per Pro/Owner.");return;}
  const p=state.players.find(x=>String(x.id)===String(state.openPlayerId));
  if(!p)return;
  const verdict=typeof scoutVerdict==="function"?scoutVerdict(p):{label:"Da monitorare",reason:p.signal||""};
  const playerEvents=state.events.filter(e=>String(e.playerId)===String(p.id)||e.playerName===p.name);
  const report=[
    "MATCHIQ PLAYER SCOUT REPORT",
    "===========================",
    "",
    `Giocatore: ${p.name}`,
    `Squadra: ${p.team}`,
    `Ruolo: ${p.role}`,
    `Verdetto: ${verdict.label}`,
    `Motivo: ${verdict.reason}`,
    `Data source: ${p.data_source}`,
    `Data quality: ${p.data_quality}`,
    "",
    "METRICHE",
    "-------",
    `Scout Score: ${Math.round(num(p.scout_score,0))}`,
    `Impact Score: ${Math.round(num(p.impact_score,0))}`,
    `Threat: ${Math.round(num(p.threat,0))}%`,
    `Creativity: ${Math.round(num(p.creativity,0))}%`,
    `Pressure: ${Math.round(num(p.pressure,0))}%`,
    `Momentum: ${Math.round(num(p.momentum,0))}%`,
    `Stamina: ${Math.round(num(p.stamina,0))}%`,
    "",
    "COMMENTO STAFF",
    "--------------",
    p.ai_summary||aiComment(p),
    "",
    "EVENTI PLAYER",
    "-------------",
    ...(playerEvents.length?playerEvents.map(e=>`${e.minute}' ${e.label} - ${e.title}: ${e.desc}`):["Nessun evento specifico disponibile."])
  ].join("\n");
  downloadText(`matchiq_player_${safeFilename(p.name)}_staff.txt`,report);
}
function downloadText(filename,text){ const blob=new Blob([text],{type:"text/plain;charset=utf-8"}); const url=URL.createObjectURL(blob); const a=document.createElement("a"); a.href=url; a.download=filename; document.body.appendChild(a); a.click(); document.body.removeChild(a); URL.revokeObjectURL(url); toast("Export completato",filename); }
function csv(v){ return `"${String(v??"").replaceAll('"','""')}"`; }
function safeFilename(v){ return String(v||"player").toLowerCase().replace(/[^a-z0-9]+/gi,"_").replace(/^_+|_+$/g,""); }
