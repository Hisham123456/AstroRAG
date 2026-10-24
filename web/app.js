"use strict";

const form = document.querySelector("#question-form");
const input = document.querySelector("#question");
const send = document.querySelector("#send");
const newChat = document.querySelector("#new-chat");
const messages = document.querySelector("#messages");
const welcome = document.querySelector("#welcome");
const statusBox = document.querySelector("#model-status");
const statusText = document.querySelector("#status-text");
const sourceContent = document.querySelector("#sources-content");
const emptySources = sourceContent.innerHTML;
let turns = [];
let busy = false;
let ready = false;
let currentTurn = null;
let selectedSource = null;

function element(tag, className, text) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text !== undefined) node.textContent = text;
  return node;
}

function setControls() {
  input.disabled = busy || !ready;
  send.disabled = busy || !ready || !input.value.trim();
  newChat.disabled = busy;
  document.querySelectorAll("[data-question]").forEach(button => { button.disabled = busy || !ready; });
  form.setAttribute("aria-busy", String(busy));
}

function scrollConversation() {
  const scroller = document.querySelector("#conversation-scroll");
  if (window.innerWidth > 760) scroller.scrollTop = scroller.scrollHeight;
  else messages.lastElementChild?.scrollIntoView({ block: "start", behavior: "auto" });
}

function displaySources(turn, sourceId = null, moveToSource = false) {
  currentTurn = turn;
  selectedSource = sourceId;
  sourceContent.replaceChildren();
  const count = document.querySelector("#source-count");
  const used = new Set(turn.result.answer.statements.flatMap(statement => statement.source_ids));
  const sources = turn.result.retrieved_sources.filter(source => used.has(source.source_id));
  count.hidden = sources.length === 0;
  count.textContent = `${sources.length} passage${sources.length > 1 ? "s" : ""}`;
  if (!sources.length) {
    const empty = element("div", "sources-empty");
    empty.append(element("h3", "", "Aucun passage cité."));
    empty.append(element("p", "", "Les extraits retrouvés ne suffisent pas à répondre à cette question."));
    sourceContent.append(empty);
  }
  for (const source of sources) {
    const section = element("section", "source-entry");
    const toggle = element("button", "source-toggle");
    toggle.type = "button";
    toggle.id = `source-toggle-${turn.id}-${source.source_id}`;
    toggle.setAttribute("aria-expanded", String(sourceId === source.source_id));
    const bodyId = `source-body-${turn.id}-${source.source_id}`;
    toggle.setAttribute("aria-controls", bodyId);
    toggle.append(element("span", "source-number", String(source.source_id)));
    const title = element("span", "source-name", source.title);
    title.append(element("span", "source-section", source.section_path.join(" › ")));
    toggle.append(title);
    const body = element("div", "source-body");
    body.id = bodyId;
    body.hidden = sourceId !== source.source_id;
    toggle.classList.toggle("selected", !body.hidden);
    body.append(element("p", "", source.text));
    const url = new URL(source.revision_url);
    if (url.protocol === "https:" && url.hostname === "fr.wikipedia.org") {
      const link = element("a", "", "Ouvrir l’article sur Wikipédia");
      link.href = url.href;
      link.target = "_blank";
      link.rel = "noopener noreferrer";
      body.append(link);
    }
    body.append(element("div", "source-attribution", `Révision ${source.revision_id}. Contributeurs et contributrices de Wikipédia. ${source.license.text || ""}.`));
    toggle.addEventListener("click", () => {
      const wasOpen = !body.hidden;
      displaySources(turn, wasOpen ? null : source.source_id);
      document.getElementById(toggle.id)?.focus({ preventScroll: true });
    });
    section.append(toggle, body);
    sourceContent.append(section);
  }
  document.querySelectorAll(".citation").forEach(button => {
    const selected = button.dataset.turn === turn.id && Number(button.dataset.source) === sourceId;
    button.classList.toggle("selected", selected);
    button.setAttribute("aria-pressed", String(selected));
  });
  if (moveToSource) {
    document.getElementById(`source-toggle-${turn.id}-${sourceId}`)?.focus({ preventScroll: true });
    if (window.innerWidth <= 760) document.querySelector("#sources-panel").scrollIntoView({ behavior: "auto", block: "start" });
  }
}

function renderAnswer(turn, container) {
  container.replaceChildren();
  const heading = element("div", "assistant-heading");
  const mark = element("img"); mark.src = "/static/orbit.svg"; mark.alt = "";
  heading.append(mark, element("span", "", "AstroRAG"));
  const body = element("div", "assistant-message");
  if (!turn.result.answer.answerable) {
    body.append(element("p", "clarification", turn.result.formatted_answer));
  } else {
    for (const statement of turn.result.answer.statements) {
      const paragraph = element("p", "", statement.text + " ");
      for (const ref of [...new Set(statement.source_ids)].sort((a, b) => a - b)) {
        const button = element("button", "citation", String(ref));
        button.type = "button";
        button.dataset.turn = turn.id;
        button.dataset.source = String(ref);
        button.setAttribute("aria-label", `Lire la source ${ref}`);
        button.setAttribute("aria-pressed", "false");
        button.addEventListener("click", () => displaySources(turn, ref, true));
        paragraph.append(button, document.createTextNode(" "));
      }
      body.append(paragraph);
    }
  }
  const meta = element("div", "turn-meta");
  if (turn.result.answer.answerable) {
    const view = element("button", "view-sources", "Consulter les sources de cette réponse");
    view.type = "button";
    view.addEventListener("click", () => {
      const ref = turn.result.answer.statements[0]?.source_ids[0];
      displaySources(turn, ref, true);
    });
    meta.append(view);
  }
  meta.append(element("span", "", `${turn.result.elapsed_seconds} s`));
  container.append(heading, body, meta);
}

async function submitQuestion(question, retryTurn = null) {
  if (busy || !ready || !question.trim()) return;
  const clean = question.trim();
  const precedingTurns = retryTurn ? turns.slice(0, turns.indexOf(retryTurn)) : turns;
  const history = precedingTurns.filter(turn => turn.result).slice(-3).map(turn => ({
    question: turn.question,
    answer: turn.result.answer.answerable ? turn.result.answer.statements.map(s => s.text).join("\n").slice(0, 3500) : turn.result.formatted_answer,
  }));
  const turn = retryTurn || { id: crypto.randomUUID(), question: clean };
  if (!retryTurn) {
    turns.push(turn);
    welcome.hidden = true;
    const section = element("article", "turn");
    section.id = `turn-${turn.id}`;
    section.append(element("div", "user-message", clean));
    turn.container = element("div");
    section.append(turn.container);
    messages.append(section);
  }
  const thinking = element("div", "thinking");
  thinking.setAttribute("role", "status");
  thinking.append(element("span", "status-dot"), element("span", "", history.length ? "Je reprends le fil et consulte les sources…" : "Je consulte les sources et prépare la réponse…"));
  turn.container.replaceChildren(thinking);
  busy = true;
  input.value = "";
  input.style.height = "auto";
  setControls();
  scrollConversation();
  try {
    const response = await fetch("/api/chat", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ question: clean, history }),
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || "La réponse est indisponible. Réessayez.");
    turn.result = data;
    renderAnswer(turn, turn.container);
    displaySources(turn);
  } catch (error) {
    const block = element("div", "turn-error");
    block.setAttribute("role", "alert");
    block.append(element("div", "", error.message === "Failed to fetch" ? "La connexion à l’application est interrompue. Vérifiez que le serveur est lancé." : error.message));
    const retry = element("button", "error-retry", "Réessayer cette question");
    retry.type = "button";
    retry.addEventListener("click", () => submitQuestion(clean, turn));
    block.append(retry);
    turn.container.replaceChildren(block);
  } finally {
    busy = false;
    setControls();
    input.focus({ preventScroll: true });
    scrollConversation();
  }
}

form.addEventListener("submit", event => { event.preventDefault(); submitQuestion(input.value); });
input.addEventListener("input", () => {
  input.style.height = "auto";
  input.style.height = `${Math.min(input.scrollHeight, 140)}px`;
  setControls();
});
input.addEventListener("keydown", event => {
  if (event.key === "Enter" && !event.shiftKey && !event.isComposing) {
    event.preventDefault();
    if (input.value.trim()) form.requestSubmit();
  }
});
document.querySelectorAll("[data-question]").forEach(button => button.addEventListener("click", () => submitQuestion(button.dataset.question)));
newChat.addEventListener("click", () => {
  if (busy) return;
  turns = [];
  currentTurn = null;
  selectedSource = null;
  messages.replaceChildren();
  sourceContent.innerHTML = emptySources;
  document.querySelector("#source-count").hidden = true;
  welcome.hidden = false;
  input.value = "";
  setControls();
  input.focus();
});
document.querySelector("#back-to-chat").addEventListener("click", () => {
  const target = currentTurn ? document.getElementById(`turn-${currentTurn.id}`) : welcome;
  target.tabIndex = -1;
  target.focus({ preventScroll: true });
  target.scrollIntoView({ block: "start", behavior: "auto" });
});

async function checkStatus() {
  try {
    const response = await fetch("/api/status");
    if (!response.ok) throw new Error("status");
    const data = await response.json();
    ready = data.state === "ready";
    statusBox.className = `model-status ${data.state}`;
    statusText.textContent = ready ? "Prêt à explorer. Historique limité à cette page." : (data.message || "Chargement du modèle, une seule fois au démarrage…");
    if (data.articles) document.querySelector("#corpus-count").textContent = `${data.articles} articles dans votre corpus`;
    setControls();
    if (data.state === "loading") setTimeout(checkStatus, 1500);
  } catch {
    statusBox.className = "model-status error";
    statusText.textContent = "L’application ne répond pas. Vérifiez que le serveur est lancé, puis actualisez la page.";
  }
}
setControls();
checkStatus();
