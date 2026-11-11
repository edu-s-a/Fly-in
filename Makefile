.PHONY: install run debug clean lint lint-strict bench

PYTHON      := python3
POETRY      := poetry
MAIN        := fly_in.py
MAP         ?= maps/example.txt
ARGS        ?=

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

BENCH_DIRS  := maps maps/own maps/easy maps/medium maps/hard maps/challenger

install:
	@if ! command -v poetry >/dev/null 2>&1; then \
		printf "$(YELLOW) -> Poetry not found. Installing...$(RESET)\n"; \
		$(PYTHON) -m pip install poetry; \
	fi
	@printf "$(MAGENTA) -> Installing project dependencies with Poetry$(RESET)\n"
	@$(POETRY) install --no-root --quiet
	@printf "$(GREEN) -> Installation complete!$(RESET)\n"

run:
	@$(POETRY) run $(PYTHON) $(MAIN) $(ARGS) $(MAP)

debug:
	@$(POETRY) run $(PYTHON) -m pdb $(MAIN) $(ARGS) $(MAP)

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

bench:
	@printf "%-44s %-9s %-7s %-6s %s\n" MAP TURNS TARGET STATUS TIME
	@for dir in $(BENCH_DIRS); do \
		for f in $$dir/*.txt; do \
			[ -e "$$f" ] || continue; \
			target="-"; \
			case "$$f" in \
				*01_linear_path*) target=6;; \
				*02_simple_fork*) target=8;; \
				*03_basic_capacity*) target=6;; \
				*01_dead_end_trap*) target=12;; \
				*02_circular_loop*) target=15;; \
				*03_priority_puzzle*) target=12;; \
				*01_maze_nightmare*) target=30;; \
				*02_capacity_hell*) target=35;; \
				*03_ultimate_challenge*) target=45;; \
				*01_the_impossible_dream*) target=44;; \
			esac; \
			start=$$(date +%s.%N); \
			out=$$($(POETRY) run $(PYTHON) $(MAIN) $$f 2>&1 >/dev/null | head -n 1); \
			end=$$(date +%s.%N); \
			turns=$${out#turns: }; \
			status="-"; \
			if [ "$$target" != "-" ]; then \
				if [ "$$turns" -le "$$target" ] 2>/dev/null; then \
					status=ok; else status=OVER; fi; \
			fi; \
			secs=$$(awk -v a=$$start -v b=$$end 'BEGIN{printf "%.2f", b-a}'); \
			printf "%-44s %-9s %-7s %-6s %ss\n" "$$f" "$$turns" "$$target" "$$status" "$$secs"; \
		done; \
	done