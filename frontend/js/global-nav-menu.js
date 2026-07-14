(function(){
  "use strict";

  const focusable = 'a[href],button:not([disabled]),input:not([disabled]),select:not([disabled]),textarea:not([disabled]),[tabindex]:not([tabindex="-1"])';

  function wire(){
    const root = document.querySelector("[data-miq-global-nav]");
    if(!root || root.dataset.menuReady === "true") return;
    root.dataset.menuReady = "true";
    const trigger = root.querySelector(".miq-nav-menu-button");
    const drawer = root.querySelector(".miq-nav-drawer");
    const closeButton = root.querySelector("[data-miq-menu-close]");
    let previousFocus = null;

    function close(){
      if(drawer.hidden) return;
      drawer.hidden = true;
      trigger.setAttribute("aria-expanded", "false");
      document.body.classList.remove("miq-nav-menu-open");
      (previousFocus || trigger).focus();
    }

    function open(){
      previousFocus = document.activeElement;
      drawer.hidden = false;
      trigger.setAttribute("aria-expanded", "true");
      document.body.classList.add("miq-nav-menu-open");
      (drawer.querySelector(focusable) || closeButton).focus();
    }

    trigger.addEventListener("click", () => drawer.hidden ? open() : close());
    closeButton.addEventListener("click", close);
    drawer.querySelectorAll("a").forEach((link) => link.addEventListener("click", close));
    document.addEventListener("pointerdown", (event) => {
      if(drawer.hidden || drawer.contains(event.target) || trigger.contains(event.target)) return;
      close();
    });
    document.addEventListener("keydown", (event) => {
      if(drawer.hidden) return;
      if(event.key === "Escape") return close();
      if(event.key !== "Tab") return;
      const items = [...drawer.querySelectorAll(focusable)];
      if(!items.length) return;
      const first = items[0];
      const last = items[items.length - 1];
      if(event.shiftKey && document.activeElement === first){ event.preventDefault(); last.focus(); }
      else if(!event.shiftKey && document.activeElement === last){ event.preventDefault(); first.focus(); }
    });
  }

  function boot(){
    window.MatchIQGlobalNavRender?.mount();
    wire();
  }

  if(document.readyState === "loading") document.addEventListener("DOMContentLoaded", boot, { once: true });
  else boot();
})();
