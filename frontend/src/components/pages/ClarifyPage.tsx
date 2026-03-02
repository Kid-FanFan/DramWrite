import { useState, useEffect, useRef } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { useProjectStore } from '../../stores/projectStore'
import { Send, Sparkles, RotateCcw, MessageSquare, ListTodo, Info } from 'lucide-react'
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
  const eventSource = new EventSource(`/api/v1/projects/${projectId}/chat/stream`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ message, type: 'text' }),
  } as any)

  // 使用 fetch 实现 POST 方式的 SSE
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

function ClarifyPage() {
  const navigate = useNavigate()
  const { id } = useParams<{ id: string }>()
  const { getProject, updateProject, addMessage, fetchProject } = useProjectStore()
  const project = getProject(id || '')

  const [inputMessage, setInputMessage] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [pageLoading, setPageLoading] = useState(true)
  const messagesEndRef = useRef<HTMLDivElement>(null)

  // 页面加载时从后端获取完整项目数据（包含消息历史）
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
      let tempMessageId: string | null = null

      chatAPIStream(project.id, message, {
        onContent: (content, isComplete) => {
          if (!tempMessageId) {
            // 首次收到内容，添加临时消息
            tempMessageId = `msg_${Date.now()}`
            addMessage(project.id, {
              role: 'assistant',
              content: content,
              type: 'text'
            })
          } else {
            // 更新已有消息内容
            const currentProject = getProject(project.id)
            if (currentProject) {
              const messages = [...currentProject.messages]
              const lastMsg = messages[messages.length - 1]
              if (lastMsg && lastMsg.role === 'assistant') {
                messages[messages.length - 1] = {
                  ...lastMsg,
                  content: content
                }
                updateProject(project.id, { messages })
              }
            }
          }
        },
        onMetadata: (metadata) => {
          // 更新项目完整度
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
      // 非流式模式（原有逻辑）
      try {
        const response = await chatAPI(project.id, message)

        if (response.code === 200) {
          const { data } = response

          // 检查 LLM 是否未配置
          if (data.llm_not_configured) {
            // 添加错误消息
            addMessage(project.id, {
              role: 'assistant',
              content: data.content,
              type: 'error'
            })
          } else {
            // 添加助手消息
            addMessage(project.id, {
              role: 'assistant',
              content: data.content,
              type: data.options ? 'option' : 'text',
              options: data.options
            })

            // 更新项目完整度
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
        // 添加错误提示
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
    handleSendMessage()
  }

  const handleAutoFill = () => {
    setInputMessage('自动生成')
    handleSendMessage()
  }

  const handleGetSuggestions = () => {
    setInputMessage('给我建议')
    handleSendMessage()
  }

  // 需求澄清阶段不直接显示已确认的需求项
  // 需求确认书将在确认页面由大模型汇总优化后展示

  return (
    <div className="h-[calc(100vh-140px)]">
      <div className="card h-full flex flex-col">
        {/* 头部 */}
        <div className="flex items-center justify-between mb-4 pb-4 border-b">
          <div className="flex items-center gap-3">
            <h2 className="text-lg font-semibold">{project.name}</h2>
            <span className="text-sm text-gray-500">- 需求澄清</span>
          </div>
          <div className="flex items-center gap-4">
            {/* 进度条 */}
            <div className="flex items-center gap-2">
              <div className="w-32 h-2 bg-gray-200 rounded-full overflow-hidden">
                <div
                  className="h-full bg-primary transition-all duration-300"
                  style={{ width: `${project.completeness}%` }}
                />
              </div>
              <span className="text-sm text-gray-600">{project.completeness}%</span>
            </div>
            <button
              type="button"
              disabled={project.completeness < 80}
              className="btn-primary text-sm disabled:opacity-50"
              onClick={() => navigate(`/project/${id}/confirm`)}
            >
              下一步 →
            </button>
          </div>
        </div>

        {/* 三栏布局 */}
        <div className="flex-1 flex gap-4 min-h-0">
          {/* 左侧 - 对话历史 */}
          <div className="w-48 border-r pr-4 overflow-y-auto scrollbar-thin hidden lg:block">
            <h3 className="text-sm font-medium text-gray-500 mb-3 flex items-center gap-2">
              <MessageSquare className="w-4 h-4" />
              对话历史
            </h3>
            <div className="space-y-2">
              {project.messages.map((msg, index) => (
                <div
                  key={index}
                  className={`text-sm p-2 rounded cursor-pointer hover:bg-gray-50 ${
                    msg.role === 'user' ? 'text-primary' : 'text-gray-600'
                  }`}
                >
                  <span className="text-xs text-gray-400">{msg.role === 'user' ? '你' : '助手'}:</span>
                  <p className="truncate">{msg.content}</p>
                </div>
              ))}
            </div>
          </div>

          {/* 中间 - 当前对话 */}
          <div className="flex-1 flex flex-col min-w-0">
            {/* 消息区域 */}
            <div className="flex-1 overflow-y-auto scrollbar-thin space-y-4 pr-2">
              {project.messages.map((msg, index) => (
                <div
                  key={index}
                  className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
                >
                  <div
                    className={`max-w-[80%] rounded-lg p-3 ${
                      msg.role === 'user'
                        ? 'bg-primary text-white'
                        : 'bg-gray-100 text-gray-800'
                    }`}
                  >
                    <p className="whitespace-pre-wrap">{msg.content}</p>

                    {/* 选项按钮 */}
                    {msg.options && msg.options.length > 0 && (
                      <div className="mt-3 space-y-2">
                        {msg.options.map((option) => (
                          <button
                            type="button"
                            key={option.id}
                            onClick={() => handleOptionClick(option)}
                            className="w-full text-left p-2 rounded bg-white/50 hover:bg-white/80 transition-colors"
                          >
                            <span className="font-medium">{option.id}. {option.title}</span>
                            <span className="text-sm text-gray-500 ml-2">- {option.description}</span>
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
            <div className="mt-4 pt-4 border-t">
              <div className="flex gap-2 mb-3">
                <button
                  type="button"
                  onClick={handleAutoFill}
                  disabled={isLoading}
                  className="text-xs px-3 py-1.5 bg-gray-100 hover:bg-gray-200 rounded-full text-gray-600 flex items-center gap-1"
                >
                  <Sparkles className="w-3 h-3" />
                  自动生成
                </button>
                <button
                  type="button"
                  onClick={handleGetSuggestions}
                  disabled={isLoading}
                  className="text-xs px-3 py-1.5 bg-gray-100 hover:bg-gray-200 rounded-full text-gray-600 flex items-center gap-1"
                >
                  <RotateCcw className="w-3 h-3" />
                  给我建议
                </button>
              </div>

              <div className="flex gap-2">
                <textarea
                  value={inputMessage}
                  onChange={(e) => setInputMessage(e.target.value)}
                  onKeyDown={handleKeyDown}
                  placeholder="输入您的回答..."
                  className="input flex-1 resize-none h-20"
                  disabled={isLoading}
                />
                <button
                  type="button"
                  onClick={handleSendMessage}
                  disabled={!inputMessage.trim() || isLoading}
                  className="btn-primary px-4"
                  aria-label="发送消息"
                >
                  {isLoading ? (
                    <span className="animate-spin">⏳</span>
                  ) : (
                    <Send className="w-5 h-5" />
                  )}
                </button>
              </div>
            </div>
          </div>

          {/* 右侧 - 需求面板 */}
          <div className="w-64 border-l pl-4 overflow-y-auto scrollbar-thin hidden md:block">
            <h3 className="text-sm font-medium text-gray-500 mb-3 flex items-center gap-2">
              <ListTodo className="w-4 h-4" />
              需求收集进度
            </h3>

            {/* 进度条 */}
            <div className="mb-4">
              <div className="flex justify-between text-sm mb-1">
                <span>完整度</span>
                <span className="font-medium">{project.completeness}%</span>
              </div>
              <div className="w-full h-2 bg-gray-200 rounded-full overflow-hidden">
                <div
                  className="h-full bg-primary transition-all duration-300"
                  style={{ width: `${project.completeness}%` }}
                />
              </div>
            </div>

            {/* 说明提示 */}
            <div className="mb-4 p-3 bg-blue-50 rounded-lg">
              <div className="flex items-start gap-2">
                <Info className="w-4 h-4 text-blue-500 flex-shrink-0 mt-0.5" />
                <p className="text-xs text-blue-700">
                  需求澄清阶段您只需与AI对话交流创作想法即可。
                </p>
              </div>
            </div>

            {/* 下一步提示 */}
            {project.completeness >= 80 && (
              <div className="mt-4 p-3 bg-green-50 rounded-lg">
                <div className="flex items-start gap-2">
                  <Info className="w-4 h-4 text-green-500 flex-shrink-0 mt-0.5" />
                  <div className="text-sm text-green-700">
                    <p className="font-medium mb-1">✓ 需求收集完成！</p>
                    <p className="text-xs">点击"下一步"，AI将为您生成专业的需求确认书。</p>
                  </div>
                </div>
              </div>
            )}

            {/* 快捷操作 */}
            <div className="mt-4 pt-4 border-t">
              <h4 className="text-xs font-medium text-gray-400 mb-2 uppercase tracking-wider">
                快捷操作
              </h4>
              <div className="space-y-2">
                <button
                  type="button"
                  onClick={handleAutoFill}
                  disabled={isLoading}
                  className="w-full text-xs px-3 py-2 bg-gray-100 hover:bg-gray-200 rounded-lg text-gray-600 flex items-center justify-center gap-1 transition-colors"
                >
                  <Sparkles className="w-3 h-3" />
                  自动生成当前项
                </button>
                <button
                  type="button"
                  onClick={handleGetSuggestions}
                  disabled={isLoading}
                  className="w-full text-xs px-3 py-2 bg-gray-100 hover:bg-gray-200 rounded-lg text-gray-600 flex items-center justify-center gap-1 transition-colors"
                >
                  <RotateCcw className="w-3 h-3" />
                  获取AI建议
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

export default ClarifyPage