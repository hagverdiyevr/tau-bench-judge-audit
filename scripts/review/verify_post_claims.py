"""Re-derive every correction from the post-release review (FINDINGS R-L1 .. R-L9). Offline, $0.

Written after three public replies showed that some of our published prose went further than the
repros behind it. Every number in the R-L entries comes from this file, so the corrections are held
to the same standard as the claims they correct (D-004: a finding without committed code is not a
finding).

OFFLINE BY CONSTRUCTION. The NL judge is patched to raise if it is ever called. That guard exists
because an earlier ad-hoc version of R-L2 ran tau2's full evaluator on a task that has an assertion
and made a live judge call (R-L12). Tasks that carry assertions are scored on the DB component only.

Run:  cd vendor/tau2-bench && .venv/bin/python ../../scripts/review/verify_post_claims.py
Out:  results/review/post_claims.json
"""

import collections
import copy
import glob
import json
import math
import pathlib
import statistics
import sys
from unittest import mock

REPO = pathlib.Path(__file__).resolve().parents[2]
VENDOR = REPO / "vendor" / "tau2-bench"
DOMAINS = VENDOR / "data" / "tau2" / "domains"
SIMS = VENDOR / "data" / "simulations"
OUT = REPO / "results" / "review" / "post_claims.json"

from loguru import logger  # noqa: E402

logger.remove()

from tau2.data_model.message import AssistantMessage, UserMessage  # noqa: E402
from tau2.data_model.simulation import SimulationRun  # noqa: E402
from tau2.domains.retail.environment import get_environment, get_tasks  # noqa: E402
from tau2.evaluator import evaluator_nl_assertions as ENA  # noqa: E402
from tau2.evaluator.evaluator import EvaluationType, evaluate_simulation  # noqa: E402


def _no_network(*_a, **_k):
    raise RuntimeError("OFFLINE GUARD: the NL judge was about to be called. This script must not spend.")


ENA.generate = _no_network

WRITE = {"cancel_pending_order", "exchange_delivered_order_items", "modify_pending_order_address",
         "modify_pending_order_items", "modify_pending_order_payment", "modify_user_address",
         "return_delivered_order_items"}
TASKS = {t.id: t for t in get_tasks("base")}
out = {}


def say(msg=""):
    print(msg)


def replay(task):
    """Replay a task's gold actions; report failures, writes and whether a null agent matches."""
    ini = task.initial_state
    kw = dict(initialization_data=ini.initialization_data if ini else None,
              initialization_actions=ini.initialization_actions if ini else None)
    gold = get_environment()
    gold.set_state(**kw, message_history=(ini.message_history if ini and ini.message_history else []),
                   strict=True)
    null = get_environment()
    null.set_state(**kw, message_history=[], strict=True)
    fails, writes = [], []
    for a in task.evaluation_criteria.actions or []:
        before = gold.get_db_hash()
        try:
            gold.make_tool_call(tool_name=a.name, requestor=a.requestor, **a.arguments)
        except Exception as e:  # recorded, not swallowed
            fails.append({"action_id": a.action_id, "name": a.name, "write": a.name in WRITE,
                          "error": str(e)[:80]})
        if a.name in WRITE:
            writes.append({"action_id": a.action_id, "name": a.name,
                           "changed_db": gold.get_db_hash() != before})
    return fails, writes, gold.get_db_hash() == null.get_db_hash()


# ---------------------------------------------------------------- R-L1: why the null agent passes
say("R-L1  why a null agent passes DB on 11 tasks")
null_pass = {}
for tid in ["10", "12", "24", "25", "50", "57", "62", "65", "67", "68", "105"]:
    fails, writes, matches = replay(TASKS[tid])
    landed = [w for w in writes if w["changed_db"]]
    cause = ("failed gold write" if writes and not landed and any(f["write"] for f in fails)
             else "gold makes no writes" if not writes else "other")
    null_pass[tid] = {"matches": matches, "gold_writes": len(writes), "failed": fails, "cause": cause}
    say(f"      {tid:>4}  writes={len(writes)}  failed={[f['name'] for f in fails] or '-'}  -> {cause}")
by_cause = collections.Counter(v["cause"] for v in null_pass.values())
out["R-L1"] = {"tasks": null_pass, "by_cause": dict(by_cause)}
say(f"      by cause: {dict(by_cause)}")

# ---------------------------------------------------------------- R-L2 / R-L3: tau2's own evaluator
say("\nR-L2/3  tau2's evaluator on a conversation where the agent does nothing")
tmpl = json.loads((SIMS / "phaseC_t1_gem" / "results.json").read_text())["simulations"][0]
empty_eval = {}
for tid in ["10", "12", "25", "50", "57", "65", "24", "62", "67", "68", "64", "105"]:
    s = copy.deepcopy(tmpl)
    s["task_id"] = tid
    s["messages"] = [
        UserMessage(role="user", content="Hi, I need help with my order.", turn_idx=0).model_dump(),
        AssistantMessage(role="assistant", content="Sorry, I can't help with that. Goodbye.",
                         turn_idx=1).model_dump()]
    task = TASKS[tid]
    has_nl = bool(task.evaluation_criteria.nl_assertions)
    etype = EvaluationType.ENV if has_nl else EvaluationType.ALL   # never reach the judge
    ri = evaluate_simulation(simulation=SimulationRun(**s), task=task, evaluation_type=etype,
                             solo_mode=False, domain="retail")
    bd = {getattr(k, "value", k): v for k, v in (ri.reward_breakdown or {}).items()}
    empty_eval[tid] = {"reward": ri.reward if not has_nl else None, "breakdown": bd,
                       "judge_gated": has_nl}
    note = "judge-gated: DB only, reward not free" if has_nl else f"FULL reward {ri.reward}"
    say(f"      {tid:>4}  DB={bd.get('DB')}  {note}")
split = json.loads((DOMAINS / "retail" / "split_tasks.json").read_text())
free = sorted((t for t, v in empty_eval.items() if v["reward"] == 1.0), key=int)
out["R-L2"] = {"evaluations": empty_eval, "full_reward_tasks": free,
               "full_reward_in_test_split": [t for t in free if t in {str(x) for x in split["test"]}]}
say(f"      full reward for doing nothing: {free}  (test split: {out['R-L2']['full_reward_in_test_split']})")

# shipped results: how many stored runs of 64 / 105 matched their half-applied targets
shipped = collections.defaultdict(collections.Counter)
for f in glob.glob(str(VENDOR / "data" / "tau2" / "results" / "**" / "*.json"), recursive=True):
    try:
        sims = json.loads(pathlib.Path(f).read_text(encoding="utf-8")).get("simulations") or []
    except Exception:
        continue
    for s in sims:
        t = str(s.get("task_id"))
        if t in ("64", "105") and "retail" in f.lower():
            ri = s.get("reward_info") or {}
            shipped[t]["sims"] += 1
            shipped[t]["db_match_true"] += (ri.get("db_check") or {}).get("db_match") is True
            shipped[t]["reward_1"] += ri.get("reward") == 1.0
f64, w64, _ = replay(TASKS["64"])
out["R-L3"] = {"task64_writes": w64, "task64_failed": f64, "shipped": {k: dict(v) for k, v in shipped.items()},
               "task105_action_ids": [a.action_id for a in TASKS["105"].evaluation_criteria.actions]}
say(f"      task 64 writes: {[(w['action_id'], w['changed_db']) for w in w64]}")
say(f"      shipped results: { {k: dict(v) for k, v in sorted(shipped.items())} }")

# ---------------------------------------------------------------- R-L4: judge cost, measured
say("\nR-L4  judge cost: measured Phase D vs the B-L14 estimate")
led = json.loads((REPO / "results" / "spend_ledger.json").read_text())
J = [json.loads(x) for x in (REPO / "results/phase_d/regrade_journal.jsonl").read_text().splitlines() if x.strip()]
inc = [r for r in J if r["judge"] == "gpt-4.1-2025-04-14" and r["replicate"] == 1]
rows, tot_au, tot_j = {}, 0.0, 0.0
for arm, tag in (("google", "gem"), ("openai", "oai")):
    au = sum(r["agent_user_usd"] for r in led["runs"] if r["run"].startswith("phaseC_") and r["run"].endswith(tag))
    j = sum(r["usd"] for r in inc if r["run"].endswith(tag))
    rows[arm] = {"agent_user_usd": round(au, 4), "judge_usd_measured": round(j, 4), "judge_share": round(j / (au + j), 4)}
    tot_au += au
    tot_j += j
est = sum(r["judge_usd_estimated"] for r in led["runs"] if r["run"].startswith("phaseC_"))
out["R-L4"] = {"by_arm": rows, "judge_usd_measured": round(tot_j, 4), "judge_usd_estimated": round(est, 4),
               "judge_share_measured": round(tot_j / (tot_au + tot_j), 4),
               "mean_completion_tokens": round(statistics.mean(r["completion_tokens"] for r in inc), 1),
               "agent_cost_ratio": round(rows["google"]["agent_user_usd"] / rows["openai"]["agent_user_usd"], 2)}
say(f"      measured ${tot_j:.4f} vs estimated ${est:.4f}; share {tot_j / (tot_au + tot_j):.1%}; "
    f"google {rows['google']['judge_share']:.1%} vs openai {rows['openai']['judge_share']:.1%}")

# ---------------------------------------------------------------- R-L5: where ACTION is scored
say("\nR-L5  ACTION scoring and compare_args: [] across every domain")
act = {}
for d in sorted(p for p in DOMAINS.iterdir() if (p / "tasks.json").exists()):
    tasks = json.loads((d / "tasks.json").read_text())
    ec = lambda t: t.get("evaluation_criteria") or {}  # noqa: E731
    empties = [(str(t["id"]), a["name"], sorted(a.get("arguments") or {}))
               for t in tasks for a in (ec(t).get("actions") or []) if a.get("compare_args") == []]
    act[d.name] = {"tasks": len(tasks),
                   "action_in_basis": sum(1 for t in tasks if "ACTION" in (ec(t).get("reward_basis") or [])),
                   "empty_compare_args": len(empties),
                   "empty_compare_args_names": dict(collections.Counter(n for _, n, _ in empties)),
                   "empty_compare_args_arg_keys": sorted({k for _, _, ks in empties for k in ks})}
    say(f"      {d.name:<18} ACTION scored on {act[d.name]['action_in_basis']:>3}/{len(tasks):<5} "
        f"compare_args=[]: {len(empties):>3} {act[d.name]['empty_compare_args_names']}")
out["R-L5"] = act

# ---------------------------------------------------------------- R-L6: malformed replies raise
say("\nR-L6  a fenced judge reply: silent pass, or failure?")
t = next(t for t in TASKS.values() if t.evaluation_criteria.nl_assertions)
fenced = AssistantMessage(role="assistant", content='```json\n{"results": []}\n```')
with mock.patch.object(ENA, "generate", return_value=fenced):
    try:
        ENA.NLAssertionsEvaluator.calculate_reward(task=t, full_trajectory=[
            UserMessage(role="user", content="hi")])
        r6 = "returned (would be a silent pass)"
    except Exception as e:
        r6 = f"raised {type(e).__name__}"
out["R-L6"] = {"fenced_reply": r6}
say(f"      fenced reply -> {r6}")

# ---------------------------------------------------------------- R-L7: thought signatures, full arms
say("\nR-L7  thought signatures in tool-call ids, all 160 trajectories per arm")
sig = {}
for arm in ("gem", "oai"):
    ids = []
    for trial in (1, 2, 3, 4):
        d = json.loads((SIMS / f"phaseC_t{trial}_{arm}" / "results.json").read_text())
        ids += [tc["id"] for s in d["simulations"] for m in s["messages"] for tc in (m.get("tool_calls") or [])]
    sig[arm] = {"tool_calls": len(ids), "with_thought": sum("__thought__" in i for i in ids),
                "max_id_len": max(map(len, ids))}
    say(f"      {arm}: {sig[arm]}")
out["R-L7"] = sig

# ---------------------------------------------------------------- R-L8: one flip is not an asymmetry
say("\nR-L8  does one flip establish a family asymmetry?")
a, b, c, d = 1, 127, 0, 128                      # OpenAI judges 1/128 flips, Google judges 0/128
p = math.comb(a + b, a) * math.comb(c + d, c) / math.comb(a + b + c + d, a + c)
man = json.loads((REPO / "results/phaseD_regrade_manifest.json").read_text())
rep = {(x["run"], x["task"]) for x in man["design"]["replicate_trajectories"]}
disagree = []
for r in inc:
    if r["matches_incumbent"] is False:
        k = (r["run"], r["task"])
        disagree.append({"run": r["run"], "task": r["task"], "in_replicate_sample": k in rep,
                         "gradings": [x["nl_reward"] for x in J
                                      if x["judge"] == "gpt-4.1-2025-04-14" and (x["run"], x["task"]) == k]})
out["R-L8"] = {"fisher_one_sided_p": round(p, 3), "incumbent_disagreements": disagree,
               "undated_judge_names": [j for j in man["design"]["judges"] if "2025" not in j]}
say(f"      Fisher one-sided p = {p:.2f}; disagreements: {disagree}")

# ---------------------------------------------------------------- R-L9: what the journal records
say("\nR-L9  can a re-grade be matched and re-read from the journal alone?")
keys = sorted(J[0])
out["R-L9"] = {"fields": keys,
               "has_request_hash": any("hash" in k or "sha" in k for k in keys),
               "has_raw_completion": any(k in keys for k in ("content", "raw", "completion", "response")),
               "has_judge_reasoning": "reasoning" in json.dumps(J[0].get("verdicts"))}
say(f"      {out['R-L9']}")

OUT.parent.mkdir(parents=True, exist_ok=True)
OUT.write_text(json.dumps(out, indent=1, default=str) + "\n")
say(f"\nwrote {OUT.relative_to(REPO)}")
sys.exit(0)
