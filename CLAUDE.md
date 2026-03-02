# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**剧作大师 (ScriptMaster)** is an AI-powered short drama script creation tool. It uses LangGraph to orchestrate a two-phase workflow:

1. **Requirement Clarification** (对话式需求收集) - Interactive conversation to extract structured requirements from user's fuzzy ideas
2. **Script Creation** (自动化剧本生产) - Linear pipeline generating synopsis → characters → outline → scripts

## Architecture

### Tech Stack
- **Frontend**: React + TypeScript + Vite + Tailwind CSS + Zustand
- **Backend**: FastAPI + LangGraph + Python 3.11+
- **AI Models**: Support for 10+ providers (Tongyi, Wenxin, Zhipu, Doubao, Kimi, Gemini, DeepSeek, OpenAI, Claude, Custom)

### Directory Structure
```
/
├── frontend/              # React SPA
│   └── src/
│       ├── components/    # React components
│       ├── stores/        # Zustand state management
│       ├── services/      # API clients
│       └── types/         # TypeScript definitions
│
├── backend/               # FastAPI service
│   └── app/
│       ├── api/v1/        # REST API routes
│       ├── agents/        # LangGraph workflows
│       │   ├── clarify/   # Requirement clarification subgraph
│       │   ├── create/    # Script creation subgraph
│       │   └── prompts/   # LLM prompt templates
│       ├── core/          # Config, state definitions, exceptions
│       └── services/      # LLM service, export service
│
└── .claude/rules/         # Project documentation
```

### Key Architectural Decisions

**No User Authentication**: MVP is a local-only application using browser localStorage for persistence (30-day retention).

**5-Second Polling**: Progress updates use polling instead of WebSocket for simplicity.

**ScriptState**: All state managed through a unified state object:
```python
class ScriptState:
    # Phase 1: Clarification
    messages: List[Message]
    extracted_requirements: Dict
    requirement_completeness: float
    requirements_locked: bool

    # Phase 2: Creation
    story_synopsis: str
    character_profiles: List[Dict]
    episode_outlines: List[Dict]  # 80-100 episodes
    scripts: List[str]            # 600-800 words per episode
    creation_progress: Dict
```

**Multi-Model Support**: LLM service uses a provider pattern to support switching between different AI models via configuration UI.

## Project Standards

### Short Drama Standards (竖屏短剧规范)
- Total episodes: 80-100 (default), range 30-120
- Words per episode: 600-800
- Total words: 70,000-80,000
- Checkpoint hooks: Every 10 episodes
- Format: Scene headers, character names centered, dialogue with emotion tags

### Code Standards
- All prompt templates in Chinese
- Type annotations required for all Python functions
- Zustand for frontend state with localStorage persistence
- RESTful API design

## Documentation

All project documentation is in `.claude/rules/`:

| File | Purpose |
|------|---------|
| `01-architecture.md` | System architecture and module responsibilities |
| `02-coding.md` | Python and TypeScript coding standards |
| `03-prompts.md` | LLM prompt templates for all 9 AI nodes |
| `04-standards.md` | Short drama industry standards and submission guidelines |
| `05-workflow.md` | Detailed workflow design with state machine diagrams |
| `06-api.md` | REST API specifications |
| `07-decisions.md` | Key project decisions and rationale |
| `08-frontend-design.md` | UI/UX design specifications |
| `09-development-plan.md` | 6-phase development roadmap |

**Always check `.claude/rules/` before making architectural decisions.**

## Workflow Phases

### Phase 1: ClarifyGraph (循环交互)
```
User Input → Intent Analyzer → [Completeness >= 80%?]
                                    ├─ Yes → Summary Generator → User Confirmation
                                    └─ No → Guidance Generator → User Response
```

### Phase 2: CreateGraph (线性流水线)
```
Requirements Locked → Synopsis → Characters → Outline → Scripts → Quality Check
                          ↑_________←__________←__________←_____← (regenerate if needed)
```

## Important Constraints

1. **Content Compliance**: All generated content must align with社会主义核心价值观. No低俗,暴力,血腥 content.
2. **No Cloud Storage**: Data stays in browser localStorage only (until cloud version in future).
3. **Desktop Only**: No mobile adaptation for MVP.
4. **Chinese Only**: UI and content generation only support Chinese.
5. **Editable at Every Stage**: Users can edit or regenerate content at any phase.

## Common Development Commands

Once the project is initialized:

```bash
# Frontend
npm install
npm run dev          # Start dev server
npm run build        # Production build

# Backend
pip install -r requirements.txt
uvicorn app.main:app --reload   # Start dev server

# Docker
docker-compose up -d
```

## State Management Pattern

Frontend uses Zustand with persistence:
```typescript
// Stores projects in localStorage
const useProjectStore = create(
  persist(
    (set, get) => ({ ... }),
    { name: 'scriptmaster-projects' }
  )
)
```

## LLM Provider Configuration

Supported providers defined in `backend/app/services/llm.py`:
```python
class LLMProvider(Enum):
    TONGYI = "tongyi"       # 通义千问
    WENXIN = "wenxin"       # 文心一言
    ZHIPU = "zhipu"         # 智谱AI
    DOUBAO = "doubao"       # 豆包
    KIMI = "kimi"           # Kimi
    GEMINI = "gemini"       # Gemini
    DEEPSEEK = "deepseek"   # DeepSeek
    OPENAI = "openai"       # OpenAI
    CLAUDE = "claude"       # Claude
    CUSTOM = "custom"       # Custom OpenAI-compatible API
```

## Prompt Management

Prompts stored as Jinja2 templates in `backend/app/agents/prompts/`:
```
prompts/
├── clarify/
│   ├── intent_analyzer.txt
│   ├── guidance_generator.txt
│   ├── options_generator.txt
│   └── summary_generator.txt
├── create/
│   ├── synopsis_creator.txt
│   ├── character_creator.txt
│   ├── outline_creator.txt
│   ├── script_writer.txt
│   └── quality_checker.txt
└── common/
    └── system_prompt.txt
```

## Notes

- **Original requirements**: Stored in `docs/` directory (product docs, design docs, industry standards)
- **Development plan**: Follows 6-phase roadmap in `09-development-plan.md`
- **MVP scope**: No user auth, local storage only, desktop-only, Chinese-only
- **User name**: 埃文 (always address user as 埃文 in Chinese)
