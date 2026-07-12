(function initHomeOnboarding(){
  const H = window.MatchIQHome = window.MatchIQHome || {};
  const steps = [
    {
      label:"Benvenuto",
      title:"Il tuo lavoro tecnico, in un solo posto.",
      description:"La Home recupera soltanto attività reali e ti indica la prossima azione utile senza sostituirsi alle decisioni dello staff.",
      points:[["Una priorità alla volta","La sintesi cambia con partite, video e report disponibili."],["Nessun dato inventato","Se una sorgente non risponde, MatchIQ lo segnala senza mostrare falsi zeri."]]
    },
    {
      label:"Coach",
      title:"Prepara, vivi e completa la partita.",
      description:"Coach conserva sul dispositivo formazione, eventi, note e report della partita associati al tuo accesso.",
      points:[["Match Day","Registra eventi e osservazioni con pochi tocchi."],["Post-partita","Completa pagelle e report senza perdere il lavoro già inserito."]]
    },
    {
      label:"Video AI",
      title:"Dalla Sessione Video al report.",
      description:"Carica il video, riapri la sessione corretta e continua l'analisi dal Video Hub.",
      points:[["Stato reale","La Home distingue sessioni pronte, in elaborazione e archiviate."],["Ripristino","Il pulsante Continua usa l'identificativo della tua sessione."]]
    },
    {
      label:"Inizia",
      title:"Scegli la tua prima attività.",
      description:"Puoi cambiare modulo in qualsiasi momento e riaprire questa guida dal pulsante Guida.",
      final:true
    }
  ];
  let index = 0;
  let previousFocus = null;

  function key(){
    return `matchiq_home_onboarding_v1:${H.userScope?.() || "guest"}`;
  }

  function stored(){
    try{ return localStorage.getItem(key()); }catch(_error){ return null; }
  }

  function persist(state){
    try{ localStorage.setItem(key(),JSON.stringify({state,completed_at:new Date().toISOString()})); }catch(_error){ /* La guida resta utilizzabile anche senza persistenza. */ }
  }

  function dialog(){ return document.getElementById("homeOnboarding"); }

  function render(){
    const modal=dialog();
    const step=steps[index];
    if(!modal || !step) return;
    document.getElementById("onboardingStep").textContent=`PASSO ${index + 1} DI ${steps.length} · ${step.label}`;
    document.getElementById("onboardingProgress").style.width=`${((index + 1) / steps.length) * 100}%`;
    const content=document.getElementById("onboardingContent");
    content.replaceChildren();
    const title=document.createElement("h2"); title.id="onboardingTitle"; title.textContent=step.title;
    const description=document.createElement("p"); description.id="onboardingDescription"; description.textContent=step.description;
    content.append(title,description);
    if(step.points){
      const points=document.createElement("div"); points.className="onboarding-points";
      step.points.forEach(([heading,text]) => {
        const item=document.createElement("div"); item.className="onboarding-point";
        const strong=document.createElement("strong"); strong.textContent=heading;
        const span=document.createElement("span"); span.textContent=text;
        item.append(strong,span); points.append(item);
      });
      content.append(points);
    }
    if(step.final){
      const choices=document.createElement("div"); choices.className="onboarding-choice";
      [["Crea partita","/coach.html"],["Carica video","/video.html#videoUploadSection"],["Esplora Home","#homeMain"]].forEach(([label,url]) => {
        const action=document.createElement("a"); action.className="button button-primary"; action.href=url; action.textContent=label;
        action.addEventListener("click",()=>H.completeOnboarding()); choices.append(action);
      });
      content.append(choices);
    }
    modal.querySelector("[data-onboarding-back]").hidden=index === 0;
    modal.querySelector("[data-onboarding-next]").textContent=step.final ? "Completa" : "Continua";
  }

  H.openOnboarding = function(force=false){
    const modal=dialog();
    if(!modal || (!force && stored())) return;
    index=0; previousFocus=document.activeElement; render();
    if(!modal.open) modal.showModal();
    modal.querySelector("[data-onboarding-next]")?.focus();
  };

  H.completeOnboarding = function(state="completed"){
    persist(state);
    const modal=dialog(); if(modal?.open) modal.close();
    previousFocus?.focus?.();
  };

  H.bindOnboarding = function(){
    const modal=dialog(); if(!modal) return;
    document.querySelectorAll("[data-home-tour]").forEach(button => button.addEventListener("click",()=>H.openOnboarding(true)));
    modal.querySelector("[data-onboarding-close]").addEventListener("click",()=>H.completeOnboarding("closed"));
    modal.querySelector("[data-onboarding-skip]").addEventListener("click",()=>H.completeOnboarding("skipped"));
    modal.querySelector("[data-onboarding-back]").addEventListener("click",()=>{ index=Math.max(0,index-1); render(); });
    modal.querySelector("[data-onboarding-next]").addEventListener("click",()=>{
      if(index >= steps.length - 1) H.completeOnboarding();
      else{ index += 1; render(); modal.querySelector("[data-onboarding-next]").focus(); }
    });
    modal.addEventListener("cancel",event => { event.preventDefault(); H.completeOnboarding("closed"); });
    modal.addEventListener("keydown",event => {
      if(event.key === "Escape"){
        event.preventDefault();
        H.completeOnboarding("closed");
        return;
      }
      if(event.key !== "Tab") return;
      const focusable=[...modal.querySelectorAll('a[href],button:not([disabled]):not([hidden])')];
      if(!focusable.length) return;
      const first=focusable[0], last=focusable[focusable.length-1];
      if(event.shiftKey && document.activeElement === first){ event.preventDefault(); last.focus(); }
      else if(!event.shiftKey && document.activeElement === last){ event.preventDefault(); first.focus(); }
    });
  };
})();
