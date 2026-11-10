.PHONY: install run debug clean lint lint-strict

PYTHON      := python3
POETRY      := poetry
MAIN        := fly_in.py
MAP        	?= maps/example.txt

GREEN       := \033[1;32m
YELLOW      := \033[1;33m
MAGENTA     := \033[1;35m
RESET       := \033[0m

MYPY_FLAGS  := --warn-return-any \
               --warn-unused-ignores \
               --ignore-missing-imports \
               --disallow-untyped-defs \
               --check-untyped-defs
MYPY_EXCL   := --exclude '(^|/)\.venv/'

install:
	@if ! command -v poetry >/dev/null 2>&1; then \
		printf "$(YELLOW) -> Poetry not found. Installing...$(RESET)\n"; \
		$(PYTHON) -m pip install poetry; \
	fi
	@printf "$(MAGENTA) -> Installing project dependencies$(RESET)\n"
	@$(POETRY) install --no-root --quiet
	@printf "$(GREEN) -> Installation complete!$(RESET)\n"

run:
	@printf "$(MAGENTA) -> Running $(MAIN) with $(MAP) $(RESET)"
	@$(POETRY) run $(PYTHON) $(MAIN) $(MAP)

debug:
	@$(POETRY) run $(PYTHON) -m pdb $(MAIN) $(MAP)

clean:
	@find . -type d -name "__pycache__" -not -path "./.venv/*" -exec rm -rf {} +
	@find . -type f -name "*.pyc" -not -path "./.venv/*" -delete
	@rm -rf .mypy_cache .pytest_cache

lint:
	@$(POETRY) run flake8 . --exclude=.venv
	@$(POETRY) run mypy . $(MYPY_FLAGS) $(MYPY_EXCL)

lint-strict:
	@$(POETRY) run flake8 . --exclude=.venv
	@$(POETRY) run mypy . --strict $(MYPY_EXCL)