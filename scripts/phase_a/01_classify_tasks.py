import pathlib as _pl
_REPO = _pl.Path(__file__).resolve().parents[2]
_OUT = _REPO / "results" / "phase_a"; _OUT.mkdir(parents=True, exist_ok=True)
_STR_OUT = str(_OUT)
import json, collections, pathlib

ROOT = _REPO / "vendor" / "tau2-bench"
tasks = json.loads((ROOT/"data/tau2/domains/retail/tasks.json").read_text())
split = json.loads((ROOT/"data/tau2/domains/retail/split_tasks.json").read_text())

WRITE = {"cancel_pending_order","exchange_delivered_order_items","modify_pending_order_address",
         "modify_pending_order_items","modify_pending_order_payment","modify_user_address",
         "return_delivered_order_items"}

print(f"tasks.json objects: {len(tasks)}")
print(f"split keys: { {k: len(v) for k,v in split.items()} }")
print(f"top-level task keys seen: {sorted({k for t in tasks for k in t})}")

rows=[]
for t in tasks:
    ec = t.get("evaluation_criteria") or {}
    actions = ec.get("actions") or []
    names = [a.get("name") for a in actions]
    ci = ec.get("communicate_info") or []
    rb = ec.get("reward_basis")
    rows.append(dict(id=str(t.get("id")), mutating=any(n in WRITE for n in names),
                     n_actions=len(actions), n_ci=len(ci), reward_basis=tuple(rb) if rb else None,
                     nl=len(ec.get("nl_assertions") or []), env=len(ec.get("env_assertions") or []),
                     action_names=names))

mut  = [r for r in rows if r["mutating"]]
ci   = [r for r in rows if r["n_ci"]>0]
both = [r for r in rows if r["mutating"] and r["n_ci"]>0]
neither=[r for r in rows if not r["mutating"] and r["n_ci"]==0]

print("\n=== PHASE A STOP-GATE ===")
print(f"total tasks                       : {len(rows)}")
print(f"mutating (>=1 WRITE gold action)  : {len(mut)}  ({len(mut)/len(rows):.0%})")
print(f"non-empty communicate_info        : {len(ci)}  ({len(ci)/len(rows):.0%})")
print(f"BOTH non-trivial (the subset)     : {len(both)}  ({len(both)/len(rows):.0%})   <-- gate: need >=25")
print(f"NEITHER (DB=1 and COMM=1 free)    : {len(neither)}")
print(f"read-only (DB vacuous -> null agent scores 1): {len(rows)-len(mut)}")

print(f"\nreward_basis values: {collections.Counter(r['reward_basis'] for r in rows)}")
print(f"tasks with nl_assertions: {sum(1 for r in rows if r['nl'])}, env_assertions: {sum(1 for r in rows if r['env'])}")
print(f"tasks with ZERO gold actions: {sum(1 for r in rows if r['n_actions']==0)}")

both_ids={r["id"] for r in both}
for name, ids in split.items():
    ids={str(i) for i in ids}
    print(f"split {name:6s}: n={len(ids):3d}  both-non-trivial within = {len(ids & both_ids)}")

json.dump(rows, open(_STR_OUT + "/task_class.json","w"), indent=1)
