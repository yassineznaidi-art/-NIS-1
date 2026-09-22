"""
ModelProvider Abstraction — NIS App v0.1
Interface is intentionally minimal and provider-independent.
Never hard-code to one AI provider.
"""
from typing import Dict, Any, Generator, Optional
from abc import ABC, abstractmethod

class ModelProvider(ABC):
    name: str = "base"

    @abstractmethod
    def generate(self, prompt: str, context: Optional[Dict] = None) -> Dict[str, Any]:
        """
        Generate a response.
        Must return dict with at least: {"text": str, "provenance": str, "mock": bool}
        Should not raise unhandled; use health() for status.
        """
        pass

    def stream(self, prompt: str, context: Optional[Dict] = None) -> Generator[str, None, None]:
        """
        Optional streaming. Default fallback yields generate() in one chunk.
        Override for true streaming.
        """
        res = self.generate(prompt, context)
        yield res.get("text", "")

    @abstractmethod
    def health(self) -> Dict[str, Any]:
        """
        Returns {"status": "ok"|"degraded"|"unavailable", "details": str, "mock": bool}
        """
        pass
