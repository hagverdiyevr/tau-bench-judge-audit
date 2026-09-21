"""Launcher: install the A-003 attempt logger, then delegate to tau2's CLI in-process.

D-007 anticipated exactly this: the accounting callback must sit in the SAME interpreter that
issues the requests, so a plain `subprocess(["tau2", ...])` cannot see them. This wrapper is
subprocessed by run_phase_c.py (keeping crash isolation) but calls tau2.cli.main() in-process,
so litellm.callbacks is live for every agent, simulator and judge request.

Usage (argv after -- is passed verbatim to tau2):
  python tau2_with_logging.py --attempt-log PATH --invocation TAG -- tau2 run --domain retail ...
"""
import pathlib
import sys

REPO = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "scripts" / "phase_c"))

argv = sys.argv[1:]
log_path, invocation = None, ""
while argv and argv[0] != "--":
    if argv[0] == "--attempt-log":
        log_path = argv[1]; argv = argv[2:]
    elif argv[0] == "--invocation":
        invocation = argv[1]; argv = argv[2:]
    else:
        sys.exit(f"unexpected launcher arg: {argv[0]}")
if not argv or argv[0] != "--":
    sys.exit("missing '--' separator before the tau2 command")
tau2_argv = argv[1:]
if not log_path:
    sys.exit("--attempt-log is required (A-003: every attempt must be recorded)")

import attempt_logger  # noqa: E402

attempt_logger.install(log_path, invocation)
print(f"[attempt-logger] recording every LiteLLM attempt -> {log_path}", flush=True)

from tau2.cli import main  # noqa: E402  (import AFTER the callback is installed)

sys.argv = tau2_argv          # tau2.cli.main() takes no args; it reads sys.argv
try:
    rc = main()
except SystemExit as e:
    rc = e.code
s = attempt_logger.summarize(log_path)
print(f"[attempt-logger] attempts={s.get('attempts')} successes={s.get('successes')} "
      f"failures={s.get('failures')} by_class={s.get('failures_by_class')} "
      f"usd_from_attempts={s.get('usd_from_attempts')}", flush=True)
sys.exit(rc if isinstance(rc, int) else 0)
