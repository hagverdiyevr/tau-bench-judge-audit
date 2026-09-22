# Upstream contribution drafts — `sierra-research/tau2-bench`

> **STATUS: FILED 22 September 2026**, authorised by the project owner, as
> [@hagverdiyevr](https://github.com/hagverdiyevr).
>
> **8 new issues + 4 comments**, not 13 new issues. A duplicate check against the live tracker
> found that 5 drafts overlapped existing threads; filing those as new issues would have been
> duplicate noise. They were posted as comments adding evidence instead.

| Filed | Draft | What |
| --- | --- | --- |
| [#553](https://github.com/sierra-research/tau2-bench/issues/553) | 1 | Judge prompt is ~20% literal `assistant: None` |
| [#554](https://github.com/sierra-research/tau2-bench/issues/554) | 2 | `all([])` scores an empty judge response as a full pass |
| [#555](https://github.com/sierra-research/tau2-bench/issues/555) | 3 | Raw `json.loads`; `gemini-3.8-flash` crashes 448/448 |
| [#556](https://github.com/sierra-research/tau2-bench/issues/556) | 4 | Judge cost unrecorded; hidden share varies 30–60% by model |
| [#557](https://github.com/sierra-research/tau2-bench/issues/557) | 5 | ACTION checker order-sensitive (`tasks.py:195`) |
| [#558](https://github.com/sierra-research/tau2-bench/issues/558) | 11 | `--seed` silently dropped for Gemini |
| [#559](https://github.com/sierra-research/tau2-bench/issues/559) | 12 | `ToolCall` has no `provider_specific_fields` |
| [#560](https://github.com/sierra-research/tau2-bench/issues/560) | 13 | Stale `uv.lock` at tag v1.0.1 |

| Comment on | Draft | What it added |
| --- | --- | --- |
| [#499](https://github.com/sierra-research/tau2-bench/issues/499#issuecomment-5772485558) | 9 | The 16-read / 2-write split; tasks 64 and 105 have policy-violating gold |
| [#384](https://github.com/sierra-research/tau2-bench/issues/384#issuecomment-5774383986) | 8 + 10 | 72/114 tasks auto-pass NL; null agent passes DB on 11 |
| [#540](https://github.com/sierra-research/tau2-bench/issues/540#issuecomment-5774393926) | 7 | Decomposes the noise floor into agent and judge terms |
| [#474](https://github.com/sierra-research/tau2-bench/issues/474#issuecomment-5774408352) | 6 | Still reproduces; the override is worth 9.1 points |

**One draft was withdrawn, not filed.** Draft 13 originally paired the stale `uv.lock` with a
claim that `requires-python` is wrong because `tau2` cannot be imported on Python 3.13
(`audioop`, PEP 594). No Python 3.13 is available on this machine and the `audioop`-importing
dependency could not be located in the installed venv — it is most likely behind the voice extras,
which are not installed. **The claim was dropped rather than asserted unverified**, and #560
carries only the `uv.lock` half, which was reproduced directly. See [D-004](DECISIONS.md).

Two other draft claims were corrected during verification rather than published as written:
`uv sync --frozen` does **not** fail on the stale lock (tested, it succeeds), and the `--seed`
mechanism is `litellm.drop_params = True` at `llm_utils.py:71` turning an `UnsupportedParamsError`
into a silent no-op — not a bare drop as first written.

All against **v1.0.1** (`fc0055dc4e0a316c3f83133267fbd6faaa770992`), Python 3.12.9, retail domain.
Every claim below was measured on that pin; the evidence entry is linked for each.

**Ordered by impact**, not by discovery. The first five change scores or crash runs; the rest are
correctness and ergonomics.

---

## 1 · NL-judge prompt is ~20% literal `"assistant: None"` noise

**Evidence:** [B4](FINDINGS.md) · **Severity:** high — affects every judge-gated score

`evaluator_nl_assertions.py:80` serializes the trajectory as:

```python
trajectory_str = "\n".join(
    [f"{message.role}: {message.content}" for message in trajectory]
)
```

On a tool-calling turn `content` is `None`, so the line renders as the literal string
`assistant: None`.

**This is not a disagreement about design intent.** `ticks_to_message_history` (line 151)
documents the intent explicitly — *"Only speech content is included (tool calls are ignored for NL
evaluation)"* — and implements it by skipping tool-call chunks. Line 80 does not implement that
same intent: instead of **omitting** the turn it **emits `None`**.

**Measured over 320 retail trajectories (8,430 serialized lines):**

| | |
| --- | ---: |
| Lines rendering as `<role>: None` | **1,674 (19.9%)** |
| Trajectories containing at least one | **310 / 320** |
| Per trajectory (min / median / max) | 0 / 5 / **15** |

So roughly **one line in five** of what the judge reads is content-free noise, and the judge is
asked to assess whether the agent performed actions whose names and arguments it cannot see.

**Suggested fix** — implement line 80 the way line 151 already describes:

```python
trajectory_str = "\n".join(
    f"{m.role}: {m.content}" for m in trajectory if m.content is not None
)
```

If instead tool calls *should* be visible to the judge, that is a larger design change and worth
its own discussion — but the current behaviour serves neither goal.

---

## 2 · `all([])` scores an empty judge response as a **full pass**

**Evidence:** [B-L16](FINDINGS.md) · **Severity:** high — silent false positive

`evaluator_nl_assertions.py:51`:

```python
all_expectations_met = all(result.met for result in nl_assertions_checks)
```

`all()` over an empty iterable returns `True`. If the judge returns `{"results": []}` — or a
response whose verdicts all fail to parse into checks — the task is scored as **fully meeting every
NL assertion**.

There is no validation that the number of verdicts matches the number of assertions, so duplicate,
extra, missing and mismatched verdicts are all equally silent.

**Suggested fix** — require a 1:1 correspondence before scoring:

```python
if len(nl_assertions_checks) != len(nl_assertions):
    raise ValueError(
        f"judge returned {len(nl_assertions_checks)} verdicts "
        f"for {len(nl_assertions)} assertions"
    )
all_expectations_met = all(c.met for c in nl_assertions_checks)
```

A reference fail-closed implementation is in this repo at `scripts/grading/judge_adapter.py`.

---

## 3 · Judge path ignores upstream's own fence stripper — 100% crash on `gemini-3.8-flash`

**Evidence:** [B-L16](FINDINGS.md), [D-L3](FINDINGS.md) · **Severity:** high — one-line fix

`evaluator_nl_assertions.py:127` parses the judge response with raw `json.loads`:

```python
result_data = json.loads(assistant_message.content)
```

`llm_utils.py:509` already provides `extract_json_from_llm_response`, which handles Markdown
fences. The judge path does not call it.

Models that fence their JSON therefore crash the evaluator. **Measured: `gemini/gemini-3.8-flash`
fenced 448 of 448 responses (100%)** across 320 trajectories. The other three judges tested
(`gpt-4.1-2025-04-14`, `gpt-4.1-mini`, `gemini-3.1-flash-lite`) fenced 0 of 448 each — so this is
invisible with OpenAI judges and total with that Gemini model.

**Suggested fix:**

```python
result_data = json.loads(extract_json_from_llm_response(assistant_message.content))
```

---

## 4 · Judge cost is entirely unaccounted — ~40% understatement

**Evidence:** [B-L14](FINDINGS.md) · **Severity:** medium-high — affects every published cost figure

No cost or usage field exists anywhere for the NL-assertion judge call. On judge-gated tasks the
judge is a second LLM call per task, comparable in prompt size to the agent's context, and it is
absent from the reported run cost.

Measured understatement on judge-gated retail tasks: **~40%** of true spend.

Anyone comparing models on cost using tau2's own numbers is comparing agent cost only, while the
judge cost varies with trajectory length — i.e. with how much the agent talked.

**Suggested fix:** thread the judge's `usage`/`response_cost` into `RewardInfo` alongside the
verdicts, and include it in run-level totals.

---

## 5 · `ACTION` checker is order-sensitive on list arguments

**Evidence:** [B-L7](FINDINGS.md) · **Severity:** medium — false negatives

A tool call identical to gold except for the **order of a list argument** scores
`action_match: false`:

```python
gold = {"order_id": "#W1", "item_ids": ["1", "2"], "payment_method_id": "c1"}
got  = {"order_id": "#W1", "item_ids": ["2", "1"], "payment_method_id": "c1"}
# semantically identical; compares unequal
```

This is the sibling of the known DB-hash issue (#514) on the *action* side, and it penalises
correct behaviour wherever `ACTION` gates reward.

> **Note.** We deliberately did **not** patch this locally: fixing it breaks comparability with
> published v1.0.1 numbers. Recommend fixing behind a flag, with both variants reported during a
> transition.

---

## 6 · The NL judge is hardcoded, and swapping it moves scores by 9 points

**Evidence:** [D-L2](FINDINGS.md) · **Severity:** medium — reproducibility / vendor coupling

`config.py:24` pins `DEFAULT_LLM_NL_ASSERTIONS = "gpt-4.1-2025-04-14"`, marked experimental/WIP.
There is no supported way to override it per-run; patching `tau2.config` is a **silent no-op**
because the evaluator binds the name at import (the effective patch target is
`tau2.evaluator.evaluator_nl_assertions.DEFAULT_LLM_NL_ASSERTIONS`).

Re-grading the same 320 saved trajectories under four judges — identical captured prompts, only
the model changing — gives:

| Judge | Mean NL reward |
| --- | ---: |
| `gpt-4.1-mini` | 0.647 |
| `gpt-4.1-2025-04-14` *(default)* | 0.609 |
| `gemini-3.1-flash-lite` | 0.597 |
| `gemini-3.8-flash` | 0.556 |

**A 9.1-point spread attributable to grader choice alone.** Since the default is a dated snapshot,
scores are also implicitly pinned to that snapshot's availability.

**Suggested fix:** expose the judge model as a documented CLI/config parameter, and record the
judge model and its resolved snapshot in the results artifact.

---

## 7 · The default judge is not reproducible at temperature 0

**Evidence:** [D-L5](FINDINGS.md) · **Severity:** medium — noise floor under every judge-gated score

`DEFAULT_LLM_NL_ASSERTIONS_TEMPERATURE = 0.0`, but temperature 0 is not determinism for remote
inference.

Re-grading a pre-drawn 20% sample three times per judge (256 repeated pairs):

| Judge | Flipped verdicts |
| --- | ---: |
| `gpt-4.1-2025-04-14` *(default)* | **1 / 64** |
| `gpt-4.1-mini` | 0 / 64 |
| `gemini-3.8-flash` | 0 / 64 |
| `gemini-3.1-flash-lite` | 0 / 64 |

The single flip is the default judge: retail task 105, graded `1.0 / 0.0 / 1.0` across three
identical requests. Independently, re-grading with the default judge reproduces tau2's own recorded
verdicts on **317/320 (99.1%)** trajectories — the 3 residual disagreements are the same effect.

Small, but it is a **floor under every judge-gated score**, and worth documenting so users do not
read single-run differences of a point or two as signal.

---

## 8 · `communicate_info` is populated on 36 tasks and scored on none

**Evidence:** [A1](FINDINGS.md) · **Severity:** medium — docs/schema mismatch

In retail, `COMMUNICATE` appears in the `reward_basis` of **zero** of 114 tasks — `[DB,
COMMUNICATE]` is only the schema *default*. Meanwhile `communicate_info` is populated on **36**
tasks and contributes to reward on **none** of them.

Retail reward is effectively `DB × NL_ASSERTION`.

This cost us an entire research direction: three independent passes read the schema/docs and
concluded `COMMUNICATE` was live. Reading the shipped task files is the only reliable check, and
the mismatch is worth either fixing or documenting prominently.

---

## 9 · `#499` characterization: 18 failing golden actions across 15 tasks

**Evidence:** [A4](FINDINGS.md) · **Severity:** medium — sharpens an open issue

Replaying each task's own `evaluation_criteria.actions` against a fresh environment fails on **18
actions across 15 tasks**: `2, 3, 4, 35, 37, 38, 39, 46, 47, 54, 55, 64, 67, 68, 105`.

These split into two distinct causes — worth separating, because only one is a data bug:

- **16** are stale-data mismatches (the gold action no longer applies to the seeded state)
- **2** are **logically impossible** gold actions (tasks **64** and **105**)

Tasks **67, 68, 105** additionally interact with the null-agent false-positive mechanism in #10
below.

---

## 10 · A null agent passes the DB check on 11 tasks

**Evidence:** [A5](FINDINGS.md) · **Severity:** medium — validity check worth adopting

An agent that takes **no action at all** passes the DB component on 11 of 114 retail tasks:
`10, 12, 24, 25, 50, 57, 62, 65, 67, 68, 105`. Three of those (**67, 68, 105**) also have failing
golden actions, so the task cannot distinguish "did nothing" from "did the right thing".

This is a cheap, reusable validity check: **any task a null agent passes cannot measure agent
capability on its scored component.** Recommend adding it to CI.

---

## 11 · LiteLLM silently drops `seed` for the `gemini` provider

**Evidence:** [B-L15 correction](FINDINGS.md) · **Severity:** medium — false reproducibility promise

`llm_utils.py` passes `seed` through to LiteLLM, which drops it for the `gemini` provider without
warning. A user setting `--seed` for a Gemini arm gets no seeding and no indication of it.

Because Gemini models happen to be highly reproducible at temperature 0, this can look like seeding
is working when it is not — the more dangerous failure mode.

**Suggested fix:** warn when a requested `seed` is not supported by the resolved provider.

---

## 12 · `ToolCall` cannot carry `provider_specific_fields`

**Evidence:** [B-L6](FINDINGS.md) · **Severity:** medium — latent, breaks silently

Gemini thought signatures survive tau2's multi-turn tool-calling path **only** because LiteLLM
packs them into the tool-call `id`, which tau2 happens to preserve. `ToolCall` has no field for
`provider_specific_fields`.

This works today by coincidence. Any LiteLLM change to how signatures are transported breaks
Gemini multi-turn tool calling **silently** — degraded outputs, no error. Related: `litellm#25322`.

**Suggested fix:** add an explicit passthrough field so the dependency is declared rather than
accidental.

---

## 13 · Environment and packaging

**Evidence:** [A0](FINDINGS.md), [A0b](FINDINGS.md) · **Severity:** low — friction

**a. `requires-python` is wrong.** `pyproject.toml` declares `<3.14`, but `tau2` **cannot be
imported on 3.13**: a transitive dependency uses `audioop`, removed in 3.13 by PEP 594.

Upstream also ships `.python-version` = `3.12`, so the *default* `uv sync` path works — the defect
bites anyone following the declared range instead (an existing 3.13 env, or a CI matrix testing
3.13). **Fix:** declare `<3.13`.

**b. Committed `uv.lock` is stale at tag v1.0.1.** The lock pins `tau2` version `1.0.0` while
`pyproject.toml` says `1.0.1`, so `uv run` rewrites the lock on first use and leaves a dirty tree.
`uv sync --frozen` fails. **Fix:** regenerate and commit the lock at tag time.

---

## Reproducing any of these

Every claim above regenerates from this repository with **no API keys and no spend**:

```bash
make verify
cd vendor/tau2-bench && uv run python ../../tests/test_phase_a_regression.py
```

The measured judge results (items 1, 3, 6, 7) come from `results/phase_d/regrade_journal.jsonl`
and regenerate with:

```bash
python3 scripts/phase_d/analyze_phase_d.py
```
