"""Orchestrator (root) agent of the FatiBot system.

It orchestrates two specialist agents as **tools** (`AgentTool`) so it always stays in control and
composes the final reply itself, then delivers that reply through `send_reply` — which runs the
compliance guardrail and **pauses for human approval** (HITL). Using AgentTool (instead of
transfer-based sub_agents) is what makes the human-approval gate reliable, and it makes both the
guardrail and the approval visible in `adk web`.
"""
from __future__ import annotations

from google.adk.agents import LlmAgent
from google.adk.models.google_llm import Gemini
from google.adk.tools.agent_tool import AgentTool

from config import MODEL, retry_config
from guardrails.claims_filter import claims_after_model_callback

from .product_advisor import product_advisor
from .order_agent import order_agent
from .approval import send_reply_tool

coordinator = LlmAgent(
    name="Orchestrator",
    model=Gemini(model=MODEL, retry_options=retry_config),
    description="Orchestrator (root) of the FatiBot system for Fatima's Garden; calls the specialists and sends the reply for human approval.",
    instruction=(
        "You are FatiBot, the customer-service assistant for 'Fatima's Garden', an organic Moroccan "
        "cosmetics shop. You are warm, helpful and brand-aware.\n"
        "- For skin/hair concerns and product recommendations, call the `product_advisor` tool.\n"
        "- For stock availability or order status, call the `order_agent` tool.\n"
        "- Use those tools to gather what you need, then compose ONE concise, friendly reply in English.\n"
        "- IMPORTANT: deliver your final reply by calling the `send_reply` tool with the FULL reply "
        "text. Do NOT write the final reply as plain text — ALWAYS send it via `send_reply`. After "
        "`send_reply` returns, tell the user in one short line whether it was sent or held.\n"
        "- NEVER invent products, prices, stock or order data — rely on the specialist tools.\n"
        "- COMPLIANCE: cosmetic benefit claims are allowed and encouraged (e.g. 'helps moisturize', "
        "'nourishing', 'helps soften the appearance of', 'traditionally used in Moroccan skincare'). "
        "Only MEDICAL or THERAPEUTIC claims are forbidden ('cure', 'treat', 'heal', 'eczema', "
        "'psoriasis', 'antibacterial', 'medical', 'therapeutic'). If asked for a forbidden medical "
        "claim, decline in general terms (do NOT quote the forbidden words) and pivot to compliant help."
    ),
    tools=[
        AgentTool(agent=product_advisor),
        AgentTool(agent=order_agent),
        send_reply_tool,
    ],
    after_model_callback=claims_after_model_callback,
)
