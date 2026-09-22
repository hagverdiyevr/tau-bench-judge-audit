"""Verify the Phase D runner's safety guards actually fire. No API spend.

Same discipline as test_runner_guards.py: each guard is asserted by making its precondition
false and confirming the runner REFUSES, not by trusting that the code reads correctly.

This file never writes to a real artifact path. The test that destroyed 40 paid simulations
wrote a stub to a live path and cleaned up only `if created`; everything here backs up first and
restores in `finally`.
"""
import json
import pathlib
import subprocess
import sys

REPO = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "scripts" / "phase_d"))
RUNNER = REPO / "scripts/phase_d/run_phase_d.py"
BUILDER = REPO / "scripts/phase_d/build_manifest.py"
MANIFEST = REPO / "results/phaseD_regrade_manifest.json"
JOURNAL = REPO / "results/phase_d/regrade_journal.jsonl"
FAIL = []


def run(extra=()):
    return subprocess.run([sys.executable, str(RUNNER), *extra],
                          cwd=REPO / "vendor/tau2-bench", capture_output=True, text=True)


def check(name, cond, detail=""):
    print(f"  {'PASS' if cond else 'FAIL'}  {name}{'' if cond else ' — ' + detail}")
    if not cond:
        FAIL.append(name)


m = json.loads(MANIFEST.read_text())
d, params = m["design"], m["parameters"]

# ---------------------------------------------------------------- manifest shape
print("--- manifest: the §6.3 replicate design is pre-specified, not improvised ---")
check("320 trajectories x 4 judges = 1280 base evaluations",
      d["base_evaluations"] == 1280, str(d["base_evaluations"]))
check("§6.3 replicates present (64 trajectories x 4 judges x 2 extra = 512)",
      d["replicate_evaluations"] == 512, str(d["replicate_evaluations"]))
check("total is 1792, not the 1280 the plan quoted",
      d["total_evaluations"] == 1792, str(d["total_evaluations"]))
check("replicate sample is 20% of 320", len(d["replicate_trajectories"]) == 64,
      str(len(d["replicate_trajectories"])))

per_run = {}
for t in d["replicate_trajectories"]:
    per_run[t["run"]] = per_run.get(t["run"], 0) + 1
check("replicate sample is stratified 8-per-invocation (A-005), not free across 320",
      set(per_run.values()) == {8} and len(per_run) == 8, str(sorted(per_run.items())))
check("every judge carries an equal share of the work",
      len({sum(1 for u in m["units"] if u["judge"] == j) for j in d["judges"]}) == 1)
check("the incumbent judge is in the grid",
      "gpt-4.1-2025-04-14" in d["judges"], str(d["judges"]))

# ---------------------------------------------------------------- determinism of the draw
print("\n--- manifest: the pre-drawn sample must be reproducible from the stated seed ---")
bak = MANIFEST.read_text()
try:
    subprocess.run([sys.executable, str(BUILDER)], cwd=REPO, capture_output=True, text=True)
    again = json.loads(MANIFEST.read_text())["design"]
    check("rebuilding reproduces the same replicate sample",
          again["replicate_sha256"] == d["replicate_sha256"],
          f"{again['replicate_sha256'][:12]} vs {d['replicate_sha256'][:12]}")
    check("rebuilding reproduces the same trajectory set",
          again["trajectory_sha256"] == d["trajectory_sha256"])
finally:
    MANIFEST.write_text(bak)

# ---------------------------------------------------------------- the A-002 defect, not repeated
print("\n--- config: the zero-retry defect that killed 6/40 simulations must not recur ---")
check("bounded retries are configured (A-005: 4, matching A-004)",
      params["max_retries"] == 4, str(params["max_retries"]))
check("retries are NOT zero — litellm's own default, and A-002's mistake",
      params["max_retries"] != 0)
check("retry delay suits a per-minute limit (5.0s, not litellm's 1.0s)",
      params["retry_delay"] >= 5.0, str(params["retry_delay"]))
check("a request timeout is set so one hung call cannot stall 1,792 units",
      params["request_timeout"] and params["request_timeout"] <= 300,
      str(params["request_timeout"]))
src = RUNNER.read_text()
check("the runner actually passes num_retries to completion()",
      "num_retries=p[\"max_retries\"]" in src.replace("'", '"'))
check("the runner installs the A-003 attempt logger",
      "attempt_logger.install" in src)

# ---------------------------------------------------------------- cost: never silently free
print("\n--- pricing: an unpriced call is UNKNOWN, never 0.0 ---")
from pricing import price, resolve_cost  # noqa: E402

check("a known model prices correctly",
      abs(price("gpt-4.1-2025-04-14", 1_000_000, 0) - 2.00) < 1e-9)
check("an UNKNOWN model returns None, not 0.0",
      price("some/unpriced-model", 1000, 100) is None)
check("missing usage returns None, not 0.0", price("gpt-4.1-mini", None, None) is None)
usd, srcname = resolve_cost("gpt-4.1-mini", None, 1_000_000, 0)
check("litellm reporting nothing falls back to the table",
      abs(usd - 0.40) < 1e-9 and srcname == "price_table", f"{usd} {srcname}")
usd, srcname = resolve_cost("gpt-4.1-mini", 0.0, 1_000_000, 0)
check("litellm reporting a suspicious 0.0 also falls back (the known defect)",
      abs(usd - 0.40) < 1e-9 and srcname == "price_table", f"{usd} {srcname}")
usd, srcname = resolve_cost("some/unpriced-model", 0.0, 1000, 100)
check("an unpriceable call surfaces as UNKNOWN so it cannot vanish from the ledger",
      usd is None and srcname == "UNKNOWN", f"{usd} {srcname}")

# ---------------------------------------------------------------- resume semantics
print("\n--- resume: settled work is skipped, UNSETTLED work is retried (D-020) ---")
had = JOURNAL.exists()
bakj = JOURNAL.read_text() if had else None
try:
    JOURNAL.parent.mkdir(parents=True, exist_ok=True)
    u0 = m["units"][0]
    settled = dict(u0, settled=True, ok=True, nl_reward=1.0, usd=0.001)
    JOURNAL.write_text(json.dumps(settled) + "\n")
    r = run(["--dry-run"])
    check("a settled unit is not re-dispatched",
          "already settled     : 1" in r.stdout, r.stdout[-300:])

    # An API failure is an infrastructure outcome, not a verdict. If resume treated it as done,
    # a transient rate limit would become permanent missing data in the paired contrast.
    u1 = m["units"][1]
    unsettled = dict(u1, settled=False, ok=False, error_kind="APIError", nl_reward=None, usd=None)
    JOURNAL.write_text(json.dumps(settled) + "\n" + json.dumps(unsettled) + "\n")
    r = run(["--dry-run"])
    check("an UNSETTLED (APIError) unit is re-dispatched, not banked as missing data",
          "already settled     : 1" in r.stdout, r.stdout[-300:])

    # A killed process can leave a half-written final line.
    JOURNAL.write_text(json.dumps(settled) + "\n" + json.dumps(settled)[:40])
    r = run(["--dry-run"])
    check("a torn final journal line does not crash resume",
          r.returncode == 0 and "already settled     : 1" in r.stdout, r.stdout[-300:])
finally:
    if had:
        JOURNAL.write_text(bakj)
    elif JOURNAL.exists():
        JOURNAL.unlink()

# ---------------------------------------------------------------- input-corpus gate
print("\n--- gate 3: a changed input corpus must block dispatch ---")
bak = MANIFEST.read_text()
try:
    tampered = json.loads(bak)
    tampered["design"]["trajectory_sha256"] = "0" * 64
    MANIFEST.write_text(json.dumps(tampered, indent=1, sort_keys=True) + "\n")
    r = run(["--dry-run"])
    check("refuses when the corpus hash does not match the manifest",
          r.returncode != 0 and "REFUSING TO RUN" in r.stdout + r.stderr, f"rc={r.returncode}")
finally:
    MANIFEST.write_text(bak)
r = run(["--dry-run"])
check("proceeds again once restored", r.returncode == 0, f"rc={r.returncode}")

# ---------------------------------------------------------------- no-credential safety
print("\n--- dry-run must validate without credentials or spend ---")
check("dry-run reaches the budget gate and dispatches nothing",
      "DRY RUN — nothing dispatched, no spend." in r.stdout)
check("gates run before any live import (dry-run needs no API key)",
      src.index("if args.dry_run") < src.index("from litellm import completion"))

print()
if FAIL:
    print(f"  {len(FAIL)} PHASE D GUARD FAILURE(S): {FAIL}")
    sys.exit(1)
print("  ALL PHASE D GUARDS FIRE CORRECTLY.")
sys.exit(0)
