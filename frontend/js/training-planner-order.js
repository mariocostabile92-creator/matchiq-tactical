(function(){
  const T=window.MatchIQTraining;
  const baseRender=T.render;

  function makeButton(direction,label,kind,disabled){
    const control=document.createElement("button");
    control.type="button";
    control.textContent=label;
    control.dataset[kind]=String(direction);
    control.title=kind==="moveSession"?`Sposta seduta ${label.toLowerCase()}`:`Sposta esercizio ${label.toLowerCase()}`;
    control.disabled=disabled;
    return control;
  }

  T.render=function(plan){
    baseRender(plan);
    if(!plan?.current_plan?.sessions)return;
    document.querySelectorAll("#sessionTimeline .session").forEach((card,index,cards)=>{
      const tools=document.createElement("div");
      tools.className="order-tools session-order";
      tools.setAttribute("aria-label","Ordine seduta");
      const title=document.createElement("strong");
      title.textContent=`Seduta ${index+1}`;
      tools.append(title,makeButton(-1,"Su","moveSession",index===0),makeButton(1,"Giu","moveSession",index===cards.length-1));
      card.prepend(tools);
      card.querySelectorAll(".drill").forEach((drill,drillIndex,drills)=>{
        const drillTools=document.createElement("div");
        drillTools.className="order-tools drill-order";
        drillTools.append(makeButton(-1,"Su","moveDrill",drillIndex===0),makeButton(1,"Giu","moveDrill",drillIndex===drills.length-1));
        drill.prepend(drillTools);
      });
    });
  };

  document.getElementById("sessionTimeline").addEventListener("click",event=>{
    const sessionButton=event.target.closest("[data-move-session]");
    const drillButton=event.target.closest("[data-move-drill]");
    if(!sessionButton&&!drillButton)return;
    const current=T.readEditor();
    if(sessionButton){
      const from=Number(sessionButton.closest(".session").dataset.index);
      const to=from+Number(sessionButton.dataset.moveSession);
      if(to>=0&&to<current.sessions.length){
        const [session]=current.sessions.splice(from,1);
        current.sessions.splice(to,0,session);
      }
    }else{
      const card=drillButton.closest(".session");
      const box=drillButton.closest(".drill");
      const session=current.sessions[Number(card.dataset.index)];
      const from=Number(box.dataset.drill);
      const to=from+Number(drillButton.dataset.moveDrill);
      if(to>=0&&to<session.drills.length){
        const [drill]=session.drills.splice(from,1);
        session.drills.splice(to,0,drill);
      }
    }
    T.state.plan.current_plan=current;
    T.render(T.state.plan);
    T.notice("Ordine aggiornato. Premi Salva modifiche per confermare.");
  });
})();
