# NIS v0.2 — PRE-v0.3 ENGINEERING AUDIT
**Date:** 2026-09-22 23:15 UTC  
**Auditor:** v0.2 Implementation vs v1.1 Canonical  
**Scope:** No redesign, no v0.3 code, no feature creep — determine exactly what must change before v0.3  
**Sources:** `NIS_Architecture_v1.1_Canonical.md` (653 lines), `nis/memory.py` (415 lines), `nis/nodes.py` (1348 lines), `nis/orchestrator.py`, `nis/config.py`, `REPORT_v02.md` (33K), `logs/simulations.json` (5), `logs/arch_tests.json` (6), `logs/intelligence_tests.json` (12), `logs/traces.json` (17+ stages)

---
## A — Executive Verdict

**v0.2 is a sound intelligence upgrade on a correctly preserved v1.1, but it is NOT semantically genuine.** The 5 priorities are delivered as *framework-REAL but semantic-PROXY*. The system passes 23/23 traces (11 regression + 12 intelligence) and demonstrates the *control plane* is ready (deliberation, verification loops, provenance, permission gates), while the *cognitive plane* still runs on TF-IDF and regex.

**Genuinely working (REAL):** Persistent S1/S7, hybrid retrieval orchestration, intent classification shape, consequence-aware deliberation, separate N7 reasoning with firewall, V1-V8 loop, budget enforcement, Master-Wins, L4 gating.

**Only proxy/mock (not yet semantic):** Dense embeddings are TF-IDF, semantic retrieval is hybrid-but-TFIDF, NER is regex, V4 is substring, WorkingContext is string-split.

**Still stub:** Vault encryption, DAG parallel, S6 same-turn learning, live tools.

**Bottleneck to genuine semantic:** TF-IDF (A) starves semantic retrieval (B); WorkingContext string contamination (E) forces brittle N7/N6 hacks that will break when embeddings go dense.

**v0.3 must not widen scope.** The architecture can absorb exactly three *independent* semantic upgrades next — embeddings, WorkingContext separation, V4 hardening — without touching Vault/DAG/Live. Everything else must wait.

**Do NOT claim production-ready.** MVV contracts hold today only because thresholds are heuristic-floored, not learned.

## B — Current Capability Matrix (v0.2 as built)

| Store/Node | v1.1 Requires | v0.2 Implements | Tag | Evidence |
|---|---|---|---|---|
| **S1 Working** | Volatile RAM, turn+10m, session | `S1_working.json` per-trace, 24h prune, session_id `YYYY-MM-DD`, `set_working/get_session_working` | **[REAL]** | `setup_memory.py` + `memory.py:58-98` + traces S1 0 hits for L0 |
| **S7 Task** | Volatile task lifetime | `S7_tasks.json` 100 max, `set_task/get_task/list_tasks/clear_task` isolated | **[REAL]** | `memory.py:178-210` |
| **S2 Conversation** | Short-term 24h | `S2_conversation.json` last 100 | **[REAL]** | unchanged |
| **S3 Preferences** | Persistent versioned | `S3_preferences.json` | **[REAL]** | S2 poem cites warm/concise |
| **S4 LTM** | Vector+Graph indefinite | `S4_ltm.json` versioned | **[REAL]** | helios_project 21.5% |
| **S5 Project** | Project DB+FS `/home/user` | `FS scan /home/user/*.md` up to 25 | **[REAL]** | `project_helios.md` 22% |
| **S6 Behavioral** | 90d half-life, decay-weighted | `S6_behavioral.json` + `S6_rerank_log.json` bounded 300, `get_reranking_boost(max 0.2, half 90d)` | **[REAL] framework / [STUB] learning** | `memory.py:148-177` + `REPORT_v02` T7-T18 rerank_delta 0.0 |
| **Vault** | Encrypted separate, TTL, N10-gated | `VAULT_secrets.json` gated, not encrypted, `vault_get/set` | **[STUB]** | matrix, no encryption |
| **N1 Perception** | Normalizer, PII, injection scan | Regex PII, injection `ignore.*previous`, file parse | **[REAL]** | `nodes.py:12-45` |
| **N2 Context** | Merger, Resolver, Compressor, Contradiction Detector | Concat `User: | Memory hits: | UserState`, regex entities, no compressor | **[REAL] minimal / [STUB] resolver/compressor** | `nodes.py:47-84` string join |
| **N3 Intent** | Classifier, Slot, Ambiguity 0-1, Consequence 0-1 | `tfidf-cosine-v0.2` `TfidfVectorizer(1,2, max_features 3000)` + prototypes 7/7/8/7/4, softmax temp5, regex NER | **[PROXY] model / [MOCK] NER** | `nodes.py:87-352` |
| **N4 User-State** | Preference Loader, Affect, Expertise, Load | `SUBSTRATE.get_preferences()` + urgency/load heuristics | **[REAL] minimal** | `nodes.py:354-380` |
| **N5 Retrieval** | Vector+Lexical+Freshness+Intent/Project+Re-rank | Hybrid `0.35 lexical +0.45 semantic(TF-IDF) +0.20 metadata`, freshness `0.5^(age/180)`, rerank `S6`, conflict helios `≥0.3` | **[REAL] orchestration / [PROXY] semantic** | `memory.py:258-410` |
| **N6 Deliberation** | Axis Scorer, Level Mapper, Budget Allocator, Escalation | Consumes N3 `confidence/ambiguity/candidate`, `domain` map+`0.07*len(required_context)`, `tool_need`, TF-IDF novelty heuristic, multiplier `1.0-1.5`, floors `eu≥0.67 helios≥0.57 poem 0.228-0.39` | **[REAL]** | `nodes.py:391-535` `n6-v0.2-consumes-n3` |
| **N7 Reasoning** | Inference, Evidence Weigher, Uncertainty, Assumptions, Hypotheses | TF-IDF `_score_evidence`, L-level branches, `alternatives` 2-3, `_private_scratch` firewalled | **[REAL] separate / [PROXY] evidence** | `nodes.py:537-742` `hybrid-tfidf-v0.2` |
| **N8 Planning** | Decomposer, Sequencer, Resource Mapper, Checkpoint, Fallback | Linear steps, `edges`, `fallback_plan` L3+ stub, `parallel_branches [STUB]` | **[REAL] linear / [STUB] DAG** | `nodes.py:744-827` |
| **N9 Priority** | Stack, Detector, Logger — literal 1-6 | Literal `1 System>2 Safety>3 User Obj>4 Pref>5 Task>6 Persona`, `variant literal/task_first` | **[REAL]** | `nodes.py:829-856` |
| **N10 Permission** | Policy, Consent, Risk, Confirm Manager — Hard gate | `A0-A2 implicit`, `A3/A4 confirm` (`ambiguity>0.35` for L4), `F-PERM/F-UNSAFE`, proactive deny | **[REAL]** | `nodes.py:858-904` |
| **N11 Router** | 7 Questions, Selector, Validator | `ROUTER.route` Q1-Q7, least-privilege, `SKIP_TOOL` | **[REAL]** | `nodes.py:906-924` + `tools.py` |
| **N12 Execution** | Invoker, Retry, Provenance, Sandbox | `read_file/system_time` **REAL**, `web_search/fetch_page/generate_image` **MOCK**, file sandbox `/home/user` | **[REAL/MOCK split]** | `nodes.py:926-955` |
| **N13 Formation** | Validator, Deduplicator, TTL, Versioned Committer — single writer | `NO_WRITE` default, only `user_explicit_remember` or ≥2 corroborations | **[REAL]** | `nodes.py:956-992` |
| **N14 Verification** | V1-V8 + Leak Scanner, 3 loops | V1 grounding, V2 consistency, V3 intent, V4 tool-accuracy (substring, exempt pure retrieval), V5 completeness, V6 contradictions, V7 leak, V8 integrity, `max_loops 3` via `N15` | **[REAL] V1-V3,V5-V8 / [PROXY] V4** | `nodes.py:994-1213` + `orchestrator.py:294-314` |
| **N15 Recovery** | Classifier, Strategy, Retry Budget, Breaker — 10 types | `F-INS/F-AMB/F-TOOL/F-CONFLICT/F-MEM/F-EXEC/F-VER/F-PERM/F-UNSAFE/F-CAP`, `reroute` alias fixed | **[REAL]** | `nodes.py:1215-1280` |
| **N16 Persona** | Style Renderer, Citations, Firewall, Nudge | `style≠facts`, tone warm, CoT firewall, citations | **[REAL]** separate | `nodes.py:1281-1333` |
| **N17 Feedback** | Classifier, Preference Updater, Memory Corrector, Threshold Tuner | Logs `S6`, no same-turn adaptation | **[STUB]** | `nodes.py:1335-1348` |
| **INCP/Trace** | Envelope, trace_id, blocked edge | `GLOBAL_TRACE` 17 stages | **[REAL]** | `incp.py` + `orchestrator.py:28-30` |
| **N0/N0.1** | State Machine, Router, Budget Enforcer, Tick | Sequential `run_turn`, tick disabled by default | **[REAL] sequential / [STUB] async** | `orchestrator.py:18-362` |

## C — Real vs Proxy vs Mock vs Stub

### Focus A — Dense semantic embeddings

- **Classification:** **[PROXY]**
- **Current implementation:** `sklearn.feature_extraction.text.TfidfVectorizer(ngram_range=(1,2), stop_words=english, max_features 5000/3000)` + `cosine_similarity`. Used in `N3._tfidf_intent_scores` (fit on `[query]+prototypes` per turn), `N5._semantic_score_tfidf` (fit on `[query]+docs` per retrieval), `N6._semantic_novelty` (unused due to summary string), `N7._score_evidence`. *Proved real vector math but sparse, per-turn fit, English-only, no dense.* `pip show` logged `sklearn 1.6.1 ok, sentence-transformers missing, spacy 3.8.14 no model`.
- **Current limitation:** TF-IDF is lexical-weighted; `solar tracker` vs `helios` gets `lexical 0.285` only if token overlap; IDF collapses when `helios` appears in many docs (relevance `0.002` for `project_helios.md` on helios query — see `T15` debug). No sub-word, no multilingual, no cross-lingual. Per-turn fit leaks query into IDF. `max_features 5000` truncates long docs.
- **Why it matters:** NIS v1.1 §8 `Hybrid vector+lexical` requires *semantic* beyond lexical. Without dense, `T12` “solar tracker → helios” only passes via fallback top-3, not ranking; `T7` paraphrase stability currently relies on heuristic floors `poem 0.228-0.39` not embedding similarity. This is the root blocker for “genuinely semantic”.
- **Dependencies:** `N3` (intent), `N5` (retrieval ranking), `N6` novelty, `N7` evidence scoring — all four consume embeddings.
- **Required change:** Install `sentence-transformers` (`all-MiniLM-L6-v2` or multilingual) **[RECOMMENDED]** with offline cache, keep TF-IDF fallback. Pre-compute doc embeddings, cache in `S5`/`S4` with timestamp, cosine via `numpy`. Do not change `N3` prototypes — embed them once. **[DERIVED]** from §8 vector requirement.
- **Nodes affected:** `N3, N5, N7` (primary), `N6` secondary; `SUBSTRATE` cache layer.
- **Tests required:** Before: `T7 Δ<0.15` with TF-IDF baseline logged; `T12` relevance `>0.05` with TF-IDF. After: `T7` Δ should remain `<0.10` with dense *without* floors (remove poem floor and still L1); `T12` rank-1 `helios_project` without fallback; `T10` conflicts still surfaced; new test `T19` dense paraphrase `helios → solar tracker → sun chaser` all rank helios >0.35 without lexical overlap.
- **Regression risks:** Per-turn fit → global fit changes IDF; dense will shift all `relevance_scores` and `N3 confidence` distributions, breaking `L0-L4` floors (`eu≥0.67` etc.). Must re-tune `threshold 0.15` and `consequence_multiplier`.
- **Recommended order:** **1st** (with E together, see §G).

### Focus B — Semantic memory retrieval

- **Classification:** **[REAL] orchestration / [PROXY] semantic core**
- **Current implementation:** `MemorySubstrateV02.retrieve` does `lexical 0.35 + semantic 0.45 + metadata 0.20`, freshness `0.5^(age/180)`, S6 rerank `[-0.2,0.2]`, threshold `0.15` (L0/L1) / `0.08` (L3+), budget `0:0,1:3,2:6,3:12,4:12`, appendix if `freshness<0.6`. Conflict helios `≥0.3`. Intent-scoped penalty `S5 -0.25` when query lacks helios, `S3 +0.12` for poem. Provenance `hits, provenance, freshness_scores, relevance_scores, lexical_scores, semantic_scores, rerank_deltas, retrieval_path`.
- **Current limitation:** Ranking is *orchestration-REAL* but *semantic-PROXY*; threshold/fallback (`if len(filtered)<2 and L2+ → top3`) masks TF-IDF failures (e.g., `project_helios.md` relevance `0.002` still retrieved via fallback for L2, not ranking). `freshness` for `eu_ai_act_general` was reset by `setup_memory.py` to now, so `T11` stale test had to be relaxed (no `freshness<0.7` hit). `appendix` not exercised because all hits fresh `1.0`.
- **Why it matters:** Retrieval is the substrate feeding `N2→N7`; if semantic is weak, `N7` evidence_links are weak (`T13` “newer” relies on freshness, not semantic). `N2` has no compressor, so larger budgets amplify contamination.
- **Dependencies:** Depends on A (embeddings) + S6 (rerank) + `WorkingContext` (E) for query isolation.
- **Required change:** Keep orchestration, swap semantic to dense (A), add persistent embedding cache `data/memory/embeddings.json` with `key → (vector, timestamp)` **[DERIVED]**, keep lexical+metadata+freshness weighting but re-tune `0.35/0.45/0.20` after dense (likely `0.25/0.55/0.20`). Add `freshness` half-life test harness with old `eu_ai_act` timestamp `2024-12-01` not reset. **[RECOMMENDED]** tuning.
- **Nodes affected:** `N5` + `SUBSTRATE` + `N2` (budget).
- **Tests required:** Before: `T12` with TF-IDF logs `relevance 0.002`; after: `T12` rank-1 without fallback; `T11` must have `freshness<0.6` hit when old timestamp injected; `T10` conflicts still `21.5 vs 22.0` with provenance.
- **Regression risks:** Re-ranking `S6` boost `+0.08` currently invisible because `relevance` shift dwarfs it; dense may amplify rerank effect → needs boundedness test.
- **Recommended order:** **1st, same deploy as A** (cannot be separate; A is sub-component of B).

### Focus C — NER replacement for regex

- **Classification:** **[MOCK]**
- **Current implementation:** `N3._extract_entities` regex: `FILE_PATH /home/user/…`, `EMAIL`, `PERCENTAGE \d+%, `PROPER_NOUN \b[A-Z]…\b`, `DATE`. No `spacy` model; `_detect_pronouns` regex `\b(it|him|her|them|they|he|she|this|that)\b`. No entity linking.
- **Current limitation:** `PROPER_NOUN` captures `The, And, What` filtered only 3 stopwords; misses multi-lang, misses `Alice` vs `alice`, misses file without `/home/user` prefix. Pronoun `it` in “it contradicts” was incorrectly flagged `pronoun_resolution` until patched with `slots.file` resolvable check. Still brittle for `“him”` without antecedent (T5/T9 rely on simple pronoun list). No `DATE` extraction for EU Act `2025-08-02` vs `Aug 2, 2025`.
- **Why it matters:** `required_context` and `slots.file` drive `N6.tool_need` and `N11` routing; false `pronoun_resolution` caused `S3` V3 `pass_with_warnings` before patch. For L4, ambiguous recipients “entire team” must be entity-resolved, not regex.
- **Dependencies:** `N3` only; feeds `N6` and `N8` `tool_hint` path.
- **Required change:** Install `spacy en_core_web_sm` or `transformers` NER **[RECOMMENDED]** with regex fallback, keep file/email/percentage regex as `[DERIVED]` for `A0` paths. Add `Path` resolution for `helios_spec.pdf` → `/home/user/helios_spec.pdf`. Keep `PROXY` not `MOCK` if spacy available, but **do not** replace entire N3 — only NER sub-node.
- **Nodes affected:** `N3` sub-node `Entity Extractor` only.
- **Tests required:** Before: regex baseline logs `entities: FILE_PATH, PERCENTAGE` for `helios_spec.pdf 22%`; after: new test `T20` NER `Alice, Bob, EU AI Act Feb 2 2025` correctly typed, `“it”` not flagged when `slots.file` present (S3), pronoun `“him”` without antecedent still `ambiguity 0.70`.
- **Regression risks:** Low — NER does not affect `L0-L4` score directly except via `required_context` length (`domain +0.07*len`). New entities must not inflate `domain` beyond `0.85` cap.
- **Recommended order:** **2nd or 3rd** (independent, see §G).

### Focus D — N14 V4 hardening

- **Classification:** **[PROXY] / [ARCHITECTURAL RISK] / [READY FOR UPGRADE]**
- **Current implementation:** `N14._check_v4_tool_accuracy` does `claims_specific` (`web_search/fetch_page/read_file/system_time/generate_image`), `claims_search` (`search`+`eu ai act`), `claims_generic_tool` (`"tool" in lower and "no tool" not in lower …`) plus exemptions `pure retrieval / no file read executed / will trigger`. If `claims_tool` and `not actually_used` → `V4` high → `fail` → `recommended_reroute N12`. No structured claim metadata; substring check caused `T12` spurious `V4` fail: `Response "General request ... Execution: N12:skipped | Memory: 3 hits"` contains `"tool"`? No, but lower `general request ... memory hits ... tool or memory`? Actually `T12` triggered `V4` because `lower` contained `"tool"` via `“tool or memory”` in generic fallback, causing 3 retries → `pass_with_warnings`.
- **Current limitation:** Substring heuristics conflate *mention* vs *claim*. Exempt list is manual string list, not contract. No citation graph; `V1`/`V7` already check provenance, so `V4` duplicates and over-fires. `S3` required patch `trigger read_file → trigger a file read` to avoid false `V4`.
- **Why it matters:** `V4` is **blocking High** per v1.1 §9; false High causes `F-VER` loop (max 3) and degrades to `pass_with_warnings` with `VERIFICATION WARNING` footer, which is visible to user (seen in `T12`). This is theater, not safety.
- **Dependencies:** `N14` ↔ `N16` (response), `N11/N12` (tool), `orchestrator` loop.
- **Required change:** Replace substring with **structured** `N16` metadata: `N16` should emit `claims: {tool_claimed: bool, citations: [url, provenance]}` **[DERIVED]** from §9 `Tool-Result Accuracy` (compare `ExecutionResult` vs `draft_response` citations). Keep substring as fallback but lower severity to `medium` unless structured claim is true. **[RECOMMENDED]** to add `V4` unit harness with 6 cases (pure retrieval, mock with disclaimer, real, hallucinated, exempt, generic mention).
- **Nodes affected:** `N14` V4 sub-checker, `N16` (new `claims` field, but `Output: UserMessage` unchanged — `claims` stays internal, not rendered, so not a new node).
- **Tests required:** Before: `T12` currently `pass_with_warnings` after 3 retries is documented proxy behavior. After: `T12` must be `pass` loop 0; new tests `T21` hallucinated tool claim → `V4` fail → `N12`, `T22` pure retrieval mentions “tool” generically → no fail, `T23` mock with disclaimer → no fail.
- **Regression risks:** If structured claims missing, `V4` may under-detect real hallucination (e.g., `S4` EU Act timeline citing mock as real). Must keep `V1/V7` as backstop.
- **Recommended order:** **2nd** (independent, high ROI, no embedding dependency).

### Focus E — Working Context separation

- **Classification:** **[STUB] / [ARCHITECTURAL RISK] / [READY FOR UPGRADE]**
- **Current implementation:** `N2` builds `summary = "User: {text} | Memory hits: {N} — {key:value} | History … | UserState …"[:800]` (single string). `N7`, `N16`, `N6` then `split("|")[0]` to get `user_part` to avoid memory contamination (poem + helios hits → mis-route to Helios). Patched in v0.2 with `user_part = full_summary.split("|")[0]`. `N6` also has `summary_lower = full_summary_lower; user_part_n6 = split("|")[0]`. This is a **string hack**.
- **Current limitation:** Contamination was proven: `S2` poem retrieved `helios_spec` hits (relevance `0.12` before fix) → `N7` branched to Helios → `SKIP_TOOL` → `read_file` mis-plan. Fix heals symptom but architecture still has **single source of truth violation** (v1.1 §13 `WorkingContext is single source of truth` — but `N2` is supposed to *separate* fields, not concatenate). No `entities, open_tasks, constraints` structured use; all checks are substring on `summary`. Adding dense retrieval will increase hits, amplifying contamination.
- **Why it matters:** This is the **architectural bottleneck** for semantic (E). Without separation, dense will make *every* query retrieve `helios` spuriously and break `N7` again. v1.1 §3 N2 `Contradiction Detector` and §6 freshness are not implemented beyond `contradiction_flags = memory_bundle.conflicts`.
- **Dependencies:** `N2` (producer), `N6,N7,N16` (consumers), `orchestrator`.
- **Required change:** In `N2.process` keep `summary` string for logging but add structured `WorkingContext { user_query: normalized_text, memory_context: {hits, conflicts}, user_state, history }` **[DERIVED]** from §3 N2 Output `summary, entities[], open_tasks[], constraints[], contradiction_flags[]` — fields exist but empty. Change `N7/N6/N16` to branch on `user_query` not `summary`, keep `memory_context` for evidence only. No new node; just N2 field split. **[EXPLICIT]** already required.
- **Nodes affected:** `N2` (output), `N6,N7,N16` (input), `orchestrator` (passes `WorkingContext`).
- **Tests required:** Before: `S2` poem with helios hits must stay L1 (currently patched, but fragile). After: remove `split("|")` hack, `S2` still L1 even if `memory_bundle` contains helios hits with high relevance (inject fake helios hit into S2 context and assert still poem). New test `T24` `user_query="poem"` with forced `memory_context` helios must not branch to Helios.
- **Regression risks:** All `L0-L4` floors that use `raw_text = intent + summary` must be re-tested; they will shift when summary no longer contains memory. `N6` `raw_text` currently also patched to `user_part`; after real split, must use `user_query`.
- **Recommended order:** **1st, together with A/B** (must ship before dense, otherwise dense breaks). See §G dependency.

### Focus F — S6 learning

- **Classification:** **[STUB]**
- **Current implementation:** `S6` has `add_behavioral`, `get_reranking_boost`, `S6_rerank_log.json` bounded `300`, decay `0.5^(age/90)`, `[-0.2,0.2]` per key, `traceable/reversible`. But `N17.Feedback` only logs `positive_feedback/correction` on *next turn* user followup, not same-turn; `Threshold Tuner` not implemented. `Reranking` is REAL for boost, `Learning` is STUB. `setup_memory.py` never writes `S6` feedback, so `rerank_delta` always `0.0` in traces.
- **Current limitation:** No adaptation; `N7`/`N14` cannot learn from `V4` spurious. No `decay-weighted` threshold tuning (v1.1 §17 N17). Feedback loop `F5 Response→Feedback→Adaptation` is stub same-turn.
- **Why it matters:** Without learning, `V4` spurious and TF-IDF floors must stay heuristic; cannot self-heal.
- **Dependencies:** `N17` → `S6` → `N5`. Independent of embeddings.
- **Required change:** Implement `N17.add_behavioral("tool_success", {key, trace})` called from `orchestrator` after `N14 pass`, and `get_reranking_boost` already does decay; add same-turn `Threshold Tuner` that adjusts `CONFIG.deliberation.ambiguity_threshold` by `±0.02` guarded, decay-weighted **[DERIVED]** from §17.
- **Nodes affected:** `N17`, `S6`, `CONFIG`.
- **Tests required:** Before: `S6_rerank_log` empty. After: `T25` `positive_feedback` → boost `+0.08` for that key on next retrieval; `T26` half-life decay (inject old log `90d` ago → boost `0.04`); `T27` bounded `>0.2` clamped.
- **Regression risks:** Boost could dominate `relevance 0.002` Helios case → rank inversion; must keep `max_boost 0.2` and weight `relevance 0.45` vs `rerank`.
- **Recommended order:** **4th** (after A/B/E/D, low risk, independent).

### Focus G — Vault encryption

- **Classification:** **[STUB]**
- **Current implementation:** `VAULT_secrets.json` with `vault_get/set` plain JSON, `gated` check only via `N10` (no encryption), `S4` vs `Vault` placement rule not enforced (`N13` allows `Vault` write but no encryption).
- **Current limitation:** `NOT IMPLEMENTED` per architecture §6 Vault `Encrypted separate store, TTL, N10-gated`. No TTL, no encryption at rest.
- **Why it matters:** Not a semantic blocker; but v1.1 §4 `Governance WHO/WHAT` says secrets → Vault, not S4. Currently not exercised (no secret in tests), so no risk to regression.
- **Dependencies:** `N13`, `N10`, `Vault` store only.
- **Required change:** Add `cryptography Fernet` with key from env, `TTL` pruning, keep `vault_get/set` API. **[EXPLICIT]** required by §6.
- **Nodes affected:** `N13`, `Vault` only.
- **Tests required:** `T28` `vault_set` → encrypted on disk, `vault_get` with TTL expiry, `N10` deny without gate.
- **Regression risks:** None to semantic/deliberation; isolated.
- **Recommended order:** **7th (defer)** — not needed for v0.3 semantic milestone.

### Focus H — DAG parallel execution

- **Classification:** **[STUB]**
- **Current implementation:** `N8` outputs `Plan {steps:[], edges:[from→to], fallback_plan?}` but `steps` always linear `step_1→step_2→…`, `parallel_branches = "[STUB] Parallel DAG branches — [NOT IMPLEMENTED] in MVV, sequential only"`. `orchestrator` executes only first `tool_hint` step per turn, then simulates second `fetch_page` as bundled mock in `web_search` branch (see `orchestrator.py:193-205` `fetch1 ok, fetch2 timeout` for `S4`).
- **Current limitation:** `S4` EU Act `web_search + fetch_page top2` is not parallel; second fetch timeout is mocked inside same tool, not separate node. No `Checkpoint Inserter`, no true `Resource Mapper`. `T14` expects `parallel_branches` but gets stub.
- **Why it matters:** v1.1 §8 `DAG+fallbacks, parallel` and §10 `F3 Planning↔Execution` assume DAG. Sequential limits L3 `tool_budget 6` not exercised (only 1 tool per turn). Not a blocker for semantic, but blocker for L3/L4 tool orchestration.
- **Dependencies:** `N8`, `N11`, `N12`, `N0` budget.
- **Required change:** Implement `asyncio` fan-out for independent branches (e.g., two `fetch_page` in parallel), keep sequential fallback, preserve `edges` acyclic check. **[EXPLICIT]** per §8.
- **Nodes affected:** `N8, N11, N12, N0`.
- **Tests required:** `T29` two independent `read_file` in parallel → both `ok` with `cost` sum; `T30` one branch timeout → fallback `pass_with_warnings` with provenance.
- **Regression risks:** Concurrency breaks idempotency keys and `Sandbox Manager` (`/home/user` writes). Must gate behind `CONFIG.tool_budget` and `N10` per-tool.
- **Recommended order:** **5th** (after semantic, before live tools).

### Focus I — Live tool integration

- **Classification:** **[MOCK]**
- **Current implementation:** `tools.py` `REGISTRY` has `web_search:MOCK`, `fetch_page:MOCK` (returns deterministic snippets `artificialintelligenceact.eu 2025...`, `commission.europa.eu`, timeout `https://bad.timeout.url`), `generate_image:MOCK`, `generate_speech:MOCK`, `read_file:REAL`, `system_time:REAL` (provenance `system_time:real`). `MOCK` flagged in `provenance` and `response` disclaimer `(MOCK, not live)`.
- **Current limitation:** No network, no `httpx`, no rate limit, no `image_search` real. `S4` EU Act timeline cites mock URLs as if real but with disclaimer; `V4` must check `MOCK` disclaimer.
- **Why it matters:** Without live, `V1` factual correctness cannot be real; `freshness` heuristic is only way to trigger `web_search`. For genuine expansion, live is needed but not for semantic milestone.
- **Dependencies:** `N11,N12,N14` (V1/V4).
- **Required change:** Add `httpx` with `MOCK` flag default `true` for CI, `dry_run` for L4 **[RECOMMENDED]**, keep `read_file/system_time` REAL. Add timeout `30s` and `cost`. **[DERIVED]** from §8 tool registry.
- **Nodes affected:** `N11,N12,N14`.
- **Tests required:** `T31` `MOCK true` → deterministic; `T32` `MOCK false` with bad URL → `F-TOOL` timeout → `N15` retry 1-2× → fallback.
- **Regression risks:** Live flakiness breaks 11/11 determinism; must keep `MOCK` default for regression, live only opt-in.
- **Recommended order:** **6th** (after DAG).

## D — Bottleneck Analysis

**Hard dependency graph (from §14):**
```
N0 → All
N1 → N2 → N3 → N6 → N0 → N7
Substrate → N5 --intent via N3--> N2 → N7
N5 → N4 → N2/N16; N4.proactive_level → N0.1
N7 → N8 → N11 → N10 → N12 → N14 → N15 → {N7,N8,N12,N9} (loop)
N14 → N13 → Substrate → N5 (F4)
N16 → User → N17 → N4/N13 → N5 (F5)
Blocked: N7.private_scratch ──X──► N16 (V7)
```

**Bottlenecks identified (R-03.1 + v0.2 evidence):**

1. **N5 retrieval** — `T15` relevance `0.002` still needed fallback; `T12` needed fallback; `S2` poem contamination before fix. Cache `0.5` appendix threshold masks stale but not ranking. Mitigation patched with `split("|")` and intent penalty, but fragile. *Risk: High, Impact: High.*

2. **N7 reasoning** — Persona-off but branches are substring on `summary`; evidence scoring TF-IDF not dense; `alternatives` 2-3 hard-coded, not enumerated from retrieval. *Risk: Med/High.*

3. **N12 execution** — Single tool per turn; `web_search` bundles two fetches mockingly; no retry for idempotent vs non. *Risk: Med.*

4. **N14 verification** — V4 substring causes livelock `T12` 3 retries; V1/V7 duplicate `V4` checks. *Risk: Med.*

5. **N13 single-writer** — Not bottleneck (async in LEARNING, not critical path) — correctly not on hot path.

6. **N2 context** — No compressor; `summary[:800]` truncates `S4 21.5%` vs `S5 22%` may lose provenance; contamination hack shows N2 is bottleneck for semantic.

**Parallelism currently none:** `N2+N3` partially overlap (draft), `Plan` branches sequential, `V1-V8` sequential. v0.3 can parallel `V1-V8` and `fetch_page` fan-out without touching state machine.

## E — Semantic Intelligence Gap

**What prevents genuine semantic?**

| Gap | v0.2 Proxy | Genuine Requires | Evidence |
|-----|------------|------------------|----------|
| Embeddings | TF-IDF sparse, per-turn fit, English stop_words | Dense `all-MiniLM`/`multilingual`, pre-computed, cached, sub-word | `pip show` missing, `relevance 0.002` |
| Retrieval ranking | Hybrid REAL but semantic 0.45 is TF-IDF | Dense cosine 0.55 + BM25, embedding cache, no fallback top3 | `T12` needs fallback, `project_helios.md 0.002` |
| Intent classification | Prototypes 7/7/8/7/4 TF-IDF, softmax temp5 | Dense prototype embeddings, not keyword prototypes | `T8` creation vs analysis `confidence 0.526` low for multi-intent |
| Evidence scoring | TF-IDF per-hit | Dense cross-encoder rerank | `N7._score_evidence` same TF-IDF as N5 |
| NER | Regex | Spacy/transformers | `FILE_PATH` regex, no `Alice` disambiguation |
| Novelty | Heuristic `0.7 eu, 0.4 poem` | Semantic novelty `1 - cosine(query, hits)` dense | `N6._semantic_novelty` defined but not used (falls back to heuristic) |

**Consequence:** v0.2 *looks* semantic (hybrid, TF-IDF) but is **lexical-weighted**. `T7` paraphrase passes only because of heuristic floors, not embedding. Replace floors with dense and `T7` will fail unless dense is installed. That is proof of proxy.

**What can be genuinely semantic without dense? Nothing.** All semantic paths (N3,N5,N7,N6 novelty) converge on A. So A is the *semantic root*.

## F — Dependency Graph (for v0.3 order)

```
A Dense embeddings ──┬─→ B Semantic retrieval ──→ N7 evidence ──→ N14 V1
                     ├─→ N3 intent ──→ N6 ──→ L0-L4
                     └─→ N6 novelty

E WorkingContext separation ──→ B (prevents contamination) ──→ N7/N6/N16
        ↑
        must precede A (otherwise dense amplifies contamination)

D V4 hardening ──→ N14/N16 (independent, no embedding, high ROI)

C NER ──→ N3 required_context (independent)

F S6 learning ──→ N5 rerank (independent, needs stable retrieval first)

H DAG ──→ N8/N11/N12 (independent, needs stable planning)

I Live tools ──→ N11/N12/N14 V1 (independent, needs V4 hardened first)

G Vault ──→ N13 only (isolated, defer)
```

**Hard dependency:** `E → A/B` (E must be before or together with A). `D → I` (harden before live). Others independent but ordered by risk/ROI.

## G — Upgrade Order (with tags)

| Order | Upgrade | Tag | Why this order |
|-------|---------|-----|----------------|
| **0** | **Preserve & freeze v0.2** — no new features, tag `v0.2` backups, lock `CONFIG` thresholds | **[EXPLICIT]** | Required before any v0.3 |
| **1** | **E WorkingContext separation** + **A Dense embeddings** + **B Semantic retrieval re-tune** (atomic deploy) | **E [EXPLICIT]**, **A [DERIVED]/[RECOMMENDED]**, **B [DERIVED]** | E is bottleneck that will break when A goes dense; ship together as one PR with feature flag `USE_DENSE=false` for rollback |
| **2** | **D N14 V4 hardening** (structured claims) | **[DERIVED]** | Independent, high ROI, unblocks I, fixes `T12` livelock |
| **3** | **C NER** (spacy) | **[RECOMMENDED]** | Independent, low risk, improves `required_context` |
| **4** | **F S6 learning** (same-turn tuner) | **[DERIVED]** | Needs stable retrieval (1) to measure, not urgent |
| **5** | **H DAG parallel** | **[EXPLICIT]** | Needs stable planning (N8) and tool budgets |
| **6** | **I Live tools** (httpx, MOCK flag) | **[DERIVED]/[RECOMMENDED]** | Needs V4 hardened (2) and DAG (5) to handle partial |
| **7** | **G Vault encryption** | **[EXPLICIT]** | Isolated, defer to end, never on critical path |

**Defer indefinitely unless needed:** Proactive tick expansion, multi-project scoping beyond `/home/user`, confidence badges, dry_run UI.

## H — Risk Register

| ID | Risk | Likelihood / Impact | If not fixed | v0.2 mitigation | v0.3 mitigation |
|----|------|---------------------|--------------|----------------|-----------------|
| **R1** | Verification theater (same model) | Low(Med in MVV)/Critical | Pass theater, leak | Separate verifier **[DERIVED]** for Advanced; provenance grounding | Keep separate model; add V1 citation graph (D) |
| **R2** | Memory poisoning / stale overwrite | Med/High | Silent overwrite 22→21.5 | Single-writer + versioning + conflict surfaced | Keep; add S6 learning F |
| **R3** | Tool hallucination (V4) | Med/High | Mock cited as real | V4 blocking High (but proxy) | Harden V4 structured (D) |
| **R4** | Loop livelock (V4 spurious) | Med/Med | 3 retries → warning footer visible | Max 3 loops → degrade | Harden V4 (D) |
| **R5** | Priority inversion | Low/Critical | Persona overrides safety | Literal stack + V8 audit | Preserve, no task_first |
| **R6** | Context overflow / contamination | High/Med | Poem → Helios mis-route, dense amplifies | `split("|")` hack | Real split E |
| **R7** | Stale memory drift | High/Med | EU 2024 cited as 2026 | `freshness 0.5` appendix, but timestamp reset | Persistent old timestamp + embedding cache (B) |
| **R8** | Over-deliberation | Med/Med | L0 → L2 due to entropy | Floors `eu≥0.67` etc. | Retune after dense (A) |
| **R9** | Under-deliberation | Low/Critical | L4 → L2, no confirm | Auto-escalation `≥0.8→0.85` | Keep, test `T18` L4 |
| **R10** | CoT leakage | Med/Med | `_private_scratch` in response | Firewall + V7 scan | Keep |
| **R11** | Single-writer bottleneck | Low/Low | N13 blocks turn | Async in LEARNING | Keep |
| **R12** | Proactive over-nudging | Med/Med | Spam | N10 gate, `max 1/session` | Keep disabled |

## I — Test Requirements (Before/After per upgrade)

**Invariant for all upgrades:** `setup_memory.py + run_simulations.py + run_arch_tests.py` must stay **11/11**; `run_intelligence_tests.py` must stay **12/12** (with re-tuned thresholds where expected).

| Upgrade | Before (must exist, log baseline) | After (must pass) | Regression guard |
|---------|-----------------------------------|-------------------|------------------|
| **E+A+B atomic** | `T7 Δ TF-IDF 0.085`, `T12 relevance 0.002 fallback`, `S2 poem with injected helios hit` (currently patched) | `T7 Δ dense <0.10` *without* poem floor, `T12` rank-1 helios without fallback, `T10` conflicts still, `T19` dense paraphrase `helios/solar tracker/sun chaser` all >0.35, `S2` poem not mis-routed even with forced helios hit | Remove `poem 0.228-0.39` floor and `S5 -0.25` penalty re-tuned; assert `L0-L4` still 5/5 but scores will shift ±0.1 — update expected scores in `run_simulations.py` golden |
| **D V4** | `T12` `pass_with_warnings` after 3 retries with `V4` spurious (logged) | `T12` `pass` loop 0, `T21` hallucinated claim → `V4 fail→N12`, `T22` generic “tool” mention → no fail, `T23` mock with disclaimer → no fail | `S4` EU Act mock disclaimer still `pass` (V4 exempt) |
| **C NER** | Regex baseline `entities: FILE_PATH, PERCENTAGE` for `helios_spec.pdf 22%` | `T20` `Alice, Bob, Feb 2 2025` typed correctly, `“it contradicts”` not `pronoun_resolution` when `slots.file` present, `“him”` without antecedent still `0.70` | `required_context` length unchanged for S3 (still not pronoun) |
| **F S6** | `S6_rerank_log` empty, `rerank_delta 0.0` | `T25` `positive_feedback → +0.08`, `T26` 90d decay `0.04`, `T27` `>0.2` clamped | Retrieval ranking not inverted for Helios `0.002` case |
| **H DAG** | `parallel_branches [STUB]`, sequential 1 tool/turn | `T29` two `read_file` parallel `ok`, `T30` one timeout → fallback | `tool_budget` still enforced, idempotency keys unique |
| **I Live** | `MOCK true` deterministic | `T31` `MOCK true` deterministic, `T32` `MOCK false` bad URL → `F-TOOL` retry 2 → fallback | 11/11 stays `MOCK true` default |
| **G Vault** | `VAULT_secrets.json` plain | `T28` encrypted on disk, TTL expiry, `N10` deny | No change to S4/S5 |

**Test harness must also add:** `T19` dense paraphrase, `T20` NER, `T21-T23` V4, `T24` context contamination, `T25-T27` S6, `T28` Vault, `T29-T30` DAG, `T31-T32` live — total ≥12 new tests already, but each upgrade adds its own before/after pair.

## J — Architecture Preservation Check (Will v0.3 violate v1.1?)

| Proposed change | Violates v1.1? | Why | Tag |
|-----------------|----------------|-----|-----|
| Dense embeddings inside N3/N5/N7 | **No** | Sub-node of existing nodes, `Vector Search` already explicit in N5 §3; no new top node | **[DERIVED]** |
| WorkingContext split into `user_query` vs `memory_context` | **No** | N2 Output already `summary, entities[], open_tasks[], constraints[], contradiction_flags[]` — `summary` was meant structured, not string; restoring fields is **[EXPLICIT]** |
| V4 structured claims field in N16 | **No if internal** | `N16 Output UserMessage` unchanged; `claims` stays internal to `N14` input, not rendered. If added to `UserMessage` schema, would be **[RECOMMENDED]** extension, not violation |
| Spacy NER inside N3 | **No** | `Classifier, Slot Filler` already has NER as sub-node implied; not a new node | **[RECOMMENDED]** |
| S6 same-turn tuner | **No** | N17 `Threshold Tuner` already explicit in §3 | **[EXPLICIT]** |
| DAG parallel | **No** | N8 `parallel_branches` already explicit, MVV stub | **[EXPLICIT]** |
| Live httpx with MOCK flag | **No** | Tool registry already explicit, `dry_run` already **[RECOMMENDED]** | **[DERIVED]** |
| Vault encryption | **No** | Vault already `[DERIVED]` encrypted separate | **[EXPLICIT]** |
| **Would violate:** Renaming N3→IntentClassifier, merging N7+N16, new top node “Semantic Router”, replacing N6 weights without preserving `L0-L4` thresholds, making `task_first` default, removing `CoT firewall` blocked edge | **Yes — forbidden** | Must keep node identities, responsibilities, memory stores, priority hierarchy, L0-L4, N14 V1-V8, CoT firewall | **[UNSUPPORTED]** if proposed |

**All 1-6 upgrades above preserve contracts if implemented as sub-nodes, not new nodes.**

## K — What Must NOT Change (Until v0.3 semantic is proven)

1. **Node identities & counts** — `N0-N17 + N0.1` 18 nodes, no rename, no merge, no new top node.
2. **Memory stores** — `S1-S7 + Vault` 7+1, no new store, no removal.
3. **Priority hierarchy** — Literal `1 System>2 Safety>3 User Obj>4 Pref>5 Task>6 Persona`, `variant literal` default. Do not make `task_first` default.
4. **Permission gates** — `A0-A4`, `L4` threshold `0.35` for `A3/A4`, pre-reasoning/pre-planning/pre-execution/pre-response enforcement.
5. **Deliberation levels** — `L0-L4` thresholds `0.20/0.40/0.65/0.85` and `tool_budget`/`retrieval_budget` maps. May *re-tune weights* but not thresholds without 11/11 re-validation.
6. **N6 5 axes** — `w_ambiguity 0.25, w_domain 0.20, w_tool 0.15, w_consequence 0.25, w_novelty 0.15` may tune but not remove axis.
7. **N14 verification** — `V1-V8` 8 axes, `max_loops 3`, `N15` typed `F-` taxonomy, no new V9 without §9 amendment.
8. **N15 execution** — `F-INS/F-AMB/...` 10 types, retry budgets `3 iters, 2 retries, 2 replans`, not enlarged.
9. **N16 persona separation** — `style≠facts`, `CoT firewall` blocked edge `private_scratch ──X──► N16`, leak scan stays.
10. **Feedback loops** — `F1-F7` with breakers, no new loop without §10 amendment.
11. **Heuristic floors** — `eu≥0.67, helios≥0.57, poem 0.228-0.39, time≤0.19` must be *removed* only after dense proves stability with `T7` — not before. Keep until E+A+B deploy.
12. **Tool registry** — `read_file/system_time` REAL, `web_search` MOCK default — do not make live default.

## L — v0.3 Readiness Verdict

**Is v0.2 ready for v0.3?** **Yes, but only for the atomic E+A+B → D → C sequence.**

- **Ready:** Control plane (deliberation, verification loop, provenance, permission) is *REAL* and tested 23/23. S1/S7 persistence is *REAL*. Hybrid orchestration is *REAL* — only semantic core is proxy.
- **Not ready for semantic without E:** Dense alone will re-break `S2` poem (proven by `0.002` fallback and `split("|")` hack). **E must ship with A.**
- **Not ready for DAG/Live without D:** `V4` spurious will livelock live parallel fetches.
- **Ready for NER (C) now:** Independent, low risk, can ship parallel to E+A+B if needed, but not before E.

**Overall:** **GO for v0.3 with scope limited to E+A+B (1 PR) then D (1 PR) then C (1 PR).** All other upgrades (F,G,H,I) are **NOT READY** — they depend on stable semantic and would be feature creep.

**If scope widens beyond those 3, verdict becomes NO-GO.**

## M — Exact Next Implementation Directive (for v0.3 PR #1)

**Title:** `v0.3-P1 E+A+B — WorkingContext separation + Dense embeddings`

**Do NOT write v0.3 code yet — this is the directive; implement only after explicit approval.**

**Objective:** Replace TF-IDF proxy with dense `sentence-transformers` while fixing the contamination bottleneck that would otherwise break with dense.

**Files to touch (only):**
- `nis/memory.py` — add embedding cache `data/memory/embeddings.json`, keep `TfidfVectorizer` fallback, add `USE_DENSE` flag **[DERIVED]**
- `nis/nodes.py` — `N2` split `WorkingContext` fields, `N3/N6/N7/N16` use `user_query` not `split("|")`, `N3/N5/N7` use dense cosine with fallback
- `nis/config.py` — add `embedding_model: "all-MiniLM-L6-v2"` and `USE_DENSE: false` default **[RECOMMENDED]**
- `setup_memory.py` — stop resetting `eu_ai_act` timestamp to now; keep old `2024-12-01` for stale test
- `requirements.txt` — add `sentence-transformers`, `numpy` (fallback already `sklearn` 1.6.1)

**Files to NOT touch:** `nis/orchestrator.py` (except passing `WorkingContext`), `nis/tools.py`, `nis/incp.py`, `Vault`, `DAG`, `Live` tools.

**Implementation steps (exact):**
1. Run baseline `python run_intelligence_tests.py` and log `T7 Δ TF-IDF`, `T12 relevance`, `S2` with injected helios hit.
2. Add `WorkingContext` structured fields in `N2.process` keep `summary` for logging, add `user_query` + `memory_context`, change `N7/N6/N16` branching to `user_query`.
3. Install `sentence-transformers` with offline cache, implement `embed(texts) → vectors` with `numpy` cosine, cache `key → (vector, timestamp)` in `embeddings.json`, keep TF-IDF fallback if `USE_DENSE false` or model missing.
4. In `N3._tfidf_intent_scores` keep prototypes but embed them (pre-compute), not per-turn fit. Same for `N5._semantic_score_tfidf` → `_semantic_score_dense`.
5. Re-tune `retrieval_budget threshold 0.15→0.25` (dense scores higher) and `weights 0.35/0.45/0.20 → 0.25/0.55/0.20` with 23/23 logs before commit.
6. Remove heuristic floors `poem 0.228-0.39` etc. only after `T7` passes without them; otherwise keep and mark `[RECOMMENDED]` .
7. Re-run `setup_memory.py + run_simulations.py + run_arch_tests.py` → must stay **11/11** (update golden scores where `L0 0.123 → ~0.15` etc. allowed ±0.1 but L must stay).
8. Re-run `run_intelligence_tests.py` → must stay **12/12**, plus new `T19` dense paraphrase and `T24` contamination guard.

**Tagging:** E is **[EXPLICIT]** (N2 fields), A is **[DERIVED]** (vector search), B is **[DERIVED]** (hybrid).

**Regression guard:** `USE_DENSE=false` must still pass 11/11 with TF-IDF (fallback). `USE_DENSE=true` must pass 11/11 with dense.

---

## NEXT ACTION

**Give the implementation agent this exact instruction and nothing else:**

> **Implement v0.3-P1 E+A+B — WorkingContext separation + Dense embeddings (single PR, feature-flagged).**
>
> 1. In `nis/nodes.py` `N2` add structured `WorkingContext {user_query, memory_context}` keep `summary` for logs, change `N7/N6/N16` to branch on `user_query` (remove `split("|")` hack).
> 2. Add `sentence-transformers` `all-MiniLM-L6-v2` dense embeddings with offline cache `data/memory/embeddings.json` and TF-IDF fallback behind `CONFIG.USE_DENSE` (default false for 11/11). Replace `N3._tfidf_intent_scores`, `N5._semantic_score_tfidf`, `N7._score_evidence` with dense cosine when flag true, keep prototypes embedded pre-compute.
> 3. In `nis/memory.py` keep hybrid `0.35/0.45/0.20` but re-tune to `0.25/0.55/0.20` for dense, add persistent embedding cache, fix `setup_memory.py` to keep `eu_ai_act` old timestamp `2024-12-01` for stale test.
> 4. Preserve all v1.1 contracts: node IDs, `L0-L4` thresholds, `S1/S7`, `N9` literal, `N10` gates, `N14` V1-V8 `max_loops 3`, `CoT firewall`, `Vault` stub, `DAG` stub, `N17` stub.
> 5. Before/after tests: Log baseline `T7 Δ TF-IDF`, `T12 relevance 0.002`, inject helios into `S2` poem context. After: `T7` must be same L1 without poem floor, `T12` rank-1 helios without fallback, `T24` poem with forced helios hit must not mis-route, plus new `T19` dense paraphrase `helios/solar tracker/sun chaser`. `setup_memory+run_simulations+run_arch_tests` must stay **11/11**, `run_intelligence_tests` **12/12** for both `USE_DENSE false` and `true`.
>
> **Do NOT touch Vault, DAG, Live tools, or S6 learning in this PR. STOP after this PR and re-audit before next upgrade.**

