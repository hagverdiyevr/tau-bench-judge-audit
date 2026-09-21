"""Build the immutable Phase C execution manifest.

Everything needed to reproduce the confirmatory run exactly, generated from a committed script
rather than an ad-hoc command, and content-hashed so it cannot drift silently.

Satisfies PREREGISTRATION §5.2 (pre-drawn seeded permutation, published before execution) and
AMENDMENTS A-002 (balanced order, pinned snapshot, recorded retry/timeout/limits).

Run:  python scripts/phase_c/build_manifest.py
"""

import datetime
import hashlib
import json
import pathlib
import random
import subprocess
import sys

REPO = pathlib.Path(__file__).resolve().parents[2]
OUT = REPO / "results" / "phaseC_execution_manifest.json"

# --- frozen identities (PREREGISTRATION §4.2, as pinned by AMENDMENT A-002) ---------------
AGENTS = {
    "openai": "gpt-4.1-nano-2025-04-14",          # A-002: explicit snapshot, not the alias
    "google": "gemini/gemini-3.1-flash-lite",
}
SIMULATOR = "gemini/gemini-3.1-flash-lite"        # fixed, not a factor (§4.2)
PERMUTATION_SEED = 20260920                       # stated, fixed, pre-drawn
TRIALS = (1, 2, 3, 4)                             # seeds 1000+trial (§4.5)

# --- operational parameters (A-002) --------------------------------------------------------
MAX_STEPS = 120          # §4.5
MAX_CONCURRENCY = 2      # §4.5
MAX_RETRIES = 4          # A-004: 200k TPM ceiling; requested waits are 46ms-1.4s so the tail needs 5 attempts
RETRY_DELAY = 5.0        # A-003: 1.0s default is far too short for a per-minute rate limit
MAX_ERRORS = 10          # upstream default, recorded explicitly
TEMPERATURE = 0.0        # §4.5, both roles


def git(*args, cwd=REPO):
    return subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True).stdout.strip()


# --- task set: derived from shipped data, never hardcoded (D-004) --------------------------
cls = {r["id"]: r for r in json.loads((REPO / "results/phase_a/task_class.json").read_text())}
split = json.loads((REPO / "vendor/tau2-bench/data/tau2/domains/retail/split_tasks.json").read_text())
base = {str(i) for i in split["base"]}
tasks = sorted([t for t, c in cls.items() if t in base and c["nl"] > 0], key=int)
if len(tasks) != 40:
    sys.exit(f"expected 40 judge-gated base tasks, got {len(tasks)} — refusing to build")

# --- balanced 2:2 order (A-002) ------------------------------------------------------------
# Two trials lead with OpenAI, two with Google, assigned by the stated seed.
orders = [("openai", "google")] * 2 + [("google", "openai")] * 2
random.Random(PERMUTATION_SEED).shuffle(orders)

invocations = []
for trial, order in zip(TRIALS, orders):
    for pos, fam in enumerate(order, 1):
        tag = "oai" if fam == "openai" else "gem"
        save_to = f"phaseC_t{trial}_{tag}"
        invocations.append({
            "trial": trial, "seed": 1000 + trial, "position": pos,
            "agent_family": fam, "agent_llm": AGENTS[fam], "user_llm": SIMULATOR,
            "save_to": save_to,
            "log_file": f"results/phase_c/logs/{save_to}.log",
            "argv": [
                "tau2", "run",
                "--domain", "retail",
                "--agent-llm", AGENTS[fam],
                "--user-llm", SIMULATOR,
                "--agent-llm-args", json.dumps({"temperature": TEMPERATURE}),
                "--user-llm-args", json.dumps({"temperature": TEMPERATURE}),
                "--num-trials", "1",
                "--task-ids", *tasks,
                "--max-concurrency", str(MAX_CONCURRENCY),
                "--max-steps", str(MAX_STEPS),
                "--max-errors", str(MAX_ERRORS),
                "--max-retries", str(MAX_RETRIES),
                "--retry-delay", str(RETRY_DELAY),
                "--seed", str(1000 + trial),
                "--save-to", save_to,
            ],
        })

lead = [i["agent_family"] for i in invocations if i["position"] == 1]
manifest = {
    "schema": "phaseC-execution-manifest/1",
    "generated_by": "scripts/phase_c/build_manifest.py",
    "generated_utc": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    "preregistration": {
        "sections": ["4.2", "4.3", "4.5", "5.1", "5.2"],
        "frozen_sha256": json.loads((REPO / "results/preregistration.sha256").read_text())["sha256"],
        "amendments": [e["id"] for e in
                       json.loads((REPO / "results/preregistration_chain.json").read_text())["chain"]],
    },
    "provenance": {
        "superproject_head": git("rev-parse", "HEAD"),
        "superproject_dirty": bool(git("status", "--porcelain")),
        "submodule_sha": git("rev-parse", "HEAD", cwd=REPO / "vendor/tau2-bench"),
        "submodule_describe": git("describe", "--tags", cwd=REPO / "vendor/tau2-bench"),
        "python": sys.version.split()[0],
    },
    "parameters": {
        "temperature_agent": TEMPERATURE, "temperature_user": TEMPERATURE,
        "max_steps": MAX_STEPS, "max_concurrency": MAX_CONCURRENCY,
        "max_retries": MAX_RETRIES, "retry_delay": RETRY_DELAY,
        "max_errors": MAX_ERRORS, "timeout": None,
        "max_output_tokens": None,
        "simulator": SIMULATOR,
        "retry_rationale": "A-003 supersedes A-002. Zero retries turned transient provider rate "
                           "limits into permanent agent failures (18 RateLimitError -> 6/40 dead "
                           "simulations on phaseC_t1_oai), biasing the arm by our configuration. "
                           "Bounded retries restore transient calls; every attempt is recorded "
                           "independently of tau2 by scripts/phase_c/attempt_logger.py. A-004 raised "
                           "retries 2->4 after the attempt log identified a 200k TPM org ceiling "
                           "with sub-2s requested waits.",
    },
    "design": {
        "n_tasks": len(tasks), "n_agents": len(AGENTS), "n_trials": len(TRIALS),
        "n_trajectories": len(tasks) * len(AGENTS) * len(TRIALS),
        "permutation_seed": PERMUTATION_SEED,
        "lead_agent_by_trial": lead,
        "order_balanced": lead.count("openai") == lead.count("google"),
        "task_ids": tasks,
        "task_id_sha256": hashlib.sha256(",".join(tasks).encode()).hexdigest(),
    },
    "invocations": invocations,
}

body = json.dumps(manifest, indent=1, sort_keys=True)
manifest["manifest_sha256"] = hashlib.sha256(body.encode()).hexdigest()
OUT.write_text(json.dumps(manifest, indent=1, sort_keys=True) + "\n")

print(f"  tasks            : {len(tasks)}  (sha {manifest['design']['task_id_sha256'][:12]}…)")
print(f"  trajectories     : {manifest['design']['n_trajectories']}")
print(f"  lead by trial    : {lead}  -> balanced={manifest['design']['order_balanced']}")
print(f"  openai agent     : {AGENTS['openai']}   (snapshot, not alias)")
print(f"  max_retries      : {MAX_RETRIES}")
print(f"  superproject     : {manifest['provenance']['superproject_head'][:12]}…"
      f"  dirty={manifest['provenance']['superproject_dirty']}")
print(f"  submodule        : {manifest['provenance']['submodule_sha'][:12]}…"
      f" ({manifest['provenance']['submodule_describe']})")
print(f"  manifest sha256  : {manifest['manifest_sha256'][:16]}…")
print(f"\n  wrote {OUT.relative_to(REPO)}")
