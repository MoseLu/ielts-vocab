import React from 'react'
import { fireEvent, render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { vi } from 'vitest'
import { AppRoutes } from './AppRoutes'

const showToastMock = vi.fn()
const practicePageMock = vi.fn((props: {
  user?: { id: number; username: string }
  showToast?: (message: string, type?: 'info' | 'success' | 'error') => void
}) => (
  <button
    type="button"
    onClick={() => props.showToast?.('favorite-clicked', 'success')}
  >
    practice-page
  </button>
))

vi.mock('../contexts', () => ({
  useAuth: () => ({
    user: { id: 7, username: 'tester', is_admin: false },
    logout: vi.fn(),
    isAdmin: false,
    isLoading: false,
  }),
  useToast: () => ({
    toast: null,
    showToast: showToastMock,
  }),
}))

vi.mock('../components/practice/PracticePage', () => ({
  default: (props: unknown) => practicePageMock(props),
}))

vi.mock('../components/ai-chat/page/AIChatPanel', () => ({ default: () => null }))
vi.mock('../components/layout/navigation/GlobalWordSearch', () => ({ default: () => null }))
vi.mock('../components/layout/navigation/BottomNav', () => ({ default: () => null }))
vi.mock('../components/layout/navigation/Header', () => ({ default: () => null }))
vi.mock('../components/layout/navigation/LeftSidebar', () => ({ default: () => null }))
vi.mock('../components/ui/Toast', () => ({ default: () => null }))
vi.mock('./ScrollToTop', () => ({ ScrollToTop: () => null }))
vi.mock('../components/admin/page/AdminDashboard', () => ({ default: () => null }))
vi.mock('../components/auth/page/AuthPage', () => ({ default: () => null }))
vi.mock('../components/books/page/VocabBookPage', () => ({ default: () => null }))
vi.mock('../components/errors/page/ErrorsPage', () => ({ default: () => null }))
vi.mock('../components/home/page/HomePage', () => ({ default: () => null }))
vi.mock('../components/journal/page/LearningJournalPage', () => ({ default: () => null }))
vi.mock('../components/not-found/page/NotFoundPage', () => ({ default: () => null }))
vi.mock('../components/practice/ConfusableMatchPage', () => ({ default: () => null }))
vi.mock('../components/profile/page/ProfilePage', () => ({ default: () => null }))
vi.mock('../components/stats/page/StatsPage', () => ({ default: () => null }))
vi.mock('../components/terms/page/TermsPage', () => ({ default: () => null }))
vi.mock('../components/ui/Loading', () => ({ Loading: () => null }))
vi.mock('../components/vocab-test/page/VocabTestPage', () => ({ default: () => null }))

describe('AppRoutes practice route', () => {
  beforeEach(() => {
    showToastMock.mockReset()
    practicePageMock.mockClear()
  })

  it('passes the authenticated user and shared showToast into PracticePage', () => {
    render(
      <MemoryRouter initialEntries={['/practice']}>
        <AppRoutes
          mode="meaning"
          currentDay={1}
          onModeChange={vi.fn()}
          onDayChange={vi.fn()}
        />
      </MemoryRouter>,
    )

    expect(practicePageMock).toHaveBeenCalled()
    expect(practicePageMock.mock.calls[0]?.[0]).toMatchObject({
      user: { id: 7, username: 'tester', is_admin: false },
    })

    fireEvent.click(screen.getByRole('button', { name: 'practice-page' }))
    expect(showToastMock).toHaveBeenCalledWith('favorite-clicked', 'success')
  })

  it('mounts PracticePage on the independent /game route with fixed game mode', () => {
    render(
      <MemoryRouter initialEntries={['/game?book=book-1&chapter=2']}>
        <AppRoutes
          mode="meaning"
          currentDay={1}
          onModeChange={vi.fn()}
          onDayChange={vi.fn()}
        />
      </MemoryRouter>,
    )

    expect(practicePageMock).toHaveBeenCalled()
    expect(practicePageMock.mock.calls[0]?.[0]).toMatchObject({
      mode: 'game',
    })
  })
})
