import React from 'react'
import { fireEvent, render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { vi } from 'vitest'
import { AppRoutes } from './AppRoutes'

const showToastMock = vi.fn()
const aiChatPanelMock = vi.fn((props: { avoidBottomNav?: boolean }) => (
  <div data-testid="ai-chat-panel" data-avoid-bottom-nav={String(Boolean(props.avoidBottomNav))} />
))
const practicePageMock = vi.fn((props: {
  user?: { id: number; username: string }
  mode?: string
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
vi.mock('../components/game/page/GameComingSoonPage', () => ({
  default: () => <div>game-coming-soon-page</div>,
}))

vi.mock('../components/ai-chat/page/AIChatPanel', () => ({
  default: (props: { avoidBottomNav?: boolean }) => aiChatPanelMock(props),
}))
vi.mock('../components/layout/navigation/GlobalWordSearch', () => ({ default: () => null }))
vi.mock('../components/layout/navigation/BottomNav', () => ({ default: () => null }))
vi.mock('../components/layout/navigation/Header', () => ({ default: () => null }))
vi.mock('../components/layout/navigation/LeftSidebar', () => ({
  default: () => <aside data-testid="left-sidebar" className="left-sidebar" />,
}))
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
    aiChatPanelMock.mockClear()
    practicePageMock.mockClear()
  })

  it('renders the sidebar shell immediately on authenticated app routes', () => {
    const { container } = render(
      <MemoryRouter initialEntries={['/plan']}>
        <AppRoutes
          mode="meaning"
          currentDay={1}
          onModeChange={vi.fn()}
          onDayChange={vi.fn()}
        />
      </MemoryRouter>,
    )

    expect(screen.getByTestId('left-sidebar')).toBeInTheDocument()
    expect(container.querySelector('.app-body')).toBeTruthy()
    expect(container.querySelector('.practice-fullscreen')).toBeFalsy()
  })

  it('does not render the sidebar shell on fullscreen practice surfaces', async () => {
    const { container } = render(
      <MemoryRouter initialEntries={['/game']}>
        <AppRoutes
          mode="meaning"
          currentDay={1}
          onModeChange={vi.fn()}
          onDayChange={vi.fn()}
        />
      </MemoryRouter>,
    )

    expect(screen.queryByTestId('left-sidebar')).toBeNull()
    expect(await screen.findByText('game-coming-soon-page')).toBeInTheDocument()
    expect(container.querySelector('.practice-fullscreen')).toBeTruthy()
    expect(container.querySelector('.app-body')).toBeFalsy()
  })

  it('keeps the legacy speaking redirect in the fullscreen shell', async () => {
    const { container } = render(
      <MemoryRouter initialEntries={['/speaking']}>
        <AppRoutes
          mode="meaning"
          currentDay={1}
          onModeChange={vi.fn()}
          onDayChange={vi.fn()}
        />
      </MemoryRouter>,
    )

    expect(screen.queryByTestId('left-sidebar')).toBeNull()
    expect(await screen.findByText('game-coming-soon-page')).toBeInTheDocument()
    expect(container.querySelector('.practice-fullscreen')).toBeTruthy()
    expect(container.querySelector('.app-body')).toBeFalsy()
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

  it('does not offset AI chat on fullscreen practice surfaces without bottom nav', async () => {
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

    expect(await screen.findByTestId('ai-chat-panel', undefined, { timeout: 2000 }))
      .toHaveAttribute('data-avoid-bottom-nav', 'false')
  })

  it('honors a classic practice mode from the route query', () => {
    const onModeChange = vi.fn()

    render(
      <MemoryRouter initialEntries={['/practice?book=custom_1&chapter=custom_1_2&mode=quickmemory']}>
        <AppRoutes
          mode="listening"
          currentDay={1}
          onModeChange={onModeChange}
          onDayChange={vi.fn()}
        />
      </MemoryRouter>,
    )

    expect(practicePageMock.mock.calls[0]?.[0]).toMatchObject({
      mode: 'quickmemory',
    })
    expect(onModeChange).toHaveBeenCalledWith('quickmemory')
  })

  it('honors the independent audio-first test mode from the route query', () => {
    const onModeChange = vi.fn()

    render(
      <MemoryRouter initialEntries={['/practice?book=custom_1&chapter=custom_1_2&mode=test']}>
        <AppRoutes
          mode="listening"
          currentDay={1}
          onModeChange={onModeChange}
          onDayChange={vi.fn()}
        />
      </MemoryRouter>,
    )

    expect(practicePageMock.mock.calls[0]?.[0]).toMatchObject({
      mode: 'test',
    })
    expect(onModeChange).toHaveBeenCalledWith('test')
  })

  it('shows the coming soon placeholder on /game', async () => {
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

    expect(await screen.findByText('game-coming-soon-page')).toBeInTheDocument()
    expect(practicePageMock).not.toHaveBeenCalled()
  })

  it('shows the coming soon placeholder on the game theme catalog route', async () => {
    render(
      <MemoryRouter initialEntries={['/game/themes']}>
        <AppRoutes
          mode="meaning"
          currentDay={1}
          onModeChange={vi.fn()}
          onDayChange={vi.fn()}
        />
      </MemoryRouter>,
    )

    expect(await screen.findByText('game-coming-soon-page')).toBeInTheDocument()
    expect(practicePageMock).not.toHaveBeenCalled()
  })

  it('shows the coming soon placeholder on a themed game map route', async () => {
    render(
      <MemoryRouter initialEntries={['/game/themes/study-campus?page=2']}>
        <AppRoutes
          mode="meaning"
          currentDay={1}
          onModeChange={vi.fn()}
          onDayChange={vi.fn()}
        />
      </MemoryRouter>,
    )

    expect(await screen.findByText('game-coming-soon-page')).toBeInTheDocument()
    expect(practicePageMock).not.toHaveBeenCalled()
  })

  it('shows the coming soon placeholder on a themed game mission route', async () => {
    render(
      <MemoryRouter initialEntries={['/game/themes/science-tech/mission']}>
        <AppRoutes
          mode="meaning"
          currentDay={1}
          onModeChange={vi.fn()}
          onDayChange={vi.fn()}
        />
      </MemoryRouter>,
    )

    expect(await screen.findByText('game-coming-soon-page')).toBeInTheDocument()
    expect(practicePageMock).not.toHaveBeenCalled()
  })

  it('shows the coming soon placeholder on /game/mission', async () => {
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

    expect(await screen.findByText('game-coming-soon-page')).toBeInTheDocument()
    expect(practicePageMock).not.toHaveBeenCalled()
  })

  it('redirects /practice?mode=game into the coming soon placeholder', async () => {
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

    expect(await screen.findByText('game-coming-soon-page')).toBeInTheDocument()
    expect(practicePageMock).not.toHaveBeenCalled()
  })
})
