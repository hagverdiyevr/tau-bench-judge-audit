"""Execute Phase C from the immutable manifest, with logging, resume, and a budget guard.

Addresses external-review finding E3: upstream retries are unpersisted, so without per-invocation
logging the attempt history is unrecoverable after dispatch and cost silently undercounts. A-002
sets --max-retries 0; this runner additionally tees every invocation and records timings.

Guarantees:
  * refuses to run if the pre-registration or amendment chain is broken
  * refuses to run if the manifest's provenance no longer matches the working tree
  * resume-never-restart: an invocation whose artifact already exists is skipped, not repeated
  * pre-dispatch budget check against the regenerated ledger; stops rather than overrunning
  * every invocation's stdout/stderr tee'd to results/phase_c/logs/<save_to>.log

Run:  cd vendor/tau2-bench && uv run python ../../scripts/phase_c/run_phase_c.py --dry-run
      cd vendor/tau2-bench && uv run python ../../scripts/phase_c/run_phase_c.py
"""

import argparse
import datetime
import json
import pathlib
import subprocess
import sys

REPO = pathlib.Path(__file__).resolve().parents[2]
MANIFEST = REPO / "results" / "phaseC_execution_manifest.json"
LEDGER = REPO / "results" / "spend_ledger.json"
LOGDIR = REPO / "results" / "phase_c" / "logs"
JOURNAL = REPO / "results" / "phase_c" / "run_journal.json"
SIMS = REPO / "vendor" / "tau2-bench" / "data" / "simulations"

# Stop dispatching if the ledger's remaining headroom would fall below this after an invocation.
SAFETY_FLOOR_USD = 5.00
# Conservative per-invocation upper bound (40 tasks). Gemini arm measured ~$0.0212/traj.
EST_PER_INVOCATION = {"google": 1.40, "openai": 0.80}

ap = argparse.ArgumentParser()
ap.add_argument("--dry-run", action="store_true", help="validate and print, dispatch nothing")
ap.add_argument("--only", help="run a single save_to (for a smoke test)")
args = ap.parse_args()


def utc():
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def die(msg):
    sys.exit(f"  REFUSING TO RUN — {msg}")


# ---- gate 1: pre-registration and amendment chain intact ---------------------------------
r = subprocess.run([sys.executable, str(REPO / "scripts/verify_preregistration.py")],
                   capture_output=True, text=True)
if r.returncode != 0:
    die("pre-registration or amendment chain failed verification:\n" + r.stdout + r.stderr)
print("  gate 1: pre-registration + amendment chain INTACT")

# ---- gate 2: manifest provenance still matches reality ------------------------------------
m = json.loads(MANIFEST.read_text())
sub = subprocess.run(["git", "rev-parse", "HEAD"], cwd=REPO / "vendor/tau2-bench",
                     capture_output=True, text=True).stdout.strip()
if sub != m["provenance"]["submodule_sha"]:
    die(f"submodule moved: manifest {m['provenance']['submodule_sha'][:12]} vs actual {sub[:12]}")
if not m["design"]["order_balanced"]:
    die("manifest execution order is not balanced (A-002 requires 2:2)")
print(f"  gate 2: provenance OK — submodule {sub[:12]}…, order balanced, "
      f"{m['design']['n_trajectories']} trajectories planned")

todo = m["invocations"]
if args.only:
    todo = [i for i in todo if i["save_to"] == args.only] or die(f"no invocation named {args.only}")

LOGDIR.mkdir(parents=True, exist_ok=True)
journal = json.loads(JOURNAL.read_text()) if JOURNAL.exists() else {"entries": []}
done = {e["save_to"] for e in journal["entries"] if e.get("status") == "completed"}

print(f"\n  planned invocations: {len(todo)}   already completed: {len(done)}")

for inv in todo:
    tag = inv["save_to"]
    artifact = SIMS / tag / "results.json"

    # ---- resume-never-restart -------------------------------------------------------------
    if tag in done or artifact.exists():
        n = len(json.loads(artifact.read_text())["simulations"]) if artifact.exists() else "?"
        print(f"  SKIP {tag}: artifact exists ({n} sims) — resume, never restart")
        continue

    # ---- pre-dispatch budget check --------------------------------------------------------
    led = json.loads(LEDGER.read_text())
    est = EST_PER_INVOCATION[inv["agent_family"]]
    if led["remaining_usd"] - est < SAFETY_FLOOR_USD:
        die(f"budget floor: remaining ${led['remaining_usd']:.2f}, this invocation ~${est:.2f}, "
            f"floor ${SAFETY_FLOOR_USD:.2f}")

    logf = REPO / inv["log_file"]
    print(f"\n  {'DRY-RUN ' if args.dry_run else 'RUN '}{tag}  "
          f"agent={inv['agent_llm']}  seed={inv['seed']}  pos={inv['position']}")
    print(f"    est ${est:.2f} | ledger remaining ${led['remaining_usd']:.2f} | log {logf.name}")
    if args.dry_run:
        print(f"    argv: {' '.join(inv['argv'][:10])} … ({len(inv['argv'])} args, "
              f"{len(m['design']['task_ids'])} task ids)")
        continue

    start = utc()
    with open(logf, "w") as fh:
        fh.write(f"# {tag} started {start}\n# argv: {json.dumps(inv['argv'])}\n\n")
        fh.flush()
        proc = subprocess.run(["uv", "run", "--project", str(REPO / "vendor/tau2-bench"), *inv["argv"]],
                              cwd=REPO, stdout=fh, stderr=subprocess.STDOUT, text=True)
    end = utc()

    log = logf.read_text()
    entry = {
        "save_to": tag, "agent_llm": inv["agent_llm"], "seed": inv["seed"],
        "started_utc": start, "ended_utc": end, "returncode": proc.returncode,
        "status": "completed" if proc.returncode == 0 and artifact.exists() else "failed",
        "simulations": len(json.loads(artifact.read_text())["simulations"]) if artifact.exists() else 0,
        # E3: make attempt history observable even though upstream discards it
        "retry_markers": log.lower().count("succeeded on retry"),
        "permanent_failures": log.lower().count("failed permanently"),
        "log_file": inv["log_file"],
    }
    journal["entries"].append(entry)
    JOURNAL.write_text(json.dumps(journal, indent=1) + "\n")
    print(f"    -> {entry['status']}  sims={entry['simulations']}  "
          f"retries={entry['retry_markers']}  perm_fail={entry['permanent_failures']}")

    if entry["status"] != "completed":
        die(f"{tag} did not complete cleanly (rc={proc.returncode}); see {logf}. "
            f"Resume after diagnosing — do not restart completed work.")

    subprocess.run([sys.executable, str(REPO / "scripts/build_spend_ledger.py")],
                   cwd=REPO / "vendor/tau2-bench", capture_output=True)

if args.dry_run:
    print("\n  DRY RUN — nothing dispatched, no spend.")
else:
    led = json.loads(LEDGER.read_text())
    print(f"\n  done. spend ${led['total_usd']:.4f} of ${led['cap_usd']:.2f} "
          f"(remaining ${led['remaining_usd']:.2f})")
