(function(){
  "use strict";

  const escapeHtml = (value) => window.MatchIQSafe?.escapeHtml
    ? window.MatchIQSafe.escapeHtml(value)
    : String(value ?? "").replace(/[&<>"']/g, char => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[char]));

  function linkMarkup(item, activeKey, className){
    const active = item.key === activeKey;
    return `<a class="${className}${active ? " is-active" : ""}" data-miq-nav-key="${escapeHtml(item.key)}" href="${escapeHtml(item.href)}"${active ? ' aria-current="page"' : ""}>${escapeHtml(item.label)}</a>`;
  }

  function mount(){
    if(document.querySelector("[data-miq-global-nav]")) return;
    const config = window.MatchIQGlobalNavConfig;
    const stateApi = window.MatchIQGlobalNavState;
    if(!config || !stateApi) return;

    const declared = document.body?.dataset?.miqModule;
    const moduleKey = declared && config.modules[declared] ? declared : config.moduleFromPath(location.pathname);
    const activeKey = config.activeFromLocation(location);
    const module = config.modules[moduleKey] || config.modules.home;
    const state = stateApi.snapshot();
    const accessLabel = state.canAdmin ? "Owner" : "Private Beta";
    if(moduleKey === "admin" && !state.canAdmin) return;
    const adminLink = state.canAdmin
      ? `<a class="miq-nav-account" href="${config.withVersion("/admin-beta.html")}">Admin</a>`
      : "";
    const nav = document.createElement("header");
    nav.className = "miq-global-nav";
    nav.dataset.miqGlobalNav = "";
    nav.innerHTML = `
      <a class="miq-nav-brand" href="${escapeHtml(module.href)}" aria-label="${escapeHtml(module.title)}">
        <img src="/assets/matchiq-logo.png" width="40" height="40" alt="">
        <span><strong>${escapeHtml(module.title)}</strong><small>${escapeHtml(module.subtitle)}</small></span>
      </a>
      <nav class="miq-nav-links" aria-label="Navigazione principale">
        ${config.navigation.map((item) => linkMarkup(item, activeKey, "miq-nav-link")).join("")}
      </nav>
      <div class="miq-nav-user">
        <a class="miq-nav-plan" href="${config.withVersion("/account.html")}" aria-label="Accesso ${escapeHtml(accessLabel)}">${escapeHtml(accessLabel)}</a>
        ${adminLink}
        <button class="miq-nav-menu-button" type="button" aria-label="Apri menu" aria-expanded="false" aria-controls="miqMobileMenu">
          <span aria-hidden="true"></span><span aria-hidden="true"></span><span aria-hidden="true"></span>
        </button>
      </div>
      <div id="miqMobileMenu" class="miq-nav-drawer" hidden>
        <div class="miq-nav-drawer-head"><strong>${escapeHtml(module.title)}</strong><button type="button" data-miq-menu-close aria-label="Chiudi menu">&times;</button></div>
        <nav aria-label="Navigazione mobile">
          ${config.navigation.map((item) => linkMarkup(item, activeKey, "miq-nav-drawer-link")).join("")}
          ${state.canAdmin ? `<a class="miq-nav-drawer-link" href="${config.withVersion("/admin-beta.html")}">Admin</a>` : ""}
        </nav>
      </div>`;

    document.body.prepend(nav);
    document.body.classList.add("miq-global-nav-mounted");
    window.addEventListener("hashchange", () => {
      const nextActive = config.activeFromLocation(location);
      nav.querySelectorAll("[data-miq-nav-key]").forEach((link) => {
        const isActive = link.dataset.miqNavKey === nextActive;
        link.classList.toggle("is-active", isActive);
        if(isActive) link.setAttribute("aria-current", "page");
        else link.removeAttribute("aria-current");
      });
    });
    window.dispatchEvent(new CustomEvent("matchiq:global-nav-ready", { detail: { moduleKey, state } }));
  }

  window.MatchIQGlobalNavRender = { mount };
})();
