"""Phase D analysis: the §6.1 primary estimand, §6.2 secondaries, and the §6.3 noise floor.

Computes exactly what PREREGISTRATION §3 defines and nothing more. Everything outside §6.1-§6.2
is printed under an EXPLORATORY heading and carries no inferential statistics, per §6.5.

    FamilyBias = [ S(gpt4.1, openai_agent) - S(gemini, openai_agent) ]
               - [ S(gpt4.1, google_agent) - S(gemini, google_agent) ]

The bracketed control term is mandatory: without it this measures judge LENIENCY, not bias
(D-009). A judge that is uniformly stricter is not a biased judge.

Two rules this file exists to enforce:
  * Bootstrap resamples TASKS, never trajectories. Four trials of one task are not four
    independent observations (§6.1).
  * A null is a claim. If the CI contains zero, §6.5 requires TOST against a 5pp margin and an
    explicit statement of what effect size was ruled out.

Run:  python scripts/phase_d/analyze_phase_d.py
"""

import json
import math
import pathlib
import random
import statistics
import sys

REPO = pathlib.Path(__file__).resolve().parents[2]
JOURNAL = REPO / "results" / "phase_d" / "regrade_journal.jsonl"
MANIFEST = REPO / "results" / "phaseD_regrade_manifest.json"
OUT = REPO / "results" / "phase_d" / "analysis.json"

B = 10_000                  # §6.1 bootstrap replicates
BOOTSTRAP_SEED = 20260922   # stated, so the CI is reproducible
TOST_MARGIN = 0.05          # §6.5: 5 percentage points

OPENAI_JUDGES = {"gpt-4.1-2025-04-14", "gpt-4.1-mini"}
GOOGLE_JUDGES = {"gemini/gemini-3.8-flash", "gemini/gemini-3.1-flash-lite"}
HIGH_TIER = {"gpt-4.1-2025-04-14", "gemini/gemini-3.8-flash"}
INCUMBENT = "gpt-4.1-2025-04-14"
GOOGLE_HIGH = "gemini/gemini-3.8-flash"


def arm(run):
    """phaseC_t3_oai -> openai."""
    return "openai" if run.endswith("_oai") else "google"


rows = [json.loads(x) for x in JOURNAL.read_text().splitlines() if x.strip()]
man = json.loads(MANIFEST.read_text())

settled = [r for r in rows if r.get("settled")]
unsettled = [r for r in rows if not r.get("settled")]
scored = [r for r in settled if r.get("ok") and r.get("nl_reward") is not None]

print("=" * 78)
print("PHASE D — accounting first (§6.4: every attempted unit is accounted for)")
print("=" * 78)
print(f"  planned            : {man['design']['total_evaluations']}")
print(f"  journaled          : {len(rows)}")
print(f"  settled            : {len(settled)}")
print(f"  unsettled (API)    : {len(unsettled)}")
print(f"  scored (parsed OK) : {len(scored)}")
print(f"  withheld (anomaly) : {len(settled) - len(scored)}   reward never granted on a bad parse")
print(f"  spend              : ${sum(r.get('usd') or 0 for r in rows):.4f}")
unpriced = [r for r in rows if r.get("usd_source") == "UNKNOWN"]
if unpriced:
    print(f"  !! UNPRICED        : {len(unpriced)} — total is a LOWER BOUND, not a total")

if len(rows) < man["design"]["total_evaluations"]:
    print("\n  INCOMPLETE — analysis below is provisional. Resume the runner before reporting.")

# ---------------------------------------------------------------- §6.3 noise floor
print("\n" + "=" * 78)
print("§6.3 NOISE FLOOR — same trajectory, same judge, repeated gradings")
print("=" * 78)
reps = {}
for r in scored:
    reps.setdefault((r["run"], r["task"], r["judge"]), []).append(r["nl_reward"])
repeated = {k: v for k, v in reps.items() if len(v) > 1}
flips_by_judge = {}
for (run, task, judge), vals in repeated.items():
    d = flips_by_judge.setdefault(judge, [0, 0])
    d[1] += 1
    if len(set(vals)) > 1:
        d[0] += 1
total_flip, total_pairs = 0, 0
print(f"  {'judge':<32}{'flipped':>8}{'of':>6}{'rate':>9}")
for j in man["design"]["judges"]:
    f, n = flips_by_judge.get(j, [0, 0])
    total_flip += f
    total_pairs += n
    rate = f"{f / n:.3f}" if n else "n/a"
    print(f"  {j:<32}{f:>8}{n:>6}{rate:>9}")
overall = total_flip / total_pairs if total_pairs else None
if overall is not None:
    print(f"  {'OVERALL':<32}{total_flip:>8}{total_pairs:>6}{overall:>9.3f}")
    if total_flip == 0 and total_pairs:
        # Rule of three: 0/n observed -> upper 95% bound is 3/n.
        print(f"\n  Zero flips observed. Rule of three: flip rate < {3 / total_pairs:.3f} "
              f"(95% upper bound). This is a BOUND, not a demonstration of determinism.")
    if overall > 0.09:
        print("\n  !! Flip rate exceeds the 9% bound from B-L13. §6.3 requires the primary estimate "
              "be reported AGAINST this noise floor and the conclusion downgraded to a bounded null.")

# ---------------------------------------------------------------- judge leniency (a main effect)
print("\n" + "=" * 78)
print("JUDGE LENIENCY — mean NL reward per judge (NOT bias; see §3)")
print("=" * 78)
base = [r for r in scored if r["replicate"] == 1]
print(f"  {'judge':<32}{'openai arm':>12}{'google arm':>12}{'overall':>10}{'n':>7}")
for j in man["design"]["judges"]:
    o = [r["nl_reward"] for r in base if r["judge"] == j and arm(r["run"]) == "openai"]
    g = [r["nl_reward"] for r in base if r["judge"] == j and arm(r["run"]) == "google"]
    allv = o + g
    if not allv:
        continue
    print(f"  {j:<32}{statistics.mean(o) if o else float('nan'):>12.3f}"
          f"{statistics.mean(g) if g else float('nan'):>12.3f}"
          f"{statistics.mean(allv):>10.3f}{len(allv):>7}")

# ---------------------------------------------------------------- §6.1 primary
print("\n" + "=" * 78)
print("§6.1 PRIMARY — FamilyBias (difference-in-differences), task-clustered")
print("=" * 78)


def per_task(judge_o, judge_g):
    """Per-task DiD: (O_agent scored by OpenAI judge - by Google judge) minus the same for G_agent.

    Returns {task: did}. A task contributes only when all four cells are present, because the
    estimand is a contrast of contrasts -- a partially observed task cannot supply one.
    """
    cell = {}
    for r in base:
        cell.setdefault(r["task"], {})[(arm(r["run"]), r["judge"])] = \
            cell.setdefault(r["task"], {}).get((arm(r["run"]), r["judge"]), []) + [r["nl_reward"]]
    out, dropped = {}, []
    for task, c in cell.items():
        need = [("openai", judge_o), ("openai", judge_g), ("google", judge_o), ("google", judge_g)]
        if not all(c.get(k) for k in need):
            dropped.append(task)
            continue
        mean = {k: statistics.mean(c[k]) for k in need}
        out[task] = ((mean[("openai", judge_o)] - mean[("openai", judge_g)])
                     - (mean[("google", judge_o)] - mean[("google", judge_g)]))
    return out, dropped


def cluster_bootstrap(vals_by_task, b=B, seed=BOOTSTRAP_SEED):
    """Resample TASKS with replacement, carrying all trials of a task together (§6.1)."""
    tasks = list(vals_by_task)
    if not tasks:
        return None, None, None
    rng = random.Random(seed)
    point = statistics.mean(vals_by_task[t] for t in tasks)
    draws = []
    for _ in range(b):
        pick = [vals_by_task[tasks[rng.randrange(len(tasks))]] for _ in tasks]
        draws.append(sum(pick) / len(pick))
    draws.sort()
    return point, draws[int(0.025 * b)], draws[int(0.975 * b)]


did, dropped = per_task(INCUMBENT, GOOGLE_HIGH)
print(f"  contrast   : [{INCUMBENT} - {GOOGLE_HIGH}]")
print(f"  tasks used : {len(did)}" + (f"   dropped (incomplete cells): {sorted(dropped, key=int)}"
                                      if dropped else ""))
if did:
    point, lo, hi = cluster_bootstrap(did)
    print(f"\n  FamilyBias = {point:+.4f}   95% CI [{lo:+.4f}, {hi:+.4f}]   "
          f"(cluster bootstrap, B={B}, tasks resampled)")
    sd = statistics.pstdev(list(did.values()))
    mde = 2.8 * sd / math.sqrt(len(did)) if len(did) > 1 else float("nan")
    print(f"  between-task SD = {sd:.4f}   realized MDE (80% power, two-sided 0.05) ≈ {mde:.4f}")
    if lo <= 0 <= hi:
        # §6.5: a null is a claim and must be defended, not merely observed.
        inside = lo > -TOST_MARGIN and hi < TOST_MARGIN
        print(f"\n  The CI contains zero -> this is a NULL CLAIM (§6.5).")
        verdict = ("EQUIVALENT — effects beyond ±5pp are ruled out" if inside
                   else "NOT equivalent — the data cannot rule out an effect of practical size")
        print(f"  TOST against ±{TOST_MARGIN:.2f}: {verdict}")
        print(f"  Ruled out: |FamilyBias| > {max(abs(lo), abs(hi)):.4f}")
    else:
        sign = "POSITIVE (favours H1)" if point > 0 else "NEGATIVE (against H1)"
        print(f"\n  CI excludes zero -> directional effect, sign {sign}")
    print("\n  Interpretation constraint, mandatory (C-L3): the OpenAI arm is FLOOR-BOUND "
          "(pass^1 0.138 vs 0.675).\n  Capability is confounded with family; no interaction may "
          "be attributed to family alone without\n  stating this.")

# ---------------------------------------------------------------- §6.2 secondaries
print("\n" + "=" * 78)
print("§6.2 SECONDARY")
print("=" * 78)
print("  S1 — tier control: a genuine family effect must appear in BOTH tiers")
for tier, jo, jg in (("high", "gpt-4.1-2025-04-14", "gemini/gemini-3.8-flash"),
                     ("low", "gpt-4.1-mini", "gemini/gemini-3.1-flash-lite")):
    dd, _ = per_task(jo, jg)
    if dd:
        p, lo2, hi2 = cluster_bootstrap(dd)
        print(f"    {tier:<5} {p:+.4f}  95% CI [{lo2:+.4f}, {hi2:+.4f}]  (n={len(dd)} tasks)")

print("\n  S2 — capability contrast: high vs low tier WITHIN each family")
for fam, hi_j, lo_j in (("openai", "gpt-4.1-2025-04-14", "gpt-4.1-mini"),
                        ("google", "gemini/gemini-3.8-flash", "gemini/gemini-3.1-flash-lite")):
    h = [r["nl_reward"] for r in base if r["judge"] == hi_j]
    lw = [r["nl_reward"] for r in base if r["judge"] == lo_j]
    if h and lw:
        print(f"    {fam:<7} high {statistics.mean(h):.3f}  low {statistics.mean(lw):.3f}  "
              f"delta {statistics.mean(h) - statistics.mean(lw):+.3f}")

print("\n  S3 — incumbent agreement: does a re-grade reproduce the score tau2 recorded?")
for j in man["design"]["judges"]:
    v = [r for r in base if r["judge"] == j and r.get("matches_incumbent") is not None]
    if v:
        ag = sum(1 for r in v if r["matches_incumbent"])
        print(f"    {j:<32}{ag:>5}/{len(v):<5} ({ag / len(v):.3f})")

# ---------------------------------------------------------------- exploratory (§6.5)
print("\n" + "=" * 78)
print("EXPLORATORY — no inferential statistics (§6.5)")
print("=" * 78)
fenced = {}
for r in settled:
    if r.get("fenced"):
        fenced[r["judge"]] = fenced.get(r["judge"], 0) + 1
tot = {}
for r in settled:
    tot[r["judge"]] = tot.get(r["judge"], 0) + 1
print("  fenced JSON responses (each would crash upstream's raw json.loads — B-L16 J1):")
for j in man["design"]["judges"]:
    print(f"    {j:<32}{fenced.get(j, 0):>5}/{tot.get(j, 0):<5}")
models = {}
for r in settled:
    models.setdefault(r["judge"], set()).add(r.get("model_returned"))
print("\n  alias resolution (what the provider actually returned):")
for j, v in models.items():
    flag = "  <-- MORE THAN ONE SNAPSHOT SERVED" if len(v) > 1 else ""
    print(f"    {j:<32}{sorted(x for x in v if x)}{flag}")

OUT.parent.mkdir(parents=True, exist_ok=True)
OUT.write_text(json.dumps({
    "planned": man["design"]["total_evaluations"], "journaled": len(rows),
    "settled": len(settled), "unsettled": len(unsettled), "scored": len(scored),
    "usd": round(sum(r.get("usd") or 0 for r in rows), 6),
    "noise_floor": {"flipped": total_flip, "pairs": total_pairs, "rate": overall},
    "family_bias": ({"point": point, "ci_low": lo, "ci_high": hi, "n_tasks": len(did),
                     "between_task_sd": sd, "realized_mde": mde} if did else None),
}, indent=1) + "\n")
print(f"\n  wrote {OUT.relative_to(REPO)}")
sys.exit(0)
