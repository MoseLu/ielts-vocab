import AvatarUpload from '../../profile/avatar/AvatarUpload'
import SettingsPanel from '../../settings/SettingsPanel'
import Popover from '../../ui/Popover'
import { Scrollbar } from '../../ui/Scrollbar'
import { useHeader } from '../../../composables/layout/navigation/useHeader'
import HeaderHelpModal from './HeaderHelpModal'
import type { HeaderProps, PracticeMode } from './Header.types'

export type { HeaderProps, PracticeMode, User } from './Header.types'

function Header({
  user,
  currentDay,
  onLogout,
  onDayChange,
  onUserUpdate,
}: HeaderProps) {
  const {
    location,
    dayDropdownRef,
    mainNavItems,
    modeNames,
    modeDescriptions,
    showDayDropdown,
    showHelp,
    showSettings,
    showAvatarUpload,
    showMobileMenu,
    setShowDayDropdown,
    setShowHelp,
    setShowSettings,
    setShowAvatarUpload,
    toggleMobileMenu,
    closeMobileMenu,
    handleLogout,
    handleDayChange,
    handleAvatarSave,
    handleSearchOpen,
    navigateTo,
    navigateMobile,
  } = useHeader({ onLogout, onDayChange, onUserUpdate })

  const isNavItemActive = (path: string) => (
    location.pathname === path || location.pathname.startsWith(`${path}/`)
  )

  return (
    <header className="header">
      {/* Logo - left, aligned with sidebar width */}
      <div className="header-logo-area" onClick={() => navigateTo('/plan')}>
        <img src="/images/logo.png" alt="Logo" className="header-logo-img" onError={(e) => { e.currentTarget.style.display = 'none' }} />
        <span className="header-logo-text">雅思冲刺</span>
      </div>

      {/* Nav - inline after logo */}
      <nav className="header-nav">
        {mainNavItems.map(item => (
          <button
            key={item.key}
            className={`header-nav-item ${isNavItemActive(item.path) ? 'active' : ''}`}
            onClick={() => navigateTo(item.path)}
          >
            {item.label}
          </button>
        ))}
      </nav>

      {/* Right area: search + toolbar */}
      <div className="header-right">
        {/* Mobile hamburger menu button */}
        {user && (
          <button className="header-btn header-hamburger" onClick={toggleMobileMenu} title="菜单">
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
        <button
          type="button"
          className="header-btn header-search-shortcut"
          title="单词搜索（Shift + Q）"
          aria-label="打开全局单词搜索"
          onClick={handleSearchOpen}
        >
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden="true">
            <circle cx="11" cy="11" r="8" />
            <path d="M21 21l-4.35-4.35" />
          </svg>
        </button>

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
                          onClick={() => handleDayChange(i + 1)}
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
                    <img src="/default-avatar.jpg" alt="avatar" className="user-avatar-img" />
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
                    <img src="/default-avatar.jpg" alt="avatar" className="user-avatar-img" />
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
        <div className="header-mobile-menu" onClick={closeMobileMenu}>
          <div className="mobile-menu-items">
            {mainNavItems.map(item => (
              <button
                key={item.key}
                className={`mobile-menu-item ${isNavItemActive(item.path) ? 'active' : ''}`}
                onClick={() => navigateMobile(item.path)}
              >
                {item.label}
              </button>
            ))}
          </div>
        </div>
      )}

      {showHelp && (
        <HeaderHelpModal
          modeNames={modeNames}
          modeDescriptions={modeDescriptions}
          onClose={() => setShowHelp(false)}
          pathname={location.pathname}
        />
      )}

      <SettingsPanel showSettings={showSettings} onClose={() => setShowSettings(false)} />

      {showAvatarUpload && user && (
        <AvatarUpload
          user={user}
          onClose={() => setShowAvatarUpload(false)}
          onSave={handleAvatarSave}
        />
      )}
    </header>
  )
}

export default Header
