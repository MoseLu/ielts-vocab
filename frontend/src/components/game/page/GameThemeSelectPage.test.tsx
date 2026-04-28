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

  it('uses OSS theme artwork from the backend catalog', async () => {
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
            desktopMap: 'https://oss.example/game-assets/study-campus/desktop/map.png',
            mobileMap: 'https://oss.example/game-assets/study-campus/mobile/map.png',
            selectCard: 'https://oss.example/game-assets/study-campus/desktop/select-card.png',
            emptyState: 'https://oss.example/game-assets/study-campus/desktop/empty-state.png',
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
            desktopMap: 'https://oss.example/game-assets/environment-nature/desktop/map.png',
            mobileMap: 'https://oss.example/game-assets/environment-nature/mobile/map.png',
            selectCard: 'https://oss.example/game-assets/environment-nature/desktop/select-card.png',
            emptyState: 'https://oss.example/game-assets/environment-nature/desktop/empty-state.png',
          },
        },
      ],
    })

    render(<GameThemeSelectPage onSelectTheme={vi.fn()} />)

    const campaign = await screen.findByLabelText('IELTS 主题战役')
    const images = Array.from(campaign.querySelectorAll('img'))
    const imageSources = images.map(image => image.getAttribute('src'))

    expect(imageSources).toContain('https://oss.example/game-assets/study-campus/desktop/map.png')
    expect(imageSources).toContain('https://oss.example/game-assets/study-campus/desktop/select-card.png')
    expect(imageSources).toContain('https://oss.example/game-assets/environment-nature/desktop/select-card.png')
    expect(imageSources.join(' ')).not.toContain('/ui/')
    expect(imageSources.join(' ')).not.toContain('/game/campaign-v2/')
  })
})
