"""STEP 2 — one minimal live call. Proves billing works AND that cost accounting is trustworthy.

COST: ~USD 0.00002 (a few dozen tokens). This is the smallest possible real call.

Why this step exists: tau2's get_response_cost() swallows exceptions and returns 0.0, so an
unpriced model silently reports as FREE. If we trusted that, the budget ledger would lie and we
would discover it only from a surprise invoice. This verifies the number is real before anything
else depends on it.

Run:  cd vendor/tau2-bench && uv run --frozen python ../../scripts/phase_b/step2_verify_billing.py
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

if not os.environ.get("GEMINI_API_KEY", "").strip():
    raise SystemExit("No GEMINI_API_KEY. Run step1 first.")

import litellm
from litellm import completion

from tau2.utils.llm_utils import get_response_cost, get_response_usage

MODEL = "gemini/gemini-3.1-flash-lite"
# Our own pricing table (docs/REFERENCE.md), USD per 1M tokens. Never trust LiteLLM's alone.
OUR_PRICE = {"input": 0.25, "output": 1.50}

print("=" * 72)
print(f"STEP 2 — live billing + cost-accounting check   ({MODEL})")
print("=" * 72)

resp = completion(
    model=MODEL,
    messages=[{"role": "user", "content": "Reply with exactly one word: ok"}],
    max_tokens=200,  # must exceed the thinking budget or content comes back empty
    temperature=0.0,
)

content = (resp.choices[0].message.content or "").strip()
returned_model = resp.model
usage = resp.usage

print(f"\n  call succeeded. reply: {content!r}")
print(f"  requested model : {MODEL}")
print(f"  returned model  : {returned_model}")

prompt_t = getattr(usage, "prompt_tokens", None)
completion_t = getattr(usage, "completion_tokens", None)
details = getattr(usage, "completion_tokens_details", None)
reasoning_t = getattr(details, "reasoning_tokens", None) if details else None

print("\n--- usage ---")
print(f"  prompt_tokens     : {prompt_t}")
print(f"  completion_tokens : {completion_t}")
print(f"  reasoning_tokens  : {reasoning_t}   (None => provider omitted the split)")

# Three independent cost numbers; they must agree.
litellm_cost = resp._hidden_params.get("response_cost")
tau2_cost = get_response_cost(resp)
tau2_usage = get_response_usage(resp)
ours = (
    (prompt_t or 0) / 1e6 * OUR_PRICE["input"] + (completion_t or 0) / 1e6 * OUR_PRICE["output"]
)

print("\n--- cost, three ways (must agree) ---")
print(f"  litellm response_cost   : {litellm_cost}")
print(f"  tau2 get_response_cost  : {tau2_cost}")
print(f"  our own price table     : {ours:.10f}")

checks = {
    "call returned content": bool(content),
    "returned model matches request": MODEL.split("/")[-1] in str(returned_model),
    "usage present and non-zero": bool(prompt_t) and prompt_t > 0,
    "litellm cost is not None": litellm_cost is not None,
    "litellm cost > 0 (NOT the silent-zero bug)": bool(litellm_cost and litellm_cost > 0),
    "tau2 cost > 0 (NOT the silent-zero bug)": bool(tau2_cost and tau2_cost > 0),
    "tau2 usage dict populated": bool(tau2_usage),
}
# agreement within 1% or 1e-9 absolute, whichever is looser
if litellm_cost:
    checks["our table agrees with litellm (<1%)"] = abs(ours - litellm_cost) <= max(
        1e-9, 0.01 * litellm_cost
    )

print("\n--- verdict ---")
for k, v in checks.items():
    print(f"  {'PASS' if v else 'FAIL'}  {k}")

ok = all(checks.values())
print("\n" + "=" * 72)
if ok:
    print("  STEP 2 PASS — billing is live and cost accounting is trustworthy.")
    print(f"  This call cost approximately USD {litellm_cost:.8f}")
    print("  Next: step3 thought-signature preflight (~USD 0.01) — REQUIRED before any")
    print("        multi-turn tool-calling run, per litellm#25322.")
else:
    print("  STEP 2 FAIL — do NOT proceed. Cost accounting cannot be trusted,")
    print("  and the USD 75 ledger would be built on a number that is wrong.")
print("=" * 72)

json.dump(
    {
        "model_requested": MODEL,
        "model_returned": str(returned_model),
        "prompt_tokens": prompt_t,
        "completion_tokens": completion_t,
        "reasoning_tokens": reasoning_t,
        "litellm_cost": litellm_cost,
        "tau2_cost": tau2_cost,
        "our_cost": ours,
        "checks": checks,
        "pass": ok,
    },
    open(_OUT / "step2_billing.json", "w"),
    indent=1,
)
print(f"\nwrote {_OUT / 'step2_billing.json'}")
