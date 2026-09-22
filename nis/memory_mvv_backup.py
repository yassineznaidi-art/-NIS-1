"""
Memory Substrate — Canonical v1.1
7 stores + Secret Vault [DERIVED]
MVV implements: S1 Working [MOCK volatile], S2 Conversation [REAL json], S3 Preferences [REAL json], S4 LTM [REAL json], S5 Project [REAL fs], S6 Behavioral [STUB], S7 Task [MOCK volatile], Vault [STUB]
"""
import json
import os
import time
from pathlib import Path
from typing import List, Dict, Any, Optional

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
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

class MemoryHit:
    def __init__(self, store: str, key: str, value: Any, provenance: str, timestamp: float, confidence: float = 0.7, freshness: float = 1.0):
        self.store = store
        self.key = key
        self.value = value
        self.provenance = provenance
        self.timestamp = timestamp
        self.confidence = confidence
        self.freshness = freshness

    def to_dict(self):
        return {"store": self.store, "key": self.key, "value": self.value, "provenance": self.provenance, "timestamp": self.timestamp, "confidence": self.confidence, "freshness": self.freshness}

class MemorySubstrate:
    """
    7 stores + Vault. MVV marks:
    - REAL: S2, S3, S4, S5 (project files in /home/user)
    - MOCK: S1 (volatile dict), S7 (volatile dict)
    - STUB: S6 (in-memory list, 90d half-life not yet decayed), Vault (encrypted, mocked as plain json but gated)
    """
    def __init__(self, base: Path = BASE):
        self.base = base
        # File-backed stores
        self.s2_path = base / "S2_conversation.json"  # [REAL]
        self.s3_path = base / "S3_preferences.json"   # [REAL]
        self.s4_path = base / "S4_ltm.json"           # [REAL]
        self.s6_path = base / "S6_behavioral.json"    # [STUB] — 90d half-life not computed, just list
        self.vault_path = base / "VAULT_secrets.json" # [STUB] — plain json, gated by N10+N13
        # Volatile
        self.s1_working = {}  # [MOCK] volatile RAM
        self.s7_task = {}     # [MOCK] volatile per-task
        self.s5_project_dir = Path("/home/user")  # [REAL] — maps to filesystem

        # Ensure files exist
        for p, default in [(self.s2_path, []), (self.s3_path, {}), (self.s4_path, []), (self.s6_path, []), (self.vault_path, {})]:
            if not p.exists():
                _save_json(p, default)

    # ---- S2 Conversation State [REAL] ----
    def append_conversation(self, turn: Dict):
        data = _load_json(self.s2_path, [])
        data.append(turn)
        # Keep last 24h (simplified: keep last 50 turns)
        data = data[-50:]
        _save_json(self.s2_path, data)

    def get_conversation(self, last_n: int = 10) -> List[Dict]:
        data = _load_json(self.s2_path, [])
        return data[-last_n:]

    # ---- S3 Preferences [REAL] ----
    def get_preferences(self) -> Dict:
        return _load_json(self.s3_path, {})

    def set_preference(self, key: str, value: Any):
        data = _load_json(self.s3_path, {})
        data[key] = {"value": value, "updated": time.time(), "provenance": "N17 or explicit"}
        _save_json(self.s3_path, data)

    # ---- S4 Long-Term Memory [REAL] ----
    def get_ltm(self) -> List[Dict]:
        return _load_json(self.s4_path, [])

    def add_ltm(self, key: str, value: Any, provenance: str, confidence: float = 0.7):
        data = _load_json(self.s4_path, [])
        # Versioned: keep history
        data.append({"key": key, "value": value, "provenance": provenance, "timestamp": time.time(), "confidence": confidence})
        _save_json(self.s4_path, data)

    def search_ltm(self, query: str, limit: int = 5) -> List[MemoryHit]:
        # Simple lexical search [MOCK] — real would be vector+lexical hybrid [STUB for vector]
        hits = []
        q = query.lower()
        for item in self.get_ltm():
            # Score: lexical overlap + recency
            val_str = json.dumps(item.get("value",""), ensure_ascii=False).lower() + " " + item.get("key","").lower()
            score = 1 if q in val_str else 0
            # Boost for recent
            freshness = max(0.1, 1.0 - (time.time() - item.get("timestamp", time.time())) / (180*24*3600))
            if score > 0:
                hits.append(MemoryHit(store="S4", key=item["key"], value=item["value"], provenance=item.get("provenance",""), timestamp=item["timestamp"], confidence=item.get("confidence",0.7), freshness=freshness))
        # Sort by freshness
        hits.sort(key=lambda h: h.freshness, reverse=True)
        # Apply appendix threshold: <0.5 → appendix unless L3+ (handled by caller)
        return hits[:limit]

    # ---- S5 Project Memory [REAL] ----
    def get_project_files(self, pattern: str = "*.md") -> List[str]:
        try:
            return [str(p) for p in self.s5_project_dir.glob(pattern) if p.is_file()]
        except:
            return []

    def search_project(self, query: str, limit: int = 3) -> List[MemoryHit]:
        q = query.lower()
        hits = []
        for f in self.get_project_files("*.md")[:20]:
            try:
                text = Path(f).read_text(encoding="utf-8", errors="ignore")[:2000]
                if q in text.lower() or q.split()[0] in text.lower():
                    hits.append(MemoryHit(store="S5", key=f, value=text[:500], provenance=f"file:{f}", timestamp=Path(f).stat().st_mtime, confidence=0.8, freshness=0.9))
                    if len(hits) >= limit:
                        break
            except:
                continue
        return hits

    # ---- S6 Behavioral [STUB] ----
    def get_behavioral(self) -> List[Dict]:
        # [STUB] — not decayed, just list. [NOT IMPLEMENTED: 90d half-life decay math]
        return _load_json(self.s6_path, [])

    def add_behavioral(self, pattern: str, data: Dict):
        arr = _load_json(self.s6_path, [])
        arr.append({"pattern": pattern, "data": data, "timestamp": time.time()})
        _save_json(self.s6_path, arr[-100:])

    # ---- S3 retrieval + intent-scoped retrieval [DERIVED] ----
    def retrieve(self, query: str, intent_frame: Dict, deliberation_level: str, project_scope: Optional[str] = None) -> Dict:
        """
        Hybrid retrieval [MOCK lexical only] — vector hybrid is [STUB]
        Intent-scoped [DERIVED]: uses intent_frame.slots to scope query
        Project-scoped [DERIVED]: filters by active project
        Budget by L [EXPLICIT]: L0:0, L1:1-3, L2:3-6, L3:6-12, L4:8-12
        Freshness <0.5 → appendix unless L3+ [RECOMMENDED]
        """
        from .config import CONFIG
        budgets = {0:0, 1:3, 2:6, 3:12, 4:12}
        level_num = {"L0":0,"L1":1,"L2":2,"L3":3,"L4":4}.get(deliberation_level, 2)
        budget = budgets.get(level_num, 6)

        if budget == 0:
            return {"hits": [], "provenance": [], "freshness_scores": [], "conflicts": [], "appendix": []}

        # Gather hits from S3, S4, S5, S6
        hits = []
        # S3 preferences — if query mentions tone etc., but we add relevant prefs always for L1+
        prefs = self.get_preferences()
        if prefs and level_num >= 1:
            # Example: if we have any prefs, include as hit for personalization
            for k,v in list(prefs.items())[:1]:
                hits.append(MemoryHit(store="S3", key=k, value=v, provenance="S3_preferences", timestamp=v.get("updated", time.time()) if isinstance(v, dict) else time.time(), confidence=0.8, freshness=0.95))

        # S4 LTM
        hits.extend(self.search_ltm(query, limit=budget))
        # S5 Project
        hits.extend(self.search_project(query, limit=2))
        # S6 Behavioral [STUB]
        # Note: Vector hybrid is [NOT IMPLEMENTED] — lexical only is [MOCK]
        # Sort by freshness*confidence
        hits.sort(key=lambda h: h.freshness * h.confidence, reverse=True)
        # Trim to budget
        hits = hits[:budget]

        # Freshness appendix rule [RECOMMENDED]
        main_hits = []
        appendix = []
        conflicts = []
        for h in hits:
            if h.freshness < 0.5 and level_num < 3:
                appendix.append(h)
            else:
                main_hits.append(h)

        # Simple conflict detection [MOCK] — if two hits have same key but different value
        seen = {}
        for h in main_hits:
            if h.key in seen and seen[h.key].value != h.value:
                conflicts.append({"key": h.key, "values": [seen[h.key].value, h.value], "stores": [seen[h.key].store, h.store]})
            else:
                seen[h.key] = h

        return {
            "hits": [h.to_dict() for h in main_hits],
            "provenance": [h.provenance for h in main_hits],
            "freshness_scores": [h.freshness for h in main_hits],
            "conflicts": conflicts,
            "appendix": [h.to_dict() for h in appendix]
        }

    # ---- S1 Working Context [MOCK] volatile ----
    def set_working(self, trace_id: str, context: Dict):
        self.s1_working[trace_id] = context

    def get_working(self, trace_id: str) -> Optional[Dict]:
        return self.s1_working.get(trace_id)

    # ---- S7 Task State [MOCK] ----
    def set_task(self, trace_id: str, data: Dict):
        self.s7_task[trace_id] = data

    def get_task(self, trace_id: str) -> Dict:
        return self.s7_task.get(trace_id, {})

    # ---- Vault [STUB] ----
    def vault_get(self, key: str):
        # [STUB] plain json, not encrypted; gated by N10+N13 (enforced outside)
        data = _load_json(self.vault_path, {})
        return data.get(key)

    def vault_set(self, key: str, value: Any):
        # [STUB] not encrypted; real would be encrypted with TTL
        data = _load_json(self.vault_path, {})
        data[key] = {"value": value, "timestamp": time.time()}
        _save_json(self.vault_path, data)

# Singleton for MVV
SUBSTRATE = MemorySubstrate()
