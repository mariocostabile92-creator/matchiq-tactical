function boot(){
    const dateInput = document.getElementById("matchDateInput");
    if(dateInput && !dateInput.value){
        dateInput.value = todayISO();
    }

    loadState();
    if(coachState.live?.running){
        ensureCoachLiveTicker();
    }
    renderAll();
}

boot();

if("serviceWorker" in navigator){
    window.addEventListener("load", () => {
        navigator.serviceWorker.register("/service-worker.js")
            .catch(err => console.warn("Service Worker non registrato:", err));
    });
}
