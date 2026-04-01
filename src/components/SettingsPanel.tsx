import React, { useState, useEffect, useCallback } from 'react'
import { createPortal } from 'react-dom'

type TabType = 'answer' | 'sound' | 'display' | 'review'

interface AppSettings {
  repeatWrong: boolean
  showAnswer: boolean
  shuffle: boolean
  autoSubmit: boolean
  errorBook: boolean
  voice: string
  playbackCount: string
  playbackSpeed: string
  volume: string
  interval: string
  dictationMode: boolean
  darkMode: boolean
  fontSize: string
  showPhonetic: boolean
  showPos: boolean
  reviewInterval: string
  reviewLimit: string
}

interface SettingsPanelProps {
  showSettings: boolean
  onClose: () => void
}

const defaultSettings: AppSettings = {
  repeatWrong: true,
  showAnswer: false,
  shuffle: true,
  autoSubmit: false,
  errorBook: true,
  voice: 'default',
  playbackCount: '2',
  playbackSpeed: '0.8',
  volume: '100',
  interval: '2',
  dictationMode: false,
  darkMode: false,
  fontSize: 'medium',
  showPhonetic: true,
  showPos: true,
  reviewInterval: '1',
  reviewLimit: 'unlimited'
}

function SettingsPanel({ showSettings, onClose }: SettingsPanelProps) {
  const [activeTab, setActiveTab] = useState<TabType>('answer')
  const [settings, setSettings] = useState<AppSettings>(() => {
    const saved = localStorage.getItem('app_settings')
    return saved ? JSON.parse(saved) : defaultSettings
  })

  // Apply settings to document on mount and when settings change
  useEffect(() => {
    document.documentElement.setAttribute('data-theme', settings.darkMode ? 'dark' : 'light')
    document.documentElement.setAttribute('data-font-size', settings.fontSize || 'medium')
  }, [settings.darkMode, settings.fontSize])

  useEffect(() => {
    if (!showSettings) return
    const root = document.documentElement
    const body = document.body
    const prevBodyOverflow = body.style.overflow
    const prevBodyPaddingRight = body.style.paddingRight
    const prevRootOverflow = root.style.overflow
    const prevRootPaddingRight = root.style.paddingRight
    const scrollbarWidth = window.innerWidth - document.documentElement.clientWidth
    if (scrollbarWidth > 0) {
      const compensation = `${scrollbarWidth}px`
      body.style.paddingRight = compensation
      root.style.paddingRight = compensation
    }
    body.style.overflow = 'hidden'
    root.style.overflow = 'hidden'
    const onKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose()
    }
    document.addEventListener('keydown', onKeyDown)
    return () => {
      body.style.overflow = prevBodyOverflow
      body.style.paddingRight = prevBodyPaddingRight
      root.style.overflow = prevRootOverflow
      root.style.paddingRight = prevRootPaddingRight
      document.removeEventListener('keydown', onKeyDown)
    }
  }, [showSettings, onClose])

  const updateSetting = <K extends keyof AppSettings>(key: K, value: AppSettings[K]) => {
    const newSettings = { ...settings, [key]: value }
    setSettings(newSettings)
    localStorage.setItem('app_settings', JSON.stringify(newSettings))
    // Apply immediately
    if (key === 'darkMode') {
      document.documentElement.setAttribute('data-theme', value ? 'dark' : 'light')
    }
    if (key === 'fontSize') {
      document.documentElement.setAttribute('data-font-size', String(value))
    }
  }

  const onOverlayClick = useCallback(
    (e: React.MouseEvent<HTMLDivElement>) => {
      if (e.target === e.currentTarget) onClose()
    },
    [onClose],
  )

  if (!showSettings) return null

  return createPortal(
    <div className="settings-overlay show" onClick={onOverlayClick}>
      <div className="settings-modal">
        <div className="settings-header">
          <h2 className="settings-title">设置</h2>
          <button className="settings-close" onClick={onClose}>
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <line x1="18" y1="6" x2="6" y2="18"></line>
              <line x1="6" y1="6" x2="18" y2="18"></line>
            </svg>
          </button>
        </div>
        <div className="settings-body">
          {/* Sidebar Tabs */}
          <div className="settings-sidebar">
            <button className={`settings-tab ${activeTab === 'answer' ? 'active' : ''}`} onClick={() => setActiveTab('answer')}>
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"></path>
              </svg>
              <span>答题</span>
            </button>
            <button className={`settings-tab ${activeTab === 'sound' ? 'active' : ''}`} onClick={() => setActiveTab('sound')}>
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <polygon points="11 5 6 9 2 9 2 15 6 15 11 19 11 5"></polygon>
                <path d="M19.07 4.93a10 10 0 0 1 0 14.14M15.54 8.46a5 5 0 0 1 0 7.07"></path>
              </svg>
              <span>声音</span>
            </button>
            <button className={`settings-tab ${activeTab === 'display' ? 'active' : ''}`} onClick={() => setActiveTab('display')}>
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <rect x="2" y="3" width="20" height="14" rx="2" ry="2"></rect>
                <line x1="8" y1="21" x2="16" y2="21"></line>
                <line x1="12" y1="17" x2="12" y2="21"></line>
              </svg>
              <span>显示</span>
            </button>
            <button className={`settings-tab ${activeTab === 'review' ? 'active' : ''}`} onClick={() => setActiveTab('review')}>
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <polyline points="23 4 23 10 17 10"></polyline>
                <polyline points="1 20 1 14 7 14"></polyline>
                <path d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15"></path>
              </svg>
              <span>复习</span>
            </button>
          </div>

          {/* Settings Content Panels */}
          <div className="settings-content settings-content--native">
            {/* Answer Settings */}
            {activeTab === 'answer' && (
            <div className="settings-panel active">
                <div className="settings-item">
                  <div className="settings-item-info">
                    <div className="settings-item-title">错词循环</div>
                    <div className="settings-item-desc">答错的单词将在本轮中循环出现</div>
                  </div>
                  <label className="switch">
                    <input type="checkbox" checked={settings.repeatWrong} onChange={(e) => updateSetting('repeatWrong', e.target.checked)} />
                    <span className="switch-slider"></span>
                  </label>
                </div>
                <div className="settings-item">
                  <div className="settings-item-info">
                    <div className="settings-item-title">答错显示答案</div>
                    <div className="settings-item-desc">答错后显示正确答案供参考</div>
                  </div>
                  <label className="switch">
                    <input type="checkbox" checked={settings.showAnswer} onChange={(e) => updateSetting('showAnswer', e.target.checked)} />
                    <span className="switch-slider"></span>
                  </label>
                </div>
                <div className="settings-item">
                  <div className="settings-item-info">
                    <div className="settings-item-title">随机顺序</div>
                    <div className="settings-item-desc">随机打乱单词学习顺序</div>
                  </div>
                  <label className="switch">
                    <input type="checkbox" checked={settings.shuffle} onChange={(e) => updateSetting('shuffle', e.target.checked)} />
                    <span className="switch-slider"></span>
                  </label>
                </div>
                <div className="settings-item">
                  <div className="settings-item-info">
                    <div className="settings-item-title">自动提交</div>
                    <div className="settings-item-desc">拼写模式下输入完成自动提交</div>
                  </div>
                  <label className="switch">
                    <input type="checkbox" checked={settings.autoSubmit} onChange={(e) => updateSetting('autoSubmit', e.target.checked)} />
                    <span className="switch-slider"></span>
                  </label>
                </div>
                <div className="settings-item">
                  <div className="settings-item-info">
                    <div className="settings-item-title">错误本</div>
                    <div className="settings-item-desc">记录答错单词到错误本</div>
                  </div>
                  <label className="switch">
                    <input type="checkbox" checked={settings.errorBook} onChange={(e) => updateSetting('errorBook', e.target.checked)} />
                    <span className="switch-slider"></span>
                  </label>
                </div>
              </div>
            )}

            {/* Sound Settings */}
            {activeTab === 'sound' && (
            <div className="settings-panel active">
                <div className="settings-item">
                  <div className="settings-item-info">
                    <div className="settings-item-title">语音选择</div>
                    <div className="settings-item-desc">选择单词发音口音</div>
                  </div>
                  <select className="settings-select" value={settings.voice} onChange={(e) => updateSetting('voice', e.target.value)}>
                    <option value="default">默认</option>
                    <option value="uk">英式发音</option>
                    <option value="us">美式发音</option>
                  </select>
                </div>
                <div className="settings-item">
                  <div className="settings-item-info">
                    <div className="settings-item-title">播放次数</div>
                    <div className="settings-item-desc">每个单词的发音播放次数</div>
                  </div>
                  <select className="settings-select" value={settings.playbackCount} onChange={(e) => updateSetting('playbackCount', e.target.value)}>
                    <option value="1">1次</option>
                    <option value="2">2次</option>
                    <option value="3">3次</option>
                  </select>
                </div>
                <div className="settings-item">
                  <div className="settings-item-info">
                    <div className="settings-item-title">播放速度</div>
                    <div className="settings-item-desc">发音播放的语速快慢</div>
                  </div>
                  <select className="settings-select" value={settings.playbackSpeed} onChange={(e) => updateSetting('playbackSpeed', e.target.value)}>
                    <option value="0.6">慢速 0.6x</option>
                    <option value="0.8">正常 0.8x</option>
                    <option value="1.0">快速 1.0x</option>
                    <option value="1.2">极速 1.2x</option>
                  </select>
                </div>
                <div className="settings-item">
                  <div className="settings-item-info">
                    <div className="settings-item-title">音量</div>
                    <div className="settings-item-desc">发音播放音量大小</div>
                  </div>
                  <select className="settings-select" value={settings.volume} onChange={(e) => updateSetting('volume', e.target.value)}>
                    <option value="40">低</option>
                    <option value="70">中</option>
                    <option value="100">高</option>
                  </select>
                </div>
                <div className="settings-item">
                  <div className="settings-item-info">
                    <div className="settings-item-title">播放间隔</div>
                    <div className="settings-item-desc">连续播放时每词间隔秒数</div>
                  </div>
                  <select className="settings-select" value={settings.interval} onChange={(e) => updateSetting('interval', e.target.value)}>
                    <option value="1">1秒</option>
                    <option value="2">2秒</option>
                    <option value="3">3秒</option>
                    <option value="5">5秒</option>
                  </select>
                </div>
                <div className="settings-item">
                  <div className="settings-item-info">
                    <div className="settings-item-title">连续播放模式</div>
                    <div className="settings-item-desc">自动依次播放每个单词</div>
                  </div>
                  <label className="switch">
                    <input type="checkbox" checked={settings.dictationMode} onChange={(e) => updateSetting('dictationMode', e.target.checked)} />
                    <span className="switch-slider"></span>
                  </label>
                </div>
              </div>
            )}

            {/* Display Settings */}
            {activeTab === 'display' && (
            <div className="settings-panel active">
                <div className="settings-item">
                  <div className="settings-item-info">
                    <div className="settings-item-title">深色模式</div>
                    <div className="settings-item-desc">切换深色/浅色主题</div>
                  </div>
                  <label className="switch">
                    <input type="checkbox" checked={settings.darkMode} onChange={(e) => updateSetting('darkMode', e.target.checked)} />
                    <span className="switch-slider"></span>
                  </label>
                </div>
                <div className="settings-item">
                  <div className="settings-item-info">
                    <div className="settings-item-title">字体大小</div>
                    <div className="settings-item-desc">调整界面显示字体大小</div>
                  </div>
                  <select className="settings-select" value={settings.fontSize} onChange={(e) => updateSetting('fontSize', e.target.value)}>
                    <option value="small">小</option>
                    <option value="medium">中</option>
                    <option value="large">大</option>
                  </select>
                </div>
                <div className="settings-item">
                  <div className="settings-item-info">
                    <div className="settings-item-title">显示音标</div>
                    <div className="settings-item-desc">在单词下方显示国际音标</div>
                  </div>
                  <label className="switch">
                    <input type="checkbox" checked={settings.showPhonetic} onChange={(e) => updateSetting('showPhonetic', e.target.checked)} />
                    <span className="switch-slider"></span>
                  </label>
                </div>
                <div className="settings-item">
                  <div className="settings-item-info">
                    <div className="settings-item-title">显示词性</div>
                    <div className="settings-item-desc">显示单词的词性标签</div>
                  </div>
                  <label className="switch">
                    <input type="checkbox" checked={settings.showPos} onChange={(e) => updateSetting('showPos', e.target.checked)} />
                    <span className="switch-slider"></span>
                  </label>
                </div>
              </div>
            )}

            {/* Review Settings */}
            {activeTab === 'review' && (
            <div className="settings-panel active">
                <div className="settings-item">
                  <div className="settings-item-info">
                    <div className="settings-item-title">复习间隔</div>
                    <div className="settings-item-desc">艾宾浩斯遗忘曲线复习间隔天数</div>
                  </div>
                  <select className="settings-select" value={settings.reviewInterval} onChange={(e) => updateSetting('reviewInterval', e.target.value)}>
                    <option value="1">1天</option>
                    <option value="3">3天</option>
                    <option value="7">7天</option>
                  </select>
                </div>
                <div className="settings-item">
                  <div className="settings-item-info">
                    <div className="settings-item-title">复习数量</div>
                    <div className="settings-item-desc">每次复习的单词数量上限</div>
                  </div>
                  <select className="settings-select" value={settings.reviewLimit} onChange={(e) => updateSetting('reviewLimit', e.target.value)}>
                    <option value="10">10个</option>
                    <option value="20">20个</option>
                    <option value="50">50个</option>
                    <option value="100">100个</option>
                    <option value="unlimited">不设上限</option>
                  </select>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>,
    document.body,
  )
}

export default SettingsPanel
