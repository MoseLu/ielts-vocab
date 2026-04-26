import { render, screen } from '@testing-library/react'
import { vi } from 'vitest'
import GameThemeSelectPage from './GameThemeSelectPage'
import { fetchGameThemeCatalog } from '../../../lib/gamePractice'

vi.mock('../../../lib/gamePractice', () => ({
  fetchGameThemeCatalog: vi.fn(),
}))

const mockedFetchGameThemeCatalog = vi.mocked(fetchGameThemeCatalog)

describe('GameThemeSelectPage', () => {
  beforeEach(() => {
    mockedFetchGameThemeCatalog.mockReset()
  })

  it('uses PRD map artwork instead of old campaign card placeholders', async () => {
    mockedFetchGameThemeCatalog.mockResolvedValue({
      sourceBooks: ['ielts_reading_premium', 'ielts_listening_premium'],
      pageSize: 8,
      totalWords: 1854,
      themes: [
        {
          id: 'study-campus',
          title: '教育校园',
          subtitle: 'Campus study routes',
          description: '',
          wordCount: 906,
          totalChapters: 15,
          currentPage: 1,
          totalPages: 2,
          chapters: [],
          assets: {
            desktopMap: '/game/campaign-v2/themes/study-campus/desktop/map.png',
            mobileMap: '/game/campaign-v2/themes/study-campus/mobile/map.png',
            selectCard: '/game/campaign-v2/themes/study-campus/desktop/select-card.png',
            emptyState: '/game/campaign-v2/themes/study-campus/desktop/empty-state.png',
          },
        },
        {
          id: 'environment-nature',
          title: '环境自然',
          subtitle: 'Environment and nature',
          description: '',
          wordCount: 948,
          totalChapters: 15,
          currentPage: 1,
          totalPages: 2,
          chapters: [],
          assets: {
            desktopMap: '/game/campaign-v2/themes/environment-nature/desktop/map.png',
            mobileMap: '/game/campaign-v2/themes/environment-nature/mobile/map.png',
            selectCard: '/game/campaign-v2/themes/environment-nature/desktop/select-card.png',
            emptyState: '/game/campaign-v2/themes/environment-nature/desktop/empty-state.png',
          },
        },
      ],
    })

    render(<GameThemeSelectPage onSelectTheme={vi.fn()} />)

    const campaign = await screen.findByLabelText('IELTS 主题战役')
    const images = Array.from(campaign.querySelectorAll('img'))
    const imageSources = images.map(image => image.getAttribute('src'))

    expect(imageSources).toContain('/ui/background/map_education.png')
    expect(imageSources).toContain('/ui/background/map_environment.png')
    expect(imageSources.join(' ')).not.toContain('/game/campaign-v2/')
  })
})
