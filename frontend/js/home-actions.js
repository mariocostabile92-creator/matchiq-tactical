(function initHomeActions(){
  const H = window.MatchIQHome = window.MatchIQHome || {};
  const STAFF_PRIORITY_ACTIONS=new Set(["CONFIRMED","DISMISSED","MODIFIED"]);
  H.refreshHome = async function(){
    await H.loadHomeData();
    H.renderHome();
  };

  H.bindActions = function(){
    document.querySelectorAll("[data-home-retry]").forEach(button => button.addEventListener("click", async () => {
      button.disabled=true; button.textContent="…";
      try{ await H.refreshHome(); }
      finally{ button.disabled=false; button.textContent="↻"; }
    }));
    let lastResumeRefresh=0;
    const refreshAfterResume=async () => {
      if(document.visibilityState === "hidden" || Date.now() - lastResumeRefresh < 15000) return;
      lastResumeRefresh=Date.now();
      try{ await H.refreshHome(); }catch(_error){ /* Stato parziale già gestito dalla Home. */ }
    };
    window.addEventListener("pageshow",event => { if(event.persisted) refreshAfterResume(); });
    document.addEventListener("visibilitychange",refreshAfterResume);

    const priorities=document.getElementById("weeklyPrioritiesContent");
    priorities?.addEventListener("click",async event=>{
      const button=event.target.closest("[data-priority-action],[data-priority-edit]");
      if(!button)return;
      const card=button.closest("[data-priority-id]");
      if(!card)return;
      const form=card.querySelector("[data-priority-form]");
      if(button.dataset.priorityEdit){
        form.hidden=!form.hidden;
        if(!form.hidden)form.querySelector("input")?.focus();
        return;
      }
      if(!STAFF_PRIORITY_ACTIONS.has(button.dataset.priorityAction))return;
      button.disabled=true;
      try{
        await H.updateWeeklyPriority(card.dataset.priorityId,{status:button.dataset.priorityAction});
        await H.refreshHome();
      }catch(error){
        H.state.error=error?.message||"Non e stato possibile aggiornare la priorita.";
        H.renderNotice();
      }finally{button.disabled=false}
    });
    priorities?.addEventListener("submit",async event=>{
      const form=event.target.closest("[data-priority-form]");
      if(!form)return;
      event.preventDefault();
      const card=form.closest("[data-priority-id]");
      const submit=form.querySelector("[type='submit']");
      const data=new FormData(form);
      submit.disabled=true;
      try{
        await H.updateWeeklyPriority(card.dataset.priorityId,{
          status:"MODIFIED",
          topic:String(data.get("topic")||"").trim(),
          priority_level:String(data.get("priority_level")||"MEDIUM"),
          staff_reason:String(data.get("staff_reason")||"").trim()||null
        });
        await H.refreshHome();
      }catch(error){
        H.state.error=error?.message||"Non e stato possibile salvare la modifica.";
        H.renderNotice();
      }finally{submit.disabled=false}
    });
  };
})();
