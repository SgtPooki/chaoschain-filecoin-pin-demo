# ChaosChain Filecoin Pin Demo Makefile
# Provides convenient commands for setting up and running the demo

.PHONY: help install setup demo clean test check-env venv

VENV_DIR := .venv
SYSTEM_PYTHON := $(shell command -v python3 2>/dev/null || command -v python 2>/dev/null)
SYSTEM_PIP := $(shell command -v pip3 2>/dev/null || command -v pip 2>/dev/null)
PYTHON = $(if $(wildcard $(VENV_DIR)/bin/python),$(VENV_DIR)/bin/python,$(SYSTEM_PYTHON))
PIP = $(if $(wildcard $(VENV_DIR)/bin/pip),$(VENV_DIR)/bin/pip,$(SYSTEM_PIP))

# Default target
help:
	@echo "ChaosChain Filecoin Pin Demo"
	@echo "============================"
	@echo ""
	@echo "Available commands:"
	@echo "  make install     - Install Python dependencies"
	@echo "  make setup       - Set up filecoin-pin CLI and ChaosChain wallets"
	@echo "  make demo        - Run the complete demo with automatic Filecoin pinning"
	@echo "  make agent       - Run just the ChaosChain agent"
	@echo "  make test-storage - Test the Filecoin Pin storage provider"
	@echo "  make check-env   - Check environment configuration"
	@echo "  make clean       - Clean up generated files"
	@echo "  make test        - Run basic connectivity tests"
	@echo ""
	@echo "Prerequisites:"
	@echo "  1. Copy env.example to .env and configure"
	@echo "  2. Install filecoin-pin CLI: npm install -g filecoin-pin"
	@echo "  3. Run 'make setup' to initialize wallets and verify configuration"

# Create a virtual environment (if needed)
venv:
	@if [ -z "$(SYSTEM_PYTHON)" ]; then \
		echo "ERROR: python3 not found. Please install Python 3 (>=3.9)."; \
		exit 1; \
	fi; \
	if [ ! -d $(VENV_DIR) ]; then \
		echo "Creating virtual environment at $(VENV_DIR)..."; \
		$(SYSTEM_PYTHON) -m venv $(VENV_DIR); \
		$(VENV_DIR)/bin/python -m pip install --upgrade pip >/dev/null; \
		echo "Virtual environment created."; \
	else \
		echo "Virtual environment already exists at $(VENV_DIR)."; \
	fi

# Install Python dependencies
install: venv
	@echo "Installing Python dependencies..."
	@$(PYTHON) -m pip install -r requirements.txt
	@echo "Dependencies installed inside $(VENV_DIR)."

# Set up filecoin-pin CLI and ChaosChain wallets
setup: check-env
	@echo "Setting up filecoin-pin CLI and ChaosChain wallets..."
	@set -a; . ./.env; set +a; \
	FILECOIN_PIN_CMD=$${FILECOIN_PIN_PATH:-filecoin-pin}; \
	$$FILECOIN_PIN_CMD --version
	@echo "filecoin-pin CLI is ready."
	@echo ""
	@echo "Setting up ChaosChain wallet..."
	@set -a; . ./.env; set +a; $(PYTHON) scripts/generate_wallet.py
	@echo ""
	@echo "Note: Make sure you have configured filecoin-pin authentication:"
	@echo "  - Set up your wallet and API keys"
	@echo "  - Configure the Filecoin network settings"
	@echo "  - Test with: $$FILECOIN_PIN_CMD add --help"

# Check environment configuration
check-env:
	@echo "Checking environment configuration..."
	@if [ ! -f .env ]; then \
		echo "ERROR: .env file not found. Copy env.example to .env and configure it."; \
		exit 1; \
	fi
	@echo ".env file found."
	@echo "Checking filecoin-pin CLI..."
	@set -a; . ./.env; set +a; \
	FILECOIN_PIN_CMD=$${FILECOIN_PIN_PATH:-filecoin-pin}; \
	if ! command -v $$FILECOIN_PIN_CMD >/dev/null 2>&1; then \
		echo "ERROR: filecoin-pin CLI not found: $$FILECOIN_PIN_CMD"; \
		echo "  Install with: npm install -g filecoin-pin"; \
		echo "  Or set FILECOIN_PIN_PATH in .env to the correct path"; \
		exit 1; \
	fi
	@echo "filecoin-pin CLI found: $$FILECOIN_PIN_CMD."
	@echo "Loading environment variables..."
	@set -a; . ./.env; set +a; \
	if [ -z "$$CHAOS_NETWORK" ]; then \
		echo "ERROR: CHAOS_NETWORK not set"; \
		exit 1; \
	fi; \
	if [ -z "$$BASE_SEPOLIA_PRIVATE_KEY" ] || [ "$$BASE_SEPOLIA_PRIVATE_KEY" = "your-base-sepolia-private-key" ]; then \
		echo "ERROR: BASE_SEPOLIA_PRIVATE_KEY not configured"; \
		echo "  Please set your Base-Sepolia private key in .env"; \
		exit 1; \
	fi; \
	if [ -z "$$BASE_SEPOLIA_RPC_URL" ]; then \
		echo "ERROR: BASE_SEPOLIA_RPC_URL not set"; \
		exit 1; \
	fi; \
	if [ -z "$$FILECOIN_CALIBRATION_PRIVATE_KEY" ] || [ "$$FILECOIN_CALIBRATION_PRIVATE_KEY" = "your-filecoin-calibration-private-key" ]; then \
		echo "ERROR: FILECOIN_CALIBRATION_PRIVATE_KEY not configured"; \
		echo "  Please set your Filecoin Calibration private key in .env"; \
		exit 1; \
	fi; \
	if [ -z "$$FILECOIN_CALIBRATION_RPC_URL" ]; then \
		echo "ERROR: FILECOIN_CALIBRATION_RPC_URL not set"; \
		exit 1; \
	fi; \
	echo "Environment variables configured."

# Run the complete demo (now with automatic Filecoin pinning)
demo: check-env
	@echo "============================================================"
	@echo "Running ChaosChain Filecoin Pin Demo"
	@echo "============================================================"
	@echo ""
	@echo "This demo will:"
	@echo "1. Run the ChaosChain agent"
	@echo "2. Automatically pin the proof to Filecoin via filecoin-pin CLI"
	@echo "3. Save the results to receipts/"
	@echo ""
	@echo "Starting demo..."
	@set -a; . ./.env; set +a; $(PYTHON) agent/agent.py
	@echo ""
	@echo "============================================================"
	@echo "Demo completed. The proof was automatically pinned to Filecoin."
	@echo "Check the receipts/ directory for detailed results."
	@echo "============================================================"

# Run just the ChaosChain agent
agent: check-env
	@echo "Running ChaosChain agent with automatic Filecoin pinning..."
	@set -a; . ./.env; set +a; $(PYTHON) agent/agent.py

# Test the Filecoin Pin storage provider
test-storage: check-env
	@echo "Testing Filecoin Pin storage provider..."
	@set -a; . ./.env; set +a; $(PYTHON) test_storage_provider.py


# Run basic connectivity tests
test: check-env
	@echo "Running connectivity tests..."
	@echo ""
	@echo "1. Testing filecoin-pin CLI..."
	@set -a; . ./.env; set +a; \
	FILECOIN_PIN_CMD=$${FILECOIN_PIN_PATH:-filecoin-pin}; \
	if command -v $$FILECOIN_PIN_CMD >/dev/null 2>&1; then \
		echo "filecoin-pin CLI is installed: $$FILECOIN_PIN_CMD"; \
		$$FILECOIN_PIN_CMD --version; \
	else \
		echo "WARNING: filecoin-pin CLI not found: $$FILECOIN_PIN_CMD"; \
		echo "  Install with: npm install -g filecoin-pin"; \
		echo "  Or set FILECOIN_PIN_PATH in .env to the correct path"; \
	fi
	@echo ""
	@echo "2. Testing Python dependencies..."
	@if $(PYTHON) -c "import chaoschain_sdk" > /dev/null 2>&1; then \
		echo "chaoschain-sdk is installed."; \
	else \
		echo "WARNING: chaoschain-sdk not installed."; \
		echo "  Install with: make install"; \
	fi
	@echo ""
	@echo "3. Testing environment configuration..."
	@set -a; . ./.env; set +a; \
	if [ -n "$$CHAOS_NETWORK" ] && [ -n "$$BASE_SEPOLIA_RPC_URL" ] && [ -n "$$FILECOIN_CALIBRATION_RPC_URL" ]; then \
		echo "Environment variables are set."; \
	else \
		echo "WARNING: Environment variables not properly configured."; \
	fi
	@echo ""
	@echo "Connectivity tests completed."

# Clean up generated files
clean:
	@echo "Cleaning up generated files..."
	@rm -rf receipts/*.json
	@echo "Generated receipt files removed."

# Development helpers
dev-setup: install setup
	@echo "Development environment ready!"

# Quick demo with minimal output (now just runs the agent)
demo-quick: check-env
	@echo "Running quick demo..."
	@set -a; . ./.env; set +a; $(PYTHON) agent/agent.py > /dev/null 2>&1
	@echo "Quick demo completed (proof automatically pinned to Filecoin)."

# Show latest results
results:
	@echo "Latest demo results:"
	@echo "==================="
	@LATEST_RECEIPT=$$(ls -t receipts/chaos_proof_*.json 2>/dev/null | head -1); \
	if [ -n "$$LATEST_RECEIPT" ]; then \
		echo "Latest proof receipt: $$LATEST_RECEIPT"; \
		cat $$LATEST_RECEIPT | $(PYTHON) -m json.tool; \
	else \
		echo "No proof receipts found. Run the demo first."; \
	fi
