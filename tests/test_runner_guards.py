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
AMEND.write_text(bak.replace("high tier)", "HIGH TIER)", 1))
r = run(["--dry-run"])
check("refuses on tampered amendment", r.returncode != 0 and "REFUSING TO RUN" in r.stdout + r.stderr,
      f"rc={r.returncode}")
AMEND.write_text(bak)
r = run(["--dry-run"])
check("proceeds again once restored", r.returncode == 0, f"rc={r.returncode}")

print("\n--- guard: budget floor must block dispatch ---")
led = json.loads(LEDGER.read_text())
LEDGER.write_text(json.dumps({**led, "remaining_usd": 5.50}, indent=1))
r = run()
check("refuses when remaining would breach the floor",
      r.returncode != 0 and "budget floor" in r.stdout + r.stderr, f"rc={r.returncode}")
LEDGER.write_text(json.dumps(led, indent=1))

print("\n--- guard: resume-never-restart must skip an existing artifact ---")
tgt = SIMS / "phaseC_t1_gem"
created = not tgt.exists()
tgt.mkdir(parents=True, exist_ok=True)
(tgt / "results.json").write_text(json.dumps({"simulations": [{"task_id": "x"}]}))
r = run(["--dry-run"])
check("skips the completed invocation", "SKIP phaseC_t1_gem" in r.stdout,
      "did not skip an existing artifact")
if created:
    shutil.rmtree(tgt)

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
check("retries disabled (A-002)", m["parameters"]["max_retries"] == 0,
      str(m["parameters"]["max_retries"]))

print()
if FAIL:
    print(f"  {len(FAIL)} GUARD FAILURE(S): {FAIL}")
    sys.exit(1)
print("  ALL RUNNER GUARDS FIRE CORRECTLY.")
sys.exit(0)
