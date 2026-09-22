# Offline verification. No API keys required, no spend.
.PHONY: verify test docs ledger artifacts dry-run dry-run-d help

help:
	@echo "make verify     - run every offline check (docs, freeze, tests). Gate before spending."
	@echo "make test       - judge-adapter + runner-guard + Phase D guard tests"
	@echo "make docs       - documentation alignment checker"
	@echo "make ledger     - regenerate the spend ledger from run artifacts"
	@echo "make artifacts  - export sanitized run artifacts out of the submodule"
	@echo "make dry-run    - validate the Phase C manifest, dispatch nothing"
	@echo "make dry-run-d  - validate the Phase D manifest, dispatch nothing"

verify: docs test
	@python3 scripts/verify_preregistration.py
	@echo ""
	@echo "  VERIFY PASSED — offline gates clear."

docs:
	@python3 scripts/check_docs.py

test:
	@python3 tests/test_judge_adapter.py
	@echo ""
	@python3 tests/test_runner_guards.py
	@echo ""
	@cd vendor/tau2-bench && uv run python ../../tests/test_phase_d_guards.py
	@echo ""
	@cd vendor/tau2-bench && uv run python ../../tests/test_phase_a_regression.py

ledger:
	@cd vendor/tau2-bench && uv run python ../../scripts/build_spend_ledger.py

artifacts:
	@python3 scripts/export_artifacts.py

dry-run:
	@cd vendor/tau2-bench && uv run python ../../scripts/phase_c/run_phase_c.py --dry-run

dry-run-d:
	@cd vendor/tau2-bench && uv run python ../../scripts/phase_d/run_phase_d.py --dry-run
