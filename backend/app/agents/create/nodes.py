"""
剧本创作阶段节点实现

包含节点：
1. synopsis_creator - 故事梗概生成
2. character_creator - 人物小传生成
3. outline_creator - 分集大纲生成
4. script_writer - 剧本正文生成
5. quality_checker - 质量检查
"""
import json
import re
from typing import Dict, Any, List

from app.core.state import ScriptState, EpisodeOutline, EpisodeScript
from app.services.llm import get_llm_service
from loguru import logger


# ===== 字段标准化工具函数 =====

def _normalize_character_fields(char: Dict) -> Dict:
    """
    标准化人物字段名，确保使用snake_case

    处理LLM可能返回的各种字段名变体
    """
    # 字段名映射：可能的变体 -> 标准名称
    field_mappings = {
        # memory_point 的各种变体
        'memory_point': 'memory_point',
        'memoryPoint': 'memory_point',
        'memorypoint': 'memory_point',
        'memory_point特征': 'memory_point',
        '记忆点': 'memory_point',
        # relationships 的各种变体
        'relationships': 'relationships',
        'relationship': 'relationships',
        '人物关系': 'relationships',
    }
    # logger.info(f"正在标准化{char["name"]}的人物字段，原始字段: {list(char.keys())}")
    normalized = {}
    for key, value in char.items():
        # 转换为标准名称
        standard_key = field_mappings.get(key, key)
        # logger.info(f"标准化字段 {key} -> {standard_key}")
        normalized[standard_key] = value

    return normalized


# ===== 故事梗概生成节点 =====

SYNOPSIS_CREATOR_PROMPT = """你是一位擅长构建宏大世界观与紧凑剧情的资深编剧。

# 剧本需求
题材：{genre}
主角设定：{protagonist}
核心冲突：{conflict}
风格基调：{style}
目标受众：{target_audience}
总集数：{episodes}集

# 约束条件
1. 字数：300-2000字
2. 必须包含完整的起承转合
3. 必须符合竖屏短剧节奏：开篇即高潮，前3集要有强冲突
4. 设置明显的情绪钩子（爽感或虐点）
5. 内容必须原创，严禁抄袭
6. 符合社会主义核心价值观，拒绝低俗内容

# 任务
撰写该剧的故事梗概。

# 输出格式 (JSON)
{{
    "story_title": "剧名，响亮好记",
    "one_liner": "一句话梗概，30字内，极具吸引力",
    "synopsis": "详细梗概，包含开端、发展、高潮、结局",
    "selling_points": ["卖点1", "卖点2", "卖点3", "卖点4"]
}}

请只输出JSON，不要有任何其他文字。"""


async def synopsis_creator_node(state: ScriptState) -> ScriptState:
    """
    故事梗概生成节点

    根据需求确认书生成故事梗概、标题、一句话简介、核心卖点
    """
    # 优先使用需求确认书（结构化需求），回退到原始需求
    confirmation = state.get("requirement_confirmation", {})
    requirements = state.get("requirements", {})

    # 合并数据源：需求确认书优先
    genre = confirmation.get("genre") or requirements.get("genre", "短剧")
    protagonist = confirmation.get("protagonist_summary") or requirements.get("protagonist", "主角")
    conflict = confirmation.get("core_conflict_summary") or requirements.get("conflict", "核心冲突")
    style = confirmation.get("style_summary") or requirements.get("style", "爽文")
    target_audience = confirmation.get("target_audience") or requirements.get("target_audience", "大众")
    episodes = confirmation.get("episodes") or requirements.get("episodes", 80)
    world_building = confirmation.get("world_building_summary", "")
    romance_line = confirmation.get("romance_line_summary", "")
    checkpoints = confirmation.get("checkpoint_summary", "")
    selling_points = confirmation.get("selling_points", [])

    # 构建增强版提示词
    prompt = f"""你是一位擅长构建宏大世界观与紧凑剧情的资深编剧。

# 剧本需求
题材：{genre}
主角设定：{protagonist}
核心冲突：{conflict}
风格基调：{style}
目标受众：{target_audience}
总集数：{episodes}集

# 关键设计要素（必须融入梗概）
{"世界观设定：" + world_building if world_building else ""}
{"感情线设计：" + romance_line if romance_line else ""}
{"付费卡点规划：" + checkpoints if checkpoints else ""}
{"核心卖点：" + ", ".join(selling_points) if selling_points else ""}

# 约束条件
1. 字数：300-2000字
2. 必须包含完整的起承转合
3. 必须符合竖屏短剧节奏：开篇即高潮，前3集要有强冲突
4. 设置明显的情绪钩子（爽感或虐点）
5. 内容必须原创，严禁抄袭
6. 符合社会主义核心价值观，拒绝低俗内容
7. **必须体现世界观设定**（如有）
8. **必须体现感情线脉络**（如有）
9. **必须为付费卡点埋下伏笔**（每10集一个强钩子）

# 任务
撰写该剧的故事梗概。

# 输出格式 (JSON)
{{
    "story_title": "剧名，响亮好记",
    "one_liner": "一句话梗概，30字内，极具吸引力",
    "synopsis": "详细梗概，包含开端、发展、高潮、结局",
    "selling_points": ["卖点1", "卖点2", "卖点3", "卖点4"]
}}

请只输出JSON，不要有任何其他文字。"""

    try:
        # 调用LLM
        llm_service = get_llm_service()
        response = await llm_service.generate_with_retry(prompt, max_tokens=2000)

        # 清理响应（处理markdown代码块）
        cleaned_response = response.strip()
        if cleaned_response.startswith("```json"):
            cleaned_response = cleaned_response[7:]
        if cleaned_response.startswith("```"):
            cleaned_response = cleaned_response[3:]
        if cleaned_response.endswith("```"):
            cleaned_response = cleaned_response[:-3]
        cleaned_response = cleaned_response.strip()

        # 解析JSON响应
        result = json.loads(cleaned_response)

        # V1.2修改：优先使用需求确认书中的title，不再重新生成剧名
        confirmation_title = confirmation.get("title", "")
        if confirmation_title:
            state["story_title"] = confirmation_title
            logger.info(f"[故事梗概] 使用需求确认书剧名: {confirmation_title}")
        else:
            state["story_title"] = result.get("story_title", "未命名剧本")
            logger.info(f"[故事梗概] 使用AI生成剧名: {state['story_title']}")

        state["one_liner"] = result.get("one_liner", "")
        state["story_synopsis"] = result.get("synopsis", "")
        state["selling_points"] = result.get("selling_points", [])

        logger.info(f"[故事梗概] 生成完成 - 剧名:{state['story_title']}, 一句话:{state['one_liner'][:30]}..., 字数:{len(state['story_synopsis'])}")

    except (json.JSONDecodeError, Exception) as e:
        logger.error(f"[故事梗概] 生成失败: {e}")
        logger.error(f"[故事梗概] 清理后的响应前200字: {cleaned_response[:200] if 'cleaned_response' in locals() else 'N/A'}")
        # 回退方案：优先使用需求确认书剧名
        confirmation_title = confirmation.get("title", "")
        genre = confirmation.get("genre") or requirements.get("genre", "短剧")
        protagonist = confirmation.get("protagonist_summary") or requirements.get("protagonist", "主角")

        state["story_title"] = confirmation_title if confirmation_title else f"《{protagonist}的{genre}传奇》"
        state["one_liner"] = f"一个关于{protagonist}的传奇故事"
        state["story_synopsis"] = f"这是一个{genre}题材的故事，主角{protagonist}凭借智慧和勇气，一步步突破重围，最终实现逆袭。"
        state["selling_points"] = [f"{genre}题材热门", "人设鲜明", "冲突强烈", "节奏紧凑"]
        logger.info(f"[故事梗概] 使用回退方案 - 剧名:{state['story_title']}")

    # 更新进度
    state["creation_progress"] = {
        "step": "synopsis",
        "status": "completed",
        "percentage": 10,
        "completed_episodes": 0,
        "total_episodes": state.get("total_episodes", 80)
    }

    return state


# ===== 人物小传生成节点（V1.1优化版）=====

CHARACTER_CREATOR_PROMPT = """你是一位擅长塑造鲜明人物形象的资深编剧，特别擅长为竖屏短剧设计令人印象深刻的人物。

# 故事梗概
剧名：{story_title}
一句话简介：{one_liner}
详细梗概：
{synopsis}

# 需求约束
题材：{genre}
风格：{style}
总集数：{total_episodes}集

# ═══════════════════════════════════════════════════════════
# 人物设定规范（严格遵守）
# ═══════════════════════════════════════════════════════════

## 1. 人物数量（根据集数动态调整）
- **简单剧情（≤50集）**：2-3个主要人物 + 1-2个配角
- **中等剧情（51-80集）**：3-4个主要人物 + 2-3个配角
- **复杂剧情（>80集）**：4-6个主要人物 + 3-5个配角

## 2. 人物命名规范
- 接地气，避免生僻字（如"丽君"、"东升"、"建国"）
- 女频可用叠音（如"萱萱"、"甜甜"、"瑶瑶"）
- 便于观众记忆和传播

## 3. 每个人物必须包含
- **基本信息**：姓名、年龄、性格、背景、目标
- **外观形象**：身高、体型、发型、穿着风格、标志性特征
- **记忆点**：口头禅、习惯动作、标志性物品
- **成长性**：主角必须有成长弧线，反派智商在线

## 4. 人物关系
- 关系清晰，避免过于复杂
- 主要关系不超过5-6人
- 每对关系要有张力（爱恨、利益、矛盾）

# 任务
为该剧创作完整的人物小传，包括：
1. **主要人物**：主角、核心对手、爱情线角色
2. **重要配角**：推动剧情的关键配角
3. **人物关系图**：文字描述关系网

# 输出格式 (JSON)
{{
    "characters": [
        {{
            "name": "姓名",
            "role": "主角/反派/爱情线/配角",
            "age": "年龄（如：28岁）",
            "appearance": {{
                "height": "身高（如：180cm）",
                "build": "体型（如：身材健硕、纤细苗条）",
                "hair": "发型发色",
                "clothing_style": "穿着风格（如：商务精英风、休闲运动风）",
                "distinctive_features": "标志性特征（如：左眉有疤、总戴金丝眼镜）"
            }},
            "personality": "性格描述（3-5个关键词+展开）",
            "background": "背景故事（100字以内）",
            "goal": "人物目标/动机",
            "memory_point": "记忆点特征（标志性动作或特点，可包含口头禅）"
        }}
    ],
    "relationship_map": "文字描述的人物关系图（如：主角与反派是仇人，与女主是恋人）"
}}

# 输出前检查
- [ ] 人物数量符合集数要求
- [ ] 每个人物都有完整的外观描述
- [ ] 主角有成长性，反派有智商
- [ ] 人物关系清晰有张力

请只输出JSON，不要有任何其他文字。"""


async def character_creator_node(state: ScriptState) -> ScriptState:
    """
    人物小传生成节点（V1.2优化版）

    根据集数动态调整人物数量，增加外观描述
    使用需求确认书中的结构化信息
    """
    # 优先使用需求确认书
    confirmation = state.get("requirement_confirmation", {})
    requirements = state.get("requirements", {})
    total_episodes = state.get("total_episodes", 80)

    # 合并数据源
    genre = confirmation.get("genre") or requirements.get("genre", "短剧")
    style = confirmation.get("style_summary") or requirements.get("style", "爽文")
    world_building = confirmation.get("world_building_summary", "")
    romance_line = confirmation.get("romance_line_summary", "")
    protagonist_summary = confirmation.get("protagonist_summary", "")

    # 构建增强版提示词（修复版：避免f-string条件表达式问题）
    # 先构建条件部分
    romance_role_line = "- **必须包含感情线角色**：根据感情线设计设置爱情/暧昧对象\n" if romance_line else ""
    world_role_line = "- **必须符合世界观**：人物能力、地位、身份与世界观一致\n" if world_building else ""
    romance_in_task = "、爱情线角色" if romance_line else ""
    romance_check = "- [ ] 感情线角色已设置并符合感情线设计\n" if romance_line else ""
    world_check = "- [ ] 人物符合世界观设定\n" if world_building else ""

    prompt = f"""你是一位擅长塑造鲜明人物形象的资深编剧，特别擅长为竖屏短剧设计令人印象深刻的人物。

# 故事梗概
剧名：{state.get("story_title", "未命名")}
一句话简介：{state.get("one_liner", "")}
详细梗概：
{state.get("story_synopsis", "")[:500]}

# 需求约束
题材：{genre}
风格：{style}
总集数：{total_episodes}集

# ═══════════════════════════════════════════════════════════
# 需求确认书中的关键设计（必须遵守）
# ═══════════════════════════════════════════════════════════

## 主角设定摘要
{protagonist_summary if protagonist_summary else "（基于梗概提炼）"}

## 世界观设定（人物必须符合这个世界观）
{world_building if world_building else "（现代/常规背景）"}

## 感情线设计（人物关系必须符合此设计）
{romance_line if romance_line else "（无特殊感情线要求）"}

# ═══════════════════════════════════════════════════════════
# 人物设定规范（严格遵守）
# ═══════════════════════════════════════════════════════════

## 1. 人物数量（根据集数动态调整）
- **简单剧情（≤50集）**：2-3个主要人物 + 1-2个配角
- **中等剧情（51-80集）**：3-4个主要人物 + 2-3个配角
- **复杂剧情（>80集）**：4-6个主要人物 + 3-5个配角

## 2. 人物命名规范
- 接地气，避免生僻字（如"丽君"、"东升"、"建国"）
- 女频可用叠音（如"萱萱"、"甜甜"、"瑶瑶"）
- 便于观众记忆和传播
- **必须符合世界观设定**（如古代背景用古风名）

## 3. 每个人物必须包含
- **基本信息**：姓名、年龄、性格、背景、目标
- **外观形象**：身高、体型、发型、穿着风格、标志性特征
- **记忆点**：容易引起观众共鸣的特点
- **成长性**：主角必须有成长弧线，反派智商在线

## 4. 人物关系设计原则
- 关系清晰，避免过于复杂
- 主要关系不超过5-6人
- 每对关系要有张力（爱恨、利益、矛盾）
{romance_role_line}{world_role_line}
# 任务
为该剧创作完整的人物小传，包括：
1. **主要人物**：主角、核心对手{romance_in_task}
2. **重要配角**：推动剧情的关键配角

# 输出格式 (JSON)
{{
    "characters": [
        {{
            "name": "姓名",
            "role": "主角/反派/爱情线/配角",
            "age": "年龄（如：28岁）",
            "appearance": {{
                "height": "身高（如：180cm）",
                "build": "体型（如：身材健硕、纤细苗条）",
                "hair": "发型发色",
                "clothing_style": "穿着风格（如：商务精英风、休闲运动风）",
                "distinctive_features": "标志性特征（如：左眉有疤、总戴金丝眼镜）"
            }},
            "personality": "性格描述（3-5个关键词+展开）",
            "background": "背景故事（100字以内）",
            "goal": "人物目标/动机",
            "memory_point": "记忆点特征",
            "relationships": "与主要人物的关系（简短描述）"
        }}
    ]
}}

# 输出前检查
- [ ] 人物数量符合集数要求
- [ ] 每个人物都有完整的外观描述
- [ ] 主角有成长性，反派有智商
所有字段值（Value）的内部文本中，严禁出现双引号字符。如果原文包含双引号，请将其替换为单引号（'）或直接移除，以确保无需转义即可安全解析。
{romance_check}{world_check}
请只输出JSON，不要有任何其他文字。
所有字段值（Value）的内部文本中，严禁出现双引号字符。如果需要使用单引号（'），以确保无需转义即可安全解析。
"""

    try:
        # 调用LLM（max_tokens=8000 确保完整 JSON 输出）
        llm_service = get_llm_service()
        response = await llm_service.generate_with_retry(prompt, max_tokens=8000)

        logger.info(f"[人物小传] LLM响应长度: {len(response)}")
        # logger.info(f"response: {response}")
        # 清理响应（处理markdown代码块）
        response = response.strip("```json").strip("```").strip()
        # logger.info(f"response.strip: {response.strip()}")
        # 直接JSON解析（LLM输出已规范，跳过复杂修复）
        result = json.loads(response.strip())

        if result and "characters" in result:
            # 标准化字段名
            raw_characters = result.get("characters", [])
            state["character_profiles"] = [_normalize_character_fields(c) for c in raw_characters]
            logger.info(f"[人物小传] 成功解析，获得{len(state['character_profiles'])}个人物")
        else:
            raise ValueError("JSON解析结果缺少characters字段")

    except Exception as e:
        logger.error(f"人物小传生成失败: {e}")
        logger.error(f"原始响应前500字: {response[:500] if 'response' in locals() else 'N/A'}")

        # 解析失败时使用回退方案
        logger.warning("[人物小传] 使用默认回退方案")
        genre = requirements.get("genre", "短剧")
        state["character_profiles"] = [
                {
                    "name": "林萧",
                    "role": "主角",
                    "age": "28岁",
                    "appearance": {
                        "height": "182cm",
                        "build": "身材修长健硕",
                        "hair": "黑色短发，略显凌乱",
                        "clothing_style": "低调简约，常穿深色休闲装",
                        "distinctive_features": "眼神深邃，左眉骨有一道浅疤"
                    },
                    "personality": "隐忍沉稳，内心强大，外冷内热",
                    "background": f"表面平凡的年轻人，实则是隐藏的{genre}高手",
                    "goal": "复仇并夺回属于自己的一切",
                    "memory_point": "标志性的冷笑和整理袖口的动作，口头禅：有意思...",
                    "relationships": "与反派王少是仇人"
                },
                {
                    "name": "王少",
                    "role": "反派",
                    "age": "30岁",
                    "appearance": {
                        "height": "178cm",
                        "build": "微胖，有些啤酒肚",
                        "hair": "油头，梳得一丝不苟",
                        "clothing_style": "浮夸奢华，喜欢名牌Logo",
                        "distinctive_features": "手腕上总是戴着金表"
                    },
                    "personality": "嚣张跋扈，目中无人，外强中干",
                    "background": "富二代，仗着家族势力为非作歹",
                    "goal": "打压主角，维护自己地位",
                    "memory_point": "说话时喜欢摇晃手腕展示金表，口头禅：你知道我是谁吗？",
                    "relationships": "与主角林萧是仇人"
                },
                {
                    "name": "苏婉",
                    "role": "爱情线",
                    "age": "26岁",
                    "appearance": {
                        "height": "168cm",
                        "build": "身材纤细苗条",
                        "hair": "黑色长发，微卷",
                        "clothing_style": "清新淡雅，喜欢浅色系裙装",
                        "distinctive_features": "笑起来有浅浅的酒窝"
                    },
                    "personality": "温柔善良，内心坚强，善解人意",
                    "background": "主角的青梅竹马，一直默默支持他",
                    "goal": "陪伴主角度过难关",
                    "memory_point": "紧张时会不自觉地握紧双手，口头禅：我相信你。"
                }
            ]

    # 更新进度
    state["creation_progress"] = {
        "step": "characters",
        "status": "completed",
        "percentage": 20,
        "completed_episodes": 0,
        "total_episodes": state.get("total_episodes", 80)
    }

    return state


# ===== JSON提取辅助函数 =====

def _extract_outlines_with_regex(text: str, start_ep: int, end_ep: int) -> List[Dict]:
    """
    使用正则表达式从文本中提取大纲条目
    当JSON解析失败时的最后回退方案
    """
    import re
    outlines = []

    # 尝试匹配 episode_number 和 summary
    # 格式示例："episode_number": 1 或 episode_number: 1
    pattern = r'["\']?episode_number["\']?\s*[:=]\s*(\d+)'
    matches = list(re.finditer(pattern, text, re.IGNORECASE))

    for i, match in enumerate(matches):
        ep_num = int(match.group(1))
        if start_ep <= ep_num <= end_ep:
            # 提取该集周围的内容
            start_pos = match.start()
            end_pos = matches[i + 1].start() if i + 1 < len(matches) else len(text)
            chunk = text[start_pos:end_pos]

            # 提取summary
            summary_match = re.search(r'["\']?summary["\']?\s*[:=]\s*["\']([^"\']+)["\']', chunk, re.IGNORECASE)
            summary = summary_match.group(1) if summary_match else f"第{ep_num}集：剧情发展"

            # 提取hook
            hook_match = re.search(r'["\']?hook["\']?\s*[:=]\s*["\']([^"\']+)["\']', chunk, re.IGNORECASE)
            hook = hook_match.group(1) if hook_match else "剧情悬念..."

            outlines.append({
                "episode_number": ep_num,
                "summary": summary,
                "hook": hook,
                "is_checkpoint": ep_num % 10 == 0
            })

    # 如果没有匹配到任何内容，生成默认大纲
    if not outlines:
        for ep in range(start_ep, end_ep + 1):
            outlines.append({
                "episode_number": ep,
                "summary": f"第{ep}集：剧情推进，人物关系发展",
                "hook": "悬念待揭晓...",
                "is_checkpoint": ep % 10 == 0
            })

    return outlines


# ===== 分集大纲生成节点 =====

OUTLINE_CREATOR_PROMPT = """你是一位精通短剧节奏把控的剧本统筹。

# 故事梗概
{synopsis}

# 人物小传
{characters}

# 总集数
{total_episodes}集

# 约束条件
1. 节奏要求：每集必须推进剧情，无废戏
2. 卡点设计：每集结尾必须有悬念钩子；每10集设置一个强付费卡点
3. 结构要求：
   - 前3集必须完成世界观建立、主角登场、核心冲突爆发
   - 每集对应1-3分钟拍摄时长
   - 信息密度高，节奏极快
4. 字数要求：单集大纲简洁明了，50-100字

# 任务
撰写第{start_episode}集到第{end_episode}集的分集大纲。

# 输出格式 (JSON)
{{
    "outlines": [
        {{
            "episode_number": 1,
            "summary": "本集剧情概要...",
            "hook": "结尾卡点/钩子...",
            "is_checkpoint": false
        }}
    ]
}}

注意：
- is_checkpoint 只在第10、20、30...集时设为true
- 每集都必须有明确的剧情推进和卡点
- 前3集要有强冲突爆发

请只输出JSON，不要有任何其他文字。"""


async def outline_creator_node(state: ScriptState) -> ScriptState:
    """
    分集大纲生成节点（V1.2优化版）

    生成所有集的大纲，使用需求确认书中的付费卡点设计
    """
    total_episodes = state.get("total_episodes", 80)
    characters = state.get("character_profiles", [])

    # 获取需求确认书中的关键信息
    confirmation = state.get("requirement_confirmation", {})
    checkpoint_summary = confirmation.get("checkpoint_summary", "")
    world_building = confirmation.get("world_building_summary", "")
    romance_line = confirmation.get("romance_line_summary", "")
    plot_summary = confirmation.get("plot_summary", "")

    outlines = []

    # 分批生成，每批10集
    batch_size = 10
    for batch_start in range(1, total_episodes + 1, batch_size):
        batch_end = min(batch_start + batch_size - 1, total_episodes)

        # 构建增强版提示词
        prompt = f"""你是一位精通短剧节奏把控的剧本统筹。

# 故事梗概
{state.get("story_synopsis", "")[:800]}

# 人物小传
{json.dumps(characters[:3], ensure_ascii=False)}

# 总集数
{total_episodes}集

# ═══════════════════════════════════════════════════════════
# 需求确认书中的关键设计（必须严格遵守）
# ═══════════════════════════════════════════════════════════

## 剧情规划摘要
{plot_summary if plot_summary else "（基于故事梗概）"}

## 付费卡点设计（核心指导）
{checkpoint_summary if checkpoint_summary else "每10集设置一个强付费卡点（第10、20、30...集）"}

## 世界观设定
{world_building if world_building else "（现代/常规背景）"}

## 感情线设计
{romance_line if romance_line else "（根据剧情需要设置感情线）"}

# ═══════════════════════════════════════════════════════════
# 约束条件
# ═══════════════════════════════════════════════════════════
1. **节奏要求**：每集必须推进剧情，无废戏
2. **卡点设计**：
   - 每集结尾必须有悬念钩子
   - **严格遵循付费卡点设计**，第10/20/30...集必须是强付费卡点
   - 卡点必须与剧情紧密结合，不能生硬
3. **结构要求**：
   - 前3集必须完成世界观建立、主角登场、核心冲突爆发
   - 每集对应1-3分钟拍摄时长
   - 信息密度高，节奏极快
4. **字数要求**：单集大纲简洁明了，50-100字
5. **感情线融入**：{"感情线进度必须在各集中有所体现" if romance_line else ""}
6. **世界观一致性**：{"所有情节必须符合世界观设定" if world_building else ""}

# 任务
撰写第{batch_start}集到第{batch_end}集的分集大纲。

# 输出格式 (JSON)
{{
    "outlines": [
        {{
            "episode_number": 1,
            "summary": "本集剧情概要...",
            "hook": "结尾卡点/钩子...",
            "is_checkpoint": false
        }}
    ]
}}

注意：
- is_checkpoint 只在第10、20、30...集时设为true（付费卡点）
- **必须参考付费卡点设计来编写卡点内容**
- 每集都必须有明确的剧情推进和卡点
- 前3集要有强冲突爆发

请只输出JSON，不要有任何其他文字。"""

        # 标志位，标记是否成功处理当前批次
        batch_success = False

        try:
            # 调用LLM
            llm_service = get_llm_service()
            response = await llm_service.generate_with_retry(prompt, max_tokens=3000, temperature=0.3)

            # 清理和修复JSON响应
            cleaned_response = response.strip()

            # 尝试提取JSON部分（去除可能的markdown代码块标记）
            if cleaned_response.startswith("```json"):
                cleaned_response = cleaned_response[7:]
            if cleaned_response.startswith("```"):
                cleaned_response = cleaned_response[3:]
            if cleaned_response.endswith("```"):
                cleaned_response = cleaned_response[:-3]

            cleaned_response = cleaned_response.strip()

            # 尝试解析JSON
            result = None
            parse_success = False

            try:
                result = json.loads(cleaned_response)
                parse_success = True
            except json.JSONDecodeError as json_err:
                print(f"初次JSON解析失败: {json_err}")
                # 尝试修复常见的JSON格式问题
                # 修复单引号
                if cleaned_response.startswith("'") and cleaned_response.endswith("'"):
                    cleaned_response = cleaned_response[1:-1]
                # 修复尾随逗号
                cleaned_response = re.sub(r',(\s*[}\]])', r'\1', cleaned_response)

                # 再次尝试解析
                try:
                    result = json.loads(cleaned_response)
                    parse_success = True
                except json.JSONDecodeError as e2:
                    print(f"修复后仍解析失败: {e2}")

            if parse_success and result:
                batch_outlines = result.get("outlines", [])
                for outline in batch_outlines:
                    ep_num = outline.get("episode_number", 0)
                    outline["is_checkpoint"] = (ep_num % 10 == 0)
                    outlines.append(outline)
                batch_success = True
            else:
                # 使用正则提取作为回退
                print(f"尝试使用正则表达式提取大纲")
                batch_outlines = _extract_outlines_with_regex(cleaned_response, batch_start, batch_end)
                if batch_outlines:
                    outlines.extend(batch_outlines)
                    batch_success = True

        except Exception as e:
            print(f"第{batch_start}-{batch_end}集大纲生成失败: {e}")

        # 如果所有方法都失败，使用最后的回退方案
        if not batch_success:
            print(f"使用默认回退方案生成第{batch_start}-{batch_end}集大纲")
            for i in range(batch_start, batch_end + 1):
                if i % 10 == 0:
                    summary = f"第{i}集：重要剧情节点，主角实力再次提升。"
                    hook = f"结尾：惊天反转，所有人都震惊了！"
                elif i % 5 == 0:
                    summary = f"第{i}集：反派再次出手，主角巧妙化解。"
                    hook = f"结尾：主角露出神秘微笑，似乎早有准备。"
                else:
                    summary = f"第{i}集：剧情推进，人物关系进一步发展。"
                    hook = f"结尾：意外发现，为下一集埋下伏笔。"

                outlines.append({
                    "episode_number": i,
                    "summary": summary,
                    "hook": hook,
                    "is_checkpoint": i % 10 == 0
                })

    # 按集数排序
    outlines.sort(key=lambda x: x["episode_number"])

    state["episode_outlines"] = outlines

    # 更新进度
    state["creation_progress"] = {
        "step": "outline",
        "status": "completed",
        "percentage": 30,
        "completed_episodes": 0,
        "total_episodes": total_episodes
    }

    return state


# ===== 剧本上下文管理工具函数 =====

def initialize_script_context(state: ScriptState) -> ScriptState:
    """
    初始化剧本创作上下文

    在开始生成剧本前调用，建立故事弧线、人物初始状态等
    """
    total_episodes = state.get("total_episodes", 80)
    outlines = state.get("episode_outlines", [])
    characters = state.get("character_profiles", [])

    # 确定故事阶段分界点
    phase_boundaries = {
        "起": (1, max(3, total_episodes // 10)),           # 开端：前10%
        "承": (max(3, total_episodes // 10) + 1, total_episodes // 2),  # 发展：10%-50%
        "转": (total_episodes // 2 + 1, total_episodes * 8 // 10),      # 转折：50%-80%
        "合": (total_episodes * 8 // 10 + 1, total_episodes)            # 结局：80%-100%
    }

    # 初始化人物状态
    character_statuses = {}
    for char in characters:
        name = char.get("name", "")
        if name:
            character_statuses[name] = {
                "name": name,
                "current_emotion": "平静",           # 初始情绪
                "current_situation": char.get("background", "")[:100],  # 初始处境
                "goal_progress": "初始阶段",          # 目标进展
                "relationships": {},                   # 关系状态
                "key_events": [],                      # 关键事件
                "secrets_known": []                    # 已知秘密
            }

    # 构建故事弧线（基于大纲识别）
    story_arcs = []
    arc_keywords = {
        "身份揭秘": ["身份", "真相", "秘密"],
        "复仇": ["复仇", "报复", "雪恨"],
        "爱情": ["爱情", "感情", "表白", "分手"],
        "权力斗争": ["权力", "斗争", "争夺"],
        "成长": ["成长", "变强", "突破"]
    }

    # 从大纲中提取故事弧线
    for arc_name, keywords in arc_keywords.items():
        trigger_episode = None
        for outline in outlines:
            summary = outline.get("summary", "")
            if any(kw in summary for kw in keywords):
                if trigger_episode is None:
                    trigger_episode = outline["episode_number"]
                # 找到最后一集包含关键词的作为解决
                resolve_episode = outline["episode_number"]

        if trigger_episode:
            story_arcs.append({
                "arc_type": "主线" if arc_name in ["身份揭秘", "复仇"] else "支线",
                "name": arc_name,
                "status": "进行中",
                "trigger_episode": trigger_episode,
                "resolve_episode": resolve_episode if trigger_episode != resolve_episode else None,
                "key_events": []
            })

    # 初始化剧本上下文
    state["script_context"] = {
        "story_phase": "起",
        "phase_progress": "故事开端，世界观建立阶段",
        "character_statuses": character_statuses,
        "completed_events": [],
        "pending_hooks": [],
        "resolved_hooks": [],
        "foreshadowing": [],
        "recent_summary": "",
        "key_revelations": [],
        "constraints_check": []
    }

    state["story_arcs"] = story_arcs

    return state


def get_story_phase(episode_number: int, total_episodes: int) -> tuple:
    """
    获取当前故事阶段

    Returns:
        (阶段名称, 阶段描述)
    """
    progress = episode_number / total_episodes

    if progress <= 0.1:
        return ("起", "故事开端，主角登场，世界观建立，核心冲突引入")
    elif progress <= 0.5:
        return ("承", "情节发展，冲突升级，人物关系深化，主角成长")
    elif progress <= 0.8:
        return ("转", "重大转折，真相揭露，高潮铺垫，命运抉择")
    else:
        return ("合", "终极对决，矛盾解决，大结局，人物归宿")


def generate_recent_summary(outlines: List[Dict], scripts: List[Dict], current_episode: int) -> str:
    """
    生成最近3集的剧情摘要
    """
    if current_episode <= 1:
        return "这是第1集，故事刚刚开始。"

    summaries = []
    start_ep = max(1, current_episode - 3)

    for ep in range(start_ep, current_episode):
        # 查找该集的大纲和剧本
        outline = next((o for o in outlines if o["episode_number"] == ep), None)
        script = next((s for s in scripts if s["episode_number"] == ep), None)

        if outline:
            summary = outline.get("summary", "")
            hook = outline.get("hook", "")

            # 尝试从剧本中提取关键对话或动作
            key_moment = ""
            if script:
                content = script.get("content", "")
                # 提取场景开头部分
                if "场景：" in content:
                    scene_start = content.find("场景：")
                    scene_end = content.find("\n\n", scene_start)
                    if scene_end > scene_start:
                        key_moment = content[scene_start:scene_end][:100]

            summaries.append(f"第{ep}集：{summary[:60]}... 卡点：{hook[:40]}...")

    return "\n".join(summaries)


def update_character_statuses(
    context: Dict,
    script_content: str,
    characters: List[Dict]
) -> Dict:
    """
    根据剧本内容更新人物状态

    分析剧本中的人物情绪、关系变化等
    """
    character_statuses = context.get("character_statuses", {})

    for char in characters:
        name = char.get("name", "")
        if not name or name not in character_statuses:
            continue

        status = character_statuses[name]

        # 检测情绪变化（简单关键词匹配）
        emotion_indicators = {
            "愤怒": ["愤怒", "生气", "怒吼", "咆哮"],
            "悲伤": ["悲伤", "哭泣", "流泪", "痛苦"],
            "喜悦": ["高兴", "开心", "笑", "兴奋"],
            "恐惧": ["害怕", "惊恐", "颤抖", "恐惧"],
            "坚定": ["坚定", "决心", "毅然", "毫不"],
            "隐忍": ["隐忍", "忍耐", "沉默", "克制"]
        }

        # 查找该人物在剧本中的情绪
        # 简单方案：检查人物名附近是否有情绪词
        import re
        pattern = rf"\*\*{name}[（(]([^）)]+)[）)]\*\*"
        matches = re.findall(pattern, script_content)

        if matches:
            # 使用剧本中标注的情绪
            latest_emotion = matches[-1]
            if len(latest_emotion) <= 10:  # 合理的情绪描述长度
                status["current_emotion"] = latest_emotion

        # 检测人物是否经历了关键事件
        if name in script_content:
            # 简单检测是否有重大对话或动作
            lines = script_content.split("\n")
            for i, line in enumerate(lines):
                if name in line and i < len(lines) - 1:
                    next_line = lines[i + 1].strip()
                    if next_line.startswith('"') and len(next_line) > 10:
                        # 这是一句台词，可能是关键对话
                        if any(kw in next_line for kw in ["秘密", "真相", "复仇", "爱", "杀", "死", "身份"]):
                            event = f"说出关键台词：{next_line[:30]}..."
                            if event not in status["key_events"]:
                                status["key_events"].append(event)
                                if len(status["key_events"]) > 5:
                                    status["key_events"].pop(0)

    context["character_statuses"] = character_statuses
    return context


def extract_hooks_and_events(script_content: str, outline: Dict) -> tuple:
    """
    从剧本中提取悬念钩子和关键事件

    Returns:
        (新钩子列表, 关键事件列表, 揭示的秘密列表)
    """
    new_hooks = []
    key_events = []
    revelations = []

    # 提取卡点/钩子
    if "【本集卡点" in script_content:
        import re
        match = re.search(r"【本集卡点[^】]*】([^\n]*)", script_content)
        if match:
            hook = match.group(1).strip()
            if hook:
                new_hooks.append(hook)

    # 提取大纲中的关键事件
    summary = outline.get("summary", "")
    hook = outline.get("hook", "")

    # 检测揭示类事件
    revelation_keywords = ["真相", "秘密", "身份", "原来是", "发现", "得知"]
    for kw in revelation_keywords:
        if kw in summary or kw in script_content:
            revelations.append(f"第{outline['episode_number']}集揭示：{summary[:50]}...")
            break

    return (new_hooks, key_events, revelations)


# ===== 剧本正文生成节点 =====

SCRIPT_CREATOR_PROMPT = """你是一位专业的短剧剧本撰写师，熟悉竖屏拍摄特点。

# === 故事背景 ===
剧名：{story_title}
总集数：{total_episodes}集

# === 人物设定（含当前状态）===
{characters}

# === 故事结构定位 ===
当前阶段：{story_phase}
阶段说明：{phase_progress}

# === 剧情追踪 ===
最近3集剧情回顾：
{recent_summary}

关键揭示/反转：
{key_revelations}

待回收的悬念：
{pending_hooks}

# === 本集信息 ===
集数：第{episode_number}集
剧情概要：{summary}
卡点要求：{hook}
本集定位：{episode_position}

# === 上一集结尾 ===
{previous_ending}

# === 创作指引 ===
1. **故事连贯性**：
   - 承接上一集结尾，自然过渡到本集开头
   - 关注"最近3集剧情回顾"，确保剧情连贯
   - 如有"待回收的悬念"，在本集适当回应

2. **人物一致性**：
   - 参考"人物当前状态"保持情绪和处境的连贯
   - 人物性格应与设定一致，避免突然降智或性格突变
   - 台词要符合人物当前情绪状态

3. **节奏控制**：
   - 当前处于"{story_phase}"阶段，{phase_instruction}
   - 本集必须有明确的剧情推进，无废戏
   - 情绪起伏要有层次，不能平淡

4. **卡点设置**：
   - 必须在结尾设置强钩子，符合大纲要求
   - 钩子要与本集剧情紧密相关，不能突兀

# === 格式要求（严格遵守）===
1. **场景标注**：内景/外景-地点-日/夜
2. **人物标注**：人物名居中，标注情绪状态
3. **台词**：口语化、简短有力，符合人设，每句台词不超过30字
4. **动作描述**：简洁，包含镜头提示（如【特写】、【转场】）
5. **字数控制**：
   - 目标字数：1500-1800字
   - 硬性限制：必须在 1200-2000 字之间
   - 字数不足则扩充对话和动作描述
   - 字数过多则精简冗余对话
6. **卡点**：必须在结尾设置强钩子

# 剧本格式示例
第X集 集标题

场景：内景-办公室-日

人物：张三、李四

▶动作描述：张三猛拍桌子，文件飞散。【特写】愤怒的眼神

**张三（愤怒）：**
"你敢顶嘴？"

**李四（隐忍，双手握拳）：**
"老板，这不是我的错。"

▶动作描述：【转场】夜晚，李四独自走在街头

【本集卡点/钩子】
重大反转即将揭晓...

# 任务
请撰写第{episode_number}集的完整剧本。

要求：
1. 严格遵循大纲设定和卡点要求
2. 保持人物性格一致性和情绪连贯
3. 承接前文剧情，自然推进故事
4. 对话推动剧情，不要旁白过多
5. 情绪张力强，适合竖屏观看
6. 符合拍摄可行性，场景不要太复杂

请直接输出剧本正文，使用上述格式。"""


def format_characters_with_status(characters: List[Dict], context: Dict) -> str:
    """
    格式化人物信息，包含当前状态
    """
    character_statuses = context.get("character_statuses", {})
    formatted = []

    for char in characters:
        name = char.get("name", "")
        status = character_statuses.get(name, {})

        char_info = f"""
【{name} - {char.get('role', '角色')}】
基础设定：{char.get('age', '')}岁，{char.get('personality', '')}
背景：{char.get('background', '')[:80]}...
目标：{char.get('goal', '')}
当前状态：{status.get('current_emotion', '平静')}，{status.get('current_situation', '正常处境')[:60]}
目标进展：{status.get('goal_progress', '初始阶段')}
关键经历：{', '.join(status.get('key_events', [])[-2:]) or '暂无'}
"""
        formatted.append(char_info)

    return "\n".join(formatted)


def get_phase_instruction(phase: str) -> str:
    """获取阶段的创作指引"""
    instructions = {
        "起": "重点：快速建立世界观，主角登场要有冲击力，核心冲突在第1-3集爆发",
        "承": "重点：冲突逐步升级，人物关系深化，主角经历成长，每集推进剧情",
        "转": "重点：重大转折出现，真相揭露，情绪张力最强，为高潮做铺垫",
        "合": "重点：矛盾集中爆发并解决，人物命运尘埃落定，给出圆满结局"
    }
    return instructions.get(phase, "保持剧情连贯，推进故事发展")


async def script_writer_node(state: ScriptState, batch_end: int = None) -> ScriptState:
    """
    剧本正文生成节点（V1.2增强版）

    逐集生成剧本，维护剧情连贯性和人物状态一致性
    使用需求确认书中的风格基调、世界观、感情线等关键信息

    Args:
        state: 项目状态
        batch_end: 批次结束集数（用于分批生成，None表示生成全部）
    """
    outlines = state.get("episode_outlines") or []
    characters = state.get("character_profiles") or []
    total_episodes = state.get("total_episodes", 80)

    # 获取需求确认书中的关键信息
    confirmation = state.get("requirement_confirmation", {})
    style_summary = confirmation.get("style_summary", "")
    world_building = confirmation.get("world_building_summary", "")
    romance_line = confirmation.get("romance_line_summary", "")
    checkpoint_summary = confirmation.get("checkpoint_summary", "")
    genre = confirmation.get("genre", "") or state.get("requirements", {}).get("genre", "短剧")

    # 安全检查：确保 outlines 不为空
    if not outlines:
        logger.error("episode_outlines 为空，无法生成剧本")
        state["creation_progress"] = {
            "step": "script",
            "status": "failed",
            "percentage": 30,
            "completed_episodes": 0,
            "total_episodes": total_episodes
        }
        return state

    # 初始化剧本上下文（如果是第一次）
    if not state.get("script_context"):
        state = initialize_script_context(state)

    scripts = state.get("scripts") or []
    context = state.get("script_context", {})

    # 确定从哪一集开始生成
    completed_episodes = len(scripts)
    start_index = completed_episodes

    # 确定结束位置
    end_index = batch_end if batch_end else len(outlines)
    end_index = min(end_index, len(outlines))

    logger.info(f"开始生成剧本: 第{start_index + 1}集到第{end_index}集 (共{len(outlines)}集)")

    # 逐集生成
    for i in range(start_index, end_index):
        outline = outlines[i]
        episode_number = outline["episode_number"]
        summary = outline["summary"]
        hook = outline["hook"]

        # 更新故事阶段
        story_phase, phase_progress = get_story_phase(episode_number, total_episodes)
        context["story_phase"] = story_phase
        context["phase_progress"] = phase_progress

        # 生成最近3集摘要
        recent_summary = generate_recent_summary(outlines, scripts, episode_number)
        context["recent_summary"] = recent_summary

        # 获取上一集结尾
        previous_ending = ""
        if scripts:
            last_script = scripts[-1]["content"]
            if "【本集卡点" in last_script:
                parts = last_script.split("【本集卡点")
                previous_ending = "【本集卡点" + parts[1][:200] if len(parts) > 1 else ""
            else:
                previous_ending = last_script[-200:] if len(last_script) > 200 else last_script

        # 格式化人物信息（带状态）
        characters_formatted = format_characters_with_status(characters, context)

        # 计算本集在感情线中的进度（如果有感情线）
        romance_progress = ""
        if romance_line and episode_number <= total_episodes:
            progress_pct = (episode_number / total_episodes) * 100
            if progress_pct <= 20:
                romance_progress = "相识/初遇阶段"
            elif progress_pct <= 40:
                romance_progress = "误会/试探阶段"
            elif progress_pct <= 60:
                romance_progress = "升温/暧昧阶段"
            elif progress_pct <= 80:
                romance_progress = "确认/热恋阶段"
            else:
                romance_progress = "终成眷属/情感升华阶段"

        # 检查是否是付费卡点集
        is_checkpoint_episode = episode_number % 10 == 0
        checkpoint_guidance = ""
        if is_checkpoint_episode and checkpoint_summary:
            checkpoint_num = episode_number // 10
            checkpoint_guidance = f"""
⚠️ 【付费卡点集特别提示】
这是第{checkpoint_num}个付费卡点（第{episode_number}集），必须设置最强钩子！
参考付费卡点设计：{checkpoint_summary}
要求：悬念必须足够强，让观众产生强烈的"想看下一集"的冲动。
"""

        # 构建增强版提示词
        prompt = f"""你是一位专业的短剧剧本撰写师，熟悉竖屏拍摄特点。

# === 故事背景 ===
剧名：{state.get("story_title", "未命名")}
总集数：{total_episodes}集
题材：{genre}

# === 需求确认书关键设计（创作时必须遵守）===
## 风格基调
{style_summary if style_summary else "爽文风格，节奏快，冲突强"}

## 世界观设定
{world_building if world_building else "（现代/常规背景，无特殊设定）"}

## 感情线设计{"（本集进度：" + romance_progress + "）" if romance_line else ""}
{romance_line if romance_line else "（根据剧情需要自然发展感情线）"}

{checkpoint_guidance}

# === 人物设定（含当前状态）===
{characters_formatted}

# === 故事结构定位 ===
当前阶段：{story_phase}
阶段说明：{phase_progress}

# === 剧情追踪 ===
最近3集剧情回顾：
{recent_summary}

关键揭示/反转：
{"\n".join(f"- {r}" for r in context.get("key_revelations", [])[-3:]) or "暂无重大揭示"}

待回收的悬念：
{"\n".join(f"- {h}" for h in context.get("pending_hooks", [])[-3:]) or "无待回收悬念"}

# === 本集信息 ===
集数：第{episode_number}集
剧情概要：{summary}
卡点要求：{hook}
本集定位：第{episode_number}集/共{total_episodes}集（{story_phase}阶段）
{"感情线进度：" + romance_progress if romance_line else ""}

# === 上一集结尾 ===
{previous_ending or "这是第1集，故事刚刚开始。"}

# === 创作指引 ===
1. **故事连贯性**：
   - 承接上一集结尾，自然过渡到本集开头
   - 关注"最近3集剧情回顾"，确保剧情连贯
   - 如有"待回收的悬念"，在本集适当回应

2. **人物一致性**：
   - 参考"人物当前状态"保持情绪和处境的连贯
   - 人物性格应与设定一致，避免突然降智或性格突变
   - 台词要符合人物当前情绪状态
   {"- 感情线角色互动必须符合感情线设计" if romance_line else ""}
   {"- 人物能力/行为必须符合世界观设定" if world_building else ""}

3. **风格与节奏**：
   - 当前处于"{story_phase}"阶段，{get_phase_instruction(story_phase)}
   - **风格基调**：{style_summary if style_summary else "快节奏爽文，强冲突"}
   - 本集必须有明确的剧情推进，无废戏
   - 情绪起伏要有层次，不能平淡
   {"- 感情线在本集要有相应进展" if romance_line else ""}

4. **卡点设置**：
   - 必须在结尾设置强钩子，符合大纲要求
   - 钩子要与本集剧情紧密相关，不能突兀
   {"- 付费卡点集必须设置最强悬念" if is_checkpoint_episode else ""}

# === 格式要求（严格遵守）===
1. **场景标注**：内景/外景-地点-日/夜
2. **人物标注**：人物名居中，标注情绪状态
3. **台词**：口语化、简短有力，符合人设，每句台词不超过30字
4. **动作描述**：简洁，包含镜头提示（如【特写】、【转场】）
5. **字数控制**：
   - 目标字数：1500-1800字
   - 硬性限制：必须在 1200-2000 字之间
   - 字数不足则扩充对话和动作描述
   - 字数过多则精简冗余对话
6. **卡点**：必须在结尾设置强钩子
{"7. **世界观一致性**：所有情节、人物能力必须符合世界观设定" if world_building else ""}
{"8. **感情线进展**：本集感情线应符合" + romance_progress + "的设定" if romance_line else ""}

# 剧本格式示例
第X集 集标题

场景：内景-办公室-日

人物：张三、李四

▶动作描述：张三猛拍桌子，文件飞散。【特写】愤怒的眼神

**张三（愤怒）：**
"你敢顶嘴？"

**李四（隐忍，双手握拳）：**
"老板，这不是我的错。"

▶动作描述：【转场】夜晚，李四独自走在街头

【本集卡点/钩子】
重大反转即将揭晓...

# 任务
请撰写第{episode_number}集的完整剧本。

要求：
1. 严格遵循大纲设定和卡点要求
2. 保持人物性格一致性和情绪连贯
3. 承接前文剧情，自然推进故事
4. 对话推动剧情，不要旁白过多
5. 情绪张力强，适合竖屏观看
6. 符合拍摄可行性，场景不要太复杂
{"7. 必须符合风格基调和世界观设定" if style_summary or world_building else ""}
{"8. 感情线进展必须自然，符合当前阶段设定" if romance_line else ""}

请直接输出剧本正文，使用上述格式。"""

        try:
            # 调用LLM（V1.1优化：增加字数校验与修正循环）
            llm_service = get_llm_service()
            content = await llm_service.generate_with_retry(prompt, max_tokens=3000)

            word_count = len(content)

            # V1.1新增：字数校验与自动修正循环
            # 目标字数：1500-1800字，硬性限制：1200-2000字
            max_retries = 2
            retry_count = 0

            while retry_count < max_retries:
                if 1500 <= word_count <= 1800:
                    # 字数完美，退出循环
                    break
                elif word_count < 1500:
                    # 字数不足，请求扩充
                    retry_count += 1
                    logger.info(f"第{episode_number}集字数不足（{word_count}字），尝试扩充（第{retry_count}次）")
                    expand_prompt = f"""以下剧本字数为{word_count}字，不足1500字。

请扩充以下剧本，要求：
1. 增加更多对话和动作描述
2. 增加场景细节和人物情绪描写
3. 保持原有剧情和风格
4. 扩充后字数达到1500-1800字

原剧本：
{content}

请直接输出扩充后的完整剧本，不要有任何解释。"""
                    content = await llm_service.generate_with_retry(expand_prompt, max_tokens=3000)
                    word_count = len(content)
                elif word_count > 2000:
                    # 字数过多，请求精简
                    retry_count += 1
                    logger.info(f"第{episode_number}集字数过多（{word_count}字），尝试精简（第{retry_count}次）")
                    trim_prompt = f"""以下剧本字数为{word_count}字，超过2000字。

请精简以下剧本，要求：
1. 删除冗余的对话和描述
2. 保留核心剧情和关键对话
3. 保持剧本的完整性
4. 精简后字数控制在1500-1800字

原剧本：
{content}

请直接输出精简后的完整剧本，不要有任何解释。"""
                    content = await llm_service.generate_with_retry(trim_prompt, max_tokens=3000)
                    word_count = len(content)
                elif word_count > 1800 and word_count <= 2000:
                    # 略多但在可接受范围内，退出循环
                    break

            # 质量检查（V1.1优化：调整字数标准）
            issues = []
            if word_count < 1200:
                issues.append(f"字数严重不足（{word_count}字），建议扩充到1500-1800字")
            elif word_count < 1500:
                issues.append(f"字数略少（{word_count}字），建议补充到1500-1800字")
            elif word_count > 2000:
                issues.append(f"字数过多（{word_count}字），建议精简到1500-1800字")
            if "场景：" not in content:
                issues.append("缺少场景标注")
            if "【本集卡点" not in content:
                issues.append("缺少卡点")

            # 更新上下文（人物状态、剧情追踪）
            context = update_character_statuses(context, content, characters)
            new_hooks, key_events, revelations = extract_hooks_and_events(content, outline)

            # 更新待回收悬念
            for hook_text in new_hooks:
                if hook_text not in context.get("pending_hooks", []):
                    context.setdefault("pending_hooks", []).append(hook_text)

            # 更新已揭示的秘密
            for rev in revelations:
                if rev not in context.get("key_revelations", []):
                    context.setdefault("key_revelations", []).append(rev)

            # 将已回收的悬念从pending移到resolved
            for pending in context.get("pending_hooks", [])[:]:
                if pending in summary or pending in content:
                    context.setdefault("resolved_hooks", []).append(pending)
                    context["pending_hooks"].remove(pending)

            scripts.append({
                "episode_number": episode_number,
                "title": f"第{episode_number}集",
                "content": content,
                "word_count": word_count,
                "status": "completed",
                "quality_report": {
                    "pass": len(issues) == 0,
                    "word_count": word_count,
                    "issues": issues,
                    "suggestions": []
                }
            })

            # 更新状态
            state["scripts"] = scripts
            state["script_context"] = context

            # 每5集保存一次上下文状态（防止中断丢失）
            if episode_number % 5 == 0:
                logger.info(f"[剧本生成] 第{episode_number}集完成，字数:{word_count}，上下文已更新")
                logger.info(f"  - 待回收悬念: {len(context.get('pending_hooks', []))}")
                logger.info(f"  - 关键揭示: {len(context.get('key_revelations', []))}")

        except Exception as e:
            logger.error(f"第{episode_number}集剧本生成失败: {e}")
            # 回退方案（V1.1优化：增加更合理的默认内容）
            fallback_content = f"""第{episode_number}集

场景：内景-办公室-日

人物：主角、反派

▶办公室内，阳光透过落地窗洒入。主角站在窗前，背影挺拔。

**主角（沉思）：**
"事情比我想象的更复杂。"

▶反派推门而入，脸上带着得意的笑容。

**反派（得意）：**
"怎么，还在为那件事烦恼？"

**主角（转身，眼神坚定）：**
"你以为这样就能打倒我？"

▶两人对峙，空气中弥漫着紧张的气氛。

【本集卡点】
{hook}

---
（此为生成失败的回退内容，请手动编辑或重新生成）
"""
            scripts.append({
                "episode_number": episode_number,
                "title": f"第{episode_number}集",
                "content": fallback_content,
                "word_count": len(fallback_content),
                "status": "completed",
                "quality_report": {
                    "pass": False,
                    "word_count": len(fallback_content),
                    "issues": ["生成失败，使用回退方案"],
                    "suggestions": ["请手动编辑或重新生成"]
                }
            })

    # 更新进度
    completed = sum(1 for s in scripts if s["status"] == "completed")
    state["scripts"] = scripts
    state["script_context"] = context
    state["creation_progress"] = {
        "step": "script",
        "status": "in_progress",
        "percentage": 30 + (completed / total_episodes * 60),
        "completed_episodes": completed,
        "total_episodes": total_episodes
    }

    return state


# ===== 质量检查节点 =====

def quality_checker_node(state: ScriptState) -> ScriptState:
    """
    质量检查节点

    检查已生成剧本的质量
    """
    scripts = state.get("scripts", [])

    for script in scripts:
        if script["status"] != "completed":
            continue

        issues = []
        suggestions = []

        # 字数检查
        word_count = script.get("word_count", 0)
        if word_count < 500:
            issues.append("字数不足，建议扩充到600-800字")
        elif word_count > 1000:
            issues.append("字数过多，建议精简到800字以内")

        # 格式检查
        content = script.get("content", "")
        if "场景：" not in content:
            issues.append("缺少场景标注")
        if "人物：" not in content:
            issues.append("缺少人物标注")

        # 卡点检查
        if "【本集卡点】" not in content:
            issues.append("缺少卡点/钩子")

        # 生成建议
        if not issues:
            suggestions.append("剧本格式规范，内容完整")
        else:
            suggestions.append("请根据 issues 修改")

        script["quality_report"] = {
            "pass": len(issues) == 0,
            "word_count": word_count,
            "issues": issues,
            "suggestions": suggestions
        }

    # 更新进度
    completed = sum(1 for s in scripts if s["status"] == "completed")
    total = len(scripts)

    state["creation_progress"] = {
        "step": "quality_check",
        "status": "completed",
        "percentage": 100,
        "completed_episodes": completed,
        "total_episodes": total
    }

    # 标记项目完成
    state["status"] = "completed"

    return state
