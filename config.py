"""Central configuration. Loads .env and exposes the model id + retry options.

NO secrets live in code — the API key is read from the environment (.env, git-ignored).
"""
from __future__ import annotations

import os
import warnings
from pathlib import Path

from dotenv import load_dotenv

# ADK marks several stable-enough features as [EXPERIMENTAL]; hide that console noise
# so demo/video output stays clean. Genuine warnings still surface.
warnings.filterwarnings("ignore", message=r"\[EXPERIMENTAL\]")

# Load the project's .env regardless of the current working directory.
load_dotenv(Path(__file__).resolve().parent / ".env")

# google-genai authenticates with GOOGLE_API_KEY. This project standardizes on
# GEMINI_API_KEY, so promote it and drop GEMINI_API_KEY to avoid the client's
# "Both GOOGLE_API_KEY and GEMINI_API_KEY are set" notice.
_key = os.environ.get("GEMINI_API_KEY")
if _key:
    os.environ["GOOGLE_API_KEY"] = _key
    os.environ.pop("GEMINI_API_KEY", None)

# Use the Gemini Developer API (an AI Studio key), not Vertex AI.
os.environ.setdefault("GOOGLE_GENAI_USE_VERTEXAI", "False")

# Model ids — verified against the live Gemini API docs (June 2026). Override via .env.
MODEL = os.environ.get("GEMINI_MODEL", "gemini-3.5-flash")
MODEL_LITE = os.environ.get("GEMINI_MODEL_LITE", "gemini-3.1-flash-lite")

# Transient-error retry policy for LLM calls (rate limits / 5xx).
try:
    from google.genai import types

    retry_config = types.HttpRetryOptions(
        attempts=5,
        exp_base=7,
        initial_delay=1,
        http_status_codes=[429, 500, 503, 504],
    )
except Exception:  # pragma: no cover - google-genai not yet importable
    retry_config = None
