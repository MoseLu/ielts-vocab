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

  it('prefers packaged select-card artwork for known themes', async () => {
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
    const cards = Array.from(campaign.querySelectorAll<HTMLButtonElement>('.game-theme-select__card'))
    const cardArtwork = cards.map(card => card.getAttribute('style') ?? '')

    expect(cardArtwork[0]).toContain('/game/themes/select-card/study-campus.webp')
    expect(cardArtwork[1]).toContain('/game/themes/select-card/environment-nature.webp')
    expect(cardArtwork.join(' ')).not.toContain('https://oss.example')
    expect(cardArtwork.join(' ')).not.toContain('/game/campaign-v2/')
    expect(campaign.querySelector('img')).toBeNull()
  })

  it('falls back to catalog artwork for unknown themes', async () => {
    mockedFetchGameThemeCatalog.mockResolvedValue({
      sourceBooks: ['ielts_reading_premium'],
      pageSize: 8,
      totalWords: 120,
      themes: [
        {
          id: 'custom-theme',
          title: '自定义主题',
          subtitle: 'Custom route',
          description: '',
          wordCount: 120,
          totalChapters: 2,
          currentPage: 1,
          totalPages: 1,
          chapters: [],
          assets: {
            desktopMap: '',
            mobileMap: '',
            selectCard: 'https://oss.example/game-assets/custom-theme/desktop/select-card.png',
            emptyState: '',
          },
        },
      ],
    })

    render(<GameThemeSelectPage onSelectTheme={vi.fn()} />)

    const campaign = await screen.findByLabelText('IELTS 主题战役')
    const card = campaign.querySelector<HTMLButtonElement>('.game-theme-select__card')
    expect(card?.getAttribute('style')).toContain('https://oss.example/game-assets/custom-theme/desktop/select-card.png')
  })
})
