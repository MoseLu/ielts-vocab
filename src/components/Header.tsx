import React, { useState, useEffect, useRef } from 'react'
import { useNavigate, useLocation } from 'react-router-dom'
import { useAuth } from '../contexts'
import SettingsPanel from './SettingsPanel'
import AvatarUpload from './AvatarUpload'
import Popover from './ui/Popover'
import { Scrollbar } from './ui/Scrollbar'

export interface User {
  username?: string
  email?: string
  avatar_url?: string | null
}

export type PracticeMode = 'smart' | 'listening' | 'meaning' | 'dictation' | 'radio'

export interface HeaderProps {
  user: User | null
  currentDay?: number | null
  mode?: PracticeMode
  onLogout: () => void
  onModeChange?: (mode: PracticeMode) => void
  onDayChange?: (day: number) => void
  onUserUpdate?: (user: User) => void
}

function Header({
  user,
  currentDay,
  mode,
  onLogout,
  onModeChange,
  onDayChange,
  onUserUpdate,
  onMenuToggle,
}: HeaderProps) {
  const { updateUser, isAdmin } = useAuth()
  const [showModeDropdown, setShowModeDropdown] = useState(false)
  const [showDayDropdown, setShowDayDropdown] = useState(false)
  const [showHelp, setShowHelp] = useState(false)
  const [showSettings, setShowSettings] = useState(false)
  const [showAvatarUpload, setShowAvatarUpload] = useState(false)
  const [showMobileMenu, setShowMobileMenu] = useState(false)
  const [searchQuery, setSearchQuery] = useState('')
  const navigate = useNavigate()
  const location = useLocation()
  const dayDropdownRef = useRef<HTMLDivElement>(null)
  const modeDropdownRef = useRef<HTMLDivElement>(null)

  const isPracticePage = location.pathname === '/practice'
  const isHomePage = location.pathname === '/'
  const isPlanPage = location.pathname === '/plan'

  const modeNames: Record<PracticeMode, string> = {
    'smart': '智能模式',
    'listening': '听音选义',
    'meaning': '看词选义',
    'dictation': '听写模式',
    'radio': '随身听',
  }

  const modeDescriptions: Record<PracticeMode, string> = {
    'smart': '根据水平自动调整',
    'listening': '听发音选中文释义',
    'meaning': '看英文选中文释义',
    'dictation': '听发音拼写单词',
    'radio': '连续播放音频',
  }

  // Main navigation items
  const mainNavItems: Array<{ key: string; label: string; path: string }> = [
    { key: 'plan', label: '学习中心', path: '/plan' },
    { key: 'books', label: '词书', path: '/' },
    ...(isAdmin ? [{ key: 'admin', label: '管理控制台', path: '/admin' }] : []),
  ]

  // Close dropdowns on outside click
  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (dayDropdownRef.current && !dayDropdownRef.current.contains(e.target as Node)) {
        setShowDayDropdown(false)
      }
      if (modeDropdownRef.current && !modeDropdownRef.current.contains(e.target as Node)) {
        setShowModeDropdown(false)
      }
      // Close mobile menu on outside click
      const mobileMenu = document.querySelector('.header-mobile-menu')
      const hamburgerBtn = document.querySelector('.header-hamburger')
      if (mobileMenu && hamburgerBtn && !mobileMenu.contains(e.target as Node) && !hamburgerBtn.contains(e.target as Node)) {
        setShowMobileMenu(false)
      }
    }
    document.addEventListener('pointerdown', handleClickOutside)
    return () => document.removeEventListener('pointerdown', handleClickOutside)
  }, [])

  const handleLogout = () => {
    onLogout()
    navigate('/login')
  }

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault()
    if (searchQuery.trim()) {
      // TODO: Implement search
      console.log('Search:', searchQuery)
    }
  }

  return (
    <header className="header">
      {/* Logo - left, aligned with sidebar width */}
      <div className="header-logo-area" onClick={() => navigate('/')}>
        <img src="/images/logo.png" alt="Logo" className="header-logo-img" onError={(e) => { e.currentTarget.style.display = 'none' }} />
        <span className="header-logo-text">雅思冲刺</span>
      </div>

      {/* Nav - inline after logo */}
      <nav className="header-nav">
        {mainNavItems.map(item => (
          <button
            key={item.key}
            className={`header-nav-item ${location.pathname === item.path ? 'active' : ''}`}
            onClick={() => navigate(item.path)}
          >
            {item.label}
          </button>
        ))}
      </nav>

      {/* Right area: search + toolbar */}
      <div className="header-right">
        {/* Mobile hamburger menu button */}
        {user && (
          <button className="header-btn header-hamburger" onClick={() => setShowMobileMenu(!showMobileMenu)} title="菜单">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              {showMobileMenu ? (
                <>
                  <line x1="18" y1="6" x2="6" y2="18"/>
                  <line x1="6" y1="6" x2="18" y2="18"/>
                </>
              ) : (
                <>
                  <line x1="3" y1="6" x2="21" y2="6"/>
                  <line x1="3" y1="12" x2="21" y2="12"/>
                  <line x1="3" y1="18" x2="21" y2="18"/>
                </>
              )}
            </svg>
          </button>
        )}

        {/* Global Search */}
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
          </div>

        {/* Toolbar: settings, help, user */}
        <div className="header-toolbar">
          {user && (
            <>
              {/* Day Selector - hidden, moved to homepage */}
              <div className="day-selector-wrapper day-selector-wrapper--hidden" ref={dayDropdownRef}>
                <div
                  className="day-selector"
                  onClick={() => setShowDayDropdown(!showDayDropdown)}
                >
                  <span className="day-selector-current">
                    {currentDay ? `Day ${currentDay}` : '选择单元'}
                  </span>
                  <svg
                    className={`day-selector-arrow${showDayDropdown ? ' is-open' : ''}`}
                    viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"
                  >
                    <polyline points="6 9 12 15 18 9"></polyline>
                  </svg>
                </div>
                {showDayDropdown && (
                  <div className="day-dropdown show">
                    <div className="day-dropdown-header">选择学习单元</div>
                    <Scrollbar className="day-dropdown-scroll" maxHeight={300}>
                      {Array.from({ length: 30 }, (_, i) => (
                        <div
                          key={i + 1}
                          className={`day-dropdown-item ${currentDay === i + 1 ? 'active' : ''}`}
                          onClick={() => {
                            onDayChange?.(i + 1)
                            setShowDayDropdown(false)
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
                    </Scrollbar>
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

          {/* User Menu — Popover */}
          {user && (
            <Popover
              placement="bottom-end"
              offset={10}
              panelClassName="popover-user-panel"
              trigger={
                <button className="user-btn" title={user.username || user.email}>
                  {user.avatar_url ? (
                    <img src={user.avatar_url} alt="avatar" className="user-avatar-img" />
                  ) : (
                    <img src="/assets/default-avatar.jpg" alt="avatar" className="user-avatar-img" />
                  )}
                </button>
              }
            >
              <div className="popover-user-header">
                <button
                  className="popover-avatar-btn"
                  onClick={() => setShowAvatarUpload(true)}
                  title="点击更换头像"
                >
                  {user.avatar_url ? (
                    <img src={user.avatar_url} alt="avatar" className="user-avatar-img" />
                  ) : (
                    <img src="/assets/default-avatar.jpg" alt="avatar" className="user-avatar-img" />
                  )}
                  <div className="avatar-edit-hint">
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                      <path d="M23 19a2 2 0 0 1-2 2H3a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h4l2-3h6l2 3h4a2 2 0 0 1 2 2z"/>
                      <circle cx="12" cy="13" r="4"/>
                    </svg>
                  </div>
                </button>
                <div>
                  <div className="popover-user-name">{user.username || user.email}</div>
                  <div className="popover-user-email">{user.email}</div>
                </div>
              </div>
              <div className="popover-divider" />
              <button className="popover-item popover-item-danger" onClick={handleLogout}>
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"/>
                  <polyline points="16 17 21 12 16 7"/>
                  <line x1="21" y1="12" x2="9" y2="12"/>
                </svg>
                退出登录
              </button>
            </Popover>
          )}
        </div>
      </div>

      {/* Mobile Menu Dropdown */}
      {showMobileMenu && (
        <div className="header-mobile-menu" onClick={() => setShowMobileMenu(false)}>
          <div className="mobile-menu-items">
            {mainNavItems.map(item => (
              <button
                key={item.key}
                className={`mobile-menu-item ${location.pathname === item.path ? 'active' : ''}`}
                onClick={() => { navigate(item.path); setShowMobileMenu(false) }}
              >
                {item.label}
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Help Modal */}
      {showHelp && (
        <div className="settings-overlay show" onClick={(e) => e.target === e.currentTarget && setShowHelp(false)}>
          <div className="settings-modal settings-modal--help">
            <div className="settings-header">
              <h2 className="settings-title">帮助</h2>
              <button className="settings-close" onClick={() => setShowHelp(false)}>
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <line x1="18" y1="6" x2="6" y2="18"></line>
                  <line x1="6" y1="6" x2="18" y2="18"></line>
                </svg>
              </button>
            </div>
            <div className="settings-content settings-content--help">
              <div className="help-modal-section">
                <h3 className="help-modal-title">键盘快捷键</h3>
                <div className="help-modal-list">
                  {([['1 - 4', '选择答案选项'], ['5', '不知道（跳过）'], ['空格', '重新播放发音'], ['Esc', '退出练习']] as [string, string][]).map(([key, desc]) => (
                    <div key={key} className="help-modal-row">
                      <kbd className="help-modal-kbd">{key}</kbd>
                      <span className="help-modal-text">{desc}</span>
                    </div>
                  ))}
                </div>
              </div>
              <div>
                <h3 className="help-modal-title">学习模式说明</h3>
                <div className="help-modal-list">
                  {(Object.entries(modeNames) as [PracticeMode, string][]).map(([key, name]) => (
                    <div key={key} className="help-modal-mode">
                      <strong className="help-modal-mode-name">{name}</strong> — {modeDescriptions[key]}
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
            updateUser(updatedUser as any)
          }}
        />
      )}
    </header>
  )
}

export default Header
