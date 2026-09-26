# FINDINGS — evidence we measured

> **Role in the memory system:** this file holds **only what we measured ourselves**, with the
> method and the exact numbers. External facts (prior art, vendor pricing, upstream API surface)
> live in [REFERENCE.md](REFERENCE.md). Why we acted on a finding lives in
> [DECISIONS.md](DECISIONS.md). Append-only — never rewrite a finding, supersede it with a new
> dated entry.

**Target under measurement:** `sierra-research/tau2-bench` @ tag `v1.0.1`,
commit `fc0055dc4e0a316c3f83133267fbd6faaa770992`, MIT.
**Cumulative API spend represented in this file: USD 13.76 of 75.00** — Phase A and the
post-release review are static/replay (USD 0.00); spend is Phase B gates, Phase C and Phase D.

---

# Phase A — What τ³-retail actually scores

*Measured 19 Sep 2026. Scripts: `scripts/phase_a/01`–`04`. Environment: Python 3.12.9,
`uv sync` inside `vendor/tau2-bench`.*

## A0 — `tau2` v1.0.1 cannot be imported on Python 3.13

**Claim.** `pyproject.toml` declares `requires-python = ">=3.12,<3.14"`, but `import tau2` fails on
Python 3.13 with `ModuleNotFoundError: No module named 'audioop'`.

**Method.** `uv sync` with `.python-version` = 3.13.13, then `import tau2`. Confirmed `audioop`
absent on 3.13.13 and present on 3.12.9.

**Root cause.** `audioop` was removed from the stdlib in Python 3.13 (PEP 594). The core import
chain reaches it unconditionally, so **text-mode users are affected even without the `voice` extra**:

```
tau2/__init__.py → tau2.runner → tau2.runner.batch → tau2.evaluator.evaluator
  → tau2.evaluator.evaluator_nl_assertions → tau2.agent.base.streaming:22
  → tau2.voice.utils.audio_preprocessing:4 → import audioop
```

**Effective supported range: `>=3.12,<3.13`.** Fix options: guard the voice import behind the extra,
declare `audioop-lts` for 3.13+, or narrow `requires-python`.

**Nuance added 20 Sep 2026 (do not overstate this finding).** Upstream also ships
`.python-version` = **`3.12`**, so the *default* `uv sync` path resolves to 3.12 and works. The
defect bites anyone who follows the declared `requires-python` instead — installing into an existing
3.13 environment, or a CI matrix testing 3.13. The declaration is wrong; the default path is not.

**Consequence for us.** Pin 3.12.9 everywhere. The plan's original 3.13.13 pin was wrong.

**Correction 22 Sep 2026 — the ambient interpreter was misreported.** This finding, and the docs
quoting it, stated "machine default `python3` is 3.14.6". Measured directly:
`which python3` → `/usr/bin/python3` → **3.9.6**. `python3.14` is on PATH but is *not* the
default. The finding's conclusion is unchanged — 3.9.6 is equally outside `>=3.12`, so the pin
stays mandatory — but the number was wrong and it concealed a live constraint:

| Invocation | Version | Runs |
| --- | --- | --- |
| `python3` | **3.9.6** | `make verify`, `check_docs.py`, manifest builders, analysis |
| `uv run python` in `vendor/tau2-bench` | **3.12.9** | anything importing `tau2` |

So **repo-level scripts must remain 3.9-compatible**. This was found when a multiline f-string
expression (PEP 701, 3.12+) raised `SyntaxError` in `scripts/phase_d/analyze_phase_d.py` under
`python3` — a construct that runs fine under `uv run`. Nothing shipped was affected; the failure
was immediate and loud.

> **Superseded, 27 Sep 2026 → [R-L10](FINDINGS.md).** Bare `python3` is not a fixed interpreter here:
> it resolved to 3.14.6, 3.9.6 and 3.13.5 in different sessions depending on which shell startup files
> loaded. The gate no longer uses it.

## A0b — Upstream's committed `uv.lock` is stale at tag v1.0.1

`pyproject.toml` declares `version = "1.0.1"` but the committed `uv.lock` records the `tau2`
package as `version = "1.0.0"`. `uv` corrects it on sync — **even with `--frozen`** — so any working
environment dirties the upstream tree by exactly one line.

**Consequence for our discipline.** A byte-clean upstream working tree is unattainable while having
a usable environment. This does **not** weaken the pin: the submodule records a **commit SHA**, and
working-tree dirt does not change it. Our test suite therefore asserts the submodule *SHA*, never
working-tree cleanliness. [D-007](DECISIONS.md) is scoped accordingly.

## A1 — `COMMUNICATE` is used by zero retail tasks

**Claim.** The English-substring grader does not participate in retail scoring at all.

**Method.** Parsed `evaluation_criteria.reward_basis` for all 114 tasks in
`data/tau2/domains/retail/tasks.json`; read the gating logic in `src/tau2/evaluator/evaluator.py`.

| `reward_basis` | Tasks |
| --- | ---: |
| `[DB, NL_ASSERTION]` | 112 |
| `[DB]` | 2 |
| **containing `COMMUNICATE`** | **0** |

`[DB, COMMUNICATE]` is only the *schema default* — `EvaluationCriteria.reward_basis`'s own field
description reads *"Default `[DB, COMMUNICATE]` matches the original τ-bench"*. Every τ³ retail task
overrides it. The evaluator gates strictly on the task's basis
(`evaluator.py`: `if task_reward_basis & comm_bases:`), so the substring matcher never runs.

**`communicate_info` is populated on 36 of 114 tasks and contributes to reward on 0 of them.**
Dead data in this release. Either the data or the documentation is wrong.

## A2 — Retail reward is gated by a hardcoded LLM judge

**Claim.** `NL_ASSERTION` is an LLM judge, fixed to one vendor's model, and marked experimental.

**Method.** Read `src/tau2/evaluator/evaluator_nl_assertions.py` (calls `generate` from
`tau2.utils.llm_utils`) and `src/tau2/config.py`.

```python
# src/tau2/config.py:24
DEFAULT_LLM_NL_ASSERTIONS = "gpt-4.1-2025-04-14"
```

Not obviously environment-overridable. The component's own field description marks it
*"experimental / WIP"*.

**Consequence.** An OpenAI model grades part of every agent's retail score, including on the
official leaderboard path. This is the basis of the current research question — see
[PLAN.md](PLAN.md).

## A3 — Two-thirds of retail tasks are effectively DB-only

**Claim.** Published retail numbers aggregate across two materially different scoring regimes.

**Method.** Cross-tabulated `reward_basis` against whether `nl_assertions` is non-empty. Missing
criteria default to 1.0, so a task listing `NL_ASSERTION` with no assertions is DB-gated in practice.

| Effective regime | Tasks |
| --- | ---: |
| **DB only** (no live judge) | **74 (65%)** |
| **DB × live LLM judge** | **40 (35%)** |

Distribution across the shipped splits — this constrains any judge-dependent design:

| Split | n | live judge | mutating **and** live judge |
| --- | ---: | ---: | ---: |
| `train` | 74 | 29 | 27 |
| `test` | 40 | **11** | 9 |
| `base` | 114 | **40** | 36 |

**Consequence.** A judge study must use the `base` split; `test` alone yields n=11.

## A4 — Upstream #499 reproduced: 18 golden actions fail, silently

**Claim.** 18 golden actions raise during gold-environment replay and are swallowed as warnings.
Only 2 of them actually corrupt the target DB hash.

**Method.** Replayed `evaluation_criteria.actions` for all 114 tasks against a freshly constructed
environment, capturing exceptions instead of letting `evaluator_env.py` swallow them. The upstream
site:

```python
try:
    gold_environment.make_tool_call(tool_name=action.name, requestor=action.requestor, **action.arguments)
except Exception as e:
    logger.warning(f"Error in golden actions {action.name}({action.arguments}): {e}")
```

**Result: 18 failing golden actions across 15 tasks**, all `ValueError`.
Task IDs: `2, 3, 4, 35, 37, 38, 39, 46, 47, 54, 55, 64, 67, 68, 105`.

| Kind | Count | Effect on target hash |
| --- | ---: | --- |
| READ / GENERIC (`get_product_details`, `find_user_id_by_email`, `find_user_id_by_name_zip`) | 16 | **None** — but proves gold trajectories reference users/products absent from `db.json` (**stale task data**) |
| **WRITE** | **2** | **Target DB hash is wrong** |

The two hash-corrupting cases have gold action sequences that are **impossible under the domain's
own rules**:

| Task | Action | Error |
| --- | --- | --- |
| **64** | `exchange_delivered_order_items` | `Non-delivered order cannot be exchanged` |
| **105** | `exchange_delivered_order_items` | `Insufficient gift card balance to pay for the price difference` |

**This is sharper than the issue title.** "18 failures" is mostly stale data; the real defect is
two tasks whose gold answer violates the policy the agent is graded against.

> **Superseded in part, 27 Sep 2026 → [R-L3](FINDINGS.md), then [R-L13](FINDINGS.md).** Only task
> **105**'s target is wrong. Task 64's failing step is a duplicate of the next one with the wrong tool;
> removing it leaves the target unchanged, so 64's target is **correct**.

## A5 — Null-agent baseline: 10% of tasks pass DB by doing nothing

**Claim.** An agent taking no actions matches the gold DB hash on 11 of 114 tasks — and on 3 of
those, only because the gold replay failed.

**Method.** Built the predicted environment with identical `initialization_data` /
`initialization_actions` but an **empty** message history, and compared `get_db_hash()` against the
gold environment's.

**Result: 11 / 114 (10%)** — IDs `10, 12, 24, 25, 50, 57, 62, 65, 67, 68, 105`.

This is materially better than feared (a pre-measurement review estimated 30–40%): **DB is more
discriminative than a read-only task count would suggest.**

**The interaction that matters.** Three of the eleven — **67, 68, 105** — pass *because* their gold
replay failed (A4), leaving the target DB unchanged, which a do-nothing agent trivially matches.

**The inversion.** All three are still gated by one live NL assertion each, so a null agent does
**not** collect full reward on them. The *experimental, hardcoded, WIP* judge is what prevents the
false positive that the database check admits. **Benchmark validity here depends materially on the
component its own source marks least trustworthy.** This is the observation the current research
question is built on.

> **Corrected, 27 Sep 2026 → [R-L1](FINDINGS.md), [R-L2](FINDINGS.md).** 67 and 68 pass because
> their gold makes no writes, not because replay failed — only 105 is a #499 artifact. And on six
> other null-pass tasks (10, 12, 25, 50, 57, 65) nothing blocks the false positive: a do-nothing
> agent scores full reward.

## A6 — Upstream #514 confirmed: the DB hash is order-sensitive on lists

**Claim.** `get_dict_hash` distinguishes list orderings that are semantically identical.

**Method.** `get_dict_hash({"payment_history":[A,B]}) == get_dict_hash({"payment_history":[B,A]})`
→ `False`.

**Consequence.** Financially identical orderings flip the verdict. **Do not fix this** — fixing it
breaks comparability with official v1.0.1 numbers. Compute both the raw and an order-canonicalized
hash and report both; the delta is itself a diagnostic.

---

## Phase A summary — what it ruled in and out

**Ruled out.** Any thesis resting on `COMMUNICATE` being retail's language-brittle grader (A1).
That component does not run. A design premised on it would have measured nothing, at full price.
See [DECISIONS.md](DECISIONS.md) D-004.

**Ruled in.** The live grader is an LLM judge (A2), hardcoded to one vendor, covering 35% of tasks
(A3), doing load-bearing validity work (A5). Whether its verdicts depend on the agent's model
family is a first-order validity question for every published τ³-retail number — and it is
measurable by **re-grading saved trajectories** rather than re-running them.

## Upstream contributions — **FILED 22 September 2026**

Filed as [@hagverdiyevr](https://github.com/hagverdiyevr) against v1.0.1 (`fc0055dc`):
**8 new issues ([#553–#560](https://github.com/sierra-research/tau2-bench/issues/553)) and
4 comments** on existing threads. Full record, including three claims that verification corrected
before publication, in [UPSTREAM_ISSUES.md](UPSTREAM_ISSUES.md).

**Two entries in this table were NOT filed, and the reconciliation is recorded rather than tidied
away:**

- **#1 (Py3.13 import failure) — WITHDRAWN.** No Python 3.13 is available on this machine and the
  `audioop`-importing dependency could not be located in the installed venv; it is most likely
  behind the voice extras, which are not installed. Asserting it publicly would have repeated
  [D-004](DECISIONS.md)'s error — claiming from our own notes rather than shipped reality. Only the
  `uv.lock` half ([A0b](FINDINGS.md)) was filed, as #560.
- **#7 (models-list endpoint) — NOT FILED.** It is an observation about provider account
  provisioning, not a tau2 defect, so it has no natural home in this tracker. Retained here as
  evidence ([B-L1](FINDINGS.md)); see [D-022](DECISIONS.md).

Two contributions filed were **not** in the original 13 and are appended below as 14 and 15.

| # | Contribution | Source finding | **Filed as** |
| --- | --- | --- | --- |
| 1 | Py3.13 import failure; one-line root cause, three fix options | A0 | **WITHDRAWN** — unreproducible |
| 2 | #499 characterization: the 16/2 stale-data vs hash-corrupting split, with task IDs; tasks 64 and 105 have logically impossible gold actions | A4 | comment on [#499](https://github.com/sierra-research/tau2-bench/issues/499#issuecomment-5772485558) |
| 3 | Null-agent baseline as a reusable validity check; the 67/68/105 × #499 false-positive mechanism *(corrected: 105 only — [R-L1](FINDINGS.md))* | A5 | comment on [#384](https://github.com/sierra-research/tau2-bench/issues/384#issuecomment-5774383986) |
| 4 | Docs/schema mismatch: `communicate_info` populated on 36 tasks, scored on none | A1 | comment on [#384](https://github.com/sierra-research/tau2-bench/issues/384#issuecomment-5774383986) |
| 5 | **NL-assertion judge cannot see tool calls** — `tool_calls` dropped by the `message.content` serialization; empty assistant turns leak as literal `"assistant: None"` into the judge prompt | B4 | **[#553](https://github.com/sierra-research/tau2-bench/issues/553)** |
| 6 | **`ToolCall` cannot carry `provider_specific_fields`**, so Gemini thought signatures survive only via LiteLLM's id-packing fallback (litellm#41534). A transport change breaks tau2's Gemini multi-turn tool calling silently | B-L6 | **[#559](https://github.com/sierra-research/tau2-bench/issues/559)** |
| 7 | Models-list endpoint advertises models the account cannot call (`gemini-2.5-flash-lite`, `gemini-3.1-flash-lite-preview`) — availability needs a real call | B-L1 | **not filed** — not a tau2 defect |
| 8 | **ACTION checker is order-sensitive on list arguments** — a call identical to gold except list order scores `action_match: false`. Sibling of #514; a false-negative mechanism wherever `ACTION` gates reward *(zero retail/airline tasks — [R-L5](FINDINGS.md))* | B-L7 | **[#557](https://github.com/sierra-research/tau2-bench/issues/557)** |
| 9 | **Judge cost is entirely unaccounted** — no cost/usage field exists for the NL-assertion judge; measured ~40% understatement of true run cost on judge-gated tasks *(an estimate; measured 32.8% — [R-L4](FINDINGS.md))* | B-L14 | **[#556](https://github.com/sierra-research/tau2-bench/issues/556)** |
| 10 | **Run-to-run noise floor for #540**, plus a reproducibility asymmetry: at temperature 0 one model family reproduces identical message contents/tool calls/rewards across repeat invocations and another does not | B-L15 | comment on [#540](https://github.com/sierra-research/tau2-bench/issues/540#issuecomment-5774393926) |
| 11 | **LiteLLM silently drops `seed` for the `gemini` provider** (`llm_utils.py:71`), so seeded reproducibility is unavailable for Gemini arms without the caller knowing | B-L15 correction | **[#558](https://github.com/sierra-research/tau2-bench/issues/558)** |
| 12 | **NL-judge path does not use upstream's own fence stripper** — `evaluator_nl_assertions.py:127` calls raw `json.loads` while `llm_utils.py:509` provides `extract_json_from_llm_response`; `gemini-3.8-flash` therefore crashes the evaluator. One-line wiring fix | B-L16 | **[#555](https://github.com/sierra-research/tau2-bench/issues/555)** |
| 13 | **`all([])` scores an empty judge response as a full pass**; duplicate, extra and mismatched verdicts are equally silent | B-L16 | **[#554](https://github.com/sierra-research/tau2-bench/issues/554)** |
| 14 | **Committed `uv.lock` is stale at tag v1.0.1** — records `tau2` 1.0.0 against `pyproject.toml`'s 1.0.1, so any `uv run` dirties a fresh clone. `uv sync --frozen` still succeeds (tested) | A0b | **[#560](https://github.com/sierra-research/tau2-bench/issues/560)** |
| 15 | **The judge is hardcoded with no override, and the override is worth 9.1 points** — patching `tau2.config` is a silent no-op; measured leniency spread across four judges on identical prompts | B1, [D-L2](FINDINGS.md) | comment on [#474](https://github.com/sierra-research/tau2-bench/issues/474#issuecomment-5774408352) |

---

# Phase B — Verification gates

*Gates B1 and B4 measured 20 Sep 2026, offline with a mocked transport. **USD 0.00.**
Script: `scripts/phase_b/b1_b4_judge_gates.py`. Raw: `results/phase_b/b1_b4_gates.json`.*

## B1 — The judge model is swappable · **PASS**

**Claim.** Patching `tau2.evaluator.evaluator_nl_assertions.DEFAULT_LLM_NL_ASSERTIONS` changes the
model that issues the judge call. Patching `tau2.config` does **not**.

**Method.** Mocked `evaluator_nl_assertions.generate`, captured the dispatched `model` kwarg across
three conditions.

| Condition | Dispatched model |
| --- | --- |
| baseline | `gpt-4.1-2025-04-14` |
| patch `evaluator_nl_assertions.DEFAULT_LLM_NL_ASSERTIONS` | `PATCHED/judge-x` ✅ |
| patch `tau2.config.DEFAULT_LLM_NL_ASSERTIONS` (negative control) | `gpt-4.1-2025-04-14` — **no effect** |

**Why the negative control matters.** `from tau2.config import DEFAULT_LLM_NL_ASSERTIONS` binds the
name into the evaluator module at import. Patching `tau2.config` is a **silent no-op** — it raises
no error and changes nothing. A study built on that mistake would have run every "different judge"
arm against `gpt-4.1` and reported a null result.

**Consequence.** The re-grading method in [PLAN.md](PLAN.md) works. The thesis survives its
highest-risk gate.

## B4 — The judge cannot see tool calls · **CONFIRMED (finding, not just a check)**

**Claim.** The NL-assertion judge grades agent behavior while structurally unable to observe the
agent's actions.

**Method.** Built a synthetic trajectory containing a realistic tool-calling turn
(`AssistantMessage(content=None, tool_calls=[...])` followed by a `ToolMessage`), captured the exact
prompt text sent to the judge.

**What the judge actually receives:**

```
user: Please cancel my order.
assistant: None
tool: {"order_id": "#W0000042", "status": "cancelled"}
assistant: Your order has been cancelled.
```

| Observable to the judge? | |
| --- | --- |
| Tool **name** (`cancel_pending_order`) | **NO** |
| Tool **arguments** (`order_id`, `reason`) | **NO** |
| Tool **result** | YES |
| Empty assistant turn leaks as literal `"assistant: None"` | YES |

**Root cause.** `evaluator_nl_assertions.py` serializes the trajectory as
`"\n".join(f"{message.role}: {message.content}" for message in trajectory)`.
`AssistantMessage.content` is `Optional[str]` and is `None` on a pure tool-calling turn, so the
`tool_calls` field is simply dropped.

**Two consequences, both material:**

1. **The judge infers actions from tool outputs and the agent's own narration.** An agent that
   *claims* to have cancelled an order and one that *did* differ, to the judge, only via the tool
   result line. This is the mechanism behind the field's standing criticism that a chatty model can
   beat a genuine tool-caller — confirmed here at the **judge** level, reproducibly.
2. **Every tool-calling turn injects a literal `assistant: None` line.** A typical retail trajectory
   with ~15 tool calls feeds the judge ~15 lines of `None`.

**Implication for the current thesis — it strengthens it.** If the judge grades largely on
*narration style* rather than observable actions, then style is exactly the channel through which
model-family affinity would operate. B4 makes the family-bias hypothesis more plausible, not less,
and gives it a concrete mechanism to test.

## B-live — first paid calls · **~USD 0.02 total**

*Measured 20 Sep 2026 with a Gemini AI Studio key, Tier 1 prepaid.
Scripts: `scripts/phase_b/step1`–`step3b`. Raw: `results/phase_b/*.json`.*

### B-L1 — Account access, and the model list over-reports

All three planned Gemini arms are reachable: `gemini-3.1-flash-lite`, `gemini-3.5-flash-lite`,
`gemini-3.8-flash`. 58 models visible, 41 support `generateContent`. `serviceTier: "standard"`
confirms **paid tier**, not free quota.

**But the models-list endpoint advertises models the account cannot call.** `gemini-2.5-flash-lite`
is listed, yet both `v1` and `v1beta` return HTTP 404: *"no longer available to new users… use
models/gemini-3.5-flash-lite"*. The shut-down `gemini-3.1-flash-lite-preview` is likewise listed.

> **Method rule:** model availability must be confirmed by an actual call. A listing is necessary,
> not sufficient.

Consequence: the cheap `gemini-2.5-flash-lite` arm ($0.10/$0.40, ~2.5× cheaper) is **unavailable**
to this account. Planned arms stand.

### B-L2 — Cost accounting is trustworthy · **PASS**

Three independent cost computations agree exactly on a live call:

| Source | Value |
| --- | --- |
| LiteLLM `response_cost` | `0.000287` |
| tau2 `get_response_cost()` | `0.000287` |
| Our own price table | `0.000287` |

**The silent-`0.0` bug is not triggered** for this model, and our table matches to the digit
(8 prompt × $0.25/1M + 5 completion × $1.50/1M). The USD 75 ledger can be built on these numbers.

### B-L3 — Reasoning tokens: a scare, then a correction

A *trivial* prompt ("reply with one word") returned `completion_tokens=190` of which
**`reasoning_tokens=189`** — 99.5% of billed output was thinking, for one visible token. With
`max_tokens=8` the model spent the entire budget thinking and returned **empty content**.

> **Operational rule:** `max_tokens` must exceed the thinking budget or the agent emits nothing
> while still being billed. `minimal` thinking is not *off*.

On a **realistic** prompt (real retail `policy.md` + a customer turn, 1508 input tokens) the picture
is far better — thinking is roughly a constant ~108 tokens, so it only dominates when the prompt is
tiny:

| | tokens | share |
| --- | ---: | ---: |
| input | 1508 | 65% of cost |
| output (visible) | 26 | |
| output (reasoning) | 108 | **28% of cost** |
| **per call** | | **$0.000578** |

**No budget blowout.** Extrapolating to ~11.5k input/call gives ≈$0.12/trajectory against the
planned $0.140 — the [REFERENCE](REFERENCE.md) estimate holds.

### B-L4 — `reasoning_effort` is silently ignored

`default`, `"low"` and `"none"` produced **byte-identical** usage (134 completion / 108 reasoning /
26 visible) and identical cost on `gemini-3.1-flash-lite`. Not a coincidence — the parameter is
dropped somewhere between LiteLLM and the API.

**We cannot dial thinking down on this model.** Treat the ~28% thinking overhead as fixed.

### B-L5 / Gate B8 — Thought signatures survive 8 tool-calling turns · **PASS**

Raw LiteLLM path, 8 forced tool calls (the defect in litellm#25322 typically appears only after
3–4): tool call on every turn, signature present on every turn, output tokens stable (176 → 111),
no repetition loop, no silent degradation.

### B-L6 / Gate B8b — …but tau2 preserves them only *by accident* · **PASS, with a fragility**

Gate B8 tested the raw path; Phase C runs through tau2's models. Re-tested with tau2's own
`generate()` and the real 16-tool retail schema — 8/8 turns clean, no degradation.

**The mechanism matters more than the pass:**

- `tau2.data_model.message.ToolCall` has only `{id, name, arguments, requestor}` — **no
  `provider_specific_fields`, no `thought_signature`, no `extra="allow"`**. Verified: the attribute
  is absent. `llm_utils.py:436` constructs it from the raw response, discarding everything else.
- tau2's outgoing `to_litellm_messages` rebuilds the call preserving **`tc.id`**.
- LiteLLM's *fallback* transport packs the signature into that id (`…__thought__<sig>`), observed
  at **372–604 characters**.

> So tau2's Gemini support is protected from litellm#25322 **only by LiteLLM's id-packing hack**.
> That hack is itself the subject of litellm#41534 (the packed id leaks into OpenAI's Responses API
> and causes HTTP 400 on router fallback). If LiteLLM changes that transport, tau2's Gemini
> multi-turn tool calling breaks **silently**.

**Phase C is safe on the Gemini arm**, with the runtime degradation detector kept on.


### B-L7 — The ACTION checker is order-sensitive on list arguments · **NEW DEFECT**

> **Qualified, 27 Sep 2026 → [R-L5](FINDINGS.md).** `ACTION` is in the reward basis of **zero** retail
> and airline tasks, so this changes no retail score. It is live on 32 telecom and 9 banking tasks.

**Claim.** A tool call identical to the gold action except for the *order* of a list-valued
argument is scored `action_match: false`.

**Method.** Ran retail task 73 end-to-end (`step4_floor_gate`). Compared the agent's
`return_delivered_order_items` call against the gold action field by field.

| | `item_ids` |
| --- | --- |
| gold | `7228247242, 2698416822, 8098621301, 3320557165` |
| agent | `3320557165, 2698416822, 8098621301, 7228247242` |

`order_id` equal, `payment_method_id` equal, `item_ids` equal **as a set**, same length,
**different order**. `compare_args` was `null`, so every argument is compared strictly.

Result: `action_match: false`, `action_reward: 0.0` — while `db_match: true` and the task scored
**reward 1.0**.

**Why it matters.** This is the sibling of #514 ([A6](FINDINGS.md)): tau2 has order-sensitivity in
**both** scoring paths — the DB hash *and* the action checker. Retail does not place `ACTION` in
`reward_basis`, so here it only produces a **misleading diagnostic** ("agent failed the required
write" when the agent performed it correctly). **For any task that does gate on `ACTION`, this is a
false-negative mechanism: a correct agent scores 0.** It is the inverse of upstream #327.

Observed on 3 of 40 checked gold actions across the calibration sample (2 of those 3 were task 72's
genuine failure).

### B-L8 / Gate B6 — Agent floor gate · **PASS**

**Method.** 7 clean DB-only `train` tasks, stratified by gold-action count (1,2,3,4,5,12,13),
excluding null-passable and replay-failing tasks. Agent and simulator both
`gemini/gemini-3.1-flash-lite`, 1 trial, `--max-steps 120`, seed 1001.

| | |
| --- | --- |
| Average reward | **0.857** (6/7) |
| Write actions correct | 12/14 (85.7%) |
| DB match | 6/7 |
| Termination | 7/7 normal `USER_STOP` — no step truncation |
| Agent / user errors | 0 / 0 |

The agent clears the floor decisively. The one failure (task 72) is genuine — both writes wrong,
`db_match: false`.

⚠️ **Headroom caveat.** 86% is *above* the 50–70% band the plan wanted. These are **DB-only** tasks,
which are the easier 74 of 114. The study population is the **40 judge-gated** tasks, whose
difficulty is still unmeasured and requires an OpenAI key to evaluate.

### B-L9 / Gate B7 — True cost is 6.6× below plan

Measured from tau2's persisted `agent_cost` + `user_cost`:

| | USD / trajectory |
| --- | ---: |
| min | 0.0137 |
| **mean** | **0.0212** |
| median | 0.0215 |
| max | 0.0300 |
| stdev | 0.0063 |

Planned estimate was **$0.140** ([REFERENCE](REFERENCE.md) §2) → **6.6× cheaper**.
User-simulator share measured at **14%**, not the estimated 21%.

**Cost tracks conversation length, not task complexity.** The 13-gold-action task cost $0.0268; the
2-action task cost $0.0300. Do not budget by task complexity.

**Budget consequence.** *(Superseded 2026-09-21: the design is now **320 trajectories / 1,280
judge evaluations** — 2 agents x 40 tasks x 4 trials, 4 judges. See [PLAN.md](PLAN.md).)*
Phase C projects to ~$5 on the Gemini arm rather than $17. The binding cost shifts to **Phase D
judging** — which cannot be sized until `gpt-4.1-2025-04-14` pricing is verified (gate B3).

### B-L10 / Gate B3 — Judge pricing verified, and Phase D sized from real trajectories

`gpt-4.1-2025-04-14` = **$2.00 in / $8.00 out** per 1M (LiteLLM registry, whose Gemini prices we
verified exact in [B-L2](FINDINGS.md)). That is **8x** our Gemini arm's input price.

Sized against the **8 real trajectories** we generated, reproducing the judge's exact
`f"{role}: {content}"` serialization:

| judge input tokens | min | mean | max |
| --- | ---: | ---: | ---: |
| per trajectory | 1,668 | **3,409** | 5,853 |

| Phase | Measured projection |
| --- | ---: |
| C — 240 trajectories @ $0.0212 | **$5.09** |
| D — 240 x 2 judges (gpt-4.1 + Gemini) | **$2.52** (worst case $3.84) |
| **Remaining study total** | **$7.61** against the $75 cap |

**The study is ~10x under budget.** Surplus should go to trials/arms, not scope creep — tasks are
capped at 40 by [A3](FINDINGS.md), so [D-010](DECISIONS.md)'s "tasks over trials" rule is already
satisfied and extra budget buys trials, judge replicates, or a third family.

**B4 corroborated in production data:** every real trajectory feeds the judge **4-11
`content: None` lines** (one per tool-calling turn), not just the synthetic probe.

### B-L11 / Gate B6b — Judge-gated tasks are far harder · **headroom resolved**

The DB-only floor gate ([B-L8](FINDINGS.md)) gave 0.857, *above* the 50-70% band we wanted. The
actual study population behaves very differently. 5 clean judge-gated `train` tasks
(89, 76, 109, 103, 43), same agent/simulator/settings:

| population | tasks | avg reward | write actions |
| --- | ---: | ---: | ---: |
| DB-only | 7 | **0.857** | 12/14 |
| **judge-gated** | 5 | **0.400** | 7/11 |

**Headroom concern resolved** — the study population sits comfortably below ceiling.
Cost was unchanged ($0.0194 vs $0.0212), so judge-gated tasks are *harder, not longer*.

### B-L12 — DB and the judge disagree on 3 of 5 judge-gated tasks

Because reward is the **product** of components, any disagreement zeroes the score. Per-task
decomposition from `reward_breakdown`:

| task | DB | NL | reward | what actually happened |
| --- | ---: | ---: | ---: | --- |
| 43 | 1.0 | 1.0 | 1.0 | both agree — pass |
| 89 | 1.0 | 1.0 | 1.0 | both agree — pass |
| **103** | **1.0** | **0.0** | 0.0 | **judge right, DB blind** |
| **109** | **0.0** | **1.0** | 0.0 | **judge wrong, DB right** |
| **76** | **0.0** | **1.0** | 0.0 | components measuring different things |

**Task 103 — the judge caught what the database could not.** All four gold actions matched and
`DB = 1.0`, yet the user had asked for the *cancelled* order's tracking number (`286422338955`)
and the agent supplied the *returned* order's (`682308736931`), explicitly saying so. The correct
number appears **only inside a tool result**, never in an agent message. DB alone would have
scored this a pass. This corroborates [A5](FINDINGS.md): the WIP judge is doing real validity work.

**Task 109 — the judge missed what the database caught.** Gold expected the address change on
`#W1603792`; the agent modified `#W1092119`. The assertion reads *"Agent should make changes to
address on order and user profile"* — too vague to distinguish *which* order, and per
[B4](FINDINGS.md) the judge cannot see tool-call arguments. It marked the assertion met.

**Task 76 — orthogonal components.** The agent cancelled both correct orders but **swapped the
`reason`** between them (`"no longer needed"` <-> `"ordered by mistake"`), so `DB = 0`. The single
NL assertion concerned a price it stated correctly, so `NL = 1`.

> **Interpretation.** DB and the judge are partially independent instruments with different blind
> spots, combined multiplicatively. Neither dominates: the judge caught a genuine failure DB missed
> (103) and missed a genuine failure DB caught (109).

### B-L13 / Gates B2 + B5 — Re-grading works; judge noise is bounded below ~9%

**B2 PASS.** Re-grading 5 **saved** trajectories reproduced tau2's own recorded verdict on
**11/11 assertions (100%)**, with every message rebuilt intact (21/21, 33/33, 24/24, 38/38, 28/28).
The re-grading method ([D-009](DECISIONS.md)) is validated end to end — this is the core tool.

**B5 PASS.** 3 repeats per trajectory at the pinned `temperature = 0.0`: **11/11 assertions stable**,
zero flips across 33 observations.

> Reported honestly: zero observed flips does **not** prove zero noise. By the rule of three, 0/33
> bounds the flip rate at roughly **<9% (95%)**. Sufficient that judge noise will not swamp a real
> effect, but replicate grading stays in the Phase D design and results are reported against this
> bound.

### B-L14 — tau2 does not account for judge cost at all

> **Magnitude superseded, 27 Sep 2026 → [R-L4](FINDINGS.md).** The figures below are estimates that
> assume 300 output tokens. Measured in Phase D the judge is **32.8%** of true cost (20% vs 58% by arm).

`SimulationRun` carries only `agent_cost` and `user_cost`. There is **no cost or usage field
anywhere** for the NL-assertion judge — not on the run, not in `reward_info`, not in `info`.

The judge is `gpt-4.1-2025-04-14` at **$2.00/$8.00 per 1M** — 8x our agent's input price. On our
5 judge-gated tasks, tau2 reported **$0.1123** while the true cost was **~$0.157**: a **~40%
understatement**.

**Anyone reporting τ³ cost from tau2's own numbers understates it on judge-gated tasks** — including
leaderboard submissions, where cost reporting is explicitly invited.

### B-L15 / Gate B9 — Run-to-run noise floor, and a determinism asymmetry between families

**Upstream #540 asks what the run-to-run noise floor of τ³ baselines is. It has no published
answer.** Measured here by re-running an identical configuration under different seeds as
**separate invocations**.

**Caching ruled out first:** `LLM_CACHE_ENABLED = False` (config.py:47), env unset,
`litellm.cache = None`, and wall-clock durations differ across runs (129.5s / 130.9s / 133.8s).
Every run performed real inference.

> ### ⚠️ CORRECTION issued 2026-09-21 — "byte-identical" was WRONG
>
> An independent verification pass re-compared the **complete** simulation objects across the
> three runs, not just the fields our own script hashed. **Zero simulations were byte-identical.**
> `scripts/phase_b/` hashed only `role + content`, so the claim asserted more than the method could
> support. The original wording is preserved below so the error stays on the record.
>
> **What is actually true, and was verified field by field:**
> - Message **contents** identical across all 3 runs, 5/5 tasks.
> - Tool-call **names and arguments** identical, 5/5 (t43 5 calls, t76 12, t89 6, t103 12, t109 9).
> - Per-task **rewards** identical (1.0/0.0/1.0/0.0/0.0), aggregate 0.400000 in all three runs.
> - `agent_cost + user_cost` identical to the cent.
> - **Differing:** message ids, tool-call ids (which carry the LiteLLM thought-signature payload),
>   timestamps, durations, and the gpt-4.1 judge's free-text `justification` — the judge's
>   verdicts (`met` flags) were identical in all 22 pairwise comparisons, only its prose varied.
>
> **Second correction — "across seeds" is also wrong for the Gemini arm.** LiteLLM drops the
> `seed` parameter for the `gemini` provider (`vendor/tau2-bench/src/tau2/utils/llm_utils.py:71`),
> so seeds 1001/1002/1003 never reached the API. Those were **three repeat invocations with no
> seed applied**. This *strengthens* the stability observation — output was stable without any
> seed pinning — while invalidating how it was described.
>
> **Corrected statement:** *in a 5-task, ~15-minute pilot, three repeat invocations of
> `gemini-3.1-flash-lite` at temperature 0 produced identical message contents, tool calls,
> rewards and costs; the OpenAI arm produced none identical across 3 tasks.* Scope is a pilot
> observation, not a structural property. **Re-verify on the Phase C output before reporting.**

#### Result — the two agent families behave oppositely at the same temperature 0.0

| Agent | Seeds | Byte-identical conversations | Cost spread |
| --- | --- | --- | --- |
| `gemini/gemini-3.1-flash-lite` | 1001, 1002, 1003 | **5/5** | **$0.000000** |
| `gpt-4.1-nano` | 2001, 2002 | **0/3** | up to **2.6×** on one task ($0.00476 → $0.01254) |

The Gemini arm reproduced identical **message contents**, message counts, rewards and costs to
the cent across three independent runs (see the CORRECTION above — *not* byte-identical). The OpenAI arm reproduced
**none** of three, despite identical settings, identical simulator, and `temperature = 0.0` on both.

Aggregate rewards were stable for both (Gemini 0.400 ×3; OpenAI 0.333 ×2), so the divergence is in
*trajectories*, not in headline score — at this sample size.

#### Consequences — these matter more than the number

1. **Trials are informative for one arm and not the other.** With a deterministic arm, `pass^4`
   equals `pass^1` **by construction**, and four trials produce four identical copies. Any
   variance-based statistic computed across arms is comparing a structural zero against a real
   quantity.
2. **Published τ³ variation cannot come from seeds** for a deterministic arm. It must come from
   temperature settings, model or provider drift, or harness changes. Note τ-bench v1 ran its user
   simulator at **temperature 1.0**; τ³ defaults to **0.0** ([REFERENCE](REFERENCE.md) §3).
3. **Cost forecasting is arm-dependent.** A 2.6× per-task cost swing on the OpenAI arm means
   budget estimates for it need a range, not a point.

#### Scope — do not overstate

Two models, one domain, 5 tasks (Gemini) and 3 tasks (OpenAI), 3 and 2 runs respectively, inside a
~15-minute window. This shows determinism **holds for one arm and fails for another under identical
conditions**; it does not establish that either behaviour is stable over days, across domains, or
across other models. Provider-side updates could change it at any time.

#### Effect on the frozen design — **no deviation taken**

[PREREGISTRATION](PREREGISTRATION.md) §4.1 specifies T = 4. It would be cheaper to drop to T = 1 on
the deterministic arm, saving roughly USD 3. **We are not doing that.** Touching a frozen design to
save 4% of a budget with USD 74 remaining is a bad trade against the integrity the freeze exists to
protect. T = 4 is retained for both arms; the determinism is **reported as a result**, and `pass^4`
for the Gemini arm is disclosed as trivially equal to `pass^1` rather than presented as a
reliability measurement.


*Not started. B5 (judge noise floor) and B6 (agent floor gate) are next and require spend.*

> **Process note:** `step3`/`step3b` were not cost-instrumented — a gap in our own tooling, since
> they are the most informative cost samples we have (8 turns × 16 real tool schemas). Step 4 must
> capture cost via tau2's persisted `agent_cost`/`user_cost`.

# Phase C — Trajectory generation

## C-L1 — Smoke invocation: 1 of 8 complete · **$1.21**

*First confirmatory invocation, `phaseC_t1_gem` (Gemini agent, seed 1001), 21 Sep 2026.
Artifact: `results/artifacts/phaseC_t1_gem.json`. Journal: `results/phase_c/run_journal.json`.*

| Metric | Value | Against expectation |
| --- | --- | --- |
| Simulations | 40 / 40 | complete |
| Mean reward | **0.675** (27 pass / 13 fail) | 5-task pilot read 0.400 — the pilot drew harder tasks |
| DB component | 0.775 | |
| NL component | 0.850 | |
| **Components disagree** | **11 / 40 (28%)** | pilot suggested 3/5; 28% is the honest rate |
| Terminations | 40 × `user_stop` | **no truncation, no errors** |
| Cost / trajectory | mean **$0.02117** | matches the $0.0212 B-L9 measurement exactly |
| Cost tail | max **$0.12413** | **one task cost 5.9× the mean** — new observation |
| Duration | 19.4 min (29.1 s/task) | 8 invocations ≈ 2.5 h wall clock |
| Retries / perm. failures | 0 / 0 | A-002's `--max-retries 0` held |
| `info.git_commit` | recorded (`d56ed425`) | the R3 'unknown' defect is fixed going forward |

**Three things this changes:**

1. **Headroom is real but tighter than hoped.** 0.675 sits just above the 50–70% band. There is
   room for an effect, but the agent is not far from ceiling on this population.
2. **The judge component genuinely varies.** 28% component disagreement at n=40 means the NL
   component is not a constant — so the judge study has something to measure. This materially
   softens the null preview in [B-L16](FINDINGS.md), which rested on 5 trajectories where all
   four judges happened to agree.
3. **Cost has a long tail.** Mean $0.0212 but max $0.124. Budget by the mean, but expect
   individual invocations to vary; the per-invocation estimate should not be read as a bound.

**Free determinism re-test at scale.** The design runs the Gemini arm four times over the *same*
40 tasks at seeds 1001–1004, and LiteLLM drops `seed` for that provider
([B-L15 correction](FINDINGS.md)). So trials 2–4 constitute an n=40 replication of the
reproducibility claim **at no extra cost** — it is already in the protocol. This is the check
[CLAUDE.md](../CLAUDE.md) requires before `pass^k` is reported for that arm.

## C-L2 — Determinism replicates at n=40, and it breaks `pass^k` comparability

*8/8 invocations, 320 simulations, **zero** `infrastructure_error`, 7,516 logged attempts.
Script: `scripts/phase_c/analyze_phase_c.py`. Raw: `results/phase_c/determinism_n40.json`.*

[CLAUDE.md](../CLAUDE.md) required this before `pass^k` could be reported for the Gemini arm,
because [B-L15](FINDINGS.md) rested on 5 tasks in a ~15-minute window. Phase C runs the same 40
tasks four times per arm, and LiteLLM drops `seed` for the gemini provider, so these are four
repeat invocations — a free n=40 replication.

| Identical across 4 invocations | `gemini-3.1-flash-lite` | `gpt-4.1-nano` |
| --- | ---: | ---: |
| message contents | **40/40 (100%)** | 0/40 (0%) |
| tool calls | **40/40 (100%)** | 4/40 (10%) |
| **rewards** | **40/40 (100%)** | 32/40 (80%) |
| whole object | 0/40 | 0/40 |

**The pilot claim holds at scale.** Whole-object identity remains 0/40 for both — ids and
timestamps always differ — which is exactly the correction [B-L15](FINDINGS.md) carries.

### Consequence: `pass^k` means different things in the two arms

| | pass^1 | pass^4 | gap |
| --- | ---: | ---: | ---: |
| `gemini-3.1-flash-lite` | 0.675 | **0.675** | **+0.000** |
| `gpt-4.1-nano` | 0.138 | 0.050 | **+0.088** |

For the Gemini arm reward is identical on **all 40** tasks, so **`pass^4` equals `pass^1` by
construction, not by measurement** — it must be reported as a determinism result. For the OpenAI
arm reward genuinely varied on **8/40** tasks (`24, 40, 44, 45, 59, 60, 67, 70`), so its `pass^k`
is a real reliability measurement with a meaningful 8.8pp drop.

> **`pass^k` is therefore not comparable across these arms.** One side is a structural constant,
> the other a measured quantity. Any cross-arm variance statistic must state this or it is
> comparing a zero to a number. This is the asymmetry [D-018](DECISIONS.md) anticipated.

## C-L3 — The OpenAI arm is floor-bound, which constrains what Phase D can conclude

| arm | pass^1 | DB | NL | components disagree | $/traj |
| --- | ---: | ---: | ---: | ---: | ---: |
| `gemini-3.1-flash-lite` | **0.675** | 0.775 | 0.850 | 44/160 (28%) | 0.02117 |
| `gpt-4.1-nano` | **0.138** | 0.263 | 0.362 | 56/160 (35%) | 0.00549 |

`gpt-4.1-nano` is **far weaker on τ³-retail than expected** — pass^1 of 0.138 against the Gemini
arm's 0.675. The [B6 floor gate](FINDINGS.md) wanted 50–70%; the Gemini arm sits in band, the
OpenAI arm is well below it.

**Why this matters for the primary estimand, stated before Phase D runs:** the judge DiD compares
how two judge families score each agent's trajectories. If one agent's trajectories are
overwhelmingly failures, judges have less to disagree about on that arm, and any interaction is
estimated on a narrower base. The NL component still varies (0.362, and components disagree on
35% of that arm's trajectories), so there is signal — but **capability is now heavily confounded
with family**, and no claim may attribute an interaction to family without stating that the two
arms differ by 54 percentage points in baseline success.

This is a limitation to declare, not a defect to fix: the arms were frozen in
[§4.2](PREREGISTRATION.md) and changing them now would be exactly the post-hoc choice the
pre-registration exists to prevent.

# Phase D — Judge re-grading

*Complete, 22 Sep 2026. **1,792 evaluations** (1,280 base + 512 §6.3 replicates) over the 320
Phase C trajectories. **0 unsettled, 0 anomalies, 0 truncations, 1,792/1,792 priced.** USD 5.4086.
Runner: `scripts/phase_d/run_phase_d.py`. Analysis: `scripts/phase_d/analyze_phase_d.py`.
Raw: `results/phase_d/regrade_journal.jsonl`, `results/phase_d/analysis.json`.*

Every planned unit was settled and the journal matches the manifest **exactly** — 1,792 planned,
1,792 settled, 0 missing, 0 unplanned, 0 duplicated.

## D-L1 — The incumbent judge shows **no detectable family bias**, and the study is underpowered to call that equivalence

**The pre-registered primary estimand ([§3](PREREGISTRATION.md)), computed as specified:**

```
FamilyBias = +0.0063    95% CI [-0.0875, +0.1062]    (task-level cluster bootstrap, B=10,000, n=40 tasks)
```

The interval contains zero, so this is a **null claim** and [§6.5](PREREGISTRATION.md) requires it
be defended rather than merely stated.

**TOST against the pre-specified ±5pp margin: NOT equivalent.** The realized MDE is **0.1367** —
the design can detect a ~14-point interaction, not a 5-point one. What the data *does* rule out is
**|FamilyBias| > 0.1062**.

The gap is structural, not a budget problem. Between-task SD is **0.3087** across a task set
**hard-capped at 40** by the benchmark ([A3](FINDINGS.md)). More trials shrink within-task noise,
which is not the binding term; only more *tasks* would move the MDE, and there are none.

**The §6.2 S1 tier control agrees, which is the more informative result.** A genuine family effect
must appear in both tiers:

| Tier | FamilyBias | 95% CI |
| --- | ---: | --- |
| High (`gpt-4.1` vs `gemini-3.8-flash`) | +0.0063 | [-0.0875, +0.1062] |
| Low (`gpt-4.1-mini` vs `gemini-3.1-flash-lite`) | +0.0000 | [-0.0875, +0.0750] |

Both are indistinguishable from zero and neither carries the other. Two independent tiers pointing
at nothing is stronger than one tier's interval alone.

**Mandatory interpretation constraint ([C-L3](FINDINGS.md)).** The OpenAI arm is floor-bound —
pass^1 **0.138** vs the Gemini arm's **0.675**. Capability is confounded with family by 54 points
of baseline success. This null is therefore *"no family bias detectable **between these two
specific agents**"*, and cannot be generalized to a family claim.

## D-L2 — Judges differ in **leniency by 9.1 points** — which a naive contrast would have reported as bias

Mean NL-assertion reward, **same 320 trajectories, same captured prompt**, only the grader changes:

| Judge | OpenAI arm | Google arm | Overall |
| --- | ---: | ---: | ---: |
| `gpt-4.1-mini` | 0.394 | 0.900 | **0.647** |
| `gpt-4.1-2025-04-14` (incumbent) | 0.369 | 0.850 | 0.609 |
| `gemini/gemini-3.1-flash-lite` | 0.344 | 0.850 | 0.597 |
| `gemini/gemini-3.8-flash` | 0.312 | 0.800 | **0.556** |

**A 9.1-point spread between the strictest and most lenient judge.** Swapping the grader alone
moves a reported score by more than most leaderboard gaps.

This is the finding [D-009](DECISIONS.md) predicted and the reason the DiD control term is
mandatory. Taking the incumbent's **+0.056** advantage over `gemini-3.8-flash` on the OpenAI arm
as evidence of favouritism would be wrong: it grades the *Google* arm **+0.050** higher too. It is
a uniformly more lenient judge, not a biased one. **The control term is what separates those, and
without it this study would have reported a false positive.**

**Capability moves leniency more than family does (§6.2 S2).** Within each family the low tier is
the *more* lenient: OpenAI −0.037 high-vs-low, Google −0.041. Nearly identical in both families —
so the ordering tracks capability tier, not vendor.

## D-L3 — `gemini-3.8-flash` fenced **448 of 448** responses; upstream's parser would crash every time

[B-L16](FINDINGS.md) found the NL-judge path calls raw `json.loads` while upstream's own
`extract_json_from_llm_response` sits unused one module away, and that `gemini-3.8-flash` fences
its JSON in Markdown. At n=5 that was a defect report. At **n=448 it is a 100% failure rate**:

| Judge | Fenced |
| --- | ---: |
| `gemini/gemini-3.8-flash` | **448/448 (100%)** |
| `gpt-4.1-2025-04-14` | 0/448 |
| `gpt-4.1-mini` | 0/448 |
| `gemini/gemini-3.1-flash-lite` | 0/448 |

Anyone pointing τ³'s judge at `gemini-3.8-flash` gets a crash on **every single task**, not an
occasional one. The fail-closed adapter is not defensive polish — it is the only reason a quarter
of this study exists. Strengthens upstream contribution #12.

**Alias resolution, recorded because the freeze uses two aliases:** `gpt-4.1-mini` →
`gpt-4.1-mini-2025-04-14` on all 448 calls; no judge served more than one snapshot, so no drift
occurred during the run.

## D-L4 — LiteLLM reports **no cost on ~0.4% of successful calls**, and summing them as zero is the defect we document in others

Reconciling two independent instruments over the same 1,792 evaluations:

| Instrument | Total |
| --- | ---: |
| Per-evaluation journal | $5.408567 |
| Attempt log (LiteLLM callback) | $5.400018 |
| **Difference** | **$0.008550** |

The gap resolves **exactly**: 2 attempt-log rows carry `usd: None` while the journal priced them
($0.007924 + $0.000626). `response_cost` is not reliably populated in `_hidden_params` at the
moment the success callback fires.

**It is not confined to Phase D.** Across Phase C, **30 of 7,516** successful attempts (0.40%) are
unpriced, spread over **all four models** — `gemini-3.1-flash-lite` (25), `gpt-4.1-nano` (3),
`gpt-4.1` (3), `gpt-4.1-mini` (1). A model-agnostic timing race, not a pricing gap.

**Our own code had the defect it documents.** `attempt_logger.summarize()` and
`build_spend_ledger.py` both summed `row.get("usd") or 0.0`, silently billing an unpriced success
at zero — the identical shape to upstream's `get_response_cost()` returning `0.0` on exception,
and the fourth instance of [D-020](DECISIONS.md). Both now count unpriced successes and mark any
total containing one a **LOWER BOUND**. The ledger prints the warning rather than a clean number.

Magnitude is small (cents) but the *claim* was wrong: Phase C's "$7.33 measured" was a lower bound
presented as a measurement.

## D-L5 — Re-grading reproduces the incumbent's own verdicts at **99.1%**, and the incumbent is the only judge that flips

**Mechanism validation at full scale.** Replaying each trajectory to `gpt-4.1-2025-04-14` — the
model tau2 itself used — reproduces tau2's recorded verdict on **317 of 320** trajectories
(**99.1%**). Prompt identity by capture ([B-L16](FINDINGS.md)) holds at n=320, so a cross-judge
difference is attributable to the judge and not to a reconstructed prompt.

| Judge | Agrees with tau2's recorded verdict |
| --- | ---: |
| `gpt-4.1-2025-04-14` (the model tau2 used) | **317/320 (99.1%)** |
| `gpt-4.1-mini` | 298/320 (93.1%) |
| `gemini/gemini-3.1-flash-lite` | 295/320 (92.2%) |
| `gemini/gemini-3.8-flash` | 290/320 (90.6%) |

**§6.3 noise floor — and an independent replication of [C-L2](FINDINGS.md).** 256 repeated-grading
pairs over the pre-drawn 20% sample:

| Judge | Flipped | Of | Rate |
| --- | ---: | ---: | ---: |
| `gpt-4.1-2025-04-14` | **1** | 64 | 0.016 |
| `gpt-4.1-mini` | 0 | 64 | 0.000 |
| `gemini/gemini-3.8-flash` | 0 | 64 | 0.000 |
| `gemini/gemini-3.1-flash-lite` | 0 | 64 | 0.000 |
| **Overall** | **1** | **256** | **0.004** |

0.4%, far inside [B-L13](FINDINGS.md)'s <9% bound, so no downgrade to a bounded null is triggered.

The single flip is the **incumbent**: `phaseC_t1_gem` task 105, graded **1.0 / 0.0 / 1.0** across
three byte-identical requests at temperature 0. All three non-incumbent judges flipped zero times.

C-L2 found `gpt-4.1-nano` nondeterministic and `gemini-3.1-flash-lite` deterministic at temperature
0 **in the agent role**. This reproduces that asymmetry **in the judge role**, on a different task
set, with a different instrument — the same 3/320 residual disagreement in the table above is the
same phenomenon. **The benchmark's official grader is not reproducible**, and its own
irreproducibility is the floor under every score it assigns.

> **Qualified, 27 Sep 2026 → [R-L8](FINDINGS.md).** One flip in 256 does not establish an asymmetry
> (Fisher p = 0.50), and the 3 residual disagreements are not shown to be the same effect. What stands:
> the default judge flipped once on identical requests, so its floor is not zero.

# Phase E — Completing the pre-registered analysis

*22 Sep 2026. **USD 0.00** — no new data; these are the [§6.2](PREREGISTRATION.md) secondaries
computed over Phase C components and Phase D verdicts. Script:
`scripts/phase_d/analyze_phase_d.py`.*

**A label was wrong and is corrected here.** The block the analyzer first printed as "S3" was
*mechanism validation* (does a re-grade reproduce tau2's own verdict), not §6.2's S3 (component
decomposition). It is now printed as **M1**, and the real S3 is below. Passing a convenience
metric off as a pre-registered secondary is precisely the drift the freeze exists to stop.

## E-L1 — DB and the judge disagree on **31% of all trajectories**; the judge passes 64 that the database fails

[§6.2](PREREGISTRATION.md) S3, as a 2×2 contingency. Reward is the **product** of the two
components, so an additive "contribution" split would be meaningless and is not computed.

| Arm | n | DB+ NL+ | DB+ NL− | DB− NL+ | DB− NL− | **Disagree** |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| OpenAI | 160 | 22 | 20 | 36 | 82 | **56 (35.0%)** |
| Google | 160 | 108 | 16 | 28 | 8 | **44 (27.5%)** |
| **Both** | **320** | **130** | **36** | **64** | **90** | **100 (31.2%)** |

[B-L12](FINDINGS.md) proposed partial independence from 5 trajectories. At **n=320 it holds**: the
two instruments disagree on **roughly a third of all trajectories**.

The **DB− NL+** cell is the one to read twice. On **64 trajectories (20% of the corpus)** the LLM
judge certifies the agent did what was asked while the database says the world was not changed
correctly. Multiplicative scoring saves the final number — those trajectories score 0 regardless —
but **the judge alone would have passed one trajectory in five that the database fails**. Anyone
using an NL judge without a state check inherits that error rate.

The mirror cell, **DB+ NL− (36)**, is the reverse: the right end state reached without the
narration the assertions demand.

## E-L2 — The cheaper agent costs **10× more per reliably-completed task**

[§6.2](PREREGISTRATION.md) S5, judge cost included ([B-L14](FINDINGS.md): tau2 omits it entirely).
Phase D's re-grading cost is split evenly across arms — each contributed 160 of 320 trajectories.

| Arm | Generation | Judge | Total | k=1 successes | **Cost / success** | k=4 all-4 | **Cost / reliable task** |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| OpenAI (`gpt-4.1-nano`) | $2.8363 | $2.7043 | $5.5406 | 22/160 | **$0.2518** | 2/40 | **$2.7703** |
| Google (`gemini-3.1-flash-lite`) | $4.4936 | $2.7043 | $7.1979 | 108/160 | **$0.0666** | 27/40 | **$0.2666** |

**The ranking inverts depending on what you count.** Per *attempt*, the OpenAI arm is the cheaper
one — it generated 160 trajectories for $2.84 against $4.49. Per *success* it is **3.8× more
expensive**. Per *reliably-completed task* (all four trials passing) it is **10.4× more expensive**.

Reliability compounds: the arm that succeeds 13.8% of the time needs ~7 attempts per success, and
far more than that for four-in-a-row. A cost-per-token or cost-per-attempt comparison — the
default in most model marketing — points at the wrong model here by an order of magnitude.

> Cost per success is **undefined, never zero**, at zero successes ([§6.5](PREREGISTRATION.md)).
> Both arms have successes, so both are defined.

## E-L3 — The pre-specified sensitivity analysis does not change the conclusion

[§4.3](PREREGISTRATION.md) disclosed that 5 tasks (**89, 76, 109, 103, 43**) were inspected during
Phase B calibration, and required a pre-specified sensitivity analysis excluding them.

| Set | FamilyBias | 95% CI | n |
| --- | ---: | --- | ---: |
| All tasks | **+0.0063** | [−0.0875, +0.1062] | 40 |
| Excluding the 5 disclosed | **−0.0143** | [−0.1143, +0.0929] | 35 |

The point estimate moves by 0.0205 and **changes sign**, which is unsurprising when both estimates
are indistinguishable from zero and the shift is a seventh of the interval's width. Both intervals
contain zero; **the conclusion is unchanged**, as §4.3 required.

## E-L4 — ITT and per-protocol are identical

[§6.4](PREREGISTRATION.md) requires both. Phase C completed with **zero `infrastructure_error`
trajectories**, so there is nothing to exclude and the two analyses coincide at **n = 40 per
cell**. The distinction was not idle: [A-004](PREREGISTRATION_AMENDMENTS.md) had to settle whether
such trajectories are scored zeros or missing data, and an earlier discarded invocation had 6.

# Post-release review — what our public posts got wrong, and what others found

*26–27 Sep 2026. **USD 0.00** (one unintended judge call was rejected unbilled — R-L12). Prompted by
three replies to the 12 posts filed as `@hagverdiyevr` on 22 Sep. Every claim in all 12 was
re-checked against v1.0.1 (`fc0055dc`) and this study's committed artifacts.
Script: `scripts/review/verify_post_claims.py` (offline; the judge is patched to raise if called).
Raw: `results/review/post_claims.json`.*

**Verdict on the 12 posts.** 2 hold fully (#555, #560); 3 hold with a small slip (#553, #558,
#474); **7 need correction** (#554, #556, #557, #559, and the comments on #499, #384, #540).
**No reported bug turned out not to exist** — the mechanism behind all eight issues re-verified.
The errors are in scope and precision, and nearly all have one shape: **prose that went further
than the repro under it.** The repros were run before filing ([D-022](DECISIONS.md)); the
sentences around them were not checked against them.

| Shape of the error | Where |
| --- | --- |
| A co-occurrence read as a cause | R-L1 — A5, #499, #384 |
| "One write failed" read as "nothing changed" | R-L3 — #499 |
| An estimate reported as a measurement | R-L4 — B-L14, #556, CLAUDE.md, README |
| A single observation read as a pattern | R-L8 — D-L5, D-021, #540, README |
| A subset described as the whole | R-L7 — #559 |
| An outcome asserted without tracing the code path | R-L6 — #554 |

These are the [D-020](DECISIONS.md) pattern — a weak signal treated as proof — turned on our own
prose rather than our code.

## R-L1 — The null agent passes 67 and 68 because they need no writes, not because replay failed

*Supersedes the causal claim in [A5](FINDINGS.md) ("67, 68, 105 pass because their gold replay
failed"), repeated in the public comments on #499 and #384.*

Replaying the full gold sequence of all 11 tasks a null agent passes:

| Cause of the null-agent match | Tasks | n |
| --- | --- | ---: |
| **Gold makes no writes** — "nothing changed" is the correct end state | 10, 12, 24, 25, 50, 57, 62, 65, **67, 68** | **10** |
| **A failed gold write** — the target is the untouched database | **105** | **1** |

67 and 68 do have failing gold actions, but they are **reads** (`find_user_id_by_name_zip`), which
change nothing; they would be null-passable if every read succeeded. So A5's "three #499 false
positives" is **one**.

**Why the test did not catch it.** `test_phase_a_regression.py` asserts that three tasks *both*
pass with a null agent *and* have replay failures. That is true. The prose read the co-occurrence
as causation. Independently confirmed by Ruler4396 on #499 (26 Sep): "Tasks 67/68 have no
reference writes."

## R-L2 — A do-nothing agent scores **full reward** on 6 of 114 retail tasks

*New. A5 checked only the three tasks it believed were #499 artifacts, and concluded that the judge
blocks the null agent's false positive. For those three it does; for six others nothing does.*

tau2's **own evaluator** (`EvaluationType.ALL`) on a two-message conversation in which the agent
calls no tool and says only "Sorry, I can't help with that. Goodbye.":

| Task | DB | NL_ASSERTION | **Reward** | Split |
| --- | ---: | ---: | ---: | --- |
| 10, 25, 50, 57 | 1.0 | 1.0 | **1.0** | train |
| **12, 65** | 1.0 | 1.0 | **1.0** | **test** |
| 24, 62, 67, 68, 105 | 1.0 | judge-gated | not free | — |

DB passes because the gold makes no writes; NL passes because these six list `NL_ASSERTION` in their
basis but carry no assertions, so `evaluator_nl_assertions.py:38` returns `1.0` without calling the
judge. On 10, 12 and 50 the gold's intended behaviour is a hand-off (`transfer_to_human_agents`);
because `ACTION` is not scored in retail (R-L5), declining to hand off scores the same.

**A5's "inversion" survives, narrowed:** on 5 of the 11 null-pass tasks the judge is what stops a
do-nothing agent collecting full reward. On the other 6, nothing does.

## R-L3 — Task 64: a do-nothing agent fails it, but its target is still half-applied

> **Superseded, 27 Sep 2026 → [R-L13](FINDINGS.md).** The mechanism below is right (64_7 lands, an
> empty trajectory scores DB 0.0). The interpretation is **wrong**: 64's target is not half-applied,
> it is correct, and the 11/16 shipped matches are genuine successes.

*Supersedes the mechanism [A4](FINDINGS.md) and the #499 comment gave for task 64. A4's row
"WRITE · 2 · target DB hash is wrong" stands for both tasks.*

| Step | Action | Result |
| --- | --- | --- |
| `64_6` | `exchange_delivered_order_items` | **fails** — "Non-delivered order cannot be exchanged" |
| `64_7` | `modify_pending_order_items` | **succeeds, changes the DB** |

So 64's target is *not* the untouched database, and tau2's evaluator scores an empty conversation
**DB 0.0** on it (R-L2 run). Our comment's "the target hash is computed from an un-mutated
database" is true for **105 only** — corrected by justavibedev (23 Sep), verified here.

The underlying problem is real, though. The target includes `64_7` and omits the impossible exchange,
and in the benchmark's **own shipped results** (`data/tau2/results`):

| Task | Stored simulations | `db_match = true`, reward 1.0 |
| --- | ---: | ---: |
| 64 | 16 | **11** |
| 105 | 16 | **10** |

Most published runs of both tasks match a gold state whose reference never fully applied. Added by
Ruler4396 (26 Sep); reproduced here on our pin.

*Aside, unverified:* task 105's only gold action is labelled `106_0`. Possibly a labelling slip in
the task data; not investigated.

## R-L4 — Judge cost, measured: **32.8%** of true cost, not ~40%

*Supersedes the magnitude in [B-L14](FINDINGS.md) and in #556; the direction is unchanged.*

B-L14 priced the judge from its serialized prompt with an **assumed** 300 output tokens. Phase D
measured the same default judge over the same 320 base trajectories:

| | Estimated (B-L14, #556) | **Measured (Phase D)** |
| --- | ---: | ---: |
| Judge cost | $2.7898 | **$2.0855** (mean 148 output tokens) |
| Judge share of true cost | 39.5% | **32.8%** |
| … Gemini arm | 30% | **20.4%** |
| … OpenAI arm | 60–61% | **58.1%** |

The argument #556 makes — the hidden share differs by agent model, so cost *comparisons* are
biased — **gets stronger** (20% vs 58%). Three sentences in #556 are wrong: "understates true cost
by 65%" (tau2 reports 67% of true cost), "agent cost varies by an order of magnitude" (**3.9×**), and
"judge cost is roughly fixed per task" (measured, **40% higher** on the OpenAI arm).

The spend ledger is **not** affected: Phase C totals come from measured attempt logs, and the
estimate applies only to pre-Phase-C runs. This corrects an analytic claim, not money.

## R-L5 — ACTION is scored on zero retail tasks, and `compare_args: []` is deliberate

*Qualifies [B-L7](FINDINGS.md) and corrects #557.*

| Domain | Tasks | `ACTION` in `reward_basis` | `compare_args: []` actions |
| --- | ---: | ---: | ---: |
| retail | 114 | **0** | 4 |
| airline | 50 | **0** | 1 |
| telecom | 2,285 | 32 | 32 |
| banking_knowledge | 97 | 9 | 18 |
| mock | 10 | 2 | 1 |

- The order-sensitivity in B-L7 is real but **changes no retail or airline score**. It is live on
  32 telecom and 9 banking tasks. #557 used a retail example and never said so.
- **All 56** `compare_args: []` actions are human hand-offs (`transfer_to_human_agents`,
  `request_human_agent_transfer`) whose only argument is a free-text `summary`. Not grading
  free text is intended. #557 wrongly said no retail task sets it (there are four: 10, 12, 26, 50)
  and wrongly called it an auto-pass defect.

## R-L6 — A malformed judge reply fails the task; it does not pass silently

*Corrects one sentence in #554.* The NL evaluator call is not wrapped in `try` in
`evaluate_simulation`. A fenced reply raises `JSONDecodeError` (reproduced), the exception
propagates, and the batch runner records the task as `infrastructure_error`.

> **Precision, 27 Sep 2026.** The conversion happens in `runner/progress.py`: the retry wrapper
> re-runs the **whole simulation** on any exception and, once retries are exhausted, returns a
> `SimulationRun` with `termination_reason=infrastructure_error`, `messages=[]` and no reward. So a
> malformed judge reply also discards the conversation and re-runs the agent. Only **valid JSON with
missing, empty or too few verdicts** reaches `all([])` — which is what #554's repro shows. Its line
"truncation, a refusal, a fenced body … converts into a silent full pass" is wrong, and contradicts
#555.

## R-L7 — Thought signatures, measured over the full arms

*Corrects #559's sample label ("320 trajectories per arm": it was one 40-trajectory run per arm).*

| Arm (160 trajectories each) | Tool calls | Id carries `__thought__` | Max id length |
| --- | ---: | ---: | ---: |
| `gemini-3.1-flash-lite` | 1,280 | **1,104** | **4,572** |
| `gpt-4.1-nano` | 1,351 | 0 | 29 |

The conclusion holds and is stronger.

## R-L8 — One flip does not establish an asymmetry

*Qualifies [D-L5](FINDINGS.md) and [D-021](DECISIONS.md); corrects #540 and the README.*

D-L5 said the judge result "reproduces" C-L2's determinism asymmetry "in the judge role". It rests
on **one flip in 256**: OpenAI judges 1/128, Google judges 0/128 — **Fisher exact one-sided
p = 0.50**. Consistent with an asymmetry, and no evidence for one. What stands is narrower: the
default judge flipped once on byte-identical requests, so its irreproducibility floor is **not zero**.

D-L5 also called the 3 residual disagreements (317/320) "the same phenomenon". **Unverified.** One
(`phaseC_t1_oai` task 105) was re-graded three times with `1.0` each time yet differs from tau2's
record — not a flip, cause unknown. 317/320 remains strong evidence that prompt capture works; it
is not proof that the remainder is judge noise.

Also: #474 said two of the four judge names are aliases. **Three** carry no date; only
`gpt-4.1-2025-04-14` is a dated snapshot.

## R-L9 — The re-grade journal cannot answer two reuse questions

*Prompted by Universeyi on #540 (23 Sep).* Each record carries the requested judge and the
resolved `model_returned` snapshot. It does **not** carry a request hash, the judge's raw reply, or
its reasoning. So a re-grade can be matched to its trajectory only by `(run, task)`, and the judge
term cannot be re-read from the record — only re-measured. A real limitation of the harness as a
reusable tool.

## R-L10 — Three `python3` interpreters; the results do not depend on which one runs

*Supersedes the [A0](FINDINGS.md) correction ("bare `python3` is 3.9.6").*

| Interpreter | Version | Resolves as `python3` when |
| --- | --- | --- |
| `/opt/anaconda3/bin/python3` | 3.13.5 | `~/.zshrc` is loaded (conda init, since 2025-07-04) |
| `/opt/homebrew/bin/python3` | 3.14.6 | only `~/.zprofile` is loaded |
| `/usr/bin/python3` | 3.9.6 | neither is loaded |

Nothing on the machine changed; the tool shell loaded different startup files in different
sessions. That is why this project recorded 3.14.6, then 3.9.6, then 3.13.5 as "the default".
The previously unpinned gate steps produce **identical** results under all three (26 / 22 / 13
checks, exit 0). The gate now runs every step on the venv's **3.12.9** ([D-023](DECISIONS.md)).

## R-L11 — `make verify` modified upstream on every run

Plain `uv run` rewrites upstream's stale `uv.lock` (the #560 defect): one line, `tau2`
`1.0.0 → 1.0.1`, no dependency changes. The gate used plain `uv run`, so the check meant to prove
"upstream is untouched" modified it every time — and both manifests recorded
`superproject_dirty=True` (Phase C, 21 Sep; Phase D, 22 Sep, which also had uncommitted new files).

**No result is affected:** the submodule commit was `fc0055dc` throughout, and the only change is
that version label. But the manifests cannot prove that on their own, so it is disclosed here.
Fixed in [D-023](DECISIONS.md): the gate calls the venv's Python directly, runners use
`uv run --frozen`, and `make pristine` now **fails** if upstream moved or is modified — tested in
both directions.

## R-L12 — An unintended live judge call during this review

An ad-hoc first version of R-L2 ran tau2's full evaluator on task 105, which carries an assertion,
so it called `gpt-4.1-2025-04-14`. The request was rejected with `RateLimitError` (HTTP 429), retried
by LiteLLM, and returned nothing. Rejected 429s are not billed; **USD 0.00**. The error body was not
captured, so whether it was a per-minute limit or an exhausted quota is unknown, and no further call
was made to find out.

**Lesson:** `EvaluationType.ALL` is not offline for any task with assertions. The committed script
patches the judge to raise and scores judge-gated tasks on DB only.

## R-L13 — Task 64's target is correct; only task 105 is a scoring defect

*27 Sep 2026. Supersedes the interpretation in [R-L3](FINDINGS.md) and A4's "target DB hash is wrong"
for task 64. Prompted by PR #571 (Ruler4396, 26 Sep). Reproduced in
`scripts/review/verify_post_claims.py`.*

| Check | Result |
| --- | --- |
| `64_6` and `64_7` arguments | **identical** — same order `#W7464385`, same item, same replacement, same payment method |
| Status of `#W7464385` in `db.json` | **pending** — so the exchange tool (`64_6`) is the wrong tool and fails; the modify tool (`64_7`) is the right one |
| Gold target with `64_6` removed vs as shipped | **identical hash** |
| Task 105: price difference vs gift card balance | **$21.10 vs $17.00** — the reference cannot apply |

So `64_6` is a **harmless duplicate** of the step that follows it. Task 64's target is exactly the
intended change, and the **11 of 16** shipped runs that match it are **genuine successes**, not a
defect being masked. The only failed write that corrupts a target is **105**: its answer key is
unsatisfiable, the gold stays at the untouched database, and a do-nothing agent matches it
(10 of 16 shipped runs do).

**How R-L3 got it wrong.** It established that `64_7` lands, then adopted "a gold state whose
reference never fully applied" without asking what `64_7` does relative to `64_6`. That is the
same error R-L1–R-L8 correct — the sentence went further than the check under it — committed in the
correction itself, one day later.

**Net effect on the #499 comment.** Of its two "impossible gold" tasks, **105 stands and 64 does
not**. Of its three null-agent false positives, only 105 stands ([R-L1](FINDINGS.md)).
