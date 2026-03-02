"""
ScriptState 状态定义模块
"""
from typing import Any, Dict, List, Optional, TypedDict
from datetime import datetime
from enum import Enum


class ProjectStatus(str, Enum):
    """项目状态"""
    CLARIFYING = "clarifying"          # 需求澄清中
    REQUIREMENT_LOCKED = "locked"      # 需求已锁定
    CREATING = "creating"              # 剧本创作中
    PAUSED = "paused"                  # 已暂停
    COMPLETED = "completed"            # 已完成
    FAILED = "failed"                  # 失败


class EpisodeStatus(str, Enum):
    """单集状态"""
    PENDING = "pending"                # 等待生成
    GENERATING = "generating"          # 生成中
    COMPLETED = "completed"            # 已完成
    FAILED = "failed"                  # 失败


class Message(TypedDict):
    """对话消息"""
    role: str                          # user / assistant / system
    content: str
    type: Optional[str]                # text / option / summary
    options: Optional[List[Dict[str, Any]]]
    created_at: Optional[str]


class Character(TypedDict):
    """人物信息"""
    name: str
    role: str                          # 主角/反派/配角
    age: str
    personality: str
    background: str
    goal: str
    memory_point: str


class EpisodeOutline(TypedDict):
    """分集大纲"""
    episode_number: int
    summary: str
    hook: str                          # 卡点/钩子
    is_checkpoint: bool                # 是否是付费卡点


class EpisodeScript(TypedDict):
    """单集剧本"""
    episode_number: int
    title: str
    content: str
    word_count: int
    status: str
    quality_report: Optional[Dict[str, Any]]


class CharacterStatus(TypedDict):
    """人物状态追踪（用于剧本生成时的上下文）"""
    name: str
    current_emotion: str              # 当前情绪状态
    current_situation: str            # 当前处境/状况
    goal_progress: str                # 目标进展
    relationships: Dict[str, str]     # 与其他人物的关系状态
    key_events: List[str]             # 该人物经历的关键事件
    secrets_known: List[str]          # 该人物已知的秘密/信息


class StoryArc(TypedDict):
    """故事弧线追踪"""
    arc_type: str                     # 主线/支线
    name: str                         # 弧线名称
    status: str                       # 进行中/已解决/待触发
    trigger_episode: int              # 触发集数
    resolve_episode: Optional[int]    # 解决集数
    key_events: List[Dict[str, Any]]  # 关键事件列表


class ScriptContext(TypedDict):
    """剧本创作上下文（增强上下文管理）"""
    # 故事结构定位
    story_phase: str                  # 起/承/转/合/高潮/结局
    phase_progress: str               # 当前阶段进展描述

    # 人物状态（动态更新）
    character_statuses: Dict[str, CharacterStatus]

    # 剧情追踪
    completed_events: List[str]       # 已完成的关键事件
    pending_hooks: List[str]          # 待回收的悬念/钩子
    resolved_hooks: List[str]         # 已解决的悬念
    foreshadowing: List[str]          # 已埋下的伏笔

    # 前情摘要（动态生成）
    recent_summary: str               # 最近3集剧情摘要
    key_revelations: List[str]        # 关键揭示/反转

    # 创作约束
    constraints_check: List[str]      # 需要遵守的约束检查点


class CreationProgress(TypedDict):
    """创作进度"""
    step: str                          # synopsis/characters/outline/script/quality_check
    status: str                        # pending/in_progress/completed/failed
    percentage: int                    # 0-100
    completed_episodes: int
    total_episodes: int
    estimated_remaining_time: Optional[int]  # 预计剩余时间（秒）


class ScriptState(TypedDict):
    """
    剧本创作状态

    统一状态管理对象，贯穿需求澄清和剧本创作两个阶段
    """
    # 项目基础信息
    project_id: str
    project_name: str
    status: str                        # ProjectStatus
    created_at: str
    updated_at: str

    # ===== 阶段一：需求澄清 =====
    messages: List[Message]            # 对话历史
    requirements: Dict[str, Any]       # 已提取的需求字段
    completeness: int                  # 需求完整度 0-100
    requirements_locked: bool          # 需求是否已锁定
    pending_field: Optional[str]       # 当前待询问的字段
    showed_summary: bool               # 是否已展示确认书

    # ===== 阶段二：剧本创作 =====
    story_synopsis: Optional[str]              # 故事梗概
    story_title: Optional[str]                 # 故事标题
    one_liner: Optional[str]                   # 一句话梗概
    selling_points: Optional[List[str]]        # 核心卖点

    character_profiles: Optional[List[Character]]      # 人物小传
    relationship_map: Optional[str]                    # 人物关系图

    episode_outlines: Optional[List[EpisodeOutline]]   # 分集大纲
    total_episodes: int                                # 总集数

    scripts: Optional[List[EpisodeScript]]             # 剧本正文
    creation_progress: Optional[CreationProgress]      # 创作进度
    fix_attempts: int                                  # 自动修复尝试次数

    # 增强上下文管理
    script_context: Optional[ScriptContext]            # 剧本创作上下文
    story_arcs: Optional[List[StoryArc]]               # 故事弧线追踪

    # 版本历史
    versions: List[Dict[str, Any]]             # 版本历史记录


def create_initial_state(project_id: str, project_name: str) -> ScriptState:
    """创建初始状态"""
    now = datetime.now().isoformat()
    return {
        "project_id": project_id,
        "project_name": project_name,
        "status": ProjectStatus.CLARIFYING,
        "created_at": now,
        "updated_at": now,

        # 需求澄清阶段
        "messages": [],
        "requirements": {},
        "completeness": 0,
        "requirements_locked": False,
        "pending_field": None,
        "showed_summary": False,

        # 剧本创作阶段
        "story_synopsis": None,
        "story_title": None,
        "one_liner": None,
        "selling_points": None,

        "character_profiles": None,
        "relationship_map": None,

        "episode_outlines": None,
        "total_episodes": 80,

        "scripts": None,
        "creation_progress": None,
        "fix_attempts": 0,

        # 增强上下文管理
        "script_context": None,
        "story_arcs": None,

        # 版本历史
        "versions": []
    }


def check_requirement_completeness(requirements: Dict[str, Any]) -> int:
    """
    检查需求完整度

    必需字段及权重：
    - genre (题材): 20分
    - protagonist (主角): 20分
    - conflict (核心冲突): 20分
    - target_audience (目标受众): 15分
    - episodes (集数): 15分
    - style (风格基调): 10分

    总分100分，>=80分视为完整
    """
    weights = {
        "genre": 20,
        "protagonist": 20,
        "conflict": 20,
        "target_audience": 15,
        "episodes": 15,
        "style": 10
    }

    score = 0
    for field, weight in weights.items():
        if field in requirements and requirements[field]:
            score += weight

    return score
