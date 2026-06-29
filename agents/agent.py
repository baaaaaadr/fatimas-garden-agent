"""ADK entry point. ``adk web`` looks for a module-level ``root_agent``."""
from .coordinator import coordinator as root_agent

__all__ = ["root_agent"]
