# Does the τ³-bench judge favour its own model family?

**No effect detectable — but the search found three things that matter more.**

τ³-bench (`tau2`) scores 40 of its 114 retail tasks with an **LLM judge hardcoded to
`gpt-4.1-2025-04-14`**. If that judge favoured agents from its own family, a component of every
retail score would be a vendor artifact. This repository tests that, pre-registered and frozen
before any confirmatory data existed.

It is also a reusable toolkit: **generate trajectories once, then re-grade the same saved
conversations under any number of judges.** The judge comparison is within-trajectory and paired,
so it costs one short LLM call and carries no capability confound.

**320 trajectories · 1,792 judge evaluations · USD 13.76 · zero anomalies.**

---

## Three findings that don't depend on the null

### 1. Swapping only the grader moves scores by 9.1 points

Same 320 trajectories, same captured prompt, only the judge changes:

| Judge | Mean NL-assertion reward |
| --- | ---: |
| `gpt-4.1-mini` | **0.647** |
| `gpt-4.1-2025-04-14` *(the incumbent)* | 0.609 |
| `gemini-3.1-flash-lite` | 0.597 |
| `gemini-3.8-flash` | **0.556** |

A 9.1-point spread — wider than most leaderboard gaps. **This is also where the study nearly went
wrong.** The incumbent grades the OpenAI arm **+0.056** above `gemini-3.8-flash`, which reads as
favouritism until you notice it grades the *Google* arm **+0.050** higher too. It is a uniformly
more lenient judge, not a biased one. Without the difference-in-differences control term, this
would have been published as bias.

### 2. The official grader gave different verdicts to identical requests

At temperature 0, across byte-identical repeated requests, the **incumbent `gpt-4.1` was the only
judge of four to flip a verdict** — task 105, graded `1.0 / 0.0 / 1.0`. The three others flipped
zero times in 64 pairs each.

That is **one flip in 256**. It shows the default grader's irreproducibility floor is not zero; it
does **not** show that one model family is less reproducible than the other (Fisher p = 0.50).
An earlier version of this README said it did — see *Corrections* below.

### 3. Pointing the judge at `gemini-3.8-flash` crashes it 100% of the time

`evaluator_nl_assertions.py` calls raw `json.loads`, while upstream's own
`extract_json_from_llm_response` sits unused one module away. `gemini-3.8-flash` fences its JSON in
Markdown — **448 of 448 responses**. Not a flaky edge case: a total failure for anyone swapping the
judge. Separately, `all([])` means an **empty** judge response scores as a **full pass**.

### And one more, from the cost model

**The cheaper agent costs 10× more per reliably-completed task.**

| Arm | Cost / attempt | Cost / success (k=1) | Cost / reliable task (k=4) |
| --- | ---: | ---: | ---: |
| `gpt-4.1-nano` | **cheaper** ($2.84 / 160) | $0.2518 | **$2.7703** |
| `gemini-3.1-flash-lite` | $4.49 / 160 | **$0.0666** | **$0.2666** |

The ranking inverts depending on what you count. Reliability compounds — and cost-per-token, the
default comparison, points at the wrong model here by an order of magnitude.

---

## The pre-registered result, stated precisely

```
FamilyBias = +0.0063     95% CI [-0.0875, +0.1062]     n = 40 tasks
                         task-level cluster bootstrap, B = 10,000
```

**This is an underpowered null, not a finding of fairness.** TOST against the pre-specified ±5pp
margin does **not** clear. The realized MDE is **0.1367** — the design could only ever have seen a
~14-point interaction. What the data rules out is `|FamilyBias| > 0.1062`.

Two constraints travel with that number and are never dropped:

- **The OpenAI arm is floor-bound** — pass^1 of 0.138 against the Google arm's 0.675. Capability is
  confounded with family by 54 points of baseline success. The null means *"no family bias
  detectable between these two specific agents"*, not a claim about model families.
- **More money cannot fix it.** Between-task SD is 0.3087 over a task set hard-capped at 40 by the
  benchmark. Trials shrink within-task noise, which is not the binding term. Only more *tasks*
  would move the MDE, and none exist.

The tier control agrees and is the more informative half: high tier **+0.0063**, low tier
**+0.0000**. Two independent tiers pointing at nothing.

---

## What's reusable

| Tool | What it does |
| --- | --- |
| `scripts/phase_a/` | **Evaluator audit suite** — maps what a benchmark actually scores, offline, $0, no API keys |
| `scripts/phase_d/` | **Judge-swap re-grading harness** — generate once, score under N judges, gated and resumable |
| `scripts/grading/judge_adapter.py` | **Fail-closed judge parser** — strips fences, validates 1:1 assertion↔verdict, never grants a vacuous pass |
| `scripts/phase_c/attempt_logger.py` | **True spend accounting** — every API attempt at the shared LiteLLM boundary, failures and judge calls included |

The audit suite is the piece most likely to transfer: it answers *"what does this benchmark
actually measure?"* before you spend anything. Here it killed the project's original thesis for
**$0.00** — see below.

---

## Reproduce it

```bash
git clone --recurse-submodules <repo> && cd t-bench
make setup         # pinned venv, Python 3.12.9 (uv sync --frozen)
make verify        # every offline check, then proves upstream untouched. No API keys.
```

```bash
vendor/tau2-bench/.venv/bin/python scripts/phase_d/analyze_phase_d.py   # every number above, from raw artifacts
```

Upstream is a pinned submodule at **v1.0.1** (`fc0055dc`), byte-untouched — our code registers from
outside, and `make verify` ends by **failing** if upstream has moved or been modified. Until 27 Sep
the gate itself modified upstream's `uv.lock` on every run; that is fixed and disclosed in
[FINDINGS R-L11](docs/FINDINGS.md).

---

## How this was kept honest

The design was **frozen and SHA-256 sealed** before confirmatory data existed
(`a917984e…`), with deviations appended to a hash-chained amendment log rather than edited in.
`make verify` checks both.

Three habits did the real work:

**Verify against shipped data, not documentation.** The original thesis — that retail reward is
gated by a `COMMUNICATE` substring matcher — was **falsified before any spend**. `COMMUNICATE`
appears in the `reward_basis` of **zero** of 114 retail tasks; it is only the schema default. Three
research passes had read the docs and repeated the same error. Cost of catching it: **$0.00**.

**Never infer success from a weak proxy.** A test once checked `if created` before cleaning up and
destroyed 40 paid simulations. An invocation was marked `completed` on exit code alone while 6/40
were dead. Resume accepted a truncated artifact because the file merely *existed*. Each is now a
test that proves the property instead of assuming it — and each is the same shape as the upstream
defects catalogued here, where a swallowed exception, a `0.0` cost, and `all([])` all report
success by default.

**Negative results are retained.** Two theses were killed and both autopsies are in
[`docs/DECISIONS.md`](docs/DECISIONS.md), which is append-only. History is the artifact.

---

## Upstream contributions

**15 defects and gaps** documented with reproductions — **13 reported upstream** — in
[`docs/FINDINGS.md`](docs/FINDINGS.md) § Upstream. Highlights:

- The NL judge **cannot see tool calls** — `content` is `None` on tool-calling turns, so names and
  arguments are dropped and literal `"assistant: None"` lines reach the judge prompt
- **`all([])` scores an empty judge response as a full pass**
- The judge path **ignores upstream's own fence stripper**, crashing on fenced JSON
- **Judge cost is entirely unaccounted** — measured at a third of true cost on judge-gated tasks, and
  20% vs 58% depending on the agent model, so cost comparisons between models are skewed
- **A do-nothing agent scores full reward on 6 of 114 retail tasks** — no writes needed, and no
  assertions for the judge to check *(found in the post-release review; not yet reported)*
- The **ACTION checker is order-sensitive on list arguments**, a false-negative sibling of #514
- LiteLLM **silently drops `seed` for the `gemini` provider**, so seeded reproducibility is
  unavailable without the caller knowing

**Filed 22 September 2026** as [#553–#560](https://github.com/sierra-research/tau2-bench/issues/553)
plus evidence comments on four existing threads
([#499](https://github.com/sierra-research/tau2-bench/issues/499),
[#384](https://github.com/sierra-research/tau2-bench/issues/384),
[#540](https://github.com/sierra-research/tau2-bench/issues/540),
[#474](https://github.com/sierra-research/tau2-bench/issues/474)).

Eight new issues rather than thirteen: a duplicate check found five drafts overlapped open threads,
so those were posted as comments adding evidence instead. One draft was **withdrawn rather than
filed** — a Python 3.13 import claim that could not be reproduced on this machine. Full record and
the three claims that verification corrected before publication:
[`docs/UPSTREAM_ISSUES.md`](docs/UPSTREAM_ISSUES.md).

---

## Corrections since release

Three people replied to our upstream posts within four days; two corrected us, and both were right.
A claim-by-claim re-check of all 12 posts followed. **No reported bug turned out not to exist**, but
**7 of the 12 contain a claim that goes further than the evidence under it**:

- Tasks 67 and 68 pass for a do-nothing agent because they need no writes — **not** because the gold
  replay failed. Only task 105 is that case.
- Of the two tasks we said had impossible answer keys, only **task 105** does. Task 64's failing step
  duplicates the next step with the wrong tool, so its target is correct — as PR #571 showed.
- The judge-cost figure near 40% was an **estimate**; measured, it is 32.8%.
- The ACTION order bug changes **no retail score** — ACTION isn't scored in retail.
- "A family asymmetry in the judge" rested on a **single flip**.

The corrections, each with its evidence, are in [FINDINGS R-L1–R-L12](docs/FINDINGS.md) and re-derive
offline from `scripts/review/verify_post_claims.py`. Public corrections to the posts themselves are
pending.

---

## Documentation

| File | Contents |
| --- | --- |
| [`docs/STATUS.md`](docs/STATUS.md) | Where the work stands — start here |
| [`docs/PLAN.md`](docs/PLAN.md) | Thesis, design, phases, measured budget |
| [`docs/PREREGISTRATION.md`](docs/PREREGISTRATION.md) | Frozen hypothesis and analysis plan |
| [`docs/FINDINGS.md`](docs/FINDINGS.md) | Everything measured, with method and numbers |
| [`docs/DECISIONS.md`](docs/DECISIONS.md) | Every fork, including the theses that were killed |
| [`docs/REFERENCE.md`](docs/REFERENCE.md) | External facts: upstream API, pricing, prior art |

---

## Scope and limits

Results are a **custom subset** (40 judge-gated `base` tasks) with a **standard** scaffold — not an
official τ³ score, and not leaderboard-comparable. The 74 DB-only tasks are a different regime
(reward 0.857 vs 0.400) and are never pooled into a headline number. `pass^k` is not comparable
across the two arms: the Google arm's is a determinism constant, the OpenAI arm's a real
measurement.

MIT, matching upstream.
