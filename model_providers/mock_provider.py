"""
Mock Model Provider — clearly marked as development fallback.
Never pretend to be a real AI model.
"""
from .base import ModelProvider
from typing import Dict, Any
import time

class MockProvider(ModelProvider):
    name = "mock"

    def generate(self, prompt: str, context=None) -> Dict[str, Any]:
        # Deterministic mock, no external call
        return {
            "text": f"[MOCK] NIS mock response to: {prompt[:120]!r} — This is a development fallback. Configure a real provider via MODEL_PROVIDER env. Time {time.strftime('%Y-%m-%d %H:%M UTC', time.gmtime())}",
            "provenance": "mock_provider:MOCK",
            "mock": True,
            "model": "mock-nis-v0.1"
        }

    def health(self) -> Dict[str, Any]:
        return {
            "status": "ok",
            "details": "Mock provider always available (development fallback)",
            "mock": True,
            "provider": self.name
        }
