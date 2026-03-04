"""
需求澄清对话 API
"""
from typing import Optional
import uuid
import json

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from loguru import logger

from app.services.project import ProjectService
from app.agents.clarify.graph import run_clarify_step
from app.agents.clarify.nodes import (
    guidance_generator_node,
    options_generator_node,
    streaming_guidance_generator,
    streaming_options_generator,
    check_llm_configured,
    get_missing_fields,
    get_current_llm_config,
    check_requirement_completeness,
    generate_requirement_confirmation,
)
from app.agents.clarify.context_manager import update_all_context
from app.services.llm import LLMConfig, get_llm_service

router = APIRouter()


class ChatRequest(BaseModel):
    """对话请求"""
    message: str = Field(..., min_length=1, description="用户消息")
    type: str = Field(default="text", description="消息类型 (text/option/auto_fill)")


class ChatResponse(BaseModel):
    """对话响应"""
    message_id: str
    role: str
    content: str
    options: Optional[list] = None
    requirements_updated: Optional[dict] = None
    completeness: int
    status: str
    # V1.2 新增字段
    requirement_assessment: Optional[dict] = None
    understanding_display: Optional[dict] = None
    understanding_summary: Optional[str] = None  # 需求理解摘要（Markdown格式）
    pending_field: Optional[str] = None


@router.post("/{project_id}/chat", response_model=dict)
async def send_message(project_id: str, request: ChatRequest):
    """
    发送对话消息

    Args:
        project_id: 项目ID
        request: 对话请求
    """
    logger.info("=" * 60)
    logger.info(f"📨 [API] POST /{project_id}/chat - 收到请求")
    logger.info(f"📝 [API] 用户消息: {request.message[:100]}{'...' if len(request.message) > 100 else ''}")
    logger.info("=" * 60)

    # 获取项目
    project = ProjectService.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")

    # 检查状态
    if project.get("status") != "clarifying":
        raise HTTPException(status_code=400, detail="项目不在需求澄清阶段")

    # 添加用户消息
    user_message = {
        "role": "user",
        "content": request.message,
        "type": request.type
    }
    project["messages"].append(user_message)

    # 运行 ClarifyGraph
    try:
        logger.info("🔄 [API] 开始执行 ClarifyGraph...")
        result = await run_clarify_step(project)
        logger.info("✅ [API] ClarifyGraph 执行完成")
        # 更新项目
        ProjectService.update_project(project_id, result)
    except Exception as e:
        logger.error(f"ClarifyGraph 执行失败: {e}")
        raise HTTPException(status_code=500, detail="处理消息失败")

    # 获取最后一条助手消息
    messages = result.get("messages", [])
    last_assistant_msg = None
    for msg in reversed(messages):
        if msg["role"] == "assistant":
            last_assistant_msg = msg
            break

    if not last_assistant_msg:
        last_assistant_msg = {
            "role": "assistant",
            "content": "处理中...",
            "type": "text"
        }

    # 检查是否是 LLM 未配置的错误消息
    # 优先使用状态中的标记，这个标记只在当前请求未配置时设置
    is_llm_error = result.get("llm_not_configured", False)

    # 如果没有标记，只检查最后一条助手消息是否是错误类型
    # （避免历史错误消息影响当前请求）
    if not is_llm_error and last_assistant_msg:
        if last_assistant_msg.get("type") == "error":
            is_llm_error = True

    return {
        "code": 200,
        "message": "success",
        "data": {
            "message_id": f"msg_{uuid.uuid4().hex[:8]}",
            "role": "assistant",
            "content": last_assistant_msg["content"],
            "options": last_assistant_msg.get("options"),
            "requirements_updated": result.get("requirements"),
            "completeness": result.get("completeness", 0),
            "status": "locked" if result.get("requirements_locked") else "clarifying",
            "llm_not_configured": is_llm_error,
            # V1.2 新增字段
            "requirement_assessment": result.get("requirement_assessment"),
            "understanding_display": result.get("understanding_display"),
            "understanding_summary": result.get("understanding_summary"),
            "pending_field": result.get("pending_field")
        }
    }


@router.get("/{project_id}/messages", response_model=dict)
async def get_messages(
    project_id: str,
    before_id: Optional[str] = None,
    limit: int = 20
):
    """
    获取对话历史

    Args:
        project_id: 项目ID
        before_id: 起始消息ID（分页用）
        limit: 返回数量
    """
    project = ProjectService.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")

    messages = project.get("messages", [])

    # TODO: 实现分页逻辑

    return {
        "code": 200,
        "message": "success",
        "data": {
            "messages": messages,
            "has_more": False
        }
    }


class ConfirmRequirementsRequest(BaseModel):
    """确认需求请求"""
    confirmed: bool = True
    modifications: Optional[dict] = None


@router.get("/{project_id}/requirement-summary", response_model=dict)
async def get_requirement_summary(project_id: str):
    """
    获取优化后的需求确认书

    基于完整对话历史，由大模型汇总优化生成专业的需求确认书
    而不是直接展示用户的原始回答

    Args:
        project_id: 项目ID
    """
    project = ProjectService.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")

    # 检查 LLM 配置
    is_configured, error_message = check_llm_configured()
    if not is_configured:
        return {
            "code": 4001,
            "message": "LLM未配置",
            "data": None
        }

    messages = project.get("messages", [])
    if not messages:
        return {
            "code": 4002,
            "message": "对话历史为空",
            "data": None
        }

    try:
        # 初始化 LLM 服务
        config = get_current_llm_config()
        # 创建 LLM 配置 - 注意：这里使用用户配置，但需求确认书生成时会强制覆盖为4000
        raw_max_tokens = config.get("maxTokens", 4000)
        logger.info(f"🔧 [API] 用户配置 maxTokens={raw_max_tokens}")

        llm_config = LLMConfig(
            provider=config.get("provider", "tongyi"),
            api_key=config.get("apiKey"),
            api_base=config.get("apiBase") or None,
            model=config.get("model", "qwen-max"),
            temperature=config.get("temperature", 0.7),
            max_tokens=raw_max_tokens
        )
        llm_service = get_llm_service(llm_config)
        logger.info(f"🔧 [API] LLMService 创建完成，config.max_tokens={llm_service.config.max_tokens}")

        # 构建统一上下文
        requirements = project.get("requirements", {})

        # ===== V2.0: 使用混合架构生成确认书 =====
        confirmation = await generate_requirement_confirmation(
            messages=messages,
            llm_service=llm_service,
            core_requirements=requirements
        )

        # 将确认书中的关键信息更新到项目 requirements 中
        requirements["episodes"] = confirmation.get("episodes", "80")
        requirements["genre"] = confirmation.get("genre", requirements.get("genre", ""))
        structured_data = confirmation.get("structured_data", {})
        requirements["protagonist"] = structured_data.get("protagonist", {}).get("name", requirements.get("protagonist", ""))
        requirements["target_audience"] = confirmation.get("target_audience", requirements.get("target_audience", ""))
        requirements["style"] = confirmation.get("style_summary", requirements.get("style", ""))
        project["requirements"] = requirements

        # 保存确认书到项目
        project["requirement_confirmation"] = confirmation
        ProjectService.update_project(project_id, project)

        logger.info(f"✅ [API] 需求确认书V4生成成功，剧名: {confirmation.get('title', 'N/A')}")

        return {
            "code": 200,
            "message": "success",
            "data": {
                "confirmation": confirmation,
                "raw_requirements": requirements,
                "completeness": project.get("completeness", 0)
            }
        }
    except Exception as e:
        logger.error(f"生成需求确认书失败: {e}")
        raise HTTPException(status_code=500, detail=f"生成需求确认书失败: {str(e)}")


@router.post("/{project_id}/confirm-requirements", response_model=dict)
async def confirm_requirements(
    project_id: str,
    request: ConfirmRequirementsRequest
):
    """
    确认需求并启动创作

    Args:
        project_id: 项目ID
        confirmed: 是否确认
        modifications: 修改内容
    """
    project = ProjectService.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")

    if request.confirmed:
        # 锁定需求，进入创作阶段
        project["requirements_locked"] = True
        project["status"] = "creating"

        # 从需求中提取集数并设置到项目
        requirements = project.get("requirements", {})
        episodes = requirements.get("episodes", 80)
        try:
            project["total_episodes"] = int(episodes) if episodes else 80
        except (ValueError, TypeError):
            project["total_episodes"] = 80

        ProjectService.update_project(project_id, project)

        return {
            "code": 200,
            "message": "success",
            "data": {
                "status": "creating",
                "estimated_time": 1800  # 预计30分钟
            }
        }
    else:
        # 用户需要修改
        if request.modifications:
            requirements = project.get("requirements", {})
            requirements.update(request.modifications)
            project["requirements"] = requirements
            project["showed_summary"] = False
            ProjectService.update_project(project_id, project)

        return {
            "code": 200,
            "message": "success",
            "data": {
                "status": "clarifying"
            }
        }


@router.post("/{project_id}/regenerate-confirmation", response_model=dict)
async def regenerate_confirmation(project_id: str):
    """
    重新生成需求确认书

    基于最新的对话历史和需求，重新生成一份需求确认书。
    旧版本会保留在历史记录中（如需要可实现版本管理）。

    Args:
        project_id: 项目ID
    """
    project = ProjectService.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")

    # 检查 LLM 配置
    is_configured, error_message = check_llm_configured()
    if not is_configured:
        return {
            "code": 4001,
            "message": "LLM未配置",
            "data": None
        }

    messages = project.get("messages", [])
    if not messages:
        return {
            "code": 4002,
            "message": "对话历史为空",
            "data": None
        }

    try:
        # 初始化 LLM 服务
        config = get_current_llm_config()
        llm_config = LLMConfig(
            provider=config.get("provider", "tongyi"),
            api_key=config.get("apiKey"),
            api_base=config.get("apiBase") or None,
            model=config.get("model", "qwen-max"),
            temperature=config.get("temperature", 0.8),  # 重新生成时略微增加随机性
            max_tokens=config.get("maxTokens", 4000)
        )
        llm_service = get_llm_service(llm_config)

        # 获取当前需求
        requirements = project.get("requirements", {})

        # 保存旧版本到历史记录（可选）
        old_confirmation = project.get("requirement_confirmation")
        if old_confirmation:
            if "confirmation_history" not in project:
                project["confirmation_history"] = []
            project["confirmation_history"].append({
                "confirmation": old_confirmation,
                "saved_at": project.get("updated_at")
            })
            # 只保留最近3个版本
            project["confirmation_history"] = project["confirmation_history"][-3:]

        # ===== 使用生成器重新生成确认书 =====
        confirmation = await generate_requirement_confirmation(
            messages=messages,
            llm_service=llm_service,
            core_requirements=requirements
        )

        # 更新项目中的确认书
        project["requirement_confirmation"] = confirmation

        # 同时更新 requirements 中的关键字段
        requirements["episodes"] = confirmation.get("episodes", "80")
        requirements["genre"] = confirmation.get("genre", requirements.get("genre", ""))
        structured_data = confirmation.get("structured_data", {})
        requirements["protagonist"] = structured_data.get("protagonist", {}).get("name", requirements.get("protagonist", ""))
        requirements["target_audience"] = confirmation.get("target_audience", requirements.get("target_audience", ""))
        requirements["style"] = confirmation.get("style_summary", requirements.get("style", ""))
        project["requirements"] = requirements

        ProjectService.update_project(project_id, project)

        logger.info(f"✅ [API] 需求确认书已重新生成，剧名: {confirmation.get('title', 'N/A')}")

        return {
            "code": 200,
            "message": "success",
            "data": {
                "confirmation": confirmation,
                "raw_requirements": requirements,
                "completeness": project.get("completeness", 0)
            }
        }
    except Exception as e:
        logger.error(f"重新生成需求确认书失败: {e}")
        raise HTTPException(status_code=500, detail=f"重新生成需求确认书失败: {str(e)}")


# ===== 流式对话 API =====

class StreamChatRequest(BaseModel):
    """流式对话请求"""
    message: str = Field(..., min_length=1, description="用户消息")
    type: str = Field(default="text", description="消息类型 (text/option/auto_fill)")


async def stream_chat_response(project_id: str, project: dict, user_message: dict):
    """
    真正实时的流式生成对话响应

    架构：
    1. 意图分析（非流式）- 必须等待结构化结果
    2. 引导/选项生成（流式）- LLM实时生成，即时推送到前端
    """
    import asyncio
    from app.agents.clarify.nodes import intent_analyzer_node

    logger.info("🌊 [流式] stream_chat_response 开始执行")

    # 添加用户消息
    messages = project.get("messages", [])
    messages.append(user_message)
    project["messages"] = messages
    logger.info(f"🌊 [流式] 用户消息已添加，当前消息数: {len(messages)}")

    # 检查 LLM 配置
    is_configured, error_message = check_llm_configured()
    if not is_configured:
        yield f"data: {json.dumps({'type': 'error', 'content': error_message}, ensure_ascii=False)}\n\n"
        return

    # 第一步：运行意图分析节点（非流式，需要结构化输出）
    try:
        logger.info("🌊 [流式] 开始意图分析...")
        result = await intent_analyzer_node(project)
        logger.info(f"🌊 [流式] 意图分析完成，意图类型: {result.get('last_intent') or 'unknown'}")
    except Exception as e:
        logger.error(f"🌊 [流式] 意图分析失败: {e}")
        yield f"data: {json.dumps({'type': 'error', 'content': '分析用户意图失败'}, ensure_ascii=False)}\n\n"
        return

    # 检查是否已锁定需求
    if result.get("requirements_locked"):
        # 需求已锁定，直接返回确认书
        yield f"data: {json.dumps({'type': 'metadata', 'completeness': 100, 'status': 'locked'}, ensure_ascii=False)}\n\n"
        yield f"data: {json.dumps({'type': 'content', 'content': '需求已确认！点击下方按钮开始创作。', 'is_complete': True}, ensure_ascii=False)}\n\n"
        yield f"data: {json.dumps({'type': 'done'}, ensure_ascii=False)}\n\n"
        ProjectService.update_project(project_id, result)
        return

    # 发送元数据（完整度、状态等）
    metadata = {
        "type": "metadata",
        "completeness": result.get("completeness", 0),
        "status": "clarifying",
        "requirements_updated": result.get("requirements"),
        # V1.2 新增字段
        "requirement_assessment": result.get("requirement_assessment"),
        "understanding_display": result.get("understanding_display"),
        "understanding_summary": result.get("understanding_summary"),
        "pending_field": result.get("pending_field")
    }
    yield f"data: {json.dumps(metadata, ensure_ascii=False)}\n\n"

    # 第二步：根据意图选择流式生成方式
    need_options = result.get("need_options", False)

    # 定义流式回调函数
    async def on_chunk(chunk: str, full_content: str, is_complete: bool):
        """每个token生成时立即发送"""
        data = {
            "type": "content",
            "content": full_content,
            "chunk": chunk,
            "is_complete": is_complete
        }
        yield f"data: {json.dumps(data, ensure_ascii=False)}\n\n"
        # 强制刷新缓冲区，确保实时发送
        await asyncio.sleep(0)

    try:
        if need_options:
            # 流式生成选项
            logger.info("开始流式生成选项...")

            # 手动管理流式输出
            from app.agents.clarify.nodes import (
                STREAMING_OPTIONS_PROMPT, CLARIFY_SYSTEM_PROMPT,
                parse_options_from_text, format_messages_for_prompt
            )

            pending_field = result.get("pending_field", "")
            requirements = result.get("requirements", {})
            messages_history = result.get("messages", [])
            context = format_messages_for_prompt(messages_history, max_messages=6)

            prompt = STREAMING_OPTIONS_PROMPT.format(
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

            full_content = ""
            async for chunk in llm_service.generate_stream(
                prompt,
                system_prompt=CLARIFY_SYSTEM_PROMPT,
                max_tokens=800
            ):
                full_content += chunk
                data = {
                    "type": "content",
                    "content": full_content,
                    "chunk": chunk,
                    "is_complete": False
                }
                yield f"data: {json.dumps(data, ensure_ascii=False)}\n\n"
                await asyncio.sleep(0)  # 让出控制权，确保实时发送

            # 完成
            options = parse_options_from_text(full_content)
            data = {
                "type": "content",
                "content": full_content,
                "is_complete": True,
                "options": options
            }
            yield f"data: {json.dumps(data, ensure_ascii=False)}\n\n"

            # 更新状态
            message = {
                "role": "assistant",
                "content": full_content,
                "type": "option",
                "options": options
            }
            messages_history.append(message)
            result["messages"] = messages_history
            result["need_options"] = False

        else:
            # 流式生成引导问题
            logger.info("开始流式生成引导问题...")

            from app.agents.clarify.nodes import (
                STREAMING_GUIDANCE_PROMPT, CLARIFY_SYSTEM_PROMPT,
                get_missing_fields, format_messages_for_prompt
            )

            raw_requirements = result.get("requirements", {})
            requirements = {k.strip(): v for k, v in raw_requirements.items() if isinstance(k, str)} if isinstance(raw_requirements, dict) else {}
            missing_fields = get_missing_fields(requirements)

            priority = ["genre", "protagonist", "conflict", "target_audience", "episodes", "style"]
            next_field = None
            for field in priority:
                if field in missing_fields:
                    next_field = field
                    break
            if not next_field:
                next_field = missing_fields[0] if missing_fields else ""

            messages_history = result.get("messages", [])
            context = format_messages_for_prompt(messages_history, max_messages=8)

            prompt = STREAMING_GUIDANCE_PROMPT.format(
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

            full_content = ""
            async for chunk in llm_service.generate_stream(
                prompt,
                system_prompt=CLARIFY_SYSTEM_PROMPT,
                max_tokens=500
            ):
                full_content += chunk
                data = {
                    "type": "content",
                    "content": full_content,
                    "chunk": chunk,
                    "is_complete": False
                }
                yield f"data: {json.dumps(data, ensure_ascii=False)}\n\n"
                await asyncio.sleep(0)

            # 确保引导语
            if "如果您没有主意" not in full_content:
                extra = " 如果您没有主意，回复'给我建议'我来帮您。"
                full_content += extra
                data = {
                    "type": "content",
                    "content": full_content,
                    "chunk": extra,
                    "is_complete": True
                }
                yield f"data: {json.dumps(data, ensure_ascii=False)}\n\n"
            else:
                data = {
                    "type": "content",
                    "content": full_content,
                    "is_complete": True
                }
                yield f"data: {json.dumps(data, ensure_ascii=False)}\n\n"

            # 更新状态
            message = {
                "role": "assistant",
                "content": full_content,
                "type": "text"
            }
            messages_history.append(message)
            result["messages"] = messages_history
            result["pending_field"] = next_field

    except Exception as e:
        logger.error(f"流式生成失败: {e}")
        yield f"data: {json.dumps({'type': 'error', 'content': f'生成回复失败: {str(e)}'}, ensure_ascii=False)}\n\n"
        return

    # ===== V1.3 异步上下文更新 =====
    # 先发送 done 标记，让用户可以继续输入（前端 isLoading = false）
    yield f"data: {json.dumps({'type': 'done'}, ensure_ascii=False)}\n\n"

    # 更新项目状态（先保存基本状态）
    ProjectService.update_project(project_id, result)

    # ===== V1.3 异步评估 + 实时推送 =====
    # 评估需求收集进度并推送到前端
    try:
        from app.agents.clarify.nodes import assess_progress_after_response
        logger.info("📊 [流式] 开始异步评估需求进度...")
        assessment_result = await assess_progress_after_response(result)

        # 更新状态中的评估结果
        result["completeness"] = assessment_result.get("completeness", result.get("completeness", 0))
        result["requirement_assessment"] = assessment_result.get("requirement_assessment")

        # 发送 assessment_update 事件到前端
        assessment_update = {
            "type": "assessment_update",
            "completeness": assessment_result.get("completeness", 0),
            "requirement_assessment": assessment_result.get("requirement_assessment")
        }
        yield f"data: {json.dumps(assessment_update, ensure_ascii=False)}\n\n"
        logger.info(f"📊 [流式] 评估已推送，完整度: {assessment_result.get('completeness')}%")

        # 保存更新后的状态
        ProjectService.update_project(project_id, result)

    except Exception as e:
        logger.warning(f"📊 [流式] 评估失败（不影响主流程）: {e}")

    # ===== 后台更新上下文（不推送到前端，用户主动获取时再显示） =====
    try:
        logger.info("🔄 [流式] 开始更新统一上下文（后台）...")
        result = await update_all_context(result)
        logger.info("✅ [流式] 统一上下文更新完成")

        # 保存更新后的状态（包括 understanding_summary）
        ProjectService.update_project(project_id, result)
        logger.info("📤 [流式] 上下文已更新，用户可主动获取分析详情")
    except Exception as e:
        logger.warning(f"更新上下文失败（不影响主流程）: {e}")


@router.post("/{project_id}/chat/stream")
async def send_message_stream(project_id: str, request: StreamChatRequest):
    """
    发送对话消息（流式响应）

    使用 Server-Sent Events (SSE) 实现流式输出
    """
    logger.info("=" * 60)
    logger.info(f"📨 [API] POST /{project_id}/chat/stream - 收到流式请求")
    logger.info(f"📝 [API] 用户消息: {request.message[:100]}{'...' if len(request.message) > 100 else ''}")
    logger.info("=" * 60)

    # 获取项目
    project = ProjectService.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")

    # 检查状态
    if project.get("status") != "clarifying":
        raise HTTPException(status_code=400, detail="项目不在需求澄清阶段")

    # 构建用户消息
    user_message = {
        "role": "user",
        "content": request.message,
        "type": request.type
    }

    return StreamingResponse(
        stream_chat_response(project_id, project, user_message),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"  # 禁用 Nginx 缓冲
        }
    )


@router.get("/{project_id}/requirement-analysis", response_model=dict)
async def get_requirement_analysis(project_id: str):
    """
    获取需求分析详情（用户主动点击时调用）

    返回最新的需求理解摘要（Markdown格式）和相关信息
    """
    logger.info(f"📋 [API] GET /{project_id}/requirement-analysis - 获取需求分析")

    project = ProjectService.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")

    # 检查 LLM 配置
    is_configured, error_message = check_llm_configured()
    if not is_configured:
        return {
            "code": 4001,
            "message": "LLM未配置",
            "data": None
        }

    # 如果已有 understanding_summary，直接返回
    existing_summary = project.get("understanding_summary")
    if existing_summary:
        logger.info(f"📋 [API] 返回已缓存的需求分析")
        return {
            "code": 200,
            "message": "success",
            "data": {
                "understanding_summary": existing_summary,
                "requirement_analysis": project.get("requirement_analysis"),
                "conversation_summary": project.get("conversation_summary"),
                "understanding_display": project.get("understanding_display"),
                "completeness": project.get("completeness", 0)
            }
        }

    # 如果没有，尝试生成（后台更新可能还没完成，或者用户第一次请求）
    try:
        logger.info("📋 [API] 未找到缓存，尝试生成需求分析...")
        result = await update_all_context(project)

        # 保存更新
        ProjectService.update_project(project_id, result)

        return {
            "code": 200,
            "message": "success",
            "data": {
                "understanding_summary": result.get("understanding_summary"),
                "requirement_analysis": result.get("requirement_analysis"),
                "conversation_summary": result.get("conversation_summary"),
                "understanding_display": result.get("understanding_display"),
                "completeness": result.get("completeness", 0)
            }
        }
    except Exception as e:
        logger.error(f"生成需求分析失败: {e}")
        raise HTTPException(status_code=500, detail=f"生成需求分析失败: {str(e)}")
