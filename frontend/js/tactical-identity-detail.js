(function(){
  const I=window.MatchIQIdentity;
  const fact=(label,value)=>`<div><small>${I.escape(label)}</small><strong>${I.escape(value||"Non disponibile")}</strong></div>`;
  const period=value=>value?.count?`${value.count} evidenze, ${value.from||"?"} - ${value.to||"?"}`:"Non determinabile";
  I.openDetail=async(id,focusValidation=false)=>{
    try{
      const item=await I.api.detail(id); I.state.activeDimension=item; I.els.dialogTitle.textContent=item.label;
      const evidence=item.evidence?.items||[], declared=item.declared_source||{};
      I.els.detail.innerHTML=`
        <section><h3>Lettura MatchIQ</h3><p>${I.escape(item.explanation)}</p><div class="dimension-meta"><span class="status">Affidabilita ${I.escape(item.confidence_level)}</span><span class="status">${item.match_count} partite</span><span class="status">${item.evidence_count} evidenze</span><span class="status">${I.escape(String(item.alignment_state).replaceAll("_"," "))}</span></div></section>
        <section><h3>Dichiarazione del mister</h3><div class="source-facts">${fact("Valore",item.declared_value)}${fact("Origine",declared.source_type)}${fact("Inserita da",declared.author)}${fact("Ultimo aggiornamento",declared.updated_at)}${fact("Stato",declared.confirmation_state)}${fact("Affidabilita",declared.reliability)}</div></section>
        <section><h3>Limiti e contraddizioni</h3><ul>${(item.limitations||[]).map(x=>`<li>${I.escape(x)}</li>`).join("")}</ul></section>
        <section><h3>Fonti verificabili</h3><div class="evidence-list">${evidence.map(source=>`<article class="evidence-item"><strong>${I.escape(source.source_type)} &middot; ${I.escape(source.reliability_level)}</strong><p>${I.escape(source.evidence_summary)}</p><small>${I.escape(source.occurred_at||"Data non disponibile")}</small></article>`).join("")||"<p>Nessuna evidenza disponibile per i filtri correnti.</p>"}</div></section>
        <section><h3>Confronto temporale</h3><div class="source-facts">${fact("Periodo precedente",period(item.previous_period))}${fact("Periodo recente",period(item.recent_period))}</div><p class="validation-help">Il confronto e descrittivo e non dimostra causalita.</p></section>
        <section id="identityValidationSection"><h3>Decisione dello staff</h3><p class="validation-help">La scelta crea una nuova versione e non cancella le evidenze.</p><div class="validation-panel"><label>Azione<select id="identityValidationAction"><option value="confirmed">Conferma</option><option value="contested">Contesta</option><option value="monitor">Da monitorare</option><option value="not_representative">Non rappresentativa</option><option value="update_declared">Aggiorna preferenza dichiarata</option></select></label><label>Nota o nuova preferenza<textarea id="identityValidationNote" maxlength="2000" rows="3" placeholder="Motiva la decisione dello staff"></textarea></label><button type="button" class="primary" data-save-validation="${item.id}">Salva decisione</button></div></section>`;
      if(!I.els.dialog.open)I.els.dialog.showModal();
      if(focusValidation)setTimeout(()=>document.getElementById("identityValidationAction")?.focus(),0);
    }catch(error){I.notice(error.message,true)}
  };
  I.closeDetail=()=>I.els.dialog.close();
})();
