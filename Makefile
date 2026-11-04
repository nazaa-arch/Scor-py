.PHONY: help install install-dev test test-cov lint format typecheck benchmark run-dashboard clean build

help:
	@echo "Perintah yang tersedia:"
	@echo "  make install        - Install pustaka dalam mode editable"
	@echo "  make install-dev    - Install dependensi pengujian & pengembangan"
	@echo "  make test           - Jalankan test suite pytest"
	@echo "  make test-cov       - Jalankan pytest dengan coverage report"
	@echo "  make lint           - Pengecekan linter dengan Ruff"
	@echo "  make format         - Format kode dengan Ruff"
	@echo "  make typecheck      - Pengecekan tipe statis dengan Mypy"
	@echo "  make benchmark      - Jalankan benchmark performa"
	@echo "  make run-dashboard  - Jalankan Streamlit dashboard interaktif"
	@echo "  make build          - Build distribution wheel dan sdist"
	@echo "  make clean          - Bersihkan build artifacts dan cache"

install:
	pip install -e .

install-dev:
	pip install -e ".[dev,dashboard]"

test:
	pytest -q

test-cov:
	pytest -q --cov=scorpy --cov-report=term-missing

lint:
	ruff check .

format:
	ruff format .

typecheck:
	mypy scorpy

benchmark:
	python benchmarks/benchmark_engine.py

run-dashboard:
	streamlit run dashboard/app.py

build:
	python -m build

clean:
	rm -rf build dist *.egg-info .pytest_cache .mypy_cache .ruff_cache htmlcov .coverage
