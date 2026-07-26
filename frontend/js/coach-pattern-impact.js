(function(){
    const token = localStorage.getItem("matchiq_auth_token") || sessionStorage.getItem("matchiq_auth_token");
    if(!token) return;

    async function refresh(){
        if(!window.coachState?.match) return;
        let panel = document.getElementById("coachPatternImpact");
        if(!panel){
            panel = document.createElement("div");
            panel.id = "coachPatternImpact";
            panel.className = "panel";
            panel.innerHTML = '<span class="badge blue">IMPATTO SULLO STORICO</span><h2>Cosa si ripete</h2><div data-pattern-impact class="empty">Verifico l’impatto di questa partita sulle ricorrenze storiche.</div><a class="btn dark" href="/pattern-intelligence.html">Apri le ricorrenze</a>';
            const history = document.getElementById("coachPhaseHistory") || document.querySelector(".wrap") || document.body;
            history.appendChild(panel);
        }
        try{
            const response = await fetch("/api/pattern-intelligence/impact", {
                method:"POST",
                headers:{"Content-Type":"application/json", Authorization:`Bearer ${token}`},
                body:JSON.stringify({match:coachState.match, events:coachState.events || []})
            });
            if(!response.ok) return;
            const {data} = await response.json();
            const target = panel.querySelector("[data-pattern-impact]");
            const lines = [];
            (data.strengthened || []).forEach(item => lines.push(`Questa partita rafforza la ricorrenza “${item.title}”.`));
            (data.not_confirmed || []).forEach(item => lines.push(`Questa partita non conferma la ricorrenza “${item.title}”.`));
            if(data.new_signal) lines.push("È emerso un nuovo segnale da monitorare.");
            target.className = "";
            target.textContent = lines.join(" ") || "Nessun impatto storico rilevabile con i dati disponibili.";
            target.title = data.disclaimer || "";
        }catch{}
    }

    window.addEventListener("load", refresh);
    document.addEventListener("click", event => {
        if(event.target.closest("#coachPatternImpact")) return;
        setTimeout(refresh, 300);
    });
})();
