import { useState, useEffect, useRef } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { useProjectStore } from '../../stores/projectStore'
import ReactMarkdown from 'react-markdown'
import {
  Send, Lightbulb, CheckCircle2, Circle, Clock,
  X, Brain
} from 'lucide-react'
import type { Option } from '../../types'

// 真实 API 调用（非流式）
const chatAPI = async (projectId: string, message: string): Promise<any> => {
  const response = await fetch(`/api/v1/projects/${projectId}/chat`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ message, type: 'text' }),
  })

  if (!response.ok) {
    throw new Error(`HTTP error! status: ${response.status}`)
  }

  return await response.json()
}

// 流式 API 调用
const chatAPIStream = (
  projectId: string,
  message: string,
  callbacks: {
    onContent: (content: string, isComplete: boolean) => void
    onMetadata: (metadata: any) => void
    onError: (error: string) => void
    onDone: () => void
    onAssessmentUpdate?: (data: any) => void  // V1.3 新增：评估更新（实时推送）
  }
): (() => void) => {
  const abortController = new AbortController()

  fetch(`/api/v1/projects/${projectId}/chat/stream`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ message, type: 'text' }),
    signal: abortController.signal,
  }).then(async (response) => {
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`)
    }

    const reader = response.body?.getReader()
    if (!reader) {
      throw new Error('No response body')
    }

    const decoder = new TextDecoder()
    let buffer = ''

    while (true) {
      const { done, value } = await reader.read()
      if (done) break

      buffer += decoder.decode(value, { stream: true })
      const lines = buffer.split('\n\n')
      buffer = lines.pop() || ''

      for (const line of lines) {
        if (line.startsWith('data: ')) {
          try {
            const data = JSON.parse(line.slice(6))

            if (data.type === 'content') {
              callbacks.onContent(data.content, data.is_complete)
            } else if (data.type === 'metadata') {
              callbacks.onMetadata(data)
            } else if (data.type === 'error') {
              callbacks.onError(data.content)
            } else if (data.type === 'assessment_update') {
              // V1.3 新增：处理评估更新（实时推送完整度和评估）
              if (callbacks.onAssessmentUpdate) {
                callbacks.onAssessmentUpdate(data)
              }
            } else if (data.type === 'done') {
              callbacks.onDone()
            }
          } catch (e) {
            console.error('解析 SSE 数据失败:', e)
          }
        }
      }
    }
  }).catch((error) => {
    if (error.name !== 'AbortError') {
      callbacks.onError(error.message)
    }
  })

  return () => abortController.abort()
}

// 需求字段配置
const REQUIREMENT_FIELDS = [
  { key: 'genre', label: '题材类型', icon: '🎭' },
  { key: 'protagonist', label: '主角设定', icon: '👤' },
  { key: 'conflict', label: '核心冲突', icon: '⚔️' },
  { key: 'target_audience', label: '目标受众', icon: '👥' },
  { key: 'episodes', label: '集数', icon: '📺' },
  { key: 'style', label: '风格基调', icon: '🎨' },
]

// 子字段到主字段的映射（与后端保持一致）
const SUBFIELD_MAPPING: Record<string, string[]> = {
  genre: ['genre', '题材类型'],
  protagonist: [
    'protagonist', 'protagonist_identity', 'protagonist_traits',
    'protagonist_goal', 'protagonist_occupation', 'protagonist_style',
    '主角', '主角设定'
  ],
  conflict: [
    'conflict', 'core_conflict', 'system_binding_reason',
    'system_operation_mode', '穿越原因', '绑定系统'
  ],
  target_audience: ['target_audience', '目标受众', '受众'],
  episodes: ['episodes', '集数'],
  style: ['style', '风格', '风格基调']
}

// 检查字段是否已填充（支持子字段检测）
function hasFieldValue(requirements: Record<string, any>, fieldKey: string): boolean {
  // 先检查主字段
  if (requirements[fieldKey]) {
    return true
  }
  // 检查子字段
  const subfields = SUBFIELD_MAPPING[fieldKey]
  if (subfields) {
    return subfields.some(sf => requirements[sf])
  }
  return false
}

// 获取字段的显示值（优先主字段，否则拼接子字段）
function getFieldDisplayValue(requirements: Record<string, any>, fieldKey: string): string | null {
  // 优先返回主字段值
  if (requirements[fieldKey]) {
    return String(requirements[fieldKey])
  }
  // 拼接子字段值
  const subfields = SUBFIELD_MAPPING[fieldKey]
  if (subfields) {
    const values = subfields
      .filter(sf => sf !== fieldKey && requirements[sf])
      .map(sf => requirements[sf])
    if (values.length > 0) {
      return values.slice(0, 2).join('，') + (values.length > 2 ? '...' : '')
    }
  }
  return null
}

// 获取需求分析 API
const fetchRequirementAnalysis = async (projectId: string): Promise<any> => {
  const response = await fetch(`/api/v1/projects/${projectId}/requirement-analysis`, {
    method: 'GET',
    headers: {
      'Content-Type': 'application/json',
    },
  })

  if (!response.ok) {
    throw new Error(`HTTP error! status: ${response.status}`)
  }

  return await response.json()
}

// 详情弹窗组件 - 显示需求分析详情（Markdown格式）
interface DetailModalProps {
  project: any
  onClose: () => void
}

function DetailModal({ project, onClose }: DetailModalProps) {
  const understandingSummary = project.understandingSummary

  // 如果有 Markdown 摘要，渲染摘要；否则显示空状态
  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4" onClick={onClose}>
      <div
        className="bg-white rounded-2xl shadow-xl max-w-2xl w-full max-h-[80vh] overflow-hidden flex flex-col"
        onClick={e => e.stopPropagation()}
      >
        {/* 头部 */}
        <div className="flex items-center justify-between p-4 border-b bg-gray-50">
          <div className="flex items-center gap-3">
            <Brain className="w-6 h-6 text-primary" />
            <h3 className="text-lg font-semibold">📋 需求分析详情</h3>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="p-1 hover:bg-gray-200 rounded-full transition-colors"
            aria-label="关闭"
          >
            <X className="w-5 h-5 text-gray-500" />
          </button>
        </div>

        {/* 内容 */}
        <div className="flex-1 overflow-y-auto p-6">
          {understandingSummary ? (
            <article className="prose prose-sm max-w-none prose-headings:text-gray-800 prose-headings:font-semibold prose-h2:text-lg prose-h2:mt-6 prose-h2:mb-3 prose-h3:text-base prose-h3:mt-4 prose-h3:mb-2 prose-p:text-gray-600 prose-li:text-gray-600 prose-strong:text-gray-800">
              <ReactMarkdown>{understandingSummary}</ReactMarkdown>
            </article>
          ) : (
            <div className="flex flex-col items-center justify-center py-12 text-gray-400">
              <Brain className="w-12 h-12 mb-4 opacity-50" />
              <p className="text-lg mb-2">暂无需求分析</p>
              <p className="text-sm">开始对话后，AI 会自动生成需求分析报告</p>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

// 右侧边栏组件 - 单卡片形式
interface SidebarProps {
  project: any
  onViewAnalysis: () => void  // 查看需求分析详情
  isLoadingAnalysis: boolean  // 是否正在加载分析
  hasAnalysis: boolean        // 是否已有分析（决定按钮是否可用）
}

function RequirementSidebar({ project, onViewAnalysis, isLoadingAnalysis, hasAnalysis }: SidebarProps) {
  const requirements = project.requirements || {}
  const completeness = project.completeness || 0
  const assessment = project.requirementAssessment || {}

  // 使用子字段检测计算已完成数量
  const completedCount = REQUIREMENT_FIELDS.filter(f => hasFieldValue(requirements, f.key)).length

  // 获取每个字段的状态摘要
  const getFieldSummary = () => {
    return REQUIREMENT_FIELDS.map(field => {
      const fieldAssessment = assessment[field.key] || {}
      // 检查主字段或子字段
      const hasValue = hasFieldValue(requirements, field.key)
      const value = getFieldDisplayValue(requirements, field.key)
      const status = fieldAssessment.status || (hasValue ? 'confirmed' : 'empty')
      const shortValue = value
        ? (typeof value === 'string' ? value.slice(0, 20) + (value.length > 20 ? '...' : '') : String(value))
        : null

      return {
        ...field,
        status,
        shortValue
      }
    })
  }

  const fieldSummaries = getFieldSummary()

  return (
    <div className="w-80 border-l bg-gray-50 flex flex-col h-full overflow-hidden">
      {/* 进度区域 */}
      <div className="p-4 border-b bg-white">
        <h3 className="text-sm font-medium text-gray-700 mb-3">📊 需求收集进度</h3>

        {/* 进度条 */}
        <div className="flex items-center gap-3 mb-3">
          <div className="relative w-14 h-14">
            <svg className="w-14 h-14 transform -rotate-90">
              <circle
                cx="28"
                cy="28"
                r="24"
                stroke="#e5e7eb"
                strokeWidth="4"
                fill="none"
              />
              <circle
                cx="28"
                cy="28"
                r="24"
                stroke={completeness >= 80 ? '#22c55e' : '#4A90E2'}
                strokeWidth="4"
                fill="none"
                strokeDasharray={`${completeness * 1.507} 150.7`}
                strokeLinecap="round"
                className="transition-all duration-500"
              />
            </svg>
            <span className="absolute inset-0 flex items-center justify-center text-sm font-bold">
              {completeness}%
            </span>
          </div>
          <div className="flex-1">
            <p className="text-sm text-gray-600">
              已收集 <span className="font-semibold text-primary">{completedCount}</span>/6 项
            </p>
            <p className="text-xs text-gray-400 mt-1">
              {completeness >= 80 ? '✓ 可生成确认书' : '继续完善需求...'}
            </p>
          </div>
        </div>
      </div>

      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {/* 需求完整性评估卡片 */}
        <div className="bg-white rounded-xl border border-gray-200 p-4">
          {/* 卡片标题 */}
          <div className="flex items-center gap-2 mb-3">
            <CheckCircle2 className="w-5 h-5 text-primary" />
            <span className="font-medium text-gray-800">需求完整性评估</span>
          </div>

          {/* 字段状态列表 */}
          <div className="space-y-2">
            {fieldSummaries.map(field => (
              <div key={field.key} className="flex items-center gap-2 text-sm">
                <span className="text-base">{field.icon}</span>
                <span className="text-gray-500 w-16">{field.label}</span>
                {field.status === 'confirmed' ? (
                  <>
                    <span className="flex-1 text-gray-700 truncate">{field.shortValue}</span>
                    <CheckCircle2 className="w-4 h-4 text-green-500 flex-shrink-0" />
                  </>
                ) : field.status === 'partial' ? (
                  <>
                    <span className="flex-1 text-gray-400">部分确认</span>
                    <Clock className="w-4 h-4 text-yellow-500 flex-shrink-0" />
                  </>
                ) : (
                  <>
                    <span className="flex-1 text-gray-300">待确认</span>
                    <Circle className="w-4 h-4 text-gray-300 flex-shrink-0" />
                  </>
                )}
              </div>
            ))}
          </div>
        </div>

        {/* 需求分析详情卡片 */}
        <div className="bg-white rounded-xl border border-gray-200 p-4">
          {/* 卡片标题 */}
          <div className="flex items-center gap-2 mb-3">
            <Brain className="w-5 h-5 text-primary" />
            <span className="font-medium text-gray-800">需求分析详情</span>
          </div>

          {/* 分析状态 */}
          {hasAnalysis ? (
            <div className="text-sm text-gray-600 mb-3">
              AI 已完成需求分析，点击查看详细报告
            </div>
          ) : (
            <div className="text-sm text-gray-400 mb-3">
              开始对话后，点击按钮获取需求分析
            </div>
          )}

          {/* 查看详情按钮 */}
          <button
            type="button"
            onClick={onViewAnalysis}
            disabled={isLoadingAnalysis}
            className="w-full py-2 px-4 rounded-lg bg-primary/10 text-primary text-sm font-medium hover:bg-primary/20 transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
          >
            {isLoadingAnalysis ? (
              <>
                <span className="animate-spin">⏳</span>
                <span>正在获取分析...</span>
              </>
            ) : (
              <>
                <span>📋</span>
                <span>查看需求分析详情</span>
              </>
            )}
          </button>
        </div>
      </div>
    </div>
  )
}

function ClarifyPage() {
  const navigate = useNavigate()
  const { id } = useParams<{ id: string }>()
  const { getProject, updateProject, addMessage, fetchProject } = useProjectStore()
  const project = getProject(id || '')

  const [inputMessage, setInputMessage] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [pageLoading, setPageLoading] = useState(true)
  const messagesEndRef = useRef<HTMLDivElement>(null)

  // 详情弹窗状态
  const [showDetail, setShowDetail] = useState(false)
  // 需求分析加载状态
  const [isLoadingAnalysis, setIsLoadingAnalysis] = useState(false)

  // 页面加载时从后端获取完整项目数据
  useEffect(() => {
    if (id) {
      console.log('[ClarifyPage] Loading project:', id)
      fetchProject(id).then((project) => {
        console.log('[ClarifyPage] Loaded project:', project?.id, 'messages:', project?.messages?.length)
        setPageLoading(false)
      })
    }
  }, [id])

  // 自动滚动到最新消息
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [project?.messages])

  if (pageLoading) {
    return (
      <div className="card text-center py-12">
        <p className="text-gray-500">加载中...</p>
      </div>
    )
  }

  if (!project) {
    return (
      <div className="card text-center py-12">
        <p className="text-gray-500">项目不存在</p>
        <a href="#/" className="btn-primary mt-4 inline-block">
          返回首页
        </a>
      </div>
    )
  }

  // 是否使用流式输出
  const useStreaming = true

  const handleSendMessage = async () => {
    if (!inputMessage.trim() || isLoading) return

    const message = inputMessage.trim()
    setInputMessage('')
    setIsLoading(true)

    // 添加用户消息到本地状态
    addMessage(project.id, {
      role: 'user',
      content: message,
      type: 'text'
    })

    if (useStreaming) {
      // 流式输出模式
      chatAPIStream(project.id, message, {
        onContent: (content, _isComplete) => {
          const currentProject = getProject(project.id)
          if (currentProject) {
            const messages = [...currentProject.messages]
            const lastMsg = messages[messages.length - 1]

            if (lastMsg && lastMsg.role === 'assistant') {
              // 更新已有消息内容
              messages[messages.length - 1] = {
                ...lastMsg,
                content: content
              }
            } else {
              // 添加新的助手消息
              messages.push({
                id: `msg_${Date.now()}`,
                role: 'assistant',
                content: content,
                type: 'text',
                createdAt: new Date().toISOString()
              })
            }
            updateProject(project.id, { messages })
          }
        },
        onMetadata: (metadata) => {
          if (metadata.completeness !== undefined) {
            const updates: any = {
              completeness: metadata.completeness,
              requirements: metadata.requirements_updated || project.requirements
            }
            // V1.2 新增字段
            if (metadata.requirement_assessment) {
              updates.requirementAssessment = metadata.requirement_assessment
            }
            if (metadata.understanding_display) {
              updates.understandingDisplay = metadata.understanding_display
            }
            if (metadata.understanding_summary) {
              updates.understandingSummary = metadata.understanding_summary
            }
            if (metadata.pending_field) {
              updates.pendingField = metadata.pending_field
            }
            updateProject(project.id, updates)
          }
        },
        onError: (error) => {
          console.error('流式输出错误:', error)
          addMessage(project.id, {
            role: 'assistant',
            content: `服务调用失败: ${error}`,
            type: 'error'
          })
          setIsLoading(false)
        },
        onDone: () => {
          setIsLoading(false)
        },
        // V1.3 新增：处理评估更新（异步推送）
        onAssessmentUpdate: (data) => {
          console.log('[ClarifyPage] 收到评估更新:', data)
          const updates: any = {}
          if (data.completeness !== undefined) {
            updates.completeness = data.completeness
          }
          if (data.requirement_assessment) {
            updates.requirementAssessment = data.requirement_assessment
          }
          if (Object.keys(updates).length > 0) {
            updateProject(project.id, updates)
          }
        }
      })
    } else {
      // 非流式模式
      try {
        const response = await chatAPI(project.id, message)

        if (response.code === 200) {
          const { data } = response

          if (data.llm_not_configured) {
            addMessage(project.id, {
              role: 'assistant',
              content: data.content,
              type: 'error'
            })
          } else {
            addMessage(project.id, {
              role: 'assistant',
              content: data.content,
              type: data.options ? 'option' : 'text',
              options: data.options
            })

            const updates: any = {}
            if (data.completeness !== undefined) {
              updates.completeness = data.completeness
              updates.requirements = data.requirements_updated || project.requirements
            }
            // V1.2 新增字段
            if (data.requirement_assessment) {
              updates.requirementAssessment = data.requirement_assessment
            }
            if (data.understanding_display) {
              updates.understandingDisplay = data.understanding_display
            }
            if (data.understanding_summary) {
              updates.understandingSummary = data.understanding_summary
            }
            if (data.pending_field) {
              updates.pendingField = data.pending_field
            }
            if (Object.keys(updates).length > 0) {
              updateProject(project.id, updates)
            }
          }
        }
      } catch (error) {
        console.error('发送消息失败:', error)
        addMessage(project.id, {
          role: 'assistant',
          content: '服务调用失败，请检查后端是否正常运行',
          type: 'error'
        })
      } finally {
        setIsLoading(false)
      }
    }
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSendMessage()
    }
  }

  const handleOptionClick = (option: Option) => {
    setInputMessage(option.title)
    setTimeout(() => handleSendMessage(), 0)
  }

  const handleGetSuggestions = () => {
    setInputMessage('给我建议')
    handleSendMessage()
  }

  // 处理查看需求分析 - 主动从后端获取
  const handleViewAnalysis = async () => {
    if (!id || isLoadingAnalysis) return

    setIsLoadingAnalysis(true)
    try {
      console.log('[ClarifyPage] 正在获取需求分析...')
      const response = await fetchRequirementAnalysis(id)

      if (response.code === 200 && response.data) {
        const updates: any = {}
        if (response.data.understanding_summary) {
          updates.understandingSummary = response.data.understanding_summary
        }
        if (response.data.requirement_analysis) {
          updates.requirementAnalysis = response.data.requirement_analysis
        }
        if (response.data.conversation_summary) {
          updates.conversationSummary = response.data.conversation_summary
        }
        if (response.data.understanding_display) {
          updates.understandingDisplay = response.data.understanding_display
        }
        if (Object.keys(updates).length > 0) {
          updateProject(id, updates)
          console.log('[ClarifyPage] 已更新需求分析:', updates)
        }
        // 显示弹窗
        setShowDetail(true)
      } else {
        console.error('[ClarifyPage] 获取需求分析失败:', response.message)
      }
    } catch (error) {
      console.error('[ClarifyPage] 获取需求分析失败:', error)
    } finally {
      setIsLoadingAnalysis(false)
    }
  }

  return (
    <div className="h-[calc(100vh-140px)] flex flex-col">
      {/* 头部 */}
      <div className="card mb-4 p-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-4">
            <h2 className="text-lg font-semibold">{project.name}</h2>
            <span className="text-sm text-gray-400">需求澄清</span>
          </div>

          <button
            type="button"
            disabled={project.completeness < 80}
            className="btn-primary text-sm disabled:opacity-50 disabled:cursor-not-allowed"
            onClick={() => navigate(`/project/${id}/confirm`)}
          >
            {project.completeness >= 80 ? '生成需求确认书 →' : '继续完善需求...'}
          </button>
        </div>
      </div>

      {/* 主体区域 - 两栏布局 */}
      <div className="flex-1 flex min-h-0">
        {/* 左侧对话区域 */}
        <div className="flex-1 flex flex-col min-w-0">
          <div className="card flex-1 flex flex-col overflow-hidden">
            {/* 对话区域 */}
            <div className="flex-1 overflow-y-auto p-6 space-y-4">
              {project.messages.map((msg, index) => (
                <div
                  key={index}
                  className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
                >
                  <div
                    className={`max-w-[75%] rounded-2xl px-4 py-3 ${
                      msg.role === 'user'
                        ? 'bg-primary text-white rounded-br-md'
                        : 'bg-gray-100 text-gray-800 rounded-bl-md'
                    }`}
                  >
                    <p className="whitespace-pre-wrap leading-relaxed">{msg.content}</p>

                    {/* 选项按钮 */}
                    {msg.options && msg.options.length > 0 && (
                      <div className="mt-3 space-y-2">
                        {msg.options.map((option) => (
                          <button
                            type="button"
                            key={option.id}
                            onClick={() => handleOptionClick(option)}
                            className="w-full text-left p-3 rounded-xl bg-white/80 hover:bg-white border border-gray-200 hover:border-primary/30 transition-all group"
                          >
                            <span className="font-medium text-gray-800 group-hover:text-primary">
                              {option.id}. {option.title}
                            </span>
                            {option.description && (
                              <span className="text-sm text-gray-500 ml-2">- {option.description}</span>
                            )}
                          </button>
                        ))}
                      </div>
                    )}
                  </div>
                </div>
              ))}
              <div ref={messagesEndRef} />
            </div>

            {/* 输入区域 */}
            <div className="border-t p-4 bg-gray-50/50">
              {/* 建议按钮 - 左对齐在输入框上方 */}
              <div className="mb-2">
                <button
                  type="button"
                  onClick={handleGetSuggestions}
                  disabled={isLoading}
                  className="flex items-center gap-1.5 px-3 py-2 text-sm text-gray-600 hover:text-primary hover:bg-white rounded-lg border border-gray-200 hover:border-primary/30 transition-all disabled:opacity-50"
                  title="获取AI建议"
                >
                  <Lightbulb className="w-4 h-4" />
                  <span>给我建议</span>
                </button>
              </div>

              {/* 输入框和发送按钮 */}
              <div className="flex gap-3 items-end">
                {/* 输入框 - 3行高度 */}
                <div className="flex-1 relative">
                  <textarea
                    value={inputMessage}
                    onChange={(e) => setInputMessage(e.target.value)}
                    onKeyDown={handleKeyDown}
                    placeholder="输入您的想法..."
                    className="w-full px-4 py-3 rounded-xl border border-gray-200 focus:border-primary focus:ring-2 focus:ring-primary/20 resize-none transition-all"
                    style={{ height: '96px', minHeight: '96px' }}
                    disabled={isLoading}
                    rows={3}
                  />
                </div>

                {/* 发送按钮 */}
                <button
                  type="button"
                  onClick={handleSendMessage}
                  disabled={!inputMessage.trim() || isLoading}
                  className="flex-shrink-0 w-12 h-12 rounded-xl bg-primary hover:bg-primary/90 text-white flex items-center justify-center disabled:opacity-50 disabled:cursor-not-allowed transition-all self-end"
                  aria-label="发送消息"
                >
                  {isLoading ? (
                    <span className="animate-spin text-lg">⏳</span>
                  ) : (
                    <Send className="w-5 h-5" />
                  )}
                </button>
              </div>
            </div>
          </div>
        </div>

        {/* 右侧边栏 */}
        <RequirementSidebar
          project={project}
          onViewAnalysis={handleViewAnalysis}
          isLoadingAnalysis={isLoadingAnalysis}
          hasAnalysis={!!project.understandingSummary}
        />
      </div>

      {/* 详情弹窗 */}
      {showDetail && (
        <DetailModal
          project={project}
          onClose={() => setShowDetail(false)}
        />
      )}
    </div>
  )
}

export default ClarifyPage
