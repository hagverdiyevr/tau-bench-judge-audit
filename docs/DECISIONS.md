# DECISIONS — why we chose what we chose

> **Role in the memory system:** append-only log of forks in the road. Each entry records what was
> decided, the evidence behind it, and what it costs us. **Never delete an entry** — supersede it
> with a later one and mark the original `SUPERSEDED BY`. The evidence cited lives in
> [FINDINGS.md](FINDINGS.md) (ours) or [REFERENCE.md](REFERENCE.md) (external). The resulting plan
> lives in [PLAN.md](PLAN.md).
>
> Several entries below are records of **theses we killed**. They are the most valuable content
> here: they are why the project is not doing the obvious thing, and they are the actual
> engineering work of the planning phase.

Status values: `ACTIVE` · `SUPERSEDED` · `REJECTED` (an option considered and declined)

---

## D-001 — Raise the budget and time envelope · `ACTIVE` · 19 Sep 2026

**Context.** `RETAIL_AGENT_IMPLEMENTATION_PLAN.md` v1.0 specified USD 25 and 18–24h. The owner's
actual goal is a portfolio artifact that earns attention from senior AI engineers and recruiters,
toward retail/e-commerce AI roles in Germany. At USD 25 the achievable sample (10 held-out tasks ×
2 trials = 40 trajectories) cannot support any claim a stranger would repeat.

**Decision.** USD 75 cumulative ceiling (~40 planned, 35 reserve); 40–60 engineering hours over
8–10 weeks. Authorized by the owner in conversation, 19 Sep 2026.

**Consequence.** Both on-disk documents stated USD 25 as "already authorized", which would have
stalled an implementing agent. Both were updated the same day; `RETAIL_AGENT_IMPLEMENTATION_PLAN.md`
carries a SUPERSEDED banner. v1.0's *operating rules* remain binding; its *scope* does not.

## D-002 — Drop agent architectures as experiment arms · `ACTIVE` · 19 Sep 2026

**Context.** The owner initially asked for "different frameworks" to signal seniority, and chose to
make agent architectures (ReAct vs state-machine vs LangGraph) the controlled arms.

**Evidence.** The field has treated "scaffold choice dominates" as settled since 2025 — Harness-Bench
(5,194 trajectories, 23.8pp best-vs-worst spread) and *Stop Comparing LLM Agents Without Disclosing
the Harness* (arXiv 2605.23950). Sierra's own leaderboard already encodes it as a standard/custom
submission split. v1.0's risk register names the failure mode directly: *"weak career narrative →
framework list with no evidence."*

**Decision.** Dropped. Scaffold stays stock `llm_agent`, which also keeps runs classifiable as
"standard" for leaderboard purposes. Owner reversed their earlier choice once shown the evidence.

**Consequence.** Those trajectories are reallocated to the open question. Framework breadth is not
demonstrated by this artifact; it is demonstrable in interview discussion instead.

## D-003 — Reject the four crowded angles · `REJECTED` · 19 Sep 2026

**Evidence.** Prior-art survey, recorded in [REFERENCE.md](REFERENCE.md) §Prior art.

| Angle | Why rejected |
| --- | --- |
| Cost-vs-accuracy Pareto | HAL/Princeton (21,730 rollouts), OpenRouter, Artificial Analysis all ship Pareto charts. Alan (European) added the latency-budget cut. |
| Retail failure taxonomy | Advani et al., 9,876 τ²-bench trajectories, 8 model families (arXiv 2606.09863). |
| Annotation / evaluator audit **as headline** | Amazon `tau2-bench-verified` + SABER (arXiv 2512.07850); arXiv 2607.02577 found 18.5% misalignment; **Sierra already shipped 50+ task fixes** Feb 2026. Redoing it is homework against a moved target. |
| Prompt / scaffolding uplift | IRMA (+16.1% pass@5, arXiv 2508.20931), Cleanlab (−50% failures). |

**Note.** The audit work was *retained as Phase A infrastructure* — it just stopped being the claim.
That turned out to be the decision that saved the project: Phase A is what falsified D-004.

## D-004 — Reject the COMMUNICATE multilingual-artifact thesis · `REJECTED` · 19 Sep 2026

**The thesis.** Retail reward is `DB × COMMUNICATE`, where DB is a language-agnostic state hash and
COMMUNICATE is an English substring match. So a German score drop decomposes into genuine execution
failure versus measurement artifact — and if the drop concentrates in COMMUNICATE, "the multilingual
penalty is substantially a measurement artifact."

**Why it died — three independent reasons, in the order we found them:**

1. **Hostile review, before any spend.** A null agent reproduces the predicted signature exactly:
   doing nothing scores DB=1 on every read-only task and COMMUNICATE=0. The hypothesis and total
   agent collapse would have been observationally identical. Also: with English keys, the German
   COMMUNICATE ceiling is just the fraction of language-invariant keys — computable offline for
   $0, so measuring it with API calls would confirm arithmetic.
2. **Phase A [A1](FINDINGS.md), decisive.** **`COMMUNICATE` appears in the `reward_basis` of 0 of
   114 retail tasks.** `[DB, COMMUNICATE]` is the *schema default*; every τ³ task overrides it to
   `[DB, NL_ASSERTION]`. There is no substring grader in retail's reward path. `communicate_info`
   is populated on 36 tasks and scored on none.
3. The supporting claim — that this explains SEATauBench's R²=0.014 — annexed another paper's null
   result across a different benchmark, languages and models. Range restriction explains it equally
   well.

**Cost of the error: USD 0.00.** The Phase-A-before-spending gate existed precisely for this.

**Lesson, recorded deliberately.** The false premise came from reading the schema default and the
docs rather than the shipped task files. Three independent research passes all repeated it. **Verify
against data, not documentation, before a claim becomes load-bearing.**

## D-005 — Reject the agent × simulator "self-preference" matrix · `REJECTED` · 19 Sep 2026

**Context.** Proposed as the second open gap: does an agent score higher when the user simulator
shares its model family? Sierra's τ²-bench paper reports retail simulator error at 40% (12%
critical) without ever sizing the score distortion.

**Why rejected — two independent killers:**

1. **Power.** A 3×3 interaction at 40 tasks × 4 trials = 1,440 trajectories ≈ USD 72 — the entire
   budget — for an interaction MDE of ~22pp against a hypothesized ~9pp effect. Underpowered by
   2.5× at full price. All 114 tasks (~USD 200+) still only reaches ~13pp. A later analysis using
   the averaged matched-vs-crossed contrast and bimodal task difficulty put the MDE at 9–13pp — at
   best a *bounded null*, never a confirmation.
2. **Construct.** The user simulator is not a judge, and the grader was believed deterministic, so
   there was no evaluative-bias channel. "Self-preference" was a mislabel.

**Partially reversed by Phase A.** [A2](FINDINGS.md) showed the grader *is* an LLM. Killer (2) no
longer applies to the **judge**; see D-006. Killer (1) still applies to the **simulator** matrix,
which stays rejected.

## D-006 — Adopt agent × judge family bias as the research question · `ACTIVE` · 19 Sep 2026

**Context.** Phase A findings [A2](FINDINGS.md), [A3](FINDINGS.md), [A5](FINDINGS.md):

- Retail reward is `DB × NL_ASSERTION`; the judge is hardcoded to `gpt-4.1-2025-04-14` and its own
  source marks it *experimental / WIP*.
- It gates 40 of 114 tasks; the other 74 are effectively DB-only.
- On tasks 67/68/105, that judge is the **only** thing preventing a false positive that the DB check
  admits.

**Decision.** Research question: **does the hardcoded judge favor agents from its own model family?**
Measured by **re-grading identical saved trajectories** under judges from several families.

**Why this one survives where the others died:**

| Criterion | Status |
| --- | --- |
| Novelty | The survey found judge self-preference established *in the LLM-judge literature* but **never isolated on tau-bench**, and never agent↔judge. |
| Construct validity | There genuinely is a judge. D-005's killer (2) is void. |
| Power | The grader contrast is **within-trajectory and paired** — no cross-arm variance, no capability confound. |
| Cost | Trajectories are generated once (~USD 35); each re-grade is one short LLM call (~USD 2 total). |
| Stakes | It is the official leaderboard scoring path, not a side quest. |
| Scoop-proof | Phase A ships regardless and retains value independently. |

**Known constraint.** The live judge covers 40 tasks (`base`), only 11 in `test`. The design must use
`base`. n=40 clusters.

**Declined alternatives at this fork:** adding a German language axis (halves n per cell and adds a
15–25h localization workstream — deferred, not dead); publishing Phase A alone (kept as the fallback
if Phase B gates fail); leading with the DB-only/judge-gated regime split ([A3](FINDINGS.md)) — kept
as a secondary result.

## D-007 — Overlay package + pinned submodule, not a fork · `ACTIVE` · 19 Sep 2026

**Decision.** Upstream stays a read-only checkout pinned at `v1.0.1`
(`fc0055dc4e0a316c3f83133267fbd6faaa770992`); our code registers into it from outside.

**Rationale.** "The baseline is stock" becomes *provable by construction* rather than something a
reviewer must audit a diff to believe. `git diff` on our repo is exactly our contribution. A future
upstream PR is a directory move plus a few registry lines.

**Consequence.** Registration cannot happen by mere installation — a wrapper entry point must import
the registry, register, and delegate to `tau2.cli.main` **in-process**, so that our accounting
callback sits in the same interpreter as the requests.

**Scope clarified 20 Sep 2026.** "Byte-untouched" means *we author no change to upstream tracked
content*. It cannot mean a byte-clean working tree: upstream's `uv.lock` is stale at v1.0.1
([A0b](FINDINGS.md)) and `uv` rewrites one version string on every sync, `--frozen` included.
The pin is enforced by the **recorded submodule commit SHA**, which working-tree dirt cannot change.
Tests assert the SHA, never cleanliness. An earlier session did overwrite upstream's
`.python-version`; it was restored, and `uv sync --frozen` is now the required install command.

## D-008 — Pin Python 3.12.9, not 3.13 · `ACTIVE` · 19 Sep 2026

**Supersedes** the plan's original 3.13.13 pin. **Evidence:** [A0](FINDINGS.md) — `tau2` v1.0.1
declares `<3.14` but cannot be imported on 3.13 (`audioop`, PEP 594). Effective range is
`>=3.12,<3.13`. Machine default `python3` is 3.14.6, so the pin is mandatory, not cosmetic.

## D-009 — Measure by re-grading, not re-running · `ACTIVE` · 19 Sep 2026

**Context.** The artifact under study is a property of the **grader**, not of the run.

**Decision.** Generate each trajectory once; score the *same saved trajectory* under multiple
graders. Report the grader contrast as a **paired within-trajectory quantity**.

**Rationale.** Eliminates cross-arm sampling variance and the capability confound entirely, and costs
nothing in additional trajectory generation. This is the structural move that makes the study
affordable at USD 75.

**Required control term.** The naive contrast is confounded with grader leniency — a lenient judge
raises *every* score. The identified estimand is a difference-in-differences:

```
Effect = [R_judgeB(agentA) − R_judgeA(agentA)] − [R_judgeB(agentB) − R_judgeA(agentB)]
```

Omitting the control term measures leniency, not bias.

## D-010 — Prefer tasks over trials for paired contrasts · `ACTIVE` · 19 Sep 2026

**Supersedes** the earlier "4 trials" choice. For a paired difference at fixed trajectory budget
`N = n·T`, variance is `(σ²_between·T + v̄)/N` — **monotonically increasing in `T`**. Tasks add
independent clusters; trials only shrink a term already divided by `T`.

**Decision.** Spend the budget on tasks, not trials. `T` is set by what pass^k reporting requires,
not by what the estimator wants. Never headline `pass^k` at `k = num_trials` — it degenerates to one
Bernoulli draw per task.

## D-011 — Do not fix upstream #514 · `ACTIVE` · 19 Sep 2026

**Evidence.** [A6](FINDINGS.md) — the DB hash is order-sensitive on lists; semantically identical
payment orderings flip the verdict.

**Decision.** Leave it. Fixing it breaks comparability with official v1.0.1 numbers. Compute both
the raw and an order-canonicalized hash for every run and report both; the delta is a diagnostic and
a reportable finding, not a bug to patch mid-study.

## D-012 — Pre-register before the confirmatory run · `ACTIVE` · 19 Sep 2026

**Decision.** Before any confirmatory spend, freeze and `sha256`-commit: the primary contrast, the
judge model list, the task ID set, exclusion rules, and the analysis plan. Everything not in that
file is explicitly exploratory and reported without inferential statistics.

**Rationale.** The design has many defensible cuts (judge × agent × task-regime × trial). Without a
pre-registered primary contrast, something will look significant. This is also the cheapest possible
answer to the reviewer objection that the result was chosen after seeing the data.

## D-013 — Add OpenAI only, not OpenRouter · `ACTIVE` · 20 Sep 2026

**Context.** Phase B exhausted what one model family allows. The study is *does the incumbent judge
favour its own family* — Gemini on both sides yields no contrast. Options were OpenAI only,
OpenRouter (many families, one account), Gemini+Gemma only, or stop.

**Decision.** Add an OpenAI key. Verified reachable 20 Sep 2026; `gpt-4.1-2025-04-14` cost
accounting agrees exactly with our own table.

**Consequence.** Gives the core 2×2 the estimand needs: agent ∈ {OpenAI, Google} × judge ∈
{OpenAI, Google}, including **the real incumbent judge**. Forgoes an Anthropic judge arm, so
"family" in this study means these two lineages and nothing broader — declared in
[PREREGISTRATION §8](PREREGISTRATION.md).

**Why not Gemini+Gemma.** It would have measured "does judge choice move scores at all" — a real
validity question, but unable to say anything about the incumbent or about published numbers, which
is where the force of the finding comes from.

## D-014 — Four judges, not two: separate family from capability · `ACTIVE` · 20 Sep 2026

**Context.** The obvious design compares `gpt-4.1` (high tier) against a cheap Gemini judge. That
**confounds family with capability**: a weaker judge may be more easily persuaded by narration
regardless of family — which matters especially given [B4](FINDINGS.md), since the judge cannot see
tool calls and grades narration plus tool results.

**Decision.** Use a 2 × 2 judge grid — {OpenAI, Google} × {high, low tier}:
`gpt-4.1-2025-04-14`, `gpt-4.1-mini`, `gemini-3.8-flash`, `gemini-3.1-flash-lite`.

**Rationale.** A genuine family effect must appear in **both** tiers; a capability effect appears in
**both** families. The two become separable rather than entangled.

**Cost.** ~USD 2 extra, because re-grading is offline and one call per trajectory. This is the
clearest instance of [D-009](DECISIONS.md) paying off: a control that would be unaffordable as
extra *runs* is trivial as extra *grades*.

## D-015 — Include all 40 judge-gated tasks, with a sensitivity analysis · `ACTIVE` · 20 Sep 2026

**Context.** Five judge-gated tasks (89, 76, 109, 103, 43) were run and inspected in detail during
Phase B ([B-L11](FINDINGS.md), [B-L12](FINDINGS.md)). Strict held-out discipline would burn them —
but the population is only 40, so excluding them costs 12.5% of n.

**Decision.** Primary analysis uses all 40. A **pre-specified sensitivity analysis excluding those
5** must not change the conclusion.

**Justification.** No hypothesis or parameter was tuned on them; they informed *scale* (the headroom
question) only. That is a scale decision, not outcome-dependent tuning. Disclosed in
[PREREGISTRATION §4.3](PREREGISTRATION.md) rather than quietly absorbed.

## D-016 — Four trials, despite D-010 · `ACTIVE` · 20 Sep 2026

**Context.** [D-010](DECISIONS.md) established that for paired contrasts at fixed trajectory budget,
tasks strictly dominate trials. That argued for T = 2.

**Decision.** T = 4.

**Why this does not contradict D-010.** D-010 governs how to spend a *fixed* budget when tasks can
grow. Here tasks are **hard-capped at 40** by the benchmark ([A3](FINDINGS.md)), so the trade-off
D-010 describes does not exist — surplus budget cannot buy tasks. Given measured costs are 6.6×
below plan, T = 4 is affordable and buys pass^1..pass^4 at the leaderboard's own convention.

## D-017 — Do not fix B-L7 (action-checker order sensitivity) · `ACTIVE` · 20 Sep 2026

**Evidence.** [B-L7](FINDINGS.md) — a tool call identical to gold except for list order scores
`action_match: false`.

**Decision.** Leave it, exactly as with [D-011](DECISIONS.md) and #514. Patching it would break
comparability with official v1.0.1 numbers. Instead: document it, add a regression test
(`test_action_order.py`), and report it upstream as contribution #8.

**Note.** Retail does not gate on `ACTION`, so within this study it is a misleading *diagnostic*
only. It becomes a false-negative mechanism in any domain that does gate on it — which is why it is
worth reporting even though it does not affect our numbers.

## D-018 — Retain T = 4 rather than deviate after the determinism finding · `ACTIVE` · 20 Sep 2026

**Context.** [B-L15](FINDINGS.md) showed `gemini-3.1-flash-lite` reproduces identical message
contents, tool calls, rewards and costs across repeat invocations at temperature 0, while
`gpt-4.1-nano` reproduces none. *(Corrected 2026-09-21: the original wording said
"byte-identical across seeds". Zero simulations were byte-identical, and LiteLLM drops `seed` for
the gemini provider entirely — see the CORRECTION in B-L15. The decision below is unaffected: the
reproducibility asymmetry is real either way.)* For the
deterministic arm, the frozen T = 4 buys four identical copies — roughly **USD 3 of pure waste**.

**Decision.** **Keep T = 4 for both arms.** No deviation is entered in
[PREREGISTRATION §10](PREREGISTRATION.md); §10 remains empty.

**Rationale.** The pre-registration was frozen specifically so that post-hoc design changes cannot
be made once data starts arriving. Amending it to save 4% of a budget with USD 74 remaining would
spend the exact credibility the freeze was created to buy — on its first test, which is when
precedent is set. Symmetric T across arms also keeps the paired analysis simple.

**What changes instead — reporting, not design.** `pass^4` for the deterministic arm is disclosed
as **trivially equal to `pass^1`**, never presented as a reliability measurement, and no
variance-based statistic is compared across arms without stating the asymmetry.

**Precedent.** A deviation is warranted when the frozen design would produce an *invalid* result.
It is not warranted to reduce cost or tidy an inefficiency. This entry is the reference for future
deviation requests.

## D-019 — Act on an external review rather than defend against it · `ACTIVE` · 21 Sep 2026

**Context.** Before dispatching Phase C, an external model reviewed the repository and produced 10
recommendations plus a "not yet safe to start" verdict. An independent verification pass
(6 dimensions, 34 findings, `$0.0025` of probes) checked each claim against code and data.

**Decision.** Treat the review as evidence, verify every claim independently, and act on what
survives — including the parts that were errors of ours rather than the reviewer's.

**What it caught that we had wrong.** Five of our own claims were false:

| Our claim | Reality |
| --- | --- |
| Gemini runs were "byte-identical" | **0/5** whole-object identical; our script hashed only `role + content` |
| "across seeds 1001/1002/1003" | LiteLLM **drops `seed`** for the gemini provider; those were repeat invocations |
| `.env` backup held only placeholders | Held a **live OpenAI key** behind a `#` |
| Ledger "regenerated from run artifacts" | No generator existed; line items did not sum to the total |
| PLAN's verification table | Named **9 test files; 2 existed** |

**What the reviewer overstated.** "Reward metadata differ" — reward metadata is *identical* across
runs; only the judge's free-text justification varies. And J1, though a genuine blocker, could not
have affected Phase C generation, only Phase D re-grading.

**The sharpest consequence.** J1 (`gemini-3.8-flash` fences its JSON and crashes the evaluator) was
made *more* central by our own [A-001](PREREGISTRATION_AMENDMENTS.md), which pinned the **primary**
estimand to that judge. Had we dispatched first, we would have generated 320 trajectories and only
then discovered Phase D could not score them.

**Cost of the review: `$0.09` of probes. Cost avoided: a 320-trajectory run scored by a broken
parser, and a published paper resting on a false determinism claim.**

**Precedent.** An unsolicited review that contradicts our own records is worth more than one that
agrees. Verify it independently, correct the record where it is right, and say plainly where it is
wrong — do not split the difference.

## D-020 — Never infer success from a weak proxy · `ACTIVE` · 22 Sep 2026

**Context.** Three defects surfaced during Phase C, all mine, all with the same shape: a check
asked an *easy* question and treated the answer as evidence for a *different, harder* one.

| Proxy asked | Property that actually mattered | Damage |
| --- | --- | --- |
| `if created` (did *I* make this directory?) | Is it safe to delete what is here? | A test overwrote a real artifact and **destroyed 40 paid simulations**; no export existed |
| `returncode == 0` | Did every task actually run? | An invocation was marked `completed` with **6/40 simulations dead** of `infrastructure_error` |
| `artifact.exists()` | Is this invocation complete? | Resume accepted a **21/40 truncated file** from a killed run as finished |

Each would have entered the confirmatory analysis silently. None raised an error.

**Decision.** A check must verify the property it is relied upon for, not a correlate of it.
Concretely, now enforced in code and tests:

- Completion requires a **journal entry** *and* the **full expected simulation count** *and*
  **zero `infrastructure_error`** — not an exit code, not a file's existence.
- Tests write only to a **reserved probe path** that no real invocation can claim, and restore in
  `finally`, not on a conditional.
- Anomalies **fail loudly**. The fail-closed judge adapter is the same principle applied to the
  judge: an unparseable or incomplete verdict withholds reward rather than defaulting to a pass —
  which is precisely upstream's `all([]) is True` defect ([B-L16](FINDINGS.md)).

**Why this is worth a decision entry.** The pattern recurred three times in one phase despite each
individual fix being obvious in hindsight. It is also the *same* failure mode as the upstream
defects this project exists to document: `#499` swallows replay exceptions, `get_response_cost()`
returns `0.0` on error, `all([])` returns `True`. The benchmark's bugs and our own share a root —
**treating absence of evidence as evidence of success** — and the study loses its standing to
report theirs if it repeats them.

**Test of the rule:** if the check passed while the underlying property was false, would anything
notice? If not, the check is a proxy and must be replaced.

## D-021 — Lead with the positives; report the primary as an underpowered null, never as "no bias"

**Date:** 22 September 2026 · **Context:** Phase D complete, [D-L1..D-L5](FINDINGS.md)

**The fork.** The pre-registered primary came back null: FamilyBias **+0.0063**, 95% CI
**[−0.0875, +0.1062]**, and TOST against ±5pp does **not** clear. Three ways to present that.

| Option | Why not |
| --- | --- |
| **A. Headline "the τ³ judge is not biased."** | Unsupported. The CI admits effects up to ±10.6pp, and the realized MDE is **0.1367** — the design could only ever have seen a ~14-point effect. Absence of evidence, sold as evidence of absence. It is also the fourth appearance of [D-020](DECISIONS.md)'s shape: a weak instrument's silence read as a strong result. |
| **B. Bury the null; publish only the defects.** | Suppresses the pre-registered result because it was uninteresting. That is exactly the practice pre-registration exists to prevent, and [CLAUDE.md](../CLAUDE.md) requires negative results be retained. |
| **C. Report the null precisely, lead with the positives.** | **Chosen.** |

**Decision.** The primary is reported as *"no family bias detectable **between these two specific
agents**, at a design whose realized MDE is 0.137"* — with the ruled-out region
(|effect| > 0.1062), the failed TOST, and the [C-L3](FINDINGS.md) floor-bound confound all stated
**in the same breath**, not in a limitations section at the end.

The **deliverable leads with the three positive findings**, which are sharper than the null and do
not depend on it:

1. **A 9.1-point judge-leniency spread** ([D-L2](FINDINGS.md)) — swapping only the grader moves a
   reported score by more than most leaderboard gaps. And the DiD control is what stops this being
   published as bias: the incumbent's +0.053 edge on the OpenAI arm comes with a +0.050 edge on the
   Google arm. **Without the control term this study would have reported a false positive.**
2. **A 100% fence-crash rate** ([D-L3](FINDINGS.md)) — 448/448 for `gemini-3.8-flash` against
   upstream's raw `json.loads`. Not a flaky edge case; a total failure for anyone swapping the judge.
3. **The official grader is not reproducible** ([D-L5](FINDINGS.md)) — the incumbent `gpt-4.1` is
   the *only* judge of four that flipped a verdict across byte-identical requests at temperature 0,
   independently reproducing [C-L2](FINDINGS.md)'s agent-role asymmetry in the judge role.

**Rationale.** The null is real and must be published, but it is the *weakest* thing measured here.
The three positives are direct measurements with no power caveat — and the leniency result is what
gives the null its value: it shows the instrument **can** detect large judge differences, so the
absence of an *interaction* is informative rather than merely quiet.

**Consequence.** No headline may contain "unbiased", "fair" or "no bias" unqualified. Phase E's
title and abstract lead with judge leniency and the grader's irreproducibility; the pre-registered
null is reported in full, in its own section, with its MDE beside it.

**Why more spend would not fix this.** Between-task SD is **0.3087** over a task set hard-capped at
**40** by the benchmark ([A3](FINDINGS.md)). Trials reduce within-task noise, which is not the
binding term. Only more *tasks* would move the MDE, and none exist. USD 61.24 remains and **cannot
buy power here** — a structural ceiling, not a budget decision.
