# dealflow developer Makefile (Unix / macOS / Linux).
# Windows users: run  .\install.ps1  instead of `make install`.
#
# All targets operate inside a local virtualenv at ./.venv so nothing touches
# your system Python.

PY      ?= python3
VENV    := .venv
VBIN    := $(VENV)/bin
VPY     := $(VBIN)/python
DEALFLOW := $(VBIN)/dealflow

.PHONY: install test demo lint clean help

help:
	@echo "targets:"
	@echo "  install  create .venv and install dealflow editable + dev extra"
	@echo "  test     run the pytest suite in the venv"
	@echo "  demo     run all demo scenarios (offline, bundled samples)"
	@echo "  lint     ruff if available, else python compileall"
	@echo "  clean    remove .venv, build artifacts, caches"

install:
	@test -x "$(VPY)" || $(PY) -m venv $(VENV)
	$(VPY) -m pip install --upgrade pip
	$(VPY) -m pip install -e ".[dev]" || $(VPY) -m pip install -e .
	@$(DEALFLOW) --help >/dev/null 2>&1 && echo "OK: dealflow console script works" \
		|| $(VPY) -m dealflow --help >/dev/null && echo "OK: python -m dealflow works"
	@echo "Installed. Activate with: source $(VBIN)/activate"

test: install
	$(VPY) -m pytest -q

demo: install
	$(VPY) demos/run_all.py

lint:
	@if [ -x "$(VBIN)/ruff" ]; then \
		$(VBIN)/ruff check .; \
	elif command -v ruff >/dev/null 2>&1; then \
		ruff check .; \
	else \
		echo "ruff not found; running python compileall as a fallback"; \
		$(VPY) -m compileall -q dealflow demos livesearch.py integrations || \
			$(PY) -m compileall -q dealflow demos livesearch.py integrations; \
	fi

clean:
	rm -rf $(VENV) build dist *.egg-info .pytest_cache
	find . -type d -name __pycache__ -prune -exec rm -rf {} + 2>/dev/null || true
	@echo "cleaned."
