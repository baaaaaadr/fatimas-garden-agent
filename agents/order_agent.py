"""Order sub-agent.

Answers stock and order-status questions by calling the MCP server's tools over stdio.
It never reads the JSON files directly — it always goes through MCP, exactly as it would
for a third-party MCP server (GitHub, a database, etc.).
"""
from __future__ import annotations

import sys
from pathlib import Path

from google.adk.agents import LlmAgent
from google.adk.models.google_llm import Gemini
from google.adk.tools.mcp_tool.mcp_toolset import McpToolset
from google.adk.tools.mcp_tool.mcp_session_manager import StdioConnectionParams
from mcp import StdioServerParameters

from config import MODEL, retry_config

_SERVER_PATH = Path(__file__).resolve().parent.parent / "mcp_server" / "server.py"

# Launch our own MCP server as a subprocess (stdio). `sys.executable` = the venv's python.
mcp_tools = McpToolset(
    connection_params=StdioConnectionParams(
        server_params=StdioServerParameters(
            command=sys.executable,
            args=[str(_SERVER_PATH)],
        ),
        timeout=30,
    )
)

order_agent = LlmAgent(
    name="order_agent",
    model=Gemini(model=MODEL, retry_options=retry_config),
    description="Answers stock and order-status questions by calling the MCP server tools.",
    instruction=(
        "You are the Order Agent for 'Fatima's Garden'. Answer questions about product stock and "
        "order status by calling your MCP tools: search_products, check_stock, get_order_status. "
        "Never guess stock or order data — always call a tool and report its result clearly and "
        "factually. SKUs look like 'ARGAN-30'; order ids look like 'ORD-1042'. Answer in English."
    ),
    tools=[mcp_tools],
)
