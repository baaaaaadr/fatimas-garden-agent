"""Orchestrator — the coordinator (root) agent of the FatiBot system.

Receives the customer message, delegates to the two specialist sub-agents, and assembles
one concise, brand-aware reply. A second pass of the claims guardrail runs here too, so the
final assembled draft is compliant before the human-approval step in main.py.
"""
from __future__ import annotations

from google.adk.agents import LlmAgent
from google.adk.models.google_llm import Gemini

from config import MODEL, retry_config
from guardrails.claims_filter import claims_after_model_callback

from .product_advisor import product_advisor
from .order_agent import order_agent

coordinator = LlmAgent(
    name="Orchestrator",
    model=Gemini(model=MODEL, retry_options=retry_config),
    description="Orchestrator (root) of the FatiBot system for Fatima's Garden; routes to specialists and assembles the reply.",
    instruction=(
        "You are FatiBot, the customer-service assistant for 'Fatima's Garden', an organic Moroccan "
        "cosmetics shop. You are the orchestrator that coordinates specialist agents; you are warm, "
        "helpful and brand-aware.\n"
        "- For skin/hair concerns and product recommendations, delegate to `product_advisor`.\n"
        "- For stock availability or order status, delegate to `order_agent`.\n"
        "- You may use both, then assemble ONE concise, friendly reply in English.\n"
        "- NEVER invent products, prices, stock or order data — always rely on the sub-agents.\n"
        "- COMPLIANCE: cosmetic benefit claims are allowed and encouraged (e.g. 'helps moisturize', "
        "'nourishing', 'helps soften the appearance of', 'traditionally used in Moroccan skincare'). "
        "Only MEDICAL or THERAPEUTIC claims are forbidden ('cure', 'treat', 'heal', 'eczema', "
        "'psoriasis', 'antibacterial', 'medical', 'therapeutic'). If asked to make a forbidden medical "
        "claim, politely decline in GENERAL terms — do NOT quote or repeat the specific forbidden "
        "words — and pivot to how you can help with compliant cosmetic language."
    ),
    sub_agents=[product_advisor, order_agent],
    after_model_callback=claims_after_model_callback,
)
