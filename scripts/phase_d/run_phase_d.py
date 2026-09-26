"""Execute Phase D from the immutable manifest: gated, resumable, attempt-logged.

scripts/phase_d/regrade.py proved the MECHANISM (prompt identity by capture, fail-closed parsing,
20/20 in B-L16). It was never a RUNNER. It had no pre-registration gate, no budget gate, no
resume, no attempt log, and -- the defect that matters most -- no retries, so a transient rate
limit became a permanently missing verdict. This file adds the operational discipline Phase C had
to learn the hard way, and keeps regrade.py's capture mechanism unchanged.

Why a missing verdict is worse here than a missing simulation was in Phase C: the estimand is a
WITHIN-TRAJECTORY paired contrast across four judges. Losing one judge's verdict does not cost one
observation, it unpairs the trajectory. And rate-limit losses concentrate on the longest
trajectories -- the hardest tasks -- so the loss is systematic, not noise.

Resume granularity is ONE EVALUATION, not one run. A crash loses at most the in-flight unit.
Following D-020, a unit counts as done only when a journal line proves it, never because a file
exists.

Run:  cd vendor/tau2-bench && uv run --frozen python ../../scripts/phase_d/run_phase_d.py --dry-run
      cd vendor/tau2-bench && uv run --frozen python ../../scripts/phase_d/run_phase_d.py --limit 20
      cd vendor/tau2-bench && uv run --frozen python ../../scripts/phase_d/run_phase_d.py
"""

import argparse
import datetime
import json
import pathlib
import subprocess
import sys
from unittest import mock

REPO = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "scripts" / "grading"))
sys.path.insert(0, str(REPO / "scripts" / "phase_c"))
sys.path.insert(0, str(REPO / "scripts" / "phase_d"))

MANIFEST = REPO / "results" / "phaseD_regrade_manifest.json"
LEDGER = REPO / "results" / "spend_ledger.json"
OUTDIR = REPO / "results" / "phase_d"
JOURNAL = OUTDIR / "regrade_journal.jsonl"
ATTEMPTS = OUTDIR / "attempts" / "phase_d.jsonl"
SIMS = REPO / "vendor" / "tau2-bench" / "data" / "simulations"

SAFETY_FLOOR_USD = 5.00

# Cost handling lives in pricing.py so a test can import it without executing a run. Its one
# rule: an unpriced call is recorded as None and surfaced, NEVER as 0.0 (CLAUDE.md, known defect).
from pricing import PRICES, resolve_cost  # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument("--dry-run", action="store_true", help="validate and print, dispatch nothing")
ap.add_argument("--limit", type=int, default=0, help="cap units this session (smoke test)")
ap.add_argument("--only-run", help="restrict to one Phase C invocation")
args = ap.parse_args()


def utc():
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def die(msg):
    sys.exit(f"  REFUSING TO RUN — {msg}")


# ---- gate 1: pre-registration and amendment chain intact ----------------------------------
r = subprocess.run([sys.executable, str(REPO / "scripts/verify_preregistration.py")],
                   capture_output=True, text=True)
if r.returncode != 0:
    die("pre-registration or amendment chain failed verification:\n" + r.stdout + r.stderr)
print("  gate 1: pre-registration + amendment chain INTACT")

# ---- gate 2: manifest provenance still matches reality -------------------------------------
m = json.loads(MANIFEST.read_text())
sub = subprocess.run(["git", "rev-parse", "HEAD"], cwd=REPO / "vendor/tau2-bench",
                     capture_output=True, text=True).stdout.strip()
if sub != m["provenance"]["submodule_sha"]:
    die(f"submodule moved: manifest {m['provenance']['submodule_sha'][:12]} vs actual {sub[:12]}")
frozen = json.loads((REPO / "results/preregistration.sha256").read_text())["sha256"]
if frozen != m["preregistration"]["frozen_sha256"]:
    die("manifest was built against a different frozen pre-registration")
print(f"  gate 2: provenance OK — submodule {sub[:12]}…, manifest {m['manifest_sha256'][:12]}…")

# ---- gate 3: the INPUT trajectories are still the ones the manifest was built over ----------
# Phase D reads Phase C's artifacts. If one were truncated or regenerated since, every downstream
# verdict would silently describe a different corpus.
import hashlib  # noqa: E402

runs = sorted({u["run"] for u in m["units"]})
traj, loaded = [], {}
for run in runs:
    art = SIMS / run / "results.json"
    if not art.exists():
        die(f"{run}: results.json is missing — Phase D cannot re-grade absent trajectories")
    d = json.loads(art.read_text())
    sims = d["simulations"]
    infra = [s for s in sims if s.get("termination_reason") == "infrastructure_error"]
    if len(sims) != 40 or infra:
        die(f"{run}: {len(sims)}/40 simulations, {len(infra)} infrastructure_error — "
            f"input corpus is damaged")
    loaded[run] = d
    traj += [f"{run}:{t}" for t in sorted((str(s['task_id']) for s in sims), key=int)]
actual = hashlib.sha256(",".join(traj).encode()).hexdigest()
if actual != m["design"]["trajectory_sha256"]:
    die(f"input corpus changed since the manifest was built "
        f"(expected {m['design']['trajectory_sha256'][:12]}…, got {actual[:12]}…). "
        f"Rebuild the manifest only if the change was intended.")
print(f"  gate 3: input corpus INTACT — {len(traj)} trajectories, 0 infra errors "
      f"(sha {actual[:12]}…)")

# ---- resume: a unit is done only when a journal line proves it (D-020) ---------------------
OUTDIR.mkdir(parents=True, exist_ok=True)
done, prior_usd = {}, 0.0
if JOURNAL.exists():
    for line in JOURNAL.read_text().splitlines():
        if not line.strip():
            continue
        try:
            rec = json.loads(line)
        except json.JSONDecodeError:
            continue          # a torn last line from a kill — the unit simply re-runs
        # Only a SETTLED unit counts as done. An API error is unsettled and must be retried on
        # resume; treating it as done would bake a rate limit into the dataset permanently.
        if rec.get("settled"):
            done[(rec["run"], rec["task"], rec["judge"], rec["replicate"])] = rec
        prior_usd += rec.get("usd") or 0.0

todo = [u for u in m["units"]
        if (u["run"], u["task"], u["judge"], u["replicate"]) not in done]
if args.only_run:
    todo = [u for u in todo if u["run"] == args.only_run]
if args.limit:
    todo = todo[: args.limit]

p = m["parameters"]
print(f"\n  evaluations planned : {m['design']['total_evaluations']} "
      f"({m['design']['base_evaluations']} base + {m['design']['replicate_evaluations']} replicate)")
print(f"  already settled     : {len(done)}   (prior spend ${prior_usd:.4f})")
print(f"  this session        : {len(todo)}")
print(f"  retries             : {p['max_retries']}   timeout {p['request_timeout']}s")

if not todo:
    print("\n  nothing to do — Phase D is complete.")
    sys.exit(0)

# ---- gate 4: pre-dispatch budget ------------------------------------------------------------
# Priced from the manifest's own token accounting so the estimate cannot drift from the plan.
led = json.loads(LEDGER.read_text())
per_traj_in = 3368          # measured, ledger: judge_input_tokens / simulations on phaseC_t1_gem
est = 0.0
for u in todo:
    pin, pout = PRICES.get(u["judge"], (2.0, 8.0))
    est += per_traj_in / 1e6 * pin + 120 / 1e6 * pout
print(f"  estimated cost      : ${est:.2f}   ledger remaining ${led['remaining_usd']:.2f}")
if led["remaining_usd"] - est < SAFETY_FLOOR_USD:
    die(f"budget floor: remaining ${led['remaining_usd']:.2f}, this session ~${est:.2f}, "
        f"floor ${SAFETY_FLOOR_USD:.2f}")
print("  gate 4: budget OK")

if args.dry_run:
    byj = {}
    for u in todo:
        byj[u["judge"]] = byj.get(u["judge"], 0) + 1
    print("\n  units by judge:")
    for j, n in byj.items():
        print(f"    {j:<32}{n}")
    print("\n  DRY RUN — nothing dispatched, no spend.")
    sys.exit(0)

# ---- live imports (only past the gates, so --dry-run needs no credentials) ------------------
from dotenv import load_dotenv  # noqa: E402
from loguru import logger  # noqa: E402

logger.remove()
load_dotenv(REPO / ".env", override=True)

import attempt_logger  # noqa: E402
from judge_adapter import grade_safe  # noqa: E402
from litellm import completion  # noqa: E402

from tau2.data_model.message import (  # noqa: E402
    AssistantMessage,
    SystemMessage,
    ToolMessage,
    UserMessage,
)
from tau2.evaluator import evaluator_nl_assertions as ENA  # noqa: E402

# A-003: every attempt at the one shared request boundary, successes and failures alike.
attempt_logger.install(ATTEMPTS, invocation="phase_d")
print(f"  attempt log         : {ATTEMPTS.relative_to(REPO)}")

CLS = {"user": UserMessage, "assistant": AssistantMessage,
       "tool": ToolMessage, "system": SystemMessage}


def rebuild(msgs, where):
    """Reconstruct a trajectory. Loses NOTHING silently.

    The original implementation wrapped this in `except Exception: pass`, which would have
    dropped messages from the conversation the judge sees without a word -- D-020's shape
    exactly. Verified lossless over all 8,430 Phase C messages; this makes that a proven
    property instead of an assumption.
    """
    out = []
    for msg in msgs:
        cls = CLS.get(msg.get("role"))
        if cls is None:
            die(f"{where}: unknown message role {msg.get('role')!r}")
        try:
            out.append(cls(**msg))
        except Exception as exc:
            die(f"{where}: message failed to rebuild ({type(exc).__name__}: {exc}). "
                f"Re-grading a silently truncated trajectory would corrupt the verdict.")
    if len(out) != len(msgs):
        die(f"{where}: rebuilt {len(out)} of {len(msgs)} messages")
    return out


def capture_prompt(trajectory, assertions):
    """Let tau2 build its own judge prompt, then hand it back verbatim (B-L16)."""
    seen = {}

    def fake(**kw):
        seen["messages"] = kw["messages"]
        return AssistantMessage(role="assistant", content=json.dumps(
            {"results": [{"expectedOutcome": x, "metExpectation": True, "reasoning": "capture"}
                         for x in assertions]}))

    with mock.patch.object(ENA, "generate", side_effect=fake):
        ENA.NLAssertionsEvaluator.evaluate_nl_assertions(
            trajectory=trajectory, nl_assertions=list(assertions))
    return [{"role": x.role, "content": x.content} for x in seen["messages"]]


# ---- prompt cache: capture once per trajectory, reuse for every judge and replicate ---------
prompts, incumbents, assertions = {}, {}, {}


def prepare(run, task):
    key = (run, task)
    if key in prompts:
        return
    data = loaded[run]
    tasks = {str(t["id"]): t for t in data["tasks"]}
    sim = next(s for s in data["simulations"] if str(s["task_id"]) == task)
    asrt = ((tasks.get(task, {}).get("evaluation_criteria") or {}).get("nl_assertions")) or []
    prompts[key] = capture_prompt(rebuild(sim["messages"], f"{run}:{task}"), asrt)
    assertions[key] = asrt
    incumbents[key] = {c["nl_assertion"]: c["met"]
                       for c in (sim["reward_info"].get("nl_assertions") or [])}


print(f"\n  dispatching {len(todo)} evaluations…\n")
session_usd, settled, unsettled, anomalies, unpriced = 0.0, 0, 0, 0, 0
started = utc()

with JOURNAL.open("a") as jf:
    for n, u in enumerate(todo, 1):
        run, task, judge, rep = u["run"], u["task"], u["judge"], u["replicate"]
        key = (run, task)
        prepare(run, task)

        rec = {"run": run, "task": task, "judge": judge, "replicate": rep, "utc": utc()}
        try:
            resp = completion(model=judge, messages=prompts[key],
                              temperature=p["temperature"], max_tokens=p["max_tokens"],
                              num_retries=p["max_retries"], timeout=p["request_timeout"])
        except Exception as exc:
            # UNSETTLED: retries are exhausted, but this is an infrastructure outcome, not a
            # verdict. It is journaled for the record and re-attempted on the next resume.
            rec.update(settled=False, ok=False, error_kind="APIError",
                       error=f"{type(exc).__name__}: {str(exc)[:200]}", nl_reward=None, usd=None)
            jf.write(json.dumps(rec) + "\n")
            jf.flush()
            unsettled += 1
            print(f"  [{n}/{len(todo)}] {run}:{task} {judge:<30} UNSETTLED {type(exc).__name__}")
            continue

        choice = resp.choices[0]
        content = choice.message.content
        finish = getattr(choice, "finish_reason", None)
        usage = getattr(resp, "usage", None)
        pt = getattr(usage, "prompt_tokens", None)
        ct = getattr(usage, "completion_tokens", None)
        reported = (getattr(resp, "_hidden_params", None) or {}).get("response_cost")
        usd, src = resolve_cost(judge, reported, pt, ct)
        if src == "UNKNOWN":
            unpriced += 1
        session_usd += usd or 0.0

        out = grade_safe(content, assertions[key])
        if not out.ok or finish == "length":
            anomalies += 1
        verdicts = {x.assertion: x.met for x in out.results} if out.ok else None
        rec.update(
            settled=True,
            ok=bool(out.ok) and finish != "length",
            model_returned=getattr(resp, "model", None),
            finish_reason=finish,
            error_kind=("truncated" if finish == "length" else out.error_kind),
            error=out.error,
            # fail-closed: a response we cannot trust yields no reward, never a vacuous pass
            nl_reward=(1.0 if out.all_met else 0.0) if (out.ok and finish != "length") else None,
            verdicts=verdicts,
            matches_incumbent=(verdicts == incumbents[key]) if verdicts is not None else None,
            fenced=(content or "").lstrip().startswith("```"),
            prompt_tokens=pt, completion_tokens=ct, usd=usd, usd_source=src,
        )
        jf.write(json.dumps(rec) + "\n")
        jf.flush()
        settled += 1
        if n % 50 == 0 or n == len(todo):
            print(f"  [{n}/{len(todo)}] settled={settled} unsettled={unsettled} "
                  f"anomalies={anomalies} ${session_usd:.4f}")

summary = attempt_logger.summarize(ATTEMPTS)
print(f"\n  started {started}  ended {utc()}")
print(f"  settled            : {settled}")
print(f"  unsettled (retry)  : {unsettled}")
print(f"  anomalies          : {anomalies}   (reward withheld, never granted)")
print(f"  session spend      : ${session_usd:.4f}")
if unpriced:
    print(f"  UNPRICED CALLS     : {unpriced} — cost is UNKNOWN, not zero. Add the model to "
          f"scripts/phase_d/pricing.py and re-derive the ledger before reporting any total.")
print(f"  attempts logged    : {summary.get('attempts')} "
      f"(failed {summary.get('failures')} {summary.get('failures_by_class')})")

subprocess.run([sys.executable, str(REPO / "scripts/build_spend_ledger.py")],
               cwd=REPO / "vendor/tau2-bench", capture_output=True)

remaining = m["design"]["total_evaluations"] - (len(done) + settled)
if unsettled or remaining:
    print(f"\n  {remaining} evaluation(s) still outstanding. Re-run to resume — settled work "
          f"is never repeated.")
    sys.exit(1)
print("\n  PHASE D COMPLETE — every planned evaluation is settled.")
sys.exit(0)
