import { useState, useEffect } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { useProjectStore } from '../../stores/projectStore'
import { ArrowLeft, Rocket, RefreshCw, Loader2, User, Swords, BookOpen, Globe, Heart, Palette, DollarSign, Sparkles, FileText, CheckCircle } from 'lucide-react'
import type { RequirementConfirmation } from '../../types'

// API 调用
const confirmAPI = {
  // 获取AI优化后的需求确认书
  getRequirementSummary: async (projectId: string) => {
    const response = await fetch(`/api/v1/projects/${projectId}/requirement-summary`)
    return await response.json()
  },
  // 重新生成确认书
  regenerateConfirmation: async (projectId: string) => {
    const response = await fetch(`/api/v1/projects/${projectId}/regenerate-confirmation`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
    })
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

// 信息卡片组件
interface InfoCardProps {
  icon: React.ReactNode
  title: string
  children: React.ReactNode
  className?: string
  highlight?: boolean
}

function InfoCard({ icon, title, children, className = '', highlight = false }: InfoCardProps) {
  return (
    <div className={`bg-white rounded-xl border ${highlight ? 'border-primary/30 ring-1 ring-primary/10' : 'border-gray-200'} p-6 ${className}`}>
      <div className="flex items-center gap-3 mb-4">
        <div className={`w-10 h-10 rounded-lg flex items-center justify-center ${highlight ? 'bg-primary/10 text-primary' : 'bg-gray-100 text-gray-600'}`}>
          {icon}
        </div>
        <h3 className="text-lg font-semibold text-gray-900">{title}</h3>
      </div>
      <div className="text-gray-700 leading-relaxed">
        {children}
      </div>
    </div>
  )
}

// 判断是否为恋爱类题材
function isRomanceGenre(genre: string): boolean {
  if (!genre) return false
  const romanceKeywords = ['恋爱', '甜宠', '虐恋', '情感', '爱情', '言情', ' romantic', 'romance']
  return romanceKeywords.some(keyword => genre.toLowerCase().includes(keyword.toLowerCase()))
}

function ConfirmPage() {
  const navigate = useNavigate()
  const { id } = useParams<{ id: string }>()
  const { getProject, updateProject } = useProjectStore()
  const project = getProject(id || '')

  const [isLoading, setIsLoading] = useState(false)
  const [pageLoading, setPageLoading] = useState(true)
  const [error, setError] = useState('')
  const [confirmation, setConfirmation] = useState<RequirementConfirmation | null>(null)
  const [isRegenerating, setIsRegenerating] = useState(false)

  // 页面加载时获取需求确认书
  useEffect(() => {
    if (id) {
      loadRequirementSummary()
    }
  }, [id])

  const loadRequirementSummary = async () => {
    if (!id) return
    setPageLoading(true)
    setError('') // 清除之前的错误
    try {
      const response = await confirmAPI.getRequirementSummary(id)
      if (response.code === 200 && response.data?.confirmation) {
        setConfirmation(response.data.confirmation)
        // 同步到项目 store
        updateProject(id, { requirementConfirmation: response.data.confirmation })
      } else {
        setError(response.message || '生成需求确认书失败')
      }
    } catch (err) {
      console.error('获取需求确认书失败:', err)
      setError('网络错误，请重试')
    } finally {
      setPageLoading(false)
    }
  }

  const handleRegenerate = async () => {
    if (!id) return
    setIsRegenerating(true)
    setError('')
    try {
      const response = await confirmAPI.regenerateConfirmation(id)
      if (response.code === 200 && response.data?.confirmation) {
        setConfirmation(response.data.confirmation)
        // 同步到项目 store
        updateProject(id, { requirementConfirmation: response.data.confirmation })
      } else {
        setError(response.message || '重新生成失败')
      }
    } catch (err) {
      console.error('重新生成确认书失败:', err)
      setError('网络错误，请重试')
    } finally {
      setIsRegenerating(false)
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
      if (confirmation) {
        updateProject(project?.id || '', {
          status: 'creating',
          requirementsLocked: true,
          storyTitle: confirmation.title || project?.name,
          totalEpisodes: parseInt(confirmation.episodes || '80', 10)
        })
      }

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

  if (pageLoading) {
    return (
      <div className="max-w-6xl mx-auto">
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
      <div className="max-w-6xl mx-auto">
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

  // 判断是否为恋爱类题材
  const showRomanceLine = isRomanceGenre(confirmation.genre)

  return (
    <div className="max-w-6xl mx-auto">
      {/* 顶部操作栏 */}
      <div className="sticky top-0 z-20 bg-white/95 backdrop-blur border-b border-gray-200 py-4 mb-6">
        <div className="flex items-center justify-between">
          <button
            type="button"
            onClick={handleBack}
            className="btn-secondary flex items-center gap-2"
          >
            <ArrowLeft className="w-4 h-4" />
            返回修改
          </button>

          <div className="flex items-center gap-3">
            <button
              type="button"
              onClick={handleRegenerate}
              disabled={isRegenerating}
              className="btn-secondary flex items-center gap-2"
            >
              {isRegenerating ? (
                <Loader2 className="w-4 h-4 animate-spin" />
              ) : (
                <RefreshCw className="w-4 h-4" />
              )}
              重新生成
            </button>
            <button
              type="button"
              onClick={handleConfirm}
              disabled={isLoading}
              className="btn-primary flex items-center gap-2"
            >
              {isLoading ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin" />
                  处理中...
                </>
              ) : (
                <>
                  <Rocket className="w-4 h-4" />
                  开始创作
                </>
              )}
            </button>
          </div>
        </div>
      </div>

      {/* 错误提示 */}
      {error && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-4 text-red-800 mb-6">
          <p className="text-sm">{error}</p>
        </div>
      )}

      {/* 主内容区 - 卡片布局 */}
      <div className="space-y-6 pb-12">
        {/* 顶部标题卡 */}
        <div className="bg-gradient-to-r from-primary/5 to-primary/10 rounded-xl p-6">
          <div className="flex items-center gap-3 mb-2">
            <div className="w-12 h-12 bg-primary/20 rounded-full flex items-center justify-center">
              <CheckCircle className="w-6 h-6 text-primary" />
            </div>
            <div>
              <h1 className="text-2xl font-bold text-gray-900">
                《{confirmation.title}》
              </h1>
              <p className="text-gray-600">
                {confirmation.genre} · {confirmation.episodes}集 · {confirmation.target_audience}
              </p>
            </div>
          </div>
        </div>

        {/* 第一行：主角设定 + 核心冲突 */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <InfoCard icon={<User className="w-5 h-5" />} title="主角设定" highlight>
            <p>{confirmation.protagonist_summary}</p>
          </InfoCard>

          <InfoCard icon={<Swords className="w-5 h-5" />} title="核心冲突" highlight>
            <p>{confirmation.core_conflict_summary}</p>
          </InfoCard>
        </div>

        {/* 剧情规划 - 重点突出 */}
        <InfoCard icon={<BookOpen className="w-5 h-5" />} title="剧情规划" highlight>
          <p>{confirmation.plot_summary}</p>
        </InfoCard>

        {/* 第二行：世界观 + 感情线（条件显示） */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <InfoCard icon={<Globe className="w-5 h-5" />} title="世界观设定">
            <p>{confirmation.world_building_summary}</p>
          </InfoCard>

          {showRomanceLine ? (
            <InfoCard icon={<Heart className="w-5 h-5" />} title="感情线设计" className="bg-pink-50/50 border-pink-200">
              <p>{confirmation.romance_line_summary}</p>
            </InfoCard>
          ) : (
            <InfoCard icon={<Heart className="w-5 h-5" />} title="感情线设计" className="opacity-60">
              <p className="text-gray-400 italic">该题材不涉及感情线</p>
            </InfoCard>
          )}
        </div>

        {/* 第三行：风格基调 + 付费卡点 */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <InfoCard icon={<Palette className="w-5 h-5" />} title="风格基调">
            <p>{confirmation.style_summary}</p>
          </InfoCard>

          <InfoCard icon={<DollarSign className="w-5 h-5" />} title="付费卡点设计" className="bg-amber-50/50 border-amber-200">
            <p>{confirmation.checkpoint_summary}</p>
          </InfoCard>
        </div>

        {/* 核心卖点 */}
        <InfoCard icon={<Sparkles className="w-5 h-5" />} title="核心卖点">
          <div className="flex flex-wrap gap-2">
            {confirmation.selling_points?.map((point, index) => (
              <span
                key={index}
                className="px-3 py-1.5 bg-primary/10 text-primary rounded-full text-sm font-medium"
              >
                {point}
              </span>
            ))}
          </div>
        </InfoCard>

        {/* 特殊说明 */}
        {confirmation.special_notes && (
          <InfoCard icon={<FileText className="w-5 h-5" />} title="特殊说明">
            <p>{confirmation.special_notes}</p>
          </InfoCard>
        )}

        {/* 底部操作栏 */}
        <div className="mt-12 pt-6 border-t border-gray-200 flex items-center justify-between">
          <button
            type="button"
            onClick={handleBack}
            className="btn-secondary flex items-center gap-2"
          >
            <ArrowLeft className="w-4 h-4" />
            返回修改
          </button>
          <div className="flex gap-3">
            <button
              type="button"
              onClick={handleRegenerate}
              disabled={isRegenerating}
              className="btn-secondary flex items-center gap-2"
            >
              {isRegenerating ? (
                <Loader2 className="w-4 h-4 animate-spin" />
              ) : (
                <RefreshCw className="w-4 h-4" />
              )}
              重新生成
            </button>
            <button
              type="button"
              onClick={handleConfirm}
              disabled={isLoading}
              className="btn-primary flex items-center gap-2"
            >
              {isLoading ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin" />
                  处理中...
                </>
              ) : (
                <>
                  <Rocket className="w-4 h-4" />
                  开始创作
                </>
              )}
            </button>
          </div>
        </div>

        {/* 提示信息 */}
        <div className="p-4 bg-blue-50 rounded-lg text-sm text-blue-700">
          <p>💡 确认后将锁定需求，进入自动化创作流程。如需修改请返回调整。</p>
        </div>
      </div>
    </div>
  )
}

export default ConfirmPage
