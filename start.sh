#!/bin/bash

# 剧作大师 (ScriptMaster) - 一键启动脚本
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
echo -e "${CYAN}║              剧作大师 (ScriptMaster) - 一键启动               ║${NC}"
echo -e "${CYAN}║                                                              ║${NC}"
echo -e "${CYAN}╚══════════════════════════════════════════════════════════════╝${NC}"
echo ""

# 检查环境
echo -e "${BLUE}[检查]${NC} 正在检查运行环境..."

# 检查 Python
if command -v python3 &> /dev/null; then
    PYTHON_CMD="python3"
elif command -v python &> /dev/null; then
    PYTHON_CMD="python"
else
    echo -e "${RED}[错误] 未检测到 Python，请先运行 ./setup.sh 进行部署${NC}"
    exit 1
fi

# 检查 Node.js
if ! command -v node &> /dev/null; then
    echo -e "${RED}[错误] 未检测到 Node.js，请先运行 ./setup.sh 进行部署${NC}"
    exit 1
fi

# 检查虚拟环境
if [ ! -d "$SCRIPT_DIR/backend/venv" ]; then
    echo -e "${RED}[错误] 未检测到后端虚拟环境，请先运行 ./setup.sh 进行部署${NC}"
    exit 1
fi

# 检查前端依赖
if [ ! -d "$SCRIPT_DIR/frontend/node_modules" ]; then
    echo -e "${RED}[错误] 未检测到前端依赖，请先运行 ./setup.sh 进行部署${NC}"
    exit 1
fi

echo -e "${GREEN}[✓]${NC} 环境检查通过"
echo ""

# 启动后端服务
echo -e "${BLUE}[启动]${NC} 正在启动后端服务..."
cd "$SCRIPT_DIR/backend"
source venv/bin/activate

# 在后台启动后端
$PYTHON_CMD -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000 --log-level info &
BACKEND_PID=$!

echo -e "${YELLOW}[→]${NC} 等待后端服务初始化..."
sleep 3

# 检查后端是否成功启动
if ! kill -0 $BACKEND_PID 2>/dev/null; then
    echo -e "${RED}[错误] 后端服务启动失败${NC}"
    exit 1
fi

echo -e "${GREEN}[✓]${NC} 后端服务已启动 (PID: $BACKEND_PID)"
echo ""

# 启动前端服务
echo -e "${BLUE}[启动]${NC} 正在启动前端服务..."
cd "$SCRIPT_DIR/frontend"

# 在后台启动前端
npm run dev &
FRONTEND_PID=$!

echo -e "${YELLOW}[→]${NC} 等待前端服务初始化..."
sleep 3

# 检查前端是否成功启动
if ! kill -0 $FRONTEND_PID 2>/dev/null; then
    echo -e "${RED}[错误] 前端服务启动失败${NC}"
    kill $BACKEND_PID 2>/dev/null
    exit 1
fi

echo -e "${GREEN}[✓]${NC} 前端服务已启动 (PID: $FRONTEND_PID)"
echo ""

echo -e "${GREEN}╔══════════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║                    服务启动成功！                             ║${NC}"
echo -e "${GREEN}╚══════════════════════════════════════════════════════════════╝${NC}"
echo ""
echo "访问地址："
echo -e "  ${CYAN}前端界面:${NC} http://localhost:5173"
echo -e "  ${CYAN}后端API:${NC}  http://localhost:8000"
echo -e "  ${CYAN}API文档:${NC}  http://localhost:8000/docs"
echo ""
echo -e "${YELLOW}[提示]${NC} 首次使用请先配置大模型 API 密钥："
echo "       编辑 backend/.env 文件"
echo ""
echo "按 Ctrl+C 停止服务"
echo ""

# 捕获 Ctrl+C 信号
trap 'echo ""; echo "正在停止服务..."; kill $BACKEND_PID $FRONTEND_PID 2>/dev/null; exit 0' INT

# 等待进程
wait
