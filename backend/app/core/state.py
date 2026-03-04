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


class CharacterAppearance(TypedDict):
    """人物外观"""
    height: str                        # 身高
    build: str                         # 体型
    hair: str                          # 发型发色
    clothing_style: str                # 穿着风格
    distinctive_features: str          # 标志性特征


class Character(TypedDict):
    """人物信息（V1.4增强版）"""
    name: str                          # 姓名
    role: str                          # 主角/反派/爱情线/配角
    age: str                           # 年龄
    appearance: Optional[CharacterAppearance]  # 外观形象
    personality: str                   # 性格描述
    background: str                    # 背景故事
    goal: str                          # 人物目标/动机
    memory_point: str                  # 记忆点特征（包含口头禅）
    relationships: Optional[str]       # 与主要人物的关系


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


class RequirementAssessmentField(TypedDict):
    """单个需求字段的评估"""
    status: str                        # empty / partial / confirmed
    understanding: str                 # 智能体的理解描述
    confidence: float                  # 置信度 0-1
    suggestion: Optional[str]          # 改进建议


class RequirementAssessment(TypedDict):
    """需求评估结果"""
    genre: Optional[RequirementAssessmentField]
    protagonist: Optional[RequirementAssessmentField]
    conflict: Optional[RequirementAssessmentField]
    target_audience: Optional[RequirementAssessmentField]
    episodes: Optional[RequirementAssessmentField]
    style: Optional[RequirementAssessmentField]


class UnderstandingDisplay(TypedDict):
    """需求理解展示（用于右侧边栏）"""
    title: Optional[str]               # 暂定剧名
    genre_summary: Optional[str]       # 题材概述
    protagonist_summary: Optional[str] # 主角概述
    conflict_summary: Optional[str]    # 冲突概述
    style_summary: Optional[str]       # 风格概述
    next_steps: List[str]              # 接下来要完善的内容


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

    # ===== V1.3 统一上下文管理 =====
    # 三层核心信息
    conversation_summary: Optional[str]                      # 对话摘要（200字内，历史上下文）
    requirement_analysis: Optional[str]                      # 需求分析（300字内，当前理解）
    last_context_update_index: int                           # 上次上下文更新时的消息索引

    # 结构化数据
    requirement_assessment: Optional[RequirementAssessment]  # 需求评估（内部结构化数据）

    # 展示数据
    understanding_display: Optional[UnderstandingDisplay]    # 需求理解展示（侧边栏用）
    understanding_summary: Optional[str]                     # 需求理解报告（弹窗显示，Markdown格式）

    # 传递给下一阶段的上下文
    clarify_context_for_creation: Optional[Dict[str, Any]]   # 需求澄清阶段的上下文，传递给剧本创作阶段

    # 兼容旧版本（将逐步移除）
    last_summary_index: int                                  # [兼容] 上次摘要时的消息索引
    recent_context: Optional[str]                            # [兼容] 最近5轮对话内容

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

        # V1.3 统一上下文管理
        "conversation_summary": None,
        "requirement_analysis": None,
        "last_context_update_index": 0,
        "requirement_assessment": None,
        "understanding_display": None,
        "understanding_summary": None,
        "clarify_context_for_creation": None,  # 传递给剧本创作阶段的上下文
        # 兼容旧版本
        "last_summary_index": 0,
        "recent_context": None,

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
    检查需求完整度（支持子字段检测）

    必需字段及权重：
    - genre (题材): 20分
    - protagonist (主角): 20分
    - conflict (核心冲突): 20分
    - target_audience (目标受众): 15分
    - episodes (集数): 15分
    - style (风格基调): 10分

    总分100分，>=80分视为完整

    支持子字段检测：当主字段为空时，检查对应的子字段是否存在
    """
    weights = {
        "genre": 20,
        "protagonist": 20,
        "conflict": 20,
        "target_audience": 15,
        "episodes": 15,
        "style": 10
    }

    # 子字段到主字段的映射
    subfield_mapping = {
        "genre": ["genre", "题材类型"],
        "protagonist": [
            "protagonist", "protagonist_identity", "protagonist_traits",
            "protagonist_goal", "protagonist_occupation", "protagonist_style",
            "主角", "主角设定"
        ],
        "conflict": [
            "conflict", "core_conflict", "system_binding_reason",
            "system_operation_mode", "穿越原因", "绑定系统"
        ],
        "target_audience": ["target_audience", "目标受众", "受众"],
        "episodes": ["episodes", "集数"],
        "style": ["style", "风格", "风格基调"]
    }

    score = 0
    for field, weight in weights.items():
        # 检查主字段
        if field in requirements and requirements[field]:
            score += weight
        # 检查子字段（如果主字段为空）
        elif field in subfield_mapping:
            subfields = subfield_mapping[field]
            if any(sf in requirements and requirements[sf] for sf in subfields):
                score += weight

    return score
