"""Product Advisor sub-agent.

Maps a customer concern to 1-3 catalog products with a short reason each, using only
compliant cosmetic language. The forbidden-claims guardrail is wired in as an
``after_model_callback`` so every draft it produces is screened before use.
"""
from __future__ import annotations

import json
from pathlib import Path

from google.adk.agents import LlmAgent
from google.adk.models.google_llm import Gemini

from config import MODEL, retry_config
from guardrails.claims_filter import claims_after_model_callback

_DATA_DIR = Path(__file__).resolve().parent.parent / "data"
_catalog = json.loads((_DATA_DIR / "products.json").read_text(encoding="utf-8"))
_inventory = json.loads((_DATA_DIR / "inventory.json").read_text(encoding="utf-8"))

# Embed the catalog + stock snapshot so the advisor only ever recommends real items.
_catalog_text = "\n".join(
    f"- {p['sku']}: {p['name']} ({p['size']}) — for {', '.join(p['concerns'])}; "
    f"{p['short_desc']} {p['price_eur']} EUR; stock={_inventory.get(p['sku'], 'NA')}"
    for p in _catalog
)

product_advisor = LlmAgent(
    name="product_advisor",
    model=Gemini(model=MODEL, retry_options=retry_config),
    description="Recommends 1-3 catalog products for a skin or hair concern, in compliant cosmetic language.",
    instruction=(
        "You are the Product Advisor for 'Fatima's Garden', an organic Moroccan cosmetics shop.\n"
        "Recommend ONLY products from this catalog (never invent products, prices or stock):\n"
        f"{_catalog_text}\n\n"
        "Given a customer's concern, suggest 1-3 suitable products with a short reason for each.\n"
        "If a recommended product is out of stock (stock=0), say so and offer an in-stock alternative "
        "for the same concern (for example, Argan Oil for very dry skin when Shea Butter is out).\n"
        "COMPLIANCE: cosmetic benefit claims are allowed and encouraged (e.g. 'helps moisturize', "
        "'nourishing', 'helps soften the appearance of', 'traditionally used in Moroccan skincare'). "
        "Only MEDICAL or THERAPEUTIC claims are forbidden ('cure', 'treat', 'heal', 'eczema', "
        "'psoriasis', 'antibacterial', 'medical', 'therapeutic'). If asked for a forbidden medical "
        "claim, decline in general terms (do NOT quote the specific forbidden words) and still help "
        "with compliant cosmetic language. Always answer in English."
    ),
    after_model_callback=claims_after_model_callback,
)
