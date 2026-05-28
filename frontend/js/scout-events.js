/* MatchIQ Scout - Events Module V8.0.3 Hotfix 3 */
function simulateHighImpactEvent(){
  if(!canSimulateScout()){ toast("Funzione PRO","La simulazione eventi è disponibile solo per Pro/Owner."); return; }
  if(!state.hasRealPlayers){ toast("Nessun player reale","Prima carica dati reali."); return; }
  generateLocalEvent(true);
}
function generateLocalEvent(high=false){
  if(!state.players.length) return;
  const templates=[{type:"shot",label:"TIRO",className:"",score:3,threat:5,momentum:3},{type:"chance",label:"OCCASIONE",className:"alert",score:5,threat:8,momentum:4},{type:"goal",label:"GOAL",className:"goal",score:10,threat:10,momentum:8},{type:"assist",label:"ASSIST",className:"goal",score:8,threat:6,momentum:7},{type:"pressure",label:"PRESSIONE",className:"momentum",score:4,threat:2,momentum:6},{type:"momentum",label:"MOMENTUM",className:"momentum",score:4,threat:4,momentum:9}];
  const pool=high?templates.filter(t=>["goal","assist","chance","momentum"].includes(t.type)):templates;
  const t=pool[Math.floor(Math.random()*pool.length)], p=pickPlayer(), m=getMatch();
  const event={id:uid(),minute:m?.minute||1,type:t.type,label:t.label,className:t.className,playerId:p.id,playerName:p.name,title:eventTitle(t.type,p),desc:eventDesc(t.type,p)};
  applyImpact(p,t); state.events.push(event); updateCache(); renderAll(); flashCard(p.id); toast(event.title,event.desc);
}
function pickPlayer(){ const weighted=[]; state.players.forEach(p=>{let w=1;if(p.signal_type==="hot")w+=3;if(p.signal_type==="danger")w+=2;if(num(p.threat,0)>=75)w+=2;for(let i=0;i<w;i++)weighted.push(p);}); return weighted[Math.floor(Math.random()*weighted.length)]; }
function applyImpact(p,t){ p.scout_score=clamp(num(p.scout_score,0)+t.score,0,99);p.impact_score=clamp(num(p.impact_score,0)+t.score,0,99);p.threat=clamp(num(p.threat,0)+t.threat,0,99);p.momentum=clamp(num(p.momentum,0)+t.momentum,0,99);p.fatigue=clamp(num(p.fatigue,35)+2,0,99);p.stamina=clamp(100-p.fatigue,0,100); if(t.type==="shot")p.shots=num(p.shots,0)+1; if(t.type==="assist"||t.type==="chance")p.key_passes=num(p.key_passes,0)+1; if(t.type==="pressure")p.pressure=clamp(num(p.pressure,0)+8,0,99); if(t.type==="goal"||t.type==="assist"||p.scout_score>=84){p.signal_type="hot";p.signal="Hot Player";}else if(t.type==="chance"||p.threat>=82){p.signal_type="danger";p.signal="High Threat Zone";}else if(t.type==="pressure"){p.signal_type="pressure";p.signal="Pressure Trigger";} }
function eventTitle(type,p){return {shot:`${p.name} tenta la conclusione`,chance:`AI ALERT: ${p.name} crea una grande occasione`,goal:`GOAL IMPACT: ${p.name}`,assist:`Assist rilevato per ${p.name}`,pressure:`${p.name} attiva pressione alta`,momentum:`Momentum spike detected`}[type]||`Evento live per ${p.name}`;}
function eventDesc(type,p){return {shot:`Threat offensivo in crescita per ${p.name}.`,chance:`${p.name} entra in zona ad alta pericolosità.`,goal:`Scout score aggiornato dopo evento decisivo.`,assist:`Contributo creativo diretto rilevato dal motore AI.`,pressure:`Pressure engine segnala intensità sopra media.`,momentum:`${p.name} sta influenzando il ritmo della partita.`}[type]||"Evento rilevato da MatchIQ AI.";}
