"""Fail-closed adapter for the tau3 NL-assertion judge.

Two upstream defects make the raw path unusable for a multi-judge study:

  J1  evaluator_nl_assertions.py:127 calls raw json.loads on the judge's content.
      gemini-3.8-flash returns valid JSON inside a ```json fence, so it raises
      JSONDecodeError. Verified live: gpt-4.1, gpt-4.1-mini and gemini-3.1-flash-lite
      return bare JSON; gemini-3.8-flash does not. Upstream already ships a fence
      stripper (utils/llm_utils.py:509 extract_json_from_llm_response) but does not
      use it in this path.

  J2  the parser never checks the returned results against the assertions it asked
      about. `{"results": []}` yields reward 1.0, because calculate_reward applies
      all() to an empty list. Duplicates, extras and mismatched text are equally
      silent. An absent judgement is scored as a pass.

FAIL-CLOSED CONTRACT. This adapter never converts an anomalous judge response into a
pass. Every anomaly either raises, or (via grade_safe) is recorded as an explicit
failure with reward withheld. Silence is the bug being fixed; it is never the fallback.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field

FENCE = re.compile(r"```(?:json)?\s*([\s\S]*?)```")


class JudgeError(RuntimeError):
    """Base: the judge response cannot be trusted."""


class JudgeParseError(JudgeError):
    """Content is not recoverable JSON."""


class JudgeValidationError(JudgeError):
    """JSON parsed, but does not answer exactly the question asked."""


@dataclass
class JudgeResult:
    assertion: str
    met: bool
    justification: str = ""


@dataclass
class JudgeOutcome:
    ok: bool
    results: list[JudgeResult] = field(default_factory=list)
    error: str | None = None
    error_kind: str | None = None
    raw: str | None = None

    @property
    def all_met(self) -> bool:
        """True only if the response was valid AND every assertion was met.

        Deliberately False for an invalid response — never 'vacuously true',
        which is exactly upstream's J2 defect.
        """
        return self.ok and bool(self.results) and all(r.met for r in self.results)


def extract_json(content: str) -> str:
    """Recover a JSON object from judge content, tolerating markdown fences."""
    if content is None:
        raise JudgeParseError("judge returned no content")
    m = FENCE.search(content)
    if m:
        return m.group(1).strip()
    start, end = content.find("{"), content.rfind("}")
    if start != -1 and end > start:
        return content[start : end + 1]
    return content.strip()


def parse_and_validate(content: str, assertions: list[str]) -> list[JudgeResult]:
    """Parse judge content and prove it answers exactly `assertions`, once each."""
    if not assertions:
        raise JudgeValidationError("no assertions supplied — nothing to grade")

    text = extract_json(content)
    try:
        data = json.loads(text)
    except json.JSONDecodeError as e:
        raise JudgeParseError(f"not JSON after fence extraction: {e}") from e

    if not isinstance(data, dict) or "results" not in data:
        raise JudgeValidationError("response has no 'results' key")
    rows = data["results"]
    if not isinstance(rows, list):
        raise JudgeValidationError("'results' is not a list")

    # J2: absence must never read as success.
    if len(rows) == 0:
        raise JudgeValidationError(
            f"empty results for {len(assertions)} assertion(s) — refusing to score as met"
        )

    seen: dict[str, JudgeResult] = {}
    for i, row in enumerate(rows):
        if not isinstance(row, dict):
            raise JudgeValidationError(f"results[{i}] is not an object")
        if "expectedOutcome" not in row or "metExpectation" not in row:
            raise JudgeValidationError(f"results[{i}] missing expectedOutcome/metExpectation")
        key = str(row["expectedOutcome"]).strip()
        if key not in assertions:
            raise JudgeValidationError(f"results[{i}] grades an assertion we did not ask: {key!r}")
        if key in seen:
            raise JudgeValidationError(f"duplicate verdict for assertion {key!r}")
        met = row["metExpectation"]
        if not isinstance(met, bool):
            raise JudgeValidationError(f"results[{i}] metExpectation is {type(met).__name__}, not bool")
        seen[key] = JudgeResult(assertion=key, met=met,
                                justification=str(row.get("reasoning", "")))

    missing = [a for a in assertions if a not in seen]
    if missing:
        raise JudgeValidationError(f"{len(missing)} assertion(s) ungraded: {missing[:2]}")

    return [seen[a] for a in assertions]   # stable order = the order we asked


def grade(content: str, assertions: list[str]) -> list[JudgeResult]:
    """Strict: raises on any anomaly. Use when a caller wants to abort loudly."""
    return parse_and_validate(content, assertions)


def grade_safe(content: str, assertions: list[str]) -> JudgeOutcome:
    """Fail-closed: records the anomaly instead of raising, so a batch re-grade
    over 1,280 evaluations does not abort on one bad response. Reward is withheld,
    never granted, on failure."""
    try:
        return JudgeOutcome(ok=True, results=parse_and_validate(content, assertions), raw=content)
    except JudgeError as e:
        return JudgeOutcome(ok=False, error=str(e), error_kind=type(e).__name__, raw=content)
