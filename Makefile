.PHONY: all install test lint typecheck format clean

all: install lint typecheck test

install:
	pip install -e ".[dev]"

test:
	pytest tests/ -v

lint:
	ruff check src/ tests/

typecheck:
	mypy src/

format:
	ruff format src/ tests/

clean:
	rm -rf build/ dist/ *.egg-info .pytest_cache .ruff_cache __pycache__/
	find . -name "*.pyc" -delete
