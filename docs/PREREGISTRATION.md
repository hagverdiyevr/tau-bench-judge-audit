# PRE-REGISTRATION — frozen before any confirmatory data exists

> **Role in the memory system:** this file freezes the primary hypothesis, design, and analysis
> **before** Phase C generates any confirmatory data. It is the answer to the reviewer objection
> that a result was selected after seeing the data.
>
> **Status: FROZEN 2026-09-20T10:54:29Z.** Binding. Changes are deviations (§10), not edits.
> Once frozen, this file is **immutable**. Deviations are not edits; they are appended to §10
> with a reason and a date.

**Prepared:** 20 September 2026
**Target:** `sierra-research/tau2-bench` @ `v1.0.1`, commit `fc0055dc4e0a316c3f83133267fbd6faaa770992`
**Evidence base:** [FINDINGS.md](FINDINGS.md) Phase A + Phase B (all gates passed, ~USD 0.47)

---

## 1. Background and motivation

τ³-retail computes reward as the **product** of the components in each task's `reward_basis`.
Measured on the shipped task files ([A1](FINDINGS.md), [A3](FINDINGS.md)):

- `COMMUNICATE` appears in **0 of 114** retail tasks.
- 112 tasks use `[DB, NL_ASSERTION]`; 2 use `[DB]`.
- Only **40 of 114** tasks carry live `nl_assertions`; the other 74 are effectively DB-only.
- `NL_ASSERTION` is an LLM judge **hardcoded to `gpt-4.1-2025-04-14`** (`config.py:24`), marked
  *experimental / WIP* by its own source, with **no environment override**.

In a stock τ³ run the same OpenAI model is the default agent, the default user simulator, **and**
the grader. If that judge's verdicts depend on the agent's model family, a component of every
published τ³-retail score is a function of vendor affinity rather than agent quality.

## 2. Primary hypothesis

> **H1.** The incumbent `gpt-4.1` judge assigns systematically more favourable NL-assertion
> verdicts to trajectories produced by an OpenAI-family agent than a non-OpenAI judge does,
> relative to the same comparison for a Google-family agent.

**H0 (null).** The agent-family × judge-family interaction is zero: judges differ only in overall
leniency, not in which agent family they favour.

This is an **interaction**, not a main effect. A judge that is uniformly stricter is not biased.

## 3. Primary estimand

Let `S(j, a, t, r)` be the NL-assertion component score for judge `j`, agent `a`, task `t`,
trial `r`, taken from `reward_breakdown[NL_ASSERTION]`.

```
FamilyBias = [ S(gpt4.1, openai_agent) − S(gemini, openai_agent) ]
           − [ S(gpt4.1, google_agent) − S(gemini, google_agent) ]
```

Aggregated per task, then across tasks. **The bracketed control term is mandatory** — omitting it
measures judge leniency, not bias ([D-009](DECISIONS.md)).

**Direction.** H1 predicts `FamilyBias > 0`. The test is two-sided.

## 4. Design

### 4.1 Factors

| Factor | Levels | Notes |
| --- | --- | --- |
| Agent family | 2 — OpenAI, Google | generated once, paid |
| Judge family × tier | **4** — 2 families × 2 capability tiers | re-graded offline, cheap |
| Task | 40 judge-gated, `base` split | hard cap, see §4.3 |
| Trial | 4 | enables pass^1..pass^4 |

### 4.2 Exact model identifiers — frozen

| Slot | Model ID |
| --- | --- |
| Agent — OpenAI family | `gpt-4.1-nano` |
| Agent — Google family | `gemini/gemini-3.1-flash-lite` |
| **Judge — OpenAI, high tier (INCUMBENT)** | **`gpt-4.1-2025-04-14`** |
| Judge — OpenAI, low tier | `gpt-4.1-mini` |
| Judge — Google, high tier | `gemini/gemini-3.8-flash` |
| Judge — Google, low tier | `gemini/gemini-3.1-flash-lite` |
| User simulator (**fixed**, not a factor) | `gemini/gemini-3.1-flash-lite` |

**Why four judges.** Comparing `gpt-4.1` (high tier) only against a small Gemini judge would
confound **family** with **capability**. The 2 × 2 judge grid separates them: a family effect must
appear across *both* tiers, while a capability effect appears across *both* families. This control
costs ~USD 2 because re-grading is offline.

**Simulator.** Held constant across every cell and therefore inside every trajectory, so it cancels
in the within-trajectory judge contrast. It shares a family with one agent; this is **disclosed**,
not corrected, because it cannot bias a within-trajectory comparison.

**Scaffold.** Stock `llm_agent`, unmodified — runs remain classifiable as **"standard"** under
Sierra's submission rules.

### 4.3 Task set

All **40** `base`-split tasks carrying live `nl_assertions` ([A3](FINDINGS.md)). This is the entire
population; no selection discretion exists. `test` alone yields only 11, so `base` is required.

**Disclosure.** Five of these (**89, 76, 109, 103, 43**) were run and inspected during Phase B
calibration ([B-L11](FINDINGS.md), [B-L12](FINDINGS.md)). No hypothesis or parameter was tuned on
them — they informed *scale* (headroom) only. The primary analysis includes all 40; a
**pre-specified sensitivity analysis excludes those 5** and must not change the conclusion.

### 4.4 Volume

**320 trajectories** = 2 agents × 40 tasks × 4 trials.
**1,280 judge evaluations** = 320 × 4 judges. Plus replicates (§6.3).

### 4.5 Fixed parameters

Agent temperature 0.0 · simulator temperature 0.0 · judge temperature 0.0 (upstream default)
· `--max-steps 120` · `--max-concurrency 2` · seeds `1001..1004` (trial index `r` → seed `1000+r`),
identical across cells so harness-side variation cancels in pairing.

> Seeds control harness-side sampling only. They do **not** make remote inference deterministic.

## 5. Execution protocol

1. Generation runs as one invocation per (agent × trial index) over all 40 tasks, `--num-trials 1`.
2. Cell order within each trial block follows a **pre-drawn seeded permutation**, published here
   before execution, to avoid confounding cell with wall-clock time.
3. Per-invocation UTC start/end are recorded; cell means by block are reported as a drift diagnostic.
4. On partial failure: **resume, never restart** — same commit, same seed, `--task-ids` limited to
   missing units.
5. Re-grading (Phase D) runs offline against **saved** trajectories. No conversation is ever
   re-generated for a judge comparison. Mechanism validated at 11/11 in [B-L13](FINDINGS.md).

## 6. Analysis plan

### 6.1 Primary

`FamilyBias` (§3), with **task-level cluster bootstrap** 95% CIs, B = 10,000, resampling *tasks*
with replacement and carrying all trials of a task together.

> Trials of one task are not independent. Bootstrapping at trajectory level is invalid here.

Reported alongside every estimate: the **realized minimum detectable effect** computed from the
observed between-task variance.

### 6.2 Pre-specified secondary

- **S1 — tier control.** `FamilyBias` computed within each judge tier separately. A genuine family
  effect must appear in both.
- **S2 — capability contrast.** High vs low tier within each family, to size capability against family.
- **S3 — component decomposition.** DB vs NL_ASSERTION agreement per task ([B-L12](FINDINGS.md)
  found disagreement on 3/5 in pilot). Reported as a 2×2 contingency, **not** as an additive split —
  reward is multiplicative.
- **S4 — regime split.** All results reported separately for the 40 judge-gated tasks; the 74
  DB-only tasks are *not* part of this study and are never pooled into a headline number.
- **S5 — cost.** Cost per attempt and cost per reliably-completed task at k = 1 and k = 4, with
  **judge cost included** ([B-L14](FINDINGS.md) — tau2 omits it entirely).

### 6.3 Noise control

Judge self-consistency was bounded at **<9% flip rate (0/33, rule of three)** in
[B-L13](FINDINGS.md). Phase D re-grades a **pre-specified random 20% of trajectories 3×** per judge.
If the measured flip rate exceeds 9%, the primary estimate is reported **against that noise floor**
and the conclusion is downgraded to a bounded null.

### 6.4 Exclusions — fixed in advance

- **Intention-to-treat is primary:** errored or interrupted trajectories score 0 and are retained.
- Per-protocol (excluding infrastructure failures) is reported as secondary. Both appear.
- A trajectory flagged `SUSPECT_SIGNATURE_LOSS` by the degradation detector is reported separately
  and excluded from the headline, never silently dropped.
- Every attempted trajectory is accounted for in a run table. No silent deletion, ever.

### 6.5 Inference discipline

- Any "no effect" claim is a **null claim** → TOST equivalence with a pre-specified margin of
  **5 percentage points**, and the ruled-out effect size is stated explicitly.
- Never headline `pass^k` at `k = num_trials`; it degenerates to one Bernoulli draw per task.
- `cost_per_success` is **undefined**, never 0, at zero successes.
- Nothing outside §6.1–6.2 is confirmatory. Anything else is labelled exploratory and reported
  without inferential statistics.

## 7. What would falsify H1

`FamilyBias` CI containing 0 **and** an MDE small enough to rule out a 5pp effect → report a
**bounded null**: *"family-alignment effects larger than X pp are ruled out."* This is a publishable
result and is accepted in advance as an outcome.

A CI containing 0 with a **large** MDE is reported as **underpowered**, not as evidence of absence.

## 8. Declared limitations

1. **n = 2 agent families.** Nothing here generalises to "model families in general."
2. **Family is confounded with vendor, tokenizer, and training data.** "Family" means these specific
   model lineages.
3. **40 tasks is a hard cap** set by the benchmark, not by budget.
4. The judge **cannot see tool calls** ([B4](FINDINGS.md)) — it grades narration plus tool results.
   Any bias found may operate through narration style. This is a mechanism, not a confound, but it
   constrains interpretation.
5. Results are a **custom subset**, not an official τ³ score, and are not leaderboard-comparable.
6. `gpt-4.1-2025-04-14` is a fixed April-2025 snapshot; the finding is about that judge.

## 9. Freeze

This document is frozen by recording the SHA-256 of its own content, committed **before** the first
Phase C invocation.

```
SHA-256 : a917984e48d16f28ea0280c5e7a2cb9b6e4a786a123a43efc989f09a972c3906
Frozen  : 2026-09-20T10:54:29Z
Method  : sha256 of this file with the fenced block in S9 replaced by the literal line
          <<FREEZE BLOCK CANONICALISED FOR HASHING>> (the hash cannot cover itself).
          Verify with: python scripts/verify_preregistration.py
```

Phase C is unblocked. Any departure from S2-S6 is appended to S10, never edited in.

## 10. Deviation log

*Empty at freeze. Every departure from §2–§6 after freezing is appended here with date and reason.
Deviations are disclosed in the write-up; they are not retroactive edits.*
