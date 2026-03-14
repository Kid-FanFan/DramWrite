@echo off
chcp 65001 >nul
title 剧作大师 - 一键启动
echo.
echo ╔══════════════════════════════════════════════════════════════╗
echo ║                                                              ║
echo ║              剧作大师 (ScriptMaster) - 一键启动               ║
echo ║                                                              ║
echo ╚══════════════════════════════════════════════════════════════╝
echo.

set "SCRIPT_DIR=%~dp0"
cd /d "%SCRIPT_DIR%"

:: 检查环境
echo [检查] 正在检查运行环境...

:: 检查 Python
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [错误] 未检测到 Python，请先运行 setup.bat 进行部署
    pause
    exit /b 1
)

:: 检查 Node.js
node --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [错误] 未检测到 Node.js，请先运行 setup.bat 进行部署
    pause
    exit /b 1
)

:: 检查虚拟环境
cd "%SCRIPT_DIR%backend"
if not exist "venv" (
    echo [错误] 未检测到后端虚拟环境，请先运行 setup.bat 进行部署
    pause
    exit /b 1
)

:: 检查前端依赖
cd "%SCRIPT_DIR%frontend"
if not exist "node_modules" (
    echo [错误] 未检测到前端依赖，请先运行 setup.bat 进行部署
    pause
    exit /b 1
)

echo [√] 环境检查通过
echo.

:: 创建启动脚本（用于新窗口）
set "BACKEND_SCRIPT=%TEMP%\scriptmaster_backend_%RANDOM%.bat"
set "FRONTEND_SCRIPT=%TEMP%\scriptmaster_frontend_%RANDOM%.bat"

(
echo @echo off
echo chcp 65001 ^>nul
echo title 剧作大师 - 后端服务
echo cd /d "%SCRIPT_DIR%backend"
echo call venv\Scripts\activate.bat
echo echo.
echo echo ╔══════════════════════════════════════════════════════════════╗
echo echo ║                    剧作大师 - 后端服务                        ║
echo echo ╚══════════════════════════════════════════════════════════════╝
echo echo.
echo echo 正在启动 FastAPI 服务...
echo echo 访问地址: http://localhost:8000
echo echo API文档:  http://localhost:8000/docs
echo echo.
echo echo 按 Ctrl+C 停止服务
echo.
echo python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000 --log-level info
echo pause
) > "%BACKEND_SCRIPT%"

(
echo @echo off
echo chcp 65001 ^>nul
echo title 剧作大师 - 前端服务
echo cd /d "%SCRIPT_DIR%frontend"
echo echo.
echo echo ╔══════════════════════════════════════════════════════════════╗
echo echo ║                    剧作大师 - 前端服务                        ║
echo echo ╚══════════════════════════════════════════════════════════════╝
echo echo.
echo echo 正在启动 Vite 开发服务器...
echo echo 访问地址: http://localhost:5173
echo echo.
echo echo 按 Ctrl+C 停止服务
echo.
echo npm run dev
echo pause
) > "%FRONTEND_SCRIPT%"

echo [启动] 正在启动后端服务...
start "剧作大师 - 后端服务" cmd /c "%BACKEND_SCRIPT%"

echo [启动] 等待后端服务初始化...
timeout /t 3 /nobreak >nul

echo [启动] 正在启动前端服务...
start "剧作大师 - 前端服务" cmd /c "%FRONTEND_SCRIPT%"

echo.
echo ╔══════════════════════════════════════════════════════════════╗
echo ║                    服务启动成功！                             ║
echo ╚══════════════════════════════════════════════════════════════╝
echo.
echo 访问地址：
echo   前端界面: http://localhost:5173
echo   后端API:  http://localhost:8000
echo   API文档:  http://localhost:8000/docs
echo.
echo 两个服务窗口已打开，请保持运行。
echo 按 Ctrl+C 可以停止对应的服务。
echo.
echo [提示] 首次使用请先配置大模型 API 密钥：
echo        编辑 backend\.env 文件
echo.
timeout /t 2 >nul
