"""Phase A: null-agent DB baseline, #499 gold-replay audit, #514 order-sensitivity."""
import pathlib as _pl
_REPO = _pl.Path(__file__).resolve().parents[2]
_OUT = _REPO / "results" / "phase_a"; _OUT.mkdir(parents=True, exist_ok=True)
_STR_OUT = str(_OUT)
import json, collections, contextlib, io, sys
from loguru import logger
logger.remove()  # silence warnings; we capture exceptions ourselves

from tau2.domains.retail.environment import get_environment, get_tasks

tasks = get_tasks("base")
print(f"tasks: {len(tasks)}")

results = []
for task in tasks:
    ec = task.evaluation_criteria
    init_data = task.initial_state.initialization_data if task.initial_state else None
    init_acts = task.initial_state.initialization_actions if task.initial_state else None
    hist = task.initial_state.message_history if (task.initial_state and task.initial_state.message_history) else []

    # --- GOLD env: replay golden actions, capturing exceptions (#499) ---
    gold = get_environment()
    gold.set_state(initialization_data=init_data, initialization_actions=init_acts,
                   message_history=hist, strict=True)
    errs = []
    for a in (ec.actions or []):
        try:
            gold.make_tool_call(tool_name=a.name, requestor=a.requestor, **a.arguments)
        except Exception as e:
            errs.append({"action": a.name, "err": f"{type(e).__name__}: {e}"[:160]})
    gold_hash = gold.get_db_hash()

    # --- NULL agent: same init, but NO agent actions at all ---
    null = get_environment()
    null.set_state(initialization_data=init_data, initialization_actions=init_acts,
                   message_history=[], strict=True)
    null_hash = null.get_db_hash()

    results.append(dict(
        id=task.id,
        n_gold_actions=len(ec.actions or []),
        replay_errors=errs,
        gold_hash=gold_hash,
        null_hash=null_hash,
        null_passes_db=(gold_hash == null_hash),
        basis=[str(b) for b in (ec.reward_basis or [])],
        n_nl=len(ec.nl_assertions or []),
    ))

# ---------- report ----------
err_tasks = [r for r in results if r["replay_errors"]]
null_pass = [r for r in results if r["null_passes_db"]]

print("\n=== #499: gold-replay exceptions (silently swallowed upstream) ===")
print(f"tasks with >=1 failing golden action : {len(err_tasks)} / {len(results)}")
print(f"total failing golden actions         : {sum(len(r['replay_errors']) for r in err_tasks)}")
print(f"affected task IDs: {sorted(r['id'] for r in err_tasks)}")
kinds = collections.Counter(e["err"].split(':')[0] for r in err_tasks for e in r["replay_errors"])
print(f"exception kinds: {dict(kinds)}")
print("\nsample failures:")
for r in err_tasks[:6]:
    for e in r["replay_errors"][:1]:
        print(f"  task {r['id']:>4}  {e['action']:<32} {e['err'][:90]}")

print("\n=== NULL-AGENT DB BASELINE (does-nothing agent) ===")
print(f"tasks where a DO-NOTHING agent matches the gold DB hash: {len(null_pass)} / {len(results)}  ({len(null_pass)/len(results):.0%})")
print(f"  of those, effectively DB-only (no live NL judge): "
      f"{sum(1 for r in null_pass if not (r['n_nl']>0 and 'NL_ASSERTION' in str(r['basis'])))}")
print(f"  null-passing task IDs: {sorted(r['id'] for r in null_pass)}")

overlap = [r for r in null_pass if r["replay_errors"]]
print(f"\n  !! null-passes AND had replay errors (spurious DB=1 from #499): {len(overlap)} -> {sorted(r['id'] for r in overlap)}")

json.dump(results, open(_STR_OUT + "/phase_a3.json","w"), indent=1)
print("\nwrote phase_a3.json")
