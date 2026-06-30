"""Human-in-the-loop send gate (+ final compliance pass) for FatiBot.

`send_reply` is the tool the Orchestrator calls to deliver its final reply to the customer.
It is a LONG-RUNNING tool: it first runs the claims guardrail on the text, then asks a HUMAN to
confirm before the reply is "sent". In `adk web` this shows an Approve/Reject prompt and the agent
pauses until you decide; in the CLI (`main.py`) it prompts y/n. Same mechanism, two surfaces.
"""
from __future__ import annotations

from google.adk.tools.long_running_tool import LongRunningFunctionTool
from google.adk.tools.tool_context import ToolContext

from guardrails.claims_filter import check_claims


def send_reply(reply: str, tool_context: ToolContext) -> dict:
    """Deliver the final customer reply. Pauses for HUMAN APPROVAL before sending.

    Args:
        reply: the complete, customer-facing reply to review and send.

    Returns:
        dict: {"status": "pending_approval" | "sent" | "held", "reply": <compliant text>, ...}.
        First call → runs the compliance guardrail, requests human confirmation, returns
        "pending_approval". After the human decides → "sent" (approved) or "held" (rejected).
    """
    # Final compliance pass on the exact text to be sent (the guardrail, at send time).
    screened = check_claims(reply)
    safe_reply = screened["rewritten"]

    confirmation = tool_context.tool_confirmation
    if not confirmation:
        # First call: ask a human to approve before anything is sent.
        # Surface the guardrail result in the bold hint so it is visible in adk web.
        # Base the message on whether the text ACTUALLY changed (some forbidden words are
        # detection-only and intentionally not rewritten, so "flagged" != "rewritten").
        rewritten_something = safe_reply != reply
        if rewritten_something:
            hint = "Approve sending this reply?   GUARDRAIL: rewrote forbidden claim(s) to stay compliant."
        else:
            hint = "Approve sending this reply?   GUARDRAIL: compliant (no medical claims)."
        tool_context.request_confirmation(
            hint=hint,
            payload={
                "reply": safe_reply,
                "guardrail": "rewritten" if rewritten_something else "compliant",
            },
        )
        return {
            "status": "pending_approval",
            "reply": safe_reply,
            "compliance": screened["status"],
        }

    # Resumed after the human decided.
    if confirmation.confirmed:
        return {"status": "sent", "reply": safe_reply}
    return {"status": "held", "message": "Not approved — held for a human to edit."}


# Long-running so ADK pauses for the human decision (works in `adk web` and the CLI).
send_reply_tool = LongRunningFunctionTool(send_reply)
