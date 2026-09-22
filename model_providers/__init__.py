from .base import ModelProvider
from .mock_provider import MockProvider
from .nis_core_provider import NISCoreProvider

def get_provider(name: str = None) -> ModelProvider:
    """
    Factory: reads env MODEL_PROVIDER (nis_core | mock | auto)
    auto = try nis_core, fallback to mock
    Never hard-codes to one provider.
    """
    import os
    requested = (name or os.getenv("MODEL_PROVIDER", "nis_core")).lower()
    if requested == "mock":
        return MockProvider()
    if requested == "nis_core":
        try:
            return NISCoreProvider()
        except Exception as e:
            # Fallback to mock if core unavailable, but clearly mark
            print(f"WARNING: NIS Core provider unavailable ({e}), falling back to mock")
            return MockProvider()
    if requested == "auto":
        try:
            p = NISCoreProvider()
            h = p.health()
            if h.get("status") == "ok":
                return p
            return MockProvider()
        except:
            return MockProvider()
    # Unknown -> try nis_core first
    try:
        return NISCoreProvider()
    except:
        return MockProvider()
