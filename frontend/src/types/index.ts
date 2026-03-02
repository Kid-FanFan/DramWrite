// 项目类型定义

export interface Project {
  id: string
  name: string
  status: 'clarifying' | 'locked' | 'creating' | 'paused' | 'completed' | 'failed'
  genre?: string
  totalEpisodes: number
  completeness: number
  createdAt: string
  updatedAt: string

  // 需求澄清
  requirements: Record<string, any>
  messages: Message[]

  // 剧本内容
  storySynopsis?: string
  storyTitle?: string
  characterProfiles?: Character[]
  episodeOutlines?: EpisodeOutline[]
  scripts?: EpisodeScript[]

  // 创作进度
  creationProgress?: CreationProgress
}

export interface Message {
  role: 'user' | 'assistant' | 'system'
  content: string
  type?: 'text' | 'option' | 'summary'
  options?: Option[]
  createdAt?: string
}

export interface Option {
  id: number | string
  title: string
  description: string
}

export interface Character {
  name: string
  role: '主角' | '反派' | '配角'
  age: string
  personality: string
  background: string
  goal: string
  memoryPoint: string
}

export interface EpisodeOutline {
  episodeNumber: number
  summary: string
  hook: string
  isCheckpoint: boolean
}

export interface EpisodeScript {
  episodeNumber: number
  title: string
  content: string
  wordCount: number
  status: 'pending' | 'generating' | 'completed' | 'failed'
  qualityReport?: QualityReport
}

export interface QualityReport {
  pass: boolean
  wordCount: number
  issues: string[]
  suggestions: string[]
}

export interface CreationProgress {
  step: string
  status: 'pending' | 'in_progress' | 'completed' | 'failed'
  percentage: number
  completedEpisodes: number
  totalEpisodes: number
  estimatedRemainingTime?: number
}

// LLM 配置
export interface LLMConfig {
  provider: string
  apiKey: string
  apiBase?: string
  model: string
  temperature: number
  maxTokens: number
}

// 应用设置
export interface AppSettings {
  llm: LLMConfig
  defaults: {
    episodes: number
    wordsPerEpisode: string
  }
}

// 需求确认书（由大模型优化生成）
export interface RequirementConfirmation {
  title: string
  genre: string
  episodes: string
  target_audience: string
  protagonist: {
    name: string
    identity: string
    personality: string
    background: string
    goal: string
    golden_finger?: string
  }
  supporting_roles?: Array<{
    name: string
    role_type: string
    description: string
  }>
  core_conflict: string
  plot_summary: string
  style: string
  selling_points?: string[]
  special_requirements?: string
}

// API 响应
export interface ApiResponse<T = any> {
  code: number
  message: string
  data: T
}
