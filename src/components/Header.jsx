import React, { useState, useEffect, useRef } from 'react'
import { useNavigate, useLocation } from 'react-router-dom'
import SettingsPanel from './SettingsPanel'
import AvatarUpload from './AvatarUpload'

function Header({ user, currentDay, mode, onLogout, onModeChange, onDayChange, onUserUpdate }) {
  const [showModeDropdown, setShowModeDropdown] = useState(false)
  const [showDayDropdown, setShowDayDropdown] = useState(false)
  const [showUserDropdown, setShowUserDropdown] = useState(false)
  const [showHelp, setShowHelp] = useState(false)
  const [showSettings, setShowSettings] = useState(false)
  const [showAvatarUpload, setShowAvatarUpload] = useState(false)
  const [searchQuery, setSearchQuery] = useState('')
  const navigate = useNavigate()
  const location = useLocation()
  const userMenuRef = useRef(null)
  const dayDropdownRef = useRef(null)
  const modeDropdownRef = useRef(null)

  const isPracticePage = location.pathname === '/practice'
  const isHomePage = location.pathname === '/'
  const isPlanPage = location.pathname === '/plan'

  const modeNames = {
    'smart': '智能模式',
    'listening': '听音选义',
    'meaning': '看词选义',
    'dictation': '听写模式',
    'radio': '随身听'
  }

  const modeDescriptions = {
    'smart': '根据水平自动调整',
    'listening': '听发音选中文释义',
    'meaning': '看英文选中文释义',
    'dictation': '听发音拼写单词',
    'radio': '连续播放音频'
  }

  // Main navigation items
  const mainNavItems = [
    { key: 'plan', label: '学习中心', path: '/plan' },
    { key: 'books', label: '词书', path: '/' },
  ]

  // Close dropdowns on outside click
  useEffect(() => {
    const handleClickOutside = (e) => {
      if (userMenuRef.current && !userMenuRef.current.contains(e.target)) {
        setShowUserDropdown(false)
      }
      if (dayDropdownRef.current && !dayDropdownRef.current.contains(e.target)) {
        setShowDayDropdown(false)
      }
      if (modeDropdownRef.current && !modeDropdownRef.current.contains(e.target)) {
        setShowModeDropdown(false)
      }
    }
    document.addEventListener('pointerdown', handleClickOutside)
    return () => document.removeEventListener('pointerdown', handleClickOutside)
  }, [])

  const handleLogout = () => {
    onLogout()
    navigate('/login')
  }

  const handleSearch = (e) => {
    e.preventDefault()
    if (searchQuery.trim()) {
      // TODO: Implement search
      console.log('Search:', searchQuery)
    }
  }

  return (
    <header className="header">
      <div className="header-left">
        <div className="logo" onClick={() => navigate('/')}>
          <img src="/images/logo.png" alt="Logo" className="logo-img" onError={(e) => { e.target.style.display='none' }} />
          <span className="logo-text">雅思冲刺</span>
        </div>

        {/* Main Navigation */}
        <nav className="main-nav">
          {mainNavItems.map(item => (
            <button
              key={item.key}
              className={`main-nav-item ${location.pathname === item.path ? 'active' : ''}`}
              onClick={() => navigate(item.path)}
            >
              {item.label}
            </button>
          ))}
        </nav>
      </div>

      <div className="header-right">
        {/* Search Box */}
        <div className="header-search-box">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <circle cx="11" cy="11" r="8" />
            <path d="M21 21l-4.35-4.35" />
          </svg>
          <input
            type="text"
            placeholder="单词查询"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && handleSearch(e)}
          />
          <span className="header-search-shortcut">Shift+Q</span>
        </div>

        {user && (
          <>
            {/* Day Selector - hidden, moved to homepage */}
            <div className="day-selector-wrapper" ref={dayDropdownRef} style={{ display: 'none' }}>
              <div
                className="day-selector"
                onClick={() => setShowDayDropdown(!showDayDropdown)}
              >
                <span className="day-selector-current">
                  {currentDay ? `Day ${currentDay}` : '选择单元'}
                </span>
                <svg
                  className="day-selector-arrow"
                  style={{ transform: showDayDropdown ? 'rotate(180deg)' : 'none', transition: 'transform 0.2s' }}
                  viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"
                >
                  <polyline points="6 9 12 15 18 9"></polyline>
                </svg>
              </div>
              {showDayDropdown && (
                <div className="day-dropdown show">
                  <div className="day-dropdown-header">选择学习单元</div>
                  <div className="day-dropdown-scroll">
                    {Array.from({ length: 30 }, (_, i) => (
                      <div
                        key={i + 1}
                        className={`day-dropdown-item ${currentDay === i + 1 ? 'active' : ''}`}
                        onClick={() => {
                          onDayChange(i + 1)
                          setShowDayDropdown(false)
                          if (isPracticePage) {
                            // reload practice
                          }
                        }}
                      >
                        <span>Day {i + 1}</span>
                        {currentDay === i + 1 && (
                          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
                            <polyline points="20 6 9 17 4 12"></polyline>
                          </svg>
                        )}
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>

            {/* Settings Button */}
            <button className="header-btn icon-btn" title="设置" onClick={() => setShowSettings(true)}>
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <circle cx="12" cy="12" r="3"></circle>
                <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06-.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z"></path>
              </svg>
            </button>
          </>
        )}

        {/* Help Button */}
        <button className="header-btn icon-btn" title="帮助" onClick={() => setShowHelp(true)}>
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
            <circle cx="12" cy="12" r="10"></circle>
            <path d="M9.09 9a3 3 0 0 1 5.66 0 2.48 2.48 0 0 1-.6 1.85c-.55.6-1.26 1.08-1.9 1.63-.6.52-.96 1.25-.96 2.07V15"></path>
            <circle cx="12" cy="18.5" r="0.8" fill="currentColor" stroke="none"></circle>
          </svg>
        </button>

        {/* User Menu */}
        {user && (
          <div className="user-menu" ref={userMenuRef}>
            <button
              className="user-btn"
              onClick={() => setShowUserDropdown(!showUserDropdown)}
              title={user.username || user.email}
            >
              {user.avatar_url ? (
                <img src={user.avatar_url} alt="avatar" className="user-avatar-img" />
              ) : (
                <span>{user.username?.[0]?.toUpperCase() || user.email?.[0]?.toUpperCase() || '?'}</span>
              )}
            </button>
            {showUserDropdown && (
              <div className="user-dropdown show">
                <div className="user-dropdown-header">
                  <button
                    className="user-dropdown-avatar-btn"
                    onClick={() => { setShowUserDropdown(false); setShowAvatarUpload(true) }}
                    title="点击更换头像"
                  >
                    {user.avatar_url ? (
                      <img src={user.avatar_url} alt="avatar" className="user-avatar-img" />
                    ) : (
                      <span>{user.username?.[0]?.toUpperCase() || '?'}</span>
                    )}
                    <div className="avatar-edit-hint">换</div>
                  </button>
                  <div>
                    <div className="user-dropdown-name">{user.username || user.email}</div>
                    <div className="user-dropdown-email">{user.email}</div>
                  </div>
                </div>
                <div className="user-dropdown-divider"></div>
                <button className="dropdown-item logout-item" onClick={handleLogout}>
                  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"></path>
                    <polyline points="16 17 21 12 16 7"></polyline>
                    <line x1="21" y1="12" x2="9" y2="12"></line>
                  </svg>
                  退出登录
                </button>
              </div>
            )}
          </div>
        )}
      </div>

      {/* Help Modal */}
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
                  {[['1 - 4', '选择答案选项'], ['5', '不知道（跳过）'], ['空格', '重新播放发音'], ['Esc', '退出练习']].map(([key, desc]) => (
                    <div key={key} style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                      <kbd style={{ background: 'var(--bg-tertiary)', border: '1px solid var(--border)', borderRadius: '6px', padding: '4px 10px', fontSize: '13px', fontWeight: '600', color: 'var(--text-primary)', minWidth: '52px', textAlign: 'center' }}>{key}</kbd>
                      <span style={{ fontSize: '14px', color: 'var(--text-secondary)' }}>{desc}</span>
                    </div>
                  ))}
                </div>
              </div>
              <div>
                <h3 style={{ fontSize: '14px', fontWeight: '700', color: 'var(--text-tertiary)', textTransform: 'uppercase', letterSpacing: '0.5px', marginBottom: '12px' }}>学习模式说明</h3>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
                  {Object.entries(modeNames).map(([key, name]) => (
                    <div key={key} style={{ fontSize: '14px', color: 'var(--text-secondary)' }}>
                      <strong style={{ color: 'var(--text-primary)' }}>{name}</strong> — {modeDescriptions[key]}
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </div>
        </div>
      )}

      <SettingsPanel showSettings={showSettings} onClose={() => setShowSettings(false)} />

      {showAvatarUpload && user && (
        <AvatarUpload
          user={user}
          onClose={() => setShowAvatarUpload(false)}
          onSave={(updatedUser) => {
            onUserUpdate && onUserUpdate(updatedUser)
          }}
        />
      )}
    </header>
  )
}

export default Header