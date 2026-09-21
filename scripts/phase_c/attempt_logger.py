"""Record EVERY LiteLLM attempt — successes and failures alike — to a JSONL file.

Required by AMENDMENT A-003. tau2 persists only completed simulations, so a retried or
rate-limited attempt leaves no trace in results.json: cost undercounts and intention-to-treat
failures disappear. A-002 tried to fix that by forbidding retries, which instead converted
transient provider rate limits into permanent agent failures (18 x RateLimitError -> 6 of 40
simulations dead on phaseC_t1_oai).

A-003's answer is to make attempts observable rather than forbidden. This sits at the ONE shared
request boundary every agent, user-simulator and judge call passes through, so the record is
complete regardless of what tau2 chooses to keep.

One JSONL line per attempt. Never raises into the caller — a logging failure must not fail a run.
"""

from __future__ import annotations

import json
import os
import pathlib
import threading

try:
    from litellm.integrations.custom_logger import CustomLogger
except ImportError:                                    # importable outside the tau2 venv
    class CustomLogger:                                # minimal stand-in; hooks are ours anyway
        """Fallback base so this module (and its tests) import without litellm installed.

        Only `install()` needs the real litellm. The JSONL recording and `summarize()` — the
        parts a test needs to prove failures are captured — are pure stdlib.
        """

        def __init__(self, *a, **k):
            pass


class AttemptLogger(CustomLogger):
    def __init__(self, path: str | pathlib.Path, invocation: str = ""):
        super().__init__()
        self.path = pathlib.Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.invocation = invocation
        self._lock = threading.Lock()   # tau2 runs tasks concurrently
        self._n = 0

    # -- internals ---------------------------------------------------------------
    def _write(self, rec: dict) -> None:
        try:
            with self._lock:
                self._n += 1
                rec["seq"] = self._n
                rec["invocation"] = self.invocation
                with self.path.open("a") as fh:
                    fh.write(json.dumps(rec, default=str) + "\n")
        except Exception:
            pass   # logging must never break a run

    @staticmethod
    def _secs(start, end):
        try:
            return round((end - start).total_seconds(), 3)
        except Exception:
            return None

    @staticmethod
    def _usage(response_obj):
        u = getattr(response_obj, "usage", None)
        if u is None and isinstance(response_obj, dict):
            u = response_obj.get("usage")
        if u is None:
            return {}
        g = (lambda k: getattr(u, k, None) if not isinstance(u, dict) else u.get(k))
        d = g("completion_tokens_details")
        reasoning = None
        if d is not None:
            reasoning = getattr(d, "reasoning_tokens", None) if not isinstance(d, dict) else d.get("reasoning_tokens")
        return {"prompt_tokens": g("prompt_tokens"), "completion_tokens": g("completion_tokens"),
                "reasoning_tokens": reasoning}

    # -- hooks -------------------------------------------------------------------
    def log_success_event(self, kwargs, response_obj, start_time, end_time):
        hp = getattr(response_obj, "_hidden_params", None) or {}
        self._write({
            "outcome": "success",
            "model_requested": kwargs.get("model"),
            "model_returned": getattr(response_obj, "model", None),
            "call_name": (kwargs.get("litellm_params") or {}).get("metadata", {}).get("call_name")
                         or kwargs.get("call_name"),
            "latency_s": self._secs(start_time, end_time),
            "usd": hp.get("response_cost") if isinstance(hp, dict) else None,
            **self._usage(response_obj),
        })

    def log_failure_event(self, kwargs, response_obj, start_time, end_time):
        exc = kwargs.get("exception") or response_obj
        # THE point of this file: a failed attempt is billable-ish, invisible to tau2,
        # and must appear in the record with its error class.
        self._write({
            "outcome": "failure",
            "model_requested": kwargs.get("model"),
            "error_class": type(exc).__name__ if exc is not None else None,
            "error": str(exc)[:300] if exc is not None else None,
            "latency_s": self._secs(start_time, end_time),
            "usd": None,
        })


def install(path: str | pathlib.Path, invocation: str = "") -> AttemptLogger:
    """Attach the logger to LiteLLM's global callback list (idempotent per process)."""
    import litellm

    handler = AttemptLogger(path, invocation)
    existing = [c for c in (litellm.callbacks or []) if isinstance(c, AttemptLogger)]
    if not existing:
        litellm.callbacks = list(litellm.callbacks or []) + [handler]
    return handler


def summarize(path: str | pathlib.Path) -> dict:
    """Aggregate a JSONL attempt log: attempts, failures by class, and true spend."""
    p = pathlib.Path(path)
    if not p.exists():
        return {"attempts": 0}
    rows = [json.loads(l) for l in p.read_text().splitlines() if l.strip()]
    fails: dict[str, int] = {}
    usd = 0.0
    for r in rows:
        if r.get("outcome") == "failure":
            fails[r.get("error_class") or "Unknown"] = fails.get(r.get("error_class") or "Unknown", 0) + 1
        usd += r.get("usd") or 0.0
    return {"attempts": len(rows),
            "successes": sum(1 for r in rows if r.get("outcome") == "success"),
            "failures": sum(1 for r in rows if r.get("outcome") == "failure"),
            "failures_by_class": fails,
            "usd_from_attempts": round(usd, 6)}


if __name__ == "__main__":
    import sys
    print(json.dumps(summarize(sys.argv[1]), indent=1))
