@echo off
chcp 65001 >nul
title 剧作大师 - 一键部署脚本
echo.
echo ╔══════════════════════════════════════════════════════════════╗
echo ║                                                              ║
echo ║              剧作大师 (ScriptMaster) - 一键部署               ║
echo ║                                                              ║
echo ╚══════════════════════════════════════════════════════════════╝
echo.

set "SCRIPT_DIR=%~dp0"
cd /d "%SCRIPT_DIR%"

:: 检查 Python
echo [1/6] 正在检查 Python 环境...
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [错误] 未检测到 Python，请先安装 Python 3.11 或更高版本
echo 下载地址: https://www.python.org/downloads/
    pause
    exit /b 1
)
for /f "tokens=*" %%a in ('python --version 2^>^&1') do echo [√] 检测到 %%a
echo.

:: 检查 Node.js
echo [2/6] 正在检查 Node.js 环境...
node --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [错误] 未检测到 Node.js，请先安装 Node.js 18 或更高版本
echo 下载地址: https://nodejs.org/
    pause
    exit /b 1
)
for /f "tokens=*" %%a in ('node --version 2^>^&1') do echo [√] 检测到 Node.js %%a
for /f "tokens=*" %%a in ('npm --version 2^>^&1') do echo [√] 检测到 npm %%a
echo.

:: 创建后端虚拟环境
echo [3/6] 正在配置后端环境...
cd "%SCRIPT_DIR%backend"

if not exist "venv" (
    echo [→] 创建 Python 虚拟环境...
    python -m venv venv
    if %errorlevel% neq 0 (
        echo [错误] 创建虚拟环境失败
        pause
        exit /b 1
    )
    echo [√] 虚拟环境创建成功
) else (
    echo [√] 虚拟环境已存在
)

:: 激活虚拟环境并安装依赖
echo [→] 正在安装后端依赖（可能需要几分钟）...
call venv\Scripts\activate.bat

python -m pip install --upgrade pip >nul 2>&1
pip install -r requirements.txt >nul 2>&1

if %errorlevel% neq 0 (
    echo [错误] 安装后端依赖失败
    pause
    exit /b 1
)
echo [√] 后端依赖安装完成
echo.

:: 创建 .env 文件（如果不存在）
if not exist ".env" (
    if exist ".env.example" (
        copy .env.example .env >nul
        echo [√] 已创建 .env 配置文件（请根据实际需要修改配置）
    )
)
echo.

:: 安装前端依赖
echo [4/6] 正在配置前端环境...
cd "%SCRIPT_DIR%frontend"

if not exist "node_modules" (
    echo [→] 正在安装前端依赖（可能需要几分钟，请耐心等待）...
    npm install
    if %errorlevel% neq 0 (
        echo [错误] 安装前端依赖失败
        pause
        exit /b 1
    )
    echo [√] 前端依赖安装完成
) else (
    echo [√] 前端依赖已安装
)
echo.

:: 创建必要的目录
echo [5/6] 创建必要的目录...
cd "%SCRIPT_DIR%backend"
if not exist "data" mkdir data
if not exist "exports" mkdir exports
echo [√] 目录创建完成
echo.

:: 完成
echo [6/6] 部署完成！
echo.
echo ╔══════════════════════════════════════════════════════════════╗
echo ║                    部署成功！                                 ║
echo ╚══════════════════════════════════════════════════════════════╝
echo.
echo 使用方法：
echo   1. 运行 start.bat 启动应用
echo   2. 或使用 start-all.ps1 启动所有服务
echo.
echo 访问地址：
echo   前端界面: http://localhost:5173
echo   后端API:  http://localhost:8000
echo   API文档:  http://localhost:8000/docs
echo.
echo 配置说明：
echo   1. 编辑 backend\.env 文件配置大模型 API 密钥
echo   2. 支持通义千问、文心一言、OpenAI、Claude 等多种模型
echo.
pause
