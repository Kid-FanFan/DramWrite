import { useState, useEffect } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { useProjectStore } from '../../stores/projectStore'
import { CheckCircle, Edit3, Rocket, ArrowLeft, FileText, Users, Target, Hash, Palette, Loader2, Sparkles } from 'lucide-react'
import type { RequirementConfirmation } from '../../types'

// API 调用
const confirmAPI = {
  // 获取AI优化后的需求确认书
  getRequirementSummary: async (projectId: string) => {
    const response = await fetch(`/api/v1/projects/${projectId}/requirement-summary`)
    return await response.json()
  },
  confirm: async (projectId: string, confirmed: boolean = true) => {
    const response = await fetch(`/api/v1/projects/${projectId}/confirm-requirements`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ confirmed }),
    })
    return await response.json()
  },
  startCreation: async (projectId: string) => {
    const response = await fetch(`/api/v1/projects/${projectId}/create/start`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
    })
    return await response.json()
  }
}

function ConfirmPage() {
  const navigate = useNavigate()
  const { id } = useParams<{ id: string }>()
  const { getProject, updateProject, fetchProject } = useProjectStore()
  const project = getProject(id || '')

  const [isLoading, setIsLoading] = useState(false)
  const [pageLoading, setPageLoading] = useState(true)
  const [error, setError] = useState('')
  const [confirmation, setConfirmation] = useState<RequirementConfirmation | null>(null)
  const [isGeneratingSummary, setIsGeneratingSummary] = useState(true)

  // 页面加载时获取AI优化后的需求确认书
  useEffect(() => {
    if (id) {
      fetchProject(id).then(() => {
        loadRequirementSummary()
      })
    }
  }, [id])

  const loadRequirementSummary = async () => {
    if (!id) return
    setIsGeneratingSummary(true)
    try {
      const response = await confirmAPI.getRequirementSummary(id)
      if (response.code === 200 && response.data?.confirmation) {
        setConfirmation(response.data.confirmation)
      } else {
        setError(response.message || '生成需求确认书失败')
      }
    } catch (err) {
      console.error('获取需求确认书失败:', err)
      setError('网络错误，请重试')
    } finally {
      setIsGeneratingSummary(false)
      setPageLoading(false)
    }
  }

  const handleConfirm = async () => {
    setIsLoading(true)
    setError('')

    try {
      // 第1步：确认需求
      const confirmResponse = await confirmAPI.confirm(project?.id || '', true)
      if (confirmResponse.code !== 200) {
        setError(confirmResponse.message || '确认失败')
        setIsLoading(false)
        return
      }

      // 更新本地状态
      updateProject(project?.id || '', {
        status: 'creating',
        requirements_locked: true,
        storyTitle: confirmation?.title || project?.name,
        totalEpisodes: parseInt(confirmation?.episodes || '80', 10)
      })

      // 第2步：开始创作（后台异步执行）
      const startResponse = await confirmAPI.startCreation(project?.id || '')
      if (startResponse.code !== 200) {
        setError(startResponse.message || '启动创作失败')
        setIsLoading(false)
        return
      }

      // 跳转到创作控制台
      navigate(`/project/${id}/create`)
    } catch (err) {
      console.error('确认需求失败:', err)
      setError('网络错误，请重试')
    } finally {
      setIsLoading(false)
    }
  }

  const handleBack = () => {
    navigate(`/project/${id}/clarify`)
  }

  if (pageLoading || isGeneratingSummary) {
    return (
      <div className="max-w-4xl mx-auto">
        <div className="card text-center py-16">
          <div className="flex flex-col items-center gap-4">
            <Loader2 className="w-12 h-12 text-primary animate-spin" />
            <div>
              <p className="text-lg font-medium text-gray-800 mb-1">
                AI正在生成需求确认书
              </p>
              <p className="text-sm text-gray-500">
                请稍候，正在汇总优化我们的对话内容...
              </p>
            </div>
          </div>
        </div>
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

  if (!confirmation) {
    return (
      <div className="max-w-4xl mx-auto">
        <div className="card text-center py-12">
          <p className="text-red-500 mb-4">{error || '生成需求确认书失败'}</p>
          <button
            type="button"
            onClick={loadRequirementSummary}
            className="btn-primary"
          >
            重试
          </button>
        </div>
      </div>
    )
  }

  return (
    <div className="max-w-4xl mx-auto">
      {/* 头部 */}
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-3">
          <button
            type="button"
            onClick={handleBack}
            className="p-2 hover:bg-gray-100 rounded-full transition-colors"
            aria-label="返回"
          >
            <ArrowLeft className="w-5 h-5" />
          </button>
          <div>
            <h1 className="text-xl font-semibold">{project.name}</h1>
            <p className="text-sm text-gray-500">需求确认书</p>
          </div>
        </div>
        <div className="flex items-center gap-2 text-sm text-green-600 bg-green-50 px-3 py-1 rounded-full">
          <Sparkles className="w-4 h-4" />
          <span>AI智能生成</span>
        </div>
      </div>

      {/* 确认书内容 */}
      <div className="card space-y-8">
        {/* 标题 */}
        <div className="text-center pb-6 border-b">
          <div className="inline-flex items-center justify-center w-16 h-16 bg-green-100 rounded-full mb-4">
            <CheckCircle className="w-8 h-8 text-green-600" />
          </div>
          <h2 className="text-2xl font-bold mb-2">📜 需求确认书</h2>
          <p className="text-gray-500">
            以下是AI根据我们的对话为您整理的专业需求文档
          </p>
        </div>

        {/* 剧名 */}
        <div className="bg-gradient-to-r from-primary/5 to-primary/10 rounded-lg p-6">
          <h3 className="text-lg font-bold text-primary mb-1">{confirmation.title}</h3>
          <p className="text-sm text-gray-600">{confirmation.genre} · {confirmation.episodes}集</p>
        </div>

        {/* 基础信息 */}
        <div>
          <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
            <FileText className="w-5 h-5 text-primary" />
            基础信息
          </h3>
          <div className="bg-gray-50 rounded-lg p-4 space-y-3">
            <div className="flex justify-between py-2 border-b border-gray-200">
              <span className="text-gray-600">题材</span>
              <span className="font-medium">{confirmation.genre || '待补充'}</span>
            </div>
            <div className="flex justify-between py-2 border-b border-gray-200">
              <span className="text-gray-600">集数</span>
              <span className="font-medium">{confirmation.episodes || '80'} 集</span>
            </div>
            <div className="flex justify-between py-2">
              <span className="text-gray-600">目标受众</span>
              <span className="font-medium">{confirmation.target_audience || '待补充'}</span>
            </div>
          </div>
        </div>

        {/* 核心人物 */}
        <div>
          <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
            <Users className="w-5 h-5 text-primary" />
            核心人物
          </h3>
          <div className="bg-gray-50 rounded-lg p-4 space-y-4">
            {/* 主角 */}
            {confirmation.protagonist && (
              <div className="border-b border-gray-200 pb-4 last:border-0 last:pb-0">
                <h4 className="font-medium text-gray-800 mb-2">
                  主角：{confirmation.protagonist.name || '待命名'}
                </h4>
                <div className="text-sm text-gray-600 space-y-1">
                  {confirmation.protagonist.identity && (
                    <p><span className="text-gray-400">身份：</span>{confirmation.protagonist.identity}</p>
                  )}
                  {confirmation.protagonist.personality && (
                    <p><span className="text-gray-400">性格：</span>{confirmation.protagonist.personality}</p>
                  )}
                  {confirmation.protagonist.background && (
                    <p><span className="text-gray-400">背景：</span>{confirmation.protagonist.background}</p>
                  )}
                  {confirmation.protagonist.goal && (
                    <p><span className="text-gray-400">目标：</span>{confirmation.protagonist.goal}</p>
                  )}
                  {confirmation.protagonist.golden_finger && (
                    <p><span className="text-gray-400">特殊能力：</span>{confirmation.protagonist.golden_finger}</p>
                  )}
                </div>
              </div>
            )}

            {/* 配角 */}
            {confirmation.supporting_roles && confirmation.supporting_roles.length > 0 && (
              <div>
                <h4 className="font-medium text-gray-700 mb-2">其他角色</h4>
                <div className="space-y-2">
                  {confirmation.supporting_roles.map((role, index) => (
                    <div key={index} className="text-sm">
                      <span className="font-medium">{role.name}</span>
                      <span className="text-gray-400 mx-1">·</span>
                      <span className="text-gray-600">{role.role_type}</span>
                      {role.description && (
                        <span className="text-gray-500"> - {role.description}</span>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        </div>

        {/* 剧情概要 */}
        <div>
          <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
            <Target className="w-5 h-5 text-primary" />
            剧情概要
          </h3>
          <div className="bg-gray-50 rounded-lg p-4">
            {confirmation.plot_summary ? (
              <p className="text-gray-700 leading-relaxed whitespace-pre-wrap">
                {confirmation.plot_summary}
              </p>
            ) : (
              <p className="text-gray-400 italic">剧情概要待补充</p>
            )}
          </div>
        </div>

        {/* 核心冲突 */}
        <div>
          <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
            <Target className="w-5 h-5 text-primary" />
            核心冲突
          </h3>
          <div className="bg-gray-50 rounded-lg p-4">
            <p className="text-gray-700">{confirmation.core_conflict || '待补充'}</p>
          </div>
        </div>

        {/* 风格基调 */}
        <div>
          <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
            <Palette className="w-5 h-5 text-primary" />
            风格基调
          </h3>
          <div className="bg-gray-50 rounded-lg p-4">
            <p className="text-gray-700">{confirmation.style || '待补充'}</p>
          </div>
        </div>

        {/* 卖点 */}
        {confirmation.selling_points && confirmation.selling_points.length > 0 && (
          <div>
            <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
              <Sparkles className="w-5 h-5 text-primary" />
              核心卖点
            </h3>
            <div className="bg-gray-50 rounded-lg p-4">
              <ul className="space-y-2">
                {confirmation.selling_points.map((point, index) => (
                  <li key={index} className="flex items-start gap-2 text-gray-700">
                    <span className="text-primary font-medium">{index + 1}.</span>
                    <span>{point}</span>
                  </li>
                ))}
              </ul>
            </div>
          </div>
        )}

        {/* 特殊要求 */}
        {confirmation.special_requirements && (
          <div>
            <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
              <Hash className="w-5 h-5 text-primary" />
              特殊要求
            </h3>
            <div className="bg-yellow-50 rounded-lg p-4">
              <p className="text-gray-700">{confirmation.special_requirements}</p>
            </div>
          </div>
        )}

        {/* 完整度 */}
        <div className="bg-blue-50 rounded-lg p-4 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <Hash className="w-5 h-5 text-blue-600" />
            <span className="font-medium text-blue-900">需求完整度</span>
          </div>
          <div className="flex items-center gap-3">
            <div className="w-32 h-2 bg-blue-200 rounded-full overflow-hidden">
              <div
                className="h-full bg-blue-600 transition-all duration-300"
                style={{ width: `${project.completeness}%` }}
              />
            </div>
            <span className="font-semibold text-blue-900">{project.completeness}%</span>
          </div>
        </div>

        {/* 提示信息 */}
        {project.completeness < 80 && (
          <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4 text-yellow-800">
            <p className="text-sm">
              ⚠️ 需求完整度不足 80%，建议返回完善需求信息，以获得更好的创作效果。
            </p>
          </div>
        )}

        {/* 错误提示 */}
        {error && (
          <div className="bg-red-50 border border-red-200 rounded-lg p-4 text-red-800">
            <p className="text-sm">{error}</p>
          </div>
        )}

        {/* 操作按钮 */}
        <div className="flex items-center justify-between pt-6 border-t">
          <button
            type="button"
            onClick={handleBack}
            className="btn-secondary flex items-center gap-2"
          >
            <Edit3 className="w-4 h-4" />
            返回修改
          </button>

          <button
            type="button"
            onClick={handleConfirm}
            disabled={isLoading}
            className="btn-primary flex items-center gap-2"
          >
            {isLoading ? (
              <>
                <span className="animate-spin">⏳</span>
                处理中...
              </>
            ) : (
              <>
                <Rocket className="w-4 h-4" />
                确认，开始创作
              </>
            )}
          </button>
        </div>

        {/* 说明 */}
        <p className="text-center text-sm text-gray-500">
          💡 确认后将锁定需求，进入自动化剧本创作流程
        </p>
      </div>
    </div>
  )
}

export default ConfirmPage
