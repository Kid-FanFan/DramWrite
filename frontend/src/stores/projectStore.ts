import { create } from 'zustand'
import type { Project, Message } from '../types'

interface ProjectState {
  projects: Project[]
  currentProjectId: string | null
  isLoading: boolean

  // Actions
  loadProjects: () => Promise<void>
  createProject: (name: string) => Promise<Project>
  deleteProject: (id: string) => Promise<void>
  getProject: (id: string) => Project | undefined
  updateProject: (id: string, updates: Partial<Project>) => void
  addMessage: (projectId: string, message: Message) => void
  setCurrentProject: (id: string | null) => void
  fetchProject: (id: string) => Promise<Project | null>
}

// API 调用函数
const projectAPI = {
  list: async () => {
    const response = await fetch('/api/v1/projects')
    return await response.json()
  },
  create: async (name: string) => {
    const response = await fetch('/api/v1/projects', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ name }),
    })
    return await response.json()
  },
  get: async (id: string) => {
    const response = await fetch(`/api/v1/projects/${id}`)
    return await response.json()
  },
  delete: async (id: string) => {
    const response = await fetch(`/api/v1/projects/${id}`, {
      method: 'DELETE',
    })
    return await response.json()
  },
}

// 转换后端项目格式为前端格式
const convertBackendProject = (backendProject: any): Project => {
  // 安全获取数组字段（防止null/undefined）
  const safeArray = (val: any): any[] => Array.isArray(val) ? val : []

  return {
    id: backendProject.id || backendProject.project_id,
    name: backendProject.name || backendProject.project_name,
    status: backendProject.status,
    totalEpisodes: backendProject.total_episodes || 80,
    completeness: backendProject.completeness || 0,
    createdAt: backendProject.created_at,
    updatedAt: backendProject.updated_at,
    requirements: backendProject.requirements || {},
    messages: backendProject.messages || [],
    pendingField: backendProject.pending_field || backendProject.pendingField,
    // V1.2 新增字段
    requirementAssessment: backendProject.requirement_assessment || backendProject.requirementAssessment,
    understandingDisplay: backendProject.understanding_display || backendProject.understandingDisplay,
    understandingSummary: backendProject.understanding_summary || backendProject.understandingSummary,
    // 创作内容字段（snake_case -> camelCase），使用安全获取
    storySynopsis: backendProject.story_synopsis || backendProject.storySynopsis || '',
    storyTitle: backendProject.story_title || backendProject.storyTitle || '',
    oneLiner: backendProject.one_liner || backendProject.oneLiner || '',
    sellingPoints: safeArray(backendProject.selling_points || backendProject.sellingPoints),
    characterProfiles: safeArray(backendProject.character_profiles || backendProject.characterProfiles),
    relationshipMap: backendProject.relationship_map || backendProject.relationshipMap || '',
    episodeOutlines: safeArray(backendProject.episode_outlines || backendProject.episodeOutlines),
    scripts: safeArray(backendProject.scripts || backendProject.scripts),
    creationProgress: backendProject.creation_progress || backendProject.creationProgress,
  }
}

export const useProjectStore = create<ProjectState>()(
  (set, get) => ({
    projects: [],
    currentProjectId: null,
    isLoading: false,

    // 从后端加载项目列表
    loadProjects: async () => {
      set({ isLoading: true })
      try {
        const response = await projectAPI.list()
        if (response.code === 200) {
          const projects = (response.data.items || []).map(convertBackendProject)
          set({ projects })
        }
      } catch (err) {
        console.error('加载项目列表失败:', err)
      } finally {
        set({ isLoading: false })
      }
    },

    createProject: async (name: string) => {
      // 调用后端 API 创建项目
      const response = await projectAPI.create(name)

      if (response.code !== 200) {
        throw new Error(response.message || '创建项目失败')
      }

      const project = convertBackendProject(response.data)

      set((state) => ({
        projects: [project, ...state.projects],
        currentProjectId: project.id,
      }))

      return project
    },

    deleteProject: async (id: string) => {
      // 调用后端 API 删除
      try {
        await projectAPI.delete(id)
      } catch (err) {
        console.error('后端删除失败:', err)
      }
      // 从本地状态中移除
      set((state) => ({
        projects: state.projects.filter((p) => p.id !== id),
        currentProjectId: state.currentProjectId === id ? null : state.currentProjectId,
      }))
    },

    getProject: (id: string) => {
      return get().projects.find((p) => p.id === id)
    },

    // 从后端获取单个项目详情
    fetchProject: async (id: string) => {
      try {
        const response = await projectAPI.get(id)
        if (response.code === 200) {
          const project = convertBackendProject(response.data)
          // 更新本地状态
          set((state) => {
            const exists = state.projects.find((p) => p.id === id)
            if (exists) {
              return {
                projects: state.projects.map((p) =>
                  p.id === id ? project : p
                ),
              }
            } else {
              return { projects: [...state.projects, project] }
            }
          })
          return project
        }
        return null
      } catch (err) {
        console.error('获取项目详情失败:', err)
        return null
      }
    },

    updateProject: (id: string, updates: Partial<Project>) => {
      set((state) => ({
        projects: state.projects.map((p) =>
          p.id === id
            ? { ...p, ...updates, updatedAt: new Date().toISOString() }
            : p
        ),
      }))
    },

    addMessage: (projectId: string, message: Message) => {
      const { getProject, updateProject } = get()
      const project = getProject(projectId)
      if (!project) return

      const newMessage = {
        ...message,
        createdAt: new Date().toISOString(),
      }

      updateProject(projectId, {
        messages: [...project.messages, newMessage],
      })
    },

    setCurrentProject: (id: string | null) => {
      set({ currentProjectId: id })
    },
  })
)
