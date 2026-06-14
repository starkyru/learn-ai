/**
 * Module 22 — AI Product UX: browser JS (no build step, plain ES module)
 *
 * Works with both the Python (server.py) and TypeScript (server.ts) backends —
 * both serve on port 3100 with identical endpoint contracts.
 *
 * Task map:
 *   Task 1 — streamAnswer()         : SSE streaming, token-by-token rendering
 *   Task 2 — renderCitations()      : citation chips + source drill-down panel
 *   Task 3 — showState()            : loading / error / empty / answer states
 *   Task 4 — submitFeedback()       : 👍👎 + "looks wrong" → POST /feedback
 *   Task 5 — requestAction() / approve() : modal gating a risky action
 */

// ---------------------------------------------------------------------------
// Config — change this if your backend runs on a different port
// ---------------------------------------------------------------------------
const BACKEND_URL = "http://localhost:3100";

// ---------------------------------------------------------------------------
// State
// ---------------------------------------------------------------------------
let currentQuestion = "";
let currentAnswer   = "";
let pendingToken    = null;   // one-time approval token from /actions/request

// ---------------------------------------------------------------------------
// DOM refs
// ---------------------------------------------------------------------------
const form          = document.getElementById("ask-form");
const input         = document.getElementById("question-input");
const submitBtn     = form.querySelector("button[type=submit]");
const statusBadge   = document.getElementById("status-indicator");

const stateLoading  = document.getElementById("state-loading");
const stateError    = document.getElementById("state-error");
const stateEmpty    = document.getElementById("state-empty");
const answerCard    = document.getElementById("answer-card");

const errorMsg      = document.getElementById("error-message");
const retryBtn      = document.getElementById("retry-btn");
const answerText    = document.getElementById("answer-text");
const confidenceBadge = document.getElementById("confidence-badge");
const modelLabel    = document.getElementById("model-label");

const citationsRow  = document.getElementById("citations-row");
const citationChips = document.getElementById("citation-chips");

const feedbackBtns  = document.querySelectorAll(".feedback-btn");
const wrongBtn      = document.getElementById("wrong-btn");
const wrongForm     = document.getElementById("wrong-form");
const wrongNote     = document.getElementById("wrong-note");
const submitWrongBtn = document.getElementById("submit-wrong-btn");
const feedbackThanks = document.getElementById("feedback-thanks");

const sourcePanel   = document.getElementById("source-panel");
const panelContent  = document.getElementById("panel-content");
const closePanel    = document.getElementById("close-panel");
const panelOverlay  = document.getElementById("panel-overlay");

const riskyBtn      = document.getElementById("risky-action-btn");
const approvalModal = document.getElementById("approval-modal");
const modalDesc     = document.getElementById("modal-action-desc");
const modalPayload  = document.getElementById("modal-payload");
const modalApprove  = document.getElementById("modal-approve");
const modalReject   = document.getElementById("modal-reject");
const modalResult   = document.getElementById("modal-result");

// ---------------------------------------------------------------------------
// Task 3 — State machine
// ---------------------------------------------------------------------------

/**
 * Show exactly one state panel.
 *
 * @param {"loading"|"error"|"empty"|"answer"} state
 * @param {string} [errorText]
 */
function showState(state, errorText = "") {
  stateLoading.classList.toggle("hidden", state !== "loading");
  stateLoading.classList.toggle("flex",   state === "loading");
  stateError.classList.toggle("hidden",   state !== "error");
  stateEmpty.classList.toggle("hidden",   state !== "empty");
  answerCard.classList.toggle("hidden",   state !== "answer");

  if (state === "loading") {
    setStatus("Streaming…", "blue");
    submitBtn.disabled = true;
  } else if (state === "error") {
    errorMsg.textContent = errorText;
    setStatus("Error", "red");
    submitBtn.disabled = false;
  } else if (state === "empty") {
    setStatus("Ready", "gray");
    submitBtn.disabled = false;
  } else {
    setStatus("Done", "green");
    submitBtn.disabled = false;
  }
}

function setStatus(text, color) {
  const colors = {
    blue: "bg-blue-50 text-blue-600",
    green: "bg-green-50 text-green-600",
    red: "bg-red-50 text-red-600",
    gray: "bg-gray-100 text-gray-500",
  };
  statusBadge.className = `text-xs px-2 py-1 rounded-full ${colors[color] || colors.gray}`;
  statusBadge.textContent = text;
}

// ---------------------------------------------------------------------------
// Task 1 — Streaming answer
// ---------------------------------------------------------------------------

/**
 * Stream the answer token-by-token using SSE.
 *
 * SSE event types (from the server):
 *   token    → append text, show cursor
 *   citation → render a citation chip
 *   done     → show confidence badge, remove cursor
 *   error    → show error state
 */
async function streamAnswer(question) {
  showState("loading");
  answerText.textContent = "";
  answerText.classList.add("cursor");
  citationsRow.classList.add("hidden");
  citationChips.innerHTML = "";
  confidenceBadge.className = "text-xs font-medium px-2 py-0.5 rounded-full";
  confidenceBadge.textContent = "";
  modelLabel.textContent = "";
  feedbackThanks.classList.add("hidden");
  wrongForm.classList.add("hidden");

  const collectedDocs = [];

  try {
    const resp = await fetch(`${BACKEND_URL}/ask/stream`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ question }),
    });

    if (!resp.ok) throw new Error(`HTTP ${resp.status}`);

    const reader = resp.body.getReader();
    const decoder = new TextDecoder();
    let buffer = "";

    // SSE parsing: lines arrive as "data: {...}\n\n"
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });

      const parts = buffer.split("\n\n");
      buffer = parts.pop() ?? "";   // keep any incomplete chunk

      for (const part of parts) {
        if (!part.startsWith("data: ")) continue;
        const payload = JSON.parse(part.slice(6));

        if (payload.type === "token") {
          // Task 1 — append token
          answerText.textContent += payload.text;
          currentAnswer = answerText.textContent;
        } else if (payload.type === "citation") {
          // Task 2 — collect doc
          collectedDocs.push(payload.doc);
        } else if (payload.type === "done") {
          // Task 3 — show confidence
          answerText.classList.remove("cursor");
          renderCitations(collectedDocs);
          renderConfidence(payload.confidence);
          showState("answer");
        } else if (payload.type === "error") {
          answerText.classList.remove("cursor");
          showState("error", payload.message);
          return;
        }
      }
    }

  } catch (err) {
    answerText.classList.remove("cursor");
    showState("error", err.message);
  }
}

// ---------------------------------------------------------------------------
// Task 2 — Citations
// ---------------------------------------------------------------------------

/**
 * Render citation chips from the collected docs.
 * Clicking a chip opens the source panel.
 */
function renderCitations(docs) {
  if (!docs.length) return;
  citationChips.innerHTML = "";
  docs.forEach((doc) => {
    const chip = document.createElement("button");
    chip.className = "citation-chip";
    chip.textContent = doc.title;
    chip.addEventListener("click", () => openSourcePanel(doc));
    citationChips.appendChild(chip);
  });
  citationsRow.classList.remove("hidden");
  citationsRow.classList.add("flex");
}

function openSourcePanel(doc) {
  panelContent.innerHTML = `
    <h3 class="font-semibold text-gray-800">${escHtml(doc.title)}</h3>
    <a href="${escHtml(doc.url)}" class="text-xs text-blue-500 hover:underline break-all" target="_blank">
      ${escHtml(doc.url)}
    </a>
    <p class="text-gray-700 text-sm leading-relaxed">${escHtml(doc.content)}</p>
  `;
  sourcePanel.classList.remove("hidden");
  panelOverlay.classList.remove("hidden");
}

closePanel.addEventListener("click", closeSourcePanel);
panelOverlay.addEventListener("click", closeSourcePanel);

function closeSourcePanel() {
  sourcePanel.classList.add("hidden");
  panelOverlay.classList.add("hidden");
}

// ---------------------------------------------------------------------------
// Task 3 — Confidence badge
// ---------------------------------------------------------------------------

function renderConfidence(score) {
  let label, cls;
  if (score >= 0.75) {
    label = `High confidence (${Math.round(score * 100)}%)`;
    cls = "badge-high";
  } else if (score >= 0.50) {
    label = `Moderate confidence (${Math.round(score * 100)}%)`;
    cls = "badge-medium";
  } else {
    label = `Low confidence (${Math.round(score * 100)}%) — verify sources`;
    cls = "badge-low";
  }
  confidenceBadge.textContent = label;
  confidenceBadge.className = `text-xs font-medium px-2 py-0.5 rounded-full ${cls}`;
}

// ---------------------------------------------------------------------------
// Task 4 — Feedback
// ---------------------------------------------------------------------------

feedbackBtns.forEach((btn) => {
  btn.addEventListener("click", async () => {
    const rating = btn.dataset.rating;
    await submitFeedback(rating, "");
  });
});

wrongBtn.addEventListener("click", () => {
  wrongForm.classList.toggle("hidden");
});

submitWrongBtn.addEventListener("click", async () => {
  await submitFeedback("wrong", wrongNote.value.trim());
  wrongForm.classList.add("hidden");
  wrongNote.value = "";
});

/**
 * POST feedback to /feedback.
 *
 * @param {"up"|"down"|"wrong"} rating
 * @param {string} note
 */
async function submitFeedback(rating, note) {
  try {
    await fetch(`${BACKEND_URL}/feedback`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        question: currentQuestion,
        answer:   currentAnswer,
        rating,
        note,
      }),
    });
    feedbackThanks.classList.remove("hidden");
    // Hide thanks after 3 s
    setTimeout(() => feedbackThanks.classList.add("hidden"), 3000);
  } catch (err) {
    console.error("Feedback failed:", err);
  }
}

// ---------------------------------------------------------------------------
// Task 5 — Approval flow
// ---------------------------------------------------------------------------

riskyBtn.addEventListener("click", async () => {
  await requestAction(
    "delete-all-eval-results",
    { path: "modules/21-llmops-eval/results/", reason: "demo wipe" }
  );
});

/**
 * Request approval for a risky action.
 * Shows a modal; on Approve → POST /actions/approve.
 */
async function requestAction(action, payload) {
  // Step A — request a token from the server
  let token;
  try {
    const resp = await fetch(`${BACKEND_URL}/actions/request`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ action, payload }),
    });
    const data = await resp.json();
    token = data.token;
  } catch (err) {
    alert("Could not initiate action: " + err.message);
    return;
  }

  pendingToken = token;

  // Step B — show modal
  modalDesc.textContent = `Action: "${action}"`;
  modalPayload.textContent = JSON.stringify(payload, null, 2);
  modalResult.classList.add("hidden");
  modalApprove.disabled = false;
  modalReject.disabled  = false;
  approvalModal.classList.remove("hidden");
}

modalApprove.addEventListener("click", async () => {
  await sendApproval(true);
});

modalReject.addEventListener("click", async () => {
  await sendApproval(false);
});

async function sendApproval(approved) {
  modalApprove.disabled = true;
  modalReject.disabled  = true;

  try {
    const resp = await fetch(`${BACKEND_URL}/actions/approve`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ token: pendingToken, approved }),
    });
    const data = await resp.json();

    modalResult.textContent =
      data.status === "executed" ? "✅ Action executed." :
      data.status === "rejected" ? "🚫 Action cancelled." :
                                   "⏱ Token expired.";
    modalResult.className = "text-center text-sm font-medium " +
      (data.status === "executed" ? "text-green-600" : "text-gray-500");
    modalResult.classList.remove("hidden");

    setTimeout(() => approvalModal.classList.add("hidden"), 2000);
  } catch (err) {
    modalResult.textContent = "Error: " + err.message;
    modalResult.classList.remove("hidden");
  }

  pendingToken = null;
}

// ---------------------------------------------------------------------------
// Form submission
// ---------------------------------------------------------------------------

form.addEventListener("submit", async (e) => {
  e.preventDefault();
  const question = input.value.trim();
  if (!question) return;
  currentQuestion = question;
  currentAnswer   = "";
  input.value     = "";
  await streamAnswer(question);
});

retryBtn.addEventListener("click", async () => {
  if (currentQuestion) await streamAnswer(currentQuestion);
});

// ---------------------------------------------------------------------------
// Utils
// ---------------------------------------------------------------------------

function escHtml(str) {
  return str
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

// Show empty state on load
showState("empty");
