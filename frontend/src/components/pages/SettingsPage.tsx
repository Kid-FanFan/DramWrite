import { useState, useEffect } from 'react'
import { Check, AlertCircle, HardDrive, Save, RotateCcw } from 'lucide-react'

const LLM_PROVIDERS = [
  { id: 'tongyi', name: '通义千问' },
  { id: 'wenxin', name: '文心一言' },
  { id: 'zhipu', name: '智谱AI' },
  { id: 'doubao', name: '豆包' },
  { id: 'kimi', name: 'Kimi' },
  { id: 'gemini', name: 'Gemini' },
  { id: 'deepseek', name: 'DeepSeek' },
  { id: 'openai', name: 'OpenAI' },
  { id: 'claude', name: 'Claude' },
  { id: 'custom', name: '自定义' },
]

// 默认模型
const DEFAULT_MODELS: Record<string, string> = {
  tongyi: 'qwen-max',
  wenxin: 'ERNIE-Bot-4',
  zhipu: 'glm-4',
  doubao: 'doubao-pro-128k',
  kimi: 'moonshot-v1-128k',
  gemini: 'gemini-pro',
  deepseek: 'deepseek-chat',
  openai: 'gpt-4',
  claude: 'claude-3-sonnet-20240229',
  custom: '',
}

// 默认配置
const DEFAULT_CONFIG = {
  provider: 'tongyi',
  apiKey: '',
  apiBase: '',
  model: 'qwen-max',
  temperature: 0.7,
  maxTokens: 4000,
}

function SettingsPage() {
  const [config, setConfig] = useState(DEFAULT_CONFIG)
  const [testStatus, setTestStatus] = useState<'idle' | 'testing' | 'success' | 'error'>('idle')
  const [testMessage, setTestMessage] = useState('')
  const [isSaving, setIsSaving] = useState(false)
  const [saveSuccess, setSaveSuccess] = useState(false)
  const [isLoading, setIsLoading] = useState(true)

  // 从后端加载配置
  useEffect(() => {
    fetchConfig()
  }, [])

  const fetchConfig = async () => {
    try {
      const response = await fetch('/api/v1/settings/llm')
      const result = await response.json()
      if (result.code === 200 && result.data) {
        setConfig(prev => ({ ...prev, ...result.data }))
      }
    } catch (error) {
      console.error('加载配置失败:', error)
    } finally {
      setIsLoading(false)
    }
  }

  // 处理提供商变更
  const handleProviderChange = (providerId: string) => {
    setConfig({
      ...config,
      provider: providerId,
      model: DEFAULT_MODELS[providerId] || '',
      apiBase: '',
    })
  }

  // 测试连接
  const handleTestConnection = async () => {
    if (!config.apiKey) {
      setTestStatus('error')
      setTestMessage('请输入 API Key')
      return
    }

    setTestStatus('testing')
    setTestMessage('')

    try {
      const response = await fetch('/api/v1/settings/llm/test', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          provider: config.provider,
          apiKey: config.apiKey,
          apiBase: config.apiBase,
          model: config.model,
          temperature: config.temperature,
          maxTokens: config.maxTokens,
        }),
      })

      const result = await response.json()

      if (result.data?.success) {
        setTestStatus('success')
        setTestMessage(`连接成功 (${result.data.responseTime}s)`)
      } else {
        setTestStatus('error')
        setTestMessage(result.data?.message || '连接失败')
      }
    } catch (error) {
      setTestStatus('error')
      setTestMessage('网络错误，请检查后端服务')
    }
  }

  // 保存设置
  const handleSave = async () => {
    setIsSaving(true)

    try {
      const response = await fetch('/api/v1/settings/llm', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(config),
      })

      if (response.ok) {
        setSaveSuccess(true)
        setTimeout(() => setSaveSuccess(false), 3000)
      }
    } catch (error) {
      console.error('保存失败:', error)
    } finally {
      setIsSaving(false)
    }
  }

  // 恢复默认
  const handleReset = () => {
    if (confirm('确定要恢复默认设置吗？')) {
      setConfig(DEFAULT_CONFIG)
    }
  }

  if (isLoading) {
    return (
      <div className="max-w-3xl mx-auto py-12 text-center">
        <p className="text-gray-500">加载中...</p>
      </div>
    )
  }

  return (
    <div className="max-w-3xl mx-auto space-y-6 pb-12">
      <h1 className="text-2xl font-bold">设置</h1>

      {/* LLM 配置 */}
      <div className="card space-y-6">
        <h2 className="text-lg font-semibold border-b pb-3">🤖 大模型配置</h2>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            模型提供商 *
          </label>
          <div className="grid grid-cols-5 gap-2">
            {LLM_PROVIDERS.map((provider) => (
              <button
                key={provider.id}
                type="button"
                onClick={() => handleProviderChange(provider.id)}
                className={`p-2 text-sm rounded-md border transition-all ${
                  config.provider === provider.id
                    ? 'border-primary bg-primary/10 text-primary'
                    : 'border-gray-200 hover:border-gray-300'
                }`}
              >
                {provider.name}
              </button>
            ))}
          </div>
        </div>

        <div>
          <label htmlFor="apiKey" className="block text-sm font-medium text-gray-700 mb-2">
            API Key *
          </label>
          <input
            id="apiKey"
            type="password"
            value={config.apiKey}
            onChange={(e) => setConfig({ ...config, apiKey: e.target.value })}
            placeholder="输入你的 API Key"
            className="input w-full"
          />
        </div>

        <div>
          <label htmlFor="apiBase" className="block text-sm font-medium text-gray-700 mb-2">
            API Base URL（可选，自定义模型时需要）
          </label>
          <input
            id="apiBase"
            type="text"
            value={config.apiBase}
            onChange={(e) => setConfig({ ...config, apiBase: e.target.value })}
            placeholder="https://api.example.com/v1"
            className="input w-full"
          />
        </div>

        <div>
          <label htmlFor="model" className="block text-sm font-medium text-gray-700 mb-2">
            模型名称
          </label>
          <input
            id="model"
            type="text"
            value={config.model}
            onChange={(e) => setConfig({ ...config, model: e.target.value })}
            placeholder="模型名称"
            className="input w-full"
          />
        </div>

        <div>
          <label htmlFor="temperature" className="block text-sm font-medium text-gray-700 mb-2">
            Temperature: {config.temperature}
          </label>
          <input
            id="temperature"
            type="range"
            min="0"
            max="2"
            step="0.1"
            value={config.temperature}
            onChange={(e) =>
              setConfig({ ...config, temperature: parseFloat(e.target.value) })
            }
            className="w-full"
          />
          <p className="text-xs text-gray-500 mt-1">
            较低：更严谨规范 / 较高：更有创意
          </p>
        </div>

        <div className="flex items-center gap-4">
          <button
            type="button"
            onClick={handleTestConnection}
            disabled={testStatus === 'testing'}
            className="btn-secondary"
          >
            {testStatus === 'testing' ? '测试中...' : '测试连接'}
          </button>
          {testStatus === 'success' && (
            <span className="text-sm text-green-600 flex items-center gap-1">
              <Check className="w-4 h-4" /> {testMessage}
            </span>
          )}
          {testStatus === 'error' && (
            <span className="text-sm text-red-600 flex items-center gap-1">
              <AlertCircle className="w-4 h-4" /> {testMessage}
            </span>
          )}
        </div>
      </div>

      {/* 保存按钮 */}
      <div className="flex justify-end gap-3">
        <button
          type="button"
          onClick={handleReset}
          className="btn-secondary flex items-center gap-2"
        >
          <RotateCcw className="w-4 h-4" />
          恢复默认
        </button>
        <button
          type="button"
          onClick={handleSave}
          disabled={isSaving}
          className="btn-primary flex items-center gap-2"
        >
          {isSaving ? (
            <>
              <span className="animate-spin">⏳</span>
              保存中...
            </>
          ) : (
            <>
              <Save className="w-4 h-4" />
              保存设置
            </>
          )}
        </button>
      </div>

      {/* 保存成功提示 */}
      {saveSuccess && (
        <div className="fixed bottom-4 right-4 bg-green-500 text-white px-4 py-2 rounded-lg shadow-lg flex items-center gap-2">
          <Check className="w-4 h-4" />
          设置已保存
        </div>
      )}
    </div>
  )
}

export default SettingsPage
