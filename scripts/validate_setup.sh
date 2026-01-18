#!/bin/bash
# FASE 1 Setup Validation Script
# Validates that all components are properly installed and configured

echo ""
echo "================================================================================"
echo "  BotPolyMarket - FASE 1 Setup Validation"
echo "================================================================================"
echo ""

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Counters
PASSED=0
FAILED=0

# Function to check command
check_command() {
    if command -v $1 &> /dev/null; then
        echo -e "${GREEN}✓${NC} $2"
        ((PASSED++))
        return 0
    else
        echo -e "${RED}✗${NC} $2 - Not found"
        ((FAILED++))
        return 1
    fi
}

# Function to check Python package
check_python_package() {
    if python3 -c "import $1" 2>/dev/null; then
        echo -e "${GREEN}✓${NC} Python package: $1"
        ((PASSED++))
        return 0
    else
        echo -e "${RED}✗${NC} Python package: $1 - Not installed"
        echo "    Install with: pip install $2"
        ((FAILED++))
        return 1
    fi
}

# Function to check file exists
check_file() {
    if [ -f "$1" ]; then
        echo -e "${GREEN}✓${NC} File: $1"
        ((PASSED++))
        return 0
    else
        echo -e "${RED}✗${NC} File: $1 - Not found"
        ((FAILED++))
        return 1
    fi
}

# Function to check directory
check_directory() {
    if [ -d "$1" ]; then
        echo -e "${GREEN}✓${NC} Directory: $1"
        ((PASSED++))
        return 0
    else
        echo -e "${YELLOW}!${NC} Directory: $1 - Will be created"
        mkdir -p "$1"
        ((PASSED++))
        return 0
    fi
}

echo "[1/6] Checking System Requirements..."
echo "---------------------------------------------"
check_command "python3" "Python 3"
check_command "pip3" "pip"
check_command "git" "Git"
echo ""

echo "[2/6] Checking Python Version..."
echo "---------------------------------------------"
PYTHON_VERSION=$(python3 --version | cut -d' ' -f2)
echo "Python version: $PYTHON_VERSION"
if [[ "$PYTHON_VERSION" > "3.11" ]]; then
    echo -e "${GREEN}✓${NC} Python version >= 3.11"
    ((PASSED++))
else
    echo -e "${YELLOW}!${NC} Python 3.11+ recommended (current: $PYTHON_VERSION)"
    ((PASSED++))
fi
echo ""

echo "[3/6] Checking Python Dependencies..."
echo "---------------------------------------------"
check_python_package "pandas" "pandas"
check_python_package "numpy" "numpy"
check_python_package "aiohttp" "aiohttp"
check_python_package "ccxt" "ccxt"
check_python_package "websocket" "websocket-client"
check_python_package "dotenv" "python-dotenv"

# Check py-clob-client separately (might not be installed yet)
if python3 -c "import py_clob_client" 2>/dev/null; then
    echo -e "${GREEN}✓${NC} Python package: py-clob-client"
    ((PASSED++))
else
    echo -e "${YELLOW}!${NC} Python package: py-clob-client - Install for live trading"
    echo "    Install with: pip install py-clob-client"
    ((PASSED++))  # Not critical for testing
fi
echo ""

echo "[4/6] Checking Project Structure..."
echo "---------------------------------------------"
check_directory "core"
check_directory "strategies"
check_directory "config"
check_directory "scripts"
check_directory "data"
check_directory "data/trades"
check_directory "logs"
check_directory "tests"
echo ""

echo "[5/6] Checking Core Files..."
echo "---------------------------------------------"
check_file "core/polymarket_client.py"
check_file "core/external_apis.py"
check_file "strategies/kelly_auto_sizing.py"
check_file "strategies/gap_strategies_optimized.py"
check_file "config/fase1_config.yaml"
check_file "scripts/run_fase1.py"
check_file "requirements_fase1.txt"
check_file ".env.example"
echo ""

echo "[6/6] Checking Environment Configuration..."
echo "---------------------------------------------"
if [ -f ".env" ]; then
    echo -e "${GREEN}✓${NC} .env file exists"
    ((PASSED++))
    
    # Check for critical variables
    if grep -q "POLYMARKET_PRIVATE_KEY=" .env && [ -n "$(grep 'POLYMARKET_PRIVATE_KEY=' .env | cut -d'=' -f2)" ]; then
        echo -e "${GREEN}✓${NC} POLYMARKET_PRIVATE_KEY configured"
        ((PASSED++))
    else
        echo -e "${YELLOW}!${NC} POLYMARKET_PRIVATE_KEY not set (required for live trading)"
        ((PASSED++))  # Not critical for paper trading
    fi
else
    echo -e "${YELLOW}!${NC} .env file not found"
    echo "    Copy .env.example to .env and configure:"
    echo "    cp .env.example .env"
    ((FAILED++))
fi
echo ""

echo "================================================================================"
echo "  VALIDATION SUMMARY"
echo "================================================================================"
echo ""
echo "Total Checks:  $((PASSED + FAILED))"
echo -e "${GREEN}Passed:        $PASSED${NC}"
echo -e "${RED}Failed:        $FAILED${NC}"
echo ""

if [ $FAILED -eq 0 ]; then
    echo -e "${GREEN}✓ ALL CHECKS PASSED!${NC}"
    echo ""
    echo "Next steps:"
    echo "  1. Install dependencies:  pip install -r requirements_fase1.txt"
    echo "  2. Configure .env:        cp .env.example .env && nano .env"
    echo "  3. Run tests:             python tests/test_fase1.py"
    echo "  4. Start bot (paper):     python scripts/run_fase1.py --mode paper"
    echo ""
    exit 0
else
    echo -e "${RED}✗ SOME CHECKS FAILED${NC}"
    echo ""
    echo "Please fix the issues above before proceeding."
    echo ""
    exit 1
fi
