# Makefile for AI-Powered AML Suspicious Activity Detection Agent
# Reference: Implementation Plan §8

.PHONY: install dev test run clean

# Install dependencies
install:
	pip install -r requirements.txt

# Run in development/stub mode (no LLM calls)
dev:
	STUB_MODE=true python -m src.main

# Run tests
test:
	pytest tests/ -v

# Run the walking skeleton checkpoint (Phase 0 validation)
checkpoint:
	STUB_MODE=true python -m src.main

# Clean generated files
clean:
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
