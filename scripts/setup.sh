#!/bin/bash
# scripts/setup.sh
# 环境安装脚本

set -e  # 遇到错误立即退出

echo "=== Brand Safety Agent - Environment Setup ==="
echo ""

# 颜色定义
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# 检查 Python 版本
echo "Checking Python version..."
PYTHON_VERSION=$(python3 --version 2>&1 | awk '{print $2}')
PYTHON_MAJOR=$(echo $PYTHON_VERSION | cut -d. -f1)
PYTHON_MINOR=$(echo $PYTHON_VERSION | cut -d. -f2)

if [ "$PYTHON_MAJOR" -lt 3 ] || [ "$PYTHON_MINOR" -lt 10 ]; then
    echo -e "${RED}✗ Python version $PYTHON_VERSION is too old (need >= 3.10)${NC}"
    echo "Please install Python 3.10 or higher:"
    echo "  sudo apt update"
    echo "  sudo apt install python3.10 python3.10-venv python3.10-dev"
    exit 1
else
    echo -e "${GREEN}✓ Python $PYTHON_VERSION${NC}"
fi

# 创建必要的目录
echo ""
echo "Creating directories..."
mkdir -p artifacts
mkdir -p artifacts/screenshots
mkdir -p logs
echo -e "${GREEN}✓ Directories created${NC}"

# 安装 Python 依赖
echo ""
echo "Installing Python dependencies..."
if [ -f "requirements.txt" ]; then
    pip3 install --user -r requirements.txt
else
    # 如果没有 requirements.txt，手动安装核心依赖
    pip3 install --user \
        playwright \
        anthropic \
        jsonschema \
        python-dotenv \
        requests
fi
echo -e "${GREEN}✓ Python dependencies installed${NC}"

# 安装 Playwright 浏览器
echo ""
echo "Installing Playwright browsers (this may take a few minutes)..."
python3 -m playwright install chromium
if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ Playwright browsers installed${NC}"
else
    echo -e "${YELLOW}⚠ Playwright browser installation failed${NC}"
    echo "You may need to install chromium manually:"
    echo "  sudo apt install chromium-browser"
    echo "Or increase timeout:"
    echo "  PLAYWRIGHT_DOWNLOAD_TIMEOUT=300000 python3 -m playwright install chromium"
fi

# 检查 Node.js（可选，仅用于 docx-js）
echo ""
echo "Checking Node.js (optional, for docx generation)..."
if command -v node &> /dev/null; then
    NODE_VERSION=$(node --version)
    echo -e "${GREEN}✓ Node.js $NODE_VERSION${NC}"
    
    # 检查是否需要安装 docx
    read -p "Install docx-js for document generation? (y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        npm install -g docx
        echo -e "${GREEN}✓ docx-js installed${NC}"
    fi
else
    echo -e "${YELLOW}⚠ Node.js not found (optional)${NC}"
    echo "If you need document generation, install Node.js 20+:"
    echo "  curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.0/install.sh | bash"
    echo "  nvm install 20"
fi

# 验证核心文件存在
echo ""
echo "Checking required files..."
REQUIRED_FILES=(
    "datasets/tasks.json"
    "datasets/allowlist.txt"
    "eval/schema.json"
)

MISSING_FILES=()
for file in "${REQUIRED_FILES[@]}"; do
    if [ -f "$file" ]; then
        echo -e "${GREEN}✓ $file${NC}"
    else
        echo -e "${RED}✗ $file (missing)${NC}"
        MISSING_FILES+=("$file")
    fi
done

if [ ${#MISSING_FILES[@]} -gt 0 ]; then
    echo ""
    echo -e "${RED}Missing required files:${NC}"
    for file in "${MISSING_FILES[@]}"; do
        echo "  - $file"
    done
    echo ""
    echo "Please create these files or restore them from git."
fi

# 检查 .env 文件（包含 API keys）
echo ""
if [ -f ".env" ]; then
    echo -e "${GREEN}✓ .env file found${NC}"
    # 检查是否包含必要的 key
    if grep -q "MINIMAX_API_KEY" .env || grep -q "OPENAI_API_KEY" .env; then
        echo -e "${GREEN}✓ API keys configured${NC}"
    else
        echo -e "${YELLOW}⚠ .env exists but no API keys found${NC}"
        echo "Please add your API key to .env:"
        echo "  echo 'MINIMAX_API_KEY=your_key_here' >> .env"
    fi
else
    echo -e "${YELLOW}⚠ .env file not found${NC}"
    echo "Creating template .env file..."
    cat > .env << 'EOF'
# API Keys (replace with your actual keys)
MINIMAX_API_KEY=your_minimax_key_here
OPENAI_API_KEY=your_openai_key_here

# Optional: Anthropic key for Claude API
ANTHROPIC_API_KEY=your_anthropic_key_here
EOF
    echo -e "${GREEN}✓ .env template created${NC}"
    echo "Please edit .env and add your actual API keys"
fi

# 验证 JSON 文件格式
echo ""
echo "Validating JSON files..."
for file in datasets/*.json eval/*.json; do
    if [ -f "$file" ]; then
        if python3 -m json.tool "$file" > /dev/null 2>&1; then
            echo -e "${GREEN}✓ $file${NC}"
        else
            echo -e "${RED}✗ $file (invalid JSON)${NC}"
        fi
    fi
done

# 最终检查
echo ""
echo "=== Setup Summary ==="
echo ""

# 检查是否可以导入核心模块
IMPORT_CHECK=$(python3 -c "
try:
    import playwright
    import jsonschema
    print('OK')
except ImportError as e:
    print(f'FAIL: {e}')
" 2>&1)

if [ "$IMPORT_CHECK" = "OK" ]; then
    echo -e "${GREEN}✓ All core dependencies ready${NC}"
else
    echo -e "${RED}✗ Import check failed: $IMPORT_CHECK${NC}"
fi

# 磁盘空间检查
DISK_AVAIL=$(df -h . | awk 'NR==2 {print $4}')
echo "Disk space available: $DISK_AVAIL"

# 内存检查
MEM_AVAIL=$(free -h | awk 'NR==2 {print $7}')
echo "Memory available: $MEM_AVAIL"

echo ""
echo "=== Next Steps ==="
echo ""
echo "1. Edit .env and add your API keys"
echo "2. Run a test: python3 agent/agent.py --task_id T1 --strategy_id A --timeout 90 --max_steps 8"
echo "3. Check output: tail -n 1 artifacts/runs.jsonl | python3 -m json.tool"
echo ""
echo -e "${GREEN}Setup complete!${NC}"