import React from 'react'
import { useNavigate, useLocation } from 'react-router-dom'

interface MenuItem {
  key: string
  label: string
  icon: React.ReactNode
  path: string
}

function LeftSidebar() {
  const navigate = useNavigate()
  const location = useLocation()

  const menuItems: MenuItem[] = [
    {
      key: 'home',
      label: '\u9996\u9875',
      icon: (
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
          <path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"></path>
          <polyline points="9 22 9 12 15 12 15 22"></polyline>
        </svg>
      ),
      path: '/plan',
    },
    {
      key: 'errors',
      label: '\u9519\u8bcd\u672c',
      icon: (
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
          <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path>
          <polyline points="14 2 14 8 20 8"></polyline>
          <line x1="9" y1="15" x2="15" y2="15"></line>
        </svg>
      ),
      path: '/errors',
    },
    {
      key: 'stats',
      label: '\u7edf\u8ba1',
      icon: (
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
          <path d="M21.21 15.89A10 10 0 1 1 8 2.83"></path>
          <path d="M22 12A10 10 0 0 0 12 2v10z"></path>
        </svg>
      ),
      path: '/stats',
    },
    {
      key: 'journal',
      label: '\u65e5\u8bb0',
      icon: (
        <svg viewBox="0 0 1024 1024" fill="currentColor" width="20" height="20">
          <path d="M853.36 85.32H256.11c-23.47 0-42.66 19.2-42.66 42.66h-42.66c-23.47 0-42.66 19.2-42.66 42.66s19.2 42.66 42.66 42.66h42.66v85.32h-42.66c-23.47 0-42.66 19.2-42.66 42.66s19.2 42.66 42.66 42.66h42.66v85.32h-42.66c-23.47 0-42.66 19.2-42.66 42.66s19.2 42.66 42.66 42.66h42.66v85.32h-42.66c-23.47 0-42.66 19.2-42.66 42.66s19.2 42.66 42.66 42.66h42.66v85.32h-42.66c-23.47 0-42.66 19.2-42.66 42.66s19.2 42.66 42.66 42.66h42.66c0 23.46 19.2 42.66 42.66 42.66h597.25c23.47 0 42.66-19.2 42.66-42.66V127.98c0-23.46-19.2-42.66-42.66-42.66zM810.7 853.21H298.77V170.64H810.7v682.57z"/>
          <path d="M426.75 725.23m-42.66 0a42.66 42.66 0 1 0 85.32 0 42.66 42.66 0 1 0-85.32 0Z"/>
          <path d="M554.73 725.23m-42.66 0a42.66 42.66 0 1 0 85.32 0 42.66 42.66 0 1 0-85.32 0Z"/>
          <path d="M682.72 725.23m-42.66 0a42.66 42.66 0 1 0 85.32 0 42.66 42.66 0 1 0-85.32 0Z"/>
          <path d="M426.75 597.25c23.56 0 42.66-19.1 42.66-42.66V401.61l183.14 183.14a42.605 42.605 0 0 0 30.16 12.5c5.5 0 11.04-1.06 16.33-3.25 15.94-6.6 26.33-22.16 26.33-39.41V298.62c0-23.56-19.1-42.66-42.66-42.66-23.56 0-42.66 19.1-42.66 42.66V451.6L456.91 268.46a42.62 42.62 0 0 0-46.49-9.25c-15.94 6.6-26.33 22.16-26.33 39.41v255.96c0 23.57 19.1 42.67 42.66 42.67z"/>
        </svg>
      ),
      path: '/journal',
    },
    {
      key: 'profile',
      label: '\u6211\u7684',
      icon: (
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
          <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"></path>
          <circle cx="12" cy="7" r="4"></circle>
        </svg>
      ),
      path: '/profile',
    },
  ]

  return (
    <aside className="left-sidebar">
      <nav className="left-sidebar-nav">
        {menuItems.map((item: MenuItem) => (
          <button
            key={item.key}
            className={`left-sidebar-item ${location.pathname === item.path ? 'active' : ''}`}
            onClick={() => navigate(item.path)}
          >
            <span className="left-sidebar-item-inner">
              <span className="left-sidebar-icon">{item.icon}</span>
              <span className="left-sidebar-label">{item.label}</span>
            </span>
          </button>
        ))}
      </nav>
    </aside>
  )
}

export default LeftSidebar
