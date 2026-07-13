(function () {
  "use strict";

  const A = window.MatchIQAssistant;

  A.openSources = message => {
    const response = message.response_json || {};
    const body = document.getElementById("sourceDialogBody");
    body.replaceChildren();

    const query = document.createElement("section");
    query.className = "source";
    query.innerHTML = `<strong>Query applicata</strong><p>${A.escape(JSON.stringify(response.query_applied || {}))}</p><p><b>Sufficienza:</b> ${A.escape(response.sufficiency?.level || "non indicata")} · <b>Fonti:</b> ${Number(response.source_count || 0)}</p>`;
    body.append(query);

    (message.sources || response.sources || []).forEach(item => {
      const node = document.createElement("article");
      node.className = "source";
      node.innerHTML = `<strong>${A.escape(item.title)}</strong><p>${A.escape(item.evidence_summary || "Fonte collegata alla memoria tecnica.")}</p><div class="chips"><span class="chip">${A.escape(item.source_type)}</span><span class="chip">Affidabilità ${A.escape(item.reliability_level || "non indicata")}</span><span class="chip">${A.escape(item.objective_or_subjective || "natura non indicata")}</span></div>`;
      if (item.action_url) {
        const paragraph = document.createElement("p");
        const link = document.createElement("a");
        link.href = A.safeUrl(item.action_url);
        link.textContent = "Apri fonte";
        paragraph.append(link);
        node.append(paragraph);
      }
      body.append(node);
    });

    if (response.limitations?.length) {
      const limits = document.createElement("section");
      limits.className = "source";
      limits.innerHTML = `<strong>Limiti</strong><ul>${response.limitations.map(item => `<li>${A.escape(item)}</li>`).join("")}</ul>`;
      body.append(limits);
    }

    document.getElementById("sourceDialog").showModal();
    document.getElementById("sourceDialogClose").focus();
  };
})();
