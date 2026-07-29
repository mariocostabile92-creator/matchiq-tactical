(async function(){
  const T=window.MatchIQTraining;
  if(!T.token()){
    location.href="/login.html?next=/training-planner.html";
    return;
  }

  async function load(){
    try{
      const [planPayload,libraryPayload,knowledgePayload]=await Promise.all([
        T.current(),T.library(),T.knowledge()
      ]);
      T.state.library=libraryPayload.data?.items||[];
      T.state.profile=knowledgePayload.knowledge?.team_profile||{};
      T.applyTeamProfile(T.state.profile);
      const plan=planPayload.data?.plan;
      T.render(plan);
      T.notice(
        plan
          ?"Bozza caricata. Le priorita e le evidenze originali restano collegate."
          :"Conferma una priorita della settimana per creare automaticamente una bozza."
      );
      if(plan&&!plan.is_viewed)await T.view(plan.id);
    }catch(error){
      T.notice(error.message,true);
    }
  }

  async function generate(force){
    try{
      T.notice("Leggo contesto, calendario e priorità confermate...");
      const knowledge=await T.saveTeamProfile(T.profilePayload());
      T.state.profile=knowledge.knowledge?.team_profile||T.state.profile;
      const payload=await T.generate(force);
      if(!payload.data?.sufficient){
        T.render(null);
        T.notice(payload.data?.message||"Nessuna priorita confermata disponibile.",true);
        return;
      }
      T.render(payload.data.plan);
      T.notice(
        payload.generated
          ?"Seduta composta con la libreria verificata MatchIQ."
          :"Contesto e priorità non sono cambiati: mostro la seduta disponibile."
      );
    }catch(error){
      T.notice(error.message,true);
    }
  }

  document.getElementById("generatePlan").addEventListener("click",()=>generate(false));
  document.getElementById("regeneratePlan").addEventListener("click",()=>generate(true));

  document.getElementById("addExercise").addEventListener("click",()=>{
    const sessionIndex=Number(document.getElementById("exerciseSession").value);
    const exerciseId=document.getElementById("exerciseLibrary").value;
    const session=T.state.plan?.current_plan?.sessions?.[sessionIndex];
    const source=T.state.library.find(item=>item.id===exerciseId);
    if(!session||!source)return;
    if((session.drills||[]).some(item=>item.id===source.id)){
      T.notice("Questa esercitazione e gia presente nella seduta.",true);
      return;
    }
    const drill=structuredClone(source);
    drill.players=Math.min(
      Number(session.players||document.getElementById("players").value||18),
      Number(drill.max_players||40)
    );
    drill.selected_duration=drill.duration;
    drill.selected_intensity=session.intensity||drill.intensity;
    drill.composer_block=document.getElementById("exerciseBlock").value;
    session.drills=session.drills||[];
    session.drills.push(drill);
    session.status="modificata";
    T.render(T.state.plan);
    T.notice("Esercitazione aggiunta alla bozza. Salva per confermare la modifica.");
  });

  document.getElementById("sessionTimeline").addEventListener("click",event=>{
    const button=event.target.closest("[data-remove-drill]");
    if(!button)return;
    const sessionCard=button.closest(".session");
    const sessionIndex=Number(sessionCard?.dataset.index);
    const drillIndex=Number(button.dataset.removeDrill);
    const session=T.state.plan?.current_plan?.sessions?.[sessionIndex];
    if(!session?.drills?.[drillIndex])return;
    session.drills.splice(drillIndex,1);
    session.status="modificata";
    T.render(T.state.plan);
    T.notice("Esercitazione rimossa dalla bozza. Salva per confermare la modifica.");
  });

  document.getElementById("savePlan").addEventListener("click",async()=>{
    try{
      const payload=await T.save(
        T.state.plan.id,
        T.readEditor(),
        document.getElementById("staffNote").value.trim()||null
      );
      T.render(payload.data.plan);
      T.notice("Modifiche salvate. Priorita ed evidenze originali sono rimaste intatte.");
    }catch(error){
      T.notice(error.message,true);
    }
  });

  document.querySelector("#planArea .actions").addEventListener("click",async event=>{
    const action=event.target.dataset.planAction;
    if(!action)return;
    try{
      const payload=await T.action(
        T.state.plan.id,
        action,
        document.getElementById("staffNote").value.trim()||null
      );
      T.render(payload.data.plan);
      T.notice(`Piano: ${payload.data.plan.status}.`);
    }catch(error){
      T.notice(error.message,true);
    }
  });

  await load();
  if("serviceWorker" in navigator)navigator.serviceWorker.register("/service-worker.js").catch(()=>{});
})();
