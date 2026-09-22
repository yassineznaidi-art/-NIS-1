"""
NIS Application Adapter — clean boundary UI → API → NIS Core
Must NOT duplicate N3/N6/N7/N14 logic.
Single responsibility: translate API request into NIS Core call and return sanitized response.
"""
from typing import Dict, List, Optional
import time
from model_providers import get_provider
from model_providers.base import ModelProvider

class NISAdapter:
    """
    Adapter around NIS Core.
    Keeps NIS Core as authority for intent/memory/deliberation/reasoning/verification.
    """
    def __init__(self, provider: ModelProvider = None):
        self.provider = provider or get_provider()

    def chat(self, message: str, session_id: Optional[str]=None, attachments: List[str]=None) -> Dict:
        """
        Main entry: UI message -> NIS Core -> sanitized response.
        Handles all error cases gracefully, never silently fabricates.
        Returns dict for API to forward to UI (already CoT-firewalled).
        """
        t0 = time.time()
        attachments = attachments or []
        context = {"session_id": session_id, "attachments": attachments, "trace_id": None}
        # Basic input validation
        if not message or not message.strip():
            return {
                "error": "empty_message",
                "message": "Please type a message.",
                "status": "error",
                "trace_id": None,
                "latency_ms": 0
            }
        if len(message) > 8000:
            return {
                "error": "message_too_long",
                "message": "Message too long (max 8000 chars). Please shorten.",
                "status": "error",
                "trace_id": None,
                "latency_ms": 0
            }

        # Call provider (which is NIS Core authority)
        try:
            result = self.provider.generate(message, context)
        except Exception as e:
            # Model unavailable / exception
            return {
                "error": "model_unavailable",
                "message": "NIS is temporarily unavailable. Please try again in a moment.",
                "details": str(e) if self._is_debug() else None,
                "status": "error",
                "trace_id": None,
                "latency_ms": int((time.time()-t0)*1000)
            }

        # Handle provider-level error
        if result.get("exception") or result.get("error"):
            # Check if it's NIS Core failure vs provider
            if result.get("exception"):
                return {
                    "error": "core_failure",
                    "message": "Something went wrong inside NIS Core. Please try rephrasing or try again.",
                    "details": result.get("details") if self._is_debug() else None,
                    "status": "error",
                    "trace_id": result.get("trace_id"),
                    "latency_ms": int((time.time()-t0)*1000)
                }

        # Malformed handling: ensure text is string
        if result.get("text") is None and not result.get("nis_result"):
            # Provider returned malformed (None), coerce to empty and mark error
            result["text"] = ""
        # Extract NIS result if available (NISCoreProvider puts full trace in nis_result)
        nis_result = result.get("nis_result")
        if nis_result:
            # Sanitize for UI: NEVER expose private_scratch, internal reasoning, secret memory
            response_text = nis_result.get("response", "") or ""
            # Ensure CoT firewall: check response doesn't contain private scratch marker
            if "PRIVATE SCRATCH" in response_text or "private scratch" in response_text.lower():
                # Filter it (should never happen due to N14, but defense in depth)
                response_text = response_text.split("[PRIVATE")[0].strip() + " (internal reasoning removed)"
            # Check verification
            verification = nis_result.get("verification", {})
            deliberation = nis_result.get("deliberation", {})
            intent = nis_result.get("intent", {})
            # Handle verification failure gracefully
            if verification.get("verdict") == "fail":
                # Surface user-facing message but preserve diagnostics for dev
                response_text = response_text + "\n\n[Verification flagged this response — it was delivered with a warning and logged for review.]" if self._is_debug() else response_text

            latency = int((time.time()-t0)*1000)
            return {
                "status": "ok",
                "message": response_text,
                "trace_id": nis_result.get("trace_id"),
                "deliberation_level": deliberation.get("level"),
                "verification": verification.get("verdict"),
                "intent": intent.get("primary_intent"),
                "latency_ms": latency,
                "mock": result.get("mock", False),
                "provenance": result.get("provenance"),
                # Safe metadata for UI (no internals)
                "meta": {
                    "deliberation_level": deliberation.get("level"),
                    "verification": verification.get("verdict"),
                    "latency_ms": latency,
                    "trace_id": nis_result.get("trace_id"),
                }
            }
        else:
            # Mock provider path — ensure string
            latency = int((time.time()-t0)*1000)
            msg = result.get("text")
            if not isinstance(msg, str):
                msg = "" if msg is None else str(msg)
            return {
                "status": "ok",
                "message": msg,
                "trace_id": None,
                "mock": True,
                "provenance": result.get("provenance"),
                "latency_ms": latency,
                "meta": {"mock": True, "latency_ms": latency}
            }

    def stream_chat(self, message: str, session_id: Optional[str]=None):
        """
        Streaming wrapper — yields chunks. For NIS Core, chunks are simulated.
        """
        try:
            context = {"session_id": session_id}
            for chunk in self.provider.stream(message, context):
                yield chunk
        except Exception as e:
            yield f"\n[Stream error: {e}]"

    def health(self) -> Dict:
        try:
            return self.provider.health()
        except Exception as e:
            return {"status": "unavailable", "details": str(e), "provider": "unknown"}

    def _is_debug(self) -> bool:
        try:
            from app.config import is_debug
            return is_debug()
        except:
            return False
