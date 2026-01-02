#!/bin/bash
# =============================================================================
# Cheemski Bot - Linux/macOS Installation Script
# =============================================================================
# This script sets up the bot from scratch on Linux or macOS
# Run with: bash setup_unix.sh
# =============================================================================

set -e

echo "🐕 Cheemski Bot - Installation Script for Linux/macOS"
echo "========================================================"
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Detect OS
if [[ "$OSTYPE" == "linux-gnu"* ]]; then
    OS="linux"
    echo -e "${GREEN}✓ Detected: Linux${NC}"
elif [[ "$OSTYPE" == "darwin"* ]]; then
    OS="macos"
    echo -e "${GREEN}✓ Detected: macOS${NC}"
else
    echo -e "${RED}✗ Unsupported OS: $OSTYPE${NC}"
    exit 1
fi

# Check if running as root (not recommended)
if [[ $EUID -eq 0 ]]; then
    echo -e "${YELLOW}⚠ Running as root is not recommended. Consider using a regular user.${NC}"
fi

echo ""
echo -e "${BLUE}Step 1: Installing Python 3.11+${NC}"
echo "--------------------------------"

# Check Python version
if command -v python3 &> /dev/null; then
    PYTHON_VERSION=$(python3 -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')
    PYTHON_MAJOR=$(echo $PYTHON_VERSION | cut -d. -f1)
    PYTHON_MINOR=$(echo $PYTHON_VERSION | cut -d. -f2)
    
    if [[ $PYTHON_MAJOR -ge 3 ]] && [[ $PYTHON_MINOR -ge 11 ]]; then
        echo -e "${GREEN}✓ Python $PYTHON_VERSION is installed${NC}"
    else
        echo -e "${YELLOW}⚠ Python $PYTHON_VERSION found, but 3.11+ is recommended${NC}"
        
        if [[ "$OS" == "linux" ]]; then
            echo "Installing Python 3.11..."
            if command -v apt-get &> /dev/null; then
                sudo apt-get update
                sudo apt-get install -y python3.11 python3.11-venv python3-pip
            elif command -v dnf &> /dev/null; then
                sudo dnf install -y python3.11 python3-pip
            elif command -v pacman &> /dev/null; then
                sudo pacman -S python python-pip
            fi
        elif [[ "$OS" == "macos" ]]; then
            if command -v brew &> /dev/null; then
                brew install python@3.11
            else
                echo -e "${RED}✗ Homebrew not found. Install from https://brew.sh/${NC}"
                exit 1
            fi
        fi
    fi
else
    echo "Python 3 not found. Installing..."
    if [[ "$OS" == "linux" ]]; then
        if command -v apt-get &> /dev/null; then
            sudo apt-get update
            sudo apt-get install -y python3.11 python3.11-venv python3-pip
        elif command -v dnf &> /dev/null; then
            sudo dnf install -y python3.11 python3-pip
        elif command -v pacman &> /dev/null; then
            sudo pacman -S python python-pip
        fi
    elif [[ "$OS" == "macos" ]]; then
        if command -v brew &> /dev/null; then
            brew install python@3.11
        else
            echo -e "${RED}✗ Install Homebrew first: /bin/bash -c \"\$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)\"${NC}"
            exit 1
        fi
    fi
fi

echo ""
echo -e "${BLUE}Step 2: Installing Java (for Lavalink)${NC}"
echo "---------------------------------------"

if command -v java &> /dev/null; then
    JAVA_VERSION=$(java -version 2>&1 | head -n 1 | cut -d'"' -f2 | cut -d'.' -f1)
    if [[ $JAVA_VERSION -ge 17 ]]; then
        echo -e "${GREEN}✓ Java $JAVA_VERSION is installed${NC}"
    else
        echo -e "${YELLOW}⚠ Java 17+ required for Lavalink${NC}"
    fi
else
    echo "Installing Java 17..."
    if [[ "$OS" == "linux" ]]; then
        if command -v apt-get &> /dev/null; then
            sudo apt-get install -y openjdk-17-jre-headless
        elif command -v dnf &> /dev/null; then
            sudo dnf install -y java-17-openjdk
        elif command -v pacman &> /dev/null; then
            sudo pacman -S jre17-openjdk
        fi
    elif [[ "$OS" == "macos" ]]; then
        brew install openjdk@17
    fi
fi

echo ""
echo -e "${BLUE}Step 3: Creating Virtual Environment${NC}"
echo "--------------------------------------"

if [[ ! -d "venv" ]]; then
    python3 -m venv venv
    echo -e "${GREEN}✓ Virtual environment created${NC}"
else
    echo -e "${YELLOW}⚠ Virtual environment already exists${NC}"
fi

# Activate virtual environment
source venv/bin/activate
echo -e "${GREEN}✓ Virtual environment activated${NC}"

echo ""
echo -e "${BLUE}Step 4: Installing Python Dependencies${NC}"
echo "----------------------------------------"

pip install --upgrade pip
pip install -r requirements.txt
echo -e "${GREEN}✓ Dependencies installed${NC}"

echo ""
echo -e "${BLUE}Step 5: Setting Up Configuration${NC}"
echo "----------------------------------"

if [[ ! -f "settings.json" ]]; then
    if [[ -f "settings Example.json" ]]; then
        cp "settings Example.json" settings.json
        echo -e "${GREEN}✓ Created settings.json from template${NC}"
        echo -e "${YELLOW}⚠ IMPORTANT: Edit settings.json with your bot token and settings!${NC}"
    else
        echo -e "${RED}✗ No settings template found${NC}"
    fi
else
    echo -e "${GREEN}✓ settings.json already exists${NC}"
fi

echo ""
echo -e "${BLUE}Step 6: Creating Run Script${NC}"
echo "----------------------------"

cat > run.sh << 'EOF'
#!/bin/bash
# Activate virtual environment and run bot
source venv/bin/activate
python main.py
EOF
chmod +x run.sh
echo -e "${GREEN}✓ Created run.sh${NC}"

echo ""
echo "========================================================"
echo -e "${GREEN}🎉 Installation Complete!${NC}"
echo "========================================================"
echo ""
echo "Next steps:"
echo "  1. Edit settings.json with your Discord bot token"
echo "  2. Set up MongoDB (Atlas or local)"
echo "  3. Set up Lavalink (see lavalink/ folder)"
echo "  4. Run: ./run.sh"
echo ""
echo "For Lavalink, you can use:"
echo "  cd lavalink && java -jar Lavalink.jar"
echo ""
