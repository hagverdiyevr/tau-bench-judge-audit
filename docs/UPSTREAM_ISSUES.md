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

## Post-filing audit — 26–27 September 2026

**Who wrote the posts.** Claude drafted and posted all 12 through the GitHub CLI, which is signed in as
`@hagverdiyevr`; the account owner chose the filing plan but did not write the text. On GitHub they
read as the owner's own words. Nothing else has been posted from the account.

Three replies arrived, and every claim in every post was then re-checked against v1.0.1 and the
committed artifacts ([FINDINGS R-L1–R-L12](FINDINGS.md); offline script
`scripts/review/verify_post_claims.py`). **No reported bug turned out not to exist.** Seven posts
contain at least one claim that goes further than its evidence.

| Post | Verdict | What is wrong, and the evidence |
| --- | --- | --- |
| #553 | Holds · slip | "Line 79 expresses the same intent" — the intent is documented in a different function |
| #554 | **Correct** | "A fenced/truncated/refused reply converts into a silent full pass" — it raises; only valid-but-incomplete JSON passes ([R-L6](FINDINGS.md)) |
| #555 | Holds | — |
| #556 | **Correct** | Figures were estimates: measured 32.8%, 20% vs 58% by arm; "65%", "order of magnitude" (3.9×) and "roughly fixed per task" are wrong ([R-L4](FINDINGS.md)) |
| #557 | **Correct** | The bug is **latent**: no task that scores `ACTION` compares a reorderable list, so no shipped score changes and the comparability caveat is wrong; wrongly says no retail task sets `compare_args: []` (4 do) and calls it a defect (all 56 are deliberate hand-offs) ([R-L5](FINDINGS.md), [R-L14](FINDINGS.md)) |
| #558 | Holds · slip | Cites `llm_config.py:47`; the assignment is on line 48 |
| #559 | **Correct** | "320 trajectories per arm" was one 40-trajectory run; full arms: 1,104/1,280. "Degrades with no error" was never tested ([R-L7](FINDINGS.md), [R-L15](FINDINGS.md)) |
| #560 | Holds | Re-verified on a real fresh clone |
| #499 comment | **Correct** | Task 64's target is correct — its failing step duplicates the next with the wrong tool; only 105 is a defect. 67/68 need no writes ([R-L1](FINDINGS.md), [R-L13](FINDINGS.md)) |
| #384 comment | **Correct** | One #499 false positive (105), not three; "remaining 8" is 10 ([R-L1](FINDINGS.md)) |
| #540 comment | **Correct** | "Family asymmetry in the judge role" rests on one flip (p = 0.50); "3 residual disagreements are the same effect" unverified ([R-L8](FINDINGS.md)) |
| #474 comment | Holds · slip | "Two of four are aliases" — three of four names are undated |

**Replies received** (verified in [REFERENCE](REFERENCE.md#replies-to-our-posts--what-others-established-verified-2627-sep-2026)):
Universeyi on #540 (23 Sep) — agrees, and asks whether the journal stores a request hash and the raw
judge reply (it stores **neither**, [R-L9](FINDINGS.md)); justavibedev on #499 (23 Sep) — corrects
task 64, right; Ruler4396 on #499 (26 Sep) — independently reproduces the finding and confirms both
corrections.

**Public corrections:** posted one at a time, each after an explicit go-ahead — see *Corrections posted* below.

### Corrections posted

Each was shown to the account owner word for word and posted only after an explicit yes. The live
text is checked against the approved text after posting.

| # | Posted (UTC) | Where | What it corrects | Live == approved |
| --- | --- | --- | --- | --- |
| 1 | 2026-09-26 20:36 | [#499 reply](https://github.com/sierra-research/tau2-bench/issues/499#issuecomment-5849678221) | Withdraws the task 64 claim (its target is correct — PR #571) and the 67/68 causal claim; confirms 105 | ✅ |
| 2 | 2026-09-26 20:43 | [#384 reply](https://github.com/sierra-research/tau2-bench/issues/384#issuecomment-5849720653) | Only 105 is a #499 false positive (not 67/68); adds that a do-nothing agent scores **full reward on 6 tasks**, two in `test` ([R-L2](FINDINGS.md)) | ✅ |
| 3 | 2026-09-26 20:46 | [#540 reply](https://github.com/sierra-research/tau2-bench/issues/540#issuecomment-5849746351) | Withdraws "family asymmetry" (one flip, p = 0.50) and "same effect"; answers Universeyi: model id yes, request hash **no**, raw completion **no**; **promises to link the harness when public** | ✅ |
| 4 | 2026-09-27 | [#554 description](https://github.com/sierra-research/tau2-bench/issues/554) — **edited** | Dated correction note at top; the "malformed reply converts into a silent full pass" sentence struck through and corrected ([R-L6](FINDINGS.md)) | ✅ |
| 5 | 2026-09-27 | [#556 title + description](https://github.com/sierra-research/tau2-bench/issues/556) — **edited** | Estimates replaced by the measured table (32.8%; 20% vs 58%); "65%", "order of magnitude", "roughly fixed" and "enough to reorder" struck and corrected ([R-L4](FINDINGS.md)) | ✅ |
| 6 | 2026-09-27 | [#557 description](https://github.com/sierra-research/tau2-bench/issues/557) — **edited** | States the bug is latent (no shipped score changes); withdraws the `compare_args: []` "defect"; strikes the comparability caveat ([R-L5](FINDINGS.md), [R-L14](FINDINGS.md)) | ✅ |
| 7 | 2026-09-27 | [#559 description](https://github.com/sierra-research/tau2-bench/issues/559) — **edited** | Sample size corrected to one 40-run per arm, with the full-arm table (1,104/1,280); the untested "degrades with no error" claims struck ([R-L7](FINDINGS.md), [R-L15](FINDINGS.md)) | ✅ |
| 8 | 2026-09-26 22:06 | [#540 follow-up](https://github.com/sierra-research/tau2-bench/issues/540#issuecomment-5850307643) | Keeps the promise: links the public repo, the harness, the manifest and the 1,792-record journal; restates the two gaps | ✅ |

<details><summary>Full text of correction 1, as posted</summary>

Thanks @justavibedev and @Ruler4396 — both corrections are right. I've re-checked them on `fc0055dc`, and I got two things wrong in my comment above.

**Task 64.** I wrote that its gold write never lands and the target is the untouched database. As @justavibedev showed, `64_7` lands — and #571 goes further: `64_6` and `64_7` are the same change with identical arguments, and `64_6` just uses the exchange tool on an order that is still `pending`. Removing `64_6` leaves the gold hash unchanged:

```python
from tau2.domains.retail.environment import get_environment, get_tasks

t = {x.id: x for x in get_tasks("base")}["64"]   # task 64 has no initial_state

def gold(skip=()):
    g = get_environment()
    for a in t.evaluation_criteria.actions:
        if a.action_id in skip:
            continue
        try:
            g.make_tool_call(tool_name=a.name, requestor=a.requestor, **a.arguments)
        except Exception:
            pass
    return g.get_db_hash()

print(gold() == gold(skip=("64_6",)))   # True
```

So 64's target is exactly the intended change, and I'd read the 11 of 16 shipped runs that match it as genuine successes rather than masking. Of the two tasks where I said a failed write corrupts the target, only **105** holds — and the $21.10-vs-$17.00 arithmetic in #571 shows why it can never apply.

**Tasks 67 and 68.** I also wrote that these pass a null agent *because* their gold replay failed. That's wrong too: their gold makes no writes at all, and the failing actions are reads (`find_user_id_by_name_zip`), which change nothing. They would pass a null agent even if every read succeeded — that's #384's territory rather than this issue's. Of the 11 tasks a null agent passes on DB, only 105 is a #499 artifact.

What still stands from my comment is the count: 18 failing actions across the same 15 tasks, 16 reads and 2 writes — which @Ruler4396 reproduced independently.

</details>

<details><summary>Full text of correction 2, as posted</summary>

A correction to my comment above, and one addition that I think is squarely this issue.

**Correction.** I wrote that of the 11 tasks a null agent passes on DB, three (67, 68, 105) match "because the gold replay itself failed". Only **105** does. Tasks 67 and 68 have no gold writes at all — their failing actions are reads, which change nothing — so they belong with the read-only tasks. That makes it **10** tasks where an unchanged database is simply the expected end state, not 8, and **one** #499-corrupted target, not three. (Details in my reply on #499.)

**Addition: on 6 retail tasks, doing nothing scores full reward.** Of those 10, six carry no NL assertions, so the line-38 early return you identified gives `NL_ASSERTION = 1.0`, and DB passes because the gold makes no writes. Scored end to end with tau2's own evaluator, on a two-message conversation in which the agent does nothing:

```python
from tau2.data_model.message import AssistantMessage, UserMessage
from tau2.data_model.simulation import SimulationRun
from tau2.domains.retail.environment import get_tasks
from tau2.evaluator.evaluator import EvaluationType, evaluate_simulation

tasks = {t.id: t for t in get_tasks("base")}
do_nothing = [UserMessage(role="user", content="Hi, I need help with my order.", turn_idx=0),
              AssistantMessage(role="assistant", content="Sorry, I can't help with that. Goodbye.", turn_idx=1)]

for tid in ["10", "12", "25", "50", "57", "65"]:
    sim = SimulationRun(id=tid, task_id=tid, start_time="", end_time="", duration=0.0,
                        termination_reason="user_stop", messages=do_nothing)
    r = evaluate_simulation(simulation=sim, task=tasks[tid], evaluation_type=EvaluationType.ALL,
                            solo_mode=False, domain="retail")
    print(tid, r.reward, {k.value: v for k, v in r.reward_breakdown.items()})
```

Output on `fc0055dc`:

```
10 1.0 {'DB': 1.0, 'NL_ASSERTION': 1.0}
12 1.0 {'DB': 1.0, 'NL_ASSERTION': 1.0}
25 1.0 {'DB': 1.0, 'NL_ASSERTION': 1.0}
50 1.0 {'DB': 1.0, 'NL_ASSERTION': 1.0}
57 1.0 {'DB': 1.0, 'NL_ASSERTION': 1.0}
65 1.0 {'DB': 1.0, 'NL_ASSERTION': 1.0}
```

Two of the six (**12** and **65**) are in the `test` split. None of them has `communicate_info`, and `ACTION` is in no retail reward basis, so on these tasks the only thing scored is that the agent didn't change the database. For 10, 12 and 50 the gold behaviour is a hand-off (`transfer_to_human_agents`), so declining to help scores the same as handing off correctly; task 57 has no gold actions at all.

That's the retail form of your airline P0 — tasks scored on inaction only. It also sharpens the null-agent check I suggested: flagging tasks where a no-op agent gets full *reward*, not just a DB match, catches these six directly, and needs no API calls for them because there is no judge to call.

</details>

<details><summary>Full text of correction 3, as posted</summary>

Thanks — and agreed that the two designs meeting in the middle is the useful part. Your released-file comparison (NL-gated tasks flipping at 0.24 vs 0.26 for DB-only) and our direct re-grade (1 flip in 256) point at the same answer from opposite directions: the judge term is real but small, and the pooled floor is mostly agent plus user simulator.

**One correction to my comment.** I wrote that "the same family asymmetry shows up in the judge role". That doesn't survive: it rests on a single flip — OpenAI judges 1/128, Google judges 0/128, one-sided Fisher exact p = 0.50. What stands is narrower: the default judge gave different verdicts to byte-identical requests once, so its floor isn't zero. I also called the 3 re-grades that disagree with tau2's recorded verdict "the same effect", and that isn't shown either — one of them was re-graded three times with the same answer each time, so it isn't a flip, and its cause is unknown.

**Your two questions**, answered from the record format as it stands:

1. **Judge model id — yes. Request hash — no.** Each record stores the judge requested *and* the snapshot the provider returned (e.g. `gpt-4.1-mini` → `gpt-4.1-mini-2025-04-14`). A re-grade is matched to its trajectory by `(run, task, judge, replicate)`. The prompt is reproducible — it is captured from tau2's own prompt construction rather than rebuilt — but no hash of it is stored.
2. **Raw completion — no.** Only the parsed verdicts (assertion → met), plus `finish_reason`, whether the reply was fenced, token counts and cost. The judge's reasoning text is dropped too. So the judge term can't be read off the record, only re-measured. You've put your finger on the right gap: a request hash and the raw completion are what I'd add.

For reference, a record carries: `run, task, judge, replicate, utc, settled, ok, model_returned, finish_reason, nl_reward, verdicts, matches_incumbent, fenced, prompt_tokens, completion_tokens, usd, usd_source, error_kind, error`.

The harness isn't in a public repository yet; I'll link it here when it is.

And agreed on "seed accepted" vs "seed honoured" — on the Gemini path in #558 it isn't even accepted: the seed is dropped before the request is sent.

</details>

<details><summary>Full text of the #540 follow-up, as posted</summary>

Following up as promised — the harness and the full record are now public: https://github.com/hagverdiyevr/tau-bench-judge-audit

For the two things you asked about:

- **Harness:** [`scripts/phase_d/run_phase_d.py`](https://github.com/hagverdiyevr/tau-bench-judge-audit/blob/main/scripts/phase_d/run_phase_d.py) re-grades saved trajectories under any number of judges. It captures the prompt tau2's own evaluator builds (`capture_prompt`), so every judge receives the identical request, and parses replies through a fail-closed adapter ([`scripts/grading/judge_adapter.py`](https://github.com/hagverdiyevr/tau-bench-judge-audit/blob/main/scripts/grading/judge_adapter.py)). The pre-drawn work units, including the 20% replicate sample, are in [`results/phaseD_regrade_manifest.json`](https://github.com/hagverdiyevr/tau-bench-judge-audit/blob/main/results/phaseD_regrade_manifest.json).
- **Journal:** all 1,792 records are in [`results/phase_d/regrade_journal.jsonl`](https://github.com/hagverdiyevr/tau-bench-judge-audit/blob/main/results/phase_d/regrade_journal.jsonl), in the format I listed above — so the same two gaps apply: no request hash, no raw completion.

The re-graded trajectories themselves are in `results/artifacts/`, and `make setup && make verify` reproduces the checks without API keys or spend.

</details>

**Note on the drafts below.** The numbered sections are the pre-filing drafts. The posted text was
rewritten during filing and differs; the posted versions are the record, and the audit above is
about them. Commands in the drafts use plain `uv run`, which modifies upstream — use
`uv run --frozen` ([R-L11](FINDINGS.md)).

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
