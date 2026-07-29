(function(){
  const T=window.MatchIQTraining;
  const $=id=>document.getElementById(id);
  const el=(tag,text,className)=>{
    const node=document.createElement(tag);
    if(text!=null)node.textContent=text;
    if(className)node.className=className;
    return node;
  };
  const BLOCK_LABELS={
    activation:"Attivazione",
    technique:"Tecnica",
    situational:"Situazionale",
    position_game:"Gioco di posizione",
    themed_match:"Partita a tema",
    cooldown:"Defaticamento"
  };

  T.escape=value=>String(value||"").replace(
    /[&<>"']/g,
    char=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[char])
  );

  T.notice=(text,error=false)=>{
    const box=$("trainingNotice");
    box.textContent=text;
    box.style.borderColor=error?"#ff5678":"";
  };

  T.applyTeamProfile=profile=>{
    const values={
      category:profile.category||"Dilettanti",
      teamLevel:profile.level||"",
      averageAge:profile.average_age??"",
      players:profile.player_count||18,
      keepers:profile.goalkeeper_count??2,
      duration:profile.training_duration||90,
      matchDay:profile.match_day||"",
      intensity:profile.average_intensity||"media",
      pitchType:profile.pitch_type||"",
      pitchDimensions:profile.pitch_dimensions||"",
      availableMaterials:(profile.available_materials||[]).join(", "),
      preferredFormation:profile.preferred_formation||"",
      playingPrinciples:(profile.playing_principles||[]).join(", "),
      seasonObjectives:(profile.season_objectives||[]).join(", ")
    };
    Object.entries(values).forEach(([id,value])=>{
      const input=$(id);
      if(input)input.value=value;
    });
    const selected=new Set(profile.training_days||[]);
    document.querySelectorAll('input[name="day"]').forEach(input=>{
      input.checked=selected.has(input.value);
    });
    const complete=[
      profile.category,profile.level,profile.player_count,
      profile.training_duration,profile.match_day
    ].filter(Boolean).length;
    $("profileStatus").textContent=complete>=4?"Profilo operativo":"Profilo da completare";
  };

  T.renderLibraryControls=()=>{
    const sessionSelect=$("exerciseSession");
    const exerciseSelect=$("exerciseLibrary");
    if(!sessionSelect||!exerciseSelect)return;
    sessionSelect.replaceChildren();
    exerciseSelect.replaceChildren();
    (T.state.plan?.current_plan?.sessions||[]).forEach((session,index)=>{
      const option=el("option",session.title||session.objective||`Seduta ${index+1}`);
      option.value=String(index);
      sessionSelect.append(option);
    });
    (T.state.library||[]).forEach(item=>{
      const option=el("option",`${item.title} · ${item.tactical_theme}`);
      option.value=item.id;
      exerciseSelect.append(option);
    });
    $("addExercise").disabled=!sessionSelect.options.length||!exerciseSelect.options.length;
  };

  function renderExplainability(current){
    const chain=$("explainabilityChain");
    chain.replaceChildren();
    const labels=current.explainability?.chain||["Pattern","Priorità","Decisione","Seduta"];
    labels.forEach((label,index)=>{
      chain.append(el("span",label,"chain-step"));
      if(index<labels.length-1)chain.append(el("span","→","chain-arrow"));
    });
    const calendar=current.calendar_context||{};
    const context=el("span",null,"calendar-context");
    const distance=calendar.days_to_match?` · -${calendar.days_to_match} dalla gara`:"";
    context.textContent=`${calendar.training_day||"Da programmare"}${distance} · ${calendar.load_strategy||"carico da definire"}`;
    chain.append(context);
  }

  function renderDecisions(current){
    const container=$("decisionList");
    container.replaceChildren();
    (current.decisions||[]).forEach(item=>{
      const deferred=item.status==="DEFERRED";
      const card=el("article",null,`decision ${deferred?"deferred":"scheduled"}`);
      card.append(
        el("span",deferred?"RINVIATA":"INSERITA","decision-status"),
        el("strong",item.title||item.topic||"Priorità"),
        el("p",item.reason)
      );
      container.append(card);
    });
  }

  function renderPriorities(current){
    const priorities=$("priorityList");
    priorities.replaceChildren();
    (current.priorities||[]).forEach((item,index)=>{
      const card=el("article",null,"priority");
      card.append(
        el("span",`PRIORITÀ ${index+1}`,"eyebrow"),
        el("h3",item.title),
        el("p",item.reason),
        el("strong",`Affidabilità ${item.reliability}`)
      );
      const sources=el("div",null,"sources");
      (item.sources||[]).forEach(source=>{
        sources.append(el("span",`${source.module}: ${source.label} (${source.count})`,"source"));
      });
      card.append(sources);
      priorities.append(card);
    });
  }

  function renderDrill(drill,drillIndex,current,session){
    const box=el("div",null,"drill");
    box.dataset.drill=drillIndex;
    box.innerHTML=`
      <div class="drill-head">
        <div><span class="library-badge">LIBRERIA MATCHIQ</span><h4>${T.escape(drill.title)}</h4></div>
        <button type="button" class="remove-drill" data-remove-drill="${drillIndex}" aria-label="Rimuovi ${T.escape(drill.title)}">Rimuovi</button>
      </div>
      <p>${T.escape(drill.description)}</p>
      <div class="drill-grid">
        <label>Durata<input data-drill-field="selected_duration" type="number" min="5" max="60" value="${Number(drill.selected_duration||drill.duration)}"></label>
        <label>Giocatori<input data-drill-field="players" type="number" min="4" max="40" value="${Number(drill.players||18)}"></label>
        <label>Campo<input data-drill-field="field_dimensions" value="${T.escape(drill.field_dimensions)}"></label>
        <label>Intensità<select data-drill-field="selected_intensity"><option>bassa</option><option>media</option><option>alta</option></select></label>
      </div>
      <div class="why">
        <strong>PERCHÉ È QUI</strong>
        ${T.escape((current.priorities||[]).find(priority=>
          String(priority.priority_id||"")===String(drill.priority_id||"")
        )?.reason||"Collegato a una priorità confermata dallo staff.")}
      </div>`;
    box.querySelector('[data-drill-field="selected_intensity"]').value=
      drill.selected_intensity||drill.intensity;
    return box;
  }

  function renderSession(session,index,current){
    const card=el("article",null,"session");
    card.dataset.index=index;
    card.innerHTML=`
      <div class="session-summary">
        <div><span class="eyebrow">OBIETTIVO DELLA SEDUTA</span><h3>${T.escape(session.objective)}</h3><p>${T.escape(session.why)}</p></div>
        <strong>${Number(session.duration||90)}'</strong>
      </div>
      <div class="session-grid">
        <label>Giorno<input data-field="day" value="${T.escape(session.day)}"></label>
        <label>Durata<input data-field="duration" type="number" min="30" max="180" value="${Number(session.duration||90)}"></label>
        <label>Intensità<select data-field="intensity"><option>bassa</option><option>media</option><option>alta</option></select></label>
        <label>Stato<select data-field="status"><option>bozza</option><option>proposta_ai</option><option>accettata</option><option>modificata</option><option>completata</option></select></label>
      </div>
      <label>Obiettivo<input data-field="objective" value="${T.escape(session.objective)}"></label>
      <label>Tema<input data-field="theme" value="${T.escape(session.theme)}"></label>`;
    card.querySelector('[data-field="intensity"]').value=session.intensity;
    card.querySelector('[data-field="status"]').value=session.status;

    const blocks=el("div",null,"composer-blocks");
    const configured=session.blocks?.length?session.blocks:Object.entries(BLOCK_LABELS).map(
      ([block_id,label])=>({block_id,label,duration:0,objective:"",note:""})
    );
    configured.forEach(block=>{
      const section=el("section",null,"composer-block");
      section.dataset.block=block.block_id;
      section.innerHTML=`
        <div class="block-head">
          <span class="block-index">${String(configured.indexOf(block)+1).padStart(2,"0")}</span>
          <div><h4>${T.escape(block.label||BLOCK_LABELS[block.block_id])}</h4><p>${T.escape(block.objective)}</p></div>
          <label>Minuti<input data-block-field="duration" type="number" min="0" max="90" value="${Number(block.duration||0)}"></label>
        </div>`;
      const blockDrills=(session.drills||[])
        .map((drill,drillIndex)=>({drill,drillIndex}))
        .filter(item=>(item.drill.composer_block||"situational")===block.block_id);
      blockDrills.forEach(item=>section.append(
        renderDrill(item.drill,item.drillIndex,current,session)
      ));
      if(!blockDrills.length)section.append(
        el("p",block.note||"Completa con il protocollo abituale dello staff.","empty-block")
      );
      blocks.append(section);
    });
    card.append(blocks);
    return card;
  }

  T.render=plan=>{
    T.state.plan=plan;
    if(!plan){
      $("planArea").hidden=true;
      $("planStatus").textContent="Nessuna seduta";
      return;
    }
    const current=plan.current_plan||{};
    $("planArea").hidden=false;
    $("planStatus").textContent=plan.status.replaceAll("_"," ");
    $("planTitle").textContent=current.title||"Seduta MatchIQ";
    $("planMeta").textContent=`Settimana ${plan.week_key} · versione ${plan.version} · ${plan.training_days.join(", ")}`;
    $("staffNote").value=plan.staff_note||"";
    renderExplainability(current);
    renderDecisions(current);
    renderPriorities(current);
    const timeline=$("sessionTimeline");
    timeline.replaceChildren();
    (current.sessions||[]).forEach((session,index)=>{
      timeline.append(renderSession(session,index,current));
    });
    $("regeneratePlan").hidden=false;
    T.renderLibraryControls();
  };
})();
