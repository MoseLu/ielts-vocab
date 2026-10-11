import { useNavigate, useLocation } from 'react-router-dom'
import homeActiveIcon from '../../../assets/icons/bottom-nav/home-active.svg?raw'
import homeInactiveIcon from '../../../assets/icons/bottom-nav/home-inactive.svg?raw'
import booksActiveIcon from '../../../assets/icons/bottom-nav/books-active.svg?raw'
import booksInactiveIcon from '../../../assets/icons/bottom-nav/books-inactive.svg?raw'
import practiceActiveIcon from '../../../assets/icons/bottom-nav/practice-active.svg?raw'
import practiceInactiveIcon from '../../../assets/icons/bottom-nav/practice-inactive.svg?raw'
import statsActiveIcon from '../../../assets/icons/bottom-nav/stats-active.svg?raw'
import statsInactiveIcon from '../../../assets/icons/bottom-nav/stats-inactive.svg?raw'
import profileActiveIcon from '../../../assets/icons/bottom-nav/profile-active.svg?raw'
import profileInactiveIcon from '../../../assets/icons/bottom-nav/profile-inactive.svg?raw'

interface NavItem {
  key: string
  label: string
  match?: string[]
  path: string
  activeIcon: string
  inactiveIcon: string
}

const UNSAFE_SVG_PATTERN = /<script\b|on[a-z]+\s*=|<foreignObject\b|(?:href|src)\s*=\s*["'](?:javascript:|data:)/i
const REQUIRED_ACTIVE_ICON_IDS = [
  'home-door',
  'book-left-page',
  'practice-pencil',
  'data-pie-slice',
  'profile-body',
] as const

export function assertSafeBottomNavIcon(svg: string, requiredIds: readonly string[] = []) {
  if (UNSAFE_SVG_PATTERN.test(svg)) {
    throw new Error('Unsafe bottom navigation SVG asset')
  }

  requiredIds.forEach((id) => {
    if (!svg.includes(`id="${id}"`)) {
      throw new Error(`Bottom navigation SVG asset missing #${id}`)
    }
  })

  return svg
}

const navItems: NavItem[] = [
  {
    key: 'home',
    label: '\u9996\u9875',
    path: '/plan',
    match: ['/plan'],
    activeIcon: assertSafeBottomNavIcon(homeActiveIcon, ['home-door']),
    inactiveIcon: assertSafeBottomNavIcon(homeInactiveIcon),
  },
  {
    key: 'books',
    label: '\u8bcd\u4e66',
    path: '/books',
    match: ['/books'],
    activeIcon: assertSafeBottomNavIcon(booksActiveIcon, ['book-left-page']),
    inactiveIcon: assertSafeBottomNavIcon(booksInactiveIcon),
  },
  {
    key: 'practice',
    label: '\u7ec3\u4e60',
    path: '/practice?review=due',
    match: ['/practice'],
    activeIcon: assertSafeBottomNavIcon(practiceActiveIcon, ['practice-pencil']),
    inactiveIcon: assertSafeBottomNavIcon(practiceInactiveIcon),
  },
  {
    key: 'stats',
    label: '\u6570\u636e',
    path: '/stats',
    match: ['/stats'],
    activeIcon: assertSafeBottomNavIcon(statsActiveIcon, ['data-pie-slice']),
    inactiveIcon: assertSafeBottomNavIcon(statsInactiveIcon),
  },
  {
    key: 'profile',
    label: '\u6211\u7684',
    path: '/profile',
    match: ['/profile'],
    activeIcon: assertSafeBottomNavIcon(profileActiveIcon, ['profile-body']),
    inactiveIcon: assertSafeBottomNavIcon(profileInactiveIcon),
  },
]

REQUIRED_ACTIVE_ICON_IDS.forEach((id) => {
  if (!navItems.some(item => item.activeIcon.includes(`id="${id}"`))) {
    throw new Error(`Bottom navigation icon registry missing #${id}`)
  }
})

function isNavItemActive(pathname: string, item: NavItem) {
  const activePaths = item.match ?? [item.path]
  return activePaths.some(path => pathname === path || pathname.startsWith(`${path}/`))
}

function BottomNav() {
  const navigate = useNavigate()
  const location = useLocation()

  return (
    <nav className="bottom-nav">
      {navItems.map(item => {
        const isActive = isNavItemActive(location.pathname, item)
        const className = ['bottom-nav-item', isActive ? 'active' : ''].filter(Boolean).join(' ')
        return (
          <button
            key={item.key}
            className={className}
            onClick={() => navigate(item.path)}
            aria-current={isActive ? 'page' : undefined}
          >
            <span className="bottom-nav-icon">
              <span
                key={`${item.key}-${isActive ? 'active' : 'inactive'}`}
                aria-hidden="true"
                className="bottom-nav-icon-svg"
                dangerouslySetInnerHTML={{ __html: isActive ? item.activeIcon : item.inactiveIcon }}
              />
            </span>
            <span className="bottom-nav-label">{item.label}</span>
          </button>
        )
      })}
    </nav>
  )
}

export default BottomNav
