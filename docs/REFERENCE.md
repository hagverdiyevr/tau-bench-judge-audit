# REFERENCE — external facts we verified

> **Role in the memory system:** facts **others established** that we checked and now rely on —
> upstream API surface, vendor pricing, prior art. Distinct from [FINDINGS.md](FINDINGS.md), which
> holds only our own measurements. Slow-changing; re-verify anything time-sensitive before it
> becomes load-bearing in a published claim.

**Entries verified 19–22 September 2026** unless noted. Prices and model availability are
time-sensitive — **re-verify before any paid run and again at write-up time.**

---

## 1. Upstream harness — τ³-bench

| | |
| --- | --- |
| Repo | `sierra-research/tau2-bench` (the τ² name persists; the release is **τ³-bench**) |
| Pinned | tag `v1.0.1`, commit `fc0055dc4e0a316c3f83133267fbd6faaa770992` |
| Package / version | `tau2` / `1.0.1` · MIT · homepage `taubench.com` |
| Python | declares `>=3.12,<3.14` — **actually `>=3.12,<3.13`**, see [FINDINGS A0](FINDINGS.md) |
| Install | `uv sync` (not pip) |
| Extras | `voice`, `live`, `knowledge`, `gym`, `dev`, `experiments`, `all` |
| Domains | `mock`, `airline`, `retail`, `telecom`, `telecom-workflow`, `banking_knowledge` |

### Retail domain

Data in `data/tau2/domains/retail/`: `tasks.json` (346 KB, **114 tasks**), `split_tasks.json`
(train 74 / test 40 / base 114), `policy.md` (6.7 KB markdown prose), `db.json` (2.8 MB),
plus voice variants and `task_issues/`.

Code in `src/tau2/domains/retail/`: `data_model.py`, `environment.py`, `tools.py` (29 KB),
`utils.py`. **Tool descriptions are Python docstrings** parsed at runtime by `docstring-parser` —
localizing them requires code, not data.

**Tool types** (from `@is_tool(...)` decorators): 7 WRITE (`cancel_pending_order`,
`exchange_delivered_order_items`, `modify_pending_order_address`, `modify_pending_order_items`,
`modify_pending_order_payment`, `modify_user_address`, `return_delivered_order_items`);
7 READ; 2 GENERIC (`calculate`, `transfer_to_human_agents`).

### Scoring machinery

Final reward = **product** of the components listed in the task's `evaluation_criteria.reward_basis`.
Any zero component zeroes the total. Components absent from the basis do not run; criteria absent
from the task default to 1.0. Abnormal termination → reward 0 before evaluation.

| `RewardType` | Evaluator | Mechanism |
| --- | --- | --- |
| `DB` | `evaluator_env.py` | Predicted end-DB hash vs gold DB hash |
| `ENV_ASSERTION` | `evaluator_env.py` | Assertion list |
| `COMMUNICATE` | `evaluator_communicate.py` | Substring match on `communicate_info` |
| `NL_ASSERTION` | `evaluator_nl_assertions.py` | **LLM judge**, `DEFAULT_LLM_NL_ASSERTIONS = "gpt-4.1-2025-04-14"` (`config.py:24`); marked *experimental / WIP* |
| `ACTION` | `evaluator_action.py` | Matching tool call per listed action |

> The schema default is `[DB, COMMUNICATE]` ("matches the original τ-bench"). **What retail tasks
> actually use is different** — see [FINDINGS A1](FINDINGS.md). Do not trust the default.

Gold DB is built by replaying `evaluation_criteria.actions` in a clean environment, with exceptions
swallowed as warnings (upstream #499 — see [FINDINGS A4](FINDINGS.md)).

### Extension points

- **Agent:** `HalfDuplexAgent` (`src/tau2/agent/base_agent.py`), constructor
  `__init__(self, tools: list[Tool], domain_policy: str)` — receives **only** tools and policy, so
  evaluator isolation is architectural. Reference impl `llm_agent.py`. Register via
  `registry.register_agent_factory(fn, "name")`; the name becomes `--agent`.
- **User simulator:** `HalfDuplexUser` (`user_simulator_base.py`), via `registry.register_user(...)`.
- **Domain:** `src/tau2/domains/<name>/` + `data/tau2/domains/<name>/`, registered with
  `register_domain` / `register_tasks`. `split_tasks.json` **must** contain a `base` split.
- Registered at import: domains as above; agents `llm_agent`, `llm_agent_gt`, `llm_agent_solo`,
  `discrete_time_audio_native_agent`; users `user_simulator`, `dummy_user`.
  ⚠️ `llm_agent_gt` — name implies ground-truth conditioning; **unverified**, do not use as a
  baseline without reading it.

### Metrics and persistence (reuse, do not reimplement)

- `pass_hat_k(num_trials, success_count, k) = comb(success_count,k)/comb(num_trials,k)` in
  `metrics/agent_metrics.py`; per-task via `get_tasks_pass_hat_k()`.
- `metrics/break_down_metrics.py` returns per-task and per-action DataFrames.
- `SimulationRun` persists `agent_cost`, `user_cost`, `agent_usage`, `reward_info`, `messages`,
  `trial`, `seed`, `termination_reason`, `duration`.
- `RewardInfo.reward_breakdown: dict[RewardType, float]` — per-component scores, recoverable offline.
- ⚠️ `get_response_cost()` in `utils/llm_utils.py` **catches exceptions and returns `0.0`**, so an
  unpriced model silently reports as free. Compute cost independently and cross-check.
- ⚠️ **No judge cost is recorded anywhere.** `SimulationRun` has only `agent_cost` / `user_cost`;
  `reward_info` and `info` carry none. NL-assertion judge spend is invisible — measured ~40%
  understatement on judge-gated tasks ([B-L14](FINDINGS.md)).

### CLI

`tau2 run` flags: `--domain`, `--agent-llm`, `--user-llm`, `--agent-llm-args`, `--user-llm-args`,
`--agent`, `--user`, `--num-trials` (1), `--num-tasks`, `--task-ids`, `--task-split-name` (`base`),
`--max-steps` (200), `--max-errors` (10), `--max-concurrency` (3), `--seed` (300), `--save-to`,
`--max-retries` (3), `--timeout`, `--review-model` (`claude-opus-4-5`).

Other commands: `tau2 view` (terminal results browser, `--only-show-failed`), `tau2 play`,
`tau2 review`, `tau2 evaluate-trajs <paths> --fresh-tasks` (**re-grade saved runs offline** — the
mechanism D-009 depends on; confirm it reloads criteria from the task file), `tau2 leaderboard`,
`tau2 submit`, `tau2 domain`, `tau2 check-data`, `tau2 convert-results`.

Results land in `data/simulations/<run_name>/results.json`. `TAU2_DATA_DIR` required for
non-editable installs.

### Known open upstream defects

*Rows marked **filed 22 Sep** were reported by us as [@hagverdiyevr](https://github.com/hagverdiyevr); see [UPSTREAM_ISSUES.md](UPSTREAM_ISSUES.md).*

| Issue | Defect | Our stance |
| --- | --- | --- |
| **#499** | 18 retail golden actions raise during gold replay, silently swallowed | Reproduced and characterized — [A4](FINDINGS.md). **Evidence posted 22 Sep**: the 16-read / 2-write split; tasks 64 and 105 have policy-violating gold |
| **#514** | DB hash order-sensitive on lists | Confirmed [A6](FINDINGS.md); **do not fix** (D-011), report both hashes |
| **#384 / #327** | No-op / missing reward checks permit false-positive rewards | Quantified via null-agent baseline [A5](FINDINGS.md). **Evidence posted 22 Sep**: 72/114 retail tasks auto-pass the NL component; null agent passes DB on 11 |
| **#540** | Run-to-run noise floor of published baselines unknown | **Evidence posted 22 Sep** decomposing the floor into agent and judge terms. | **Answered** by [C-L2](FINDINGS.md) at **n=40**: not one number — at temperature 0 `gemini-3.1-flash-lite` reproduces identical rewards 40/40 across four invocations while `gpt-4.1-nano` reproduces 32/40. Supersedes the 5-task pilot in [B-L15](FINDINGS.md) |
| **#224** | "Airline domain may NOT be a reliable benchmark" | Context only; we use retail |
| **#474** (closed) | NL-assertion judge hardcoded, no override mechanism | Still reproduces on v1.0.1. **Evidence posted 22 Sep**: the override is worth **9.1 points** of leniency ([D-L2](FINDINGS.md)) |
| — | Py3.13 import failure | Ours, [A0](FINDINGS.md). **NOT filed** — could not be reproduced (no 3.13 available; `audioop` dependency not locatable). Withdrawn rather than asserted, [D-022](DECISIONS.md) |
| **#553** | Judge prompt is ~20% literal `assistant: None`; line 79 ignores its own documented intent | Ours, [B4](FINDINGS.md) — **filed 22 Sep** |
| **#554** | `all([])` scores an empty or short judge response as a full pass | Ours, [B-L16](FINDINGS.md) — **filed 22 Sep** |
| **#555** | Judge parses with raw `json.loads`; `gemini-3.8-flash` crashes 448/448 | Ours, [B-L16](FINDINGS.md), [D-L3](FINDINGS.md) — **filed 22 Sep** |
| **#558** | `--seed` silently dropped for Gemini via `litellm.drop_params = True` | Ours, [B-L15 correction](FINDINGS.md) — **filed 22 Sep** |
| **#559** | `ToolCall` has no `provider_specific_fields`; signatures ride in the `id` (4,572 chars observed) | Ours, [B-L6](FINDINGS.md) — **filed 22 Sep** |
| **#560** | Committed `uv.lock` stale at tag v1.0.1 | Ours, [A0b](FINDINGS.md) — **filed 22 Sep**. `uv sync --frozen` still succeeds (tested) |
| **#557** | ACTION checker order-sensitive on lists | Ours, [B-L7](FINDINGS.md) — **filed 22 Sep**; **do not fix locally** ([D-017](DECISIONS.md)) |
| **#556** | Judge cost unaccounted; hidden share varies 30–60% by agent model | Ours, [B-L14](FINDINGS.md) — **filed 22 Sep** |
| — | **NL-judge path ignores upstream's own fence stripper** — `evaluator_nl_assertions.py:127` calls raw `json.loads` while `llm_utils.py:509` provides `extract_json_from_llm_response`, so `gemini-3.8-flash` crashes the evaluator | Ours, [B-L16](FINDINGS.md); one-line wiring fix, **do not patch our vendored copy** |
| — | **`all([])` scores an empty judge response as a full pass**; duplicate, extra and mismatched verdicts equally silent | Ours, [B-L16](FINDINGS.md); mitigated by our fail-closed adapter, not by patching upstream |
| — | Committed `uv.lock` stale at v1.0.1 (records `1.0.0`) | Ours, [A0b](FINDINGS.md); cosmetic, but it dirties every working tree |

**Comparability:** results from `< v1.0.1` are formally non-comparable; 50+ tasks changed Feb 2026.
Leaderboard submissions need pass^1–pass^4, ≥4 trials/domain, cost optional, and are classified
**"standard"** (unmodified scaffold) vs **"custom"**.

---

## 2. Models and pricing

Verified against `ai.google.dev/gemini-api/docs/pricing` (page updated 2026-09-16), OpenAI,
Anthropic and DeepSeek pricing pages. **All figures USD per 1M tokens.**

| Model ID | Input | Output | Notes |
| --- | ---: | ---: | --- |
| `gpt-5-nano` | 0.05 | 0.40 | Price floor; parallel function calling |
| `gpt-4.1-nano` | 0.10 | 0.40 | |
| `groq/openai/gpt-oss-120b` | 0.15 | 0.60 | Open-weight; Groq is a *serving* provider, not lineage |
| `gpt-5-mini` | 0.25 | 2.00 | |
| `gemini/gemini-3.1-flash-lite` | 0.25 | 1.50 | `minimal` thinking default; 1M ctx |
| `gemini/gemini-3.5-flash-lite` | 0.30 | 2.50 | |
| `gemini/gemini-3.8-flash` | 0.75 | 3.75 | **Promotional through 2026-12-31**, then 1.50/7.50. Cannot go below `low` thinking |
| `claude-haiku-4-5-20251001` | 1.00 | 5.00 | Retirement "not sooner than 2026-10-15" — check before use |
| `gpt-4.1-2025-04-14` | **2.00** | **8.00** | **The hardcoded τ³ NL-assertion judge** — also the default agent, user simulator and env interface. Verified 20 Sep 2026 ([B-L10](FINDINGS.md)) |
| `gpt-4.1-mini` | 0.40 | 1.60 | Low-tier OpenAI judge arm (capability control, [D-014](DECISIONS.md)) |
| `gpt-4.1-nano` | 0.10 | 0.40 | OpenAI **agent** arm |
| `gemini-2.5-flash-lite` | 0.10 | 0.40 | ⚠️ **404 for new accounts** — "no longer available to new users"; verified 20 Sep 2026 ([B-L1](FINDINGS.md)) |

**Estimated all-in cost per trajectory** (agent + simulator, ~30 calls each, no caching):
`gpt-5-nano` ~$0.030 · `gpt-oss-120b` ~$0.078 · `gemini-3.1-flash-lite` ~$0.140 ·
`gemini-3.8-flash` ~$0.405 · `claude-haiku-4-5` ~$0.540.

**Role split:** the agent is ~79% of trajectory cost, the simulator ~21% (it sees no tool outputs).
So an expensive *simulator* is affordable where an expensive *agent* is not.

**Three corrections to the above, all resolved by pilot measurement:**
- Thinking tokens bill as output and can push cost **1.5–2×** on any thinking-on arm.
- Context caching could cut input cost substantially (input is ~95% of spend; the workload — fixed
  system prompt + tool schemas + growing prefix re-sent ~30× — is the ideal case).
- Batch mode is 50% off at Google/OpenAI/Anthropic but is async; unusable for live multi-turn.

### Adapter hazards (LiteLLM)

- **litellm#25322 (OPEN)** — Gemini **thought signatures** mis-propagated in multi-turn tool calling.
  Google requires verbatim resend; Gemini 3.x enforces strictly; in parallel calls only the **first**
  `functionCall` carries the signature. Failure is **silent degradation** (short garbage replies,
  repetition loops, token burn) typically after 3–4 successful tool calls — *not* a clean error. A
  Gemini arm hitting this scores as "bad at multi-turn tool use". Validate structurally before
  trusting any Gemini score.
- `gemini-3.1-flash-lite-preview` is **shut down**; the GA ID is un-suffixed. LiteLLM's registry
  still lists the dead preview with live pricing.
- litellm#18896 — Gemini 3 Flash returns `completion_tokens_details = None` unless
  `reasoning_effort` is passed explicitly. Always pass it.
- ⚠️ **`reasoning_effort` is silently ignored on `gemini-3.1-flash-lite`** — `default`/`low`/`none`
  give byte-identical usage and cost. Thinking overhead (~28% of cost on realistic prompts) is
  **not controllable**. Measured 20 Sep 2026 ([B-L4](FINDINGS.md)).
- ⚠️ `max_tokens` must exceed the thinking budget or content returns **empty while still billed**
  ([B-L3](FINDINGS.md)).
- Cost/usage introspection: `response._hidden_params["response_cost"]`,
  `usage.completion_tokens_details.reasoning_tokens`. LiteLLM's price list is community-maintained —
  assert against our own table.

---

## 3. Prior art — what is taken and what is open

Full survey 19 Sep 2026. Decisions derived from it: [D-003](DECISIONS.md), [D-005](DECISIONS.md),
[D-006](DECISIONS.md).

### Benchmark lineage

- **τ-bench** (arXiv 2406.12045, ICLR 2025) — introduced `pass^k`. Retail 115 tasks. Headline:
  GPT-4o ~61% pass^1 → **<25% pass^8** on retail. Simulator was `gpt-4-0613` at temp 1.0.
- **τ²-bench** (arXiv 2506.07982) — dual-control telecom. **Publishes retail user-simulator error at
  40% / 12% critical**, airline 47% / 13% — acknowledged, never sized as score distortion.
- **τ³-bench** (Sierra, 18 Mar 2026) — current generation; adds `banking_knowledge` + voice.
  Companions: τ-Voice (2603.13686), τ-knowledge, μ-Bench, τ^τ-bench (2609.04611).
- **Sierra's own task fixes** (Feb 2026) — 50+ tasks across airline/retail, crediting τ-Bench-Verified
  and community contributions. Airline moved +14 to +20 points.

### Occupied niches

| Niche | Owner |
| --- | --- |
| Cost-vs-accuracy Pareto | HAL/Princeton (arXiv 2510.11977, 21,730 rollouts, ~$40k), OpenRouter, Artificial Analysis; Alan (Europe) added latency budgets |
| Retail failure taxonomy | Advani et al. (arXiv 2606.09863) — 9,876 τ²-bench trajectories, 8 families; false-success 13–79% across families |
| Annotation / validity audit | Amazon `tau2-bench-verified` + SABER (2512.07850); arXiv 2607.02577 (τ²-Retail: 112 tasks, 11 disagreements) |
| Scaffolding uplift | IRMA (2508.20931), Cleanlab |
| Scaffold-dominance argument | Harness-Bench (2605.27922, 23.8pp spread), arXiv 2605.23950 — **neither on tau-bench** |
| Simulated-vs-human users | *Lost in Simulation* (2601.17087) — τ-Bench retail, up to **9pp** spread across simulator LLMs |
| Multilingual | Sierra τ-Multilingual PRs #538/#546 (ES/PT/HI/KO/ZH); SEATauBench (2606.28715, SE Asia); `j-tau-bench` (Japanese) |

### Open

1. **Agent ↔ judge family bias on tau-bench.** Judge self-preference is established in the
   LLM-judge literature but **never isolated on tau-bench**, and never agent↔judge. → **D-006, adopted.**
2. **Non-Iberian European localization.** German, French, Dutch, Polish, Turkish all empty.
   SEATauBench's S1–S4 ladder + canonical-token masking is a citable, reusable method. → *deferred*.
3. **Cost against pass^k rather than pass^1.** Every cost leaderboard uses single-run accuracy. →
   *folded in as an analysis layer*.

### Reception pattern (drives deliverable format)

Traction ranks **infrastructure/tool > corrected-dataset artifact > one sharp counterintuitive
finding > leaderboard chart > full paper**. `tau2-bench-verified` (~53 stars) got Sierra to change
the official benchmark — the highest impact-per-effort on the list. Lewis Tunstall's single
manually-read-trajectory finding (a chatty model with zero tool-calling beats a real one on Airline)
is the most-cited criticism of the benchmark.

**Explainer content is completely saturated** by an SEO content-farm layer. Do not write one.

### Adjacent benchmarks (for framing, not for use)

CRMArena-Pro (2505.18878, Salesforce — European retailers run Salesforce), ECom-Bench (2507.05639,
EMNLP 2025, GPT-4o only 10–20%), BFCL v4, WebMall (SIGIR 2026), ShoppingBench, EComAgentBench.
WebShop / Mind2Web are dated — citing them as the primary frame signals being behind.
