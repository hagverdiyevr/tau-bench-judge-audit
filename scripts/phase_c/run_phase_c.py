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

Run:  cd vendor/tau2-bench && uv run --frozen python ../../scripts/phase_c/run_phase_c.py --dry-run
      cd vendor/tau2-bench && uv run --frozen python ../../scripts/phase_c/run_phase_c.py
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

    # ---- resume-never-restart, but only for a VALID artifact ------------------------------
    # An artifact's mere existence is not evidence of completion. A killed run leaves a
    # truncated results.json behind, and an earlier version of this check skipped such a file
    # as "done" — phaseC_t2_oai was accepted with 21/40 sims and 7 infrastructure errors, no
    # journal entry and no attempt log. Completion is now proven, not assumed.
    if artifact.exists():
        try:
            asims = json.loads(artifact.read_text())["simulations"]
        except Exception:
            asims = []
        n_expected = m["design"]["n_tasks"]
        ainfra = [str(x.get("task_id")) for x in asims
                  if x.get("termination_reason") == "infrastructure_error"]
        journaled = tag in done
        valid = journaled and len(asims) == n_expected and not ainfra
        if valid:
            print(f"  SKIP {tag}: complete ({len(asims)}/{n_expected} sims, 0 infra, journaled)")
            continue
        why = []
        if not journaled:
            why.append("no completed journal entry (likely a killed run)")
        if len(asims) != n_expected:
            why.append(f"{len(asims)}/{n_expected} simulations")
        if ainfra:
            why.append(f"{len(ainfra)} infrastructure_error (tasks {ainfra[:5]})")
        die(f"{tag} has an INVALID artifact — {'; '.join(why)}. "
            f"Refusing to treat it as complete and refusing to silently overwrite it. "
            f"Archive it to results/discarded/ and remove "
            f"{artifact.parent.relative_to(REPO)} to re-run.")

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
    attempts = REPO / "results/phase_c/attempts" / f"{tag}.jsonl"
    attempts.parent.mkdir(parents=True, exist_ok=True)
    # A-003: delegate via tau2_with_logging.py so litellm.callbacks is live in the SAME
    # interpreter that issues the requests (D-007). A plain subprocess(["tau2", ...]) cannot
    # see them, which is why retried/rate-limited attempts were previously invisible.
    # --frozen: plain `uv run` rewrites upstream's stale uv.lock, modifying the submodule (R-L11).
    cmd = ["uv", "run", "--frozen", "--project", str(REPO / "vendor/tau2-bench"),
           "python", str(REPO / "scripts/phase_c/tau2_with_logging.py"),
           "--attempt-log", str(attempts), "--invocation", tag, "--", *inv["argv"]]
    with open(logf, "w") as fh:
        fh.write(f"# {tag} started {start}\n# argv: {json.dumps(inv['argv'])}\n\n")
        fh.flush()
        proc = subprocess.run(cmd, cwd=REPO / "vendor/tau2-bench",
                              stdout=fh, stderr=subprocess.STDOUT, text=True)
    end = utc()

    # A-003: an invocation is complete only if NO simulation died of infrastructure_error.
    # phaseC_t1_oai was previously marked "completed" with 6 such failures because only the
    # process exit code was checked.
    sims, infra, infra_ids = [], 0, []
    if artifact.exists():
        sims = json.loads(artifact.read_text())["simulations"]
        infra_ids = [str(x.get("task_id")) for x in sims
                     if x.get("termination_reason") == "infrastructure_error"]
        infra = len(infra_ids)
    sys.path.insert(0, str(REPO / "scripts/phase_c"))
    import attempt_logger as _al
    summary = _al.summarize(attempts)

    if proc.returncode != 0 or not artifact.exists():
        status = "failed"
    elif infra > 0:
        status = "degraded"
    else:
        status = "completed"

    entry = {
        "save_to": tag, "agent_llm": inv["agent_llm"], "seed": inv["seed"],
        "started_utc": start, "ended_utc": end, "returncode": proc.returncode,
        "status": status,
        "simulations": len(sims),
        "infrastructure_errors": infra,
        "infrastructure_error_task_ids": infra_ids,
        "attempts": summary.get("attempts"),
        "attempt_failures": summary.get("failures"),
        "attempt_failures_by_class": summary.get("failures_by_class"),
        "usd_from_attempts": summary.get("usd_from_attempts"),
        "attempt_log": str(attempts.relative_to(REPO)),
        "log_file": inv["log_file"],
    }
    journal["entries"].append(entry)
    JOURNAL.write_text(json.dumps(journal, indent=1) + "\n")
    print(f"    -> {entry['status']}  sims={entry['simulations']}  "
          f"infra_errors={infra}  attempts={entry['attempts']} "
          f"(failed {entry['attempt_failures']} {entry['attempt_failures_by_class']})  "
          f"true_usd=${(entry['usd_from_attempts'] or 0):.4f}")

    if status == "degraded":
        die(f"{tag} is DEGRADED: {infra}/{len(sims)} simulations died of infrastructure_error "
            f"(tasks {infra_ids}). Under A-003 this is not a completed invocation. "
            f"Diagnose from {entry['attempt_log']} — if it is rate limiting, lower "
            f"--max-concurrency or raise --retry-delay, delete the artifact, and re-run.")
    if status == "failed":
        die(f"{tag} did not complete (rc={proc.returncode}); see {logf}. "
            f"Resume after diagnosing — do not restart completed work.")

    subprocess.run([sys.executable, str(REPO / "scripts/build_spend_ledger.py")],
                   cwd=REPO / "vendor/tau2-bench", capture_output=True)

if args.dry_run:
    print("\n  DRY RUN — nothing dispatched, no spend.")
else:
    led = json.loads(LEDGER.read_text())
    print(f"\n  done. spend ${led['total_usd']:.4f} of ${led['cap_usd']:.2f} "
          f"(remaining ${led['remaining_usd']:.2f})")
