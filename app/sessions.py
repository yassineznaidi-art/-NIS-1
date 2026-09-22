"""
Session Management — basic, simple, file-backed.
Each session is UI-level conversation history, separate from NIS Core memory (S2/S3/S4).
Preserves NIS memory as source of truth; session is shell.
"""
import json, time, uuid
from pathlib import Path
from typing import List, Dict, Optional

BASE = Path(__file__).parent.parent / "data" / "memory"
SESSIONS_PATH = BASE / "app_sessions.json"

def _load() -> Dict:
    if not SESSIONS_PATH.exists():
        return {"sessions": {}}
    try:
        return json.loads(SESSIONS_PATH.read_text(encoding="utf-8"))
    except:
        return {"sessions": {}}

def _save(data: Dict):
    BASE.mkdir(parents=True, exist_ok=True)
    tmp = SESSIONS_PATH.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(SESSIONS_PATH)

def list_sessions(limit: int = 50) -> List[Dict]:
    data = _load()
    sessions = list(data.get("sessions", {}).values())
    # Sort by updated_at desc
    sessions.sort(key=lambda s: s.get("updated_at", 0), reverse=True)
    # Return summary (without messages for list)
    return [
        {
            "id": s["id"],
            "title": s.get("title","New conversation"),
            "created_at": s.get("created_at"),
            "updated_at": s.get("updated_at"),
            "message_count": len(s.get("messages", [])),
            "preview": (s.get("messages", [])[-1].get("content","")[:80] if s.get("messages") else "")
        }
        for s in sessions[:limit]
    ]

def get_session(session_id: str) -> Optional[Dict]:
    data = _load()
    return data.get("sessions", {}).get(session_id)

def create_session(title: str = None) -> Dict:
    data = _load()
    sid = f"sess-{uuid.uuid4().hex[:8]}-{int(time.time())}"
    session = {
        "id": sid,
        "title": title or "New conversation",
        "created_at": time.time(),
        "updated_at": time.time(),
        "messages": []
    }
    data["sessions"][sid] = session
    _save(data)
    return session

def delete_session(session_id: str) -> bool:
    data = _load()
    if session_id in data.get("sessions", {}):
        del data["sessions"][session_id]
        _save(data)
        return True
    return False

def append_message(session_id: str, role: str, content: str, meta: Dict = None) -> Optional[Dict]:
    data = _load()
    sess = data.get("sessions", {}).get(session_id)
    if not sess:
        # Auto-create if missing
        sess = create_session()
        data = _load()
        sess = data["sessions"][sess["id"]]
        session_id = sess["id"]
    msg = {
        "role": role,
        "content": content,
        "timestamp": time.time(),
        "id": f"msg-{uuid.uuid4().hex[:8]}",
    }
    if meta:
        # Only store safe meta (no private scratch, no CoT)
        safe_meta = {k: v for k,v in meta.items() if k in ["trace_id","deliberation_level","verification","latency_ms","model","provenance","mock"]}
        msg["meta"] = safe_meta
    sess["messages"].append(msg)
    # Update title from first user message if default
    if sess.get("title") == "New conversation" and role == "user" and content:
        sess["title"] = content[:40] + ("…" if len(content)>40 else "")
    sess["updated_at"] = time.time()
    # Keep max 100 messages per session
    if len(sess["messages"]) > 100:
        sess["messages"] = sess["messages"][-100:]
    _save(data)
    return {"session_id": session_id, "message": msg, "session": sess}

def rename_session(session_id: str, title: str) -> bool:
    data = _load()
    sess = data.get("sessions", {}).get(session_id)
    if not sess:
        return False
    sess["title"] = title[:60]
    sess["updated_at"] = time.time()
    _save(data)
    return True
