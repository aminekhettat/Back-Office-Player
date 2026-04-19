# ============================================================
# Back-Office Player — local development Makefile
# ============================================================
# Usage:
#   make test       — run tests with coverage (must reach 100%)
#   make lint       — run ruff + black --check on source code
#   make format     — apply black formatting in-place
#   make docs       — build Sphinx HTML documentation
#   make ci         — run lint + test + docs (full local CI)
#   make clean      — remove build artefacts
#   make hooks      — install the git pre-push hook
# ============================================================

PYTHON   ?= python
PYTEST   ?= pytest
RUFF     ?= ruff
BLACK    ?= black
SPHINX   ?= sphinx-build

SOURCES  = core/ infra/ ui/ app.py __version__.py
TESTS    = tests/
DOCS_SRC = docs/
DOCS_OUT = docs/_build/html

# ── Lint ─────────────────────────────────────────────────────────────────────
.PHONY: lint
lint:
	$(RUFF) check .
	@echo "✓ ruff passed"
	$(BLACK) --check .
	@echo "✓ black passed"

# ── Format (apply) ───────────────────────────────────────────────────────────
.PHONY: format
format:
	$(BLACK) .
	@echo "✓ black formatting applied"

# ── Tests + Coverage ─────────────────────────────────────────────────────────
.PHONY: test
test:
	$(PYTEST) $(TESTS) \
		--cov=. \
		--cov-config=.coveragerc \
		--cov-report=term-missing \
		--cov-report=html:$(DOCS_OUT)/coverage \
		--cov-fail-under=100 \
		-v
	@echo "✓ All tests passed — coverage ≥ 100 %"

# ── Sphinx documentation ──────────────────────────────────────────────────────
.PHONY: docs
docs:
	$(SPHINX) -b html $(DOCS_SRC) $(DOCS_OUT) -W --keep-going
	@echo "✓ HTML documentation built in $(DOCS_OUT)"

# ── Full local CI (lint → test → docs) ───────────────────────────────────────
.PHONY: ci
ci: lint test docs
	@echo ""
	@echo "============================================"
	@echo "  ✓ Local CI passed — safe to push"
	@echo "============================================"

# ── Install git hooks ─────────────────────────────────────────────────────────
.PHONY: hooks
hooks:
	@cp scripts/pre-commit .git/hooks/pre-commit
	@chmod +x .git/hooks/pre-commit
	@echo "✓ pre-commit hook installed (auto-bump patch on every commit)"
	@cp scripts/pre-push .git/hooks/pre-push
	@chmod +x .git/hooks/pre-push
	@echo "✓ pre-push hook installed (ruff + black + tests before push)"

# ── Bump version manually ─────────────────────────────────────────────────────
.PHONY: bump-patch bump-minor bump-major
bump-patch:
	$(PYTHON) -m bumpversion patch
	@echo "✓ Patch bumped — don't forget to git add + git commit"

bump-minor:
	$(PYTHON) -m bumpversion minor
	@echo "✓ Minor bumped — don't forget to git add + git commit"

bump-major:
	$(PYTHON) -m bumpversion major
	@echo "✓ Major bumped — don't forget to git add + git commit"

# ── Clean ─────────────────────────────────────────────────────────────────────
.PHONY: clean
clean:
	@rm -rf docs/_build __pycache__ .pytest_cache .coverage coverage.xml
	@find . -name "*.pyc" -delete
	@find . -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true
	@echo "✓ Build artefacts removed"
