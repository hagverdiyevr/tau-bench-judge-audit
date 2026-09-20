# STATUS — session resume point

> **Role in the memory system:** where we are *right now*. Read this first when resuming.
> Update it at the end of every working session. Keep it short — detail belongs in
> [FINDINGS.md](FINDINGS.md), rationale in [DECISIONS.md](DECISIONS.md), the route in
> [PLAN.md](PLAN.md).

**Last updated:** 20 September 2026 (commit `24aa218`)
**Phase:** A ✅ · B ✅ (all 11 gates + B9) · pre-registration **FROZEN** · **Phase C is next**
**Cumulative API spend: USD 0.89 of 75.00** — USD 74.11 remaining
**Ledger of record:** `results/spend_ledger.json` (regenerated from run artifacts)

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
│   ├── PREREGISTRATION.md         FROZEN a917984e, 2026-09-20T10:54:29Z
│   ├── FINDINGS.md                Phase A + B evidence, append-only
│   ├── DECISIONS.md               D-001..D-018, append-only
│   └── REFERENCE.md               upstream API, pricing, prior art
├── scripts/phase_a/               01..04, reproduce every Phase A number
├── scripts/phase_b/               step1..step5, all Phase B gates
├── results/                       phase_a/, phase_b/, spend_ledger.json
├── scripts/check_docs.py          doc alignment — run every iteration
├── scripts/verify_preregistration.py  tamper check for the freeze
└── vendor/tau2-bench/             pinned v1.0.1 @ fc0055dc, .venv on 3.12.9
```

**Not yet created:** our own package, `pyproject.toml`, the offline test suite, budget ledger.
`.env` holds live Gemini + OpenAI keys and is gitignored.

**Git:** committed on `main` — `24aa218`, 33 files, working tree clean.
`vendor/tau2-bench` is now a **registered submodule** pinned at `v1.0.1` (`fc0055dc`), so the pin is
**enforced by git**, not merely documented.

**Reproducibility verified end to end (20 Sep):** a fresh
`git clone --recurse-submodules` yields the full tree with upstream data present, **no secrets**,
and `scripts/phase_a/01` regenerates the headline Phase A numbers with **no setup and no API keys**.

## Verified environment

| | |
| --- | --- |
| Upstream | `v1.0.1` @ `fc0055dc4e0a316c3f83133267fbd6faaa770992`, MIT |
| Python | **3.12.9** — 3.13 is broken ([A0](FINDINGS.md)), machine default 3.14.6 is out of range |
| Install | `cd vendor/tau2-bench && uv sync` — verified working, 114 retail tasks load |
| Credentials | **Gemini AI Studio key live**, Tier 1 prepaid, `serviceTier: standard`. `.env` gitignored. No OpenAI/Anthropic key yet. |

## Next executable task

**Phase C — generate 320 confirmatory trajectories** (~USD 3.50).
Unblocked: the pre-registration is frozen and verified.

Per [PREREGISTRATION §4–5](PREREGISTRATION.md): 2 agents × 40 judge-gated `base` tasks × 4 trials,
one invocation per (agent × trial index), interleaved by a pre-drawn seeded permutation,
resume-never-restart, intention-to-treat primary.

**Carry into Phase C:**
- `pass^k` is a **structural constant** for the Gemini arm ([B-L15](FINDINGS.md)) — four trials
  produce four identical copies. Disclose; never present as a reliability measurement.
- Judge cost is **not tracked by tau2** ([B-L14](FINDINGS.md)) — our ledger must add it.
- OpenAI-arm cost varies up to **2.6× per task between runs** — budget a range, not a point.

Then **Phase D** (1,280 judge evaluations, ~USD 5.97) and **Phase E** (analysis, USD 0.00).

**Parallel, non-blocking:** ten upstream contributions are prepared and unfiled. Filing is a
separately authorised action and does not depend on the study's outcome.

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
| 2026-09-20 | **Initial commit `24aa218`** — 33 files. Upstream converted to a submodule (pin now git-enforced). Restored upstream to pristine after an earlier overwrite; `uv sync --frozen` now required. A0 nuanced, A0b added. Fresh-clone reproducibility verified | $0.00 |
| 2026-09-20 | Pre-registration **FROZEN** (`a917984e`, tamper-tested) + verifier. **B9 complete** — answered #540; found determinism asymmetry between families (contribution #10). Docs realigned; spend ledger automated | ~$0.42 |
