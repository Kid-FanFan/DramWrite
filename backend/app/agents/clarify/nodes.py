"""
需求澄清阶段节点实现

包含节点：
1. intent_analyzer - 意图分析
2. guidance_generator - 引导提问生成
3. options_generator - 建议选项生成
4. summary_generator - 需求确认书生成
"""
import json
import re
import asyncio
from typing import Dict, Any, List, Optional

from loguru import logger

from app.core.state import ScriptState, check_requirement_completeness
from app.services.llm import get_llm_service, LLMConfig, LLMProvider


# ===== 系统提示词（方案C）=====

CLARIFY_SYSTEM_PROMPT = """你是剧作大师的AI策划编辑，一位拥有10年经验的资深短剧策划专家。

你的职责：
1. 通过专业、亲切的对话，帮助用户理清创作思路
2. 精准提取用户的创作需求，转化为结构化数据
3. 提供创意建议，激发用户灵感

对话风格要求：
1. 专业但不失亲切，像资深编辑与作者交流
2. 简洁直接，不要冗余的客套话
3. 每句话都要有价值，推动对话进展
4. 保持前后一致，记住之前确认的所有信息

重要原则：
1. **禁止添加问候语**（如"你好"、"您好"），直接切入正题
2. **禁止重复询问**已确认的信息
3. **保持上下文连贯**，参考之前的对话历史
4. **主动关联**用户提到的所有信息，形成完整画面"""


# ===== 对话摘要功能（方案A）=====

async def generate_conversation_summary(messages: List[Dict], llm_service) -> str:
    """
    生成对话摘要

    当对话历史过长时，生成摘要来保留关键信息

    Args:
        messages: 完整对话历史
        llm_service: LLM服务实例

    Returns:
        对话摘要文本
    """
    if len(messages) <= 6:
        return ""

    # 取前N条消息生成摘要（保留最近2条）
    messages_to_summarize = messages[:-2]

    summary_prompt = f"""请对以下对话生成简洁摘要，保留所有关键信息：

对话记录：
{json.dumps(messages_to_summarize, ensure_ascii=False)}

摘要要求：
1. 总结用户已确认的所有需求
2. 记录重要的背景信息
3. 保持简洁，不超过200字
4. 使用中文输出

请直接输出摘要内容，不要添加任何标题或格式。"""

    try:
        summary = await llm_service.generate(summary_prompt, max_tokens=300)
        return summary.strip()
    except Exception as e:
        logger.warning(f"生成对话摘要失败: {e}")
        return ""


def build_context_with_summary(
    messages: List[Dict],
    summary: str,
    max_recent: int = 4
) -> str:
    """
    构建带摘要的对话上下文

    Args:
        messages: 完整对话历史
        summary: 对话摘要（如果有）
        max_recent: 保留的最近消息数量

    Returns:
        格式化后的上下文字符串
    """
    context_parts = []

    # 添加摘要（如果有）
    if summary:
        context_parts.append(f"【对话摘要】\n{summary}\n")

    # 添加最近的消息
    recent_messages = messages[-max_recent:] if len(messages) > max_recent else messages
    context_parts.append("【最近对话】")

    for msg in recent_messages:
        role = "用户" if msg["role"] == "user" else "助手"
        content = msg["content"][:200]  # 限制单条消息长度
        if len(msg["content"]) > 200:
            content += "..."
        context_parts.append(f"{role}: {content}")

    return "\n".join(context_parts)


def format_messages_for_prompt(messages: List[Dict], max_messages: int = 10) -> str:
    """
    格式化消息列表用于提示词

    智能处理长对话：
    - 消息少时返回全部
    - 消息多时生成摘要+保留最近消息

    Args:
        messages: 消息列表
        max_messages: 最大消息数量

    Returns:
        格式化后的消息字符串
    """
    if len(messages) <= max_messages:
        # 消息不多，返回全部
        formatted = []
        for msg in messages:
            role = "用户" if msg["role"] == "user" else "助手"
            formatted.append(f"{role}: {msg['content']}")
        return "\n".join(formatted)

    # 消息太多，只保留最近N条
    recent = messages[-max_messages:]
    formatted = ["【以下是最近的几轮对话】"]
    for msg in recent:
        role = "用户" if msg["role"] == "user" else "助手"
        content = msg["content"][:300]
        if len(msg["content"]) > 300:
            content += "..."
        formatted.append(f"{role}: {content}")
    return "\n".join(formatted)


def clean_json_string(text: str) -> str:
    """
    清理 JSON 字符串中的常见问题

    Args:
        text: 原始文本

    Returns:
        清理后的文本
    """
    if not text:
        return "{}"

    # 移除 BOM 标记
    text = text.lstrip('\ufeff')

    # 尝试提取 markdown 代码块中的 JSON
    code_block_match = re.search(r'```(?:json)?\s*([\s\S]*?)\s*```', text, re.DOTALL)
    if code_block_match:
        text = code_block_match.group(1).strip()

    # 尝试找到第一个 '{' 和最后一个 '}'
    start = text.find('{')
    end = text.rfind('}')
    if start != -1 and end != -1 and end > start:
        text = text[start:end+1]

    # 清理 JSON 键名中的换行符和多余空格
    # 处理多行键名的情况，如 "\n    \"key\": " -> "\"key\":"

    # 步骤1: 移除键名内部的换行符和空格
    # 匹配模式: "..." 或 '...' 后跟冒号
    def clean_key_with_newlines(match):
        quote = match.group(1)
        key_parts = match.group(2)
        # 合并所有部分并清理空白
        key = ''.join(key_parts.split())
        return f'{quote}{key}{quote}:'

    # 处理跨行的键名
    text = re.sub(r'(["\'])([^"\']*?(?:\n[^"\']*?)*?)(["\'])\s*:', clean_key_with_newlines, text)

    # 步骤2: 移除值之间的多余空白，但保留字符串内容
    # 这一步比较激进，需要小心处理

    return text.strip()


def extract_fields_manually(text: str, field_names: list) -> dict:
    """
    当 JSON 解析失败时，手动提取关键字段

    Args:
        text: 原始文本
        field_names: 要提取的字段名列表

    Returns:
        提取的字段字典
    """
    result = {}
    for field in field_names:
        # 尝试匹配 "field": "value" 或 "field": ["value1", "value2"]
        # 支持多行的情况
        pattern = rf'["\']?\s*{re.escape(field)}\s*["\']?\s*:\s*(?:(?P<str>["\'])(?P<strval>.*?)(?P=str)|(?P<arr>\[[^\]]*\])|(?P<num>\d+)|(?P<bool>true|false)|(?P<null>null))'
        match = re.search(pattern, text, re.DOTALL | re.IGNORECASE)
        if match:
            if match.group('strval') is not None:
                result[field] = match.group('strval').strip()
            elif match.group('arr') is not None:
                arr_text = match.group('arr')
                try:
                    result[field] = json.loads(arr_text)
                except:
                    result[field] = []
            elif match.group('num') is not None:
                result[field] = int(match.group('num'))
            elif match.group('bool') is not None:
                result[field] = match.group('bool').lower() == 'true'
            elif match.group('null') is not None:
                result[field] = None
    return result


def parse_llm_json_response(response: str, expected_fields: list = None) -> tuple[bool, Any]:
    """
    解析 LLM 返回的 JSON 响应

    Args:
        response: LLM 返回的原始文本
        expected_fields: 期望提取的字段名列表（用于手动提取备选）

    Returns:
        (是否成功, 解析结果或错误信息)
    """
    if not response:
        return False, "空响应"

    text = clean_json_string(response)

    try:
        result = json.loads(text)
        return True, result
    except json.JSONDecodeError as e:
        # 尝试更激进的清理：移除所有空白字符后重试
        try:
            compact = re.sub(r'\s+', ' ', text)
            result = json.loads(compact)
            return True, result
        except json.JSONDecodeError:
            # 最后尝试手动提取关键字段
            if expected_fields:
                manual_result = extract_fields_manually(text, expected_fields)
                if manual_result:
                    logger.warning(f"JSON解析失败，使用手动提取: {manual_result}")
                    return True, manual_result
            return False, f"JSON解析失败: {str(e)}, 文本: {text[:200]}..."


# ===== API Key 检查 =====

def get_current_llm_config() -> dict:
    """获取当前 LLM 配置（从 settings API 模块）"""
    # 从 settings API 模块获取当前配置（使用内部函数确保合并默认配置）
    from app.api.v1.endpoints.settings import _get_current_config
    return _get_current_config()


def check_llm_configured() -> tuple[bool, str]:
    """
    检查 LLM 是否已配置

    Returns:
        (是否配置, 错误消息)
    """
    config = get_current_llm_config()
    if not config.get("apiKey"):
        return False, """⚠️ **大模型未配置**

欢迎使用剧作大师！在开始创作之前，请先配置大模型 API Key。

**配置步骤：**
1. 点击右上角的【设置】按钮
2. 选择您要使用的模型提供商（如：通义千问、OpenAI 等）
3. 填写 API Key 和其他必要信息
4. 点击【测试连接】验证配置
5. 保存设置后即可开始创作

**支持的模型：**
- 通义千问（推荐）
- 文心一言
- Kimi
- OpenAI GPT-4
- Claude
- 其他 OpenAI 兼容接口

配置完成后，我将作为您的专属短剧策划编辑，帮助您创作精彩的短剧剧本！"""
    return True, ""


# ===== 意图分析节点（V1.3简化版 - 仅提取需求）=====

INTENT_ANALYZER_PROMPT = """{system_prompt}

# ═══════════════════════════════════════════════════════════
# 统一上下文
# ═══════════════════════════════════════════════════════════
{unified_context}

# 已提取的需求字段
{extracted_requirements}

# ═══════════════════════════════════════════════════════════
# 任务：分析用户意图并提取需求信息
# ═══════════════════════════════════════════════════════════

## Step 1 - 理解用户意图
分析用户最新回复的内容，判断其核心目的：
- ANSWER: 用户回答问题，提供了有效信息
- QUESTION: 用户提出问题，需要解释或引导
- CHAT: 用户进行闲聊或补充说明
- REQUEST_SUGGESTION: 用户请求建议（"给我建议"、"帮我想想"、"没主意"）
- AUTO_FILL: 用户要求自动填充（"随便"、"自动生成"、"你来定"）
- CONFIRM_START: 用户确认开始创作（"开始吧"、"没问题了"）
- MODIFY: 用户修改已有信息（"不对，应该是..."、"改成..."）

## Step 2 - 提取结构化数据
从用户回复中提取所有与需求相关的信息：
- 字段名可能是：genre(题材)、protagonist(主角)、conflict(冲突)、target_audience(受众)、episodes(集数)、style(风格)
- 字段值要简洁明了
- 如果包含多个信息点，全部提取

# ═══════════════════════════════════════════════════════════
# 输出格式 (JSON)
# ═══════════════════════════════════════════════════════════
{{"intent": "意图类型", "extracted_data": {{"字段名": "值"}}, "reasoning": "简短判断理由"}}

只输出JSON，不要其他文字。"""


async def intent_analyzer_node(state: ScriptState) -> ScriptState:
    """
    意图分析节点（V1.3简化版）

    职责：仅分析意图并提取需求信息，不做评估
    评估在响应生成后异步进行
    """
    messages = state.get("messages", [])
    if not messages or messages[-1]["role"] != "user":
        return state

    # 检查 LLM 是否配置
    is_configured, error_message = check_llm_configured()
    if not is_configured:
        messages.append({
            "role": "assistant",
            "content": error_message,
            "type": "error",
            "options": []
        })
        state["messages"] = messages
        state["llm_not_configured"] = True
        return state

    # 获取当前用户消息
    user_message = messages[-1]["content"]
    requirements = state.get("requirements", {})

    # 构建统一上下文
    unified_context = build_unified_context_simple(state)

    # 初始化 LLM 服务
    config = get_current_llm_config()
    llm_config = LLMConfig(
        provider=config.get("provider", "tongyi"),
        api_key=config.get("apiKey"),
        api_base=config.get("apiBase") or None,
        model=config.get("model", "qwen-max"),
        temperature=config.get("temperature", 0.7),
        max_tokens=config.get("maxTokens", 4000)
    )
    llm_service = get_llm_service(llm_config)

    # 构建提示词
    prompt = INTENT_ANALYZER_PROMPT.format(
        system_prompt=CLARIFY_SYSTEM_PROMPT,
        unified_context=unified_context,
        extracted_requirements=json.dumps(requirements, ensure_ascii=False)
    )

    # 调用LLM
    response = await llm_service.generate_with_retry(
        prompt,
        system_prompt=CLARIFY_SYSTEM_PROMPT,
        max_tokens=500
    )

    # 解析JSON响应
    success, result = parse_llm_json_response(response, expected_fields=["intent", "extracted_data"])
    if not success or not isinstance(result, dict):
        # 解析失败，使用默认值
        result = {"intent": "ANSWER", "extracted_data": {}}

    intent = result.get("intent", "ANSWER")
    extracted_data = result.get("extracted_data", {})

    # 更新需求（仅提取，不评估）
    if intent in ["ANSWER", "MODIFY", "CHAT"] and extracted_data:
        requirements.update(extracted_data)
        state["requirements"] = requirements
        # 计算完整度（仅用于路由判断，不做评估）
        state["completeness"] = check_requirement_completeness(requirements)

    # 保存意图类型（用于路由）
    state["last_intent"] = intent
    state["need_options"] = intent == "REQUEST_SUGGESTION"

    # 检测是否确认开始
    if intent == "CONFIRM_START" and state.get("completeness", 0) >= 80:
        state["requirements_locked"] = True

    logger.info(f"🎯 [意图分析] intent={intent}, extracted={list(extracted_data.keys())}")
    return state


def build_unified_context_simple(state: ScriptState) -> str:
    """
    构建简化的统一上下文

    包含：对话摘要 + 需求分析 + 最近对话 + 用户当前输入
    """
    messages = state.get("messages", [])
    conversation_summary = state.get("conversation_summary", "")
    requirement_analysis = state.get("requirement_analysis", "")

    # 获取用户当前输入
    user_message = ""
    for msg in reversed(messages):
        if msg["role"] == "user":
            user_message = msg["content"]
            break

    # 获取最近对话（2轮）
    recent_messages = messages[-4:] if len(messages) > 4 else messages
    recent_text = "\n".join([
        f"{'用户' if m['role'] == 'user' else '助手'}: {m['content'][:100]}{'...' if len(m['content']) > 100 else ''}"
        for m in recent_messages
    ])

    parts = []
    if conversation_summary:
        parts.append(f"【对话摘要】\n{conversation_summary}")
    if requirement_analysis:
        parts.append(f"【需求分析】\n{requirement_analysis}")
    parts.append(f"【最近对话】\n{recent_text}")
    parts.append(f"【用户当前输入】\n{user_message}")

    return "\n\n".join(parts)


# ===== 统一响应生成节点（V1.3新增）=====

RESPONSE_GENERATOR_PROMPT = """{system_prompt}

# ═══════════════════════════════════════════════════════════
# 统一上下文
# ═══════════════════════════════════════════════════════════
{unified_context}

# 已确认的需求信息
{extracted_requirements}

# 待收集的字段
{missing_fields}

# 下一个要询问的字段
{next_field}

字段说明：
- genre: 题材类型（战神、甜宠、都市情感等）
- protagonist: 主角设定（身份、性格、特点）
- conflict: 核心冲突（主线矛盾）
- target_audience: 目标受众（性别、年龄段）
- episodes: 集数（默认80集）
- style: 风格基调（爽文、虐恋、轻松等）

# 任务
根据用户意图和当前状态，生成合适的回复：

1. 如果用户回答了问题：确认理解，继续询问下一个缺失字段
2. 如果用户提问：解答问题，并继续引导
3. 如果用户闲聊：友好回应，自然引导回需求收集

要求：
- 结合已确认信息，体现对需求的理解
- 回复要自然流畅，像资深编辑与作者交流
- 每次只问一个问题，聚焦明确
- **禁止添加问候语**，直接进入正题
- 如果还有缺失字段，末尾加上引导语
- 引导语格式："如果您没有主意，回复'给我建议'我来帮您。"

请直接输出回复文本，不要输出JSON或其他格式。"""


async def response_generator_node(state: ScriptState) -> ScriptState:
    """
    统一响应生成节点（V1.3）

    职责：根据意图和当前状态，生成统一回复
    支持：确认回答、解答问题、闲聊引导、继续询问
    """
    # 检查 LLM 配置
    is_configured, _ = check_llm_configured()
    if not is_configured:
        return state

    # 获取需求信息
    requirements = state.get("requirements", {})
    missing_fields = get_missing_fields(requirements)

    # 确定下一个要询问的字段
    priority = ["genre", "protagonist", "conflict", "target_audience", "episodes", "style"]
    next_field = None
    for field in priority:
        if field in missing_fields:
            next_field = field
            break
    if not next_field and missing_fields:
        next_field = missing_fields[0]

    # 构建统一上下文
    unified_context = build_unified_context_simple(state)

    # 构建提示词
    prompt = RESPONSE_GENERATOR_PROMPT.format(
        system_prompt=CLARIFY_SYSTEM_PROMPT,
        unified_context=unified_context,
        extracted_requirements=json.dumps(requirements, ensure_ascii=False),
        missing_fields=json.dumps(missing_fields, ensure_ascii=False),
        next_field=next_field or "无"
    )

    # 初始化 LLM 服务
    config = get_current_llm_config()
    llm_config = LLMConfig(
        provider=config.get("provider", "tongyi"),
        api_key=config.get("apiKey"),
        api_base=config.get("apiBase") or None,
        model=config.get("model", "qwen-max"),
        temperature=config.get("temperature", 0.7),
        max_tokens=config.get("maxTokens", 4000)
    )
    llm_service = get_llm_service(llm_config)

    # 生成回复
    response_text = await llm_service.generate_with_retry(
        prompt,
        system_prompt=CLARIFY_SYSTEM_PROMPT,
        max_tokens=500
    )
    response_text = response_text.strip()

    # 确保引导语
    if missing_fields and "如果您没有主意" not in response_text:
        response_text += " 如果您没有主意，回复'给我建议'我来帮您。"

    # 更新状态
    message = {
        "role": "assistant",
        "content": response_text,
        "type": "text"
    }
    messages = state.get("messages", [])
    messages.append(message)
    state["messages"] = messages
    state["pending_field"] = next_field

    logger.info(f"💬 [响应生成] 已生成回复，长度: {len(response_text)}字")
    return state


# ===== 流式统一响应生成器 =====

STREAMING_RESPONSE_PROMPT = """{system_prompt}

# ═══════════════════════════════════════════════════════════
# 统一上下文
# ═══════════════════════════════════════════════════════════
{unified_context}

# 已确认的需求信息
{extracted_requirements}

# 待收集的字段
{missing_fields}

# 下一个要询问的字段
{next_field}

# 任务
根据用户意图和当前状态，生成自然流畅的回复：
1. 确认用户回答（如果有）
2. 继续引导下一个缺失字段
3. 语气专业亲切，**禁止问候语**

请直接输出回复文本。"""


async def streaming_response_generator(
    state: ScriptState,
    on_chunk: callable
) -> ScriptState:
    """
    流式统一响应生成器

    实时生成响应并推送
    """
    is_configured, _ = check_llm_configured()
    if not is_configured:
        return state

    requirements = state.get("requirements", {})
    missing_fields = get_missing_fields(requirements)

    priority = ["genre", "protagonist", "conflict", "target_audience", "episodes", "style"]
    next_field = None
    for field in priority:
        if field in missing_fields:
            next_field = field
            break
    if not next_field and missing_fields:
        next_field = missing_fields[0]

    unified_context = build_unified_context_simple(state)

    prompt = STREAMING_RESPONSE_PROMPT.format(
        system_prompt=CLARIFY_SYSTEM_PROMPT,
        unified_context=unified_context,
        extracted_requirements=json.dumps(requirements, ensure_ascii=False),
        missing_fields=json.dumps(missing_fields, ensure_ascii=False),
        next_field=next_field or "无"
    )

    config = get_current_llm_config()
    llm_config = LLMConfig(
        provider=config.get("provider", "tongyi"),
        api_key=config.get("apiKey"),
        api_base=config.get("apiBase") or None,
        model=config.get("model", "qwen-max"),
        temperature=config.get("temperature", 0.7),
        max_tokens=config.get("maxTokens", 4000)
    )
    llm_service = get_llm_service(llm_config)

    full_content = ""
    try:
        async for chunk in llm_service.generate_stream(
            prompt,
            system_prompt=CLARIFY_SYSTEM_PROMPT,
            max_tokens=500
        ):
            full_content += chunk
            await on_chunk(chunk, full_content, False)

        # 确保引导语
        if missing_fields and "如果您没有主意" not in full_content:
            extra = " 如果您没有主意，回复'给我建议'我来帮您。"
            full_content += extra
            await on_chunk(extra, full_content, True)
        else:
            await on_chunk("", full_content, True)

        # 更新状态
        message = {
            "role": "assistant",
            "content": full_content,
            "type": "text"
        }
        messages = state.get("messages", [])
        messages.append(message)
        state["messages"] = messages
        state["pending_field"] = next_field

        logger.info(f"💬 [流式响应] 生成完成，长度: {len(full_content)}字")

    except Exception as e:
        logger.error(f"流式响应生成失败: {e}")
        raise

    return state


def get_missing_fields(requirements: Dict[str, Any]) -> List[str]:
    """获取缺失的关键字段"""
    required_fields = ["genre", "protagonist", "conflict", "target_audience", "episodes", "style"]
    return [f for f in required_fields if f not in requirements or not requirements[f]]


# ===== V1.3 异步评估函数 =====

ASSESS_PROGRESS_PROMPT = """{system_prompt}

# ═══════════════════════════════════════════════════════════
# 统一上下文（包含本轮回复）
# ═══════════════════════════════════════════════════════════
{unified_context}

# 已提取的需求字段
{extracted_requirements}

# ═══════════════════════════════════════════════════════════
# 任务：评估需求收集进度
# ═══════════════════════════════════════════════════════════

对每个需求字段进行评估，输出 JSON 格式：
{{
    "completeness": 0-100的总分,
    "assessment": {{
        "genre": {{"status": "empty/partial/confirmed", "understanding": "当前理解的描述", "confidence": 0.0-1.0, "suggestion": "可选的改进建议"}},
        "protagonist": {{...}},
        "conflict": {{...}},
        "target_audience": {{...}},
        "episodes": {{...}},
        "style": {{...}}
    }}
}}

字段状态说明：
- empty: 完全没有信息
- partial: 有部分信息但不完整
- confirmed: 信息已确认且完整

评分规则：
- genre (题材): 20分
- protagonist (主角): 20分
- conflict (冲突): 20分
- target_audience (受众): 15分
- episodes (集数): 15分
- style (风格): 10分

只输出JSON，不要其他文字。"""


async def assess_progress_after_response(state: ScriptState) -> Dict[str, Any]:
    """
    V1.3 异步评估函数

    在回复生成完成后异步执行，评估需求收集进度并返回结果
    用于通过 assessment_update SSE 事件推送到前端

    Args:
        state: 当前状态（已包含本轮回复）

    Returns:
        包含 completeness 和 requirement_assessment 的字典
    """
    logger.info("📊 [异步评估] 开始评估需求收集进度...")

    # 检查 LLM 配置
    is_configured, _ = check_llm_configured()
    if not is_configured:
        return {
            "completeness": state.get("completeness", 0),
            "requirement_assessment": None
        }

    requirements = state.get("requirements", {})

    # 构建统一上下文（包含本轮回复）
    unified_context = build_unified_context_simple(state)

    # 初始化 LLM 服务
    config = get_current_llm_config()
    llm_config = LLMConfig(
        provider=config.get("provider", "tongyi"),
        api_key=config.get("apiKey"),
        api_base=config.get("apiBase") or None,
        model=config.get("model", "qwen-max"),
        temperature=config.get("temperature", 0.5),  # 评估用较低温度
        max_tokens=config.get("maxTokens", 4000)
    )
    llm_service = get_llm_service(llm_config)

    # 构建提示词
    prompt = ASSESS_PROGRESS_PROMPT.format(
        system_prompt=CLARIFY_SYSTEM_PROMPT,
        unified_context=unified_context,
        extracted_requirements=json.dumps(requirements, ensure_ascii=False)
    )

    try:
        # 调用 LLM 进行评估
        response = await llm_service.generate_with_retry(
            prompt,
            system_prompt=CLARIFY_SYSTEM_PROMPT,
            max_tokens=800
        )

        # 解析 JSON 响应
        success, result = parse_llm_json_response(
            response,
            expected_fields=["completeness", "assessment"]
        )

        if success and isinstance(result, dict):
            completeness = result.get("completeness", 0)
            assessment = result.get("assessment", {})

            logger.info(f"📊 [异步评估] 完成，完整度: {completeness}%")

            return {
                "completeness": completeness,
                "requirement_assessment": assessment
            }
        else:
            # 解析失败，使用基础计算
            logger.warning(f"📊 [异步评估] JSON解析失败，使用基础计算")
            return {
                "completeness": check_requirement_completeness(requirements),
                "requirement_assessment": None
            }

    except Exception as e:
        logger.error(f"📊 [异步评估] 评估失败: {e}")
        return {
            "completeness": check_requirement_completeness(requirements),
            "requirement_assessment": None
        }


async def guidance_generator_node(state: ScriptState) -> ScriptState:
    """
    引导提问节点

    使用 LLM 根据当前需求状态生成下一个引导问题
    """
    # 检查 LLM 是否已配置，未配置则跳过
    is_configured, _ = check_llm_configured()
    if not is_configured:
        return state

    # 防御性编程：确保 state 是字典类型
    if not isinstance(state, dict):
        logger.error(f"guidance_generator_node: state 不是字典类型: {type(state)}")
        return {}

    # 防御性编程：清理 requirements 中的异常键
    raw_requirements = state.get("requirements", {})
    if isinstance(raw_requirements, dict):
        requirements = {k.strip(): v for k, v in raw_requirements.items() if isinstance(k, str)}
    else:
        requirements = {}

    missing_fields = get_missing_fields(requirements)

    if not missing_fields:
        return state

    # 确定下一个要询问的字段
    priority = ["genre", "protagonist", "conflict", "target_audience", "episodes", "style"]
    next_field = None
    for field in priority:
        if field in missing_fields:
            next_field = field
            break
    if not next_field:
        next_field = missing_fields[0]

    # 防御性编程：清理 missing_fields
    if isinstance(missing_fields, list):
        missing_fields = [f.strip() if isinstance(f, str) else str(f) for f in missing_fields]

    # 获取对话历史并格式化上下文
    messages = state.get("messages", [])
    context = format_messages_for_prompt(messages, max_messages=8)

    # 使用 LLM 生成引导问题
    prompt = GUIDANCE_GENERATOR_PROMPT.format(
        system_prompt=CLARIFY_SYSTEM_PROMPT,
        context=context,
        extracted_requirements=json.dumps(requirements, ensure_ascii=False),
        missing_fields=json.dumps(missing_fields, ensure_ascii=False),
        next_field=next_field
    )

    config = get_current_llm_config()
    llm_config = LLMConfig(
        provider=config.get("provider", "tongyi"),
        api_key=config.get("apiKey"),
        api_base=config.get("apiBase") or None,
        model=config.get("model", "qwen-max"),
        temperature=config.get("temperature", 0.7),
        max_tokens=config.get("maxTokens", 4000)
    )
    llm_service = get_llm_service(llm_config)
    response = await llm_service.generate_with_retry(
        prompt,
        system_prompt=CLARIFY_SYSTEM_PROMPT,
        max_tokens=500
    )

    # 解析 LLM 响应
    success, result = parse_llm_json_response(response, expected_fields=["question_text", "internal_options_cache", "next_field_to_ask"])
    if success and isinstance(result, dict):
        question_text = result.get("question_text", f"请告诉我关于「{next_field}」的信息。")
        # 缓存内部选项供用户请求建议时使用
        state["_internal_options_cache"] = result.get("internal_options_cache", [])
    else:
        # 如果返回不是JSON，直接使用返回文本
        question_text = response.strip()
        state["_internal_options_cache"] = []
        # 记录解析失败日志
        logger.warning(f"guidance_generator_node JSON解析失败，使用原始文本。错误: {result}")
        logger.warning(f"原始响应: {response[:500]}")

    # 确保引导语在问题中
    if "如果您没有主意" not in question_text:
        question_text += " 如果您没有主意，回复'给我建议'我来帮您。"

    message = {
        "role": "assistant",
        "content": question_text,
        "type": "text"
    }

    # 获取 messages 列表并追加新消息
    messages = state.get("messages", [])
    messages.append(message)
    state["messages"] = messages
    state["pending_field"] = next_field

    return state


# ===== 选项生成节点 =====

OPTIONS_GENERATOR_PROMPT = """{system_prompt}

# 当前对话上下文
{context}

# 当前询问的字段
{pending_field}

# 已确认的需求信息
{extracted_requirements}

# 任务
针对当前字段，提供3个经典的、高分的短剧设定建议。

要求：
1. 选项要具体、有吸引力，符合竖屏短剧的"爽点"逻辑
2. 选项之间要有明显区别
3. 结合已确认的需求，提供关联性强的建议
4. **禁止添加问候语或开场白**，直接输出选项

# 输出格式 (JSON)
{{"options": [{{"id": 1, "title": "选项名称", "description": "一句话亮点描述"}}, {{"id": 2, "title": "选项名称", "description": "一句话亮点描述"}}, {{"id": 3, "title": "选项名称", "description": "一句话亮点描述"}}]}}

只输出JSON，不要有其他文字。"""


async def options_generator_node(state: ScriptState) -> ScriptState:
    """
    选项生成节点

    使用 LLM 为用户生成个性化的建议选项
    """
    pending_field = state.get("pending_field", "")
    requirements = state.get("requirements", {})

    # 获取对话历史并格式化上下文
    messages = state.get("messages", [])
    context = format_messages_for_prompt(messages, max_messages=6)

    # 使用 LLM 生成个性化选项
    prompt = OPTIONS_GENERATOR_PROMPT.format(
        system_prompt=CLARIFY_SYSTEM_PROMPT,
        context=context,
        pending_field=pending_field,
        extracted_requirements=json.dumps(requirements, ensure_ascii=False)
    )

    config = get_current_llm_config()
    llm_config = LLMConfig(
        provider=config.get("provider", "tongyi"),
        api_key=config.get("apiKey"),
        api_base=config.get("apiBase") or None,
        model=config.get("model", "qwen-max"),
        temperature=config.get("temperature", 0.7),
        max_tokens=config.get("maxTokens", 4000)
    )
    llm_service = get_llm_service(llm_config)
    response = await llm_service.generate_with_retry(
        prompt,
        system_prompt=CLARIFY_SYSTEM_PROMPT,
        max_tokens=800
    )

    # 解析 LLM 响应
    success, result = parse_llm_json_response(response, expected_fields=["options"])
    if not success or not isinstance(result, dict):
        raise ValueError(f"选项生成失败 - JSON解析错误: {result}")

    options = result.get("options", [])
    if not options or len(options) < 3:
        raise ValueError(f"LLM 返回选项不足: {options}")

    # 构建回复文本
    response_text = f"关于「{pending_field}」，我为您准备了以下建议：\n\n"
    for opt in options:
        response_text += f"{opt['id']}. **{opt['title']}** - {opt['description']}\n"
    response_text += "\n请回复数字选择，或直接告诉我您的想法。"

    # 添加系统消息
    message = {
        "role": "assistant",
        "content": response_text,
        "type": "option",
        "options": options
    }

    state["messages"].append(message)
    state["need_options"] = False

    return state


# ===== 需求确认书节点 =====

SUMMARY_GENERATOR_PROMPT = """{system_prompt}

# 已收集的需求信息
{requirements}

# 任务
生成一份需求确认书，以友好的方式向用户确认所有需求。

确认书结构：
1. 项目概述（一句话概括）
2. 已确认的需求项（分点列出）
3. 下一步说明（将自动生成什么内容）
4. 确认引导（请用户确认或提出修改）

要求：
1. **禁止添加问候语**（如"你好"、"您好"）
2. **直接开始**项目概述部分
3. 使用Markdown格式，层次清晰
4. 语言简洁专业

直接输出确认书文本，不要任何开场白。"""


# ===== 需求字段完整性校验（V1.1新增）=====

REQUIRED_FIELDS = {
    "genre": "题材类型",
    "protagonist": "主角设定",
    "conflict": "核心冲突",
    "target_audience": "目标受众",
    "episodes": "集数",
    "style": "风格基调"
}


def validate_requirements_completeness(requirements: Dict[str, Any]) -> tuple:
    """
    校验需求字段完整性

    Args:
        requirements: 需求字典

    Returns:
        (是否完整, 缺失字段列表, 缺失字段描述列表)
    """
    missing_fields = []
    missing_descriptions = []

    for field, desc in REQUIRED_FIELDS.items():
        if field not in requirements or not requirements[field]:
            missing_fields.append(field)
            missing_descriptions.append(desc)

    return len(missing_fields) == 0, missing_fields, missing_descriptions


def extract_key_requirement_messages(messages: List[Dict], keywords: List[str] = None) -> str:
    """
    提取包含需求关键词的关键对话片段

    Args:
        messages: 对话历史
        keywords: 关键词列表

    Returns:
        关键对话片段文本
    """
    if keywords is None:
        keywords = ["题材", "主角", "冲突", "受众", "集数", "风格", "设定", "剧情", "人物", "主题"]

    key_fragments = []
    for msg in messages:
        content = msg.get("content", "")
        if any(kw in content for kw in keywords):
            role = "用户" if msg["role"] == "user" else "助手"
            # 截取相关片段（关键词前后50字）
            for kw in keywords:
                if kw in content:
                    idx = content.find(kw)
                    start = max(0, idx - 50)
                    end = min(len(content), idx + 100)
                    fragment = content[start:end]
                    key_fragments.append(f"{role}: ...{fragment}...")
                    break  # 每条消息只提取一次

    return "\n".join(key_fragments[-10:])  # 最多保留10条关键片段


def merge_context_layers(
    core_requirements: Dict[str, Any],
    key_messages: str,
    summary: str
) -> str:
    """
    合并三层上下文信息

    Args:
        core_requirements: 核心需求层（最可靠）
        key_messages: 关键对话层
        summary: 摘要层

    Returns:
        合并后的上下文文本
    """
    parts = []

    # 第一层：核心需求（最可靠）
    if core_requirements:
        parts.append("【已确认的核心需求】")
        for key, value in core_requirements.items():
            if value:
                parts.append(f"- {REQUIRED_FIELDS.get(key, key)}: {value}")

    # 第二层：关键对话
    if key_messages:
        parts.append("\n【关键对话片段】")
        parts.append(key_messages)

    # 第三层：摘要
    if summary:
        parts.append("\n【对话摘要】")
        parts.append(summary)

    return "\n".join(parts)


# ===== 需求确认书结构化生成节点（V1.1优化版 - 三层记忆策略）=====

REQUIREMENT_CONFIRMATION_PROMPT = """{system_prompt}

# ═══════════════════════════════════════════════════════════
# 重要：必须保留以下所有已确认的核心需求，不得遗漏或修改！
# ═══════════════════════════════════════════════════════════

{core_requirements}

# 补充上下文（用于理解用户意图，请参考但不要覆盖核心需求）
{conversation_context}

# 任务
你是一位资深的短剧策划编辑，现在需要根据以上信息，生成一份专业的《需求确认书》。

## 核心原则
1. **信息保留**：核心需求层的所有字段必须100%保留，不得遗漏
2. **合理补充**：根据上下文补充合理的细节，但不得偏离用户原始意图
3. **专业表述**：使用专业的短剧行业术语进行整理
4. **完整性**：任何字段都不得留空，如信息不足则根据上下文合理推测

## 输出格式 (JSON)
请严格按照以下格式输出（不要输出其他文字）：
{{
    "title": "优化后的剧名（响亮好记）",
    "genre": "题材类型（如都市情感、战神、甜宠等）",
    "episodes": "集数（数字）",
    "target_audience": "目标受众（性别、年龄段）",
    "protagonist": {{
        "name": "主角姓名",
        "identity": "主角身份",
        "personality": "主角性格特点",
        "background": "主角背景故事",
        "goal": "主角目标",
        "golden_finger": "金手指/特殊能力（如有）"
    }},
    "supporting_roles": [
        {{
            "name": "配角姓名",
            "role_type": "与主角关系（如反派、爱情线、导师等）",
            "description": "简要描述"
        }}
    ],
    "core_conflict": "核心冲突（主线矛盾）",
    "plot_summary": "剧情概要（300-500字，包含起承转合）",
    "style": "风格基调（爽文、虐恋、轻松等）",
    "selling_points": ["卖点1", "卖点2", "卖点3"],
    "special_requirements": "特殊要求（如必须包含的元素、禁忌等）"
}}

## 输出前检查清单
- [ ] 核心需求的所有字段都已包含
- [ ] 剧名已优化（不是用户的原始表述）
- [ ] 剧情概要完整（包含起承转合）
- [ ] JSON格式正确"""


async def generate_requirement_confirmation(
    messages: List[Dict[str, Any]],
    llm_service,
    core_requirements: Dict[str, Any] = None
) -> Dict[str, Any]:
    """
    生成优化后的需求确认书（V1.1 三层记忆策略）

    基于三层记忆策略，确保信息不丢失：
    1. 核心需求层：从 requirements 字典直接获取（最可靠）
    2. 关键对话层：提取包含需求关键词的对话片段
    3. 摘要层：生成对话摘要作为补充

    Args:
        messages: 完整对话历史
        llm_service: LLM服务实例
        core_requirements: 已提取的核心需求（可选，如提供则优先使用）

    Returns:
        结构化的需求确认书数据
    """
    # 第一层：核心需求（最可靠）
    if core_requirements is None:
        core_requirements = {}
    core_req_text = "\n".join([
        f"- {REQUIRED_FIELDS.get(k, k)}: {v}"
        for k, v in core_requirements.items()
        if v
    ]) or "暂无已确认的核心需求"

    # 第二层：关键对话片段
    key_messages = extract_key_requirement_messages(messages)

    # 第三层：对话摘要（用于补充理解）
    summary = ""
    if len(messages) > 6:
        summary = await generate_conversation_summary(messages, llm_service)

    # 合并三层上下文
    conversation_context = merge_context_layers({}, key_messages, summary)

    prompt = REQUIREMENT_CONFIRMATION_PROMPT.format(
        system_prompt=CLARIFY_SYSTEM_PROMPT,
        core_requirements=core_req_text,
        conversation_context=conversation_context
    )

    try:
        response = await llm_service.generate_with_retry(
            prompt,
            system_prompt=CLARIFY_SYSTEM_PROMPT,
            max_tokens=2500,
            temperature=0.7
        )

        # 解析JSON响应
        success, result = parse_llm_json_response(response, expected_fields=[
            "title", "genre", "episodes", "target_audience", "protagonist",
            "core_conflict", "plot_summary", "style"
        ])

        if success and isinstance(result, dict):
            # 校验完整性：确保核心需求字段都被包含
            if core_requirements:
                # 如果原始需求中有但结果中没有，补充回去
                for key, value in core_requirements.items():
                    if value and key not in result:
                        logger.warning(f"需求确认书缺少字段 {key}，从核心需求补充")
                        result[key] = value

            logger.info(f"需求确认书生成成功，包含字段: {list(result.keys())}")
            return result
        else:
            logger.warning(f"需求确认书解析失败: {result}")
            # 返回基本结构，并尝试保留核心需求
            fallback = {
                "title": core_requirements.get("title", "未命名短剧"),
                "genre": core_requirements.get("genre", "待补充"),
                "episodes": core_requirements.get("episodes", "80"),
                "target_audience": core_requirements.get("target_audience", "待补充"),
                "protagonist": {"name": "", "identity": "", "personality": "", "background": "", "goal": "", "golden_finger": ""},
                "core_conflict": core_requirements.get("conflict", "待补充"),
                "plot_summary": "对话历史未能正确解析，请返回需求澄清阶段完善信息。",
                "style": core_requirements.get("style", "待补充"),
                "selling_points": [],
                "supporting_roles": [],
                "special_requirements": ""
            }
            return fallback
    except Exception as e:
        logger.error(f"生成需求确认书失败: {e}")
        raise


async def summary_generator_node(state: ScriptState) -> ScriptState:
    """
    需求确认书节点

    使用 LLM 生成需求确认书供用户确认
    """
    requirements = state.get("requirements", {})

    # 使用 LLM 生成需求确认书
    prompt = SUMMARY_GENERATOR_PROMPT.format(
        system_prompt=CLARIFY_SYSTEM_PROMPT,
        requirements=json.dumps(requirements, ensure_ascii=False)
    )

    config = get_current_llm_config()
    llm_config = LLMConfig(
        provider=config.get("provider", "tongyi"),
        api_key=config.get("apiKey"),
        api_base=config.get("apiBase") or None,
        model=config.get("model", "qwen-max"),
        temperature=config.get("temperature", 0.7),
        max_tokens=config.get("maxTokens", 4000)
    )
    llm_service = get_llm_service(llm_config)
    summary = await llm_service.generate_with_retry(
        prompt,
        system_prompt=CLARIFY_SYSTEM_PROMPT,
        max_tokens=1500
    )

    # 添加系统消息
    message = {
        "role": "assistant",
        "content": summary.strip(),
        "type": "summary"
    }

    state["messages"].append(message)
    state["showed_summary"] = True

    return state


# ===== 流式引导生成器（真正实时流式）=====

STREAMING_GUIDANCE_PROMPT = """{system_prompt}

# 当前对话上下文
{context}

# 已确认的需求信息
{extracted_requirements}

# 待收集的字段
{missing_fields}

# 当前需要询问的字段
当前字段：{next_field}

字段说明：
- genre: 题材类型（如战神、甜宠、都市情感等）
- protagonist: 主角设定（身份、性格、特点）
- conflict: 核心冲突（主线矛盾、主要挑战）
- target_audience: 目标受众（性别、年龄段）
- episodes: 集数（默认80集）
- style: 风格基调（爽文、虐恋、轻松等）

# 任务
针对当前字段，生成一个引导问题。要求：
1. 结合已确认的信息，体现你对需求的理解
2. 问题要具体、有针对性
3. **禁止添加问候语和开场白**，直接问问题
4. 语气专业亲切，像资深编辑与作者交流
5. 问题末尾必须加上："如果您没有主意，回复'给我建议'我来帮您。"

请直接输出问题文本，不要输出JSON格式，不要输出字段名，只输出自然语言的问题。"""


async def streaming_guidance_generator(
    state: ScriptState,
    on_chunk: callable
) -> ScriptState:
    """
    流式引导生成器

    真正实时的流式生成，LLM每生成一个token就立即发送给前端

    Args:
        state: 当前状态
        on_chunk: 回调函数，用于发送每个文本片段

    Returns:
        更新后的状态
    """
    # 检查 LLM 是否已配置
    is_configured, _ = check_llm_configured()
    if not is_configured:
        return state

    # 防御性编程
    if not isinstance(state, dict):
        logger.error(f"streaming_guidance_generator: state 不是字典类型")
        return state

    # 获取需求信息
    raw_requirements = state.get("requirements", {})
    requirements = {k.strip(): v for k, v in raw_requirements.items() if isinstance(k, str)} if isinstance(raw_requirements, dict) else {}

    missing_fields = get_missing_fields(requirements)

    if not missing_fields:
        return state

    # 确定下一个字段
    priority = ["genre", "protagonist", "conflict", "target_audience", "episodes", "style"]
    next_field = None
    for field in priority:
        if field in missing_fields:
            next_field = field
            break
    if not next_field:
        next_field = missing_fields[0]

    # 清理字段名
    missing_fields = [f.strip() if isinstance(f, str) else str(f) for f in missing_fields]

    # 获取对话历史
    messages = state.get("messages", [])
    context = format_messages_for_prompt(messages, max_messages=8)

    # 构建提示词
    prompt = STREAMING_GUIDANCE_PROMPT.format(
        system_prompt=CLARIFY_SYSTEM_PROMPT,
        context=context,
        extracted_requirements=json.dumps(requirements, ensure_ascii=False),
        missing_fields=json.dumps(missing_fields, ensure_ascii=False),
        next_field=next_field
    )

    # 初始化 LLM 服务
    config = get_current_llm_config()
    llm_config = LLMConfig(
        provider=config.get("provider", "tongyi"),
        api_key=config.get("apiKey"),
        api_base=config.get("apiBase") or None,
        model=config.get("model", "qwen-max"),
        temperature=config.get("temperature", 0.7),
        max_tokens=config.get("maxTokens", 4000)
    )
    llm_service = get_llm_service(llm_config)

    # 流式生成
    full_content = ""
    try:
        async for chunk in llm_service.generate_stream(
            prompt,
            system_prompt=CLARIFY_SYSTEM_PROMPT,
            max_tokens=500
        ):
            full_content += chunk
            # 立即发送给前端
            await on_chunk(chunk, full_content, False)

        # 确保引导语在问题中
        if "如果您没有主意" not in full_content:
            extra = " 如果您没有主意，回复'给我建议'我来帮您。"
            full_content += extra
            await on_chunk(extra, full_content, True)
        else:
            await on_chunk("", full_content, True)

        # 更新状态
        message = {
            "role": "assistant",
            "content": full_content,
            "type": "text"
        }
        messages.append(message)
        state["messages"] = messages
        state["pending_field"] = next_field

    except Exception as e:
        logger.error(f"流式生成失败: {e}")
        raise

    return state


# ===== 流式选项生成器 =====

STREAMING_OPTIONS_PROMPT = """{system_prompt}

# 当前对话上下文
{context}

# 当前询问的字段
{pending_field}

# 已确认的需求信息
{extracted_requirements}

# 任务
针对当前字段，提供3个经典的、高分的短剧设定建议。

要求：
1. 选项要具体、有吸引力，符合竖屏短剧的"爽点"逻辑
2. 选项之间要有明显区别
3. 结合已确认的需求，提供关联性强的建议
4. **禁止添加问候语或开场白**

请直接输出选项，格式如下：
1. **选项标题** - 一句话亮点描述
2. **选项标题** - 一句话亮点描述
3. **选项标题** - 一句话亮点描述

最后加上："请回复数字选择，或直接告诉我您的想法。"""


async def streaming_options_generator(
    state: ScriptState,
    on_chunk: callable
) -> ScriptState:
    """
    流式选项生成器

    真正实时的流式生成建议选项
    """
    pending_field = state.get("pending_field", "")
    requirements = state.get("requirements", {})

    # 获取对话历史
    messages = state.get("messages", [])
    context = format_messages_for_prompt(messages, max_messages=6)

    # 构建提示词
    prompt = STREAMING_OPTIONS_PROMPT.format(
        system_prompt=CLARIFY_SYSTEM_PROMPT,
        context=context,
        pending_field=pending_field,
        extracted_requirements=json.dumps(requirements, ensure_ascii=False)
    )

    # 初始化 LLM 服务
    config = get_current_llm_config()
    llm_config = LLMConfig(
        provider=config.get("provider", "tongyi"),
        api_key=config.get("apiKey"),
        api_base=config.get("apiBase") or None,
        model=config.get("model", "qwen-max"),
        temperature=config.get("temperature", 0.7),
        max_tokens=config.get("maxTokens", 4000)
    )
    llm_service = get_llm_service(llm_config)

    # 流式生成
    full_content = ""
    try:
        async for chunk in llm_service.generate_stream(
            prompt,
            system_prompt=CLARIFY_SYSTEM_PROMPT,
            max_tokens=800
        ):
            full_content += chunk
            await on_chunk(chunk, full_content, False)

        await on_chunk("", full_content, True)

        # 解析选项（简化版，从文本中提取）
        options = parse_options_from_text(full_content)

        # 更新状态
        message = {
            "role": "assistant",
            "content": full_content,
            "type": "option",
            "options": options
        }
        messages = state.get("messages", [])
        messages.append(message)
        state["messages"] = messages
        state["need_options"] = False

    except Exception as e:
        logger.error(f"流式选项生成失败: {e}")
        raise

    return state


def parse_options_from_text(text: str) -> list:
    """
    从文本中解析选项

    简单解析，提取编号项作为选项
    """
    options = []
    lines = text.split('\n')

    for line in lines:
        line = line.strip()
        # 匹配 1. **标题** - 描述 或 1. 标题 - 描述
        match = re.match(r'^(\d+)\.\s*\*\*(.+?)\*\*\s*[-–]\s*(.+)$', line)
        if not match:
            match = re.match(r'^(\d+)\.\s*(.+?)\s*[-–]\s*(.+)$', line)

        if match:
            options.append({
                "id": int(match.group(1)),
                "title": match.group(2).strip(),
                "description": match.group(3).strip()
            })

    # 如果解析失败，返回默认选项
    if len(options) < 3:
        return [
            {"id": 1, "title": "选项一", "description": "基于您需求的经典设定"},
            {"id": 2, "title": "选项二", "description": "创新但稳妥的设定"},
            {"id": 3, "title": "选项三", "description": "大胆突破的设定"}
        ]

    return options
