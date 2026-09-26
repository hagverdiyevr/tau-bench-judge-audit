"""STEP 3b / GATE B8b — does the signature survive TAU2'S OWN message path?

COST: ~USD 0.02 (8 turns, real retail tools, growing context).

WHY THIS EXISTS:
Step 3 passed, but it exercised the RAW litellm path. Phase C will run through tau2's own
models, and tau2.data_model.message.ToolCall has ONLY {id, name, arguments, requestor} -
no provider_specific_fields, no thought_signature, no extra="allow". llm_utils.py:436 builds
ToolCall(...) from the raw response, so anything outside those four fields is DISCARDED.

tau2's outgoing conversion (to_litellm_messages) does preserve tc.id. LiteLLM's FALLBACK
transport packs the signature into the id as `call_x__thought__<sig>`. So the signature
survives IFF it travels via the id rather than via provider_specific_fields.

This test answers that empirically, using the real retail tools and tau2's own generate().

Run:  cd vendor/tau2-bench && uv run --frozen python ../../scripts/phase_b/step3b_tau2_path_signature.py
"""

import json
import pathlib as _pl

from dotenv import load_dotenv
from loguru import logger

logger.remove()

_REPO = _pl.Path(__file__).resolve().parents[2]
_OUT = _REPO / "results" / "phase_b"
_OUT.mkdir(parents=True, exist_ok=True)
load_dotenv(_REPO / ".env")

from tau2.data_model.message import AssistantMessage, SystemMessage, ToolMessage, UserMessage
from tau2.domains.retail.environment import get_environment
from tau2.utils.llm_utils import generate

MODEL = "gemini/gemini-3.1-flash-lite"
N_TURNS = 8

env = get_environment()
tools = env.get_tools()
tool_names = [t.name for t in tools]

print("=" * 78)
print("STEP 3b / GATE B8b — signature survival through TAU2's own message path")
print(f"  model: {MODEL}   |   real retail tools: {len(tools)}")
print("=" * 78)

messages = [
    SystemMessage(
        role="system",
        content=(
            "You are a retail customer service agent. For EVERY user request you MUST call a "
            "tool before replying. Never answer from memory."
        ),
    )
]

ORDER_IDS = [f"#W000{i:04d}" for i in range(1, N_TURNS + 1)]
turns = []
degraded = False
id_carries_sig = False

for i in range(1, N_TURNS + 1):
    messages.append(
        UserMessage(role="user", content=f"What is the status of order {ORDER_IDS[i-1]}?")
    )

    msg: AssistantMessage = generate(
        model=MODEL, messages=messages, tools=tools, tool_choice="auto",
        temperature=0.0, max_tokens=2000,
    )

    tcs = msg.tool_calls or []
    content = (msg.content or "").strip()

    # After tau2's conversion, the ONLY place a signature could hide is the id.
    ids = [tc.id for tc in tcs]
    sig_in_id = any("__thought__" in (i_ or "") for i_ in ids)
    id_carries_sig = id_carries_sig or sig_in_id
    # Confirm the model object genuinely has no signature field
    has_psf_field = any(hasattr(tc, "provider_specific_fields") for tc in tcs)

    messages.append(msg)
    for tc in tcs:
        messages.append(
            ToolMessage(
                id=tc.id, role="tool",
                content=json.dumps({"order_id": tc.arguments.get("order_id", "?"),
                                    "status": "delivered"}),
                requestor="assistant",
            )
        )

    short_garbage = (not tcs) and len(content) < 12
    degraded = degraded or short_garbage

    turns.append(dict(turn=i, n_tool_calls=len(tcs), tool=(tcs[0].name if tcs else None),
                      sig_in_id=sig_in_id, has_psf_field=has_psf_field,
                      id_len=(len(ids[0]) if ids else 0), content_len=len(content),
                      content_preview=content[:60]))

    status = "OK " if tcs else "NO TOOL CALL"
    print(f"  turn {i}: tool_calls={len(tcs)} tool={(tcs[0].name if tcs else '-'):<24} "
          f"id_len={(len(ids[0]) if ids else 0):<4} sig_in_id={'Y' if sig_in_id else 'n'} {status}")
    if short_garbage:
        print(f"      !! possible silent degradation: {content!r}")

tool_turns = [t for t in turns if t["n_tool_calls"] > 0]
late = [t for t in turns if t["turn"] >= 4]
late_ok = [t for t in late if t["n_tool_calls"] > 0]

checks = {
    f"all {N_TURNS} turns produced a tool call (tau2 path)": len(tool_turns) == N_TURNS,
    "no silent degradation after turn 3": not degraded and len(late_ok) == len(late),
    "tool names are real retail tools": all(
        (t["tool"] in tool_names) for t in tool_turns
    ),
}

print("\n--- verdict ---")
for k, v in checks.items():
    print(f"  {'PASS' if v else 'FAIL'}  {k}")

print("\n--- signature transport ---")
print(f"  tau2 ToolCall exposes provider_specific_fields : "
      f"{any(t['has_psf_field'] for t in turns)}")
print(f"  signature packed into tool-call id             : {id_carries_sig}")

ok = all(checks.values())
print("\n" + "=" * 78)
if ok and id_carries_sig:
    print("  GATE B8b PASS — signatures ride in the tool-call id, which tau2 preserves.")
    print("  Phase C is safe on the tau2 path.")
elif ok:
    print("  GATE B8b PASS (behavioural) — tau2's path sustained tool calling for all")
    print(f"  {N_TURNS} turns with no degradation, even though no signature is visible in")
    print("  the id and tau2's ToolCall cannot carry provider_specific_fields.")
    print("  => Empirically safe for Phase C, but the runtime degradation detector stays ON,")
    print("     and this is a real upstream fragility worth reporting.")
else:
    print("  GATE B8b FAIL — tau2's own path degrades where the raw litellm path did not.")
    print("  ROOT CAUSE: tau2 ToolCall drops provider_specific_fields (litellm#25322).")
    print("  Do NOT attribute this to model quality. Report upstream; drop or patch the arm.")
print("=" * 78)

json.dump({"model": MODEL, "turns": turns, "checks": checks,
           "id_carries_sig": id_carries_sig, "pass": ok},
          open(_OUT / "step3b_tau2_path.json", "w"), indent=1)
print(f"\nwrote {_OUT / 'step3b_tau2_path.json'}")
