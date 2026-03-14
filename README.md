# 剧作大师 (ScriptMaster)

<div align="center">

**AI 驱动的短剧剧本创作工具**

基于 LangGraph 的智能剧本生成系统，通过对话式需求收集 + 自动化流水线，快速生成符合行业标准的竖屏短剧剧本。

[![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://www.python.org/)
[![Node.js](https://img.shields.io/badge/Node.js-18+-green.svg)](https://nodejs.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.109+-orange.svg)](https://fastapi.tiangolo.com/)
[![React](https://img.shields.io/badge/React-18+-61DAFB.svg)](https://react.dev/)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](#license)

</div>

---

## 功能特性

### 核心功能
- **🤖 智能需求澄清** - 对话式引导，将模糊创意转化为结构化需求
- **📝 自动化剧本生产** - 流水线生成：故事梗概 → 人物小传 → 分集大纲 → 剧本正文
- **✏️ 全流程可编辑** - 每个阶段支持人工修改和重新生成
- **📊 质量检查** - 自动检测字数、格式、卡点设计
- **📤 多格式导出** - 支持 Word 文档导出，符合投稿标准
- **🔌 多模型支持** - 支持通义千问、文心一言、Claude、OpenAI 等 10+ 模型

### 短剧行业规范支持
- **标准集数** - 80-100集（可配置30-120集）
- **单集字数** - 600-800字标准，符合拍摄时长要求
- **卡点设计** - 每10集设置强付费卡点
- **格式规范** - 符合竖屏短剧投稿标准

## 技术栈

### 后端
- **框架**: FastAPI (异步 Web 框架)
- **AI 编排**: LangGraph (状态机 + 智能体编排)
- **LLM 接口**: LangChain + 多提供商适配
- **数据库**: SQLite (本地) / PostgreSQL (云端)
- **ORM**: SQLAlchemy
- **文档生成**: python-docx

### 前端
- **框架**: React 18 + TypeScript
- **构建工具**: Vite
- **样式**: Tailwind CSS
- **状态管理**: Zustand (持久化到 localStorage)
- **路由**: React Router
- **HTTP 客户端**: Axios
- **UI 组件**: 自定义组件 + Headless UI

## 快速开始

### 环境要求

- Python 3.11+
- Node.js 18+
- npm 或 yarn

### 安装步骤

#### 1. 克隆仓库

```bash
git clone <repository-url>
cd DramWrite
```

#### 2. 配置后端

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

# 复制环境配置模板
cp .env.example .env

# 编辑 .env 文件，填入你的 API Key
# LLM_API_KEY=your_api_key_here
```

#### 3. 配置前端

```bash
cd ../frontend

# 安装依赖
npm install

# 复制环境配置模板
cp .env.example .env
```

#### 4. 启动服务

**方式一：使用启动脚本（Windows PowerShell）**

```powershell
# 在项目根目录运行
.\start-all.ps1
```

**方式二：分别启动**

```bash
# 终端 1 - 启动后端
cd backend
venv\Scripts\activate  # Windows
# source venv/bin/activate  # macOS/Linux
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# 终端 2 - 启动前端
cd frontend
npm run dev
```

#### 5. 访问应用

打开浏览器访问: http://localhost:5173

## 项目结构

```
DramWrite/
├── backend/                    # 后端服务
│   ├── app/
│   │   ├── api/v1/endpoints/  # API 路由端点
│   │   ├── agents/            # LangGraph 智能体
│   │   │   ├── clarify/       # 需求澄清子图
│   │   │   │   ├── nodes.py
│   │   │   │   ├── graph.py
│   │   │   │   └── prompts/   # 需求澄清提示词
│   │   │   ├── create/        # 剧本创作子图
│   │   │   │   ├── nodes.py
│   │   │   │   ├── graph.py
│   │   │   │   └── prompts/   # 剧本创作提示词
│   │   │   └── common/prompts/# 通用提示词
│   │   ├── core/              # 核心模块
│   │   │   ├── config.py      # 配置管理
│   │   │   ├── database.py    # 数据库连接
│   │   │   ├── exceptions.py  # 异常定义
│   │   │   └── state.py       # ScriptState 状态定义
│   │   ├── models/            # Pydantic 数据模型
│   │   │   ├── chat.py
│   │   │   ├── project.py
│   │   │   ├── script.py
│   │   │   └── settings.py
│   │   ├── services/          # 业务服务
│   │   │   ├── agent_service.py   # 智能体服务
│   │   │   ├── llm.py             # LLM 统一接口
│   │   │   ├── project_service.py # 项目管理
│   │   │   └── export_service.py  # 导出服务
│   │   └── main.py            # FastAPI 入口
│   ├── data/                  # SQLite 数据库（git 忽略）
│   ├── tests/                 # 测试代码
│   ├── requirements.txt       # Python 依赖
│   └── .env.example           # 环境变量模板
│
├── frontend/                   # 前端应用
│   ├── src/
│   │   ├── components/        # React 组件
│   │   │   ├── common/        # 通用组件
│   │   │   ├── layout/        # 布局组件
│   │   │   └── pages/         # 页面组件
│   │   │       ├── HomePage.tsx
│   │   │       ├── ClarifyPage.tsx
│   │   │       ├── ConfirmPage.tsx
│   │   │       ├── CreatePage.tsx
│   │   │       └── EditorPage.tsx
│   │   ├── hooks/             # 自定义 Hooks
│   │   ├── stores/            # Zustand 状态管理
│   │   ├── services/          # API 服务
│   │   ├── types/             # TypeScript 类型定义
│   │   └── utils/             # 工具函数
│   ├── public/
│   ├── package.json
│   ├── tsconfig.json
│   ├── vite.config.ts
│   └── .env.example           # 环境变量模板
│
├── .claude/rules/             # Claude Code 规则文档
│   ├── 01-architecture.md     # 架构设计
│   ├── 02-coding.md           # 编码规范
│   ├── 03-prompts.md          # 提示词规范
│   ├── 04-standards.md        # 短剧行业标准
│   ├── 05-workflow.md         # 工作流设计
│   ├── 06-api.md              # API 规范
│   ├── 07-decisions.md        # 关键决策记录
│   ├── 08-frontend-design.md  # 前端设计规范
│   └── 09-development-plan.md # 开发计划
│
├── docs/                       # 产品文档
│   └── ...
│
├── .gitignore
├── docker-compose.yml         # Docker 编排
└── README.md
```

## 配置说明

### 后端环境变量 (backend/.env)

```env
# 应用配置
DEBUG=true
HOST=0.0.0.0
PORT=8000

# CORS 配置
CORS_ORIGINS=http://localhost:5173,http://127.0.0.1:5173

# LLM 配置
LLM_PROVIDER=tongyi           # 模型提供商
LLM_API_KEY=your_api_key      # API 密钥（必填）
LLM_API_BASE=                 # 自定义 API 地址（可选）
LLM_MODEL=qwen-max            # 模型名称
LLM_TEMPERATURE=0.7           # 温度参数
LLM_MAX_TOKENS=4000           # 最大 Token 数
```

### 支持的模型提供商

| 提供商 | ID | 默认模型 |
|-------|-----|---------|
| 通义千问 | `tongyi` | qwen-max |
| 文心一言 | `wenxin` | ERNIE-Bot-4 |
| 智谱 AI | `zhipu` | glm-4 |
| 豆包 | `doubao` | doubao-pro-128k |
| Kimi | `kimi` | moonshot-v1-128k |
| Gemini | `gemini` | gemini-pro |
| DeepSeek | `deepseek` | deepseek-chat |
| OpenAI | `openai` | gpt-4 |
| Claude | `claude` | claude-3-sonnet |
| 自定义 | `custom` | - |

> **提示**: 也可以在应用的「设置」页面配置模型，配置会保存到本地数据库。

## 开发指南

### Claude Code 规则文档

本项目使用 Claude Code 进行开发，所有规则文档位于 `.claude/rules/` 目录：

| 文档 | 内容 | 优先级 |
|------|------|--------|
| [01-architecture.md](.claude/rules/01-architecture.md) | 系统架构设计、模块职责、技术选型 | 高 |
| [02-coding.md](.claude/rules/02-coding.md) | Python/TypeScript 编码规范、LangGraph 规范 | 高 |
| [03-prompts.md](.claude/rules/03-prompts.md) | AI 节点提示词规范、提示词管理 | 高 |
| [04-standards.md](.claude/rules/04-standards.md) | 竖屏短剧行业标准、投稿规范 | 高 |
| [05-workflow.md](.claude/rules/05-workflow.md) | 双阶段工作流详细设计、节点实现 | 高 |
| [06-api.md](.claude/rules/06-api.md) | RESTful API 规范、WebSocket 设计 | 中 |
| [07-decisions.md](.claude/rules/07-decisions.md) | 关键决策记录 | 中 |
| [08-frontend-design.md](.claude/rules/08-frontend-design.md) | 前端交互设计规范 | 中 |
| [09-development-plan.md](.claude/rules/09-development-plan.md) | 6阶段开发计划 | 低 |

### API 文档

启动后端后访问:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

### 代码规范

**Python**
- 使用 4 空格缩进
- 类型注解必填
- 遵循 PEP 8 规范
- 所有函数必须有 docstring

**TypeScript/React**
- 使用函数组件 + Hooks
- 组件使用 PascalCase 命名
- 使用 Tailwind CSS 样式

### 分支管理

```bash
main        # 主分支，稳定版本
develop     # 开发分支
feature/*   # 功能分支
fix/*       # 修复分支
```

## 常见问题

### Q: 启动后端报错 `ModuleNotFoundError`

确保已激活虚拟环境并安装依赖：
```bash
cd backend
source venv/bin/activate  # macOS/Linux
# 或 venv\Scripts\activate  # Windows
pip install -r requirements.txt
```

### Q: 前端无法连接后端 API

1. 确认后端服务已启动（访问 http://localhost:8000/docs）
2. 检查 `frontend/.env` 中的 `VITE_API_BASE_URL` 配置
3. 检查后端 CORS 配置是否正确

### Q: AI 生成失败

1. 检查 API Key 是否正确（在设置页面测试连接）
2. 检查 API Key 余额是否充足
3. 查看后端控制台日志获取详细错误信息

### Q: 如何切换 AI 模型

在应用中点击右上角「设置」按钮，选择模型提供商并填入对应的 API Key。

### Q: 项目数据存储在哪里

- **MVP 版本**: 数据存储在浏览器 localStorage 中
- **数据保留期限**: 30 天
- **导出备份**: 使用导出功能保存到本地文件

## 贡献指南

1. Fork 本仓库
2. 创建功能分支 (`git checkout -b feature/amazing-feature`)
3. 提交更改 (`git commit -m 'Add amazing feature'`)
4. 推送到分支 (`git push origin feature/amazing-feature`)
5. 创建 Pull Request

## 版本历史

| 版本 | 日期 | 更新内容 |
|------|------|----------|
| v1.1.5 | 2026-03-04 | 优化需求澄清节点，增强记忆管理 |
| v1.0.0 | 2026-02-26 | MVP 版本发布 |

## 许可证

暂无

## 致谢

- [LangGraph](https://github.com/langchain-ai/langgraph) - AI 工作流编排
- [FastAPI](https://fastapi.tiangolo.com/) - 现代化 Python Web 框架
- [React](https://react.dev/) - 用户界面库
- [Tailwind CSS](https://tailwindcss.com/) - 原子化 CSS 框架

---

<div align="center">

**剧作大师 ScriptMaster** - 让 AI 助你创作精彩短剧

当前版本: v1.1.5

</div>
