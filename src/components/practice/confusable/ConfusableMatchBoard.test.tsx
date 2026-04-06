import React from 'react'
import { render, screen } from '@testing-library/react'
import { vi } from 'vitest'
import { ConfusableMatchBoard, type ConfusableBoardGroup } from './ConfusableMatchBoard'
import type { MatchCard, MatchWord } from '../confusableMatch'

function createWord(overrides: Partial<MatchWord> = {}): MatchWord {
  return {
    key: 'group-1-word-1',
    groupKey: 'group-1',
    word: 'site',
    phonetic: '/saɪt/',
    pos: 'n.',
    definition: '位置；场所',
    ...overrides,
  }
}

function createCard(overrides: Partial<MatchCard> = {}): MatchCard {
  return {
    id: 'word-group-1-word-1',
    side: 'word',
    wordKey: 'group-1-word-1',
    groupKey: 'group-1',
    label: 'site',
    word: 'site',
    phonetic: '/saɪt/',
    ...overrides,
  }
}

function createBoardGroup(overrides: Partial<ConfusableBoardGroup> = {}): ConfusableBoardGroup {
  const word = createWord()
  return {
    key: 'group-1',
    groupNumber: 1,
    words: [word, createWord({ key: 'group-1-word-2', word: 'sight', definition: '看见；景象；视力' })],
    cards: [
      createCard(),
      createCard({
        id: 'definition-group-1-word-1',
        side: 'definition',
        label: '位置；场所',
      }),
    ],
    ...overrides,
  }
}

describe('ConfusableMatchBoard', () => {
  it('does not crash when both active group and active line are absent', () => {
    const groupBoardRefs = { current: {} } as React.MutableRefObject<Record<string, HTMLDivElement | null>>
    const cardRefs = { current: {} } as React.MutableRefObject<Record<string, HTMLButtonElement | null>>

    render(
      <ConfusableMatchBoard
        boardGroups={[]}
        queuedGroups={[]}
        selectedCard={null}
        activeLine={null}
        errorCardIds={[]}
        successCardIds={[]}
        answeredGroupCount={0}
        totalGroups={0}
        completedGroup={null}
        errorComparison={null}
        groupBoardRefs={groupBoardRefs}
        cardRefs={cardRefs}
        onCardClick={vi.fn()}
      />,
    )

    expect(screen.getByText('等待下一组')).toBeInTheDocument()
    expect(screen.getByText('当前词族已完成')).toBeInTheDocument()
  })

  it('renders a success line only when the active line matches the active group', () => {
    const groupBoardRefs = { current: {} } as React.MutableRefObject<Record<string, HTMLDivElement | null>>
    const cardRefs = { current: {} } as React.MutableRefObject<Record<string, HTMLButtonElement | null>>

    const { container, rerender } = render(
      <ConfusableMatchBoard
        boardGroups={[createBoardGroup()]}
        queuedGroups={[]}
        selectedCard={null}
        activeLine={{ id: 'line-1', groupKey: 'group-2', path: 'M 1 1 L 2 2' }}
        errorCardIds={[]}
        successCardIds={[]}
        answeredGroupCount={0}
        totalGroups={1}
        completedGroup={null}
        errorComparison={null}
        groupBoardRefs={groupBoardRefs}
        cardRefs={cardRefs}
        onCardClick={vi.fn()}
      />,
    )

    expect(container.querySelector('.confusable-line')).toBeNull()

    rerender(
      <ConfusableMatchBoard
        boardGroups={[createBoardGroup()]}
        queuedGroups={[]}
        selectedCard={null}
        activeLine={{ id: 'line-1', groupKey: 'group-1', path: 'M 1 1 L 2 2' }}
        errorCardIds={[]}
        successCardIds={[]}
        answeredGroupCount={0}
        totalGroups={1}
        completedGroup={null}
        errorComparison={null}
        groupBoardRefs={groupBoardRefs}
        cardRefs={cardRefs}
        onCardClick={vi.fn()}
      />,
    )

    expect(container.querySelector('.confusable-line')).not.toBeNull()
  })
})
