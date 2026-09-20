# STATUS — session resume point

> **Role in the memory system:** where we are *right now*. Read this first when resuming.
> Update it at the end of every working session. Keep it short — detail belongs in
> [FINDINGS.md](FINDINGS.md), rationale in [DECISIONS.md](DECISIONS.md), the route in
> [PLAN.md](PLAN.md).

**Last updated:** 20 September 2026
**Phase:** A complete · **B complete except B9** — B1-B8b ALL PASSED
**Cumulative API spend: ~USD 0.47 of 75.00** ($74.53 remaining)

---

## Where we are

Phase A — the zero-cost evaluator audit — is **complete and passed its stop-gate**. It produced six
findings, four upstream contributions ready to file, and it **falsified the previous thesis before
any money was spent** ([D-004](DECISIONS.md)).

The project is now aimed at: **does τ³-retail's hardcoded `gpt-4.1-2025-04-14` NL-assertion judge
favor agents from its own model family?** Measured by re-grading saved trajectories, not re-running
them. Full rationale in [PLAN.md](PLAN.md).

## What exists on disk

```
t-bench/
├── CLAUDE.md                      binding rules + map of this system
├── RETAIL_AGENT_IMPLEMENTATION_PLAN.md   v1.0, SUPERSEDED banner; rules still binding
├── .python-version                3.12.9  (NOT 3.13 — see FINDINGS A0)
├── docs/
│   ├── STATUS.md                  ← you are here
│   ├── PLAN.md                    v4.0, active (measured budget)
│   ├── PREREGISTRATION.md         DRAFT — freeze before Phase C
│   ├── FINDINGS.md                Phase A + B evidence, append-only
│   ├── DECISIONS.md               D-001..D-017, append-only
│   └── REFERENCE.md               upstream API, pricing, prior art
├── scripts/phase_a/               01..04, reproduce every Phase A number
├── scripts/phase_b/               step1..step5, all Phase B gates
├── results/                       phase_a/, phase_b/ raw outputs
└── vendor/tau2-bench/             pinned v1.0.1 @ fc0055dc, .venv on 3.12.9
```

**Not yet created:** our own package, `pyproject.toml`, the offline test suite, budget ledger.
`.env` holds live Gemini + OpenAI keys and is gitignored.

**Git:** initialised on `main`, `.gitignore` in place (secrets, venvs, raw runs excluded — verified).
**Nothing is committed yet** — no commit has been requested. 15 files are staged-ready outside
`vendor/`.

⚠️ **Outstanding structural task:** `vendor/tau2-bench` is a plain clone, not a registered git
submodule. [D-007](DECISIONS.md) calls for a submodule so the pin is reproducible for a stranger.
Converting it requires a commit, so it is deferred until commits are requested. Until then the pin
is documented (`v1.0.1` @ `fc0055dc`) but not enforced by git.

## Verified environment

| | |
| --- | --- |
| Upstream | `v1.0.1` @ `fc0055dc4e0a316c3f83133267fbd6faaa770992`, MIT |
| Python | **3.12.9** — 3.13 is broken ([A0](FINDINGS.md)), machine default 3.14.6 is out of range |
| Install | `cd vendor/tau2-bench && uv sync` — verified working, 114 retail tasks load |
| Credentials | **Gemini AI Studio key live**, Tier 1 prepaid, `serviceTier: standard`. `.env` gitignored. No OpenAI/Anthropic key yet. |

## Next executable task

**Phase B has passed every gate.** The method is validated, the agent works, the study population
has headroom, judge noise is bounded, and costs are ~7x below plan.

Before any Phase C spend:

1. **Pre-register** the primary contrast and hash it ([D-012](DECISIONS.md)) — the design now has
   many defensible cuts (agent x judge x task-regime x trial), so the primary comparison must be
   frozen in writing first.
2. **B9** — run-to-run noise floor (upstream #540): one config twice, different seeds, ~USD 0.20.
   This is the ruler every later claim is read against.
3. **Phase C** — 240 trajectories, 2 agent families x 40 judge-gated tasks x 2 trials (~USD 5).
4. **Phase D** — re-grade under gpt-4.1 and a Gemini judge (~USD 2.52), plus replicates.

**Projected remaining: ~USD 8 of the USD 74.53 left.** Surplus should buy trials and judge
replicates, not new questions — tasks are hard-capped at 40 by [A3](FINDINGS.md).

## Blockers

| Blocker | Impact |
| --- | --- |
| ~~Gemini-only credentials~~ | **RESOLVED 20 Sep** — OpenAI key added; `gpt-4.1-2025-04-14` verified reachable, cost accounting exact. Both families available. |
| `gpt-4.1-2025-04-14` pricing unverified | Cannot finalise the Phase D budget line until checked (gate B3) |
| `gemini-2.5-flash-lite` unavailable | The 2.5×-cheaper arm is closed to new accounts ([B-L1](FINDINGS.md)); planned arms stand |

## Open questions carried forward

- **B5:** judge noise floor. **Correction (20 Sep):** the judge is pinned at
  `DEFAULT_LLM_NL_ASSERTIONS_TEMPERATURE = 0.0`, not hot as previously recorded. Risk downgraded
  from "most likely way the study ends early" to a routine check — temp 0 still is not determinism
  for remote inference.
- Whether `llm_agent_gt` leaks ground truth (name implies it does; unread). Do not use as a baseline
  until checked.
- **Resolved 20 Sep:** B1 (judge swappable — yes), B4 (judge sees tool calls — no). See
  [FINDINGS](FINDINGS.md).

## Session log

| Date | Work | Spend |
| --- | --- | ---: |
| 2026-09-19 | Research passes (harness, prior art, pricing); hostile review; plan v2 approved | $0.00 |
| 2026-09-19 | Governance fix ($25 → $75 in both documents); repo init; upstream pinned @ v1.0.1 | $0.00 |
| 2026-09-19 | **Phase A complete** — 6 findings; thesis falsified; direction changed to judge bias | $0.00 |
| 2026-09-20 | Memory system restructured into 6 documents; CLAUDE.md realigned; Phase A scripts made repo-relative and **all headline numbers re-verified**; `.gitignore` added | $0.00 |
| 2026-09-20 | **Gate B1 PASS** (judge swappable; `tau2.config` patch proven a silent no-op). **Gate B4 CONFIRMED** — judge cannot see tool calls; became upstream contribution #5 | $0.00 |
| 2026-09-20 | **Live gates**: key verified, billing + cost accounting exact, thinking overhead measured (28%, not controllable), **B8/B8b PASS** — signatures survive tau2's path only via LiteLLM's id-packing. Contributions #6–7 added | ~$0.02 |
| 2026-09-20 | **Step 4**: B6 floor gate PASS (6/7, reward 0.857), B7 cost calibration — measured **$0.0212/traj, 6.6x below plan**. New defect B-L7: ACTION checker order-sensitive (contribution #8) | ~$0.16 |
| 2026-09-20 | OpenAI key added. **Phase B complete**: B2/B3/B5/B6b PASS. Judge-gated tasks measured far harder (0.400 vs 0.857 — headroom resolved). DB/judge disagree on 3/5. Contribution #9: tau2 does not account for judge cost (~40% understatement) | ~$0.29 |
