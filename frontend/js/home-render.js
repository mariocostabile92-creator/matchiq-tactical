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
    const next=H.state.view?.nextMatch;
    if(next)badges.append(node("span",`Prossima: ${next.home} - ${next.away}`,"badge"));
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

  H.renderWeekly=function(){
    const root=$("weeklyContent");if(!root)return;root.replaceChildren();const weekly=H.state.view?.weekly;
    if(!weekly){root.append(H.emptyState("La sintesi di questa settimana non è ancora disponibile.","Apri La tua settimana per riunire partite, osservazioni e materiali già raccolti.",[{label:"Prepara la settimana",url:"/weekly-briefing.html",primary:true}]));return}
    const card=node("article",undefined,"weekly-summary"),copy=node("div"),facts=node("div",undefined,"summary-facts");
    copy.append(node("span",weekly.isRead?"GIÀ LETTO":"DA LEGGERE","summary-kicker"),node("strong",weekly.title,"summary-title"),node("p",weekly.subtitle,"summary-copy"));
    weekly.sources.forEach(source=>facts.append(node("span",source)));if(weekly.sources.length)copy.append(facts);
    card.append(copy,link(weekly.isRead?"Rileggi":"Inizia la settimana","/weekly-briefing.html","card-action primary"));root.append(card);
  };

  H.renderWeeklyPriorities=function(){
    const root=$("weeklyPrioritiesContent");if(!root)return;root.replaceChildren();
    const items=H.state.view?.weeklyPriorities||[];
    if(!items.length){
      root.append(H.emptyState(
        "Le priorita emergeranno dalle partite.",
        "Dopo almeno tre partite coerenti, MatchIQ mostrera qui i pattern consolidati senza richiedere un'azione manuale."
      ));
      return;
    }
    items.slice(0,5).forEach(item=>{
      const card=node("article",undefined,"weekly-priority");
      card.dataset.priorityId=item.priority_id;
      const heading=node("div",undefined,"weekly-priority__heading");
      const copy=node("div");
      copy.append(
        node("span",`LIVELLO ${item.priority_level}`,"summary-kicker"),
        node("h3",item.topic),
        node("p",item.reason?.summary||"Priorita sostenuta da evidenze consolidate.")
      );
      const status=node("span",item.status==="CONFIRMED"?"CONFERMATA":item.status,"status-chip");
      heading.append(copy,status);

      const details=document.createElement("details");
      details.className="weekly-priority__details";
      const summary=node("summary","Visualizza dettagli");
      const references=item.references||{};
      const facts=node("div",undefined,"weekly-priority__facts");
      [
        ["Partite",(references.matches||[]).length],
        ["Pattern",(references.patterns||[]).length],
        ["Evidenze",(references.evidence||[]).length],
        ["Voice Coach",(references.voice_coach||[]).length],
        ["Video AI",(references.video_ai||[]).length],
        ["Note Coach",(references.coach_notes||[]).length]
      ].forEach(([label,value])=>facts.append(node("span",`${label}: ${value}`)));
      const factors=node("div",undefined,"weekly-priority__factors");
      Object.entries(item.reason?.factors||{})
        .filter(([key])=>["frequency","recency","confidence","staff_confirmation","impact"].includes(key))
        .forEach(([key,value])=>factors.append(node("span",`${key.replace("_"," ")} ${Math.round(Number(value)||0)}/100`)));
      details.append(summary,facts,factors);

      const actions=node("div",undefined,"weekly-priority__actions");
      const confirm=node("button","Conferma","button button-primary");
      confirm.type="button";confirm.dataset.priorityAction="CONFIRMED";
      const dismiss=node("button","Ignora","button button-muted");
      dismiss.type="button";dismiss.dataset.priorityAction="DISMISSED";
      const edit=node("button","Modifica","button button-muted");
      edit.type="button";edit.dataset.priorityEdit="toggle";
      actions.append(confirm,dismiss,edit);

      const form=document.createElement("form");
      form.className="weekly-priority__form";form.hidden=true;
      form.dataset.priorityForm="";
      const topicLabel=node("label","Titolo");
      const topic=document.createElement("input");
      topic.name="topic";topic.value=item.topic;topic.required=true;topic.maxLength=160;
      topicLabel.append(topic);
      const levelLabel=node("label","Livello");
      const level=document.createElement("select");level.name="priority_level";
      ["HIGH","MEDIUM","LOW"].forEach(value=>{
        const option=node("option",value);option.value=value;option.selected=value===item.priority_level;level.append(option);
      });
      levelLabel.append(level);
      const reasonLabel=node("label","Nota staff");
      const reason=document.createElement("textarea");
      reason.name="staff_reason";reason.maxLength=1200;reason.rows=2;
      reason.value=item.staff_reason||"";reasonLabel.append(reason);
      const save=node("button","Salva modifica","button button-primary");save.type="submit";
      form.append(topicLabel,levelLabel,reasonLabel,save);

      card.append(heading,details,actions,form);root.append(card);
    });
  };

  H.renderVideoFocus=function(){
    const root=$("videoFocusContent");if(!root)return;root.replaceChildren();const item=H.state.view?.videoAttention;
    if(!item){root.append(H.emptyState("Nessun progetto Video AI richiede attenzione.","Quando carichi una sessione, qui comparirà lo stato operativo più importante.",[{label:"Apri Video AI",url:"/video.html",primary:true}]));return}
    const card=node("article",undefined,"video-summary"),copy=node("div");
    copy.append(node("span",item.label,"summary-kicker"),node("strong",item.title,"summary-title"),node("p",item.copy,"summary-copy"));
    const actionClass=item.state==="failed"?"card-action":"card-action primary";card.append(copy,link(item.action,item.url,actionClass));root.append(card);
  };

  H.renderWeeklyFlow=function(){
    const list=$("weeklyFlowList");if(!list)return;list.replaceChildren();
    [
      ["Prepara","Obiettivi, squadra e piano gara."],
      ["Match Day","Eventi, Voice Coach e note dal campo."],
      ["Analizza","Video, report ed evidenze."],
      ["Allena","Priorità trasformate in sedute."],
      ["Riparti","Identità e decisioni per la prossima gara."]
    ].forEach(([title,copy],index)=>{const item=node("li");if(index===(H.state.view?.weeklyFlowCurrent??0)){item.classList.add("is-current");item.setAttribute("aria-current","step")}item.append(node("span",String(index+1),"flow-index"),node("strong",title),node("small",copy));list.append(item)});
  };

  H.renderIntelligence=function(){
    const grid=$("homeIntelligenceGrid");if(!grid)return;grid.replaceChildren();
    [
      ["Cosa si ripete","Rivedi comportamenti ricorrenti e le evidenze che li sostengono.","/pattern-intelligence.html"],
      ["Come gioca la tua squadra","Confronta i principi dello staff con ciò che emerge dal campo.","/tactical-identity.html"],
      ["Opzioni da valutare","Confronta poche alternative verificabili: la decisione resta allo staff.","/decision-engine.html"],
      ["Vista società","Condividi priorità tecniche con la società senza mescolare i contesti.","/club-intelligence.html"]
    ].forEach(([title,copy,url])=>{const card=node("article",undefined,"intelligence-card");card.append(node("span","APPROFONDISCI","intelligence-tag"),node("h3",title),node("p",copy),link("Apri",url));grid.append(card)});
  };

  H.renderActivity=function(){
    const root=$("recentActivity");if(!root)return;root.replaceChildren();const items=H.state.view?.activities||[];
    if(!items.length){root.append(H.emptyState("Nessuna attività recente.","Le attività reali di Coach e Video AI compariranno qui dopo il primo utilizzo."));return}
    items.slice(0,6).forEach(item=>{
      const row=node("article",undefined,"timeline-item"),copy=node("div");
      copy.append(node("strong",item.title||item.module),node("small",`${item.module} · ${item.status||"Aggiornato"}`));
      row.append(node("span",H.itemIcon(item.kind),"item-icon"),copy,node("time",H.formatDate(item.updated_at||item.created_at),"timeline-time"));
      if(item.url&&item.action)row.append(link(item.action,item.url));root.append(row);
    });
  };

  H.renderNotice=function(){
    const notice=$("homeNotice");if(!notice)return;const messages=[];
    if(H.state.error)messages.push(H.state.error);
    if(H.state.localOwnershipMismatch)messages.push("Le attività locali associate a un altro account non vengono mostrate.");
    notice.textContent=messages.join(" ");notice.hidden=!notice.textContent;
  };

  H.renderHome=function(){
    H.renderAccount();H.renderHero();H.renderPriorities();H.renderContinue();H.renderNextMatch();H.renderWeekly();H.renderWeeklyPriorities();H.renderVideoFocus();H.renderWeeklyFlow();H.renderIntelligence();H.renderActivity();H.renderNotice();
  };
})();
