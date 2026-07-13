(function () {
  "use strict";

  const A = window.MatchIQAssistant;
  const $ = id => document.getElementById(id);

  A.setStatus = (text, type = "") => {
    const box = $("assistantStatus");
    box.textContent = text;
    box.className = `status ${type}`;
  };

  A.renderSuggestions = () => {
    const root = $("suggestedQuestions");
    root.replaceChildren();
    (A.state.config?.suggestions || []).forEach(text => {
      const button = document.createElement("button");
      button.type = "button";
      button.textContent = text;
      button.addEventListener("click", () => {
        $("messageInput").value = text;
        $("messageInput").focus();
      });
      root.append(button);
    });
  };

  A.renderConversations = () => {
    const root = $("conversationList");
    root.replaceChildren();
    if (!A.state.conversations.length) {
      root.textContent = "Nessuna conversazione.";
      return;
    }

    A.state.conversations.forEach(item => {
      const button = document.createElement("button");
      const title = document.createElement("strong");
      const updated = document.createElement("small");
      button.type = "button";
      button.className = `conversation-item ${item.id === A.state.conversation?.id ? "active" : ""}`;
      title.textContent = item.title || "Conversazione";
      updated.textContent = new Date(item.updated_at).toLocaleString("it-IT");
      button.append(title, updated);
      button.addEventListener("click", () => A.openConversation(item.id));
      root.append(button);
    });
  };

  const section = (title, content) => {
    if (!content) return "";
    const body = Array.isArray(content)
      ? `<ul>${content.map(item => `<li>${A.escape(typeof item === "string" ? item : item.text)}</li>`).join("")}</ul>`
      : `<p>${A.escape(content)}</p>`;
    return `<section class="answer-section"><h3>${A.escape(title)}</h3>${body}</section>`;
  };

  A.messageNode = message => {
    const node = document.createElement("article");
    node.className = `message ${message.role}`;
    if (message.role === "user") {
      node.innerHTML = `<div class="message-meta">Tu</div><p>${A.escape(message.content)}</p>`;
      return node;
    }

    const response = message.response_json || {};
    node.innerHTML = `<div class="message-meta">MatchIQ · ${A.escape(response.intent || message.intent || "")} · ${A.escape(response.sufficiency?.level || message.confidence_level || "")}</div><h2>${A.escape(response.direct_answer || message.content)}</h2>${section("Perché", response.why)}${section("Cosa significa", response.meaning)}${section("Opzioni", response.options)}${response.contradictions?.length ? `<div class="contradiction"><strong>Fonti non concordi</strong><ul>${response.contradictions.map(item => `<li>${A.escape(item)}</li>`).join("")}</ul></div>` : ""}<div class="message-actions"><button type="button" data-why>Perché MatchIQ risponde così?</button><button type="button" data-useful>Utile</button><button type="button" data-not-useful>Non utile</button></div>`;

    const actions = node.querySelector(".message-actions");
    if (response.next_action?.url) {
      const link = document.createElement("a");
      link.href = A.safeUrl(response.next_action.url);
      link.textContent = response.next_action.label || "Apri";
      actions.insertBefore(link, actions.querySelector("[data-useful]"));
    }

    node.querySelector("[data-why]").addEventListener("click", () => A.openSources(message));
    node.querySelector("[data-useful]").addEventListener("click", () => A.sendFeedback(message.id, "utile", 1));
    node.querySelector("[data-not-useful]").addEventListener("click", () => A.openFeedback(message));
    return node;
  };

  A.renderMessages = () => {
    const root = $("messageList");
    root.replaceChildren();
    if (!A.state.messages.length) {
      root.innerHTML = '<section class="welcome"><h2>MatchIQ non inventa. MatchIQ motiva.</h2><p>La risposta nasce dalla memoria tecnica reale. Se non ci sono dati sufficienti, MatchIQ non completa i vuoti.</p></section>';
    } else {
      A.state.messages.forEach(message => root.append(A.messageNode(message)));
    }
    root.scrollTop = root.scrollHeight;
    const sources = A.state.messages.filter(item => item.role === "assistant").slice(-1)[0]?.sources || [];
    $("activeSourceSummary").textContent = sources.length
      ? `${sources.length} fonti: ${[...new Set(sources.map(item => item.source_type))].join(", ")}`
      : "Nessuna fonte attiva.";
  };
})();
