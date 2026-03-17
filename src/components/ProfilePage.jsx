import React, { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import SettingsPanel from './SettingsPanel'

function ProfilePage({ user, onLogout, showToast }) {
  const navigate = useNavigate()
  const [showSettings, setShowSettings] = useState(false)

  const handleLogout = () => {
    onLogout()
    navigate('/login')
  }

  const handlePlaceholder = (label) => {
    showToast?.(`${label} — 敬请期待`, 'info')
  }

  const menuItems = [
    {
      icon: (
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
          <circle cx="12" cy="12" r="10" />
          <path d="M12 8v4l3 3" />
        </svg>
      ),
      label: '词汇量测试',
      action: () => navigate('/')
    },
    {
      icon: (
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
          <path d="M11.049 2.927c.3-.921 1.603-.921 1.902 0l1.518 4.674a1 1 0 00.95.69h4.908c.969 0 1.371 1.24.588 1.81l-3.972 2.883a1 1 0 00-.364 1.118l1.518 4.674c.3.921-.755 1.688-1.538 1.118l-3.972-2.883a1 1 0 00-1.175 0l-3.972 2.883c-.783.57-1.838-.197-1.538-1.118l1.518-4.674a1 1 0 00-.364-1.118L2.083 10.1c-.783-.57-.38-1.81.588-1.81h4.908a1 1 0 00.95-.69l1.518-4.674z" />
        </svg>
      ),
      label: '功能许愿池',
      action: () => handlePlaceholder('功能许愿池')
    },
    {
      icon: (
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
          <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />
        </svg>
      ),
      label: 'BUG反馈',
      action: () => handlePlaceholder('BUG反馈')
    },
    {
      icon: (
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
          <circle cx="12" cy="12" r="3" />
          <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83-2.83l.06-.06A1.65 1.65 0 0 0 4.68 15a1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 2.83-2.83l.06.06A1.65 1.65 0 0 0 9 4.68a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 2.83l-.06.06A1.65 1.65 0 0 0 19.4 9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z" />
        </svg>
      ),
      label: '设置',
      action: () => setShowSettings(true)
    },
  ]

  const initials = user?.username
    ? user.username.slice(0, 2).toUpperCase()
    : user?.email?.slice(0, 2).toUpperCase() || '?'

  return (
    <div className="profile-page">
      {/* User card */}
      <div className="profile-user-card">
        <div className="profile-avatar">
          {user?.avatar_url ? (
            <img src={user.avatar_url} alt="avatar" className="profile-avatar-img" />
          ) : (
            <div className="profile-avatar-initials">{initials}</div>
          )}
        </div>
        <div className="profile-user-info">
          <div className="profile-username">{user?.username || '用户'}</div>
          <div className="profile-email">{user?.email || ''}</div>
        </div>
        <div className="profile-pro-badge">免费版</div>
      </div>

      {/* Menu list */}
      <div className="profile-menu">
        {menuItems.map((item) => (
          <button key={item.label} className="profile-menu-item" onClick={item.action}>
            <span className="profile-menu-icon">{item.icon}</span>
            <span className="profile-menu-label">{item.label}</span>
            <svg className="profile-menu-arrow" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <polyline points="9 18 15 12 9 6" />
            </svg>
          </button>
        ))}

        {/* Logout — separate, destructive style */}
        <button className="profile-menu-item profile-logout-item" onClick={handleLogout}>
          <span className="profile-menu-icon">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
              <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4" />
              <polyline points="16 17 21 12 16 7" />
              <line x1="21" y1="12" x2="9" y2="12" />
            </svg>
          </span>
          <span className="profile-menu-label">退出登录</span>
          <svg className="profile-menu-arrow" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <polyline points="9 18 15 12 9 6" />
          </svg>
        </button>
      </div>

      {showSettings && (
        <SettingsPanel showSettings={showSettings} onClose={() => setShowSettings(false)} />
      )}
    </div>
  )
}

export default ProfilePage
