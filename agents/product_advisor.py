"""Product Advisor sub-agent.

Maps a customer concern to 1-3 catalog products with a short reason each, using only
compliant cosmetic language. It verifies availability LIVE via the MCP ``check_stock`` tool
(never from a baked-in snapshot), and the forbidden-claims guardrail is wired in as an
``after_model_callback`` so every draft it produces is screened before use.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

from google.adk.agents import LlmAgent
from google.adk.models.google_llm import Gemini
from google.adk.tools.mcp_tool.mcp_toolset import McpToolset
from google.adk.tools.mcp_tool.mcp_session_manager import StdioConnectionParams
from mcp import StdioServerParameters

from config import MODEL, retry_config
from guardrails.claims_filter import claims_after_model_callback

_DATA_DIR = Path(__file__).resolve().parent.parent / "data"
_catalog = json.loads((_DATA_DIR / "products.json").read_text(encoding="utf-8"))

# Catalog WITHOUT stock numbers — availability is fetched LIVE via the check_stock MCP tool,
# so the advisor can never give a stale stock answer.
_catalog_text = "\n".join(
    f"- {p['sku']}: {p['name']} ({p['size']}) — for {', '.join(p['concerns'])}; "
    f"{p['short_desc']} {p['price_eur']} EUR"
    for p in _catalog
)

# Live availability comes from the same MCP server, limited to the check_stock tool.
_SERVER_PATH = Path(__file__).resolve().parent.parent / "mcp_server" / "server.py"
_stock_tool = McpToolset(
    connection_params=StdioConnectionParams(
        server_params=StdioServerParameters(command=sys.executable, args=[str(_SERVER_PATH)]),
        timeout=30,
    ),
    tool_filter=["check_stock"],
)

product_advisor = LlmAgent(
    name="product_advisor",
    model=Gemini(model=MODEL, retry_options=retry_config),
    description="Recommends 1-3 catalog products for a skin or hair concern, in compliant cosmetic language.",
    instruction=(
        "You are the Product Advisor for 'Fatima's Garden', an organic Moroccan cosmetics shop.\n"
        "Recommend ONLY products from this catalog (never invent products or prices):\n"
        f"{_catalog_text}\n\n"
        "Given a customer's concern, pick 1-3 suitable products and give a short reason for each.\n"
        "ALWAYS call the `check_stock` tool to verify LIVE availability before you state it — never "
        "assume or guess stock. If a suitable product is out of stock, say so and recommend an "
        "in-stock alternative for the same concern (e.g. Argan Oil for very dry skin when Shea "
        "Butter is out).\n"
        "COMPLIANCE: cosmetic benefit claims are allowed and encouraged (e.g. 'helps moisturize', "
        "'nourishing', 'helps soften the appearance of', 'traditionally used in Moroccan skincare'). "
        "Only MEDICAL or THERAPEUTIC claims are forbidden ('cure', 'treat', 'heal', 'eczema', "
        "'psoriasis', 'antibacterial', 'medical', 'therapeutic'). If asked for a forbidden medical "
        "claim, decline in general terms (do NOT quote the specific forbidden words) and still help "
        "with compliant cosmetic language. Always answer in English."
    ),
    tools=[_stock_tool],
    after_model_callback=claims_after_model_callback,
)
