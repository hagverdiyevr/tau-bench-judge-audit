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
R=[]
for t in tasks:
    ec=t.get("evaluation_criteria") or {}
    names=[a.get("name") for a in (ec.get("actions") or [])]
    R.append(dict(id=str(t["id"]), mut=any(n in WRITE for n in names),
                  nl=len(ec.get("nl_assertions") or []), ci=len(ec.get("communicate_info") or []),
                  basis=tuple(ec.get("reward_basis") or [])))

live_nl=[r for r in R if "NL_ASSERTION" in r["basis"] and r["nl"]>0]
dbonly_eff=[r for r in R if not ("NL_ASSERTION" in r["basis"] and r["nl"]>0)]
both=[r for r in R if r["mut"] and "NL_ASSERTION" in r["basis"] and r["nl"]>0]

print("=== ACTUAL reward composition, tau3 v1.0.1 retail ===")
print(f"reward_basis distribution : {collections.Counter(r['basis'] for r in R)}")
print(f"COMMUNICATE in any basis  : {sum(1 for r in R if 'COMMUNICATE' in r['basis'])} / {len(R)}")
print()
print(f"NL_ASSERTION in basis          : {sum(1 for r in R if 'NL_ASSERTION' in r['basis'])}")
print(f"  ...and nl_assertions present : {len(live_nl)}   <- judge actually gates these")
print(f"  ...but nl_assertions EMPTY   : {sum(1 for r in R if 'NL_ASSERTION' in r['basis'] and r['nl']==0)}   <- defaults to 1.0 => DB-only in practice")
print(f"EFFECTIVELY DB-ONLY tasks      : {len(dbonly_eff)} / {len(R)}  ({len(dbonly_eff)/len(R):.0%})")
print()
print("=== communicate_info: dead data? ===")
print(f"tasks with non-empty communicate_info : {sum(1 for r in R if r['ci']>0)}")
print(f"  ...of which ANY have COMMUNICATE in reward_basis: {sum(1 for r in R if r['ci']>0 and 'COMMUNICATE' in r['basis'])}")
print()
print("=== REVISED both-non-trivial gate (mutating AND live judge) ===")
print(f"mutating gold actions        : {sum(1 for r in R if r['mut'])}")
print(f"live NL judge                : {len(live_nl)}")
print(f"BOTH live                    : {len(both)}  <- revised subset")
bid={r['id'] for r in both}; lid={r['id'] for r in live_nl}
for k,v in split.items():
    s={str(i) for i in v}
    print(f"  split {k:6s} n={len(s):3d} | both-live={len(s&bid):3d} | live-judge={len(s&lid):3d}")
