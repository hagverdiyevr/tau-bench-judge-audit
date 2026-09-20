"""Phase B gates B1 and B4 — fully offline, mocked transport, USD 0.00.

B1: can the NL-assertion judge model be swapped, and is our patch target the right one?
B4: does the judge actually see tool calls, or only natural-language content?

Run:  cd vendor/tau2-bench && uv run python ../../scripts/phase_b/b1_b4_judge_gates.py
"""

import json
import pathlib as _pl
from unittest import mock

from loguru import logger

logger.remove()

_REPO = _pl.Path(__file__).resolve().parents[2]
_OUT = _REPO / "results" / "phase_b"
_OUT.mkdir(parents=True, exist_ok=True)

from tau2.data_model.message import AssistantMessage, ToolCall, ToolMessage, UserMessage
from tau2.evaluator import evaluator_nl_assertions as ENA

SENTINEL_JSON = json.dumps(
    {"results": [{"expectedOutcome": "probe", "reasoning": "mocked", "metExpectation": True}]}
)

captured: dict = {}


def fake_generate(*args, **kwargs):
    """Stand-in for tau2.utils.llm_utils.generate — records the call, never touches a provider."""
    captured.clear()
    captured.update(kwargs)
    captured["_positional"] = args
    return AssistantMessage(role="assistant", content=SENTINEL_JSON)


def run_judge(trajectory, assertions=("probe",)):
    with mock.patch.object(ENA, "generate", side_effect=fake_generate):
        ENA.NLAssertionsEvaluator.evaluate_nl_assertions(
            trajectory=list(trajectory), nl_assertions=list(assertions)
        )
    return captured.get("model"), captured.get("messages")


# ---------------------------------------------------------------- B1
print("=" * 72)
print("GATE B1 — is the judge model swappable, and is our patch target correct?")
print("=" * 72)

traj = [UserMessage(role="user", content="hello"), AssistantMessage(role="assistant", content="hi")]

baseline_model, _ = run_judge(traj)
print(f"\n  [baseline]         dispatched model = {baseline_model!r}")

# POSITIVE: patch the name where it is BOUND (the evaluator module namespace)
with mock.patch.object(ENA, "DEFAULT_LLM_NL_ASSERTIONS", "PATCHED/judge-x"):
    patched_model, _ = run_judge(traj)
print(f"  [patch evaluator]  dispatched model = {patched_model!r}")

# NEGATIVE CONTROL: patch tau2.config — should have NO effect, name already imported
import tau2.config as tau2_config

with mock.patch.object(tau2_config, "DEFAULT_LLM_NL_ASSERTIONS", "WRONG/should-not-apply"):
    config_model, _ = run_judge(traj)
print(f"  [patch tau2.config] dispatched model = {config_model!r}   <- must equal baseline")

b1_positive = patched_model == "PATCHED/judge-x"
b1_negative = config_model == baseline_model
b1_pass = b1_positive and b1_negative

print(f"\n  positive (evaluator patch takes effect) : {'PASS' if b1_positive else 'FAIL'}")
print(f"  negative (config patch is a no-op)      : {'PASS' if b1_negative else 'FAIL'}")
print(f"\n  >>> GATE B1: {'PASS' if b1_pass else 'FAIL'}")
if b1_pass:
    print("      Judge is swappable. Patch target CONFIRMED:")
    print("      tau2.evaluator.evaluator_nl_assertions.DEFAULT_LLM_NL_ASSERTIONS")
    print("      Patching tau2.config is a silent no-op — never use it.")

# ---------------------------------------------------------------- B4
print()
print("=" * 72)
print("GATE B4 — does the judge see tool calls?")
print("=" * 72)

TOOL_NAME = "cancel_pending_order"
TOOL_ARG_ORDER = "#W0000042"
TOOL_ARG_REASON = "no longer needed"
TOOL_RESULT = '{"order_id": "#W0000042", "status": "cancelled"}'

tool_call = ToolCall(
    id="call_1",
    name=TOOL_NAME,
    arguments={"order_id": TOOL_ARG_ORDER, "reason": TOOL_ARG_REASON},
    requestor="assistant",
)

# A realistic tool-calling turn: assistant emits tool_calls with NO text content.
traj_tools = [
    UserMessage(role="user", content="Please cancel my order."),
    AssistantMessage(role="assistant", content=None, tool_calls=[tool_call]),
    ToolMessage(id="call_1", role="tool", content=TOOL_RESULT, requestor="assistant"),
    AssistantMessage(role="assistant", content="Your order has been cancelled."),
]

_, messages = run_judge(traj_tools)
user_prompt = next((m.content for m in messages if m.role == "user"), "")

print("\n--- exact trajectory text the judge receives ---")
for line in user_prompt.splitlines():
    if line.strip():
        print(f"  | {line.strip()}")

checks = {
    "tool NAME visible": TOOL_NAME in user_prompt,
    "tool ARGUMENTS visible": TOOL_ARG_ORDER in user_prompt and TOOL_ARG_REASON in user_prompt,
    "tool RESULT visible": "cancelled" in user_prompt,
    "empty assistant turn leaks as 'None'": "assistant: None" in user_prompt,
}
print("\n--- what is observable ---")
for k, v in checks.items():
    print(f"  {'YES' if v else 'NO ':<4} {k}")

print("\n  >>> GATE B4 result:")
if not checks["tool NAME visible"] and not checks["tool ARGUMENTS visible"]:
    print("      CONFIRMED — the judge CANNOT see tool calls (name or arguments).")
    print("      It sees only natural-language content plus tool RESULTS.")
    print("      => It grades agent actions it cannot directly observe.")
else:
    print("      NOT confirmed — tool calls are at least partly visible.")

json.dump(
    {
        "b1": {
            "baseline_model": baseline_model,
            "evaluator_patch_model": patched_model,
            "config_patch_model": config_model,
            "positive_pass": b1_positive,
            "negative_control_pass": b1_negative,
            "pass": b1_pass,
            "confirmed_patch_target": "tau2.evaluator.evaluator_nl_assertions.DEFAULT_LLM_NL_ASSERTIONS",
        },
        "b4": {**checks, "judge_visible_text": user_prompt},
    },
    open(_OUT / "b1_b4_gates.json", "w"),
    indent=1,
)
print(f"\nwrote {_OUT / 'b1_b4_gates.json'}")
