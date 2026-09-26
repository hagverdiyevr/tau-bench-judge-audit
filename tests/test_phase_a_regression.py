"""Regression locks for every Phase A finding, plus the two order-sensitivity defects.

Purpose: these numbers are load-bearing for the whole study and are quoted across the docs.
If upstream drifts, or one of our own scripts changes behaviour, this fails loudly instead of
the docs silently becoming wrong. Each assertion cites the finding it pins.

Requires the tau2 venv (it replays the real environment):
  cd vendor/tau2-bench && uv run --frozen python ../../tests/test_phase_a_regression.py
"""

import json
import pathlib
import sys

REPO = pathlib.Path(__file__).resolve().parents[1]
FAIL = []


def check(name, cond, detail=""):
    print(f"  {'PASS' if cond else 'FAIL'}  {name}{'' if cond else ' — ' + detail}")
    if not cond:
        FAIL.append(name)


# ---------------------------------------------------------------- upstream pin
import subprocess  # noqa: E402

PINNED = "fc0055dc4e0a316c3f83133267fbd6faaa770992"
sha = subprocess.run(["git", "rev-parse", "HEAD"], cwd=REPO / "vendor/tau2-bench",
                     capture_output=True, text=True).stdout.strip()
print("--- upstream pin ---")
check("submodule is at the pinned v1.0.1 commit", sha == PINNED, f"got {sha[:12]}…")

# ---------------------------------------------------------------- A1 / A3
print("\n--- A1/A3: reward composition (what retail actually scores) ---")
WRITE = {"cancel_pending_order", "exchange_delivered_order_items", "modify_pending_order_address",
         "modify_pending_order_items", "modify_pending_order_payment", "modify_user_address",
         "return_delivered_order_items"}
tasks = json.loads((REPO / "vendor/tau2-bench/data/tau2/domains/retail/tasks.json").read_text())
split = json.loads((REPO / "vendor/tau2-bench/data/tau2/domains/retail/split_tasks.json").read_text())

bases, live, mutating, comm = {}, 0, 0, 0
for t in tasks:
    ec = t.get("evaluation_criteria") or {}
    b = tuple(ec.get("reward_basis") or [])
    bases[b] = bases.get(b, 0) + 1
    nl = len(ec.get("nl_assertions") or [])
    if "NL_ASSERTION" in b and nl > 0:
        live += 1
    if "COMMUNICATE" in b:
        comm += 1
    if any(a.get("name") in WRITE for a in (ec.get("actions") or [])):
        mutating += 1

check("114 retail tasks", len(tasks) == 114, str(len(tasks)))
check("112 tasks use [DB, NL_ASSERTION]", bases.get(("DB", "NL_ASSERTION")) == 112,
      str(bases.get(("DB", "NL_ASSERTION"))))
check("2 tasks use [DB] only", bases.get(("DB",)) == 2, str(bases.get(("DB",))))
check("COMMUNICATE is in ZERO reward bases (A1)", comm == 0, str(comm))
check("40 tasks have a LIVE judge (A3)", live == 40, str(live))
check("74 tasks are effectively DB-only (A3)", len(tasks) - live == 74, str(len(tasks) - live))
check("104 mutating tasks", mutating == 104, str(mutating))
check("splits are 74/40/114", [len(split["train"]), len(split["test"]), len(split["base"])] == [74, 40, 114],
      str([len(split[k]) for k in ("train", "test", "base")]))

# ---------------------------------------------------------------- A2: judge identity
print("\n--- A2: the judge is hardcoded ---")
from tau2.config import DEFAULT_LLM_NL_ASSERTIONS, DEFAULT_LLM_NL_ASSERTIONS_TEMPERATURE  # noqa: E402

check("judge is gpt-4.1-2025-04-14", DEFAULT_LLM_NL_ASSERTIONS == "gpt-4.1-2025-04-14",
      DEFAULT_LLM_NL_ASSERTIONS)
check("judge temperature is 0.0", DEFAULT_LLM_NL_ASSERTIONS_TEMPERATURE == 0.0,
      str(DEFAULT_LLM_NL_ASSERTIONS_TEMPERATURE))

# ---------------------------------------------------------------- B1: patch target
print("\n--- B1: judge patch target (and that tau2.config is a no-op) ---")
from unittest import mock  # noqa: E402

import tau2.config as cfg  # noqa: E402
from tau2.evaluator import evaluator_nl_assertions as ENA  # noqa: E402

check("name is bound in the evaluator module", hasattr(ENA, "DEFAULT_LLM_NL_ASSERTIONS"))
with mock.patch.object(cfg, "DEFAULT_LLM_NL_ASSERTIONS", "SHOULD/not-apply"):
    check("patching tau2.config does NOT change the evaluator's binding",
          ENA.DEFAULT_LLM_NL_ASSERTIONS == "gpt-4.1-2025-04-14", ENA.DEFAULT_LLM_NL_ASSERTIONS)

# ---------------------------------------------------------------- A6 / B-L7
print("\n--- A6 / B-L7: order sensitivity in BOTH scoring paths ---")
from tau2.utils.utils import get_dict_hash  # noqa: E402

check("#514: DB hash IS order-sensitive on lists (do not 'fix')",
      get_dict_hash({"payment_history": [{"a": 1}, {"b": 2}]})
      != get_dict_hash({"payment_history": [{"b": 2}, {"a": 1}]}))
gold = {"order_id": "#W1", "item_ids": ["1", "2"], "payment_method_id": "c1"}
same_set = {"order_id": "#W1", "item_ids": ["2", "1"], "payment_method_id": "c1"}
check("B-L7: identical-except-list-order args compare unequal",
      gold != same_set and set(gold["item_ids"]) == set(same_set["item_ids"]))

# ---------------------------------------------------------------- A4 / A5
print("\n--- A4/A5: gold replay + null agent (committed allowlists) ---")
from loguru import logger  # noqa: E402

logger.remove()
from tau2.domains.retail.environment import get_environment, get_tasks  # noqa: E402

A4_TASKS = {"2", "3", "4", "35", "37", "38", "39", "46", "47", "54", "55", "64", "67", "68", "105"}
A5_TASKS = {"10", "12", "24", "25", "50", "57", "62", "65", "67", "68", "105"}

replay_fail, null_pass, n_actions = set(), set(), 0
for task in get_tasks("base"):
    ec = task.evaluation_criteria
    idata = task.initial_state.initialization_data if task.initial_state else None
    iacts = task.initial_state.initialization_actions if task.initial_state else None
    hist = (task.initial_state.message_history
            if task.initial_state and task.initial_state.message_history else [])
    g = get_environment()
    g.set_state(initialization_data=idata, initialization_actions=iacts, message_history=hist, strict=True)
    for a in (ec.actions or []):
        try:
            g.make_tool_call(tool_name=a.name, requestor=a.requestor, **a.arguments)
        except Exception:
            replay_fail.add(task.id)
            n_actions += 1
    n = get_environment()
    n.set_state(initialization_data=idata, initialization_actions=iacts, message_history=[], strict=True)
    if g.get_db_hash() == n.get_db_hash():
        null_pass.add(task.id)

check("A4: exactly 18 failing golden actions", n_actions == 18, str(n_actions))
check("A4: across exactly the 15 committed task IDs", replay_fail == A4_TASKS,
      f"diff={sorted(replay_fail ^ A4_TASKS)}")
check("A5: null agent passes DB on exactly the 11 committed task IDs", null_pass == A5_TASKS,
      f"diff={sorted(null_pass ^ A5_TASKS)}")
check("A5: 3 tasks both null-pass AND had replay failures",
      len(null_pass & replay_fail) == 3, str(sorted(null_pass & replay_fail)))

print()
if FAIL:
    print(f"  {len(FAIL)} REGRESSION FAILURE(S): {FAIL}")
    print("  A finding the docs rely on has changed. Investigate before trusting any claim.")
    sys.exit(1)
print("  ALL PHASE A FINDINGS REPRODUCE — docs' load-bearing numbers are locked.")
sys.exit(0)
