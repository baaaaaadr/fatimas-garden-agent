"""Fatima's Garden agent package.

Ensures the project root is importable (so ``config``, ``guardrails`` and ``mcp_server``
resolve) regardless of how the package is loaded (``adk web`` or ``python main.py``),
then exposes the agent module for ADK discovery.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import config  # noqa: E402,F401  (loads .env, installs warning filter, configures key)
from . import agent  # noqa: E402,F401
