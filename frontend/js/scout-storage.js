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
function scoutReportCss(){
  return `
    body{margin:0;background:#e9edf3;color:#0f172a;font-family:Inter,Arial,sans-serif}
    .page{width:min(920px,calc(100% - 36px));margin:24px auto;background:white;box-shadow:0 20px 60px rgba(15,23,42,.14)}
    .head{background:#07111f;color:white;padding:28px 34px}
    .brand{color:#00b894;font-size:12px;font-weight:900;text-transform:uppercase;letter-spacing:.08em}
    h1{margin:8px 0 6px;font-size:30px;line-height:1.05}
    .sub{color:#b7c7df;font-size:13px}
    .section{padding:24px 34px;border-bottom:1px solid #e7edf5}
    h2{font-size:16px;margin:0 0 14px;color:#0b2b48}
    .grid{display:grid;grid-template-columns:repeat(4,1fr);gap:10px}
    .kpi{border:1px solid #dce6f2;border-radius:12px;padding:12px;background:#f8fbff}
    .kpi small{display:block;color:#64748b;font-size:10px;font-weight:900;text-transform:uppercase}
    .kpi strong{display:block;margin-top:7px;font-size:21px}
    table{width:100%;border-collapse:collapse;font-size:12px}
    th{background:#e8fff6;color:#075f48;text-align:left;font-size:10px;text-transform:uppercase}
    th,td{padding:10px;border:1px solid #e2e8f0;vertical-align:top}
    .note{border-left:4px solid #00b894;background:#f0fff9;padding:14px 16px;line-height:1.55}
    .pill{display:inline-block;border-radius:999px;background:#e8fff6;color:#047857;padding:5px 9px;font-weight:900;font-size:11px}
    .foot{padding:18px 34px;color:#64748b;font-size:11px}
    @media print{body{background:white}.page{width:100%;margin:0;box-shadow:none}.section{break-inside:avoid}}
  `;
}
function htmlDoc(title, body){
  return `<!DOCTYPE html><html lang="it"><head><meta charset="UTF-8"><title>${esc(title)}</title><style>${scoutReportCss()}</style></head><body><main class="page">${body}</main></body></html>`;
}
function exportScoutReport(){
  if(!canExportScout()){toast("Export PRO","Report Scout disponibile solo per Pro/Owner.");return;}
  if(!state.players.length){toast("Nessun dato","Non ci sono player reali da esportare.");return;}
  const m=getMatch();
  const topPlayers=[...state.players].sort((a,b)=>num(b.scout_score,0)-num(a.scout_score,0)).slice(0,12);
  const urgent=state.players.filter(p=>num(p.scout_score,0)>=82||num(p.threat,0)>=75);
  const recommendation=scoutReportRecommendation(state.players,state.watchlist);
  const title=m?`${m.home} - ${m.away}`:"Scout report";
  const topRows=topPlayers.map((p,i)=>{
      const verdict=typeof scoutVerdict==="function"?scoutVerdict(p):{label:"Da monitorare",reason:p.signal||""};
      return `<tr><td>${i+1}</td><td><strong>${esc(p.name)}</strong><br>${esc(p.team)} · ${esc(p.role)}</td><td>${Math.round(num(p.scout_score,0))}</td><td><span class="pill">${esc(verdict.label)}</span><br>${esc(verdict.reason)}</td></tr>`;
    }).join("");
  const watchRows=state.watchlist.length?state.watchlist.map((p,i)=>`<tr><td>${i+1}</td><td><strong>${esc(p.name)}</strong><br>${esc(p.team)} · ${esc(p.role)}</td><td>${Math.round(num(p.scout_score,0))}</td><td>${esc(p.verdict_label||"Da monitorare")}<br>${esc(p.verdict_reason||p.signal||"profilo salvato")}</td></tr>`).join(""):`<tr><td colspan="4">Nessun player salvato in watchlist.</td></tr>`;
  const eventRows=[...state.events].sort((a,b)=>num(b.minute,0)-num(a.minute,0)).slice(0,8).map(e=>`<tr><td>${esc(e.minute)}'</td><td>${esc(e.label)}</td><td><strong>${esc(e.title)}</strong><br>${esc(e.desc)}</td></tr>`).join("")||`<tr><td colspan="3">Nessun evento live disponibile.</td></tr>`;
  const html=htmlDoc(`MatchIQ Scout - ${title}`,`
    <header class="head">
      <div class="brand">MatchIQ Scout Staff Report</div>
      <h1>${esc(title)}</h1>
      <div class="sub">${m?`Score ${esc(m.scoreHome)}-${esc(m.scoreAway)} · ${esc(m.minute)}' · ${esc(m.status||"Live")}`:"Partita non indicata"} · Generato ${new Date().toLocaleString("it-IT")}</div>
    </header>
    <section class="section"><h2>Sintesi staff</h2><div class="note">${esc(recommendation)}</div></section>
    <section class="section"><h2>Numeri chiave</h2><div class="grid">
      <div class="kpi"><small>Player analizzati</small><strong>${state.players.length}</strong></div>
      <div class="kpi"><small>Segnali forti</small><strong>${urgent.length}</strong></div>
      <div class="kpi"><small>Eventi timeline</small><strong>${state.events.length}</strong></div>
      <div class="kpi"><small>Watchlist</small><strong>${state.watchlist.length}</strong></div>
    </div></section>
    <section class="section"><h2>Top player</h2><table><thead><tr><th>#</th><th>Giocatore</th><th>Score</th><th>Verdetto</th></tr></thead><tbody>${topRows}</tbody></table></section>
    <section class="section"><h2>Watchlist staff</h2><table><thead><tr><th>#</th><th>Giocatore</th><th>Score</th><th>Motivo</th></tr></thead><tbody>${watchRows}</tbody></table></section>
    <section class="section"><h2>Ultimi eventi live</h2><table><thead><tr><th>Min</th><th>Tipo</th><th>Evento</th></tr></thead><tbody>${eventRows}</tbody></table></section>
    <footer class="foot">Documento generato con MatchIQ Scout. Usare come supporto decisionale, non come valutazione definitiva.</footer>
  `);
  downloadHtml(`matchiq_scout_${safeFilename(title)}_staff.html`,html);
}
function exportOpenPlayerReport(){
  if(!canExportScout()){toast("Export PRO","Player report disponibile solo per Pro/Owner.");return;}
  const p=state.players.find(x=>String(x.id)===String(state.openPlayerId));
  if(!p)return;
  const verdict=typeof scoutVerdict==="function"?scoutVerdict(p):{label:"Da monitorare",reason:p.signal||""};
  const playerEvents=state.events.filter(e=>String(e.playerId)===String(p.id)||e.playerName===p.name);
  const eventRows=playerEvents.length?playerEvents.map(e=>`<tr><td>${esc(e.minute)}'</td><td>${esc(e.label)}</td><td><strong>${esc(e.title)}</strong><br>${esc(e.desc)}</td></tr>`).join(""):`<tr><td colspan="3">Nessun evento specifico disponibile.</td></tr>`;
  const html=htmlDoc(`MatchIQ Player - ${p.name}`,`
    <header class="head">
      <div class="brand">MatchIQ Player Scout Report</div>
      <h1>${esc(p.name)}</h1>
      <div class="sub">${esc(p.team)} · ${esc(p.role)} · ${esc(cleanScoutLabel(p.data_source||"Live data"))}</div>
    </header>
    <section class="section"><h2>Verdetto</h2><div class="note"><strong>${esc(verdict.label)}</strong><br>${esc(verdict.reason)}</div></section>
    <section class="section"><h2>Metriche</h2><div class="grid">
      <div class="kpi"><small>Scout score</small><strong>${Math.round(num(p.scout_score,0))}</strong></div>
      <div class="kpi"><small>Impact</small><strong>${Math.round(num(p.impact_score,0))}</strong></div>
      <div class="kpi"><small>Threat</small><strong>${Math.round(num(p.threat,0))}%</strong></div>
      <div class="kpi"><small>Creatività</small><strong>${Math.round(num(p.creativity,0))}%</strong></div>
      <div class="kpi"><small>Pressione</small><strong>${Math.round(num(p.pressure,0))}%</strong></div>
      <div class="kpi"><small>Momentum</small><strong>${Math.round(num(p.momentum,0))}%</strong></div>
      <div class="kpi"><small>Stamina</small><strong>${Math.round(num(p.stamina,0))}%</strong></div>
      <div class="kpi"><small>Qualità dato</small><strong>${esc(cleanScoutLabel(p.data_quality||"--"))}</strong></div>
    </div></section>
    <section class="section"><h2>Commento staff</h2><div class="note">${esc(p.ai_summary||aiComment(p))}</div></section>
    <section class="section"><h2>Eventi player</h2><table><thead><tr><th>Min</th><th>Tipo</th><th>Evento</th></tr></thead><tbody>${eventRows}</tbody></table></section>
    <footer class="foot">Documento generato con MatchIQ Scout.</footer>
  `);
  downloadHtml(`matchiq_player_${safeFilename(p.name)}_staff.html`,html);
}
function downloadText(filename,text){ const blob=new Blob([text],{type:"text/plain;charset=utf-8"}); const url=URL.createObjectURL(blob); const a=document.createElement("a"); a.href=url; a.download=filename; document.body.appendChild(a); a.click(); document.body.removeChild(a); URL.revokeObjectURL(url); toast("Export completato",filename); }
function downloadHtml(filename,html){ const blob=new Blob([html],{type:"text/html;charset=utf-8"}); const url=URL.createObjectURL(blob); const a=document.createElement("a"); a.href=url; a.download=filename; document.body.appendChild(a); a.click(); document.body.removeChild(a); URL.revokeObjectURL(url); toast("Report HTML pronto",filename); }
function csv(v){ return `"${String(v??"").replaceAll('"','""')}"`; }
function safeFilename(v){ return String(v||"player").toLowerCase().replace(/[^a-z0-9]+/gi,"_").replace(/^_+|_+$/g,""); }
