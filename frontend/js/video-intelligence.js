(function(){
  const setup = document.getElementById("videoIntelligenceSetup");
  const workspace = document.getElementById("videoEvidenceWorkspace");
  if(!setup || !workspace) return;

  const state = {
    mode: "analysis",
    project: null,
    evidences: [],
    matches: [],
    halftimeAvailable: false,
    halftimeAnalysis: null,
    busy: false,
    clipStopHandler: null
  };

  const elements = {
    modeButtons: Array.from(setup.querySelectorAll("[data-vi-mode]")),
    coachField: document.getElementById("viCoachMatchField"),
    coachMatch: document.getElementById("viCoachMatch"),
    videoType: document.getElementById("viVideoType"),
    period: document.getElementById("viPeriod"),
    perspective: document.getElementById("viPerspective"),
    prepare: document.getElementById("viPrepareBtn"),
    run: document.getElementById("viRunBtn"),
    halftime: document.getElementById("viHalftimeBtn"),
    refresh: document.getElementById("viRefreshBtn"),
    projectState: document.getElementById("viProjectState"),
    stats: document.getElementById("viEvidenceStats"),
    statusFilter: document.getElementById("viStatusFilter"),
    phaseFilter: document.getElementById("viPhaseFilter"),
    pending: document.getElementById("viPendingBtn"),
    confirmVisible: document.getElementById("viConfirmVisibleBtn"),
    report: document.getElementById("viReportBtn"),
    list: document.getElementById("viEvidenceList"),
    halftimePanel: document.getElementById("viHalftimePanel"),
    halftimeSummary: document.getElementById("viHalftimeSummary"),
    halftimeList: document.getElementById("viHalftimeList"),
    halftimeVerify: document.getElementById("viHalftimeVerify")
  };

  function html(value){
    return String(value == null ? "" : value)
      .replace(/&/g,"&amp;")
      .replace(/</g,"&lt;")
      .replace(/>/g,"&gt;")
      .replace(/"/g,"&quot;")
      .replace(/'/g,"&#039;");
  }

  function authJsonHeaders(){
    if(typeof apiHeaders === "function") return apiHeaders();
    const token = localStorage.getItem("matchiq_auth_token") || sessionStorage.getItem("matchiq_auth_token") || "";
    return {
      "Accept":"application/json",
      "Content-Type":"application/json",
      ...(token ? {"Authorization":`Bearer ${token}`} : {})
    };
  }

  async function request(path, options={}){
    const response = await fetch(`${window.location.origin}/api/video/intelligence${path}`, {
      ...options,
      headers: authJsonHeaders()
    });
    let payload = {};
    try{ payload = await response.json(); }catch(err){}
    if(!response.ok || payload.ok === false){
      const detail = payload && payload.detail;
      throw new Error(typeof detail === "string" ? detail : (detail?.message || payload.message || "Operazione Video Intelligence non riuscita"));
    }
    return payload;
  }

  function notify(message, type="ok"){
    if(typeof showStatus === "function") showStatus(message, type);
  }

  function assetId(){
    return Number(typeof currentVideoAssetId !== "undefined" ? currentVideoAssetId : 0) || 0;
  }

  function secondsLabel(milliseconds){
    const seconds = Math.max(0, Math.round(Number(milliseconds || 0) / 1000));
    if(typeof formatTime === "function") return formatTime(seconds);
    const minutes = String(Math.floor(seconds / 60)).padStart(2,"0");
    return `${minutes}:${String(seconds % 60).padStart(2,"0")}`;
  }

  function phaseLabel(value){
    const labels = {
      build_up:"Costruzione dal basso",
      offensive_phase:"Fase offensiva",
      defensive_phase:"Fase difensiva",
      transition:"Transizione",
      pressing:"Pressing",
      set_piece:"Palla inattiva",
      set_piece_offensive:"Palla inattiva offensiva",
      set_piece_defensive:"Palla inattiva difensiva",
      corner_offensive:"Calcio d'angolo offensivo",
      corner_defensive:"Calcio d'angolo difensivo",
      throw_in_offensive:"Rimessa laterale offensiva",
      throw_in_defensive:"Rimessa laterale difensiva",
      free_kick_offensive:"Punizione offensiva",
      free_kick_defensive:"Punizione difensiva",
      unclassified:"Da classificare"
    };
    return labels[value] || String(value || "Da classificare").replace(/_/g," ");
  }

  function reviewLabel(value){
    return ({pending:"Da revisionare",confirmed:"Confermata",corrected:"Corretta",rejected:"Scartata"})[value] || value;
  }

  function setBusy(busy){
    state.busy = busy;
    [elements.prepare,elements.run,elements.halftime,elements.refresh,elements.confirmVisible,elements.report].forEach(button => {
      if(button) button.disabled = busy;
    });
    updateHalftimeAvailability();
  }

  function renderProjectState(){
    const pipeline = state.project?.pipeline || {};
    const progress = Math.max(0, Math.min(100, Number(pipeline.progress || 0)));
    const status = pipeline.status || "draft";
    const labels = {
      draft:"Progetto pronto",
      queued:"In coda",
      processing:"Analisi in corso",
      review_ready:"Revisione richiesta",
      completed:"Report completato",
      failed:"Analisi interrotta",
      cancelled:"Analisi annullata"
    };
    if(!state.project){
      elements.projectState.innerHTML = `<b>Non avviato</b><span>Prepara il progetto dopo aver scelto il contesto.</span><div class="vi-progress" aria-hidden="true"><span></span></div>`;
      return;
    }
    const error = pipeline.error?.message || "";
    elements.projectState.innerHTML = `
      <b>${html(labels[status] || status)}</b>
      <span>${html(error || `${pipeline.stage || "project"} · ${progress}%`)}</span>
      <div class="vi-progress" aria-label="Avanzamento ${progress}%"><span style="width:${progress}%"></span></div>
    `;
  }

  async function loadCoachMatches(){
    try{
      const payload = await request("/coach-matches");
      state.matches = Array.isArray(payload.matches) ? payload.matches : [];
      elements.coachMatch.innerHTML = `<option value="">Seleziona partita</option>` + state.matches.map(item => {
        const label = [item.home,item.away].filter(Boolean).join(" - ") || `Partita ${item.id}`;
        return `<option value="${html(item.id || item.match_id)}">${html(label)}</option>`;
      }).join("");
    }catch(err){
      state.matches = [];
      elements.coachMatch.innerHTML = `<option value="">Nessuna partita disponibile</option>`;
    }
  }

  async function loadHalftimeConfig(){
    try{
      const payload = await request("/halftime/config");
      state.halftimeAvailable = payload.available === true;
    }catch(err){
      state.halftimeAvailable = false;
    }
    updateHalftimeAvailability();
  }

  function updateHalftimeAvailability(){
    if(!elements.halftime) return;
    const firstHalf = elements.period.value === "first_half";
    elements.halftime.hidden = !state.halftimeAvailable;
    elements.halftime.disabled = state.busy || !firstHalf;
    elements.halftime.title = firstHalf ? "" : "Seleziona Primo tempo per usare il beta intervallo";
  }

  function setMode(mode){
    state.mode = mode === "coach" ? "coach" : "analysis";
    elements.modeButtons.forEach(button => {
      const active = button.dataset.viMode === state.mode;
      button.classList.toggle("active", active);
      button.setAttribute("aria-pressed", String(active));
    });
    elements.coachField.hidden = state.mode !== "coach";
    if(state.mode === "coach" && !state.matches.length) loadCoachMatches();
  }

  function projectPayload(){
    const matchId = elements.coachMatch.value || null;
    const observed = document.getElementById("observedTeam")?.value.trim() || document.getElementById("clubName")?.value.trim() || "";
    const home = document.getElementById("homeTeamName")?.value.trim() || "";
    const away = document.getElementById("awayTeamName")?.value.trim() || "";
    return {
      video_asset_id: assetId() || null,
      analysis_mode: state.mode,
      title: document.getElementById("videoTitle")?.value.trim() || "Analisi Video MatchIQ",
      observed_team: observed,
      opponent: state.mode === "coach" ? "" : away,
      video_type: elements.videoType.value,
      period: elements.period.value,
      perspective: elements.perspective.value,
      notes: document.getElementById("videoNotes")?.value.trim() || "",
      match_id: state.mode === "coach" ? matchId : null,
      context: {
        focus: document.getElementById("videoFocus")?.value || "",
        home_team: home,
        away_team: away,
        home_formation: document.getElementById("homeFormation")?.value.trim() || "",
        away_formation: document.getElementById("awayFormation")?.value.trim() || ""
      }
    };
  }

  async function prepareProject(force=false){
    if(state.mode === "coach" && !elements.coachMatch.value){
      throw new Error("Seleziona la partita Coach da collegare all'analisi");
    }
    if(state.project && Number(state.project.video_asset_id) === assetId() && !force) return state.project;
    if(assetId() && !force){
      try{
        const existing = await request(`/projects/${assetId()}`);
        state.project = existing.project;
        state.evidences = Array.isArray(state.project.evidences) ? state.project.evidences : [];
        renderProjectState();
        renderWorkspace();
        workspace.hidden = false;
        return state.project;
      }catch(err){
        if(!/non trovato/i.test(err.message)) throw err;
      }
    }
    const payload = await request("/projects", {method:"POST", body:JSON.stringify(projectPayload())});
    state.project = payload.project;
    if(typeof currentVideoAssetId !== "undefined") currentVideoAssetId = Number(state.project.video_asset_id) || currentVideoAssetId;
    renderProjectState();
    workspace.hidden = false;
    return state.project;
  }

  function pipelinePayload(){
    const times = typeof extractedFrameTimes !== "undefined" && Array.isArray(extractedFrameTimes) ? extractedFrameTimes : [];
    const meta = typeof extractedFrameMeta !== "undefined" && Array.isArray(extractedFrameMeta) ? extractedFrameMeta : [];
    const alternatives = typeof candidateFrameResults !== "undefined" && Array.isArray(candidateFrameResults) ? candidateFrameResults : [];
    const candidates = [];

    times.forEach((seconds,index) => {
      const timestampMs = Math.max(0,Math.round(Number(seconds || 0) * 1000));
      candidates.push({
        timestamp_ms:timestampMs,
        frame_index:index,
        candidate_role:"primary",
        frame_meta:{
          ...(meta[index] && typeof meta[index] === "object" ? meta[index] : {}),
          candidate_role:"primary"
        }
      });
    });

    alternatives.forEach((item,index) => {
      const timestampMs = Math.max(0,Math.round(Number(item?.time || 0) * 1000));
      if(candidates.some(candidate => Math.abs(candidate.timestamp_ms - timestampMs) < 450)) return;
      candidates.push({
        timestamp_ms:timestampMs,
        frame_index:times.length + index,
        candidate_role:"alternative",
        frame_meta:{
          ...(item?.meta && typeof item.meta === "object" ? item.meta : {}),
          candidate_role:"alternative"
        }
      });
    });

    candidates.sort((left,right) => left.timestamp_ms - right.timestamp_ms || left.frame_index - right.frame_index);
    const candidateKey = candidates.map(item => `${item.timestamp_ms}:${item.candidate_role}`).join("-");
    return {
      idempotency_key: `vi-${assetId()}-${candidateKey}-${document.getElementById("videoFocus")?.value || "focus"}`,
      duration_seconds: Number(document.getElementById("videoPreview")?.duration || 0),
      frame_times_ms: candidates.map(item => item.timestamp_ms),
      frame_meta: candidates.map(item => ({
        ...item.frame_meta,
        frame_index:item.frame_index,
        timestamp_ms:item.timestamp_ms,
        candidate_role:item.candidate_role
      })),
      staff_events: []
    };
  }

  async function runPipeline(){
    const payload = pipelinePayload();
    if(!payload.frame_times_ms.length) throw new Error("Estrai prima i fotogrammi reali dal video");
    await prepareProject();
    const response = await request(`/projects/${assetId()}/pipeline`, {method:"POST", body:JSON.stringify(payload)});
    state.project = response.project;
    state.evidences = Array.isArray(state.project.evidences) ? state.project.evidences : [];
    state.halftimeAnalysis = null;
    renderProjectState();
    renderWorkspace();
    renderHalftimeAnalysis();
    workspace.hidden = false;
    workspace.scrollIntoView({behavior:"smooth",block:"start"});
  }

  async function loadProject(options={}){
    const id = assetId();
    if(!id){
      if(!options.quiet) notify("Prepara prima un progetto Video Intelligence.","warn");
      return;
    }
    try{
      const payload = await request(`/projects/${id}`);
      state.project = payload.project;
      state.mode = state.project.analysis_mode || "analysis";
      setMode(state.mode);
      if(state.project.match_id) elements.coachMatch.value = String(state.project.match_id);
      state.evidences = Array.isArray(state.project.evidences) ? state.project.evidences : [];
      const halftimeRuns = Array.isArray(state.project.halftime_runs) ? state.project.halftime_runs : [];
      state.halftimeAnalysis = halftimeRuns.length ? halftimeRuns[halftimeRuns.length - 1] : null;
      renderProjectState();
      renderWorkspace();
      renderHalftimeAnalysis();
      workspace.hidden = false;
    }catch(err){
      state.project = null;
      state.evidences = [];
      state.halftimeAnalysis = null;
      renderProjectState();
      renderHalftimeAnalysis();
      workspace.hidden = true;
      if(!options.quiet && !/non trovato/i.test(err.message)) notify(err.message,"warn");
    }
  }

  function filteredEvidences(){
    const status = elements.statusFilter.value;
    const phase = elements.phaseFilter.value;
    return state.evidences.filter(item => {
      return (status === "all" || item.review_status === status) && (phase === "all" || item.phase_type === phase);
    });
  }

  function frameOptions(selectedMs){
    const times = typeof extractedFrameTimes !== "undefined" && Array.isArray(extractedFrameTimes) ? extractedFrameTimes : [];
    if(!times.length) return `<option value="">Nessun frame estratto</option>`;
    return times.map((seconds,index) => {
      const value = Math.round(Number(seconds || 0) * 1000);
      return `<option value="${value}"${Math.abs(value - Number(selectedMs || 0)) < 750 ? " selected" : ""}>Frame ${index + 1} · ${html(secondsLabel(value))}</option>`;
    }).join("");
  }

  function renderStats(){
    const counts = state.evidences.reduce((acc,item) => {
      acc[item.review_status] = (acc[item.review_status] || 0) + 1;
      return acc;
    },{});
    elements.stats.innerHTML = [
      ["Evidenze",state.evidences.length],
      ["Da revisionare",counts.pending || 0],
      ["Confermate",(counts.confirmed || 0) + (counts.corrected || 0)],
      ["Scartate",counts.rejected || 0]
    ].map(([label,value]) => `<div class="vi-stat"><span>${label}</span><strong>${value}</strong></div>`).join("");
  }

  function renderPhaseFilter(){
    const current = elements.phaseFilter.value || "all";
    const phases = Array.from(new Set(state.evidences.map(item => item.phase_type).filter(Boolean))).sort();
    elements.phaseFilter.innerHTML = `<option value="all">Tutte le fasi</option>` + phases.map(value => `<option value="${html(value)}">${html(phaseLabel(value))}</option>`).join("");
    elements.phaseFilter.value = phases.includes(current) ? current : "all";
  }

  function renderWorkspace(){
    renderStats();
    renderPhaseFilter();
    const items = filteredEvidences();
    if(!items.length){
      elements.list.innerHTML = `<div class="vi-empty">Nessuna evidenza per i filtri scelti. Avvia l'analisi oppure cambia filtro.</div>`;
      return;
    }
    elements.list.innerHTML = items.map(item => {
      const clip = item.clip_reference || {};
      const start = Number(clip.start_timestamp_ms ?? item.start_timestamp_ms ?? 0) / 1000;
      const end = Number(clip.end_timestamp_ms ?? item.end_timestamp_ms ?? 0) / 1000;
      const confidence = Math.round(Number(item.confidence_score || 0) * (Number(item.confidence_score || 0) <= 1 ? 100 : 1));
      return `
        <article class="vi-evidence ${html(item.review_status)}" data-evidence-id="${html(item.evidence_id)}">
          <div class="vi-evidence-top">
            <div>
              <div class="vi-chip-row">
                <span class="vi-chip ${html(item.review_status)}">${html(reviewLabel(item.review_status))}</span>
                <span class="vi-chip">${html(phaseLabel(item.phase_type))}</span>
                <span class="vi-chip">${html(secondsLabel(item.representative_timestamp_ms))}</span>
              </div>
              <h4>${html(item.title)}</h4>
              <p>${html(item.motivation || "Proposta generata dai segnali disponibili nel video.")}</p>
            </div>
            <div class="vi-card-actions">
              <button class="btn dark small" type="button" data-action="open">Apri momento</button>
              <button class="btn dark small" type="button" data-action="play">Riproduci clip</button>
            </div>
          </div>
          <div class="vi-evidence-copy">
            <label>Titolo<input data-field="title" value="${html(item.title)}"></label>
            <label>Fase<input data-field="phase_type" value="${html(item.phase_type || "unclassified")}"></label>
            <label class="full">Osservazione<textarea data-field="observation">${html(item.observation || "")}</textarea></label>
            <label class="full">Interpretazione<textarea data-field="interpretation">${html(item.interpretation || "")}</textarea></label>
          </div>
          <div class="vi-evidence-meta">
            <div>Affidabilità<strong>${confidence}% · ${html(item.confidence_label || "")}</strong></div>
            <div>Fonte<strong>${html(item.source_type || "video")}</strong></div>
            <div>Collegamento Coach<strong>${html(item.linked_match_event_id || item.linked_note_id || "Nessuno")}</strong></div>
          </div>
          <div class="vi-editors">
            <div class="vi-clip-editor">
              <label>Inizio clip<input type="number" min="0" step="1" data-field="clip_start" value="${Math.max(0,Math.round(start))}"></label>
              <label>Fine clip<input type="number" min="0" step="1" data-field="clip_end" value="${Math.max(0,Math.round(end))}"></label>
              <button class="btn dark small" type="button" data-action="save-clip">Salva clip</button>
            </div>
            <div class="vi-frame-editor">
              <label>Frame rappresentativo<select data-field="frame_timestamp">${frameOptions(item.representative_timestamp_ms)}</select></label>
              <button class="btn dark small" type="button" data-action="save-frame">Sostituisci frame</button>
            </div>
          </div>
          <div class="vi-card-actions">
            <button class="btn small" type="button" data-action="confirm">Conferma</button>
            <button class="btn dark small" type="button" data-action="correct">Salva correzione</button>
            <button class="btn dark small" type="button" data-action="reject">Scarta</button>
          </div>
        </article>
      `;
    }).join("");
  }

  function renderHalftimeAnalysis(){
    const analysis = state.halftimeAnalysis;
    if(!analysis){
      elements.halftimePanel.hidden = true;
      return;
    }
    const facts = Array.isArray(analysis.facts) ? analysis.facts : [];
    elements.halftimePanel.hidden = false;
    elements.halftimeSummary.textContent = analysis.summary || "Momenti prioritari del primo tempo.";
    elements.halftimeList.innerHTML = facts.map(item => `
      <article class="vi-halftime-item">
        <div class="vi-chip-row">
          <span class="vi-chip">${html(item.timecode || "00:00")}</span>
          <span class="vi-chip ${item.requires_staff_verification ? "pending" : ""}">${item.requires_staff_verification ? "Da verificare" : "Verificata"}</span>
        </div>
        <h5>${html(item.title || "Evidenza video")}</h5>
        <p>${html(item.observation || "")}</p>
        <button class="btn dark small" type="button" data-halftime-evidence="${html(item.evidence_id)}">Apri momento</button>
      </article>
    `).join("") || `<div class="vi-empty">Nessuna evidenza disponibile per l'intervallo.</div>`;
    const verify = Array.isArray(analysis.points_to_verify) ? analysis.points_to_verify : [];
    elements.halftimeVerify.innerHTML = verify.length
      ? `<strong>Punti da verificare</strong><ul>${verify.map(item => `<li>${html(item)}</li>`).join("")}</ul>`
      : `<strong>Tutte le evidenze selezionate sono già state verificate dallo staff.</strong>`;
  }

  async function generateHalftimeAnalysis(){
    if(elements.period.value !== "first_half") throw new Error("Seleziona Primo tempo prima di avviare l'analisi intervallo");
    await prepareProject();
    const payload = await request(`/projects/${assetId()}/halftime`, {
      method:"POST",
      body:JSON.stringify({max_evidences:5})
    });
    state.halftimeAnalysis = payload.analysis || null;
    renderHalftimeAnalysis();
    elements.halftimePanel.scrollIntoView({behavior:"smooth",block:"start"});
  }

  function evidenceCard(id){
    return elements.list.querySelector(`[data-evidence-id="${CSS.escape(String(id))}"]`);
  }

  function cardValue(card, field){
    return card?.querySelector(`[data-field="${field}"]`)?.value || "";
  }

  async function reviewEvidence(id, status){
    const card = evidenceCard(id);
    const body = {status};
    if(status === "corrected"){
      body.title = cardValue(card,"title").trim();
      body.phase_type = cardValue(card,"phase_type").trim() || "unclassified";
      body.observation = cardValue(card,"observation").trim();
      body.interpretation = cardValue(card,"interpretation").trim() || null;
      body.user_correction = "Contenuto revisionato manualmente dallo staff";
    }
    const payload = await request(`/projects/${assetId()}/evidences/${encodeURIComponent(id)}/review`, {method:"PATCH",body:JSON.stringify(body)});
    const index = state.evidences.findIndex(item => item.evidence_id === id);
    if(index >= 0) state.evidences[index] = payload.evidence;
    renderWorkspace();
  }

  async function saveClip(id){
    const card = evidenceCard(id);
    const start = Math.max(0,Number(cardValue(card,"clip_start") || 0));
    const end = Math.max(0,Number(cardValue(card,"clip_end") || 0));
    if(end <= start) throw new Error("La fine del clip deve essere successiva all'inizio");
    const payload = await request(`/projects/${assetId()}/evidences/${encodeURIComponent(id)}/clip`, {
      method:"POST",
      body:JSON.stringify({start_timestamp_ms:Math.round(start*1000),end_timestamp_ms:Math.round(end*1000)})
    });
    const index = state.evidences.findIndex(item => item.evidence_id === id);
    if(index >= 0) state.evidences[index] = payload.evidence;
    renderWorkspace();
  }

  async function saveFrame(id){
    const card = evidenceCard(id);
    const timestamp = Number(cardValue(card,"frame_timestamp"));
    if(!Number.isFinite(timestamp)) throw new Error("Seleziona un frame reale estratto dal video");
    const times = typeof extractedFrameTimes !== "undefined" && Array.isArray(extractedFrameTimes) ? extractedFrameTimes : [];
    const frameIndex = times.findIndex(value => Math.abs(Number(value)*1000 - timestamp) < 750);
    const payload = await request(`/projects/${assetId()}/evidences/${encodeURIComponent(id)}/frame`, {
      method:"POST",
      body:JSON.stringify({representative_timestamp_ms:timestamp,frame_index:frameIndex >= 0 ? frameIndex : null,motivation:"Frame scelto manualmente dallo staff"})
    });
    const index = state.evidences.findIndex(item => item.evidence_id === id);
    if(index >= 0) state.evidences[index] = payload.evidence;
    renderWorkspace();
  }

  async function openMoment(item, playClip=false){
    const video = document.getElementById("videoPreview");
    if(!video?.src) throw new Error("Apri prima il video collegato alla sessione");
    const clip = item.clip_reference || {};
    const targetMs = playClip ? Number(clip.start_timestamp_ms ?? item.start_timestamp_ms ?? 0) : Number(item.representative_timestamp_ms || 0);
    const endMs = Number(clip.end_timestamp_ms ?? item.end_timestamp_ms ?? targetMs + 10000);
    video.pause();
    if(typeof seekVideo === "function") await seekVideo(video,targetMs/1000);
    else video.currentTime = targetMs/1000;
    video.scrollIntoView({behavior:"smooth",block:"center"});
    if(playClip){
      if(state.clipStopHandler) video.removeEventListener("timeupdate",state.clipStopHandler);
      state.clipStopHandler = () => {
        if(video.currentTime * 1000 >= endMs){
          video.pause();
          video.removeEventListener("timeupdate",state.clipStopHandler);
          state.clipStopHandler = null;
        }
      };
      video.addEventListener("timeupdate",state.clipStopHandler);
      await video.play();
    }
  }

  async function confirmVisible(){
    const pending = filteredEvidences().filter(item => item.review_status === "pending");
    if(!pending.length) throw new Error("Non ci sono evidenze visibili da confermare");
    for(const item of pending) await reviewEvidence(item.evidence_id,"confirmed");
  }

  async function generateReport(){
    const payload = await request(`/projects/${assetId()}/reports`, {
      method:"POST",
      body:JSON.stringify({title:document.getElementById("videoTitle")?.value.trim() || "Report tecnico Video Intelligence",include_pending_appendix:true})
    });
    state.project = (await request(`/projects/${assetId()}`)).project;
    renderProjectState();
    const report = payload.report || {};
    const findings = (report.sections || []).flatMap(section => section.findings || []);
    const text = [
      report.title || "Report tecnico Video Intelligence",
      report.evidence_policy || "",
      ...findings.map(item => `${item.timecode} · ${item.title}\n${item.observation}${item.interpretation ? `\nLettura: ${item.interpretation}` : ""}`),
      ...(report.limitations || []).map(item => `Limite: ${item}`)
    ].filter(Boolean).join("\n\n");
    const target = document.getElementById("reportBox");
    if(target) target.textContent = text;
    if(typeof updateReportMeta === "function") updateReportMeta("report",findings.length);
  }

  async function guarded(action, successMessage){
    if(state.busy) return;
    setBusy(true);
    try{
      await action();
      if(successMessage) notify(successMessage,"ok");
    }catch(err){
      notify(err.message || "Operazione non completata","err");
    }finally{
      setBusy(false);
    }
  }

  elements.modeButtons.forEach(button => button.addEventListener("click",() => setMode(button.dataset.viMode)));
  elements.prepare.addEventListener("click",() => guarded(async() => {
    await prepareProject(false);
    await loadProject();
  },"Progetto Video Intelligence pronto."));
  elements.run.addEventListener("click",() => guarded(runPipeline,"Analisi completata. Revisiona le evidenze proposte."));
  elements.halftime?.addEventListener("click",() => guarded(generateHalftimeAnalysis,"Analisi intervallo pronta per la verifica dello staff."));
  elements.refresh.addEventListener("click",() => guarded(() => loadProject(),"Evidenze aggiornate."));
  elements.period.addEventListener("change",updateHalftimeAvailability);
  elements.statusFilter.addEventListener("change",renderWorkspace);
  elements.phaseFilter.addEventListener("change",renderWorkspace);
  elements.pending.addEventListener("click",() => {elements.statusFilter.value="pending";renderWorkspace();});
  elements.confirmVisible.addEventListener("click",() => guarded(confirmVisible,"Evidenze visibili confermate."));
  elements.report.addEventListener("click",() => guarded(generateReport,"Report basato sulle evidenze confermate."));

  elements.list.addEventListener("click",event => {
    const button = event.target.closest("[data-action]");
    const card = event.target.closest("[data-evidence-id]");
    if(!button || !card) return;
    const id = card.dataset.evidenceId;
    const item = state.evidences.find(entry => entry.evidence_id === id);
    if(!item) return;
    const action = button.dataset.action;
    if(action === "open") guarded(() => openMoment(item,false));
    if(action === "play") guarded(() => openMoment(item,true));
    if(action === "confirm") guarded(() => reviewEvidence(id,"confirmed"),"Evidenza confermata.");
    if(action === "correct") guarded(() => reviewEvidence(id,"corrected"),"Correzione salvata.");
    if(action === "reject") guarded(() => reviewEvidence(id,"rejected"),"Evidenza esclusa dal report.");
    if(action === "save-clip") guarded(() => saveClip(id),"Intervallo clip aggiornato.");
    if(action === "save-frame") guarded(() => saveFrame(id),"Frame rappresentativo aggiornato.");
  });

  elements.halftimeList?.addEventListener("click",event => {
    const button = event.target.closest("[data-halftime-evidence]");
    if(!button) return;
    const item = state.evidences.find(entry => entry.evidence_id === button.dataset.halftimeEvidence);
    if(item) guarded(() => openMoment(item,false));
  });

  const legacyExtractFrames = window.extractFrames;
  if(typeof legacyExtractFrames === "function"){
    window.extractFrames = async function(){
      const result = await legacyExtractFrames.apply(this,arguments);
      if(Array.isArray(extractedFrameTimes) && extractedFrameTimes.length){
        notify("Fotogrammi pronti. Ora puoi avviare Video Intelligence.","ok");
      }
      return result;
    };
  }

  const legacyOpenLibraryVideo = window.openLibraryVideo;
  if(typeof legacyOpenLibraryVideo === "function"){
    window.openLibraryVideo = async function(){
      const result = await legacyOpenLibraryVideo.apply(this,arguments);
      await loadProject({quiet:true});
      return result;
    };
  }

  document.getElementById("videoInput")?.addEventListener("change",() => {
    state.project = null;
    state.evidences = [];
    state.halftimeAnalysis = null;
    workspace.hidden = true;
    renderHalftimeAnalysis();
    renderProjectState();
  });

  setMode("analysis");
  renderProjectState();
  loadHalftimeConfig();
  window.MatchIQVideoIntelligence = {loadProject,runPipeline,prepareProject};
})();
