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
  pendingField?: string  // 当前待询问的字段
  requirementsLocked?: boolean  // 需求是否已锁定

  // V1.2 新增：需求评估与理解
  requirementAssessment?: RequirementAssessment
  understandingDisplay?: UnderstandingDisplay
  understandingSummary?: string  // 需求理解摘要（Markdown格式）

  // V1.3 新增：统一上下文管理
  conversationSummary?: string    // 对话摘要（200字内）
  requirementAnalysis?: string    // 需求分析（300字内）

  // 剧本内容
  storySynopsis?: string
  storyTitle?: string
  oneLiner?: string
  sellingPoints?: string[]
  characterProfiles?: Character[]
  relationshipMap?: string
  episodeOutlines?: EpisodeOutline[]
  scripts?: EpisodeScript[]

  // 创作进度
  creationProgress?: CreationProgress
}

// 需求评估字段
export interface RequirementAssessmentField {
  status: 'empty' | 'partial' | 'confirmed'
  understanding: string
  confidence: number
  suggestion: string
}

// 需求评估
export interface RequirementAssessment {
  genre?: RequirementAssessmentField
  protagonist?: RequirementAssessmentField
  conflict?: RequirementAssessmentField
  target_audience?: RequirementAssessmentField
  episodes?: RequirementAssessmentField
  style?: RequirementAssessmentField
  // 索引签名，允许通过任意字符串访问
  [key: string]: RequirementAssessmentField | undefined
}

// 需求理解展示
export interface UnderstandingDisplay {
  title?: string
  genre_summary?: string
  protagonist_summary?: string
  conflict_summary?: string
  style_summary?: string
  next_steps?: string[]
}

export interface Message {
  id?: string
  role: 'user' | 'assistant' | 'system'
  content: string
  type?: 'text' | 'option' | 'summary' | 'error'
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

// 需求确认书（V4 - 卡片展示结构）
export interface RequirementConfirmation {
  // 基础信息
  title: string
  genre: string
  episodes: string
  target_audience: string

  // 展示用摘要字段（卡片渲染）
  protagonist_summary: string      // 主角设定
  core_conflict_summary: string    // 核心冲突
  plot_summary: string             // 剧情规划（起承转合）
  world_building_summary: string   // 世界观设定
  romance_line_summary: string     // 感情线设计（恋爱类有内容，其他为空字符串）
  style_summary: string            // 风格基调
  checkpoint_summary: string       // 付费卡点设计

  // 其他信息
  selling_points: string[]         // 核心卖点
  special_notes: string            // 特殊说明

  // 结构化数据（给创作阶段使用）
  structured_data: {
    protagonist: {
      name: string
      identity: string
      personality: string
      background: string
      goal: string
      golden_finger: string
    }
    supporting_roles: Array<{
      name: string
      role_type: string
      description: string
    }>
    checkpoints: Array<{
      episode: number
      hook: string
      emotion: string
    }>
  }
}

// API 响应
export interface ApiResponse<T = any> {
  code: number
  message: string
  data: T
}
