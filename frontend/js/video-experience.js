(function(){
  const shell = document.getElementById("videoExperienceShell");
  if(!shell || shell.dataset.mounted === "true") return;
  shell.dataset.mounted = "true";

  const views = new Map(Array.from(shell.querySelectorAll("[data-vx-view]")).map(node => [node.dataset.vxView,node]));
  const steps = Array.from(shell.querySelectorAll("[data-vx-step]"));
  const projectDialog = document.getElementById("vxProjectsDialog");
  const state = {
    view:"start",
    previousView:"start",
    project:null,
    evidences:[],
    mode:"analysis",
    processingStarted:0,
    elapsedTimer:0,
    mounted:false
  };

  function node(id){ return document.getElementById(id); }
  function text(value){ return String(value == null ? "" : value); }
  function safeProject(){ return state.project && typeof state.project === "object" ? state.project : {}; }
  function pipeline(){ return safeProject().pipeline || {}; }
  function hasVideo(){ return Boolean(node("videoInput")?.files?.[0] || node("videoPreview")?.src); }

  function updateSelectedFile(){
    const dropzone = node("vxUploadDropzone");
    const file = node("videoInput")?.files?.[0];
    if(!dropzone) return;
    dropzone.classList.toggle("has-file",Boolean(file));
    const title = dropzone.querySelector("strong");
    const description = dropzone.querySelector("span");
    if(title) title.textContent = file ? file.name : "Trascina qui il video";
    if(description) description.textContent = file
      ? `${Math.max(.1,file.size / 1024 / 1024).toFixed(1)} MB · pronto per la configurazione`
      : "Partita, allenamento o clip da una sorgente autorizzata.";
  }

  function move(targetId, element){
    const target = node(targetId);
    if(target && element) target.appendChild(element);
  }

  function fieldByControl(controlId){ return node(controlId)?.closest(".field") || null; }

  function mountExistingExperience(){
    if(state.mounted) return;
    const upload = node("videoUploadSection");
    const form = upload?.previousElementSibling?.classList.contains("form-grid") ? upload.previousElementSibling : document.querySelector(".hero .form-grid");
    const setup = node("videoIntelligenceSetup");
    const evidence = node("videoEvidenceWorkspace");
    const videoLibrary = upload?.querySelector(".video-library");
    const player = node("videoShell");
    const tactical = node("tacticalTools");
    const primaryIds = ["videoTitle","observedTeam","videoFocus","videoCategory"];

    move("vxUploadInputMount",node("videoInput"));
    move("vxSetupEngineMount",setup);
    primaryIds.forEach(id => move("vxPrimaryFields",fieldByControl(id)));
    if(form){
      Array.from(form.children).forEach(child => move("vxAdvancedFields",child));
      form.hidden = true;
    }
    move("vxProjectsMount",videoLibrary);
    move("vxPlayerMount",player);
    move("vxPlayerToolsMount",tactical);
    move("vxEvidenceMount",evidence);

    const actions = node("extractBtn")?.closest(".actions");
    move("vxReviewSecondaryMount",actions);
    move("vxReviewSecondaryMount",node("aiSlideDeck"));
    move("vxReviewSecondaryMount",node("statusBox"));
    move("vxReviewSecondaryMount",node("framesGrid"));

    const reportPanel = document.querySelector(".hero > .panel:last-child");
    const archive = reportPanel?.querySelector(".archive");
    if(archive) move("vxProjectsMount",archive);
    [node("reportMeta"),node("reportBox"),reportPanel?.querySelector(".sample-report")].forEach(item => move("vxReportMount",item));

    if(upload) upload.hidden = true;
    if(reportPanel) reportPanel.hidden = true;
    const hero = document.querySelector(".wrap > .hero");
    if(hero) hero.setAttribute("aria-hidden","true");
    document.body.classList.add("video-experience-enhanced");
    shell.hidden = false;
    state.mounted = true;
  }

  function stepIndex(view){
    return ({start:0,setup:1,processing:2,error:2,review:3,report:4})[view] ?? 0;
  }

  function setView(next, options={}){
    if(!views.has(next)) next = "start";
    if(state.view !== next && !["processing","error"].includes(state.view)) state.previousView = state.view;
    state.view = next;
    views.forEach((view,key) => { view.hidden = key !== next; });
    const activeIndex = stepIndex(next);
    steps.forEach((step,index) => {
      step.classList.toggle("active",index === activeIndex);
      step.classList.toggle("complete",index < activeIndex);
      if(index === activeIndex) step.setAttribute("aria-current","step");
      else step.removeAttribute("aria-current");
    });
    shell.dataset.state = next;
    if(!options.keepScroll) shell.scrollIntoView({block:"start",behavior:options.instant ? "auto" : "smooth"});
    updateChrome();
  }

  function projectTitle(){
    return safeProject().title || node("videoTitle")?.value.trim() || node("videoInput")?.files?.[0]?.name || "Analisi Video MatchIQ";
  }

  function counts(){
    return state.evidences.reduce((acc,item) => {
      const key = item.review_status || "pending";
      acc[key] = (acc[key] || 0) + 1;
      return acc;
    },{});
  }

  function updateChrome(){
    const title = projectTitle();
    const currentPipeline = pipeline();
    const evidenceCounts = counts();
    const reviewed = (evidenceCounts.confirmed || 0) + (evidenceCounts.corrected || 0) + (evidenceCounts.rejected || 0);
    if(node("vxProjectTitle")) node("vxProjectTitle").textContent = title;
    if(node("vxProjectMeta")) node("vxProjectMeta").textContent = `${state.mode === "coach" ? "Coach Mode" : "Analysis Mode"} · ${reviewed}/${state.evidences.length} evidenze revisionate`;
    if(node("vxProcessingTitle")) node("vxProcessingTitle").textContent = title;
    if(node("vxProcessingFile")){
      const file = node("videoInput")?.files?.[0]?.name;
      node("vxProcessingFile").textContent = file ? `${file} · Il progetto resta recuperabile dal Video Hub.` : "Il progetto resta recuperabile dal Video Hub anche se lasci questa pagina.";
    }
    const progress = Math.max(0,Math.min(100,Number(currentPipeline.progress || 0)));
    if(node("vxProcessingBar")) node("vxProcessingBar").style.width = `${progress}%`;
    if(node("vxProcessingPercent")) node("vxProcessingPercent").textContent = `${progress}%`;
    const stageLabels = {
      upload:"Caricamento",
      preparing:"Preparazione video",
      segmentation:"Segmentazione",
      frame_extraction:"Estrazione frame",
      frame_ranking:"Ranking frame",
      clip_generation:"Generazione clip",
      evidence_generation:"Preparazione evidenze",
      human_review:"Revisione staff",
      report:"Preparazione report",
      completed:"Completata"
    };
    const stage = text(currentPipeline.stage || "preparing");
    if(node("vxProcessingStage")) node("vxProcessingStage").textContent = stageLabels[stage] || stage.replace(/_/g," ");
    if(node("vxProcessingEvidenceCount")) node("vxProcessingEvidenceCount").textContent = String(state.evidences.length);
    renderProcessingActions();
    renderReportStats();
  }

  function renderProcessingActions(){
    const target = node("vxProcessingActions");
    if(!target) return;
    const status = pipeline().status || "draft";
    target.innerHTML = (status === "processing" || status === "queued")
      ? '<button class="btn dark" type="button" data-vx-action="cancel">Annulla elaborazione</button><button class="btn dark" type="button" data-vx-action="projects">Vai ai progetti</button>'
      : '<button class="btn dark" type="button" data-vx-action="projects">Vai ai progetti</button>';
  }

  function renderReportStats(){
    const target = node("vxReportStats");
    if(!target) return;
    const value = counts();
    const clips = state.evidences.filter(item => item.clip_reference).length;
    const frames = state.evidences.filter(item => Number.isFinite(Number(item.representative_timestamp_ms))).length;
    target.innerHTML = [
      ["Confermate",(value.confirmed || 0)],
      ["Corrette",(value.corrected || 0)],
      ["Pendenti",(value.pending || 0)],
      ["Frame / clip",`${frames} / ${clips}`]
    ].map(([label,value]) => `<div><span>${label}</span><strong>${value}</strong></div>`).join("");
  }

  function updateElapsed(){
    if(!state.processingStarted || state.view !== "processing") return;
    const seconds = Math.max(0,Math.round((Date.now() - state.processingStarted) / 1000));
    const minutes = String(Math.floor(seconds / 60)).padStart(2,"0");
    const rest = String(seconds % 60).padStart(2,"0");
    if(node("vxProcessingElapsed")) node("vxProcessingElapsed").textContent = `${minutes}:${rest}`;
  }

  function syncMode(mode){
    state.mode = mode === "coach" ? "coach" : "analysis";
    shell.querySelectorAll("[data-vx-mode]").forEach(button => button.classList.toggle("active",button.dataset.vxMode === state.mode));
    const original = document.querySelector(`[data-vi-mode="${state.mode}"]`);
    if(original && original.getAttribute("aria-pressed") !== "true") original.click();
  }

  function showProjects(){
    if(!projectDialog) return;
    if(typeof projectDialog.showModal === "function") projectDialog.showModal();
    else projectDialog.setAttribute("open","");
  }

  function closeProjects(){
    if(!projectDialog) return;
    if(typeof projectDialog.close === "function") projectDialog.close();
    else projectDialog.removeAttribute("open");
  }

  function setInputFiles(files){
    const input = node("videoInput");
    if(!input || !files?.length) return;
    try{
      const transfer = new DataTransfer();
      Array.from(files).slice(0,1).forEach(file => transfer.items.add(file));
      input.files = transfer.files;
      input.dispatchEvent(new Event("change",{bubbles:true}));
    }catch(err){
      input.click();
    }
  }

  async function startAnalysis(){
    const hint = node("vxSetupHint");
    try{
      if(!hasVideo() && state.mode !== "coach") throw new Error("Seleziona prima un video da analizzare.");
      state.processingStarted = Date.now();
      setView("processing");
      if(typeof extractedFrameTimes !== "undefined" && Array.isArray(extractedFrameTimes) && !extractedFrameTimes.length){
        if(typeof window.extractFrames === "function") await window.extractFrames();
      }
      if(!window.MatchIQVideoIntelligence?.runPipeline) throw new Error("Video Intelligence non e ancora disponibile.");
      await window.MatchIQVideoIntelligence.runPipeline();
    }catch(err){
      if(hint) hint.textContent = err.message || "Analisi non avviata.";
      if(!safeProject().pipeline || !["failed","cancelled"].includes(pipeline().status)) setView("setup");
    }
  }

  function openReport(){
    const button = node("viReportBtn");
    if(button && !button.disabled) button.click();
    window.setTimeout(() => setView("report"),180);
  }

  function applyExperienceState(detail={}){
    if(detail.project !== undefined) state.project = detail.project;
    if(Array.isArray(detail.evidences)) state.evidences = detail.evidences;
    if(detail.mode) state.mode = detail.mode;
    const status = pipeline().status || "draft";
    if(status === "queued" || status === "processing"){
      if(!state.processingStarted) state.processingStarted = Date.now();
      setView("processing",{keepScroll:true});
    }else if(status === "failed" || status === "cancelled"){
      const error = pipeline().error?.message || (status === "cancelled" ? "Elaborazione annullata. Puoi riprenderla dal progetto salvato." : "Elaborazione interrotta.");
      if(node("vxErrorMessage")) node("vxErrorMessage").textContent = error;
      if(node("vxErrorDetails")) node("vxErrorDetails").textContent = JSON.stringify(pipeline().error || {status,stage:pipeline().stage || "unknown"},null,2);
      if(node("vxRecoveryMissing")) node("vxRecoveryMissing").textContent = status === "cancelled"
        ? "Riavvio dell'elaborazione quando decidi tu"
        : `Ripresa dalla fase ${text(pipeline().stage || "interrotta").replace(/_/g," ")}`;
      setView("error",{keepScroll:true});
    }else if(status === "completed" && Array.isArray(safeProject().reports) && safeProject().reports.length){
      setView("report",{keepScroll:true});
    }else if(state.evidences.length || status === "review_ready"){
      setView("review",{keepScroll:true});
    }
    syncMode(state.mode);
    updateChrome();
  }

  shell.addEventListener("click",event => {
    const mode = event.target.closest("[data-vx-mode]");
    if(mode){ syncMode(mode.dataset.vxMode); if(mode.dataset.vxMode === "coach") setView("setup"); return; }
    const button = event.target.closest("[data-vx-action]");
    if(!button) return;
    const action = button.dataset.vxAction;
    if(action === "projects") showProjects();
    if(action === "close-projects") closeProjects();
    if(action === "start") setView("start");
    if(action === "setup" || action === "settings") setView("setup");
    if(action === "review") setView("review");
    if(action === "report") openReport();
    if(action === "pending"){
      if(node("viStatusFilter")) node("viStatusFilter").value = "pending";
      node("viStatusFilter")?.dispatchEvent(new Event("change",{bubbles:true}));
      setView("review");
    }
    if(action === "download") node("downloadPdfBtn")?.click();
    if(action === "retry") node("viProjectState")?.querySelector('[data-project-action="retry"]')?.click();
    if(action === "cancel") node("viProjectState")?.querySelector('[data-project-action="cancel"]')?.click();
  });

  const dropzone = node("vxUploadDropzone");
  dropzone?.addEventListener("click",event => { if(!event.target.closest("button,input")) node("videoInput")?.click(); });
  dropzone?.addEventListener("keydown",event => { if(event.key === "Enter" || event.key === " "){ event.preventDefault(); node("videoInput")?.click(); } });
  ["dragenter","dragover"].forEach(type => dropzone?.addEventListener(type,event => { event.preventDefault(); dropzone.classList.add("dragover"); }));
  ["dragleave","drop"].forEach(type => dropzone?.addEventListener(type,event => { event.preventDefault(); dropzone.classList.remove("dragover"); }));
  dropzone?.addEventListener("drop",event => setInputFiles(event.dataTransfer?.files));
  node("vxSelectVideoBtn")?.addEventListener("click",() => node("videoInput")?.click());
  node("vxStartAnalysisBtn")?.addEventListener("click",startAnalysis);
  node("videoInput")?.addEventListener("change",() => {
    updateSelectedFile();
    if(node("videoInput")?.files?.length) setView("setup");
  });
  projectDialog?.addEventListener("click",event => { if(event.target === projectDialog) closeProjects(); });
  document.addEventListener("matchiq:video-experience",event => applyExperienceState(event.detail || {}));

  mountExistingExperience();
  updateSelectedFile();
  syncMode("analysis");
  setView(hasVideo() ? "setup" : "start",{instant:true,keepScroll:true});
  state.elapsedTimer = window.setInterval(updateElapsed,1000);
  updateChrome();
  window.MatchIQVideoExperience = {setView,showProjects,applyExperienceState};
})();
