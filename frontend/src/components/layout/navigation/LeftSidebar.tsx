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
      key: 'speaking',
      label: '\u53e3\u8bed',
      icon: (
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
          <path d="M12 2a3 3 0 0 1 3 3v6a3 3 0 0 1-6 0V5a3 3 0 0 1 3-3z"></path>
          <path d="M19 11a7 7 0 0 1-14 0"></path>
          <line x1="12" y1="18" x2="12" y2="22"></line>
          <line x1="8" y1="22" x2="16" y2="22"></line>
        </svg>
      ),
      path: '/speaking',
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
      label: '\u65e5\u5fd7',
      icon: (
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
          <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path>
          <polyline points="14 2 14 8 20 8"></polyline>
          <line x1="8" y1="13" x2="16" y2="13"></line>
          <line x1="8" y1="17" x2="12" y2="17"></line>
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
