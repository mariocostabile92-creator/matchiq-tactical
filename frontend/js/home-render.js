(function initHomeRender(){
  const H=window.MatchIQHome=window.MatchIQHome||{};
  const $=id=>document.getElementById(id);
  const node=(tag,value,className="")=>{const element=document.createElement(tag);if(className)element.className=className;if(value!==undefined)element.textContent=value;return element};
  const link=(label,href,className="card-action")=>{const element=node("a",label,className);element.href=href;return element};

  H.emptyState=function(title,description,actions=[]){
    const box=node("div",undefined,"empty-state");box.append(node("strong",title),node("p",description));
    if(actions.length){const row=node("div",undefined,"empty-actions");actions.forEach(action=>row.append(link(action.label,action.url,`button ${action.primary?"button-primary":"button-muted"}`)));box.append(row)}
    return box;
  };

  H.renderAccount=function(){
    const badges=$("heroBadges");if(!badges)return;badges.replaceChildren();
    badges.append(node("span",H.isOwner()?"Owner":"Private Beta",`badge ${H.isOwner()?"gold":""}`));
    badges.append(node("span",window.matchMedia?.("(display-mode: standalone)")?.matches?"PWA":"Web app","badge"));
  };

  H.itemIcon=function(kind){return({coach_match:"C",video_session:"V",video_report:"AI"})[kind]||"•"};

  H.renderHero=function(){
    const hero=H.state.view?.hero||H.contextForToday().hero;
    const greeting=$("heroGreeting"),title=$("heroTitle"),lead=$("heroLead"),actions=$("heroActions");
    if(greeting)greeting.textContent=hero.eyebrow;if(title)title.textContent=hero.title;if(lead)lead.textContent=hero.lead;
    if(actions){actions.replaceChildren();actions.append(link(hero.action,hero.url,"button button-primary"))}
    const statusTitle=$("heroStatusTitle"),statusText=$("heroStatusText");
    if(statusTitle)statusTitle.textContent=hero.statusTitle;if(statusText)statusText.textContent=hero.statusText;
  };

  H.renderPriorities=function(){
    const grid=$("priorityGrid");if(!grid)return;grid.replaceChildren();
    const items=H.state.view?.priorities||[];
    if(!items.length){grid.append(H.emptyState("Nessuna urgenza aperta.","Il lavoro disponibile è aggiornato. Puoi concentrarti sulla prossima attività dello staff."));return}
    items.slice(0,4).forEach(item=>{
      const card=node("article",undefined,"priority-card"),copy=node("div");
      copy.append(node("span",item.type==="system"?"Sistema":"Azione richiesta","priority-kind"),node("h3",item.title),node("p",item.text||""));
      card.append(copy,link(item.action||"Apri",item.url||"/index.html"));grid.append(card);
    });
  };

  H.renderContinue=function(){
    const list=$("continueList");if(!list)return;list.replaceChildren();const items=H.state.view?.continueItems||[];
    if(!items.length){list.append(H.emptyState("Tutto aggiornato.","Non ci sono attività interrotte da riprendere in questo momento."));return}
    items.forEach(item=>{
      const card=node("article",undefined,"continue-card"),copy=node("div");
      copy.append(node("h3",item.title||item.module),node("p",item.status||"In lavorazione"),node("span",H.formatDate(item.updated_at||item.created_at),"item-meta"));
      card.append(node("span",H.itemIcon(item.kind),"item-icon"),copy,link(item.action||"Continua",item.url||"/index.html"));list.append(card);
    });
  };

  H.renderNextMatch=function(){
    const root=$("nextMatchContent");if(!root)return;root.replaceChildren();const match=H.state.view?.nextMatch;
    if(!match){root.append(H.emptyState("Nessuna partita programmata.","Quando crei la prossima partita in Coach, qui troverai avversario, appuntamento e stato della preparazione.",[{label:"Prepara partita",url:"/coach.html#matchSetup",primary:true}]));return}
    const card=node("article",undefined,"match-summary"),copy=node("div"),facts=node("div",undefined,"summary-facts");
    copy.append(node("span",match.preparation,"summary-kicker"),node("strong",`${match.home} - ${match.away}`,"summary-title"));
    facts.append(node("span",match.date));if(match.time)facts.append(node("span",match.time));if(match.location)facts.append(node("span",match.location));copy.append(facts);
    card.append(copy,link(match.action,match.url,"card-action primary"));root.append(card);
  };

  H.renderWeeklyFlow=function(){
    const list=$("weeklyFlowList");if(!list)return;list.replaceChildren();
    [
      ["Prepara","Obiettivi, squadra e piano gara."],
      ["Match Day","Eventi, Voice Coach e note dal campo."],
      ["Analizza","Video, report ed evidenze."],
      ["Allena","Priorità trasformate in sedute."],
      ["Riparti","Identità e decisioni per la prossima gara."]
    ].forEach(([title,copy],index)=>{const item=node("li");item.append(node("span",String(index+1),"flow-index"),node("strong",title),node("small",copy));list.append(item)});
  };

  H.renderIntelligence=function(){
    const grid=$("homeIntelligenceGrid");if(!grid)return;grid.replaceChildren();
    [
      ["Pattern Intelligence","Scopri cosa si ripete nel tempo.","/pattern-intelligence.html"],
      ["Tactical Identity","Confronta principi dichiarati ed evidenze.","/tactical-identity.html"],
      ["Decision Engine","Valuta alternative con fonti verificabili.","/decision-engine.html"],
      ["Club Intelligence","Condividi priorità tecniche con la società.","/club-intelligence.html"]
    ].forEach(([title,copy,url])=>{const card=node("article",undefined,"intelligence-card");card.append(node("span","INTELLIGENCE","intelligence-tag"),node("h3",title),node("p",copy),link("Apri",url));grid.append(card)});
  };

  H.renderNotice=function(){
    const notice=$("homeNotice");if(!notice)return;const messages=[];
    if(H.state.error)messages.push(H.state.error);
    if(H.state.localOwnershipMismatch)messages.push("Le attività locali associate a un altro account non vengono mostrate.");
    notice.textContent=messages.join(" ");notice.hidden=!notice.textContent;
  };

  H.renderHome=function(){
    H.renderAccount();H.renderHero();H.renderPriorities();H.renderContinue();H.renderNextMatch();H.renderWeeklyFlow();H.renderIntelligence();H.renderNotice();
  };
})();
