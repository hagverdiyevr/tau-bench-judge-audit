"""Build the immutable Phase D re-grading manifest.

Phase D's work unit is one (run, task, judge, replicate) evaluation. Enumerating them up front —
before a single call is dispatched — is what makes the run resumable, auditable and budget-bounded,
exactly as scripts/phase_c/build_manifest.py does for generation.

Two things here are PREREGISTRATION requirements, not conveniences:

  * §6.3 noise control requires "a pre-specified random 20% of trajectories 3x per judge". A
    sample that is drawn at dispatch time is not pre-specified. It is drawn HERE, from a stated
    seed, and published in the manifest before execution.
  * §5.2's discipline — a pre-drawn permutation published before execution — is applied to the
    replicate sample for the same reason: so the selection cannot be nudged once results exist.

The 20% sample is stratified by invocation (8 of each run's 40 trajectories) rather than drawn
freely across all 320. Free sampling can land unevenly across arms and trials, which would make
the per-arm flip rate — the number §6.3 exists to produce — rest on whatever the draw happened to
give. Stratification is recorded in AMENDMENT A-005.

Run:  python scripts/phase_d/build_manifest.py
"""

import datetime
import hashlib
import json
import pathlib
import random
import subprocess
import sys

REPO = pathlib.Path(__file__).resolve().parents[2]
OUT = REPO / "results" / "phaseD_regrade_manifest.json"
SIMS = REPO / "vendor" / "tau2-bench" / "data" / "simulations"

# --- frozen judge grid (PREREGISTRATION §4.2) ---------------------------------------------
# These four strings are FROZEN. Two are aliases rather than dated snapshots; that is what the
# pre-registration fixed, so they are not "improved" here. The runner records the model the
# provider actually returns, so alias drift is detectable after the fact instead of invisible.
JUDGES = [
    "gpt-4.1-2025-04-14",            # OpenAI, high tier — THE INCUMBENT
    "gpt-4.1-mini",                  # OpenAI, low tier
    "gemini/gemini-3.8-flash",       # Google, high tier
    "gemini/gemini-3.1-flash-lite",  # Google, low tier
]

# --- §6.3 noise control --------------------------------------------------------------------
REPLICATE_SEED = 20260922      # stated, fixed, pre-drawn
REPLICATE_FRACTION = 0.20      # §6.3: "a pre-specified random 20% of trajectories"
REPLICATE_TOTAL = 3            # §6.3: "3x per judge" — 3 gradings in total, so 2 beyond the base

# --- operational parameters (A-005) ---------------------------------------------------------
TEMPERATURE = 0.0              # §4.5, upstream judge default
MAX_TOKENS = 4000              # max assertions on any one task is 4; 4000 is ~50x headroom
MAX_RETRIES = 4                # A-004's setting, for A-004's reason: a 200k TPM org ceiling
RETRY_DELAY = 5.0              # a per-minute limit is not survivable with litellm's 1.0s default
REQUEST_TIMEOUT = 120.0        # a hung judge call must not stall 1,792 units


def git(*args, cwd=REPO):
    return subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True).stdout.strip()


# --- trajectories: derived from the shipped artifacts, never hardcoded (D-004) ---------------
runs = sorted(p.name for p in SIMS.iterdir() if p.is_dir() and p.name.startswith("phaseC_"))
if len(runs) != 8:
    sys.exit(f"expected 8 Phase C invocations, found {len(runs)} — refusing to build")

trajectories, per_run = [], {}
for run in runs:
    data = json.loads((SIMS / run / "results.json").read_text())
    sims = data["simulations"]
    infra = [s for s in sims if s.get("termination_reason") == "infrastructure_error"]
    if len(sims) != 40 or infra:
        sys.exit(f"{run} is not a clean invocation ({len(sims)}/40 sims, {len(infra)} infra) — "
                 f"refusing to build a manifest over damaged input")
    ids = sorted((str(s["task_id"]) for s in sims), key=int)
    per_run[run] = ids
    trajectories += [{"run": run, "task": t} for t in ids]

if len(trajectories) != 320:
    sys.exit(f"expected 320 trajectories, got {len(trajectories)} — refusing to build")

# --- pre-drawn replicate sample, stratified by invocation (A-005) ----------------------------
k = round(40 * REPLICATE_FRACTION)                    # 8 of each run's 40
rng = random.Random(REPLICATE_SEED)
replicate_set = []
for run in runs:
    replicate_set += [{"run": run, "task": t} for t in sorted(rng.sample(per_run[run], k), key=int)]

rep_keys = {(r["run"], r["task"]) for r in replicate_set}

# --- work units ------------------------------------------------------------------------------
# One unit = one judge call. `replicate` is 1 for the base pass; the sampled 20% also get 2 and 3.
units = []
for tr in trajectories:
    reps = REPLICATE_TOTAL if (tr["run"], tr["task"]) in rep_keys else 1
    for judge in JUDGES:
        for rep in range(1, reps + 1):
            units.append({"run": tr["run"], "task": tr["task"], "judge": judge, "replicate": rep})

base = sum(1 for u in units if u["replicate"] == 1)
extra = len(units) - base

manifest = {
    "schema": "phaseD-regrade-manifest/1",
    "generated_by": "scripts/phase_d/build_manifest.py",
    "generated_utc": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    "preregistration": {
        "sections": ["4.2", "4.4", "5.5", "6.3"],
        "frozen_sha256": json.loads((REPO / "results/preregistration.sha256").read_text())["sha256"],
        "amendments": [e["id"] for e in
                       json.loads((REPO / "results/preregistration_chain.json").read_text())["chain"]],
    },
    "provenance": {
        "superproject_head": git("rev-parse", "HEAD"),
        "superproject_dirty": bool(git("status", "--porcelain")),
        "submodule_sha": git("rev-parse", "HEAD", cwd=REPO / "vendor/tau2-bench"),
        "phase_c_manifest_sha256": json.loads(
            (REPO / "results/phaseC_execution_manifest.json").read_text())["manifest_sha256"],
        "python": sys.version.split()[0],
    },
    "parameters": {
        "temperature": TEMPERATURE, "max_tokens": MAX_TOKENS,
        "max_retries": MAX_RETRIES, "retry_delay": RETRY_DELAY,
        "request_timeout": REQUEST_TIMEOUT,
        "retry_rationale": "A-005. litellm.completion() defaults to num_retries=None, i.e. ZERO "
                           "retries. Phase D pushes ~1.01M input tokens per judge pass against the "
                           "same 200k TPM org ceiling A-004 identified, so rate limiting is certain "
                           "by construction. Unretried, a limit becomes a permanent missing verdict "
                           "-- and a missing verdict breaks the within-trajectory PAIRING, which is "
                           "the estimand itself. Worse, the loss is not missing-at-random: it "
                           "concentrates on the longest trajectories, which are the hardest tasks.",
    },
    "design": {
        "n_trajectories": len(trajectories), "n_judges": len(JUDGES),
        "base_evaluations": base,
        "replicate_evaluations": extra,
        "total_evaluations": len(units),
        "judges": JUDGES,
        "replicate_seed": REPLICATE_SEED,
        "replicate_fraction": REPLICATE_FRACTION,
        "replicate_total_per_judge": REPLICATE_TOTAL,
        "replicate_stratified_by": "invocation (8 of each run's 40)",
        "replicate_trajectories": replicate_set,
        "replicate_sha256": hashlib.sha256(
            ",".join(f"{r['run']}:{r['task']}" for r in replicate_set).encode()).hexdigest(),
        "trajectory_sha256": hashlib.sha256(
            ",".join(f"{t['run']}:{t['task']}" for t in trajectories).encode()).hexdigest(),
    },
    "units": units,
}

body = json.dumps(manifest, indent=1, sort_keys=True)
manifest["manifest_sha256"] = hashlib.sha256(body.encode()).hexdigest()
OUT.write_text(json.dumps(manifest, indent=1, sort_keys=True) + "\n")

d = manifest["design"]
print(f"  trajectories      : {d['n_trajectories']}  (sha {d['trajectory_sha256'][:12]}…)")
print(f"  judges            : {d['n_judges']}")
print(f"  base evaluations  : {d['base_evaluations']}")
print(f"  replicates (§6.3) : {d['replicate_evaluations']}  "
      f"= {len(replicate_set)} trajectories x {d['n_judges']} judges x {REPLICATE_TOTAL - 1} extra")
print(f"  TOTAL evaluations : {d['total_evaluations']}")
print(f"  replicate sample  : {len(replicate_set)} = 8 per invocation, seed {REPLICATE_SEED} "
      f"(sha {d['replicate_sha256'][:12]}…)")
print(f"  max_retries       : {MAX_RETRIES}   (litellm default is ZERO — see retry_rationale)")
print(f"  submodule         : {manifest['provenance']['submodule_sha'][:12]}…")
print(f"  manifest sha256   : {manifest['manifest_sha256'][:16]}…")
print(f"\n  wrote {OUT.relative_to(REPO)}")
