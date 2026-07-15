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
    H.renderAccount();H.renderWeeklyFlow();H.renderIntelligence();H.renderNotice();
  };
})();
