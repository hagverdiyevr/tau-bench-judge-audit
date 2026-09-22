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

### 2. The official grader is not reproducible

At temperature 0, across byte-identical repeated requests, the **incumbent `gpt-4.1` was the only
judge of four to flip a verdict** — task 105, graded `1.0 / 0.0 / 1.0`. The three others flipped
zero times in 64 pairs each.

This independently reproduces, in the *judge* role, a determinism asymmetry first measured in the
*agent* role on a different task set. The benchmark's own grader has an irreproducibility floor
under every score it assigns.

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
make verify        # every offline gate: docs, frozen hash, amendment chain, 99 checks. No API keys.
```

```bash
python3 scripts/phase_d/analyze_phase_d.py      # regenerates every number above from raw artifacts
```

Upstream is a pinned submodule at **v1.0.1** (`fc0055dc`), byte-untouched — our code registers from
outside, so "the baseline is stock" is provable rather than asserted.

---

## How this was kept honest

The design was **frozen and SHA-256 sealed** before confirmatory data existed
(`a917984e…`), with deviations appended to a hash-chained amendment log rather than edited in.
`python3 scripts/verify_preregistration.py` verifies both.

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

**13 defects** found and documented with reproductions, in
[`docs/FINDINGS.md`](docs/FINDINGS.md) § Upstream. Highlights:

- The NL judge **cannot see tool calls** — `content` is `None` on tool-calling turns, so names and
  arguments are dropped and literal `"assistant: None"` lines reach the judge prompt
- **`all([])` scores an empty judge response as a full pass**
- The judge path **ignores upstream's own fence stripper**, crashing on fenced JSON
- **Judge cost is entirely unaccounted** — ~40% understatement on judge-gated tasks
- The **ACTION checker is order-sensitive on list arguments**, a false-negative sibling of #514
- LiteLLM **silently drops `seed` for the `gemini` provider**, so seeded reproducibility is
  unavailable without the caller knowing

*Filing is a separate, explicitly authorised step; drafts are prepared, nothing has been submitted.*

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
