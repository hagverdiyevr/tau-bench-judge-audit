"""B9 — run-to-run reproducibility across repeat invocations (upstream #540).

Was missing from the repo: the B-L15 finding was published without the code that produced it,
violating the project's own D-004 lesson. This reconstructs it and additionally reports the
fields the original inline check did NOT compare — which is how "byte-identical" got asserted.

Run:  cd vendor/tau2-bench && uv run --frozen python ../../scripts/phase_b/b9_determinism.py
"""
import hashlib, json, pathlib

REPO = pathlib.Path(__file__).resolve().parents[2]
SIMS = REPO / "vendor/tau2-bench/data/simulations"
ARMS = {"gemini-3.1-flash-lite": ["step5_judge_gated", "b9_seed1002", "b9_seed1003"],
        "gpt-4.1-nano":          ["b9_openai_seed2001", "b9_openai_seed2002"]}

def load(tag):
    d = json.loads((SIMS / tag / "results.json").read_text())
    return {str(s["task_id"]): s for s in d["simulations"]}

def canon(o):  # full object, order-insensitive
    return hashlib.sha256(json.dumps(o, sort_keys=True).encode()).hexdigest()

out = {}
for arm, tags in ARMS.items():
    runs = [load(t) for t in tags]
    tasks = sorted(set(runs[0]) & set.intersection(*[set(r) for r in runs[1:]]), key=int)
    rows = []
    for t in tasks:
        sims = [r[t] for r in runs]
        content = {hashlib.sha256("|".join(f"{m['role']}:{m.get('content') or ''}"
                   for m in s["messages"]).encode()).hexdigest() for s in sims}
        tools = {hashlib.sha256(json.dumps([[tc["name"], tc["arguments"]]
                 for m in s["messages"] for tc in (m.get("tool_calls") or [])],
                 sort_keys=True).encode()).hexdigest() for s in sims}
        rows.append(dict(task=t,
            content_identical=len(content) == 1,
            toolcalls_identical=len(tools) == 1,
            rewards={s["reward_info"]["reward"] for s in sims},
            reward_identical=len({s["reward_info"]["reward"] for s in sims}) == 1,
            cost_identical=len({round(s["agent_cost"] + s["user_cost"], 8) for s in sims}) == 1,
            whole_object_identical=len({canon(s) for s in sims}) == 1))
    out[arm] = rows
    n = len(rows)
    print(f"\n{arm}  ({len(tags)} repeat invocations, {n} tasks)")
    print(f"  message contents identical : {sum(r['content_identical'] for r in rows)}/{n}")
    print(f"  tool calls identical       : {sum(r['toolcalls_identical'] for r in rows)}/{n}")
    print(f"  rewards identical          : {sum(r['reward_identical'] for r in rows)}/{n}")
    print(f"  costs identical            : {sum(r['cost_identical'] for r in rows)}/{n}")
    print(f"  WHOLE OBJECT identical     : {sum(r['whole_object_identical'] for r in rows)}/{n}"
          f"   <- why 'byte-identical' was wrong")

print("\nNOTE: LiteLLM drops `seed` for the gemini provider (utils/llm_utils.py:71),")
print("so the Gemini runs are repeat invocations, NOT seeded replicates.")
(REPO / "results/phase_b/b9_determinism.json").write_text(json.dumps(
    {k: [{**r, "rewards": sorted(r["rewards"])} for r in v] for k, v in out.items()}, indent=1) + "\n")
