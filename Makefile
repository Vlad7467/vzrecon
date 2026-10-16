.PHONY: help install dev test selftest clean

help:
	@echo "install   editable install"
	@echo "dev       editable install with dev extras"
	@echo "test      run pytest"
	@echo "selftest  protocol self-test"
	@echo "clean     remove build artefacts"

install:
	pip install -e .

dev:
	pip install -e ".[dev]"

test:
	pytest -q

selftest:
	vzrecon --self-test

clean:
	rm -rf build dist *.egg-info .pytest_cache .coverage
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
