# Retail Agent Reliability Lab — implementation plan and Codex brief

Version: 1.0 • Prepared: 19 September 2026
Owner: Ramiz Hagverdiyev
Status: implementation specification; no benchmark measurements or improvements have been produced yet.
Initial external spending authorization: USD 25 total. This is a cumulative project cap, not a per-session allowance.

> ## ⚠️ SUPERSEDED IN PART — read this first
>
> This v1.0 spec was written against **τ²-bench**. The upstream repository now ships as
> **τ³-bench v1.0.1**, which invalidates several assumptions below (pip → `uv sync`,
> Python 3.10 → `>=3.12,<3.14`), and already provides natively four things §5 plans to build:
> the dev/held-out split (`split_tasks.json`, 74/40/114), `pass_hat_k()`, per-run cost capture
> (`agent_cost`/`user_cost`), and a results viewer.
>
> **The active plan is the τ³-retail evaluator-audit + language-aware-grading plan** (approved
> 19 Sep 2026). Changes that override this document:
>
> | Item | This document (v1.0) | **Active plan** |
> | --- | --- | --- |
> | Spend ceiling | USD 25 | **USD 75** (~40 planned, 35 reserve), authorized 19 Sep 2026 |
> | Time | 18–24h / 4 weeks | 40–60h / 8–10 weeks |
> | Research question | One intervention on a 10/10 task split | Grader-artifact measurement via **re-grading**, German language contrast |
> | Phases | §6–§12 (Phases 0–6) | Phases A–E |
>
> **What remains binding from this document:** the operating rules in §1 (no secrets, no mocked
> results presented as real, pin upstream, preserve stock benchmark behavior, no evaluator state
> in agent inputs, no unevidenced claims), the budget-accounting semantics in §8, the risk
> register in §14, and the release checklist in §16. Those carry forward unchanged.

## 1. Read this first: the decision and the next action

Build a small, reproducible evaluation project around the Retail domain of Sierra's maintained tau-bench repository. Use Gemini Flash models, capture complete experiment costs and trajectories, classify failures, and evaluate one evidence-driven intervention. Ship a useful engineering artifact before pursuing leaderboard performance.

The project question is: **How reliably can an inexpensive agent complete retail customer-service operations, and which engineering intervention changes that reliability at an acceptable cost?**

Start with Phase 0 and implement Phases 1–2 immediately. Do not restart broad benchmark selection or spend days comparing frameworks. The first milestone is one valid Retail trajectory, preserved tool-call metadata, a usable trace, and a verified cost record. A baseline runner is valuable before any accuracy improvement.

### Instructions to the implementing Codex agent

1. Read this document fully and any applicable repository instructions. Inspect existing files and git status before modifying anything; preserve unrelated work.
2. Maintain a short execution plan. Implement the smallest working vertical slice in the phase order below. Use existing harness functionality before writing replacements.
3. The user's USD 25 experiment allowance is already authorized. Do not request that authorization again. Enforce the cumulative cap and proceed with available credentials. Do not assume this allowance authorizes unrelated services or recurring subscriptions.
4. Never print API keys, commit secrets, or request keys in chat. Use local environment variables or a gitignored environment file.
5. If credentials are unavailable, complete installation, integration code, offline checks, documentation, and an exact one-command smoke-run path. Report only the remaining credential action. Never describe mocked output as a real model result.
6. Treat model names and prices below as a dated research snapshot. Verify account access, current documentation, and adapter compatibility during Phase 0. Record any substitutions; never silently fall back to another model.
7. Pin the upstream commit and dependencies. Do not update them mid-comparison. If a necessary correction changes results, rerun affected comparisons and explain why.
8. Preserve benchmark policies, tools, tasks, and evaluators in the baseline. Custom agent interventions must be identified as such.
9. Keep hidden task specifications, expected actions, and evaluator state outside the agent's accessible inputs. Do not use gold answers to construct runtime validation rules.
10. Continue with routine reversible implementation choices autonomously. Public posting, messaging, deployment, and leaderboard submission are separate actions; prepare reviewable materials but do not perform them without authorization.
11. Make no score, saving, production-impact, or hiring claims without evidence. An unsuccessful experiment is an acceptable result.
12. End each work session with implemented changes, verification performed, actual cumulative spend, blockers, and the next executable task in `docs/status.md`.

## 2. Purpose, scope, and career positioning

The intended outcomes are practical experience with tool-using agents; evidence of senior engineering judgment; and a public case study relevant to retail AI engineers and recruiters in Germany, particularly Zalando and Delivery Hero. “One Delivery” from the discussion is provisionally interpreted as Delivery Hero.

Ramiz already has retail AI experience in shopping assistance, recommendations, and multilingual systems. This project should extend that experience with visible evaluation, operational reliability, and cost ownership. It should not be presented as the first evidence of professional experience.

### In scope for version 0.1

- Text-only Retail tasks in the maintained tau-bench harness.
- Two Gemini agent candidates and one fixed user simulator.
- Reproducible experiment manifests and bounded spending.
- Observable traces, native benchmark results, and manual failure analysis.
- One targeted intervention chosen from actual development failures.
- A frozen small held-out comparison with complete reporting.
- An English README, short demo, technical case study, and draft social content.

### Deferred until there is evidence of need

RAG, tau-Knowledge, voice, fine-tuning, reinforcement learning, multi-agent orchestration, model routing, vector databases, production commerce integrations, Kubernetes, a custom dashboard, and a broad model tournament. A framework or feature enters scope only when it solves a documented problem that blocks the current milestone.

Retail support operations are related to real commercial workflows, but a simulator is not a production deployment. This project does not measure real customer satisfaction, revenue, refund loss, or recommendation quality. Do not equate benchmark success with those outcomes.

### Definition of success

Required: another engineer can reproduce a small run; costs and failures are inspectable; integration errors are distinguishable from agent failures; one hypothesis is tested honestly; the owner can explain the system.

Desired: a measurable improvement on the reserved tasks without an unacceptable regression in cost or failure severity.

Not required: leaderboard rank, statistical significance from a tiny sample, a new algorithm, or a positive result.

## 3. Research snapshot and choices

### Benchmark

The maintained repository is `https://github.com/sierra-research/tau2-bench`. Its current README presents the suite as tau-three/tau³-bench while retaining older repository and CLI naming. It includes Retail, task corrections, LiteLLM integration, and an existing trajectory viewer. The README currently specifies Python >=3.12 and <3.14 and installation with uv. Validate against the pinned revision rather than assuming old tutorials apply. [S1]

Use the Retail domain, not the banking-oriented knowledge domain. The stock harness owns simulation, tool execution, and evaluation. Agent code should participate through documented extension points.

### Models and prices recorded in the preceding research

| Exact model ID | Initial role | Standard input USD / 1M | Standard output USD / 1M |
| --- | --- | ---: | ---: |
| `gemini-3.8-flash` | Reference agent and fixed simulator | 0.75 | 3.75 |
| `gemini-3.5-flash-lite` | Efficiency challenger | 0.30 | 2.50 |
| `gemini-3.1-flash-lite` | Optional fallback; not part of initial sweep | 0.25 | 1.50 |

The recorded 3.8 Flash pricing is promotional through 31 December 2026; the documented subsequent rates are 1.50/7.50. Output pricing includes thinking. Rates require verification before paid execution. Free quota is a bonus, not an assumption in the budget. [S2]

Google's model page describes 3.8 Flash as stable, supporting function calling, structured output, and low/medium/high thinking; `minimal` is unsupported. Start the reference agent at low thinking, then keep that choice fixed for its experiment arm. Validate supported settings independently for Flash-Lite; do not copy incompatible parameters across models. Account availability remains untested. [S3]

Use explicit IDs rather than a moving `latest` alias. Record returned model/version information when available. Stable IDs do not guarantee byte-for-byte provider reproducibility, so dates and raw metadata matter.

### Framework decision

Use the stock tau harness with its LiteLLM adapter. Add only thin project-specific configuration, cost accounting, reporting, and an intervention through the documented agent interface. LiteLLM's Gemini documentation explains that tool-call thought signatures live in provider-specific fields and must survive conversation history handling. Test this end to end before interpreting scores. [S4]

LangGraph provides stateful workflow orchestration; ADK provides a Gemini-oriented agent development ecosystem. Both remain options for a later standalone application, not mandatory layers in this experiment. [S5, S6]

### Employer relevance

Zalando's August 2026 engineering article discusses LiteLLM access, cost tracking, agent-session inspection, and practical training. These are useful themes for framing this project. Delivery Hero's engineering site features AI workflow measurement and multilingual query validation. These publications support relevance; they do not establish requirements for a specific open vacancy or promise recruiter interest. [S7, S8]

## 4. Time plan and execution gates

Budget 18–24 focused engineering hours. With two jobs, prefer two 60-minute weekday sessions plus one 3–4-hour weekend block: approximately four weeks. Session numbers below are an ordered sequence, not a demand for daily late-night work. Publish the first engineering milestone after roughly 8–10 hours if it is ready.

| Phase | Sessions | Hours | Spend envelope | Exit gate |
| --- | --- | ---: | ---: | --- |
| 0: verify and initialize | 1 | 1 | 0 | Pinned environment and validated execution plan |
| 1: learn the domain and freeze protocol | 2 | 2 | 0 | Task manifests and protocol written |
| 2: working integration and cost controls | 3–4 | 3–4 | 2 | Valid real trajectory and trustworthy accounting |
| 3: baseline and model comparison | 5–6 | 3 | 4 | Development results and failure taxonomy |
| 4: one intervention | 7–8 | 4–5 | 6 | Frozen intervention with focused checks |
| 5: held-out evaluation | 9–10 | 3–4 | 8 | Complete comparison and reconciled spend |
| 6: portfolio release preparation | 11 | 2–3 | 0 | Reproducible release and publication drafts |
| Contingency | As needed | Within available time | 5 | Reserved, not a target to spend |

If an integration problem consumes the Phase 2 timebox, ship an integration-focused milestone and adjust the schedule. Do not compensate by removing the budget gate or weakening evaluation integrity. If the owner has less time, spread sessions over more weeks without expanding scope.

## 5. Repository and architecture

Choose an existing project location if one exists. Otherwise create `retail-agent-lab`. Keep the upstream checkout pinned and visibly separate from project code. Prefer a documented external checkout or submodule; do not copy untracked upstream source into the project without provenance. Follow applicable upstream licensing.

Proposed structure (adapt names to actual harness interfaces):

```text
retail-agent-lab/
  README.md
  pyproject.toml
  uv.lock
  .env.example
  .gitignore
  configs/
    smoke.yaml
    comparison.yaml
    final.yaml
    pricing.json
  manifests/
    dev_tasks.json
    heldout_tasks.json
  src/retail_agent_lab/
    cli.py
    config.py
    budget.py
    telemetry.py
    reporting.py
    agents/
      validated_agent.py
  tests/
    test_budget.py
    test_history_roundtrip.py
    test_intervention.py
  docs/
    status.md
    protocol.md
    decisions.md
    failure_taxonomy.md
    case_study.md
    publication_plan.md
  runs/                       # raw local data; gitignored by default
  examples/                   # reviewed, sanitized sample artifacts
```

These are proposed project modules, not claims about upstream APIs. Reuse upstream persistence and the existing viewer; only add fields and exports needed for our analysis. A CLI and static report are sufficient.

Boundaries:

- Harness: task loading, simulator, environment, tool execution, scoring.
- Agent: observable conversation, published policy, allowed tools, proposed actions.
- Intervention: checks or state derived only from those observable inputs.
- Experiment layer: model configuration, manifests, budget, logging, reporting.
- Analyst: can inspect development results and evaluator artifacts offline; never feeds hidden fields into the agent.

## 6. Phase 0 — verify and initialize

### Why

Prevent stale documentation, unsupported model IDs, and incompatible adapters from corrupting the experiment before it begins.

### Steps

1. Inspect the working directory, repository instructions, and existing changes. Record current implementation state; do not invent prior work.
2. Fetch the official upstream repository through an available authorized route. Record commit SHA, origin, license, Python requirement, and relevant documentation URLs.
3. Install the core text evaluation dependencies with uv according to the pinned README. Do not install voice or knowledge extras unless required by the actual dependency graph.
4. Read the current CLI help, agent extension guide, configuration code, message schemas, and Retail evaluator. Record exact supported flags before writing scripts around them.
5. Verify current Gemini model IDs and pricing through official sources. Check account availability via an available model-list endpoint or the smallest necessary request. Do not run a full experiment to discover a missing model.
6. Confirm the pinned LiteLLM version supports the selected models and preserves provider-specific metadata. If it needs a change, isolate and document that change before locking the baseline.
7. Create `docs/status.md` with phase, task checklist, blockers, spend-to-date (initially zero), and next action.
8. Create `.env.example` containing names/placeholders only and a gitignore covering secrets and raw runs. Follow the installed adapter's documented environment variable names.

### Acceptance criteria

- Environment imports successfully and CLI help works.
- Upstream revision and dependency versions are recorded.
- Actual model access is verified or explicitly marked blocked.
- Price table records source, check date, billing units, and effective date.
- No credential value is printed or committed.

## 7. Phase 1 — understand Retail and freeze the protocol

### Why

The owner must understand what correct behavior looks like, and the experiment must be specified before optimizing outcomes.

### Steps

1. Read the complete Retail policy and tool schemas. Write a short map of supported operations, required information, confirmation rules, and state transitions. Use the benchmark's rules; do not import assumed Zalando policies or German legal requirements.
2. Manually trace two development tasks. For each turn, write the expected next action, necessary information, and evidence that would establish completion.
3. Inspect the actual task split implementation. Use a documented non-overlapping split if suitable; otherwise create a deterministic custom partition and disclose it.
4. Reserve 10 development tasks and 10 held-out tasks. Distribute available workflow families reasonably. Keep closely related variants in one partition. Select before inspecting model performance.
5. Commit task IDs, selection method, seed where applicable, and manifest hashes. These are a small portfolio evaluation sample, not an official full-domain score.
6. Write `docs/protocol.md`: benchmark revision, task selection, two agent candidates, fixed simulator configuration, trial schedule, limits, metrics, exclusion rules, and planned intervention-selection process.
7. Keep the held-out task payloads out of prompts and developer convenience examples. The evaluation runner can load them; the agent receives only the information provided through the normal harness.
8. Establish a failure taxonomy with definitions: integration, transport, policy interpretation, missing information, wrong tool/arguments, state tracking, premature completion, loop/timeout, simulator anomaly, evaluation ambiguity.

### Acceptance criteria

- Task manifests have no ID overlap and variant grouping is documented.
- The owner can explain a successful task without relying on model output.
- Native scoring behavior and its limitations are documented.
- No evaluator-specific shortcut appears in the agent implementation.

## 8. Phase 2 — integration, telemetry, and budget controls

### Why

Scores are meaningful only after the model-to-tool conversation and the accounting are correct.

### Implementation order

1. Run an offline configuration validation. Verify model IDs, task manifests, output locations, price entries, and limits.
2. Add accounting at the shared request boundary used by both agent and simulator. Account for all retry attempts; prevent hidden provider/adapter retries from bypassing limits.
3. Configure concurrency one initially. Use conservative explicit turn and output limits based on the pinned harness and smoke behavior. Record exact numeric values before comparison; stop on truncation rather than silently changing limits halfway through an arm.
4. Add durable request reservation and settlement records before any paid call. Retain completed run output atomically so an interruption does not lose all evidence.
5. Exercise a Gemini tool-call round trip: assistant tool call, tool response, next assistant turn. Preserve opaque thought signatures exactly; do not attempt to interpret them as reasoning text.
6. Run one real development task, then up to two additional smoke tasks within the USD 2 envelope. Inspect the trace and reconcile returned usage with the price calculation.
7. Verify the normal tool execution path remains under the harness. Do not enable a second SDK automatic tool executor alongside it.
8. Add a small report showing status, native reward, calls, tokens, latency, and spend. Reuse the existing viewer for conversation inspection.

### Budget specification

- USD 25 is the cumulative authorized ceiling, including previous project runs across resumed sessions.
- USD 20 is the planned experiment allocation; USD 5 is held for uncertainty and contingency. Stop starting scheduled experiments at the planning threshold.
- Before a request, reserve a conservative upper-bound cost using input token counts or a validated upper bound, configured maximum billed output, and current rates. If no trustworthy bound is available, do not claim hard enforcement; stop and resolve it before batch execution.
- Dispatch only when settled spend plus outstanding reservations plus the new reservation fits both the active stage envelope and overall ceiling.
- Output reasoning tokens must be counted once according to the provider's usage semantics. Do not double-count fields or assume missing fields mean zero.
- A timed-out request may still incur cost. Keep an unresolved reservation until reconciliation; never automatically release it as free.
- On restart, reload the ledger and reconcile unfinished requests before spending more. Account for all processes using the experiment's credentials, or use an isolated project/key and explain the remaining billing boundary.
- Cap retries; retry only transient conditions with bounded backoff. Authentication/schema errors require repair, not repeated calls.
- Avoid automatic replay of uncertain state-changing tool operations. Inspect whether execution occurred before retrying.
- Disable optional paid grounding, search, and other services not required by Retail. Local simulated tools do not need external commerce services.
- Log application estimates separately from provider-reconciled charges. Allow for tax/FX if the user's USD 25 limit represents cash outlay rather than pre-tax API usage; leave reserve rather than maximizing spend.

### Minimum run record

`run_id`, UTC timestamps, upstream/project commit, config and task-manifest hashes, task ID, trial ID, requested/returned model identifiers, agent and simulator settings, provider request IDs when available, token usage by role, reasoning usage semantics, cache usage if present, prices/version, estimated and reconciled costs, latency, tool calls/results, terminal status, native reward, failure label, and artifact paths.

Never log API secrets. Public examples need an explicit review even when benchmark customer details are synthetic.

### Focused tests

- A request exceeding the remaining allowance is rejected before dispatch.
- Agent, simulator, and retries consume the same cumulative allowance.
- Unknown pricing/missing usage cannot be counted as zero.
- Ledger survives restart and retains ambiguous in-flight reservations.
- Serialized message history preserves tool IDs and provider-specific fields through a multi-turn sequence.

Use offline fixtures for these checks and a minimal live integration smoke. Avoid tests that merely restate configuration literals.

### Acceptance criteria

A completed real trajectory with valid tool history, no silent metadata loss, complete accounting, and functioning stop controls. If unavailable credentials block live validation, mark this gate incomplete and deliver all offline work first.

## 9. Phase 3 — baseline and small model comparison

### Why

Choose a practical reference configuration and identify the recurring failure worth addressing.

### Steps

1. Choose five representative tasks from the development manifest before running models.
2. Evaluate two agent models on those tasks, two trials each: 20 trajectories. Keep the simulator model, prompt, settings, task IDs, and limits fixed. Use the same seed schedule where supported; do not imply seeds guarantee deterministic remote inference.
3. Inspect initial per-trajectory costs. Forecast remaining stage cost using a conservative observed range. Reduce planned run count before launch if the envelope cannot support it; record the deviation.
4. Inspect all failures and several successes. Assign a primary failure label with evidence and optional secondary labels. Record infrastructure failures separately without silently deleting them from the report.
5. Compare success counts, severe mistakes, cost per attempt, total cost divided by successful tasks, and latency. With five tasks, model selection is a practical choice, not a general model ranking.
6. Choose the main agent based on observed quality/cost and integration stability. If the cheap model produces too few useful completions, use Flash as the reference; if results are inconclusive, prefer the reference Flash configuration and document uncertainty.
7. Use the remaining development tasks within the next phase's envelope to test the selected hypothesis. Do not touch held-out outcomes.
8. Prepare the first milestone: working runner, budget mechanism, annotated trajectory, and limitations. No accuracy improvement claim is needed.

### Acceptance criteria

Every attempted run is accounted for, the selection decision is documented, and a recurring actionable failure has been identified—or there is an explicit finding that the sample did not reveal one.

## 10. Phase 4 — one intervention and a controlled ablation

### Why

A small, interpretable change supports learning and credible attribution better than changing prompts, models, tools, and orchestration simultaneously.

### Select using evidence

| Development finding | Candidate change | What could regress |
| --- | --- | --- |
| Missing prerequisites before a write | Observable-state pre-action validator | False blocks, added turns |
| Losing previously confirmed details | Compact structured state summary | Incorrect/stale summaries |
| Claiming completion after tool failure | Tool-result evidence check | Excessive caution or escalation |
| Repeated transient API failure | Bounded recovery policy | Extra spend, duplicate execution |
| Recurring policy misunderstanding | Focused policy checklist | Overfitting or incorrect generalization |

Prefer pre-action validation only if traces justify it. Do not build all five options.

### Steps

1. Write one hypothesis before implementation, including expected benefit, potential harm, metric, and affected workflow.
2. Implement behind one configuration flag. Keep the base model, simulator, tool definitions, task set, and evaluator fixed.
3. Build rules only from the public policy, conversation, and tool responses. Required confirmation must come from actual observable dialogue, not evaluator labels.
4. Add focused regression cases: the observed failure, a valid action that must remain allowed, missing/stale state, and ambiguous execution where appropriate.
5. Run a small matched development comparison. Report extra calls and latency as well as outcomes.
6. Permit at most two development iterations within the allocated time and spend. Document each revision so experimentation history remains visible.
7. Freeze baseline and intervention configs with hashes. Write a decision record explaining the change and alternatives rejected.

### If no improvement appears

Do not widen scope automatically. Keep the baseline, explain the negative result, and release the reliability tooling and failure analysis. If all observed issues are adapter defects, fix the integration and report that contribution separately; a broken adapter is not a valid baseline for a model-quality claim.

### Acceptance criteria

One isolated intervention, observable inputs only, focused regression checks, a frozen comparison, and an explicit statement of what the experiment can establish.

## 11. Phase 5 — frozen evaluation and interpretation

### Steps

1. Verify budget headroom, clean config hashes, pinned versions, and non-overlapping manifests.
2. Evaluate ten reserved tasks with baseline and intervention, two trials per configuration: 40 planned trajectories. If measured costs cannot support this within USD 8, reduce the protocol before seeing held-out results and disclose the new sample size.
3. Predefine execution order to reduce time-related confounding, for example interleaving configurations by task. Keep the simulator identical between arms.
4. Save all attempts. Report interrupted, invalid, and completed runs separately. A stopped run is not silently discarded or described as a normal scored failure without checking evaluator semantics.
5. Make no changes based on emerging held-out scores. If an infrastructure defect invalidates results, document it and rerun both affected arms if affordable.
6. Analyze native task success plus supplemental manual categories. Do not replace the native evaluator with a Gemini judge to obtain a more favorable score.
7. Show paired task outcomes and variability across the two trials. Report counts and percentages together. Do not treat repeated trials of the same task as independent new tasks.
8. If uncertainty intervals are included, resample at task level and explain that ten tasks give unstable estimates. A descriptive report is preferable to unsupported significance claims.
9. Reconcile spend and freeze the report. After inspecting held-out failures, mark that set as used; future tuning needs a fresh evaluation set.

### Required results table

| Configuration | Completed / attempted runs | Native successes | Cost per attempt | Cost per success | Median latency | Severe observed failures |
| --- | --- | --- | --- | --- | --- | --- |
| Baseline | Measured only | n/N | Measured only | Measured only | Measured only | Defined labels + counts |
| Intervention | Measured only | n/N | Measured only | Measured only | Measured only | Defined labels + counts |

Define cost per success as total relevant run cost divided by successful runs, including expenditure on failures. If there are zero successes, report undefined rather than zero. Report user-simulator cost separately as well as combined cost: simulator expense is evaluation overhead, not a direct estimate of deployed customer-service cost.

### Decision rule

Adopt the intervention provisionally only when the paired outcomes and failure analysis support its intended benefit, there is no new severe failure requiring resolution, and added cost/latency is explained. Otherwise retain the baseline. No predetermined score increase is promised.

### Acceptance criteria

Complete accounting, clearly labeled custom subset results, all material regressions disclosed, limitations explicit, and no official leaderboard comparability claim. Any later submission requires a fresh review of the then-current official protocol.

## 12. Phase 6 — reproducible release and visibility

### Repository deliverables

- README opening: business problem, measured outcome or negative finding, reproduction path, and limitations.
- Installation verified from a clean environment where practical; actual tested commands, never invented flags.
- One small smoke command, one experiment command, and one report command provided by the implemented CLI or documented upstream equivalents.
- Pinned versions, benchmark attribution, model configurations, task manifests, pricing snapshot, and decision records.
- Reviewed sample traces and an aggregate results file. Keep secrets and unnecessary raw payloads out of git.
- A 60–90-second local demo showing task, tool action, result, cost, and failure diagnosis.
- A case study whose numbers link back to actual run artifacts.

### Case-study outline

1. Retail workflow and why mistakes matter.
2. Scope and constraints, including USD 25.
3. Baseline architecture and evaluation protocol.
4. Concrete observed failure with annotated trace.
5. Intervention and why it was chosen.
6. Full result table, regressions, costs, and uncertainty.
7. What would be needed for a real deployment.
8. What was learned and the next evidence-driven question.

Production discussion can cover authentication, authorization, idempotency, audit logs, escalation, monitoring, rollout, and rollback. Label these as future design requirements unless implemented and tested; do not label a local benchmark project production-ready.

### Publication sequence

| Timing | Topic | Evidence | Intended reader |
| --- | --- | --- | --- |
| After Phase 3 | Reproducible retail-agent evaluation under a budget | Runner, cost ledger, trace | AI engineers |
| After Phase 4 | One recurring failure and an attempted fix | Annotated before/after, regression check | Applied AI teams |
| After Phase 5–6 | Complete engineering case study | Honest results, repo, demo | Engineers and recruiters |

Prepare English posts. Each should state one useful finding, explain its retail relevance, provide one artifact, and acknowledge the main limitation. Avoid tagging companies merely for reach, implying endorsement, or using tiny-sample percentages as sensational headlines.

Drafts may be prepared autonomously. The user reviews before public posting or outbound messages. Track technical feedback, reproductions, relevant conversations, and interview discussions; views and likes alone do not establish career impact.

### Recruiting use

- Place the project in a pinned portfolio position once it has evidence.
- Connect it to existing shopping-assistant and recommendation experience in applications.
- For applied AI/platform/customer-service roles, emphasize reliability, evaluation, and cost decisions.
- For search/recommendation roles, lead with the relevant production work; this project provides additional engineering evidence.
- Check live vacancies when applying. Do not infer current openings, relocation support, or required technologies from a blog article.
- Prepare a five-minute interview explanation: problem, constraints, architecture, surprising failure, measured trade-off, and next step.
- Build a CV bullet only after measurements exist. Use placeholders in drafts rather than fabricated improvements.

## 13. Learning responsibilities and working rhythm

Codex can accelerate implementation, but Ramiz should own the reasoning and be able to defend it.

| Session activity | Ramiz | Codex |
| --- | --- | --- |
| Policy walkthrough | Predict correct actions; explain ambiguity | Locate policy/tool definitions and illustrate flow |
| Architecture | Decide boundaries and trade-offs | Implement thin interfaces and document decisions |
| Failure analysis | Review at least three traces personally | Summarize evidence and propose categories |
| Intervention | State a falsifiable hypothesis | Implement and run focused checks |
| Evaluation | Explain leakage, simulator effects, and cost denominators | Execute frozen protocol and produce tables |
| Publication | Validate claims and articulate lessons | Draft from verified artifacts |

At the end of each session, answer: What did we learn? What evidence supports it? What is the next smallest action? Update status before stopping. Avoid increasing workload by adding parallel projects or extra frameworks.

## 14. Risk register and stop conditions

| Risk | Early signal | Action |
| --- | --- | --- |
| Unsupported/stale model ID | Not listed or access error | Check official docs and account; record an explicit replacement |
| Lost Gemini metadata | Tool-history error | Fix serialization and rerun smoke before scoring |
| Incomplete cost accounting | Missing usage or unexpected bill | Stop paid batches and reconcile |
| Budget exhausted | Reservation cannot fit | Stop paid work; finish analysis and documentation |
| Simulator weakness/bias | Implausible behavior or inconsistent instructions | Flag affected traces; disclose same-family limitation; do not swap simulator mid-arm |
| Task/evaluator ambiguity | Correct-looking action receives unexpected outcome | Inspect offline; log issue; avoid agent-specific gold-answer hacks |
| Held-out contamination | Tuning after inspecting final failures | Mark set used; reserve new tasks for later claims |
| Intervention false blocks | Valid requests fail | Record regression; retain baseline if unresolved |
| Scope/time overrun | No working run after integration timebox | Ship a smaller integration milestone; defer optional features |
| Weak career narrative | Framework list with no evidence | Rewrite around decisions, failures, and measured trade-offs |

A spending cap in project code protects only requests routed through that code and its accounting assumptions. Do not represent it as a provider-wide billing guarantee. Keep outstanding reservations and reconciliation conservative.

## 15. Backlog after version 0.1

Only choose one follow-up after reviewing the evidence:

1. Broader task coverage and additional trials to test whether the finding persists.
2. Cross-provider simulator validation to investigate correlated model-family behavior.
3. Small, separately labeled robustness suite for paraphrases, interruptions, and language variation. Do not merge custom tasks into official benchmark scores.
4. A standalone retail workflow demo with explicit human approval for consequential actions, using LangGraph or ADK if the workflow requires it.
5. A useful upstream issue or small contribution if integration work reveals a reproducible defect; follow contribution instructions and prepare a reviewable patch.
6. A search/recommendation evaluation project if actual target vacancies make that a better career investment.

No follow-up may silently exceed the initial USD 25 allowance. New spending requires new authorization.

## 16. Final release checklist

- [ ] One real task completes through the intended harness.
- [ ] Thought-signature/tool-history handling verified.
- [ ] Model and simulator versions/configurations recorded.
- [ ] Agent sees no hidden evaluation information.
- [ ] Budget accounting covers both roles, retries, and restarts.
- [ ] Baseline and intervention are frozen and comparable.
- [ ] Every attempted run has a terminal or explicitly unresolved status.
- [ ] Metrics include counts, costs, and limitations.
- [ ] Negative findings and regressions are retained.
- [ ] Reproduction commands have actually been exercised.
- [ ] Public examples and git changes reviewed for secrets.
- [ ] Case study contains no unsupported business or leaderboard claims.
- [ ] Owner can explain the implementation and the experiment without reading a script.
- [ ] Publication drafts are ready for user review.

## 17. Copy-paste kickoff instruction

> Read RETAIL_AGENT_IMPLEMENTATION_PLAN.md and execute the phases in order. Begin with repository inspection and Phase 0; then implement the smallest working Retail evaluation with Gemini, cost accounting, and a verified tool-call history. The total initial project spending cap is USD 25, already authorized; retain the specified reserve and cumulative ledger. Use current official documentation to validate model access, pricing, and exact harness interfaces before paid runs. Do not restart broad planning, add unnecessary frameworks, or tune against held-out tasks. If credentials are missing, complete all offline implementation and verification and provide the exact remaining setup action. Maintain docs/status.md with progress, actual spend, evidence, and next action. Prepare publication materials only after results exist; do not publish or contact anyone automatically.

## 18. Source register

Research basis: official sources reviewed in the preceding planning conversation on 19 September 2026. This document carries that dated analysis forward; implementation must verify time-sensitive availability and pricing. Proposed schedules, budget allocations, architecture, and acceptance criteria are our engineering decisions, not vendor recommendations.

- [S1] Sierra tau-bench repository and linked documentation: https://github.com/sierra-research/tau2-bench
- [S2] Gemini Developer API pricing: https://ai.google.dev/gemini-api/docs/pricing
- [S3] Gemini 3.8 Flash model documentation: https://ai.google.dev/gemini-api/docs/models/gemini-3.8-flash ; model catalog: https://ai.google.dev/gemini-api/docs/models
- [S4] LiteLLM Gemini integration: https://docs.litellm.ai/docs/providers/gemini
- [S5] LangGraph overview: https://docs.langchain.com/oss/python/langgraph/overview
- [S6] Google ADK documentation: https://adk.dev/
- [S7] Zalando, Agentic Engineering at Zalando: a snapshot: https://engineering.zalando.com/posts/2026/08/agentic-engineering-at-zalando-a-snapshot.html
- [S8] Delivery Hero engineering publication index: https://deliveryhero.jobs/

No benchmark result, current vacancy, model account access, or implementation completion is asserted by this plan.
