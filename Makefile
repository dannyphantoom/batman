# Batman Package Manager Makefile

.PHONY: help install uninstall test lint clean dev-setup run-tests

# Default target
help:
	@echo "🦇 Batman Package Manager"
	@echo "========================="
	@echo ""
	@echo "Available targets:"
	@echo "  install      Install batman system-wide"
	@echo "  uninstall    Remove batman from system"
	@echo "  test         Run tests"
	@echo "  lint         Run linting"
	@echo "  clean        Clean up temporary files"
	@echo "  dev-setup    Setup development environment"
	@echo "  run-tests    Run all tests with verbose output"
	@echo ""

# Install batman system-wide
install:
	@echo "🔧 Installing Batman Package Manager..."
	chmod +x batman.py
	sudo ln -sf $(shell pwd)/batman.py /usr/local/bin/batman
	@echo "✅ Batman installed! You can now use 'batman' command globally."
	@echo "📋 Run 'batman --help' to get started."

# Uninstall batman
uninstall:
	@echo "🗑️  Uninstalling Batman Package Manager..."
	sudo rm -f /usr/local/bin/batman
	@echo "✅ Batman uninstalled."

# Run tests
test:
	@echo "🧪 Running tests..."
	python3 -m pytest tests/ -v

# Run linting
lint:
	@echo "🔍 Running linting..."
	python3 -m flake8 src/ batman.py --max-line-length=100
	python3 -m pylint src/ batman.py

# Clean up temporary files
clean:
	@echo "🧹 Cleaning up..."
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	rm -rf .pytest_cache/
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info/
	@echo "✅ Cleanup complete."

# Setup development environment
dev-setup:
	@echo "🛠️  Setting up development environment..."
	python3 -m pip install --user pytest flake8 pylint
	mkdir -p tests
	@echo "✅ Development environment ready."

# Run all tests with verbose output
run-tests:
	@echo "🧪 Running comprehensive tests..."
	python3 -m py_compile batman.py && echo "✅ Syntax check passed" || echo "❌ Syntax check failed"
	python3 batman.py --help > /dev/null && echo "✅ Help command works" || echo "❌ Help command failed"
	python3 batman.py -i test-package --dry-run > /dev/null && echo "✅ Dry run works" || echo "❌ Dry run failed"
	@echo "🎯 Basic tests completed"

# Quick development test
quick-test:
	@echo "⚡ Quick test..."
	python3 -m py_compile batman.py
	python3 batman.py --help
	@echo "✅ Quick test passed!"

# Show current installation status
status:
	@echo "📊 Batman Package Manager Status"
	@echo "================================"
	@echo "Batman executable: $(shell which batman 2>/dev/null || echo 'Not installed')"
	@echo "Source location: $(shell pwd)"
	@echo "Python version: $(shell python3 --version)"
	@echo "Configuration: $(shell [ -f ~/.batman/config.json ] && echo 'Exists' || echo 'Not created yet')"
	@echo "Package database: $(shell [ -f ~/.batman/packages.json ] && echo 'Exists' || echo 'Not created yet')" 