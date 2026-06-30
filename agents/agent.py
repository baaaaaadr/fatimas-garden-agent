"""ADK entry points.

Exposes `app` — a **resumable** App so `adk web` (and the CLI) can pause for human approval when the
Orchestrator calls the `send_reply` tool — and `root_agent` for discovery. ADK's loader prefers
`app` when present, so `adk web` runs the resumable App automatically.
"""
from google.adk.apps.app import App, ResumabilityConfig

from .coordinator import coordinator as root_agent

# Resumable → enables the human-in-the-loop confirmation pause in `adk web` and the CLI.
app = App(
    name="agents",
    root_agent=root_agent,
    resumability_config=ResumabilityConfig(is_resumable=True),
)

__all__ = ["app", "root_agent"]
