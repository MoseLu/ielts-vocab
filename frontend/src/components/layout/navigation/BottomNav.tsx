import type { ComponentType } from 'react'
import { useNavigate, useLocation } from 'react-router-dom'

// Icons for bottom navigation
const HomeIcon = ({ active }: { active: boolean }) => (
  <svg viewBox="0 0 24 24" fill="none" stroke={active ? 'var(--accent)' : 'currentColor'} strokeWidth="2">
    <path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/>
    <polyline points="9 22 9 12 15 12 15 22"/>
  </svg>
)

const ErrorsIcon = ({ active }: { active: boolean }) => (
  <svg viewBox="0 0 24 24" fill="none" stroke={active ? 'var(--accent)' : 'currentColor'} strokeWidth="2">
    <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
    <polyline points="14 2 14 8 20 8"/>
    <line x1="9" y1="15" x2="15" y2="15"/>
  </svg>
)

const ExamsIcon = ({ active }: { active: boolean }) => (
  <svg viewBox="0 0 24 24" fill="none" stroke={active ? 'var(--accent)' : 'currentColor'} strokeWidth="2">
    <path d="M6 3h9l5 5v13a1 1 0 0 1-1 1H6a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2z"/>
    <polyline points="14 3 14 8 19 8"/>
    <path d="M8 13h8M8 17h6"/>
  </svg>
)

const GameIcon = ({ active }: { active: boolean }) => (
  <svg viewBox="0 0 24 24" fill="none" stroke={active ? 'var(--accent)' : 'currentColor'} strokeWidth="2">
    <path d="M4 19h16"/>
    <path d="M5 19l2.5-9 4.5 4 4-8 3 13"/>
    <circle cx="7.5" cy="10" r="1.2"/>
    <circle cx="12" cy="14" r="1.2"/>
    <circle cx="16" cy="6" r="1.2"/>
  </svg>
)

const StatsIcon = ({ active }: { active: boolean }) => (
  <svg viewBox="0 0 24 24" fill="none" stroke={active ? 'var(--accent)' : 'currentColor'} strokeWidth="2">
    <path d="M21.21 15.89A10 10 0 1 1 8 2.83"/>
    <path d="M22 12A10 10 0 0 0 12 2v10z"/>
  </svg>
)

const ProfileIcon = ({ active }: { active: boolean }) => (
  <svg viewBox="0 0 24 24" fill="none" stroke={active ? 'var(--accent)' : 'currentColor'} strokeWidth="2">
    <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/>
    <circle cx="12" cy="7" r="4"/>
  </svg>
)

interface NavItem {
  key: string
  label: string
  path: string
  icon: ComponentType<{ active: boolean }>
}

const navItems: NavItem[] = [
  { key: 'home', label: '\u9996\u9875', path: '/plan', icon: HomeIcon },
  { key: 'exams', label: '\u771f\u9898', path: '/exams', icon: ExamsIcon },
  { key: 'game', label: '\u95ef\u5173', path: '/game', icon: GameIcon },
  { key: 'errors', label: '\u9519\u8bcd', path: '/errors', icon: ErrorsIcon },
  { key: 'stats', label: '\u7edf\u8ba1', path: '/stats', icon: StatsIcon },
  { key: 'profile', label: '\u6211\u7684', path: '/profile', icon: ProfileIcon },
]

function BottomNav() {
  const navigate = useNavigate()
  const location = useLocation()

  return (
    <nav className="bottom-nav">
      {navItems.map(item => {
        const isActive = location.pathname === item.path
        return (
          <button
            key={item.key}
            className={`bottom-nav-item ${isActive ? 'active' : ''}`}
            onClick={() => navigate(item.path)}
          >
            <span className="bottom-nav-icon">
              <item.icon active={isActive} />
            </span>
            <span className="bottom-nav-label">{item.label}</span>
          </button>
        )
      })}
    </nav>
  )
}

export default BottomNav
