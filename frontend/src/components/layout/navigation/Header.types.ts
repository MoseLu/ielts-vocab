export interface User {
  username?: string
  email?: string
  avatar_url?: string | null
}

export type PracticeMode = 'smart' | 'listening' | 'meaning' | 'dictation' | 'radio' | 'game'

export interface HeaderProps {
  user: User | null
  currentDay?: number | null
  mode?: PracticeMode
  onLogout: () => void
  onModeChange?: (mode: PracticeMode) => void
  onDayChange?: (day: number) => void
  onUserUpdate?: (user: User) => void
}
