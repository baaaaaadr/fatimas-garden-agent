"""CLI entry point — demonstrates the Human-in-the-Loop (HITL) approval gate.

    python main.py
    python main.py "your custom customer message here"

Needs GEMINI_API_KEY in .env. The coordinator (with its two sub-agents and the MCP server)
produces a DRAFT reply; the draft is screened by the claims guardrail; then a human is asked
to approve before the reply is "sent" (printed). Nothing is sent without a 'y'.
"""
from __future__ import annotations

import asyncio
import sys
from pathlib import Path

# Make the project root importable no matter the current working directory.
sys.path.insert(0, str(Path(__file__).resolve().parent))

# Print UTF-8 cleanly on Windows consoles (emojis, accents, dashes).
try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass

import config  # noqa: F401  (loads .env, configures API key + model)
from agents.coordinator import coordinator
from guardrails.claims_filter import check_claims

from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

APP_NAME = "fatimas_garden"


async def draft_reply(message: str) -> str:
    """Run the multi-agent system once and return the coordinator's final reply text."""
    session_service = InMemorySessionService()
    runner = Runner(agent=coordinator, app_name=APP_NAME, session_service=session_service)
    await session_service.create_session(app_name=APP_NAME, user_id="customer", session_id="cli")

    content = types.Content(role="user", parts=[types.Part(text=message)])
    final_text = ""
    async for event in runner.run_async(user_id="customer", session_id="cli", new_message=content):
        # Keep the latest NON-empty assistant text. In a multi-agent transfer flow the very
        # last event can be an empty transfer wrapper, so we must not let it overwrite the reply.
        if event.content and event.content.parts:
            text = "".join(part.text or "" for part in event.content.parts)
            if text.strip():
                final_text = text
    return final_text.strip()


def main() -> None:
    message = " ".join(sys.argv[1:]).strip() or (
        "Hi, I have very dry skin and damaged hair - what do you recommend? "
        "Also, has my order ORD-1043 shipped yet?"
    )
    print("\n=== Customer message ===\n" + message)

    draft = asyncio.run(draft_reply(message))

    # Defense in depth: screen the assembled draft once more before a human sees it.
    screened = check_claims(draft)
    if screened["status"] == "flagged":
        print("\n[guardrail] softened non-compliant phrasing:", screened["issues"])
    draft = screened["rewritten"]

    print("\n=== DRAFT reply (awaiting human approval) ===\n" + draft)

    try:
        decision = input("\nApprove and send this reply? [y/n] ").strip().lower()
    except EOFError:
        decision = "n"  # no interactive input available -> default to NOT sending
    if decision == "y":
        print("\n=== ✅ SENT to customer ===\n" + draft)
    else:
        print("\n=== ❌ NOT sent — held for a human to edit ===")


if __name__ == "__main__":
    main()
