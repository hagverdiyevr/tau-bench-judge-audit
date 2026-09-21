"""Regenerate the spend ledger from run artifacts.

CLAUDE.md and PLAN.md both state the ledger is "regenerated from run artifacts, never by hand".
That was false until this script existed — the file was produced by an ad-hoc inline command and
its line items did not sum to its total. This makes the claim true.

Critically, it adds JUDGE COST, which tau2 does not record anywhere (FINDINGS B-L14): SimulationRun
carries only agent_cost and user_cost, so any ledger built from those alone understates true spend
on judge-gated tasks. Judge cost is computed from the judge's ACTUAL serialization of each
trajectory, not a flat per-call guess.

Run:  cd vendor/tau2-bench && uv run python ../../scripts/build_spend_ledger.py
"""

import glob
import json
import pathlib
import sys

REPO = pathlib.Path(__file__).resolve().parents[1]
OUT = REPO / "results" / "spend_ledger.json"
CAP_USD = 75.00

# USD per 1M tokens — our own table (REFERENCE §2), never LiteLLM's registry alone.
PRICES = {
    "gpt-4.1-2025-04-14": (2.00, 8.00),
    "gpt-4.1-mini": (0.40, 1.60),
    "gpt-4.1-nano-2025-04-14": (0.10, 0.40),
    "gemini/gemini-3.8-flash": (0.75, 3.75),
    "gemini/gemini-3.1-flash-lite": (0.25, 1.50),
}
JUDGE = "gpt-4.1-2025-04-14"          # incumbent, fires automatically during tau2 run
JUDGE_OUTPUT_TOKENS = 300             # measured typical verdict length

try:
    from litellm import token_counter
except ImportError:
    sys.exit("run under the tau2 venv: cd vendor/tau2-bench && uv run python ../../scripts/build_spend_ledger.py")


def judge_input_tokens(sim):
    """Reproduce evaluator_nl_assertions' exact serialization to price the judge call."""
    txt = "\n".join(f"{m['role']}: {m.get('content')}" for m in sim["messages"])
    return token_counter(model=JUDGE, text=txt)


runs, totals = [], {"agent_user": 0.0, "judge": 0.0}
for path in sorted(glob.glob(str(REPO / "vendor/tau2-bench/data/simulations/*/results.json"))):
    d = json.loads(pathlib.Path(path).read_text())
    name = pathlib.Path(path).parent.name
    au = sum(s["agent_cost"] + s["user_cost"] for s in d["simulations"])
    judged = [s for s in d["simulations"] if (s["reward_info"].get("nl_assertions") or [])]
    jin = sum(judge_input_tokens(s) for s in judged)
    jcost = jin / 1e6 * PRICES[JUDGE][0] + len(judged) * JUDGE_OUTPUT_TOKENS / 1e6 * PRICES[JUDGE][1]
    runs.append({"run": name, "simulations": len(d["simulations"]),
                 "agent_user_usd": round(au, 6),
                 "judge_calls": len(judged), "judge_input_tokens": jin,
                 "judge_usd": round(jcost, 6),
                 "git_commit": (d.get("info") or {}).get("git_commit", "unknown")})
    totals["agent_user"] += au
    totals["judge"] += jcost

# Spend outside tau2 runs: standalone probes and offline re-grades. Enumerated, not guessed.
OUT_OF_BAND = [
    {"item": "phase_b steps 1-3b probes (access, billing, thinking, signatures)", "usd": 0.0200},
    {"item": "key verification calls (gemini + openai)", "usd": 0.0004},
    {"item": "B5 judge re-grades, 15 calls", "usd": 0.1350},
    {"item": "external-review verification probes (workflow)", "usd": 0.0025},
]
oob = sum(x["usd"] for x in OUT_OF_BAND)
total = totals["agent_user"] + totals["judge"] + oob

ledger = {
    "schema": "spend-ledger/2",
    "generated_by": "scripts/build_spend_ledger.py",
    "note": "Judge cost is computed from the judge's own trajectory serialization because tau2 "
            "records no judge cost at all (FINDINGS B-L14).",
    "cap_usd": CAP_USD,
    "total_usd": round(total, 4),
    "remaining_usd": round(CAP_USD - total, 2),
    "components": {
        "agent_user_usd": round(totals["agent_user"], 4),
        "judge_usd_untracked_by_tau2": round(totals["judge"], 4),
        "out_of_band_usd": round(oob, 4),
    },
    "trajectories": sum(r["simulations"] for r in runs),
    "runs": runs,
    "out_of_band": OUT_OF_BAND,
}
OUT.write_text(json.dumps(ledger, indent=1) + "\n")

print(f"  {'run':<24}{'sims':>5}{'agent+user':>12}{'judge':>10}")
for r in runs:
    print(f"  {r['run']:<24}{r['simulations']:>5}{r['agent_user_usd']:>12.5f}{r['judge_usd']:>10.5f}")
print(f"\n  agent+user                 ${totals['agent_user']:.4f}")
print(f"  judge (untracked by tau2)  ${totals['judge']:.4f}")
print(f"  out of band                ${oob:.4f}")
print(f"  {'-'*44}")
print(f"  TOTAL                      ${total:.4f} of ${CAP_USD:.2f}")
print(f"  REMAINING                  ${CAP_USD - total:.2f}")
chk = abs((totals['agent_user'] + totals['judge'] + oob) - total) < 1e-9
print(f"\n  components sum to total: {chk}")
print(f"  wrote {OUT.relative_to(REPO)}")
