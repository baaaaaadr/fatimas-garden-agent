"""Forbidden-claims guardrail — the graded "Security" concept.

Cosmetics may NOT make medical or therapeutic claims (EU Reg. 1223/2009 and UK/US
equivalents). A moisturizer "helps soften the appearance of fine lines"; it does not
"cure wrinkles". This module enforces that on every customer-facing draft.

Two layers:
  1. ``check_claims(text)`` — a pure, unit-testable function. Detects forbidden phrasing
     and returns a compliant rewrite.
  2. ``claims_after_model_callback(...)`` — an ADK ``after_model_callback`` that runs the
     model's draft through ``check_claims`` and softens it BEFORE it reaches the customer.
"""
from __future__ import annotations

import re
from typing import Optional

# Forbidden medical/therapeutic patterns (case-insensitive). Longer phrases first so they
# are detected/rewritten before their shorter sub-phrases.
FORBIDDEN_PATTERNS: list[str] = [
    r"clinically proven to cure",
    r"eliminates wrinkles",
    r"acne treatment",
    r"\bcures?\b",
    r"\btreats?\b",
    r"\bheals?\b",
    r"\beczema\b",
    r"\bpsoriasis\b",
    r"\bantibacterial\b",
    r"\bmedical\b",
    r"\btherapeutic\b",
]

# Compliant rewrites applied in order (forbidden -> allowed cosmetic phrasing).
REWRITES: list[tuple[str, str]] = [
    (r"clinically proven to cure", "traditionally used to help with"),
    (r"eliminates wrinkles", "helps soften the appearance of fine lines"),
    (r"acne treatment", "care for blemish-prone skin"),
    (r"\bcures?\b", "helps care for"),
    (r"\btreats?\b", "helps care for"),
    (r"\bheals?\b", "helps soothe"),
    (r"\beczema\b", "dryness"),
    (r"\bpsoriasis\b", "dry, flaky skin"),
    (r"\bantibacterial\b", "cleansing"),
    # NOTE: 'medical' and 'therapeutic' are DETECTED (see FORBIDDEN_PATTERNS) and logged, but
    # intentionally NOT auto-rewritten — they usually appear when the assistant *explains* it will
    # not make such claims, and blindly swapping them would invert that meaning.
]

# Compliant phrases to steer the model toward (referenced in agent instructions too).
COMPLIANT_HINTS: list[str] = [
    "helps moisturize",
    "may help soften the appearance of",
    "traditionally used in Moroccan skincare",
    "nourishing",
    "for the look of",
]


def check_claims(text: str) -> dict:
    """Screen text for forbidden cosmetic claims and produce a compliant rewrite.

    Args:
        text: a draft customer-facing message or product recommendation.

    Returns:
        dict: {"status": "ok" | "flagged", "issues": [matched phrases], "rewritten": str}.
        When status == "ok", "rewritten" equals the input unchanged.
    """
    if not text:
        return {"status": "ok", "issues": [], "rewritten": text}

    issues: list[str] = []
    for pattern in FORBIDDEN_PATTERNS:
        for match in re.finditer(pattern, text, flags=re.IGNORECASE):
            issues.append(match.group(0))

    rewritten = text
    for pattern, replacement in REWRITES:
        rewritten = re.sub(pattern, replacement, rewritten, flags=re.IGNORECASE)

    return {"status": "flagged" if issues else "ok", "issues": issues, "rewritten": rewritten}


def claims_after_model_callback(callback_context, llm_response):
    """ADK ``after_model_callback``: soften forbidden claims in the model's draft.

    Mutates the response parts in place and returns the modified ``LlmResponse`` when the
    draft was flagged; returns ``None`` to keep the original otherwise. The guardrail
    fails open (returns None) on any unexpected shape so it can never break the agent.

    Signature follows ADK: (callback_context: CallbackContext, llm_response: LlmResponse).
    """
    try:
        content = getattr(llm_response, "content", None)
        parts = getattr(content, "parts", None) if content else None
        if not parts:
            return None
        changed = False
        for part in parts:
            text = getattr(part, "text", None)
            if not text:
                continue
            result = check_claims(text)
            if result["status"] == "flagged":
                # Visible when the guardrail actually fires (CLI or `adk web` terminal).
                print(f"[guardrail] softened forbidden claims: {result['issues']}", flush=True)
                part.text = result["rewritten"]
                changed = True
        return llm_response if changed else None
    except Exception:
        return None


if __name__ == "__main__":
    samples = [
        "Argan oil is nourishing and helps moisturize very dry skin.",
        "This balm cures eczema and is clinically proven to cure acne. A great acne treatment!",
        "This serum heals acne, is antibacterial, and treats psoriasis.",
        "We don't make medical or therapeutic claims about treating eczema.",
    ]
    print("=" * 74)
    print("  CLAIMS GUARDRAIL DEMO  -  cosmetics may not make medical/therapeutic claims")
    print("=" * 74)
    for s in samples:
        r = check_claims(s)
        if r["status"] == "ok":
            print(f"\n[ OK ] {s}")
        else:
            print(f"\n[FLAG] {s}")
            print(f"       forbidden : {', '.join(r['issues'])}")
            print(f"       rewritten : {r['rewritten']}")
    print("\n" + "=" * 74)

    # self-tests (fail loudly if the guardrail logic regresses)
    assert check_claims(samples[0])["status"] == "ok"
    bad = check_claims(samples[1])
    assert bad["status"] == "flagged" and "cure" not in bad["rewritten"].lower()
    bad2 = check_claims(samples[2])
    assert bad2["status"] == "flagged" and not any(w in bad2["rewritten"].lower() for w in ("antibacterial", "psoriasis"))
    meta = check_claims(samples[3])
    assert "medical or therapeutic claims" in meta["rewritten"]  # meta-statement stays intact
    print("  [OK] guardrail self-tests passed")
