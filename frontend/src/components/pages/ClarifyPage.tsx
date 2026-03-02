import { useState, useEffect, useRef } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { useProjectStore } from '../../stores/projectStore'
import { Send, Sparkles, Lightbulb, ChevronDown, ChevronUp, CheckCircle2, Circle } from 'lucide-react'
import type { Message, Option } from '../../types'

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

function ClarifyPage() {
  const navigate = useNavigate()
  const { id } = useParams<{ id: string }>()
  const { getProject, updateProject, addMessage, fetchProject } = useProjectStore()
  const project = getProject(id || '')

  const [inputMessage, setInputMessage] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [pageLoading, setPageLoading] = useState(true)
  const [showProgressPanel, setShowProgressPanel] = useState(true)
  const messagesEndRef = useRef<HTMLDivElement>(null)

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

  // 获取已完成的需求字段
  const getCompletedFields = () => {
    const requirements = project.requirements || {}
    return REQUIREMENT_FIELDS.map(field => ({
      ...field,
      completed: !!(requirements[field.key])
    }))
  }

  const completedFields = getCompletedFields()
  const completedCount = completedFields.filter(f => f.completed).length

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
        onContent: (content, isComplete) => {
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
            updateProject(project.id, {
              completeness: metadata.completeness,
              requirements: metadata.requirements_updated || project.requirements
            })
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

            if (data.completeness !== undefined) {
              updateProject(project.id, {
                completeness: data.completeness,
                requirements: data.requirements_updated || project.requirements
              })
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

  const handleAutoFill = () => {
    setInputMessage('自动生成')
    handleSendMessage()
  }

  const handleGetSuggestions = () => {
    setInputMessage('给我建议')
    handleSendMessage()
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

          <div className="flex items-center gap-6">
            {/* 进度指示器 */}
            <div className="flex items-center gap-3">
              <div className="relative w-12 h-12">
                <svg className="w-12 h-12 transform -rotate-90">
                  <circle
                    cx="24"
                    cy="24"
                    r="20"
                    stroke="#e5e7eb"
                    strokeWidth="4"
                    fill="none"
                  />
                  <circle
                    cx="24"
                    cy="24"
                    r="20"
                    stroke={project.completeness >= 80 ? '#22c55e' : '#4A90E2'}
                    strokeWidth="4"
                    fill="none"
                    strokeDasharray={`${project.completeness * 1.256} 125.6`}
                    strokeLinecap="round"
                    className="transition-all duration-500"
                  />
                </svg>
                <span className="absolute inset-0 flex items-center justify-center text-sm font-medium">
                  {project.completeness}%
                </span>
              </div>
              <div className="text-sm">
                <p className="text-gray-600">已收集 <span className="font-medium text-primary">{completedCount}</span>/6 项</p>
              </div>
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
      </div>

      {/* 主体区域 */}
      <div className="flex-1 flex flex-col min-h-0">
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

          {/* 底部需求进度面板（可折叠） */}
          <div className="border-t">
            <button
              type="button"
              onClick={() => setShowProgressPanel(!showProgressPanel)}
              className="w-full px-4 py-2 flex items-center justify-between text-sm text-gray-600 hover:bg-gray-50 transition-colors"
            >
              <span className="flex items-center gap-2">
                <span>需求收集进度</span>
                {completedCount === 6 && (
                  <span className="text-green-500 text-xs">✓ 已完成</span>
                )}
              </span>
              {showProgressPanel ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
            </button>

            {showProgressPanel && (
              <div className="px-4 pb-4">
                {/* 需求标签流 */}
                <div className="flex flex-wrap gap-2">
                  {completedFields.map((field) => (
                    <div
                      key={field.key}
                      className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full text-sm transition-all ${
                        field.completed
                          ? 'bg-green-50 text-green-700 border border-green-200'
                          : 'bg-gray-50 text-gray-400 border border-gray-200'
                      }`}
                    >
                      <span>{field.icon}</span>
                      <span>{field.label}</span>
                      {field.completed ? (
                        <CheckCircle2 className="w-3.5 h-3.5 text-green-500" />
                      ) : (
                        <Circle className="w-3.5 h-3.5 text-gray-300" />
                      )}
                    </div>
                  ))}
                </div>

                {/* 完成提示 */}
                {project.completeness >= 80 && (
                  <div className="mt-3 p-3 bg-green-50 rounded-lg border border-green-100">
                    <p className="text-sm text-green-700">
                      🎉 需求收集完成！点击右上角「生成需求确认书」继续下一步。
                    </p>
                  </div>
                )}
              </div>
            )}
          </div>

          {/* 输入区域 */}
          <div className="border-t p-4 bg-gray-50/50">
            <div className="flex gap-3 items-end">
              {/* 快捷按钮 */}
              <div className="flex gap-2">
                <button
                  type="button"
                  onClick={handleGetSuggestions}
                  disabled={isLoading}
                  className="flex items-center gap-1.5 px-3 py-2 text-sm text-gray-600 hover:text-primary hover:bg-white rounded-lg border border-gray-200 hover:border-primary/30 transition-all disabled:opacity-50"
                  title="获取AI建议"
                >
                  <Lightbulb className="w-4 h-4" />
                  <span className="hidden sm:inline">建议</span>
                </button>
                <button
                  type="button"
                  onClick={handleAutoFill}
                  disabled={isLoading}
                  className="flex items-center gap-1.5 px-3 py-2 text-sm text-gray-600 hover:text-primary hover:bg-white rounded-lg border border-gray-200 hover:border-primary/30 transition-all disabled:opacity-50"
                  title="自动填充"
                >
                  <Sparkles className="w-4 h-4" />
                  <span className="hidden sm:inline">跳过</span>
                </button>
              </div>

              {/* 输入框 */}
              <div className="flex-1 relative">
                <textarea
                  value={inputMessage}
                  onChange={(e) => setInputMessage(e.target.value)}
                  onKeyDown={handleKeyDown}
                  placeholder="输入您的想法，或点击上方按钮获取帮助..."
                  className="w-full px-4 py-3 pr-12 rounded-xl border border-gray-200 focus:border-primary focus:ring-2 focus:ring-primary/20 resize-none h-12 transition-all"
                  disabled={isLoading}
                  rows={1}
                />
              </div>

              {/* 发送按钮 */}
              <button
                type="button"
                onClick={handleSendMessage}
                disabled={!inputMessage.trim() || isLoading}
                className="flex-shrink-0 w-12 h-12 rounded-xl bg-primary hover:bg-primary/90 text-white flex items-center justify-center disabled:opacity-50 disabled:cursor-not-allowed transition-all"
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
    </div>
  )
}

export default ClarifyPage
