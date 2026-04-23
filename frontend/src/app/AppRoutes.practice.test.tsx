import React from 'react'
import { fireEvent, render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { vi } from 'vitest'
import { AppRoutes } from './AppRoutes'

const showToastMock = vi.fn()
const gameCampaignPageMock = vi.fn((props: { surface?: 'map' | 'mission' }) => (
  <div>game-campaign-page {props.surface}</div>
))
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
vi.mock('../components/game/page/GameCampaignPage', () => ({
  default: (props: { surface?: 'map' | 'mission' }) => gameCampaignPageMock(props),
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
    gameCampaignPageMock.mockClear()
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

  it('mounts the independent game campaign page on /game', async () => {
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

    expect(await screen.findByText(/game-campaign-page/)).toBeInTheDocument()
    expect(gameCampaignPageMock.mock.calls[0]?.[0]).toMatchObject({ surface: 'map' })
    expect(practicePageMock).not.toHaveBeenCalled()
  })

  it('mounts the independent game mission page on /game/mission', async () => {
    render(
      <MemoryRouter initialEntries={['/game/mission?book=book-1&chapter=2']}>
        <AppRoutes
          mode="meaning"
          currentDay={1}
          onModeChange={vi.fn()}
          onDayChange={vi.fn()}
        />
      </MemoryRouter>,
    )

    expect(await screen.findByText(/game-campaign-page/)).toBeInTheDocument()
    expect(gameCampaignPageMock.mock.calls[0]?.[0]).toMatchObject({ surface: 'mission' })
    expect(practicePageMock).not.toHaveBeenCalled()
  })

  it('redirects /practice?mode=game into /game', async () => {
    render(
      <MemoryRouter initialEntries={['/practice?mode=game&book=book-1']}>
        <AppRoutes
          mode="meaning"
          currentDay={1}
          onModeChange={vi.fn()}
          onDayChange={vi.fn()}
        />
      </MemoryRouter>,
    )

    expect(await screen.findByText(/game-campaign-page/)).toBeInTheDocument()
    expect(gameCampaignPageMock.mock.calls[0]?.[0]).toMatchObject({ surface: 'map' })
    expect(practicePageMock).not.toHaveBeenCalled()
  })
})
