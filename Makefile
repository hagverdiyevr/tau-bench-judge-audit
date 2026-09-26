# Offline verification. No API keys required, no spend.
#
# Every step runs on ONE interpreter: the pinned tau2 venv (Python 3.12.9). Bare `python3` is not
# used, because on this machine it resolves to Anaconda 3.13, Homebrew 3.14 or the system 3.9
# depending on how the shell was started (FINDINGS R-L10). The venv's python is called directly
# rather than through `uv run`, because plain `uv run` rewrites upstream's stale uv.lock and so
# modified the submodule on every gate run (FINDINGS R-L11). `make verify` now ends by proving
# upstream is untouched instead of assuming it.

VENDOR := vendor/tau2-bench
PY     := $(CURDIR)/$(VENDOR)/.venv/bin/python
PINNED := fc0055dc4e0a316c3f83133267fbd6faaa770992

.PHONY: verify setup venv-check pristine test docs ledger artifacts dry-run dry-run-d help

help:
	@echo "make setup      - create the pinned venv (uv sync --frozen; leaves uv.lock untouched)"
	@echo "make verify     - every offline check, then prove upstream is untouched. Gate before spending."
	@echo "make test       - judge-adapter, runner-guard, Phase D guard and Phase A regression tests"
	@echo "make docs       - documentation alignment checker"
	@echo "make pristine   - fail unless upstream is at the pinned commit with no modified files"
	@echo "make ledger     - regenerate the spend ledger from run artifacts"
	@echo "make artifacts  - export sanitized run artifacts out of the submodule"
	@echo "make dry-run    - validate the Phase C manifest, dispatch nothing"
	@echo "make dry-run-d  - validate the Phase D manifest, dispatch nothing"

setup:
	@cd $(VENDOR) && uv sync --frozen

venv-check:
	@test -x "$(PY)" || { echo "  REFUSING — pinned venv missing at $(PY). Run: make setup"; exit 1; }
	@echo "  gate interpreter: $$($(PY) -c 'import sys; print(sys.version.split()[0], "@", sys.executable)')"

verify: venv-check docs test
	@$(PY) scripts/verify_preregistration.py
	@$(MAKE) --no-print-directory pristine
	@echo ""
	@echo "  VERIFY PASSED — offline gates clear, upstream untouched."

pristine:
	@sha=$$(git -C $(VENDOR) rev-parse HEAD); \
	 if [ "$$sha" != "$(PINNED)" ]; then echo "  FAIL  upstream moved: $$sha, pinned $(PINNED)"; exit 1; fi; \
	 dirty=$$(git -C $(VENDOR) status --porcelain); \
	 if [ -n "$$dirty" ]; then echo "  FAIL  upstream is modified — inspect with: git -C $(VENDOR) diff"; echo "$$dirty" | sed 's/^/        /'; exit 1; fi; \
	 echo "  PASS  upstream at pinned $(PINNED) with no modified files"

docs: venv-check
	@$(PY) scripts/check_docs.py

test: venv-check
	@$(PY) tests/test_judge_adapter.py
	@echo ""
	@$(PY) tests/test_runner_guards.py
	@echo ""
	@cd $(VENDOR) && $(PY) ../../tests/test_phase_d_guards.py
	@echo ""
	@cd $(VENDOR) && $(PY) ../../tests/test_phase_a_regression.py

ledger: venv-check
	@cd $(VENDOR) && $(PY) ../../scripts/build_spend_ledger.py

artifacts: venv-check
	@$(PY) scripts/export_artifacts.py

dry-run: venv-check
	@cd $(VENDOR) && $(PY) ../../scripts/phase_c/run_phase_c.py --dry-run

dry-run-d: venv-check
	@cd $(VENDOR) && $(PY) ../../scripts/phase_d/run_phase_d.py --dry-run
