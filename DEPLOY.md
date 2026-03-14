# 剧作大师 (ScriptMaster) - 快速部署指南

## 系统要求

### 必需软件

| 软件 | 版本要求 | 下载地址 |
|------|---------|---------|
| Python | 3.11+ | https://www.python.org/downloads/ |
| Node.js | 18+ | https://nodejs.org/ |

### 操作系统支持

- ✅ Windows 10/11
- ✅ macOS 11+
- ✅ Linux (Ubuntu 20.04+, CentOS 8+)

---

## 快速开始（推荐）

### 第一步：下载项目

```bash
# 使用 Git 克隆项目
git clone https://github.com/your-repo/scriptmaster.git
cd scriptmaster

# 或者直接下载 ZIP 压缩包并解压
```

### 第二步：一键部署

#### Windows 用户

1. 双击运行 `setup.bat`
2. 等待部署完成（首次部署需要几分钟下载依赖）
3. 部署成功后会显示提示信息

#### macOS/Linux 用户

```bash
# 运行部署脚本
./setup.sh

# 如果提示权限不足，先添加执行权限：
chmod +x setup.sh start.sh
./setup.sh
```

### 第三步：配置大模型 API

编辑 `backend/.env` 文件，添加你的大模型 API 密钥：

```env
# 选择模型提供商（tongyi/wenxin/zhipu/openai/claude/custom 等）
LLM_PROVIDER=tongyi

# API 密钥（根据所选模型填写）
LLM_API_KEY=your_api_key_here

# 模型名称（可选，留空使用默认）
LLM_MODEL=

# API 基础地址（自定义模型时需要）
LLM_API_BASE=
```

支持的模型：
- 通义千问 (tongyi) - 推荐国内用户使用
- 文心一言 (wenxin)
- 智谱 AI (zhipu)
- 豆包 (doubao)
- Kimi (kimi)
- Gemini (gemini)
- DeepSeek (deepseek)
- OpenAI (openai)
- Claude (claude)
- 自定义 OpenAI 兼容 API (custom)

### 第四步：启动应用

#### Windows 用户

双击运行 `start.bat`

#### macOS/Linux 用户

```bash
./start.sh
```

启动成功后会显示访问地址：
- 前端界面: http://localhost:5173
- 后端 API: http://localhost:8000
- API 文档: http://localhost:8000/docs

---

## 手动部署（高级用户）

如果一键部署脚本无法使用，可以手动部署：

### 1. 安装后端依赖

```bash
cd backend

# 创建虚拟环境
python -m venv venv

# 激活虚拟环境
# Windows:
venv\Scripts\activate
# macOS/Linux:
source venv/bin/activate

# 安装依赖
pip install -r requirements.txt
```

### 2. 安装前端依赖

```bash
cd frontend
npm install
```

### 3. 启动服务

```bash
# 启动后端（在 backend 目录下）
cd backend
source venv/bin/activate  # Windows: venv\Scripts\activate
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# 启动前端（在 frontend 目录下，新开终端）
cd frontend
npm run dev
```

---

## 常见问题

### 1. Python 未检测到

**问题：** 运行脚本时提示 "未检测到 Python"

**解决：**
1. 访问 https://www.python.org/downloads/ 下载并安装 Python 3.11+
2. 安装时务必勾选 "Add Python to PATH"
3. 重新打开终端窗口再试

### 2. Node.js 未检测到

**问题：** 运行脚本时提示 "未检测到 Node.js"

**解决：**
1. 访问 https://nodejs.org/ 下载并安装 Node.js 18+
2. 重新打开终端窗口再试

### 3. 端口被占用

**问题：** 启动时提示端口已被占用

**解决：**

```bash
# 查看占用 8000 端口的进程
# Windows:
netstat -ano | findstr :8000
taskkill /PID <进程ID> /F

# macOS/Linux:
lsof -i :8000
kill -9 <进程ID>
```

或者在 `backend/.env` 中修改端口：
```env
PORT=8080
```

### 4. 依赖安装失败

**问题：** pip install 或 npm install 失败

**解决：**

```bash
# 更新 pip
python -m pip install --upgrade pip

# 使用国内镜像源（中国用户）
pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
npm install --registry=https://registry.npmmirror.com
```

### 5. 后端启动失败

**问题：** 启动后端时报错

**解决：**
1. 检查是否激活了虚拟环境
2. 检查 `.env` 文件是否存在且配置正确
3. 查看 `backend/backend.log` 日志文件

### 6. 前端启动失败

**问题：** 启动前端时报错

**解决：**
1. 删除 `frontend/node_modules` 目录重新安装
2. 检查 Node.js 版本是否符合要求（18+）

---

## 目录结构

```
scriptmaster/
├── backend/              # 后端服务
│   ├── app/              # 应用代码
│   ├── data/             # 数据目录
│   ├── exports/          # 导出文件目录
│   ├── venv/             # Python 虚拟环境
│   ├── .env              # 环境变量配置
│   └── requirements.txt  # Python 依赖
│
├── frontend/             # 前端应用
│   ├── src/              # 源代码
│   ├── node_modules/     # Node.js 依赖
│   └── package.json      # 前端依赖配置
│
├── setup.bat             # Windows 一键部署
├── setup.sh              # Linux/macOS 一键部署
├── start.bat             # Windows 一键启动
├── start.sh              # Linux/macOS 一键启动
├── DEPLOY.md             # 本文档
└── README.md             # 项目说明
```

---

## 更新项目

当项目有更新时，执行以下步骤：

```bash
# 1. 拉取最新代码
git pull

# 2. 更新后端依赖
cd backend
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt

# 3. 更新前端依赖
cd ../frontend
npm install
```

---

## 技术支持

遇到问题？

1. 查看项目文档：`docs/` 目录
2. 查看日志文件：`backend/backend.log`
3. 提交 Issue 到项目仓库

---

## 许可协议

本项目仅供学习和研究使用。
