#!/bin/bash

# 剧作大师 (ScriptMaster) - 一键部署脚本
# 支持 Linux 和 macOS

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# 脚本目录
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo ""
echo -e "${CYAN}╔══════════════════════════════════════════════════════════════╗${NC}"
echo -e "${CYAN}║                                                              ║${NC}"
echo -e "${CYAN}║              剧作大师 (ScriptMaster) - 一键部署               ║${NC}"
echo -e "${CYAN}║                                                              ║${NC}"
echo -e "${CYAN}╚══════════════════════════════════════════════════════════════╝${NC}"
echo ""

# 检查 Python
echo -e "${BLUE}[1/6]${NC} 正在检查 Python 环境..."
if ! command -v python3 &> /dev/null; then
    if ! command -v python &> /dev/null; then
        echo -e "${RED}[错误] 未检测到 Python，请先安装 Python 3.11 或更高版本${NC}"
        echo "下载地址: https://www.python.org/downloads/"
        echo ""
        echo "macOS 用户可以使用 Homebrew: brew install python"
        echo "Linux 用户可以使用包管理器: sudo apt install python3 (Ubuntu/Debian)"
        exit 1
    fi
    PYTHON_CMD="python"
else
    PYTHON_CMD="python3"
fi

PYTHON_VERSION=$($PYTHON_CMD --version 2>&1)
echo -e "${GREEN}[✓]${NC} 检测到 $PYTHON_VERSION"
echo ""

# 检查 Node.js
echo -e "${BLUE}[2/6]${NC} 正在检查 Node.js 环境..."
if ! command -v node &> /dev/null; then
    echo -e "${RED}[错误] 未检测到 Node.js，请先安装 Node.js 18 或更高版本${NC}"
    echo "下载地址: https://nodejs.org/"
    echo ""
    echo "macOS 用户可以使用 Homebrew: brew install node"
    echo "Linux 用户可以使用 nvm 安装: https://github.com/nvm-sh/nvm"
    exit 1
fi

NODE_VERSION=$(node --version)
NPM_VERSION=$(npm --version)
echo -e "${GREEN}[✓]${NC} 检测到 Node.js $NODE_VERSION"
echo -e "${GREEN}[✓]${NC} 检测到 npm $NPM_VERSION"
echo ""

# 创建后端虚拟环境
echo -e "${BLUE}[3/6]${NC} 正在配置后端环境..."
cd "$SCRIPT_DIR/backend"

if [ ! -d "venv" ]; then
    echo -e "${YELLOW}[→]${NC} 创建 Python 虚拟环境..."
    $PYTHON_CMD -m venv venv
    if [ $? -ne 0 ]; then
        echo -e "${RED}[错误] 创建虚拟环境失败${NC}"
        exit 1
    fi
    echo -e "${GREEN}[✓]${NC} 虚拟环境创建成功"
else
    echo -e "${GREEN}[✓]${NC} 虚拟环境已存在"
fi

# 激活虚拟环境并安装依赖
echo -e "${YELLOW}[→]${NC} 正在安装后端依赖（可能需要几分钟）..."
source venv/bin/activate

$PYTHON_CMD -m pip install --upgrade pip -q
pip install -r requirements.txt -q

if [ $? -ne 0 ]; then
    echo -e "${RED}[错误] 安装后端依赖失败${NC}"
    exit 1
fi
echo -e "${GREEN}[✓]${NC} 后端依赖安装完成"
echo ""

# 创建 .env 文件（如果不存在）
if [ ! -f ".env" ]; then
    if [ -f ".env.example" ]; then
        cp .env.example .env
        echo -e "${GREEN}[✓]${NC} 已创建 .env 配置文件（请根据实际需要修改配置）"
    fi
fi
echo ""

# 安装前端依赖
echo -e "${BLUE}[4/6]${NC} 正在配置前端环境..."
cd "$SCRIPT_DIR/frontend"

if [ ! -d "node_modules" ]; then
    echo -e "${YELLOW}[→]${NC} 正在安装前端依赖（可能需要几分钟，请耐心等待）..."
    npm install
    if [ $? -ne 0 ]; then
        echo -e "${RED}[错误] 安装前端依赖失败${NC}"
        exit 1
    fi
    echo -e "${GREEN}[✓]${NC} 前端依赖安装完成"
else
    echo -e "${GREEN}[✓]${NC} 前端依赖已安装"
fi
echo ""

# 创建必要的目录
echo -e "${BLUE}[5/6]${NC} 创建必要的目录..."
cd "$SCRIPT_DIR/backend"
mkdir -p data exports
echo -e "${GREEN}[✓]${NC} 目录创建完成"
echo ""

# 完成
echo -e "${BLUE}[6/6]${NC} 部署完成！"
echo ""
echo -e "${GREEN}╔══════════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║                    部署成功！                                 ║${NC}"
echo -e "${GREEN}╚══════════════════════════════════════════════════════════════╝${NC}"
echo ""
echo "使用方法："
echo "  1. 运行 ./start.sh 启动应用（Linux/macOS）"
echo "  2. 或在 Windows 上运行 start.bat"
echo ""
echo "访问地址："
echo "  前端界面: http://localhost:5173"
echo "  后端API:  http://localhost:8000"
echo "  API文档:  http://localhost:8000/docs"
echo ""
echo "配置说明："
echo "  1. 编辑 backend/.env 文件配置大模型 API 密钥"
echo "  2. 支持通义千问、文心一言、OpenAI、Claude 等多种模型"
echo ""
