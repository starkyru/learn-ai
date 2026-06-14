# Module 22 — AI Product UX

> **Depth tags** 🟢 app-level · 🟡 build-one-piece-by-hand

Building an LLM that can answer questions is now table stakes. Making that LLM
feel **trustworthy and usable** — so users know when to trust it, can see where
it got its information, and have a way to push back when it's wrong — is the
actual hard product problem.

This module builds a small but fully runnable RAG chat UI and the backend that
powers it. Every trust/UX principle is embodied in working code you can run and
inspect.

---

## Concepts

### Why UX matters for AI trust

A model that's right 85 % of the time is worse than useless if the user can't
tell which 15 % to ignore. The UX job is to surface the model's uncertainty,
show its reasoning, and give users a way to correct it.

Five patterns that separate a demo from a trustworthy product:

| Pattern | The problem it solves |
|---------|----------------------|
| **Streaming** | Long waits feel broken. Tokens arriving immediately feel alive. |
| **Citations** | "Where did that come from?" — users won't trust what they can't verify. |
| **Confidence states** | Low confidence answers need a warning, not silent delivery. |
| **Feedback** | Users need a way to push back. Every "looks wrong" is training data. |
| **Approval flows** | Risky AI actions (send email, delete data) must be gated. |

### Streaming (SSE)

Server-Sent Events (SSE) are the right transport for token streaming:

- One-way server → client (simpler than WebSocket).
- Works over plain HTTP with no special setup.
- The client reads `text/event-stream` with `EventSource` or `fetch` + `ReadableStream`.

Each SSE event in this module is a typed JSON payload:
```
data: {"type": "token",    "text": "..."}
data: {"type": "citation", "doc": {...}}
data: {"type": "done",     "confidence": 0.85}
data: {"type": "error",    "message": "..."}
```

Typed events let the client handle each state correctly without fragile
string parsing.

### Citations / "show sources"

The LLM is instructed to output a citation block at the end of its answer:
```json
{"citations": ["doc1", "doc3"]}
```

The server strips this from the streamed text, resolves the doc IDs to full
metadata, and sends them as `citation` events. The client renders chips that
open a source drill-down panel — letting users verify any claim.

This is the single highest-impact trust feature. Users forgive wrong answers
they can check; they don't forgive wrong answers with no source.

### Confidence & failure states

Every answer has an explicit confidence score. The client renders:
- **High (≥ 75%)** — green badge, proceed.
- **Medium (50–74%)** — yellow badge, "verify sources".
- **Low (< 50%)** — red badge, prominent warning.

An explicit error state (not just a console log) with a retry button covers
network failures and provider errors. Empty state (before any question) is a
third distinct state — not a blank page.

### Feedback capture

Every 👍/👎 and "this looks wrong" report is a POST to `/feedback` and stored
as JSONL. That log feeds directly into module 21's human review queue — closing
the product loop: bad production outputs → human labels → better eval set →
better model.

### Approval flows for risky actions

When an AI agent wants to take a consequential action (send an email, delete a
record, make a purchase), require explicit user confirmation:

1. Server issues a one-time approval token (`/actions/request`).
2. Client shows a modal with the action description and payload.
3. User approves or rejects (`/actions/approve`).
4. Token expires after 120 seconds even if unused.

This pattern is mandatory for any agentic action with side effects. It's the
difference between an AI that helps and one that causes incidents.

---

## Setup

### Python backend

```bash
# Install FastAPI + uvicorn:
uv sync --extra production

# Start the server:
uv run python modules/22-ai-product-ux/py/server.py
```

### TypeScript backend

```bash
# Install deps (express is in package.json):
pnpm install

# Start the server:
pnpm tsx modules/22-ai-product-ux/ts/server.ts
```

Both backends run on **port 3100** and expose identical endpoints, so the
same frontend works with both.

### Frontend

Open `web/index.html` directly in a browser — no build step required.

```bash
# macOS:
open modules/22-ai-product-ux/web/index.html

# Or serve via Python's built-in HTTP server to avoid CORS issues:
python -m http.server 8080 --directory modules/22-ai-product-ux/web
# Then visit http://localhost:8080
```

**Endpoints:**

| Method | Path | Description |
|--------|------|-------------|
| `GET`  | `/health` | Health check |
| `POST` | `/ask/stream` | Streaming RAG answer (SSE) |
| `POST` | `/ask` | Synchronous RAG answer |
| `POST` | `/feedback` | Store user feedback |
| `POST` | `/actions/request` | Request approval token |
| `POST` | `/actions/approve` | Consume approval token |

**Files produced at runtime:**

| File | Created by |
|------|-----------|
| `py/feedback.jsonl` | Python server — task 4 |
| `py/actions.jsonl`  | Python server — task 5 |
| `ts/feedback.jsonl` | TS server — task 4 |
| `ts/actions.jsonl`  | TS server — task 5 |

---

## UI walkthrough

### Empty state
Open the page before asking anything. You see a centred placeholder with
example questions — no blank white void.

### Loading state
Submit a question. A spinner appears immediately with "Thinking…" — the user
knows something is happening.

### Streaming (task 1)
Tokens arrive one by one in the answer card. A blinking cursor indicates the
stream is live. Watch the Network tab → `/ask/stream` → Response to see the
raw SSE events.

### Citations (task 2)
After the final token, source chips appear below the answer ("Sources: Module 05
— RAG  Module 07 — Advanced & Production"). Click a chip to slide open the
source panel with title, URL, and excerpt. Click the overlay or ✕ to close it.

### Confidence (task 3)
A coloured badge appears in the top-left of the answer card. Green = high,
yellow = medium, red = low. Low-confidence answers include "verify sources"
in the badge text.

### Error state (task 3)
Stop the backend and submit a question. The error state appears with the
network error message and a "Try again" link.

### Feedback (task 4)
Click 👍 or 👎 — a green "Thanks for your feedback!" confirmation appears for
3 seconds. Click "This looks wrong" to expand a text area; submitting it sends
rating="wrong" with the note to `/feedback`. Check `feedback.jsonl` to verify.

### Approval flow (task 5)
Click "⚠ Simulate a risky action (requires approval)" at the bottom of the
answer card. A modal appears with the action description and a JSON payload.
Click Approve → server logs it in `actions.jsonl` and confirms. Click Cancel →
server logs it as rejected. Wait 2 minutes without responding → token expires.

---

## Tasks

### Task 1 — Streaming UI 🟢

**Goal:** Ask a question and watch tokens arrive live.

**Steps (Python):**
1. Start the Python server: `uv run python modules/22-ai-product-ux/py/server.py`
2. Open `web/index.html`.
3. Ask "What is RAG?" — watch tokens stream in.
4. Open `py/server.py`. Study `stream_rag_answer()` — it splits the SSE events
   by type. Add a second event type if you like (e.g., `"thinking"` before
   the first token).
5. Study `web/app.js` `streamAnswer()` — the `fetch` + `ReadableStream` SSE
   client. Trace one token from server to DOM.

**Steps (TypeScript):**
1. Start: `pnpm tsx modules/22-ai-product-ux/ts/server.ts`
2. Same frontend works. Study `ts/server.ts` `app.post("/ask/stream")`.

**Acceptance:**
- Tokens appear progressively (not all at once after a delay).
- The blinking cursor disappears when streaming is done.
- Opening DevTools → Network → `/ask/stream` → Response shows individual
  `data: {...}` lines arriving.

---

### Task 2 — Citations + source drill-down 🟢

**Goal:** Every answer shows which sources it used, and each source is
inspectable.

**Steps:**
1. The backend already sends `citation` events. Open `web/app.js`.
2. Find `renderCitations()`. Extend it: add a small superscript number to the
   answer text next to each sentence that cites a source (like Wikipedia [1]).
   Hint: you'll need to match the citation token in the streamed text.
3. Extend `openSourcePanel()` to show the full doc URL as a clickable link
   (for real corpus entries where URL is a real path).
4. Extend `retrieveContext()` in the server to simulate retrieval by filtering
   docs whose content includes at least one word from the question.

**Acceptance:**
- Source chips appear after every answer.
- Clicking a chip opens a panel with title, URL, content.
- Closing the panel (✕ or overlay click) works.

---

### Task 3 — Confidence + failure states 🟡

**Goal:** The UI handles all three non-happy states: loading, error, low confidence.

**Steps:**
1. `web/app.js` already has `showState()`. Verify all four states render by:
   - Asking a question (loading → answer).
   - Stopping the server and asking again (loading → error → retry).
   - Modify `stream_rag_answer` to send `confidence: 0.2` and see the red badge.
2. Extend the synchronous `/ask` endpoint to return a confidence score computed
   from the LLM-judge faithfulness grader from module 21.
   Hint: import `grade_llm_judge` from `../21-llmops-eval/py/01_versioned_eval.py`
   or copy the logic inline.
3. (Stretch) Add a fourth state: "partial" — the model answered but with low
   confidence and no citations. Render a prominent yellow callout above the
   answer text.

**Acceptance:**
- Network error shows the error state with a retry button.
- Low-confidence answers (< 50%) show a red badge with "verify sources".
- High-confidence answers show a green badge.

---

### Task 4 — Feedback capture 🟢

**Goal:** Users can rate answers and report problems; all feedback is stored.

**Steps:**
1. Click 👍 and 👎 — verify `feedback.jsonl` is written.
2. Click "This looks wrong", type a note, submit — verify the note is stored.
3. Extend the backend to accept an optional `session_id` in the feedback body
   so you can group feedback from one user session.
4. Write a small script (Python or TS) that reads `feedback.jsonl` and prints:
   - Total ratings, up vs down ratio.
   - All "wrong" reports with their notes.
   This is the seed of a feedback dashboard.

**Acceptance:**
- `feedback.jsonl` contains one entry per feedback submission.
- Each entry has: id, timestamp, question, answer, rating, note.
- The "Thanks!" confirmation appears and disappears after 3 s.

---

### Task 5 — Approval flow for risky actions 🟡

**Goal:** A modal gate prevents AI-triggered side effects without user confirmation.

**Steps:**
1. Click "⚠ Simulate a risky action" — the modal appears.
2. Approve — check `actions.jsonl` for `"approved": true`.
3. Reject — check for `"approved": false`.
4. Extend the backend: after an approval, actually execute a side effect. Start
   with something safe and observable: write a file, log to a special file,
   or print a server-side message.
5. Add a second simulated risky action: "summarize-and-email" with a
   payload of `{"to": "test@example.com", "subject": "AI Summary"}`.
   The modal should show the email address prominently — users need to see
   exactly what will happen.
6. Test token expiry: change the TTL to 5 s in the server; request an action,
   wait 6 s, then approve — you should get `"status": "expired"`.

**Acceptance:**
- The modal shows action name and JSON payload.
- Approve / reject both write to `actions.jsonl`.
- Expired tokens return `"status": "expired"` (not an error).

---

## Done when

- [ ] Task 1: ask a question, tokens stream live; cursor disappears on finish.
- [ ] Task 2: source chips appear; clicking one opens the drill-down panel.
- [ ] Task 3: three distinct states render correctly (loading, error, answer).
- [ ] Task 4: `feedback.jsonl` grows with each rating; "looks wrong" stores note.
- [ ] Task 5: modal appears for risky action; approve/reject both logged.

---

## Going deeper

- **Real RAG retrieval**: replace the stub `retrieveContext()` with the module 05
  pipeline — embed the question, search a Chroma collection, return top-k chunks.
  The UX layer is identical; only the data source changes.
- **Streaming with tools**: if the LLM uses tool calls (module 06), stream tool
  execution status as SSE events (`{"type": "tool_call", "name": "search"}`).
  The UI can show "Searching…" inline while the agent works.
- **Latency perception**: the biggest win is often showing the first token faster,
  not reducing total generation time. Short system prompts and smaller models
  dramatically reduce time-to-first-token.
- **Feedback → eval loop**: wire `feedback.jsonl` into module 21's human review
  queue (`04_human_review.py --write-queue`). Every "looks wrong" becomes a
  candidate for the eval set — this is the full production flywheel.
- **Optimistic UI**: for fast predictable actions, show the result immediately
  and roll back on server error. For slow/uncertain actions (like this LLM),
  show the loading state and never guess.
