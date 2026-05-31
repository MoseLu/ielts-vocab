import type { ComponentType } from 'react'
import { useNavigate, useLocation } from 'react-router-dom'

// Icons for bottom navigation
const HomeIcon = ({ active }: { active: boolean }) => (
  <svg viewBox="0 0 24 24" fill={active ? 'currentColor' : 'none'} stroke="currentColor" strokeWidth={active ? '2.35' : '2'}>
    <path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/>
    <polyline points="9 22 9 12 15 12 15 22"/>
  </svg>
)

const BooksIcon = ({ active }: { active: boolean }) => (
  <svg viewBox="0 0 24 24" fill={active ? 'currentColor' : 'none'} stroke="currentColor" strokeWidth={active ? '2.35' : '2'}>
    <path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20"/>
    <path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z"/>
    <path d="M8 7h8"/>
  </svg>
)

const PracticeIcon = ({ active }: { active: boolean }) => (
  <svg viewBox="0 0 24 24" fill={active ? 'currentColor' : 'none'} stroke="currentColor" strokeWidth={active ? '2.35' : '2'}>
    <path d="M12 20h9"/>
    <path d="M16.5 3.5a2.1 2.1 0 0 1 3 3L7 19l-4 1 1-4z"/>
    <path d="M14 6l4 4"/>
  </svg>
)

const StatsIcon = ({ active }: { active: boolean }) => (
  <svg viewBox="0 0 24 24" fill={active ? 'currentColor' : 'none'} stroke="currentColor" strokeWidth={active ? '2.35' : '2'}>
    <path d="M21.21 15.89A10 10 0 1 1 8 2.83"/>
    <path d="M22 12A10 10 0 0 0 12 2v10z"/>
  </svg>
)

const ProfileIcon = ({ active }: { active: boolean }) => (
  <svg viewBox="0 0 24 24" fill={active ? 'currentColor' : 'none'} stroke="currentColor" strokeWidth={active ? '2.35' : '2'}>
    <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/>
    <circle cx="12" cy="7" r="4"/>
  </svg>
)

interface NavItem {
  key: string
  label: string
  match?: string[]
  path: string
  icon: ComponentType<{ active: boolean }>
  primary?: boolean
}

const navItems: NavItem[] = [
  { key: 'home', label: '\u9996\u9875', path: '/plan', icon: HomeIcon },
  { key: 'books', label: '\u8bcd\u4e66', path: '/books', match: ['/books'], icon: BooksIcon },
  { key: 'practice', label: '\u7ec3\u4e60', path: '/practice', match: ['/practice'], icon: PracticeIcon, primary: true },
  { key: 'stats', label: '\u6570\u636e', path: '/stats', match: ['/stats'], icon: StatsIcon },
  { key: 'profile', label: '\u6211\u7684', path: '/profile', icon: ProfileIcon },
]

function BottomNav() {
  const navigate = useNavigate()
  const location = useLocation()

  return (
    <nav className="bottom-nav">
      {navItems.map(item => {
        const isActive = item.match
          ? item.match.some(path => location.pathname === path || location.pathname.startsWith(`${path}/`))
          : location.pathname === item.path
        const className = [
          'bottom-nav-item',
          item.primary ? 'bottom-nav-item--primary' : '',
          isActive ? 'active' : '',
        ].filter(Boolean).join(' ')
        return (
          <button
            key={item.key}
            className={className}
            onClick={() => navigate(item.path)}
            aria-current={isActive ? 'page' : undefined}
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
