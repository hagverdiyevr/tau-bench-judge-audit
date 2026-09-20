import pathlib as _pl
_REPO = _pl.Path(__file__).resolve().parents[2]
_OUT = _REPO / "results" / "phase_a"; _OUT.mkdir(parents=True, exist_ok=True)
_STR_OUT = str(_OUT)
import json
from loguru import logger; logger.remove()
from tau2.domains.retail.environment import get_tasks

WRITE = {"cancel_pending_order","exchange_delivered_order_items","modify_pending_order_address",
         "modify_pending_order_items","modify_pending_order_payment","modify_user_address",
         "return_delivered_order_items"}
res = {r["id"]: r for r in json.load(open(_STR_OUT + "/phase_a3.json"))}
tasks = {t.id: t for t in get_tasks("base")}

print("=== Are the 18 swallowed failures hash-corrupting (WRITE) or benign (READ)? ===")
w=r_=0
for tid, rec in res.items():
    for e in rec["replay_errors"]:
        if e["action"] in WRITE: w+=1; print(f"  !! WRITE failure  task {tid}: {e['action']} -> {e['err'][:70]}")
        else: r_+=1
print(f"  WRITE (corrupts gold hash): {w}   READ/GENERIC (hash unaffected, but signals stale task data): {r_}")

print("\n=== The 3 spurious-pass tasks: does anything else gate them? ===")
for tid in ["67","68","105"]:
    t=tasks[tid]; ec=t.evaluation_criteria; rec=res[tid]
    nl=len(ec.nl_assertions or [])
    print(f"\n  task {tid}: basis={[str(b) for b in ec.reward_basis]} nl_assertions={nl} gold_actions={rec['n_gold_actions']}")
    print(f"    failing: {[e['action'] for e in rec['replay_errors']]}")
    print(f"    gold action names: {[a.name for a in (ec.actions or [])]}")
    verdict = "DB=1 AND no live judge -> NULL AGENT SCORES FULL REWARD" if nl==0 else f"DB=1 but {nl} NL assertion(s) still gate it"
    print(f"    => {verdict}")

print("\n=== #514: is get_dict_hash order-sensitive on lists? ===")
from tau2.utils.utils import get_dict_hash
a={"payment_history":[{"x":1},{"y":2}]}; b={"payment_history":[{"y":2},{"x":1}]}
print(f"  hash([A,B]) == hash([B,A]) ? {get_dict_hash(a)==get_dict_hash(b)}")
print(f"    -> {'NOT order-sensitive' if get_dict_hash(a)==get_dict_hash(b) else 'ORDER-SENSITIVE: #514 confirmed (equivalent orderings hash differently)'}")
