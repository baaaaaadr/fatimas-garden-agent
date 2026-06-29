# CLAUDE.md — Fatima's Garden Advisor Agent

> Build spec for Claude Code. This is a **Kaggle capstone prototype** (Google × Kaggle
> 5-Day AI Agents). Optimize for a clean, runnable, well-documented prototype —
> **NOT** a production deployment. Favor clarity over cleverness.
>
> **Updated 2026-06-29:** model ids refreshed to the current Gemini API (the original spec's
> `gemini-2.5-*` is a generation behind; `gemini-2.0-*` was shut down 2026-06-01). See §2/§6.

---

## 1. Mission

Build a multi-agent customer-service assistant for an organic Moroccan cosmetics
e-commerce store ("Fatima's Garden"). Flow:

1. A customer describes a skin or hair concern in natural language.
2. The system recommends suitable products from the catalog.
3. It checks live stock and (if asked) order status.
4. It drafts a customer-service reply.
5. It **pauses for human approval** before the reply is "sent".

A **compliance guardrail** ensures the reply never contains forbidden cosmetic claims
(no medical/therapeutic promises).

---

## 2. Stack (do not deviate)

- **Python 3.11+**
- **Google ADK** (Agent Development Kit) — package `google-adk`
- **Gemini** via ADK — `gemini-3.5-flash` for the coordinator and sub-agents.
  `gemini-3.1-pro-preview` (or stable `gemini-2.5-pro`) allowed for the coordinator if planning
  quality needs it. Model name read from env (see §6). Verified current ids as of 2026-06-29.
- **MCP** (Model Context Protocol) server via **`fastmcp`**, **stdio** transport.
- `python-dotenv` for config.
- **No** web framework, **no** cloud, **no** database server. Seed data = local JSON files.

> ADK's MCP integration uses `McpToolset` with `StdioConnectionParams` +
> `StdioServerParameters`. Import paths verified against the installed `google-adk`.
> Reference: https://google.github.io/adk-docs/ and the Day 2b MCP pattern from the course.

---

## 3. Hard constraints (non-negotiable)

- **NEVER hardcode API keys or secrets.** Read `GEMINI_API_KEY` from the environment
  (`.env`, git-ignored). Ship `.env.example` only. Keys in code = disqualified.
- Repo must be **public-safe**: all data is **fictional/mock**. No real customer data.
- **User-facing agent output in English.**
- Every tool gets a **rich docstring**: purpose, args, return value, and error shape.
  Returns must be concise and structured (dicts with a `status` field).
- Keep it **Level 2–3**: one coordinator + two specialist sub-agents. **No A2A, no remote
  agents, no payment protocols.**

---

## 4. Architecture

```
                    ┌─────────────────────────┐
   customer ──────► │   Orchestrator (root)   │  gemini-3.5-flash
   message          │  - routes to specialists │
                    │  - assembles reply       │
                    │  - HITL approval pause   │
                    └───────┬─────────┬────────┘
                            │         │
              delegates to  │         │  delegates to
                            ▼         ▼
        ┌───────────────────────┐   ┌──────────────────────────┐
        │   Product Advisor      │   │   Order Agent             │
        │  - maps concern→product│   │  - stock & order status   │
        │  - CLAIMS GUARDRAIL    │   │  - calls MCP tools         │
        └───────────────────────┘   └────────────┬──────────────┘
                                                  │ MCP (stdio)
                                                  ▼
                              ┌──────────────────────────────────┐
                              │   MCP Server (fastmcp)            │
                              │  search_products / check_stock /  │
                              │  get_order_status                 │
                              │  ← reads data/*.json              │
                              └──────────────────────────────────┘
```

**Orchestrator (the coordinator / root agent):** receives the customer message, decides which
sub-agent(s) to call, aggregates their output into a single draft reply, then triggers the
human-approval step before producing the final "sent" message. It is the brain of the **FatiBot**
system and speaks to the customer as "FatiBot". Persona: helpful, warm, brand-aware support
assistant. Must NOT invent products or stock numbers — always rely on sub-agents.

**Product Advisor (sub-agent):** given a concern, recommends 1–3 catalog products with a short
reason each. **Applies the claims guardrail** (§7): only compliant cosmetic language. If a
recommended product is out of stock, says so and suggests an in-stock alternative.

**Order Agent (sub-agent):** answers stock and order-status questions by calling the **MCP
server tools** (never reads JSON directly — it goes through MCP). Returns clear, factual status.

---

## 5. Concepts demonstrated (Kaggle requires ≥ 3)

| # | Concept | Where | How |
|---|---|---|---|
| 1 | **Multi-agent system (ADK)** | Code | Coordinator + 2 sub-agents via `sub_agents=[...]` |
| 2 | **MCP Server** | Code | Custom `fastmcp` server exposing catalog/stock/order tools |
| 3 | **Security / HITL** | Code | Forbidden-claims guardrail + human-approval pause |

The agent runs on **Gemini** (ADK + Gemini API) — the required Google stack. "Antigravity"
(the IDE used to build it) is an optional 4th concept shown only in the video; it is **not** a
code task.

---

## 6. File structure

```
fatimas-garden-agent/
├── CLAUDE.md                 # this file
├── README.md                 # problem, solution, architecture, setup/run
├── .env.example              # GEMINI_API_KEY + GEMINI_MODEL=gemini-3.5-flash
├── .gitignore                # .env, __pycache__/, *.pyc, .venv/
├── requirements.txt          # google-adk, fastmcp, python-dotenv
├── config.py                 # loads .env, exposes MODEL + retry options
├── data/
│   ├── products.json         # catalog (§8)
│   ├── inventory.json        # stock levels per SKU
│   └── orders.json           # sample orders + statuses
├── mcp_server/
│   └── server.py             # fastmcp server: search_products, check_stock, get_order_status
├── agents/
│   ├── __init__.py
│   ├── agent.py              # exposes `root_agent` for `adk web`
│   ├── coordinator.py        # root agent + delegation
│   ├── product_advisor.py    # advisor sub-agent + claims guardrail
│   └── order_agent.py        # order sub-agent + MCPToolset connection
├── guardrails/
│   └── claims_filter.py      # forbidden-claims checker (pure function + ADK callback)
└── main.py                   # CLI entrypoint showing the HITL approval step
```

Runnable **two ways**:
- `adk web` → visual demo (multi-agent flow + MCP tool calls + Trace tab).
- `python main.py` → CLI that prints the DRAFT and asks `Approve? [y/n]` before the final "SENT" reply.

---

## 7. The claims guardrail (the distinctive part)

Cosmetics must not make **medical or therapeutic claims**. `guardrails/claims_filter.py`:
- `check_claims(text) -> {"status": "ok"|"flagged", "issues": [...], "rewritten": ...}` (pure function).
- Forbidden patterns (case-insensitive): `cure(s)`, `treat(s)`, `heal(s)`, `eczema`, `psoriasis`,
  `acne treatment`, `antibacterial`, `medical`, `therapeutic`, `clinically proven to cure`,
  `eliminates wrinkles`.
- Compliant rewrites: "helps moisturize", "may help soften the appearance of", "traditionally used
  in Moroccan skincare", "nourishing", "for the look of".
- Wired into ADK via `after_model_callback` so a flagged draft is corrected before reaching the customer.

---

## 8. Seed data (fictional, public-safe; mainstream products only)

`data/products.json` — 6 items, shape `{sku, name, size, concerns[], short_desc, price_eur}`:
ARGAN-30, ROSEHIP-30, ALOE-100, SHEA-100, CLAYMASK-100, ROSEWATER-100.

`data/inventory.json` — stock per SKU, with edge cases: `ROSEHIP-30`=6 (low), `SHEA-100`=0 (out →
advisor suggests an in-stock alternative), the rest 25–90.

`data/orders.json` — 3 orders `{order_id, items[], status, tracking}`: ORD-1042 shipped/TRK-1042,
ORD-1043 processing/null, ORD-1044 delivered/TRK-1044.

---

## 9. Out of scope — do NOT build

OpenTelemetry observability, LLM-as-a-judge eval, CI/CD, Terraform/IaC, live deployment,
A2A / remote agents, payment protocols (AP2/x402). These belong to Days 4–5 and add risk.
