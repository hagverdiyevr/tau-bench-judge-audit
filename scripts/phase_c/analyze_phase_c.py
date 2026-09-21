"""Phase C analysis: determinism replication at n=40, and the agent main effect.

The determinism check is required by CLAUDE.md before pass^k may be reported for the Gemini arm:
B-L15 observed stability on 5 tasks in a ~15-minute window, which is a pilot observation, not a
structural property. Phase C runs the SAME 40 tasks four times per arm, and LiteLLM drops `seed`
for the gemini provider, so trials 2-4 are a free n=40 replication.

Run:  python scripts/phase_c/analyze_phase_c.py
"""
import collections, hashlib, json, pathlib, statistics as st

REPO = pathlib.Path(__file__).resolve().parents[2]
SIMS = REPO / "vendor/tau2-bench/data/simulations"
ARMS = {"gemini-3.1-flash-lite": [f"phaseC_t{t}_gem" for t in (1, 2, 3, 4)],
        "gpt-4.1-nano":          [f"phaseC_t{t}_oai" for t in (1, 2, 3, 4)]}

def load(tag):
    return {str(s["task_id"]): s for s in
            json.loads((SIMS / tag / "results.json").read_text())["simulations"]}

def h(o): return hashlib.sha256(json.dumps(o, sort_keys=True).encode()).hexdigest()

out = {}
print("=" * 78)
print("DETERMINISM REPLICATION AT n=40  (4 repeat invocations per arm, same tasks)")
print("=" * 78)
for arm, tags in ARMS.items():
    runs = [load(t) for t in tags]
    tasks = sorted(set(runs[0]).intersection(*[set(r) for r in runs[1:]]), key=int)
    c = t_ = r_ = w = 0
    per_task_rewards = {}
    for tid in tasks:
        S = [r[tid] for r in runs]
        content = {h(["|".join(f"{m['role']}:{m.get('content') or ''}" for m in s["messages"])]) for s in S}
        tools = {h([[tc["name"], tc["arguments"]] for m in s["messages"]
                    for tc in (m.get("tool_calls") or [])]) for s in S}
        rews = [s["reward_info"]["reward"] for s in S]
        c += len(content) == 1; t_ += len(tools) == 1
        r_ += len(set(rews)) == 1; w += len({h(s) for s in S}) == 1
        per_task_rewards[tid] = rews
    n = len(tasks)
    out[arm] = dict(n=n, content=c, tools=t_, rewards=r_, whole=w, per_task=per_task_rewards)
    print(f"\n{arm}  ({len(tags)} invocations x {n} tasks)")
    print(f"  message contents identical : {c}/{n}  ({c/n:.0%})")
    print(f"  tool calls identical       : {t_}/{n}  ({t_/n:.0%})")
    print(f"  REWARDS identical          : {r_}/{n}  ({r_/n:.0%})   <- decides pass^k")
    print(f"  whole object identical     : {w}/{n}   (ids/timestamps always differ)")

print("\n" + "=" * 78)
print("WHAT THIS MEANS FOR pass^k")
print("=" * 78)
for arm, d in out.items():
    varying = [t for t, r in d["per_task"].items() if len(set(r)) > 1]
    p1 = st.mean([st.mean(r) for r in d["per_task"].values()])
    p4 = st.mean([1.0 if all(x == 1.0 for x in r) else 0.0 for r in d["per_task"].values()])
    print(f"\n  {arm}")
    print(f"    pass^1 = {p1:.3f}   pass^4 = {p4:.3f}   gap = {p1-p4:+.3f}")
    if d["rewards"] == d["n"]:
        print(f"    reward identical on ALL {d['n']} tasks -> pass^4 == pass^1 BY CONSTRUCTION.")
        print(f"    Report as a determinism result, NOT as a reliability measurement.")
    else:
        print(f"    reward VARIED on {len(varying)}/{d['n']} tasks -> pass^k is a real measurement.")
        print(f"    varying task ids: {varying[:12]}")

print("\n" + "=" * 78)
print("AGENT MAIN EFFECT (secondary; primary estimand is the judge DiD in Phase D)")
print("=" * 78)
print(f"  {'arm':<26}{'pass^1':>8}{'DB':>8}{'NL':>8}{'disagree':>10}{'$/traj':>9}")
for arm, tags in ARMS.items():
    rew, db, nl, dis, cost, tot = [], [], [], 0, [], 0
    for tag in tags:
        for s in load(tag).values():
            ri = s["reward_info"]; bd = ri.get("reward_breakdown") or {}
            rew.append(ri["reward"]); tot += 1
            if bd.get("DB") is not None: db.append(bd["DB"])
            if bd.get("NL_ASSERTION") is not None: nl.append(bd["NL_ASSERTION"])
            if bd.get("DB") is not None and bd.get("NL_ASSERTION") is not None and \
               (bd["DB"] == 1.0) != (bd["NL_ASSERTION"] == 1.0): dis += 1
            cost.append(s["agent_cost"] + s["user_cost"])
    print(f"  {arm:<26}{st.mean(rew):>8.3f}{st.mean(db):>8.3f}{st.mean(nl):>8.3f}"
          f"{f'{dis}/{tot}':>10}{st.mean(cost):>9.5f}")

json.dump({k: {kk: vv for kk, vv in v.items() if kk != "per_task"} for k, v in out.items()},
          open(REPO / "results/phase_c/determinism_n40.json", "w"), indent=1)
print(f"\n  wrote results/phase_c/determinism_n40.json")
