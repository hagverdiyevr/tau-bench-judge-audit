"""STEP 2b — how much do reasoning tokens actually cost us, and can we control them?

COST: ~USD 0.01. A handful of calls on a realistic-length prompt.

Why: step2 showed a TRIVIAL prompt burned 189 reasoning tokens to emit 1 visible token.
Reasoning bills at the OUTPUT rate. Our Phase C estimate assumed ~550 output tokens/call.
If a real retail turn burns far more, the generation budget is wrong by a large factor.
Measure before committing money.

Run:  cd vendor/tau2-bench && uv run --frozen python ../../scripts/phase_b/step2b_thinking_cost.py
"""

import json
import os
import pathlib as _pl

from dotenv import load_dotenv
from loguru import logger

logger.remove()

_REPO = _pl.Path(__file__).resolve().parents[2]
_OUT = _REPO / "results" / "phase_b"
_OUT.mkdir(parents=True, exist_ok=True)
load_dotenv(_REPO / ".env")

from litellm import completion

# Real retail policy — the actual system prompt the agent gets. Realistic input size.
POLICY = (_REPO / "vendor/tau2-bench/data/tau2/domains/retail/policy.md").read_text()

PROMPT = (
    "You are a retail customer service agent. Follow this policy:\n\n"
    + POLICY
    + "\n\nCustomer: Hi, I'd like to cancel order #W0000042 because I ordered the wrong size.\n"
    "What is your next step? Answer in one short sentence."
)

PRICES = {  # USD per 1M, from docs/REFERENCE.md
    "gemini/gemini-3.1-flash-lite": {"in": 0.25, "out": 1.50},
    "gemini/gemini-2.5-flash-lite": {"in": 0.10, "out": 0.40},
}

# (label, model, extra kwargs) — probe whether thinking is controllable
TRIALS = [
    ("3.1-flash-lite default", "gemini/gemini-3.1-flash-lite", {}),
    ("3.1-flash-lite effort=low", "gemini/gemini-3.1-flash-lite", {"reasoning_effort": "low"}),
    ("3.1-flash-lite effort=none", "gemini/gemini-3.1-flash-lite", {"reasoning_effort": "none"}),
    ("2.5-flash-lite default", "gemini/gemini-2.5-flash-lite", {}),
]

print("=" * 78)
print("STEP 2b — reasoning-token cost probe on a REALISTIC retail prompt")
print(f"  prompt is the real retail policy + a customer turn (~{len(PROMPT)//4} tokens)")
print("=" * 78)

rows = []
for label, model, extra in TRIALS:
    try:
        r = completion(
            model=model,
            messages=[{"role": "user", "content": PROMPT}],
            max_tokens=2000,
            temperature=0.0,
            **extra,
        )
    except Exception as e:
        print(f"\n  {label:<28} ERROR: {type(e).__name__}: {str(e)[:110]}")
        rows.append({"label": label, "model": model, "error": str(e)[:200]})
        continue

    u = r.usage
    pt = getattr(u, "prompt_tokens", 0) or 0
    ct = getattr(u, "completion_tokens", 0) or 0
    d = getattr(u, "completion_tokens_details", None)
    rt = (getattr(d, "reasoning_tokens", None) if d else None) or 0
    visible = ct - rt
    cost = r._hidden_params.get("response_cost") or 0.0
    p = PRICES[model]
    think_cost = rt / 1e6 * p["out"]

    rows.append(
        dict(
            label=label, model=model, prompt_tokens=pt, completion_tokens=ct,
            reasoning_tokens=rt, visible_tokens=visible, cost=cost,
            thinking_cost=think_cost,
            thinking_share_of_output=(rt / ct if ct else 0),
            thinking_share_of_cost=(think_cost / cost if cost else 0),
        )
    )
    print(f"\n  {label}")
    print(f"    in={pt:<6} out={ct:<5} (reasoning={rt:<5} visible={visible:<4})")
    print(f"    cost=${cost:.6f}   thinking={think_cost/cost*100 if cost else 0:.0f}% of it")

ok_rows = [r for r in rows if "error" not in r]

print("\n" + "=" * 78)
print("  PER-CALL COST, and what it implies for a 30-call trajectory")
print("=" * 78)
print(f"  {'config':<28} {'$/call':>10} {'$/traj(30)':>12} {'think% cost':>12}")
for r in ok_rows:
    print(
        f"  {r['label']:<28} {r['cost']:>10.6f} {r['cost']*30:>12.4f} "
        f"{r['thinking_share_of_cost']*100:>11.0f}%"
    )

print("\n  NOTE: a real trajectory's input GROWS each turn (history + tool results),")
print("  so $/traj above is a LOWER BOUND on the agent side. Step 4 measures the truth.")

if ok_rows:
    base = next((r for r in ok_rows if r["label"].startswith("3.1-flash-lite default")), None)
    best = min(ok_rows, key=lambda r: r["cost"])
    if base and best["label"] != base["label"]:
        print(
            f"\n  CHEAPEST: {best['label']} at ${best['cost']:.6f}/call "
            f"= {base['cost']/best['cost']:.1f}x cheaper than the planned arm."
        )
        print("  If it clears the Step-4 floor gate, switching saves most of the Phase C budget.")

json.dump(rows, open(_OUT / "step2b_thinking.json", "w"), indent=1)
print(f"\nwrote {_OUT / 'step2b_thinking.json'}")
