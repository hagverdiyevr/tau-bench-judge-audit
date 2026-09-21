"""Phase D re-grading harness: score saved trajectories under multiple judges.

Prompt identity is guaranteed by construction: the harness lets tau2's own evaluator build its
system+user prompt, captures it, and re-sends that exact payload to each judge. Nothing about the
question changes between judges — only the model answering it.

Parsing goes through scripts/grading/judge_adapter.py, not upstream's raw json.loads, because
gemini-3.8-flash fences its JSON (J1) and because upstream scores an empty result set as a full
pass (J2). Anomalies are recorded with reward withheld, never silently granted.

Run:  cd vendor/tau2-bench && uv run python ../../scripts/phase_d/regrade.py --run step5_judge_gated
      ... --judges gpt-4.1-2025-04-14 gpt-4.1-mini gemini/gemini-3.8-flash gemini/gemini-3.1-flash-lite
"""

import argparse
import json
import pathlib
import sys
from unittest import mock

REPO = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "scripts" / "grading"))

from dotenv import load_dotenv  # noqa: E402
from loguru import logger  # noqa: E402

logger.remove()
load_dotenv(REPO / ".env", override=True)

from judge_adapter import grade_safe  # noqa: E402
from litellm import completion  # noqa: E402

from tau2.data_model.message import (  # noqa: E402
    AssistantMessage,
    SystemMessage,
    ToolMessage,
    UserMessage,
)
from tau2.evaluator import evaluator_nl_assertions as ENA  # noqa: E402

PRICES = {  # USD per 1M (REFERENCE §2)
    "gpt-4.1-2025-04-14": (2.00, 8.00), "gpt-4.1-mini": (0.40, 1.60),
    "gemini/gemini-3.8-flash": (0.75, 3.75), "gemini/gemini-3.1-flash-lite": (0.25, 1.50),
}
DEFAULT_JUDGES = list(PRICES)

ap = argparse.ArgumentParser()
ap.add_argument("--run", required=True, help="simulation dir under vendor/.../data/simulations")
ap.add_argument("--judges", nargs="+", default=DEFAULT_JUDGES)
ap.add_argument("--limit", type=int, default=0, help="cap trajectories (smoke test)")
ap.add_argument("--out", default=None)
a = ap.parse_args()

SIMS = REPO / "vendor/tau2-bench/data/simulations" / a.run / "results.json"
data = json.loads(SIMS.read_text())
tasks = {str(t["id"]): t for t in data["tasks"]}


def rebuild(msgs):
    out = []
    for m in msgs:
        r, cls = m.get("role"), None
        cls = {"user": UserMessage, "assistant": AssistantMessage,
               "tool": ToolMessage, "system": SystemMessage}.get(r)
        if cls:
            try:
                out.append(cls(**m))
            except Exception:
                pass
    return out


def capture_prompt(trajectory, assertions):
    """Let tau2 build its own prompt, then hand it back verbatim."""
    seen = {}

    def fake(**kw):
        seen["messages"] = kw["messages"]
        # canned VALID response so the evaluator completes without raising
        return AssistantMessage(role="assistant", content=json.dumps(
            {"results": [{"expectedOutcome": x, "metExpectation": True, "reasoning": "capture"}
                         for x in assertions]}))

    with mock.patch.object(ENA, "generate", side_effect=fake):
        ENA.NLAssertionsEvaluator.evaluate_nl_assertions(
            trajectory=trajectory, nl_assertions=list(assertions))
    return seen["messages"]


rows, spend, anomalies = [], 0.0, 0
sims = [s for s in data["simulations"] if (s["reward_info"].get("nl_assertions") or [])]
if a.limit:
    sims = sims[: a.limit]
print(f"  run={a.run}  trajectories={len(sims)}  judges={len(a.judges)}  "
      f"evaluations={len(sims) * len(a.judges)}")

for sim in sims:
    tid = str(sim["task_id"])
    asserts = ((tasks.get(tid, {}).get("evaluation_criteria") or {}).get("nl_assertions")) or []
    traj = rebuild(sim["messages"])
    payload = capture_prompt(traj, asserts)
    msgs = [{"role": m.role, "content": m.content} for m in payload]
    incumbent = {c["nl_assertion"]: c["met"] for c in (sim["reward_info"].get("nl_assertions") or [])}

    for j in a.judges:
        try:
            r = completion(model=j, messages=msgs, temperature=0.0, max_tokens=4000)
            content = r.choices[0].message.content
            cost = r._hidden_params.get("response_cost") or 0.0
            spend += cost
        except Exception as e:
            rows.append(dict(task=tid, judge=j, ok=False, error_kind="APIError",
                             error=f"{type(e).__name__}: {str(e)[:120]}", nl_reward=None))
            anomalies += 1
            continue

        out = grade_safe(content, asserts)
        if not out.ok:
            anomalies += 1
        rows.append(dict(
            task=tid, judge=j, ok=out.ok,
            error_kind=out.error_kind, error=out.error,
            # fail-closed: no reward when the response is not trustworthy
            nl_reward=(1.0 if out.all_met else 0.0) if out.ok else None,
            verdicts={r_.assertion: r_.met for r_ in out.results} if out.ok else None,
            matches_incumbent=(
                {r_.assertion: r_.met for r_ in out.results} == incumbent) if out.ok else None,
            fenced=(content or "").lstrip().startswith("```"),
            usd=round(cost, 6),
        ))

print(f"\n  {'task':>5} {'judge':<32}{'ok':<4}{'nl':<5}{'fenced':<8}{'==incumbent':<12}note")
for r in rows:
    print(f"  {r['task']:>5} {r['judge']:<32}{str(r['ok']):<4}"
          f"{str(r['nl_reward']):<5}{str(r.get('fenced')):<8}"
          f"{str(r.get('matches_incumbent')):<12}{(r.get('error_kind') or '')}")

ok = [r for r in rows if r["ok"]]
agree = [r for r in ok if r.get("matches_incumbent")]
print(f"\n  evaluations     : {len(rows)}")
print(f"  parsed OK       : {len(ok)}/{len(rows)}")
print(f"  anomalies       : {anomalies}  (reward withheld, not granted)")
print(f"  fenced responses: {sum(1 for r in rows if r.get('fenced'))}  "
      f"<- would have crashed upstream's json.loads")
print(f"  agree w/ incumbent (where judge == incumbent model): "
      f"{len([r for r in agree if r['judge'] == 'gpt-4.1-2025-04-14'])}"
      f"/{len([r for r in ok if r['judge'] == 'gpt-4.1-2025-04-14'])}")
print(f"  spend           : ${spend:.5f}")

by = {}
for r in ok:
    by.setdefault(r["judge"], []).append(r["nl_reward"])
print("\n  mean NL reward by judge (same trajectories, same prompt):")
for j, v in by.items():
    print(f"    {j:<32}{sum(v)/len(v):.3f}  (n={len(v)})")

out_path = pathlib.Path(a.out) if a.out else REPO / "results/phase_d" / f"regrade_{a.run}.json"
out_path.parent.mkdir(parents=True, exist_ok=True)
out_path.write_text(json.dumps(
    {"run": a.run, "judges": a.judges, "evaluations": len(rows), "parsed_ok": len(ok),
     "anomalies": anomalies, "usd": round(spend, 6), "rows": rows}, indent=1) + "\n")
print(f"\n  wrote {out_path.relative_to(REPO)}")
sys.exit(0 if len(ok) == len(rows) else 1)
