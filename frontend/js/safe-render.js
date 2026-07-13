(function () {
  "use strict";

  const HTML_MAP = { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" };
  const ALLOWED_TAGS = new Set(["A", "B", "BR", "DIV", "EM", "H1", "H2", "H3", "H4", "HR", "I", "LI", "OL", "P", "SECTION", "SMALL", "SPAN", "STRONG", "TABLE", "TBODY", "TD", "TH", "THEAD", "TR", "U", "UL"]);
  const ALLOWED_ATTRIBUTES = new Set(["class", "colspan", "rowspan", "title"]);

  function escapeHtml(value) {
    return String(value == null ? "" : value).replace(/[&<>"']/g, char => HTML_MAP[char]);
  }

  function safeUrl(value) {
    const raw = String(value || "").trim();
    if (!raw || raw.startsWith("#")) return raw || "#";
    try {
      const base = (window.location && window.location.origin) || "https://tactical.matchiq.it";
      const url = new URL(raw, base);
      const sameOrigin = url.origin === base;
      const localHttp = url.protocol === "http:" && ["localhost", "127.0.0.1"].includes(url.hostname);
      if (!sameOrigin && url.protocol !== "https:" && !localHttp) return "#";
      if (!["http:", "https:"].includes(url.protocol)) return "#";
      return sameOrigin ? `${url.pathname}${url.search}${url.hash}` : url.href;
    } catch (_) {
      return "#";
    }
  }

  function sanitizeHtml(value) {
    if (typeof DOMParser === "undefined") return escapeHtml(value);
    const parsed = new DOMParser().parseFromString(`<body>${String(value || "")}</body>`, "text/html");
    Array.from(parsed.body.querySelectorAll("*")).forEach(node => {
      if (!ALLOWED_TAGS.has(node.tagName)) {
        node.replaceWith(parsed.createTextNode(node.textContent || ""));
        return;
      }
      Array.from(node.attributes).forEach(attribute => {
        const name = attribute.name.toLowerCase();
        if (name.startsWith("on") || name === "style" || (!ALLOWED_ATTRIBUTES.has(name) && name !== "href")) {
          node.removeAttribute(attribute.name);
        }
      });
      if (node.tagName === "A") {
        node.setAttribute("href", safeUrl(node.getAttribute("href")));
        node.setAttribute("rel", "noopener noreferrer");
      }
    });
    return parsed.body.innerHTML;
  }

  function setText(node, value) {
    if (node) node.textContent = String(value == null ? "" : value);
  }

  window.MatchIQSafe = Object.freeze({ escapeHtml, safeUrl, sanitizeHtml, setText });
})();
