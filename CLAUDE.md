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

**Phase A and B complete; Phase C 1/8 dispatched. USD 8.35 spent of 75.00; USD 66.65 remaining.**
Every mechanism the study depends on is verified. The pre-registration is **frozen**
(`a917984e…`, 2026-09-20T10:54:29Z). **Phase C is unblocked**; no confirmatory data exists yet.

Spend is tracked in `results/spend_ledger.json`, regenerated from run artifacts — never by hand.

Upstream is checked out at `vendor/tau2-bench`, pinned to **v1.0.1**
(`fc0055dc4e0a316c3f83133267fbd6faaa770992`), MIT, with a working venv on Python 3.12.9.
Both `GEMINI_API_KEY` and `OPENAI_API_KEY` are live in a gitignored `.env`.

## What is being built

**Research question:** τ³-retail's reward is gated on 40 of 114 tasks by an LLM judge hardcoded to
`gpt-4.1-2025-04-14`. **Does that judge favour agents from its own model family?**

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
  (`audioop`, PEP 594). Machine default `python3` is 3.14.6. [A0](docs/FINDINGS.md)

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
  with 4–11 literal `"assistant: None"` lines per trajectory. [B4](docs/FINDINGS.md)
- **Judge temperature is 0.0** and self-consistency measured 11/11; flip rate bounded **<9%**
  (0/33, rule of three). Not zero — a bound. [B-L13](docs/FINDINGS.md)
- **tau2 does not account for judge cost at all** — ~40% understatement of true run cost on
  judge-gated tasks. Our ledger must add it. [B-L14](docs/FINDINGS.md)

**Reproducibility — the two arms differ**
- **At temperature 0, `gemini-3.1-flash-lite` is deterministic and `gpt-4.1-nano` is not.** Across
  repeat invocations the Gemini arm reproduced **5/5 identical message contents, tool calls,
  rewards and costs**; the OpenAI arm reproduced **0/3**, with up to **2.6×** per-task cost
  variation. Caching ruled out. **Not byte-identical** — ids/timestamps differ. Also: LiteLLM
  **drops `seed` for the gemini provider**, so these were repeats, not seeded replicates.
  [B-L15](docs/FINDINGS.md)
- **Therefore `pass^k` was constant for the Gemini arm in a 5-task pilot** — repeat invocations
  yielded identical rewards, so `pass^4` would equal `pass^1`. This is a **pilot observation, not
  a structural guarantee**; re-verify on the Phase C output before reporting. Disclose it; never
  present it as reliability, and never compare a variance-based statistic across arms without
  stating the asymmetry. [D-018](docs/DECISIONS.md)

**The judge parser — use our adapter, never the raw path**
- **`gemini-3.8-flash` fences its JSON**, so upstream's raw `json.loads`
  (`evaluator_nl_assertions.py:127`) raises `JSONDecodeError`. Verified live: the other three
  frozen judges return bare JSON. Upstream already ships `extract_json_from_llm_response`
  (`llm_utils.py:509`) but does not use it here.
- **Upstream scores an empty result set as a full pass** — `all([])` is `True`, so a judge
  response with zero verdicts silently earns full NL reward. Duplicates, extras and mismatched
  assertion text are equally silent.
- **Therefore all re-grading goes through `scripts/grading/judge_adapter.py`**, which is
  fail-closed: it strips fences, proves one unique verdict per supplied assertion, and **never**
  converts an anomalous response into a pass. 21 regression tests in `tests/test_judge_adapter.py`.

**Known defects — document, do not patch**
- **#514**: DB hash is order-sensitive on lists. [D-011](docs/DECISIONS.md)
- **B-L7**: the ACTION checker is order-sensitive on list arguments — a call identical to gold except
  list order scores `action_match: false`. [D-017](docs/DECISIONS.md)
- Fixing either breaks comparability with official v1.0.1 numbers. Compute both variants, report both.
- **`get_response_cost()` returns `0.0` on exception** — an unpriced model reports as free.
- **litellm#25322**: Gemini thought signatures survive tau2's path **only** because LiteLLM packs
  them into the tool-call `id`, which tau2 preserves. `ToolCall` cannot carry
  `provider_specific_fields`. A transport change breaks this silently. [B-L6](docs/FINDINGS.md)

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
- **Never leak evaluation state into the agent.** `HalfDuplexAgent.__init__(tools, domain_policy)`
  enforces this architecturally — do not weaken it.
- **Pre-registration is frozen before Phase C.** Anything outside it is exploratory and reported
  without inferential statistics. [D-012](docs/DECISIONS.md)
- **Pin and hold.** No dependency or commit bumps mid-comparison.
- **Never present mocked output as a real model result.** If credentials are missing, finish the
  offline work and report the exact remaining setup action.
- **Negative results are retained.** No score, savings, production-impact or hiring claim without a
  linked run artifact. A well-specified null with a stated MDE is a valid outcome.
- Secrets live in a gitignored `.env`; `.env.example` carries names only. **Never `cp .env.example
  .env` over a live file.** Never print or commit a key.
- **Publishing is separately authorised** — posting, messages, deployment, leaderboard submission,
  and filing upstream issues or PRs. Prepare drafts; do not perform them.

## Phases

**A** evaluator audit ($0.00 ✅) → **B** 11 gates ($0.47 ✅) → **B9** noise floor ($0.42 ✅) →
**C** 320 trajectories (✅ complete, $7.33) → **D** 1,280 judge evaluations (~$5.97) →
**E** analysis and release ($0.00). **Spent $8.35 · Phase D ~$6 · projected total ~$14.**

The pre-registration is frozen and Phase C is unblocked. Verify the freeze any time with
`python scripts/verify_preregistration.py`.

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
python scripts/check_docs.py          # links, frozen hash, spend agreement, stale claims
```

It must print **DOCS ALIGNED** before moving on. Before any *spend*, `make verify` must pass —
that adds the judge-adapter and runner-guard tests to the doc check. A failure is drift, not noise — fix the document,
do not silence the check. If a check is wrong rather than the docs, fix the *check* and say so.

**Two invariants that outrank convenience:**
- **FINDINGS and DECISIONS are append-only.** History is the artifact; rewriting it destroys the
  record of how conclusions were reached — including the two theses we killed.
- **The frozen pre-registration is immutable.** Deviations are logged, never edited in. Its first
  real test came when determinism made T = 4 wasteful; we kept the design and logged
  [D-018](docs/DECISIONS.md) instead of saving USD 3.

## Commands

```bash
make verify                                                      # ALL offline gates — run before any spend
make dry-run                                                     # validate Phase C manifest, dispatch nothing
python scripts/check_docs.py                                     # doc alignment (run every iteration)
python scripts/verify_preregistration.py                         # freeze + amendment chain integrity
cd vendor/tau2-bench && uv sync --frozen                         # pinned harness, Python 3.12.9
uv run python ../../scripts/phase_a/03_replay_and_null_agent.py  # reproduce Phase A
uv run python ../../scripts/phase_b/step5_judge_noise.py         # re-grade saved trajectories
```

Read actual `--help` output before wrapping any CLI flag. Never invent one.
