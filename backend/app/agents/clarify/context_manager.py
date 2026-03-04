"""
统一上下文管理模块 (Unified Context Manager)

职责：
1. 构建统一上下文（对话摘要 + 需求分析 + 用户问题）
2. 更新对话摘要（控制在200字内）
3. 更新需求分析（控制在300字内）
4. 更新需求评估和下一步建议
5. 确保各节点使用一致的上下文

设计原则：
- 每轮对话完成后更新上下文
- 对话摘要控制在200字内
- 需求分析控制在300字内
- 需求确认书阶段将需求分析传递给下一阶段，保证需求一致性
"""
import json
from typing import Dict, Any, List, Optional
from loguru import logger

from app.core.state import ScriptState
from app.services.llm import get_llm_service, LLMConfig


# ===== 提示词模板 =====

CONVERSATION_SUMMARY_PROMPT = """请对以下对话生成简洁摘要，保留所有关键信息。

## 对话记录
{messages}

## 已确认的需求
{requirements}

## 摘要要求
1. 总结用户已确认的所有需求信息
2. 记录重要的背景信息和偏好
3. 标注尚未明确的需求字段
4. **严格控制在200字以内**
5. 使用中文输出

请直接输出摘要内容，不要添加任何标题或格式。"""


REQUIREMENT_ANALYSIS_PROMPT = """根据以下信息，生成结构化的需求分析报告。

## 对话摘要
{conversation_summary}

## 最近对话（5轮）
{recent_context}

## 已提取的需求字段
{requirements}

## 需求评估
{assessment}

## 需求分析要求
1. 分析当前对用户需求的理解程度
2. 总结已确认的核心信息
3. 指出信息不完整或模糊的地方
4. **严格控制在300字以内**
5. 使用简洁的专业语言

请直接输出分析内容，不要添加任何标题或格式。"""


UNDERSTANDING_DISPLAY_PROMPT = """根据以下信息，生成用于前端右侧边栏展示的需求理解摘要。

## 需求分析
{requirement_analysis}

## 已提取的需求字段
{requirements}

## 输出要求
生成 JSON 格式的结构化数据：
{{
    "title": "暂定剧名（如能推断，否则为空）",
    "genre_summary": "题材概述（一句话）",
    "protagonist_summary": "主角概述（一句话）",
    "conflict_summary": "冲突概述（一句话）",
    "style_summary": "风格概述（一句话）",
    "next_steps": ["接下来要完善的内容1", "接下来要完善的内容2"]
}}

只输出 JSON，不要有其他文字。"""


UNDERSTANDING_SUMMARY_PROMPT = """根据以下信息，生成一份结构化的需求理解报告（Markdown格式）。

## 需求分析
{requirement_analysis}

## 已提取的需求字段
{requirements}

## 需求评估
{assessment}

## 输出要求
生成一份简洁专业的需求理解报告，使用 Markdown 格式，包含以下部分：

### 📌 剧名
（如能推断，否则写"待定"）

### 🎭 题材类型
（题材描述，包括主要风格）

### 👤 主角设定
（主角的基本信息、性格特点、背景故事）

### ⚔️ 核心冲突
（故事的主要矛盾和冲突点）

### 🎯 目标受众
（预期的观众群体）

### 📺 集数规划
（预计集数）

### 🎨 风格基调
（整体风格和情感基调）

### 💡 创作建议
（基于当前信息的一两点专业建议）

要求：
- 使用简洁的专业语言
- 如果某个字段信息不足，写"待确认"
- 总字数控制在 300-500 字
- 使用中文输出"""


# ===== 工具函数 =====

def format_messages_for_summary(messages: List[Dict], max_messages: int = 20) -> str:
    """格式化消息用于摘要生成"""
    if not messages:
        return "暂无对话"

    # 取最近的N条消息
    recent = messages[-max_messages:] if len(messages) > max_messages else messages

    lines = []
    for msg in recent:
        role = "用户" if msg["role"] == "user" else "助手"
        content = msg["content"][:150]  # 限制单条消息长度
        if len(msg["content"]) > 150:
            content += "..."
        lines.append(f"{role}: {content}")

    return "\n".join(lines)


def get_recent_context(messages: List[Dict], rounds: int = 5) -> str:
    """获取最近N轮对话内容"""
    if not messages:
        return "暂无对话"

    # 取最近N轮（每轮2条消息）
    recent_messages = messages[-(rounds * 2):] if len(messages) >= rounds * 2 else messages

    lines = []
    for msg in recent_messages:
        role = "用户" if msg["role"] == "user" else "助手"
        content = msg["content"][:100]
        if len(msg["content"]) > 100:
            content += "..."
        lines.append(f"{role}: {content}")

    return "\n".join(lines)


def format_requirements_for_prompt(requirements: Dict[str, Any]) -> str:
    """格式化需求用于提示词"""
    if not requirements:
        return "暂无已收集的需求"

    field_names = {
        "genre": "题材类型",
        "protagonist": "主角设定",
        "conflict": "核心冲突",
        "target_audience": "目标受众",
        "episodes": "集数",
        "style": "风格基调"
    }

    lines = []
    for key, value in requirements.items():
        if value:
            name = field_names.get(key, key)
            lines.append(f"- {name}: {value}")

    return "\n".join(lines) if lines else "暂无已收集的需求"


def format_assessment_for_prompt(assessment: Optional[Dict]) -> str:
    """格式化需求评估用于提示词"""
    if not assessment:
        return "暂无评估信息"

    field_names = {
        "genre": "题材类型",
        "protagonist": "主角设定",
        "conflict": "核心冲突",
        "target_audience": "目标受众",
        "episodes": "集数",
        "style": "风格基调"
    }

    lines = []
    for key, name in field_names.items():
        field_data = assessment.get(key, {})
        status = field_data.get("status", "empty")
        understanding = field_data.get("understanding", "")
        confidence = field_data.get("confidence", 0)

        status_icon = {"empty": "○", "partial": "◐", "confirmed": "●"}.get(status, "○")
        lines.append(f"- {status_icon} {name}: {understanding or '待确认'} (置信度: {confidence:.0%})")

    return "\n".join(lines)


# ===== 核心类 =====

class UnifiedContextManager:
    """统一上下文管理器"""

    def __init__(self, llm_config: Optional[Dict] = None):
        """
        初始化上下文管理器

        Args:
            llm_config: LLM 配置，如果为 None 则从全局配置获取
        """
        self.llm_config = llm_config

    def _get_llm_service(self):
        """获取 LLM 服务实例"""
        if self.llm_config:
            config = self.llm_config
        else:
            # 使用 nodes.py 中定义的函数，正确获取用户配置
            from app.agents.clarify.nodes import get_current_llm_config
            config = get_current_llm_config()

        llm_config = LLMConfig(
            provider=config.get("provider", "tongyi"),
            api_key=config.get("apiKey"),
            api_base=config.get("apiBase") or None,
            model=config.get("model", "qwen-max"),
            temperature=config.get("temperature", 0.7),
            max_tokens=config.get("maxTokens", 4000)
        )
        return get_llm_service(llm_config)

    def build_unified_context(self, state: ScriptState) -> str:
        """
        构建统一上下文字符串

        包含三层信息：
        1. 对话摘要（历史上下文）
        2. 需求分析（当前理解）
        3. 用户当前问题

        Args:
            state: 当前状态

        Returns:
            格式化的上下文字符串
        """
        messages = state.get("messages", [])
        user_message = ""
        for msg in reversed(messages):
            if msg["role"] == "user":
                user_message = msg["content"]
                break

        return f"""# ═══════════════════════════════════════════════════════════
# 对话摘要（历史上下文）
# ═══════════════════════════════════════════════════════════
{state.get("conversation_summary", "暂无对话历史")}

# ═══════════════════════════════════════════════════════════
# 需求分析（当前理解）
# ═══════════════════════════════════════════════════════════
{state.get("requirement_analysis", "暂无需求分析")}

# ═══════════════════════════════════════════════════════════
# 用户当前问题
# ═══════════════════════════════════════════════════════════
{user_message}"""

    async def update_conversation_summary(self, state: ScriptState) -> str:
        """
        更新对话摘要

        Args:
            state: 当前状态

        Returns:
            新的对话摘要（控制在200字内）
        """
        messages = state.get("messages", [])
        requirements = state.get("requirements", {})

        if len(messages) < 4:
            return state.get("conversation_summary", "")

        try:
            llm_service = self._get_llm_service()

            messages_text = format_messages_for_summary(messages)
            requirements_text = format_requirements_for_prompt(requirements)

            prompt = CONVERSATION_SUMMARY_PROMPT.format(
                messages=messages_text,
                requirements=requirements_text
            )

            summary = await llm_service.generate_with_retry(
                prompt,
                max_tokens=300,  # 约200中文字
                temperature=0.5
            )

            # 确保不超过200字
            summary = summary.strip()
            if len(summary) > 200:
                summary = summary[:197] + "..."

            logger.info(f"📝 [对话摘要] 已更新，长度: {len(summary)}字")
            return summary

        except Exception as e:
            logger.warning(f"更新对话摘要失败: {e}")
            return state.get("conversation_summary", "")

    async def update_requirement_analysis(self, state: ScriptState) -> str:
        """
        更新需求分析

        Args:
            state: 当前状态

        Returns:
            新的需求分析（控制在300字内）
        """
        messages = state.get("messages", [])
        requirements = state.get("requirements", {})
        assessment = state.get("requirement_assessment", {})
        conversation_summary = state.get("conversation_summary", "")

        if len(messages) < 2:
            return state.get("requirement_analysis", "")

        try:
            llm_service = self._get_llm_service()

            recent_context = get_recent_context(messages, rounds=5)
            requirements_text = format_requirements_for_prompt(requirements)
            assessment_text = format_assessment_for_prompt(assessment)

            prompt = REQUIREMENT_ANALYSIS_PROMPT.format(
                conversation_summary=conversation_summary or "暂无对话摘要",
                recent_context=recent_context,
                requirements=requirements_text,
                assessment=assessment_text
            )

            analysis = await llm_service.generate_with_retry(
                prompt,
                max_tokens=400,  # 约300中文字
                temperature=0.5
            )

            # 确保不超过300字
            analysis = analysis.strip()
            if len(analysis) > 300:
                analysis = analysis[:297] + "..."

            logger.info(f"📊 [需求分析] 已更新，长度: {len(analysis)}字")
            return analysis

        except Exception as e:
            logger.warning(f"更新需求分析失败: {e}")
            return state.get("requirement_analysis", "")

    async def update_understanding_display(self, state: ScriptState) -> Dict[str, Any]:
        """
        更新需求理解展示（用于前端右侧边栏）

        Args:
            state: 当前状态

        Returns:
            需求理解展示数据
        """
        requirements = state.get("requirements", {})
        requirement_analysis = state.get("requirement_analysis", "")

        try:
            llm_service = self._get_llm_service()

            requirements_text = format_requirements_for_prompt(requirements)

            prompt = UNDERSTANDING_DISPLAY_PROMPT.format(
                requirement_analysis=requirement_analysis or "暂无需求分析",
                requirements=requirements_text
            )

            response = await llm_service.generate_with_retry(
                prompt,
                max_tokens=500,
                temperature=0.5
            )

            # 解析 JSON
            import json
            import re

            # 尝试提取 JSON
            json_match = re.search(r'\{[\s\S]*\}', response)
            if json_match:
                result = json.loads(json_match.group())
                logger.info(f"📋 [理解展示] 已更新")
                return result

        except Exception as e:
            logger.warning(f"更新理解展示失败: {e}")

        # 返回默认值
        return {
            "title": requirements.get("title", ""),
            "genre_summary": requirements.get("genre", ""),
            "protagonist_summary": requirements.get("protagonist", ""),
            "conflict_summary": requirements.get("conflict", ""),
            "style_summary": requirements.get("style", ""),
            "next_steps": self._generate_next_steps(requirements)
        }

    def _generate_next_steps(self, requirements: Dict[str, Any]) -> List[str]:
        """生成下一步建议"""
        field_descriptions = {
            "genre": "确定题材类型",
            "protagonist": "明确主角设定",
            "conflict": "设计核心冲突",
            "target_audience": "确定目标受众",
            "episodes": "确定集数",
            "style": "确定风格基调"
        }

        missing = []
        for field, desc in field_descriptions.items():
            if field not in requirements or not requirements[field]:
                missing.append(desc)

        return missing[:3]  # 最多返回3个

    async def update_understanding_summary(self, state: ScriptState) -> str:
        """
        更新需求理解报告（Markdown格式，用于弹窗展示）

        Args:
            state: 当前状态

        Returns:
            Markdown 格式的需求理解报告
        """
        requirements = state.get("requirements", {})
        requirement_analysis = state.get("requirement_analysis", "")
        assessment = state.get("requirement_assessment", {})

        if not requirements:
            return ""

        try:
            llm_service = self._get_llm_service()

            requirements_text = format_requirements_for_prompt(requirements)
            assessment_text = format_assessment_for_prompt(assessment)

            prompt = UNDERSTANDING_SUMMARY_PROMPT.format(
                requirement_analysis=requirement_analysis or "暂无需求分析",
                requirements=requirements_text,
                assessment=assessment_text
            )

            summary = await llm_service.generate_with_retry(
                prompt,
                max_tokens=800,
                temperature=0.5
            )

            summary = summary.strip()
            logger.info(f"📄 [理解报告] 已生成，长度: {len(summary)}字")
            return summary

        except Exception as e:
            logger.warning(f"生成理解报告失败: {e}")
            return state.get("understanding_summary", "")

    async def update_all_context(self, state: ScriptState) -> ScriptState:
        """
        统一更新所有上下文（对话摘要 + 需求分析 + 理解展示 + 理解报告）

        在每轮对话完成后调用

        Args:
            state: 当前状态

        Returns:
            更新后的状态
        """
        logger.info("=" * 60)
        logger.info("🔄 [上下文管理] 开始统一更新上下文")
        logger.info("=" * 60)

        messages = state.get("messages", [])

        # 条件1：至少有4条消息（2轮对话）才更新
        if len(messages) >= 4:
            # 更新对话摘要
            conversation_summary = await self.update_conversation_summary(state)
            state["conversation_summary"] = conversation_summary
            logger.info(f"   ✓ 对话摘要已更新 ({len(conversation_summary)}字)")
        else:
            logger.info(f"   - 跳过对话摘要更新（消息数: {len(messages)} < 4）")

        # 条件2：至少有2条消息才更新需求分析
        if len(messages) >= 2:
            # 更新需求分析
            requirement_analysis = await self.update_requirement_analysis(state)
            state["requirement_analysis"] = requirement_analysis
            logger.info(f"   ✓ 需求分析已更新 ({len(requirement_analysis)}字)")

            # 更新理解展示（侧边栏结构化数据）
            understanding_display = await self.update_understanding_display(state)
            state["understanding_display"] = understanding_display
            logger.info("   ✓ 理解展示已更新")

            # V1.3 新增：更新理解报告（Markdown格式，用于弹窗）
            understanding_summary = await self.update_understanding_summary(state)
            state["understanding_summary"] = understanding_summary
            logger.info(f"   ✓ 理解报告已更新 ({len(understanding_summary)}字)")
        else:
            logger.info(f"   - 跳过需求分析更新（消息数: {len(messages)} < 2）")

        # 记录更新位置
        state["last_context_update_index"] = len(messages)

        logger.info("=" * 60)
        logger.info("🔄 [上下文管理] 统一更新完成")
        logger.info("=" * 60)

        return state

    def get_context_for_summary_generator(self, state: ScriptState) -> Dict[str, Any]:
        """
        获取用于需求确认书生成的上下文

        确保需求分析能传递给下一阶段，保证需求一致性

        Args:
            state: 当前状态

        Returns:
            包含需求分析和需求字段的字典
        """
        return {
            "requirement_analysis": state.get("requirement_analysis", ""),
            "conversation_summary": state.get("conversation_summary", ""),
            "requirements": state.get("requirements", {}),
            "requirement_assessment": state.get("requirement_assessment", {}),
            "completeness": state.get("completeness", 0)
        }


# ===== 全局实例 =====

_context_manager: Optional[UnifiedContextManager] = None


def get_context_manager(llm_config: Optional[Dict] = None) -> UnifiedContextManager:
    """获取上下文管理器实例"""
    global _context_manager
    if _context_manager is None or llm_config is not None:
        _context_manager = UnifiedContextManager(llm_config)
    return _context_manager


# ===== 便捷函数 =====

def build_unified_context(state: ScriptState) -> str:
    """构建统一上下文（便捷函数）"""
    return get_context_manager().build_unified_context(state)


async def update_all_context(state: ScriptState) -> ScriptState:
    """统一更新所有上下文（便捷函数）"""
    return await get_context_manager().update_all_context(state)


def get_context_for_next_stage(state: ScriptState) -> Dict[str, Any]:
    """获取用于下一阶段的上下文（便捷函数）"""
    return get_context_manager().get_context_for_summary_generator(state)
