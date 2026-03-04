import { useEffect, useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { useProjectStore } from '../../stores/projectStore'
import { Play, Pause, FileText, Users, List, BookOpen, CheckCircle, Loader2, X, ChevronRight, ClipboardList, ArrowLeft, RefreshCw } from 'lucide-react'

interface CreationStep {
  id: string
  name: string
  icon: React.ReactNode
  description: string
}

const STEPS: CreationStep[] = [
  { id: 'synopsis', name: '故事梗概', icon: <FileText className="w-5 h-5" />, description: '生成故事主线' },
  { id: 'characters', name: '人物小传', icon: <Users className="w-5 h-5" />, description: '创建人物设定' },
  { id: 'outline', name: '分集大纲', icon: <List className="w-5 h-5" />, description: '规划剧情节奏' },
  { id: 'script', name: '剧本正文', icon: <BookOpen className="w-5 h-5" />, description: '撰写完整剧本' },
]

// API 调用函数
const creationAPI = {
  start: async (projectId: string) => {
    const response = await fetch(`/api/v1/projects/${projectId}/create/start`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
    })
    return await response.json()
  },
  pause: async (projectId: string) => {
    const response = await fetch(`/api/v1/projects/${projectId}/create/pause`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
    })
    return await response.json()
  },
  resume: async (projectId: string) => {
    const response = await fetch(`/api/v1/projects/${projectId}/create/resume`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
    })
    return await response.json()
  },
  getProgress: async (projectId: string) => {
    const response = await fetch(`/api/v1/projects/${projectId}/progress`)
    return await response.json()
  },
  // V1.2新增：重新生成
  regenerate: async (projectId: string, contentType: string) => {
    const response = await fetch(`/api/v1/projects/${projectId}/create/regenerate`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ content_type: contentType }),
    })
    return await response.json()
  },
}

// 项目API
const projectAPI = {
  get: async (id: string) => {
    const response = await fetch(`/api/v1/projects/${id}`)
    return await response.json()
  }
}

function CreatePage() {
  const navigate = useNavigate()
  const { id } = useParams<{ id: string }>()
  const { getProject, updateProject, fetchProject } = useProjectStore()
  const project = getProject(id || '')

  const [isLoading, setIsLoading] = useState(false)
  const [progress, setProgress] = useState(0)
  const [currentStep, setCurrentStep] = useState(0)
  const [error, setError] = useState('')
  const [pageLoading, setPageLoading] = useState(true)
  const [viewingStep, setViewingStep] = useState<string | null>(null)
  const [showRequirements, setShowRequirements] = useState(false)
  const [isRegenerating, setIsRegenerating] = useState(false)

  // 初始加载：获取最新项目状态
  useEffect(() => {
    if (id) {
      fetchProject(id).then(() => {
        setPageLoading(false)
      })
    }
  }, [id])

  // 获取进度并同步项目数据
  const fetchProgress = async () => {
    if (!id) return
    try {
      // 同时获取进度和最新项目数据
      const [progressRes, projectRes] = await Promise.all([
        creationAPI.getProgress(id),
        projectAPI.get(id)
      ])

      if (progressRes.code === 200) {
        const data = progressRes.data
        setProgress(data.percentage || 0)
        // 根据当前步骤设置 currentStep
        const stepIndex = STEPS.findIndex(s => s.id === data.current_step)
        if (stepIndex >= 0) {
          setCurrentStep(stepIndex)
        }
        // 更新项目状态
        if (data.status === 'completed') {
          updateProject(id, { status: 'completed' })
        }
      }

      // 关键：同步最新项目数据到 store，确保内容字段可用
      if (projectRes.code === 200) {
        const freshData = projectRes.data
        // 转换字段名
        const updates: any = {
          storySynopsis: freshData.story_synopsis || freshData.storySynopsis || '',
          storyTitle: freshData.story_title || freshData.storyTitle || '',
          oneLiner: freshData.one_liner || freshData.oneLiner || '',
          sellingPoints: freshData.selling_points || freshData.sellingPoints || [],
          characterProfiles: freshData.character_profiles || freshData.characterProfiles || [],
          episodeOutlines: freshData.episode_outlines || freshData.episodeOutlines || [],
          scripts: freshData.scripts || [],
        }
        // 如果有进度数据也更新
        if (freshData.creation_progress) {
          updates.creationProgress = freshData.creation_progress
        }
        updateProject(id, updates)
      }
    } catch (err) {
      console.error('获取进度失败:', err)
    }
  }

  // 轮询进度
  useEffect(() => {
    if (!project || project.status !== 'creating') return

    fetchProgress() // 立即获取一次

    const interval = setInterval(() => {
      fetchProgress()
    }, 5000) // 每5秒轮询一次

    return () => clearInterval(interval)
  }, [project?.status, id])

  if (pageLoading) {
    return (
      <div className="card text-center py-16">
        <div className="flex flex-col items-center gap-4">
          <Loader2 className="w-12 h-12 text-primary animate-spin" />
          <p className="text-gray-500">加载中...</p>
        </div>
      </div>
    )
  }

  if (!project) {
    return (
      <div className="card text-center py-12">
        <p className="text-gray-500">项目不存在</p>
        <button onClick={() => navigate('/')} className="btn-primary mt-4">
          返回首页
        </button>
      </div>
    )
  }

  const handleStart = async () => {
    if (!id) return
    setIsLoading(true)
    setError('')
    try {
      const response = await creationAPI.start(id)
      if (response.code === 200) {
        updateProject(id, { status: 'creating' })
      } else {
        setError(response.message || '启动失败')
      }
    } catch (err) {
      setError('启动创作失败，请检查后端是否正常运行')
    } finally {
      setIsLoading(false)
    }
  }

  const handlePause = async () => {
    if (!id) return
    setIsLoading(true)
    try {
      await creationAPI.pause(id)
      updateProject(id, { status: 'paused' })
    } catch (err) {
      console.error('暂停失败:', err)
    } finally {
      setIsLoading(false)
    }
  }

  const handleResume = async () => {
    if (!id) return
    setIsLoading(true)
    try {
      await creationAPI.resume(id)
      updateProject(id, { status: 'creating' })
    } catch (err) {
      console.error('继续失败:', err)
    } finally {
      setIsLoading(false)
    }
  }

  const handleGoToEditor = () => {
    navigate(`/project/${id}/edit`)
  }

  // V1.2新增：返回需求确认书
  const handleBackToConfirm = () => {
    if (!id) return
    navigate(`/project/${id}/confirm`)
  }

  // V1.2新增：重新生成指定步骤
  const handleRegenerate = async (contentType: string) => {
    if (!id) return
    setIsRegenerating(true)
    setError('')
    try {
      const response = await creationAPI.regenerate(id, contentType)
      if (response.code === 200) {
        // 重新获取项目数据
        await fetchProject(id)
        setError('')
      } else {
        setError(response.message || '重新生成失败')
      }
    } catch (err) {
      setError('重新生成失败，请检查后端是否正常运行')
    } finally {
      setIsRegenerating(false)
    }
  }

  // 获取步骤内容
  const getStepContent = (stepId: string) => {
    switch (stepId) {
      case 'synopsis': {
        const synopsis = project?.storySynopsis || ''
        const title = project?.storyTitle || ''
        const oneLiner = project?.oneLiner || ''
        const sellingPoints = project?.sellingPoints || []

        if (!synopsis) {
          return { title: '故事梗概', content: '暂无内容' }
        }

        let content = ''
        if (title) content += `【剧名】${title}\n\n`
        if (oneLiner) content += `【一句话简介】${oneLiner}\n\n`
        content += `【故事梗概】\n${synopsis}\n\n`
        if (sellingPoints.length > 0) {
          content += `【核心卖点】\n${sellingPoints.map((p: string, i: number) => `${i + 1}. ${p}`).join('\n')}`
        }

        return { title: '故事梗概', content }
      }
      case 'characters': {
        const chars = project?.characterProfiles || []
        if (chars.length === 0) {
          return { title: '人物小传', content: '暂无内容' }
        }

        const content = chars.map((c: any) => {
          const lines = [`【${c.name} - ${c.role}】`]
          if (c.age) lines.push(`年龄：${c.age}`)

          // 外观信息
          if (c.appearance) {
            const app = c.appearance
            const appParts = []
            if (app.height) appParts.push(`身高${app.height}`)
            if (app.build) appParts.push(`体型${app.build}`)
            if (app.hair) appParts.push(`发型${app.hair}`)
            if (app.clothing_style) appParts.push(`穿着${app.clothing_style}`)
            if (app.distinctive_features) appParts.push(`特征${app.distinctive_features}`)
            if (appParts.length > 0) lines.push(`外观：${appParts.join('，')}`)
          }

          if (c.personality) lines.push(`性格：${c.personality}`)
          if (c.background) lines.push(`背景：${c.background}`)
          if (c.goal) lines.push(`目标：${c.goal}`)

          // 兼容两种字段名
          const memoryPoint = c.memory_point || c.memoryPoint
          if (memoryPoint) lines.push(`记忆点：${memoryPoint}`)

          // 人物关系
          if (c.relationships) lines.push(`关系：${c.relationships}`)

          return lines.join('\n')
        }).join('\n\n---\n\n')

        return { title: '人物小传', content }
      }
      case 'outline': {
        const outlines = project?.episodeOutlines || []
        if (outlines.length === 0) {
          return { title: '分集大纲', content: '暂无内容' }
        }

        const content = outlines.map((o: any) => {
          const epNum = o.episodeNumber || o.episode_number
          const isCheckpoint = o.isCheckpoint || o.is_checkpoint
          const summary = o.summary || ''
          const hook = o.hook || ''
          return `第${epNum}集${isCheckpoint ? ' [付费卡点]' : ''}\n剧情：${summary}\n卡点：${hook}`
        }).join('\n\n---\n\n')

        return { title: '分集大纲', content }
      }
      case 'script': {
        const scripts = project?.scripts || []
        return {
          title: '剧本正文',
          content: scripts.length > 0
            ? `${scripts.length}集剧本已生成，请进入编辑器查看完整内容。`
            : '暂无内容'
        }
      }
      default:
        return { title: '', content: '' }
    }
  }

  const isCompleted = project.status === 'completed'
  const isCreating = project.status === 'creating'
  const isPaused = project.status === 'paused'
  // 判断创作是否真正开始（有进度数据且大于0）
  const hasProgress = progress > 0

  // 获取当前步骤状态
  const getStepStatus = (index: number) => {
    if (isCompleted) return 'completed'
    if (index < currentStep) return 'completed'
    if (index === currentStep && isCreating && hasProgress) return 'active'
    return 'pending'
  }

  return (
    <div className="space-y-6">
      {/* 头部 */}
      <div className="card">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold">{project.name}</h1>
            <p className="text-gray-500 mt-1">剧本创作中</p>
          </div>
          <div className="flex gap-3">
            {/* V1.2新增：返回需求确认书 */}
            <button
              onClick={handleBackToConfirm}
              className="btn-secondary flex items-center gap-2"
              title="返回需求确认书阶段"
            >
              <ArrowLeft className="w-4 h-4" />
              返回确认书
            </button>

            {/* 查看需求按钮 - 随时可用 */}
            <button
              onClick={() => setShowRequirements(true)}
              className="btn-secondary flex items-center gap-2"
              title="查看需求确认书"
            >
              <ClipboardList className="w-4 h-4" />
              需求
            </button>

            {isCompleted ? (
              <button onClick={handleGoToEditor} className="btn-primary">
                查看剧本 →
              </button>
            ) : isCreating && hasProgress ? (
              <button onClick={handlePause} disabled={isLoading} className="btn-secondary flex items-center gap-2">
                <Pause className="w-4 h-4" />
                暂停
              </button>
            ) : isPaused ? (
              <button onClick={handleResume} disabled={isLoading} className="btn-primary flex items-center gap-2">
                <Play className="w-4 h-4" />
                继续
              </button>
            ) : (
              <button onClick={handleStart} disabled={isLoading} className="btn-primary flex items-center gap-2">
                {isLoading ? (
                  <Loader2 className="w-4 h-4 animate-spin" />
                ) : (
                  <Play className="w-4 h-4" />
                )}
                {hasProgress ? '继续创作' : '开始创作'}
              </button>
            )}
          </div>
        </div>
        {error && (
          <div className="mt-4 p-3 bg-red-50 text-red-700 rounded-lg text-sm">
            {error}
          </div>
        )}
      </div>

      {/* 创作流水线 */}
      <div className="card">
        <h2 className="text-lg font-semibold mb-6">🎬 创作流水线</h2>

        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          {STEPS.map((step, index) => {
            const status = getStepStatus(index)
            const isActive = status === 'active'
            const isDone = status === 'completed'

            return (
              <div
                key={step.id}
                onClick={() => {
                  if (isDone || (isActive && (step.id === 'synopsis' || step.id === 'characters' || step.id === 'outline'))) {
                    setViewingStep(step.id)
                  }
                }}
                className={`p-4 rounded-lg border-2 transition-all ${
                  isActive
                    ? 'border-primary bg-primary/5 cursor-pointer hover:shadow-md'
                    : isDone
                    ? 'border-green-500 bg-green-50 cursor-pointer hover:shadow-md hover:bg-green-100'
                    : 'border-gray-200 bg-gray-50'
                }`}
              >
                <div className="flex items-center gap-3 mb-2">
                  <div
                    className={`p-2 rounded-lg ${
                      isActive ? 'bg-primary text-white' : isDone ? 'bg-green-500 text-white' : 'bg-gray-200'
                    }`}
                  >
                    {isDone && !isActive ? <CheckCircle className="w-5 h-5" /> : step.icon}
                  </div>
                  <span className={`font-medium ${isActive ? 'text-primary' : isDone ? 'text-green-700' : 'text-gray-500'}`}>
                    {step.name}
                  </span>
                </div>
                <p className="text-sm text-gray-500">{step.description}</p>
                {isActive && (
                  <div className="mt-2 flex items-center gap-2 text-sm text-primary">
                    <Loader2 className="w-4 h-4 animate-spin" />
                    生成中...
                  </div>
                )}
                {isDone && (
                  <div className="mt-2 flex items-center gap-1 text-sm text-green-600">
                    <span>点击查看</span>
                    <ChevronRight className="w-4 h-4" />
                  </div>
                )}
              </div>
            )
          })}
        </div>
      </div>

      {/* 进度条 - 基于实际剧本生成数量 */}
      <div className="card">
        <div className="flex items-center justify-between mb-4">
          <h3 className="font-medium">总体进度</h3>
          <span className="text-2xl font-bold text-primary">{progress}%</span>
        </div>
        <div className="w-full h-4 bg-gray-200 rounded-full overflow-hidden">
          <div
            className="h-full bg-primary transition-all duration-500"
            style={{ width: `${progress}%` }}
          />
        </div>
        <div className="flex justify-between mt-2 text-sm text-gray-500">
          <span>
            {isCreating ? '创作进行中...' : isPaused ? '已暂停' : isCompleted ? '创作完成' : '准备就绪'}
          </span>
          <span>
            {(() => {
              const completedScripts = project.scripts?.length || 0
              const total = project.totalEpisodes || 80
              return `${completedScripts} / ${total} 集`
            })()}
          </span>
        </div>
      </div>

      {/* V1.2新增：重新生成控制面板（仅已完成或暂停状态显示） */}
      {(isCompleted || isPaused) && (
        <div className="card">
          <h3 className="font-medium mb-4 flex items-center gap-2">
            <RefreshCw className="w-5 h-5" />
            重新生成控制
          </h3>
          <p className="text-sm text-gray-500 mb-4">
            对某个阶段的生成结果不满意？可以选择重新生成该阶段及其后续内容。
          </p>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
            {STEPS.map((step) => (
              <button
                key={step.id}
                onClick={() => handleRegenerate(step.id)}
                disabled={isRegenerating || isCreating}
                className="btn-secondary text-sm py-2 flex items-center justify-center gap-2"
              >
                {isRegenerating ? (
                  <Loader2 className="w-4 h-4 animate-spin" />
                ) : (
                  step.icon
                )}
                重生成{step.name}
              </button>
            ))}
          </div>
          {isRegenerating && (
            <p className="mt-3 text-sm text-primary flex items-center gap-2">
              <Loader2 className="w-4 h-4 animate-spin" />
              正在重新生成，请稍候...
            </p>
          )}
        </div>
      )}

      {/* 提示 */}
      {!isCreating && !isCompleted && progress === 0 && (
        <div className="bg-blue-50 border border-blue-200 rounded-lg p-4 text-blue-700">
          <p className="font-medium">💡 准备开始创作</p>
          <p className="text-sm mt-1">点击"开始创作"按钮，系统将自动生成完整剧本。整个过程大约需要 30 分钟。</p>
        </div>
      )}

      {isCompleted && (
        <div className="bg-green-50 border border-green-200 rounded-lg p-4 text-green-700">
          <p className="font-medium">🎉 创作完成！</p>
          <p className="text-sm mt-1">剧本已生成完毕，点击下方按钮查看和编辑。</p>
          <button onClick={handleGoToEditor} className="btn-primary mt-3">
            进入剧本编辑器
          </button>
        </div>
      )}

      {/* 查看内容弹窗 */}
      {viewingStep && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-lg max-w-2xl w-full max-h-[80vh] flex flex-col">
            <div className="flex items-center justify-between p-4 border-b">
              <h3 className="text-lg font-semibold">{getStepContent(viewingStep).title}</h3>
              <button
                type="button"
                onClick={() => setViewingStep(null)}
                className="p-1 hover:bg-gray-100 rounded-full"
                aria-label="关闭"
              >
                <X className="w-5 h-5" />
              </button>
            </div>
            <div className="p-4 overflow-y-auto flex-1">
              <pre className="whitespace-pre-wrap text-sm text-gray-700 font-mono leading-relaxed">
                {getStepContent(viewingStep).content}
              </pre>
            </div>
            <div className="p-4 border-t flex justify-end gap-3">
              <button
                type="button"
                onClick={() => setViewingStep(null)}
                className="btn-secondary"
              >
                关闭
              </button>
              {viewingStep === 'script' && (
                <button type="button" onClick={handleGoToEditor} className="btn-primary">
                  进入编辑器
                </button>
              )}
            </div>
          </div>
        </div>
      )}

      {/* 需求确认书弹窗 */}
      {showRequirements && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-lg max-w-2xl w-full max-h-[80vh] flex flex-col">
            <div className="flex items-center justify-between p-4 border-b">
              <h3 className="text-lg font-semibold">📋 需求确认书</h3>
              <button
                type="button"
                onClick={() => setShowRequirements(false)}
                className="p-1 hover:bg-gray-100 rounded-full"
                aria-label="关闭"
              >
                <X className="w-5 h-5" />
              </button>
            </div>
            <div className="p-4 overflow-y-auto flex-1">
              <div className="space-y-4 text-sm text-gray-700">
                {(() => {
                  const req = project?.requirements || {}
                  return (
                    <>
                      <div className="bg-gray-50 p-4 rounded-lg">
                        <h4 className="font-medium text-gray-900 mb-2">基础信息</h4>
                        <p><span className="text-gray-500">题材：</span>{req.genre || '未设置'}</p>
                        <p><span className="text-gray-500">集数：</span>{req.episodes || project?.totalEpisodes || 80}集</p>
                        <p><span className="text-gray-500">风格基调：</span>{req.style || '未设置'}</p>
                      </div>

                      {req.protagonist && (
                        <div className="bg-gray-50 p-4 rounded-lg">
                          <h4 className="font-medium text-gray-900 mb-2">主角设定</h4>
                          <p>{req.protagonist}</p>
                        </div>
                      )}

                      {req.conflict && (
                        <div className="bg-gray-50 p-4 rounded-lg">
                          <h4 className="font-medium text-gray-900 mb-2">核心冲突</h4>
                          <p>{req.conflict}</p>
                        </div>
                      )}

                      {req.target_audience && (
                        <div className="bg-gray-50 p-4 rounded-lg">
                          <h4 className="font-medium text-gray-900 mb-2">目标受众</h4>
                          <p>{req.target_audience}</p>
                        </div>
                      )}

                      {Object.keys(req).length === 0 && (
                        <p className="text-gray-500 text-center py-8">暂无需求信息</p>
                      )}
                    </>
                  )
                })()}
              </div>
            </div>
            <div className="p-4 border-t flex justify-end">
              <button
                type="button"
                onClick={() => setShowRequirements(false)}
                className="btn-secondary"
              >
                关闭
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

export default CreatePage
