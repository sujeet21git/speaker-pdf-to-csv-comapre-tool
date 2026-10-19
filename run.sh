#!/usr/bin/env bash
# ==============================================================================
# 🎙️ Speaker Compare & Verification Tool - Startup Script
# ==============================================================================

set -e

# Resolve project directory
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECT_DIR"

PORT="${PORT:-5055}"

# Formatting & Colors
CYAN='\033[0;36m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BOLD='\033[1m'
NC='\033[0m' # No Color

echo -e "${CYAN}${BOLD}"
echo "=================================================================="
echo "    🎙️  SPEAKER COMPARE & VERIFICATION TOOL (Cardiff Expo 2026)  "
echo "=================================================================="
echo -e "${NC}"

# 1. Check Python installation
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}[ERROR] python3 is not installed on this system. Please install Python 3.10+.${NC}"
    exit 1
fi

# 2. Check and setup virtual environment
VENV_DIR="$PROJECT_DIR/.venv"
if [ ! -d "$VENV_DIR" ]; then
    echo -e "${YELLOW}[INFO] Virtual environment not found. Creating .venv...${NC}"
    python3 -m venv "$VENV_DIR"
    echo -e "${GREEN}[OK] .venv created successfully.${NC}"
    
    echo -e "${YELLOW}[INFO] Installing dependencies from requirements.txt...${NC}"
    "$VENV_DIR/bin/pip" install --upgrade pip
    "$VENV_DIR/bin/pip" install -r requirements.txt
    echo -e "${GREEN}[OK] Dependencies installed.${NC}"
else
    # Quick check if flask is installed in venv
    if ! "$VENV_DIR/bin/python" -c "import flask, pypdf, pandas" &> /dev/null; then
        echo -e "${YELLOW}[INFO] Installing missing dependencies into .venv...${NC}"
        "$VENV_DIR/bin/pip" install -r requirements.txt
    fi
fi

# 3. Check if existing process is running on the port
EXISTING_PID=$(lsof -ti :$PORT 2>/dev/null || true)
if [ -n "$EXISTING_PID" ]; then
    echo -e "${YELLOW}[NOTE] An existing process (PID: $EXISTING_PID) is already using port $PORT.${NC}"
    echo -e "${YELLOW}[NOTE] Stopping previous instance to allow fresh start...${NC}"
    kill -9 $EXISTING_PID 2>/dev/null || true
    sleep 1
fi

echo -e "${GREEN}${BOLD}✓ System checks passed!${NC}"
echo -e "${CYAN}→ Starting Web Server on:${NC} ${BOLD}http://127.0.0.1:${PORT}${NC}"
echo -e "${YELLOW}Press [CTRL + C] anytime to stop the server.${NC}\n"

# Run Flask Application
exec "$VENV_DIR/bin/python" app.py
