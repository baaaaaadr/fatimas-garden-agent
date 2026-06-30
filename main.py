"""CLI entry point — runs FatiBot and demonstrates the Human-in-the-Loop approval gate.

The Orchestrator gathers info from the specialists, composes a reply, then calls the `send_reply`
tool which PAUSES for human approval. This CLI detects that pause, shows the draft, asks y/n, and
resumes — the same approval that `adk web` shows as an Approve/Reject button. Needs GEMINI_API_KEY.

    python main.py
    python main.py "your custom customer message here"
"""
from __future__ import annotations

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

# Clean UTF-8 output on Windows consoles (emojis, accents).
try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass

import config  # noqa: F401  (loads .env, configures API key + model)
from agents.agent import app
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

APP_NAME = app.name


def _confirmation_call(event):
    """Return the `adk_request_confirmation` function call in an event, if present."""
    for fc in (event.get_function_calls() or []):
        if fc.name == "adk_request_confirmation":
            return fc
    return None


async def run(message: str) -> None:
    session_service = InMemorySessionService()
    runner = Runner(app=app, session_service=session_service)
    await session_service.create_session(app_name=APP_NAME, user_id="customer", session_id="cli")

    state = {"pending_id": None, "draft": "", "final": ""}

    async def consume(new_message):
        async for event in runner.run_async(user_id="customer", session_id="cli", new_message=new_message):
            fc = _confirmation_call(event)
            if fc:
                state["pending_id"] = fc.id
                args = dict(fc.args) if fc.args else {}
                tc = args.get("toolConfirmation") or args.get("tool_confirmation") or {}
                payload = tc.get("payload") if isinstance(tc, dict) else None
                if isinstance(payload, dict) and payload.get("reply"):
                    state["draft"] = payload["reply"]
            if event.content and event.content.parts:
                text = "".join(part.text or "" for part in event.content.parts)
                if text.strip():
                    state["final"] = text

    print("\n=== Customer message ===\n" + message)
    await consume(types.Content(role="user", parts=[types.Part(text=message)]))

    if state["pending_id"]:
        print("\n=== DRAFT reply (awaiting human approval) ===\n" + (state["draft"] or state["final"] or "(draft ready)"))
        try:
            approved = input("\nApprove and send this reply? [y/n] ").strip().lower() == "y"
        except EOFError:
            approved = False  # no interactive input -> default to NOT sending
        resume = types.Content(role="user", parts=[types.Part(
            function_response=types.FunctionResponse(
                id=state["pending_id"], name="adk_request_confirmation", response={"confirmed": approved}))])
        state["pending_id"] = None
        await consume(resume)
        print("\n=== " + ("✅ SENT to customer" if approved else "❌ NOT sent — held for a human") + " ===")

    if state["final"].strip():
        print("\n" + state["final"].strip())


def main() -> None:
    message = " ".join(sys.argv[1:]).strip() or (
        "I have very dry skin and damaged hair - what do you recommend? "
        "Also, has my order ORD-1043 shipped yet?"
    )
    asyncio.run(run(message))


if __name__ == "__main__":
    main()
