const MATCHIQ_APP_META = {
    version: "10512",
    year: "2026",
    product: "MatchIQ"
};

window.MATCHIQ_APP_VERSION = MATCHIQ_APP_META.version;

(function initMatchIqLegalUi(){
    const AI_DISCLAIMER = "Le analisi e i suggerimenti generati dall'Intelligenza Artificiale rappresentano un supporto decisionale e devono essere sempre verificati dallo staff tecnico.";
    const VIDEO_DISCLAIMER = "Carica esclusivamente video di cui possiedi i diritti o l'autorizzazione all'utilizzo.";
    const MIC_DISCLAIMER = "Il microfono viene utilizzato esclusivamente durante la registrazione dei comandi vocali.";

    function injectStyle(){
        if(document.getElementById("matchiqLegalStyle")) return;
        const style = document.createElement("style");
        style.id = "matchiqLegalStyle";
        style.textContent = `
            .matchiq-footer{width:min(calc(100% - 32px),1180px);margin:34px auto 22px;padding:18px 20px;border:1px solid rgba(255,255,255,.10);border-radius:22px;background:rgba(255,255,255,.045);color:#aebee7;display:flex;justify-content:space-between;gap:16px;align-items:center;flex-wrap:wrap;box-shadow:0 18px 60px rgba(0,0,0,.18)}
            .matchiq-footer strong{color:#fff;font-weight:1000}
            .matchiq-footer small{display:block;margin-top:3px;color:#8fa3d7;font-weight:800}
            .matchiq-footer nav{display:flex;gap:10px;align-items:center;flex-wrap:wrap}
            .matchiq-footer a{color:#dbe6ff;text-decoration:none;font-weight:900;border-radius:999px;padding:8px 10px;border:1px solid transparent}
            .matchiq-footer a:focus-visible{outline:2px solid #00f5a0;outline-offset:2px}
            .matchiq-footer a:hover{border-color:rgba(0,245,160,.35);background:rgba(0,245,160,.08)}
            .matchiq-disclaimer{width:min(calc(100% - 32px),1180px);margin:18px auto 0;padding:13px 16px;border-radius:18px;border:1px solid rgba(0,245,160,.18);background:rgba(0,245,160,.07);color:#c7d7f2;font-size:13px;font-weight:800;line-height:1.55}
            .matchiq-disclaimer.video{border-color:rgba(255,209,102,.24);background:rgba(255,209,102,.08)}
            .matchiq-disclaimer.microphone{border-color:rgba(47,124,255,.24);background:rgba(47,124,255,.08);margin:10px 0 0;width:100%}
            .matchiq-legal-page{min-height:100vh;background:radial-gradient(circle at 18% 0%,rgba(0,245,160,.18),transparent 30%),radial-gradient(circle at 86% 10%,rgba(47,107,255,.20),transparent 30%),linear-gradient(180deg,#07101f,#03050b 68%,#02030a);color:#fff;font-family:Inter,Arial,sans-serif}
            .matchiq-legal-shell{width:min(calc(100% - 32px),980px);margin:0 auto;padding:38px 0 18px}
            .matchiq-legal-card{border:1px solid rgba(255,255,255,.11);border-radius:28px;background:rgba(255,255,255,.055);box-shadow:0 24px 80px rgba(0,0,0,.24);padding:28px}
            .matchiq-legal-card h1{font-size:clamp(32px,5vw,54px);line-height:1;margin-bottom:12px}
            .matchiq-legal-card h2{font-size:20px;margin:24px 0 10px}
            .matchiq-legal-card p,.matchiq-legal-card li{color:#c7d7f2;line-height:1.75;font-size:15px}
            .matchiq-legal-card ul{padding-left:20px}
            .matchiq-legal-nav{display:flex;gap:10px;flex-wrap:wrap;margin-bottom:18px}
            .matchiq-legal-nav a{color:#06111c;background:linear-gradient(135deg,#00f5a0,#2f6bff);border-radius:14px;text-decoration:none;font-weight:1000;padding:11px 14px}
            @media(max-width:700px){.matchiq-footer{display:grid;padding:16px;margin-bottom:calc(18px + env(safe-area-inset-bottom))}.matchiq-footer nav{display:grid;grid-template-columns:1fr 1fr}.matchiq-footer a{text-align:center;background:rgba(255,255,255,.05)}.matchiq-legal-card{padding:22px;border-radius:22px}}
        `;
        document.head.appendChild(style);
    }

    function currentPath(){
        return String(window.location.pathname || "").toLowerCase();
    }

    function isAiPage(path){
        return ["/index.html", "/mobile.html", "/coach.html", "/video.html", "/scout.html", "/match.html", "/tactical-assistant.html", "/tactical-identity.html", "/club-intelligence.html"].some(item => path.endsWith(item)) || path === "/";
    }

    function isVideoPage(path){
        return path.endsWith("/video.html");
    }

    function createDisclaimer(text, type){
        const node = document.createElement("div");
        node.className = `matchiq-disclaimer ${type || ""}`.trim();
        node.setAttribute("role", "note");
        node.textContent = text;
        return node;
    }

    function injectAiDisclaimer(){
        const path = currentPath();
        if(!isAiPage(path) || document.querySelector(".matchiq-disclaimer.ai")) return;
        const node = createDisclaimer(AI_DISCLAIMER, "ai");
        const footer = document.querySelector(".matchiq-footer");
        document.body.insertBefore(node, footer || null);
    }

    function injectVideoDisclaimer(){
        const path = currentPath();
        if(!isVideoPage(path) || document.querySelector(".matchiq-disclaimer.video")) return;
        const input = document.querySelector('input[type="file"]');
        const node = createDisclaimer(VIDEO_DISCLAIMER, "video");
        if(input){
            const target = input.closest(".video-upload, .upload-box, .upload, .field, .card, .panel") || input.parentElement;
            target.insertAdjacentElement("afterend", node);
        }else{
            const footer = document.querySelector(".matchiq-footer");
            document.body.insertBefore(node, footer || null);
        }
    }

    function injectMicrophoneDisclaimer(){
        if(!currentPath().endsWith("/coach.html") || document.querySelector(".matchiq-disclaimer.microphone")) return;
        const panel = document.getElementById("coachVoicePanel");
        if(!panel) return;
        const hint = document.getElementById("coachVoiceAutopilotHint") || panel;
        hint.insertAdjacentElement("afterend", createDisclaimer(MIC_DISCLAIMER, "microphone"));
    }

    function injectFooter(){
        if(document.querySelector(".matchiq-footer")) return;
        const footer = document.createElement("footer");
        footer.className = "matchiq-footer";
        footer.innerHTML = `
            <div>
                <strong>&copy; ${MATCHIQ_APP_META.year} MatchIQ</strong>
                <small>All rights reserved. Versione ${MATCHIQ_APP_META.version}</small>
            </div>
            <nav aria-label="Link legali MatchIQ">
                <a href="/privacy.html">Privacy Policy</a>
                <a href="/terms.html">Termini di utilizzo</a>
                <a href="/cookies.html">Cookie Policy</a>
            </nav>
        `;
        document.body.appendChild(footer);
    }

    function injectDecisionEntryAssets(){
        if(currentPath().endsWith("/decision-engine.html") || document.querySelector('script[src*="decision-engine-entry.js"]')) return;
        const style=document.createElement("link"); style.rel="stylesheet"; style.href="/css/decision-engine-entry.css?v=10511"; document.head.appendChild(style);
        const script=document.createElement("script"); script.src="/js/decision-engine-entry.js?v=10511"; script.defer=true; document.body.appendChild(script);
    }

    function injectClubEntryAssets(){
        if(currentPath().endsWith("/club-intelligence.html") || document.querySelector('script[src*="club-intelligence-entry.js"]')) return;
        const style=document.createElement("link"); style.rel="stylesheet"; style.href="/css/club-intelligence-entry.css?v=10512"; document.head.appendChild(style);
        const script=document.createElement("script"); script.src="/js/club-intelligence-entry.js?v=10512"; script.defer=true; document.body.appendChild(script);
    }

    function boot(){
        injectStyle();
        injectFooter();
        injectAiDisclaimer();
        injectVideoDisclaimer();
        injectMicrophoneDisclaimer();
        injectDecisionEntryAssets();
        injectClubEntryAssets();
    }

    if(document.readyState === "loading"){
        document.addEventListener("DOMContentLoaded", boot);
    }else{
        boot();
    }
})();
