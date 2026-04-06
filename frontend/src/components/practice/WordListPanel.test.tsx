import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'
import WordListPanel from './WordListPanel'
import type { WordListActionControls } from './types'

vi.mock('./WordListDetailPanel', () => ({
  default: ({ open, selectedWord }: { open: boolean; selectedWord: { word: string } | null }) =>
    open ? <div data-testid="wordlist-detail-panel">{selectedWord?.word}</div> : null,
}))

describe('WordListPanel', () => {
  it('renders familiar and favorite action buttons on the right side of each word', async () => {
    const user = userEvent.setup()
    const onFavoriteToggle = vi.fn()
    const onFamiliarToggle = vi.fn()
    const wordActionControls: WordListActionControls = {
      isFavorite: word => word === 'alpha',
      isFavoritePending: () => false,
      onFavoriteToggle,
      isFamiliar: word => word === 'beta',
      isFamiliarPending: () => false,
      onFamiliarToggle,
    }

    render(
      <WordListPanel
        show
        vocabulary={[
          { word: 'alpha', phonetic: '/a/', pos: 'n.', definition: 'alpha def' },
          { word: 'beta', phonetic: '/b/', pos: 'n.', definition: 'beta def' },
        ]}
        queue={[0, 1]}
        queueIndex={0}
        wordStatuses={{}}
        wordActionControls={wordActionControls}
        onClose={() => {}}
      />,
    )

    const familiarButtons = screen.getAllByRole('button', { name: /熟字/ })
    const favoriteButtons = screen.getAllByRole('button', { name: /收藏/ })
    const alphaRow = screen.getByRole('button', { name: '查看 alpha 详情' })

    expect(familiarButtons).toHaveLength(2)
    expect(favoriteButtons).toHaveLength(2)
    expect(favoriteButtons[0]).toHaveClass('is-active')
    expect(familiarButtons[1]).toHaveClass('is-active')
    expect(screen.queryByTestId('wordlist-detail-panel')).not.toBeInTheDocument()

    await user.click(familiarButtons[0])
    await user.click(favoriteButtons[1])

    expect(onFamiliarToggle).toHaveBeenCalledWith(expect.objectContaining({ word: 'alpha' }))
    expect(onFavoriteToggle).toHaveBeenCalledWith(expect.objectContaining({ word: 'beta' }))
    expect(screen.queryByTestId('wordlist-detail-panel')).not.toBeInTheDocument()

    await user.click(alphaRow)

    expect(screen.getByTestId('wordlist-detail-panel')).toHaveTextContent('alpha')
  })
})
