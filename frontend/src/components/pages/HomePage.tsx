import { useState, useEffect } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import { Plus, Trash2, Download, PauseCircle } from 'lucide-react'
import { useProjectStore } from '../../stores/projectStore'

function HomePage() {
  const navigate = useNavigate()
  const { projects, createProject, deleteProject, loadProjects } = useProjectStore()
  const [isCreating, setIsCreating] = useState(false)
  const [newProjectName, setNewProjectName] = useState('')
  const [isLoading, setIsLoading] = useState(true)

  // 页面加载时从后端获取项目列表
  useEffect(() => {
    loadProjects().then(() => setIsLoading(false))
  }, [])

  const handleCreate = async () => {
    if (!newProjectName.trim()) return
    const project = await createProject(newProjectName)
    setNewProjectName('')
    setIsCreating(false)
    // 自动跳转到需求澄清页
    navigate(`/project/${project.id}/clarify`)
  }

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'clarifying':
        return 'border-l-4 border-l-primary'
      case 'creating':
        return 'border-l-4 border-l-secondary'
      case 'completed':
        return 'border-l-4 border-l-success'
      case 'paused':
        return 'border-l-4 border-l-gray-400'
      default:
        return ''
    }
  }

  const getStatusText = (status: string) => {
    switch (status) {
      case 'clarifying':
        return '需求澄清中'
      case 'creating':
        return '剧本创作中'
      case 'completed':
        return '已完成'
      case 'paused':
        return '已暂停'
      default:
        return status
    }
  }

  return (
    <div className="space-y-6">
      {/* 创建新项目 */}
      <div className="card">
        {!isCreating ? (
          <button
            onClick={() => setIsCreating(true)}
            className="w-full flex items-center justify-center gap-3 p-6 border-2 border-dashed border-gray-300 rounded-lg hover:border-primary hover:bg-primary/5 transition-all"
          >
            <Plus className="w-8 h-8 text-primary" />
            <div className="text-left">
              <h3 className="text-lg font-semibold text-gray-900">创作新剧本</h3>
              <p className="text-sm text-gray-500">从零开始一个全新的短剧项目</p>
            </div>
          </button>
        ) : (
          <div className="p-6 border-2 border-primary rounded-lg bg-primary/5">
            <h3 className="text-lg font-semibold mb-4">创建新项目</h3>
            <div className="flex gap-3">
              <input
                type="text"
                placeholder="请输入项目名称"
                value={newProjectName}
                onChange={(e) => setNewProjectName(e.target.value)}
                className="input flex-1"
                autoFocus
                onKeyDown={(e) => e.key === 'Enter' && handleCreate()}
              />
              <button onClick={handleCreate} className="btn-primary">
                创建
              </button>
              <button
                onClick={() => {
                  setIsCreating(false)
                  setNewProjectName('')
                }}
                className="btn-secondary"
              >
                取消
              </button>
            </div>
          </div>
        )}
      </div>

      {/* 项目列表 */}
      <div>
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-semibold">我的作品</h2>
          <span className="text-sm text-gray-500">共 {projects.length} 个</span>
        </div>

        {isLoading ? (
          <div className="card py-12 text-center">
            <p className="text-gray-500">加载中...</p>
          </div>
        ) : projects.length === 0 ? (
          <div className="card py-12 text-center">
            <p className="text-gray-500">还没有项目，点击上方按钮开始创作吧！</p>
          </div>
        ) : (
          <div className="grid gap-4">
            {projects.map((project) => (
              <div
                key={project.id}
                className={`card ${getStatusColor(project.status)} hover:shadow-md transition-shadow`}
              >
                <div className="flex items-start justify-between">
                  <div className="flex-1">
                    <div className="flex items-center gap-3 mb-2">
                      <h3 className="text-lg font-semibold">{project.name}</h3>
                      <span
                        className={`text-xs px-2 py-1 rounded-full ${
                          project.status === 'completed'
                            ? 'bg-green-100 text-green-700'
                            : project.status === 'creating'
                            ? 'bg-orange-100 text-orange-700'
                            : 'bg-blue-100 text-blue-700'
                        }`}
                      >
                        {getStatusText(project.status)}
                      </span>
                    </div>
                    <p className="text-sm text-gray-500">
                      最后编辑：{new Date(project.updatedAt).toLocaleString()}
                    </p>
                  </div>

                  <div className="flex items-center gap-2">
                    {project.status === 'clarifying' && (
                      <Link
                        to={`/project/${project.id}/clarify`}
                        className="btn-primary text-sm"
                      >
                        继续创作 →
                      </Link>
                    )}
                    {project.status === 'creating' && (
                      <>
                        <Link
                          to={`/project/${project.id}/create`}
                          className="btn-primary text-sm"
                        >
                          查看进度
                        </Link>
                        <button className="btn-secondary p-2">
                          <PauseCircle className="w-4 h-4" />
                        </button>
                      </>
                    )}
                    {project.status === 'completed' && (
                      <>
                        <Link
                          to={`/project/${project.id}/edit`}
                          className="btn-primary text-sm"
                        >
                          查看/编辑
                        </Link>
                        <button
                          onClick={() => {
                            fetch(`/api/v1/projects/${project.id}/export`, {
                              method: 'POST',
                              headers: { 'Content-Type': 'application/json' },
                              body: JSON.stringify({
                                format: 'docx',
                                contents: ['synopsis', 'characters', 'outlines', 'scripts'],
                                episodes: 'all',
                              }),
                            })
                            .then(res => res.json())
                            .then(result => {
                              if (result.code === 200 && result.data?.download_url) {
                                window.open(result.data.download_url, '_blank')
                              } else {
                                alert('导出失败：' + result.message)
                              }
                            })
                            .catch(() => alert('导出失败，请检查网络连接'))
                          }}
                          className="btn-secondary p-2"
                          title="导出"
                        >
                          <Download className="w-4 h-4" />
                        </button>
                      </>
                    )}
                    <button
                      onClick={() => deleteProject(project.id)}
                      className="p-2 text-gray-400 hover:text-error hover:bg-red-50 rounded-md transition-colors"
                    >
                      <Trash2 className="w-4 h-4" />
                    </button>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}

export default HomePage