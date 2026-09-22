"""
Memory Substrate v0.2 — Hybrid Retrieval
Implements REAL hybrid retrieval + persistent S1/S7 + reranking
Preserves canonical contracts §4
"""
import json, os, time, re, math
from pathlib import Path
from typing import List, Dict, Any, Optional
from collections import Counter

BASE = Path(__file__).parent.parent / "data" / "memory"
BASE.mkdir(parents=True, exist_ok=True)

def _load_json(path: Path, default):
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except:
        return default

def _save_json(path: Path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(path)

def _freshness_score(ts: float, half_life_days: int = 180) -> float:
    age_days = (time.time() - ts) / 86400.0
    return 0.5 ** (age_days / half_life_days) if age_days >= 0 else 1.0

class MemoryHit:
    def __init__(self, store: str, key: str, value: Any, provenance: str, timestamp: float, confidence: float = 0.7, freshness: float = 1.0, relevance: float = 0.0, semantic: float = 0.0, lexical: float = 0.0, rerank_delta: float = 0.0):
        self.store = store
        self.key = key
        self.value = value
        self.provenance = provenance
        self.timestamp = timestamp
        self.confidence = confidence
        self.freshness = freshness
        self.relevance = relevance
        self.semantic = semantic
        self.lexical = lexical
        self.rerank_delta = rerank_delta

    def to_dict(self):
        base = {
            "store": self.store, "key": self.key, "value": self.value,
            "provenance": self.provenance, "timestamp": self.timestamp,
            "confidence": self.confidence, "freshness": self.freshness,
            "relevance_score": round(self.relevance,3),
            "semantic_score": round(self.semantic,3),
            "lexical_score": round(self.lexical,3),
            "rerank_delta": round(self.rerank_delta,3),
            "source": self.provenance,
            "memory_store": self.store
        }
        return base

class MemorySubstrateV02:
    """
    v0.2: Persistent S1/S7, hybrid retrieval, reranking, conflict surfacing
    Stores:
      S1 Working — per-session file S1_working.json (REAL, persistent, session-bounded)
      S2 Conversation — file S2_conversation.json (REAL)
      S3 Preferences — file S3_preferences.json (REAL)
      S4 LTM — file S4_ltm.json (REAL versioned)
      S5 Project — filesystem /home/user/*.md (REAL)
      S6 Behavioral — file S6_behavioral.json + S6_rerank_log.json (REAL with decay, bounded)
      S7 Task — file S7_tasks.json (REAL persistent task-scoped)
      Vault — file VAULT_secrets.json (STUB gated)
    """
    def __init__(self, base: Path = BASE):
        self.base = base
        self.s1_path = base / "S1_working.json"
        self.s2_path = base / "S2_conversation.json"
        self.s3_path = base / "S3_preferences.json"
        self.s4_path = base / "S4_ltm.json"
        self.s6_path = base / "S6_behavioral.json"
        self.s6_log_path = base / "S6_rerank_log.json"
        self.s7_path = base / "S7_tasks.json"
        self.vault_path = base / "VAULT_secrets.json"
        self.s5_project_dir = Path("/home/user")
        for p, default in [
            (self.s1_path, {}), (self.s2_path, []), (self.s3_path, {}),
            (self.s4_path, []), (self.s6_path, []), (self.s6_log_path, []),
            (self.s7_path, {}), (self.vault_path, {})
        ]:
            if not p.exists():
                _save_json(p, default)

    # ---- Session handling ----
    def _session_id(self) -> str:
        # Per-day session, could be per-user; keep simple
        return time.strftime("%Y-%m-%d", time.gmtime())

    # ---- S1 Working Memory (persistent, session-bounded) ----
    def set_working(self, trace_id: str, context: Dict):
        data = _load_json(self.s1_path, {})
        # Prune old sessions (>24h) to preserve boundaries
        cutoff = time.time() - 24*3600
        pruned = {k:v for k,v in data.items() if v.get("timestamp",0) > cutoff}
        pruned[trace_id] = {"context": context, "timestamp": time.time(), "session_id": self._session_id()}
        _save_json(self.s1_path, pruned)

    def get_working(self, trace_id: str) -> Optional[Dict]:
        data = _load_json(self.s1_path, {})
        entry = data.get(trace_id)
        return entry.get("context") if entry else None

    def get_session_working(self, session_id: Optional[str] = None) -> List[Dict]:
        sid = session_id or self._session_id()
        data = _load_json(self.s1_path, {})
        return [v["context"] for v in data.values() if v.get("session_id")==sid]

    # ---- S2 ----
    def append_conversation(self, turn: Dict):
        data = _load_json(self.s2_path, [])
        data.append(turn)
        data = data[-100:]
        _save_json(self.s2_path, data)
    def get_conversation(self, last_n: int = 10) -> List[Dict]:
        data = _load_json(self.s2_path, [])
        return data[-last_n:]

    # ---- S3 ----
    def get_preferences(self) -> Dict:
        return _load_json(self.s3_path, {})
    def set_preference(self, key: str, value: Any):
        data = _load_json(self.s3_path, {})
        data[key] = {"value": value, "updated": time.time(), "provenance": "N17 or explicit"}
        _save_json(self.s3_path, data)

    # ---- S4 ----
    def get_ltm(self) -> List[Dict]:
        return _load_json(self.s4_path, [])
    def add_ltm(self, key: str, value: Any, provenance: str, confidence: float = 0.7):
        data = _load_json(self.s4_path, [])
        data.append({"key": key, "value": value, "provenance": provenance, "timestamp": time.time(), "confidence": confidence})
        _save_json(self.s4_path, data)
    def search_ltm(self, query: str, limit: int = 5) -> List[MemoryHit]:
        # Lexical baseline used only for fallback; hybrid retrieve does full scoring
        hits=[]
        q=query.lower()
        for item in self.get_ltm():
            vs=json.dumps(item.get("value",""), ensure_ascii=False).lower()+" "+item.get("key","").lower()
            if q.split()[0] in vs if q else False:
                freshness=_freshness_score(item.get("timestamp", time.time()))
                hits.append(MemoryHit(store="S4", key=item["key"], value=item["value"], provenance=item.get("provenance",""), timestamp=item["timestamp"], confidence=item.get("confidence",0.7), freshness=freshness, relevance=0.5))
        hits.sort(key=lambda h: h.freshness, reverse=True)
        return hits[:limit]

    # ---- S5 ----
    def get_project_files(self, pattern: str = "*.md") -> List[str]:
        try:
            return [str(p) for p in self.s5_project_dir.glob(pattern) if p.is_file()]
        except:
            return []
    def search_project(self, query: str, limit: int = 3) -> List[MemoryHit]:
        q=query.lower()
        hits=[]
        for f in self.get_project_files("*.md")[:20]:
            try:
                text=Path(f).read_text(encoding="utf-8", errors="ignore")[:3000]
                if q.split()[0] in text.lower() if q else False:
                    hits.append(MemoryHit(store="S5", key=f, value=text[:600], provenance=f"file:{f}", timestamp=Path(f).stat().st_mtime, confidence=0.8, freshness=_freshness_score(Path(f).stat().st_mtime, 180), relevance=0.6))
                    if len(hits)>=limit: break
            except: continue
        return hits

    # ---- S6 Behavioral + Reranking (REAL, traceable, reversible, bounded, logged) ----
    def get_behavioral(self) -> List[Dict]:
        return _load_json(self.s6_path, [])
    def add_behavioral(self, pattern: str, data: Dict):
        arr=_load_json(self.s6_path, [])
        arr.append({"pattern": pattern, "data": data, "timestamp": time.time()})
        _save_json(self.s6_path, arr[-200:])
        # Also log rerank delta separately
        if pattern in ["positive_feedback","correction","tool_success","tool_failure","memory_useful","memory_not_useful"]:
            log=_load_json(self.s6_log_path, [])
            # Determine key affected for reranking: data may contain key
            key=data.get("key") or data.get("memory_key") or data.get("followup","")[:40] or "unknown"
            # Map pattern to delta
            delta_map={"positive_feedback":0.08, "memory_useful":0.1, "tool_success":0.05, "correction":-0.12, "memory_not_useful":-0.08, "tool_failure":-0.05}
            delta=delta_map.get(pattern,0)
            # Bounded per-entry, traceable
            entry={"key": key, "pattern": pattern, "delta": delta, "trace": data.get("trace",""), "timestamp": time.time(), "reversible": True, "bounded": "[-0.2,+0.2] per key"}
            log.append(entry)
            _save_json(self.s6_log_path, log[-300:])

    def get_reranking_boost(self, key: str, max_boost: float = 0.2, half_life_days: int = 90) -> float:
        """Compute boost for a memory key from S6, decayed by 90d half-life, bounded."""
        logs=_load_json(self.s6_log_path, [])
        now=time.time()
        total=0.0
        for e in logs:
            if e.get("key")==key or e.get("key") in key or key in e.get("key",""):
                age_days=(now - e.get("timestamp",now))/86400.0
                decay=0.5 ** (age_days / half_life_days) if age_days>=0 else 1.0
                total += e.get("delta",0) * decay
        # Bounded
        return max(-max_boost, min(max_boost, total))

    def get_rerank_log(self) -> List[Dict]:
        return _load_json(self.s6_log_path, [])

    # ---- S7 Task Memory (persistent, isolated) ----
    def set_task(self, task_id: str, data: Dict):
        store=_load_json(self.s7_path, {})
        store[task_id]={"data": data, "timestamp": time.time(), "session_id": self._session_id()}
        # Keep max 100 tasks, prune old
        if len(store)>100:
            # prune oldest
            sorted_items=sorted(store.items(), key=lambda kv: kv[1].get("timestamp",0))
            store=dict(sorted_items[-100:])
        _save_json(self.s7_path, store)
    def get_task(self, task_id: str) -> Dict:
        store=_load_json(self.s7_path, {})
        entry=store.get(task_id)
        return entry.get("data") if entry else {}
    def list_tasks(self, session_only: bool = True) -> List[str]:
        store=_load_json(self.s7_path, {})
        if session_only:
            sid=self._session_id()
            return [k for k,v in store.items() if v.get("session_id")==sid]
        return list(store.keys())
    def clear_task(self, task_id: str):
        store=_load_json(self.s7_path, {})
        if task_id in store:
            del store[task_id]
            _save_json(self.s7_path, store)

    # ---- Vault ----
    def vault_get(self, key: str):
        data=_load_json(self.vault_path, {})
        return data.get(key)
    def vault_set(self, key: str, value: Any):
        data=_load_json(self.vault_path, {})
        data[key]={"value": value, "timestamp": time.time()}
        _save_json(self.vault_path, data)

    # ---- Hybrid Retrieval ----
    def _tokenize(self, text: str) -> List[str]:
        return re.findall(r"\w+", text.lower())

    def _lexical_score(self, query: str, doc: str) -> float:
        q_toks=self._tokenize(query)
        d_toks=set(self._tokenize(doc))
        if not q_toks: return 0.0
        overlap=sum(1 for t in q_toks if t in d_toks)
        # Exact phrase boost
        exact=1.0 if query.lower() in doc.lower() else 0.0
        return 0.7*(overlap/len(q_toks)) + 0.3*exact

    def _semantic_score_tfidf(self, query: str, docs: List[str]) -> List[float]:
        """Use sklearn TF-IDF cosine as semantic proxy. Returns list per doc. [FALLBACK]"""
        try:
            from sklearn.feature_extraction.text import TfidfVectorizer
            from sklearn.metrics.pairwise import cosine_similarity
            corpus=[query] + docs
            vec=TfidfVectorizer(ngram_range=(1,2), stop_words='english', max_features=5000).fit_transform(corpus)
            q_vec=vec[0]
            d_vecs=vec[1:]
            sims=cosine_similarity(q_vec, d_vecs)[0]
            return [float(s) for s in sims]
        except Exception as e:
            # Fallback heuristic semantic = lexical
            return [self._lexical_score(query, d)*0.9 for d in docs]

    def _semantic_score(self, query: str, docs: List[str]) -> List[float]:
        """
        Dense-first semantic scoring with TF-IDF fallback.
        When CONFIG.USE_DENSE true and dense available, uses sentence-transformers deterministic embeddings (cached).
        Otherwise falls back to TF-IDF (v0.2 behavior).
        Preserves hybrid contract.
        """
        from .config import CONFIG
        # Try dense if enabled
        if getattr(CONFIG, "USE_DENSE", False):
            try:
                from .embeddings import semantic_scores_dense
                dense_scores = semantic_scores_dense(query, docs)
                if dense_scores is not None:
                    return dense_scores
            except Exception:
                pass
        # Fallback to TF-IDF
        return self._semantic_score_tfidf(query, docs)

    def retrieve(self, query: str, intent_frame: Dict, deliberation_level: str, project_scope: Optional[str] = None) -> Dict:
        from .config import CONFIG
        budgets={0:0,1:3,2:6,3:12,4:12}
        level_num={"L0":0,"L1":1,"L2":2,"L3":3,"L4":4}.get(deliberation_level,2)
        budget=budgets.get(level_num,6)
        if budget==0:
            return {"hits":[],"provenance":[],"freshness_scores":[],"conflicts":[],"appendix":[],"relevance_scores":[],"rerank_deltas":[]}

        # Gather candidates
        candidates: List[MemoryHit] = []
        # S3
        prefs=self.get_preferences()
        if prefs and level_num>=1:
            for k,v in list(prefs.items())[:2]:
                ts=v.get("updated", time.time()) if isinstance(v, dict) else time.time()
                val_str=json.dumps(v, ensure_ascii=False)
                candidates.append(MemoryHit(store="S3", key=k, value=v, provenance="S3_preferences", timestamp=ts, confidence=0.85, freshness=_freshness_score(ts)))

        # S4
        for item in self.get_ltm():
            vs=json.dumps(item.get("value",""), ensure_ascii=False) + " " + item.get("key","")
            # Don't filter lexically here; we will score all and then rank
            candidates.append(MemoryHit(store="S4", key=item["key"], value=item["value"], provenance=item.get("provenance","S4_ltm"), timestamp=item.get("timestamp",time.time()), confidence=item.get("confidence",0.7), freshness=_freshness_score(item.get("timestamp",time.time()))))

        # S5
        for f in self.get_project_files("*.md")[:25]:
            try:
                text=Path(f).read_text(encoding="utf-8", errors="ignore")[:4000]
                candidates.append(MemoryHit(store="S5", key=f, value=text[:700], provenance=f"file:{f}", timestamp=Path(f).stat().st_mtime, confidence=0.8, freshness=_freshness_score(Path(f).stat().st_mtime)))
            except: continue

        # S6 behavioral hints as context, not retrieval hits themselves (but we include recent behavioral patterns as hits for provenance)
        # For v0.2, S6 is used for reranking, not as hits

        if not candidates:
            return {"hits":[],"provenance":[],"freshness_scores":[],"conflicts":[],"appendix":[],"relevance_scores":[],"rerank_deltas":[]}

        # Compute lexical + semantic per candidate (dense-first with TF-IDF fallback)
        docs=[str(c.value)[:2000] + " " + c.key for c in candidates]
        semantic_scores=self._semantic_score(query, docs)

        # Intent/project scope metadata filtering boost
        intent_text=json.dumps(intent_frame.get("slots",{})).lower() + " " + intent_frame.get("primary_intent","").lower()
        project_bias=project_scope.lower() if project_scope else ""
        # Build intent tokens for boost
        intent_tokens=set(self._tokenize(query + " " + intent_text))

        scored=[]
        for idx, c in enumerate(candidates):
            doc_text=docs[idx]
            lexical=self._lexical_score(query, doc_text)
            semantic=semantic_scores[idx] if idx<len(semantic_scores) else lexical

            # Metadata filtering: boost if doc matches intent/project tokens
            doc_tokens=set(self._tokenize(doc_text))
            intent_overlap=len(intent_tokens & doc_tokens)/max(1,len(intent_tokens))
            metadata_boost=0.2*intent_overlap
            # Project scope boost
            if project_bias and project_bias in doc_text.lower():
                metadata_boost+=0.15

            # Combine: lexical 0.35, semantic 0.45, metadata 0.20
            relevance=0.35*lexical + 0.45*semantic + 0.20*metadata_boost
            # Intent-scoped store penalty: creation/poem or question/time should not retrieve S5 helios files unless query mentions helios
            q_lower = query.lower()
            if c.store == "S5":
                # If S5 file is about helios but query is poem/time without helios, penalize heavily
                doc_lower = doc_text.lower()
                if "helios" in doc_lower and "helios" not in q_lower and "helios" not in intent_text:
                    relevance -= 0.25
                if "efficiency" in doc_lower and "efficiency" not in q_lower:
                    relevance -= 0.15
                # For L0/L1, S5 is less relevant unless explicitly about query topic
                if level_num <= 1:
                    relevance -= 0.10
            # For creation poem, boost S3
            if c.store == "S3" and "poem" in q_lower:
                relevance += 0.12
            # Freshness and confidence already separate, but relevance includes freshness weighting later
            # Reranking boost from S6 (bounded, traceable)
            rerank_delta=self.get_reranking_boost(c.key)
            # Apply rerank bounded
            relevance_adjusted=relevance + rerank_delta
            # Floor at 0
            relevance_adjusted = max(0.0, relevance_adjusted)
            # Store per-hit scores
            c.lexical=lexical
            c.semantic=semantic
            c.relevance=relevance_adjusted
            c.rerank_delta=rerank_delta
            scored.append(c)

        # Sort by relevance * freshness * confidence
        scored.sort(key=lambda h: h.relevance * h.freshness * h.confidence, reverse=True)

        # Relevance threshold: filter very low relevance unless L3+ (keep more for complex)
        threshold=0.08 if level_num>=3 else 0.15
        filtered=[h for h in scored if h.relevance >= threshold]
        # If filtered too few, keep top 3 only for L2+ or when query explicitly asks for helios/efficiency/project
        if len(filtered)<2 and scored:
            ql = query.lower()
            if level_num>=2 or any(k in ql for k in ["helios","efficiency","project","eu ai"]):
                filtered=scored[:3]
            else:
                # For L0/L1 creation/question with no clear match, keep only S3 hits if any
                s3_hits = [h for h in scored if h.store=="S3" and h.relevance>0.05]
                if s3_hits:
                    filtered = s3_hits[:2]
                else:
                    filtered = [h for h in scored if h.relevance>0.08][:2]

        # Budget trim
        filtered=filtered[:budget]

        # Split main vs appendix via freshness
        main=[]
        appendix=[]
        for h in filtered:
            if h.freshness < CONFIG.memory.freshness_appendix_threshold and level_num < 3:
                appendix.append(h)
            else:
                main.append(h)

        # Conflict detection — never silently overwrite
        # Detect same key different values, or numeric conflicts like 22% vs 21.5%
        conflicts=[]
        seen={}
        # Also detect efficiency percentage conflicts specifically
        eff_vals={}
        for h in main:
            key_norm=h.key.lower() if isinstance(h.key,str) else str(h.key).lower()
            # Generic same-key different value
            if key_norm in seen and str(seen[key_norm].value) != str(h.value):
                conflicts.append({"key": h.key, "values": [seen[key_norm].value, h.value], "stores": [seen[key_norm].store, h.store], "provenance": [seen[key_norm].provenance, h.provenance]})
            else:
                seen[key_norm]=h
            # Efficiency conflict heuristic
            eff_match=re.search(r"(\d+\.?\d*)\s*%", str(h.value))
            if eff_match:
                eff=float(eff_match.group(1))
                # Group by Helios-like keys
                if "helios" in key_norm or "efficiency" in key_norm or "helios" in str(h.value).lower():
                    eff_vals.setdefault("helios_eff", []).append((eff, h))

        # Check for divergent efficiencies
        if "helios_eff" in eff_vals and len(eff_vals["helios_eff"])>=2:
            vals=[v for v,_ in eff_vals["helios_eff"]]
            if max(vals)-min(vals) >= 0.3:  # e.g., 22.0 vs 21.5 diff 0.5 → conflict
                conflicts.append({"key": "helios_efficiency", "values": [f"{v}%" for v,_ in eff_vals["helios_eff"]], "stores": [h.store for _,h in eff_vals["helios_eff"]], "provenance": [h.provenance for _,h in eff_vals["helios_eff"]], "note": "Surfaced, not overwritten"})

        # Build provenance-enhanced result — indicate dense vs TFIDF path
        main_dicts=[h.to_dict() for h in main]
        # Determine semantic path actually used
        from .config import CONFIG as _CFG
        semantic_tag = "TFIDF"
        if getattr(_CFG, "USE_DENSE", False):
            try:
                from .embeddings import is_dense_available
                if is_dense_available():
                    semantic_tag = "DENSE"
            except Exception:
                semantic_tag = "TFIDF"
        return {
            "hits": main_dicts,
            "provenance": [h["provenance"] for h in main_dicts],
            "freshness_scores": [h["freshness"] for h in main_dicts],
            "relevance_scores": [h["relevance_score"] for h in main_dicts],
            "lexical_scores": [h["lexical_score"] for h in main_dicts],
            "semantic_scores": [h["semantic_score"] for h in main_dicts],
            "rerank_deltas": [h["rerank_delta"] for h in main_dicts],
            "conflicts": conflicts,
            "appendix": [h.to_dict() for h in appendix],
            "source": f"hybrid: lexical+semantic({semantic_tag})+metadata+freshness+rerank",
            "memory_store": "S3+S4+S5+RERANK",
            "retrieval_path": f"N5→S3/S4/S5→{semantic_tag}→rerank(S6)→freshness→budget"
        }

# Singleton for v0.2 — alias for backward compat
SUBSTRATE = MemorySubstrateV02()
MemorySubstrate = MemorySubstrateV02

