(function(){
  "use strict";

  const LAST_ONLINE_KEY = "matchiq_ux_last_online_at";
  let lastFocused = null;

  function readStoredValue(key){
    try{
      return window.localStorage.getItem(key);
    }catch(_error){
      return null;
    }
  }

  function storeValue(key, value){
    try{
      window.localStorage.setItem(key, value);
    }catch(_error){
      // Privacy modes can disable storage; network feedback must still work.
    }
  }

  function formatTime(value){
    if(!value) return "non disponibile";
    const date = new Date(value);
    return Number.isNaN(date.getTime()) ? "non disponibile" : date.toLocaleString("it-IT");
  }

  function networkNode(){
    let node = document.getElementById("miqNetworkStatus");
    if(node) return node;
    node = document.createElement("div");
    node.id = "miqNetworkStatus";
    node.className = "miq-network-status";
    node.setAttribute("role", "status");
    node.setAttribute("aria-live", "polite");
    node.hidden = true;
    const message = document.createElement("span");
    message.dataset.miqNetworkMessage = "";
    const retry = document.createElement("button");
    retry.type = "button";
    retry.textContent = "Riprova";
    retry.addEventListener("click", () => {
      if(navigator.onLine) window.location.reload();
      else renderNetworkState(false);
    });
    node.append(message, retry);
    document.body.appendChild(node);
    return node;
  }

  function renderNetworkState(online){
    const node = networkNode();
    const message = node.querySelector("[data-miq-network-message]");
    if(online){
      storeValue(LAST_ONLINE_KEY, new Date().toISOString());
      node.hidden = true;
      return;
    }
    const last = readStoredValue(LAST_ONLINE_KEY);
    message.textContent = `Sei offline. Restano disponibili solo i dati gia salvati. Ultimo aggiornamento: ${formatTime(last)}.`;
    node.hidden = false;
  }

  function showRuntimeError(){
    if(document.getElementById("miqRuntimeError")) return;
    const node = document.createElement("div");
    node.id = "miqRuntimeError";
    node.className = "miq-runtime-error";
    node.setAttribute("role", "alert");
    const message = document.createElement("span");
    message.textContent = "Questa sezione non ha risposto correttamente. Il resto della pagina resta utilizzabile.";
    const retry = document.createElement("button");
    retry.type = "button";
    retry.textContent = "Ricarica pagina";
    retry.addEventListener("click", () => window.location.reload());
    node.append(message, retry);
    document.body.appendChild(node);
  }

  function enhanceTables(){
    document.querySelectorAll("table").forEach((table) => {
      if(table.parentElement?.classList.contains("miq-table-scroll")) return;
      const wrapper = document.createElement("div");
      wrapper.className = "miq-table-scroll";
      wrapper.tabIndex = 0;
      wrapper.setAttribute("role", "region");
      wrapper.setAttribute("aria-label", table.getAttribute("aria-label") || "Tabella scorrevole");
      table.parentNode.insertBefore(wrapper, table);
      wrapper.appendChild(table);
    });
  }

  function enhanceStatuses(){
    document.querySelectorAll(".notice,.status,.weekly-loading,.weekly-empty,.empty,.empty-state,[id$='Notice'],[id$='Status']").forEach((node) => {
      if(!node.hasAttribute("role")) node.setAttribute("role", "status");
      if(!node.hasAttribute("aria-live")) node.setAttribute("aria-live", "polite");
    });
  }

  function enhanceMedia(){
    document.querySelectorAll("img").forEach((image) => {
      if(!image.closest(".miq-global-nav") && !image.hasAttribute("loading")) image.loading = "lazy";
      if(!image.hasAttribute("decoding")) image.decoding = "async";
    });
    document.querySelectorAll("video").forEach((video) => {
      if(!video.hasAttribute("preload")) video.preload = "metadata";
    });
  }

  function enhanceDialogs(){
    document.querySelectorAll("dialog").forEach((dialog) => {
      if(dialog.dataset.miqHardened === "true") return;
      dialog.dataset.miqHardened = "true";
      dialog.addEventListener("click", (event) => {
        if(event.target !== dialog) return;
        const box = dialog.getBoundingClientRect();
        const inside = event.clientX >= box.left && event.clientX <= box.right && event.clientY >= box.top && event.clientY <= box.bottom;
        if(!inside) dialog.close();
      });
      dialog.addEventListener("close", () => {
        if(lastFocused instanceof HTMLElement && document.contains(lastFocused)) lastFocused.focus();
        lastFocused = null;
      });
    });
    document.addEventListener("click", (event) => {
      const opener = event.target.closest("button,a");
      if(opener && !opener.closest("dialog")) lastFocused = opener;
    }, true);
  }

  function observeDynamicContent(){
    const observer = new MutationObserver((records) => {
      if(!records.some((record) => record.addedNodes.length)) return;
      enhanceTables();
      enhanceStatuses();
      enhanceMedia();
      enhanceDialogs();
    });
    observer.observe(document.body, { childList: true, subtree: true });
  }

  function boot(){
    enhanceTables();
    enhanceStatuses();
    enhanceMedia();
    enhanceDialogs();
    observeDynamicContent();
    renderNetworkState(navigator.onLine);
    window.addEventListener("online", () => renderNetworkState(true));
    window.addEventListener("offline", () => renderNetworkState(false));
    window.addEventListener("error", (event) => {
      if(event.error || event.message) showRuntimeError();
    });
    window.addEventListener("unhandledrejection", showRuntimeError);
  }

  window.MatchIQUXHardening = { boot, renderNetworkState, enhanceTables };
  if(document.readyState === "loading") document.addEventListener("DOMContentLoaded", boot, { once: true });
  else boot();
})();
