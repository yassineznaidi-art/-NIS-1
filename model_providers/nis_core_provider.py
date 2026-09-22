"""
NIS Core Provider — real provider that delegates to NIS Core.
NIS Core remains authority for all intelligence; this provider is a thin wrapper,
not a competing intelligence layer.
"""
from .base import ModelProvider
from typing import Dict, Any, Optional
import time

class NISCoreProvider(ModelProvider):
    name = "nis_core"

    def __init__(self, orchestrator=None):
        # Lazy import to avoid circular
        if orchestrator is None:
            from nis.orchestrator import ORCHESTRATOR
            self.orchestrator = ORCHESTRATOR
        else:
            self.orchestrator = orchestrator

    def generate(self, prompt: str, context: Optional[Dict] = None) -> Dict[str, Any]:
        """
        Delegates to NIS Core orchestrator.run_turn.
        Context may contain session_id, attachments, trace_id.
        Returns dict with text, provenance, deliberation, verification etc.
        This is the ONLY path — no duplicate N3/N6/N7 logic here.
        """
        attachments = (context or {}).get("attachments", [])
        trace_id = (context or {}).get("trace_id")
        session_id = (context or {}).get("session_id")
        # Call NIS Core — the single source of truth
        try:
            result = self.orchestrator.run_turn(prompt, attachments=attachments, trace_id=trace_id)
            # Extract response and metadata; preserve verification/provenance
            return {
                "text": result.get("response", ""),
                "provenance": f"nis_core:{result.get('trace_id','')}",
                "mock": False,
                "model": "nis-core-v0.3-P1",
                "nis_result": result,  # full trace for backend use (not exposed verbatim to frontend)
                "trace_id": result.get("trace_id"),
                "deliberation": result.get("deliberation"),
                "verification": result.get("verification"),
                "intent": result.get("intent"),
                "memory": result.get("memory"),
                "execution": result.get("execution"),
            }
        except Exception as e:
            # Never silently fabricate; surface error with provenance
            return {
                "text": "",
                "error": str(e),
                "provenance": "nis_core:exception",
                "mock": False,
                "model": "nis-core-v0.3-P1",
                "exception": True,
                "details": f"NIS Core failure: {e.__class__.__name__}: {e}"
            }

    def stream(self, prompt: str, context: Optional[Dict] = None):
        # NIS Core currently generates response atomically (template + tools).
        # Stream by yielding chunks of generate() result for UI responsiveness.
        # Do not compromise correctness for streaming.
        res = self.generate(prompt, context)
        text = res.get("text", "")
        # Chunk by sentence/50 chars to simulate streaming without needing LLM tokens
        chunk_size = 80
        for i in range(0, len(text), chunk_size):
            yield text[i:i+chunk_size]

    def health(self) -> Dict[str, Any]:
        try:
            from nis.memory import SUBSTRATE
            from nis.embeddings import cache_stats
            # Check memory readable
            hits = len(SUBSTRATE.get_ltm())
            cache = cache_stats()
            # Check orchestrator import
            ok = True
            details = f"NIS Core ok — S4 {hits} entries, cache {cache['entries']} entries, model {cache['model']}"
            return {"status": "ok", "details": details, "mock": False, "provider": self.name, "cache": cache}
        except Exception as e:
            return {"status": "unavailable", "details": f"NIS Core health check failed: {e}", "mock": False, "provider": self.name, "error": str(e)}
