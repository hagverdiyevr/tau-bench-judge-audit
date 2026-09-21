"""Regression tests for the fail-closed judge adapter.

Covers every failure mode observed in the upstream NL-assertion path: fenced JSON (J1),
and empty / missing / duplicate / extra / mismatched / malformed results (J2).

The central assertion throughout: an anomalous judge response must NEVER produce a pass.
Upstream's defect is that absence reads as success; these tests exist to keep that fixed.

Dependency-free so it runs anywhere:
  python tests/test_judge_adapter.py      -> exit 0 pass / 1 fail
Also collectable by pytest if available.
"""

import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "scripts" / "grading"))

from judge_adapter import (  # noqa: E402
    JudgeParseError,
    JudgeValidationError,
    grade,
    grade_safe,
)

A = ["Agent should confirm the order was cancelled.", "Agent should mention order #W0000042."]


def body(rows):
    return json.dumps({"results": rows})


def row(a, met=True, why="ok"):
    return {"expectedOutcome": a, "metExpectation": met, "reasoning": why}


FAILURES = []


def expect_ok(name, content, assertions, met):
    try:
        out = grade(content, assertions)
        got = [r.met for r in out]
        assert got == met, f"expected met={met}, got {got}"
        safe = grade_safe(content, assertions)
        assert safe.ok and safe.all_met == all(met), "grade_safe disagrees with grade"
        print(f"  PASS  {name}")
    except Exception as e:
        FAILURES.append(name)
        print(f"  FAIL  {name}: {e}")


def expect_reject(name, content, assertions, kind):
    try:
        grade(content, assertions)
        FAILURES.append(name)
        print(f"  FAIL  {name}: accepted a response it must reject")
        return
    except kind:
        pass
    except Exception as e:
        FAILURES.append(name)
        print(f"  FAIL  {name}: wrong exception {type(e).__name__}: {e}")
        return
    # fail-closed: grade_safe must withhold reward, never grant it
    safe = grade_safe(content, assertions)
    if safe.ok or safe.all_met:
        FAILURES.append(name)
        print(f"  FAIL  {name}: grade_safe granted reward on an invalid response")
        return
    print(f"  PASS  {name}  (rejected as {safe.error_kind}, reward withheld)")


print("--- happy paths ---")
expect_ok("bare JSON, all met", body([row(A[0]), row(A[1])]), A, [True, True])
expect_ok("bare JSON, mixed", body([row(A[0], True), row(A[1], False)]), A, [True, False])
expect_ok("order differs from ask", body([row(A[1]), row(A[0])]), A, [True, True])

print("\n--- J1: fenced JSON (the gemini-3.8-flash failure) ---")
expect_ok("```json fence", "```json\n" + body([row(A[0]), row(A[1])]) + "\n```", A, [True, True])
expect_ok("bare ``` fence", "```\n" + body([row(A[0]), row(A[1])]) + "\n```", A, [True, True])
expect_ok("fence + prose around it",
          "Here is my assessment:\n```json\n" + body([row(A[0]), row(A[1])]) + "\n```\nDone.",
          A, [True, True])
expect_ok("no fence, prose prefix",
          "Assessment: " + body([row(A[0]), row(A[1])]), A, [True, True])

print("\n--- J2: absence must never read as success ---")
expect_reject("empty results", body([]), A, JudgeValidationError)
expect_reject("one result for two assertions", body([row(A[0])]), A, JudgeValidationError)
expect_reject("no results key", json.dumps({"verdicts": []}), A, JudgeValidationError)
expect_reject("results not a list", json.dumps({"results": {}}), A, JudgeValidationError)

print("\n--- J2: duplicates, extras, mismatches ---")
expect_reject("duplicate verdict", body([row(A[0]), row(A[0])]), A, JudgeValidationError)
expect_reject("extra invented assertion",
              body([row(A[0]), row(A[1]), row("Agent should offer a refund.")]), A,
              JudgeValidationError)
expect_reject("mismatched assertion text",
              body([row(A[0]), row("Agent should mention order #W9999999.")]), A,
              JudgeValidationError)

print("\n--- malformed ---")
expect_reject("not JSON at all", "The agent did well.", A, JudgeParseError)
expect_reject("truncated JSON", '{"results": [{"expectedOutcome"', A, JudgeParseError)
expect_reject("None content", None, A, JudgeParseError)
expect_reject("row not an object", json.dumps({"results": ["yes"]}), A, JudgeValidationError)
expect_reject("missing metExpectation",
              json.dumps({"results": [{"expectedOutcome": A[0]}, row(A[1])]}), A,
              JudgeValidationError)
expect_reject("metExpectation not bool",
              body([{"expectedOutcome": A[0], "metExpectation": "true"}, row(A[1])]), A,
              JudgeValidationError)
expect_reject("no assertions supplied", body([]), [], JudgeValidationError)

print("\n--- the upstream contrast, stated explicitly ---")
o = grade_safe(body([]), A)
print(f"  upstream all([])            -> True   (awards FULL reward for zero verdicts)")
print(f"  adapter JudgeOutcome.all_met -> {o.all_met}  (reward withheld: {o.error_kind})")
if o.all_met:
    FAILURES.append("upstream-contrast")

print()
if FAILURES:
    print(f"  {len(FAILURES)} TEST FAILURE(S): {FAILURES}")
    sys.exit(1)
print("  ALL JUDGE-ADAPTER TESTS PASS — anomalies reject, reward is never granted on absence.")
sys.exit(0)
