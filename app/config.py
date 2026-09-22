"""
App Config — separates PUBLIC vs SECRET
Never place API keys in frontend source.
"""
import os
from pathlib import Path

# Public config — safe to expose to frontend via /api/config
PUBLIC_CONFIG = {
    "app_name": "NIS",
    "app_name_ar": "نِيسْ",
    "version": "v0.1",
    "features": {
        "voice_input": False,  # prepared interface, disabled
        "voice_output": False,
        "streaming": True,  # via chunked yield, not true LLM stream
        "file_upload": True,
        "debug_mode": os.getenv("NIS_DEBUG", "false").lower() == "true",
    },
    "model_provider": os.getenv("MODEL_PROVIDER", "nis_core"),
    "memory_enabled": os.getenv("NIS_MEMORY_ENABLED", "true").lower() == "true",
    "response_style": os.getenv("NIS_RESPONSE_STYLE", "warm"),
}

# Secret config — server only, never exposed
SECRET_CONFIG = {
    "openai_api_key": os.getenv("OPENAI_API_KEY", ""),
    "anthropic_api_key": os.getenv("ANTHROPIC_API_KEY", ""),
    "model_provider": os.getenv("MODEL_PROVIDER", "nis_core"),
    "nis_debug": os.getenv("NIS_DEBUG", "false"),
    "secret_key": os.getenv("NIS_SECRET_KEY", "dev-secret-key-change-me"),
}

def get_public_config():
    # Filter to only public
    return PUBLIC_CONFIG

def is_debug():
    return PUBLIC_CONFIG["features"]["debug_mode"]
