import React from 'react'
import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { vi } from 'vitest'

import { AppRoutes } from './AppRoutes'

const gameCampaignPageMock = vi.fn(() => <div>game-campaign-page</div>)

vi.mock('../contexts', () => ({
  useAuth: () => ({
    user: { id: 7, username: 'tester', is_admin: false },
    logout: vi.fn(),
    isAdmin: false,
    isLoading: false,
  }),
  useToast: () => ({
    toast: null,
    showToast: vi.fn(),
  }),
}))

vi.mock('../components/game/page/GameCampaignPage', () => ({
  default: () => gameCampaignPageMock(),
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
vi.mock('../components/books/page/CreateCustomBookPage', () => ({ default: () => null }))
vi.mock('../components/books/page/VocabBookPage', () => ({ default: () => null }))
vi.mock('../components/errors/page/ErrorsPage', () => ({ default: () => null }))
vi.mock('../components/home/page/HomePage', () => ({ default: () => null }))
vi.mock('../components/journal/page/LearningJournalPage', () => ({ default: () => null }))
vi.mock('../components/not-found/page/NotFoundPage', () => ({ default: () => null }))
vi.mock('../components/practice/ConfusableMatchPage', () => ({ default: () => null }))
vi.mock('../components/practice/PracticePage', () => ({ default: () => null }))
vi.mock('../components/profile/page/ProfilePage', () => ({ default: () => null }))
vi.mock('../components/stats/page/StatsPage', () => ({ default: () => null }))
vi.mock('../components/terms/page/TermsPage', () => ({ default: () => null }))
vi.mock('../components/ui/Loading', () => ({ Loading: () => null }))
vi.mock('../components/vocab-test/page/VocabTestPage', () => ({ default: () => null }))

describe('AppRoutes speaking route', () => {
  beforeEach(() => {
    gameCampaignPageMock.mockClear()
  })

  it('redirects the legacy /speaking route into the game campaign page', async () => {
    render(
      <MemoryRouter initialEntries={['/speaking']}>
        <AppRoutes
          mode="meaning"
          currentDay={1}
          onModeChange={vi.fn()}
          onDayChange={vi.fn()}
        />
      </MemoryRouter>,
    )

    expect(await screen.findByText('game-campaign-page')).toBeInTheDocument()
  })
})
