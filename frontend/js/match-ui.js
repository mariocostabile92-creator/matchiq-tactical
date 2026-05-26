/*
    MatchIQ - Match UI Module
    Gestisce overlay live, sezioni apribili/chiudibili e UI base del match.
*/

function showLiveOverlay(title,text){
    const overlay=document.getElementById("liveOverlay");
    if(!overlay)return;

    const titleEl=document.getElementById("liveOverlayTitle");
    const textEl=document.getElementById("liveOverlayText");

    if(titleEl)titleEl.textContent=title;
    if(textEl)textEl.textContent=text;

    overlay.classList.add("show");
    setTimeout(()=>overlay.classList.remove("show"),2800);
}

function renderSection(id,icon,title,content,flash=false){
    const open=sectionState[id];

    return`
    <div class="dashboard-section ${open?"open":"closed"} ${flash?"live-flash":""}" data-section="${id}">
        <div class="section-toggle">
            <div class="section-toggle-left"><span>${icon}</span><span>${title}</span></div>
            <button class="toggle-btn">${open?"−":"+"}</button>
        </div>
        <div class="section-content">${content}</div>
    </div>`;
}

function initToggles(){
    document.querySelectorAll(".section-toggle").forEach(toggle=>{
        toggle.addEventListener("click",()=>{
            const section=toggle.closest(".dashboard-section");
            if(!section)return;

            const id=section.dataset.section;
            sectionState[id]=!sectionState[id];

            section.classList.toggle("open",sectionState[id]);
            section.classList.toggle("closed",!sectionState[id]);

            const btn=section.querySelector(".toggle-btn");
            if(btn)btn.textContent=sectionState[id]?"−":"+";
        });
    });
}