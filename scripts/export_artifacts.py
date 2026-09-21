"""Export run artifacts out of the gitignored submodule so a fresh clone can inspect them.

Raw results.json files live at vendor/tau2-bench/data/simulations/<run>/, which is inside the
submodule AND gitignored — so a fresh clone cannot regenerate the spend ledger or independently
check any trajectory-level claim (external-review finding R2).

This writes a tracked, compact record per run: messages, reward breakdown, costs, usage,
termination. It DROPS `raw_data` (the multi-hundred-KB provider blobs, which also hold
thought-signature payloads) — that is the sanitization, and it is why the export is small enough
to commit.

Run:  python scripts/export_artifacts.py
"""
import glob, hashlib, json, pathlib

REPO = pathlib.Path(__file__).resolve().parents[1]
OUT = REPO / "results" / "artifacts"
OUT.mkdir(parents=True, exist_ok=True)

KEEP_MSG = ("role", "content", "tool_calls", "id", "requestor", "cost", "usage",
            "generation_time_seconds")
index = []
for path in sorted(glob.glob(str(REPO / "vendor/tau2-bench/data/simulations/*/results.json"))):
    d = json.loads(pathlib.Path(path).read_text())
    name = pathlib.Path(path).parent.name
    sims = []
    for s in d["simulations"]:
        sims.append({
            "task_id": s["task_id"], "trial": s.get("trial"), "seed": s.get("seed"),
            "termination_reason": s.get("termination_reason"),
            "agent_cost": s.get("agent_cost"), "user_cost": s.get("user_cost"),
            "duration": s.get("duration"),
            "reward_info": s.get("reward_info"),
            "agent_usage": s.get("agent_usage"),
            # raw_data dropped: provider blobs, not needed for any published claim
            "messages": [{k: m[k] for k in KEEP_MSG if k in m} for m in s["messages"]],
        })
    rec = {"run": name, "timestamp": d.get("timestamp"), "info": d.get("info"),
           "n_simulations": len(sims), "simulations": sims}
    body = json.dumps(rec, indent=1, sort_keys=True)
    (OUT / f"{name}.json").write_text(body + "\n")
    src = pathlib.Path(path).stat().st_size
    index.append({"run": name, "file": f"results/artifacts/{name}.json",
                  "n_simulations": len(sims),
                  "source_bytes": src, "export_bytes": len(body),
                  "sha256": hashlib.sha256(body.encode()).hexdigest()})
    print(f"  {name:<24}{len(sims):>3} sims  {src/1024:>8.0f} KB -> {len(body)/1024:>7.0f} KB")

(OUT / "index.json").write_text(json.dumps({"exports": index}, indent=1) + "\n")
tot_s = sum(i["source_bytes"] for i in index); tot_e = sum(i["export_bytes"] for i in index)
print(f"\n  {len(index)} runs, {sum(i['n_simulations'] for i in index)} simulations")
print(f"  {tot_s/1024/1024:.1f} MB raw -> {tot_e/1024/1024:.2f} MB tracked "
      f"({100*tot_e/tot_s:.0f}%)  — raw_data dropped")
print(f"  wrote {(OUT/'index.json').relative_to(REPO)}")
