# PLAN — active implementation plan

> **Role in the memory system:** what we are doing now and why, with phase gates and budget.
> Frozen hypothesis and analysis: [PREREGISTRATION.md](PREREGISTRATION.md).
> Evidence: [FINDINGS.md](FINDINGS.md). Rationale for each fork: [DECISIONS.md](DECISIONS.md).
> External facts: [REFERENCE.md](REFERENCE.md). Current position: [STATUS.md](STATUS.md).
> Binding rules: [CLAUDE.md](../CLAUDE.md).
>
> **Version 4.1** · 20 Sep 2026 · Phase B closed including B9; pre-registration frozen.
> All cost figures are **measured**. Ledger of record: `results/spend_ledger.json`.

## Context

The owner is an experienced AI engineer targeting senior retail/e-commerce AI roles in Germany.
The deliverable that earns attention in this field is **a reusable tool plus one sharp finding** —
not an explainer, not a long report ([REFERENCE](REFERENCE.md) §Reception).

Three research passes and a hostile review eliminated the obvious angles
([D-003](DECISIONS.md), [D-005](DECISIONS.md)). A zero-cost Phase A audit then **falsified the
surviving thesis** ([D-004](DECISIONS.md)) and surfaced the current one. Phase B validated every
mechanism the design depends on for **USD 2.23**.

## Thesis

> **τ³-retail's reward is gated on 40 of 114 tasks by an LLM judge hardcoded to one vendor's model.
> Does that judge favour agents from its own family?**

Measured support ([FINDINGS](FINDINGS.md)):

- Reward is `DB × NL_ASSERTION`; `COMMUNICATE` runs on **zero** tasks (A1).
- The judge is **`gpt-4.1-2025-04-14`**, hardcoded, no env override, marked *experimental / WIP* (A2).
- It gates **40 of 114** tasks; the other 74 are effectively DB-only (A3).
- In a **stock** run the same OpenAI model is agent, user simulator, *and* grader.
- The judge is load-bearing: it catches genuine failures DB cannot see (B-L12, task 103), and
  it prevents false positives DB admits (A5).
- It is also fallible: it passed an agent that modified the **wrong order** (B-L12, task 109),
  consistent with it being **unable to see tool calls** (B4).

If verdicts depend on agent family, a component of every published τ³-retail score reflects vendor
affinity rather than agent quality. Nobody has isolated agent↔judge bias on tau-bench
([REFERENCE](REFERENCE.md) §Open).

**Secondary result, free:** published retail scores silently pool 74 DB-only tasks with 40
judge-gated ones (A3). No surveyed work separates them.

## Method: measure by re-grading, not re-running

Generate each trajectory **once**; score the *same saved trajectory* under multiple judges
([D-009](DECISIONS.md)). The contrast is **within-trajectory and paired** — same agent, same
simulator, same task, same conversation — so cross-arm variance and the capability confound vanish.

**Validated, not assumed** ([B-L13](FINDINGS.md)): re-grading saved trajectories reproduced tau2's
own recorded verdict on **11/11 assertions**, with every message rebuilt intact.

The estimand is a **difference-in-differences** — see [PREREGISTRATION §3](PREREGISTRATION.md).
The control term is mandatory; without it the quantity is judge *leniency*, not bias.

### Verified mechanics

| Mechanism | Status |
| --- | --- |
| Judge swap | **Works.** Patch `tau2.evaluator.evaluator_nl_assertions.DEFAULT_LLM_NL_ASSERTIONS`. Patching `tau2.config` is a **silent no-op** — verified both directions (B1) |
| Re-grade saved runs | **Works**, 11/11 fidelity (B-L13) |
| Call granularity | **One judge call per trajectory** — assertions batched in, verdicts batched out |
| Judge input size | **3,409 tokens** mean (1,668–5,853), measured on real trajectories (B-L10) |
| Judge input content | Trajectory as `f"{role}: {content}"` — **tool calls invisible**; 4–11 literal `content: None` lines per trajectory (B4, corroborated in production) |
| Judge temperature | **0.0** (verified). Self-consistency 11/11; flip rate bounded **<9%** (B-L13) |
| Judge cost | **Not accounted by tau2 at all** — ~40% understatement of true run cost (B-L14) |
| Attempt visibility | **Every API attempt logged** at the LiteLLM boundary (A-003), failures included. This is how the 200k TPM ceiling was identified and how true spend is now measured rather than estimated |

## Design

Frozen in [PREREGISTRATION §4](PREREGISTRATION.md). Summary:

| Factor | Levels |
| --- | --- |
| Agent family | 2 — `gpt-4.1-nano`, `gemini/gemini-3.1-flash-lite` |
| Judge family × tier | **4** — 2 families × 2 tiers, to separate family from capability |
| Task | 40 judge-gated, `base` split (entire population; hard cap) |
| Trial | 4 |

**320 trajectories · 1,792 judge evaluations** (1,280 base + 512 §6.3 replicates).
Scaffold stays stock `llm_agent` ("standard").

The four-judge grid is the key addition over v3.0: comparing a strong OpenAI judge against a small
Gemini judge would confound **family** with **capability**. Because re-grading is offline and cheap,
the 2×2 control costs ~USD 2.

## Budget — measured

USD 75 ceiling · **USD 8.35 spent** · **USD 66.65 remaining**. Source of truth:
`results/spend_ledger.json` (regenerated from run artifacts, not maintained by hand).

| Phase | Work | Status | Cost |
| --- | --- | --- | ---: |
| **A** | Evaluator audit (static/replay) | ✅ complete | **$0.00** |
| **B** | 11 verification gates | ✅ complete | **$0.47** |
| **B9** | Run-to-run noise floor (#540) | ✅ complete | **$0.42** |
| **C** | 320 trajectories | ✅ **complete** | **$7.33** (measured) |
| **D** | **1,792** judge evaluations (1,280 base + 512 §6.3 replicates) | running | ~$5.93 |
| **E** | Analysis and release | pending | $0.00 |
| | **Spent to date** | | **$8.35** |
| | **Projected remaining** | | **~$11.00** |

Per-trajectory cost **measured at $0.0212** (mean; 0.0137–0.0300) for the Gemini arm — the v3.0
estimate of $0.140 was **6.6× too high** ([B-L9](FINDINGS.md)). Cost tracks conversation length, not
task complexity.

The OpenAI arm is **substantially cheaper** (~$0.007–0.011/trajectory measured in B9) because
`gpt-4.1-nano` emits no reasoning tokens, where `gemini-3.1-flash-lite` spends ~28% of cost on
thinking that **cannot be disabled** ([B-L4](FINDINGS.md)). But its cost **varies up to 2.6× per
task between runs** ([B-L15](FINDINGS.md)), so its budget needs a range, not a point.

> **Surplus is not a licence to widen scope.** Tasks are hard-capped at 40 by the benchmark.
> Spare budget buys trials and judge replicates only. Resisting scope creep is what has kept this
> project honest through two killed theses.

---

## Phases

### Phase A — Evaluator audit · ✅ COMPLETE · $0.00

Six findings; the stop-gate passed; the prior thesis falsified before any spend.
Scripts: `scripts/phase_a/01`–`04`.

### Phase B — Verification and calibration · ✅ COMPLETE · $0.47

Every gate passed. Scripts: `scripts/phase_b/step1`–`step5`.

| Gate | Result |
| --- | --- |
| B1 judge swappable | PASS — patch target confirmed, `tau2.config` proven a no-op |
| B2 re-grade saved runs | PASS — 11/11 fidelity |
| B3 judge pricing | $2.00 / $8.00 per 1M; Phase D sized from real trajectories |
| B4 judge sees tool calls | **No** — became a finding and contribution #5 |
| B5 judge noise floor | PASS — 11/11 stable; flip rate bounded <9% |
| B6 agent floor gate | PASS — 0.857 on DB-only |
| B6b study-population difficulty | **0.400** on judge-gated — headroom resolved |
| B7 cost calibration | **$0.0212/trajectory** measured |
| B8/B8b thought signatures | PASS on tau2's real path, 16-tool schema |
| — | 5 further findings, contributions #5–#9 |

### Phase B9 — Run-to-run noise floor · ✅ COMPLETE · $0.42

Answered upstream #540, which had **no published answer**. The result is not one number — the two
agent families behave **oppositely at the same temperature 0.0** ([B-L15](FINDINGS.md)):

| Arm | Byte-identical across seeds | Cost spread |
| --- | --- | --- |
| `gemini/gemini-3.1-flash-lite` | **5/5** identical contents/tool-calls/rewards (3 repeat invocations) | **$0.000000** |
| `gpt-4.1-nano` | **0/3** (2 seeds) | up to **2.6×** |

Caching ruled out first (`LLM_CACHE_ENABLED = False`, `litellm.cache = None`, durations differ).

**Consequence carried into Phase C and E:** `pass^k` is a **structural constant** for the
deterministic arm — four trials yield four identical copies, so `pass^4 = pass^1` by construction,
not by measurement. This must be **disclosed as such**, never presented as a reliability result, and
no variance-based statistic may be compared across arms without stating it.

The frozen T = 4 design was **retained, not deviated** ([D-018](DECISIONS.md)).

### Phase C — Trajectory generation · ✅ COMPLETE · **$7.33 measured**

320 trajectories (2 agents × 40 judge-gated tasks × 4 trials), 8/8 invocations,
**zero `infrastructure_error`**, 7,516 logged attempts. Executed from the content-hashed manifest
with balanced 2:2 order; every attempt recorded at the LiteLLM boundary per
[A-003](PREREGISTRATION_AMENDMENTS.md).

| | Gemini arm | OpenAI arm |
| --- | ---: | ---: |
| pass^1 | **0.675** | **0.138** |
| pass^4 | 0.675 *(= pass^1 by construction)* | 0.050 |
| DB component | 0.775 | 0.263 |
| NL component | 0.850 | 0.362 |
| components disagree | 44/160 (28%) | 56/160 (35%) |
| cost / trajectory | $0.02117 | $0.00549 |

**Two results that shape Phase D** ([C-L2](FINDINGS.md), [C-L3](FINDINGS.md)):

1. **Determinism replicated at n=40.** Gemini reproduced identical rewards on **40/40** tasks
   across four invocations; OpenAI on 32/40. So `pass^k` is a **structural constant** for one arm
   and a **real measurement** for the other — not comparable, and it must be said.
2. **The OpenAI arm is floor-bound** at 0.138 against a 50–70% target. Signal remains, but
   capability is now confounded with family. Declared as a limitation rather than fixed: the arms
   are frozen in [§4.2](PREREGISTRATION.md), and swapping one because its baseline disappoints is
   the post-hoc choice pre-registration exists to prevent.

Two invocations were discarded before the final set and retained as evidence in
`results/discarded/`: one whose data our own test destroyed, one degraded by a rate-limit ceiling.
See [A-003](PREREGISTRATION_AMENDMENTS.md) Disclosure.

### Phase D — Judge re-grading · ~$5.93 · **RUNNING**

**1,792 evaluations**, not the 1,280 quoted until now. That figure counted only the base pass
(320 trajectories × 4 judges); [§6.3](PREREGISTRATION.md)'s noise control adds **512** more —
a pre-specified random 20% of trajectories graded 3× per judge. The replicate sample is
**pre-drawn from stated seed 20260922** and published in `results/phaseD_regrade_manifest.json`
*before* execution, stratified as 8 of each invocation's 40 so the per-arm flip rate does not
rest on whatever a free draw happened to give ([A-005](PREREGISTRATION_AMENDMENTS.md)).

| | Evaluations |
| --- | ---: |
| Base — 320 trajectories × 4 judges | 1,280 |
| §6.3 replicates — 64 × 4 × 2 further gradings | 512 |
| **Total** | **1,792** |

Run by `scripts/phase_d/run_phase_d.py`, which applies Phase C's operating discipline to
re-grading: four pre-dispatch gates (freeze, provenance, **input-corpus integrity**, budget),
bounded retries with every attempt logged, and **resume at the granularity of one evaluation**.
The harness it replaces (`regrade.py`) had a validated mechanism but performed **zero retries** —
litellm's own default — which in a paired design does not lose an observation, it *unpairs the
trajectory*, and does so preferentially on the longest and hardest tasks.

Also analyse the judge's `reasoning` field qualitatively on a stratified sample — justifications are
persisted and independently checkable by a reviewer.

### Phase E — Analysis and release · $0.00

Analysis per [PREREGISTRATION §6](PREREGISTRATION.md).

**Deliverables**, ordered by the traction ranking in [REFERENCE](REFERENCE.md) §Reception:

1. **Evaluator audit suite** — Phase A, $0, reusable across languages and domains; scoop-proof.
2. **Judge-swap re-grading harness** — run once, score under many judges. The primary tool.
3. **The finding** — one sentence, with a CI and a stated MDE.
4. **Ten upstream contributions** ([FINDINGS](FINDINGS.md) §Upstream) — filing is separately authorised.
5. Reproduction path: `make verify` offline, zero API keys.

## Verification

Offline, no API keys — this is what makes the artifact reviewable by a stranger.

```bash
make verify      # the single pre-spend gate: docs + freeze + chain + all tests
```

| Test | Asserts | Status |
| --- | --- | --- |
| `tests/test_phase_a_regression.py` | Every Phase A number: 114 tasks, 112 `[DB,NL_ASSERTION]`, 2 `[DB]`, **0 COMMUNICATE**, 40 live judge, 74 DB-only, 104 mutating, splits 74/40/114; judge identity + temperature; B1 patch target *and* that `tau2.config` is a no-op; #514 and B-L7 order sensitivity; A4's 18-action/15-task allowlist; A5's 11-task null-agent set | **18 checks, passing** |
| `tests/test_judge_adapter.py` | Fenced JSON parses; empty / partial / duplicate / extra / mismatched / malformed / non-bool responses all **reject with reward withheld**; explicit upstream contrast (`all([])` is `True`) | **21 checks, passing** |
| `tests/test_runner_guards.py` | Guards **fire**: tampered amendment chain blocks dispatch, budget floor blocks dispatch, existing artifact is skipped, unknown `--only` rejected, manifest 2:2 balanced with pinned snapshot and retries disabled | **8 checks, passing** |
| `scripts/verify_preregistration.py` | Frozen hash intact; amendment chain links verified. Tamper-tested both directions | **passing** |
| `scripts/check_docs.py` | Cross-links; spend matches the generated ledger; no stale claim *asserted*; git provenance not misstated | **passing** |

> Earlier revisions of this table named nine test files that did not exist. The table now lists
> only what runs, and `make verify` executes exactly these.

## Honest risks

- **The OpenAI arm is floor-bound (pass^1 0.138 vs 0.675).** Capability is confounded with family,
  so a measured interaction cannot be attributed to family alone. This is the single largest
  interpretive constraint on the result and must appear in the abstract, not a footnote.
- **The bias may not exist.** A bounded null with a stated MDE is publishable and is accepted in
  advance ([PREREGISTRATION §7](PREREGISTRATION.md)).
- **n = 40 tasks and n = 2 agent families are hard caps.** No claim generalises beyond them.
- **Family is confounded with vendor, tokenizer and training data.** The judge-tier grid separates
  family from *capability*, not from vendor identity.
- **The judge cannot see tool calls**, so any bias found may operate through narration style —
  a mechanism, but one that constrains interpretation.
- **The judge model may be replaced upstream**, dating the specific number. Mitigated: the method is
  the contribution, and the harness re-runs against any judge.
- **Deferred, not dead:** German localisation ([D-006](DECISIONS.md)). Revisit after the judge
  result lands.
