import React, { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import SettingsPanel from './SettingsPanel'

function Header({ user, currentDay, mode, onLogout, onModeChange, onDayChange }) {
  const [showModeDropdown, setShowModeDropdown] = useState(false)
  const [showDayDropdown, setShowDayDropdown] = useState(false)
  const [showUserDropdown, setShowUserDropdown] = useState(false)
  const [showHelp, setShowHelp] = useState(false)
  const [showSettings, setShowSettings] = useState(false)
  const navigate = useNavigate()

  const modeNames = {
    'smart': '智能模式',
    'dictation': '听写模式',
    'listening': '听音选义',
    'radio': '随身听',
    'blind': '默写模式'
  }

  const handleLogout = () => {
    onLogout()
    navigate('/login')
  }

  return (
    <header className="header">
      <div className="header-left">
        <div className="logo">
          <img src="/images/logo.png" alt="Logo" className="logo-img" />
          <span className="logo-text">雅思冲刺</span>
        </div>
      </div>

      <div className="header-center"></div>

      <div className="header-right">
        {user && currentDay && (
          <>
            <div className="day-selector-wrapper">
              <div className="day-selector" onClick={() => setShowDayDropdown(!showDayDropdown)}>
                <span className="day-selector-current">超核心词汇 Day {currentDay}</span>
                <svg className="day-selector-arrow" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <polyline points="6 9 12 15 18 9"></polyline>
                </svg>
              </div>
              {showDayDropdown && (
                <div className="day-dropdown">
                  {Array.from({ length: 30 }, (_, i) => (
                    <div
                      key={i + 1}
                      className={`day-dropdown-item ${currentDay === i + 1 ? 'active' : ''}`}
                      onClick={() => {
                        onDayChange(i + 1)
                        setShowDayDropdown(false)
                      }}
                    >
                      Day {i + 1}
                    </div>
                  ))}
                </div>
              )}
            </div>

            <div className="mode-selector-wrapper">
              <button className="header-btn mode-btn" onClick={() => setShowModeDropdown(!showModeDropdown)}>
                <span>{modeNames[mode]}</span>
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <polyline points="6 9 12 15 18 9"></polyline>
                </svg>
              </button>

              {showModeDropdown && (
                <div className="mode-dropdown">
                  {Object.entries(modeNames).map(([key, name]) => (
                    <div
                      key={key}
                      className={`mode-dropdown-item ${mode === key ? 'active' : ''}`}
                      onClick={() => {
                        onModeChange(key)
                        setShowModeDropdown(false)
                      }}
                    >
                      <span>{name}</span>
                    </div>
                  ))}
                </div>
              )}
            </div>

            <button className="header-btn" title="设置" onClick={() => setShowSettings(true)}>
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <circle cx="12" cy="12" r="3"></circle>
                <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06-.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z"></path>
              </svg>
            </button>
          </>
        )}

        <button className="header-btn" title="帮助" onClick={() => setShowHelp(true)}>
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
            <circle cx="12" cy="12" r="10"></circle>
            <path d="M9.09 9a3 3 0 0 1 5.66 0 2.48 2.48 0 0 1-.6 1.85c-.55.6-1.26 1.08-1.9 1.63-.6.52-.96 1.25-.96 2.07V15"></path>
            <circle cx="12" cy="18.5" r="0.8" fill="currentColor" stroke="none"></circle>
          </svg>
        </button>

        <button className="header-btn" title="主页" onClick={() => navigate('/')}>
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"></path>
            <polyline points="9 22 9 12 15 12 15 22"></polyline>
          </svg>
        </button>

        {user && (
          <div className="user-menu">
            <button className="user-btn" onClick={() => setShowUserDropdown(!showUserDropdown)}>
              <span>{user.username?.[0]?.toUpperCase() || '?'}</span>
            </button>
            {showUserDropdown && (
              <div className="user-dropdown">
                <button className="dropdown-item" onClick={handleLogout}>
                  退出登录
                </button>
              </div>
            )}
          </div>
        )}
      </div>

      {showHelp && (
        <div className="settings-overlay show" onClick={(e) => e.target.classList.contains('settings-overlay') && setShowHelp(false)}>
          <div className="settings-modal" style={{ maxWidth: '480px' }}>
            <div className="settings-header">
              <h2 className="settings-title">帮助</h2>
              <button className="settings-close" onClick={() => setShowHelp(false)}>
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <line x1="18" y1="6" x2="6" y2="18"></line>
                  <line x1="6" y1="6" x2="18" y2="18"></line>
                </svg>
              </button>
            </div>
            <div className="settings-content" style={{ padding: '24px' }}>
              <div style={{ marginBottom: '24px' }}>
                <h3 style={{ fontSize: '14px', fontWeight: '700', color: 'var(--text-tertiary)', textTransform: 'uppercase', letterSpacing: '0.5px', marginBottom: '12px' }}>键盘快捷键</h3>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                    <kbd style={{ background: 'var(--bg-tertiary)', border: '1px solid var(--border)', borderRadius: '6px', padding: '4px 10px', fontSize: '13px', fontWeight: '600', color: 'var(--text-primary)' }}>1 - 4</kbd>
                    <span style={{ fontSize: '14px', color: 'var(--text-secondary)' }}>选择答案选项</span>
                  </div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                    <kbd style={{ background: 'var(--bg-tertiary)', border: '1px solid var(--border)', borderRadius: '6px', padding: '4px 10px', fontSize: '13px', fontWeight: '600', color: 'var(--text-primary)' }}>5</kbd>
                    <span style={{ fontSize: '14px', color: 'var(--text-secondary)' }}>不知道（跳过）</span>
                  </div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                    <kbd style={{ background: 'var(--bg-tertiary)', border: '1px solid var(--border)', borderRadius: '6px', padding: '4px 10px', fontSize: '13px', fontWeight: '600', color: 'var(--text-primary)' }}>空格</kbd>
                    <span style={{ fontSize: '14px', color: 'var(--text-secondary)' }}>重新播放发音</span>
                  </div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                    <kbd style={{ background: 'var(--bg-tertiary)', border: '1px solid var(--border)', borderRadius: '6px', padding: '4px 10px', fontSize: '13px', fontWeight: '600', color: 'var(--text-primary)' }}>Esc</kbd>
                    <span style={{ fontSize: '14px', color: 'var(--text-secondary)' }}>退出练习</span>
                  </div>
                </div>
              </div>
              <div>
                <h3 style={{ fontSize: '14px', fontWeight: '700', color: 'var(--text-tertiary)', textTransform: 'uppercase', letterSpacing: '0.5px', marginBottom: '12px' }}>学习模式</h3>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
                  <div style={{ fontSize: '14px', color: 'var(--text-secondary)' }}><strong style={{ color: 'var(--text-primary)' }}>智能模式</strong> — 根据水平自动调整练习方式</div>
                  <div style={{ fontSize: '14px', color: 'var(--text-secondary)' }}><strong style={{ color: 'var(--text-primary)' }}>听写模式</strong> — 听发音后拼写单词</div>
                  <div style={{ fontSize: '14px', color: 'var(--text-secondary)' }}><strong style={{ color: 'var(--text-primary)' }}>听音选义</strong> — 听发音选择中文释义</div>
                  <div style={{ fontSize: '14px', color: 'var(--text-secondary)' }}><strong style={{ color: 'var(--text-primary)' }}>随身听</strong> — 连续播放单词音频</div>
                  <div style={{ fontSize: '14px', color: 'var(--text-secondary)' }}><strong style={{ color: 'var(--text-primary)' }}>默写模式</strong> — 看中文释义写出英文</div>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}

      <SettingsPanel showSettings={showSettings} onClose={() => setShowSettings(false)} />
    </header>
  )
}

export default Header