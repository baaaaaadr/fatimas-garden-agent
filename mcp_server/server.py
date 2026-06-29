"""Fatima's Garden — MCP server (fastmcp, stdio transport).

Exposes three tools over the Model Context Protocol:
  - search_products(concern)   -> catalog items matching a skin/hair concern
  - check_stock(sku)           -> live stock + availability for a SKU
  - get_order_status(order_id) -> status + tracking for an order

The ADK Order Agent launches this file as a subprocess and talks to it over stdio
(see ../agents/order_agent.py). You can also run it standalone for testing:

    python mcp_server/server.py
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from fastmcp import FastMCP

DATA_DIR = Path(__file__).resolve().parent.parent / "data"

# Common words that carry no concern signal (so "very dry skin" matches on "dry", not "skin").
_STOPWORDS = {"a", "an", "the", "and", "or", "for", "with", "my", "is", "it",
              "to", "of", "very", "skin", "care", "some", "need", "want", "help"}


def _load(name: str) -> Any:
    """Read a JSON file from the data/ directory."""
    with open(DATA_DIR / name, "r", encoding="utf-8") as f:
        return json.load(f)


mcp = FastMCP("fatimas-garden")


@mcp.tool
def search_products(concern: str) -> dict:
    """Search the catalog for products that address a skin or hair concern.

    Args:
        concern: free text, e.g. "dry skin", "oily skin", "fine lines", "hair".

    Returns:
        dict: {"status": "success", "query": <concern>, "matches": [product, ...]}
        where each product has sku, name, size, concerns, short_desc, price_eur.
        Returns an empty "matches" list when nothing matches (still status "success").
    """
    products = _load("products.json")
    terms = [t for t in re.split(r"[^a-z0-9]+", concern.lower()) if t and t not in _STOPWORDS]
    matches = []
    for p in products:
        concern_text = " ".join(p["concerns"]).lower()
        if terms and any(term in concern_text for term in terms):
            matches.append(p)
    return {"status": "success", "query": concern, "matches": matches}


@mcp.tool
def check_stock(sku: str) -> dict:
    """Check live stock for a single product SKU.

    Args:
        sku: product SKU, e.g. "ARGAN-30".

    Returns:
        dict: on success {"status": "success", "sku", "stock": int, "in_stock": bool,
        "availability": "in_stock" | "low_stock" | "out_of_stock"}.
        On an unknown SKU: {"status": "error", "error": "unknown_sku", "sku": <sku>}.
    """
    inventory = _load("inventory.json")
    if sku not in inventory:
        return {"status": "error", "error": "unknown_sku", "sku": sku}
    stock = int(inventory[sku])
    if stock <= 0:
        availability = "out_of_stock"
    elif stock <= 10:
        availability = "low_stock"
    else:
        availability = "in_stock"
    return {"status": "success", "sku": sku, "stock": stock, "in_stock": stock > 0, "availability": availability}


@mcp.tool
def get_order_status(order_id: str) -> dict:
    """Look up the status and tracking of a customer order.

    Args:
        order_id: order identifier, e.g. "ORD-1042".

    Returns:
        dict: on success {"status": "success", "order_id", "order_status", "tracking", "items"}.
        On an unknown order: {"status": "error", "error": "unknown_order", "order_id": <order_id>}.
    """
    orders = _load("orders.json")
    for order in orders:
        if order["order_id"].lower() == order_id.lower():
            return {
                "status": "success",
                "order_id": order["order_id"],
                "order_status": order["status"],
                "tracking": order["tracking"],
                "items": order["items"],
            }
    return {"status": "error", "error": "unknown_order", "order_id": order_id}


if __name__ == "__main__":
    # Default transport is stdio — exactly what the ADK Order Agent connects to.
    mcp.run()
