"""
NIS App v0.1 — FastAPI backend
Serves API + static frontend, wraps NIS Core via adapter.
"""
import os, sys, time, pathlib
# Ensure project root is on path
sys.path.insert(0, str(pathlib.Path(__file__).parent.parent))

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List

from app.adapter import NISAdapter
from app.sessions import list_sessions, get_session, create_session, append_message, delete_session, rename_session
from app.config import get_public_config, is_debug
from model_providers import get_provider

app = FastAPI(title="NIS App v0.1", description="NIS — intelligent assistant shell around NIS Core", version="0.1")

# CORS for phone browser + local dev
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Singletons
provider = get_provider()
adapter = NISAdapter(provider)

# --- Models ---
class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = None
    attachments: Optional[List[str]] = None

class NewSessionRequest(BaseModel):
    title: Optional[str] = None

class RenameRequest(BaseModel):
    title: str

# --- Health & Config ---
@app.get("/api/health")
def health():
    h = adapter.health()
    # Also check adapter
    return {"status": "ok" if h.get("status")=="ok" else "degraded", "provider": h, "app": "nis-app-v0.1", "time": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}

@app.get("/api/config")
def config():
    # PUBLIC only
    return get_public_config()

# --- Sessions ---
@app.get("/api/sessions")
def sessions():
    try:
        return {"sessions": list_sessions()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"session list failed: {e}" if is_debug() else "session list failed")

@app.post("/api/sessions")
def new_session(req: NewSessionRequest = None):
    try:
        title = (req.title if req else None)
        sess = create_session(title)
        return {"session": sess}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e) if is_debug() else "create failed")

@app.get("/api/sessions/{session_id}")
def get_sess(session_id: str):
    sess = get_session(session_id)
    if not sess:
        raise HTTPException(status_code=404, detail="session not found")
    return {"session": sess}

@app.delete("/api/sessions/{session_id}")
def del_sess(session_id: str):
    ok = delete_session(session_id)
    if not ok:
        raise HTTPException(status_code=404, detail="not found")
    return {"deleted": True}

@app.post("/api/sessions/{session_id}/rename")
def rename_sess(session_id: str, req: RenameRequest):
    ok = rename_session(session_id, req.title)
    if not ok:
        raise HTTPException(status_code=404, detail="not found")
    return {"renamed": True}

# --- Chat ---
@app.post("/api/chat")
def chat(req: ChatRequest):
    # Basic validation done in adapter, but also here
    if not req.message or not req.message.strip():
        raise HTTPException(status_code=400, detail="message required")
    # Ensure session exists
    session_id = req.session_id
    if not session_id or not get_session(session_id):
        sess = create_session()
        session_id = sess["id"]
    # Append user message to session (UI history)
    append_message(session_id, "user", req.message, meta={"trace_id": None})
    # Call NIS Core via adapter
    result = adapter.chat(req.message, session_id=session_id, attachments=req.attachments)
    if result.get("status") == "error":
        # Map to HTTP but still return JSON for UI to display gracefully
        # For model_unavailable, return 503 with message
        error = result.get("error","unknown")
        msg = result.get("message","error")
        # Still store assistant error as message? No, return error payload
        return JSONResponse(status_code=503 if error=="model_unavailable" else 500, content={
            "error": error,
            "message": msg,
            "details": result.get("details"),
            "trace_id": result.get("trace_id"),
            "session_id": session_id,
        })
    # Success: append assistant message to session
    assistant_text = result.get("message","")
    meta = result.get("meta", {})
    meta["trace_id"] = result.get("trace_id")
    meta["provenance"] = result.get("provenance")
    append_message(session_id, "assistant", assistant_text, meta=meta)
    return {
        "message": assistant_text,
        "session_id": session_id,
        "trace_id": result.get("trace_id"),
        "deliberation_level": result.get("deliberation_level"),
        "verification": result.get("verification"),
        "intent": result.get("intent"),
        "latency_ms": result.get("latency_ms"),
        "mock": result.get("mock", False),
        "provenance": result.get("provenance"),
    }

# Streaming endpoint (chunked) — optional, falls back to normal if client doesn't support
from fastapi.responses import StreamingResponse
@app.post("/api/chat/stream")
def chat_stream(req: ChatRequest):
    session_id = req.session_id or create_session()["id"]
    append_message(session_id, "user", req.message)
    def gen():
        try:
            for chunk in adapter.stream_chat(req.message, session_id=session_id):
                yield chunk
        except Exception as e:
            yield f"\n[stream error: {e}]"
    # After streaming, we still need to save full message — do it after gen? For now, save after.
    # To keep simple, call adapter.chat to get full text and stream it
    result = adapter.chat(req.message, session_id=session_id)
    full = result.get("message","") if result.get("status")=="ok" else result.get("message"," error")
    # Save
    if result.get("status")=="ok":
        append_message(session_id, "assistant", full, meta=result.get("meta", {}))
    def gen2():
        chunk_size=80
        for i in range(0, len(full), chunk_size):
            yield full[i:i+chunk_size]
            time.sleep(0.02)
    return StreamingResponse(gen2(), media_type="text/plain")

# --- Voice stubs (future) ---
@app.get("/api/voice/status")
def voice_status():
    return {"input": {"enabled": False, "interface": "VoiceInput (stub) — future"}, "output": {"enabled": False, "interface": "VoiceOutput (stub) — future"}, "note": "Voice prepared but disabled in v0.1 (minimal complexity)"}

# --- Frontend static ---
# Serve frontend from /frontend via static mount, but also return index.html for root
FRONTEND_DIR = pathlib.Path(__file__).parent.parent / "frontend"
if FRONTEND_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(FRONTEND_DIR)), name="static")

@app.get("/", response_class=HTMLResponse)
def root():
    index = FRONTEND_DIR / "index.html"
    if index.exists():
        return index.read_text(encoding="utf-8")
    return HTMLResponse("<h1>NIS App v0.1</h1><p>Frontend not built. API is at /api/health</p>")

@app.get("/app", response_class=HTMLResponse)
def app_page():
    return root()

# Global error handler — never leak internals unless debug
@app.exception_handler(Exception)
async def global_exc(request: Request, exc: Exception):
    if is_debug():
        return JSONResponse(status_code=500, content={"error": "internal", "details": str(exc), "path": str(request.url)})
    return JSONResponse(status_code=500, content={"error": "internal", "message": "Something went wrong. Please try again."})
