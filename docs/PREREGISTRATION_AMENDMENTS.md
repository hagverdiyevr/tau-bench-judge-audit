# PRE-REGISTRATION AMENDMENTS — append-only, hash-chained

> **Why this file exists.** [PREREGISTRATION.md](PREREGISTRATION.md) is frozen by a SHA-256 that
> covers everything except its own §9 freeze block — **including its §10 deviation log**. So
> appending a deviation there would break `scripts/verify_preregistration.py`, the very check that
> proves the document is untampered. The frozen file must stay immutable; amendments live here.
>
> **Rules.**
> 1. **Append only.** Never edit or delete an existing amendment. Supersede it with a later one.
> 2. **Each amendment is hash-chained** to the one before it, so the order cannot be rewritten.
>    The chain is recorded in `results/preregistration_chain.json` and checked by
>    `python scripts/verify_preregistration.py`.
> 3. **Pre-data or it does not count.** An amendment is only credible if its git commit precedes
>    the data it affects. The commit timestamp is the evidence; the chain proves the ordering.
> 4. **Scope.** Amendments may *disambiguate* what the frozen text underspecifies, and may record
>    operational parameters the freeze omitted. They may **not** change the hypothesis, add or drop
>    an arm, or alter an estimand after data exists. Those would invalidate the study, not amend it.
>
> Precedent for when to amend versus when to accept an inefficiency: [D-018](DECISIONS.md).

---

## A-001 — Pin the primary estimand and remove the self-evaluation confound

**Status:** ACTIVE · **Raised:** 2026-09-21 · **Pre-data:** yes — no Phase C trajectory exists.
**Addresses:** external-review findings S1 (ambiguous estimand) and S3 (triple-role confound).

### The defect

[PREREGISTRATION §3](PREREGISTRATION.md) defines the only primary formula as

```
FamilyBias = [ S(gpt4.1, openai_agent) − S(gemini, openai_agent) ]
           − [ S(gpt4.1, google_agent) − S(gemini, google_agent) ]
```

but **§4.2 freezes four judges** — two families × two capability tiers. The token `gemini` is never
bound to one of them. The frozen text does not say whether the primary uses the high tier, the low
tier, an average of both, or whether there are two separate family interactions. **Two careful
analysts could implement different "primary" analyses and each believe they followed the
pre-registration.** That is exactly the degree of freedom a pre-registration exists to remove.

Compounding it, `gemini/gemini-3.1-flash-lite` occupies **three roles simultaneously** in the frozen
design — Google agent arm (§4.2), Google low-tier judge (§4.2), and fixed user simulator (§4.2). A
primary estimand built on the low tier would therefore contain a cell where the judge grades
**its own exact model's** output, in a conversation whose other participant is **also** that model.
"Family effect" and "exact-model self-evaluation" would be inseparable.

### The amendment

**Primary estimand is the tier-matched, high-tier contrast:**

```
FamilyBias_primary =
    [ S(gpt-4.1-2025-04-14, gpt-4.1-nano) − S(gemini-3.8-flash, gpt-4.1-nano) ]
  − [ S(gpt-4.1-2025-04-14, gemini-3.1-flash-lite) − S(gemini-3.8-flash, gemini-3.1-flash-lite) ]
```

- `gpt4.1` in §3 := **`gpt-4.1-2025-04-14`** (the incumbent).
- `gemini` in §3 := **`gemini/gemini-3.8-flash`** (high tier).
- Both judges are the high tier of their family, so **capability is matched across the contrast**.
- Neither judge is the exact model of either agent, so **no cell is exact-model self-evaluation**.

**Demoted to pre-specified secondary, exactly as §6.2 S1 already anticipated:**

- **A-001-S1** — the same DiD computed with the **low-tier** judges
  (`gpt-4.1-mini` vs `gemini/gemini-3.1-flash-lite`). A genuine family effect should appear in both
  tiers. **This cell contains exact-model self-evaluation** (`gemini-3.1-flash-lite` judging
  `gemini-3.1-flash-lite` inside a conversation it also simulated) and **must be reported with that
  stated**, since a larger effect there is equally explained by self-recognition.
- **A-001-S2** — tier contrast within family, per §6.2 S2. Unchanged.

### Residual confound, disclosed not corrected

The user simulator remains `gemini/gemini-3.1-flash-lite` for **every** trajectory in both arms. It
is constant within each trajectory, so it cannot bias the **within-trajectory judge contrast** that
the primary estimand is built from. It can still affect the **agent-side** comparison: the two
agents may interact differently with the same simulator, so between-arm differences in agent
*behaviour* are not simulator-free. The primary estimand does not depend on that, because the judge
contrast is taken within each trajectory before any cross-arm subtraction. **This limitation is
added to §8 by reference and must appear in the write-up.**

### Claim language

Per external-review finding S2 and [PREREGISTRATION §8.4](PREREGISTRATION.md): with no human or
objective gold labels, the DiD identifies an **agent-family × judge-family interaction**. It cannot
by itself attribute direction — "OpenAI favoured OpenAI" versus "Gemini disfavoured OpenAI" versus
differing sensitivity to answer style. **The confirmatory claim is therefore
"agent-family × judge-family interaction in τ³-retail NL-assertion grading", not "self-favouring
bias".** The word *bias* may only be used if a human-labelled calibration subset is added, which is
outside this study's scope.

---

## A-002 — Record operational parameters the freeze omitted

**Status:** ACTIVE · **Raised:** 2026-09-21 · **Pre-data:** yes.
**Addresses:** external-review findings E3, E4, R6, E1, E2.

[PREREGISTRATION §4.5](PREREGISTRATION.md) freezes temperatures, `--max-steps`,
`--max-concurrency` and the seed schedule, but is **silent on retry, timeout, max-errors, output
limits and model-alias resolution**. Those materially affect both cost and which runs survive into
the artifact, so they are fixed here before dispatch rather than left to defaults discovered later.

| Parameter | Value | Reason |
| --- | --- | --- |
| `--max-retries` | **0** | Upstream default is 3, i.e. up to **4 paid attempts**. Failed attempts are **not persisted**, so retries cause cost undercounting and survivorship bias against the intention-to-treat rule in §6.4. Zero retries makes every attempt observable. |
| `--max-errors` | 10 (upstream default, recorded) | Unchanged; recorded so it is not a silent default. |
| `--timeout` | none (upstream default, recorded) | Unchanged; recorded. |
| Agent — OpenAI | **`gpt-4.1-nano-2025-04-14`** | The frozen ID `gpt-4.1-nano` is an **alias**. Verified 2026-09-20 to resolve to this snapshot. Pinning the snapshot makes the arm reproducible if the alias moves. **Not a change of arm** — it is the same model the alias resolves to today. |
| Execution order | **balanced 2:2** | §5.2 requires a pre-drawn seeded permutation but does not require balance. The first draw realised **3:1** OpenAI-first. Rebalanced to 2:2 by construction. Immaterial to the offline judge contrast, but it costs nothing to remove the imbalance. |
| Per-invocation logging | **required** | stdout/stderr of every invocation is tee'd to a per-invocation log and parsed for retry/failure markers, so attempt history is recoverable. Without it the evidence is unrecoverable after dispatch. |

All are recorded in the committed execution manifest `results/phaseC_execution_manifest.json`,
generated by `scripts/phase_c/build_manifest.py`, which also records the superproject HEAD, the
submodule SHA, the Python version, and a content hash.

---

*Next amendment id: A-003.*

## A-003 — Bounded retries with every attempt logged (supersedes A-002's retry row)

**Status:** ACTIVE · **Raised:** 21 Sep 2026 · **Pre-data:** partially — see Disclosure.
**Supersedes:** the `--max-retries` row of A-002 only. All other A-002 parameters stand.

### Why A-002's choice was wrong

A-002 set `--max-retries 0` to fix a real problem: upstream's default of 3 allows up to four paid
attempts, and failed attempts are **not persisted**, so cost undercounts and intention-to-treat
failures vanish from the artifact.

Zero retries fixed that and introduced something worse. Measured on `phaseC_t1_oai`
(40 tasks, `gpt-4.1-nano-2025-04-14`): **18 × `litellm.RateLimitError`** producing **6 of 40
simulations with `termination_reason: infrastructure_error`**, `agent_cost: None`, zero messages —
task IDs 16, 29, 63, 89, 103, 109.

Under §6.4's intention-to-treat rule those six score 0. **That biases the OpenAI arm downward by our
own provider rate limit, not by agent capability** — a configuration artifact contaminating exactly
the arm the primary estimand depends on. ITT exists to retain genuine agent failures, not to convert
our infrastructure into an agent result.

### The amendment

| Parameter | A-002 | **A-003** |
| --- | --- | --- |
| `--max-retries` | 0 | **2** (3 attempts maximum) |
| `--retry-delay` | upstream default 1.0s | **5.0s** — 1s is far too short for a per-minute rate limit |
| Attempt visibility | log-scraping for retry markers | **every API attempt recorded at the LiteLLM boundary**, failures included |

**Why this is not a return to A-002's problem.** A-002's objection was that retried attempts are
*invisible*, not that retrying is wrong. Attempts are now recorded independently of tau2 by a
LiteLLM callback (`scripts/phase_c/attempt_logger.py`) writing one JSONL line per request — success
or failure — with model, latency, error class and cost. Attempt history and true spend are therefore
complete regardless of what tau2 persists. That was the real requirement; zero retries was a blunt
proxy for it.

**Completion criterion, newly explicit.** An invocation counts as completed only if its artifact
contains **zero `infrastructure_error` simulations**. Above zero it is recorded `degraded` and must
be re-run, or reported with exclusion counts. `phaseC_t1_oai` was previously marked `completed` with
6 such failures because the runner checked only the process exit code.

### Disclosure — partially, not fully, pre-data

Two invocations were dispatched under A-002 before this amendment:

- **`phaseC_t1_gem`** — 40/40 clean. **Data destroyed** by a defect in our own
  `tests/test_runner_guards.py`, which wrote a stub to the real artifact path and cleaned up only
  `if created`. Unrecoverable; no export existed. Re-run under A-003.
- **`phaseC_t1_oai`** — 34 clean / 6 `infrastructure_error`. Discarded; re-run under A-003.

**No confirmatory analysis was performed on either.** No estimand was computed and no cross-arm
comparison inspected. The amendment is therefore made in ignorance of any outcome, which is the
property that matters — but it is recorded as *partially* pre-data rather than claimed as fully
pre-data, because trajectories existed when it was written.

Both are excluded from the confirmatory set; the re-runs are the data of record.

## A-004 — Raise retries to 4; clarify how an infrastructure error enters the analysis

**Status:** ACTIVE · **Raised:** 22 Sep 2026 · **Pre-data:** partially — see A-003 Disclosure.
**Supersedes:** the `--max-retries` value in A-003 (2 → 4). Everything else in A-003 stands,
including the attempt logger and the zero-`infrastructure_error` completion criterion.

### Measured cause

A-003's bounded retries worked: `infrastructure_error` on the OpenAI arm fell from **6/40 to 1/40**
across 909 logged attempts with **15 `RateLimitError`** failures. The attempt log identifies the
constraint precisely, which log-scraping could not have:

```
rate_limit_exceeded on tokens per min (TPM): Limit 200000, Used 198321,
Requested 6194. Please try again in 1.354s.
```

It is a **200,000 TPM organisation ceiling**, not a request-rate limit. One invocation pushed
**3,132,310 tokens** through `gpt-4.1-nano`, so the ceiling is reached repeatedly by construction.

The decisive detail: the waits OpenAI asks for are **46 ms – 1.4 s**, far below our 5 s delay. So
nearly every retry succeeded; only the tail — one task — exhausted its 3 attempts.

### The amendment

`--max-retries` **2 → 4** (5 attempts maximum). `--retry-delay` stays 5.0 s, which already exceeds
every requested wait observed.

**Why raise retries rather than lower concurrency.** `--max-concurrency 2` is fixed in the **frozen**
[PREREGISTRATION §4.5](PREREGISTRATION.md); changing it is a deviation from the frozen design.
`--max-retries` is not in the frozen document at all — it is amendment territory by construction.
The lighter instrument is the correct one. Retried 429s are not billed, so the cost impact is
approximately zero.

**Why not simply tolerate 1/40.** The completion bar stays at zero `infrastructure_error`. Fixing
the cause is preferable to loosening the threshold, and a bar that moves whenever it is
inconvenient is not a bar. If 5 attempts still leave failures, that is evidence the ceiling cannot
be cleared at this tier — a finding to report, not a threshold to relax.

### Clarification — how an infrastructure error enters the analysis

[PREREGISTRATION §6.4](PREREGISTRATION.md) states intention-to-treat: errored trajectories score 0
and are retained. Applied without qualification that is wrong for the **primary** estimand, and the
distinction was not drawn when §6.4 was written.

An `infrastructure_error` trajectory has **zero messages and no `reward_info`** (verified: task 105
in the discarded `phaseC_t1_oai`). The primary estimand is a **within-trajectory judge contrast** —
the same conversation scored by four judges. A conversation that does not exist cannot be graded by
any of them, so it is a **missing observation** (n: 40 → 39), not a scored zero. Scoring it 0 would
be incoherent: there is nothing for a judge to disagree about.

Therefore:

- **Primary (judge DiD):** infrastructure-error trajectories are **excluded as missing data**, and
  the realised n is reported per cell. Exclusion is symmetric — a trajectory absent in any arm is
  absent from the paired contrast.
- **Secondary (agent main effect on reward):** §6.4's ITT rule applies unchanged — scored 0 and
  retained — **and** reported alongside a per-protocol figure, because at 1/40 the infrastructure
  bias is 2.5% and readers must be able to see both.

This is a clarification of §6.4's scope, not a change to it. No estimand is redefined.
