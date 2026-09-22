"""Judge pricing, and the one rule that governs it: unknown cost is never zero.

LiteLLM's get_response_cost() returns 0.0 on exception, so a model it cannot price reports as
FREE. Against a hard USD 75 cap that is the most dangerous possible default, and CLAUDE.md names
it as a known defect. Everything here exists to make an unpriced call loud instead of free.

Separated from the runner so it is importable by tests without executing a run.
"""

# USD per 1M tokens (input, output) — REFERENCE §2.
PRICES = {
    "gpt-4.1-2025-04-14": (2.00, 8.00),
    "gpt-4.1-mini": (0.40, 1.60),
    "gemini/gemini-3.8-flash": (0.75, 3.75),
    "gemini/gemini-3.1-flash-lite": (0.25, 1.50),
}


def price(model: str, prompt_tokens, completion_tokens):
    """Compute cost from the table. Returns None when it cannot — NEVER 0.0.

    None means "unknown, go and find out". 0.0 means "this was free", which for an unpriced
    model is a claim we have no evidence for and which silently corrupts the ledger.
    """
    table = PRICES.get(model)
    if table is None or prompt_tokens is None or completion_tokens is None:
        return None
    return prompt_tokens / 1e6 * table[0] + completion_tokens / 1e6 * table[1]


def resolve_cost(model, reported, prompt_tokens, completion_tokens):
    """Pick the trustworthy cost for one call, and say where it came from.

    `reported` is LiteLLM's response_cost. A falsy value (None, or the 0.0 it substitutes on
    failure) is not accepted at face value: the table is consulted instead, and if the table has
    no entry the result is None so the caller must surface it.
    """
    if reported:
        return float(reported), "litellm"
    fallback = price(model, prompt_tokens, completion_tokens)
    return fallback, ("price_table" if fallback is not None else "UNKNOWN")
