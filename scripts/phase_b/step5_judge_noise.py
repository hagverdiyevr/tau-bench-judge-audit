"""STEP 5 / GATES B5 + B2 — judge noise floor, and the re-grading harness itself.

COST: ~USD 0.15 (5 saved trajectories x 3 repeats, incumbent gpt-4.1 judge).

Does two jobs:
  B2 — proves we can re-score SAVED trajectories without re-running the conversation.
       This is the mechanism the whole study depends on (D-009). It also validates that a
       re-grade reproduces tau2's own recorded verdict.
  B5 — measures the judge's self-disagreement at its pinned temperature 0.0. Temperature 0
       is NOT determinism for remote inference, so this is measured, not assumed.

Run:  cd vendor/tau2-bench && uv run python ../../scripts/phase_b/step5_judge_noise.py
"""

import json
import pathlib as _pl
from collections import defaultdict

from dotenv import load_dotenv
from loguru import logger

logger.remove()

_REPO = _pl.Path(__file__).resolve().parents[2]
_OUT = _REPO / "results" / "phase_b"
_OUT.mkdir(parents=True, exist_ok=True)
load_dotenv(_REPO / ".env", override=True)

from tau2.data_model.message import AssistantMessage, SystemMessage, ToolMessage, UserMessage
from tau2.evaluator import evaluator_nl_assertions as ENA

RUN = _REPO / "vendor/tau2-bench/data/simulations/step5_judge_gated/results.json"
REPEATS = 3

data = json.loads(RUN.read_text())
tasks = {str(t["id"]): t for t in data["tasks"]}


def rebuild(msgs):
    """Reconstruct tau2 Message objects from the persisted trajectory."""
    out = []
    for m in msgs:
        r = m.get("role")
        try:
            if r == "user":
                out.append(UserMessage(**m))
            elif r == "assistant":
                out.append(AssistantMessage(**m))
            elif r == "tool":
                out.append(ToolMessage(**m))
            elif r == "system":
                out.append(SystemMessage(**m))
        except Exception:
            pass  # skip anything the model rejects; report count below
    return out


print("=" * 78)
print(f"STEP 5 — judge re-grade x{REPEATS} on saved trajectories  (incumbent gpt-4.1)")
print("=" * 78)

records = []
for sim in data["simulations"]:
    tid = str(sim["task_id"])
    task = tasks.get(tid, {})
    asserts = ((task.get("evaluation_criteria") or {}).get("nl_assertions")) or []
    if not asserts:
        continue
    traj = rebuild(sim["messages"])
    original = {c["nl_assertion"]: c["met"] for c in (sim["reward_info"].get("nl_assertions") or [])}

    reps = []
    for _ in range(REPEATS):
        checks = ENA.NLAssertionsEvaluator.evaluate_nl_assertions(
            trajectory=traj, nl_assertions=list(asserts)
        )
        reps.append({c.nl_assertion: c.met for c in checks})

    print(f"\n  task {tid}  ({len(asserts)} assertion(s), {len(traj)}/{len(sim['messages'])} msgs rebuilt)")
    for a in asserts:
        verdicts = [r.get(a) for r in reps]
        orig = original.get(a)
        stable = len(set(verdicts)) == 1
        agrees = stable and verdicts[0] == orig
        flag = "stable" if stable else "*** FLIPPED ***"
        print(f"    orig={str(orig):<5} regrades={[str(v) for v in verdicts]} {flag}"
              f"{'' if agrees or not stable else '  (differs from recorded)'}")
        records.append(dict(task=tid, assertion=a, original=orig, reps=verdicts,
                            stable=stable, matches_original=agrees))

# ---------------- verdict ----------------
n = len(records)
stable = sum(r["stable"] for r in records)
match = sum(r["matches_original"] for r in records)
flips = [r for r in records if not r["stable"]]

print("\n" + "=" * 78)
print(f"  assertions re-graded      : {n}")
print(f"  stable across {REPEATS} repeats : {stable}/{n}  ({stable/n*100:.0f}%)" if n else "  none")
print(f"  reproduced tau2's verdict : {match}/{n}  ({match/n*100:.0f}%)" if n else "")
if flips:
    print(f"\n  UNSTABLE assertions ({len(flips)}):")
    for r in flips:
        print(f"    task {r['task']}: {r['reps']}  | {r['assertion'][:70]}")
print()
b2 = n > 0 and match == n
b5 = n > 0 and stable == n
print(f"  GATE B2 (re-grade saved trajectories, reproduces recorded verdict): "
      f"{'PASS' if b2 else 'PARTIAL/FAIL'}")
print(f"  GATE B5 (judge self-consistency at temperature 0.0): "
      f"{'PASS - no observed noise' if b5 else 'NOISE DETECTED'}")
if not b5:
    print("       => judge noise is real; the family-bias estimate needs replicate grading")
    print("          and must be reported against this measured noise floor.")
print("=" * 78)

json.dump({"repeats": REPEATS, "n_assertions": n, "stable": stable,
           "matches_original": match, "records": records},
          open(_OUT / "step5_judge_noise.json", "w"), indent=1)
print(f"\nwrote {_OUT / 'step5_judge_noise.json'}")
