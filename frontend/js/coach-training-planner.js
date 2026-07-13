(async function(){
    const token = localStorage.getItem("matchiq_auth_token") || sessionStorage.getItem("matchiq_auth_token");
    if(!token) return;

    try{
        const response = await fetch("/api/training-planner/current", {
            cache: "no-store",
            headers: { Authorization: `Bearer ${token}`, Accept: "application/json" }
        });
        if(!response.ok) return;

        const { data } = await response.json();
        const plan = data?.plan;
        const mount = document.getElementById("coachAiTrainingPlannerMount");
        const timelineSection = document.getElementById("eventsTimeline")?.closest(".grid.section");
        const main = document.querySelector(".main");
        if(!mount && !main) return;

        let panel = document.getElementById("coachAiTrainingPlanner");
        if(!panel){
            panel = document.createElement("section");
            panel.id = "coachAiTrainingPlanner";
            panel.className = "panel coach-training-planner-panel";
            panel.setAttribute("aria-label", "Piano di allenamento suggerito");
            if(mount) mount.appendChild(panel);
            else main.insertBefore(panel, timelineSection || null);
        }

        const copy = document.createElement("div");
        copy.className = "coach-training-plan-copy";

        const badge = document.createElement("span");
        badge.className = "badge green";
        badge.textContent = "AI TRAINING PLANNER";

        const title = document.createElement("h2");
        title.textContent = "Dalla partita al prossimo allenamento";

        const lead = document.createElement("p");
        lead.textContent = plan
            ? "Le priorita reali sono gia collegate alle esercitazioni della libreria MatchIQ."
            : "Genera un piano soltanto quando Pattern, Weekly e Coach contengono dati sufficienti.";
        copy.append(badge, title, lead);

        const list = document.createElement("div");
        list.className = "training-plan-list";
        if(plan){
            (plan.current_plan?.priorities || []).slice(0, 3).forEach((priority, index) => {
                const card = document.createElement("article");
                card.className = "training-plan-card";

                const heading = document.createElement("strong");
                heading.textContent = `${index + 1}. ${priority.title}`;

                const drills = document.createElement("span");
                drills.textContent = (priority.drills || []).map(item => item.title).join(" · ") || "Esercitazione da definire";

                const reason = document.createElement("small");
                reason.textContent = `Perche: ${priority.reason}`;
                card.append(heading, drills, reason);
                list.appendChild(card);
            });
        }

        const actions = document.createElement("div");
        actions.className = "coach-training-plan-actions";
        const link = document.createElement("a");
        link.className = "btn green";
        link.href = "/training-planner.html";
        link.textContent = plan ? "Apri e modifica il piano" : "Crea AI Training Plan";
        actions.appendChild(link);

        panel.replaceChildren(copy, list, actions);
    }catch(_error){
        // The Coach remains usable if the optional planner is unavailable.
    }
})();
