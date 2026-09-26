# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Start here

This project keeps its memory in six connected documents. **Read [docs/STATUS.md](docs/STATUS.md)
first** — it says where the work stands, the next executable task, and what is blocking it.

| File | What it holds | When to update it |
| --- | --- | --- |
| **[docs/STATUS.md](docs/STATUS.md)** | Current phase, spend to date, next task, blockers | **Every session** |
| **[docs/PLAN.md](docs/PLAN.md)** | Active plan: thesis, design, phases, measured budget | When direction changes |
| **[docs/PREREGISTRATION.md](docs/PREREGISTRATION.md)** | Frozen hypothesis, design, analysis plan | **Immutable once frozen** — deviations append to §10 |
| **[docs/FINDINGS.md](docs/FINDINGS.md)** | Evidence **we measured**, with method and numbers | Append when a phase produces results |
| **[docs/DECISIONS.md](docs/DECISIONS.md)** | Why we chose X over Y, including killed theses | Append at every fork |
| **[docs/REFERENCE.md](docs/REFERENCE.md)** | Facts **others established**: upstream API, pricing, prior art | When re-verified |

Two distinctions that keep this system honest:

- **FINDINGS is what we measured; REFERENCE is what we looked up.** Never mix them — the first is
  the contribution, the second is background that can go stale.
- **FINDINGS and DECISIONS are append-only.** Supersede an entry; never rewrite one.

`RETAIL_AGENT_IMPLEMENTATION_PLAN.md` is the original v1.0 spec, carrying a SUPERSEDED banner: its
*scope* is obsolete, its *operating rules* remain binding.

## Current state

**All phases (A–E) complete. USD 13.76 spent of 75.00; USD 61.24 remaining.**
Every mechanism the study depends on is verified. The pre-registration is **frozen**
(`a917984e…`, 2026-09-20T10:54:29Z). **320 confirmatory trajectories and 1,792 judge evaluations
exist**, both with zero infrastructure errors.

**Post-release review (26–27 Sep).** Three replies to our public posts prompted a claim-by-claim
re-check of all 12. **7 of 12 need a correction; no reported bug turned out not to exist.** The
corrections are recorded in FINDINGS [R-L1–R-L12](docs/FINDINGS.md) and **not yet posted** — each
public correction needs its own go-ahead.

Spend is tracked in `results/spend_ledger.json`, regenerated from run artifacts — never by hand.

Upstream is checked out at `vendor/tau2-bench`, pinned to **v1.0.1**
(`fc0055dc4e0a316c3f83133267fbd6faaa770992`), MIT, with a working venv on Python 3.12.9.
Both `GEMINI_API_KEY` and `OPENAI_API_KEY` are live in a gitignored `.env`.

## What is being built

**Research question:** τ³-retail's reward is gated on 40 of 114 tasks by an LLM judge hardcoded to
`gpt-4.1-2025-04-14`. **Does that judge favour agents from its own model family?**

**Answer (Phase D, 1,792 evaluations):** no detectable effect — `FamilyBias = +0.0063`,
95% CI `[-0.0875, +0.1062]`. This is an **underpowered null, not equivalence**: realized MDE is
**0.1367**, TOST against ±5pp does not clear, and the OpenAI arm is floor-bound so capability is
confounded with family. **Never state it as "the judge is unbiased"** — [D-021](docs/DECISIONS.md)
forbids it and `scripts/check_docs.py` fails the build on that phrasing.
The durable results are the three positives: a **9.1-point judge-leniency spread**
([D-L2](docs/FINDINGS.md)), a **100% fence-crash rate** ([D-L3](docs/FINDINGS.md)), and the
official grader's **own irreproducibility** — one flip in 256 on identical requests, a floor that
is not zero, **not** an asymmetry ([D-L5](docs/FINDINGS.md), qualified by [R-L8](docs/FINDINGS.md)).

**Method:** generate each trajectory once, then re-grade the *same saved trajectory* under four
judges (2 families × 2 capability tiers). The contrast is within-trajectory and paired, so it costs
one short LLM call and carries no capability confound. The estimand is a
**difference-in-differences** — a naive contrast measures judge leniency, not bias.

The deliverable is a **reusable tool plus one sharp finding**, not a report.
See [docs/PLAN.md](docs/PLAN.md) and [docs/PREREGISTRATION.md](docs/PREREGISTRATION.md).

## Facts that prevent expensive mistakes

All measured and cited. Do not re-derive or contradict without new evidence.

**Environment**
- **Python 3.12.9 only.** `tau2` v1.0.1 declares `<3.14` but **cannot be imported on 3.13**
  (`audioop`, PEP 594). [A0](docs/FINDINGS.md)
- **Never rely on bare `python3`.** Three are installed — Anaconda 3.13.5, Homebrew 3.14.6, system
  3.9.6 — and which one wins depends on which shell startup files load; this project has recorded all
  three as "the default". **Every gate step runs on the pinned venv,
  `vendor/tau2-bench/.venv/bin/python` (3.12.9)**; create it with `make setup`. Repo scripts give
  identical results on 3.9, 3.13 and 3.14 (verified), but nothing guarantees that. [R-L10](docs/FINDINGS.md)
- **Never run plain `uv run`.** It rewrites upstream's stale `uv.lock` and so modifies the submodule —
  `make verify` did this on every run until 27 Sep. Use `uv run --frozen`, or the venv's Python
  directly. `make pristine` fails the gate if upstream is touched. [R-L11](docs/FINDINGS.md)

**Scoring**
- **Retail reward is `DB × NL_ASSERTION`, not `DB × COMMUNICATE`.** `COMMUNICATE` appears in the
  `reward_basis` of **zero** retail tasks; `[DB, COMMUNICATE]` is only the schema default.
  `communicate_info` is populated on 36 tasks and scored on none. [A1](docs/FINDINGS.md)
- **74 of 114 tasks are effectively DB-only**; only 40 have a live judge, and just 11 of those are
  in `test` — judge work must use `base`. [A3](docs/FINDINGS.md)
- **Judge-gated tasks are much harder**: 0.400 vs 0.857 on DB-only. Never pool the two regimes into
  one headline number. [B-L11](docs/FINDINGS.md)
- **DB and the judge are partially independent instruments**, combined multiplicatively. The judge
  catches failures DB cannot see, and misses failures DB catches. [B-L12](docs/FINDINGS.md)

**The judge**
- **Patch target is `tau2.evaluator.evaluator_nl_assertions.DEFAULT_LLM_NL_ASSERTIONS`.** Patching
  `tau2.config` is a **silent no-op** — no error, no effect. Verified both directions. [B1](docs/FINDINGS.md)
- **The judge cannot see tool calls.** It receives `f"{role}: {content}"`, and `content` is `None` on
  a tool-calling turn, so names and arguments are dropped. It grades narration plus tool results,
  with literal `"assistant: None"` lines — at n=320, **19.9% of all lines**, 0–15 per trajectory
  (median 5). Filed as #553. [B4](docs/FINDINGS.md)
- **Judge temperature is 0.0** and self-consistency measured 11/11; flip rate bounded **<9%**
  (0/33, rule of three). Not zero — a bound. Phase D then measured **1 flip in 256**, on the default
  judge only. One flip is a floor, not a pattern. [B-L13](docs/FINDINGS.md), [R-L8](docs/FINDINGS.md)
- **tau2 does not account for judge cost at all.** Measured, the judge is **32.8%** of true cost on
  judge-gated tasks — **20% vs 58%** by agent arm, so cross-model cost comparisons are biased, not
  just low. (An earlier figure near 40% was an estimate assuming 300 output tokens; the real mean is
  148.) Our ledger must add it. [B-L14](docs/FINDINGS.md), [R-L4](docs/FINDINGS.md)

**Reproducibility — the two arms differ, verified at n=40**
- **At temperature 0, `gemini-3.1-flash-lite` is deterministic and `gpt-4.1-nano` is not.**
  Replicated across **four** repeat invocations over **all 40** tasks: Gemini identical on message
  contents 40/40, tool calls 40/40, **rewards 40/40**; OpenAI 0/40, 4/40, 32/40. Whole-object
  identity is 0/40 for both — ids and timestamps always differ, so **never say "byte-identical"**.
  LiteLLM **drops `seed` for the gemini provider**, so these are repeat invocations, not seeded
  replicates. [C-L2](docs/FINDINGS.md), superseding the 5-task pilot in [B-L15](docs/FINDINGS.md)
- **`pass^k` is not comparable across these arms.** Gemini `pass^4` = `pass^1` = 0.675 **by
  construction**; OpenAI varied on 8/40 tasks giving a real 8.8pp drop (0.138 → 0.050). Report the
  Gemini figure as a determinism result, never as reliability, and state the asymmetry before any
  cross-arm variance statistic. [D-018](docs/DECISIONS.md)
- **The OpenAI arm is floor-bound**: pass^1 **0.138** vs Gemini's **0.675** — a 54-point gap against
  a 50–70% target. Phase D still has signal (NL 0.362; components disagree on 35% of that arm), but
  **capability is confounded with family** and no interaction may be attributed to family without
  stating this. [C-L3](docs/FINDINGS.md)

**Spend accounting — trust the attempt log, not tau2**
- **Every API attempt is recorded** by `scripts/phase_c/attempt_logger.py`, a LiteLLM callback at
  the one shared request boundary. It captures failures and the judge calls tau2 records nowhere.
  `scripts/build_spend_ledger.py` prefers these **measured** totals over estimates. [A-003](docs/PREREGISTRATION_AMENDMENTS.md)
- **LiteLLM retries NOTHING by default.** `litellm.num_retries` is `None` and `completion()` has
  no `num_retries` default — verified in the pinned venv. Any direct `completion()` call must pass
  it explicitly. In a **paired** design an unretried rate limit does not cost one observation, it
  **unpairs the trajectory**, and it does so preferentially on the longest requests, i.e. the
  hardest tasks. [A-005](docs/PREREGISTRATION_AMENDMENTS.md)
- **OpenAI org limit is 200,000 TPM.** One 40-task invocation pushes ~3.1M tokens through
  `gpt-4.1-nano`, so the ceiling is hit by construction; requested waits are 46ms–1.4s. Retries are
  set to **4** and absorb it — 101 rate-limit failures across Phase C, **zero** reaching results.
  [A-004](docs/PREREGISTRATION_AMENDMENTS.md)

**Inferring success from a weak proxy — three defects, same shape**
Each of these silently corrupted or nearly corrupted real data, and each is now a test that proves
the property instead of assuming it:
- A test wrote a stub to a **real artifact path** and cleaned up only `if created` → destroyed 40
  paid simulations. Tests now write only to a reserved probe name and clean up in `finally`.
- An invocation was marked `completed` on **exit code alone** while 6/40 simulations were dead.
  Completion now requires **zero `infrastructure_error`**.
- Resume skipped any invocation whose artifact merely **existed**, accepting a 21/40 truncated file
  from a killed run. Resume now requires a journal entry **and** the full simulation count **and**
  zero infra errors.

**The same shape in our own prose.** The post-release review found 7 of our 12 public posts with a
claim that went further than the repro under it: a co-occurrence read as a cause (67/68), "one write
failed" read as "nothing changed" (task 64), an estimate reported as a measurement (~40% judge cost),
a single flip read as a pattern, a 40-trajectory subset labelled as the whole arm. Every repro had
been run; the sentences around them had not been checked against them. **Check each sentence
against its evidence, not just the evidence.** [post-release review](docs/FINDINGS.md)

**Known defects — document, do not patch**
- **#514**: DB hash is order-sensitive on lists. [D-011](docs/DECISIONS.md)
- **B-L7**: the ACTION checker is order-sensitive on list arguments — a call identical to gold except
  list order scores `action_match: false`. [D-017](docs/DECISIONS.md) **`ACTION` is scored on zero
  retail tasks**, and no task that scores it compares a reorderable list — so this changes **no
  shipped score anywhere**; it is latent, and only mis-reports `action_match` diagnostics ([R-L14](docs/FINDINGS.md)). And
  `compare_args: []` is deliberate — all 56 are human hand-offs whose free-text `summary` is not
  graded. [R-L5](docs/FINDINGS.md)
- Fixing #514 breaks comparability with official v1.0.1 numbers — compute both variants, report both.
  Fixing B-L7 changes no shipped score ([R-L14](docs/FINDINGS.md)); it stays unpatched only under D-007.
- **`get_response_cost()` returns `0.0` on exception** — an unpriced model reports as free.
- **litellm#25322**: Gemini thought signatures survive tau2's path **only** because LiteLLM packs
  them into the tool-call `id`, which tau2 preserves. `ToolCall` cannot carry
  `provider_specific_fields`. A transport change would lose the signature — whether that fails
  silently or with an error is **untested**. [B-L6](docs/FINDINGS.md), [R-L15](docs/FINDINGS.md)

**Method**
- **Verify against shipped data, not documentation.** Reading the schema default instead of the task
  files killed an entire thesis. Three independent research passes repeated the same error.
  [D-004](docs/DECISIONS.md)
- **A model listing is not availability.** The models endpoint advertises models the account cannot
  call. Confirm with a real call. [B-L1](docs/FINDINGS.md)

## Non-negotiable operating rules

Inherited from v1.0 §1 and still binding:

- **USD 75 cumulative cap**, authorised 19 Sep 2026 — do not re-request it. Enforce with
  pre-dispatch accounting; agent, simulator, **judge**, and all retries draw on one allowance.
  Unknown pricing or missing usage is **never** zero. A timed-out request may still have cost.
- **Upstream stays byte-untouched.** It is a pinned, read-only checkout; our code registers from
  outside. "The baseline is stock" must be provable, not audited. [D-007](docs/DECISIONS.md)
  **Enforced:** `make verify` ends with `make pristine`, which fails unless upstream is at the pinned
  commit with no modified files. [D-023](docs/DECISIONS.md)
- **Never leak evaluation state into the agent.** `HalfDuplexAgent.__init__(tools, domain_policy)`
  enforces this architecturally — do not weaken it.
- **Pre-registration is frozen before Phase C.** Anything outside it is exploratory and reported
  without inferential statistics. [D-012](docs/DECISIONS.md)
- **Pin and hold.** No dependency or commit bumps mid-comparison.
- **Never present mocked output as a real model result.** If credentials are missing, finish the
  offline work and report the exact remaining setup action.
- **Negative results are retained.** No score, savings, production-impact or hiring claim without a
  linked run artifact. A well-specified null with a stated MDE is a valid outcome.
- **The repo is public** at [hagverdiyevr/tau-bench-judge-audit](https://github.com/hagverdiyevr/tau-bench-judge-audit) (since 27 Sep). **`git push`
  publishes** — commit locally as usual, but push only when the owner asks.
- **Commit only as the personal address.** This repo's local `user.email` is
  `hagverdiyev.r.99@gmail.com`. The machine's *global* git email is a work address and must never
  appear in this repository — history was rewritten on 27 Sep to remove it ([D-024](docs/DECISIONS.md)).
  Commit IDs recorded before that date resolve through `results/commit_id_map.json`.
- Secrets live in a gitignored `.env`; `.env.example` carries names only. **Never `cp .env.example
  .env` over a live file.** Never print or commit a key.
- **Publishing is separately authorised** — posting, messages, deployment, leaderboard submission,
  and filing upstream issues or PRs. Prepare drafts; do not perform them.
  **One authorisation has been given and consumed:** upstream issue filing, 22 Sep 2026 → 8 issues
  (#553–#560) + 4 comments, as `@hagverdiyevr`. That authorisation covered *those* filings only.
  **Still unauthorised:** social posts, leaderboard submission, and **PRs** — several issues offer
  one; none is open. A new go-ahead is required for each.
  **Replies received:** Universeyi on #540 (23 Sep), justavibedev (23 Sep) and Ruler4396 (26 Sep) on
  #499 — two of them correct us, and every claim in all three was verified. **Public corrections:**
  posted one at a time after an explicit yes on the exact text — #499, #384 and #540 replies and
  edits to #554, #556, #557, #559 — **all 7 done (26–27 Sep)**. The #540 reply promised a link to the harness; **kept** with a follow-up on 26 Sep once the repo
  was public. Note: Claude drafted and posted
  all 12 under the owner's name — the owner did not write them, but readers cannot tell.

## Phases

**A** evaluator audit ($0.00 ✅) → **B** 11 gates ($0.47 ✅) → **B9** noise floor ($0.42 ✅) →
**C** 320 trajectories (✅ $7.33) → **D** ✅ **1,792** judge evaluations ($5.41) →
**E** ✅ analysis and release ($0.00). **Spent $13.76 of $75 — the study is complete.**
Upstream filing was authorised and is **done**: 8 issues (#553–#560) + 4 comments on existing
threads, 22 Sep — record in [docs/UPSTREAM_ISSUES.md](docs/UPSTREAM_ISSUES.md), rationale in
[D-022](docs/DECISIONS.md). **No other publishing is authorised** (no posts, no leaderboard
submission, no PRs).

**All measurement is finished.** Nothing further requires spend.

**Phase D is 1,792 evaluations, not 1,280.** The smaller figure counted only the base pass;
[§6.3](docs/PREREGISTRATION.md)'s noise control adds 512 replicates on a pre-drawn 20% sample
([A-005](docs/PREREGISTRATION_AMENDMENTS.md)).
Verify the freeze and the 5-amendment chain (A-001–A-005) any time with `make verify`, or alone with
`vendor/tau2-bench/.venv/bin/python scripts/verify_preregistration.py`.

Surplus budget buys trials and judge replicates only. Tasks are hard-capped at 40 by the benchmark;
spare money is not a licence to widen scope.

## Statistics that survive review

- Task-level **cluster bootstrap** CIs. Trials of one task are not independent — never bootstrap at
  trajectory level.
- Report the **paired-difference CI**, not two independent per-arm CIs.
- Any "no effect" claim is a **null claim** → TOST with a pre-specified margin (5pp); state the
  effect size ruled out and the realized MDE.
- Never headline `pass^k` at `k = num_trials` — it degenerates to one Bernoulli draw per task.
- **Cost per success** = total cost including failures ÷ successes; **undefined**, never 0, at zero
  successes. Include judge cost. Report simulator cost separately as evaluation overhead.
  **State the boundary.** Any claim about what a model *costs to run* uses tau2's `agent_cost` only;
  evaluation cost (simulator + judge) is a separate number. E-L2 mixed them and overstated a 1.7×
  flip as 10× ([R-L16](docs/FINDINGS.md)). Never add this study's own re-grading cost to an agent.
- Results are a custom subset, not an official τ³ score. Declare the scaffold **"standard"** vs
  **"custom"**; never claim leaderboard comparability without it.

## Maintenance protocol — run after EVERY iteration

Documentation drifts silently. This is mechanical on purpose.

| If this happened | Update |
| --- | --- |
| Measured anything | **FINDINGS** — append a new entry with method and numbers. Never rewrite an old one; supersede it |
| Chose between options | **DECISIONS** — append `D-NNN` with context, decision, rationale, consequence |
| Spent money | Regenerate the ledger, then sync the figures in **STATUS** and **PLAN** |
| Finished a phase or gate | **STATUS** (phase line + next task) and **PLAN** (phase table + budget) |
| Learned an external fact | **REFERENCE** — with the date it was verified |
| Changed direction | **PLAN** — bump the version, state what it supersedes |
| Departed from the frozen design | **PREREGISTRATION §10 only.** Never edit §1–§9. The verifier will catch it |
| Ended a session | **STATUS** — session log row, blockers, next executable task |

Then, always:

```bash
make docs          # links, frozen hash, spend agreement, stale claims, README numbers
```

It must print **DOCS ALIGNED** before moving on. Before any *spend*, `make verify` must pass —
that adds the judge-adapter, runner-guard, Phase D and Phase A tests to the doc check, and ends by
proving upstream untouched. A failure is drift, not noise — fix the document,
do not silence the check. If a check is wrong rather than the docs, fix the *check* and say so.

**Two invariants that outrank convenience:**
- **FINDINGS and DECISIONS are append-only.** History is the artifact; rewriting it destroys the
  record of how conclusions were reached — including the two theses we killed.
- **The frozen pre-registration is immutable.** Deviations are logged, never edited in. Its first
  real test came when determinism made T = 4 wasteful; we kept the design and logged
  [D-018](docs/DECISIONS.md) instead of saving USD 3.

## Commands

```bash
make setup                        # create the pinned venv (uv sync --frozen; lock untouched)
make verify                       # ALL offline gates, on 3.12.9, then prove upstream untouched
make docs                         # doc alignment (run every iteration)
make pristine                     # fail unless upstream is at the pin with no modified files
make dry-run / make dry-run-d     # validate the Phase C / Phase D manifest, dispatch nothing
cd vendor/tau2-bench && .venv/bin/python ../../scripts/review/verify_post_claims.py   # R-L1–R-L9, offline
cd vendor/tau2-bench && uv run --frozen python ../../scripts/phase_a/03_replay_and_null_agent.py
vendor/tau2-bench/.venv/bin/python scripts/phase_d/analyze_phase_d.py                # every Phase D/E number
```

Read actual `--help` output before wrapping any CLI flag. Never invent one.
