(function(){
  const token=localStorage.getItem("token")||sessionStorage.getItem("token")||"";
  if(!token)return;
  const path=location.pathname;
  const labels={"/weekly-briefing.html":"Vedi briefing e fonti nella memoria tecnica","/pattern-intelligence.html":"Apri pattern e timeline nella memoria","/training-planner.html":"Apri piano, fonti e versioni nella memoria","/coach.html":"Apri cronologia tecnica","/video.html":"Vedi sessioni e report nella memoria tecnica","/account.html":"Apri MatchIQ Knowledge"};
  const types={"/weekly-briefing.html":"weekly_briefing","/pattern-intelligence.html":"historical_pattern","/training-planner.html":"training_plan","/coach.html":"match","/video.html":"video_report"};
  const href=`/knowledge.html${types[path]?`?node_type=${types[path]}`:""}`;
  function addCompact(){
    if(document.querySelector(".knowledge-entry"))return;
    const host=document.querySelector("main")||document.body;
    const section=document.createElement("section");section.className="knowledge-entry";section.innerHTML=`<small>MATCHIQ KNOWLEDGE</small><h2>Memoria tecnica collegata</h2><p>Apri fonti, relazioni e cronologia senza modificare i dati originali.</p><a href="${href}">${labels[path]||"Apri memoria"}</a>`;
    if(path==="/coach.html"){const target=document.querySelector(".coach-history,.history-section,#historySection");(target||host).append(section)}else host.append(section)
  }
  async function addHome(){
    if(document.querySelector(".knowledge-entry"))return;
    const host=document.querySelector("main")||document.body;const section=document.createElement("section");section.className="knowledge-entry";section.innerHTML='<small>MATCHIQ KNOWLEDGE</small><h2>La memoria tecnica della squadra</h2><p id="knowledgeHomeText">Carico gli elementi collegati...</p><a href="/knowledge.html">Apri memoria</a>';
    const anchor=document.querySelector("#trainingPlannerHome,.training-planner-home")||host.lastElementChild;anchor?.after?anchor.after(section):host.append(section);
    try{const response=await fetch("/api/knowledge-intelligence/status",{headers:{Authorization:`Bearer ${token}`}});if(!response.ok)throw new Error();const payload=await response.json(),summary=payload.data?.summary||{};section.querySelector("#knowledgeHomeText").innerHTML=summary.nodes?`<span class="knowledge-count">${summary.nodes} elementi collegati</span> · aggiornato ${summary.last_updated||"di recente"}`:"La memoria tecnica iniziera a crescere con partite, briefing e allenamenti."}catch{section.querySelector("#knowledgeHomeText").textContent="La memoria tecnica e disponibile dal tuo account."}
  }
  function addPatternDetailLink(){
    const detail=document.getElementById("patternDetail");if(!detail)return;const observer=new MutationObserver(()=>{if(detail.children.length&&!detail.querySelector(".knowledge-inline-link")){const link=document.createElement("a");link.className="knowledge-inline-link";link.href="/knowledge.html?node_type=historical_pattern";link.textContent="Vedi relazioni e timeline nella memoria";detail.append(link)}});observer.observe(detail,{childList:true,subtree:false})
  }
  if(path==="/index.html"||path==="/")addHome();else if(labels[path])addCompact();
  if(path==="/pattern-intelligence.html")addPatternDetailLink();
})();
