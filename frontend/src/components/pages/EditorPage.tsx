import { useState, useEffect } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { useProjectStore } from '../../stores/projectStore'
import { FileText, Users, List, BookOpen, ChevronRight, Download, RotateCcw, Save, CheckCircle, Loader2 } from 'lucide-react'

type TabType = 'synopsis' | 'characters' | 'outlines' | 'scripts'

interface Synopsis {
  title: string
  one_liner: string
  synopsis: string
  selling_points: string[]
}

interface Character {
  name: string
  role: string
  age: string
  personality: string
  background: string
  goal: string
  memory_point: string
  appearance?: {
    height?: string
    build?: string
    hair?: string
    clothing_style?: string
    distinctive_features?: string
  }
  relationships?: string
}

interface Outline {
  episode_number: number
  summary: string
  hook: string
  is_checkpoint: boolean
}

interface Script {
  episode_number: number
  title: string
  content: string
  word_count: number
  status: string
}

// API 调用函数
const contentAPI = {
  getSynopsis: async (projectId: string) => {
    const response = await fetch(`/api/v1/projects/${projectId}/synopsis`)
    return await response.json()
  },
  getCharacters: async (projectId: string) => {
    const response = await fetch(`/api/v1/projects/${projectId}/characters`)
    return await response.json()
  },
  getOutlines: async (projectId: string, page = 1, size = 10) => {
    const response = await fetch(`/api/v1/projects/${projectId}/outlines?page=${page}&size=${size}`)
    return await response.json()
  },
  getEpisode: async (projectId: string, episodeNumber: number) => {
    const response = await fetch(`/api/v1/projects/${projectId}/episodes/${episodeNumber}`)
    return await response.json()
  },
  regenerate: async (projectId: string, contentType: string, episodeNumber?: number) => {
    const response = await fetch(`/api/v1/projects/${projectId}/create/regenerate`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ content_type: contentType, episode_number: episodeNumber }),
    })
    return await response.json()
  },
}

function EditorPage() {
  const navigate = useNavigate()
  const { id } = useParams<{ id: string }>()
  const { getProject } = useProjectStore()
  const project = getProject(id || '')

  const [activeTab, setActiveTab] = useState<TabType>('synopsis')
  const [selectedEpisode, setSelectedEpisode] = useState(1)
  const [isExporting, setIsExporting] = useState(false)
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState('')
  const [showRegenerateOptions, setShowRegenerateOptions] = useState(false)

  // 数据状态
  const [synopsis, setSynopsis] = useState<Synopsis>({
    title: '',
    one_liner: '',
    synopsis: '',
    selling_points: [],
  })
  const [characters, setCharacters] = useState<Character[]>([])
  const [outlines, setOutlines] = useState<Outline[]>([])
  const [_scripts, _setScripts] = useState<Script[]>([])
  const [currentScript, setCurrentScript] = useState<Script | null>(null)

  // 加载数据
  useEffect(() => {
    if (!id) return

    const loadData = async () => {
      setIsLoading(true)
      setError('')
      try {
        switch (activeTab) {
          case 'synopsis':
            const synopsisRes = await contentAPI.getSynopsis(id)
            if (synopsisRes.code === 200) {
              setSynopsis(synopsisRes.data)
            }
            break
          case 'characters':
            const charRes = await contentAPI.getCharacters(id)
            if (charRes.code === 200) {
              setCharacters(charRes.data.characters || [])
            }
            break
          case 'outlines':
            const outlineRes = await contentAPI.getOutlines(id, 1, 100)
            if (outlineRes.code === 200) {
              setOutlines(outlineRes.data.items || [])
            }
            break
          case 'scripts':
            // 加载剧本列表和当前选中的剧本
            const scriptRes = await contentAPI.getEpisode(id, selectedEpisode)
            if (scriptRes.code === 200) {
              setCurrentScript(scriptRes.data)
            }
            break
        }
      } catch (err) {
        setError('加载数据失败，请检查后端是否正常运行')
      } finally {
        setIsLoading(false)
      }
    }

    loadData()
  }, [id, activeTab, selectedEpisode])

  // 导出剧本
  const handleExport = async (format: 'docx' | 'pdf' | 'zip' = 'docx') => {
    if (!id) return

    setIsExporting(true)
    try {
      const response = await fetch(`/api/v1/projects/${id}/export`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          format,
          contents: ['synopsis', 'characters', 'outlines', 'scripts'],
          episodes: 'all',
        }),
      })

      const result = await response.json()

      if (result.code === 200 && result.data?.download_url) {
        window.open(result.data.download_url, '_blank')
      } else {
        alert('导出失败：' + result.message)
      }
    } catch (error) {
      console.error('导出失败:', error)
      alert('导出失败，请检查网络连接')
    } finally {
      setIsExporting(false)
    }
  }

  // 重新生成当前阶段内容
  const handleRegenerate = async () => {
    if (!id) return
    setIsLoading(true)
    try {
      const contentType = activeTab === 'scripts' ? 'script' : activeTab
      const response = await contentAPI.regenerate(id, contentType)
      if (response.code === 200) {
        // 刷新数据
        window.location.reload()
      } else {
        setError(response.message || '重新生成失败')
      }
    } catch (err) {
      setError('重新生成失败')
    } finally {
      setIsLoading(false)
    }
  }

  // 重新生成单集剧本
  const handleRegenerateEpisode = async (episodeNumber: number) => {
    if (!id) return
    setIsLoading(true)
    try {
      const response = await contentAPI.regenerate(id, 'script', episodeNumber)
      if (response.code === 200) {
        // 刷新当前集数据
        const episodeRes = await contentAPI.getEpisode(id, episodeNumber)
        if (episodeRes.code === 200) {
          setCurrentScript(episodeRes.data)
        }
        setShowRegenerateOptions(false)
      } else {
        setError(response.message || '重新生成失败')
      }
    } catch (err) {
      setError('重新生成失败')
    } finally {
      setIsLoading(false)
    }
  }

  // 返回创作阶段重新生成全部
  const handleReturnToCreate = () => {
    if (!id) return
    // 确认对话框
    if (confirm('返回创作阶段将可以重新生成全部内容。当前已生成的内容会被保留，你可以选择重新生成任意阶段。是否继续？')) {
      navigate(`/project/${id}/create`)
    }
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

  const tabs = [
    { id: 'synopsis' as TabType, name: '故事梗概', icon: <FileText className="w-4 h-4" /> },
    { id: 'characters' as TabType, name: '人物小传', icon: <Users className="w-4 h-4" /> },
    { id: 'outlines' as TabType, name: '分集大纲', icon: <List className="w-4 h-4" /> },
    { id: 'scripts' as TabType, name: '剧本正文', icon: <BookOpen className="w-4 h-4" /> },
  ]

  return (
    <div className="h-[calc(100vh-140px)] flex gap-4">
      {/* 左侧导航 */}
      <div className="w-64 card flex flex-col">
        <h2 className="font-semibold mb-4 px-2">{project.name}</h2>

        <nav className="space-y-1 flex-1">
          {tabs.map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`w-full flex items-center gap-3 px-3 py-2 rounded-lg text-left transition-colors ${
                activeTab === tab.id
                  ? 'bg-primary text-white'
                  : 'hover:bg-gray-100'
              }`}
            >
              {tab.icon}
              {tab.name}
              {tab.id === 'synopsis' && activeTab !== 'synopsis' && <CheckCircle className="w-4 h-4 ml-auto" />}
            </button>
          ))}
        </nav>

        {/* 剧集列表（仅在剧本正文tab显示） */}
        {activeTab === 'scripts' && (
          <div className="mt-4 pt-4 border-t flex-1 overflow-y-auto">
            <h3 className="text-sm font-medium text-gray-500 mb-2">剧集列表</h3>
            <div className="space-y-1">
              {Array.from({ length: project.totalEpisodes || 80 }, (_, i) => i + 1).map((episodeNum) => (
                <button
                  key={episodeNum}
                  onClick={() => setSelectedEpisode(episodeNum)}
                  className={`w-full text-left px-3 py-2 rounded text-sm flex items-center gap-2 ${
                    selectedEpisode === episodeNum
                      ? 'bg-primary/10 text-primary'
                      : 'hover:bg-gray-100'
                  }`}
                >
                  <span className="text-gray-400">{episodeNum}</span>
                  <span className="flex-1 truncate">第{episodeNum}集</span>
                </button>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* 右侧内容区 */}
      <div className="flex-1 card flex flex-col min-w-0">
        {/* 内容头部 */}
        <div className="flex items-center justify-between mb-4 pb-4 border-b">
          <h3 className="text-lg font-semibold">
            {tabs.find((t) => t.id === activeTab)?.name}
          </h3>
          <div className="flex gap-2">
            <button
              onClick={() => {
                if (activeTab === 'scripts') {
                  setShowRegenerateOptions(true)
                } else {
                  handleRegenerate()
                }
              }}
              disabled={isLoading}
              className="btn-secondary text-sm flex items-center gap-2"
              title={activeTab === 'scripts' ? '选择重新生成方式' : '重新生成当前内容'}
            >
              {isLoading ? <Loader2 className="w-4 h-4 animate-spin" /> : <RotateCcw className="w-4 h-4" />}
              重新生成
            </button>
            <button
              onClick={handleReturnToCreate}
              className="btn-secondary text-sm flex items-center gap-2"
              title="返回创作阶段"
            >
              <ChevronRight className="w-4 h-4 rotate-180" />
              返回创作阶段
            </button>
            <button className="btn-secondary text-sm flex items-center gap-2">
              <Save className="w-4 h-4" />
              保存
            </button>
            <button
              onClick={() => handleExport('docx')}
              disabled={isExporting}
              className="btn-primary text-sm flex items-center gap-2 disabled:opacity-50"
            >
              {isExporting ? (
                <>
                  <span className="animate-spin">⏳</span>
                  导出中...
                </>
              ) : (
                <>
                  <Download className="w-4 h-4" />
                  导出
                </>
              )}
            </button>
          </div>
        </div>

        {error && (
          <div className="mb-4 p-3 bg-red-50 text-red-700 rounded-lg text-sm">
            {error}
          </div>
        )}

        {isLoading && (
          <div className="flex-1 flex items-center justify-center">
            <Loader2 className="w-8 h-8 animate-spin text-primary" />
          </div>
        )}

        {/* 内容区域 */}
        {!isLoading && (
          <div className="flex-1 overflow-y-auto">
            {activeTab === 'synopsis' && (
              <div className="space-y-6 max-w-3xl">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">剧名</label>
                  <input
                    type="text"
                    defaultValue={synopsis.title}
                    className="input text-lg font-semibold"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">一句话简介</label>
                  <input
                    type="text"
                    defaultValue={synopsis.one_liner}
                    className="input"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">故事梗概</label>
                  <textarea
                    defaultValue={synopsis.synopsis}
                    rows={12}
                    className="input resize-none font-mono leading-relaxed"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">核心卖点</label>
                  <div className="flex flex-wrap gap-2">
                    {synopsis.selling_points?.map((point, index) => (
                      <span
                        key={index}
                        className="px-3 py-1 bg-primary/10 text-primary rounded-full text-sm"
                      >
                        {point}
                      </span>
                    ))}
                  </div>
                </div>
              </div>
            )}

            {activeTab === 'characters' && (
              <div className="grid gap-4">
                {characters.length > 0 ? (
                  characters.map((char, index) => (
                    <div key={index} className="p-4 border rounded-lg hover:shadow-md transition-shadow">
                      <div className="flex items-start gap-4">
                        <div className="w-12 h-12 bg-primary/10 rounded-full flex items-center justify-center text-primary font-bold text-lg">
                          {char.name?.[0] || '?'}
                        </div>
                        <div className="flex-1">
                          <div className="flex items-center gap-3 mb-2">
                            <h4 className="font-semibold text-lg">{char.name}</h4>
                            <span className="text-xs px-2 py-1 bg-gray-100 rounded">{char.role}</span>
                            <span className="text-xs text-gray-500">{char.age}</span>
                          </div>

                          {/* 外观信息 */}
                          {char.appearance && (
                            <div className="mb-3 p-2 bg-gray-50 rounded text-sm">
                              <span className="text-gray-500">外观：</span>
                              {[
                                char.appearance.height && `身高${char.appearance.height}`,
                                char.appearance.build && `体型${char.appearance.build}`,
                                char.appearance.hair && `发型${char.appearance.hair}`,
                                char.appearance.clothing_style && `穿着${char.appearance.clothing_style}`,
                                char.appearance.distinctive_features && `特征${char.appearance.distinctive_features}`
                              ].filter(Boolean).join('，')}
                            </div>
                          )}

                          <div className="grid grid-cols-2 gap-4 text-sm">
                            <div>
                              <span className="text-gray-500">性格：</span>
                              {char.personality}
                            </div>
                            <div>
                              <span className="text-gray-500">背景：</span>
                              {char.background}
                            </div>
                            <div>
                              <span className="text-gray-500">目标：</span>
                              {char.goal}
                            </div>
                            <div>
                              <span className="text-gray-500">记忆点：</span>
                              {char.memory_point || char.memoryPoint || ''}
                            </div>
                          </div>

                          {/* 人物关系 */}
                          {char.relationships && (
                            <div className="mt-3 text-sm">
                              <span className="text-gray-500">关系：</span>
                              {char.relationships}
                            </div>
                          )}
                        </div>
                      </div>
                    </div>
                  ))
                ) : (
                  <div className="text-center py-12 text-gray-500">
                    <p>暂无人物数据</p>
                  </div>
                )}
              </div>
            )}

            {activeTab === 'outlines' && (
              <div className="space-y-2">
                {outlines.length > 0 ? (
                  outlines.map((outline) => (
                    <div
                      key={outline.episode_number}
                      className={`p-3 rounded-lg border flex items-start gap-3 ${
                        outline.is_checkpoint ? 'border-orange-200 bg-orange-50' : 'hover:bg-gray-50'
                      }`}
                    >
                      <span className="text-sm font-mono text-gray-400 w-10">
                        {outline.episode_number}
                      </span>
                      <div className="flex-1">
                        <p className="text-sm">{outline.summary}</p>
                        <p className="text-xs text-gray-500 mt-1">
                          卡点：{outline.hook}
                        </p>
                      </div>
                      {outline.is_checkpoint && (
                        <span className="text-xs px-2 py-1 bg-orange-100 text-orange-700 rounded">
                          付费卡点
                        </span>
                      )}
                    </div>
                  ))
                ) : (
                  <div className="text-center py-12 text-gray-500">
                    <p>暂无大纲数据</p>
                  </div>
                )}
              </div>
            )}

            {activeTab === 'scripts' && (
              <div className="h-full flex flex-col">
                {currentScript ? (
                  <>
                    <div className="flex items-center justify-between mb-4">
                      <div className="flex items-center gap-4">
                        <h4 className="font-semibold">
                          第{selectedEpisode}集
                        </h4>
                        <span className="text-sm text-gray-500">
                          字数：{currentScript.word_count || 0}
                        </span>
                      </div>
                      <div className="flex gap-2">
                        <button
                          onClick={() => setSelectedEpisode(Math.max(1, selectedEpisode - 1))}
                          className="text-sm text-gray-500 hover:text-primary"
                        >
                          ← 上一集
                        </button>
                        <button
                          onClick={() => setSelectedEpisode(Math.min(project.totalEpisodes || 80, selectedEpisode + 1))}
                          className="text-sm text-gray-500 hover:text-primary"
                        >
                          下一集 →
                        </button>
                      </div>
                    </div>
                    <textarea
                      defaultValue={currentScript.content}
                      className="input flex-1 resize-none font-mono leading-relaxed text-sm"
                    />
                  </>
                ) : (
                  <div className="text-center py-12 text-gray-500">
                    <p>该集剧本尚未生成</p>
                  </div>
                )}
              </div>
            )}
          </div>
        )}
      </div>

      {/* 重新生成选项弹窗 */}
      {showRegenerateOptions && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-lg max-w-md w-full">
            <div className="p-4 border-b">
              <h3 className="text-lg font-semibold">选择重新生成方式</h3>
            </div>
            <div className="p-4 space-y-3">
              <p className="text-sm text-gray-500 mb-4">
                当前查看：第{selectedEpisode}集
              </p>

              <button
                onClick={() => handleRegenerateEpisode(selectedEpisode)}
                disabled={isLoading}
                className="w-full p-4 border rounded-lg hover:bg-primary/5 hover:border-primary transition-all text-left"
              >
                <div className="font-medium">📝 仅重新生成本集</div>
                <div className="text-sm text-gray-500 mt-1">
                  只重新生成第{selectedEpisode}集剧本，其他集保持不变
                </div>
              </button>

              <button
                onClick={() => {
                  setShowRegenerateOptions(false)
                  handleRegenerate()
                }}
                disabled={isLoading}
                className="w-full p-4 border rounded-lg hover:bg-primary/5 hover:border-primary transition-all text-left"
              >
                <div className="font-medium">📚 重新生成全部剧本</div>
                <div className="text-sm text-gray-500 mt-1">
                  重新生成所有集数的剧本正文
                </div>
              </button>

              <button
                onClick={handleReturnToCreate}
                className="w-full p-4 border rounded-lg hover:bg-orange-50 hover:border-orange-300 transition-all text-left"
              >
                <div className="font-medium">🔄 返回创作阶段</div>
                <div className="text-sm text-gray-500 mt-1">
                  回到创作控制台，可以重新生成任意阶段（梗概、人物、大纲等）
                </div>
              </button>
            </div>
            <div className="p-4 border-t flex justify-end">
              <button
                onClick={() => setShowRegenerateOptions(false)}
                className="btn-secondary"
              >
                取消
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

export default EditorPage
