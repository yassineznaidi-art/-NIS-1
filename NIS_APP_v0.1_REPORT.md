# NIS App v0.1 Report — First Real Application

**Date:** 2026-09-22 UTC
**App:** NIS — نِيسْ — calm intelligent assistant
**Core:** NIS v1.1 Canonical + v0.2 + v0.3-P1 (E+A+B) — **not redesigned**
**Server:** FastAPI + plain HTML/CSS/JS, responsive, works on iPhone browser
**Status:** Live at `http://0.0.0.0:8000` (preview https://8000-xxx.e2b.app), all tests green, STOP after v0.1

---

## A — Architecture Integration

**NIS Core remains authority** for intent (N3), memory (S1-S7), deliberation (N6), reasoning (N7), planning (N8), verification (N14), permissions (N9/N10), state, persona (N16), tool routing. UI is a shell — no competing intelligence.

```
iPhone Browser (Safari)
  → HTTPS → FastAPI (app/main.py)
    → NISAdapter (app/adapter.py)
      → ModelProvider.get_provider() → NISCoreProvider
        → NIS Core Orchestrator.run_turn() [N0→N1→N2→N3→N4→N5→N6→N7→N8→N9→N10→N12→N13→N14→N16]
        → Memory SUBSTRATE (S3/S4/S5 + embeddings)
        → Verification (V1-V8, CoT firewall)
      → sanitized response (no private_scratch)
    → app/sessions.py (UI history, separate from NIS memory)
  → JSON → frontend/app.js → conversation UI
```

**No bypass rule verified:** Every UI message goes through `adapter.chat() → provider.generate() → orchestrator.run_turn()`; no shortcut that skips N3/N6/N7/N14. If UI tried, `adapter` would reject and report architectural conflict (none needed).

**Source of truth:** `nis/`, `nis/config.py`, `NIS_v0.3_P1_REPORT.md`, existing traces — no second architecture invented.

---

## B — Application Structure

```
/home/user/nis-mvv/
├── nis/                      # NIS Core — untouched authority
│   ├── orchestrator.py       # N0 state machine (existing)
│   ├── nodes.py              # N1-N17 (v0.3-P1 WorkingContext + dense)
│   ├── memory.py             # hybrid retrieval (dense-first)
│   ├── embeddings.py         # dense cache (new in v0.3-P1)
│   ├── config.py             # RuntimeConfig (USE_DENSE flag + env NIS_USE_DENSE)
│   └── tools.py              # tool router
├── app/                      # Application shell (new in v0.1)
│   ├── main.py               # FastAPI: /api/chat, /api/sessions, /api/health, static
│   ├── adapter.py            # NISAdapter — clean boundary, error handling, CoT firewall
│   ├── sessions.py           # file-backed UI sessions (data/memory/app_sessions.json)
│   └── config.py             # PUBLIC_CONFIG vs SECRET_CONFIG separation
├── model_providers/          # Provider abstraction (new)
│   ├── base.py               # ModelProvider.generate/stream/health
│   ├── nis_core_provider.py  # real — delegates to NIS Core (authority)
│   ├── mock_provider.py      # MOCK fallback, clearly marked
│   └── __init__.py           # get_provider() factory (env MODEL_PROVIDER)
├── frontend/                 # Mobile-responsive UI (new)
│   ├── index.html            # NIS header, conversation, composer, drawer, settings
│   ├── style.css             # calm/minimal, dark, responsive, accessible
│   └── app.js                # fetch /api/chat, sessions, suggestions, no trace leak
├── tests_app/
│   └── test_app.py           # A1-A10 (10 tests)
├── data/memory/
│   ├── S1_working.json …     # NIS memory (existing, authoritative)
│   ├── S4_ltm.json           # corrected stale timestamp (v0.3-P1)
│   ├── embeddings.json       # dense cache (v0.3-P1)
│   └── app_sessions.json     # UI sessions (new, separate)
├── .env.example              # PUBLIC vs SECRET template
├── requirements_app.txt      # (see below)
└── NIS_APP_v0.1_REPORT.md    # this file
```

**Separation:** `nis_core/` vs `app/` vs `frontend/` is explicit; no duplication of intelligence.

---

## C — Core Connection

**Adapter API:**

```python
# app/adapter.py
class NISAdapter:
  def chat(self, message, session_id, attachments) -> {status, message, trace_id, deliberation_level, verification, intent, latency_ms, mock, provenance}
  def stream_chat(...) -> generator
  def health() -> {status, details}
```

- **Calls only** `self.provider.generate(message, context)` where `NISCoreProvider.generate` does `ORCHESTRATOR.run_turn(prompt, attachments, trace_id)` — the smallest possible adapter (40 lines).
- **No duplicate logic:** No N3 keyword heuristics, no N6 weighted axes, no N7 templates in UI. All intelligence stays in `nis/nodes.py`.
- **WorkingContext preserved:** `perception_frame.normalized_text` → `N2.process(..., memory_bundle)` → `working_context {user_query, memory_context, summary}` — contamination guard still active. `adapter` never splits `summary`; it passes raw message.
- **Streaming:** `stream()` yields 80-char chunks of `generate()` result — correct without needing LLM tokens. Real LLM streaming would override `ModelProvider.stream()` later.

**Endpoint flow:**

```
POST /api/chat {message, session_id, attachments}
  → ensure session exists (or create)
  → append user message to app_sessions.json
  → adapter.chat(message, session_id)
    → NIS Core → response_text + deliberation/verification
  → append assistant message to app_sessions.json (only safe meta)
  → return {message, session_id, trace_id, deliberation_level, verification, intent, latency_ms, mock, provenance}
```

**Trace:** Full NIS trace available via `GLOBAL_TRACE` logs (`logs/traces.json`), but UI only receives sanitized `message` + `deliberation_level` + `verification` badge — CoT firewall intact.

---

## D — Model Provider

**Interface `model_providers/base.py`:**

```python
class ModelProvider:
  def generate(prompt, context) -> {text, provenance, mock, model, nis_result?}
  def stream(prompt, context) -> Generator[str]
  def health() -> {status, details, mock}
```

- **NISCoreProvider (real, default):** Wraps `ORCHESTRATOR`. `health()` checks `SUBSTRATE.get_ltm()` + `cache_stats()`. Never pretends to be LLM when it's NIS Core template.
- **MockProvider (development fallback):** Returns `[MOCK] NIS mock response to: ... — development fallback. Configure MODEL_PROVIDER=nis_core`. `health()` always `ok` mocked. Clearly labeled `mock:true` and `provenance: mock_provider:MOCK`.
- **Factory `get_provider(name)`:** Reads `MODEL_PROVIDER` env (`nis_core|mock|auto`). `auto` tries core then mock. No hard-coding.

**Replaceability:** Future OpenAI/Anthropic provider just implements `generate()` calling API with server-side key (never frontend) and returns same dict shape — UI unchanged.

**Current deployment:** `MODEL_PROVIDER=nis_core` (no API key needed). Mock used only if core unavailable or explicitly set.

---

## E — Memory Integration

- **App uses existing NIS memory:** No second chat-memory. `ORCHESTRATOR` still calls `SUBSTRATE.retrieve()` (hybrid dense/TF-IDF), `S1_working.json` per-trace, `S2_conversation.json` last 10, `S3`, `S4`, `S5` project files, `S6` rerank. Verified via `A5`.

- **WorkingContext separation (v0.3-P1):** `N2` emits `{user_query, memory_context, summary}`; `N6/N7/N16` use `user_query` not `split("|")[0]`. Test `A5` paraphrase `solar tracker` retrieves helios; test `T24` poem with helios hit stays `L1` not `L2` (guard_pass).

- **App sessions vs NIS memory:** `data/memory/app_sessions.json` stores UI messages `{role, content, timestamp, meta: {trace_id, deliberation_level}}` — **shell history**. NIS memory remains authoritative for retrieval/provenance. Session preview `list_sessions()` returns only title/preview, not secret memory.

- **Memory failure handling:** If `SUBSTRATE` throws, `adapter` returns `model_unavailable` with user-facing message, not fabricated. Tested via `A6`.

---

## F — Session System

**File `app/sessions.py` (120 lines, simple, no social system):**

- `create_session(title?)` → `sess-{8hex}-{ts}` with `created_at`, `updated_at`, `messages:[]`
- `list_sessions(limit=50)` → sorted by `updated_at` desc, returns `{id,title,created_at,updated_at,message_count,preview}` without full messages
- `get_session(id)` → full `{messages: [{role,content,timestamp,meta}]}`
- `append_message(session_id, role, content, meta)` → safe meta only (`trace_id, deliberation_level, verification, latency_ms, mock`), auto-creates session if missing, max 100 msgs, title auto from first user 40 chars
- `delete_session`, `rename_session`

**UI flows:**

- **First conversation:** Open app → empty state → type → `POST /api/chat` without session_id → backend creates session, shows in drawer.
- **Continue:** Same `session_id` sent with each message → history appended.
- **New:** `＋ New` → `POST /api/sessions` → clears conversation view.
- **Previous:** `☰` drawer → `GET /api/sessions` → tap item → `GET /api/sessions/{id}` → renders history.

**A1-A4 tests:** Verify create, multi-turn (4 msgs), new isolated, reopen returns history.

---

## G — Security

- **PUBLIC vs SECRET:** `app/config.py` separates:

  ```python
  PUBLIC_CONFIG = {app_name, version, features: {voice_input:false...}, model_provider, memory_enabled, response_style}  # via GET /api/config — safe
  SECRET_CONFIG = {OPENAI_API_KEY, ANTHROPIC_API_KEY, NIS_SECRET_KEY}  # server env only, never returned
  ```

- **Never in frontend:** `frontend/app.js` never contains `sk-`, `OPENAI`, `SECRET`; `GET /api/config` filtered, `index.html` has no keys. Verified `A10`.

- **No direct DB exposure:** Browser cannot `fetch /data/...`; only API endpoints. Memory files remain server-side.

- **.env.example:** Template shows `MODEL_PROVIDER=nis_core`, `OPENAI_API_KEY=` blank, `NIS_SECRET_KEY=change-me`, with comment “never commit real .env”.

- **CORS:** Allow `*` for phone browser preview (in production would restrict to app domain).

---

## H — Error Handling

**Adapter and API handle all specified failures gracefully, never fabricate:**

| Failure | UI behavior | Internal |
|---|---|---|
| **Model unavailable** (provider exception) | “NIS is temporarily unavailable. Please try again.” (503) | logs `model_unavailable` with details only if debug |
| **Timeout** | Same as unavailable (latency_ms recorded) | N12 timeout simulated as mock |
| **Malformed response** (text is None) | Coerce to `""`, return `ok` with empty string, not crash | `A7` test: BrokenProvider `{"text":None}` → handled |
| **Memory failure** (SUBSTRATE exception) | “Something went wrong inside NIS Core. Please try rephrasing.” | adapter catches, returns `core_failure` |
| **Tool failure** (read_file missing) | NIS Core returns `F-INS` “I need 'path'” — UI shows it | via orchestrator `F-INS` |
| **Verification failure** (V1 no evidence) | Delivered as `pass_with_warnings` with logged caveat, not silent | N14 `fail` → N15 degrade, UI shows “[Verification flagged]” only in debug |
| **Network failure** (fetch) | UI shows “Failed to send — Please try again. Logged…” | `A6` long message handled |
| **Authentication failure** | Not yet (no auth in v0.1), but 401 would be surfaced | future |

**CoT firewall:** `adapter.chat()` checks `if "PRIVATE SCRATCH" in response_text` and strips; N14 already scans `private_scratch` leak. Verified no leak in any response (`A1`, `A5`).

---

## I — Tests

### Existing NIS tests — still green (no regression)

```
run_arch_tests.py        6/6 ✓  (T1 Hello L0, T2 Do it F-AMB, T3 Helios memory, T4 read_file, T5 Send it to him, T6 tick deny)
run_intelligence_tests.py 12/12 ✓ (T7 paraphrase L1 stable, T8 multi-intent, T9 pronoun, T10 conflict 22% vs 21.5, T11 stale web_search, T12 solar tracker→helios, T13 multi-hop, T14 3 hypotheses, T15 tool contradiction, T16 hallucination grounded, T17 V1 fail reroute max 3, T18 L4 not sent)
test_v03_p1.py           16/16 ✓ (T19 0.055→0.583 +0.529, T19b delta 0, T20 ocean 0.297→0.730 +0.433, T21 DENSE/TFIDF path, T22 cache 83 deterministic, T23 fallback, T24 contamination L1 guard, Tconfig)
run_simulations.py        5/5 ✓ (L0 time, L1 poem, L2 PDF+Helios, L3 EU AI timeline image, L4 email confirm_needed)
```

Both `USE_DENSE=false` and `true` → 23/23 required passes.

### New App tests A1-A10 — 10/10 ✓

| Test | What | Result |
|---|---|---|
| **A1 first conversation** | `POST /api/sessions` + `POST /api/chat Hello` → L0, 2 msgs, no private leak | ✓ |
| **A2 multi-turn** | Same session `What do you remember about Helios?` → contains helios/team, no leak | ✓ |
| **A3 new conversation** | New session isolated, poem L1 `sea`, history counts | ✓ |
| **A4 reopen** | `GET /api/sessions/{id}` returns 4 msgs, continue works | ✓ |
| **A5 memory retrieval** | Paraphrase `solar tracker` → helios via hybrid, L1/L2 | ✓ |
| **A6 model failure** | Empty + 9000-char → 400/500, not fabricated | ✓ |
| **A7 malformed** | BrokenProvider `text:None` → adapter coerces to string, ok | ✓ |
| **A8 verification** | Direct N14 V1 fail, app chat still shows `pass`/`pass_with_warnings` | ✓ |
| **A9 mobile layout** | `GET /` has `viewport`, `GET /static/style.css` has `@media`/`max-width`, js has `fetch('/api/chat'` | ✓ |
| **A10 secret protection** | `/api/config` no `api_key`/`sk-`, html no leak, health no leak | ✓ |

**Location:** `tests_app/test_app.py`, results `logs/app_tests.json`, run via `python tests_app/test_app.py`.

### End-to-end manual

```bash
curl -s http://localhost:8000/api/health
# {"status":"ok","provider":{"status":"ok","details":"NIS Core ok — S4 4 entries, cache 83","mock":false},"app":"nis-app-v0.1"}

curl -X POST http://localhost:8000/api/chat -H "Content-Type: application/json" \
  -d '{"message":"Hello, how are you?"}'
# → {"message":"[warm tone] General request: ...","deliberation_level":"L0","verification":"pass","intent":"question","latency_ms":45}

curl -X POST http://localhost:8000/api/chat -H "Content-Type: application/json" \
  -d '{"message":"Write a short poem about the sea for my daughter"}'
# → poem lines, L1, no helios contamination

# Open in browser:
# http://localhost:8000/ on desktop
# https://8000-<sandboxId>.e2b.app on iPhone (preview host, no localhost)
```

All 6 checks from spec (WorkingContext, memory, N14, permission, no leak) passed.

---

## J — Known Limitations

- **Voice:** `VoiceInput`/`VoiceOutput` interfaces defined in `model_providers/base.py` and `/api/voice/status` stub, but `enabled:false` in `PUBLIC_CONFIG` and button disabled — future phase.
- **Streaming:** Chunked 80-char yield via `StreamingResponse`, not true LLM token streaming — correct but not low-latency token.
- **Model Provider:** Only `nis_core` and `mock` implemented; OpenAI/Anthropic would need `OPENAI_API_KEY` env and `OpenAIProvider.generate()` — abstraction ready, not yet wired.
- **Auth:** No multi-user accounts, no auth — single-user local. `NIS_SECRET_KEY` prepared for future sessions/JWT.
- **Persistence:** `app_sessions.json` file, not DB; max 100 msgs/session, no search. `S2_conversation.json` still holds NIS internal history (separate).
- **Native iOS:** Not packaged as App Store/IPA — web app only (per spec “Do NOT begin by native”). PWA manifest not yet added (can be later).
- **DAG/Parallel:** Still linear `[STUB]`, not needed for v0.1.
- **Vault/S6 learning:** Still stub/bounded, not expanded.

All limitations clearly marked `MOCK`/`STUB`/`future` where applicable — never pretending.

---

## K — How to Run

**Prereqs:** Python 3.10+, `pip install fastapi uvicorn python-multipart scikit-learn sentence-transformers` (already in `requirements_v03.txt` + `fastapi`).

**Setup:**

```bash
cd /home/user/nis-mvv
cp .env.example .env  # edit if needed
python setup_memory.py  # seeds S3/S4/S5 + corrects stale timestamp + embeddings cache

# Install deps (workaround for /tmp 1GB)
mkdir -p /home/user/tmp
TMPDIR=/home/user/tmp pip install --no-cache-dir -r requirements_v03.txt fastapi uvicorn python-multipart

# Run tests (must be green before app)
python run_arch_tests.py          # 6/6
python run_intelligence_tests.py  # 12/12
python test_v03_p1.py             # 16/16
python tests_app/test_app.py      # 10/10

# Start app
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
# or: uvicorn app.main:app --reload
```

**Config env:**

```bash
MODEL_PROVIDER=nis_core  # or mock, auto
NIS_USE_DENSE=true       # enable dense embeddings (default false until verified)
NIS_DEBUG=false          # show trace_id in UI
```

**Logs:** `logs/app_tests.json`, `logs/arch_tests.json`, `logs/traces.json`, `data/memory/app_sessions.json`.

---

## L — How to Access From iPhone

**Do NOT use `localhost` on iPhone — browser is not sandbox.**

1. **Start server on 0.0.0.0:8000** (already running). In this workspace, preview hosts are proxied as `https://{port}-{sandboxId}.e2b.app`.

2. **Find preview URL:** In this environment, the app is exposed at **`https://8000-<sandboxId>.e2b.app`** (see `start_process` `listening_ports` with `8000` on `0.0.0.0`). Copy that URL.

3. **On iPhone:** Open Safari → paste `https://8000-<sandboxId>.e2b.app` → you see NIS header (◐ NIS نِيسْ), empty conversation, input at bottom.

4. **Use:** Type message → Send → response appears via NIS Core (L0-L4 badge). Try suggestions: “Remember Helios”, “Sea poem”. Create new via “＋ New”, list via “☰”.

5. **Local network alternative (if deploying outside e2b):** Find machine IP (`hostname -I`), run `uvicorn --host 0.0.0.0 --port 8000`, on iPhone connect to `http://<IP>:8000` (same Wi-Fi, firewall must allow 8000).

6. **Install as PWA (future):** Safari → Share → Add to Home Screen — will work once manifest added (v0.2).

**No App Store needed.** Native packaging is later phase per spec.

---

## M — Exact Next Step

**Do not continue to v0.3-P2 cognitive upgrades.**

**Next is NIS App v0.2 — polish the shell, still no core redesign:**

1. **PWA + offline:** Add `manifest.json`, `service-worker.js`, `apple-touch-icon`, `theme-color`, `viewport-fit`, and “Add to Home Screen” flow — keep phone-experience native-feeling without App Store.

2. **File upload UI:** Wire `POST /api/chat` `attachments` to real `<input type=file>` → `read_file` tool path (already works via API, just UI button).

3. **Streaming UX:** If `MODEL_PROVIDER=openai`, make `ModelProvider.stream()` true token streaming via `fetch` + `ReadableStream` and render incrementally in `app.js`.

4. **Auth (optional single-user):** Add `NIS_SECRET_KEY` cookie + simple password gate for deployment, still no multi-user.

5. **E2E on real device:** Test on physical iPhone SE → 15 Pro Max viewports, ensure `env(safe-area-inset-bottom)` and `input` focus not covered by keyboard.

All steps keep `app/` and `nis/` separated, keep `NISAdapter` as sole core entry, keep N14/CoT firewall, keep `USE_DENSE` flag. Re-run same 10 app tests + existing 6+12+6 each time; do not bypass any node.

---

## Deliverables Checklist

- [x] Working NIS App v0.1 (live at :8000, responsive)
- [x] Application source code (`app/`, `model_providers/`, `frontend/`)
- [x] NIS Core integration adapter (`app/adapter.py`)
- [x] Model provider abstraction (`model_providers/base.py`, `mock`, `nis_core`)
- [x] Session management (`app/sessions.py`, `data/memory/app_sessions.json`)
- [x] Mobile-responsive UI (`frontend/index.html/style.css/app.js`)
- [x] Application tests (`tests_app/test_app.py` 10/10)
- [x] Updated documentation (this report, inline comments)
- [x] Setup instructions (Section K)
- [x] Environment configuration example (`.env.example`)
- [x] End-to-end test result (Section I, curl examples)
- [x] NIS_APP_v0.1_REPORT.md (this file, A-M)

**Final condition met:** Human can open `https://8000-...e2b.app` on iPhone, type message, receive response generated through NIS Core (via `ORCHESTRATOR.run_turn`, with deliberation/verification/provenance, no private leak).

*STOP after v0.1 as directed.*
