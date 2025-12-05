#!/bin/bash

# LiveKit Intelligent Interruption Handler - Setup Script
# This script helps you set up and test the implementation

set -e

BOLD='\033[1m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${BOLD}╔════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BOLD}║  LiveKit Intelligent Interruption Handler - Setup         ║${NC}"
echo -e "${BOLD}╚════════════════════════════════════════════════════════════╝${NC}"
echo ""

# Check Python version
echo -e "${YELLOW}→${NC} Checking Python version..."
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}✗${NC} Python 3 is not installed. Please install Python 3.8 or higher."
    exit 1
fi

PYTHON_VERSION=$(python3 --version | cut -d' ' -f2 | cut -d'.' -f1,2)
echo -e "${GREEN}✓${NC} Python $PYTHON_VERSION detected"

# Check if we're in the right directory
echo -e "\n${YELLOW}→${NC} Checking directory structure..."
if [ ! -f "README.md" ]; then
    echo -e "${RED}✗${NC} README.md not found. Please run this script from the project root."
    exit 1
fi
echo -e "${GREEN}✓${NC} Directory structure looks good"

# Create virtual environment
echo -e "\n${YELLOW}→${NC} Setting up virtual environment..."
if [ ! -d "venv" ]; then
    python3 -m venv venv
    echo -e "${GREEN}✓${NC} Virtual environment created"
else
    echo -e "${GREEN}✓${NC} Virtual environment already exists"
fi

# Activate virtual environment
echo -e "\n${YELLOW}→${NC} Activating virtual environment..."
source venv/bin/activate
echo -e "${GREEN}✓${NC} Virtual environment activated"

# Install dependencies
echo -e "\n${YELLOW}→${NC} Installing dependencies..."
pip install --upgrade pip > /dev/null 2>&1
pip install -r requirements.txt > /dev/null 2>&1
echo -e "${GREEN}✓${NC} Dependencies installed"

# Set up .env file
echo -e "\n${YELLOW}→${NC} Checking environment configuration..."
if [ ! -f ".env" ]; then
    echo -e "${YELLOW}!${NC} .env file not found. Creating from template..."
    cp .env.example .env
    echo -e "${GREEN}✓${NC} .env file created"
    echo -e "${YELLOW}⚠${NC}  Please edit .env and add your API keys:"
    echo -e "   - LIVEKIT_URL"
    echo -e "   - LIVEKIT_API_KEY"
    echo -e "   - LIVEKIT_API_SECRET"
    echo -e "   - DEEPGRAM_API_KEY"
    echo -e "   - OPENAI_API_KEY"
    echo -e "   - ELEVEN_API_KEY"
    echo ""
    read -p "Press Enter after you've configured your .env file..."
else
    echo -e "${GREEN}✓${NC} .env file exists"
fi

# Verify .env has required keys
echo -e "\n${YELLOW}→${NC} Verifying environment configuration..."
source .env
MISSING_KEYS=()

if [ -z "$LIVEKIT_URL" ]; then MISSING_KEYS+=("LIVEKIT_URL"); fi
if [ -z "$LIVEKIT_API_KEY" ]; then MISSING_KEYS+=("LIVEKIT_API_KEY"); fi
if [ -z "$LIVEKIT_API_SECRET" ]; then MISSING_KEYS+=("LIVEKIT_API_SECRET"); fi
if [ -z "$DEEPGRAM_API_KEY" ]; then MISSING_KEYS+=("DEEPGRAM_API_KEY"); fi
if [ -z "$OPENAI_API_KEY" ]; then MISSING_KEYS+=("OPENAI_API_KEY"); fi
if [ -z "$ELEVEN_API_KEY" ]; then MISSING_KEYS+=("ELEVEN_API_KEY"); fi

if [ ${#MISSING_KEYS[@]} -gt 0 ]; then
    echo -e "${RED}✗${NC} Missing required environment variables:"
    for key in "${MISSING_KEYS[@]}"; do
        echo -e "   - $key"
    done
    echo -e "\n${YELLOW}Please add these to your .env file${NC}"
    exit 1
fi
echo -e "${GREEN}✓${NC} All required environment variables are set"

# Run tests
echo -e "\n${YELLOW}→${NC} Running test suite..."
python3 test_interruption.py
if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓${NC} All tests passed!"
else
    echo -e "${RED}✗${NC} Some tests failed. Please review the output above."
    exit 1
fi

# Success summary
echo -e "\n${BOLD}╔════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BOLD}║  ${GREEN}Setup Complete!${NC}${BOLD}                                         ║${NC}"
echo -e "${BOLD}╚════════════════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "${GREEN}✓${NC} Environment configured"
echo -e "${GREEN}✓${NC} Dependencies installed"
echo -e "${GREEN}✓${NC} Tests passing"
echo ""
echo -e "${BOLD}Next Steps:${NC}"
echo ""
echo -e "1. ${BOLD}Run in terminal mode:${NC}"
echo -e "   python3 agent_with_interruption.py console"
echo ""
echo -e "2. ${BOLD}Run in development mode:${NC}"
echo -e "   python3 agent_with_interruption.py dev"
echo ""
echo -e "3. ${BOLD}Test with LiveKit Playground:${NC}"
echo -e "   https://agents-playground.livekit.io/"
echo ""
echo -e "4. ${BOLD}Create demo recording:${NC}"
echo -e "   - Test all scenarios"
echo -e "   - Save video or logs to demo/ folder"
echo ""
echo -e "5. ${BOLD}Submit your PR:${NC}"
echo -e "   See SUBMISSION_GUIDE.md for details"
echo ""
echo -e "${BOLD}Test Scenarios to Verify:${NC}"
echo -e "  □ Agent ignores 'yeah', 'ok', 'hmm' while speaking"
echo -e "  □ Agent responds to 'yeah' when silent"
echo -e "  □ Agent stops on 'stop', 'wait', 'no'"
echo -e "  □ Mixed input handled correctly"
echo ""
echo -e "${YELLOW}Happy coding! 🚀${NC}"
