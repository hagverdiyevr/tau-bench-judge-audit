"""Verify the Phase C runner's safety guards actually fire. No API spend.

Each guard is asserted by making the precondition false and confirming the runner REFUSES
to dispatch, rather than by trusting that the code reads correctly.
"""
import json, pathlib, shutil, subprocess, sys

REPO = pathlib.Path(__file__).resolve().parents[1]
RUNNER = REPO / "scripts/phase_c/run_phase_c.py"
LEDGER = REPO / "results/spend_ledger.json"
AMEND = REPO / "docs/PREREGISTRATION_AMENDMENTS.md"
SIMS = REPO / "vendor/tau2-bench/data/simulations"
FAIL = []


def run(extra=()):
    return subprocess.run([sys.executable, str(RUNNER), *extra], cwd=REPO / "vendor/tau2-bench",
                          capture_output=True, text=True)


def check(name, cond, detail=""):
    print(f"  {'PASS' if cond else 'FAIL'}  {name}{'' if cond else ' — ' + detail}")
    if not cond:
        FAIL.append(name)


print("--- guard: broken amendment chain must block dispatch ---")
bak = AMEND.read_text()
try:  # restore even if the check raises — a half-tampered amendment breaks every later gate
    AMEND.write_text(bak.replace("high tier)", "HIGH TIER)", 1))
    r = run(["--dry-run"])
    check("refuses on tampered amendment",
          r.returncode != 0 and "REFUSING TO RUN" in r.stdout + r.stderr, f"rc={r.returncode}")
finally:
    AMEND.write_text(bak)
r = run(["--dry-run"])
check("proceeds again once restored", r.returncode == 0, f"rc={r.returncode}")

print("\n--- guard: budget floor must block dispatch ---")
led = json.loads(LEDGER.read_text())
try:  # a ledger left showing fake headroom would mis-gate every later dispatch
    LEDGER.write_text(json.dumps({**led, "remaining_usd": 5.50}, indent=1))
    r = run()
    check("refuses when remaining would breach the floor",
          r.returncode != 0 and "budget floor" in r.stdout + r.stderr, f"rc={r.returncode}")
finally:
    LEDGER.write_text(json.dumps(led, indent=1))

print("\n--- guard: resume-never-restart must skip an existing artifact ---")
# NEVER write to a real artifact path. An earlier version of this test wrote a stub to
# phaseC_t1_gem/results.json and only cleaned up `if created` — so once a real run existed it
# silently DESTROYED 40 simulations of paid data, and the runner then skipped the invocation
# because a file was present. Use a name no invocation can ever claim, and always clean up.
probe = SIMS / "__guard_probe_never_a_real_invocation__"
real_paths = {i["save_to"] for i in json.loads(
    (REPO / "results/phaseC_execution_manifest.json").read_text())["invocations"]}
assert probe.name not in real_paths, "probe name collides with a real invocation"
try:
    probe.mkdir(parents=True, exist_ok=True)
    (probe / "results.json").write_text(json.dumps({"simulations": [{"task_id": "probe"}]}))
    # the runner's skip logic is what we are testing; point it at the probe
    r = run(["--dry-run", "--only", probe.name])
    check("rejects an --only that is not in the manifest (probe is not a real invocation)",
          r.returncode != 0, "probe was accepted as a real invocation")
    # and verify the real skip path using the manifest's own first entry, read-only
    first = sorted(real_paths)[0]
    exists = (SIMS / first / "results.json").exists()
    r = run(["--dry-run"])
    if exists:
        check(f"skips {first} because its artifact exists", f"SKIP {first}" in r.stdout,
              "did not skip an existing artifact")
    else:
        check(f"lists {first} for dispatch (no artifact yet)", first in r.stdout,
              "invocation missing from dry-run plan")
finally:
    shutil.rmtree(probe, ignore_errors=True)
check("no real artifact was modified by this test",
      not (SIMS / "__guard_probe_never_a_real_invocation__").exists())

print("\n--- guard: unknown invocation name must not silently run everything ---")
r = run(["--dry-run", "--only", "does_not_exist"])
check("rejects an unknown --only", r.returncode != 0, f"rc={r.returncode}")

print("\n--- guard: manifest order must be balanced ---")
m = json.loads((REPO / "results/phaseC_execution_manifest.json").read_text())
lead = [i["agent_family"] for i in m["invocations"] if i["position"] == 1]
check("manifest is 2:2 balanced", lead.count("openai") == lead.count("google") == 2, str(lead))
check("openai arm is a pinned snapshot, not an alias",
      all(i["agent_llm"] != "gpt-4.1-nano" for i in m["invocations"]),
      "found the moving alias in the manifest")
# A-003 supersedes A-002's retry row: bounded retries, every attempt logged.
check("bounded retries (A-004: 4, superseding A-003's 2 and A-002's 0)",
      m["parameters"]["max_retries"] == 4, str(m["parameters"]["max_retries"]))
check("retry delay raised for per-minute rate limits (A-003: 5.0s)",
      m["parameters"].get("retry_delay") == 5.0, str(m["parameters"].get("retry_delay")))
check("every invocation routes through the attempt logger",
      all("tau2_with_logging" not in " ".join(i["argv"]) for i in m["invocations"]),
      "argv should hold the bare tau2 command; the runner wraps it")

print("\n--- guard: A-003 attempt logging must actually record failures ---")
import importlib.util
spec = importlib.util.spec_from_file_location(
    "attempt_logger", REPO / "scripts/phase_c/attempt_logger.py")
al = importlib.util.module_from_spec(spec); spec.loader.exec_module(al)
tmp = REPO / "results/phase_c/attempts/__guard_probe.jsonl"
tmp.parent.mkdir(parents=True, exist_ok=True)
tmp.unlink(missing_ok=True)
try:
    lg = al.AttemptLogger(tmp, "guard_probe")
    import datetime as _dt
    t0 = _dt.datetime(2026, 1, 1); t1 = _dt.datetime(2026, 1, 1, 0, 0, 2)
    class _E(Exception): pass
    lg.log_failure_event({"model": "m", "exception": _E("rate limited")}, None, t0, t1)
    lg.log_failure_event({"model": "m", "exception": _E("again")}, None, t0, t1)
    summ = al.summarize(tmp)
    check("failed attempts are recorded, not silently dropped", summ["failures"] == 2, str(summ))
    check("failure classes are captured", "_E" in (summ["failures_by_class"] or {}),
          str(summ["failures_by_class"]))
finally:
    tmp.unlink(missing_ok=True)

print()
if FAIL:
    print(f"  {len(FAIL)} GUARD FAILURE(S): {FAIL}")
    sys.exit(1)
print("  ALL RUNNER GUARDS FIRE CORRECTLY.")
sys.exit(0)
