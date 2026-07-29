(function(){
  const T=window.MatchIQTraining;
  const $=id=>document.getElementById(id);
  const el=(tag,text,className)=>{
    const node=document.createElement(tag);
    if(text!=null)node.textContent=text;
    if(className)node.className=className;
    return node;
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

  T.render=plan=>{
    T.state.plan=plan;
    if(!plan){
      $("planArea").hidden=true;
      $("planStatus").textContent="Nessuna bozza";
      return;
    }
    $("planArea").hidden=false;
    $("planStatus").textContent=plan.status.replaceAll("_"," ");
    $("planTitle").textContent=plan.current_plan?.title||"Bozze allenamento";
    $("planMeta").textContent=`Settimana ${plan.week_key} · versione ${plan.version} · ${plan.training_days.join(", ")}`;
    $("staffNote").value=plan.staff_note||"";

    const priorities=$("priorityList");
    priorities.replaceChildren();
    (plan.current_plan?.priorities||[]).forEach((item,index)=>{
      const card=el("article",null,"priority");
      card.append(
        el("span",`PRIORITA ${index+1}`,"eyebrow"),
        el("h3",item.title),
        el("p",item.reason),
        el("strong",`Affidabilita ${item.reliability}`)
      );
      const sources=el("div",null,"sources");
      (item.sources||[]).forEach(source=>{
        sources.append(el("span",`${source.module}: ${source.label} (${source.count})`,"source"));
      });
      card.append(sources);
      priorities.append(card);
    });

    const timeline=$("sessionTimeline");
    timeline.replaceChildren();
    (plan.current_plan?.sessions||[]).forEach((session,index)=>{
      const card=el("article",null,"session");
      card.dataset.index=index;
      card.innerHTML=`
        <div class="session-grid">
          <label>Giorno<input data-field="day" value="${T.escape(session.day)}"></label>
          <label>Durata<input data-field="duration" type="number" min="30" max="180" value="${Number(session.duration||90)}"></label>
          <label>Intensita<select data-field="intensity"><option>bassa</option><option>media</option><option>alta</option></select></label>
          <label>Stato<select data-field="status"><option>bozza</option><option>proposta_ai</option><option>accettata</option><option>modificata</option><option>completata</option></select></label>
        </div>
        <label>Obiettivo<input data-field="objective" value="${T.escape(session.objective)}"></label>
        <label>Tema<input data-field="theme" value="${T.escape(session.theme)}"></label>`;
      card.querySelector('[data-field="intensity"]').value=session.intensity;
      card.querySelector('[data-field="status"]').value=session.status;

      (session.drills||[]).forEach((drill,drillIndex)=>{
        const box=el("div",null,"drill");
        box.dataset.drill=drillIndex;
        box.innerHTML=`
          <div class="drill-head">
            <h4>${T.escape(drill.title)}</h4>
            <button type="button" class="remove-drill" data-remove-drill="${drillIndex}" aria-label="Rimuovi ${T.escape(drill.title)}">Rimuovi</button>
          </div>
          <p>${T.escape(drill.description)}</p>
          <div class="drill-grid">
            <label>Durata<input data-drill-field="selected_duration" type="number" min="5" max="60" value="${Number(drill.selected_duration||drill.duration)}"></label>
            <label>Giocatori<input data-drill-field="players" type="number" min="4" max="40" value="${Number(drill.players||18)}"></label>
            <label>Campo<input data-drill-field="field_dimensions" value="${T.escape(drill.field_dimensions)}"></label>
            <label>Intensita<select data-drill-field="selected_intensity"><option>bassa</option><option>media</option><option>alta</option></select></label>
          </div>
          <div class="why">
            <strong>PERCHE TI PROPONGO QUESTO?</strong>
            ${T.escape((plan.current_plan.priorities||[]).find(priority=>
              priority.priority_id&&(session.priority_ids||[]).includes(priority.priority_id)
            )?.reason||"Collegato a una priorita confermata dallo staff.")}
          </div>`;
        box.querySelector('[data-drill-field="selected_intensity"]').value=
          drill.selected_intensity||drill.intensity;
        card.append(box);
      });
      timeline.append(card);
    });
    $("regeneratePlan").hidden=false;
    T.renderLibraryControls();
  };
})();
