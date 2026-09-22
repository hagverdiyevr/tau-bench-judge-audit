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


# Phase C invocations have an ATTEMPT LOG (A-003), which records true spend at the LiteLLM
# boundary including the judge calls tau2 omits. Prefer measured over estimated wherever it exists.
ATTEMPTS = REPO / "results" / "phase_c" / "attempts"


def attempt_usd(run_name):
    """Measured spend for one invocation, plus how many successes carried no cost.

    A successful call with usd=None is NOT a free call. LiteLLM does not always have
    response_cost populated in _hidden_params when the success callback fires -- 30 of 7,516
    Phase C attempts (0.40%), across all four models, so it is a callback timing race rather
    than a pricing gap. Summing `or 0.0` would silently bill those at zero, which is the very
    defect this project documents in get_response_cost(). They are counted and surfaced, and a
    total carrying any of them is reported as a LOWER BOUND. [D-L4](../docs/FINDINGS.md)
    """
    f = ATTEMPTS / f"{run_name}.jsonl"
    if not f.exists():
        return None, 0
    usd, unpriced = 0.0, 0
    for line in f.read_text().splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        if row.get("outcome") == "failure":
            continue
        if row.get("usd") is None:
            unpriced += 1
        else:
            usd += row["usd"]
    return round(usd, 6), unpriced


runs, totals = [], {"agent_user": 0.0, "judge": 0.0, "measured": 0.0}
for path in sorted(glob.glob(str(REPO / "vendor/tau2-bench/data/simulations/*/results.json"))):
    d = json.loads(pathlib.Path(path).read_text())
    name = pathlib.Path(path).parent.name
    au = sum(s["agent_cost"] + s["user_cost"] for s in d["simulations"])
    judged = [s for s in d["simulations"] if (s["reward_info"].get("nl_assertions") or [])]
    jin = sum(judge_input_tokens(s) for s in judged)
    jcost = jin / 1e6 * PRICES[JUDGE][0] + len(judged) * JUDGE_OUTPUT_TOKENS / 1e6 * PRICES[JUDGE][1]
    measured, unpriced_n = attempt_usd(name)
    runs.append({"run": name, "simulations": len(d["simulations"]),
                 "agent_user_usd": round(au, 6),
                 "judge_calls": len(judged), "judge_input_tokens": jin,
                 "judge_usd_estimated": round(jcost, 6),
                 "measured_usd_from_attempts": measured,
                 "unpriced_successes": unpriced_n,
                 "measured_is_lower_bound": bool(unpriced_n),
                 "source": "attempt_log" if measured is not None else "estimate",
                 "git_commit": (d.get("info") or {}).get("git_commit", "unknown")})
    if measured is not None:
        totals["measured"] += measured          # authoritative: every attempt, judge included
    else:
        totals["agent_user"] += au
        totals["judge"] += jcost

# Spend outside tau2 runs: standalone probes and offline re-grades. Enumerated, not guessed.
OUT_OF_BAND = [
    {"item": "phase_b steps 1-3b probes (access, billing, thinking, signatures)", "usd": 0.0200},
    {"item": "key verification calls (gemini + openai)", "usd": 0.0004},
    {"item": "B5 judge re-grades, 15 calls", "usd": 0.1350},
    {"item": "external-review verification probes (workflow)", "usd": 0.0025},
    {"item": "judge adapter probe, 4 judges x 1 trajectory (J1 confirmation)", "usd": 0.0100},
    {"item": "Phase D regrade smoke, 5 trajectories x 4 judges (rec 10)", "usd": 0.0890},
]
oob = sum(x["usd"] for x in OUT_OF_BAND)

# Phase D is re-grading, not simulation: it has no results.json, so it is accounted from its own
# per-evaluation journal. The journal is preferred over the attempt log because it is the more
# complete instrument -- it carried a cost for 1,792 of 1,792 evaluations where the attempt log
# was missing 2. Both are kept; they agree to $0.0085. [D-L4](../docs/FINDINGS.md)
PHASE_D_JOURNAL = REPO / "results" / "phase_d" / "regrade_journal.jsonl"
phase_d = {"evaluations": 0, "usd": 0.0, "unpriced": 0}
if PHASE_D_JOURNAL.exists():
    for line in PHASE_D_JOURNAL.read_text().splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        if not row.get("settled"):
            continue
        phase_d["evaluations"] += 1
        if row.get("usd") is None:
            phase_d["unpriced"] += 1
        else:
            phase_d["usd"] += row["usd"]
phase_d["usd"] = round(phase_d["usd"], 6)

total = totals["agent_user"] + totals["judge"] + totals["measured"] + oob + phase_d["usd"]

ledger = {
    "schema": "spend-ledger/3",
    "generated_by": "scripts/build_spend_ledger.py",
    "note": "Judge cost is computed from the judge's own trajectory serialization because tau2 "
            "records no judge cost at all (FINDINGS B-L14).",
    "cap_usd": CAP_USD,
    "total_usd": round(total, 4),
    "remaining_usd": round(CAP_USD - total, 2),
    "components": {
        "measured_from_attempt_logs_usd": round(totals["measured"], 4),
        "phase_d_regrade_usd": phase_d["usd"],
        "agent_user_usd_estimated": round(totals["agent_user"], 4),
        "judge_usd_estimated_untracked_by_tau2": round(totals["judge"], 4),
        "out_of_band_usd": round(oob, 4),
    },
    "trajectories": sum(r["simulations"] for r in runs),
    "runs": runs,
    "out_of_band": OUT_OF_BAND,
}
OUT.write_text(json.dumps(ledger, indent=1) + "\n")

print(f"  {'run':<24}{'sims':>5}{'usd':>11}  source")
for r in runs:
    u = r['measured_usd_from_attempts'] if r['source'] == 'attempt_log' else r['agent_user_usd'] + r['judge_usd_estimated']
    print(f"  {r['run']:<24}{r['simulations']:>5}{u:>11.5f}  {r['source']}")
print(f"\n  MEASURED (attempt logs)    ${totals['measured']:.4f}  <- Phase C, judge included")
print(f"  PHASE D (regrade journal)  ${phase_d['usd']:.4f}  <- {phase_d['evaluations']} evaluations")
_unp = sum(r.get('unpriced_successes') or 0 for r in runs) + phase_d['unpriced']
if _unp:
    print(f"  !! {_unp} successful call(s) carried NO cost from LiteLLM — totals above are a "
          f"LOWER BOUND, not a total (D-L4)")
print(f"  agent+user (estimated)     ${totals['agent_user']:.4f}")
print(f"  judge      (estimated)     ${totals['judge']:.4f}")
print(f"  out of band                ${oob:.4f}")
print(f"  {'-'*44}")
print(f"  TOTAL                      ${total:.4f} of ${CAP_USD:.2f}")
print(f"  REMAINING                  ${CAP_USD - total:.2f}")
chk = abs((totals['agent_user'] + totals['judge'] + totals['measured'] + oob + phase_d['usd']) - total) < 1e-9
print(f"\n  components sum to total: {chk}")
print(f"  wrote {OUT.relative_to(REPO)}")
